"""
NFT Flipping Strategy

Monitors Magic Eden for underpriced NFTs and flips them for profit.
Buys NFTs below floor price and lists them at floor for quick sale.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager
from integrations.nft.magic_eden import MagicEdenIntegration, NFTListing


logger = logging.getLogger(__name__)


@dataclass
class FlipRecord:
    """Record of an NFT flip operation."""
    nft_mint: str
    collection: str
    buy_price: float
    list_price: float
    buy_tx_hash: Optional[str]
    list_tx_hash: Optional[str]
    sell_tx_hash: Optional[str]
    profit: float
    timestamp: datetime
    status: str  # "purchased", "listed", "sold", "failed"
    error: Optional[str] = None


class NFTFlipper(Strategy):
    """
    NFT flipping strategy that buys underpriced NFTs and sells at floor.
    
    This strategy monitors top NFT collections on Magic Eden for listings
    priced below floor. When found, it purchases the NFT and immediately
    lists it at floor price for a quick flip.
    
    Features:
    - Monitors top 10 collections by volume
    - 10% minimum profit threshold
    - Automatic listing at floor price
    - Maximum position size: 1 SOL per NFT
    - Profit tracking and recording
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        collections: Optional[List[str]] = None,
        profit_threshold: float = 0.10,
        max_position_size: float = 1.0,
        top_collections_count: int = 10,
        state_file: Optional[str] = None
    ):
        """
        Initialize NFT flipping strategy.
        
        Args:
            wallet: WalletManager instance for signing transactions
            collections: List of collection symbols to monitor (default: top 10)
            profit_threshold: Minimum profit percentage (default: 0.10 = 10%)
            max_position_size: Maximum SOL per NFT (default: 1.0)
            top_collections_count: Number of top collections to monitor (default: 10)
            state_file: Path to state file for tracking flips
        """
        self.wallet = wallet
        self.profit_threshold = profit_threshold
        self.max_position_size = max_position_size
        self.top_collections_count = top_collections_count
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "nft_flipper_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Initialize Magic Eden integration
        self.magic_eden = self._initialize_magic_eden()
        
        # Set collections to monitor
        if collections is None:
            # Will fetch top collections dynamically
            self.collections = []
        else:
            self.collections = collections
        
        logger.info(f"NFTFlipper initialized")
        logger.info(f"Profit threshold: {self.profit_threshold * 100}%")
        logger.info(f"Max position size: {self.max_position_size} SOL")
        logger.info(f"Monitoring top {self.top_collections_count} collections")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "nft_flipper"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan Magic Eden for underpriced NFTs.
        
        Monitors top collections by volume and finds NFTs listed below
        floor price with sufficient profit potential.
        
        Returns:
            List of opportunities for underpriced NFTs
        """
        opportunities = []
        
        try:
            # Get collections to monitor
            collections_to_check = self._get_collections_to_monitor()
            
            logger.info(f"Scanning {len(collections_to_check)} collections for underpriced NFTs")
            
            # Check each collection
            for collection_symbol in collections_to_check:
                try:
                    # Find underpriced NFTs in this collection
                    underpriced = self.magic_eden.find_underpriced_nfts(
                        collection_symbol=collection_symbol,
                        discount_threshold=self.profit_threshold,
                        limit=50
                    )
                    
                    # Create opportunities for valid NFTs
                    for listing in underpriced:
                        # Check if price is within our position size limit
                        if listing.price > self.max_position_size:
                            logger.debug(
                                f"NFT {listing.mint} price {listing.price} exceeds "
                                f"max position size {self.max_position_size}"
                            )
                            continue
                        
                        # Calculate profit potential
                        profit = self._calculate_profit(listing)
                        profit_pct = profit / listing.price if listing.price > 0 else 0
                        
                        # Verify profit meets threshold
                        if profit_pct >= self.profit_threshold:
                            opportunity = Opportunity(
                                strategy_name=self.get_name(),
                                action="flip",
                                amount=listing.price,
                                expected_profit=profit,
                                risk_level="medium",
                                details={
                                    "nft_mint": listing.mint,
                                    "collection": listing.collection,
                                    "buy_price": listing.price,
                                    "floor_price": listing.floor_price,
                                    "list_price": listing.floor_price,
                                    "profit": profit,
                                    "profit_percentage": profit_pct * 100,
                                    "seller": listing.seller,
                                    "listing": listing
                                },
                                timestamp=datetime.now()
                            )
                            opportunities.append(opportunity)
                            logger.info(
                                f"Found flip opportunity: {listing.collection} NFT at "
                                f"{listing.price} SOL (floor: {listing.floor_price} SOL, "
                                f"profit: {profit_pct*100:.1f}%)"
                            )
                
                except Exception as e:
                    logger.error(f"Error scanning collection '{collection_symbol}': {e}")
                    # Continue with other collections
                    continue
            
            logger.info(f"Found {len(opportunities)} NFT flip opportunities")
        
        except Exception as e:
            logger.error(f"Error scanning for NFT opportunities: {e}")
        
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute NFT flip operation.
        
        Purchases the underpriced NFT and immediately lists it at floor price.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            Execution result with transaction hashes and profit
        """
        nft_mint = opportunity.details["nft_mint"]
        collection = opportunity.details["collection"]
        buy_price = opportunity.details["buy_price"]
        list_price = opportunity.details["list_price"]
        listing = opportunity.details["listing"]
        
        try:
            logger.info(f"Flipping NFT {nft_mint} from {collection}")
            logger.info(f"Buy: {buy_price} SOL, List: {list_price} SOL")
            
            # Step 1: Purchase the NFT
            buy_tx_hash = await self.buy_nft(listing)
            
            if not buy_tx_hash:
                raise Exception("Failed to purchase NFT")
            
            logger.info(f"Purchased NFT: {buy_tx_hash}")
            
            # Step 2: List the NFT at floor price
            try:
                list_tx_hash = await self.list_nft(nft_mint, list_price, collection)
                
                if not list_tx_hash:
                    raise Exception("Failed to send listing transaction")
            
            except Exception as list_error:
                logger.warning(f"Failed to list NFT, but purchase succeeded: {list_error}")
                # Record partial success
                record = FlipRecord(
                    nft_mint=nft_mint,
                    collection=collection,
                    buy_price=buy_price,
                    list_price=list_price,
                    buy_tx_hash=buy_tx_hash,
                    list_tx_hash=None,
                    sell_tx_hash=None,
                    profit=0.0,
                    timestamp=datetime.now(),
                    status="purchased",
                    error=f"Failed to list NFT: {str(list_error)}"
                )
                self._record_flip(record)
                
                return {
                    "success": False,
                    "buy_transaction_hash": buy_tx_hash,
                    "list_transaction_hash": None,
                    "nft_mint": nft_mint,
                    "collection": collection,
                    "buy_price": buy_price,
                    "error": f"NFT purchased but listing failed: {str(list_error)}",
                    "timestamp": record.timestamp.isoformat()
                }
            
            logger.info(f"Listed NFT at {list_price} SOL: {list_tx_hash}")
            
            # Calculate expected profit (actual profit realized when sold)
            expected_profit = self._calculate_profit(listing)
            
            # Record successful flip
            record = FlipRecord(
                nft_mint=nft_mint,
                collection=collection,
                buy_price=buy_price,
                list_price=list_price,
                buy_tx_hash=buy_tx_hash,
                list_tx_hash=list_tx_hash,
                sell_tx_hash=None,  # Will be updated when sold
                profit=expected_profit,
                timestamp=datetime.now(),
                status="listed"
            )
            self._record_flip(record)
            
            return {
                "success": True,
                "buy_transaction_hash": buy_tx_hash,
                "list_transaction_hash": list_tx_hash,
                "nft_mint": nft_mint,
                "collection": collection,
                "buy_price": buy_price,
                "list_price": list_price,
                "expected_profit": expected_profit,
                "status": "listed",
                "timestamp": record.timestamp.isoformat()
            }
        
        except Exception as e:
            error_msg = f"Failed to flip NFT {nft_mint}: {str(e)}"
            logger.error(error_msg)
            
            # Record failed flip
            record = FlipRecord(
                nft_mint=nft_mint,
                collection=collection,
                buy_price=buy_price,
                list_price=list_price,
                buy_tx_hash=None,
                list_tx_hash=None,
                sell_tx_hash=None,
                profit=0.0,
                timestamp=datetime.now(),
                status="failed",
                error=str(e)
            )
            self._record_flip(record)
            
            return {
                "success": False,
                "error": error_msg,
                "nft_mint": nft_mint,
                "collection": collection,
                "timestamp": record.timestamp.isoformat()
            }
    
    async def buy_nft(self, listing: NFTListing) -> str:
        """
        Purchase an NFT.
        
        Args:
            listing: NFTListing object with purchase details
        
        Returns:
            Transaction hash of the purchase
        
        Raises:
            Exception: If purchase fails
        """
        try:
            logger.info(f"Purchasing NFT {listing.mint} at {listing.price} SOL")
            
            # Create purchase transaction
            transaction = self.magic_eden.create_purchase_transaction(
                listing=listing,
                buyer_price=listing.price
            )
            
            # Sign and send transaction
            tx_hash = await self.wallet.sign_and_send(transaction)
            
            if not tx_hash:
                raise Exception("Failed to send purchase transaction")
            
            logger.info(f"Purchased NFT {listing.mint}")
            return tx_hash
        
        except Exception as e:
            error_msg = f"Failed to purchase NFT: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def list_nft(
        self,
        nft_mint: str,
        price: float,
        collection: Optional[str] = None
    ) -> str:
        """
        List an NFT for sale at specified price.
        
        Args:
            nft_mint: NFT mint address
            price: Listing price in SOL
            collection: Optional collection symbol
        
        Returns:
            Transaction hash of the listing
        
        Raises:
            Exception: If listing fails
        """
        try:
            logger.info(f"Listing NFT {nft_mint} at {price} SOL")
            
            # Create listing transaction
            transaction = self.magic_eden.create_listing_transaction(
                nft_mint=nft_mint,
                price_sol=price,
                collection_symbol=collection
            )
            
            # Sign and send transaction
            tx_hash = await self.wallet.sign_and_send(transaction)
            
            if not tx_hash:
                raise Exception("Failed to send listing transaction")
            
            logger.info(f"Listed NFT {nft_mint} at {price} SOL")
            return tx_hash
        
        except Exception as e:
            error_msg = f"Failed to list NFT: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _get_collections_to_monitor(self) -> List[str]:
        """
        Get list of collections to monitor.
        
        If collections were specified in constructor, use those.
        Otherwise, fetch top collections by volume.
        
        Returns:
            List of collection symbols
        """
        if self.collections:
            return self.collections
        
        try:
            # Fetch top collections by 24h volume
            logger.info(f"Fetching top {self.top_collections_count} collections")
            top_collections = self.magic_eden.get_top_collections(
                limit=self.top_collections_count,
                timeframe="24h"
            )
            
            # Extract collection symbols
            symbols = [c.get("symbol", "") for c in top_collections if c.get("symbol")]
            
            logger.info(f"Monitoring collections: {symbols}")
            return symbols
        
        except Exception as e:
            logger.error(f"Failed to fetch top collections: {e}")
            # Fallback to popular Solana NFT collections
            fallback_collections = [
                "degods",
                "okay_bears",
                "mad_lads",
                "tensorians",
                "famous_fox_federation",
                "solana_monkey_business",
                "abc",
                "claynosaurz",
                "sharky_fi",
                "lifinity_flares"
            ][:self.top_collections_count]
            
            logger.info(f"Using fallback collections: {fallback_collections}")
            return fallback_collections
    
    def _calculate_profit(self, listing: NFTListing) -> float:
        """
        Calculate expected profit from flipping an NFT.
        
        Profit = (Floor Price - Buy Price) - Fees
        
        Args:
            listing: NFTListing object
        
        Returns:
            Expected profit in SOL
        """
        # Magic Eden charges 2% marketplace fee
        marketplace_fee_rate = 0.02
        
        # Calculate gross profit
        gross_profit = listing.floor_price - listing.price
        
        # Subtract marketplace fee (on the sell side)
        marketplace_fee = listing.floor_price * marketplace_fee_rate
        
        # Net profit
        net_profit = gross_profit - marketplace_fee
        
        return net_profit
    
    def _initialize_magic_eden(self) -> MagicEdenIntegration:
        """
        Initialize Magic Eden integration.
        
        Returns:
            MagicEdenIntegration instance
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
        
        return MagicEdenIntegration(rpc_client, self.wallet.public_key)
    
    def _record_flip(self, record: FlipRecord):
        """
        Record an NFT flip to state.
        
        Args:
            record: FlipRecord to save
        """
        # Initialize flips list if needed
        if "flips" not in self.state:
            self.state["flips"] = []
        
        # Add flip record
        flip_data = {
            "nft_mint": record.nft_mint,
            "collection": record.collection,
            "buy_price": record.buy_price,
            "list_price": record.list_price,
            "buy_tx_hash": record.buy_tx_hash,
            "list_tx_hash": record.list_tx_hash,
            "sell_tx_hash": record.sell_tx_hash,
            "profit": record.profit,
            "timestamp": record.timestamp.isoformat(),
            "status": record.status,
            "error": record.error
        }
        
        self.state["flips"].append(flip_data)
        
        # Keep only last 100 flips
        self.state["flips"] = self.state["flips"][-100:]
        
        # Update total profit for successful flips
        if record.status == "sold":
            total_profit = self.state.get("total_profit", 0.0)
            self.state["total_profit"] = total_profit + record.profit
        
        # Save state
        self._save_state()
        
        logger.debug(f"Recorded flip for {record.nft_mint}")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {"flips": [], "total_profit": 0.0}
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {"flips": [], "total_profit": 0.0}
    
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
    
    def get_flip_history(self, collection: Optional[str] = None) -> List[Dict]:
        """
        Get flip history.
        
        Args:
            collection: Optional collection symbol to filter by
        
        Returns:
            List of flip records
        """
        flips = self.state.get("flips", [])
        
        if collection:
            return [f for f in flips if f["collection"] == collection]
        else:
            return flips
    
    def get_total_profit(self) -> float:
        """
        Get total profit from all flips.
        
        Returns:
            Total profit in SOL
        """
        return self.state.get("total_profit", 0.0)
    
    def get_active_listings(self) -> List[Dict]:
        """
        Get currently active NFT listings.
        
        Returns:
            List of flip records with status "listed"
        """
        flips = self.state.get("flips", [])
        return [f for f in flips if f.get("status") == "listed"]
