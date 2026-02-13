# Agent Architecture

Clean, modular structure for the Harvest trading bot.

## Folder Structure

```
agent/
├── core/                   # Core infrastructure
│   ├── config.py          # Configuration management
│   ├── database.py        # Database operations
│   ├── wallet.py          # Wallet management
│   └── provider.py        # AI provider (Groq)
│
├── services/              # Business logic services
│   ├── price_service.py   # Crypto price fetching
│   ├── portfolio_service.py # Portfolio analysis
│   ├── notifier.py        # Notifications
│   └── user_manager.py    # User management
│
├── trading/               # Trading logic
│   ├── loop.py           # Main trading loop
│   ├── scanner.py        # Opportunity scanner
│   ├── risk_manager.py   # Risk management
│   └── performance.py    # Performance tracking
│
├── security/              # Security features
│   ├── security.py       # Security validation
│   ├── advanced_security.py # Advanced features
│   └── multi_wallet_manager.py # Multi-wallet security
│
├── monitoring/            # Monitoring & control
│   ├── monthly_fees.py   # Fee collection
│   └── user_control.py   # User controls
│
├── handlers/              # Request handlers
│   └── message_handler.py # Message processing
│
├── ui/                    # User interface
│   ├── telegram_bot.py   # Telegram bot
│   └── telegram_ui.py    # UI components
│
└── main.py               # Entry point
```

## Design Principles

1. **Separation of Concerns** - Each folder has a single responsibility
2. **Modularity** - Services are independent and reusable
3. **Scalability** - Easy to add new features without bloating existing code
4. **Maintainability** - Clear structure makes bugs easy to find and fix

## Import Pattern

```python
# Core
from agent.core.database import Database
from agent.core.wallet import WalletManager

# Services
from agent.services.price_service import PriceService
from agent.services.user_manager import UserManager

# Trading
from agent.trading.loop import AgentLoop
from agent.trading.scanner import Scanner

# Security
from agent.security.security import SecurityValidator

# Monitoring
from agent.monitoring.monthly_fees import MonthlyFeeCollector

# Handlers
from agent.handlers.message_handler import MessageHandler

# UI
from agent.ui.telegram_bot import TelegramBot
```

## Adding New Features

1. **New Service** → Add to `services/`
2. **New Trading Strategy** → Add to `trading/`
3. **New Security Feature** → Add to `security/`
4. **New UI Component** → Add to `ui/`
5. **New Handler** → Add to `handlers/`

Each module stays focused and clean!
