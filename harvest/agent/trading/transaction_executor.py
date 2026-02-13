"""
Transaction Executor for Harvest Trading Agent

Executes transactions on Solana blockchain with:
- Transaction signing and submission
- Confirmation waiting with timeout
- Retry logic with blockhash refresh
- Priority fee optimization
- Error handling and RPC fallback
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from solders.transaction import Transaction
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """
    Result of executing a trading opportunity.
    """
    success: bool
    transaction_hash: Optional[str]
    profit: float  # Actual profit in SOL
    error: Optional[str]
    timestamp: datetime
    
    # Enhanced fields
    strategy_name: str
    expected_profit: float
    actual_gas_fee: float
    execution_time_ms: int
    confirmation_time_ms: int
    retry_count: int
    final_balance: float


class ErrorHandler:
    """
    Centralized error handling for trading operations.
    """
    
    # Retryable error patterns
    RETRYABLE_ERRORS = [
        "timeout",
        "connection",
        "network",
        "blockhash",
        "priority fee",
        "rate limit",
        "429",
        "503",
        "504",
    ]
    
    # Critical error patterns
    CRITICAL_ERRORS = [
        "wallet",
        "keypair",
        "private key",
        "signature verification failed",
    ]
    
    # Non-retryable error patterns
    NON_RETRYABLE_ERRORS = [
        "insufficient",
        "balance",
        "invalid signature",
        "invalid token",
        "slippage",
    ]
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Determine if an error should trigger a retry."""
        error_str = str(error).lower()
        
        # Check if it's a non-retryable error first
        for pattern in ErrorHandler.NON_RETRYABLE_ERRORS:
            if pattern in error_str:
                return False
        
        # Check if it's a retryable error
        for pattern in ErrorHandler.RETRYABLE_ERRORS:
            if pattern in error_str:
                return True
        
        return False
    
    @staticmethod
    def is_critical(error: Exception) -> bool:
        """Determine if an error requires system shutdown."""
        error_str = str(error).lower()
        
        for pattern in ErrorHandler.CRITICAL_ERRORS:
            if pattern in error_str:
                return True
        
        return False
    
    @staticmethod
    def get_retry_delay(attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return min(2 ** attempt, 60)  # Cap at 60 seconds
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: str,
        attempt: int = 0
    ) -> Tuple[bool, bool]:
        """
        Handle an error and determine next action.
        
        Returns:
            (should_retry, should_shutdown)
        """
        is_critical = ErrorHandler.is_critical(error)
        is_retryable = ErrorHandler.is_retryable(error)
        
        if is_critical:
            logger.critical(f"CRITICAL ERROR in {context}: {error}")
            return False, True
        
        if is_retryable:
            logger.warning(f"Retryable error in {context} (attempt {attempt}): {error}")
            return True, False
        
        logger.error(f"Non-retryable error in {context}: {error}")
        return False, False


class TransactionExecutor:
    """
    Executes transactions on Solana blockchain with retry logic.
    """
    
    def __init__(
        self,
        rpc_client: AsyncClient,
        wallet_manager,
        rpc_fallback_manager=None,
        max_retries: int = 3,
        confirmation_timeout: int = 60,
        base_priority_fee: int = 5000,  # microlamports
    ):
        """
        Initialize transaction executor.
        
        Args:
            rpc_client: Primary RPC client for blockchain interaction
            wallet_manager: Wallet manager for transaction signing
            rpc_fallback_manager: Optional RPC fallback manager for endpoint switching
            max_retries: Maximum retry attempts (default 3)
            confirmation_timeout: Seconds to wait for confirmation (default 60)
            base_priority_fee: Base priority fee in microlamports (default 5000)
        """
        self.rpc_client = rpc_client
        self.wallet_manager = wallet_manager
        self.rpc_fallback_manager = rpc_fallback_manager
        self.max_retries = max_retries
        self.confirmation_timeout = confirmation_timeout
        self.base_priority_fee = base_priority_fee
        self.current_priority_fee = base_priority_fee
        
        logger.info(
            f"TransactionExecutor initialized: "
            f"max_retries={max_retries}, "
            f"timeout={confirmation_timeout}s, "
            f"base_fee={base_priority_fee}"
        )
    
    async def execute_transaction(
        self,
        transaction: Transaction,
        strategy_name: str,
        expected_profit: float = 0.0,
        user_id: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute a transaction with retry logic.
        
        Args:
            transaction: Unsigned transaction to execute
            strategy_name: Name of strategy executing the transaction
            expected_profit: Expected profit from the transaction
            user_id: Optional user ID for user-specific RPC routing
            
        Returns:
            ExecutionResult with transaction hash and status
        """
        start_time = time.time()
        retry_count = 0
        last_error = None
        
        # Get initial balance
        initial_balance = await self.wallet_manager.get_balance()
        
        for attempt in range(self.max_retries):
            try:
                # Query and set priority fee before transaction
                await self._set_priority_fee(attempt)
                
                # Check for network congestion
                if await self._is_network_congested():
                    logger.info("Network congested, delaying transaction...")
                    await asyncio.sleep(5)
                
                # Sign transaction
                signed_tx = await self._sign_transaction(transaction)
                
                # Submit transaction
                signature = await self._submit_transaction(signed_tx, user_id)
                
                # Wait for confirmation
                confirmation_start = time.time()
                confirmed = await self._wait_for_confirmation(
                    signature,
                    self.confirmation_timeout
                )
                confirmation_time_ms = int((time.time() - confirmation_start) * 1000)
                
                if not confirmed:
                    raise Exception("Transaction confirmation timeout")
                
                # Get final balance and calculate actual profit
                final_balance = await self.wallet_manager.get_balance()
                actual_profit = final_balance - initial_balance
                
                # Calculate gas fee (approximate)
                actual_gas_fee = expected_profit - actual_profit if expected_profit > actual_profit else 0.0
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                logger.info(
                    f"Transaction successful: {signature} "
                    f"(strategy={strategy_name}, "
                    f"profit={actual_profit:.6f} SOL, "
                    f"time={execution_time_ms}ms)"
                )
                
                return ExecutionResult(
                    success=True,
                    transaction_hash=signature,
                    profit=actual_profit,
                    error=None,
                    timestamp=datetime.now(),
                    strategy_name=strategy_name,
                    expected_profit=expected_profit,
                    actual_gas_fee=actual_gas_fee,
                    execution_time_ms=execution_time_ms,
                    confirmation_time_ms=confirmation_time_ms,
                    retry_count=retry_count,
                    final_balance=final_balance
                )
            
            except Exception as e:
                last_error = e
                retry_count += 1
                
                # Handle error and determine if we should retry
                should_retry, should_shutdown = ErrorHandler.handle_error(
                    e,
                    f"execute_transaction[{strategy_name}]",
                    attempt
                )
                
                if should_shutdown:
                    logger.critical("Critical error detected, shutting down executor")
                    raise e
                
                if not should_retry or attempt >= self.max_retries - 1:
                    break
                
                # Handle blockhash expiration
                if "blockhash" in str(e).lower():
                    logger.info("Blockhash expired, refreshing...")
                    transaction = await self._handle_blockhash_expiration(transaction)
                
                # Wait with exponential backoff
                delay = ErrorHandler.get_retry_delay(attempt)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
                
                # Try RPC fallback if available
                if self.rpc_fallback_manager and "network" in str(e).lower():
                    logger.info("Attempting RPC fallback...")
                    await self._switch_rpc_endpoint()
        
        # All retries failed
        execution_time_ms = int((time.time() - start_time) * 1000)
        final_balance = await self.wallet_manager.get_balance()
        
        logger.error(
            f"Transaction failed after {retry_count} retries: {last_error} "
            f"(strategy={strategy_name})"
        )
        
        return ExecutionResult(
            success=False,
            transaction_hash=None,
            profit=0.0,
            error=str(last_error),
            timestamp=datetime.now(),
            strategy_name=strategy_name,
            expected_profit=expected_profit,
            actual_gas_fee=0.0,
            execution_time_ms=execution_time_ms,
            confirmation_time_ms=0,
            retry_count=retry_count,
            final_balance=final_balance
        )
    
    async def _sign_transaction(self, transaction: Transaction) -> Transaction:
        """
        Sign transaction using wallet manager.
        
        Args:
            transaction: Unsigned transaction
            
        Returns:
            Signed transaction
        """
        try:
            # Get recent blockhash if not set
            if not hasattr(transaction, 'recent_blockhash') or not transaction.recent_blockhash:
                blockhash_resp = await self.rpc_client.get_latest_blockhash()
                recent_blockhash = blockhash_resp.value.blockhash
                transaction.recent_blockhash = recent_blockhash
            
            # Sign with wallet
            signed_tx = self.wallet_manager.sign_transaction(transaction)
            
            logger.debug("Transaction signed successfully")
            return signed_tx
        
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise
    
    async def _submit_transaction(
        self,
        signed_tx: Transaction,
        user_id: Optional[str] = None
    ) -> str:
        """
        Submit signed transaction via RPC client.
        
        Args:
            signed_tx: Signed transaction
            user_id: Optional user ID for user-specific RPC routing
            
        Returns:
            Transaction signature
        """
        try:
            # Use RPC fallback manager if available and user_id provided
            if self.rpc_fallback_manager and user_id:
                # Serialize transaction
                tx_bytes = bytes(signed_tx.serialize())
                tx_base64 = tx_bytes.hex()
                
                # Submit via fallback manager
                signature = await self.rpc_fallback_manager.rpc_call(
                    "sendTransaction",
                    [tx_base64, {"encoding": "hex"}],
                    user_id=user_id
                )
                return signature
            
            # Use primary RPC client
            opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            response = await self.rpc_client.send_transaction(signed_tx, opts=opts)
            signature = str(response.value)
            
            logger.debug(f"Transaction submitted: {signature}")
            return signature
        
        except Exception as e:
            logger.error(f"Failed to submit transaction: {e}")
            raise
    
    async def _wait_for_confirmation(
        self,
        signature: str,
        timeout: int
    ) -> bool:
        """
        Wait for transaction confirmation.
        
        Args:
            signature: Transaction signature
            timeout: Timeout in seconds
            
        Returns:
            True if confirmed, False if timeout
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    # Check transaction status
                    response = await self.rpc_client.get_signature_statuses([signature])
                    
                    if response.value and response.value[0]:
                        status = response.value[0]
                        
                        # Check if confirmed
                        if status.confirmation_status in ["confirmed", "finalized"]:
                            logger.debug(f"Transaction confirmed: {signature}")
                            return True
                        
                        # Check for errors
                        if status.err:
                            raise Exception(f"Transaction failed: {status.err}")
                    
                    # Wait before next check
                    await asyncio.sleep(2)
                
                except Exception as e:
                    # Log but continue waiting
                    logger.debug(f"Error checking confirmation: {e}")
                    await asyncio.sleep(2)
            
            logger.warning(f"Transaction confirmation timeout: {signature}")
            return False
        
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def _handle_blockhash_expiration(
        self,
        transaction: Transaction
    ) -> Transaction:
        """
        Update transaction with fresh blockhash.
        
        Args:
            transaction: Transaction with expired blockhash
            
        Returns:
            Transaction with fresh blockhash
        """
        try:
            # Get fresh blockhash
            blockhash_resp = await self.rpc_client.get_latest_blockhash()
            recent_blockhash = blockhash_resp.value.blockhash
            
            # Update transaction
            transaction.recent_blockhash = recent_blockhash
            
            logger.debug("Blockhash refreshed")
            return transaction
        
        except Exception as e:
            logger.error(f"Failed to refresh blockhash: {e}")
            raise
    
    async def _set_priority_fee(self, retry_attempt: int = 0):
        """
        Query and set priority fee for transaction.
        
        Args:
            retry_attempt: Current retry attempt (increases fee on retries)
        """
        try:
            # Query priority fee recommendations
            priority_fee = await self._get_priority_fee_recommendation()
            
            # Increase fee on retries (50% higher per retry)
            if retry_attempt > 0:
                priority_fee = int(priority_fee * (1.5 ** retry_attempt))
                logger.info(f"Increased priority fee to {priority_fee} (retry {retry_attempt})")
            
            self.current_priority_fee = priority_fee
        
        except Exception as e:
            logger.warning(f"Failed to query priority fee: {e}, using base fee")
            self.current_priority_fee = self.base_priority_fee
    
    async def _get_priority_fee_recommendation(self) -> int:
        """
        Get priority fee recommendation from RPC.
        
        Returns:
            Recommended priority fee in microlamports
        """
        try:
            # Query recent prioritization fees
            response = await self.rpc_client.get_recent_prioritization_fees()
            
            if response and len(response) > 0:
                # Use median of recent fees
                fees = [fee.prioritization_fee for fee in response]
                fees.sort()
                median_fee = fees[len(fees) // 2]
                
                # Use at least base fee
                return max(median_fee, self.base_priority_fee)
            
            return self.base_priority_fee
        
        except Exception as e:
            logger.debug(f"Failed to get priority fee recommendation: {e}")
            return self.base_priority_fee
    
    async def _is_network_congested(self) -> bool:
        """
        Check if network is congested based on priority fees.
        
        Returns:
            True if congested (priority fee > 0.001 SOL)
        """
        try:
            priority_fee = await self._get_priority_fee_recommendation()
            
            # Convert microlamports to SOL
            priority_fee_sol = priority_fee / 1_000_000_000_000
            
            # Consider congested if fee > 0.001 SOL
            is_congested = priority_fee_sol > 0.001
            
            if is_congested:
                logger.info(f"Network congested: priority fee = {priority_fee_sol:.6f} SOL")
            
            return is_congested
        
        except Exception:
            return False
    
    async def _switch_rpc_endpoint(self):
        """
        Switch to backup RPC endpoint on network errors.
        """
        if not self.rpc_fallback_manager:
            logger.warning("No RPC fallback manager available")
            return
        
        try:
            # Get next available provider
            provider = self.rpc_fallback_manager.get_current_provider()
            logger.info(f"Switched to RPC provider: {provider.name}")
        
        except Exception as e:
            logger.error(f"Failed to switch RPC endpoint: {e}")
