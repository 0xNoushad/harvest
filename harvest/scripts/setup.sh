#!/bin/bash

set -e  # Exit on error

echo "🌾 HARVEST - Setup Script"
echo "=========================="
echo ""

# Parse command line arguments
ENVIRONMENT=${1:-development}
SKIP_TESTS=${2:-false}

echo "Environment: $ENVIRONMENT"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.8"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.8+ required, found $python_version"
    exit 1
fi
echo "✅ Python $python_version"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p logs
mkdir -p config
mkdir -p data
echo "✅ Directories created"
echo ""

# Handle environment configuration
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Setting up production environment..."
    
    # Check if .env exists
    if [ ! -f ".env" ]; then
        echo "❌ .env file not found"
        echo "For production, you must provide a .env file with all required variables"
        echo "See .env.production.template for required variables"
        exit 1
    fi
    
    # Validate environment variables
    echo "Validating environment variables..."
    python3 -c "
import sys
sys.path.insert(0, '.')
from harvest.agent.config import validate_environment
try:
    validate_environment(require_all=True)
    print('✅ All required environment variables are set')
except Exception as e:
    print(f'❌ Environment validation failed: {e}')
    sys.exit(1)
"
    
else
    echo "Setting up development environment..."
    
    # Check .env file
    if [ ! -f ".env" ]; then
        echo "⚠️  .env file not found"
        echo "Creating .env from template..."
        if [ -f ".env.template" ]; then
            cp .env.template .env
        else
            cat > .env << 'EOF'
# Telegram Bot (from @BotFather)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Groq API (FREE from console.groq.com)
GROQ_API_KEY=

# Solana
HELIUS_API_KEY=
SOLANA_NETWORK=devnet

# Wallet (generated automatically for devnet)
WALLET_ADDRESS=
WALLET_PRIVATE_KEY=

# Logging
LOG_LEVEL=INFO
CONSOLE_LOG_LEVEL=INFO

# Optional: Discord notifications
DISCORD_WEBHOOK_URL=
EOF
        fi
        echo "✅ .env file created"
        echo ""
        echo "📝 Please edit .env and add your API keys:"
        echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
        echo "   - TELEGRAM_CHAT_ID (run: python scripts/get_chat_id.py)"
        echo "   - GROQ_API_KEY (from console.groq.com)"
        echo ""
    else
        echo "✅ .env file exists"
        
        # Validate environment variables (warnings only for dev)
        echo "Validating environment variables..."
        python3 -c "
import sys
sys.path.insert(0, '.')
from harvest.agent.config import validate_environment
try:
    validate_environment(require_all=False)
    print('✅ Environment variables validated')
except Exception as e:
    print(f'⚠️  Warning: {e}')
    print('   Some features may not work without all variables set')
"
    fi
fi
echo ""

# Run tests if not skipped
if [ "$SKIP_TESTS" != "true" ]; then
    echo "Running basic tests..."
    
    # Test imports
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from harvest.agent.wallet import WalletManager
    from harvest.agent.loop import AgentLoop
    from harvest.agent.provider import GroqProvider
    from harvest.agent.notifier import TelegramNotifier
    from harvest.agent.scanner import OpportunityScanner
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)
"
    
    # Test wallet connection (devnet only)
    if [ "$ENVIRONMENT" != "production" ]; then
        echo "Testing wallet connection..."
        python3 -c "
import asyncio
import sys
sys.path.insert(0, '.')
from harvest.agent.wallet import WalletManager

async def test():
    try:
        wallet = WalletManager(network='devnet')
        print(f'✅ Wallet: {wallet.public_key}')
        balance = await wallet.get_balance()
        print(f'✅ Balance: {balance} SOL')
        await wallet.close()
    except Exception as e:
        print(f'⚠️  Wallet test failed: {e}')
        print('   This is normal if you haven\'t configured a wallet yet')

asyncio.run(test())
" || true
    fi
fi
echo ""

echo "✅ Setup complete!"
echo ""

if [ "$ENVIRONMENT" = "production" ]; then
    echo "Production environment ready!"
    echo "Start the agent with: python -m harvest.agent.main"
else
    echo "Development environment ready!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env and add your API keys"
    echo "2. Get your Telegram chat ID: python scripts/get_chat_id.py"
    echo "3. Run the agent: python -m harvest.agent.main"
    echo ""
    echo "For production deployment:"
    echo "  ./scripts/setup.sh production"
fi
echo ""
