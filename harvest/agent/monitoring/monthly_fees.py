"""
Monthly Fee Collection System - Permission-Based

Collects 2% performance fee monthly ONLY with user permission.
If user doesn't approve, bot pauses for next month until they pay.
Fair, transparent, and user-controlled.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
from pathlib import Path
import json

from agent.trading.performance import PerformanceTracker
from agent.services.user_manager import UserManager
from agent.security.security import SecurityValidator, rate_limiter

logger = logging.getLogger(__name__)


class MonthlyFeeCollector:
    """
    Collect 2% performance fee monthly with user permission.
    
    Features:
    - Calculates monthly profit per user
    - Sends notification asking for permission
    - Only charges if user approves
    - Pauses bot if user doesn't pay
    - Tracks payment status per user
    - Grace period for payment
    
    Flow:
    1. End of month: Calculate profit & fee
    2. Send notification: "You made $X, fee is $Y. Approve?"
    3. User approves → Collect fee → Continue service
    4. User declines → Pause bot for next month
    5. User can pay later to resume
    """
    
    FEE_RATE = 0.02  # 2% performance fee
    GRACE_PERIOD_DAYS = 7  # 7 days to approve payment
    
    def __init__(
        self,
        user_manager: UserManager,
        performance_tracker: PerformanceTracker,
        platform_wallet: str,
        storage_path: str = "config/monthly_fees.json"
    ):
        """
        Initialize monthly fee collector.
        
        Args:
            user_manager: UserManager instance
            performance_tracker: PerformanceTracker instance
            platform_wallet: Platform wallet address for fee collection
            storage_path: Path to store fee collection history
        """
        self.user_manager = user_manager
        self.performance_tracker = performance_tracker
        self.platform_wallet = platform_wallet
        self.storage_path = Path(storage_path)
        self.fee_history = self._load_history()
    
    def _load_history(self) -> Dict:
        """Load fee collection history from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load fee history: {e}")
        
        return {
            "collections": [],
            "pending_approvals": {},  # user_id -> pending fee info
            "payment_status": {}  # user_id -> {"paid": bool, "paused_until": date}
        }
    
    def _save_history(self):
        """Save fee collection history to storage."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.fee_history, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save fee history: {e}")
    
    def get_monthly_profit(self, user_id: str, month: datetime = None) -> float:
        """
        Calculate net profit for a user in a given month.
        
        Args:
            user_id: User ID
            month: Month to calculate (defaults to current month)
        
        Returns:
            Net profit for the month (can be negative)
        """
        if month is None:
            month = datetime.now()
        
        # Get start and end of month
        start_of_month = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month.month == 12:
            end_of_month = start_of_month.replace(year=month.year + 1, month=1)
        else:
            end_of_month = start_of_month.replace(month=month.month + 1)
        
        # Get all trades for this user in this month
        all_trades = self.performance_tracker.get_recent_trades(limit=1000)
        user_trades = [
            t for t in all_trades
            if t.timestamp >= start_of_month and t.timestamp < end_of_month
        ]
        
        # Calculate net profit
        net_profit = sum(t.actual_profit for t in user_trades)
        return net_profit
    
    def calculate_monthly_fee(self, user_id: str, month: datetime = None) -> float:
        """
        Calculate monthly fee for a user.
        
        Only charges on positive profits (no fee on losses).
        
        Args:
            user_id: User ID
            month: Month to calculate (defaults to current month)
        
        Returns:
            Fee amount (0 if no profit or loss)
        """
        monthly_profit = self.get_monthly_profit(user_id, month)
        
        # Only charge on profits
        if monthly_profit > 0:
            fee = monthly_profit * self.FEE_RATE
            logger.info(f"User {user_id} monthly fee: {fee} SOL (2% of {monthly_profit} SOL profit)")
            return fee
        
        logger.info(f"User {user_id} no fee (profit: {monthly_profit} SOL)")
        return 0.0
    
    def request_fee_approval(self, user_id: str, month: datetime = None) -> Dict:
        """
        Request fee approval from user.
        
        Sends notification with fee details and approval buttons.
        
        Args:
            user_id: User ID
            month: Month to collect for (defaults to previous month)
        
        Returns:
            Pending approval info
        """
        # SECURITY: Validate user ID
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Invalid user ID in request_fee_approval: {e}")
            return {"status": "error", "message": "Invalid user ID"}
        
        if month is None:
            # Default to previous month
            now = datetime.now()
            if now.month == 1:
                month = now.replace(year=now.year - 1, month=12)
            else:
                month = now.replace(month=now.month - 1)
        
        # Calculate fee
        monthly_profit = self.get_monthly_profit(user_id, month)
        fee = self.calculate_monthly_fee(user_id, month)
        
        if fee == 0:
            logger.info(f"No fee for user {user_id} (no profit)")
            return {"status": "no_fee_required"}
        
        # Create pending approval
        approval_info = {
            "user_id": user_id,
            "month": month.strftime("%Y-%m"),
            "monthly_profit": monthly_profit,
            "fee_amount": fee,
            "fee_rate": self.FEE_RATE,
            "requested_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=self.GRACE_PERIOD_DAYS)).isoformat(),
            "status": "pending"
        }
        
        # Store pending approval
        self.fee_history["pending_approvals"][user_id] = approval_info
        self._save_history()
        
        logger.info(f"Requested fee approval from user {user_id}: {fee} SOL")
        
        return approval_info
    
    def approve_fee(self, user_id: str) -> Dict:
        """
        User approves fee payment.
        
        Collects the fee and marks user as paid.
        
        Args:
            user_id: User ID
        
        Returns:
            Collection result
        """
        # SECURITY: Validate user ID
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Invalid user ID in approve_fee: {e}")
            return {"status": "error", "message": "Invalid user ID"}
        
        # SECURITY: Rate limiting (prevent spam approvals)
        if not rate_limiter.check_rate_limit(f"approve_{user_id}", max_requests=3, window_seconds=60):
            logger.warning(f"Rate limit exceeded for approve_fee: {user_id}")
            return {"status": "error", "message": "Too many requests. Please wait."}
        
        # Get pending approval
        if user_id not in self.fee_history["pending_approvals"]:
            return {"status": "error", "message": "No pending fee approval"}
        
        approval = self.fee_history["pending_approvals"][user_id]
        
        # Check if expired
        expires_at = datetime.fromisoformat(approval["expires_at"])
        if datetime.now() > expires_at:
            return {"status": "expired", "message": "Approval period expired"}
        
        # Collect fee
        fee = approval["fee_amount"]
        
        try:
            # REAL TRANSACTION: Transfer SOL from user wallet to platform wallet
            import asyncio
            from solders.pubkey import Pubkey
            
            # Get user wallet from user manager
            user_wallet = self.user_manager.get_user_wallet(user_id)
            
            if not user_wallet:
                logger.error(f"No wallet found for user {user_id}")
                return {"status": "failed", "error": "User wallet not found"}
            
            # SECURITY: Validate platform wallet address
            try:
                platform_wallet = SecurityValidator.validate_wallet_address(self.platform_wallet)
            except ValueError as e:
                logger.error(f"Invalid platform wallet address: {e}")
                return {"status": "failed", "error": "Invalid platform wallet address"}
            
            # SECURITY: Validate fee amount
            try:
                fee = SecurityValidator.validate_amount(fee, min_val=0.0001, max_val=1000.0)
            except ValueError as e:
                logger.error(f"Invalid fee amount: {e}")
                return {"status": "failed", "error": "Invalid fee amount"}
            
            # Execute real transfer
            logger.info(f"Transferring {fee} SOL from user {user_id} to platform wallet {platform_wallet}")
            
            # Run async transfer
            loop = asyncio.get_event_loop()
            tx_signature = loop.run_until_complete(
                user_wallet.send_sol(platform_wallet, fee)
            )
            
            if not tx_signature:
                raise Exception("Transfer failed - no transaction signature returned")
            
            result = {
                "user_id": user_id,
                "month": approval["month"],
                "monthly_profit": approval["monthly_profit"],
                "fee_amount": fee,
                "fee_rate": self.FEE_RATE,
                "collected_at": datetime.now().isoformat(),
                "status": "collected",
                "transaction_hash": tx_signature
            }
            
            # Record in history
            self.fee_history["collections"].append(result)
            
            # Mark as paid
            self.fee_history["payment_status"][user_id] = {
                "paid": True,
                "paid_at": datetime.now().isoformat(),
                "paused": False
            }
            
            # Remove pending approval
            del self.fee_history["pending_approvals"][user_id]
            
            self._save_history()
            
            logger.info(f"✅ User {user_id} approved and paid fee: {fee} SOL (tx: {tx_signature})")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to collect fee from user {user_id}: {e}")
            return {"status": "failed", "error": str(e)}
    
    def decline_fee(self, user_id: str) -> Dict:
        """
        User declines fee payment.
        
        Pauses bot for next month until they pay.
        
        Args:
            user_id: User ID
        
        Returns:
            Decline result
        """
        # SECURITY: Validate user ID
        try:
            user_id = SecurityValidator.validate_user_id(user_id)
        except ValueError as e:
            logger.error(f"Invalid user ID in decline_fee: {e}")
            return {"status": "error", "message": "Invalid user ID"}
        
        # SECURITY: Rate limiting
        if not rate_limiter.check_rate_limit(f"decline_{user_id}", max_requests=3, window_seconds=60):
            logger.warning(f"Rate limit exceeded for decline_fee: {user_id}")
            return {"status": "error", "message": "Too many requests. Please wait."}
        
        # Get pending approval
        if user_id not in self.fee_history["pending_approvals"]:
            return {"status": "error", "message": "No pending fee approval"}
        
        approval = self.fee_history["pending_approvals"][user_id]
        
        # Pause bot for next month
        pause_until = datetime.now() + timedelta(days=30)
        
        self.fee_history["payment_status"][user_id] = {
            "paid": False,
            "declined_at": datetime.now().isoformat(),
            "paused": True,
            "paused_until": pause_until.isoformat(),
            "unpaid_fee": approval["fee_amount"]
        }
        
        # Keep pending approval (they can pay later)
        approval["status"] = "declined"
        
        self._save_history()
        
        logger.info(f"User {user_id} declined fee payment. Bot paused until {pause_until}")
        
        return {
            "status": "declined",
            "paused_until": pause_until.isoformat(),
            "message": f"Bot paused until {pause_until.strftime('%Y-%m-%d')}. Pay fee to resume."
        }
    
    def is_user_active(self, user_id: str) -> bool:
        """
        Check if user is active (paid fees).
        
        Args:
            user_id: User ID
        
        Returns:
            True if user can use the bot
        """
        # Check payment status
        if user_id not in self.fee_history["payment_status"]:
            return True  # New user, no fees yet
        
        status = self.fee_history["payment_status"][user_id]
        
        # If paused, check if pause period expired
        if status.get("paused", False):
            paused_until = datetime.fromisoformat(status["paused_until"])
            if datetime.now() < paused_until:
                return False  # Still paused
            else:
                # Pause expired, but still need to pay
                return False
        
        return True
    
    def get_user_status(self, user_id: str) -> Dict:
        """
        Get user's payment status.
        
        Args:
            user_id: User ID
        
        Returns:
            Status dict with payment info
        """
        # Check if active
        is_active = self.is_user_active(user_id)
        
        # Check pending approvals
        has_pending = user_id in self.fee_history["pending_approvals"]
        pending_info = self.fee_history["pending_approvals"].get(user_id)
        
        # Check payment status
        payment_status = self.fee_history["payment_status"].get(user_id, {})
        
        return {
            "user_id": user_id,
            "is_active": is_active,
            "has_pending_fee": has_pending,
            "pending_fee": pending_info,
            "payment_status": payment_status
        }
    
    def request_all_fees(self, month: datetime = None) -> List[Dict]:
        """
        Request fee approval from all users for a given month.
        
        Run this on the 1st of each month to request previous month's fees.
        
        Args:
            month: Month to collect for (defaults to previous month)
        
        Returns:
            List of approval requests
        """
        logger.info("Requesting monthly fee approvals from all users")
        
        all_users = self.user_manager.get_all_users()
        results = []
        
        for user_id in all_users:
            try:
                result = self.request_fee_approval(user_id, month)
                results.append(result)
            except Exception as e:
                logger.error(f"Error requesting fee from user {user_id}: {e}")
                results.append({
                    "user_id": user_id,
                    "status": "error",
                    "error": str(e)
                })
        
        # Summary
        requested = sum(1 for r in results if r.get("status") == "pending")
        no_fee = sum(1 for r in results if r.get("status") == "no_fee_required")
        
        logger.info(
            f"Fee approval requests sent: {requested} requested, {no_fee} no fee required"
        )
        
        return results

    
    def get_user_fee_history(self, user_id: str) -> List[Dict]:
        """
        Get fee collection history for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            List of fee collections for this user
        """
        return [
            c for c in self.fee_history["collections"]
            if c["user_id"] == user_id
        ]
    
    def get_total_fees_collected(self) -> float:
        """
        Get total fees collected across all users.
        
        Returns:
            Total fees collected in SOL
        """
        return sum(
            c.get("fee_amount", 0)
            for c in self.fee_history["collections"]
            if c["status"] == "collected"
        )
    
    def should_request_fees(self) -> bool:
        """
        Check if it's time to request monthly fees.
        
        Returns True on the 1st of the month.
        
        Returns:
            True if fees should be requested
        """
        now = datetime.now()
        return now.day == 1
    
    def get_next_collection_date(self) -> datetime:
        """
        Get the next fee collection date (1st of next month).
        
        Returns:
            Next collection date
        """
        now = datetime.now()
        if now.month == 12:
            return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0)
        else:
            return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0)


# Example usage
if __name__ == "__main__":
    from .user_manager import UserManager
    from .performance import PerformanceTracker
    
    # Initialize
    user_manager = UserManager()
    performance_tracker = PerformanceTracker()
    platform_wallet = "PLATFORM_WALLET_ADDRESS_HERE"
    
    collector = MonthlyFeeCollector(
        user_manager=user_manager,
        performance_tracker=performance_tracker,
        platform_wallet=platform_wallet
    )
    
    # Check if it's time to request fees
    if collector.should_request_fees():
        print("🗓️  It's the 1st of the month - requesting fee approvals!")
        results = collector.request_all_fees()
        
        for result in results:
            if result.get("status") == "pending":
                print(f"📧 Requested approval from user {result['user_id']}: {result['fee_amount']} SOL")
            elif result.get("status") == "no_fee_required":
                print(f"⏭️  No fee for user {result['user_id']} (no profit)")
            else:
                print(f"❌ Failed to request from user {result['user_id']}")
    else:
        next_date = collector.get_next_collection_date()
        print(f"⏰ Next fee collection: {next_date.strftime('%Y-%m-%d')}")
