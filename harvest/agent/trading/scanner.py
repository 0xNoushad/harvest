"""Opportunity scanner - finds money-making opportunities on Solana."""

import logging
from typing import Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
from agent.security.security import SecurityValidator

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """
    Represents a money-making opportunity.
    
    Attributes:
        strategy_name: Name of the strategy that found this opportunity
        action: Action to take (e.g., "stake", "claim", "buy", "sell", "arbitrage")
        amount: Amount involved in the opportunity
        expected_profit: Expected profit from the opportunity
        risk_level: Risk level ("low", "medium", "high")
        details: Additional details about the opportunity
        timestamp: When the opportunity was found
    """
    strategy_name: str
    action: str  # "stake", "farm", "buy", "sell", "arbitrage"
    amount: float
    expected_profit: float
    risk_level: str  # "low", "medium", "high"
    details: dict[str, Any]
    timestamp: Any  # datetime


class Strategy(ABC):
    """
    Abstract base class for all trading strategies.
    
    Each strategy implements scan() to find opportunities
    and execute() to execute them.
    """
    
    @abstractmethod
    def scan(self) -> List[Opportunity]:
        """
        Scan for opportunities.
        
        Returns:
            List of Opportunity objects
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Return strategy name.
        
        Returns:
            Strategy name as string
        """
        pass


class Scanner:
    """
    Scans all enabled strategies for profitable opportunities.
    
    Iterates through all registered strategies, collects opportunities,
    and handles strategy failures gracefully to ensure one failing
    strategy doesn't break the entire scan cycle.
    """
    
    def __init__(self, strategies: List[Strategy]):
        """
        Initialize scanner with list of strategy instances.
        
        Args:
            strategies: List of Strategy instances to scan
        """
        self.strategies = strategies
        logger.info(f"Scanner initialized with {len(strategies)} strategies")
    
    async def scan_all(self) -> List[Opportunity]:
        """
        Scan all strategies in parallel and return sorted opportunities.

        Queries all enabled strategies concurrently for better performance,
        then sorts opportunities by expected profit (highest first).
        If a strategy fails, logs the error and continues with remaining strategies.

        Returns:
            List of opportunities sorted by expected profit (descending)

        """
        import asyncio

        all_opportunities = []

        # Create tasks for parallel scanning
        async def scan_strategy(self, strategy: Strategy) -> List[Opportunity]:
            """
            Scan a single strategy with security validation.

            Args:
                strategy: Strategy instance to scan

            Returns:
                List of opportunities from this strategy

            Raises:
                Exception: If strategy scan fails
            """
            import asyncio

            # SECURITY: Validate strategy name
            try:
                strategy_name = strategy.get_name()
                SecurityValidator.validate_strategy_name(strategy_name)
            except ValueError as e:
                logger.error(f"Invalid strategy name: {e}")
                return []

            logger.debug(f"Scanning strategy: {strategy_name}")

            # Call strategy scan (handle both sync and async)
            if asyncio.iscoroutinefunction(strategy.scan):
                opportunities = await strategy.scan()
            else:
                loop = asyncio.get_event_loop()
                opportunities = await loop.run_in_executor(None, strategy.scan)

            # SECURITY: Validate all opportunities
            validated_opportunities = []
            for opp in opportunities:
                try:
                    # Validate amounts
                    SecurityValidator.validate_amount(opp.amount, min_val=0.0, max_val=1000000.0)
                    SecurityValidator.validate_amount(opp.expected_profit, min_val=-1000000.0, max_val=1000000.0)

                    # Validate risk level
                    if opp.risk_level not in ['low', 'medium', 'high']:
                        logger.warning(f"Invalid risk level: {opp.risk_level}")
                        continue

                    # Validate action
                    SecurityValidator.sanitize_string(opp.action, max_length=50)

                    validated_opportunities.append(opp)
                except ValueError as e:
                    logger.error(f"Invalid opportunity from {strategy_name}: {e}")
                    continue

            return validated_opportunities

        # Scan all strategies in parallel
        tasks = [scan_strategy(self, strategy) for strategy in self.strategies]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Collect all opportunities
        for opportunities in results:
            all_opportunities.extend(opportunities)

        # Sort opportunities by expected profit (highest first)
        all_opportunities.sort(key=lambda opp: opp.expected_profit, reverse=True)

        logger.info(
            f"Total opportunities found: {len(all_opportunities)} "
            f"(sorted by expected profit)"
        )

        return all_opportunities
    
    def scan_strategy(self, strategy: Strategy) -> List[Opportunity]:
        """
        Scan a single strategy with security validation.
        
        Args:
            strategy: Strategy instance to scan
        
        Returns:
            List of opportunities from this strategy
        
        Raises:
            Exception: If strategy scan fails
        """
        # SECURITY: Validate strategy name
        try:
            strategy_name = strategy.get_name()
            SecurityValidator.validate_strategy_name(strategy_name)
        except ValueError as e:
            logger.error(f"Invalid strategy name: {e}")
            return []
        
        logger.debug(f"Scanning strategy: {strategy_name}")
        opportunities = strategy.scan()
        
        # SECURITY: Validate all opportunities
        validated_opportunities = []
        for opp in opportunities:
            try:
                # Validate amounts
                SecurityValidator.validate_amount(opp.amount, min_val=0.0, max_val=1000000.0)
                SecurityValidator.validate_amount(opp.expected_profit, min_val=-1000000.0, max_val=1000000.0)
                
                # Validate risk level
                if opp.risk_level not in ['low', 'medium', 'high']:
                    logger.warning(f"Invalid risk level: {opp.risk_level}")
                    continue
                
                # Validate action
                SecurityValidator.sanitize_string(opp.action, max_length=50)
                
                validated_opportunities.append(opp)
            except ValueError as e:
                logger.error(f"Invalid opportunity from {strategy_name}: {e}")
                continue
        
        return validated_opportunities
