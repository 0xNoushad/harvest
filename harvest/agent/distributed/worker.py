"""
Worker process for handling a subset of users.

Each worker:
- Handles 50-100 users
- Runs independent event loop
- Shares state via Redis
- Reports health to manager
"""

import asyncio
import logging
import os
from typing import List, Optional
from datetime import datetime
import signal

from agent.distributed.redis_cache import RedisCache
from agent.distributed.health_server import run_health_server
from agent.trading.loop import AgentLoop
from agent.core.wallet import WalletManager
from agent.trading.scanner import Scanner
from agent.core.provider import GroqProvider
from agent.services.notifier import Notifier
from agent.monitoring.user_control import UserControl
from agent.trading.risk_manager import RiskManager
from agent.trading.performance import PerformanceTracker
from agent.services.user_manager import UserManager

logger = logging.getLogger(__name__)


class Worker:
    """
    Worker process that handles a subset of users.
    
    Each worker:
    - Manages 50-100 users
    - Runs independent scan cycles
    - Shares cache via Redis
    - Reports health status
    """
    
    def __init__(
        self,
        worker_id: str,
        redis_url: str,
        user_ids: List[str],
        config: dict
    ):
        """
        Initialize worker.
        
        Args:
            worker_id: Unique worker identifier
            redis_url: Redis connection URL
            user_ids: List of user IDs this worker handles
            config: Configuration dictionary
        """
        self.worker_id = worker_id
        self.redis_url = redis_url
        self.user_ids = user_ids
        self.config = config
        
        self.redis_cache: Optional[RedisCache] = None
        self.user_loops: dict = {}  # user_id -> AgentLoop
        self.running = False
        self.health_server = None
        
        logger.info(
            f"Worker {worker_id} initialized with {len(user_ids)} users"
        )
    
    async def start(self):
        """Start worker process."""
        self.running = True
        logger.info(f"Worker {self.worker_id} starting...")
        
        try:
            # Start health check server (for Render free tier)
            port = int(os.getenv("PORT", "8080"))
            self.health_server = await run_health_server(
                self.worker_id,
                worker=self,
                port=port
            )
            logger.info(f"Health server started on port {port}")
            
            # Connect to Redis
            self.redis_cache = RedisCache(self.redis_url)
            await self.redis_cache.connect()
            logger.info("Connected to Redis")
            
            # Initialize agent loops for each user
            await self._initialize_user_loops()
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            # Start scan cycles for all users
            scan_tasks = [
                asyncio.create_task(self._user_scan_loop(user_id))
                for user_id in self.user_ids
            ]
            
            # Wait for all tasks
            await asyncio.gather(heartbeat_task, *scan_tasks)
            
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def _initialize_user_loops(self):
        """Initialize AgentLoop for each user."""
        logger.info(f"Initializing loops for {len(self.user_ids)} users...")
        
        for user_id in self.user_ids:
            try:
                # Get user's wallet
                # TODO: Load from multi-wallet manager
                wallet = WalletManager(network=self.config.get("network", "mainnet-beta"))
                
                # Initialize components
                scanner = Scanner(strategies=[])  # TODO: Load strategies
                provider = GroqProvider(api_key=self.config.get("groq_api_key"))
                notifier = Notifier(
                    self.config.get("telegram_token"),
                    user_id  # Use user_id as chat_id
                )
                user_control = UserControl()
                risk_manager = RiskManager()
                performance_tracker = PerformanceTracker()
                
                # Create agent loop
                agent_loop = AgentLoop(
                    wallet=wallet,
                    scanner=scanner,
                    provider=provider,
                    notifier=notifier,
                    user_control=user_control,
                    risk_manager=risk_manager,
                    performance_tracker=performance_tracker,
                    scan_interval=self.config.get("scan_interval", 300)
                )
                
                self.user_loops[user_id] = agent_loop
                
                logger.info(f"Initialized loop for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize loop for user {user_id}: {e}")
                continue
    
    async def _user_scan_loop(self, user_id: str):
        """
        Run scan loop for a single user.
        
        Args:
            user_id: User ID to scan for
        """
        agent_loop = self.user_loops.get(user_id)
        if not agent_loop:
            logger.error(f"No agent loop for user {user_id}")
            return
        
        logger.info(f"Starting scan loop for user {user_id}")
        
        while self.running:
            try:
                # Check if user is still assigned to this worker
                assigned_worker = await self.redis_cache.get_user_worker(user_id)
                if assigned_worker != self.worker_id:
                    logger.warning(
                        f"User {user_id} reassigned to {assigned_worker}, stopping"
                    )
                    break
                
                # Run scan cycle
                await agent_loop.scan_cycle()
                
                # Wait for next scan
                await asyncio.sleep(self.config.get("scan_interval", 300))
                
            except Exception as e:
                logger.error(f"Error in scan loop for user {user_id}: {e}")
                await asyncio.sleep(10)
    
    async def _heartbeat_loop(self):
        """Send heartbeat to Redis every 30 seconds."""
        while self.running:
            try:
                await self.redis_cache.set_worker_heartbeat(self.worker_id)
                logger.debug(f"Worker {self.worker_id} heartbeat sent")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Stop worker gracefully."""
        logger.info(f"Worker {self.worker_id} stopping...")
        self.running = False
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info(f"Worker {self.worker_id} cleaning up...")
        
        # Close all agent loops
        for user_id, agent_loop in self.user_loops.items():
            try:
                agent_loop.stop()
            except Exception as e:
                logger.error(f"Error stopping loop for user {user_id}: {e}")
        
        # Disconnect from Redis
        if self.redis_cache:
            await self.redis_cache.disconnect()
        
        logger.info(f"Worker {self.worker_id} cleanup complete")
    
    def get_status(self) -> dict:
        """Get worker status."""
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "user_count": len(self.user_ids),
            "active_loops": len(self.user_loops),
        }


async def run_worker(
    worker_id: str,
    redis_url: str,
    user_ids: List[str],
    config: dict
):
    """
    Run worker process.
    
    Args:
        worker_id: Worker identifier
        redis_url: Redis connection URL
        user_ids: List of user IDs to handle
        config: Configuration dictionary
    """
    worker = Worker(worker_id, redis_url, user_ids, config)
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await worker.start()
    except Exception as e:
        logger.error(f"Worker {worker_id} crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    import sys
    
    # Get worker config from environment
    worker_id = os.getenv("WORKER_ID", "worker_1")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # For testing, use dummy user IDs
    user_ids = [f"user_{i}" for i in range(1, 51)]  # 50 users
    
    config = {
        "network": os.getenv("SOLANA_NETWORK", "devnet"),
        "groq_api_key": os.getenv("GROQ_API_KEY"),
        "telegram_token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "scan_interval": int(os.getenv("SCAN_INTERVAL", "300")),
    }
    
    # Run worker
    asyncio.run(run_worker(worker_id, redis_url, user_ids, config))
