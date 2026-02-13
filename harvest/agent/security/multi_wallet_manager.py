"""
Multi-Wallet Manager - Each user gets their own wallet.

Features:
- Separate wallet per user
- Isolated balances and transactions
- Per-user encryption
- No cross-contamination
"""

import logging
from pathlib import Path
from typing import Dict, Optional
from agent.core.wallet import WalletManager
from agent.wallet_setup import WalletSetup

logger = logging.getLogger(__name__)


class MultiWalletManager:
    """Manage multiple wallets, one per user."""
    
    def __init__(self, storage_dir: str = "config/wallets"):
        """
        Initialize multi-wallet manager.
        
        Args:
            storage_dir: Directory to store user wallets
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache of active wallet managers
        self.wallets: Dict[str, WalletManager] = {}
        
        logger.info(f"MultiWalletManager initialized: {storage_dir}")
    
    def _get_wallet_dir(self, user_id: str) -> Path:
        """Get directory for user's wallet."""
        # Validate user_id
        from agent.security.security import SecurityValidator
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Invalid user_id: {e}")
            raise
        
        user_dir = self.storage_dir / user_id
        user_dir.mkdir(exist_ok=True)
        return user_dir
    
    def has_wallet(self, user_id: str) -> bool:
        """Check if user has a wallet."""
        wallet_dir = self._get_wallet_dir(user_id)
        setup = WalletSetup(storage_dir=str(wallet_dir))
        return setup.wallet_exists()
    
    def create_wallet(self, user_id: str, password: str) -> tuple[str, str]:
        """
        Create new wallet for user.
        
        Args:
            user_id: User ID
            password: Encryption password
        
        Returns:
            Tuple of (public_key, private_key)
        """
        # Validate inputs
        from agent.security.security import SecurityValidator
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
            password = SecurityValidator.sanitize_string(password, max_length=1000)
            if len(password) < 8:
                raise ValueError("Password must be at least 8 characters")
        except ValueError as e:
            logger.error(f"Invalid wallet creation parameters: {e}")
            raise
        
        wallet_dir = self._get_wallet_dir(user_id)
        setup = WalletSetup(storage_dir=str(wallet_dir))
        
        # Generate wallet
        keypair, private_key = setup.generate_new_wallet()
        
        # Save encrypted
        setup.save_wallet(private_key, password)
        
        public_key = str(keypair.pubkey())
        
        logger.info(f"Created wallet for user {user_id}: {public_key}")
        
        return public_key, private_key
    
    def load_wallet(
        self,
        user_id: str,
        password: str,
        network: str = "mainnet-beta"
    ) -> WalletManager:
        """
        Load user's wallet.
        
        Args:
            user_id: User ID
            password: Decryption password
            network: Solana network
        
        Returns:
            WalletManager instance
        
        Raises:
            FileNotFoundError: If wallet doesn't exist
            Exception: If password is incorrect
        """
        # Check cache first
        if user_id in self.wallets:
            return self.wallets[user_id]
        
        wallet_dir = self._get_wallet_dir(user_id)
        setup = WalletSetup(storage_dir=str(wallet_dir))
        
        # Load and decrypt
        private_key = setup.load_wallet(password)
        
        # Create wallet manager
        wallet = WalletManager(
            private_key=private_key,
            network=network
        )
        
        # Cache it
        self.wallets[user_id] = wallet
        
        logger.info(f"Loaded wallet for user {user_id}: {wallet.public_key}")
        
        return wallet
    
    def get_wallet(self, user_id: str) -> Optional[WalletManager]:
        """
        Get cached wallet for user.
        
        Args:
            user_id: User ID
        
        Returns:
            WalletManager if loaded, None otherwise
        """
        return self.wallets.get(user_id)
    
    async def get_balance(self, user_id: str) -> float:
        """
        Get balance for user's wallet.
        
        Args:
            user_id: User ID
        
        Returns:
            Balance in SOL
        """
        wallet = self.get_wallet(user_id)
        if not wallet:
            raise ValueError(f"Wallet not loaded for user {user_id}")
        
        return await wallet.get_balance()
    
    def get_address(self, user_id: str) -> Optional[str]:
        """
        Get wallet address for user.
        
        Args:
            user_id: User ID
        
        Returns:
            Wallet address or None
        """
        wallet = self.get_wallet(user_id)
        if wallet:
            return str(wallet.public_key)
        return None
    
    async def send_sol(
        self,
        user_id: str,
        to_address: str,
        amount: float
    ) -> Optional[str]:
        """
        Send SOL from user's wallet.
        
        Args:
            user_id: User ID
            to_address: Recipient address
            amount: Amount in SOL
        
        Returns:
            Transaction signature or None
        """
        # Validate inputs
        from agent.security.security import SecurityValidator
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
            to_address = SecurityValidator.validate_wallet_address(to_address)
            amount = SecurityValidator.validate_amount(amount, min_val=0.001, max_val=1000.0)
        except ValueError as e:
            logger.error(f"Invalid send_sol parameters: {e}")
            raise
        
        wallet = self.get_wallet(user_id)
        if not wallet:
            raise ValueError(f"Wallet not loaded for user {user_id}")
        
        return await wallet.send_sol(to_address, amount)
    
    def delete_wallet(self, user_id: str):
        """
        Delete user's wallet.
        
        Args:
            user_id: User ID
        """
        wallet_dir = self._get_wallet_dir(user_id)
        setup = WalletSetup(storage_dir=str(wallet_dir))
        setup.delete_wallet()
        
        # Remove from cache
        if user_id in self.wallets:
            del self.wallets[user_id]
        
        logger.info(f"Deleted wallet for user {user_id}")
    
    async def close_wallet(self, user_id: str):
        """
        Close user's wallet connection.
        
        Args:
            user_id: User ID
        """
        if user_id in self.wallets:
            await self.wallets[user_id].close()
            del self.wallets[user_id]
            logger.info(f"Closed wallet for user {user_id}")
    
    async def close_all(self):
        """Close all wallet connections."""
        for user_id in list(self.wallets.keys()):
            await self.close_wallet(user_id)
        logger.info("Closed all wallets")
    
    def get_all_users(self) -> list:
        """Get list of all users with wallets."""
        users = []
        for user_dir in self.storage_dir.iterdir():
            if user_dir.is_dir():
                setup = WalletSetup(storage_dir=str(user_dir))
                if setup.wallet_exists():
                    users.append(user_dir.name)
        return users
    
    def get_wallet_info(self, user_id: str) -> dict:
        """
        Get wallet information for user.
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with wallet info
        """
        wallet = self.get_wallet(user_id)
        if not wallet:
            return {
                "user_id": user_id,
                "has_wallet": self.has_wallet(user_id),
                "loaded": False,
            }
        
        return {
            "user_id": user_id,
            "has_wallet": True,
            "loaded": True,
            "address": str(wallet.public_key),
            "network": wallet.network,
        }


if __name__ == "__main__":
    import asyncio
    
    async def test_multi_wallet():
        """Test multi-wallet functionality."""
        print("\nTesting Multi-Wallet Manager\n")
        print("="*60)
        
        manager = MultiWalletManager(storage_dir="config/test_wallets")
        
        # Create wallets for 3 users
        users = [
            ("alice_123", "password_alice"),
            ("bob_456", "password_bob"),
            ("charlie_789", "password_charlie"),
        ]
        
        print("\n1. Creating wallets for users...")
        for user_id, password in users:
            if not manager.has_wallet(user_id):
                public_key, private_key = manager.create_wallet(user_id, password)
                print(f"   {user_id}: {public_key}")
        
        print("\n2. Loading wallets...")
        for user_id, password in users:
            wallet = manager.load_wallet(user_id, password, network="devnet")
            print(f"   {user_id}: Loaded")
        
        print("\n3. Checking balances...")
        for user_id, _ in users:
            balance = await manager.get_balance(user_id)
            address = manager.get_address(user_id)
            print(f"   {user_id}: {balance} SOL ({address[:20]}...)")
        
        print("\n4. Wallet info...")
        for user_id, _ in users:
            info = manager.get_wallet_info(user_id)
            print(f"   {user_id}:")
            print(f"      Has wallet: {info['has_wallet']}")
            print(f"      Loaded: {info['loaded']}")
            print(f"      Network: {info.get('network', 'N/A')}")
        
        print("\n5. Closing wallets...")
        await manager.close_all()
        print("   All wallets closed")
        
        print("\n" + "="*60)
        print("Multi-wallet test complete!")
        print("\nEach user has:")
        print("- Separate wallet file")
        print("- Independent encryption")
        print("- Isolated balance")
        print("- No cross-contamination")
        print()
    
    asyncio.run(test_multi_wallet())
