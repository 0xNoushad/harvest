"""
Harvest Trading Strategies

This module contains all trading strategies for the Harvest agent.
Each strategy implements the Strategy interface and provides:
- scan(): Find opportunities
- execute(): Execute opportunities
- get_name(): Return strategy name
"""

from strategies.airdrop_farmer import AirdropFarmer
from strategies.bounty_hunter import BountyHunter
from strategies.liquid_staking import LiquidStaking
from strategies.yield_farmer import YieldFarmer
from strategies.nft_flipper import NFTFlipper

__all__ = ["AirdropFarmer", "BountyHunter", "LiquidStaking", "YieldFarmer", "NFTFlipper"]
