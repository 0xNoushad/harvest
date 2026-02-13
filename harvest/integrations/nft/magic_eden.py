"""
Magic Eden NFT Marketplace Integration

Provides API wrapper for Magic Eden NFT marketplace.
Supports NFT price queries, purchases, and listings.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import requests
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.instruction import Instruction, AccountMeta


logger = logging.getLogger(__name__)


# Magic Eden API endpoints
MAGIC_EDEN_API_V2 = "https://api-mainnet.magiceden.dev/v2"
MAGIC_EDEN_API_V3 = "https://api-mainnet.magiceden.dev/v3"


@dataclass
class NFTListing:
    """Information about an NFT listing."""
    mint: str
    collection: str
    price: float
    floor_price: float
    seller: str
    listing_address: Optional[str] = None
    token_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CollectionStats:
    """Statistics for an NFT collection."""
    symbol: str
    floor_price: float
    listed_count: int
    volume_24h: float
    avg_price_24h: float


class MagicEdenIntegration:
    """
    Magic Eden NFT marketplace integration.
    
    Provides methods to:
    - Query NFT floor prices
    - Find underpriced listings
    - Purchase NFTs
    - List NFTs for sale
    - Query collection statistics
    """
    
    def __init__(self, rpc_client, wallet_pubkey: Pubkey, api_key: Optional[str] = None):
        """
        Initialize Magic Eden integration.
        
        Args:
            rpc_client: Helius RPC client instance
            wallet_pubkey: User's wallet public key
            api_key: Optional Magic Eden API key for higher rate limits
        """
        self.rpc_client = rpc_client
        self.wallet_pubkey = wallet_pubkey
        self.api_key = api_key
        self.api_v2_base = MAGIC_EDEN_API_V2
        self.api_v3_base = MAGIC_EDEN_API_V3
        self.session = requests.Session()
        
        # Set API key header if provided
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
        
        logger.info(f"Initialized Magic Eden integration for wallet {wallet_pubkey}")
    
    def get_collection_stats(self, collection_symbol: str) -> CollectionStats:
        """
        Get statistics for an NFT collection.
        
        Args:
            collection_symbol: Collection symbol (e.g., "degods", "okay_bears")
        
        Returns:
            CollectionStats with floor price and volume data
        
        Raises:
            Exception: If stats query fails
        """
        try:
            logger.info(f"Getting stats for collection: {collection_symbol}")
            
            response = self.session.get(
                f"{self.api_v2_base}/collections/{collection_symbol}/stats",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            stats = CollectionStats(
                symbol=collection_symbol,
                floor_price=float(data.get("floorPrice", 0)) / 1e9,  # Convert lamports to SOL
                listed_count=int(data.get("listedCount", 0)),
                volume_24h=float(data.get("volume24hr", 0)) / 1e9,
                avg_price_24h=float(data.get("avgPrice24hr", 0)) / 1e9
            )
            
            logger.info(f"Collection {collection_symbol} floor: {stats.floor_price} SOL")
            return stats
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get collection stats for {collection_symbol}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse collection stats: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_collection_listings(
        self,
        collection_symbol: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[NFTListing]:
        """
        Get current listings for a collection.
        
        Args:
            collection_symbol: Collection symbol
            limit: Maximum number of listings to return (default 20)
            offset: Pagination offset (default 0)
        
        Returns:
            List of NFTListing objects
        
        Raises:
            Exception: If listings query fails
        """
        try:
            logger.info(f"Getting listings for collection: {collection_symbol}")
            
            # First get collection stats for floor price
            stats = self.get_collection_stats(collection_symbol)
            
            # Query listings
            params = {
                "offset": offset,
                "limit": limit
            }
            
            response = self.session.get(
                f"{self.api_v2_base}/collections/{collection_symbol}/listings",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            listings = []
            for item in data:
                listing = NFTListing(
                    mint=item.get("tokenMint", ""),
                    collection=collection_symbol,
                    price=float(item.get("price", 0)),
                    floor_price=stats.floor_price,
                    seller=item.get("seller", ""),
                    listing_address=item.get("pdaAddress"),
                    token_address=item.get("tokenAddress"),
                    metadata=item.get("extra", {})
                )
                listings.append(listing)
            
            logger.info(f"Found {len(listings)} listings for {collection_symbol}")
            return listings
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get listings for {collection_symbol}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse listings: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def find_underpriced_nfts(
        self,
        collection_symbol: str,
        discount_threshold: float = 0.10,
        limit: int = 50
    ) -> List[NFTListing]:
        """
        Find NFTs listed below floor price.
        
        Args:
            collection_symbol: Collection symbol
            discount_threshold: Minimum discount from floor (default 0.10 = 10%)
            limit: Maximum listings to check
        
        Returns:
            List of underpriced NFTListing objects
        
        Raises:
            Exception: If search fails
        """
        try:
            logger.info(f"Searching for underpriced NFTs in {collection_symbol}")
            
            # Get all listings
            listings = self.get_collection_listings(collection_symbol, limit=limit)
            
            # Filter for underpriced
            underpriced = []
            for listing in listings:
                if listing.floor_price > 0:
                    discount = (listing.floor_price - listing.price) / listing.floor_price
                    if discount >= discount_threshold:
                        underpriced.append(listing)
                        logger.info(
                            f"Found underpriced NFT: {listing.mint} "
                            f"at {listing.price} SOL ({discount*100:.1f}% below floor)"
                        )
            
            logger.info(f"Found {len(underpriced)} underpriced NFTs")
            return underpriced
        
        except Exception as e:
            error_msg = f"Failed to find underpriced NFTs: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_nft_details(self, mint_address: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific NFT.
        
        Args:
            mint_address: NFT mint address
        
        Returns:
            Dictionary with NFT details
        
        Raises:
            Exception: If details query fails
        """
        try:
            logger.info(f"Getting details for NFT: {mint_address}")
            
            response = self.session.get(
                f"{self.api_v2_base}/tokens/{mint_address}",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Retrieved details for NFT {mint_address}")
            return data
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get NFT details for {mint_address}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse NFT details: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_purchase_transaction(
        self,
        listing: NFTListing,
        buyer_price: float
    ) -> Transaction:
        """
        Create a transaction to purchase an NFT.
        
        Args:
            listing: NFTListing object with purchase details
            buyer_price: Maximum price buyer is willing to pay (in SOL)
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            ValueError: If buyer price is less than listing price
            Exception: If transaction creation fails
        """
        if buyer_price < listing.price:
            raise ValueError(
                f"Buyer price {buyer_price} is less than listing price {listing.price}"
            )
        
        try:
            logger.info(f"Creating purchase transaction for NFT {listing.mint} at {listing.price} SOL")
            
            # In production, this would call Magic Eden's buy API
            # to get the actual transaction instructions
            # For now, create a placeholder transaction structure
            
            # Magic Eden V2 uses a program-based escrow system
            # The actual implementation would:
            # 1. Call Magic Eden API to get buy instructions
            # 2. Parse the returned transaction
            # 3. Add buyer's signature
            
            # Placeholder instruction
            instruction = self._create_buy_instruction(
                listing.mint,
                listing.seller,
                int(listing.price * 1e9)  # Convert to lamports
            )
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created purchase transaction for NFT {listing.mint}")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create purchase transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def create_listing_transaction(
        self,
        nft_mint: str,
        price_sol: float,
        collection_symbol: Optional[str] = None
    ) -> Transaction:
        """
        Create a transaction to list an NFT for sale.
        
        Args:
            nft_mint: NFT mint address
            price_sol: Listing price in SOL
            collection_symbol: Optional collection symbol for verification
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            ValueError: If price is not positive
            Exception: If transaction creation fails
        """
        if price_sol <= 0:
            raise ValueError("Listing price must be positive")
        
        try:
            logger.info(f"Creating listing transaction for NFT {nft_mint} at {price_sol} SOL")
            
            # In production, this would call Magic Eden's list API
            # to get the actual transaction instructions
            
            # The actual implementation would:
            # 1. Call Magic Eden API to get list instructions
            # 2. Parse the returned transaction
            # 3. Add seller's signature
            
            # Placeholder instruction
            instruction = self._create_list_instruction(
                nft_mint,
                int(price_sol * 1e9)  # Convert to lamports
            )
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created listing transaction for NFT {nft_mint}")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create listing transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def cancel_listing_transaction(self, nft_mint: str) -> Transaction:
        """
        Create a transaction to cancel an NFT listing.
        
        Args:
            nft_mint: NFT mint address
        
        Returns:
            Unsigned transaction ready to be signed
        
        Raises:
            Exception: If transaction creation fails
        """
        try:
            logger.info(f"Creating cancel listing transaction for NFT {nft_mint}")
            
            # Placeholder instruction
            instruction = self._create_cancel_instruction(nft_mint)
            
            # Create transaction
            transaction = Transaction.new_with_payer(
                [instruction],
                self.wallet_pubkey
            )
            
            logger.info(f"Created cancel listing transaction for NFT {nft_mint}")
            return transaction
        
        except Exception as e:
            error_msg = f"Failed to create cancel listing transaction: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_wallet_nfts(self, wallet_address: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all NFTs owned by a wallet.
        
        Args:
            wallet_address: Wallet address (defaults to connected wallet)
        
        Returns:
            List of NFT metadata dictionaries
        
        Raises:
            Exception: If query fails
        """
        try:
            wallet = wallet_address or str(self.wallet_pubkey)
            logger.info(f"Getting NFTs for wallet: {wallet}")
            
            response = self.session.get(
                f"{self.api_v2_base}/wallets/{wallet}/tokens",
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Found {len(data)} NFTs in wallet {wallet}")
            return data
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get wallet NFTs: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse wallet NFTs: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_top_collections(self, limit: int = 10, timeframe: str = "24h") -> List[Dict[str, Any]]:
        """
        Get top NFT collections by volume.
        
        Args:
            limit: Number of collections to return (default 10)
            timeframe: Time period ("24h", "7d", "30d")
        
        Returns:
            List of collection data dictionaries
        
        Raises:
            Exception: If query fails
        """
        try:
            logger.info(f"Getting top {limit} collections for {timeframe}")
            
            params = {
                "limit": limit,
                "window": timeframe
            }
            
            response = self.session.get(
                f"{self.api_v2_base}/collections",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            logger.info(f"Retrieved {len(data)} top collections")
            return data
        
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to get top collections: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to parse top collections: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _create_buy_instruction(
        self,
        nft_mint: str,
        seller: str,
        price_lamports: int
    ) -> Instruction:
        """
        Create a buy instruction for Magic Eden.
        
        This is a simplified placeholder. Real implementation would use
        Magic Eden's actual program instructions.
        
        Args:
            nft_mint: NFT mint address
            seller: Seller's wallet address
            price_lamports: Price in lamports
        
        Returns:
            Buy instruction
        """
        # Magic Eden program ID (placeholder)
        # Real program ID: M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K
        program_id = Pubkey.from_string("M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K")
        
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=Pubkey.from_string(seller), is_signer=False, is_writable=True),
            AccountMeta(pubkey=Pubkey.from_string(nft_mint), is_signer=False, is_writable=False),
        ]
        
        # Simplified instruction data
        data = price_lamports.to_bytes(8, 'little')
        
        return Instruction(
            program_id=program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_list_instruction(self, nft_mint: str, price_lamports: int) -> Instruction:
        """
        Create a list instruction for Magic Eden.
        
        This is a simplified placeholder.
        
        Args:
            nft_mint: NFT mint address
            price_lamports: Price in lamports
        
        Returns:
            List instruction
        """
        program_id = Pubkey.from_string("M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K")
        
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=Pubkey.from_string(nft_mint), is_signer=False, is_writable=False),
        ]
        
        data = price_lamports.to_bytes(8, 'little')
        
        return Instruction(
            program_id=program_id,
            accounts=accounts,
            data=data
        )
    
    def _create_cancel_instruction(self, nft_mint: str) -> Instruction:
        """
        Create a cancel listing instruction for Magic Eden.
        
        This is a simplified placeholder.
        
        Args:
            nft_mint: NFT mint address
        
        Returns:
            Cancel instruction
        """
        program_id = Pubkey.from_string("M2mx93ekt1fmXSVkTrUL9xVFHkmME8HTUi5Cyc5aF7K")
        
        accounts = [
            AccountMeta(pubkey=self.wallet_pubkey, is_signer=True, is_writable=True),
            AccountMeta(pubkey=Pubkey.from_string(nft_mint), is_signer=False, is_writable=False),
        ]
        
        data = b""
        
        return Instruction(
            program_id=program_id,
            accounts=accounts,
            data=data
        )
