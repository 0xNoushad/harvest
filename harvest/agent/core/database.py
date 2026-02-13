"""
SQLite Database for Harvest Bot

SECURITY & PRIVACY:
- Database is LOCAL to each user's deployment
- NO personal information stored (no names, emails, phone numbers)
- NO wallet private keys stored
- NO centralized data collection
- Each user runs their own instance with their own database
- User ID is just a hash/identifier, not personal data
- ALL inputs validated and sanitized
- SQL injection protection
- Command injection protection

Stores:
- User preferences (strategies enabled, risk tolerance)
- Trade history (for performance tracking)
- Performance metrics (profit/loss)
- Fee collection history (for transparency)
- Strategy states (last check times)

Location: config/harvest.db (local to deployment)
"""

import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from contextlib import contextmanager

from agent.security.security import SecurityValidator

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for Harvest bot.
    
    Features:
    - User management
    - Trade history
    - Performance tracking
    - Fee collection records
    - Strategy states
    - Conversation history
    """
    
    def __init__(self, db_path: str = "harvest.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database schema
        self._init_schema()
        
        logger.info(f"Database initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic commit/rollback."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row  # Return rows as dicts
            yield conn
            conn.commit()
        except sqlite3.OperationalError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operational error (locked/timeout): {e}")
            raise
        except sqlite3.DatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected database error: {e}")
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")
    
    def _init_schema(self):
        """Initialize database schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
            
                # Users table - MINIMAL DATA ONLY
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        preferences TEXT DEFAULT '{}'
                    )
                """)
                
                # Trades table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        strategy_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        amount REAL NOT NULL,
                        profit REAL NOT NULL,
                        transaction_hash TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        details TEXT DEFAULT '{}',
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Performance table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance (
                        performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        date DATE NOT NULL,
                        total_profit REAL DEFAULT 0,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        losing_trades INTEGER DEFAULT 0,
                        best_trade REAL DEFAULT 0,
                        worst_trade REAL DEFAULT 0,
                        strategy_profits TEXT DEFAULT '{}',
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        UNIQUE(user_id, date)
                    )
                """)
                
                # Fees table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS fees (
                        fee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        month TEXT NOT NULL,
                        monthly_profit REAL NOT NULL,
                        fee_amount REAL NOT NULL,
                        fee_rate REAL NOT NULL,
                        status TEXT NOT NULL,
                        requested_at TIMESTAMP,
                        collected_at TIMESTAMP,
                        transaction_hash TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        UNIQUE(user_id, month)
                    )
                """)
                
                # Conversations table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Strategy states table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_states (
                        state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        strategy_name TEXT NOT NULL,
                        enabled BOOLEAN DEFAULT 1,
                        last_check TIMESTAMP,
                        state_data TEXT DEFAULT '{}',
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        UNIQUE(user_id, strategy_name)
                    )
                """)
                
                # Positions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS positions (
                        position_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        strategy_name TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        current_price REAL NOT NULL,
                        amount REAL NOT NULL,
                        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        closed_at TIMESTAMP,
                        status TEXT DEFAULT 'open',
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Secure wallets table (stores encrypted wallet metadata)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS secure_wallets (
                        wallet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL UNIQUE,
                        public_key TEXT NOT NULL,
                        derivation_path TEXT NOT NULL,
                        mnemonic_words INTEGER NOT NULL,
                        kdf_method TEXT NOT NULL,
                        encryption_method TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_unlocked TIMESTAMP,
                        wallet_file_path TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_user ON performance(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fees_user ON fees(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_secure_wallets_user ON secure_wallets(user_id)")
                
                # Add total_profit column to users table if it doesn't exist
                cursor.execute("PRAGMA table_info(users)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'total_profit' not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN total_profit REAL DEFAULT 0")
                    logger.info("Added total_profit column to users table")
            
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    # ==================== SECURE WALLET MANAGEMENT ====================
    
    def register_secure_wallet(
        self,
        user_id: str,
        public_key: str,
        derivation_path: str,
        mnemonic_words: int,
        kdf_method: str,
        encryption_method: str,
        wallet_file_path: str
    ) -> bool:
        """
        Register a secure wallet in the database.
        
        Args:
            user_id: User ID
            public_key: Solana public key
            derivation_path: BIP44 derivation path
            mnemonic_words: Number of mnemonic words (12 or 24)
            kdf_method: Key derivation method (argon2id or pbkdf2)
            encryption_method: Encryption method (AES-256-GCM)
            wallet_file_path: Path to encrypted wallet file
        
        Returns:
            True if successful
        """
        # SECURITY: Validate inputs
        user_id = SecurityValidator.validate_user_id(user_id)
        public_key = SecurityValidator.validate_wallet_address(public_key)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO secure_wallets (
                        user_id, public_key, derivation_path, mnemonic_words,
                        kdf_method, encryption_method, wallet_file_path
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, public_key, derivation_path, mnemonic_words,
                      kdf_method, encryption_method, wallet_file_path))
                
                logger.info(f"Registered secure wallet for user {user_id}: {public_key}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Wallet already registered for user {user_id}")
            return False
    
    def get_user_wallet(self, user_id: str) -> Optional[Dict]:
        """
        Get user's secure wallet metadata.
        
        Args:
            user_id: User ID
        
        Returns:
            Wallet metadata or None
        """
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM secure_wallets WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error fetching wallet for user {user_id}: {e}")
            return None
    
    def update_wallet_last_unlocked(self, user_id: str):
        """Update wallet last unlocked timestamp."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE secure_wallets 
                    SET last_unlocked = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (user_id,))
        except Exception as e:
            logger.error(f"Error updating wallet last_unlocked for user {user_id}: {e}")
            raise
    
    def get_all_wallets(self) -> List[Dict]:
        """Get all registered wallets."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM secure_wallets ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching all wallets: {e}")
            return []
    
    # ==================== USER MANAGEMENT ====================
    
    def create_user(self, user_id: str) -> bool:
        """Create a new user with MINIMAL data and VALIDATION."""
        try:
            # SECURITY: Validate user ID
            user_id = SecurityValidator.validate_user_id(user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id)
                    VALUES (?)
                """, (user_id,))
                logger.info(f"Created user: {user_id}")
                return True
        except ValueError as e:
            logger.error(f"Invalid user ID: {e}")
            return False
        except sqlite3.IntegrityError:
            logger.warning(f"User already exists: {user_id}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields."""
        if not kwargs:
            return False
        
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        # SECURITY: Validate field names to prevent SQL injection
        # Only allow known safe field names
        allowed_fields = {'username', 'first_name', 'last_name', 'is_active', 'last_active', 'total_profit', 'preferences'}
        for field in kwargs.keys():
            if field not in allowed_fields:
                raise ValueError(f"Invalid field name: {field}")
        
        try:
            fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
            values = list(kwargs.values()) + [user_id]
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE users SET {fields} WHERE user_id = ?", values)
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE is_active = 1")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
            return []
    
    def update_last_active(self, user_id: str):
        """Update user's last active timestamp."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?
                """, (user_id,))
        except Exception as e:
            logger.error(f"Error updating last_active for user {user_id}: {e}")
            # Don't raise - this is not critical
    
    def update_user_profit(self, user_id: str, profit_delta: float) -> bool:
        """
        Update user's total profit by adding the profit delta.
        
        Args:
            user_id: User identifier
            profit_delta: Amount to add to total_profit (can be negative)
        
        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            # SECURITY: Validate inputs
            user_id = SecurityValidator.validate_user_id(user_id)
            profit_delta = SecurityValidator.validate_amount(profit_delta, min_val=-1000000.0)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users SET total_profit = total_profit + ? WHERE user_id = ?
                """, (profit_delta, user_id))
                
                if cursor.rowcount > 0:
                    logger.debug(f"Updated profit for user {user_id}: {profit_delta:+.6f} SOL")
                    return True
                else:
                    logger.error(f"Failed to update profit for user {user_id}: user not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating profit for user {user_id}: {e}")
            return False

    def get_user_stats(self, user_id: str = None) -> Union[Dict, List[Dict], None]:
        """
        Get user statistics (user_id and total_profit).

        Args:
            user_id: Optional user identifier. If None, returns all users.

        Returns:
            Dict or List[Dict]: User statistics with user_id and total_profit.
                               Returns None if single user query and user doesn't exist.
                               Returns empty list if no users exist.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if user_id is not None:
                    # Query single user
                    cursor.execute("""
                        SELECT user_id, total_profit FROM users WHERE user_id = ?
                    """, (user_id,))
                    row = cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
                else:
                    # Query all users, ordered by total_profit DESC
                    cursor.execute("""
                        SELECT user_id, total_profit FROM users ORDER BY total_profit DESC
                    """)
                    return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            if user_id is not None:
                return None
            return []

    
    # ==================== TRADE MANAGEMENT ====================
    
    def record_trade(self, user_id: str, strategy_name: str, action: str,
                    amount: float, profit: float, transaction_hash: str = None,
                    details: Dict = None) -> int:
        """Record a trade with VALIDATION."""
        # SECURITY: Validate all inputs
        user_id = SecurityValidator.validate_user_id(user_id)
        strategy_name = SecurityValidator.validate_strategy_name(strategy_name)
        action = SecurityValidator.sanitize_string(action, max_length=50)
        amount = SecurityValidator.validate_amount(amount)
        profit = SecurityValidator.validate_amount(profit, min_val=-1000000.0)
        
        if transaction_hash:
            transaction_hash = SecurityValidator.validate_transaction_hash(transaction_hash)
        
        if details:
            details = SecurityValidator.validate_json_data(details)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (user_id, strategy_name, action, amount, profit, 
                                  transaction_hash, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, strategy_name, action, amount, profit, transaction_hash,
                  json.dumps(details or {})))
            
            trade_id = cursor.lastrowid
            logger.info(f"Recorded trade {trade_id} for user {user_id}: {profit} SOL")
            return trade_id
    
    def get_user_trades(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get user's trade history."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_trades_by_month(self, user_id: str, year: int, month: int) -> List[Dict]:
        """Get trades for a specific month."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE user_id = ? 
                AND strftime('%Y', timestamp) = ? 
                AND strftime('%m', timestamp) = ?
                ORDER BY timestamp DESC
            """, (user_id, str(year), f"{month:02d}"))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== PERFORMANCE TRACKING ====================
    
    def update_daily_performance(self, user_id: str, date: str = None):
        """Update daily performance metrics."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate metrics from trades
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(profit) as total_profit,
                    SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) as losing_trades,
                    MAX(profit) as best_trade,
                    MIN(profit) as worst_trade
                FROM trades
                WHERE user_id = ? AND DATE(timestamp) = ?
            """, (user_id, date))
            
            metrics = dict(cursor.fetchone())
            
            # Get strategy profits
            cursor.execute("""
                SELECT strategy_name, SUM(profit) as profit
                FROM trades
                WHERE user_id = ? AND DATE(timestamp) = ?
                GROUP BY strategy_name
            """, (user_id, date))
            
            strategy_profits = {row['strategy_name']: row['profit'] 
                              for row in cursor.fetchall()}
            
            # Insert or update performance
            cursor.execute("""
                INSERT INTO performance (user_id, date, total_profit, total_trades,
                                       winning_trades, losing_trades, best_trade,
                                       worst_trade, strategy_profits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, date) DO UPDATE SET
                    total_profit = excluded.total_profit,
                    total_trades = excluded.total_trades,
                    winning_trades = excluded.winning_trades,
                    losing_trades = excluded.losing_trades,
                    best_trade = excluded.best_trade,
                    worst_trade = excluded.worst_trade,
                    strategy_profits = excluded.strategy_profits
            """, (user_id, date, metrics['total_profit'] or 0, 
                  metrics['total_trades'] or 0, metrics['winning_trades'] or 0,
                  metrics['losing_trades'] or 0, metrics['best_trade'] or 0,
                  metrics['worst_trade'] or 0, json.dumps(strategy_profits)))
    
    def get_user_performance(self, user_id: str, days: int = 30) -> List[Dict]:
        """Get user performance for last N days."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM performance
                WHERE user_id = ?
                ORDER BY date DESC
                LIMIT ?
            """, (user_id, days))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== FEE MANAGEMENT ====================
    
    def record_fee_request(self, user_id: str, month: str, monthly_profit: float,
                          fee_amount: float, fee_rate: float) -> bool:
        """Record a fee approval request with VALIDATION."""
        # SECURITY: Validate all inputs
        user_id = SecurityValidator.validate_user_id(user_id)
        month = SecurityValidator.validate_month(month)
        monthly_profit = SecurityValidator.validate_amount(monthly_profit, min_val=-1000000.0)
        fee_amount = SecurityValidator.validate_amount(fee_amount)
        fee_rate = SecurityValidator.validate_amount(fee_rate, min_val=0.0, max_val=1.0)
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO fees (user_id, month, monthly_profit, fee_amount, 
                                    fee_rate, status, requested_at)
                    VALUES (?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
                """, (user_id, month, monthly_profit, fee_amount, fee_rate))
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Fee request already exists for {user_id} {month}")
            return False
    
    def update_fee_status(self, user_id: str, month: str, status: str,
                         transaction_hash: str = None) -> bool:
        """Update fee collection status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == "collected":
                cursor.execute("""
                    UPDATE fees 
                    SET status = ?, collected_at = CURRENT_TIMESTAMP, transaction_hash = ?
                    WHERE user_id = ? AND month = ?
                """, (status, transaction_hash, user_id, month))
            else:
                cursor.execute("""
                    UPDATE fees SET status = ? WHERE user_id = ? AND month = ?
                """, (status, user_id, month))
            return cursor.rowcount > 0
    
    def get_user_fees(self, user_id: str) -> List[Dict]:
        """Get user's fee history."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fees WHERE user_id = ? ORDER BY month DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_fees(self, user_id: str) -> Optional[Dict]:
        """Get pending fee for user."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fees WHERE user_id = ? AND status = 'pending'
                ORDER BY requested_at DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ==================== CONVERSATION HISTORY ====================
    
    def add_conversation(self, user_id: str, role: str, message: str):
        """Add conversation message with VALIDATION."""
        # SECURITY: Validate inputs
        user_id = SecurityValidator.validate_user_id(user_id)
        role = SecurityValidator.sanitize_string(role, max_length=20)
        # Don't check for SQL injection in conversation messages (they contain natural language)
        message = SecurityValidator.sanitize_string(message, max_length=5000, check_injections=False)
        
        # Only allow specific roles
        if role not in ['user', 'assistant', 'system']:
            raise ValueError("Invalid role")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (user_id, role, message)
                VALUES (?, ?, ?)
            """, (user_id, role, message))
    
    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history in chronological order (oldest first)."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== STRATEGY STATES ====================
    
    def update_strategy_state(self, user_id: str, strategy_name: str,
                             enabled: bool = None, state_data: Dict = None):
        """Update strategy state for user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if enabled is not None and state_data is not None:
                cursor.execute("""
                    INSERT INTO strategy_states (user_id, strategy_name, enabled, 
                                               last_check, state_data)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
                    ON CONFLICT(user_id, strategy_name) DO UPDATE SET
                        enabled = excluded.enabled,
                        last_check = CURRENT_TIMESTAMP,
                        state_data = excluded.state_data
                """, (user_id, strategy_name, enabled, json.dumps(state_data)))
            elif enabled is not None:
                cursor.execute("""
                    INSERT INTO strategy_states (user_id, strategy_name, enabled, last_check)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, strategy_name) DO UPDATE SET
                        enabled = excluded.enabled,
                        last_check = CURRENT_TIMESTAMP
                """, (user_id, strategy_name, enabled))
    
    def get_user_strategies(self, user_id: str) -> List[Dict]:
        """Get user's strategy states."""
        # SECURITY: Validate user_id to prevent SQL injection
        user_id = SecurityValidator.validate_user_id(user_id)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM strategy_states WHERE user_id = ?
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== STATISTICS ====================
    
    def get_platform_stats(self) -> Dict:
        """Get platform-wide statistics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total users (all users regardless of active status)
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
            
            # Total trades
            cursor.execute("SELECT COUNT(*) as count FROM trades")
            total_trades = cursor.fetchone()['count']
            
            # Total profit
            cursor.execute("SELECT SUM(profit) as total FROM trades")
            total_profit = cursor.fetchone()['total'] or 0
            
            # Total fees collected
            cursor.execute("""
                SELECT SUM(fee_amount) as total FROM fees WHERE status = 'collected'
            """)
            total_fees = cursor.fetchone()['total'] or 0
            
            return {
                "total_users": total_users,
                "total_trades": total_trades,
                "total_profit": total_profit,
                "total_fees": total_fees
            }


# Example usage
if __name__ == "__main__":
    # Initialize database
    db = Database("harvest.db")
    
    # Create a user
    db.create_user("123456", "testuser", "Test User", "wallet_address_here")
    
    # Record a trade
    db.record_trade(
        user_id="123456",
        strategy_name="airdrop_hunter",
        action="claim",
        amount=0.1,
        profit=0.002,
        transaction_hash="abc123"
    )
    
    # Update performance
    db.update_daily_performance("123456")
    
    # Get user trades
    trades = db.get_user_trades("123456")
    print(f"User trades: {len(trades)}")
    
    # Get platform stats
    stats = db.get_platform_stats()
    print(f"Platform stats: {stats}")
