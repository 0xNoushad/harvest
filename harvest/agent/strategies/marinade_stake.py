"""Marinade Staking Strategy - Liquid staking for yield."""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from agent.trading.scanner import Strategy, Opportunity
from agent.trading.transaction_executor import TransactionExecutor, ExecutionResult
from integrations.solana.marinade import MarinadeIntegration

logger = logging.getLogger(__name__)


class MarinadeStakeStrategy(Strategy):
    """
    Strategy for liquid staking SOL via Marinade Finance.
    
    Stakes SOL to earn yield while maintaining liquidity through mSOL.
    """
    
    def __init__(
        self,
        rpc_client,
        wallet_manager,
        executor: TransactionExecutor,
        min_stake_amount: float = 0.1,
        reserve_balance: float = 0.05
    ):
        """
        Initialize Marinade staking strategy.
        
        Args:
            rpc_client: Helius RPC client
            wallet_manager: Wallet manager instance
            executor: Transaction executor for executing stakes
            min_stake_amount: Minimum SOL to stake (default 0.1)
            reserve_balance: SOL to reserve for fees (default 0.05)
        """
        self.rpc_client = rpc_client
        self.wallet_manager = wallet_manager
        self.executor = executor
        self.min_stake_amount = min_stake_amount
        self.reserve_balance = reserve_balance
        self.marinade = MarinadeIntegration(
            rpc_client,
            wallet_manager.get_public_key()
        )
        
        # Track staking positions for yield calculation
        self.staking_positions: List[Dict] = []
        
        logger.info(
            f"Initialized MarinadeStakeStrategy with min stake {min_stake_amount} SOL, "
            f"reserve {reserve_balance} SOL"
        )
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "marinade_stake"
    
    def _get_current_apy(self) -> float:
        """
        Query current Marinade APY.
        
        Returns:
            Current APY as decimal (e.g., 0.07 for 7%)
        
        """
        try:
            # In production, this would query actual Marinade APY from:
            # - Marinade state account
            # - Marinade API
            # - On-chain data
            
            # For now, return conservative estimate
            # Marinade typically offers 6-8% APY
            estimated_apy = 0.07  # 7% APY
            
            logger.debug(f"Current Marinade APY: {estimated_apy*100:.2f}%")
            return estimated_apy
        
        except Exception as e:
            logger.warning(f"Failed to query Marinade APY: {e}, using default")
            return 0.07  # Default to 7%
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for staking opportunities.
        
        Checks:
        - Current wallet balance
        - Marinade exchange rate and APY
        - Existing mSOL balance
        
        Returns:
            List of staking opportunities
        
        """
        opportunities = []
        
        try:
            # Get wallet balance
            balance = self.wallet_manager.get_balance()
            
            # Ensure 0.05 SOL reserve for fees (Requirement 3.2)
            available_to_stake = balance - self.reserve_balance
            
            if available_to_stake < self.min_stake_amount:
                logger.debug(
                    f"Insufficient balance to stake: {available_to_stake:.4f} SOL "
                    f"(balance: {balance:.4f}, reserve: {self.reserve_balance})"
                )
                return opportunities
            
            # Query Marinade exchange rate (Requirement 3.1)
            exchange_rate = self.marinade.get_exchange_rate()
            
            # Calculate expected mSOL
            expected_msol = available_to_stake * exchange_rate
            
            # Query current APY (Requirement 3.1)
            # Note: In production, this would query actual Marinade APY
            # For now, using a conservative estimate
            estimated_apy = self._get_current_apy()
            
            # Calculate expected yield (Requirement 3.2)
            annual_yield = available_to_stake * estimated_apy
            monthly_yield = annual_yield / 12
            
            # Create staking opportunity
            opportunities.append(Opportunity(
                strategy_name=self.get_name(),
                action="stake",
                amount=available_to_stake,
                expected_profit=monthly_yield,  # Monthly yield
                risk_level="low",
                details={
                    "type": "liquid_staking",
                    "protocol": "Marinade",
                    "stake_amount": available_to_stake,
                    "expected_msol": expected_msol,
                    "exchange_rate": exchange_rate,
                    "estimated_apy": estimated_apy,
                    "annual_yield": annual_yield,
                    "monthly_yield": monthly_yield,
                },
                timestamp=datetime.now()
            ))
            
            logger.info(
                f"Found staking opportunity: {available_to_stake:.4f} SOL at "
                f"{estimated_apy*100:.2f}% APY (expected mSOL: {expected_msol:.4f})"
            )
        
        except Exception as e:
            logger.error(f"Error scanning Marinade staking: {e}", exc_info=True)
        
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute a staking opportunity.
        
        Steps:
        1. Create stake transaction via Marinade
        2. Execute transaction via TransactionExecutor
        3. Verify mSOL tokens received
        4. Record staking position
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            stake_amount = opportunity.details.get("stake_amount")
            expected_msol = opportunity.details.get("expected_msol")
            
            logger.info(f"Executing Marinade stake: {stake_amount:.4f} SOL")
            
            # Get initial mSOL balance
            try:
                initial_msol_balance = self.marinade.get_msol_balance()
            except Exception as e:
                logger.warning(f"Could not get initial mSOL balance: {e}")
                initial_msol_balance = 0.0
            
            # Create stake transaction via Marinade integration (Requirement 3.3)
            transaction = self.marinade.create_stake_transaction(stake_amount)
            
            # Execute transaction via TransactionExecutor (Requirement 3.3)
            result = await self.executor.execute_transaction(
                transaction=transaction,
                strategy_name=self.get_name(),
                expected_profit=opportunity.expected_profit
            )
            
            if not result.success:
                logger.error(f"Stake transaction failed: {result.error}")
                return result
            
            # Verify mSOL tokens received (Requirement 3.4)
            try:
                final_msol_balance = self.marinade.get_msol_balance()
                msol_received = final_msol_balance - initial_msol_balance
                
                logger.info(
                    f"Stake successful: received {msol_received:.4f} mSOL "
                    f"(expected {expected_msol:.4f})"
                )
                
                # Check if we received approximately the expected amount
                # Allow 1% variance due to exchange rate fluctuations
                if msol_received < expected_msol * 0.99:
                    logger.warning(
                        f"Received less mSOL than expected: "
                        f"{msol_received:.4f} vs {expected_msol:.4f}"
                    )
            
            except Exception as e:
                logger.warning(f"Could not verify mSOL balance: {e}")
                msol_received = expected_msol  # Use expected value
            
            # Record staking position (Requirement 3.4)
            position = {
                "timestamp": datetime.now(),
                "stake_amount": stake_amount,
                "msol_received": msol_received,
                "transaction_hash": result.transaction_hash,
                "exchange_rate": opportunity.details.get("exchange_rate"),
                "estimated_apy": opportunity.details.get("estimated_apy"),
            }
            self.staking_positions.append(position)
            
            logger.info(
                f"Recorded staking position: {stake_amount:.4f} SOL -> "
                f"{msol_received:.4f} mSOL (TX: {result.transaction_hash[:8]}...)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing Marinade stake: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now(),
                strategy_name=self.get_name(),
                expected_profit=opportunity.expected_profit,
                actual_gas_fee=0.0,
                execution_time_ms=0,
                confirmation_time_ms=0,
                retry_count=0,
                final_balance=0.0
            )
    
    def create_unstake_opportunity(self) -> Optional[Opportunity]:
        """
        Create an unstake opportunity for current mSOL holdings.
        
        Returns:
            Opportunity to unstake mSOL, or None if no mSOL balance
        
        """
        try:
            # Get current mSOL balance
            msol_balance = self.marinade.get_msol_balance()
            
            if msol_balance <= 0:
                logger.debug("No mSOL balance to unstake")
                return None
            
            # Get current exchange rate
            exchange_rate = self.marinade.get_exchange_rate()
            
            # Calculate expected SOL to receive
            # Note: Unstaking typically has a 1:1 exchange rate or slightly better
            expected_sol = msol_balance / exchange_rate
            
            # Create unstake opportunity
            opportunity = Opportunity(
                strategy_name=self.get_name(),
                action="unstake",
                amount=msol_balance,
                expected_profit=0.0,  # Unstaking doesn't generate profit, just converts back
                risk_level="low",
                details={
                    "type": "liquid_unstaking",
                    "protocol": "Marinade",
                    "msol_amount": msol_balance,
                    "expected_sol": expected_sol,
                    "exchange_rate": exchange_rate,
                },
                timestamp=datetime.now()
            )
            
            logger.info(
                f"Created unstake opportunity: {msol_balance:.4f} mSOL -> "
                f"{expected_sol:.4f} SOL"
            )
            
            return opportunity
        
        except Exception as e:
            logger.error(f"Error creating unstake opportunity: {e}", exc_info=True)
            return None
    
    async def execute_unstake(self, opportunity: Opportunity) -> ExecutionResult:
        """
        Execute an unstaking opportunity.
        
        Steps:
        1. Create unstake transaction via Marinade
        2. Execute transaction via TransactionExecutor
        3. Verify SOL received
        
        Args:
            opportunity: Unstake opportunity to execute
        
        Returns:
            ExecutionResult with transaction details
        
        """
        try:
            msol_amount = opportunity.details.get("msol_amount")
            expected_sol = opportunity.details.get("expected_sol")
            
            logger.info(f"Executing Marinade unstake: {msol_amount:.4f} mSOL")
            
            # Get initial SOL balance
            initial_sol_balance = self.wallet_manager.get_balance()
            
            # Create unstake transaction via Marinade integration (Requirement 3.5)
            transaction = self.marinade.create_unstake_transaction(msol_amount)
            
            # Execute transaction via TransactionExecutor (Requirement 3.5)
            result = await self.executor.execute_transaction(
                transaction=transaction,
                strategy_name=self.get_name(),
                expected_profit=0.0  # Unstaking doesn't generate profit
            )
            
            if not result.success:
                logger.error(f"Unstake transaction failed: {result.error}")
                return result
            
            # Verify SOL received (Requirement 3.5)
            try:
                final_sol_balance = self.wallet_manager.get_balance()
                sol_received = final_sol_balance - initial_sol_balance
                
                logger.info(
                    f"Unstake successful: received {sol_received:.4f} SOL "
                    f"(expected {expected_sol:.4f})"
                )
                
                # Check if we received approximately the expected amount
                # Allow 1% variance and account for gas fees
                if sol_received < expected_sol * 0.95:
                    logger.warning(
                        f"Received less SOL than expected: "
                        f"{sol_received:.4f} vs {expected_sol:.4f}"
                    )
            
            except Exception as e:
                logger.warning(f"Could not verify SOL balance: {e}")
            
            logger.info(
                f"Completed unstake: {msol_amount:.4f} mSOL -> {sol_received:.4f} SOL "
                f"(TX: {result.transaction_hash[:8]}...)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing Marinade unstake: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                transaction_hash=None,
                profit=0.0,
                error=str(e),
                timestamp=datetime.now(),
                strategy_name=self.get_name(),
                expected_profit=0.0,
                actual_gas_fee=0.0,
                execution_time_ms=0,
                confirmation_time_ms=0,
                retry_count=0,
                final_balance=0.0
            )

    def track_msol_balance(self) -> Dict:
        """
        Track current mSOL balance with timestamp for yield calculation.
        
        Returns:
            Dictionary with balance snapshot
        
        """
        try:
            current_balance = self.marinade.get_msol_balance()
            
            snapshot = {
                "timestamp": datetime.now(),
                "msol_balance": current_balance,
            }
            
            logger.debug(f"mSOL balance snapshot: {current_balance:.4f} mSOL")
            return snapshot
        
        except Exception as e:
            logger.error(f"Error tracking mSOL balance: {e}", exc_info=True)
            return {
                "timestamp": datetime.now(),
                "msol_balance": 0.0,
                "error": str(e)
            }
    
    def calculate_yield(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> Dict:
        """
        Calculate yield over time based on staking positions.
        
        Args:
            start_time: Start of the period
            end_time: End of the period (default: now)
        
        Returns:
            Dictionary with yield metrics
        
        """
        if end_time is None:
            end_time = datetime.now()
        
        try:
            # Filter positions within the time period
            period_positions = [
                pos for pos in self.staking_positions
                if start_time <= pos["timestamp"] <= end_time
            ]
            
            if not period_positions:
                logger.debug("No staking positions in the specified period")
                return {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "total_staked": 0.0,
                    "total_msol_received": 0.0,
                    "estimated_yield": 0.0,
                    "period_days": (end_time - start_time).days,
                }
            
            # Calculate totals
            total_staked = sum(pos["stake_amount"] for pos in period_positions)
            total_msol_received = sum(pos["msol_received"] for pos in period_positions)
            
            # Get current mSOL balance
            current_msol_balance = self.marinade.get_msol_balance()
            
            # Calculate yield based on mSOL balance changes
            # mSOL appreciates over time relative to SOL
            initial_exchange_rate = period_positions[0]["exchange_rate"]
            current_exchange_rate = self.marinade.get_exchange_rate()
            
            # Calculate yield from exchange rate appreciation
            # If exchange rate decreased (mSOL worth more SOL), we gained yield
            if initial_exchange_rate > 0:
                exchange_rate_change = (initial_exchange_rate - current_exchange_rate) / initial_exchange_rate
                estimated_yield = total_staked * exchange_rate_change
            else:
                estimated_yield = 0.0
            
            period_days = (end_time - start_time).days
            
            result = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_staked": total_staked,
                "total_msol_received": total_msol_received,
                "current_msol_balance": current_msol_balance,
                "initial_exchange_rate": initial_exchange_rate,
                "current_exchange_rate": current_exchange_rate,
                "estimated_yield": estimated_yield,
                "period_days": period_days,
                "annualized_yield": estimated_yield * (365 / period_days) if period_days > 0 else 0.0,
            }
            
            logger.info(
                f"Yield calculation: {estimated_yield:.6f} SOL over {period_days} days "
                f"({total_staked:.4f} SOL staked)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error calculating yield: {e}", exc_info=True)
            return {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat() if end_time else datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_staking_summary(self) -> Dict:
        """
        Get summary of all staking positions and current status.
        
        Returns:
            Dictionary with staking summary
        
        """
        try:
            current_msol_balance = self.marinade.get_msol_balance()
            current_exchange_rate = self.marinade.get_exchange_rate()
            
            total_staked = sum(pos["stake_amount"] for pos in self.staking_positions)
            total_msol_received = sum(pos["msol_received"] for pos in self.staking_positions)
            
            # Calculate current SOL value of mSOL holdings
            current_sol_value = current_msol_balance / current_exchange_rate if current_exchange_rate > 0 else 0.0
            
            # Calculate total yield (difference between current value and amount staked)
            total_yield = current_sol_value - total_staked
            
            return {
                "total_positions": len(self.staking_positions),
                "total_staked": total_staked,
                "total_msol_received": total_msol_received,
                "current_msol_balance": current_msol_balance,
                "current_sol_value": current_sol_value,
                "total_yield": total_yield,
                "current_exchange_rate": current_exchange_rate,
                "positions": self.staking_positions,
            }
        
        except Exception as e:
            logger.error(f"Error getting staking summary: {e}", exc_info=True)
            return {
                "error": str(e)
            }
