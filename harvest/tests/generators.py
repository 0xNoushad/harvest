"""
Test data generators using Hypothesis strategies.

This module provides strategies for generating test data for users,
wallets, trades, and other domain objects used in property-based testing.
"""

from datetime import datetime, timedelta
from typing import Optional
import string

from hypothesis import strategies as st


# ============================================================================
# Basic Strategies
# ============================================================================

# Solana addresses are base58 encoded, typically 32-44 characters
solana_address_strategy = st.text(
    alphabet=string.ascii_letters + string.digits,
    min_size=32,
    max_size=44
)

# Transaction signatures are base58 encoded, typically 88 characters
transaction_signature_strategy = st.text(
    alphabet=string.ascii_letters + string.digits,
    min_size=88,
    max_size=88
)

# Token symbols are typically 3-10 uppercase letters
token_symbol_strategy = st.text(
    alphabet=string.ascii_uppercase,
    min_size=2,
    max_size=10
)

# Telegram user IDs are positive integers
telegram_user_id_strategy = st.integers(min_value=1, max_value=999999999)

# Telegram usernames are alphanumeric with underscores, 5-32 characters
telegram_username_strategy = st.text(
    alphabet=string.ascii_lowercase + string.digits + "_",
    min_size=5,
    max_size=32
).filter(lambda x: not x.startswith("_") and not x.endswith("_"))


# ============================================================================
# Amount Strategies
# ============================================================================

# SOL amounts (in SOL, not lamports)
sol_amount_strategy = st.floats(
    min_value=0.001,
    max_value=1000.0,
    allow_nan=False,
    allow_infinity=False
)

# Small SOL amounts for fees
sol_fee_strategy = st.floats(
    min_value=0.000001,
    max_value=0.01,
    allow_nan=False,
    allow_infinity=False
)

# Profit amounts (can be negative for losses)
profit_amount_strategy = st.floats(
    min_value=-1.0,
    max_value=10.0,
    allow_nan=False,
    allow_infinity=False
)

# Percentage values (0-100)
percentage_strategy = st.floats(
    min_value=0.0,
    max_value=100.0,
    allow_nan=False,
    allow_infinity=False
)

# Price values (USD)
price_strategy = st.floats(
    min_value=0.000001,
    max_value=100000.0,
    allow_nan=False,
    allow_infinity=False
)


# ============================================================================
# Timestamp Strategies
# ============================================================================

# Recent timestamps (within last 30 days)
recent_timestamp_strategy = st.datetimes(
    min_value=datetime.now() - timedelta(days=30),
    max_value=datetime.now()
)

# Future timestamps (within next 30 days)
future_timestamp_strategy = st.datetimes(
    min_value=datetime.now(),
    max_value=datetime.now() + timedelta(days=30)
)


# ============================================================================
# User Strategies
# ============================================================================

@st.composite
def user_strategy(draw, with_balance: bool = True):
    """Generate a test user with realistic data."""
    user_id = draw(telegram_user_id_strategy)
    username = draw(telegram_username_strategy)
    wallet_address = draw(solana_address_strategy)
    balance = draw(sol_amount_strategy) if with_balance else 0.0
    
    return {
        "user_id": user_id,
        "telegram_username": username,
        "wallet_address": wallet_address,
        "wallet_balance": balance,
        "preferences": {},
        "fee_status": draw(st.sampled_from(["paid", "pending", "overdue"])),
        "created_at": draw(recent_timestamp_strategy),
        "last_active": draw(recent_timestamp_strategy)
    }


# ============================================================================
# Wallet Strategies
# ============================================================================

@st.composite
def wallet_strategy(draw, min_balance: float = 0.0):
    """Generate a test wallet with realistic data."""
    address = draw(solana_address_strategy)
    balance = draw(st.floats(
        min_value=min_balance,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False
    ))
    
    return {
        "address": address,
        "balance": balance,
        "network": draw(st.sampled_from(["devnet", "mainnet-beta"])),
        "created_at": draw(recent_timestamp_strategy)
    }


# ============================================================================
# Trade Strategies
# ============================================================================

@st.composite
def trade_strategy(draw, force_profit: Optional[bool] = None):
    """Generate a test trade with realistic data."""
    strategy_name = draw(st.sampled_from([
        "jupiter_swap",
        "marinade_stake",
        "airdrop_hunter"
    ]))
    
    expected_profit = draw(profit_amount_strategy)
    
    # If force_profit is set, ensure actual_profit matches
    if force_profit is True:
        actual_profit = draw(st.floats(min_value=0.001, max_value=10.0))
    elif force_profit is False:
        actual_profit = draw(st.floats(min_value=-1.0, max_value=-0.001))
    else:
        actual_profit = draw(profit_amount_strategy)
    
    status = draw(st.sampled_from([
        "pending",
        "executing",
        "completed",
        "failed",
        "cancelled"
    ]))
    
    return {
        "strategy": strategy_name,
        "expected_profit": expected_profit,
        "actual_profit": actual_profit,
        "status": status,
        "timestamp": draw(recent_timestamp_strategy),
        "signature": draw(transaction_signature_strategy),
        "execution_time_ms": draw(st.integers(min_value=100, max_value=5000))
    }


@st.composite
def trade_sequence_strategy(draw, min_length: int = 1, max_length: int = 10):
    """Generate a sequence of trades."""
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    return [draw(trade_strategy()) for _ in range(length)]


# ============================================================================
# Token Strategies
# ============================================================================

@st.composite
def token_holding_strategy(draw):
    """Generate a token holding with realistic data."""
    symbol = draw(token_symbol_strategy)
    amount = draw(st.floats(
        min_value=0.000001,
        max_value=1000000.0,
        allow_nan=False,
        allow_infinity=False
    ))
    price = draw(price_strategy)
    
    return {
        "symbol": symbol,
        "amount": amount,
        "price_usd": price,
        "value_usd": amount * price,
        "address": draw(solana_address_strategy)
    }


@st.composite
def portfolio_strategy(draw, min_tokens: int = 0, max_tokens: int = 20):
    """Generate a portfolio with multiple token holdings."""
    num_tokens = draw(st.integers(min_value=min_tokens, max_value=max_tokens))
    holdings = [draw(token_holding_strategy()) for _ in range(num_tokens)]
    
    total_value = sum(h["value_usd"] for h in holdings)
    
    return {
        "holdings": holdings,
        "total_value_usd": total_value,
        "token_count": num_tokens
    }


# ============================================================================
# Risk Management Strategies
# ============================================================================

risk_level_strategy = st.sampled_from(["high", "medium", "low"])

@st.composite
def risk_config_strategy(draw):
    """Generate risk management configuration."""
    return {
        "risk_level": draw(risk_level_strategy),
        "max_position_pct": draw(st.floats(min_value=1.0, max_value=50.0)),
        "daily_loss_limit_pct": draw(st.floats(min_value=5.0, max_value=50.0)),
        "min_balance_sol": draw(st.floats(min_value=0.01, max_value=1.0)),
        "consecutive_loss_threshold": draw(st.integers(min_value=2, max_value=5))
    }


# ============================================================================
# Fee Strategies
# ============================================================================

@st.composite
def fee_record_strategy(draw):
    """Generate a fee record with realistic data."""
    profit = draw(st.floats(min_value=0.01, max_value=100.0))
    fee_percentage = 0.20  # 20% platform fee
    
    return {
        "user_id": draw(telegram_user_id_strategy),
        "profit_amount": profit,
        "fee_amount": profit * fee_percentage,
        "fee_percentage": fee_percentage,
        "status": draw(st.sampled_from(["pending", "paid", "declined", "overdue"])),
        "due_date": draw(future_timestamp_strategy),
        "created_at": draw(recent_timestamp_strategy)
    }


# ============================================================================
# Command Strategies
# ============================================================================

telegram_command_strategy = st.sampled_from([
    "start",
    "help",
    "wallet",
    "withdraw",
    "stats",
    "status",
    "pause",
    "resume",
    "price",
    "portfolio",
    "fees",
    "strategies",
    "settings",
    "airdrops",
    "claims",
    "bounty",
    "newwallet",
    "exportkey"
])


@st.composite
def command_with_args_strategy(draw):
    """Generate a command with arguments."""
    command = draw(telegram_command_strategy)
    
    # Generate appropriate args based on command
    if command == "withdraw":
        args = [
            str(draw(sol_amount_strategy)),
            draw(solana_address_strategy)
        ]
    elif command == "price":
        args = [draw(token_symbol_strategy)]
    elif command == "portfolio":
        args = [draw(solana_address_strategy)]
    else:
        args = []
    
    return {
        "command": command,
        "args": args
    }


# ============================================================================
# Error Strategies
# ============================================================================

error_type_strategy = st.sampled_from([
    "ValidationError",
    "InsufficientBalanceError",
    "NetworkError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "InvalidAddressError"
])


@st.composite
def error_scenario_strategy(draw):
    """Generate an error scenario for testing error handling."""
    return {
        "error_type": draw(error_type_strategy),
        "error_message": draw(st.text(min_size=10, max_size=100)),
        "should_retry": draw(st.booleans()),
        "user_facing_message": draw(st.text(min_size=20, max_size=200))
    }


# ============================================================================
# Performance Metrics Strategies
# ============================================================================

@st.composite
def performance_metrics_strategy(draw):
    """Generate performance metrics for testing."""
    total_trades = draw(st.integers(min_value=0, max_value=1000))
    winning_trades = draw(st.integers(min_value=0, max_value=total_trades))
    
    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": total_trades - winning_trades,
        "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0.0,
        "total_profit": draw(profit_amount_strategy),
        "average_profit_per_trade": draw(profit_amount_strategy),
        "largest_win": draw(st.floats(min_value=0.0, max_value=10.0)),
        "largest_loss": draw(st.floats(min_value=-10.0, max_value=0.0))
    }


# ============================================================================
# Multi-User Scenarios
# ============================================================================

@st.composite
def multi_user_scenario_strategy(draw, min_users: int = 2, max_users: int = 10):
    """Generate a multi-user scenario for concurrent testing."""
    num_users = draw(st.integers(min_value=min_users, max_value=max_users))
    users = [draw(user_strategy()) for _ in range(num_users)]
    
    return {
        "users": users,
        "concurrent_operations": draw(st.integers(min_value=1, max_value=num_users * 3))
    }
