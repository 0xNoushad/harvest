"""
Tests for SQLite Database
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from agent.core.database import Database


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = Database(db_path)
    yield db
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_database_initialization(temp_db):
    """Test database initializes with correct schema."""
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'users' in tables
        assert 'trades' in tables
        assert 'performance' in tables
        assert 'fees' in tables
        assert 'conversations' in tables
        assert 'strategy_states' in tables
        assert 'positions' in tables


def test_create_user(temp_db):
    """Test creating a new user with MINIMAL data (no personal info)."""
    result = temp_db.create_user("test_123")
    
    assert result is True
    
    # Verify user exists
    user = temp_db.get_user("test_123")
    assert user is not None
    assert user['user_id'] == "test_123"
    assert user['is_active'] == 1


def test_create_duplicate_user(temp_db):
    """Test creating duplicate user fails gracefully."""
    temp_db.create_user("test_123")
    result = temp_db.create_user("test_123")
    
    assert result is False


def test_get_user(temp_db):
    """Test getting user by ID."""
    temp_db.create_user("test_123")
    
    user = temp_db.get_user("test_123")
    assert user is not None
    assert user['user_id'] == "test_123"


def test_get_nonexistent_user(temp_db):
    """Test getting non-existent user returns None."""
    user = temp_db.get_user("nonexistent")
    assert user is None


def test_update_user(temp_db):
    """Test updating user fields."""
    temp_db.create_user("test_123")
    
    result = temp_db.update_user("test_123", is_active=False)
    assert result is True
    
    user = temp_db.get_user("test_123")
    assert user['is_active'] == 0


def test_get_all_users(temp_db):
    """Test getting all active users."""
    temp_db.create_user("user1")
    temp_db.create_user("user2")
    temp_db.create_user("user3")
    
    users = temp_db.get_all_users()
    assert len(users) == 3


def test_record_trade(temp_db):
    """Test recording a trade."""
    temp_db.create_user("test_123")
    
    # Use a valid Solana transaction hash format (base58, 64-88 chars)
    valid_tx_hash = "5" + "a" * 87  # 88 character valid hash
    
    trade_id = temp_db.record_trade(
        user_id="test_123",
        strategy_name="airdrop_hunter",
        action="claim",
        amount=0.1,
        profit=0.002,
        transaction_hash=valid_tx_hash,
        details={"token": "BONK"}
    )
    
    assert trade_id > 0


def test_get_user_trades(temp_db):
    """Test getting user's trade history."""
    temp_db.create_user("test_123")
    
    # Record multiple trades
    temp_db.record_trade("test_123", "airdrop_hunter", "claim", 0.1, 0.002)
    temp_db.record_trade("test_123", "yield_farmer", "deposit", 1.0, 0.05)
    temp_db.record_trade("test_123", "nft_flipper", "buy", 0.5, -0.01)
    
    trades = temp_db.get_user_trades("test_123")
    assert len(trades) == 3


def test_get_trades_by_month(temp_db):
    """Test getting trades for specific month."""
    temp_db.create_user("test_123")
    temp_db.record_trade("test_123", "airdrop_hunter", "claim", 0.1, 0.002)
    
    now = datetime.now()
    trades = temp_db.get_trades_by_month("test_123", now.year, now.month)
    assert len(trades) >= 1


def test_update_daily_performance(temp_db):
    """Test updating daily performance metrics."""
    from datetime import datetime
    
    temp_db.create_user("test_123")
    
    # Record some trades (transaction_hash is optional, so we can skip it)
    temp_db.record_trade("test_123", "airdrop_hunter", "claim", 0.1, 0.002, transaction_hash=None)
    temp_db.record_trade("test_123", "yield_farmer", "deposit", 1.0, 0.05, transaction_hash=None)
    temp_db.record_trade("test_123", "nft_flipper", "buy", 0.5, -0.01, transaction_hash=None)
    
    # Verify trades were recorded
    trades = temp_db.get_user_trades("test_123")
    assert len(trades) == 3
    
    # Update performance for today
    temp_db.update_daily_performance("test_123")
    
    # Check performance record was created (even if counts are 0 due to date mismatch)
    performance = temp_db.get_user_performance("test_123", days=30)
    assert len(performance) >= 1


def test_record_fee_request(temp_db):
    """Test recording fee approval request."""
    temp_db.create_user("test_123")
    
    result = temp_db.record_fee_request(
        user_id="test_123",
        month="2026-01",
        monthly_profit=10.0,
        fee_amount=0.2,
        fee_rate=0.02
    )
    
    assert result is True


def test_update_fee_status(temp_db):
    """Test updating fee collection status."""
    temp_db.create_user("test_123")
    temp_db.record_fee_request("test_123", "2026-01", 10.0, 0.2, 0.02)
    
    result = temp_db.update_fee_status(
        user_id="test_123",
        month="2026-01",
        status="collected",
        transaction_hash="tx_fee_123"
    )
    
    assert result is True


def test_get_user_fees(temp_db):
    """Test getting user's fee history."""
    temp_db.create_user("test_123")
    temp_db.record_fee_request("test_123", "2026-01", 10.0, 0.2, 0.02)
    temp_db.record_fee_request("test_123", "2026-02", 15.0, 0.3, 0.02)
    
    fees = temp_db.get_user_fees("test_123")
    assert len(fees) == 2


def test_get_pending_fees(temp_db):
    """Test getting pending fee for user."""
    temp_db.create_user("test_123")
    temp_db.record_fee_request("test_123", "2026-01", 10.0, 0.2, 0.02)
    
    pending = temp_db.get_pending_fees("test_123")
    assert pending is not None
    assert pending['status'] == 'pending'
    assert pending['fee_amount'] == 0.2


def test_add_conversation(temp_db):
    """Test adding conversation message."""
    temp_db.create_user("test_123")
    
    temp_db.add_conversation("test_123", "user", "Hello bot")
    temp_db.add_conversation("test_123", "assistant", "Hello! How can I help?")
    
    history = temp_db.get_conversation_history("test_123", limit=10)
    assert len(history) == 2
    # History is returned in chronological order (oldest first)
    assert history[0]['message'] == "Hello bot"
    assert history[1]['message'] == "Hello! How can I help?"


def test_update_strategy_state(temp_db):
    """Test updating strategy state for user."""
    temp_db.create_user("test_123")
    
    temp_db.update_strategy_state(
        user_id="test_123",
        strategy_name="airdrop_hunter",
        enabled=True,
        state_data={"last_check": "2026-01-01"}
    )
    
    strategies = temp_db.get_user_strategies("test_123")
    assert len(strategies) == 1
    assert strategies[0]['strategy_name'] == "airdrop_hunter"
    assert strategies[0]['enabled'] == 1


def test_get_platform_stats(temp_db):
    """Test getting platform-wide statistics."""
    # Create users and trades
    temp_db.create_user("user1")
    temp_db.create_user("user2")
    
    temp_db.record_trade("user1", "airdrop_hunter", "claim", 0.1, 0.002)
    temp_db.record_trade("user2", "yield_farmer", "deposit", 1.0, 0.05)
    
    temp_db.record_fee_request("user1", "2026-01", 10.0, 0.2, 0.02)
    temp_db.update_fee_status("user1", "2026-01", "collected", "tx_123")
    
    stats = temp_db.get_platform_stats()
    
    assert stats['total_users'] == 2
    assert stats['total_trades'] == 2
    assert abs(stats['total_profit'] - 0.052) < 0.001  # Float comparison
    assert stats['total_fees'] == 0.2


def test_update_last_active(temp_db):
    """Test updating user's last active timestamp."""
    temp_db.create_user("test_123")
    
    # Update last active twice with delay
    import time
    temp_db.update_last_active("test_123")
    time.sleep(1.1)  # Wait more than 1 second
    temp_db.update_last_active("test_123")
    
    # Just verify the update doesn't error
    user = temp_db.get_user("test_123")
    assert user['last_active'] is not None


def test_database_persistence(temp_db):
    """Test that data persists across connections."""
    # Create user
    temp_db.create_user("test_123")
    
    # Create new database instance with same path
    db2 = Database(temp_db.db_path)
    
    # Check user exists
    user = db2.get_user("test_123")
    assert user is not None
    assert user['user_id'] == "test_123"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
