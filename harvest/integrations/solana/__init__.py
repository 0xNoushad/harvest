"""
Solana Protocol Integrations

This module provides integration wrappers for various Solana protocols:
- Helius: Enhanced RPC client with authentication
- Marinade: Liquid staking protocol
- Kamino: Yield farming vaults
- Jupiter: Token swap aggregator
- Orca: Decentralized exchange
- Drift: Perpetual futures and spot trading
- MarginFi: Lending and borrowing protocol
"""

from .helius import HeliusClient
from .marinade import MarinadeIntegration
from .kamino import KaminoIntegration, VaultInfo
from .jupiter import JupiterIntegration, SwapRoute
from .orca import OrcaIntegration, OrcaQuote
from .drift import DriftIntegration
from .marginfi import MarginFiIntegration, MarginfiPool


__all__ = [
    "HeliusClient",
    "MarinadeIntegration",
    "KaminoIntegration",
    "VaultInfo",
    "JupiterIntegration",
    "SwapRoute",
    "OrcaIntegration",
    "OrcaQuote",
    "DriftIntegration",
    "MarginFiIntegration",
    "MarginfiPool",
]
