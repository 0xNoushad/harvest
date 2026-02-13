# Agent Folder Structure

## Core (`core/`)
- `config.py` - Configuration management
- `database.py` - Database operations
- `wallet.py` - Wallet management
- `provider.py` - AI provider (Groq)

## Services (`services/`)
- `price_service.py` - Crypto price fetching
- `portfolio_service.py` - Portfolio analysis
- `notifier.py` - Notification service
- `user_manager.py` - User management

## Trading (`trading/`)
- `loop.py` - Main trading loop
- `scanner.py` - Opportunity scanner
- `risk_manager.py` - Risk management
- `performance.py` - Performance tracking

## Security (`security/`)
- `security.py` - Security validation
- `advanced_security.py` - Advanced security features
- `multi_wallet_manager.py` - Multi-wallet security

## Monitoring (`monitoring/`)
- `monthly_fees.py` - Fee collection
- `user_control.py` - User controls

## Handlers (`handlers/`)
- `message_handler.py` - Message processing

## UI (`ui/`)
- `telegram_ui.py` - Telegram UI components
- `telegram_bot.py` - Telegram bot

## Root
- `main.py` - Entry point
- `context.py` - Context management
- `logging_config.py` - Logging setup
- `wallet_setup.py` - Wallet setup utility
- `fee_notification.py` - Fee notifications
