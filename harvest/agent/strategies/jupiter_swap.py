"""Jupiter Swap Strategy - Finds profitable token swap opportunities."""

import logging
from typing import List, Optional
from datetime import datetime

from agent.trading.scanner import Strategy, Opportunity
from agent.services.notifier import ExecutionResult
from integrations.solana.jupiter import JupiterIntegration
from integrations.solana.orca import OrcaIntegration

logger = logging.getLogger(__name__)


class JupiterSwapStrategy(Strategy):
    """
    Strategy for executing token swaps via Jupiter aggregator.
    
    Scans for profitable swap opportunities and executes them.
    Supports arbitrage detection across Jupiter and Orca.
    """
    
    def __init__(
        self,
        rpc_client,
        wallet_manager,
        executor,
        min_profit_threshold: float = 0.01,
        slippage_bps: int = 100,
        max_price_impact_pct: float = 2.0,
        high_volatility_slippage_bps: int = 200
    ):
        """
        Initialize Jupiter swap strategy.
        
        Args:
            rpc_client: Helius RPC client
            wallet_manager: Wallet manager instance
            executor: Transaction executor for executing swaps
            min_profit_threshold: Minimum profit in SOL to consider (default 0.01)
            slippage_bps: Slippage tolerance in basis points (default 100 = 1%)
            max_price_impact_pct: Maximum price impact percentage (default 2.0%)
            high_volatility_slippage_bps: Slippage for high volatility (default 200 = 2%)
        """
        self.rpc_client = rpc_client
        self.wallet_manager = wallet_manager
        self.executor = executor
        self.min_profit_threshold = min_profit_threshold
        self.slippage_bps = slippage_bps
        self.max_price_impact_pct = max_price_impact_pct
        self.high_volatility_slippage_bps = high_volatility_slippage_bps
        self.jupiter = JupiterIntegration(
            rpc_client,
            wallet_manager.get_public_key()
        )
        self.orca = OrcaIntegration(
            rpc_client,
            wallet_manager.get_public_key()
        )
        
        # Token mint addresses
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
        self.USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # Estimated gas fee per transaction (in SOL)
        self.ESTIMATED_GAS_FEE = 0.000005
        
        # Track slippage failures for reporting
        self.slippage_failures = []
        
        logger.info(
            f"Initialized JupiterSwapStrategy with min profit {min_profit_threshold} SOL, "
            f"slippage {slippage_bps} bps, max price impact {max_price_impact_pct}%"
        )
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "jupiter_swap"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for profitable swap opportunities.
        
        Checks:
        - Wallet balance validation
        - Arbitrage opportunities across Jupiter and Orca
        - Net profit calculation including all fees
        
        Returns:
            List of swap opportunities
        
        """
        opportunities = []
        
        try:
            # Get wallet balance
            balance = self.wallet_manager.get_balance()
            
            if balance < 0.1:  # Need at least 0.1 SOL
                logger.debug("Insufficient balance for swaps")
                return opportunities
            
            logger.info(f"Scanning for swap opportunities with balance {balance:.4f} SOL")
            
            # Check for arbitrage opportunities
            arb_opportunity = self._check_arbitrage(balance)
            if arb_opportunity:
                opportunities.append(arb_opportunity)
        
        except Exception as e:
            logger.error(f"Error scanning Jupiter swaps: {e}", exc_info=True)
        
        return opportunities
    
    def _check_arbitrage(self, balance: float) -> Optional[Opportunity]:
        """
        Check for arbitrage opportunities across Jupiter and Orca.
        
        Scans for profitable SOL -> USDC -> SOL arbitrage by:
        1. Querying prices from both Jupiter and Orca
        2. Calculating net profit after all fees
        3. Checking price impact and slippage protection
        4. Creating opportunity if profit exceeds threshold
        
        Args:
            balance: Current wallet balance in SOL
        
        Returns:
            Opportunity if profitable arbitrage found, None otherwise
        
        """
        try:
            # Calculate swap amount (10% of balance or max 1 SOL)
            swap_amount = min(balance * 0.1, 1.0)
            
            logger.debug(f"Checking arbitrage for {swap_amount:.4f} SOL")
            
            # Get quotes from Jupiter for SOL -> USDC -> SOL
            try:
                jupiter_route = self.jupiter.get_quote(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    swap_amount,
                    self._get_current_slippage_bps()
                )
                
                # Check price impact
                if jupiter_route.price_impact > self.max_price_impact_pct:
                    logger.debug(
                        f"Jupiter route price impact too high: {jupiter_route.price_impact:.2f}% "
                        f"(max: {self.max_price_impact_pct}%)"
                    )
                    jupiter_profit = -1.0
                    jupiter_sol_back = 0.0
                else:
                    jupiter_usdc_out = jupiter_route.output_amount / 1e6
                    jupiter_sol_back = self.jupiter.get_best_price(
                        self.USDC_MINT,
                        self.SOL_MINT,
                        jupiter_usdc_out
                    )
                    jupiter_profit = jupiter_sol_back - swap_amount
                    
                    logger.debug(
                        f"Jupiter route: {swap_amount:.4f} SOL -> {jupiter_usdc_out:.2f} USDC -> "
                        f"{jupiter_sol_back:.4f} SOL (profit: {jupiter_profit:.6f}, "
                        f"impact: {jupiter_route.price_impact:.2f}%)"
                    )
            except Exception as e:
                logger.debug(f"Jupiter quote failed: {e}")
                jupiter_profit = -1.0
                jupiter_sol_back = 0.0
            
            # Get quotes from Orca for SOL -> USDC -> SOL
            try:
                orca_quote = self.orca.get_quote(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    swap_amount,
                    self._get_current_slippage_bps()
                )
                
                # Check price impact
                if orca_quote.price_impact > self.max_price_impact_pct:
                    logger.debug(
                        f"Orca route price impact too high: {orca_quote.price_impact:.2f}% "
                        f"(max: {self.max_price_impact_pct}%)"
                    )
                    orca_profit = -1.0
                    orca_sol_back = 0.0
                else:
                    orca_usdc_out = orca_quote.output_amount / 1e6
                    orca_sol_back = self.orca.get_price(
                        self.USDC_MINT,
                        self.SOL_MINT,
                        orca_usdc_out
                    )
                    orca_profit = orca_sol_back - swap_amount
                    
                    logger.debug(
                        f"Orca route: {swap_amount:.4f} SOL -> {orca_usdc_out:.2f} USDC -> "
                        f"{orca_sol_back:.4f} SOL (profit: {orca_profit:.6f}, "
                        f"impact: {orca_quote.price_impact:.2f}%)"
                    )
            except Exception as e:
                logger.debug(f"Orca quote failed: {e}")
                orca_profit = -1.0
                orca_sol_back = 0.0
            
            # Check for cross-DEX arbitrage (buy on one, sell on other)
            try:
                # Jupiter buy, Orca sell
                jupiter_usdc = self.jupiter.get_best_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    swap_amount
                )
                orca_sol = self.orca.get_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    jupiter_usdc
                )
                cross_profit_1 = orca_sol - swap_amount
                
                # Orca buy, Jupiter sell
                orca_usdc = self.orca.get_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    swap_amount
                )
                jupiter_sol = self.jupiter.get_best_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    orca_usdc
                )
                cross_profit_2 = jupiter_sol - swap_amount
                
                logger.debug(
                    f"Cross-DEX arbitrage: Jupiter->Orca profit={cross_profit_1:.6f}, "
                    f"Orca->Jupiter profit={cross_profit_2:.6f}"
                )
            except Exception as e:
                logger.debug(f"Cross-DEX arbitrage check failed: {e}")
                cross_profit_1 = -1.0
                cross_profit_2 = -1.0
            
            # Find best opportunity
            best_profit = max(jupiter_profit, orca_profit, cross_profit_1, cross_profit_2)
            
            if best_profit == jupiter_profit:
                route_type = "jupiter_arb"
                expected_output = jupiter_sol_back
                path = "SOL -> USDC -> SOL (Jupiter)"
            elif best_profit == orca_profit:
                route_type = "orca_arb"
                expected_output = orca_sol_back
                path = "SOL -> USDC -> SOL (Orca)"
            elif best_profit == cross_profit_1:
                route_type = "cross_arb_jupiter_orca"
                expected_output = orca_sol
                path = "SOL -> USDC (Jupiter) -> SOL (Orca)"
            else:
                route_type = "cross_arb_orca_jupiter"
                expected_output = jupiter_sol
                path = "SOL -> USDC (Orca) -> SOL (Jupiter)"
            
            # Calculate net profit after fees
            # Two transactions for arbitrage (buy + sell)
            estimated_gas_fees = self.ESTIMATED_GAS_FEE * 2
            
            # DEX fees are already included in the quotes
            net_profit = best_profit - estimated_gas_fees
            
            logger.debug(
                f"Best route: {path}, gross profit: {best_profit:.6f}, "
                f"gas fees: {estimated_gas_fees:.6f}, net profit: {net_profit:.6f}"
            )
            
            # Create opportunity if profitable
            if net_profit > self.min_profit_threshold:
                opportunity = Opportunity(
                    strategy_name=self.get_name(),
                    action="arbitrage",
                    amount=swap_amount,
                    expected_profit=net_profit,
                    risk_level="medium",
                    details={
                        "type": route_type,
                        "path": path,
                        "input_amount": swap_amount,
                        "expected_output": expected_output,
                        "gross_profit": best_profit,
                        "estimated_gas_fee": estimated_gas_fees,
                        "net_profit": net_profit,
                    },
                    timestamp=datetime.now()
                )
                
                logger.info(
                    f"Found arbitrage opportunity: {path}, "
                    f"net profit {net_profit:.6f} SOL"
                )
                
                return opportunity
            else:
                logger.debug(
                    f"No profitable arbitrage found (best net profit: {net_profit:.6f} SOL)"
                )
        
        except Exception as e:
            logger.error(f"Error checking arbitrage: {e}", exc_info=True)
        
        return None
    
    def _get_current_slippage_bps(self) -> int:
        """
        Get current slippage tolerance based on market conditions.
        
        Returns slippage in basis points:
        - Normal conditions: 100 bps (1%)
        - High volatility: 200 bps (2%)
        
        Returns:
            Slippage tolerance in basis points
        
        """
        # Check for high volatility indicators
        # In production, this would check actual market volatility metrics
        # For now, use default slippage
        is_high_volatility = self._detect_high_volatility()
        
        if is_high_volatility:
            logger.info(
                f"High volatility detected, using increased slippage: "
                f"{self.high_volatility_slippage_bps} bps"
            )
            return self.high_volatility_slippage_bps
        
        return self.slippage_bps
    
    def _detect_high_volatility(self) -> bool:
        """
        Detect if market is experiencing high volatility.
        
        In production, this would check:
        - Recent price movements
        - Trading volume spikes
        - Network congestion
        
        Returns:
            True if high volatility detected
        
        """
        # Placeholder - in production, implement actual volatility detection
        # For now, always return False (normal volatility)
        return False
    
    def _record_slippage_failure(self, opportunity: Opportunity, error: str):
        """
        Record a slippage failure for tracking and analysis.
        
        Args:
            opportunity: Opportunity that failed due to slippage
            error: Error message describing the failure
        
        """
        failure_record = {
            "timestamp": datetime.now(),
            "strategy": opportunity.strategy_name,
            "path": opportunity.details.get("path", "unknown"),
            "amount": opportunity.amount,
            "expected_profit": opportunity.expected_profit,
            "error": error,
        }
        
        self.slippage_failures.append(failure_record)
        
        logger.warning(
            f"Recorded slippage failure: {opportunity.details.get('path')} - {error}"
        )
    
    def get_slippage_failures(self) -> list:
        """
        Get list of recorded slippage failures.
        
        Returns:
            List of slippage failure records
        
        """
        return self.slippage_failures
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute a swap opportunity.
        
        Steps:
        1. Validate quote freshness (revalidate before execution)
        2. Create swap transaction via Jupiter/Orca integration
        3. Execute transaction via TransactionExecutor
        4. Verify output tokens received
        5. Calculate actual profit vs expected
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            route_type = opportunity.details.get("type", "")
            path = opportunity.details.get("path", "")
            input_amount = opportunity.details.get("input_amount", 0.0)
            
            logger.info(f"Executing Jupiter swap: {path}")
            
            # Step 1: Validate quote freshness (revalidate before execution)
            logger.debug("Revalidating quote before execution...")
            
            # Get initial balance
            initial_balance = await self.wallet_manager.get_balance()
            
            # Revalidate the opportunity to ensure prices haven't changed
            fresh_opportunity = self._revalidate_opportunity(opportunity)
            
            if not fresh_opportunity:
                logger.warning("Quote no longer valid, aborting execution")
                return ExecutionResult(
                    success=False,
                    transaction_hash=None,
                    profit=0.0,
                    error="Quote validation failed - prices changed",
                    timestamp=datetime.now()
                )
            
            # Check if profit is still above threshold after revalidation
            if fresh_opportunity.expected_profit < self.min_profit_threshold:
                logger.warning(
                    f"Profit dropped below threshold after revalidation: "
                    f"{fresh_opportunity.expected_profit:.6f} < {self.min_profit_threshold}"
                )
                return ExecutionResult(
                    success=False,
                    transaction_hash=None,
                    profit=0.0,
                    error="Profit below threshold after revalidation",
                    timestamp=datetime.now()
                )
            
            logger.info(f"Quote revalidated, proceeding with execution")
            
            # Step 2 & 3: Create and execute swap transaction
            if "cross_arb" in route_type:
                # Cross-DEX arbitrage requires sequential execution
                result = await self._execute_cross_dex_arbitrage(fresh_opportunity)
            else:
                # Single-DEX arbitrage
                result = await self._execute_single_dex_swap(fresh_opportunity)
            
            # Record slippage failures
            if not result.success and "slippage" in result.error.lower():
                self._record_slippage_failure(fresh_opportunity, result.error)
            
            # Step 4 & 5: Verify output tokens and calculate actual profit
            if result.success:
                final_balance = await self.wallet_manager.get_balance()
                actual_profit = final_balance - initial_balance
                
                logger.info(
                    f"Swap executed successfully: "
                    f"expected profit={fresh_opportunity.expected_profit:.6f}, "
                    f"actual profit={actual_profit:.6f}"
                )
                
                # Update result with actual profit
                result.profit = actual_profit
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing Jupiter swap: {e}", exc_info=True)
            
            # Check if error is slippage-related
            if "slippage" in str(e).lower():
                self._record_slippage_failure(opportunity, str(e))
            
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now()
            )
    
    def _revalidate_opportunity(self, opportunity: Opportunity) -> Optional[Opportunity]:
        """
        Revalidate an opportunity by fetching fresh quotes.
        
        Args:
            opportunity: Original opportunity to revalidate
        
        Returns:
            Fresh opportunity with updated quotes, or None if validation fails
        
        """
        try:
            route_type = opportunity.details.get("type", "")
            input_amount = opportunity.details.get("input_amount", 0.0)
            
            # Get fresh quotes based on route type
            if route_type == "jupiter_arb":
                usdc_out = self.jupiter.get_best_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    input_amount
                )
                sol_back = self.jupiter.get_best_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    usdc_out
                )
                gross_profit = sol_back - input_amount
                
            elif route_type == "orca_arb":
                usdc_out = self.orca.get_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    input_amount
                )
                sol_back = self.orca.get_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    usdc_out
                )
                gross_profit = sol_back - input_amount
                
            elif route_type == "cross_arb_jupiter_orca":
                usdc_out = self.jupiter.get_best_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    input_amount
                )
                sol_back = self.orca.get_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    usdc_out
                )
                gross_profit = sol_back - input_amount
                
            elif route_type == "cross_arb_orca_jupiter":
                usdc_out = self.orca.get_price(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    input_amount
                )
                sol_back = self.jupiter.get_best_price(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    usdc_out
                )
                gross_profit = sol_back - input_amount
            else:
                logger.error(f"Unknown route type: {route_type}")
                return None
            
            # Calculate net profit
            estimated_gas_fees = self.ESTIMATED_GAS_FEE * 2
            net_profit = gross_profit - estimated_gas_fees
            
            # Create fresh opportunity
            fresh_opportunity = Opportunity(
                strategy_name=opportunity.strategy_name,
                action=opportunity.action,
                amount=input_amount,
                expected_profit=net_profit,
                risk_level=opportunity.risk_level,
                details={
                    **opportunity.details,
                    "expected_output": sol_back,
                    "gross_profit": gross_profit,
                    "net_profit": net_profit,
                    "revalidated": True,
                },
                timestamp=datetime.now()
            )
            
            logger.debug(
                f"Revalidated opportunity: gross profit={gross_profit:.6f}, "
                f"net profit={net_profit:.6f}"
            )
            
            return fresh_opportunity
        
        except Exception as e:
            logger.error(f"Failed to revalidate opportunity: {e}")
            return None
    
    async def _execute_single_dex_swap(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute a single-DEX arbitrage (two swaps on same DEX).
        
        Includes fallback to alternate DEX if primary DEX fails.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            route_type = opportunity.details.get("type", "")
            input_amount = opportunity.details.get("input_amount", 0.0)
            
            # Determine which DEX to use
            if route_type == "jupiter_arb":
                primary_dex = self.jupiter
                primary_name = "Jupiter"
                fallback_dex = self.orca
                fallback_name = "Orca"
            elif route_type == "orca_arb":
                primary_dex = self.orca
                primary_name = "Orca"
                fallback_dex = self.jupiter
                fallback_name = "Jupiter"
            else:
                raise Exception(f"Invalid single-DEX route type: {route_type}")
            
            logger.info(f"Executing {primary_name} arbitrage: SOL -> USDC -> SOL")
            
            # Try primary DEX first
            result = await self._execute_two_leg_swap(
                primary_dex,
                primary_name,
                input_amount,
                opportunity.expected_profit
            )
            
            # If primary DEX failed, try fallback
            if not result.success and "API" in result.error:
                logger.warning(
                    f"{primary_name} API failed: {result.error}. "
                    f"Falling back to {fallback_name}..."
                )
                
                result = await self._execute_two_leg_swap(
                    fallback_dex,
                    fallback_name,
                    input_amount,
                    opportunity.expected_profit
                )
                
                if result.success:
                    logger.info(f"Fallback to {fallback_name} successful")
                else:
                    logger.error(f"Fallback to {fallback_name} also failed: {result.error}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing single-DEX swap: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def _execute_two_leg_swap(
        self,
        dex,
        dex_name: str,
        input_amount: float,
        expected_profit: float
    ) -> ExecutionResult:
        """
        Execute a two-leg swap on a single DEX.
        
        Args:
            dex: DEX integration instance (Jupiter or Orca)
            dex_name: Name of the DEX for logging
            input_amount: Amount of SOL to swap
            expected_profit: Expected profit from the swap
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            # Get current slippage tolerance
            current_slippage = self._get_current_slippage_bps()
            
            # First leg: SOL -> USDC
            logger.debug(
                f"Creating first leg transaction on {dex_name}: SOL -> USDC "
                f"(slippage: {current_slippage} bps)"
            )
            
            try:
                tx1 = dex.create_swap_transaction(
                    self.SOL_MINT,
                    self.USDC_MINT,
                    input_amount,
                    current_slippage
                )
            except Exception as e:
                logger.error(f"{dex_name} API failed to create transaction: {e}")
                return ExecutionResult(
                    success=False,
                    transaction_hash=None,
                    profit=0.0,
                    error=f"{dex_name} API failed: {str(e)}",
                    timestamp=datetime.now()
                )
            
            result1 = await self.executor.execute_transaction(
                tx1,
                self.get_name(),
                expected_profit=0.0  # Intermediate step, no profit yet
            )
            
            if not result1.success:
                logger.error(f"First leg failed on {dex_name}: {result1.error}")
                return result1
            
            logger.info(f"First leg successful on {dex_name}: {result1.transaction_hash}")
            
            # Get USDC balance for second leg
            # In production, query actual USDC balance
            # For now, estimate from balance change
            usdc_amount = input_amount * 100  # Rough estimate: 1 SOL ~ 100 USDC
            
            # Second leg: USDC -> SOL
            logger.debug(
                f"Creating second leg transaction on {dex_name}: USDC -> SOL "
                f"(slippage: {current_slippage} bps)"
            )
            
            try:
                tx2 = dex.create_swap_transaction(
                    self.USDC_MINT,
                    self.SOL_MINT,
                    usdc_amount,
                    current_slippage
                )
            except Exception as e:
                logger.error(f"{dex_name} API failed to create second transaction: {e}")
                return ExecutionResult(
                    success=False,
                    transaction_hash=result1.transaction_hash,
                    profit=result1.profit,
                    error=f"{dex_name} API failed on second leg: {str(e)}",
                    timestamp=datetime.now()
                )
            
            result2 = await self.executor.execute_transaction(
                tx2,
                self.get_name(),
                expected_profit=expected_profit
            )
            
            if not result2.success:
                logger.error(f"Second leg failed on {dex_name}: {result2.error}")
                return result2
            
            logger.info(f"Second leg successful on {dex_name}: {result2.transaction_hash}")
            
            # Return combined result
            return ExecutionResult(
                success=True,
                transaction_hash=f"{result1.transaction_hash},{result2.transaction_hash}",
                profit=result2.profit,
                error=None,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Error executing two-leg swap on {dex_name}: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def _execute_cross_dex_arbitrage(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute cross-DEX arbitrage with sequential legs.
        
        Steps:
        1. Execute first leg (buy on DEX A)
        2. Verify first leg success before second leg
        3. Execute second leg (sell on DEX B) only if first succeeds
        4. Calculate net profit after both legs
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            route_type = opportunity.details.get("type", "")
            input_amount = opportunity.details.get("input_amount", 0.0)
            
            logger.info(f"Executing cross-DEX arbitrage: {route_type}")
            
            # Determine DEX routing
            if route_type == "cross_arb_jupiter_orca":
                first_dex = self.jupiter
                first_dex_name = "Jupiter"
                second_dex = self.orca
                second_dex_name = "Orca"
            elif route_type == "cross_arb_orca_jupiter":
                first_dex = self.orca
                first_dex_name = "Orca"
                second_dex = self.jupiter
                second_dex_name = "Jupiter"
            else:
                raise Exception(f"Invalid cross-DEX route type: {route_type}")
            
            # Get current slippage tolerance
            current_slippage = self._get_current_slippage_bps()
            
            # Step 1: Execute first leg (SOL -> USDC on DEX A)
            logger.info(
                f"Executing first leg: SOL -> USDC on {first_dex_name} "
                f"(slippage: {current_slippage} bps)"
            )
            
            tx1 = first_dex.create_swap_transaction(
                self.SOL_MINT,
                self.USDC_MINT,
                input_amount,
                current_slippage
            )
            
            result1 = await self.executor.execute_transaction(
                tx1,
                self.get_name(),
                expected_profit=0.0  # Intermediate step, no profit yet
            )
            
            # Step 2: Verify first leg success before proceeding
            if not result1.success:
                logger.error(
                    f"First leg failed on {first_dex_name}: {result1.error}. "
                    f"Aborting arbitrage."
                )
                return ExecutionResult(
                    success=False,
                    transaction_hash=result1.transaction_hash,
                    profit=0.0,
                    error=f"First leg failed: {result1.error}",
                    timestamp=datetime.now()
                )
            
            logger.info(
                f"First leg successful on {first_dex_name}: {result1.transaction_hash}"
            )
            
            # Get USDC balance for second leg
            # In production, query actual USDC balance from wallet
            # For now, estimate from quote
            usdc_amount = opportunity.details.get("expected_output", 0.0)
            
            # Step 3: Execute second leg only if first succeeded (USDC -> SOL on DEX B)
            logger.info(
                f"Executing second leg: USDC -> SOL on {second_dex_name} "
                f"(slippage: {current_slippage} bps)"
            )
            
            tx2 = second_dex.create_swap_transaction(
                self.USDC_MINT,
                self.SOL_MINT,
                usdc_amount,
                current_slippage
            )
            
            result2 = await self.executor.execute_transaction(
                tx2,
                self.get_name(),
                expected_profit=opportunity.expected_profit
            )
            
            if not result2.success:
                logger.error(
                    f"Second leg failed on {second_dex_name}: {result2.error}. "
                    f"First leg completed but arbitrage incomplete."
                )
                return ExecutionResult(
                    success=False,
                    transaction_hash=f"{result1.transaction_hash},{result2.transaction_hash}",
                    profit=result1.profit,  # Only profit from first leg (likely negative)
                    error=f"Second leg failed: {result2.error}",
                    timestamp=datetime.now()
                )
            
            logger.info(
                f"Second leg successful on {second_dex_name}: {result2.transaction_hash}"
            )
            
            # Step 4: Calculate net profit after both legs
            # The executor already calculated actual profit based on balance changes
            net_profit = result2.profit
            
            logger.info(
                f"Cross-DEX arbitrage completed: "
                f"{first_dex_name} -> {second_dex_name}, "
                f"expected profit={opportunity.expected_profit:.6f}, "
                f"actual profit={net_profit:.6f}"
            )
            
            # Return combined result
            return ExecutionResult(
                success=True,
                transaction_hash=f"{result1.transaction_hash},{result2.transaction_hash}",
                profit=net_profit,
                error=None,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Error executing cross-DEX arbitrage: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now()
            )
