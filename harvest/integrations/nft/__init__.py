"""
NFT Platform Integrations

Provides integrations with NFT marketplaces and platforms.
"""

from integrations.nft.magic_eden import (
    MagicEdenIntegration,
    NFTListing,
    CollectionStats
)

__all__ = [
    "MagicEdenIntegration",
    "NFTListing",
    "CollectionStats"
]
