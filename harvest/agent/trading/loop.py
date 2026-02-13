"""Core agent loop for Harvest - scan, decide, execute, notify."""

import asyncio
import logging
from typing import List, Optional, Dict
from datetime import datetime
from time import time

from agent.core.wallet import WalletManager
from agent.trading.scanner import Scanner, Opportunity
from agent.core.provider import Provider, Decision
from agent.services.notifier import Notifier, ExecutionResult
from agent.monitoring.user_control import UserControl
from agent.trading.risk_manager import RiskManager
from agent.trading.performance import PerformanceTracker
from agent.trading.trade_queue import TradeQueue
from agent.logging_config import get_activity_logger

logger = logging.getLogger(__name__)
activity_logger = get_activity_logger()


class AgentLoop:
    """
    Main control loop that orchestrates all Harvest components.
    
    The agent loop continuously:
    1. Scans for opportunities across all strategies
    2. Evaluates each opportunity using the LLM Provider
    3. Checks user control preferences (ALWAYS mode)
    4. Executes approved opportunities or sends notifications
    5. Handles errors gracefully and continues operation
    
    Features:
    - Continuous scan cycle with adaptive intervals
    - Opportunity evaluation using Provider (LLM)
    - Execution flow with user control checks
    - Error handling and logging for all operations
    - Graceful error recovery (log and continue)
    - Adaptive scan intervals based on rate limits and empty scans
    
    """
    
    DEFAULT_SCAN_INTERVAL = 300  # 5 minutes in seconds
    MIN_SCAN_INTERVAL = 5  # Minimum 5 seconds between scans
    RATE_LIMIT_INCREASE_FACTOR = 1.5  # Increase interval by 50% on rate limits
    EMPTY_SCAN_THRESHOLD = 10  # Number of empty scans before increasing interval
    EMPTY_SCAN_INTERVAL = 30  # Interval after empty scans (seconds)
    
    def __init__(
        self,
        wallet: 'MultiUserWalletManager',  # Changed from WalletManager to MultiUserWalletManager
        scanner: Scanner,
        provider: Provider,
        notifier: Notifier,
        user_control: UserControl,
        risk_manager: Optional[RiskManager] = None,
        performance_tracker: Optional[PerformanceTracker] = None,
        fee_collector: Optional['MonthlyFeeCollector'] = None,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
        min_trading_balance: float = 0.01,  # New parameter for minimum trading balance
        stagger_window: int = 60,  # New parameter for staggered scanning window in seconds
    ):
        """
        Initialize agent loop with all required components.

        Args:
            wallet: MultiUserWalletManager instance for managing multiple user wallets
            scanner: Scanner instance for finding opportunities
            provider: Provider instance for LLM decision-making
            notifier: Notifier instance for Telegram notifications
            user_control: UserControl instance for preference management
            risk_manager: RiskManager instance for risk controls (optional, creates default if None)
            performance_tracker: PerformanceTracker instance for tracking trades (optional, creates default if None)
            fee_collector: MonthlyFeeCollector instance for fee management (optional)
            scan_interval: Interval between scans in seconds (default 300)
            min_trading_balance: Minimum balance required to trade in SOL (default 0.01)
            stagger_window: Time window for staggering large user base scans in seconds (default 60)
        """
        self.wallet = wallet
        self.scanner = scanner
        self.provider = provider
        self.notifier = notifier
        self.user_control = user_control
        self.risk_manager = risk_manager if risk_manager is not None else RiskManager()
        self.performance_tracker = performance_tracker if performance_tracker is not None else PerformanceTracker()
        self.fee_collector = fee_collector
        self.scan_interval = scan_interval
        self.min_trading_balance = min_trading_balance  # New attribute
        self.stagger_window = stagger_window  # New attribute for staggered scanning

        self._running = False
        self._last_scan_time: Optional[datetime] = None
        self._last_fee_check_date: Optional[int] = None  # Track last day we checked for fees

        self._current_scan_interval = scan_interval
        self._empty_scan_count = 0
        self._rate_limit_detected = False

        # New: Track user balances for activation/deactivation detection
        self.user_balance_cache: Dict[str, float] = {}
        
        # New: Trade execution queue for serializing trades
        self.trade_queue = TradeQueue()

        logger.info(f"AgentLoop initialized with scan interval: {scan_interval}s, min_trading_balance: {min_trading_balance} SOL, stagger_window: {stagger_window}s")

    
    async def start(self):
        """
        Start the main agent loop.
        
        Runs continuously until stopped, scanning for opportunities
        at regular intervals and handling them according to user preferences.
        
        Implements graceful error recovery - errors are logged but don't
        stop the agent from continuing.
        """
        self._running = True
        logger.info("🌾 Harvest agent starting...")
        
        # Start trade queue processor
        await self.trade_queue.start_processing()
        logger.info("Trade queue processor started")
        
        try:
            await self.notifier.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize notifier: {e}")
            self._running = False
            raise
        
        try:
            while self._running:
                try:
                    if self.fee_collector:
                        now = datetime.now()
                        if now.day == 1 and self._last_fee_check_date != now.day:
                            logger.info("It's the 1st of the month - requesting fee approvals")
                            try:
                                results = self.fee_collector.request_all_fees()
                                
                                for result in results:
                                    if result.get("status") == "pending":
                                        user_id = result["user_id"]
                                        fee_amount = result["fee_amount"]
                                        monthly_profit = result["monthly_profit"]
                                        month = result["month"]
                                        
                                        message = f"""💰 **Monthly Performance Fee**

Month: {month}
Your Profit: {monthly_profit:.4f} SOL
Performance Fee (2%): {fee_amount:.4f} SOL

Approve payment to continue using Harvest next month.
You have 7 days to approve.

Use /fees to see details
Use /approve_fee to approve
Use /decline_fee to decline
"""
                                        await self.notifier.send_message(message)
                                
                                self._last_fee_check_date = now.day
                                logger.info(f"Fee approval requests sent to {len(results)} users")
                            except Exception as e:
                                logger.error(f"Error requesting monthly fees: {e}", exc_info=True)
                    
                    await self.scan_cycle()
                    
                    next_interval = self._calculate_next_scan_interval()
                    
                    # Wait for next scan interval
                    logger.info(f"Waiting {next_interval}s until next scan...")
                    await asyncio.sleep(next_interval)
                    
                except Exception as e:
                    self.handle_error(e)
                    await asyncio.sleep(10)
        
        except asyncio.CancelledError:
            logger.info("Agent loop cancelled")
            raise
        finally:
            # Cleanup
            try:
                await self.trade_queue.stop_processing()
                logger.info("Trade queue processor stopped")
            except Exception as e:
                logger.error(f"Error stopping trade queue: {e}", exc_info=True)
            
            try:
                await self.notifier.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down notifier: {e}", exc_info=True)
            
            try:
                await self.wallet.close()
            except Exception as e:
                logger.error(f"Error closing wallet: {e}", exc_info=True)
            
            logger.info("🌾 Harvest agent stopped")
    
    def stop(self):
        """Stop the agent loop."""
        logger.info("Stopping agent loop...")
        self._running = False
    
    async def scan_cycle(self) -> Dict[str, List[Opportunity]]:
        """
        Execute one scan cycle across all users.

        Iterates through all registered users, checking balances and scanning
        for opportunities independently for each user. Implements error isolation
        so that failures for one user don't affect others.
        
        For large user bases (>100 users), implements staggered scanning to
        distribute load over time and avoid overwhelming RPC providers.

        Returns:
            Dict mapping user_id to list of opportunities found

        """
        logger.info("=" * 60)
        logger.info("Starting multi-user scan cycle...")
        self._last_scan_time = datetime.now()
        scan_start_time = time()

        # Get all user IDs with registered wallets
        user_ids = self.wallet.get_all_user_ids()

        if not user_ids:
            logger.info("No users registered - skipping scan cycle")
            activity_logger.log_scan_cycle(0, time() - scan_start_time)
            return {}

        logger.info(f"Scanning for {len(user_ids)} registered users")

        # Collect opportunities per user
        opportunities_by_user: Dict[str, List[Opportunity]] = {}
        total_opportunities = 0

        # Check if we need staggered scanning (>100 users)
        if len(user_ids) > 100:
            logger.info(f"Large user base detected ({len(user_ids)} users) - using staggered scanning")
            
            # Calculate batch size and delay between batches
            num_batches = max(1, len(user_ids) // 20)  # Aim for ~20 users per batch
            batch_size = (len(user_ids) + num_batches - 1) // num_batches  # Ceiling division
            delay_between_batches = self.stagger_window / num_batches if num_batches > 1 else 0
            
            logger.info(f"Staggered scanning: {num_batches} batches of ~{batch_size} users, {delay_between_batches:.2f}s delay between batches")
            
            # Process users in batches with delays
            for batch_idx in range(num_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(user_ids))
                batch_user_ids = user_ids[start_idx:end_idx]
                
                logger.debug(f"Processing batch {batch_idx + 1}/{num_batches}: users {start_idx} to {end_idx}")
                
                # Scan users in this batch
                for user_id in batch_user_ids:
                    try:
                        # Scan for opportunities for this user
                        user_opportunities = await self.scan_user(user_id)

                        if user_opportunities:
                            opportunities_by_user[user_id] = user_opportunities
                            total_opportunities += len(user_opportunities)
                            logger.info(f"Found {len(user_opportunities)} opportunities for user {user_id}")

                    except Exception as e:
                        # Error isolation: log error but continue with other users
                        logger.error(
                            f"Error scanning for user {user_id}: {e}",
                            exc_info=True
                        )
                        activity_logger.log_error(
                            component="AgentLoop",
                            error_type=type(e).__name__,
                            error_message=f"User scan failed: {str(e)}",
                            user_id=user_id,
                        )
                        # Continue with next user
                        continue
                
                # Add delay before next batch (except for last batch)
                if batch_idx < num_batches - 1 and delay_between_batches > 0:
                    logger.debug(f"Stagger delay: waiting {delay_between_batches:.2f}s before next batch")
                    await asyncio.sleep(delay_between_batches)
        else:
            # Standard scanning for smaller user bases
            # Iterate through each user
            for user_id in user_ids:
                try:
                    # Scan for opportunities for this user
                    user_opportunities = await self.scan_user(user_id)

                    if user_opportunities:
                        opportunities_by_user[user_id] = user_opportunities
                        total_opportunities += len(user_opportunities)
                        logger.info(f"Found {len(user_opportunities)} opportunities for user {user_id}")

                except Exception as e:
                    # Error isolation: log error but continue with other users
                    logger.error(
                        f"Error scanning for user {user_id}: {e}",
                        exc_info=True
                    )
                    activity_logger.log_error(
                        component="AgentLoop",
                        error_type=type(e).__name__,
                        error_message=f"User scan failed: {str(e)}",
                        user_id=user_id,
                    )
                    # Continue with next user
                    continue

        scan_duration = time() - scan_start_time

        if total_opportunities == 0:
            logger.info("No opportunities found across all users in this cycle")
            activity_logger.log_scan_cycle(0, scan_duration)

            # Track empty scans for adaptive interval management
            self._empty_scan_count += 1
            logger.debug(f"Empty scan count: {self._empty_scan_count}")
        else:
            logger.info(f"Found {total_opportunities} total opportunities across {len(opportunities_by_user)} users")
            activity_logger.log_scan_cycle(total_opportunities, scan_duration)
            self._empty_scan_count = 0

        # Process opportunities for each user
        for user_id, opportunities in opportunities_by_user.items():
            for opportunity in opportunities:
                try:
                    await self._process_opportunity(opportunity, user_id)
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        logger.warning(f"Rate limit detected: {e}")
                        self._rate_limit_detected = True

                    logger.error(
                        f"Error processing opportunity for user {user_id} from {opportunity.strategy_name}: {e}",
                        exc_info=True
                    )
                    activity_logger.log_error(
                        component="AgentLoop",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        strategy=opportunity.strategy_name,
                        action=opportunity.action,
                        user_id=user_id,
                    )
                    # Continue with next opportunity despite error
                    continue

        return opportunities_by_user
    async def scan_user(self, user_id: str) -> List[Opportunity]:
        """
        Scan for opportunities for a specific user.

        Checks the user's wallet balance and scans all enabled strategies
        if the balance meets the minimum trading threshold. Sends notifications
        when trading is activated or deactivated.
        
        Handles balance check failures gracefully - logs error but doesn't crash.

        Args:
            user_id: User to scan for

        Returns:
            List of opportunities found for this user (empty list on error)
        """
        logger.debug(f"Scanning for user {user_id}")

        try:
            # Check user's wallet balance
            try:
                current_balance = await self.wallet.get_balance(user_id)
                logger.debug(f"User {user_id} balance: {current_balance} SOL")
            except ValueError as e:
                # User has no wallet - skip scanning
                logger.debug(f"User {user_id} has no wallet: {e}")
                return []
            except Exception as e:
                # RPC or other error - log but don't crash
                logger.error(f"Failed to get balance for user {user_id}: {e}", exc_info=True)
                activity_logger.log_error(
                    component="AgentLoop",
                    error_type=type(e).__name__,
                    error_message=f"Balance check failed: {str(e)}",
                    user_id=user_id,
                )
                # Return empty list - skip this user for this cycle
                return []

            # Check for balance threshold crossings and notify
            try:
                await self.check_balance_and_notify(user_id, current_balance)
            except Exception as e:
                # Notification failure shouldn't stop scanning
                logger.error(f"Failed to send balance notification for user {user_id}: {e}", exc_info=True)

            # If balance < min_trading_balance, skip scanning
            if current_balance < self.min_trading_balance:
                logger.debug(
                    f"User {user_id} balance ({current_balance} SOL) below minimum "
                    f"({self.min_trading_balance} SOL) - skipping scan"
                )
                return []

            # Balance >= min_trading_balance, scan all enabled strategies
            logger.debug(f"User {user_id} has sufficient balance - scanning strategies")

            # Scan for opportunities (using existing scanner)
            opportunities = await self.scanner.scan_all()

            return opportunities

        except Exception as e:
            # Catch-all for any unexpected errors
            logger.error(f"Unexpected error scanning for user {user_id}: {e}", exc_info=True)
            activity_logger.log_error(
                component="AgentLoop",
                error_type=type(e).__name__,
                error_message=f"User scan failed: {str(e)}",
                user_id=user_id,
            )
            # Return empty list - don't let one user's error stop the whole scan
            return []
    async def check_balance_and_notify(self, user_id: str, current_balance: float):
        """
        Check if balance crossed trading threshold and notify user.

        Detects threshold crossings (below → above, above → below) and sends
        Telegram notifications when trading is activated or deactivated.

        Args:
            user_id: User ID
            current_balance: Current SOL balance
        """
        # Get previous balance from cache
        previous_balance = self.user_balance_cache.get(user_id)

        # If this is the first time checking this user's balance, just cache it
        if previous_balance is None:
            self.user_balance_cache[user_id] = current_balance
            logger.debug(f"First balance check for user {user_id}: {current_balance} SOL")
            return

        # Check for threshold crossings
        was_below_threshold = previous_balance < self.min_trading_balance
        is_below_threshold = current_balance < self.min_trading_balance

        # Detect activation: below → above
        if was_below_threshold and not is_below_threshold:
            logger.info(
                f"Trading ACTIVATED for user {user_id}: "
                f"balance increased from {previous_balance:.4f} to {current_balance:.4f} SOL"
            )

            # Send activation notification
            try:
                message = (
                    f"✅ **Trading Activated!**\n\n"
                    f"Your balance has reached {current_balance:.4f} SOL "
                    f"(minimum: {self.min_trading_balance} SOL).\n\n"
                    f"The bot will now scan for trading opportunities for you."
                )
                await self.notifier.send_message_to_user(user_id, message)
                logger.info(f"Sent activation notification to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send activation notification to user {user_id}: {e}")

        # Detect deactivation: above → below
        elif not was_below_threshold and is_below_threshold:
            logger.info(
                f"Trading DEACTIVATED for user {user_id}: "
                f"balance decreased from {previous_balance:.4f} to {current_balance:.4f} SOL"
            )

            # Send deactivation notification
            try:
                message = (
                    f"⚠️ **Trading Paused**\n\n"
                    f"Your balance has dropped to {current_balance:.4f} SOL "
                    f"(minimum: {self.min_trading_balance} SOL).\n\n"
                    f"Add funds to resume trading."
                )
                await self.notifier.send_message_to_user(user_id, message)
                logger.info(f"Sent deactivation notification to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send deactivation notification to user {user_id}: {e}")

        # Update balance cache
        self.user_balance_cache[user_id] = current_balance



    
    async def _process_opportunity(self, opportunity: Opportunity, user_id: str):
        """
        Process a single opportunity for a specific user.

        Evaluates the opportunity using the Provider, checks user control
        preferences, validates with RiskManager, filters by fee ratio,
        and either executes immediately or sends a notification.

        Args:
            opportunity: Opportunity to process
            user_id: User ID for whom this opportunity is being processed

        """
        logger.info(f"Processing opportunity for user {user_id}: {opportunity.strategy_name} - {opportunity.action}")

        logger.info(
            f"Opportunity detected: user={user_id}, strategy={opportunity.strategy_name}, "
            f"action={opportunity.action}, amount={opportunity.amount:.4f} SOL, "
            f"expected_profit={opportunity.expected_profit:.4f} SOL, "
            f"risk_level={opportunity.risk_level}"
        )

        # Define high-value as expected profit > 0.1 SOL
        if opportunity.expected_profit > 0.1:
            try:
                await self.notifier.send_high_value_opportunity(opportunity, user_id=user_id)
            except Exception as e:
                logger.error(f"Failed to send high-value opportunity notification: {e}")

        if hasattr(opportunity, 'details') and 'estimated_gas_fee' in opportunity.details:
            estimated_gas_fee = opportunity.details['estimated_gas_fee']

            if opportunity.expected_profit > 0:
                fee_ratio = estimated_gas_fee / opportunity.expected_profit

                if fee_ratio > 0.05:  # 5% threshold
                    logger.warning(
                        f"Skipping opportunity for user {user_id}: gas fees ({estimated_gas_fee:.6f} SOL) "
                        f"exceed 5% of expected profit ({opportunity.expected_profit:.6f} SOL) "
                        f"- ratio: {fee_ratio*100:.2f}%"
                    )
                    activity_logger.log_risk_rejection(
                        opportunity.strategy_name,
                        f"Gas fees too high: {fee_ratio*100:.2f}% of profit"
                    )
                    logger.info(
                        f"Fee-based filtering rejected opportunity",
                        extra={
                            'extra_context': {
                                'user_id': user_id,
                                'strategy': opportunity.strategy_name,
                                'action': opportunity.action,
                                'gas_fee': estimated_gas_fee,
                                'expected_profit': opportunity.expected_profit,
                                'fee_ratio_pct': f"{fee_ratio*100:.2f}",
                            }
                        }
                    )
                    return

        approved, rejection_reason = await self.risk_manager.validate_opportunity(opportunity)

        if not approved:
            logger.warning(
                f"Opportunity rejected by risk manager for user {user_id}: {rejection_reason}"
            )
            activity_logger.log_risk_rejection(opportunity.strategy_name, rejection_reason)

            logger.warning(
                f"Risk limit violation - opportunity rejected",
                extra={
                    'extra_context': {
                        'user_id': user_id,
                        'strategy': opportunity.strategy_name,
                        'action': opportunity.action,
                        'amount': opportunity.amount,
                        'expected_profit': opportunity.expected_profit,
                        'risk_level': opportunity.risk_level,
                        'rejection_reason': rejection_reason,
                    }
                }
            )

            await self.notifier.send_risk_rejection(opportunity, rejection_reason, user_id=user_id)
            return

        try:
            # Get user's wallet balance for position sizing
            current_balance = await self.wallet.get_balance(user_id)
        except Exception as e:
            logger.error(f"Failed to get balance for user {user_id} for position sizing: {e}")
            return

        position_size = self.risk_manager.calculate_position_size(opportunity, current_balance)

        original_amount = opportunity.amount
        opportunity.amount = min(position_size, opportunity.amount)

        logger.info(
            f"Position sizing for user {user_id}: original={original_amount:.4f} SOL, "
            f"adjusted={opportunity.amount:.4f} SOL (risk={opportunity.risk_level})"
        )

        decision = await self.evaluate_opportunity(opportunity)

        logger.info(
            f"Decision for user {user_id} - {opportunity.strategy_name}: {decision.action} "
            f"(confidence: {decision.confidence:.2f})"
        )
        logger.debug(f"Reasoning: {decision.reasoning}")

        activity_logger.log_opportunity_evaluation(
            strategy_name=opportunity.strategy_name,
            action=opportunity.action,
            decision=decision.action,
            confidence=decision.confidence,
        )

        if decision.action == "skip":
            logger.info(f"Skipping opportunity for user {user_id}: {decision.reasoning}")
            return

        elif decision.action == "execute":
            if self.user_control.should_execute(opportunity.strategy_name):
                logger.info(f"Queueing opportunity for user {user_id} execution (ALWAYS mode)")
                # Queue the trade instead of executing immediately
                async def execute_trade():
                    result = await self.execute_opportunity(opportunity, user_id)
                    await self.notifier.send_execution_result(result, user_id=user_id)
                    return result
                
                trade_id = await self.trade_queue.enqueue(user_id, opportunity, execute_trade)
                logger.info(f"Trade queued with ID: {trade_id}")
            else:
                logger.info(f"Sending notification for user {user_id} approval")
                await self._send_notification_and_wait(opportunity, user_id)

        elif decision.action == "notify":
            logger.info(f"Sending notification for user {user_id} approval")
            await self._send_notification_and_wait(opportunity, user_id)

    
    async def _send_notification_and_wait(self, opportunity: Opportunity, user_id: str):
        """
        Send notification and wait for user response.

        Args:
            opportunity: Opportunity to notify about
            user_id: User ID to send notification to
        """
        try:
            message_id = await self.notifier.send_opportunity(opportunity)
            response = await self.notifier.wait_for_response(message_id)

            logger.info(f"User {user_id} response: {response}")
            activity_logger.log_user_response(opportunity.strategy_name, response)

            if response == "yes":
                # Queue the trade instead of executing immediately
                async def execute_trade():
                    result = await self.execute_opportunity(opportunity, user_id)
                    await self.notifier.send_execution_result(result, user_id=user_id)
                    return result
                
                trade_id = await self.trade_queue.enqueue(user_id, opportunity, execute_trade)
                logger.info(f"Trade queued with ID: {trade_id} after user approval")

            elif response == "always":
                self.user_control.set_always(opportunity.strategy_name)
                # Queue the trade instead of executing immediately
                async def execute_trade():
                    result = await self.execute_opportunity(opportunity, user_id)
                    await self.notifier.send_execution_result(result, user_id=user_id)
                    return result
                
                trade_id = await self.trade_queue.enqueue(user_id, opportunity, execute_trade)
                logger.info(f"Trade queued with ID: {trade_id} after user approval (ALWAYS mode set)")

            elif response == "no":
                # Skip this opportunity
                logger.info(f"User {user_id} declined opportunity")

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}", exc_info=True)
            activity_logger.log_error(
                component="AgentLoop",
                error_type=type(e).__name__,
                error_message=f"Notification failed: {str(e)}",
                strategy=opportunity.strategy_name,
                user_id=user_id,
            )

    
    async def evaluate_opportunity(self, opportunity: Opportunity) -> Decision:
        """
        Use LLM to evaluate if opportunity should be executed.
        
        Args:
            opportunity: Opportunity to evaluate
        
        Returns:
            Decision object with action, reasoning, and confidence
        
        """
        try:
            decision = await self.provider.make_decision(opportunity)
            return decision
        except Exception as e:
            logger.error(f"Error evaluating opportunity: {e}", exc_info=True)
            # Default to notify on error
            return Decision(
                action="notify",
                reasoning=f"Error during evaluation: {str(e)}",
                confidence=0.0
            )
    
    async def execute_opportunity(self, opportunity: Opportunity, user_id: str) -> ExecutionResult:
        """
        Execute the opportunity by calling the strategy's execute method.

        Records trade execution in PerformanceTracker and updates strategy
        allocations based on performance. Uses the specific user's wallet
        for transaction signing.
        
        Handles execution failures gracefully - logs error, records failed trade,
        and returns ExecutionResult with error details. Failures for one user
        don't affect other users.

        Args:
            opportunity: Opportunity to execute
            user_id: User ID for whom to execute the trade

        Returns:
            ExecutionResult with success status, transaction hash, and profit

        """
        logger.info(f"Executing opportunity for user {user_id}: {opportunity.strategy_name} - {opportunity.action}")

        logger.info(
            f"Trade execution started",
            extra={
                'extra_context': {
                    'user_id': user_id,
                    'strategy': opportunity.strategy_name,
                    'action': opportunity.action,
                    'amount': opportunity.amount,
                    'expected_profit': opportunity.expected_profit,
                    'risk_level': opportunity.risk_level,
                }
            }
        )

        execution_start_time = time()

        try:
            # Get user's wallet
            try:
                user_wallet = await self.wallet.get_wallet(user_id)
                if not user_wallet:
                    error_msg = f"Wallet not found for user {user_id}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Failed to load wallet for user {user_id}: {e}", exc_info=True)
                raise Exception(f"Failed to load wallet: {str(e)}")

            # Find the strategy that generated this opportunity
            strategy = None
            for s in self.scanner.strategies:
                if s.get_name() == opportunity.strategy_name:
                    strategy = s
                    break

            if not strategy:
                error_msg = f"Strategy not found: {opportunity.strategy_name}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Temporarily set the strategy's wallet to the user's wallet
            # (This assumes strategies have a wallet attribute that can be swapped)
            original_wallet = getattr(strategy, 'wallet', None)
            if hasattr(strategy, 'wallet'):
                strategy.wallet = user_wallet

            try:
                # Call the strategy's execute method
                logger.info(f"Calling {strategy.get_name()}.execute() for user {user_id}")
                try:
                    execution_result = await strategy.execute(opportunity)
                    # execution_result is already an ExecutionResult object
                    result = execution_result
                except Exception as e:
                    logger.error(f"Strategy execution failed for user {user_id}: {e}", exc_info=True)
                    raise Exception(f"Strategy execution failed: {str(e)}")
            finally:
                # Restore original wallet
                if original_wallet is not None and hasattr(strategy, 'wallet'):
                    strategy.wallet = original_wallet

            execution_time_ms = int((time() - execution_start_time) * 1000)

            logger.info(
                f"Execution {'succeeded' if result.success else 'failed'} for user {user_id}: "
                f"profit={result.profit} SOL, tx={result.transaction_hash}"
            )

            logger.info(
                f"Trade execution completed",
                extra={
                    'extra_context': {
                        'user_id': user_id,
                        'strategy': opportunity.strategy_name,
                        'action': opportunity.action,
                        'success': result.success,
                        'expected_profit': opportunity.expected_profit,
                        'actual_profit': result.profit,
                        'variance': result.profit - opportunity.expected_profit,
                        'transaction_hash': result.transaction_hash or 'N/A',
                        'execution_time_ms': execution_time_ms,
                        'gas_fees': getattr(result, 'actual_gas_fee', 0.0),
                    }
                }
            )

            # Log execution
            activity_logger.log_execution(
                strategy_name=opportunity.strategy_name,
                action=opportunity.action,
                success=result.success,
                transaction_hash=result.transaction_hash,
                profit=result.profit,
                error=result.error,
            )

            # Record trade in performance tracker with user_id
            from agent.trading.performance import TradeRecord

            trade_record = TradeRecord(
                strategy_name=opportunity.strategy_name,
                timestamp=result.timestamp,
                expected_profit=opportunity.expected_profit,
                actual_profit=result.profit,
                transaction_hash=result.transaction_hash or "N/A",
                was_successful=result.success,
                error_message=result.error,
                gas_fees=getattr(result, 'actual_gas_fee', 0.0),
                execution_time_ms=execution_time_ms,
            )

            # TODO: Update PerformanceTracker.record_trade to accept user_id
            # For now, just record without user_id
            self.performance_tracker.record_trade(trade_record)

            self.risk_manager.record_trade_result(
                strategy_name=opportunity.strategy_name,
                profit=result.profit,
                was_successful=result.success
            )

            if opportunity.strategy_name == "airdrop_hunter":
                try:
                    await self.notifier.send_airdrop_discovery(opportunity.details)
                except Exception as e:
                    logger.error(f"Failed to send airdrop discovery notification: {e}")

            elif opportunity.strategy_name == "airdrop_claimer" and result.success:
                try:
                    await self.notifier.send_airdrop_claimed({
                        "protocol": opportunity.details.get("protocol_name", "Unknown"),
                        "token": opportunity.details.get("token", "???"),
                        "amount": opportunity.details.get("amount", 0),
                        "value_usd": opportunity.details.get("amount", 0) * 0.5,  # Rough estimate
                        "transaction_hash": result.transaction_hash
                    })
                except Exception as e:
                    logger.error(f"Failed to send airdrop claimed notification: {e}")

            return result

        except Exception as e:
            # Comprehensive error handling for trade execution failures
            logger.error(f"Error executing opportunity for user {user_id}: {e}", exc_info=True)

            logger.error(
                f"Trade execution failed with error",
                extra={
                    'extra_context': {
                        'user_id': user_id,
                        'strategy': opportunity.strategy_name,
                        'action': opportunity.action,
                        'amount': opportunity.amount,
                        'expected_profit': opportunity.expected_profit,
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                    }
                },
                exc_info=True
            )

            execution_time_ms = int((time() - execution_start_time) * 1000)

            # Create failed execution result
            result = ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now()
            )

            # Log failed execution
            activity_logger.log_execution(
                strategy_name=opportunity.strategy_name,
                action=opportunity.action,
                success=False,
                error=str(e),
            )

            # Record failed trade
            from agent.trading.performance import TradeRecord

            trade_record = TradeRecord(
                strategy_name=opportunity.strategy_name,
                timestamp=datetime.now(),
                expected_profit=opportunity.expected_profit,
                actual_profit=0.0,
                transaction_hash="N/A",
                was_successful=False,
                error_message=str(e),
                gas_fees=0.0,
                execution_time_ms=execution_time_ms,
            )

            # TODO: Update PerformanceTracker.record_trade to accept user_id
            self.performance_tracker.record_trade(trade_record)

            self.risk_manager.record_trade_result(
                strategy_name=opportunity.strategy_name,
                profit=0.0,
                was_successful=False
            )
            
            # Send failure notification to affected user only
            try:
                # TODO: Update notifier to support per-user messages
                # For now, log the notification
                failure_message = (
                    f"❌ Trade Execution Failed\n\n"
                    f"Strategy: {opportunity.strategy_name}\n"
                    f"Action: {opportunity.action}\n"
                    f"Error: {str(e)}\n\n"
                    f"Your funds are safe. The bot will continue monitoring for opportunities."
                )
                logger.info(f"Would send to user {user_id}: {failure_message}")
                # await self.notifier.send_message_to_user(user_id, failure_message)
            except Exception as notify_error:
                logger.error(f"Failed to send failure notification to user {user_id}: {notify_error}")

            return result

    
    def handle_error(self, error: Exception):
        """
        Log error and determine if shutdown is needed.

        Implements graceful error recovery - errors are logged with full
        context. Critical errors (wallet failure) trigger shutdown.

        Args:
            error: Exception that occurred

        """
        is_critical = self._is_critical_error(error)

        if is_critical:
            logger.critical(
                f"CRITICAL ERROR in agent loop: {error}",
                exc_info=True,
                extra={
                    "error_type": type(error).__name__,
                    "last_scan_time": self._last_scan_time,
                }
            )

            activity_logger.log_error(
                component="AgentLoop",
                error_type=type(error).__name__,
                error_message=f"CRITICAL: {str(error)}",
                last_scan_time=self._last_scan_time.isoformat() if self._last_scan_time else None,
            )

            # Stop the agent loop
            logger.critical("Shutting down agent due to critical error")
            self.stop()

            # Attempt to notify operator
            try:
                import asyncio
                asyncio.create_task(
                    self.notifier.send_message(
                        f"🚨 CRITICAL ERROR - Agent shutting down:\n{str(error)}"
                    )
                )
            except Exception as notify_error:
                logger.error(f"Failed to send critical error notification: {notify_error}")
        else:
            # Non-critical error - log and continue
            logger.error(
                f"Error in agent loop: {error}",
                exc_info=True,
                extra={
                    "error_type": type(error).__name__,
                    "last_scan_time": self._last_scan_time,
                }
            )

            activity_logger.log_error(
                component="AgentLoop",
                error_type=type(error).__name__,
                error_message=str(error),
                last_scan_time=self._last_scan_time.isoformat() if self._last_scan_time else None,
            )

            logger.info("Continuing operation after error...")

    def _is_critical_error(self, error: Exception) -> bool:
        """
        Determine if an error is critical and requires shutdown.

        Critical errors include:
        - Wallet access failures
        - Private key errors
        - Persistent RPC failures
        - Database corruption

        Args:
            error: Exception to check

        Returns:
            True if error is critical

        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        critical_indicators = [
            'wallet',
            'private key',
            'keypair',
            'permission denied',
            'access denied',
            'authentication failed',
            'database',
            'corruption',
        ]

        for indicator in critical_indicators:
            if indicator in error_str or indicator in error_type:
                return True

        critical_types = [
            'PermissionError',
            'FileNotFoundError',  # If wallet file is missing
        ]

        if error_type in [t.lower() for t in critical_types]:
            if 'wallet' in error_str or 'key' in error_str or '.env' in error_str:
                return True

        return False
    
    def get_status(self) -> dict:
        """
        Get current agent status.
        
        Returns:
            Dictionary with agent status information including performance metrics
        """
        metrics = self.performance_tracker.get_metrics()
        trade_queue_stats = self.trade_queue.get_queue_stats()
        
        return {
            "running": self._running,
            "last_scan_time": self._last_scan_time.isoformat() if self._last_scan_time else None,
            "scan_interval": self.scan_interval,
            "strategies_count": len(self.scanner.strategies),
            "active_positions": len(self.risk_manager.get_active_positions()),
            "total_exposure": self.risk_manager.get_total_exposure(),
            "total_max_loss": self.risk_manager.get_total_max_loss(),
            "trade_queue": trade_queue_stats,
            "performance": {
                "total_profit": metrics.total_profit,
                "total_trades": metrics.total_trades,
                "win_rate": metrics.win_rate,
                "profit_by_strategy": metrics.profit_by_strategy,
                "performance_fee": metrics.performance_fee_collected,
            }
        }
    
    async def _monitor_positions(self):
        """
        Monitor active positions for stop-loss conditions.
        
        Checks all positions and automatically exits any that have
        hit their stop-loss thresholds.
        
        """
        positions_to_exit = self.risk_manager.monitor_positions()
        
        if not positions_to_exit:
            return
        
        logger.warning(f"Found {len(positions_to_exit)} positions requiring stop-loss exit")
        
        for position_id, reason in positions_to_exit:
            try:
                position = self.risk_manager.get_position(position_id)
                
                if position is None:
                    logger.error(f"Position {position_id} not found for exit")
                    continue
                
                logger.warning(
                    f"Executing stop-loss exit for position {position_id}: {reason}"
                )
                
                await self._exit_position(position, reason)
                
            except Exception as e:
                logger.error(
                    f"Error exiting position {position_id}: {e}",
                    exc_info=True
                )
                continue
    
    async def _exit_position(self, position, reason: str):
        """
        Exit a position due to stop-loss trigger.
        
        Args:
            position: Position object to exit
            reason: Reason for exit
        
        """
        logger.info(
            f"Exiting position {position.position_id} for {position.strategy_name}: {reason}"
        )
        
        try:
            strategy = None
            for s in self.scanner.strategies:
                if s.get_name() == position.strategy_name:
                    strategy = s
                    break
            
            if strategy and hasattr(strategy, 'exit_position'):
                logger.info(f"Calling {strategy.get_name()}.exit_position()")
                try:
                    await strategy.exit_position(position)
                except Exception as e:
                    logger.warning(f"Strategy exit failed: {e}, using fallback")
            
            closed_position = self.risk_manager.close_position(
                position.position_id,
                exit_price=position.current_price
            )
            
            if closed_position:
                loss_amount = (position.entry_price - position.current_price) * position.amount / position.entry_price
                
                activity_logger.log_stop_loss_exit(
                    position_id=position.position_id,
                    strategy_name=position.strategy_name,
                    loss_amount=loss_amount,
                    reason=reason,
                )
                
                await self.notifier.send_stop_loss_exit(closed_position, reason)
                
                logger.info(
                    f"Position {position.position_id} exited successfully"
                )
            else:
                logger.error(f"Failed to close position {position.position_id}")
        
        except Exception as e:
            logger.error(f"Error during position exit: {e}", exc_info=True)
            activity_logger.log_error(
                component="AgentLoop",
                error_type=type(e).__name__,
                error_message=f"Position exit failed: {str(e)}",
                position_id=position.position_id,
                strategy=position.strategy_name,
            )
            raise


    def _calculate_next_scan_interval(self) -> float:
        """
        Calculate the next scan interval based on adaptive logic.

        Rules:
        - Minimum 5 seconds between scans (rate limiting)
        - Increase by 50% on rate limit detection
        - Increase to 30 seconds after 10 consecutive empty scans

        Returns:
            Next scan interval in seconds

        """
        # Start with base interval
        interval = self._current_scan_interval

        # Apply rate limit increase if detected
        if self._rate_limit_detected:
            interval = interval * self.RATE_LIMIT_INCREASE_FACTOR
            logger.warning(
                f"Rate limit detected, increasing scan interval by 50% to {interval}s"
            )
            self._rate_limit_detected = False

        elif self._empty_scan_count >= self.EMPTY_SCAN_THRESHOLD:
            interval = self.EMPTY_SCAN_INTERVAL
            logger.info(
                f"No opportunities found for {self._empty_scan_count} consecutive scans, "
                f"increasing interval to {interval}s"
            )

        interval = max(interval, self.MIN_SCAN_INTERVAL)

        self._current_scan_interval = interval

        return interval

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if an error is a rate limit error.

        Args:
            error: Exception to check

        Returns:
            True if error is rate limit related
        """
        error_str = str(error).lower()
        rate_limit_indicators = [
            'rate limit',
            'too many requests',
            '429',
            'quota exceeded',
            'throttle',
        ]

        return any(indicator in error_str for indicator in rate_limit_indicators)
