"""
Drift Protocol Integration

Provides API wrapper for Drift perpetual futures and spot trading.
Supports account creation, deposits, and trading interactions.
"""

import logging
from typing import Optional, Dict, Any
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta


logger = logging.getLogger(__name__)


# Drift program ID
DRIFT_PROGRAM_ID = Pubkey.from_string("dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH")


class DriftIntegration:
    """
    Drift Protocol integration for perpetual futures and spot trading.
    
    Provides methods to:
    - Initialize user account
    - Deposit collateral
    - Withdraw collateral
    - Place orders (for airdrop farming)
    - Query account state
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey):
        """
        Initialize Drift integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.program_id = DRIFT_PROGRAM_ID
        
        logger.info(f"Initialized Drift integration for wallet {wallet_pubkey}")
    
    def has_account(self) -> bool:
        """
        Check if user has a Drift account.
        
        Returns:
            True if account exists, False otherwise
        
        Raises:
            Exception: If account check fails
        """
        try:
            logger.info("Checking for Drift account")
            
            # Derive user account PDA
            user_account = self._derive_user_account()
            
            # Check if account exists
            account_info = self.rpc_client.get_account_info(str(user_account))
            exists = account_info is not None
            
            logger.info(f"Drift account exists: {exists}")
            return exists
        
        except Exception as e:
            error_msg = f"Failed to check Drift account: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_initialize_account_transaction(self) -> Transaction:
        """
        Create a transaction to initialize a Drift user account.
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info("Creating Drift account initialization transaction")
            
            # Derive user account PDA
            user_account = self._derive_user_account()
            
            # Create initialize instruction
            instruction = self._create_initialize_instruction(user_account)
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info("Created Drift account initialization transaction")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create initialize transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_deposit_transaction(self, amount: float) -> Transaction:
        """
        Create a transaction to deposit collateral into Drift.
        
        Args:
            amount: Amount of USDC to deposit
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Deposit amount must be positive")
            
            logger.info(f"Creating Drift deposit transaction for {amount} USDC")
            
            # Convert to token units (6 decimals for USDC)
            token_amount = int(amount * 1e6)
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Create deposit instruction
            instruction = self._create_deposit_instruction(user_account, token_amount)
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created Drift deposit transaction for {amount} USDC")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create deposit transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_withdraw_transaction(self, amount: float) -> Transaction:
        """
        Create a transaction to withdraw collateral from Drift.
        
        Args:
            amount: Amount of USDC to withdraw
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Withdraw amount must be positive")
            
            logger.info(f"Creating Drift withdraw transaction for {amount} USDC")
            
            # Convert to token units
            token_amount = int(amount * 1e6)
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Create withdraw instruction
            instruction = self._create_withdraw_instruction(user_account, token_amount)
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created Drift withdraw transaction for {amount} USDC")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create withdraw transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_interaction_transaction(self) -> Transaction:
        """
        Create a small interaction transaction for airdrop farming.
        
        This creates a minimal transaction to interact with Drift protocol
        for the purpose of qualifying for potential airdrops.
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info("Creating Drift interaction transaction for airdrop farming")
            
            # For airdrop farming, we'll do a small deposit/withdraw cycle
            # or place and cancel a small order
            
            # Use a minimal amount (0.01 USDC)
            amount = 0.01
            
            # Create a deposit transaction as the interaction
            transaction = self.create_deposit_transaction(amount)
            
            logger.info("Created Drift interaction transaction")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create interaction transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_account_balance(self) -> float:
        """
        Get user's collateral balance in Drift.
        
        Returns:
            Balance in USDC
        
        Raises:
            Exception: If balance query fails
        """
        try:
            logger.info("Querying Drift account balance")
            
            # Derive user account
            user_account = self._derive_user_account()
            
            # Query account data
            account_info = self.rpc_client.get_account_info(str(user_account))
            
            if not account_info:
                logger.info("No Drift account found, balance is 0")
                return 0.0
            
            # Parse account data to get balance
            # This is simplified - real implementation would parse the account data
            balance = 0.0
            
            logger.info(f"Drift account balance: {balance} USDC")
            return balance
        
        except Exception as e:
            error_msg = f"Failed to get account balance: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _derive_user_account(self) -> Pubkey:
        """
        Derive the user account PDA for Drift.
        
        Returns:
            User account public key
        """
        # Simplified PDA derivation
        # Real implementation would use proper seeds and bump
        # For now, return a placeholder based on wallet
        
        # In production: Pubkey.find_program_address([b"user", bytes(self.wallet_pubkey)], self.program_id)
        return self.wallet_pubkey  # Placeholder
    
    def _create_initialize_instruction(self, user_account: Pubkey) -> Instruction:
        """
        Create an initialize user account instruction.
        
        Args:
            user_account: User account public key
        
        Returns:
            Initialize instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x00"  # Initialize discriminator
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_deposit_instruction(self, user_account: Pubkey, amount: int) -> Instruction:
        """
        Create a deposit instruction.
        
        Args:
            user_account: User account public key
            amount: Amount to deposit in token units
        
        Returns:
            Deposit instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x01" + amount.to_bytes(8, 'little')  # Deposit discriminator + amount
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_withdraw_instruction(self, user_account: Pubkey, amount: int) -> Instruction:
        """
        Create a withdraw instruction.
        
        Args:
            user_account: User account public key
            amount: Amount to withdraw in token units
        
        Returns:
            Withdraw instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=user_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = b"\x02" + amount.to_bytes(8, 'little')  # Withdraw discriminator + amount
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
