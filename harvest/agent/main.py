"""
🌾 HARVEST - Autonomous Money Hunter Agent

Main agent loop that runs 24/7 hunting for money on Solana
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.trading.loop import AgentLoop
from agent.core.provider import GroqProvider
from agent.trading.scanner import Scanner
from agent.services.notifier import Notifier
from agent.ui.telegram_bot import TelegramBot
from agent.core.wallet import WalletManager
from agent.core.multi_user_wallet import MultiUserWalletManager
from agent.monitoring.user_control import UserControl
from agent.trading.risk_manager import RiskManager
from agent.trading.performance import PerformanceTracker
from agent.trading.transaction_executor import TransactionExecutor
from agent.logging_config import setup_logging, get_logger
from agent.core.config import check_startup_requirements, load_config
from agent.services.user_manager import UserManager
from agent.monitoring.monthly_fees import MonthlyFeeCollector
from agent.core.api_usage_monitor import APIUsageMonitor
from agent.core.multi_api_manager import APIKeyManager
from agent.core.shared_cache import SharedPriceCache, StrategyCache
from agent.core.rpc_fallback import RPCFallbackManager
from agent.core.optimized_scanner import OptimizedScanner

# Import strategies
from agent.strategies import JupiterSwapStrategy, MarinadeStakeStrategy, AirdropHunterStrategy

# Check startup requirements first (validates environment, creates directories)
# Note: This must be called before logging setup to create required directories
check_startup_requirements()

# Load and validate configuration
config = load_config()

# Configure logging
setup_logging(
    log_dir="logs",
    log_level=config.get("LOG_LEVEL", "INFO"),
    console_level=config.get("CONSOLE_LOG_LEVEL", "INFO"),
    enable_compression=True,
    compress_after_days=7,
    retention_days=30,
)

logger = get_logger(__name__)

# Log startup information
logger.info("Harvest Agent initialized")
logger.info(f"Network: {config.get_network()}")
logger.info(f"Scan interval: {config.get_scan_interval()}s")


class HarvestAgent:
    """Main Harvest agent - autonomous money hunter."""
    
    def __init__(self):
        self.workspace = Path(__file__).parent.parent
        
        # Load configuration
        self.config = load_config()
        
        # Get API keys and config from validated environment
        self.groq_api_key = self.config.get("GROQ_API_KEY")
        self.telegram_token = self.config.get("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = self.config.get("TELEGRAM_CHAT_ID")
        self.network = self.config.get_network()
        self.scan_interval = self.config.get_scan_interval()
        
        # Initialize multi-user wallet manager
        self.multi_user_wallet = MultiUserWalletManager(
            network=self.network,
            storage_dir="config/secure_wallets"
        )
        logger.info("MultiUserWalletManager initialized")
        
        # Initialize multi-API scaling components (Requirements 1.1, 2.1, 4.1, 7.1)
        helius_keys = self.config.get_helius_api_keys()
        
        # Create API Usage Monitor (Requirement 2.1)
        self.api_usage_monitor = APIUsageMonitor(daily_limit=3300)
        logger.info(f"API Usage Monitor initialized with daily limit: 3300 requests/key")
        
        # Create API Key Manager with Helius keys (Requirement 1.1)
        if len(helius_keys) >= 3:
            self.api_key_manager = APIKeyManager(
                keys=helius_keys[:3],  # Use first 3 keys
                usage_monitor=self.api_usage_monitor
            )
            logger.info(f"API Key Manager initialized with {len(helius_keys[:3])} Helius keys")
        elif helius_keys:
            # Fallback: use available keys (even if less than 3)
            self.api_key_manager = APIKeyManager(
                keys=helius_keys,
                usage_monitor=self.api_usage_monitor
            )
            logger.warning(f"API Key Manager initialized with only {len(helius_keys)} key(s) - recommend 3 for optimal scaling")
        else:
            self.api_key_manager = None
            logger.warning("No Helius API keys configured - multi-API scaling disabled")
        
        # Create Shared Price Cache (Requirement 4.1)
        price_cache_ttl = self.config.get_price_cache_ttl()
        self.shared_price_cache = SharedPriceCache(ttl=price_cache_ttl)
        logger.info(f"Shared Price Cache initialized with TTL: {price_cache_ttl}s")
        
        # Create Strategy Cache (Requirement 7.1)
        strategy_cache_ttl = self.config.get_strategy_cache_ttl()
        self.strategy_cache = StrategyCache(ttl=strategy_cache_ttl)
        logger.info(f"Strategy Cache initialized with TTL: {strategy_cache_ttl}s")
        
        # Initialize RPC Fallback Manager with API Key Manager integration
        self.rpc_fallback_manager = RPCFallbackManager(
            api_key_manager=self.api_key_manager
        )
        logger.info("RPC Fallback Manager initialized with API Key Manager integration")
        
        # Initialize Optimized Scanner with all optimization components
        self.optimized_scanner = OptimizedScanner(
            rpc_manager=self.rpc_fallback_manager,
            api_key_manager=self.api_key_manager,
            price_cache=self.shared_price_cache,
            strategy_cache=self.strategy_cache
        )
        logger.info("Optimized Scanner initialized with all optimization components")
        
        # Initialize Transaction Executor
        # Note: TransactionExecutor will receive per-user wallet instances from AgentLoop
        self.transaction_executor = TransactionExecutor(
            rpc_client=self.rpc_fallback_manager,
            wallet_manager=None,  # Will be set per-user in AgentLoop
            rpc_fallback_manager=self.rpc_fallback_manager,
            max_retries=self.config.get_max_retries(),
            confirmation_timeout=self.config.get_confirmation_timeout()
        )
        logger.info("Transaction Executor initialized")
        
        # Initialize strategies
        # Note: Strategies will receive per-user wallet instances from AgentLoop
        strategies = [
            JupiterSwapStrategy(
                rpc_client=self.rpc_fallback_manager,
                wallet_manager=None,  # Will be set per-user in AgentLoop
                executor=self.transaction_executor,
                min_profit_threshold=0.01
            ),
            MarinadeStakeStrategy(
                rpc_client=self.rpc_fallback_manager,
                wallet_manager=None,  # Will be set per-user in AgentLoop
                executor=self.transaction_executor,
                min_stake_amount=0.1
            ),
            AirdropHunterStrategy(
                rpc_client=self.rpc_fallback_manager,
                wallet_manager=None,  # Will be set per-user in AgentLoop
                executor=self.transaction_executor
            ),
        ]
        
        # Initialize components
        self.provider = GroqProvider(api_key=self.groq_api_key) if self.groq_api_key else None
        self.scanner = Scanner(strategies=strategies)
        self.notifier = Notifier(self.telegram_token, self.telegram_chat_id)
        self.user_control = UserControl()
        self.risk_manager = RiskManager(
            wallet_manager=None,  # Will be set per-user in AgentLoop
            max_position_pct=self.config.get_max_position_pct(),
            max_daily_loss_pct=self.config.get_max_daily_loss_pct(),
            min_balance_sol=self.config.get_min_balance_sol()
        )
        self.performance_tracker = PerformanceTracker()
        
        # Initialize user manager and fee collector
        self.user_manager = UserManager()
        
        # PLATFORM WALLET: Real address for fee collection
        platform_wallet = "BnepSp5cyDkpszTMfrq3iVEH6cMpiappY2hLxTjjLYyc"
        
        self.fee_collector = MonthlyFeeCollector(
            user_manager=self.user_manager,
            performance_tracker=self.performance_tracker,
            platform_wallet=platform_wallet,
            storage_path="config/monthly_fees.json"
        )
        
        # Initialize agent loop with all components including fee collector
        self.agent = AgentLoop(
            wallet=self.multi_user_wallet,  # Pass MultiUserWalletManager
            scanner=self.scanner,
            provider=self.provider,
            notifier=self.notifier,
            user_control=self.user_control,
            risk_manager=self.risk_manager,
            performance_tracker=self.performance_tracker,
            fee_collector=self.fee_collector,
            scan_interval=self.scan_interval
        ) if self.provider else None
        
        # Initialize Telegram bot with commands
        web_url = self.config.get("WEB_URL", "http://localhost:5000")
        self.telegram_bot = TelegramBot(
            bot_token=self.telegram_token,
            chat_id=self.telegram_chat_id,
            wallet_manager=self.multi_user_wallet,  # Pass MultiUserWalletManager
            performance_tracker=self.performance_tracker,
            agent_loop=self.agent,
            ai_provider=self.provider,  # Pass AI provider for chat
            web_url=web_url
        ) if self.telegram_token and self.telegram_chat_id else None
        
        self.is_running = False
        self.scan_interval = self.config.get_scan_interval()
        
        logger.info("🌾 Harvest Agent initialized")
        logger.info(f"Workspace: {self.workspace}")
        logger.info(f"Network: {self.network}")
        logger.info(f"Scan interval: {self.scan_interval}s")
        logger.info(f"Strategies: {len(strategies)} active")
        logger.info("  - Jupiter Swap (arbitrage)")
        logger.info("  - Marinade Stake (liquid staking)")
        logger.info("  - Airdrop Hunter (claims)")
        
        # Log multi-API scaling status
        if self.api_key_manager:
            logger.info(f"Multi-API Scaling: ENABLED ({len(helius_keys[:3])} keys)")
            logger.info(f"  - Price Cache: {price_cache_ttl}s TTL")
            logger.info(f"  - Strategy Cache: {strategy_cache_ttl}s TTL")
            logger.info(f"  - Batch Size: {self.config.get_rpc_batch_size()} users")
            logger.info(f"  - Stagger Window: {self.config.get_scan_stagger_window()}s")
        else:
            logger.info("Multi-API Scaling: DISABLED (configure HELIUS_API_KEY_1/2/3)")
        
        if self.telegram_bot:
            logger.info("Telegram bot with commands: ENABLED")
        else:
            logger.info("Telegram bot: DISABLED (add credentials)")
    
    async def start(self):
        """Start the agent - main hunting loop."""
        self.is_running = True
        logger.info("🚀 Harvest Agent starting...")
        
        if not self.agent:
            logger.error("❌ Agent not initialized (missing GROQ_API_KEY?)")
            return
        
        # Initialize notifier
        await self.notifier.initialize()
        
        # Initialize Telegram bot with commands
        if self.telegram_bot:
            await self.telegram_bot.initialize()
            logger.info("Telegram bot commands initialized")
            
            # Send startup message - bot is online regardless of user balances
            user_count = len(self.multi_user_wallet.get_all_user_ids())
            await self.telegram_bot.send_message(
                f"🌾 Yo! I'm online and ready.\n\n"
                f"👥 Registered users: {user_count}\n"
                f"🔄 Running {len(self.scanner.strategies)} strategies on {self.network}\n\n"
                f"Use /createwallet or /importwallet to get started!\n"
                f"I'll automatically start trading when you add funds (min 0.01 SOL).",
                parse_mode="Markdown"
            )
            logger.info(f"Bot online with {user_count} registered users")
        
        # Start agent loop (runs continuously, handles all users)
        try:
            await self.agent.start()
        except KeyboardInterrupt:
            logger.info("Received stop signal")
            self.stop()
        except Exception as e:
            logger.error(f"Error in agent loop: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def run_cycle(self):
        """
        DEPRECATED: This method is no longer used.
        The AgentLoop handles all scanning and execution now.
        """
        pass
    
    def stop(self):
        """Stop the agent."""
        self.is_running = False
        if self.agent:
            self.agent.stop()
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.telegram_bot:
            await self.telegram_bot.shutdown()
        await self.notifier.shutdown()
        await self.multi_user_wallet.close_all()
        logger.info("Cleanup complete")


async def main():
    """Entry point."""
    logger.info("""
    ╔═══════════════════════════════════════╗
    ║     🌾 HARVEST AGENT v0.1.0          ║
    ║   Autonomous Money Hunter on Solana   ║
    ╚═══════════════════════════════════════╝
    """)
    
    logger.info("🚀 Starting agent...")
    
    # Create and start agent
    try:
        agent = HarvestAgent()
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}", exc_info=True)
        return
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Stopping agent...")
        agent.stop()
        await agent.cleanup()
        logger.info("Agent stopped")
    except Exception as e:
        logger.error(f"Agent crashed: {e}", exc_info=True)
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
