"""Multi-user wallet management for Harvest - manage multiple user wallets."""

import logging
import hashlib
import time
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from pathlib import Path

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from mnemonic import Mnemonic

from agent.core.wallet import WalletManager
from agent.core.database import Database
from agent.security.security import SecurityValidator

logger = logging.getLogger(__name__)


class SimpleWalletSecurity:
    """
    Simplified wallet security for multi-user management.
    Uses mnemonic generation and basic encryption without full BIP44 derivation.
    """
    
    def __init__(self, storage_dir: str = "config/secure_wallets"):
        """Initialize simple wallet security."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.mnemonic_generator = Mnemonic("english")
        logger.info("SimpleWalletSecurity initialized")
    
    def generate_mnemonic(self, words: int = 12) -> str:
        """Generate BIP39 mnemonic phrase."""
        if words not in [12, 24]:
            raise ValueError(f"Invalid word count. Must be 12 or 24, got {words}")
        
        strength = 128 if words == 12 else 256
        mnemonic = self.mnemonic_generator.generate(strength=strength)
        logger.info(f"Generated {words}-word mnemonic")
        return mnemonic
    
    def verify_mnemonic(self, mnemonic: str) -> bool:
        """Verify BIP39 mnemonic checksum."""
        return self.mnemonic_generator.check(mnemonic)
    
    def derive_keypair_from_mnemonic(self, mnemonic: str) -> Tuple[Keypair, str]:
        """
        Derive Solana keypair from mnemonic using simple seed derivation.
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            
        Returns:
            Tuple of (Keypair, public_key_string)
        """
        # Convert mnemonic to seed
        seed = self.mnemonic_generator.to_seed(mnemonic, passphrase="")
        
        # Use first 32 bytes as private key seed for Solana
        private_key_seed = seed[:32]
        
        # Create keypair from seed (Solana uses Ed25519)
        # We need to use from_seed_phrase_and_passphrase or create from seed
        # Let's use a simpler approach with nacl
        import nacl.signing
        import nacl.encoding
        
        # Create signing key from seed
        signing_key = nacl.signing.SigningKey(private_key_seed)
        
        # Get the full 64-byte keypair (32 private + 32 public)
        keypair_bytes = bytes(signing_key) + bytes(signing_key.verify_key)
        
        # Create Solana keypair
        keypair = Keypair.from_bytes(keypair_bytes)
        public_key = str(keypair.pubkey())
        
        logger.info(f"Derived Solana keypair: {public_key}")
        return keypair, public_key
    
    def save_encrypted_mnemonic(self, user_id: str, mnemonic: str, password: str = "default"):
        """
        Save encrypted mnemonic to file.
        Simple XOR encryption for now (can be upgraded later).
        """
        import json
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # Derive key from password
        salt = hashlib.sha256(user_id.encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Encrypt mnemonic
        f = Fernet(key)
        encrypted = f.encrypt(mnemonic.encode())
        
        # Save to file
        wallet_file = self.storage_dir / f"{user_id}.enc"
        wallet_data = {
            "user_id": user_id,
            "encrypted_mnemonic": encrypted.hex(),
            "created_at": datetime.now().isoformat()
        }
        
        with open(wallet_file, 'w') as file:
            json.dump(wallet_data, file)
        
        logger.info(f"Saved encrypted wallet for user {user_id}")
        return str(wallet_file)
    
    def load_encrypted_mnemonic(self, user_id: str, password: str = "default") -> str:
        """Load and decrypt mnemonic from file."""
        import json
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        wallet_file = self.storage_dir / f"{user_id}.enc"
        if not wallet_file.exists():
            raise FileNotFoundError(f"Wallet not found for user {user_id}")
        
        with open(wallet_file, 'r') as file:
            wallet_data = json.load(file)
        
        # Derive key from password
        salt = hashlib.sha256(user_id.encode()).digest()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt mnemonic
        f = Fernet(key)
        encrypted = bytes.fromhex(wallet_data["encrypted_mnemonic"])
        mnemonic = f.decrypt(encrypted).decode()
        
        logger.info(f"Loaded encrypted wallet for user {user_id}")
        return mnemonic


class MultiUserWalletManager:
    """
    Manages multiple user wallets with secure storage.
    
    Attributes:
        wallets: Dict[user_id, WalletManager] - Cached wallet instances
        database: Database - For wallet metadata storage
        network: str - Solana network (devnet/mainnet)
        security: SimpleWalletSecurity - For wallet encryption/decryption
    """
    
    def __init__(
        self,
        database: Database,
        network: str = "devnet",
        storage_dir: str = "config/secure_wallets",
        password: str = "default"
    ):
        """
        Initialize multi-user wallet manager.
        
        Args:
            database: Database instance for wallet metadata
            network: Solana network (devnet/mainnet-beta)
            storage_dir: Directory for encrypted wallet files
            password: Default password for wallet decryption
        """
        self.database = database
        self.network = network
        self.wallets: Dict[str, WalletManager] = {}
        self.security = SimpleWalletSecurity(storage_dir=storage_dir)
        self._balance_cache: Dict[str, Tuple[float, datetime]] = {}
        self._balance_cache_ttl = 30  # seconds
        self._default_password = password
        
        # Rate limiting for RPC calls
        self._rpc_requests: List[float] = []  # Timestamps of recent requests
        self._rate_limit_per_second = 10  # Max requests per second
        self._rate_limit_per_minute = 100  # Max requests per minute
        self._rate_limit_window_second = 1.0  # 1 second window
        self._rate_limit_window_minute = 60.0  # 60 second window
        
        # Load all wallets from database on startup
        self._load_all_wallets()
        
        logger.info(f"MultiUserWalletManager initialized (network: {network})")
    
    def _load_all_wallets(self):
        """
        Load all wallets from database on startup.
        Populates wallet cache with user_id → wallet mappings.
        """
        try:
            # Get all wallet metadata from database
            all_wallets = self.database.get_all_wallets()
            
            logger.info(f"Loading {len(all_wallets)} wallets from database...")
            
            loaded_count = 0
            failed_count = 0
            
            for wallet_metadata in all_wallets:
                user_id = wallet_metadata["user_id"]
                
                try:
                    # Load encrypted mnemonic
                    mnemonic = self.security.load_encrypted_mnemonic(user_id, self._default_password)
                    
                    # Derive keypair from mnemonic
                    keypair, public_key = self.security.derive_keypair_from_mnemonic(mnemonic)
                    
                    # Create WalletManager with the keypair
                    private_key_base58 = str(keypair)  # Keypair.__str__ returns base58 encoded private key
                    
                    wallet = WalletManager(
                        private_key=private_key_base58,
                        network=self.network
                    )
                    
                    # Cache the wallet
                    self.wallets[user_id] = wallet
                    loaded_count += 1
                    
                    logger.debug(f"Loaded wallet for user {user_id}: {public_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to load wallet for user {user_id}: {e}")
                    failed_count += 1
                    continue
            
            logger.info(
                f"Wallet loading complete: {loaded_count} loaded, {failed_count} failed"
            )
            
        except Exception as e:
            logger.error(f"Error loading wallets from database: {e}")

    
    async def create_wallet(self, user_id: str, password: str = "default") -> Tuple[str, str]:
        """
        Create new wallet for user.
        
        Args:
            user_id: Telegram user ID
            password: Password for wallet encryption (default: "default")
            
        Returns:
            (public_key, mnemonic_phrase)
            
        Raises:
            ValueError: If user already has a wallet or invalid input
            Exception: For other wallet creation errors
        """
        try:
            # SECURITY: Validate user_id to prevent SQL injection
            user_id = SecurityValidator.validate_user_id(user_id)
            
            # Check if user already has a wallet
            existing_wallet = self.database.get_user_wallet(user_id)
            if existing_wallet:
                logger.warning(f"Wallet creation rejected: user {user_id} already has a wallet")
                raise ValueError(f"You already have a wallet registered. Use /exportkey to access it.")
            
            # Generate 12-word mnemonic
            try:
                mnemonic = self.security.generate_mnemonic(words=12)
            except Exception as e:
                logger.error(f"Failed to generate mnemonic for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to generate wallet mnemonic. Please try again.")
            
            # Derive Solana keypair from mnemonic
            try:
                keypair, public_key = self.security.derive_keypair_from_mnemonic(mnemonic)
            except Exception as e:
                logger.error(f"Failed to derive keypair for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to derive wallet keypair. Please try again.")
            
            # Save encrypted mnemonic
            try:
                wallet_file_path = self.security.save_encrypted_mnemonic(user_id, mnemonic, password)
            except Exception as e:
                logger.error(f"Failed to save encrypted mnemonic for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to save wallet securely. Please try again.")
            
            # Store wallet metadata in database
            try:
                success = self.database.register_secure_wallet(
                    user_id=user_id,
                    public_key=public_key,
                    derivation_path="m/44'/501'/0'/0'/0'",
                    mnemonic_words=12,
                    kdf_method="pbkdf2",
                    encryption_method="fernet",
                    wallet_file_path=wallet_file_path
                )
                
                if not success:
                    logger.error(f"Database registration failed for user {user_id}")
                    raise Exception("Failed to register wallet in database. Please try again.")
            except Exception as e:
                logger.error(f"Database error during wallet registration for user {user_id}: {e}", exc_info=True)
                # Attempt cleanup: remove encrypted file if database registration failed
                try:
                    import os
                    if os.path.exists(wallet_file_path):
                        os.remove(wallet_file_path)
                        logger.info(f"Cleaned up wallet file after database failure: {wallet_file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup wallet file: {cleanup_error}")
                raise Exception("Failed to register wallet in database. Please try again.")
            
            logger.info(f"Successfully created wallet for user {user_id}: {public_key}")
            
            return public_key, mnemonic
            
        except ValueError as e:
            # Re-raise ValueError with user-friendly message (already formatted)
            raise
        except Exception as e:
            # Log detailed error for debugging
            logger.error(f"Unexpected error creating wallet for user {user_id}: {e}", exc_info=True)
            # Return user-friendly error message
            raise Exception(f"Failed to create wallet: {str(e)}")
    
    async def import_wallet(self, user_id: str, mnemonic: str, password: str = "default") -> str:
        """
        Import wallet from mnemonic phrase.
        
        Args:
            user_id: Telegram user ID
            mnemonic: 12 or 24 word mnemonic phrase
            password: Password for wallet encryption (default: "default")
            
        Returns:
            public_key: Wallet public key
            
        Raises:
            ValueError: If user already has wallet or mnemonic invalid
            Exception: For other wallet import errors
        """
        try:
            # SECURITY: Validate user_id to prevent SQL injection
            user_id = SecurityValidator.validate_user_id(user_id)
            
            # SECURITY: Sanitize mnemonic input
            mnemonic = SecurityValidator.sanitize_string(mnemonic, max_length=500, check_injections=False)
            
            # Check if user already has a wallet
            existing_wallet = self.database.get_user_wallet(user_id)
            if existing_wallet:
                logger.warning(f"Wallet import rejected: user {user_id} already has a wallet")
                raise ValueError(f"You already have a wallet registered. Use /exportkey to access it.")
            
            # Validate mnemonic format
            mnemonic = mnemonic.strip()
            words = mnemonic.split()
            if len(words) not in [12, 24]:
                logger.warning(f"Invalid mnemonic word count for user {user_id}: {len(words)} words")
                raise ValueError(f"Invalid mnemonic: must be 12 or 24 words, got {len(words)} words")
            
            # Verify mnemonic checksum
            try:
                if not self.security.verify_mnemonic(mnemonic):
                    logger.warning(f"Mnemonic checksum verification failed for user {user_id}")
                    raise ValueError("Invalid mnemonic: checksum verification failed. Please check your mnemonic phrase.")
            except ValueError:
                # Re-raise ValueError
                raise
            except Exception as e:
                logger.error(f"Error verifying mnemonic for user {user_id}: {e}", exc_info=True)
                raise ValueError("Invalid mnemonic: verification failed. Please check your mnemonic phrase.")
            
            # Derive Solana keypair from mnemonic
            try:
                keypair, public_key = self.security.derive_keypair_from_mnemonic(mnemonic)
            except Exception as e:
                logger.error(f"Failed to derive keypair from mnemonic for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to derive wallet from mnemonic. Please check your mnemonic phrase.")
            
            # Save encrypted mnemonic
            try:
                wallet_file_path = self.security.save_encrypted_mnemonic(user_id, mnemonic, password)
            except Exception as e:
                logger.error(f"Failed to save encrypted mnemonic for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to save wallet securely. Please try again.")
            
            # Store wallet metadata in database
            try:
                success = self.database.register_secure_wallet(
                    user_id=user_id,
                    public_key=public_key,
                    derivation_path="m/44'/501'/0'/0'/0'",
                    mnemonic_words=len(words),
                    kdf_method="pbkdf2",
                    encryption_method="fernet",
                    wallet_file_path=wallet_file_path
                )
                
                if not success:
                    logger.error(f"Database registration failed for user {user_id}")
                    raise Exception("Failed to register wallet in database. Please try again.")
            except Exception as e:
                logger.error(f"Database error during wallet import for user {user_id}: {e}", exc_info=True)
                # Attempt cleanup: remove encrypted file if database registration failed
                try:
                    import os
                    if os.path.exists(wallet_file_path):
                        os.remove(wallet_file_path)
                        logger.info(f"Cleaned up wallet file after database failure: {wallet_file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup wallet file: {cleanup_error}")
                raise Exception("Failed to register wallet in database. Please try again.")
            
            logger.info(f"Successfully imported wallet for user {user_id}: {public_key}")
            
            return public_key
            
        except ValueError as e:
            # Re-raise ValueError with user-friendly message (already formatted)
            raise
        except Exception as e:
            # Log detailed error for debugging
            logger.error(f"Unexpected error importing wallet for user {user_id}: {e}", exc_info=True)
            # Return user-friendly error message
            raise Exception(f"Failed to import wallet: {str(e)}")
    
    async def get_wallet(self, user_id: str, password: str = "default", requesting_user_id: Optional[str] = None) -> Optional[WalletManager]:
        """
        Get wallet instance for user.
        
        Args:
            user_id: Telegram user ID
            password: Password for wallet decryption (default: "default")
            requesting_user_id: User ID making the request (for authorization check)
            
        Returns:
            WalletManager instance or None if user has no wallet
            
        Raises:
            ValueError: If authorization fails or invalid input
        """
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        if requesting_user_id is not None:
            requesting_user_id = SecurityValidator.validate_user_id(requesting_user_id)
        
        # Verify wallet ownership if requesting_user_id is provided
        if requesting_user_id is not None:
            self.verify_wallet_owner(user_id, requesting_user_id)
        
        # Check cache first
        if user_id in self.wallets:
            return self.wallets[user_id]
        
        # Get wallet metadata from database
        wallet_metadata = self.database.get_user_wallet(user_id)
        if not wallet_metadata:
            return None
        
        try:
            # Load encrypted mnemonic
            mnemonic = self.security.load_encrypted_mnemonic(user_id, password)
            
            # Derive keypair from mnemonic
            keypair, public_key = self.security.derive_keypair_from_mnemonic(mnemonic)
            
            # Create WalletManager with the keypair
            private_key_base58 = str(keypair)  # Keypair.__str__ returns base58 encoded private key
            
            wallet = WalletManager(
                private_key=private_key_base58,
                network=self.network
            )
            
            # Cache the wallet
            self.wallets[user_id] = wallet
            
            # Update last unlocked timestamp
            self.database.update_wallet_last_unlocked(user_id)
            
            logger.info(f"Loaded wallet for user {user_id}: {public_key}")
            
            return wallet
            
        except Exception as e:
            logger.error(f"Failed to load wallet for user {user_id}: {e}")
            return None
    
    async def get_balance(self, user_id: str, password: str = "default", requesting_user_id: Optional[str] = None) -> float:
        """
        Get SOL balance for user's wallet.
        
        Handles RPC failures gracefully by returning cached balance if available.
        Logs errors but doesn't crash the bot.
        
        Args:
            user_id: Telegram user ID
            password: Password for wallet decryption (default: "default")
            requesting_user_id: User ID making the request (for authorization check)
            
        Returns:
            Balance in SOL (returns cached balance if RPC fails)
            
        Raises:
            ValueError: If user has no wallet or authorization fails
        """
        try:
            # SECURITY: Validate user_id to prevent SQL injection
            user_id = SecurityValidator.validate_user_id(user_id)
            if requesting_user_id is not None:
                requesting_user_id = SecurityValidator.validate_user_id(requesting_user_id)
            
            # Verify wallet ownership if requesting_user_id is provided
            if requesting_user_id is not None:
                try:
                    self.verify_wallet_owner(user_id, requesting_user_id)
                except ValueError as e:
                    logger.warning(f"Wallet ownership verification failed for user {requesting_user_id} accessing {user_id}")
                    raise
            
            # Check cache first
            if user_id in self._balance_cache:
                balance, timestamp = self._balance_cache[user_id]
                age = (datetime.now() - timestamp).total_seconds()
                if age < self._balance_cache_ttl:
                    logger.debug(f"Using cached balance for user {user_id}: {balance} SOL (age: {age:.1f}s)")
                    return balance
            
            # Check rate limit before making RPC call
            try:
                await self._check_rate_limit()
            except Exception as e:
                logger.warning(f"Rate limit check failed for user {user_id}: {e}")
                # If rate limit check fails, try to use cached balance
                if user_id in self._balance_cache:
                    balance, timestamp = self._balance_cache[user_id]
                    logger.info(f"Using cached balance due to rate limit for user {user_id}: {balance} SOL")
                    return balance
                # If no cache, raise error
                raise Exception("Rate limit exceeded and no cached balance available. Please try again later.")
            
            # Get wallet
            try:
                wallet = await self.get_wallet(user_id, password)
                if not wallet:
                    logger.warning(f"Balance check failed: no wallet found for user {user_id}")
                    raise ValueError(f"You don't have a wallet registered. Use /createwallet to create one.")
            except ValueError:
                # Re-raise ValueError (wallet not found)
                raise
            except Exception as e:
                logger.error(f"Failed to load wallet for balance check for user {user_id}: {e}", exc_info=True)
                # Try to return cached balance if available
                if user_id in self._balance_cache:
                    balance, timestamp = self._balance_cache[user_id]
                    logger.info(f"Using cached balance due to wallet load failure for user {user_id}: {balance} SOL")
                    return balance
                raise Exception("Failed to load wallet for balance check. Please try again.")
            
            # Get balance from blockchain
            try:
                balance = await wallet.get_balance()
                
                # Cache the balance
                self._balance_cache[user_id] = (balance, datetime.now())
                
                logger.debug(f"Fetched balance for user {user_id}: {balance} SOL")
                return balance
                
            except Exception as e:
                # RPC failure - log error and return cached balance if available
                logger.error(f"RPC error fetching balance for user {user_id}: {e}", exc_info=True)
                
                # Try to return cached balance
                if user_id in self._balance_cache:
                    balance, timestamp = self._balance_cache[user_id]
                    age = (datetime.now() - timestamp).total_seconds()
                    logger.warning(
                        f"RPC failed, using cached balance for user {user_id}: {balance} SOL "
                        f"(cached {age:.1f}s ago)"
                    )
                    return balance
                
                # No cached balance available - return 0.0 as safe default
                logger.warning(f"RPC failed and no cached balance for user {user_id}, returning 0.0 SOL")
                return 0.0
                
        except ValueError as e:
            # Re-raise ValueError with user-friendly message (already formatted)
            raise
        except Exception as e:
            # Log detailed error for debugging
            logger.error(f"Unexpected error getting balance for user {user_id}: {e}", exc_info=True)
            
            # Try to return cached balance as last resort
            if user_id in self._balance_cache:
                balance, timestamp = self._balance_cache[user_id]
                logger.warning(f"Using cached balance due to unexpected error for user {user_id}: {balance} SOL")
                return balance
            
            # Return 0.0 as safe default
            logger.warning(f"No cached balance available for user {user_id}, returning 0.0 SOL")
            return 0.0
    
    async def export_key(self, user_id: str, password: str = "default", requesting_user_id: Optional[str] = None) -> str:
        """
        Export user's private key or mnemonic.
        
        Args:
            user_id: Telegram user ID
            password: Password for wallet decryption (default: "default")
            requesting_user_id: User ID making the request (for authorization check)
            
        Returns:
            Mnemonic phrase or base58 private key
            
        Raises:
            ValueError: If user has no wallet or authorization fails
            Exception: For other export errors
        """
        try:
            # SECURITY: Validate user_id to prevent SQL injection
            user_id = SecurityValidator.validate_user_id(user_id)
            if requesting_user_id is not None:
                requesting_user_id = SecurityValidator.validate_user_id(requesting_user_id)
            
            # Verify wallet ownership if requesting_user_id is provided
            if requesting_user_id is not None:
                try:
                    self.verify_wallet_owner(user_id, requesting_user_id)
                except ValueError as e:
                    logger.warning(f"Wallet ownership verification failed for user {requesting_user_id} accessing {user_id}")
                    raise
            
            # Get wallet metadata from database
            wallet_metadata = self.database.get_user_wallet(user_id)
            if not wallet_metadata:
                logger.warning(f"Export key failed: no wallet found for user {user_id}")
                raise ValueError(f"You don't have a wallet registered. Use /createwallet to create one.")
            
            # Load encrypted mnemonic
            try:
                mnemonic = self.security.load_encrypted_mnemonic(user_id, password)
            except FileNotFoundError:
                logger.error(f"Wallet file not found for user {user_id}")
                raise ValueError("Wallet file not found. Please contact support.")
            except Exception as e:
                logger.error(f"Failed to decrypt wallet for user {user_id}: {e}", exc_info=True)
                raise Exception("Failed to decrypt wallet. Please try again or contact support.")
            
            # Log security event
            logger.warning(f"SECURITY: Key export requested for user {user_id}")
            
            return mnemonic
            
        except ValueError as e:
            # Re-raise ValueError with user-friendly message (already formatted)
            raise
        except Exception as e:
            # Log detailed error for debugging
            logger.error(f"Unexpected error exporting key for user {user_id}: {e}", exc_info=True)
            # Return user-friendly error message
            raise Exception(f"Failed to export key: {str(e)}")
    
    def get_all_user_ids(self) -> List[str]:
        """
        Get list of all user IDs with registered wallets.
        
        Returns:
            List of user IDs
        """
        wallets = self.database.get_all_wallets()
        return [wallet["user_id"] for wallet in wallets]
    def verify_wallet_owner(self, user_id: str, requesting_user_id: str) -> bool:
        """
        Verify that the requesting user owns the wallet.

        Args:
            user_id: The user ID associated with the wallet
            requesting_user_id: The user ID making the request

        Returns:
            True if requesting user owns the wallet, False otherwise

        Raises:
            ValueError: If wallet ownership verification fails or invalid input
        """
        # SECURITY: Validate both user IDs to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        requesting_user_id = SecurityValidator.validate_user_id(requesting_user_id)
        
        if user_id != requesting_user_id:
            logger.error(
                f"SECURITY: Wallet ownership verification failed - "
                f"user {requesting_user_id} attempted to access wallet of user {user_id}"
            )
            raise ValueError(f"Unauthorized: You do not have permission to access this wallet")

        # Additional check: verify wallet exists in database for this user
        wallet_metadata = self.database.get_user_wallet(user_id)
        if not wallet_metadata:
            raise ValueError(f"Wallet not found for user {user_id}")

        logger.debug(f"Wallet ownership verified for user {user_id}")
        return True

    
    async def close_all(self):
        """Close all wallet RPC connections."""
        for user_id, wallet in self.wallets.items():
            try:
                await wallet.close()
            except Exception as e:
                logger.error(f"Error closing wallet for user {user_id}: {e}")
        
        self.wallets.clear()
        logger.info("Closed all wallet connections")
    async def batch_get_balances(self, user_ids: List[str], password: str = "default") -> Dict[str, float]:
        """
        Get balances for multiple users using batch RPC requests.

        Processes users in batches of 10-20 to optimize RPC calls while
        avoiding rate limits. Uses Solana RPC batch requests where possible.

        Args:
            user_ids: List of user IDs to check balances for
            password: Password for wallet decryption (default: "default")

        Returns:
            Dictionary mapping user_id to balance in SOL
        """
        balances = {}
        batch_size = 15  # Process 15 users per batch

        # Process users in batches
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]

            # Get public keys for this batch
            public_keys = []
            user_key_map = {}  # Map public key to user_id

            for user_id in batch:
                try:
                    # SECURITY: Validate user_id
                    validated_user_id = SecurityValidator.validate_user_id(user_id)

                    # Check cache first
                    if validated_user_id in self._balance_cache:
                        balance, timestamp = self._balance_cache[validated_user_id]
                        age = (datetime.now() - timestamp).total_seconds()
                        if age < self._balance_cache_ttl:
                            balances[validated_user_id] = balance
                            logger.debug(f"Using cached balance for user {validated_user_id}: {balance} SOL")
                            continue

                    # Get wallet metadata
                    wallet_metadata = self.database.get_user_wallet(validated_user_id)
                    if wallet_metadata:
                        public_key = wallet_metadata["public_key"]
                        public_keys.append(public_key)
                        user_key_map[public_key] = validated_user_id
                    else:
                        logger.warning(f"No wallet found for user {validated_user_id}")
                        balances[validated_user_id] = 0.0

                except Exception as e:
                    logger.error(f"Error preparing batch request for user {user_id}: {e}")
                    balances[user_id] = 0.0

            # If no public keys to fetch, continue to next batch
            if not public_keys:
                continue

            # Fetch balances using batch RPC request
            try:
                # Check rate limit before batch request
                await self._check_rate_limit()
                
                # Get a wallet instance to access RPC client
                sample_wallet = None
                for user_id in batch:
                    if user_id in self.wallets:
                        sample_wallet = self.wallets[user_id]
                        break

                if not sample_wallet and public_keys:
                    # Create a temporary wallet to access RPC
                    first_user = user_key_map[public_keys[0]]
                    sample_wallet = await self.get_wallet(first_user, password)

                if sample_wallet and hasattr(sample_wallet, 'client'):
                    # Use batch request if available
                    from solders.pubkey import Pubkey

                    batch_results = []
                    for pub_key_str in public_keys:
                        try:
                            pubkey = Pubkey.from_string(pub_key_str)
                            balance_response = await sample_wallet.client.get_balance(pubkey)

                            if balance_response.value is not None:
                                balance_lamports = balance_response.value
                                balance_sol = balance_lamports / 1_000_000_000
                                batch_results.append((pub_key_str, balance_sol))
                            else:
                                batch_results.append((pub_key_str, 0.0))

                        except Exception as e:
                            logger.error(f"Error fetching balance for {pub_key_str}: {e}")
                            batch_results.append((pub_key_str, 0.0))

                    # Map results back to user IDs and cache
                    for pub_key, balance in batch_results:
                        user_id = user_key_map[pub_key]
                        balances[user_id] = balance
                        self._balance_cache[user_id] = (balance, datetime.now())
                        logger.debug(f"Batch fetched balance for user {user_id}: {balance} SOL")
                else:
                    # Fallback to individual requests
                    logger.warning("No wallet client available for batch request, falling back to individual requests")
                    for pub_key in public_keys:
                        user_id = user_key_map[pub_key]
                        try:
                            balance = await self.get_balance(user_id, password)
                            balances[user_id] = balance
                        except Exception as e:
                            logger.error(f"Error fetching balance for user {user_id}: {e}")
                            balances[user_id] = 0.0

            except Exception as e:
                logger.error(f"Error in batch balance request: {e}")
                # Fallback to individual requests for this batch
                for pub_key in public_keys:
                    user_id = user_key_map[pub_key]
                    try:
                        balance = await self.get_balance(user_id, password)
                        balances[user_id] = balance
                    except Exception as e:
                        logger.error(f"Error fetching balance for user {user_id}: {e}")
                        balances[user_id] = 0.0

        logger.info(f"Batch balance check complete: {len(balances)} users processed")
        return balances
    async def _check_rate_limit(self):
        """
        Check and enforce rate limits for RPC calls.

        Tracks requests per second and per minute. Adds delays when
        approaching rate limits to avoid exceeding RPC provider limits.
        """
        import asyncio

        current_time = time.time()

        # Remove old requests outside the minute window
        self._rpc_requests = [
            ts for ts in self._rpc_requests
            if current_time - ts < self._rate_limit_window_minute
        ]

        # Check per-second rate limit
        recent_second = [
            ts for ts in self._rpc_requests
            if current_time - ts < self._rate_limit_window_second
        ]

        if len(recent_second) >= self._rate_limit_per_second:
            # Wait until we can make another request
            delay = self._rate_limit_window_second - (current_time - recent_second[0])
            if delay > 0:
                logger.debug(f"Rate limit: waiting {delay:.2f}s (per-second limit)")
                await asyncio.sleep(delay)
                current_time = time.time()

        # Check per-minute rate limit
        if len(self._rpc_requests) >= self._rate_limit_per_minute:
            # Wait until oldest request falls outside the window
            delay = self._rate_limit_window_minute - (current_time - self._rpc_requests[0])
            if delay > 0:
                logger.warning(f"Rate limit: waiting {delay:.2f}s (per-minute limit)")
                await asyncio.sleep(delay)
                current_time = time.time()

        # Record this request
        self._rpc_requests.append(current_time)

    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        Get rate limiting statistics.

        Returns:
            Dictionary with rate limit metrics
        """
        current_time = time.time()

        # Count requests in last second
        recent_second = [
            ts for ts in self._rpc_requests
            if current_time - ts < self._rate_limit_window_second
        ]

        # Count requests in last minute
        recent_minute = [
            ts for ts in self._rpc_requests
            if current_time - ts < self._rate_limit_window_minute
        ]

        return {
            "requests_last_second": len(recent_second),
            "requests_last_minute": len(recent_minute),
            "limit_per_second": self._rate_limit_per_second,
            "limit_per_minute": self._rate_limit_per_minute,
            "utilization_second_percent": (len(recent_second) / self._rate_limit_per_second) * 100,
            "utilization_minute_percent": (len(recent_minute) / self._rate_limit_per_minute) * 100
        }


