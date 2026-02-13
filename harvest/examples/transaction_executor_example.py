"""
Example usage of TransactionExecutor

Demonstrates how to use the TransactionExecutor for executing
transactions with retry logic, priority fee optimization, and
error handling.
"""

import asyncio
import logging
from solana.rpc.async_api import AsyncClient
from agent.core.wallet import WalletManager
from agent.core.rpc_fallback import RPCFallbackManager
from agent.trading.transaction_executor import TransactionExecutor, ExecutionResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_usage():
    """
    Example 1: Basic transaction execution
    """
    logger.info("=== Example 1: Basic Transaction Execution ===")
    
    # Initialize components
    rpc_client = AsyncClient("https://api.devnet.solana.com")
    wallet_manager = WalletManager(network="devnet")
    
    # Create executor
    executor = TransactionExecutor(
        rpc_client=rpc_client,
        wallet_manager=wallet_manager,
        max_retries=3,
        confirmation_timeout=60
    )
    
    # Create a mock transaction (in real usage, this would be a real transaction)
    # transaction = create_swap_transaction(...)
    
    logger.info("TransactionExecutor initialized successfully")
    logger.info(f"Max retries: {executor.max_retries}")
    logger.info(f"Confirmation timeout: {executor.confirmation_timeout}s")
    logger.info(f"Base priority fee: {executor.base_priority_fee} microlamports")
    
    await rpc_client.close()
    await wallet_manager.close()


async def example_with_rpc_fallback():
    """
    Example 2: Transaction execution with RPC fallback
    """
    logger.info("\n=== Example 2: Transaction Execution with RPC Fallback ===")
    
    # Initialize components with fallback
    rpc_client = AsyncClient("https://api.devnet.solana.com")
    wallet_manager = WalletManager(network="devnet")
    rpc_fallback_manager = RPCFallbackManager()
    
    # Create executor with fallback support
    executor = TransactionExecutor(
        rpc_client=rpc_client,
        wallet_manager=wallet_manager,
        rpc_fallback_manager=rpc_fallback_manager,
        max_retries=3,
        confirmation_timeout=60
    )
    
    logger.info("TransactionExecutor with RPC fallback initialized")
    logger.info(f"Available RPC providers: {len(rpc_fallback_manager.providers)}")
    
    # Show provider status
    status = rpc_fallback_manager.get_provider_status()
    logger.info(f"Current provider: {status['current']}")
    
    await rpc_client.close()
    await wallet_manager.close()


async def example_error_handling():
    """
    Example 3: Error handling demonstration
    """
    logger.info("\n=== Example 3: Error Handling ===")
    
    from agent.trading.transaction_executor import ErrorHandler
    
    # Test retryable errors
    errors = [
        Exception("Connection timeout"),
        Exception("Network error occurred"),
        Exception("Rate limit exceeded (429)"),
        Exception("Insufficient balance"),
        Exception("Invalid signature"),
        Exception("Wallet access failed"),
    ]
    
    for error in errors:
        is_retryable = ErrorHandler.is_retryable(error)
        is_critical = ErrorHandler.is_critical(error)
        
        logger.info(f"Error: {error}")
        logger.info(f"  Retryable: {is_retryable}")
        logger.info(f"  Critical: {is_critical}")
        
        if is_retryable:
            delay = ErrorHandler.get_retry_delay(0)
            logger.info(f"  Retry delay: {delay}s")
        
        logger.info("")


async def example_priority_fee_optimization():
    """
    Example 4: Priority fee optimization
    """
    logger.info("\n=== Example 4: Priority Fee Optimization ===")
    
    rpc_client = AsyncClient("https://api.devnet.solana.com")
    wallet_manager = WalletManager(network="devnet")
    
    executor = TransactionExecutor(
        rpc_client=rpc_client,
        wallet_manager=wallet_manager,
        base_priority_fee=5000  # 5000 microlamports
    )
    
    logger.info(f"Base priority fee: {executor.base_priority_fee} microlamports")
    
    # Simulate priority fee increases on retries
    for retry in range(4):
        # In real usage, this would be called automatically during retries
        await executor._set_priority_fee(retry)
        logger.info(f"Retry {retry}: Priority fee = {executor.current_priority_fee} microlamports")
    
    await rpc_client.close()
    await wallet_manager.close()


async def example_execution_result():
    """
    Example 5: Understanding ExecutionResult
    """
    logger.info("\n=== Example 5: ExecutionResult Structure ===")
    
    from datetime import datetime
    
    # Example successful result
    success_result = ExecutionResult(
        success=True,
        transaction_hash="5j7s8K9mN2pQ3rT4uV5wX6yZ7aB8cD9eF0gH1iJ2kL3mN4oP5qR6sT7uV8wX9yZ0",
        profit=0.05,
        error=None,
        timestamp=datetime.now(),
        strategy_name="jupiter_swap",
        expected_profit=0.05,
        actual_gas_fee=0.000005,
        execution_time_ms=1234,
        confirmation_time_ms=5678,
        retry_count=0,
        final_balance=1.05
    )
    
    logger.info("Successful execution result:")
    logger.info(f"  Success: {success_result.success}")
    logger.info(f"  Transaction: {success_result.transaction_hash[:20]}...")
    logger.info(f"  Strategy: {success_result.strategy_name}")
    logger.info(f"  Expected profit: {success_result.expected_profit} SOL")
    logger.info(f"  Actual profit: {success_result.profit} SOL")
    logger.info(f"  Gas fee: {success_result.actual_gas_fee} SOL")
    logger.info(f"  Execution time: {success_result.execution_time_ms}ms")
    logger.info(f"  Confirmation time: {success_result.confirmation_time_ms}ms")
    logger.info(f"  Retries: {success_result.retry_count}")
    logger.info(f"  Final balance: {success_result.final_balance} SOL")
    
    # Example failed result
    logger.info("\nFailed execution result:")
    failed_result = ExecutionResult(
        success=False,
        transaction_hash=None,
        profit=0.0,
        error="Network timeout after 3 retries",
        timestamp=datetime.now(),
        strategy_name="jupiter_swap",
        expected_profit=0.05,
        actual_gas_fee=0.0,
        execution_time_ms=180000,
        confirmation_time_ms=0,
        retry_count=3,
        final_balance=1.0
    )
    
    logger.info(f"  Success: {failed_result.success}")
    logger.info(f"  Error: {failed_result.error}")
    logger.info(f"  Retries: {failed_result.retry_count}")


async def main():
    """Run all examples."""
    try:
        await example_basic_usage()
        await example_with_rpc_fallback()
        await example_error_handling()
        await example_priority_fee_optimization()
        await example_execution_result()
        
        logger.info("\n=== All examples completed successfully ===")
    
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
