# Implementation Plan: Multi-User Continuous Trading

## Overview

This implementation plan transforms the Harvest Telegram bot from single-user to multi-user operation. The approach is to:

1. Create MultiUserWalletManager to handle multiple wallets
2. Add wallet management commands to Telegram bot
3. Modify AgentLoop to iterate through all users
4. Update PerformanceTracker for per-user metrics
5. Add balance tracking and automatic activation logic
6. Implement error isolation between users
7. Add scalability optimizations (batching, caching, rate limiting)

## Tasks

- [x] 1. Create MultiUserWalletManager component
  - [x] 1.1 Implement wallet creation with mnemonic generation
    - Create `create_wallet(user_id)` method that generates a new Solana keypair
    - Generate 12-word BIP39 mnemonic phrase
    - Encrypt and store wallet metadata in secure_wallets table
    - Return public key and mnemonic phrase
    - _Requirements: 1.1, 9.1_
  
  - [ ]* 1.2 Write property test for wallet creation
    - **Property 1: Wallet Creation Generates Valid Mnemonic**
    - **Validates: Requirements 1.1, 9.1**
  
  - [x] 1.3 Implement wallet import from mnemonic
    - Create `import_wallet(user_id, mnemonic)` method
    - Validate mnemonic phrase (12 or 24 words)
    - Derive keypair from mnemonic
    - Store encrypted wallet metadata in database
    - Return public key
    - _Requirements: 1.2, 9.2_
  
  - [ ]* 1.4 Write property test for wallet import
    - **Property 2: Wallet Import Preserves Public Key**
    - **Validates: Requirements 1.2, 9.2**
  
  - [x] 1.5 Implement wallet retrieval and caching
    - Create `get_wallet(user_id)` method that loads wallet from database
    - Implement in-memory cache of WalletManager instances
    - Handle wallet decryption and keypair reconstruction
    - Return WalletManager instance or None
    - _Requirements: 3.1, 3.2_
  
  - [x] 1.6 Implement balance checking per user
    - Create `get_balance(user_id)` method
    - Load user's wallet and query Solana RPC for balance
    - Cache balance with timestamp for rate limiting
    - _Requirements: 3.2, 9.3_
  
  - [x] 1.7 Implement key export functionality
    - Create `export_key(user_id)` method
    - Decrypt and return mnemonic phrase or private key
    - Add security logging for export operations
    - _Requirements: 1.6, 9.5_
  
  - [ ]* 1.8 Write property test for key export round trip
    - **Property 6: Key Export Round Trip**
    - **Validates: Requirements 1.6, 9.5**
  
  - [x] 1.9 Implement duplicate wallet prevention
    - Add check in create_wallet and import_wallet for existing wallet
    - Raise ValueError if user already has wallet
    - _Requirements: 1.5_
  
  - [ ]* 1.10 Write property test for duplicate prevention
    - **Property 5: Duplicate Wallet Prevention**
    - **Validates: Requirements 1.5**
  
  - [ ]* 1.11 Write property test for wallet metadata persistence
    - **Property 3: Wallet Metadata Persistence**
    - **Validates: Requirements 1.3, 8.1**
  
  - [ ]* 1.12 Write property test for user-wallet association uniqueness
    - **Property 4: User-Wallet Association Uniqueness**
    - **Validates: Requirements 1.4, 7.1**

- [ ] 2. Add wallet management commands to Telegram bot
  - [ ] 2.1 Implement /createwallet command
    - Add cmd_createwallet handler in WalletCommands class
    - Call MultiUserWalletManager.create_wallet()
    - Send wallet address and mnemonic to user with security warning
    - Handle errors (duplicate wallet, database failure)
    - _Requirements: 1.1, 9.1_
  
  - [ ] 2.2 Implement /importwallet command
    - Add cmd_importwallet handler in WalletCommands class
    - Parse mnemonic from command arguments
    - Call MultiUserWalletManager.import_wallet()
    - Send confirmation with wallet address
    - Handle errors (invalid mnemonic, duplicate wallet)
    - _Requirements: 1.2, 9.2_
  
  - [ ] 2.3 Implement /exportkey command
    - Add cmd_exportkey handler in WalletCommands class
    - Call MultiUserWalletManager.export_key()
    - Send mnemonic privately to user with security warning
    - Handle errors (no wallet registered)
    - _Requirements: 1.6, 9.5_
  
  - [ ] 2.4 Implement /balance command
    - Add cmd_balance handler in BasicCommands class
    - Call MultiUserWalletManager.get_balance()
    - Format and send balance to user
    - _Requirements: 9.3_
  
  - [ ] 2.5 Implement /wallet command
    - Add cmd_wallet handler in BasicCommands class
    - Get user's public key from MultiUserWalletManager
    - Send wallet address to user
    - _Requirements: 9.6_
  
  - [ ] 2.6 Add wallet requirement check to commands
    - Create decorator or helper function to check if user has wallet
    - Apply to commands that require a wallet (balance, stats, etc.)
    - Send prompt to create/import wallet if not registered
    - _Requirements: 9.7_
  
  - [ ]* 2.7 Write property test for wallet requirement check
    - **Property: Commands without wallet prompt registration**
    - **Validates: Requirements 9.7**

- [ ] 3. Checkpoint - Test wallet management
  - Ensure all wallet tests pass, verify wallet creation/import/export works correctly

- [x] 4. Modify AgentLoop for multi-user scanning
  - [x] 4.1 Update AgentLoop initialization
    - Replace single WalletManager with MultiUserWalletManager
    - Add min_trading_balance parameter (default 0.01 SOL)
    - Add user_balance_cache dictionary for tracking balances
    - _Requirements: 3.1, 3.2_
  
  - [x] 4.2 Implement multi-user scan_cycle
    - Get list of all user IDs from MultiUserWalletManager
    - Iterate through each user
    - For each user, call scan_user(user_id)
    - Collect and return opportunities per user
    - Implement error isolation (catch exceptions per user, continue with others)
    - _Requirements: 3.1, 2.4, 4.4_
  
  - [ ]* 4.3 Write property test for all users scanned
    - **Property 8: All Users Scanned Per Cycle**
    - **Validates: Requirements 3.1**
  
  - [ ]* 4.4 Write property test for error isolation
    - **Property 7: Error Isolation Between Users**
    - **Validates: Requirements 2.4, 4.4**
  
  - [x] 4.5 Implement scan_user method
    - Check user's wallet balance
    - Call check_balance_and_notify to detect threshold crossings
    - If balance < min_trading_balance, skip scanning and return empty list
    - If balance >= min_trading_balance, scan all enabled strategies
    - Return list of opportunities for this user
    - _Requirements: 3.2, 3.3, 3.4_
  
  - [ ]* 4.6 Write property test for balance check before scanning
    - **Property 9: Balance Check Before Scanning**
    - **Validates: Requirements 3.2**
  
  - [ ]* 4.7 Write property test for balance threshold enforcement
    - **Property 10: Balance Threshold Enforcement**
    - **Validates: Requirements 3.3, 3.4**
  
  - [x] 4.8 Implement check_balance_and_notify method
    - Get previous balance from user_balance_cache
    - Compare with current balance
    - Detect threshold crossings (below → above, above → below)
    - Send Telegram notification on activation/deactivation
    - Update user_balance_cache with current balance
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
  
  - [ ]* 4.9 Write property test for automatic activation
    - **Property 18: Automatic Activation On Balance Increase**
    - **Validates: Requirements 6.1**
  
  - [ ]* 4.10 Write property test for automatic deactivation
    - **Property 19: Automatic Deactivation On Balance Decrease**
    - **Validates: Requirements 6.2**
  
  - [ ]* 4.11 Write property test for reactivation round trip
    - **Property 20: Trading Reactivation Round Trip**
    - **Validates: Requirements 6.3**
  
  - [x] 4.12 Update _process_opportunity for per-user execution
    - Add user_id parameter to _process_opportunity
    - Get user's wallet from MultiUserWalletManager
    - Pass user's wallet to strategy execution
    - Record trade with user_id
    - _Requirements: 4.1, 4.2, 4.3_
  
  - [ ]* 4.13 Write property test for correct wallet signs transactions
    - **Property 12: Correct Wallet Signs Transactions**
    - **Validates: Requirements 4.1, 7.3**
  
  - [ ]* 4.14 Write property test for user opportunity independence
    - **Property 11: User Opportunity Independence**
    - **Validates: Requirements 3.5**

- [x] 5. Update PerformanceTracker for per-user metrics
  - [x] 5.1 Add user_id parameter to record_trade
    - Update record_trade method signature to include user_id
    - Store user_id with each trade record
    - Update database calls to include user_id
    - _Requirements: 5.1, 4.3, 8.3_
  
  - [ ]* 5.2 Write property test for trade recording with user association
    - **Property 14: Trade Recording With User Association**
    - **Validates: Requirements 4.3, 5.1, 8.3**
  
  - [x] 5.3 Update get_metrics to filter by user_id
    - Add user_id parameter to get_metrics method
    - Filter trades and calculations to only include specified user's data
    - Return PerformanceMetrics for that user only
    - _Requirements: 5.2, 5.3, 5.4_
  
  - [ ]* 5.4 Write property test for user data isolation
    - **Property 15: User Data Isolation**
    - **Validates: Requirements 5.2, 5.4, 7.5**
  
  - [ ]* 5.5 Write property test for per-user performance aggregation
    - **Property 16: Per-User Performance Aggregation**
    - **Validates: Requirements 5.3**
  
  - [x] 5.6 Implement get_leaderboard method
    - Query database for top users by total_profit
    - Return list of {rank, profit, win_rate} without user IDs
    - Limit to top N users (default 10)
    - _Requirements: 5.5_
  
  - [ ]* 5.7 Write property test for anonymized leaderboard
    - **Property 17: Anonymized Leaderboard**
    - **Validates: Requirements 5.5**

- [x] 6. Update main.py for multi-user initialization
  - [x] 6.1 Replace WalletManager with MultiUserWalletManager
    - Initialize MultiUserWalletManager with database and network
    - Remove single wallet initialization
    - Pass MultiUserWalletManager to AgentLoop
    - _Requirements: 2.1, 2.2_
  
  - [x] 6.2 Update startup logic for zero-balance handling
    - Remove balance check that stops bot when balance is 0
    - Send startup message indicating bot is online
    - Allow bot to run even with no users or all users at 0 balance
    - _Requirements: 2.1, 2.2, 2.3_
  
  - [x] 6.3 Update TelegramBot initialization
    - Pass MultiUserWalletManager to TelegramBot
    - Ensure WalletCommands has access to MultiUserWalletManager
    - _Requirements: 9.1, 9.2, 9.5_

- [ ] 7. Checkpoint - Test multi-user trading loop
  - Ensure all tests pass, verify multiple users can trade independently

- [x] 8. Implement security and authorization checks
  - [x] 8.1 Add wallet ownership verification
    - Create verify_wallet_owner helper method
    - Check that requesting user_id matches wallet owner
    - Apply to all wallet operations (balance, export, trade)
    - _Requirements: 7.2_
  
  - [ ]* 8.2 Write property test for wallet operation authorization
    - **Property 23: Wallet Operation Authorization**
    - **Validates: Requirements 7.2**
  
  - [x] 8.3 Add SQL injection prevention
    - Verify all database queries use parameterized queries
    - Add input validation for user_id and other user inputs
    - _Requirements: 8.5_
  
  - [ ]* 8.4 Write property test for SQL injection prevention
    - **Property 26: SQL Injection Prevention**
    - **Validates: Requirements 8.5**

- [x] 9. Implement database persistence features
  - [x] 9.1 Add wallet loading on startup
    - In MultiUserWalletManager.__init__, load all wallets from database
    - Populate wallet cache with user_id → wallet mappings
    - _Requirements: 8.2_
  
  - [ ]* 9.2 Write property test for wallet persistence across restarts
    - **Property 24: Wallet Persistence Across Restarts**
    - **Validates: Requirements 8.2**
  
  - [x] 9.3 Verify user preferences persistence
    - Ensure UserManager.save_user stores preferences to database
    - Test that preferences survive bot restart
    - _Requirements: 8.4_
  
  - [ ]* 9.4 Write property test for user preferences persistence
    - **Property 25: User Preferences Persistence**
    - **Validates: Requirements 8.4**

- [x] 10. Implement scalability optimizations
  - [x] 10.1 Add batch RPC requests for balance checks
    - Implement batch_get_balances method in MultiUserWalletManager
    - Use Solana RPC batch requests to check multiple balances at once
    - Process users in batches of 10-20
    - _Requirements: 10.1_
  
  - [ ]* 10.2 Write property test for batch RPC requests
    - **Property 27: Batch RPC Requests**
    - **Validates: Requirements 10.1**
  
  - [x] 10.3 Implement rate limiting for RPC calls
    - Add rate limiter to MultiUserWalletManager
    - Track requests per second/minute
    - Add delays when approaching rate limits
    - _Requirements: 10.2_
  
  - [ ]* 10.4 Write property test for rate limiting enforcement
    - **Property 28: Rate Limiting Enforcement**
    - **Validates: Requirements 10.2**
  
  - [x] 10.5 Implement staggered scanning for large user bases
    - In AgentLoop.scan_cycle, check user count
    - If > 100 users, divide into batches and stagger over time
    - Add configurable stagger window (default 60 seconds)
    - _Requirements: 10.3_
  
  - [ ]* 10.6 Write property test for staggered scanning
    - **Property 29: Staggered Scanning For Large User Base**
    - **Validates: Requirements 10.3**
  
  - [x] 10.7 Implement price caching across users
    - Use existing SharedPriceCache for token prices
    - Ensure price cache is shared across all user scans
    - Verify cache TTL is respected
    - _Requirements: 10.4_
  
  - [ ]* 10.8 Write property test for price cache reuse
    - **Property 30: Price Cache Reuse**
    - **Validates: Requirements 10.4**
  
  - [x] 10.9 Implement trade execution queue
    - Create TradeQueue class to serialize trade execution
    - Add trades to queue instead of executing immediately
    - Process queue sequentially to avoid nonce conflicts
    - _Requirements: 10.5_
  
  - [ ]* 10.10 Write property test for trade queue ordering
    - **Property 31: Trade Queue Ordering**
    - **Validates: Requirements 10.5**

- [x] 11. Add comprehensive error handling
  - [x] 11.1 Add error handling for wallet operations
    - Wrap wallet creation/import in try-catch blocks
    - Return user-friendly error messages
    - Log detailed errors for debugging
    - _Requirements: 1.1, 1.2, 1.5, 1.6_
  
  - [x] 11.2 Add error handling for balance checks
    - Handle RPC failures gracefully
    - Return cached balance if RPC fails
    - Log errors but don't crash bot
    - _Requirements: 3.2, 6.4_
  
  - [x] 11.3 Add error handling for trade execution
    - Catch and log trade failures per user
    - Continue processing other users on failure
    - Send failure notification to affected user only
    - _Requirements: 4.4, 2.4_

- [x] 12. Update Telegram command responses
  - [x] 12.1 Update /stats command for per-user metrics
    - Modify cmd_stats to get user_id from message
    - Call PerformanceTracker.get_metrics(user_id)
    - Format and display user's individual metrics
    - _Requirements: 5.2, 9.4_
  
  - [x] 12.2 Add /leaderboard command
    - Create cmd_leaderboard handler
    - Call PerformanceTracker.get_leaderboard()
    - Display anonymized rankings
    - _Requirements: 5.5_
  
  - [x] 12.3 Update notification messages for multi-user
    - Include user identification in notifications
    - Send notifications to correct user's chat
    - Add activation/deactivation notifications
    - _Requirements: 6.5_

- [x] 13. Final checkpoint - Integration testing
  - Ensure all tests pass, verify end-to-end multi-user flows work correctly

- [x] 14. Documentation and cleanup
  - [x] 14.1 Update README with multi-user setup instructions
    - Document /createwallet and /importwallet commands
    - Explain minimum balance requirement
    - Add security best practices for key management
  
  - [x] 14.2 Add code comments and docstrings
    - Document MultiUserWalletManager methods
    - Document AgentLoop changes
    - Add inline comments for complex logic
  
  - [x] 14.3 Update configuration documentation
    - Document new environment variables (if any)
    - Update deployment guide for multi-user mode

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Error isolation is critical - one user's failure should never affect others
- Security is paramount - wallet operations must verify ownership
- Scalability optimizations can be implemented incrementally
