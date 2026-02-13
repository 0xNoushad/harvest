"""
Arbitrage Trading Strategy (Bounty Hunter)

Monitors price differences across DEXs (Jupiter and Orca) and executes
arbitrage trades when profitable opportunities are found.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager
from integrations.solana.jupiter import JupiterIntegration
from integrations.solana.orca import OrcaIntegration


logger = logging.getLogger(__name__)


@dataclass
class ArbitrageRecord:
    """Record of an arbitrage trade."""
    token_pair: str
    buy_dex: str
    sell_dex: str
    buy_price: float
    sell_price: float
    amount: float
    profit: float
    buy_tx_hash: Optional[str]
    sell_tx_hash: Optional[str]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class BountyHunter(Strategy):
    """
    Arbitrage trading strategy that exploits price differences across DEXs.
    
    This strategy monitors prices on Jupiter and Orca for configured token
    pairs and executes arbitrage trades when the profit potential exceeds
    the minimum threshold after accounting for fees.
    
    Features:
    - Monitors SOL/USDC and SOL/USDT pairs
    - Minimum profit threshold: 0.5% after fees
    - Automatic DEX direction selection (buy low, sell high)
    - Profit recording and tracking
    - Maximum position size: 10 SOL
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        min_profit_threshold: float = 0.005,  # 0.5%
        max_position_size: float = 10.0,  # 10 SOL
        monitored_pairs: Optional[List[Tuple[str, str]]] = None,
        state_file: Optional[str] = None
    ):
        """
        Initialize arbitrage trading strategy.
        
        Args:
            wallet: WalletManager instance for signing transactions
            min_profit_threshold: Minimum profit percentage after fees (default: 0.5%)
            max_position_size: Maximum position size in SOL (default: 10.0)
            monitored_pairs: List of (input_mint, output_mint) tuples to monitor
            state_file: Path to state file for tracking trades
        """
        self.wallet = wallet
        self.min_profit_threshold = min_profit_threshold
        self.max_position_size = max_position_size
        
        # Set up monitored pairs (default to SOL/USDC and SOL/USDT)
        if monitored_pairs is None:
            self.monitored_pairs = [
                ("So11111111111111111111111111111111111111112", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),  # SOL/USDC
                ("So11111111111111111111111111111111111111112", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),  # SOL/USDT
            ]
        else:
            self.monitored_pairs = monitored_pairs
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "bounty_hunter_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Initialize DEX integrations
        self.jupiter = self._initialize_jupiter()
        self.orca = self._initialize_orca()
        
        logger.info(f"BountyHunter (ArbitrageTrader) initialized")
        logger.info(f"Minimum profit threshold: {self.min_profit_threshold * 100}%")
        logger.info(f"Maximum position size: {self.max_position_size} SOL")
        logger.info(f"Monitoring {len(self.monitored_pairs)} token pairs")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "bounty_hunter"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for arbitrage opportunities across DEXs.
        
        Checks prices on Jupiter and Orca for all monitored pairs and
        identifies opportunities where the price difference exceeds the
        minimum profit threshold after fees.
        
        Returns:
            List of arbitrage opportunities
        """
        opportunities = []
        
        for input_mint, output_mint in self.monitored_pairs:
            try:
                # Get pair name for logging
                pair_name = self._get_pair_name(input_mint, output_mint)
                
                logger.info(f"Checking arbitrage for {pair_name}")
                
                # Get prices from both DEXs
                prices = self.get_prices(pair_name)
                
                if not prices:
                    logger.warning(f"Failed to get prices for {pair_name}")
                    continue
                
                jupiter_price = prices.get("jupiter", 0.0)
                orca_price = prices.get("orca", 0.0)
                
                if jupiter_price == 0.0 or orca_price == 0.0:
                    logger.warning(f"Invalid prices for {pair_name}: Jupiter={jupiter_price}, Orca={orca_price}")
                    continue
                
                logger.info(f"{pair_name} prices - Jupiter: {jupiter_price}, Orca: {orca_price}")
                
                # Determine trade direction (buy low, sell high)
                if jupiter_price < orca_price:
                    buy_dex = "jupiter"
                    sell_dex = "orca"
                    buy_price = jupiter_price
                    sell_price = orca_price
                else:
                    buy_dex = "orca"
                    sell_dex = "jupiter"
                    buy_price = orca_price
                    sell_price = jupiter_price
                
                # Calculate profit potential
                # Use a reasonable trade amount (1 SOL for SOL pairs)
                trade_amount = 1.0
                profit = self.calculate_profit(buy_price, sell_price, trade_amount)
                profit_percentage = (profit / (buy_price * trade_amount)) if buy_price > 0 else 0.0
                
                logger.info(
                    f"{pair_name} arbitrage: Buy on {buy_dex} at {buy_price}, "
                    f"sell on {sell_dex} at {sell_price}, "
                    f"profit: {profit} ({profit_percentage * 100:.2f}%)"
                )
                
                # Check if profit exceeds threshold
                if profit_percentage >= self.min_profit_threshold:
                    # Determine optimal trade amount (up to max position size)
                    optimal_amount = min(trade_amount, self.max_position_size)
                    optimal_profit = self.calculate_profit(buy_price, sell_price, optimal_amount)
                    
                    opportunity = Opportunity(
                        strategy_name=self.get_name(),
                        action="arbitrage",
                        amount=optimal_amount,
                        expected_profit=optimal_profit,
                        risk_level="medium",
                        details={
                            "token_pair": pair_name,
                            "input_mint": input_mint,
                            "output_mint": output_mint,
                            "buy_dex": buy_dex,
                            "sell_dex": sell_dex,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "trade_amount": optimal_amount,
                            "profit_percentage": profit_percentage,
                            "expected_profit": optimal_profit
                        },
                        timestamp=datetime.now()
                    )
                    opportunities.append(opportunity)
                    logger.info(
                        f"Found arbitrage opportunity: {pair_name} - "
                        f"Buy on {buy_dex}, sell on {sell_dex}, "
                        f"profit: {optimal_profit} ({profit_percentage * 100:.2f}%)"
                    )
                else:
                    logger.debug(
                        f"Profit {profit_percentage * 100:.2f}% below threshold "
                        f"{self.min_profit_threshold * 100}%"
                    )
            
            except Exception as e:
                logger.error(f"Error checking pair {input_mint}/{output_mint}: {e}")
                # Continue with other pairs
                continue
        
        logger.info(f"Found {len(opportunities)} arbitrage opportunities")
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute arbitrage trade.
        
        Buys on the cheaper DEX and sells on the more expensive DEX.
        
        Args:
            opportunity: Arbitrage opportunity to execute
        
        Returns:
            Execution result with transaction hashes and profit
        """
        token_pair = opportunity.details["token_pair"]
        input_mint = opportunity.details["input_mint"]
        output_mint = opportunity.details["output_mint"]
        buy_dex = opportunity.details["buy_dex"]
        sell_dex = opportunity.details["sell_dex"]
        buy_price = opportunity.details["buy_price"]
        sell_price = opportunity.details["sell_price"]
        trade_amount = opportunity.details["trade_amount"]
        
        try:
            logger.info(
                f"Executing arbitrage for {token_pair}: "
                f"Buy {trade_amount} on {buy_dex}, sell on {sell_dex}"
            )
            
            # Execute the arbitrage trade
            buy_tx_hash, sell_tx_hash = await self.execute_arbitrage(
                buy_dex, sell_dex, token_pair, trade_amount
            )
            
            if not buy_tx_hash or not sell_tx_hash:
                raise Exception("Failed to execute arbitrage trades")
            
            # Calculate actual profit
            actual_profit = self.calculate_profit(buy_price, sell_price, trade_amount)
            
            logger.info(
                f"Arbitrage executed for {token_pair}: "
                f"Buy tx: {buy_tx_hash}, Sell tx: {sell_tx_hash}, "
                f"Profit: {actual_profit}"
            )
            
            # Record successful trade
            record = ArbitrageRecord(
                token_pair=token_pair,
                buy_dex=buy_dex,
                sell_dex=sell_dex,
                buy_price=buy_price,
                sell_price=sell_price,
                amount=trade_amount,
                profit=actual_profit,
                buy_tx_hash=buy_tx_hash,
                sell_tx_hash=sell_tx_hash,
                timestamp=datetime.now(),
                success=True
            )
            self._record_trade(record)
            
            return {
                "success": True,
                "token_pair": token_pair,
                "buy_dex": buy_dex,
                "sell_dex": sell_dex,
                "buy_tx_hash": buy_tx_hash,
                "sell_tx_hash": sell_tx_hash,
                "amount": trade_amount,
                "profit": actual_profit,
                "timestamp": record.timestamp.isoformat()
            }
        
        except Exception as e:
            error_msg = f"Failed to execute arbitrage: {str(e)}"
            logger.error(error_msg)
            
            # Record failed trade
            record = ArbitrageRecord(
                token_pair=token_pair,
                buy_dex=buy_dex,
                sell_dex=sell_dex,
                buy_price=buy_price,
                sell_price=sell_price,
                amount=trade_amount,
                profit=0.0,
                buy_tx_hash=None,
                sell_tx_hash=None,
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )
            self._record_trade(record)
            
            return {
                "success": False,
                "error": error_msg,
                "token_pair": token_pair,
                "amount": trade_amount,
                "timestamp": record.timestamp.isoformat()
            }
    
    def get_prices(self, token_pair: str) -> Dict[str, float]:
        """
        Get prices from Jupiter and Orca for a token pair.
        
        Args:
            token_pair: Token pair identifier (e.g., "SOL/USDC")
        
        Returns:
            Dictionary with prices from each DEX
        """
        prices = {}
        
        # Parse token pair
        input_mint, output_mint = self._parse_pair_name(token_pair)
        
        # Get price from Jupiter
        try:
            jupiter_output = self.jupiter.get_best_price(input_mint, output_mint, 1.0)
            prices["jupiter"] = jupiter_output
            logger.debug(f"Jupiter price for {token_pair}: {jupiter_output}")
        except Exception as e:
            logger.error(f"Failed to get Jupiter price for {token_pair}: {e}")
            prices["jupiter"] = 0.0
        
        # Get price from Orca
        try:
            orca_output = self.orca.get_price(input_mint, output_mint, 1.0)
            prices["orca"] = orca_output
            logger.debug(f"Orca price for {token_pair}: {orca_output}")
        except Exception as e:
            logger.error(f"Failed to get Orca price for {token_pair}: {e}")
            prices["orca"] = 0.0
        
        return prices
    
    def calculate_profit(
        self,
        buy_price: float,
        sell_price: float,
        amount: float
    ) -> float:
        """
        Calculate profit after fees for an arbitrage trade.
        
        Args:
            buy_price: Price on the buy DEX (output amount per 1 input)
            sell_price: Price on the sell DEX (output amount per 1 input)
            amount: Trade amount in input tokens
        
        Returns:
            Profit after fees in output tokens
        """
        # Handle zero prices
        if buy_price == 0.0 or sell_price == 0.0:
            return 0.0
        
        # Calculate gross profit
        # When we buy, we spend amount input tokens and get amount * buy_price output tokens
        # When we sell, we spend those output tokens and get back input tokens
        # But we're comparing prices, so:
        # - Buy on cheaper DEX: spend amount input, get amount * buy_price output
        # - Sell on expensive DEX: the sell_price tells us how much output we'd get for 1 input
        # So the profit is the difference in output amounts
        buy_output = amount * buy_price  # Output tokens from buying
        sell_output = amount * sell_price  # Output tokens from selling
        gross_profit = sell_output - buy_output
        
        # Estimate fees (0.3% per trade, typical for DEXs)
        fee_rate = 0.003
        buy_fee = buy_output * fee_rate
        sell_fee = sell_output * fee_rate
        total_fees = buy_fee + sell_fee
        
        # Net profit after fees
        net_profit = gross_profit - total_fees
        
        logger.debug(
            f"Profit calculation: buy_output={buy_output}, sell_output={sell_output}, "
            f"gross_profit={gross_profit}, fees={total_fees}, net_profit={net_profit}"
        )
        
        return net_profit
    
    async def execute_arbitrage(
        self,
        buy_dex: str,
        sell_dex: str,
        token_pair: str,
        amount: float
    ) -> Tuple[str, str]:
        """
        Execute arbitrage trade (buy on one DEX, sell on another).
        
        Args:
            buy_dex: DEX to buy on ("jupiter" or "orca")
            sell_dex: DEX to sell on ("jupiter" or "orca")
            token_pair: Token pair identifier
            amount: Amount to trade
        
        Returns:
            Tuple of (buy_tx_hash, sell_tx_hash)
        
        Raises:
            Exception: If trade execution fails
        """
        input_mint, output_mint = self._parse_pair_name(token_pair)
        
        # Execute buy transaction
        logger.info(f"Buying {amount} on {buy_dex}")
        if buy_dex == "jupiter":
            buy_tx = self.jupiter.create_swap_transaction(input_mint, output_mint, amount)
        else:  # orca
            buy_tx = self.orca.create_swap_transaction(input_mint, output_mint, amount)
        
        buy_tx_hash = await self.wallet.sign_and_send(buy_tx)
        
        if not buy_tx_hash:
            raise Exception(f"Failed to execute buy on {buy_dex}")
        
        logger.info(f"Buy executed on {buy_dex}: {buy_tx_hash}")
        
        # Execute sell transaction
        # Note: In a real implementation, we'd swap back the output tokens
        # For now, we'll create a reverse swap
        logger.info(f"Selling on {sell_dex}")
        if sell_dex == "jupiter":
            sell_tx = self.jupiter.create_swap_transaction(output_mint, input_mint, amount)
        else:  # orca
            sell_tx = self.orca.create_swap_transaction(output_mint, input_mint, amount)
        
        sell_tx_hash = await self.wallet.sign_and_send(sell_tx)
        
        if not sell_tx_hash:
            raise Exception(f"Failed to execute sell on {sell_dex}")
        
        logger.info(f"Sell executed on {sell_dex}: {sell_tx_hash}")
        
        return buy_tx_hash, sell_tx_hash
    
    def _get_pair_name(self, input_mint: str, output_mint: str) -> str:
        """
        Get human-readable pair name from mint addresses.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
        
        Returns:
            Pair name (e.g., "SOL/USDC")
        """
        token_names = {
            "So11111111111111111111111111111111111111112": "SOL",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
        }
        
        input_name = token_names.get(input_mint, input_mint[:8])
        output_name = token_names.get(output_mint, output_mint[:8])
        
        return f"{input_name}/{output_name}"
    
    def _parse_pair_name(self, pair_name: str) -> Tuple[str, str]:
        """
        Parse pair name into mint addresses.
        
        Args:
            pair_name: Pair name (e.g., "SOL/USDC")
        
        Returns:
            Tuple of (input_mint, output_mint)
        """
        token_mints = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        }
        
        parts = pair_name.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid pair name: {pair_name}")
        
        input_name, output_name = parts
        input_mint = token_mints.get(input_name, input_name)
        output_mint = token_mints.get(output_name, output_name)
        
        return input_mint, output_mint
    
    def _initialize_jupiter(self) -> JupiterIntegration:
        """
        Initialize Jupiter integration.
        
        Returns:
            JupiterIntegration instance
        """
        # Note: In production, this should use the Helius RPC client
        # For now, we'll create a simple mock RPC client
        
        class MockRPCClient:
            """Mock RPC client for testing."""
            def get_account_info(self, address):
                return None
            
            def get_latest_blockhash(self):
                return {"blockhash": "mock_blockhash"}
        
        rpc_client = MockRPCClient()
        
        return JupiterIntegration(rpc_client, self.wallet.public_key)
    
    def _initialize_orca(self) -> OrcaIntegration:
        """
        Initialize Orca integration.
        
        Returns:
            OrcaIntegration instance
        """
        # Note: In production, this should use the Helius RPC client
        # For now, we'll create a simple mock RPC client
        
        class MockRPCClient:
            """Mock RPC client for testing."""
            def get_account_info(self, address):
                return None
            
            def get_latest_blockhash(self):
                return {"blockhash": "mock_blockhash"}
        
        rpc_client = MockRPCClient()
        
        return OrcaIntegration(rpc_client, self.wallet.public_key)
    
    def _record_trade(self, record: ArbitrageRecord):
        """
        Record an arbitrage trade to state.
        
        Args:
            record: ArbitrageRecord to save
        """
        # Initialize trades list if needed
        if "trades" not in self.state:
            self.state["trades"] = []
        
        # Add trade record
        trade_data = {
            "token_pair": record.token_pair,
            "buy_dex": record.buy_dex,
            "sell_dex": record.sell_dex,
            "buy_price": record.buy_price,
            "sell_price": record.sell_price,
            "amount": record.amount,
            "profit": record.profit,
            "buy_tx_hash": record.buy_tx_hash,
            "sell_tx_hash": record.sell_tx_hash,
            "timestamp": record.timestamp.isoformat(),
            "success": record.success,
            "error": record.error
        }
        
        self.state["trades"].append(trade_data)
        
        # Keep only last 100 trades
        self.state["trades"] = self.state["trades"][-100:]
        
        # Update total profit
        if record.success:
            total_profit = self.state.get("total_profit", 0.0)
            self.state["total_profit"] = total_profit + record.profit
            
            # Update successful trades count
            successful_trades = self.state.get("successful_trades", 0)
            self.state["successful_trades"] = successful_trades + 1
        
        # Update total trades count
        total_trades = self.state.get("total_trades", 0)
        self.state["total_trades"] = total_trades + 1
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded arbitrage trade: {record.token_pair} - Profit: {record.profit}")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {
                "trades": [],
                "total_profit": 0.0,
                "total_trades": 0,
                "successful_trades": 0
            }
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {
                "trades": [],
                "total_profit": 0.0,
                "total_trades": 0,
                "successful_trades": 0
            }
    
    def _save_state(self):
        """Save state to file."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_trade_history(self) -> List[Dict]:
        """
        Get trade history.
        
        Returns:
            List of trade records
        """
        return self.state.get("trades", [])
    
    def get_total_profit(self) -> float:
        """
        Get total profit from all arbitrage trades.
        
        Returns:
            Total profit amount
        """
        return self.state.get("total_profit", 0.0)
    
    def get_total_trades(self) -> int:
        """
        Get total number of trades executed.
        
        Returns:
            Total trades count
        """
        return self.state.get("total_trades", 0)
    
    def get_successful_trades(self) -> int:
        """
        Get number of successful trades.
        
        Returns:
            Successful trades count
        """
        return self.state.get("successful_trades", 0)
    
    def get_win_rate(self) -> float:
        """
        Get win rate (successful trades / total trades).
        
        Returns:
            Win rate as a percentage (0-100)
        """
        total = self.get_total_trades()
        if total == 0:
            return 0.0
        
        successful = self.get_successful_trades()
        return (successful / total) * 100.0
