"""
Tests for main agent initialization with multi-API scaling components.

Feature: multi-api-scaling-optimization
Task: 16. Update main agent initialization
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


@pytest.fixture
def mock_env_with_multi_api():
    """Mock environment with multi-API configuration."""
    env = {
        "GROQ_API_KEY": "test_groq_key",
        "TELEGRAM_BOT_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "SOLANA_NETWORK": "devnet",
        "HELIUS_API_KEY_1": "test_helius_key_1",
        "HELIUS_API_KEY_2": "test_helius_key_2",
        "HELIUS_API_KEY_3": "test_helius_key_3",
        "PRICE_CACHE_TTL": "60",
        "STRATEGY_CACHE_TTL": "30",
        "RPC_BATCH_SIZE": "10",
        "SCAN_STAGGER_WINDOW": "60",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_env_without_multi_api():
    """Mock environment without multi-API configuration."""
    env = {
        "GROQ_API_KEY": "test_groq_key",
        "TELEGRAM_BOT_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "SOLANA_NETWORK": "devnet",
        "HELIUS_API_KEY": "",
        "HELIUS_API_KEY_1": "",
        "HELIUS_API_KEY_2": "",
        "HELIUS_API_KEY_3": "",
    }
    with patch.dict(os.environ, env, clear=False):
        yield env


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies."""
    with patch("agent.main.WalletManager") as mock_wallet, \
         patch("agent.main.GroqProvider") as mock_groq, \
         patch("agent.main.Scanner") as mock_scanner, \
         patch("agent.main.Notifier") as mock_notifier, \
         patch("agent.main.TelegramBot") as mock_telegram, \
         patch("agent.main.UserControl") as mock_user_control, \
         patch("agent.main.RiskManager") as mock_risk, \
         patch("agent.main.PerformanceTracker") as mock_perf, \
         patch("agent.main.UserManager") as mock_user_mgr, \
         patch("agent.main.MonthlyFeeCollector") as mock_fee, \
         patch("agent.main.AgentLoop") as mock_agent_loop, \
         patch("agent.main.JupiterSwapStrategy") as mock_jupiter, \
         patch("agent.main.MarinadeStakeStrategy") as mock_marinade, \
         patch("agent.main.AirdropHunterStrategy") as mock_airdrop:
        
        # Configure wallet mock
        mock_wallet_instance = Mock()
        mock_wallet_instance.public_key = "test_public_key"
        mock_wallet.return_value = mock_wallet_instance
        
        yield {
            "wallet": mock_wallet,
            "groq": mock_groq,
            "scanner": mock_scanner,
            "notifier": mock_notifier,
            "telegram": mock_telegram,
            "user_control": mock_user_control,
            "risk": mock_risk,
            "perf": mock_perf,
            "user_mgr": mock_user_mgr,
            "fee": mock_fee,
            "agent_loop": mock_agent_loop,
        }


def test_initialization_with_multi_api_keys(mock_env_with_multi_api, mock_dependencies):
    """
    Test that HarvestAgent initializes all multi-API scaling components
    when 3 Helius API keys are configured.
    
    """
    from agent.main import HarvestAgent
    
    # Initialize agent
    agent = HarvestAgent()
    
    # Verify API Usage Monitor was created (Requirement 2.1)
    assert agent.api_usage_monitor is not None
    assert agent.api_usage_monitor.daily_limit == 3300
    
    # Verify API Key Manager was created with 3 keys (Requirement 1.1)
    assert agent.api_key_manager is not None
    assert len(agent.api_key_manager.keys) == 3
    
    # Verify Shared Price Cache was created (Requirement 4.1)
    assert agent.shared_price_cache is not None
    assert agent.shared_price_cache.ttl == 60
    
    # Verify Strategy Cache was created (Requirement 7.1)
    assert agent.strategy_cache is not None
    assert agent.strategy_cache.ttl == 30
    
    # Verify RPC Fallback Manager was created with API Key Manager
    assert agent.rpc_fallback_manager is not None
    assert agent.rpc_fallback_manager.api_key_manager is not None
    
    # Verify Optimized Scanner was created with all components
    assert agent.optimized_scanner is not None
    assert agent.optimized_scanner.api_key_manager is not None
    assert agent.optimized_scanner.shared_price_cache is not None
    assert agent.optimized_scanner.shared_strategy_cache is not None


def test_initialization_without_multi_api_keys(mock_env_without_multi_api, mock_dependencies):
    """
    Test that HarvestAgent gracefully handles missing multi-API configuration.
    
    """
    from agent.main import HarvestAgent
    
    # Initialize agent
    agent = HarvestAgent()
    
    # Verify API Usage Monitor was still created
    assert agent.api_usage_monitor is not None
    
    # Verify API Key Manager was NOT created (no keys configured)
    assert agent.api_key_manager is None
    
    # Verify caches were still created
    assert agent.shared_price_cache is not None
    assert agent.strategy_cache is not None
    
    # Verify RPC Fallback Manager was created without API Key Manager
    assert agent.rpc_fallback_manager is not None
    assert agent.rpc_fallback_manager.api_key_manager is None
    
    # Verify Optimized Scanner was created with None for api_key_manager
    assert agent.optimized_scanner is not None
    assert agent.optimized_scanner.api_key_manager is None


def test_initialization_with_custom_cache_ttls(mock_dependencies):
    """
    Test that custom cache TTL values are respected.
    
    """
    env = {
        "GROQ_API_KEY": "test_groq_key",
        "TELEGRAM_BOT_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "SOLANA_NETWORK": "devnet",
        "HELIUS_API_KEY_1": "test_helius_key_1",
        "HELIUS_API_KEY_2": "test_helius_key_2",
        "HELIUS_API_KEY_3": "test_helius_key_3",
        "PRICE_CACHE_TTL": "120",
        "STRATEGY_CACHE_TTL": "45",
    }
    
    with patch.dict(os.environ, env, clear=False):
        from agent.main import HarvestAgent
        
        # Initialize agent
        agent = HarvestAgent()
        
        # Verify custom TTL values
        assert agent.shared_price_cache.ttl == 120
        assert agent.strategy_cache.ttl == 45


def test_initialization_with_partial_api_keys(mock_dependencies):
    """
    Test that HarvestAgent handles partial API key configuration (less than 3 keys).
    
    """
    env = {
        "GROQ_API_KEY": "test_groq_key",
        "TELEGRAM_BOT_TOKEN": "test_telegram_token",
        "TELEGRAM_CHAT_ID": "123456789",
        "SOLANA_NETWORK": "devnet",
        "HELIUS_API_KEY": "",
        "HELIUS_API_KEY_1": "test_helius_key_1",
        "HELIUS_API_KEY_2": "test_helius_key_2",
        "HELIUS_API_KEY_3": "",
    }
    
    with patch.dict(os.environ, env, clear=False):
        from agent.main import HarvestAgent
        
        # Initialize agent
        agent = HarvestAgent()
        
        # Verify API Key Manager was created with 2 keys
        assert agent.api_key_manager is not None
        assert len(agent.api_key_manager.keys) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
