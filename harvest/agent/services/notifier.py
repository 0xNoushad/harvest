"""Telegram notifier for Harvest - sends opportunity notifications with user control."""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """
    Represents a money-making opportunity.
    
    Attributes:
        strategy_name: Name of the strategy that found this opportunity
        action: Action to take (e.g., "stake", "claim", "buy")
        amount: Amount involved in the opportunity
        expected_profit: Expected profit from the opportunity
        risk_level: Risk level ("low", "medium", "high")
        details: Additional details about the opportunity
        timestamp: When the opportunity was found
    """
    strategy_name: str
    action: str
    amount: float
    expected_profit: float
    risk_level: str
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class ExecutionResult:
    """
    Result of executing an opportunity.
    
    Attributes:
        success: Whether execution was successful
        transaction_hash: Transaction hash if successful
        profit: Actual profit/loss from execution
        error: Error message if failed
        timestamp: When execution completed
    """
    success: bool
    transaction_hash: Optional[str]
    profit: float
    error: Optional[str]
    timestamp: datetime


class Notifier:
    """
    Telegram notifier for Harvest agent.
    
    Sends opportunity notifications with YES/NO/ALWAYS buttons,
    handles user responses, and implements retry logic for failed notifications.
    
    Features:
    - Send opportunity notifications with interactive buttons
    - Handle button click callbacks
    - Retry logic (up to 3 attempts) for failed notifications
    - 5-minute timeout for user responses
    - Send execution result notifications
    """
    
    DEFAULT_TIMEOUT = 300  # 5 minutes
    MAX_RETRIES = 3
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize notifier with Telegram bot credentials.
        
        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat ID to send notifications to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.application: Optional[Application] = None
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._initialized = False
        
        logger.info(f"Notifier initialized for chat_id: {chat_id}")
    
    async def initialize(self):
        """Initialize the Telegram bot application."""
        if self._initialized:
            return
        
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add callback handler for button clicks
            self.application.add_handler(
                CallbackQueryHandler(self._handle_callback)
            )
            
            # Initialize the application
            await self.application.initialize()
            await self.application.start()
            
            self._initialized = True
            logger.info("Telegram bot initialized and started")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram notifier: {e}")
            self._initialized = False
            raise
    
    async def shutdown(self):
        """Shutdown the Telegram bot application."""
        if self.application and self._initialized:
            try:
                await self.application.stop()
                await self.application.shutdown()
                self._initialized = False
                logger.info("Telegram bot shutdown")
            except Exception as e:
                logger.error(f"Error during Telegram notifier shutdown: {e}")
                self._initialized = False
    
    async def send_message_to_user(self, user_id: str, message: str, parse_mode: str = "Markdown"):
        """
        Send a message to a specific user.
        
        Args:
            user_id: Telegram user ID (chat ID)
            message: Message text to send
            parse_mode: Message parse mode (default: Markdown)
        
        Raises:
            Exception: If message sending fails
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"Message sent to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            raise
    
    async def send_opportunity(self, opportunity: Opportunity) -> str:
        """
        Send opportunity notification with YES/NO/ALWAYS buttons.
        
        Implements retry logic (up to 3 attempts) for failed notifications.
        
        Args:
            opportunity: Opportunity to notify about
        
        Returns:
            Message ID as string
        
        Raises:
            Exception: If all retry attempts fail
        """
        if not self._initialized:
            await self.initialize()
        
        # Build notification message
        message = self._format_opportunity_message(opportunity)
        
        # Create inline keyboard with YES/NO/ALWAYS buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ YES", callback_data=f"yes:{opportunity.strategy_name}"),
                InlineKeyboardButton("❌ NO", callback_data=f"no:{opportunity.strategy_name}"),
                InlineKeyboardButton("🔄 ALWAYS", callback_data=f"always:{opportunity.strategy_name}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Retry logic
        last_exception = None
        for attempt in range(self.MAX_RETRIES):
            try:
                # Send message
                sent_message = await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
                message_id = str(sent_message.message_id)
                logger.info(f"Opportunity notification sent (message_id: {message_id})")
                return message_id
                
            except Exception as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        f"Failed to send notification (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. "
                        f"Retrying..."
                    )
                    await asyncio.sleep(1.0 * (attempt + 1))  # Simple backoff
                else:
                    logger.error(
                        f"Failed to send notification after {self.MAX_RETRIES} attempts: {e}"
                    )
        
        raise last_exception
    
    async def wait_for_response(
        self,
        message_id: str,
        timeout: int = DEFAULT_TIMEOUT
    ) -> str:
        """
        Wait for user button click response.
        
        Args:
            message_id: Message ID to wait for response on
            timeout: Timeout in seconds (default 5 minutes)
        
        Returns:
            User response: 'yes', 'no', or 'always'
            Returns 'no' if timeout occurs
        """
        # Create future for this message
        future = asyncio.Future()
        self._pending_responses[message_id] = future
        
        try:
            # Wait for response with timeout
            response = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"Received response for message {message_id}: {response}")
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response on message {message_id}, defaulting to 'no'")
            return "no"
        finally:
            # Clean up
            self._pending_responses.pop(message_id, None)
    
    async def send_high_value_opportunity(self, opportunity: Opportunity, user_id: Optional[str] = None):
        """
        Send notification about high-value opportunity detected.
        
        Args:
            opportunity: High-value opportunity to notify about
            user_id: Optional user ID to send notification to (defaults to self.chat_id)
        """
        if not self._initialized:
            await self.initialize()
        
        message = f"""💰 **HIGH-VALUE OPPORTUNITY DETECTED**

**Strategy**: {opportunity.strategy_name}
**Action**: {opportunity.action}
**Amount**: {opportunity.amount:.4f} SOL
**Expected Profit**: {opportunity.expected_profit:.4f} SOL
**Risk Level**: {opportunity.risk_level.upper()}

This opportunity has been automatically flagged for your attention due to its high expected profit.

The agent will evaluate and potentially execute this opportunity based on your preferences.
"""
        
        try:
            chat_id = user_id if user_id else self.chat_id
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info("High-value opportunity notification sent")
        except Exception as e:
            logger.error(f"Failed to send high-value opportunity notification: {e}")
    
    async def send_execution_result(self, result: ExecutionResult, user_id: Optional[str] = None):
        """
        Send notification about trade execution result.
        
        Args:
            result: ExecutionResult to notify about
            user_id: Optional user ID to send notification to (defaults to self.chat_id)
        """
        if not self._initialized:
            await self.initialize()
        
        message = self._format_execution_result(result)
        
        try:
            chat_id = user_id if user_id else self.chat_id
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info("Execution result notification sent")
        except Exception as e:
            logger.error(f"Failed to send execution result: {e}")
    
    async def send_risk_rejection(self, opportunity: Opportunity, reason: str, user_id: Optional[str] = None):
        """
        Send notification about opportunity rejected by risk manager.
        
        Args:
            opportunity: Opportunity that was rejected
            reason: Reason for rejection
            user_id: Optional user ID to send notification to (defaults to self.chat_id)
        """
        if not self._initialized:
            await self.initialize()
        
        message = f"""⚠️ **Opportunity Rejected - Risk Limit Exceeded**

**Strategy**: {opportunity.strategy_name}
**Action**: {opportunity.action}
**Amount**: {opportunity.amount:.4f} SOL
**Expected Profit**: {opportunity.expected_profit:.4f} SOL

**Rejection Reason**: {reason}

The risk manager has blocked this opportunity to protect your capital.
"""
        
        try:
            chat_id = user_id if user_id else self.chat_id
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info("Risk rejection notification sent")
        except Exception as e:
            logger.error(f"Failed to send risk rejection: {e}")
    
    async def send_stop_loss_exit(self, position, reason: str):
        """
        Send notification about stop-loss position exit.
        
        Args:
            position: Position that was exited
            reason: Reason for exit
        """
        if not self._initialized:
            await self.initialize()
        
        # Calculate loss
        loss_amount = (position.entry_price - position.current_price) * position.amount / position.entry_price
        loss_percentage = ((position.current_price - position.entry_price) / position.entry_price) * 100
        
        message = f"""🛑 **Stop-Loss Triggered**

**Strategy**: {position.strategy_name}
**Position ID**: {position.position_id}
**Entry Price**: {position.entry_price:.4f}
**Exit Price**: {position.current_price:.4f}
**Amount**: {position.amount:.4f}
**Loss**: {loss_amount:.4f} ({loss_percentage:.2f}%)

**Reason**: {reason}

The position has been automatically exited to limit losses.
"""
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown"
            )
            logger.info("Stop-loss exit notification sent")
        except Exception as e:
            logger.error(f"Failed to send stop-loss exit notification: {e}")
    
    async def send_airdrop_discovery(self, airdrop_details: Dict[str, Any]):
        """
        Send notification about newly discovered airdrop.
        
        Args:
            airdrop_details: Dictionary with airdrop information
        """
        if not self._initialized:
            await self.initialize()
        
        protocol = airdrop_details.get("protocol", "Unknown")
        token = airdrop_details.get("token", "???")
        source = airdrop_details.get("source", "Unknown")
        announcement_url = airdrop_details.get("announcement_url", "")
        claim_url = airdrop_details.get("claim_url", "")
        eligibility = airdrop_details.get("eligibility", "Check announcement")
        deadline = airdrop_details.get("deadline", "")
        is_verified = airdrop_details.get("is_verified", False)
        
        verification_status = "✅ Verified" if is_verified else "⚠️ Needs Verification"
        
        message = f"""🎁 **NEW AIRDROP DISCOVERED!**

**Protocol**: {protocol}
**Token**: {token}
**Source**: {source}
**Status**: {verification_status}

**Eligibility**: {eligibility}
"""
        
        if deadline:
            message += f"**Deadline**: {deadline}\n"
        
        message += "\n**Links**:\n"
        
        if announcement_url:
            message += f"📢 [Announcement]({announcement_url})\n"
        
        if claim_url:
            message += f"🎯 [Claim Page]({claim_url})\n"
        
        message += "\n💡 **Action Required**: Check the announcement and start farming if you're eligible!"
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            logger.info(f"Airdrop discovery notification sent for {protocol}")
        except Exception as e:
            logger.error(f"Failed to send airdrop discovery notification: {e}")
    
    async def send_airdrop_claimed(self, claim_details: Dict[str, Any]):
        """
        Send notification about successfully claimed airdrop.
        
        Args:
            claim_details: Dictionary with claim information
        """
        if not self._initialized:
            await self.initialize()
        
        protocol = claim_details.get("protocol", "Unknown")
        token = claim_details.get("token", "???")
        amount = claim_details.get("amount", 0)
        value_usd = claim_details.get("value_usd", 0)
        tx_hash = claim_details.get("transaction_hash", "")
        
        message = f"""✅ **AIRDROP CLAIMED!**

**Protocol**: {protocol}
**Token**: {token}
**Amount**: {amount:,.2f} {token}
"""
        
        if value_usd > 0:
            message += f"**Value**: ${value_usd:,.2f} USD\n"
        
        if tx_hash:
            message += f"\n**Transaction**: `{tx_hash}`\n"
            message += f"[View on Solscan](https://solscan.io/tx/{tx_hash})\n"
        
        message += "\n🎉 Free money in your wallet!"
        
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
            logger.info(f"Airdrop claimed notification sent for {protocol}")
        except Exception as e:
            logger.error(f"Failed to send airdrop claimed notification: {e}")
    
    async def _handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Handle button click callbacks.
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        query = update.callback_query
        await query.answer()
        
        # Parse callback data: "action:strategy_name"
        callback_data = query.data
        action, strategy_name = callback_data.split(":", 1)
        
        message_id = str(query.message.message_id)
        
        logger.info(f"Received callback: {action} for {strategy_name} (message: {message_id})")
        
        # Resolve pending future if exists
        if message_id in self._pending_responses:
            future = self._pending_responses[message_id]
            if not future.done():
                future.set_result(action)
        
        # Update message to show user's choice
        response_emoji = {
            "yes": "✅",
            "no": "❌",
            "always": "🔄"
        }
        
        await query.edit_message_text(
            text=f"{query.message.text}\n\n{response_emoji.get(action, '❓')} **User selected: {action.upper()}**",
            parse_mode="Markdown"
        )
    
    def _format_opportunity_message(self, opportunity: Opportunity) -> str:
        """
        Format opportunity as Telegram message.
        
        Args:
            opportunity: Opportunity to format
        
        Returns:
            Formatted message string
        """
        risk_emoji = {
            "low": "🟢",
            "medium": "🟡",
            "high": "🔴"
        }
        
        message = f"""🌾 **Harvest Opportunity**

**Strategy**: {opportunity.strategy_name}
**Action**: {opportunity.action}
**Amount**: {opportunity.amount:.4f} SOL
**Expected Profit**: {opportunity.expected_profit:.4f} SOL
**Risk Level**: {risk_emoji.get(opportunity.risk_level, '⚪')} {opportunity.risk_level.upper()}

**Details**:
"""
        
        # Add details
        for key, value in opportunity.details.items():
            message += f"• {key}: {value}\n"
        
        message += "\n**What would you like to do?**"
        
        return message
    
    def _format_execution_result(self, result: ExecutionResult) -> str:
        """
        Format execution result as Telegram message.
        
        Args:
            result: ExecutionResult to format
        
        Returns:
            Formatted message string
        """
        if result.success:
            message = f"""✅ **Trade Executed Successfully**

**Profit**: {result.profit:.4f} SOL
**Transaction**: `{result.transaction_hash}`
**Time**: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        else:
            message = f"""❌ **Trade Failed**

**Error**: {result.error}
**Time**: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return message


async def main():
    """Test notifier functionality."""
    print("🌾 Testing Harvest Notifier\n")
    
    # Get credentials from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables")
        return
    
    # Create notifier
    notifier = Notifier(bot_token=bot_token, chat_id=chat_id)
    
    try:
        # Create test opportunity
        opportunity = Opportunity(
            strategy_name="liquid_staking",
            action="stake",
            amount=1.0,
            expected_profit=0.072,
            risk_level="low",
            details={
                "protocol": "Marinade",
                "apy": "7.2%",
                "duration": "flexible"
            },
            timestamp=datetime.now()
        )
        
        # Send notification
        print("Sending opportunity notification...")
        message_id = await notifier.send_opportunity(opportunity)
        print(f"Notification sent (message_id: {message_id})")
        
        # Wait for response
        print("Waiting for user response (5 minute timeout)...")
        response = await notifier.wait_for_response(message_id, timeout=300)
        print(f"User response: {response}")
        
        # Send execution result
        if response == "yes" or response == "always":
            result = ExecutionResult(
                success=True,
                transaction_hash="abc123def456...",
                profit=0.072,
                error=None,
                timestamp=datetime.now()
            )
            await notifier.send_execution_result(result)
            print("Execution result sent")
        
    finally:
        # Shutdown
        await notifier.shutdown()
        print("\n✅ Notifier test complete")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
