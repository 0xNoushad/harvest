# Assertion Helpers Guide

This guide explains how to use the assertion helper methods provided by the TestHarness class for testing the Harvest Telegram bot.

## Overview

The TestHarness provides three main assertion helpers:

1. **assert_telegram_message_sent()** - Verify Telegram messages were sent correctly
2. **assert_transaction_executed()** - Verify blockchain transactions were executed
3. **wait_for_async_operation()** - Wait for async operations to complete

These helpers simplify test assertions and make tests more readable and maintainable.

## assert_telegram_message_sent()

Verifies that a Telegram message was sent with expected content.

### Signature

```python
def assert_telegram_message_sent(
    self,
    mock_bot,
    chat_id: int,
    text_contains: Optional[str] = None,
    call_count: Optional[int] = None
)
```

### Parameters

- **mock_bot**: Mock bot object with `send_message` method
- **chat_id**: Expected chat ID where message should be sent
- **text_contains**: Optional text that should appear in the message
- **call_count**: Optional expected number of times message was sent

### Examples

#### Basic usage - verify message was sent

```python
def test_start_command(test_harness):
    # Setup
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    # Execute
    await mock_bot.send_message(12345, "Welcome to Harvest Bot!")
    
    # Assert
    test_harness.assert_telegram_message_sent(
        mock_bot, 12345, text_contains="Welcome"
    )
```

#### Verify specific call count

```python
def test_multiple_messages(test_harness):
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    # Send 3 messages
    await mock_bot.send_message(12345, "Message 1")
    await mock_bot.send_message(12345, "Message 2")
    await mock_bot.send_message(12345, "Message 3")
    
    # Assert exactly 3 messages sent
    test_harness.assert_telegram_message_sent(
        mock_bot, 12345, call_count=3
    )
```

#### Verify message to specific chat among multiple

```python
def test_multi_user_messages(test_harness):
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    
    # Send to different users
    await mock_bot.send_message(12345, "Hello User 1")
    await mock_bot.send_message(67890, "Hello User 2")
    
    # Assert message to specific user
    test_harness.assert_telegram_message_sent(
        mock_bot, 12345, text_contains="User 1"
    )
```

### Common Patterns

**Error messages:**
```python
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="❌"
)
```

**Success confirmations:**
```python
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="✅ Success"
)
```

**Balance displays:**
```python
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="Balance: 1.5 SOL"
)
```

## assert_transaction_executed()

Verifies that a blockchain transaction was executed.

### Signature

```python
def assert_transaction_executed(
    self,
    mock_wallet,
    signature: Optional[str] = None,
    method_name: str = "withdraw"
)
```

### Parameters

- **mock_wallet**: Mock wallet object
- **signature**: Optional expected transaction signature
- **method_name**: Method name to check (default: "withdraw")

### Examples

#### Basic usage - verify transaction was executed

```python
def test_withdrawal(test_harness):
    # Setup
    mock_wallet = MagicMock()
    mock_wallet.withdraw = AsyncMock(return_value="tx_sig_123")
    
    # Execute
    await mock_wallet.withdraw(1.0, "TestAddress")
    
    # Assert
    test_harness.assert_transaction_executed(mock_wallet)
```

#### Verify specific transaction signature

```python
def test_withdrawal_signature(test_harness):
    mock_wallet = MagicMock()
    mock_wallet.withdraw = AsyncMock(return_value="abc123xyz")
    
    result = await mock_wallet.withdraw(1.0, "TestAddress")
    
    # Assert specific signature
    test_harness.assert_transaction_executed(
        mock_wallet, signature="abc123xyz"
    )
```

#### Verify custom transaction method

```python
def test_custom_transaction(test_harness):
    mock_wallet = MagicMock()
    mock_wallet.send_transaction = AsyncMock(return_value="tx_sig")
    
    await mock_wallet.send_transaction("transaction_data")
    
    # Assert custom method
    test_harness.assert_transaction_executed(
        mock_wallet, method_name="send_transaction"
    )
```

### Common Patterns

**Withdrawal transactions:**
```python
test_harness.assert_transaction_executed(
    mock_wallet, method_name="withdraw"
)
```

**Swap transactions:**
```python
test_harness.assert_transaction_executed(
    mock_wallet, method_name="execute_swap"
)
```

**Stake transactions:**
```python
test_harness.assert_transaction_executed(
    mock_wallet, method_name="stake_sol"
)
```

## wait_for_async_operation()

Waits for an async condition to become true with timeout.

### Signature

```python
async def wait_for_async_operation(
    self,
    condition_func,
    timeout: float = 5.0,
    interval: float = 0.1
) -> bool
```

### Parameters

- **condition_func**: Function that returns True when condition is met
- **timeout**: Maximum time to wait in seconds (default: 5.0)
- **interval**: Time between checks in seconds (default: 0.1)

### Returns

- **bool**: True if condition was met

### Raises

- **TimeoutError**: If timeout is reached before condition is met

### Examples

#### Wait for mock method to be called

```python
@pytest.mark.asyncio
async def test_async_operation(test_harness):
    mock_obj = MagicMock()
    mock_obj.process = AsyncMock()
    
    # Start async task
    async def process_later():
        await asyncio.sleep(0.1)
        await mock_obj.process()
    
    asyncio.create_task(process_later())
    
    # Wait for method to be called
    await test_harness.wait_for_async_operation(
        lambda: mock_obj.process.called,
        timeout=1.0
    )
    
    assert mock_obj.process.called
```

#### Wait for value to change

```python
@pytest.mark.asyncio
async def test_value_change(test_harness):
    state = {"status": "pending"}
    
    # Start async task that changes state
    async def update_state():
        await asyncio.sleep(0.1)
        state["status"] = "completed"
    
    asyncio.create_task(update_state())
    
    # Wait for state change
    await test_harness.wait_for_async_operation(
        lambda: state["status"] == "completed",
        timeout=1.0
    )
    
    assert state["status"] == "completed"
```

#### Wait with custom interval

```python
@pytest.mark.asyncio
async def test_custom_interval(test_harness):
    counter = {"value": 0}
    
    async def increment():
        for i in range(5):
            await asyncio.sleep(0.05)
            counter["value"] += 1
    
    asyncio.create_task(increment())
    
    # Check every 20ms instead of default 100ms
    await test_harness.wait_for_async_operation(
        lambda: counter["value"] >= 3,
        timeout=1.0,
        interval=0.02
    )
```

### Common Patterns

**Wait for message to be sent:**
```python
await test_harness.wait_for_async_operation(
    lambda: mock_bot.send_message.called,
    timeout=2.0
)
```

**Wait for transaction to complete:**
```python
await test_harness.wait_for_async_operation(
    lambda: mock_wallet.withdraw.called,
    timeout=5.0
)
```

**Wait for state change:**
```python
await test_harness.wait_for_async_operation(
    lambda: bot.state == "active",
    timeout=3.0
)
```

## Integration Examples

### Complete command test with all helpers

```python
@pytest.mark.asyncio
async def test_withdraw_command_complete(test_harness):
    # Setup
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    mock_wallet = MagicMock()
    mock_wallet.withdraw = AsyncMock(return_value="tx_sig_123")
    
    # Simulate async withdrawal
    async def execute_withdrawal():
        await asyncio.sleep(0.1)
        result = await mock_wallet.withdraw(1.0, "TestAddress")
        await mock_bot.send_message(
            12345, 
            f"✅ Withdrawal successful: {result}"
        )
    
    # Execute
    task = asyncio.create_task(execute_withdrawal())
    
    # Wait for transaction
    await test_harness.wait_for_async_operation(
        lambda: mock_wallet.withdraw.called,
        timeout=1.0
    )
    
    # Wait for message
    await test_harness.wait_for_async_operation(
        lambda: mock_bot.send_message.called,
        timeout=1.0
    )
    
    await task
    
    # Assert transaction
    test_harness.assert_transaction_executed(
        mock_wallet, signature="tx_sig_123"
    )
    
    # Assert message
    test_harness.assert_telegram_message_sent(
        mock_bot, 12345, text_contains="✅ Withdrawal successful"
    )
```

### Error handling test

```python
@pytest.mark.asyncio
async def test_withdrawal_error_handling(test_harness):
    # Setup
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    mock_wallet = MagicMock()
    mock_wallet.withdraw = AsyncMock(side_effect=Exception("Insufficient balance"))
    
    # Execute with error
    try:
        await mock_wallet.withdraw(100.0, "TestAddress")
    except Exception:
        await mock_bot.send_message(12345, "❌ Withdrawal failed: Insufficient balance")
    
    # Assert error message sent
    test_harness.assert_telegram_message_sent(
        mock_bot, 12345, text_contains="❌ Withdrawal failed"
    )
    
    # Transaction should have been attempted
    test_harness.assert_transaction_executed(mock_wallet)
```

## Best Practices

### 1. Use descriptive text_contains values

**Good:**
```python
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="Balance: 1.5 SOL"
)
```

**Bad:**
```python
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="1.5"
)
```

### 2. Set appropriate timeouts

For fast operations:
```python
await test_harness.wait_for_async_operation(
    condition, timeout=1.0
)
```

For slow operations (blockchain):
```python
await test_harness.wait_for_async_operation(
    condition, timeout=10.0
)
```

### 3. Combine assertions for complete verification

```python
# Verify both transaction and notification
test_harness.assert_transaction_executed(mock_wallet)
test_harness.assert_telegram_message_sent(
    mock_bot, chat_id, text_contains="Success"
)
```

### 4. Use specific signatures when testing critical operations

```python
# For withdrawals, verify exact signature
test_harness.assert_transaction_executed(
    mock_wallet, signature=expected_signature
)
```

### 5. Handle timeouts gracefully

```python
try:
    await test_harness.wait_for_async_operation(
        condition, timeout=2.0
    )
except TimeoutError:
    pytest.fail("Operation did not complete in time")
```

## Troubleshooting

### AssertionError: Expected message containing 'X' not found

**Cause:** The message was sent but doesn't contain the expected text.

**Solution:** Check the actual message content or use a more general text_contains value.

### AssertionError: Expected N calls, got M

**Cause:** The method was called a different number of times than expected.

**Solution:** Verify your test logic or adjust the expected call_count.

### TimeoutError: Condition not met within X seconds

**Cause:** The async operation didn't complete within the timeout.

**Solution:** 
- Increase the timeout value
- Check if the operation is actually being executed
- Verify the condition function is correct

### AssertionError: Method X not found on wallet

**Cause:** The mock wallet doesn't have the specified method.

**Solution:** Ensure the mock wallet has the method or use the correct method_name.

## See Also

- [Test Harness Guide](TEST_HARNESS_GUIDE.md) - Complete TestHarness documentation
- [Fixtures Guide](fixtures.py) - Pre-defined mock data
- [Testing Infrastructure](INFRASTRUCTURE_SUMMARY.md) - Overall testing strategy
