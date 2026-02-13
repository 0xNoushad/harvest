"""
Telegram Bot with Commands

Refactored modular architecture with command handlers, message handlers, and utilities.
"""

import logging
from typing import Optional
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    CallbackQueryHandler,
    filters,
)

from agent.services.user_manager import UserManager
from agent.ui.commands import (
    BasicCommands,
    TradingCommands,
    FinancialCommands,
    InfoCommands,
    WalletCommands,
)
from agent.ui.handlers import (
    MessageHandler as ChatMessageHandler,
    PollHandler,
    CallbackHandler,
)
from agent.ui.utils.messaging import send_message

logger = logging.getLogger(__name__)


class TelegramBot:
    """
    Telegram bot with modular command handlers.
    
    This is a thin orchestrator that delegates to specialized handlers:
    - BasicCommands: /start, /help, /wallet, /status
    - TradingCommands: /pause, /resume, /strategies
    - FinancialCommands: /withdraw, /fees, /approve_fee, /decline_fee
    - InfoCommands: /price, /portfolio, /stats, /bounty, /airdrops, /claims, /settings, /poll, /connect
    - WalletCommands: /newwallet, /exportkey
    - MessageHandler: Natural language chat with AI
    - PollHandler: User feedback polls
    - CallbackHandler: Inline button interactions
    """
    
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        wallet_manager,
        performance_tracker,
        agent_loop,
        ai_provider=None,
        web_url: str = "https://harvest.bot"
    ):
        """
        Initialize Telegram bot with multi-user support.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Default chat ID (for backwards compatibility)
            wallet_manager: WalletManager instance
            performance_tracker: PerformanceTracker instance
            agent_loop: AgentLoop instance
            ai_provider: AI provider for chat (GroqProvider)
            web_url: Web app URL for wallet connection
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.wallet = wallet_manager
        self.performance = performance_tracker
        self.agent_loop = agent_loop
        self.ai_provider = ai_provider
        self.web_url = web_url
        self.application: Optional[Application] = None
        self._initialized = False
        
        # Initialize user manager
        self.user_manager = UserManager()
        
        # Initialize command handlers
        self.basic_commands = BasicCommands(self)
        self.trading_commands = TradingCommands(self)
        self.financial_commands = FinancialCommands(self)
        self.info_commands = InfoCommands(self)
        self.wallet_commands = WalletCommands(self)
        
        # Initialize message handlers
        self.message_handler = ChatMessageHandler(self)
        self.poll_handler = PollHandler(self)
        self.callback_handler = CallbackHandler(self)
        
        logger.info(f"TelegramBot initialized with modular architecture")
    
    async def initialize(self):
        """Initialize the Telegram bot application with command handlers."""
        if self._initialized:
            return
        
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Register basic command handlers
            self.application.add_handler(CommandHandler("start", self.basic_commands.cmd_start))
            self.application.add_handler(CommandHandler("help", self.basic_commands.cmd_help))
            self.application.add_handler(CommandHandler("wallet", self.basic_commands.cmd_wallet))
            self.application.add_handler(CommandHandler("status", self.basic_commands.cmd_status))
            
            # Register trading command handlers
            self.application.add_handler(CommandHandler("pause", self.trading_commands.cmd_pause))
            self.application.add_handler(CommandHandler("resume", self.trading_commands.cmd_resume))
            self.application.add_handler(CommandHandler("strategies", self.trading_commands.cmd_strategies))
            
            # Register financial command handlers
            self.application.add_handler(CommandHandler("withdraw", self.financial_commands.cmd_withdraw))
            self.application.add_handler(CommandHandler("fees", self.financial_commands.cmd_fees))
            self.application.add_handler(CommandHandler("approve_fee", self.financial_commands.cmd_approve_fee))
            self.application.add_handler(CommandHandler("decline_fee", self.financial_commands.cmd_decline_fee))
            
            # Register info command handlers
            self.application.add_handler(CommandHandler("price", self.info_commands.cmd_price))
            self.application.add_handler(CommandHandler("portfolio", self.info_commands.cmd_portfolio))
            self.application.add_handler(CommandHandler("stats", self.info_commands.cmd_stats))
            self.application.add_handler(CommandHandler("leaderboard", self.info_commands.cmd_leaderboard))
            self.application.add_handler(CommandHandler("bounty", self.info_commands.cmd_bounty))
            self.application.add_handler(CommandHandler("airdrops", self.info_commands.cmd_airdrops))
            self.application.add_handler(CommandHandler("claims", self.info_commands.cmd_claims))
            self.application.add_handler(CommandHandler("settings", self.info_commands.cmd_settings))
            self.application.add_handler(CommandHandler("poll", self.info_commands.cmd_poll))
            self.application.add_handler(CommandHandler("connect", self.info_commands.cmd_connect))
            
            # Register wallet command handlers
            self.application.add_handler(CommandHandler("newwallet", self.wallet_commands.cmd_newwallet))
            self.application.add_handler(CommandHandler("exportkey", self.wallet_commands.cmd_exportkey))
            
            # Register event handlers
            self.application.add_handler(PollAnswerHandler(self.poll_handler.handle_poll_answer))
            self.application.add_handler(CallbackQueryHandler(self.callback_handler.handle_button_callback))
            
            # Register message handler for normal chat (must be last)
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler.handle_message)
            )
            
            # Initialize and start
            await self.application.initialize()
            await self.application.start()
            
            # Start polling for updates
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            self._initialized = True
            logger.info("Telegram bot initialized with modular handlers and polling started")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}", exc_info=True)
            self._initialized = False
            raise
    
    async def shutdown(self):
        """Shutdown the Telegram bot application."""
        if self.application and self._initialized:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self._initialized = False
                logger.info("Telegram bot shutdown")
            except Exception as e:
                logger.error(f"Error during Telegram bot shutdown: {e}", exc_info=True)
                self._initialized = False
    
    async def send_message(self, text: str, **kwargs):
        """
        Send a message to the user.
        
        Args:
            text: Message text to send
            **kwargs: Additional arguments for send_message
        """
        await send_message(self, text, **kwargs)
