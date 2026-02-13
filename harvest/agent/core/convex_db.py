"""
Convex database adapter.

Replaces PostgreSQL/SQLite with Convex for serverless database.
"""

import os
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConvexDB:
    """
    Convex database client.
    
    Provides same interface as Database class but uses Convex backend.
    """
    
    def __init__(self, url: str = None, site_url: str = None):
        """
        Initialize Convex client.
        
        Args:
            url: Convex cloud URL (default: from CONVEX_URL env)
            site_url: Convex site URL (default: from CONVEX_SITE_URL env)
        """
        self.url = url or os.getenv("CONVEX_URL")
        self.site_url = site_url or os.getenv("CONVEX_SITE_URL")
        
        if not self.url:
            raise ValueError("CONVEX_URL not set")
        
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"ConvexDB initialized: {self.url}")
    
    async def query(self, function: str, args: dict = None) -> Any:
        """
        Query Convex function.
        
        Args:
            function: Function path (e.g., "users:get")
            args: Function arguments
        
        Returns:
            Query result
        """
        try:
            response = await self.client.post(
                f"{self.url}/api/query",
                json={
                    "path": function,
                    "args": args or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Convex query failed: {function} - {e}")
            raise
    
    async def mutation(self, function: str, args: dict = None) -> Any:
        """
        Run Convex mutation.
        
        Args:
            function: Function path (e.g., "users:create")
            args: Function arguments
        
        Returns:
            Mutation result
        """
        try:
            response = await self.client.post(
                f"{self.url}/api/mutation",
                json={
                    "path": function,
                    "args": args or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Convex mutation failed: {function} - {e}")
            raise
    
    # User methods (compatible with Database interface)
    
    async def create_user(self, user_id: str):
        """Create user in Convex."""
        try:
            await self.mutation("users:create", {"userId": user_id})
            logger.info(f"Created user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {e}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user from Convex."""
        try:
            return await self.query("users:get", {"userId": user_id})
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def get_all_users(self) -> List[Dict]:
        """Get all users from Convex."""
        try:
            return await self.query("users:list", {})
        except Exception as e:
            logger.error(f"Failed to get all users: {e}")
            return []
    
    async def update_user(
        self,
        user_id: str,
        preferences: str = None,
        last_active: str = None
    ):
        """Update user in Convex."""
        try:
            data = {}
            if preferences:
                data["preferences"] = preferences
            if last_active:
                data["lastActive"] = last_active
            
            await self.mutation("users:update", {
                "userId": user_id,
                "data": data
            })
            logger.debug(f"Updated user: {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise
    
    async def update_last_active(self, user_id: str):
        """Update user's last active timestamp."""
        await self.update_user(
            user_id,
            last_active=datetime.now().isoformat()
        )
    
    # Conversation methods
    
    async def add_conversation(
        self,
        user_id: str,
        role: str,
        message: str
    ):
        """Add conversation message."""
        try:
            await self.mutation("conversations:create", {
                "userId": user_id,
                "role": role,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            logger.debug(f"Added conversation for {user_id}")
        except Exception as e:
            logger.error(f"Failed to add conversation: {e}")
            raise
    
    async def get_conversation_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get conversation history."""
        try:
            return await self.query("conversations:list", {
                "userId": user_id,
                "limit": limit
            })
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []
    
    # Trade methods
    
    async def create_trade(
        self,
        user_id: str,
        strategy_name: str,
        expected_profit: float,
        actual_profit: float,
        transaction_hash: str,
        was_successful: bool,
        error_message: str = None,
        gas_fees: float = 0.0,
        execution_time_ms: int = 0
    ):
        """Create trade record."""
        try:
            await self.mutation("trades:create", {
                "userId": user_id,
                "strategyName": strategy_name,
                "timestamp": datetime.now().isoformat(),
                "expectedProfit": expected_profit,
                "actualProfit": actual_profit,
                "transactionHash": transaction_hash,
                "wasSuccessful": was_successful,
                "errorMessage": error_message,
                "gasFees": gas_fees,
                "executionTimeMs": execution_time_ms
            })
            logger.info(f"Created trade for {user_id}: {strategy_name}")
        except Exception as e:
            logger.error(f"Failed to create trade: {e}")
            raise
    
    async def get_trades(
        self,
        user_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get trades."""
        try:
            args = {"limit": limit}
            if user_id:
                args["userId"] = user_id
            
            return await self.query("trades:list", args)
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return []
    
    async def get_user_stats(self, user_id: str) -> Dict:
        """Get user statistics."""
        try:
            return await self.query("users:stats", {"userId": user_id})
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {}
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
        logger.info("ConvexDB client closed")


# Compatibility alias
Database = ConvexDB


if __name__ == "__main__":
    import asyncio
    
    async def test_convex():
        """Test Convex connection."""
        print("\n🧪 Testing Convex Database\n")
        print("=" * 60)
        
        # Initialize
        db = ConvexDB()
        
        try:
            # Test user creation
            print("1️⃣  Creating test user...")
            await db.create_user("test_user_123")
            print("   ✅ User created")
            
            # Test user retrieval
            print("2️⃣  Getting user...")
            user = await db.get_user("test_user_123")
            print(f"   ✅ User retrieved: {user}")
            
            # Test conversation
            print("3️⃣  Adding conversation...")
            await db.add_conversation("test_user_123", "user", "Hello!")
            print("   ✅ Conversation added")
            
            # Test trade
            print("4️⃣  Creating trade...")
            await db.create_trade(
                user_id="test_user_123",
                strategy_name="test_strategy",
                expected_profit=0.1,
                actual_profit=0.12,
                transaction_hash="test_tx_123",
                was_successful=True
            )
            print("   ✅ Trade created")
            
            # Test stats
            print("5️⃣  Getting stats...")
            stats = await db.get_user_stats("test_user_123")
            print(f"   ✅ Stats: {stats}")
            
            print("\n" + "=" * 60)
            print("✅ All tests passed!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
        finally:
            await db.close()
    
    asyncio.run(test_convex())
