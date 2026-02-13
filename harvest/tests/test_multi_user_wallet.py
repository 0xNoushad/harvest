"""Tests for MultiUserWalletManager."""

import pytest
import asyncio
from pathlib import Path
import shutil

from agent.core.multi_user_wallet import MultiUserWalletManager
from agent.core.database import Database


@pytest.fixture
def test_database():
    """Create a test database."""
    db_path = "test_multi_user_wallet.db"
    db = Database(db_path)
    yield db
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def test_wallet_manager(test_database):
    """Create a test MultiUserWalletManager."""
    storage_dir = "test_secure_wallets"
    manager = MultiUserWalletManager(
        database=test_database,
        network="devnet",
        storage_dir=storage_dir
    )
    yield manager
    # Cleanup
    shutil.rmtree(storage_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_create_wallet(test_wallet_manager):
    """Test wallet creation."""
    user_id = "test_user_1"
    
    # Create wallet
    public_key, mnemonic = await test_wallet_manager.create_wallet(user_id)
    
    # Verify public key is returned
    assert public_key is not None
    assert len(public_key) > 0
    
    # Verify mnemonic is 12 words
    words = mnemonic.split()
    assert len(words) == 12
    
    # Verify wallet is in database
    wallet_metadata = test_wallet_manager.database.get_user_wallet(user_id)
    assert wallet_metadata is not None
    assert wallet_metadata["user_id"] == user_id
    assert wallet_metadata["public_key"] == public_key


@pytest.mark.asyncio
async def test_duplicate_wallet_prevention(test_wallet_manager):
    """Test that duplicate wallet creation is prevented."""
    user_id = "test_user_2"
    
    # Create first wallet
    await test_wallet_manager.create_wallet(user_id)
    
    # Try to create second wallet - should raise ValueError
    with pytest.raises(ValueError, match="already have a wallet"):
        await test_wallet_manager.create_wallet(user_id)


@pytest.mark.asyncio
async def test_import_wallet(test_wallet_manager):
    """Test wallet import from mnemonic."""
    user_id = "test_user_3"
    
    # Create a wallet first to get a valid mnemonic
    _, mnemonic = await test_wallet_manager.create_wallet("temp_user")
    
    # Delete the temp user's wallet from database
    # (we just needed a valid mnemonic)
    
    # Import wallet with the mnemonic
    public_key = await test_wallet_manager.import_wallet(user_id, mnemonic)
    
    # Verify public key is returned
    assert public_key is not None
    assert len(public_key) > 0
    
    # Verify wallet is in database
    wallet_metadata = test_wallet_manager.database.get_user_wallet(user_id)
    assert wallet_metadata is not None
    assert wallet_metadata["user_id"] == user_id


@pytest.mark.asyncio
async def test_import_invalid_mnemonic(test_wallet_manager):
    """Test that invalid mnemonic is rejected."""
    user_id = "test_user_4"
    
    # Try to import with invalid mnemonic
    invalid_mnemonic = "invalid mnemonic phrase"
    
    with pytest.raises(ValueError, match="Invalid mnemonic"):
        await test_wallet_manager.import_wallet(user_id, invalid_mnemonic)


@pytest.mark.asyncio
async def test_get_wallet(test_wallet_manager):
    """Test wallet retrieval."""
    user_id = "test_user_5"
    
    # Create wallet
    public_key, _ = await test_wallet_manager.create_wallet(user_id)
    
    # Get wallet
    wallet = await test_wallet_manager.get_wallet(user_id)
    
    # Verify wallet is returned
    assert wallet is not None
    assert str(wallet.public_key) == public_key


@pytest.mark.asyncio
async def test_get_wallet_caching(test_wallet_manager):
    """Test that wallet retrieval uses caching."""
    user_id = "test_user_6"
    
    # Create wallet
    await test_wallet_manager.create_wallet(user_id)
    
    # Get wallet twice
    wallet1 = await test_wallet_manager.get_wallet(user_id)
    wallet2 = await test_wallet_manager.get_wallet(user_id)
    
    # Verify same instance is returned (cached)
    assert wallet1 is wallet2


@pytest.mark.asyncio
async def test_export_key(test_wallet_manager):
    """Test key export."""
    user_id = "test_user_7"
    
    # Create wallet
    _, original_mnemonic = await test_wallet_manager.create_wallet(user_id)
    
    # Export key
    exported_mnemonic = await test_wallet_manager.export_key(user_id)
    
    # Verify exported mnemonic matches original
    assert exported_mnemonic == original_mnemonic


@pytest.mark.asyncio
async def test_get_all_user_ids(test_wallet_manager):
    """Test getting all user IDs."""
    # Create multiple wallets
    user_ids = ["user_1", "user_2", "user_3"]
    for user_id in user_ids:
        await test_wallet_manager.create_wallet(user_id)
    
    # Get all user IDs
    all_user_ids = test_wallet_manager.get_all_user_ids()
    
    # Verify all users are returned
    assert len(all_user_ids) >= len(user_ids)
    for user_id in user_ids:
        assert user_id in all_user_ids


@pytest.mark.asyncio
async def test_key_export_round_trip(test_wallet_manager):
    """Test that exporting and re-importing a key produces the same wallet."""
    user_id_1 = "test_user_8"
    user_id_2 = "test_user_9"
    
    # Create wallet
    public_key_1, _ = await test_wallet_manager.create_wallet(user_id_1)
    
    # Export key
    mnemonic = await test_wallet_manager.export_key(user_id_1)
    
    # Import into new user
    public_key_2 = await test_wallet_manager.import_wallet(user_id_2, mnemonic)
    
    # Verify public keys match
    assert public_key_1 == public_key_2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
