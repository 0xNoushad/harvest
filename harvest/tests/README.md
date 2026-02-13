# Harvest Testing Infrastructure

This directory contains the comprehensive testing infrastructure for the Harvest Telegram bot, including test harnesses, fixtures, generators, and utilities for unit, integration, property-based, and end-to-end testing.

## Overview

The testing infrastructure is designed to support:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **Property-Based Tests**: Test universal properties using Hypothesis
- **End-to-End Tests**: Test complete user workflows
- **Performance Tests**: Test scalability and response times

## Directory Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Pytest configuration and shared fixtures
├── generators.py                # Hypothesis strategies for test data generation
├── test_utils.py                # Utility functions and helpers
├── test_infrastructure.py       # Tests for the testing infrastructure itself
└── [test_*.py]                  # Feature-specific test files
```

## Key Components

### conftest.py

Central configuration file providing:

- **Pytest Configuration**: Event loop setup, environment variables
- **Mock Factories**: Reusable fixtures for creating mock objects
  - `mock_telegram_update`: Create mock Telegram Update objects
  - `mock_telegram_context`: Create mock Telegram Context objects
  - `mock_telegram_callback_query`: Create mock CallbackQuery objects
  - `mock_wallet`: Create mock WalletManager objects
  - `mock_performance_tracker`: Create mock PerformanceTracker objects
  - `mock_risk_manager`: Create mock RiskManager objects
  - `mock_user`: Create test User objects
  - `mock_price_service`: Create mock PriceService objects
  - `mock_portfolio_service`: Create mock PortfolioService objects
  - `mock_ai_chat`: Create mock AI Chat objects

- **Assertion Helpers**:
  - `assert_telegram_message_sent`: Verify Telegram messages
  - `assert_transaction_executed`: Verify blockchain transactions
  - `wait_for_async`: Wait for async conditions

### generators.py

Hypothesis strategies for generating test data:

- **Basic Strategies**:
  - `solana_address_strategy`: Generate valid Solana addresses
  - `transaction_signature_strategy`: Generate transaction signatures
  - `token_symbol_strategy`: Generate token symbols
  - `telegram_user_id_strategy`: Generate Telegram user IDs
  - `telegram_username_strategy`: Generate Telegram usernames

- **Amount Strategies**:
  - `sol_amount_strategy`: Generate SOL amounts
  - `profit_amount_strategy`: Generate profit/loss amounts
  - `price_strategy`: Generate price values

- **Composite Strategies**:
  - `user_strategy()`: Generate complete user objects
  - `wallet_strategy()`: Generate wallet objects
  - `trade_strategy()`: Generate trade objects
  - `portfolio_strategy()`: Generate portfolio objects
  - `risk_config_strategy()`: Generate risk configurations
  - `fee_record_strategy()`: Generate fee records

### test_utils.py

Utility functions for testing:

- **Async Helpers**:
  - `wait_for_condition()`: Wait for a condition to become true
  - `run_with_timeout()`: Run coroutine with timeout
  - `run_concurrent_operations()`: Run operations concurrently

- **Mock Configuration**:
  - `MockConfig`: Configure mock behavior with delays and failures
  - `build_mock_telegram_bot()`: Build configured Telegram bot mock
  - `build_mock_database()`: Build configured database mock

- **Assertion Helpers**:
  - `assert_dict_contains()`: Assert dictionary contains subset
  - `assert_called_with_partial()`: Assert mock called with kwargs
  - `assert_list_contains_item()`: Assert list contains matching item

- **Test Data Helpers**:
  - `create_test_trades()`: Create list of test trades
  - `create_test_users()`: Create list of test users

- **Performance Helpers**:
  - `PerformanceTimer`: Measure execution time
  - `measure_async_performance()`: Measure async operation performance

## Usage Examples

### Using Fixtures

```python
import pytest

@pytest.mark.asyncio
async def test_wallet_balance(mock_wallet):
    """Test wallet balance retrieval."""
    wallet = mock_wallet(balance=5.0)
    balance = await wallet.get_balance()
    assert balance == 5.0
```

### Using Generators

```python
from hypothesis import given
from tests.generators import user_strategy, sol_amount_strategy

@given(user=user_strategy(), amount=sol_amount_strategy)
def test_withdrawal(user, amount):
    """Test withdrawal for any user and amount."""
    # Test logic here
    pass
```

### Using Assertion Helpers

```python
def test_telegram_message(mock_telegram_context, assert_telegram_message_sent):
    """Test that a message was sent."""
    context = mock_telegram_context()
    
    # Send message
    await context.bot.send_message(chat_id=123, text="Hello")
    
    # Assert it was sent
    assert_telegram_message_sent(context.bot, chat_id=123, text_contains="Hello")
```

### Using Test Utilities

```python
from tests.test_utils import wait_for_condition, PerformanceTimer

async def test_async_operation():
    """Test async operation with timeout."""
    result = await wait_for_condition(
        lambda: some_condition(),
        timeout=5.0
    )
    assert result is True

def test_performance():
    """Test operation performance."""
    with PerformanceTimer("my_operation") as timer:
        # Operation to measure
        pass
    
    timer.assert_under_threshold(100)  # Must complete in <100ms
```

## Running Tests

### Run All Tests

```bash
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/ -m unit

# Integration tests only
pytest tests/ -m integration

# Property-based tests only
pytest tests/ -m property

# Slow tests excluded
pytest tests/ -m "not slow"
```

### Run with Coverage

```bash
pytest tests/ --cov=agent --cov-report=html --cov-report=term-missing
```

### Run Specific Test File

```bash
pytest tests/test_infrastructure.py -v
```

### Run with Hypothesis Profiles

```bash
# Development (20 examples, verbose)
HYPOTHESIS_PROFILE=dev pytest tests/

# CI (1000 examples)
HYPOTHESIS_PROFILE=ci pytest tests/

# Default (100 examples)
pytest tests/
```

## Test Markers

Tests can be marked with the following markers:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.property`: Property-based tests
- `@pytest.mark.asyncio`: Async tests
- `@pytest.mark.wallet`: Wallet-related tests
- `@pytest.mark.strategy`: Strategy tests
- `@pytest.mark.bot`: Telegram bot tests
- `@pytest.mark.security`: Security tests
- `@pytest.mark.command`: Command handler tests
- `@pytest.mark.risk`: Risk management tests
- `@pytest.mark.fee`: Fee collection tests
- `@pytest.mark.ai`: AI chat tests
- `@pytest.mark.price`: Price service tests
- `@pytest.mark.portfolio`: Portfolio analysis tests
- `@pytest.mark.multiuser`: Multi-user support tests
- `@pytest.mark.performance`: Performance tests

## Writing New Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
def test_my_function():
    """Test my_function with specific inputs."""
    result = my_function(input_value)
    assert result == expected_value
```

### Property-Based Test Template

```python
import pytest
from hypothesis import given
from tests.generators import user_strategy

@pytest.mark.property
@given(user=user_strategy())
def test_user_property(user):
    """
    Property: For any valid user, some property should hold.
    """
    # Test universal property
    assert some_property_holds(user)
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration(mock_wallet, mock_price_service):
    """Test integration between components."""
    wallet = mock_wallet(balance=5.0)
    price_service = mock_price_service(default_price=100.0)
    
    # Test interaction
    result = await some_operation(wallet, price_service)
    assert result is not None
```

## Best Practices

1. **Use Fixtures**: Leverage shared fixtures from conftest.py
2. **Use Generators**: Use Hypothesis strategies for property-based tests
3. **Mark Tests**: Always mark tests with appropriate markers
4. **Async Tests**: Use `@pytest.mark.asyncio` for async tests
5. **Isolation**: Ensure tests are independent and can run in any order
6. **Cleanup**: Use fixtures for setup/teardown to ensure cleanup
7. **Assertions**: Use descriptive assertion messages
8. **Performance**: Mark slow tests with `@pytest.mark.slow`
9. **Documentation**: Document test purpose and expected behavior
10. **Coverage**: Aim for >85% code coverage

## Hypothesis Configuration

Three profiles are available:

- **default**: 100 examples, no deadline (standard testing)
- **ci**: 1000 examples, no deadline (CI/CD pipelines)
- **dev**: 20 examples, verbose output (development)

Set profile with environment variable:
```bash
export HYPOTHESIS_PROFILE=dev
```

## Troubleshooting

### Tests Fail with "No event loop"

Ensure async tests are marked with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_async_function():
    pass
```

### Hypothesis Health Check Failures

If using fixtures with `@given`, suppress the health check:
```python
from hypothesis import given, settings, HealthCheck

@given(data=some_strategy)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_with_fixture(fixture_name, data):
    pass
```

### Import Errors

Ensure the parent directory is in the path (conftest.py handles this):
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

## Contributing

When adding new tests:

1. Follow the existing structure and naming conventions
2. Add appropriate markers
3. Document test purpose and expected behavior
4. Update this README if adding new utilities or patterns
5. Ensure tests pass locally before committing
6. Maintain test coverage above 85%

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Design Document](.kiro/specs/telegram-bot-testing-improvements/design.md)
- [Requirements Document](.kiro/specs/telegram-bot-testing-improvements/requirements.md)
