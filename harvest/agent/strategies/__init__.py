"""
Trading strategies for Harvest agent.

Each strategy implements the Strategy interface:
- scan(): Find opportunities
- execute(): Execute trades
"""

from agent.strategies.jupiter_swap import JupiterSwapStrategy
from agent.strategies.marinade_stake import MarinadeStakeStrategy
from agent.strategies.airdrop_hunter import AirdropHunterStrategy

__all__ = [
    'JupiterSwapStrategy',
    'MarinadeStakeStrategy',
    'AirdropHunterStrategy',
]
