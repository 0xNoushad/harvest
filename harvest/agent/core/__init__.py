"""
Core Infrastructure

Essential components for the Harvest bot:
- Configuration management
- Database operations
- Wallet management
- AI provider
"""

import os

from .config import load_config, check_startup_requirements
from .wallet import WalletManager
from .provider import GroqProvider

# Use Convex if CONVEX_URL is set, otherwise fall back to SQLite
if os.getenv("CONVEX_URL"):
    from .convex_db import ConvexDB as Database
else:
    from .database import Database

__all__ = [
    'load_config',
    'check_startup_requirements',
    'Database',
    'WalletManager',
    'GroqProvider',
]
