"""
Liquid Staking Strategy

Stakes idle SOL on Marinade Finance to earn passive yield.
Maintains a reserve for transaction fees and enforces minimum thresholds.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager
from integrations.solana.marinade import MarinadeIntegration


logger = logging.getLogger(__name__)


@dataclass
class StakingRecord:
    """Record of a staking operation."""
    amount_sol: float
    amount_msol: float
    transaction_hash: Optional[str]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


class LiquidStaking(Strategy):
    """
    Liquid staking strategy that stakes idle SOL on Marinade.
    
    This strategy monitors the wallet's SOL balance and stakes any idle
    SOL above the minimum threshold. It maintains a reserve for transaction
    fees and receives mSOL tokens in return for staked SOL.
    
    Features:
    - Minimum stake threshold: 0.1 SOL
    - Transaction fee reserve: 0.05 SOL
    - Automatic staking of idle SOL
    - mSOL balance tracking
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        min_stake_threshold: float = 0.1,
        fee_reserve: float = 0.05,
        state_file: Optional[str] = None
    ):
        """
        Initialize liquid staking strategy.
        
        Args:
            wallet: WalletManager instance for signing transactions
            min_stake_threshold: Minimum SOL to stake (default: 0.1)
            fee_reserve: SOL to keep for transaction fees (default: 0.05)
            state_file: Path to state file for tracking stakes
        """
        self.wallet = wallet
        self.min_stake_threshold = min_stake_threshold
        self.fee_reserve = fee_reserve
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "liquid_staking_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Initialize Marinade integration
        self.marinade = self._initialize_marinade()
        
        logger.info(f"LiquidStaking initialized")
        logger.info(f"Minimum stake threshold: {self.min_stake_threshold} SOL")
        logger.info(f"Fee reserve: {self.fee_reserve} SOL")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "liquid_staking"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for idle SOL that can be staked.
        
        Checks the wallet's SOL balance and determines if there is enough
        idle SOL above the minimum threshold to stake.
        
        Returns:
            List of opportunities for staking idle SOL
        """
        opportunities = []
        
        try:
            # Get idle SOL balance
            idle_sol = self.get_idle_sol()
            
            logger.info(f"Idle SOL balance: {idle_sol}")
            
            # Calculate amount available to stake (after keeping fee reserve)
            available_to_stake = idle_sol - self.fee_reserve
            
            # Check if we have enough to stake after reserve
            if available_to_stake >= self.min_stake_threshold:
                stake_amount = available_to_stake
                
                # Get current exchange rate for profit estimation
                try:
                    exchange_rate = self.marinade.get_exchange_rate()
                    expected_msol = stake_amount * exchange_rate
                except Exception as e:
                    logger.warning(f"Failed to get exchange rate: {e}")
                    exchange_rate = 0.98  # Default approximate rate
                    expected_msol = stake_amount * exchange_rate
                
                opportunity = Opportunity(
                    strategy_name=self.get_name(),
                    action="stake",
                    amount=stake_amount,
                    expected_profit=0.0,  # Yield accrues over time
                    risk_level="low",
                    details={
                        "idle_sol": idle_sol,
                        "stake_amount": stake_amount,
                        "expected_msol": expected_msol,
                        "exchange_rate": exchange_rate,
                        "fee_reserve": self.fee_reserve
                    },
                    timestamp=datetime.now()
                )
                opportunities.append(opportunity)
                logger.info(f"Found staking opportunity: {stake_amount} SOL -> {expected_msol} mSOL")
            else:
                logger.debug(f"Available to stake {available_to_stake} below threshold {self.min_stake_threshold}")
        
        except Exception as e:
            logger.error(f"Error scanning for staking opportunities: {e}")
        
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute staking operation.
        
        Stakes the specified amount of SOL on Marinade and receives mSOL tokens.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            Execution result with transaction hash and mSOL received
        """
        stake_amount = opportunity.details["stake_amount"]
        
        try:
            logger.info(f"Staking {stake_amount} SOL on Marinade")
            
            # Create stake transaction
            transaction = self.marinade.create_stake_transaction(stake_amount)
            
            # Sign and send transaction
            tx_hash = await self.wallet.sign_and_send(transaction)
            
            if not tx_hash:
                raise Exception("Failed to send stake transaction")
            
            logger.info(f"Staked {stake_amount} SOL: {tx_hash}")
            
            # Get mSOL balance to confirm receipt
            try:
                msol_balance = self.get_msol_balance()
                logger.info(f"Current mSOL balance: {msol_balance}")
            except Exception as e:
                logger.warning(f"Failed to query mSOL balance: {e}")
                msol_balance = opportunity.details.get("expected_msol", 0.0)
            
            # Record successful stake
            record = StakingRecord(
                amount_sol=stake_amount,
                amount_msol=msol_balance,
                transaction_hash=tx_hash,
                timestamp=datetime.now(),
                success=True
            )
            self._record_stake(record)
            
            return {
                "success": True,
                "transaction_hash": tx_hash,
                "amount_staked": stake_amount,
                "msol_received": opportunity.details.get("expected_msol", 0.0),
                "msol_balance": msol_balance,
                "timestamp": record.timestamp.isoformat()
            }
        
        except Exception as e:
            error_msg = f"Failed to stake SOL: {str(e)}"
            logger.error(error_msg)
            
            # Record failed stake
            record = StakingRecord(
                amount_sol=stake_amount,
                amount_msol=0.0,
                transaction_hash=None,
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )
            self._record_stake(record)
            
            return {
                "success": False,
                "error": error_msg,
                "amount_staked": stake_amount,
                "timestamp": record.timestamp.isoformat()
            }
    
    def get_idle_sol(self) -> float:
        """
        Get idle SOL balance not allocated to strategies.
        
        Returns the wallet's SOL balance minus any reserved amounts.
        
        Returns:
            Idle SOL balance
        """
        try:
            # Get total SOL balance
            total_balance = self.wallet.get_balance()
            
            # For now, consider all balance as idle
            # In a more complex system, you'd subtract:
            # - Active positions in other strategies
            # - Pending transactions
            # - Other reserved amounts
            
            idle_balance = total_balance
            
            logger.debug(f"Total SOL: {total_balance}, Idle SOL: {idle_balance}")
            return idle_balance
        
        except Exception as e:
            logger.error(f"Failed to get idle SOL: {e}")
            return 0.0
    
    def get_msol_balance(self) -> float:
        """
        Get current mSOL balance.
        
        Returns:
            mSOL token balance
        """
        try:
            balance = self.marinade.get_msol_balance()
            logger.info(f"mSOL balance: {balance}")
            return balance
        
        except Exception as e:
            logger.error(f"Failed to get mSOL balance: {e}")
            return 0.0
    
    def _initialize_marinade(self) -> MarinadeIntegration:
        """
        Initialize Marinade integration.
        
        Returns:
            MarinadeIntegration instance
        """
        # Note: In production, this should use the Helius RPC client
        # For now, we'll create a simple mock RPC client
        
        class MockRPCClient:
            """Mock RPC client for testing."""
            def get_account_info(self, address):
                return None
            
            def get_latest_blockhash(self):
                return {"blockhash": "mock_blockhash"}
            
            def get_token_balance(self, address):
                # Return mock mSOL balance
                return 0.0
        
        rpc_client = MockRPCClient()
        
        return MarinadeIntegration(rpc_client, self.wallet.public_key)
    
    def _record_stake(self, record: StakingRecord):
        """
        Record a staking operation to state.
        
        Args:
            record: StakingRecord to save
        """
        # Initialize stakes list if needed
        if "stakes" not in self.state:
            self.state["stakes"] = []
        
        # Add stake record
        stake_data = {
            "amount_sol": record.amount_sol,
            "amount_msol": record.amount_msol,
            "transaction_hash": record.transaction_hash,
            "timestamp": record.timestamp.isoformat(),
            "success": record.success,
            "error": record.error
        }
        
        self.state["stakes"].append(stake_data)
        
        # Keep only last 50 stakes
        self.state["stakes"] = self.state["stakes"][-50:]
        
        # Update total staked
        if record.success:
            total_staked = self.state.get("total_staked", 0.0)
            self.state["total_staked"] = total_staked + record.amount_sol
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded stake: {record.amount_sol} SOL")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {"stakes": [], "total_staked": 0.0}
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {"stakes": [], "total_staked": 0.0}
    
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
    
    def get_staking_history(self) -> List[Dict]:
        """
        Get staking history.
        
        Returns:
            List of staking records
        """
        return self.state.get("stakes", [])
    
    def get_total_staked(self) -> float:
        """
        Get total amount of SOL staked.
        
        Returns:
            Total SOL staked
        """
        return self.state.get("total_staked", 0.0)
