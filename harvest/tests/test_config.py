"""
Tests for configuration management.
"""

import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch
from hypothesis import given, strategies as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from the module file to avoid dependency issues
import importlib.util
spec = importlib.util.spec_from_file_location(
    "config",
    Path(__file__).parent.parent / "agent" / "core" / "config.py"
)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
EnvironmentConfig = config_module.EnvironmentConfig


class TestConfigurationLoading:
    """Test configuration loading with environment variables."""
    
    def test_helius_api_keys_from_env(self):
        """Test loading multiple Helius API keys from environment."""
        with patch.dict(os.environ, {
            'HELIUS_API_KEY_1': 'key1',
            'HELIUS_API_KEY_2': 'key2',
            'HELIUS_API_KEY_3': 'key3'
        }):
            config = EnvironmentConfig()
            keys = config.get_helius_api_keys()
            
            assert len(keys) == 3
            assert keys[0] == 'key1'
            assert keys[1] == 'key2'
            assert keys[2] == 'key3'
    
    def test_helius_api_keys_partial(self):
        """Test loading partial set of API keys."""
        with patch.dict(os.environ, {
            'HELIUS_API_KEY_1': 'key1',
            'HELIUS_API_KEY_2': 'key2',
            'HELIUS_API_KEY_3': '',
            'HELIUS_API_KEY': ''
        }, clear=False):
            config = EnvironmentConfig()
            keys = config.get_helius_api_keys()
            
            assert len(keys) == 2
            assert keys[0] == 'key1'
            assert keys[1] == 'key2'
    
    def test_helius_api_keys_fallback_to_single(self):
        """Test fallback to single HELIUS_API_KEY if multi-key not configured."""
        with patch.dict(os.environ, {
            'HELIUS_API_KEY': 'single_key',
            'HELIUS_API_KEY_1': '',
            'HELIUS_API_KEY_2': '',
            'HELIUS_API_KEY_3': ''
        }, clear=False):
            config = EnvironmentConfig()
            keys = config.get_helius_api_keys()
            
            assert len(keys) == 1
            assert keys[0] == 'single_key'
    
    def test_price_cache_ttl_default(self):
        """Test PRICE_CACHE_TTL uses default of 60 seconds."""
        # Prevent .env file loading by mocking Path.exists
        with patch('pathlib.Path.exists', return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                config = EnvironmentConfig()
                ttl = config.get_price_cache_ttl()
                
                assert ttl == 60
    
    def test_price_cache_ttl_from_env(self):
        """Test PRICE_CACHE_TTL loads from environment."""
        with patch.dict(os.environ, {'PRICE_CACHE_TTL': '120'}):
            config = EnvironmentConfig()
            ttl = config.get_price_cache_ttl()
            
            assert ttl == 120
    
    def test_price_cache_ttl_bounds(self):
        """Test PRICE_CACHE_TTL enforces bounds."""
        # Too low
        with patch.dict(os.environ, {'PRICE_CACHE_TTL': '0'}):
            config = EnvironmentConfig()
            assert config.get_price_cache_ttl() == 1
        
        # Too high
        with patch.dict(os.environ, {'PRICE_CACHE_TTL': '5000'}):
            config = EnvironmentConfig()
            assert config.get_price_cache_ttl() == 3600
    
    def test_strategy_cache_ttl_default(self):
        """Test STRATEGY_CACHE_TTL uses default of 30 seconds."""
        with patch.dict(os.environ, {}, clear=True):
            config = EnvironmentConfig()
            ttl = config.get_strategy_cache_ttl()
            
            assert ttl == 30
    
    def test_strategy_cache_ttl_from_env(self):
        """Test STRATEGY_CACHE_TTL loads from environment."""
        with patch.dict(os.environ, {'STRATEGY_CACHE_TTL': '45'}):
            config = EnvironmentConfig()
            ttl = config.get_strategy_cache_ttl()
            
            assert ttl == 45
    
    def test_rpc_batch_size_default(self):
        """Test RPC_BATCH_SIZE uses default of 10."""
        with patch.dict(os.environ, {}, clear=True):
            config = EnvironmentConfig()
            batch_size = config.get_rpc_batch_size()
            
            assert batch_size == 10
    
    def test_rpc_batch_size_from_env(self):
        """Test RPC_BATCH_SIZE loads from environment."""
        with patch.dict(os.environ, {'RPC_BATCH_SIZE': '20'}):
            config = EnvironmentConfig()
            batch_size = config.get_rpc_batch_size()
            
            assert batch_size == 20
    
    def test_rpc_batch_size_bounds(self):
        """Test RPC_BATCH_SIZE enforces bounds."""
        # Too low
        with patch.dict(os.environ, {'RPC_BATCH_SIZE': '0'}):
            config = EnvironmentConfig()
            assert config.get_rpc_batch_size() == 1
        
        # Too high
        with patch.dict(os.environ, {'RPC_BATCH_SIZE': '200'}):
            config = EnvironmentConfig()
            assert config.get_rpc_batch_size() == 100
    
    def test_scan_stagger_window_default(self):
        """Test SCAN_STAGGER_WINDOW uses default of 60 seconds."""
        with patch.dict(os.environ, {}, clear=True):
            config = EnvironmentConfig()
            window = config.get_scan_stagger_window()
            
            assert window == 60
    
    def test_scan_stagger_window_from_env(self):
        """Test SCAN_STAGGER_WINDOW loads from environment."""
        with patch.dict(os.environ, {'SCAN_STAGGER_WINDOW': '90'}):
            config = EnvironmentConfig()
            window = config.get_scan_stagger_window()
            
            assert window == 90
    
    def test_scan_stagger_window_bounds(self):
        """Test SCAN_STAGGER_WINDOW enforces bounds."""
        # Too low
        with patch.dict(os.environ, {'SCAN_STAGGER_WINDOW': '5'}):
            config = EnvironmentConfig()
            assert config.get_scan_stagger_window() == 10
        
        # Too high
        with patch.dict(os.environ, {'SCAN_STAGGER_WINDOW': '500'}):
            config = EnvironmentConfig()
            assert config.get_scan_stagger_window() == 300


class TestConfigurationPropertyTests:
    """Property-based tests for configuration loading."""
    
    @given(
        price_ttl=st.one_of(st.none(), st.integers(min_value=1, max_value=3600)),
        strategy_ttl=st.one_of(st.none(), st.integers(min_value=1, max_value=3600)),
        batch_size=st.one_of(st.none(), st.integers(min_value=1, max_value=100)),
        stagger_window=st.one_of(st.none(), st.integers(min_value=10, max_value=300))
    )
    def test_configuration_loading_with_defaults(
        self,
        price_ttl,
        strategy_ttl,
        batch_size,
        stagger_window
    ):
        """
        Test configuration loading with defaults.
        
        For any configuration parameter, if the environment variable is set,
        the system should use that value; otherwise, it should use the
        documented default value.
        """
        env_vars = {}
        
        if price_ttl is not None:
            env_vars['PRICE_CACHE_TTL'] = str(price_ttl)
        if strategy_ttl is not None:
            env_vars['STRATEGY_CACHE_TTL'] = str(strategy_ttl)
        if batch_size is not None:
            env_vars['RPC_BATCH_SIZE'] = str(batch_size)
        if stagger_window is not None:
            env_vars['SCAN_STAGGER_WINDOW'] = str(stagger_window)
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = EnvironmentConfig()
            
            # Check PRICE_CACHE_TTL
            actual_price_ttl = config.get_price_cache_ttl()
            if price_ttl is not None:
                assert actual_price_ttl == price_ttl
            else:
                assert actual_price_ttl == 60  # Default
            
            # Check STRATEGY_CACHE_TTL
            actual_strategy_ttl = config.get_strategy_cache_ttl()
            if strategy_ttl is not None:
                assert actual_strategy_ttl == strategy_ttl
            else:
                assert actual_strategy_ttl == 30  # Default
            
            # Check RPC_BATCH_SIZE
            actual_batch_size = config.get_rpc_batch_size()
            if batch_size is not None:
                assert actual_batch_size == batch_size
            else:
                assert actual_batch_size == 10  # Default
            
            # Check SCAN_STAGGER_WINDOW
            actual_stagger_window = config.get_scan_stagger_window()
            if stagger_window is not None:
                assert actual_stagger_window == stagger_window
            else:
                assert actual_stagger_window == 60  # Default
    
    @given(
        num_keys=st.integers(min_value=1, max_value=3)
    )
    def test_helius_api_keys_loading(self, num_keys):
        """
        Test Helius API keys loading.
        
        For any number of configured API keys (1-3), the system should
        load exactly that many keys from environment variables.
        """
        env_vars = {
            'HELIUS_API_KEY': '',
            'HELIUS_API_KEY_1': '',
            'HELIUS_API_KEY_2': '',
            'HELIUS_API_KEY_3': ''
        }
        for i in range(1, num_keys + 1):
            env_vars[f'HELIUS_API_KEY_{i}'] = f'test_key_{i}'
        
        with patch.dict(os.environ, env_vars, clear=False):
            config = EnvironmentConfig()
            keys = config.get_helius_api_keys()
            
            assert len(keys) == num_keys
            for i in range(num_keys):
                assert keys[i] == f'test_key_{i + 1}'
