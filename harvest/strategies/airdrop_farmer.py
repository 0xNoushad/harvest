"""
Airdrop Farming Strategy

Interacts with DeFi protocols weekly to qualify for potential airdrops.
Supports Drift, MarginFi, and Kamino protocols.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager
from integrations.solana.drift import DriftIntegration
from integrations.solana.marginfi import MarginFiIntegration
from integrations.solana.kamino import KaminoIntegration


logger = logging.getLogger(__name__)


@dataclass
class ProtocolInteraction:
    """Record of a protocol interaction for airdrop farming."""
    protocol: str
    timestamp: datetime
    transaction_hash: Optional[str]
    success: bool
    error: Optional[str] = None


class AirdropFarmer(Strategy):
    """
    Airdrop farming strategy that interacts with protocols weekly.
    
    This strategy makes small transactions with DeFi protocols to qualify
    for potential airdrops. It tracks the last interaction time for each
    protocol and ensures interactions happen at weekly intervals.
    
    Supported protocols:
    - Drift: Perpetual futures and spot trading
    - MarginFi: Lending and borrowing
    - Kamino: Yield vaults
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        protocols: Optional[List[str]] = None,
        interaction_amount: float = 0.01,
        interaction_interval_days: int = 7,
        state_file: Optional[str] = None
    ):
        """
        Initialize airdrop farmer.
        
        Args:
            wallet: WalletManager instance for signing transactions
            protocols: List of protocol names to farm (default: all supported)
            interaction_amount: Amount in SOL/USDC for each interaction (default: 0.01)
            interaction_interval_days: Days between interactions (default: 7)
            state_file: Path to state file for tracking interactions
        """
        self.wallet = wallet
        self.interaction_amount = interaction_amount
        self.interaction_interval_days = interaction_interval_days
        
        # Set up protocols to farm
        if protocols is None:
            self.protocols = ["drift", "marginfi", "kamino"]
        else:
            self.protocols = protocols
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "airdrop_farmer_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Initialize protocol integrations
        self.integrations = self._initialize_integrations()
        
        logger.info(f"AirdropFarmer initialized with protocols: {self.protocols}")
        logger.info(f"Interaction amount: {self.interaction_amount} SOL/USDC")
        logger.info(f"Interaction interval: {self.interaction_interval_days} days")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "airdrop_farmer"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan for protocols that need interaction.
        
        Checks each protocol to see if the interaction interval has passed
        since the last interaction. Returns opportunities for protocols
        that are due for interaction.
        
        Returns:
            List of opportunities for protocols needing interaction
        """
        opportunities = []
        now = datetime.now()
        
        for protocol in self.protocols:
            try:
                # Check if interaction is due
                if self._is_interaction_due(protocol, now):
                    opportunity = Opportunity(
                        strategy_name=self.get_name(),
                        action="farm",
                        amount=self.interaction_amount,
                        expected_profit=0.0,  # Airdrop value is unknown
                        risk_level="low",
                        details={
                            "protocol": protocol,
                            "interaction_type": "deposit",
                            "last_interaction": self._get_last_interaction_time(protocol)
                        },
                        timestamp=now
                    )
                    opportunities.append(opportunity)
                    logger.info(f"Protocol '{protocol}' is due for interaction")
                else:
                    last_time = self._get_last_interaction_time(protocol)
                    if last_time:
                        days_since = (now - last_time).days
                        logger.debug(f"Protocol '{protocol}' last interacted {days_since} days ago")
            
            except Exception as e:
                logger.error(f"Error checking protocol '{protocol}': {e}")
                # Continue with other protocols
                continue
        
        logger.info(f"Found {len(opportunities)} protocols due for interaction")
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute airdrop farming interaction.
        
        Creates and sends a small transaction to the specified protocol
        to maintain activity for airdrop eligibility.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            Execution result with transaction hash and status
        """
        protocol = opportunity.details["protocol"]
        
        try:
            logger.info(f"Executing airdrop farming interaction with {protocol}")
            
            # Get integration for this protocol
            integration = self.integrations.get(protocol)
            if not integration:
                raise ValueError(f"No integration found for protocol: {protocol}")
            
            # Create interaction transaction
            transaction = integration.create_interaction_transaction()
            
            # Sign and send transaction
            tx_hash = await self.wallet.sign_and_send(transaction)
            
            if tx_hash:
                # Record successful interaction
                interaction = ProtocolInteraction(
                    protocol=protocol,
                    timestamp=datetime.now(),
                    transaction_hash=tx_hash,
                    success=True
                )
                self._record_interaction(interaction)
                
                logger.info(f"Successfully interacted with {protocol}: {tx_hash}")
                
                return {
                    "success": True,
                    "transaction_hash": tx_hash,
                    "protocol": protocol,
                    "amount": self.interaction_amount,
                    "timestamp": interaction.timestamp.isoformat()
                }
            else:
                raise Exception("Transaction failed to send")
        
        except Exception as e:
            error_msg = f"Failed to interact with {protocol}: {str(e)}"
            logger.error(error_msg)
            
            # Record failed interaction
            interaction = ProtocolInteraction(
                protocol=protocol,
                timestamp=datetime.now(),
                transaction_hash=None,
                success=False,
                error=str(e)
            )
            self._record_interaction(interaction)
            
            return {
                "success": False,
                "error": error_msg,
                "protocol": protocol,
                "timestamp": interaction.timestamp.isoformat()
            }
    
    def _initialize_integrations(self) -> Dict:
        """
        Initialize protocol integrations.
        
        Returns:
            Dictionary mapping protocol names to integration instances
        """
        integrations = {}
        
        # Note: These integrations need an RPC client
        # For now, we'll create a simple mock RPC client
        # In production, this should use the Helius integration
        
        class MockRPCClient:
            """Mock RPC client for testing."""
            def get_account_info(self, address):
                return None
            
            def get_latest_blockhash(self):
                return {"blockhash": "mock_blockhash"}
        
        rpc_client = MockRPCClient()
        wallet_pubkey = self.wallet.public_key
        
        if "drift" in self.protocols:
            integrations["drift"] = DriftIntegration(rpc_client, wallet_pubkey)
        
        if "marginfi" in self.protocols:
            integrations["marginfi"] = MarginFiIntegration(rpc_client, wallet_pubkey)
        
        if "kamino" in self.protocols:
            integrations["kamino"] = KaminoIntegration(rpc_client, wallet_pubkey)
        
        return integrations
    
    def _is_interaction_due(self, protocol: str, now: datetime) -> bool:
        """
        Check if interaction is due for a protocol.
        
        Args:
            protocol: Protocol name
            now: Current datetime
        
        Returns:
            True if interaction is due, False otherwise
        """
        last_time = self._get_last_interaction_time(protocol)
        
        if last_time is None:
            # Never interacted, so it's due
            return True
        
        # Check if interval has passed
        time_since = now - last_time
        return time_since.days >= self.interaction_interval_days
    
    def _get_last_interaction_time(self, protocol: str) -> Optional[datetime]:
        """
        Get the last interaction time for a protocol.
        
        Args:
            protocol: Protocol name
        
        Returns:
            Last interaction datetime or None if never interacted
        """
        interactions = self.state.get("interactions", {}).get(protocol, [])
        
        if not interactions:
            return None
        
        # Get the most recent successful interaction
        successful = [i for i in interactions if i.get("success", False)]
        if not successful:
            return None
        
        # Sort by timestamp and get most recent
        successful.sort(key=lambda x: x["timestamp"], reverse=True)
        timestamp_str = successful[0]["timestamp"]
        
        return datetime.fromisoformat(timestamp_str)
    
    def _record_interaction(self, interaction: ProtocolInteraction):
        """
        Record a protocol interaction to state.
        
        Args:
            interaction: ProtocolInteraction to record
        """
        protocol = interaction.protocol
        
        # Initialize protocol interactions list if needed
        if "interactions" not in self.state:
            self.state["interactions"] = {}
        
        if protocol not in self.state["interactions"]:
            self.state["interactions"][protocol] = []
        
        # Add interaction record
        record = {
            "timestamp": interaction.timestamp.isoformat(),
            "transaction_hash": interaction.transaction_hash,
            "success": interaction.success,
            "error": interaction.error
        }
        
        self.state["interactions"][protocol].append(record)
        
        # Keep only last 10 interactions per protocol
        self.state["interactions"][protocol] = self.state["interactions"][protocol][-10:]
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded interaction for {protocol}")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {"interactions": {}}
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {"interactions": {}}
    
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
    
    def get_interaction_history(self, protocol: Optional[str] = None) -> List[Dict]:
        """
        Get interaction history.
        
        Args:
            protocol: Optional protocol name to filter by
        
        Returns:
            List of interaction records
        """
        if protocol:
            return self.state.get("interactions", {}).get(protocol, [])
        else:
            # Return all interactions
            all_interactions = []
            for proto, interactions in self.state.get("interactions", {}).items():
                for interaction in interactions:
                    interaction["protocol"] = proto
                    all_interactions.append(interaction)
            return all_interactions
