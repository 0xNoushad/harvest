"""
Configuration management and environment validation for Harvest agent.

This module handles:
- Environment variable validation
- Configuration loading
- Startup error handling
"""

import os
import sys
import logging
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Set up a basic logger for startup messages (before full logging is configured)
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class EnvironmentConfig:
    """Environment configuration with validation."""
    
    # Required variables for production
    REQUIRED_PRODUCTION = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "GROQ_API_KEY",
        "SOLANA_NETWORK",
    ]
    
    # Optional variables with defaults
    OPTIONAL_WITH_DEFAULTS = {
        "LOG_LEVEL": "INFO",
        "CONSOLE_LOG_LEVEL": "INFO",
        "SCAN_INTERVAL": "300",
        "PERFORMANCE_FEE": "0.02",
        "MAX_LOSS_PER_TRADE": "0.10",
        # Risk management parameters (Requirement 4.1-4.7)
        "MAX_POSITION_PCT": "0.10",  # 10% max per trade
        "MAX_DAILY_LOSS_PCT": "0.20",  # 20% daily loss limit
        "MIN_BALANCE_SOL": "0.1",  # Minimum balance to maintain
        "HIGH_RISK_POSITION_PCT": "0.05",  # 5% for high risk
        "MEDIUM_RISK_POSITION_PCT": "0.10",  # 10% for medium risk
        "LOW_RISK_POSITION_PCT": "0.20",  # 20% for low risk
        "CONSECUTIVE_LOSS_THRESHOLD": "3",  # Losses before reduction
        "CONSECUTIVE_LOSS_REDUCTION": "0.50",  # 50% reduction
        # Fee and slippage parameters (Requirement 6.1-6.6, 7.1-7.5)
        "PRIORITY_FEE_THRESHOLD": "0.001",  # SOL threshold for congestion
        "PRIORITY_FEE_INCREASE": "0.50",  # 50% increase on retry
        "MAX_FEE_PCT_OF_PROFIT": "0.05",  # 5% max fee vs profit
        "SLIPPAGE_BPS": "100",  # 1% slippage tolerance
        "HIGH_VOLATILITY_SLIPPAGE_BPS": "200",  # 2% during volatility
        "MAX_PRICE_IMPACT_PCT": "0.02",  # 2% max price impact
        # Scan interval parameters (Requirement 9.4-9.6)
        "MIN_SCAN_INTERVAL": "5",  # 5 seconds minimum
        "RATE_LIMIT_INTERVAL_INCREASE": "0.50",  # 50% increase
        "EMPTY_SCAN_THRESHOLD": "10",  # Empty scans before slowdown
        "EMPTY_SCAN_INTERVAL": "30",  # 30 seconds after empty scans
        # Strategy enable/disable flags
        "ENABLE_JUPITER_SWAP": "true",
        "ENABLE_MARINADE_STAKE": "true",
        "ENABLE_AIRDROP_HUNTER": "true",
        # Transaction execution parameters (Requirement 1.3-1.6)
        "CONFIRMATION_TIMEOUT": "60",  # 60 seconds
        "MAX_RETRIES": "3",  # 3 retry attempts
    }
    
    # Multi-API scaling optimization variables (Requirement 9.1-9.5)
    MULTI_API_VARIABLES = [
        "HELIUS_API_KEY_1",
        "HELIUS_API_KEY_2",
        "HELIUS_API_KEY_3",
    ]
    
    # Optimization configuration with defaults (Requirement 9.2-9.5)
    OPTIMIZATION_DEFAULTS = {
        "PRICE_CACHE_TTL": "60",
        "STRATEGY_CACHE_TTL": "30",
        "RPC_BATCH_SIZE": "10",
        "SCAN_STAGGER_WINDOW": "60",
    }
    
    # All known variables
    ALL_VARIABLES = (
        REQUIRED_PRODUCTION + 
        list(OPTIONAL_WITH_DEFAULTS.keys()) + 
        MULTI_API_VARIABLES +
        list(OPTIMIZATION_DEFAULTS.keys()) +
        [
            "HELIUS_API_KEY",
            "WALLET_ADDRESS",
            "WALLET_PRIVATE_KEY",
            "DISCORD_WEBHOOK_URL",
            "COLOSSEUM_API_KEY",
            "AGENT_ID",
        ]
    )
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to find .env in current directory or parent directories
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                env_path = parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path)
                    break
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable with optional default."""
        value = os.getenv(key)
        if value is None:
            if key in self.OPTIONAL_WITH_DEFAULTS:
                return self.OPTIONAL_WITH_DEFAULTS[key]
            if key in self.OPTIMIZATION_DEFAULTS:
                return self.OPTIMIZATION_DEFAULTS[key]
        return value or default
    
    def get_required(self, key: str) -> str:
        """
        Get required environment variable.
        
        Raises:
            ConfigurationError: If variable is not set
        """
        value = self.get(key)
        if not value:
            raise ConfigurationError(
                f"Required environment variable '{key}' is not set. "
                f"Please add it to your .env file."
            )
        return value
    
    def validate(self, require_all: bool = False) -> Dict[str, str]:
        """
        Validate environment configuration.
        
        Args:
            require_all: If True, require all production variables
        
        Returns:
            Dictionary of validated configuration
            
        Raises:
            ConfigurationError: If required variables are missing
        """
        config = {}
        missing = []
        warnings = []
        
        # Check required variables
        if require_all:
            for var in self.REQUIRED_PRODUCTION:
                value = self.get(var)
                if not value:
                    missing.append(var)
                else:
                    config[var] = value
        else:
            # Development mode - only warn about missing variables
            for var in self.REQUIRED_PRODUCTION:
                value = self.get(var)
                if not value:
                    warnings.append(var)
                else:
                    config[var] = value
        
        # Add optional variables with defaults
        for var, default in self.OPTIONAL_WITH_DEFAULTS.items():
            config[var] = self.get(var, default)
        
        # Add other optional variables if present
        for var in self.ALL_VARIABLES:
            if var not in config:
                value = self.get(var)
                if value:
                    config[var] = value
        
        # Report errors
        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Please add them to your .env file.\n"
                f"See .env.production.template for details."
            )
        
        # Report warnings
        if warnings:
            logger.warning(f"⚠️  Warning: Missing optional variables: {', '.join(warnings)}")
            logger.warning("   Some features may not work without these variables")
        
        return config
    
    def get_network(self) -> str:
        """Get Solana network (devnet or mainnet)."""
        return self.get("SOLANA_NETWORK", "devnet")
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.get_network() == "mainnet"
    
    def get_scan_interval(self) -> int:
        """Get scan interval in seconds."""
        try:
            interval = int(self.get("SCAN_INTERVAL", "300"))
            if interval < 60:
                logger.warning(f"Scan interval {interval}s is too low, using minimum 60s")
                return 60
            if interval > 86400:  # 24 hours
                logger.warning(f"Scan interval {interval}s is too high, using maximum 86400s")
                return 86400
            return interval
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid SCAN_INTERVAL value: {e}, using default 300s")
            return 300
    
    def get_performance_fee(self) -> float:
        """Get performance fee as decimal (e.g., 0.02 for 2%)."""
        try:
            fee = float(self.get("PERFORMANCE_FEE", "0.02"))
            if fee < 0 or fee > 1.0:
                logger.warning(f"Performance fee {fee} out of range [0, 1.0], using default 0.02")
                return 0.02
            return fee
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid PERFORMANCE_FEE value: {e}, using default 0.02")
            return 0.02
    
    def get_max_loss_per_trade(self) -> float:
        """Get maximum loss per trade as decimal (e.g., 0.10 for 10%)."""
        try:
            max_loss = float(self.get("MAX_LOSS_PER_TRADE", "0.10"))
            if max_loss < 0 or max_loss > 1.0:
                logger.warning(f"Max loss {max_loss} out of range [0, 1.0], using default 0.10")
                return 0.10
            return max_loss
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_LOSS_PER_TRADE value: {e}, using default 0.10")
            return 0.10
    
    def get_helius_api_keys(self) -> list[str]:
        """
        Get list of Helius API keys for multi-API scaling.        
        Returns:
            List of valid API keys (may be empty if none configured)
        """
        keys = []
        for i in range(1, 4):
            key = self.get(f"HELIUS_API_KEY_{i}")
            if key:
                keys.append(key)
        
        # Fallback to single HELIUS_API_KEY if multi-key not configured
        if not keys:
            single_key = self.get("HELIUS_API_KEY")
            if single_key:
                keys.append(single_key)
        
        return keys
    
    def get_price_cache_ttl(self) -> int:
        """
        Get price cache TTL in seconds.        
        Returns:
            Cache TTL in seconds (default 60)
        """
        try:
            ttl = int(self.get("PRICE_CACHE_TTL", "60"))
            if ttl < 1:
                logger.warning(f"Price cache TTL {ttl}s is too low, using minimum 1s")
                return 1
            if ttl > 3600:  # 1 hour max
                logger.warning(f"Price cache TTL {ttl}s is too high, using maximum 3600s")
                return 3600
            return ttl
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid PRICE_CACHE_TTL value: {e}, using default 60s")
            return 60
    
    def get_strategy_cache_ttl(self) -> int:
        """
        Get strategy cache TTL in seconds.        
        Returns:
            Cache TTL in seconds (default 30)
        """
        try:
            ttl = int(self.get("STRATEGY_CACHE_TTL", "30"))
            if ttl < 1:
                logger.warning(f"Strategy cache TTL {ttl}s is too low, using minimum 1s")
                return 1
            if ttl > 3600:  # 1 hour max
                logger.warning(f"Strategy cache TTL {ttl}s is too high, using maximum 3600s")
                return 3600
            return ttl
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid STRATEGY_CACHE_TTL value: {e}, using default 30s")
            return 30
    
    def get_rpc_batch_size(self) -> int:
        """
        Get RPC batch size (max users per batch).        
        Returns:
            Batch size (default 10)
        """
        try:
            batch_size = int(self.get("RPC_BATCH_SIZE", "10"))
            if batch_size < 1:
                logger.warning(f"RPC batch size {batch_size} is too low, using minimum 1")
                return 1
            if batch_size > 100:  # Solana RPC limits
                logger.warning(f"RPC batch size {batch_size} is too high, using maximum 100")
                return 100
            return batch_size
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid RPC_BATCH_SIZE value: {e}, using default 10")
            return 10
    
    def get_scan_stagger_window(self) -> int:
        """
        Get scan stagger window in seconds.        
        Returns:
            Stagger window in seconds (default 60)
        """
        try:
            window = int(self.get("SCAN_STAGGER_WINDOW", "60"))
            if window < 10:
                logger.warning(f"Scan stagger window {window}s is too low, using minimum 10s")
                return 10
            if window > 300:  # 5 minutes max
                logger.warning(f"Scan stagger window {window}s is too high, using maximum 300s")
                return 300
            return window
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid SCAN_STAGGER_WINDOW value: {e}, using default 60s")
            return 60
    
    # Risk Management Configuration (Requirement 4.1-4.7)
    
    def get_max_position_pct(self) -> float:
        """Get maximum position size as percentage of balance (default 0.10 = 10%)."""
        try:
            pct = float(self.get("MAX_POSITION_PCT", "0.10"))
            if pct < 0 or pct > 1.0:
                logger.warning(f"Max position {pct} out of range [0, 1.0], using default 0.10")
                return 0.10
            return pct
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_POSITION_PCT value: {e}, using default 0.10")
            return 0.10
    
    def get_max_daily_loss_pct(self) -> float:
        """Get maximum daily loss percentage (default 0.20 = 20%)."""
        try:
            pct = float(self.get("MAX_DAILY_LOSS_PCT", "0.20"))
            if pct < 0 or pct > 1.0:
                logger.warning(f"Max daily loss {pct} out of range [0, 1.0], using default 0.20")
                return 0.20
            return pct
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_DAILY_LOSS_PCT value: {e}, using default 0.20")
            return 0.20
    
    def get_min_balance_sol(self) -> float:
        """Get minimum SOL balance to maintain (default 0.1)."""
        try:
            balance = float(self.get("MIN_BALANCE_SOL", "0.1"))
            if balance < 0:
                logger.warning(f"Min balance {balance} is negative, using default 0.1")
                return 0.1
            return balance
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MIN_BALANCE_SOL value: {e}, using default 0.1")
            return 0.1
    
    def get_risk_position_pct(self, risk_level: str) -> float:
        """
        Get position size percentage for given risk level.
        
        Args:
            risk_level: "high", "medium", or "low"
            
        Returns:
            Position size as percentage (0.05 for high, 0.10 for medium, 0.20 for low)
        """
        risk_level = risk_level.lower()
        if risk_level == "high":
            key = "HIGH_RISK_POSITION_PCT"
            default = "0.05"
        elif risk_level == "medium":
            key = "MEDIUM_RISK_POSITION_PCT"
            default = "0.10"
        elif risk_level == "low":
            key = "LOW_RISK_POSITION_PCT"
            default = "0.20"
        else:
            logger.warning(f"Unknown risk level '{risk_level}', using medium")
            key = "MEDIUM_RISK_POSITION_PCT"
            default = "0.10"
        
        try:
            pct = float(self.get(key, default))
            if pct < 0 or pct > 1.0:
                logger.warning(f"{key} {pct} out of range [0, 1.0], using default {default}")
                return float(default)
            return pct
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid {key} value: {e}, using default {default}")
            return float(default)
    
    def get_consecutive_loss_threshold(self) -> int:
        """Get number of consecutive losses before position reduction (default 3)."""
        try:
            threshold = int(self.get("CONSECUTIVE_LOSS_THRESHOLD", "3"))
            if threshold < 1:
                logger.warning(f"Consecutive loss threshold {threshold} too low, using minimum 1")
                return 1
            return threshold
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid CONSECUTIVE_LOSS_THRESHOLD value: {e}, using default 3")
            return 3
    
    def get_consecutive_loss_reduction(self) -> float:
        """Get position reduction factor after consecutive losses (default 0.50 = 50%)."""
        try:
            reduction = float(self.get("CONSECUTIVE_LOSS_REDUCTION", "0.50"))
            if reduction < 0 or reduction > 1.0:
                logger.warning(f"Loss reduction {reduction} out of range [0, 1.0], using default 0.50")
                return 0.50
            return reduction
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid CONSECUTIVE_LOSS_REDUCTION value: {e}, using default 0.50")
            return 0.50
    
    # Fee and Slippage Configuration (Requirement 6.1-6.6, 7.1-7.5)
    
    def get_priority_fee_threshold(self) -> float:
        """Get priority fee threshold for congestion detection (default 0.001 SOL)."""
        try:
            threshold = float(self.get("PRIORITY_FEE_THRESHOLD", "0.001"))
            if threshold < 0:
                logger.warning(f"Priority fee threshold {threshold} is negative, using default 0.001")
                return 0.001
            return threshold
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid PRIORITY_FEE_THRESHOLD value: {e}, using default 0.001")
            return 0.001
    
    def get_priority_fee_increase(self) -> float:
        """Get priority fee increase factor on retry (default 0.50 = 50%)."""
        try:
            increase = float(self.get("PRIORITY_FEE_INCREASE", "0.50"))
            if increase < 0:
                logger.warning(f"Priority fee increase {increase} is negative, using default 0.50")
                return 0.50
            return increase
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid PRIORITY_FEE_INCREASE value: {e}, using default 0.50")
            return 0.50
    
    def get_max_fee_pct_of_profit(self) -> float:
        """Get maximum fee as percentage of profit (default 0.05 = 5%)."""
        try:
            pct = float(self.get("MAX_FEE_PCT_OF_PROFIT", "0.05"))
            if pct < 0 or pct > 1.0:
                logger.warning(f"Max fee pct {pct} out of range [0, 1.0], using default 0.05")
                return 0.05
            return pct
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_FEE_PCT_OF_PROFIT value: {e}, using default 0.05")
            return 0.05
    
    def get_slippage_bps(self) -> int:
        """Get slippage tolerance in basis points (default 100 = 1%)."""
        try:
            bps = int(self.get("SLIPPAGE_BPS", "100"))
            if bps < 0 or bps > 10000:
                logger.warning(f"Slippage {bps} bps out of range [0, 10000], using default 100")
                return 100
            return bps
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid SLIPPAGE_BPS value: {e}, using default 100")
            return 100
    
    def get_high_volatility_slippage_bps(self) -> int:
        """Get slippage tolerance during high volatility (default 200 = 2%)."""
        try:
            bps = int(self.get("HIGH_VOLATILITY_SLIPPAGE_BPS", "200"))
            if bps < 0 or bps > 10000:
                logger.warning(f"High volatility slippage {bps} bps out of range, using default 200")
                return 200
            return bps
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid HIGH_VOLATILITY_SLIPPAGE_BPS value: {e}, using default 200")
            return 200
    
    def get_max_price_impact_pct(self) -> float:
        """Get maximum price impact percentage (default 0.02 = 2%)."""
        try:
            pct = float(self.get("MAX_PRICE_IMPACT_PCT", "0.02"))
            if pct < 0 or pct > 1.0:
                logger.warning(f"Max price impact {pct} out of range [0, 1.0], using default 0.02")
                return 0.02
            return pct
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_PRICE_IMPACT_PCT value: {e}, using default 0.02")
            return 0.02
    
    # Scan Interval Configuration (Requirement 9.4-9.6)
    
    def get_min_scan_interval(self) -> int:
        """Get minimum scan interval in seconds (default 5)."""
        try:
            interval = int(self.get("MIN_SCAN_INTERVAL", "5"))
            if interval < 1:
                logger.warning(f"Min scan interval {interval}s too low, using minimum 1s")
                return 1
            return interval
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MIN_SCAN_INTERVAL value: {e}, using default 5s")
            return 5
    
    def get_rate_limit_interval_increase(self) -> float:
        """Get scan interval increase factor on rate limits (default 0.50 = 50%)."""
        try:
            increase = float(self.get("RATE_LIMIT_INTERVAL_INCREASE", "0.50"))
            if increase < 0:
                logger.warning(f"Rate limit increase {increase} is negative, using default 0.50")
                return 0.50
            return increase
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid RATE_LIMIT_INTERVAL_INCREASE value: {e}, using default 0.50")
            return 0.50
    
    def get_empty_scan_threshold(self) -> int:
        """Get number of empty scans before interval increase (default 10)."""
        try:
            threshold = int(self.get("EMPTY_SCAN_THRESHOLD", "10"))
            if threshold < 1:
                logger.warning(f"Empty scan threshold {threshold} too low, using minimum 1")
                return 1
            return threshold
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid EMPTY_SCAN_THRESHOLD value: {e}, using default 10")
            return 10
    
    def get_empty_scan_interval(self) -> int:
        """Get scan interval after empty scans in seconds (default 30)."""
        try:
            interval = int(self.get("EMPTY_SCAN_INTERVAL", "30"))
            if interval < 1:
                logger.warning(f"Empty scan interval {interval}s too low, using minimum 1s")
                return 1
            return interval
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid EMPTY_SCAN_INTERVAL value: {e}, using default 30s")
            return 30
    
    # Strategy Enable/Disable Flags
    
    def is_strategy_enabled(self, strategy_name: str) -> bool:
        """
        Check if a strategy is enabled.
        
        Args:
            strategy_name: "jupiter_swap", "marinade_stake", or "airdrop_hunter"
            
        Returns:
            True if enabled, False otherwise
        """
        strategy_name = strategy_name.lower()
        if strategy_name == "jupiter_swap":
            key = "ENABLE_JUPITER_SWAP"
        elif strategy_name == "marinade_stake":
            key = "ENABLE_MARINADE_STAKE"
        elif strategy_name == "airdrop_hunter":
            key = "ENABLE_AIRDROP_HUNTER"
        else:
            logger.warning(f"Unknown strategy '{strategy_name}', assuming enabled")
            return True
        
        value = self.get(key, "true").lower()
        return value in ("true", "1", "yes", "on")
    
    # Transaction Execution Configuration (Requirement 1.3-1.6)
    
    def get_confirmation_timeout(self) -> int:
        """Get transaction confirmation timeout in seconds (default 60)."""
        try:
            timeout = int(self.get("CONFIRMATION_TIMEOUT", "60"))
            if timeout < 10:
                logger.warning(f"Confirmation timeout {timeout}s too low, using minimum 10s")
                return 10
            if timeout > 300:
                logger.warning(f"Confirmation timeout {timeout}s too high, using maximum 300s")
                return 300
            return timeout
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid CONFIRMATION_TIMEOUT value: {e}, using default 60s")
            return 60
    
    def get_max_retries(self) -> int:
        """Get maximum transaction retry attempts (default 3)."""
        try:
            retries = int(self.get("MAX_RETRIES", "3"))
            if retries < 0:
                logger.warning(f"Max retries {retries} is negative, using default 3")
                return 3
            if retries > 10:
                logger.warning(f"Max retries {retries} too high, using maximum 10")
                return 10
            return retries
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid MAX_RETRIES value: {e}, using default 3")
            return 3


def validate_environment(require_all: bool = False) -> Dict[str, str]:
    """
    Validate environment configuration.
    
    Args:
        require_all: If True, require all production variables
        
    Returns:
        Dictionary of validated configuration
        
    Raises:
        ConfigurationError: If required variables are missing
    """
    config = EnvironmentConfig()
    return config.validate(require_all=require_all)


def load_config(env_file: Optional[str] = None, require_all: bool = False) -> EnvironmentConfig:
    """
    Load and validate configuration.
    
    Args:
        env_file: Path to .env file
        require_all: If True, require all production variables
        
    Returns:
        Validated EnvironmentConfig instance
        
    Raises:
        ConfigurationError: If configuration is invalid
    """
    config = EnvironmentConfig(env_file)
    config.validate(require_all=require_all)
    return config


def check_startup_requirements() -> None:
    """
    Check startup requirements and fail fast if critical config is missing.
    
    This should be called at the start of main() to ensure the agent
    can run properly.
    
    Raises:
        ConfigurationError: If critical configuration is missing
        SystemExit: If startup checks fail
    """
    try:
        config = EnvironmentConfig()
        
        # Determine if we're in production
        is_production = config.is_production()
        
        logger.info("Checking startup requirements...")
        logger.info(f"Environment: {'production' if is_production else 'development'}")
        logger.info(f"Network: {config.get_network()}")
        
        # Validate configuration
        validated = config.validate(require_all=is_production)
        
        # Check Python version
        if sys.version_info < (3, 8):
            raise ConfigurationError(
                f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}"
            )
        
        # Check critical directories exist
        required_dirs = ["logs", "config"]
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                logger.info(f"Creating directory: {dir_name}")
                dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Startup requirements satisfied")
        
        # Print configuration summary
        logger.info("Configuration:")
        logger.info(f"  Scan interval: {config.get_scan_interval()}s")
        logger.info(f"  Performance fee: {config.get_performance_fee() * 100}%")
        logger.info(f"  Max loss per trade: {config.get_max_loss_per_trade() * 100}%")
        logger.info(f"  Log level: {config.get('LOG_LEVEL')}")
        
        logger.info("Risk Management:")
        logger.info(f"  Max position: {config.get_max_position_pct() * 100}%")
        logger.info(f"  Max daily loss: {config.get_max_daily_loss_pct() * 100}%")
        logger.info(f"  Min balance: {config.get_min_balance_sol()} SOL")
        logger.info(f"  High risk position: {config.get_risk_position_pct('high') * 100}%")
        logger.info(f"  Medium risk position: {config.get_risk_position_pct('medium') * 100}%")
        logger.info(f"  Low risk position: {config.get_risk_position_pct('low') * 100}%")
        
        logger.info("Fee & Slippage:")
        logger.info(f"  Slippage tolerance: {config.get_slippage_bps()} bps")
        logger.info(f"  Max price impact: {config.get_max_price_impact_pct() * 100}%")
        logger.info(f"  Max fee % of profit: {config.get_max_fee_pct_of_profit() * 100}%")
        
        logger.info("Strategies:")
        logger.info(f"  Jupiter Swap: {'enabled' if config.is_strategy_enabled('jupiter_swap') else 'disabled'}")
        logger.info(f"  Marinade Stake: {'enabled' if config.is_strategy_enabled('marinade_stake') else 'disabled'}")
        logger.info(f"  Airdrop Hunter: {'enabled' if config.is_strategy_enabled('airdrop_hunter') else 'disabled'}")
        
        logger.info("Transaction Execution:")
        logger.info(f"  Confirmation timeout: {config.get_confirmation_timeout()}s")
        logger.info(f"  Max retries: {config.get_max_retries()}")
        
        # Warn about missing optional features
        if not config.get("HELIUS_API_KEY"):
            logger.warning("HELIUS_API_KEY not set - using default RPC (may be slower)")
        
        # Report multi-API configuration
        helius_keys = config.get_helius_api_keys()
        if helius_keys:
            logger.info(f"Multi-API scaling: {len(helius_keys)} Helius API key(s) configured")
            logger.info(f"Price cache TTL: {config.get_price_cache_ttl()}s")
            logger.info(f"Strategy cache TTL: {config.get_strategy_cache_ttl()}s")
            logger.info(f"RPC batch size: {config.get_rpc_batch_size()} users")
            logger.info(f"Scan stagger window: {config.get_scan_stagger_window()}s")
        
        if not config.get("DISCORD_WEBHOOK_URL"):
            logger.warning("⚠️  DISCORD_WEBHOOK_URL not set - Discord notifications disabled")
        
        logger.info("")
        
    except ConfigurationError as e:
        logger.error(f"\n❌ Configuration Error: {e}\n")
        logger.error("Please fix the configuration and try again.")
        logger.error("See README.md for setup instructions.\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Startup Error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    # Test configuration validation
    try:
        check_startup_requirements()
        print("✅ Configuration is valid")
    except SystemExit:
        pass
