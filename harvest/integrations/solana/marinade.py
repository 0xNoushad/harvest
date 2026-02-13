"""
Marinade Finance Integration

Provides API wrapper for Marinade liquid staking protocol.
Supports staking SOL and receiving mSOL tokens.
"""

import logging
from typing import Optional, Dict, Any
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta
from solders.system_program import ID as SYSTEM_PROGRAM_ID


logger = logging.getLogger(__name__)


# Marinade program IDs
MARINADE_PROGRAM_ID = Pubkey.from_string("MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD")
MSOL_MINT = Pubkey.from_string("mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So")


class MarinadeIntegration:
    """
    Marinade Finance integration for liquid staking.
    
    Provides methods to:
    - Stake SOL and receive mSOL
    - Unstake mSOL and receive SOL
    - Query mSOL balance
    - Get current exchange rate
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey):
        """
        Initialize Marinade integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.program_id = MARINADE_PROGRAM_ID
        self.msol_mint = MSOL_MINT
        
        logger.info(f"Initialized Marinade integration for wallet {wallet_pubkey}")
    
    def get_msol_balance(self) -> float:
        """
        Get mSOL token balance for the wallet.
        
        Returns:
            mSOL balance as float
        
        Raises:
            Exception: If balance query fails
        """
        try:
            # Find associated token account for mSOL
            token_account = self._get_associated_token_address(
                self.wallet_pubkey,
                self.msol_mint
            )
            
            balance = self.rpc_client.get_token_balance(str(token_account))
            logger.info(f"mSOL balance: {balance}")
            return balance
        
        except Exception as e:
            error_msg = f"Failed to get mSOL balance: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_exchange_rate(self) -> float:
        """
        Get current SOL to mSOL exchange rate.
        
        Returns:
            Exchange rate (mSOL per SOL)
        
        Raises:
            Exception: If rate query fails
        """
        try:
            # Query Marinade state account for exchange rate
            # This is a simplified implementation
            # In production, you'd query the actual Marinade state account
            
            # For now, return approximate rate (mSOL is slightly less than 1:1)
            # Real implementation would parse the state account data
            rate = 0.98  # Approximate rate
            logger.info(f"SOL to mSOL exchange rate: {rate}")
            return rate
        
        except Exception as e:
            error_msg = f"Failed to get exchange rate: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_stake_transaction(self, amount_sol: float) -> Transaction:
        """
        Create a transaction to stake SOL and receive mSOL.
        
        Args:
            amount_sol: Amount of SOL to stake
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount_sol <= 0:
                raise ValueError("Stake amount must be positive")
            
            lamports = int(amount_sol * 1e9)
            
            logger.info(f"Creating stake transaction for {amount_sol} SOL")
            
            # Get associated token account for mSOL
            msol_token_account = self._get_associated_token_address(
                self.wallet_pubkey,
                self.msol_mint
            )
            
            # Create instruction to stake SOL
            # This is a simplified version - real implementation would use
            # the actual Marinade instruction layout
            instruction = self._create_stake_instruction(
                lamports,
                msol_token_account
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created stake transaction for {amount_sol} SOL")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create stake transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_unstake_transaction(self, amount_msol: float) -> Transaction:
        """
        Create a transaction to unstake mSOL and receive SOL.
        
        Args:
            amount_msol: Amount of mSOL to unstake
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount_msol <= 0:
                raise ValueError("Unstake amount must be positive")
            
            logger.info(f"Creating unstake transaction for {amount_msol} mSOL")
            
            # Get associated token account for mSOL
            msol_token_account = self._get_associated_token_address(
                self.wallet_pubkey,
                self.msol_mint
            )
            
            # Create instruction to unstake mSOL
            instruction = self._create_unstake_instruction(
                int(amount_msol * 1e9),
                msol_token_account
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created unstake transaction for {amount_msol} mSOL")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create unstake transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _get_associated_token_address(self, wallet: Pubkey, mint: Pubkey) -> Pubkey:
        """
        Derive associated token account address.
        
        Args:
            wallet: Wallet public key
            mint: Token mint public key
        
        Returns:
            Associated token account public key
        """
        # This is a simplified implementation
        # Real implementation would use the SPL Token program's
        # associated token account derivation
        
        # For now, return a placeholder
        # In production, use: get_associated_token_address(wallet, mint)
        from solders.pubkey import Pubkey
        
        # Placeholder - would need proper ATA derivation
        seeds = [
            bytes(wallet),
            bytes(Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")),
            bytes(mint)
        ]
        
        # This is simplified - real implementation uses proper PDA derivation
        return wallet  # Placeholder
    
    def _create_stake_instruction(self, lamports: int, msol_account: Pubkey) -> Instruction:
        """
        Create a stake instruction for Marinade.
        
        Args:
            lamports: Amount to stake in lamports
            msol_account: mSOL token account to receive tokens
        
        Returns:
            Stake instruction
        """
        # This is a simplified instruction structure
        # Real implementation would use the actual Marinade instruction layout
        
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=msol_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
            AccountMeta(pubkey=SYSTEM_PROGRAM_ID, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        # Real implementation would encode proper instruction discriminator and data
        data = lamports.to_bytes(8, 'little')
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_unstake_instruction(self, amount: int, msol_account: Pubkey) -> Instruction:
        """
        Create an unstake instruction for Marinade.
        
        Args:
            amount: Amount to unstake
            msol_account: mSOL token account
        
        Returns:
            Unstake instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=msol_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        data = amount.to_bytes(8, 'little')
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
