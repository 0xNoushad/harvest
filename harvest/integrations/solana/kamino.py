"""
Kamino Finance Integration

Provides API wrapper for Kamino yield vaults.
Supports deposits, withdrawals, and vault queries.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta


logger = logging.getLogger(__name__)


# Kamino program ID
KAMINO_PROGRAM_ID = Pubkey.from_string("KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD")


@dataclass
class VaultInfo:
    """Information about a Kamino vault."""
    address: str
    name: str
    apy: float
    tvl: float
    token_mint: str
    strategy: str


class KaminoIntegration:
    """
    Kamino Finance integration for yield farming.
    
    Provides methods to:
    - Query available vaults
    - Deposit tokens into vaults
    - Withdraw tokens from vaults
    - Get vault APY and TVL
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey):
        """
        Initialize Kamino integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.program_id = KAMINO_PROGRAM_ID
        
        logger.info(f"Initialized Kamino integration for wallet {wallet_pubkey}")
    
    def get_vaults(self, token_mint: Optional[str] = None) -> List[VaultInfo]:
        """
        Get list of available Kamino vaults.
        
        Args:
            token_mint: Optional filter by token mint address
        
        Returns:
            List of VaultInfo objects
        
        Raises:
            Exception: If vault query fails
        """
        try:
            logger.info("Querying Kamino vaults")
            
            # In production, this would query the Kamino API or on-chain accounts
            # For now, return mock data for common vaults
            vaults = [
                VaultInfo(
                    address="KVault1111111111111111111111111111111111111",
                    name="USDC Vault",
                    apy=12.5,
                    tvl=5000000.0,
                    token_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    strategy="lending"
                ),
                VaultInfo(
                    address="KVault2222222222222222222222222222222222222",
                    name="USDT Vault",
                    apy=11.8,
                    tvl=3000000.0,
                    token_mint="Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
                    strategy="lending"
                ),
                VaultInfo(
                    address="KVault3333333333333333333333333333333333333",
                    name="SOL Vault",
                    apy=8.5,
                    tvl=10000000.0,
                    token_mint="So11111111111111111111111111111111111111112",
                    strategy="staking"
                ),
            ]
            
            # Filter by token mint if specified
            if token_mint:
                vaults = [v for v in vaults if v.token_mint == token_mint]
            
            logger.info(f"Found {len(vaults)} Kamino vaults")
            return vaults
        
        except Exception as e:
            error_msg = f"Failed to get Kamino vaults: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_best_vault(self, token_mint: str) -> Optional[VaultInfo]:
        """
        Get the vault with highest APY for a given token.
        
        Args:
            token_mint: Token mint address
        
        Returns:
            VaultInfo with highest APY or None if no vaults found
        
        Raises:
            Exception: If vault query fails
        """
        try:
            vaults = self.get_vaults(token_mint=token_mint)
            
            if not vaults:
                logger.warning(f"No vaults found for token {token_mint}")
                return None
            
            # Sort by APY descending and return first
            best_vault = max(vaults, key=lambda v: v.apy)
            logger.info(f"Best vault for {token_mint}: {best_vault.name} with {best_vault.apy}% APY")
            return best_vault
        
        except Exception as e:
            error_msg = f"Failed to get best vault: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_vault_info(self, vault_address: str) -> VaultInfo:
        """
        Get detailed information about a specific vault.
        
        Args:
            vault_address: Vault public key as string
        
        Returns:
            VaultInfo object
        
        Raises:
            Exception: If vault query fails
        """
        try:
            logger.info(f"Querying vault info for {vault_address}")
            
            # In production, query the vault account on-chain
            # For now, return from our mock list
            vaults = self.get_vaults()
            vault = next((v for v in vaults if v.address == vault_address), None)
            
            if not vault:
                raise ValueError(f"Vault not found: {vault_address}")
            
            return vault
        
        except Exception as e:
            error_msg = f"Failed to get vault info: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_user_balance(self, vault_address: str) -> float:
        """
        Get user's balance in a specific vault.
        
        Args:
            vault_address: Vault public key as string
        
        Returns:
            User's vault token balance
        
        Raises:
            Exception: If balance query fails
        """
        try:
            logger.info(f"Querying user balance in vault {vault_address}")
            
            # In production, query the user's vault token account
            # For now, return 0 as placeholder
            balance = 0.0
            
            logger.info(f"User balance in vault {vault_address}: {balance}")
            return balance
        
        except Exception as e:
            error_msg = f"Failed to get user vault balance: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_deposit_transaction(self, vault_address: str, amount: float) -> Transaction:
        """
        Create a transaction to deposit tokens into a vault.
        
        Args:
            vault_address: Vault public key as string
            amount: Amount of tokens to deposit
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Deposit amount must be positive")
            
            logger.info(f"Creating deposit transaction for {amount} tokens to vault {vault_address}")
            
            vault_pubkey = Pubkey.from_string(vault_address)
            
            # Get vault info to determine token mint
            vault_info = self.get_vault_info(vault_address)
            token_mint = Pubkey.from_string(vault_info.token_mint)
            
            # Convert amount to token units (assuming 6 decimals for USDC/USDT)
            token_amount = int(amount * 1e6)
            
            # Create deposit instruction
            instruction = self._create_deposit_instruction(
                vault_pubkey,
                token_mint,
                token_amount
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created deposit transaction for {amount} tokens")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create deposit transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_withdraw_transaction(self, vault_address: str, amount: float) -> Transaction:
        """
        Create a transaction to withdraw tokens from a vault.
        
        Args:
            vault_address: Vault public key as string
            amount: Amount of tokens to withdraw
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            if amount <= 0:
                raise ValueError("Withdraw amount must be positive")
            
            logger.info(f"Creating withdraw transaction for {amount} tokens from vault {vault_address}")
            
            vault_pubkey = Pubkey.from_string(vault_address)
            
            # Get vault info
            vault_info = self.get_vault_info(vault_address)
            token_mint = Pubkey.from_string(vault_info.token_mint)
            
            # Convert amount to token units
            token_amount = int(amount * 1e6)
            
            # Create withdraw instruction
            instruction = self._create_withdraw_instruction(
                vault_pubkey,
                token_mint,
                token_amount
            )
            
            # Get recent blockhash
            blockhash_info = self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_info.get("blockhash")
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created withdraw transaction for {amount} tokens")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create withdraw transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_deposit_instruction(
        self,
        vault: Pubkey,
        token_mint: Pubkey,
        amount: int
    ) -> Instruction:
        """
        Create a deposit instruction for Kamino.
        
        Args:
            vault: Vault public key
            token_mint: Token mint public key
            amount: Amount to deposit in token units
        
        Returns:
            Deposit instruction
        """
        # Simplified instruction structure
        # Real implementation would use actual Kamino instruction layout
        
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        # Real implementation would encode proper instruction discriminator and data
        data = amount.to_bytes(8, 'little')
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_withdraw_instruction(
        self,
        vault: Pubkey,
        token_mint: Pubkey,
        amount: int
    ) -> Instruction:
        """
        Create a withdraw instruction for Kamino.
        
        Args:
            vault: Vault public key
            token_mint: Token mint public key
            amount: Amount to withdraw in token units
        
        Returns:
            Withdraw instruction
        """
        # Simplified instruction structure
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=vault, is_signer=False, is_writable=True),
            AccountMeta(pubkey=token_mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.program_id, is_signer=False, is_writable=False),
        ]
        
        data = amount.to_bytes(8, 'little')
        
        return Instruction(
            program_id=self.program_id,
            accounts=accounts,
            data=data
        )
