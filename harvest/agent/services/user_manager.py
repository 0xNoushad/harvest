"""
User Manager - Handle multiple users with individual profiles and memory.

Each user gets:
- Personal wallet
- Conversation memory
- Trading preferences
- Performance tracking
- Persistent storage in SQLite
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from agent.core.database import Database

logger = logging.getLogger(__name__)


class UserProfile:
    """Individual user profile with memory and preferences."""
    
    def __init__(self, user_id: str, username: str = None, first_name: str = None):
        # Validate user_id
        from agent.security.security import SecurityValidator
        try:
            self.user_id = SecurityValidator.validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Invalid user_id: {e}")
            raise
        
        # Sanitize username and first_name if provided
        if username:
            try:
                self.username = SecurityValidator.sanitize_string(username, max_length=100)
            except ValueError:
                self.username = None
        else:
            self.username = None
        
        if first_name:
            try:
                self.first_name = SecurityValidator.sanitize_string(first_name, max_length=100)
            except ValueError:
                self.first_name = None
        else:
            self.first_name = None
        
        self.created_at = datetime.now().isoformat()
        
        # Trading preferences
        self.risk_tolerance = "medium"  # low, medium, high
        self.auto_execute = False
        self.strategies_enabled = {
            "airdrop_hunter": True,
            "airdrop_claimer": True,
            "yield_farmer": True,
            "liquid_staking": True,
            "nft_flipper": False,
            "arbitrage_trader": False,
            "bounty_hunter": True,
        }
        
        # Conversation memory
        self.conversation_history = []
        self.preferences = {}
        self.last_interaction = None
        
        # Wallet info
        self.wallet_address = None
        self.wallet_encrypted_path = None
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 50 messages
        if len(self.conversation_history) > 50:
            self.conversation_history = self.conversation_history[-50:]
        
        self.last_interaction = datetime.now().isoformat()
    
    def get_recent_context(self, limit: int = 10) -> list:
        """Get recent conversation for context."""
        return self.conversation_history[-limit:]
    
    def set_preference(self, key: str, value):
        """Store user preference."""
        self.preferences[key] = value
    
    def get_preference(self, key: str, default=None):
        """Get user preference."""
        return self.preferences.get(key, default)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "created_at": self.created_at,
            "risk_tolerance": self.risk_tolerance,
            "auto_execute": self.auto_execute,
            "strategies_enabled": self.strategies_enabled,
            "conversation_history": self.conversation_history,
            "preferences": self.preferences,
            "last_interaction": self.last_interaction,
            "wallet_address": self.wallet_address,
            "wallet_encrypted_path": self.wallet_encrypted_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserProfile":
        """Load from dictionary."""
        profile = cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name")
        )
        profile.created_at = data.get("created_at", profile.created_at)
        profile.risk_tolerance = data.get("risk_tolerance", "medium")
        profile.auto_execute = data.get("auto_execute", False)
        profile.strategies_enabled = data.get("strategies_enabled", profile.strategies_enabled)
        profile.conversation_history = data.get("conversation_history", [])
        profile.preferences = data.get("preferences", {})
        profile.last_interaction = data.get("last_interaction")
        profile.wallet_address = data.get("wallet_address")
        profile.wallet_encrypted_path = data.get("wallet_encrypted_path")
        return profile


class UserManager:
    """Manage multiple users with individual profiles and memory using SQLite database."""
    
    def __init__(self, storage_dir: str = "config/users", db_path: str = "config/harvest.db"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.users: Dict[str, UserProfile] = {}
        
        # Initialize database
        self.db = Database(db_path)
        
        # Load users from database
        self._load_all_users()
    
    def _load_all_users(self):
        """Load all user profiles from database."""
        db_users = self.db.get_all_users()
        for user_data in db_users:
            try:
                profile = UserProfile(
                    user_id=user_data['user_id'],
                    username=None,  # Not stored in DB
                    first_name=None  # Not stored in DB
                )
                
                # Load preferences
                if user_data['preferences']:
                    prefs = json.loads(user_data['preferences'])
                    profile.preferences = prefs
                    if 'strategies_enabled' in prefs:
                        profile.strategies_enabled = prefs['strategies_enabled']
                    if 'risk_tolerance' in prefs:
                        profile.risk_tolerance = prefs['risk_tolerance']
                    if 'auto_execute' in prefs:
                        profile.auto_execute = prefs['auto_execute']
                
                self.users[profile.user_id] = profile
                logger.info(f"Loaded user profile from DB: {profile.user_id}")
            except Exception as e:
                logger.error(f"Failed to load user {user_data['user_id']}: {e}")
    
    def get_or_create_user(
        self,
        user_id: str,
        username: str = None,
        first_name: str = None
    ) -> UserProfile:
        """Get existing user or create new profile. Names NOT stored in DB."""
        if user_id not in self.users:
            # Create in database (NO personal data)
            self.db.create_user(user_id)
            
            # Create profile object (names only in memory, not persisted)
            profile = UserProfile(user_id, username, first_name)
            self.users[user_id] = profile
            logger.info(f"Created new user profile: {user_id}")
        else:
            # Update name in memory only (not persisted)
            profile = self.users[user_id]
            if username:
                profile.username = username
            if first_name:
                profile.first_name = first_name
        
        # Update last active
        self.db.update_last_active(user_id)
        
        return self.users[user_id]
    
    def save_user(self, user_id: str):
        """Save user preferences to database (NO personal data)."""
        if user_id not in self.users:
            logger.warning(f"Cannot save unknown user: {user_id}")
            return
        
        profile = self.users[user_id]
        
        # Save ONLY preferences to database (no names, no wallet addresses)
        # Start with custom preferences, then override with specific fields
        preferences = {
            **profile.preferences,
            'strategies_enabled': profile.strategies_enabled,
            'risk_tolerance': profile.risk_tolerance,
            'auto_execute': profile.auto_execute,
        }
        
        self.db.update_user(
            user_id,
            preferences=json.dumps(preferences)
        )
    
    def add_conversation(self, user_id: str, role: str, content: str):
        """Add message to user's conversation history."""
        profile = self.get_or_create_user(user_id)
        
        # Add to database
        self.db.add_conversation(user_id, role, content)
        profile.add_message(role, content)
        self.save_user(user_id)
    
    def get_user_context(self, user_id: str, limit: int = 10) -> str:
        """Get formatted conversation context for AI from database."""
        # Get from database
        history = self.db.get_conversation_history(user_id, limit)
        
        if not history:
            return "No previous conversation."
        
        context = "Recent conversation:\n"
        for msg in history:
            context += f"{msg['role']}: {msg['message']}\n"
        
        return context
    
    def get_user_name(self, user_id: str) -> str:
        """Get user's preferred name."""
        if user_id in self.users:
            profile = self.users[user_id]
            return profile.first_name or profile.username or "User"
        return "User"
    
    def set_user_wallet(self, user_id: str, address: str, encrypted_path: str = None):
        """Associate wallet with user."""
        # Validate wallet address
        from agent.security.security import SecurityValidator
        try:
            address = SecurityValidator.validate_wallet_address(address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            raise
        
        profile = self.get_or_create_user(user_id)
        profile.wallet_address = address
        profile.wallet_encrypted_path = encrypted_path
        self.save_user(user_id)
    
    def get_user_wallet(self, user_id: str) -> Optional[str]:
        """Get user's wallet address."""
        if user_id in self.users:
            return self.users[user_id].wallet_address
        return None
    
    def enable_strategy(self, user_id: str, strategy: str, enabled: bool = True):
        """Enable/disable strategy for user."""
        # Validate strategy name
        from agent.security.security import SecurityValidator
        try:
            strategy = SecurityValidator.validate_strategy_name(strategy)
        except ValueError as e:
            logger.error(f"Invalid strategy name: {e}")
            raise
        
        profile = self.get_or_create_user(user_id)
        if strategy in profile.strategies_enabled:
            profile.strategies_enabled[strategy] = enabled
            self.save_user(user_id)
    
    def set_auto_execute(self, user_id: str, enabled: bool):
        """Set auto-execute mode for user."""
        profile = self.get_or_create_user(user_id)
        profile.auto_execute = enabled
        self.save_user(user_id)
    
    def get_all_users(self) -> list:
        """Get list of all user IDs."""
        return list(self.users.keys())
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get user statistics."""
        if user_id not in self.users:
            return {}
        
        profile = self.users[user_id]
        return {
            "user_id": user_id,
            "name": self.get_user_name(user_id),
            "created_at": profile.created_at,
            "last_interaction": profile.last_interaction,
            "total_messages": len(profile.conversation_history),
            "wallet_address": profile.wallet_address,
            "auto_execute": profile.auto_execute,
            "strategies_enabled": sum(profile.strategies_enabled.values()),
        }


if __name__ == "__main__":
    # Test user manager
    manager = UserManager(storage_dir="config/test_users")
    
    # Create test user
    user = manager.get_or_create_user("123456", "john_doe", "John")
    print(f"Created user: {user.first_name}")
    
    # Add conversation
    manager.add_conversation("123456", "user", "What's my balance?")
    manager.add_conversation("123456", "assistant", "Your balance is 10.5 SOL")
    
    # Get context
    context = manager.get_user_context("123456")
    print(f"\nContext:\n{context}")
    
    # Get stats
    stats = manager.get_user_stats("123456")
    print(f"\nStats: {stats}")
