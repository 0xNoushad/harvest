# TestHarness Usage Guide

## Overview

The `TestHarness` class provides a unified interface for creating mock objects and test utilities for the Harvest Telegram bot testing infrastructure. It consolidates all mock factories into a single, easy-to-use class.

## Quick Start

```python
from tests.test_harness import TestHarness

# Create a test harness instance
harness = TestHarness()

# Create mock objects
update = harness.create_mock_telegram_update("start", user_id=12345)
wallet = harness.create_mock_wallet(balance=1.5)
user = harness.create_test_user(user_id=12345, wallet_balance=1.5)
```

## Using with Pytest Fixtures

The TestHarness is available as a pytest fixture:

```python
def test_my_feature(test_harness):
    # Use the harness directly
    update = test_harness.create_mock_telegram_update("wallet")
    wallet = test_harness.create_mock_wallet(balance=2.0)
    
    # Your test code here
```

## Available Mock Factories

### Telegram Mocks

#### create_mock_telegram_update()
Creates a mock Telegram Update object for command testing.

```python
# Basic command
update = harness.create_mock_telegram_update("start", user_id=12345)

# Command with arguments
update = harness.create_mock_telegram_update(
    "withdraw",
    user_id=12345,
    args=["1.0", "ABC123..."]
)

# Custom message text
update = harness.create_mock_telegram_update(
    "custom",
    message_text="Custom message"
)
```

#### create_mock_telegram_context()
Creates a mock Telegram Context object.

```python
context = harness.create_mock_telegram_context(
    args=["arg1", "arg2"],
    bot_data={"key": "value"},
    user_data={"user_key": "user_value"}
)

# Access bot methods
await context.bot.send_message(chat_id, "Hello!")
```

#### create_mock_telegram_callback_query()
Creates a mock Telegram CallbackQuery object for button interactions.

```python
query = harness.create_mock_telegram_callback_query(
    "approve_fee",
    user_id=12345
)

await query.answer()
await query.edit_message_text("Updated!")
```

### Wallet Mocks

#### create_mock_wallet()
Creates a mock WalletManager object.

```python
wallet = harness.create_mock_wallet(
    balance=1.5,
    address="TestAddress123",
    network="devnet"
)

# Use wallet methods
balance = await wallet.get_balance()  # Returns 1.5
address = wallet.get_address()  # Returns "TestAddress123"
signature = await wallet.withdraw()  # Returns "mock_signature_123"
```

#### create_mock_keypair()
Creates a mock Solana Keypair object.

```python
keypair = harness.create_mock_keypair(
    public_key="TestPubKey123"
)

print(str(keypair.pubkey))  # "TestPubKey123"
```

### Performance Tracking Mocks

#### create_mock_performance_tracker()
Creates a mock PerformanceTracker for stats testing.

```python
tracker = harness.create_mock_performance_tracker(
    total_profit=0.5,
    win_rate=68.5,
    total_trades=100,
    winning_trades=68
)

# Use tracker methods
profit = tracker.get_total_profit()  # Returns 0.5
win_rate = tracker.get_win_rate()  # Returns 68.5
```

#### create_mock_risk_manager()
Creates a mock RiskManager object.

```python
risk_mgr = harness.create_mock_risk_manager(
    is_paused=False,
    risk_level="medium",
    position_size=0.1
)

# Check risk status
is_paused = risk_mgr.is_paused()  # Returns False
level = risk_mgr.get_risk_level()  # Returns "medium"
```

### User and Trade Mocks

#### create_test_user()
Creates a test User object for multi-user testing.

```python
user = harness.create_test_user(
    user_id=12345,
    telegram_username="testuser",
    wallet_balance=1.5,
    fee_status="paid"
)

# Access user data
print(user["user_id"])  # 12345
print(user["wallet_balance"])  # 1.5
```

#### create_test_trade()
Creates a test Trade object.

```python
trade = harness.create_test_trade(
    strategy="jupiter_swap",
    expected_profit=0.01,
    actual_profit=0.009,
    status="completed"
)

# Access trade data
print(trade["strategy"])  # "jupiter_swap"
print(trade["actual_profit"])  # 0.009
```

### Service Mocks

#### create_mock_price_service()
Creates a mock PriceService object.

```python
price_svc = harness.create_mock_price_service(default_price=150.0)

price_data = await price_svc.get_price()
# Returns: {"price": 150.0, "change_24h": 5.0, "market_cap": 1000000000}
```

#### create_mock_portfolio_service()
Creates a mock PortfolioService object.

```python
holdings = [{"symbol": "SOL", "amount": 10.0}]
portfolio_svc = harness.create_mock_portfolio_service(
    holdings=holdings,
    total_value=1500.0
)

result = await portfolio_svc.get_portfolio()  # Returns holdings
total = await portfolio_svc.calculate_total_value()  # Returns 1500.0
```

#### create_mock_ai_chat()
Creates a mock AI Chat object.

```python
ai_chat = harness.create_mock_ai_chat(
    default_response="Hello! How can I help?"
)

response = await ai_chat.generate_response()
# Returns: "Hello! How can I help?"
```

## RPC and API Mock Utilities

### mock_rpc_response()
Creates a mock RPC response.

```python
rpc_resp = harness.mock_rpc_response("getBalance", 1000000000)
# Returns: {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "result": 1000000000}
```

### mock_api_response()
Creates a mock API response.

```python
api_resp = harness.mock_api_response(
    "jupiter",
    "/quote",
    {"price": 100.0},
    status_code=200
)

print(api_resp.status_code)  # 200
print(api_resp.json())  # {"price": 100.0}
print(api_resp.ok)  # True
```

## Assertion Helpers

### assert_telegram_message_sent()
Asserts that a Telegram message was sent.

```python
# Send a message
await context.bot.send_message(12345, "Welcome!")

# Assert it was sent
harness.assert_telegram_message_sent(
    context.bot,
    12345,
    text_contains="Welcome"
)

# Assert call count
harness.assert_telegram_message_sent(
    context.bot,
    12345,
    call_count=1
)
```

### assert_transaction_executed()
Asserts that a blockchain transaction was executed.

```python
wallet = harness.create_mock_wallet()
signature = await wallet.withdraw()

# Assert transaction was executed
harness.assert_transaction_executed(wallet)

# Verify the signature
assert signature == "mock_signature_123"
```

### wait_for_async_operation()
Waits for an async condition to become true.

```python
wallet = harness.create_mock_wallet()

# Trigger operation
await wallet.get_balance()

# Wait for it to complete
result = await harness.wait_for_async_operation(
    lambda: wallet.get_balance.called,
    timeout=1.0
)
```

## Utility Methods

### reset_mocks()
Resets call counts on mock objects.

```python
wallet = harness.create_mock_wallet()
await wallet.get_balance()

# Reset the mock
harness.reset_mocks(wallet)

# Call count is now 0
assert wallet.get_balance.call_count == 0
```

### get_call_count()
Gets the call count for a specific method.

```python
wallet = harness.create_mock_wallet()
await wallet.get_balance()

count = harness.get_call_count(wallet, "get_balance")
assert count == 1
```

## Complete Example

Here's a complete example of testing a command handler:

```python
import pytest
from tests.test_harness import TestHarness

@pytest.mark.asyncio
async def test_wallet_command():
    # Setup
    harness = TestHarness()
    update = harness.create_mock_telegram_update("wallet", user_id=12345)
    context = harness.create_mock_telegram_context()
    wallet = harness.create_mock_wallet(balance=1.5)
    
    # Execute command (pseudo-code)
    balance = await wallet.get_balance()
    await context.bot.send_message(
        update.message.chat_id,
        f"💰 Your balance: {balance} SOL"
    )
    
    # Verify
    assert wallet.get_balance.called
    harness.assert_telegram_message_sent(
        context.bot,
        12345,
        text_contains="1.5 SOL"
    )
```

## Multi-User Testing Example

```python
@pytest.mark.asyncio
async def test_multi_user_isolation():
    harness = TestHarness()
    
    # Create multiple users
    user1 = harness.create_test_user(user_id=1, wallet_balance=1.0)
    user2 = harness.create_test_user(user_id=2, wallet_balance=2.0)
    user3 = harness.create_test_user(user_id=3, wallet_balance=3.0)
    
    # Verify isolation
    assert user1["user_id"] != user2["user_id"]
    assert user1["wallet_balance"] != user2["wallet_balance"]
    
    # Each user has independent state
    assert user1["preferences"] is not user2["preferences"]
```

## Best Practices

1. **Use the fixture**: Always use the `test_harness` fixture in your tests for consistency.

2. **Reset mocks between tests**: Use `harness.reset_mocks()` when reusing mocks across test cases.

3. **Verify behavior, not implementation**: Use assertion helpers to verify outcomes, not internal implementation details.

4. **Create realistic test data**: Use appropriate values for balances, addresses, and other data to make tests meaningful.

5. **Test isolation**: Each test should create its own mocks to ensure independence.

## Integration with Existing Fixtures

The TestHarness works alongside existing pytest fixtures in `conftest.py`. You can use both:

```python
def test_with_both(test_harness, mock_telegram_update):
    # Use TestHarness
    wallet = test_harness.create_mock_wallet(balance=1.5)
    
    # Use existing fixture
    update = mock_telegram_update("start", user_id=12345)
    
    # Both work together
```

## See Also

- `conftest.py` - Pytest configuration and fixtures
- `test_utils.py` - Additional test utilities
- `generators.py` - Hypothesis strategies for property-based testing
- Design document: `.kiro/specs/telegram-bot-testing-improvements/design.md`


## Mock Response Utilities (Task 2.2)

The TestHarness now includes enhanced mock response utilities and a comprehensive fixture library for all external services.

### Enhanced mock_rpc_response()

Creates properly formatted JSON-RPC 2.0 responses for Solana RPC and Helius RPC calls.

```python
# Success response
rpc_resp = harness.mock_rpc_response(
    "getBalance", 
    {"value": 1000000000, "context": {"slot": 123456}}
)

# Error response
rpc_resp = harness.mock_rpc_response(
    "getBalance",
    None,
    error={"code": -32602, "message": "Invalid params"}
)

# With context
rpc_resp = harness.mock_rpc_response(
    "getAccountInfo",
    {"value": {"data": "...", "lamports": 1000000}},
    context={"slot": 123456, "apiVersion": "1.14.0"}
)
```

### Enhanced mock_api_response()

Creates mock HTTP response objects for external services with support for custom headers, status codes, and simulated delays.

```python
# Jupiter quote response
api_resp = harness.mock_api_response(
    "jupiter", 
    "/quote",
    {"inAmount": "1000000", "outAmount": "950000"},
    status_code=200
)

# Groq API error with headers
api_resp = harness.mock_api_response(
    "groq",
    "/chat/completions",
    {"error": "Rate limit exceeded"},
    status_code=429,
    headers={"Retry-After": "60"}
)

# Slow API response (simulated delay)
api_resp = harness.mock_api_response(
    "coingecko",
    "/simple/price",
    {"solana": {"usd": 100.0}},
    delay_ms=2000
)
```

### Fixture Library

The `fixtures.py` module provides realistic mock data for all external services. Fixtures are organized by service and include both success and error scenarios.

#### Available Services

- **Helius RPC**: Blockchain data (balances, accounts, transactions)
- **Jupiter API**: Token swaps and quotes
- **Marinade API**: Liquid staking operations
- **Groq API**: AI chat completions
- **CoinGecko API**: Price data
- **Telegram API**: Bot messaging
- **Airdrop/Bounty**: Airdrop claims and bounties
- **Portfolio**: Portfolio analysis data
- **Error**: Common error responses

#### Using Fixtures

```python
# Get a specific fixture
balance = harness.get_fixture("helius", "get_balance_success")
quote = harness.get_fixture("jupiter", "quote_success")

# List available fixtures
all_fixtures = harness.list_fixtures()
helius_fixtures = harness.list_fixtures("helius")
```

#### Convenience Methods for Common Services

##### mock_helius_rpc()

```python
# Use fixture
response = harness.mock_helius_rpc("getBalance", "get_balance_success")

# Use custom response
response = harness.mock_helius_rpc(
    "getBalance", 
    custom_response={"value": 2000000000}
)
```

##### mock_jupiter_api()

```python
# Use fixture
response = harness.mock_jupiter_api("/quote", "quote_success")

# Use custom response
response = harness.mock_jupiter_api(
    "/quote", 
    custom_response={"outAmount": "100000"}
)
```

##### mock_groq_api()

```python
# Use fixture
response = harness.mock_groq_api("chat_completion_success")

# Use custom response
response = harness.mock_groq_api(
    custom_response={
        "choices": [{"message": {"content": "Hello!"}}]
    }
)
```

##### mock_coingecko_api()

```python
# Use fixture
response = harness.mock_coingecko_api("simple_price_success")

# Use custom response
response = harness.mock_coingecko_api(
    custom_response={"solana": {"usd": 150.0}}
)
```

### Complete Integration Test Example

Here's a complete example using fixtures for integration testing:

```python
import pytest
from tests.test_harness import TestHarness

@pytest.mark.asyncio
async def test_jupiter_swap_integration():
    """Test complete Jupiter swap flow with realistic fixtures."""
    harness = TestHarness()
    
    # Step 1: Check wallet balance
    balance_response = harness.mock_helius_rpc(
        "getBalance", 
        "get_balance_success"
    )
    balance_lamports = balance_response["result"]["value"]
    assert balance_lamports == 1000000000  # 1 SOL
    
    # Step 2: Get swap quote
    quote_response = harness.mock_jupiter_api("/quote", "quote_success")
    quote = quote_response.json()
    assert quote["inAmount"] == "1000000000"
    assert quote["outAmount"] == "100000000"
    
    # Step 3: Execute swap
    swap_response = harness.mock_jupiter_api("/swap", "swap_success")
    swap = swap_response.json()
    assert "swapTransaction" in swap
    
    # Step 4: Verify transaction
    tx_response = harness.mock_helius_rpc(
        "getTransaction",
        "get_transaction_success"
    )
    assert tx_response["result"]["meta"]["err"] is None

@pytest.mark.asyncio
async def test_error_handling_with_fixtures():
    """Test error handling using error fixtures."""
    harness = TestHarness()
    
    # Test RPC rate limit error
    rpc_error = harness.mock_helius_rpc("getBalance", "rpc_error_rate_limit")
    assert rpc_error["error"]["code"] == 429
    
    # Test API rate limit error
    api_error = harness.mock_groq_api("chat_completion_error_rate_limit")
    assert api_error.json()["error"]["type"] == "rate_limit_error"
    
    # Test network timeout
    timeout_error = harness.get_fixture("error", "network_timeout")
    assert timeout_error["code"] == "ETIMEDOUT"
```

### Available Fixtures by Service

#### Helius RPC Fixtures
- `get_balance_success` - Successful balance query (1 SOL)
- `get_balance_zero` - Zero balance
- `get_account_info_success` - Account info with data
- `get_account_info_not_found` - Account not found
- `get_token_accounts_success` - Token accounts list
- `get_recent_blockhash_success` - Recent blockhash
- `send_transaction_success` - Transaction signature
- `get_transaction_success` - Transaction details
- `rpc_error_invalid_params` - Invalid parameters error
- `rpc_error_rate_limit` - Rate limit error

#### Jupiter API Fixtures
- `quote_success` - Successful swap quote
- `quote_no_route` - No route found error
- `swap_success` - Successful swap transaction
- `swap_error_slippage` - Slippage exceeded error
- `tokens_list` - List of available tokens

#### Marinade API Fixtures
- `stake_success` - Successful stake operation
- `unstake_success` - Successful unstake operation
- `state_success` - Marinade state (APY, TVL, etc.)

#### Groq API Fixtures
- `chat_completion_success` - Successful chat completion
- `chat_completion_error_rate_limit` - Rate limit error
- `chat_completion_error_context_length` - Context length exceeded

#### CoinGecko API Fixtures
- `simple_price_success` - Single token price
- `simple_price_multiple` - Multiple token prices
- `coin_not_found` - Token not found error
- `rate_limit_error` - Rate limit error

#### Telegram API Fixtures
- `send_message_success` - Successful message send
- `send_message_error_blocked` - Bot blocked by user
- `send_message_error_chat_not_found` - Chat not found
- `get_updates_success` - Updates from Telegram
- `callback_query_success` - Callback query response

#### Airdrop Fixtures
- `available_airdrops` - List of available airdrops
- `claim_success` - Successful airdrop claim
- `claim_already_claimed` - Already claimed error

#### Portfolio Fixtures
- `portfolio_with_tokens` - Portfolio with token holdings
- `portfolio_empty` - Empty portfolio
- `portfolio_with_nfts` - Portfolio with NFTs

#### Error Fixtures
- `network_timeout` - Network timeout error
- `connection_refused` - Connection refused error
- `service_unavailable` - Service unavailable (503)
- `unauthorized` - Unauthorized (401)
- `forbidden` - Forbidden (403)
- `not_found` - Not found (404)
- `internal_server_error` - Internal server error (500)

### Best Practices for Mock Utilities

1. **Use fixtures for realistic data**: Fixtures provide realistic, well-structured data that matches actual API responses.

2. **Test both success and error paths**: Use error fixtures to test error handling logic.

3. **Combine fixtures with custom data**: Use fixtures as a base and override specific fields when needed.

4. **Use convenience methods**: The `mock_helius_rpc()`, `mock_jupiter_api()`, etc. methods simplify common mocking patterns.

5. **Verify response structure**: Always verify that your code handles the response structure correctly.

6. **Test edge cases**: Use fixtures like `get_balance_zero`, `portfolio_empty`, etc. to test edge cases.

### Testing External Service Integrations

When testing code that calls external services, use the mock utilities to simulate various scenarios:

```python
@pytest.mark.asyncio
async def test_price_service_with_fallback():
    """Test price service with primary API failure and fallback."""
    harness = TestHarness()
    
    # Primary API fails with rate limit
    primary_response = harness.mock_coingecko_api(
        "rate_limit_error",
        status_code=429
    )
    
    # Fallback API succeeds
    fallback_response = harness.mock_api_response(
        "backup_price_api",
        "/price",
        {"solana": {"usd": 127.50}},
        status_code=200
    )
    
    # Your price service should handle this gracefully
    # and fall back to the backup API
```

### See Also

- `fixtures.py` - Complete fixture library
- `test_mock_utilities.py` - Tests for mock utilities
- Design document section on "Test Data Management"
