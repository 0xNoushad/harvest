# Design Document: Multi-User Continuous Trading

## Overview

This design transforms the Harvest Telegram bot from a single-user system into a multi-user platform that runs 24/7, continuously scanning for trading opportunities across all registered users. Each user maintains their own isolated wallet, trading preferences, and performance tracking.

The key architectural shift is moving from a single wallet instance to a per-user wallet system, where the bot's main loop iterates through all active users, checking balances and scanning for opportunities independently for each user.

### Current Architecture

- Single WalletManager instance loaded at startup
- AgentLoop scans once per cycle for one wallet
- Bot stops when balance reaches 0 SOL
- UserManager exists but isn't integrated with trading loop

### Target Architecture

- Multi-user WalletManager that can load/manage multiple wallets
- AgentLoop iterates through all users per scan cycle
- Per-user balance checks and opportunity scanning
- Bot remains online regardless of individual user balances
- Automatic trading activation when users add funds

## Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Bot                             │
│  (/createwallet, /importwallet, /exportkey, /balance, etc)  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   User Manager                               │
│  - User profiles & preferences                               │
│  - Conversation history                                      │
│  - Wallet associations                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Multi-User Wallet Manager                       │
│  - Load/create wallets per user                             │
│  - Secure key storage                                        │
│  - Per-user balance checks                                   │
│  - Transaction signing per user                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Multi-User Agent Loop                         │
│  - Iterate through all users                                 │
│  - Per-user balance checks                                   │
│  - Per-user opportunity scanning                             │
│  - Per-user trade execution                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database (SQLite)                         │
│  - users table                                               │
│  - secure_wallets table                                      │
│  - trades table (with user_id)                               │
│  - performance table (with user_id)                          │
└─────────────────────────────────────────────────────────────┘
```

### Component Interactions

1. **User Registration Flow**
   - User sends /createwallet or /importwallet command
   - TelegramBot → UserManager: Create user profile
   - TelegramBot → MultiUserWalletManager: Create/import wallet
   - MultiUserWalletManager → Database: Store encrypted wallet metadata
   - TelegramBot → User: Return wallet address and mnemonic (for new wallets)

2. **Continuous Trading Loop**
   - AgentLoop starts scan cycle
   - AgentLoop → Database: Get all active users
   - For each user:
     - AgentLoop → MultiUserWalletManager: Get user's wallet
     - AgentLoop → MultiUserWalletManager: Check balance
     - If balance >= 0.01 SOL:
       - AgentLoop → Scanner: Scan strategies for user
       - AgentLoop → Provider: Evaluate opportunities
       - AgentLoop → MultiUserWalletManager: Execute trades with user's wallet
       - AgentLoop → PerformanceTracker: Record trade for user
       - AgentLoop → Database: Store trade record
   - AgentLoop: Sleep until next cycle

3. **Balance Change Detection**
   - During balance check, compare with previous balance
   - If balance increased from <0.01 to >=0.01:
     - AgentLoop → TelegramBot: Send "Trading activated" notification
   - If balance decreased from >=0.01 to <0.01:
     - AgentLoop → TelegramBot: Send "Trading paused - add funds" notification

## Components and Interfaces

### 1. MultiUserWalletManager

Manages multiple user wallets with secure key storage and per-user operations.

```python
class MultiUserWalletManager:
    """
    Manages multiple user wallets with secure storage.
    
    Attributes:
        wallets: Dict[user_id, WalletManager] - Cached wallet instances
        database: Database - For wallet metadata storage
        network: str - Solana network (devnet/mainnet)
    """
    
    def __init__(self, database: Database, network: str = "devnet"):
        """Initialize multi-user wallet manager."""
        pass
    
    async def create_wallet(self, user_id: str) -> tuple[str, str]:
        """
        Create new wallet for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            (public_key, mnemonic_phrase)
            
        Raises:
            ValueError: If user already has a wallet
        """
        pass
    
    async def import_wallet(self, user_id: str, mnemonic: str) -> str:
        """
        Import wallet from mnemonic phrase.
        
        Args:
            user_id: Telegram user ID
            mnemonic: 12 or 24 word mnemonic phrase
            
        Returns:
            public_key: Wallet public key
            
        Raises:
            ValueError: If user already has wallet or mnemonic invalid
        """
        pass
    
    async def get_wallet(self, user_id: str) -> Optional[WalletManager]:
        """
        Get wallet instance for user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            WalletManager instance or None if user has no wallet
        """
        pass
    
    async def get_balance(self, user_id: str) -> float:
        """
        Get SOL balance for user's wallet.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Balance in SOL
            
        Raises:
            ValueError: If user has no wallet
        """
        pass
    
    async def export_key(self, user_id: str) -> str:
        """
        Export user's private key or mnemonic.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Mnemonic phrase or base58 private key
            
        Raises:
            ValueError: If user has no wallet
        """
        pass
    
    def get_all_user_ids(self) -> List[str]:
        """
        Get list of all user IDs with registered wallets.
        
        Returns:
            List of user IDs
        """
        pass
    
    async def close_all(self):
        """Close all wallet RPC connections."""
        pass
```

### 2. Modified AgentLoop

Updated to iterate through multiple users per scan cycle.

```python
class AgentLoop:
    """
    Multi-user agent loop that scans for opportunities across all users.
    
    Attributes:
        wallet_manager: MultiUserWalletManager - Manages all user wallets
        scanner: Scanner - Finds opportunities
        provider: Provider - LLM decision making
        notifier: Notifier - Telegram notifications
        user_control: UserControl - User preferences
        risk_manager: RiskManager - Risk controls
        performance_tracker: PerformanceTracker - Per-user performance
        database: Database - Persistent storage
        scan_interval: int - Seconds between scans
        min_trading_balance: float - Minimum balance to trade (0.01 SOL)
    """
    
    async def scan_cycle(self) -> Dict[str, List[Opportunity]]:
        """
        Execute one scan cycle across all users.
        
        Returns:
            Dict mapping user_id to list of opportunities found
        """
        pass
    
    async def scan_user(self, user_id: str) -> List[Opportunity]:
        """
        Scan for opportunities for a specific user.
        
        Args:
            user_id: User to scan for
            
        Returns:
            List of opportunities found for this user
        """
        pass
    
    async def check_balance_and_notify(self, user_id: str, current_balance: float):
        """
        Check if balance crossed trading threshold and notify user.
        
        Args:
            user_id: User ID
            current_balance: Current SOL balance
        """
        pass
```

### 3. Wallet Commands

New Telegram commands for wallet management.

```python
class WalletCommands:
    """Wallet management commands."""
    
    async def cmd_createwallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Create new wallet for user.
        
        Command: /createwallet
        
        Response:
            - Wallet address
            - 12-word mnemonic phrase
            - Security warning to save mnemonic
        """
        pass
    
    async def cmd_importwallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Import wallet from mnemonic.
        
        Command: /importwallet <mnemonic phrase>
        
        Response:
            - Wallet address
            - Confirmation message
        """
        pass
    
    async def cmd_exportkey(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Export user's private key/mnemonic.
        
        Command: /exportkey
        
        Response:
            - Mnemonic phrase (sent privately)
            - Security warning
        """
        pass
```

### 4. Modified PerformanceTracker

Updated to track performance per user.

```python
class PerformanceTracker:
    """
    Track trading performance per user.
    
    Attributes:
        database: Database - For persistent storage
        user_metrics: Dict[user_id, UserMetrics] - Cached metrics per user
    """
    
    def record_trade(self, user_id: str, trade_record: TradeRecord):
        """
        Record trade for specific user.
        
        Args:
            user_id: User who executed the trade
            trade_record: Trade details
        """
        pass
    
    def get_metrics(self, user_id: str) -> PerformanceMetrics:
        """
        Get performance metrics for user.
        
        Args:
            user_id: User ID
            
        Returns:
            PerformanceMetrics for this user
        """
        pass
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Get anonymized leaderboard of top performers.
        
        Args:
            limit: Number of top users to return
            
        Returns:
            List of {rank, profit, win_rate} (no user IDs)
        """
        pass
```

## Data Models

### User Wallet Metadata (secure_wallets table)

```python
{
    "wallet_id": int,              # Primary key
    "user_id": str,                # Telegram user ID (unique)
    "public_key": str,             # Solana public key
    "derivation_path": str,        # BIP44 path
    "mnemonic_words": int,         # 12 or 24
    "kdf_method": str,             # "argon2id" or "pbkdf2"
    "encryption_method": str,      # "AES-256-GCM"
    "created_at": datetime,        # Wallet creation time
    "last_unlocked": datetime,     # Last access time
    "wallet_file_path": str        # Path to encrypted wallet file
}
```

### User Balance Tracking (in-memory)

```python
{
    "user_id": str,
    "current_balance": float,      # Current SOL balance
    "previous_balance": float,     # Balance from last check
    "last_check": datetime,        # Last balance check time
    "trading_active": bool         # Whether balance >= min_trading_balance
}
```

### Trade Record (trades table)

```python
{
    "trade_id": int,               # Primary key
    "user_id": str,                # User who executed trade
    "strategy_name": str,          # Strategy used
    "action": str,                 # Trade action
    "amount": float,               # Trade amount in SOL
    "profit": float,               # Profit/loss in SOL
    "transaction_hash": str,       # Solana transaction hash
    "timestamp": datetime,         # Trade execution time
    "details": dict                # Additional trade details
}
```

### User Performance Metrics

```python
{
    "user_id": str,
    "total_profit": float,         # Total profit in SOL
    "total_trades": int,           # Number of trades
    "winning_trades": int,         # Profitable trades
    "losing_trades": int,          # Losing trades
    "win_rate": float,             # Percentage of winning trades
    "best_trade": float,           # Highest profit trade
    "worst_trade": float,          # Worst loss trade
    "profit_by_strategy": dict     # Profit breakdown by strategy
}
```

## Error Handling

### Wallet Creation/Import Errors

1. **Duplicate Wallet**: User already has a wallet registered
   - Response: "You already have a wallet. Use /exportkey to access it."
   - Action: Reject creation/import request

2. **Invalid Mnemonic**: Mnemonic phrase is invalid
   - Response: "Invalid mnemonic phrase. Please check and try again."
   - Action: Reject import request

3. **Database Error**: Failed to store wallet metadata
   - Response: "Failed to create wallet. Please try again later."
   - Action: Log error, rollback any partial changes

### Trading Loop Errors

1. **User Wallet Load Failure**: Cannot load wallet for user
   - Action: Log error, skip user for this cycle, continue with other users
   - Notification: None (avoid spamming user)

2. **Balance Check Failure**: RPC error when checking balance
   - Action: Log error, skip user for this cycle, continue with other users
   - Notification: None (transient RPC errors are common)

3. **Trade Execution Failure**: Transaction fails for one user
   - Action: Log error, record failed trade, continue with other users
   - Notification: Send failure notification to affected user only

4. **Database Write Failure**: Cannot record trade
   - Action: Log error, continue operation (trade still executed on-chain)
   - Notification: None (trade succeeded even if recording failed)

### Isolation Guarantees

- Each user's scan/trade cycle is independent
- Errors for one user do not affect other users
- Failed trades for one user don't stop the bot
- Database errors are logged but don't crash the bot

## Testing Strategy

### Unit Tests

1. **MultiUserWalletManager Tests**
   - Test wallet creation with valid user ID
   - Test wallet import with valid mnemonic
   - Test duplicate wallet rejection
   - Test invalid mnemonic rejection
   - Test balance retrieval for existing wallet
   - Test balance retrieval for non-existent wallet
   - Test export key for existing wallet

2. **AgentLoop Multi-User Tests**
   - Test scan cycle with no users
   - Test scan cycle with one user above min balance
   - Test scan cycle with one user below min balance
   - Test scan cycle with multiple users (mixed balances)
   - Test balance threshold crossing detection
   - Test error isolation (one user fails, others continue)

3. **WalletCommands Tests**
   - Test /createwallet command
   - Test /importwallet command with valid mnemonic
   - Test /importwallet command with invalid mnemonic
   - Test /exportkey command
   - Test commands without registered wallet

4. **PerformanceTracker Tests**
   - Test recording trade for specific user
   - Test retrieving metrics for specific user
   - Test metrics isolation between users
   - Test leaderboard generation

### Integration Tests

1. **End-to-End User Flow**
   - Create wallet → Add funds → Automatic trading activation
   - Execute trade → Check performance metrics
   - Export key → Verify mnemonic matches

2. **Multi-User Scenarios**
   - Multiple users with different balances
   - Concurrent trade execution for different users
   - Performance tracking across multiple users

3. **Error Recovery**
   - Bot restart with existing users
   - Database connection loss and recovery
   - RPC failures for individual users

### Property-Based Tests

Property-based tests will be defined in the Correctness Properties section below.


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Wallet Management Properties

**Property 1: Wallet Creation Generates Valid Mnemonic**
*For any* user ID, when creating a wallet, the system should return a valid Solana public key and a mnemonic phrase with exactly 12 words that can recreate the same public key.
**Validates: Requirements 1.1, 9.1**

**Property 2: Wallet Import Preserves Public Key**
*For any* valid 12 or 24-word mnemonic phrase, importing the wallet should produce the same public key as deriving it directly from the mnemonic.
**Validates: Requirements 1.2, 9.2**

**Property 3: Wallet Metadata Persistence**
*For any* wallet created or imported, the database should contain an entry in secure_wallets table with the user_id, public_key, and encryption metadata.
**Validates: Requirements 1.3, 8.1**

**Property 4: User-Wallet Association Uniqueness**
*For any* user ID, the database should associate at most one wallet with that user, and each wallet should be associated with exactly one user.
**Validates: Requirements 1.4, 7.1**

**Property 5: Duplicate Wallet Prevention**
*For any* user who already has a wallet registered, attempting to create or import another wallet should be rejected with an error.
**Validates: Requirements 1.5**

**Property 6: Key Export Round Trip**
*For any* wallet, exporting the key and then importing it should produce a wallet with the same public key.
**Validates: Requirements 1.6, 9.5**

### Continuous Operation Properties

**Property 7: Error Isolation Between Users**
*For any* set of users where one user's operation fails (wallet load, balance check, or trade execution), all other users should continue to be processed normally in the same scan cycle.
**Validates: Requirements 2.4, 4.4**

### Multi-User Scanning Properties

**Property 8: All Users Scanned Per Cycle**
*For any* scan cycle, the trading loop should iterate through all users with registered wallets exactly once.
**Validates: Requirements 3.1**

**Property 9: Balance Check Before Scanning**
*For any* user being scanned, the system should check the user's wallet balance before attempting to scan for opportunities.
**Validates: Requirements 3.2**

**Property 10: Balance Threshold Enforcement**
*For any* user with balance less than 0.01 SOL, the system should skip opportunity scanning for that user; for any user with balance greater than or equal to 0.01 SOL, the system should scan all enabled strategies.
**Validates: Requirements 3.3, 3.4**

**Property 11: User Opportunity Independence**
*For any* set of opportunities found for multiple users, processing an opportunity for one user should not affect the opportunities or processing for any other user.
**Validates: Requirements 3.5**

### Trade Execution Properties

**Property 12: Correct Wallet Signs Transactions**
*For any* trade executed for a user, the transaction signature should be verifiable using that user's public key and no other user's public key.
**Validates: Requirements 4.1, 7.3**

**Property 13: Fees Deducted From Correct Wallet**
*For any* trade executed for a user, the user's wallet balance should decrease by at least the transaction fee amount.
**Validates: Requirements 4.2**

**Property 14: Trade Recording With User Association**
*For any* trade executed for a user, the database should contain a trade record with the correct user_id, transaction_hash, and profit/loss amount.
**Validates: Requirements 4.3, 5.1, 8.3**

### Performance Tracking Properties

**Property 15: User Data Isolation**
*For any* user requesting their performance statistics, trading history, or wallet information, the response should contain only data associated with that user's ID and no other user's data.
**Validates: Requirements 5.2, 5.4, 7.5**

**Property 16: Per-User Performance Aggregation**
*For any* set of trades executed by multiple users, calculating performance metrics for one user should only include trades with that user's ID.
**Validates: Requirements 5.3**

**Property 17: Anonymized Leaderboard**
*For any* leaderboard generated, the result should contain only ranks and metrics (profit, win_rate) without any user identifiers.
**Validates: Requirements 5.5**

### Automatic Trading Activation Properties

**Property 18: Automatic Activation On Balance Increase**
*For any* user whose balance increases from below 0.01 SOL to at least 0.01 SOL, the system should automatically begin scanning for opportunities for that user in the next scan cycle.
**Validates: Requirements 6.1**

**Property 19: Automatic Deactivation On Balance Decrease**
*For any* user whose balance decreases from at least 0.01 SOL to below 0.01 SOL, the system should stop scanning for opportunities for that user.
**Validates: Requirements 6.2**

**Property 20: Trading Reactivation Round Trip**
*For any* user, if trading is deactivated due to low balance and then the balance increases above 0.01 SOL again, trading should resume automatically.
**Validates: Requirements 6.3**

**Property 21: Balance Detection Within Scan Cycle**
*For any* user who adds funds to their wallet, the system should detect the balance change within one scan cycle interval.
**Validates: Requirements 6.4**

**Property 22: Activation Notification**
*For any* user whose trading is automatically activated, the system should send a Telegram notification to that user.
**Validates: Requirements 6.5**

### Security and Authorization Properties

**Property 23: Wallet Operation Authorization**
*For any* wallet operation request (balance check, export key, trade execution), the system should verify that the requesting user's ID matches the wallet owner's ID before proceeding.
**Validates: Requirements 7.2**

### Database Persistence Properties

**Property 24: Wallet Persistence Across Restarts**
*For any* set of wallets created before a system restart, all wallets should be loadable from the database after the restart with the same user_id and public_key associations.
**Validates: Requirements 8.2**

**Property 25: User Preferences Persistence**
*For any* user preferences set through the User_Manager, the preferences should be stored in the database and retrievable after the operation completes.
**Validates: Requirements 8.4**

**Property 26: SQL Injection Prevention**
*For any* user input containing SQL special characters (quotes, semicolons, etc.), the database queries should use parameterized queries that prevent the input from being executed as SQL code.
**Validates: Requirements 8.5**

### Scalability Properties

**Property 27: Batch RPC Requests**
*For any* scan cycle with multiple users, the system should use batch RPC requests where possible to reduce the total number of API calls compared to individual requests.
**Validates: Requirements 10.1**

**Property 28: Rate Limiting Enforcement**
*For any* sequence of RPC requests, the system should enforce rate limits to ensure the request rate stays below the configured threshold.
**Validates: Requirements 10.2**

**Property 29: Staggered Scanning For Large User Base**
*For any* scan cycle with more than 100 users, the system should distribute user scanning over time rather than scanning all users simultaneously.
**Validates: Requirements 10.3**

**Property 30: Price Cache Reuse**
*For any* token price lookup during a scan cycle, if the price was cached within the TTL window, the system should return the cached price without making a new RPC call.
**Validates: Requirements 10.4**

**Property 31: Trade Queue Ordering**
*For any* set of approved trades for multiple users, the trades should be executed sequentially in the order they were approved, not concurrently.
**Validates: Requirements 10.5**

