"""
Worker Manager - Orchestrates multiple worker processes.

Responsibilities:
- Spawn and manage worker processes
- Assign users to workers
- Monitor worker health
- Handle worker failures
- Load balancing
"""

import asyncio
import logging
import subprocess
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from agent.distributed.redis_cache import RedisCache
from agent.services.user_manager import UserManager

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages multiple worker processes for horizontal scaling.
    
    Features:
    - Spawns N worker processes
    - Assigns users evenly across workers
    - Monitors worker health
    - Restarts failed workers
    - Rebalances load
    """
    
    def __init__(
        self,
        redis_url: str,
        num_workers: int = 10,
        users_per_worker: int = 50,
        config: dict = None
    ):
        """
        Initialize worker manager.
        
        Args:
            redis_url: Redis connection URL
            num_workers: Number of worker processes to spawn
            users_per_worker: Target users per worker
            config: Configuration dictionary
        """
        self.redis_url = redis_url
        self.num_workers = num_workers
        self.users_per_worker = users_per_worker
        self.config = config or {}
        
        self.redis_cache: Optional[RedisCache] = None
        self.user_manager: Optional[UserManager] = None
        self.workers: Dict[str, subprocess.Popen] = {}
        self.user_assignments: Dict[str, str] = {}  # user_id -> worker_id
        
        self.running = False
        
        logger.info(
            f"WorkerManager initialized: {num_workers} workers, "
            f"{users_per_worker} users/worker"
        )
    
    async def start(self):
        """Start worker manager."""
        self.running = True
        logger.info("WorkerManager starting...")
        
        try:
            # Connect to Redis
            self.redis_cache = RedisCache(self.redis_url)
            await self.redis_cache.connect()
            logger.info("Connected to Redis")
            
            # Initialize user manager
            self.user_manager = UserManager()
            
            # Get all users
            all_users = self.user_manager.get_all_users()
            logger.info(f"Found {len(all_users)} total users")
            
            # Assign users to workers
            await self._assign_users_to_workers(all_users)
            
            # Spawn worker processes
            await self._spawn_workers()
            
            # Start monitoring loop
            await self._monitor_loop()
            
        except Exception as e:
            logger.error(f"WorkerManager error: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def _assign_users_to_workers(self, user_ids: List[str]):
        """
        Assign users evenly across workers.
        
        Args:
            user_ids: List of all user IDs
        """
        logger.info(f"Assigning {len(user_ids)} users to {self.num_workers} workers...")
        
        # Calculate users per worker
        users_per_worker = len(user_ids) // self.num_workers
        remainder = len(user_ids) % self.num_workers
        
        user_idx = 0
        for worker_num in range(self.num_workers):
            worker_id = f"worker_{worker_num + 1}"
            
            # Calculate how many users this worker gets
            num_users = users_per_worker + (1 if worker_num < remainder else 0)
            
            # Assign users
            worker_users = user_ids[user_idx:user_idx + num_users]
            
            for user_id in worker_users:
                self.user_assignments[user_id] = worker_id
                await self.redis_cache.assign_user_to_worker(user_id, worker_id)
            
            logger.info(f"{worker_id}: {len(worker_users)} users assigned")
            
            user_idx += num_users
    
    async def _spawn_workers(self):
        """Spawn all worker processes."""
        logger.info(f"Spawning {self.num_workers} worker processes...")
        
        for worker_num in range(self.num_workers):
            worker_id = f"worker_{worker_num + 1}"
            
            # Get users assigned to this worker
            worker_users = [
                user_id for user_id, wid in self.user_assignments.items()
                if wid == worker_id
            ]
            
            # Spawn worker process
            await self._spawn_worker(worker_id, worker_users)
    
    async def _spawn_worker(self, worker_id: str, user_ids: List[str]):
        """
        Spawn a single worker process.
        
        Args:
            worker_id: Worker identifier
            user_ids: List of user IDs for this worker
        """
        try:
            logger.info(f"Spawning {worker_id} with {len(user_ids)} users...")
            
            # Prepare environment
            env = os.environ.copy()
            env["WORKER_ID"] = worker_id
            env["REDIS_URL"] = self.redis_url
            env["USER_IDS"] = ",".join(user_ids)
            
            # Add config to environment
            for key, value in self.config.items():
                env[key.upper()] = str(value)
            
            # Spawn process
            process = subprocess.Popen(
                ["python", "-m", "agent.distributed.worker"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.workers[worker_id] = process
            logger.info(f"{worker_id} spawned (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to spawn {worker_id}: {e}")
    
    async def _monitor_loop(self):
        """Monitor worker health and restart failed workers."""
        logger.info("Starting worker monitoring loop...")
        
        while self.running:
            try:
                # Check worker heartbeats
                active_workers = await self.redis_cache.get_active_workers()
                
                # Check for missing workers
                for worker_id in self.workers.keys():
                    if worker_id not in active_workers:
                        logger.warning(f"{worker_id} heartbeat missing!")
                        await self._restart_worker(worker_id)
                
                # Check for crashed processes
                for worker_id, process in list(self.workers.items()):
                    if process.poll() is not None:
                        logger.error(f"{worker_id} process crashed!")
                        await self._restart_worker(worker_id)
                
                # Log status
                logger.info(
                    f"Workers: {len(active_workers)}/{self.num_workers} active"
                )
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)
    
    async def _restart_worker(self, worker_id: str):
        """
        Restart a failed worker.
        
        Args:
            worker_id: Worker to restart
        """
        logger.info(f"Restarting {worker_id}...")
        
        try:
            # Kill old process if still running
            if worker_id in self.workers:
                process = self.workers[worker_id]
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                del self.workers[worker_id]
            
            # Get users for this worker
            worker_users = [
                user_id for user_id, wid in self.user_assignments.items()
                if wid == worker_id
            ]
            
            # Spawn new process
            await self._spawn_worker(worker_id, worker_users)
            
            logger.info(f"{worker_id} restarted successfully")
            
        except Exception as e:
            logger.error(f"Failed to restart {worker_id}: {e}")
    
    async def stop(self):
        """Stop all workers gracefully."""
        logger.info("Stopping all workers...")
        self.running = False
        
        for worker_id, process in self.workers.items():
            try:
                logger.info(f"Stopping {worker_id}...")
                process.terminate()
                process.wait(timeout=10)
            except Exception as e:
                logger.error(f"Error stopping {worker_id}: {e}")
                process.kill()
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("WorkerManager cleaning up...")
        
        # Stop all workers
        await self.stop()
        
        # Disconnect from Redis
        if self.redis_cache:
            await self.redis_cache.disconnect()
        
        logger.info("WorkerManager cleanup complete")
    
    def get_status(self) -> dict:
        """Get manager status."""
        return {
            "running": self.running,
            "num_workers": self.num_workers,
            "active_workers": len(self.workers),
            "total_users": len(self.user_assignments),
        }


async def main():
    """Run worker manager."""
    import os
    
    # Get config from environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    num_workers = int(os.getenv("NUM_WORKERS", "10"))
    users_per_worker = int(os.getenv("USERS_PER_WORKER", "50"))
    
    config = {
        "network": os.getenv("SOLANA_NETWORK", "devnet"),
        "groq_api_key": os.getenv("GROQ_API_KEY"),
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "scan_interval": int(os.getenv("SCAN_INTERVAL", "300")),
    }
    
    # Create and start manager
    manager = WorkerManager(
        redis_url=redis_url,
        num_workers=num_workers,
        users_per_worker=users_per_worker,
        config=config
    )
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
