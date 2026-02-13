"""
Secure Wallet Setup for Harvest Bot

Creates a new Solana wallet on first run and securely stores the private key.
Users get their private key displayed once and can save it safely.
"""

import os
import json
import logging
from pathlib import Path
from solders.keypair import Keypair
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class WalletSetup:
    """
    Handles secure wallet creation and storage.
    
    Features:
    - Generate new Solana wallet
    - Encrypt private key with user password
    - Store encrypted key locally
    - Display private key once for user to save
    - Delete and recreate wallet option
    """
    
    def __init__(self, storage_dir: str = "config"):
        """
        Initialize wallet setup.
        
        Args:
            storage_dir: Directory to store encrypted wallet
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.wallet_file = self.storage_dir / "wallet.enc"
        self.key_file = self.storage_dir / "wallet.key"
    
    def wallet_exists(self) -> bool:
        """Check if wallet already exists."""
        return self.wallet_file.exists() and self.key_file.exists()
    
    def generate_new_wallet(self) -> tuple[Keypair, str]:
        """
        Generate a new Solana wallet.
        
        Returns:
            Tuple of (keypair, private_key_base58)
        """
        keypair = Keypair()
        # Use solders base58 encoding
        private_key = str(keypair)  # Keypair.__str__ returns base58 encoded private key
        
        logger.info(f"Generated new wallet: {keypair.pubkey()}")
        return keypair, private_key
    
    def encrypt_private_key(self, private_key: str, password: str) -> bytes:
        """
        Encrypt private key with password.
        
        Args:
            private_key: Base58 encoded private key
            password: User password for encryption
        
        Returns:
            Encrypted private key bytes
        """
        # Derive key from password
        key = base64.urlsafe_b64encode(password.encode().ljust(32)[:32])
        fernet = Fernet(key)
        
        # Encrypt private key
        encrypted = fernet.encrypt(private_key.encode())
        return encrypted
    
    def decrypt_private_key(self, encrypted_key: bytes, password: str) -> str:
        """
        Decrypt private key with password.
        
        Args:
            encrypted_key: Encrypted private key bytes
            password: User password for decryption
        
        Returns:
            Decrypted private key (base58)
        
        Raises:
            Exception: If password is incorrect
        """
        # Derive key from password
        key = base64.urlsafe_b64encode(password.encode().ljust(32)[:32])
        fernet = Fernet(key)
        
        # Decrypt private key
        decrypted = fernet.decrypt(encrypted_key)
        return decrypted.decode()
    
    def save_wallet(self, private_key: str, password: str):
        """
        Save encrypted wallet to disk.
        
        Args:
            private_key: Base58 encoded private key
            password: User password for encryption
        """
        # Encrypt and save
        encrypted = self.encrypt_private_key(private_key, password)
        self.wallet_file.write_bytes(encrypted)
        
        # Save encryption key marker (not the actual password)
        self.key_file.write_text("encrypted")
        
        logger.info("Wallet saved securely")
    
    def load_wallet(self, password: str) -> str:
        """
        Load and decrypt wallet from disk.
        
        Args:
            password: User password for decryption
        
        Returns:
            Decrypted private key (base58)
        
        Raises:
            Exception: If wallet doesn't exist or password is incorrect
        """
        if not self.wallet_exists():
            raise FileNotFoundError("No wallet found. Create a new wallet first.")
        
        # Load and decrypt
        encrypted = self.wallet_file.read_bytes()
        private_key = self.decrypt_private_key(encrypted, password)
        
        logger.info("Wallet loaded successfully")
        return private_key
    
    def delete_wallet(self):
        """Delete wallet files (for reset/recreate)."""
        if self.wallet_file.exists():
            self.wallet_file.unlink()
        if self.key_file.exists():
            self.key_file.unlink()
        
        logger.info("Wallet deleted")
    
    def create_wallet_info(self, keypair: Keypair, private_key: str) -> dict:
        """
        Create wallet info dictionary for display.
        
        Args:
            keypair: Solana keypair
            private_key: Base58 encoded private key
        
        Returns:
            Dictionary with wallet information
        """
        return {
            "public_key": str(keypair.pubkey()),
            "private_key": private_key,
            "network": "mainnet-beta",
            "explorer_url": f"https://solscan.io/account/{keypair.pubkey()}",
        }


def format_wallet_display(wallet_info: dict) -> str:
    """
    Format wallet information for beautiful display.
    
    Args:
        wallet_info: Wallet information dictionary
    
    Returns:
        Formatted string for display
    """
    return f"""
╔═══════════════════════════════════════════════════════════╗
║                  🔐 YOUR NEW WALLET                       ║
╚═══════════════════════════════════════════════════════════╝

🎉 Wallet Created Successfully!

📍 PUBLIC ADDRESS (Share this to receive SOL):
{wallet_info['public_key']}

🔑 PRIVATE KEY (SAVE THIS SECURELY - NEVER SHARE):
{wallet_info['private_key']}

⚠️  CRITICAL SECURITY INSTRUCTIONS:

1. 📝 WRITE DOWN your private key on paper
2. 💾 SAVE it in a password manager (1Password, Bitwarden, etc.)
3. 🚫 NEVER share it with anyone
4. 🚫 NEVER store it in plain text files
5. ✅ This is the ONLY time you'll see your private key

🔗 View on Solscan:
{wallet_info['explorer_url']}

═══════════════════════════════════════════════════════════

Your wallet is now ready! Fund it with SOL to start trading.
"""


def format_wallet_summary(public_key: str, balance: float = 0.0) -> str:
    """
    Format wallet summary for status display.
    
    Args:
        public_key: Wallet public key
        balance: Current balance in SOL
    
    Returns:
        Formatted string for display
    """
    return f"""
💰 **Your Wallet**

**Address:**
`{public_key}`

**Balance:**
{balance:.4f} SOL

**Network:** mainnet-beta

View on Solscan: https://solscan.io/account/{public_key}
"""


async def interactive_wallet_setup() -> tuple[str, str]:
    """
    Interactive wallet setup for CLI.
    
    Returns:
        Tuple of (private_key, password)
    """
    print("\n" + "="*60)
    print("🌾 HARVEST BOT - WALLET SETUP")
    print("="*60 + "\n")
    
    setup = WalletSetup()
    
    # Check if wallet exists
    if setup.wallet_exists():
        print("📁 Existing wallet found!\n")
        print("Options:")
        print("1. Load existing wallet")
        print("2. Delete and create new wallet")
        
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "2":
            confirm = input("⚠️  Delete existing wallet? Type 'DELETE' to confirm: ").strip()
            if confirm == "DELETE":
                setup.delete_wallet()
                print("✅ Wallet deleted\n")
            else:
                print("❌ Cancelled")
                return None, None
        elif choice == "1":
            password = input("🔐 Enter wallet password: ").strip()
            try:
                private_key = setup.load_wallet(password)
                print("✅ Wallet loaded successfully!")
                return private_key, password
            except Exception as e:
                print(f"❌ Failed to load wallet: {e}")
                return None, None
        else:
            print("❌ Invalid choice")
            return None, None
    
    # Create new wallet
    print("🆕 Creating new wallet...\n")
    
    keypair, private_key = setup.generate_new_wallet()
    wallet_info = setup.create_wallet_info(keypair, private_key)
    
    # Display wallet info
    print(format_wallet_display(wallet_info))
    
    # Ask user to confirm they saved it
    input("\n⏸️  Press ENTER after you've saved your private key...")
    
    # Set password for encryption
    print("\n🔐 Set a password to encrypt your wallet locally:")
    password = input("Password: ").strip()
    password_confirm = input("Confirm password: ").strip()
    
    if password != password_confirm:
        print("❌ Passwords don't match!")
        return None, None
    
    # Save encrypted wallet
    setup.save_wallet(private_key, password)
    
    print("\n✅ Wallet setup complete!")
    print("Your private key is now encrypted and stored locally.")
    print("\n" + "="*60 + "\n")
    
    return private_key, password


if __name__ == "__main__":
    import asyncio
    
    async def main():
        private_key, password = await interactive_wallet_setup()
        if private_key:
            print(f"\n✅ Setup successful!")
            print(f"Private key length: {len(private_key)} characters")
    
    asyncio.run(main())
