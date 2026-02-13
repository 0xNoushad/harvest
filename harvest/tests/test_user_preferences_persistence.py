"""
Test user preferences persistence across bot restarts.

This test verifies that UserManager.save_user stores preferences to database
and that preferences survive bot restart (Requirement 8.4).
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agent.services.user_manager import UserManager
from agent.core.database import Database


class TestUserPreferencesPersistence:
    """Test user preferences persistence."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test."""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def db_path(self, temp_dir):
        """Create temporary database path."""
        return str(Path(temp_dir) / "test_harvest.db")
    
    @pytest.fixture
    def storage_dir(self, temp_dir):
        """Create temporary storage directory."""
        return str(Path(temp_dir) / "users")
    
    def test_preferences_persist_after_save(self, db_path, storage_dir):
        """Test that preferences are saved to database."""
        # Create user manager
        manager = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        # Create user and set preferences
        user_id = "test_user_123"
        profile = manager.get_or_create_user(user_id, username="testuser", first_name="Test")
        
        # Set various preferences
        profile.risk_tolerance = "high"
        profile.auto_execute = True
        profile.strategies_enabled["airdrop_hunter"] = False
        profile.strategies_enabled["arbitrage_trader"] = True
        profile.set_preference("custom_key", "custom_value")
        
        # Save user
        manager.save_user(user_id)
        
        # Verify preferences are in database
        db = Database(db_path)
        user_data = db.get_user(user_id)
        
        assert user_data is not None
        assert user_data["preferences"] is not None
        
        # Parse preferences JSON
        import json
        prefs = json.loads(user_data["preferences"])
        
        assert prefs["risk_tolerance"] == "high"
        assert prefs["auto_execute"] is True
        assert prefs["strategies_enabled"]["airdrop_hunter"] is False
        assert prefs["strategies_enabled"]["arbitrage_trader"] is True
        assert prefs["custom_key"] == "custom_value"
    
    def test_preferences_survive_restart(self, db_path, storage_dir):
        """Test that preferences survive bot restart."""
        # First session: Create user and set preferences
        manager1 = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        user_id = "test_user_456"
        profile1 = manager1.get_or_create_user(user_id, username="testuser2", first_name="Test2")
        
        # Set preferences
        profile1.risk_tolerance = "low"
        profile1.auto_execute = False
        profile1.strategies_enabled["yield_farmer"] = False
        profile1.strategies_enabled["nft_flipper"] = True
        profile1.set_preference("theme", "dark")
        profile1.set_preference("notifications", True)
        
        # Save user
        manager1.save_user(user_id)
        
        # Simulate restart: Create new UserManager instance
        manager2 = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        # Get user from new manager (should load from database)
        profile2 = manager2.get_or_create_user(user_id)
        
        # Verify all preferences were loaded
        assert profile2.risk_tolerance == "low"
        assert profile2.auto_execute is False
        assert profile2.strategies_enabled["yield_farmer"] is False
        assert profile2.strategies_enabled["nft_flipper"] is True
        assert profile2.get_preference("theme") == "dark"
        assert profile2.get_preference("notifications") is True
    
    def test_multiple_users_preferences_isolated(self, db_path, storage_dir):
        """Test that multiple users' preferences are isolated."""
        manager = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        # Create multiple users with different preferences
        user1_id = "user_001"
        user2_id = "user_002"
        user3_id = "user_003"
        
        profile1 = manager.get_or_create_user(user1_id)
        profile1.risk_tolerance = "high"
        profile1.auto_execute = True
        manager.save_user(user1_id)
        
        profile2 = manager.get_or_create_user(user2_id)
        profile2.risk_tolerance = "medium"
        profile2.auto_execute = False
        manager.save_user(user2_id)
        
        profile3 = manager.get_or_create_user(user3_id)
        profile3.risk_tolerance = "low"
        profile3.auto_execute = True
        manager.save_user(user3_id)
        
        # Simulate restart
        manager2 = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        # Verify each user's preferences are correct
        reloaded1 = manager2.get_or_create_user(user1_id)
        assert reloaded1.risk_tolerance == "high"
        assert reloaded1.auto_execute is True
        
        reloaded2 = manager2.get_or_create_user(user2_id)
        assert reloaded2.risk_tolerance == "medium"
        assert reloaded2.auto_execute is False
        
        reloaded3 = manager2.get_or_create_user(user3_id)
        assert reloaded3.risk_tolerance == "low"
        assert reloaded3.auto_execute is True
    
    def test_strategy_preferences_persist(self, db_path, storage_dir):
        """Test that strategy enable/disable preferences persist."""
        manager = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        user_id = "strategy_test_user"
        profile = manager.get_or_create_user(user_id)
        
        # Modify strategy preferences
        manager.enable_strategy(user_id, "airdrop_hunter", False)
        manager.enable_strategy(user_id, "arbitrage_trader", True)
        manager.enable_strategy(user_id, "nft_flipper", True)
        
        # Simulate restart
        manager2 = UserManager(storage_dir=storage_dir, db_path=db_path)
        profile2 = manager2.get_or_create_user(user_id)
        
        # Verify strategy preferences persisted
        assert profile2.strategies_enabled["airdrop_hunter"] is False
        assert profile2.strategies_enabled["arbitrage_trader"] is True
        assert profile2.strategies_enabled["nft_flipper"] is True
    
    def test_auto_execute_preference_persists(self, db_path, storage_dir):
        """Test that auto_execute preference persists."""
        manager = UserManager(storage_dir=storage_dir, db_path=db_path)
        
        user_id = "auto_exec_test_user"
        
        # Set auto_execute to True
        manager.set_auto_execute(user_id, True)
        
        # Verify it was saved to database
        import json
        db = Database(db_path)
        user_data = db.get_user(user_id)
        prefs = json.loads(user_data["preferences"])
        assert prefs["auto_execute"] is True, f"Expected True in DB after first save, got {prefs.get('auto_execute')}"
        
        # Simulate restart
        manager2 = UserManager(storage_dir=storage_dir, db_path=db_path)
        profile2 = manager2.get_or_create_user(user_id)
        
        assert profile2.auto_execute is True
        
        # Change to False
        manager2.set_auto_execute(user_id, False)
        
        # Verify it was saved to database
        user_data2 = db.get_user(user_id)
        prefs2 = json.loads(user_data2["preferences"])
        assert prefs2["auto_execute"] is False, f"Expected False in DB after second save, got {prefs2.get('auto_execute')}"
        
        # Simulate another restart
        manager3 = UserManager(storage_dir=storage_dir, db_path=db_path)
        profile3 = manager3.get_or_create_user(user_id)
        
        assert profile3.auto_execute is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
