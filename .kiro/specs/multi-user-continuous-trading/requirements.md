# Requirements Document

## Introduction

This document specifies the requirements for implementing multi-user continuous trading operation for the Harvest Telegram bot. Currently, the bot operates in single-user mode with one wallet and stops when the balance reaches 0 SOL. The new system will enable the bot to run 24/7, continuously hunting for trading opportunities for all registered users, each with their own isolated wallet and performance tracking.

## Glossary

- **Bot**: The Harvest Telegram bot application that runs continuously
- **User**: An individual Telegram user who has registered with the bot
- **Wallet**: A Solana wallet containing a keypair (public/private key) for executing transactions
- **Trading_Loop**: The continuous process that scans for opportunities and executes trades
- **Opportunity**: A potential profitable trade identified by a strategy
- **Strategy**: A trading algorithm (e.g., airdrop hunter, liquid staking, arbitrage)
- **Balance**: The amount of SOL in a user's wallet
- **Performance_Tracker**: Component that records and analyzes trading results per user
- **Database**: SQLite database storing user data, wallets, and trade history
- **Secure_Wallets_Table**: Database table storing encrypted wallet metadata
- **User_Manager**: Service managing multiple user profiles and preferences
- **Minimum_Trading_Balance**: 0.01 SOL - the minimum balance required to execute trades

## Requirements

### Requirement 1: Multi-User Wallet Management

**User Story:** As a user, I want to create or import my own wallet via Telegram commands, so that I can have my own isolated trading account.

#### Acceptance Criteria

1. WHEN a user sends the /createwallet command, THE Bot SHALL generate a new Solana wallet with a 12-word mnemonic phrase
2. WHEN a user sends the /importwallet command with a valid mnemonic phrase, THE Bot SHALL import the wallet and associate it with the user
3. WHEN a wallet is created or imported, THE Bot SHALL encrypt the private key and store it securely in the Secure_Wallets_Table
4. WHEN a wallet is created or imported, THE Bot SHALL associate the wallet's public key with the user's Telegram ID in the Database
5. WHEN a user already has a wallet registered, THE Bot SHALL reject attempts to create or import a new wallet and inform the user
6. WHEN a user sends the /exportkey command, THE Bot SHALL return their encrypted private key or mnemonic phrase securely via Telegram

### Requirement 2: Continuous Bot Operation

**User Story:** As a platform operator, I want the bot to run 24/7 regardless of individual user balances, so that users can always interact with the bot and access their wallets.

#### Acceptance Criteria

1. WHEN the Bot starts, THE Bot SHALL remain online continuously regardless of any individual user's balance
2. WHEN all users have 0 SOL balance, THE Bot SHALL continue running and remain responsive to Telegram commands
3. WHEN a user has 0 SOL balance, THE Bot SHALL allow the user to use chat commands including /exportkey
4. WHEN the Bot encounters an error for one user, THE Bot SHALL log the error and continue processing other users
5. WHEN the Bot is running, THE Bot SHALL maintain a persistent connection to the Telegram API

### Requirement 3: Multi-User Opportunity Scanning

**User Story:** As a platform operator, I want the bot to scan for trading opportunities for all registered users, so that every user can benefit from automated trading.

#### Acceptance Criteria

1. WHEN the Trading_Loop executes a scan cycle, THE Trading_Loop SHALL iterate through all users with registered wallets
2. WHEN scanning for a user, THE Trading_Loop SHALL check the user's wallet balance before scanning for opportunities
3. WHEN a user's balance is less than Minimum_Trading_Balance, THE Trading_Loop SHALL skip opportunity scanning for that user
4. WHEN a user's balance is greater than or equal to Minimum_Trading_Balance, THE Trading_Loop SHALL scan all enabled strategies for that user
5. WHEN opportunities are found for multiple users, THE Trading_Loop SHALL process each user's opportunities independently

### Requirement 4: Per-User Trade Execution

**User Story:** As a user, I want trades to be executed using my own wallet, so that I maintain full control and ownership of my funds.

#### Acceptance Criteria

1. WHEN an opportunity is approved for execution, THE Bot SHALL sign the transaction using the specific user's wallet keypair
2. WHEN executing a trade, THE Bot SHALL deduct transaction fees from the user's wallet balance
3. WHEN a trade completes, THE Bot SHALL record the transaction hash associated with the user's account
4. WHEN a trade fails for one user, THE Bot SHALL continue processing opportunities for other users
5. WHEN multiple users have approved opportunities, THE Bot SHALL execute trades sequentially to avoid nonce conflicts

### Requirement 5: Per-User Performance Tracking

**User Story:** As a user, I want my trading performance tracked separately from other users, so that I can see my individual profit and loss.

#### Acceptance Criteria

1. WHEN a trade is executed for a user, THE Performance_Tracker SHALL record the trade result associated with that user's ID
2. WHEN a user requests their performance statistics, THE Bot SHALL return only that user's trade history and metrics
3. WHEN calculating daily performance, THE Performance_Tracker SHALL aggregate trades per user separately
4. WHEN displaying profit metrics, THE Bot SHALL show each user only their own total profit, win rate, and strategy performance
5. WHEN a user views the leaderboard, THE Bot SHALL display anonymized rankings without revealing other users' identities

### Requirement 6: Automatic Trading Activation

**User Story:** As a user, I want trading to start automatically when I add funds to my wallet, so that I don't need to manually enable trading.

#### Acceptance Criteria

1. WHEN the Trading_Loop scans and detects a user's balance has increased to at least Minimum_Trading_Balance, THE Trading_Loop SHALL automatically begin scanning for opportunities for that user
2. WHEN a user's balance drops below Minimum_Trading_Balance during operation, THE Trading_Loop SHALL stop scanning for opportunities for that user
3. WHEN a user's balance increases above Minimum_Trading_Balance again, THE Trading_Loop SHALL resume scanning for opportunities for that user
4. WHEN a user adds funds to their wallet, THE Bot SHALL detect the balance change within the next scan cycle
5. WHEN trading is automatically activated for a user, THE Bot SHALL send a Telegram notification informing the user

### Requirement 7: User Isolation and Security

**User Story:** As a user, I want my wallet and trading activity isolated from other users, so that my funds and data remain secure and private.

#### Acceptance Criteria

1. WHEN storing wallet data, THE Database SHALL associate each wallet with exactly one user ID
2. WHEN a user requests wallet operations, THE Bot SHALL verify the requesting user owns the wallet before proceeding
3. WHEN executing trades, THE Bot SHALL ensure each user's transactions are signed only with their own private key
4. WHEN one user's wallet is compromised, THE Bot SHALL ensure other users' wallets remain unaffected
5. WHEN displaying user data, THE Bot SHALL ensure users can only view their own trading history and wallet information

### Requirement 8: Database Integration

**User Story:** As a platform operator, I want user data stored in a reliable database, so that user information persists across bot restarts.

#### Acceptance Criteria

1. WHEN a user creates a wallet, THE Bot SHALL store the wallet metadata in the Secure_Wallets_Table
2. WHEN the Bot restarts, THE Bot SHALL load all user wallets from the Database
3. WHEN a trade is executed, THE Bot SHALL record the trade in the Database associated with the user's ID
4. WHEN storing user preferences, THE Bot SHALL use the existing User_Manager to persist settings to the Database
5. WHEN querying user data, THE Bot SHALL use parameterized queries to prevent SQL injection

### Requirement 9: Telegram Command Interface

**User Story:** As a user, I want to manage my wallet and view my performance through Telegram commands, so that I can control my trading without leaving Telegram.

#### Acceptance Criteria

1. WHEN a user sends /createwallet, THE Bot SHALL create a new wallet and return the mnemonic phrase
2. WHEN a user sends /importwallet <mnemonic>, THE Bot SHALL import the wallet and confirm success
3. WHEN a user sends /balance, THE Bot SHALL return the user's current SOL balance
4. WHEN a user sends /stats, THE Bot SHALL return the user's trading performance metrics
5. WHEN a user sends /exportkey, THE Bot SHALL return the user's private key or mnemonic securely
6. WHEN a user sends /wallet, THE Bot SHALL return the user's public wallet address
7. WHEN a user sends a command without a registered wallet, THE Bot SHALL prompt them to create or import a wallet first

### Requirement 10: Scalable Architecture

**User Story:** As a platform operator, I want the bot architecture to scale efficiently with multiple users, so that performance remains acceptable as the user base grows.

#### Acceptance Criteria

1. WHEN scanning for opportunities, THE Trading_Loop SHALL use batch RPC requests where possible to reduce API calls
2. WHEN processing multiple users, THE Trading_Loop SHALL implement rate limiting to avoid exceeding RPC provider limits
3. WHEN the number of users exceeds 100, THE Trading_Loop SHALL implement staggered scanning to distribute load over time
4. WHEN caching is available, THE Bot SHALL cache shared data like token prices across all users
5. WHEN executing trades, THE Bot SHALL implement a queue system to handle concurrent trade requests efficiently
