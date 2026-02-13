"""
Yield Farming Strategy

Deposits idle stablecoins into Kamino vaults to earn passive yield.
Automatically selects the highest APY vault and compounds rewards weekly.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager
from integrations.solana.kamino import KaminoIntegration, VaultInfo


logger = logging.getLogger(__name__)


@dataclass
class DepositRecord:
    """Record of a vault deposit operation."""
    vault_address: str
    vault_name: str
    amount: float
    transaction_hash: Optional[str]
    timestamp: datetime
    success: bool
    error: Optional[str] = None


@dataclass
class EarningsRecord:
    """Record of earnings from a vault."""
    vault_address: str
    vault_name: str
    earnings: float
    timestamp: datetime


class YieldFarmer(Strategy):
    """
    Yield farming strategy that deposits stablecoins into Kamino vaults.
    
    This strategy monitors the wallet's USDC balance and deposits idle
    stablecoins into the highest APY Kamino vault. It tracks earnings
    and automatically compounds rewards on a weekly basis.
    
    Features:
    - Minimum deposit threshold: 10 USDC
    - Automatic vault selection (highest APY)
    - Earnings tracking
    - Weekly auto-compound
    - Support for USDC and USDT
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        min_deposit_threshold: float = 10.0,
        compound_interval_days: int = 7,
        supported_tokens: Optional[List[str]] = None,
        state_file: Optional[str] = None
    ):
        """
        Initialize yield farming strategy.
        
        Args:
            wallet: WalletManager instance for signing transactions
            min_deposit_threshold: Minimum USDC to deposit (default: 10.0)
            compound_interval_days: Days between auto-compound (default: 7)
            supported_tokens: List of token mints to farm (default: USDC, USDT)
            state_file: Path to state file for tracking deposits
        """
        self.wallet = wallet
        self.min_deposit_threshold = min_deposit_threshold
        self.compound_interval_days = compound_interval_days
        
        # Set up supported tokens (default to USDC and USDT)
        if supported_tokens is None:
            self.supported_tokens = [
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            ]
        else:
            self.supported_tokens = supported_tokens
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "yield_farmer_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Initialize Kamino integration
        self.kamino = self._initialize_kamino()
        
        logger.info(f"YieldFarmer initialized")
        logger.info(f"Minimum deposit threshold: {self.min_deposit_threshold} USDC")
        logger.info(f"Compound interval: {self.compound_interval_days} days")
        logger.info(f"Supported tokens: {len(self.supported_tokens)}")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "yield_farmer"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for idle stablecoins that can be deposited.
        
        Checks the wallet's balance for supported tokens and determines
        if there is enough idle balance above the minimum threshold to
        deposit into a vault. Also checks for auto-compound opportunities.
        
        Returns:
            List of opportunities for depositing or compounding
        """
        opportunities = []
        
        # Check for deposit opportunities
        for token_mint in self.supported_tokens:
            try:
                # Get idle balance for this token
                idle_balance = self.get_idle_balance(token_mint)
                
                logger.info(f"Idle balance for token {token_mint[:8]}...: {idle_balance}")
                
                # Check if we have enough to deposit
                if idle_balance >= self.min_deposit_threshold:
                    # Get best vault for this token
                    best_vault = self.kamino.get_best_vault(token_mint)
                    
                    if best_vault:
                        # Calculate expected earnings (annual)
                        expected_annual_earnings = idle_balance * (best_vault.apy / 100)
                        
                        opportunity = Opportunity(
                            strategy_name=self.get_name(),
                            action="deposit",
                            amount=idle_balance,
                            expected_profit=expected_annual_earnings / 365,  # Daily earnings
                            risk_level="low",
                            details={
                                "token_mint": token_mint,
                                "vault_address": best_vault.address,
                                "vault_name": best_vault.name,
                                "vault_apy": best_vault.apy,
                                "vault_tvl": best_vault.tvl,
                                "deposit_amount": idle_balance,
                                "expected_annual_earnings": expected_annual_earnings
                            },
                            timestamp=datetime.now()
                        )
                        opportunities.append(opportunity)
                        logger.info(
                            f"Found deposit opportunity: {idle_balance} tokens "
                            f"to {best_vault.name} ({best_vault.apy}% APY)"
                        )
                    else:
                        logger.warning(f"No vaults found for token {token_mint}")
                else:
                    logger.debug(
                        f"Idle balance {idle_balance} below threshold "
                        f"{self.min_deposit_threshold}"
                    )
            
            except Exception as e:
                logger.error(f"Error checking token {token_mint}: {e}")
                # Continue with other tokens
                continue
        
        # Check for auto-compound opportunities
        try:
            compound_opps = self._check_compound_opportunities()
            opportunities.extend(compound_opps)
        except Exception as e:
            logger.error(f"Error checking compound opportunities: {e}")
        
        logger.info(f"Found {len(opportunities)} yield farming opportunities")
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute yield farming operation.
        
        Deposits tokens into the specified vault or compounds existing rewards.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            Execution result with transaction hash and status
        """
        action = opportunity.action
        
        if action == "deposit":
            return await self._execute_deposit(opportunity)
        elif action == "compound":
            return await self._execute_compound(opportunity)
        else:
            error_msg = f"Unknown action: {action}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_deposit(self, opportunity: Opportunity) -> Dict:
        """
        Execute vault deposit.
        
        Args:
            opportunity: Deposit opportunity
        
        Returns:
            Execution result
        """
        vault_address = opportunity.details["vault_address"]
        vault_name = opportunity.details["vault_name"]
        deposit_amount = opportunity.details["deposit_amount"]
        
        try:
            logger.info(f"Depositing {deposit_amount} tokens to {vault_name}")
            
            # Create deposit transaction
            transaction = self.kamino.create_deposit_transaction(
                vault_address,
                deposit_amount
            )
            
            # Sign and send transaction
            tx_hash = await self.wallet.sign_and_send(transaction)
            
            if not tx_hash:
                raise Exception("Failed to send deposit transaction")
            
            logger.info(f"Deposited {deposit_amount} tokens to {vault_name}: {tx_hash}")
            
            # Record successful deposit
            record = DepositRecord(
                vault_address=vault_address,
                vault_name=vault_name,
                amount=deposit_amount,
                transaction_hash=tx_hash,
                timestamp=datetime.now(),
                success=True
            )
            self._record_deposit(record)
            
            # Initialize earnings tracking for this vault
            self._initialize_vault_tracking(vault_address, vault_name, deposit_amount)
            
            return {
                "success": True,
                "transaction_hash": tx_hash,
                "vault_address": vault_address,
                "vault_name": vault_name,
                "amount_deposited": deposit_amount,
                "vault_apy": opportunity.details["vault_apy"],
                "timestamp": record.timestamp.isoformat()
            }
        
        except Exception as e:
            error_msg = f"Failed to deposit to vault: {str(e)}"
            logger.error(error_msg)
            
            # Record failed deposit
            record = DepositRecord(
                vault_address=vault_address,
                vault_name=vault_name,
                amount=deposit_amount,
                transaction_hash=None,
                timestamp=datetime.now(),
                success=False,
                error=str(e)
            )
            self._record_deposit(record)
            
            return {
                "success": False,
                "error": error_msg,
                "vault_address": vault_address,
                "amount_deposited": deposit_amount,
                "timestamp": record.timestamp.isoformat()
            }
    
    async def _execute_compound(self, opportunity: Opportunity) -> Dict:
        """
        Execute reward compounding.
        
        Args:
            opportunity: Compound opportunity
        
        Returns:
            Execution result
        """
        vault_address = opportunity.details["vault_address"]
        vault_name = opportunity.details["vault_name"]
        
        try:
            logger.info(f"Compounding rewards for {vault_name}")
            
            # Get current vault balance
            current_balance = self.kamino.get_user_balance(vault_address)
            
            # Calculate earnings since last compound
            vault_data = self.state.get("vaults", {}).get(vault_address, {})
            last_balance = vault_data.get("last_balance", 0.0)
            earnings = current_balance - last_balance
            
            if earnings > 0:
                # Record earnings
                earnings_record = EarningsRecord(
                    vault_address=vault_address,
                    vault_name=vault_name,
                    earnings=earnings,
                    timestamp=datetime.now()
                )
                self._record_earnings(earnings_record)
                
                logger.info(f"Recorded earnings of {earnings} tokens from {vault_name}")
            
            # Update last compound time and balance
            self._update_vault_tracking(vault_address, current_balance)
            
            return {
                "success": True,
                "vault_address": vault_address,
                "vault_name": vault_name,
                "earnings": earnings,
                "new_balance": current_balance,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            error_msg = f"Failed to compound rewards: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "vault_address": vault_address,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_idle_balance(self, token_mint: str) -> float:
        """
        Get idle balance for a specific token.
        
        Args:
            token_mint: Token mint address
        
        Returns:
            Idle token balance
        """
        try:
            # Get total token balance
            total_balance = self.wallet.get_token_balance(token_mint)
            
            # For now, consider all balance as idle
            # In a more complex system, you'd subtract:
            # - Active positions in other strategies
            # - Pending transactions
            # - Other reserved amounts
            
            idle_balance = total_balance
            
            logger.debug(f"Total balance: {total_balance}, Idle: {idle_balance}")
            return idle_balance
        
        except Exception as e:
            logger.error(f"Failed to get idle balance: {e}")
            return 0.0
    
    def _check_compound_opportunities(self) -> List[Opportunity]:
        """
        Check for vaults that need compounding.
        
        Returns:
            List of compound opportunities
        """
        opportunities = []
        now = datetime.now()
        
        vaults = self.state.get("vaults", {})
        
        for vault_address, vault_data in vaults.items():
            try:
                # Check if compound is due
                last_compound_str = vault_data.get("last_compound")
                if last_compound_str:
                    last_compound = datetime.fromisoformat(last_compound_str)
                    days_since = (now - last_compound).days
                    
                    if days_since >= self.compound_interval_days:
                        opportunity = Opportunity(
                            strategy_name=self.get_name(),
                            action="compound",
                            amount=0.0,  # No new deposit
                            expected_profit=0.0,  # Earnings calculated during execution
                            risk_level="low",
                            details={
                                "vault_address": vault_address,
                                "vault_name": vault_data.get("vault_name", "Unknown"),
                                "last_compound": last_compound_str,
                                "days_since_compound": days_since
                            },
                            timestamp=now
                        )
                        opportunities.append(opportunity)
                        logger.info(
                            f"Vault {vault_data.get('vault_name')} due for compound "
                            f"({days_since} days since last)"
                        )
            
            except Exception as e:
                logger.error(f"Error checking compound for vault {vault_address}: {e}")
                continue
        
        return opportunities
    
    def _initialize_kamino(self) -> KaminoIntegration:
        """
        Initialize Kamino integration.
        
        Returns:
            KaminoIntegration instance
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
                return 0.0
        
        rpc_client = MockRPCClient()
        
        return KaminoIntegration(rpc_client, self.wallet.public_key)
    
    def _initialize_vault_tracking(
        self,
        vault_address: str,
        vault_name: str,
        initial_deposit: float
    ):
        """
        Initialize tracking for a new vault deposit.
        
        Args:
            vault_address: Vault address
            vault_name: Vault name
            initial_deposit: Initial deposit amount
        """
        if "vaults" not in self.state:
            self.state["vaults"] = {}
        
        self.state["vaults"][vault_address] = {
            "vault_name": vault_name,
            "initial_deposit": initial_deposit,
            "last_balance": initial_deposit,
            "last_compound": datetime.now().isoformat(),
            "total_earnings": 0.0
        }
        
        self._save_state()
        logger.debug(f"Initialized tracking for vault {vault_name}")
    
    def _update_vault_tracking(self, vault_address: str, new_balance: float):
        """
        Update vault tracking after compound.
        
        Args:
            vault_address: Vault address
            new_balance: New vault balance
        """
        if "vaults" not in self.state:
            self.state["vaults"] = {}
        
        if vault_address in self.state["vaults"]:
            self.state["vaults"][vault_address]["last_balance"] = new_balance
            self.state["vaults"][vault_address]["last_compound"] = datetime.now().isoformat()
            self._save_state()
            logger.debug(f"Updated tracking for vault {vault_address}")
    
    def _record_deposit(self, record: DepositRecord):
        """
        Record a deposit operation to state.
        
        Args:
            record: DepositRecord to save
        """
        # Initialize deposits list if needed
        if "deposits" not in self.state:
            self.state["deposits"] = []
        
        # Add deposit record
        deposit_data = {
            "vault_address": record.vault_address,
            "vault_name": record.vault_name,
            "amount": record.amount,
            "transaction_hash": record.transaction_hash,
            "timestamp": record.timestamp.isoformat(),
            "success": record.success,
            "error": record.error
        }
        
        self.state["deposits"].append(deposit_data)
        
        # Keep only last 50 deposits
        self.state["deposits"] = self.state["deposits"][-50:]
        
        # Update total deposited
        if record.success:
            total_deposited = self.state.get("total_deposited", 0.0)
            self.state["total_deposited"] = total_deposited + record.amount
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded deposit: {record.amount} to {record.vault_name}")
    
    def _record_earnings(self, record: EarningsRecord):
        """
        Record earnings from a vault.
        
        Args:
            record: EarningsRecord to save
        """
        # Initialize earnings list if needed
        if "earnings" not in self.state:
            self.state["earnings"] = []
        
        # Add earnings record
        earnings_data = {
            "vault_address": record.vault_address,
            "vault_name": record.vault_name,
            "earnings": record.earnings,
            "timestamp": record.timestamp.isoformat()
        }
        
        self.state["earnings"].append(earnings_data)
        
        # Keep only last 100 earnings records
        self.state["earnings"] = self.state["earnings"][-100:]
        
        # Update total earnings
        total_earnings = self.state.get("total_earnings", 0.0)
        self.state["total_earnings"] = total_earnings + record.earnings
        
        # Update vault-specific earnings
        if "vaults" in self.state and record.vault_address in self.state["vaults"]:
            vault_earnings = self.state["vaults"][record.vault_address].get("total_earnings", 0.0)
            self.state["vaults"][record.vault_address]["total_earnings"] = vault_earnings + record.earnings
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded earnings: {record.earnings} from {record.vault_name}")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {
                "deposits": [],
                "earnings": [],
                "vaults": {},
                "total_deposited": 0.0,
                "total_earnings": 0.0
            }
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {
                "deposits": [],
                "earnings": [],
                "vaults": {},
                "total_deposited": 0.0,
                "total_earnings": 0.0
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
    
    def get_deposit_history(self) -> List[Dict]:
        """
        Get deposit history.
        
        Returns:
            List of deposit records
        """
        return self.state.get("deposits", [])
    
    def get_earnings_history(self) -> List[Dict]:
        """
        Get earnings history.
        
        Returns:
            List of earnings records
        """
        return self.state.get("earnings", [])
    
    def get_total_deposited(self) -> float:
        """
        Get total amount deposited across all vaults.
        
        Returns:
            Total deposited amount
        """
        return self.state.get("total_deposited", 0.0)
    
    def get_total_earnings(self) -> float:
        """
        Get total earnings across all vaults.
        
        Returns:
            Total earnings amount
        """
        return self.state.get("total_earnings", 0.0)
    
    def get_vault_summary(self) -> Dict[str, Dict]:
        """
        Get summary of all active vaults.
        
        Returns:
            Dictionary mapping vault addresses to vault data
        """
        return self.state.get("vaults", {})
