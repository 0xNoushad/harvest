"""User control system for Harvest - manages user preferences and ALWAYS mode."""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class UserControl:
    """
    User control system for managing strategy preferences.
    
    Manages user preferences for strategy automation with JSON persistence.
    Supports ALWAYS mode where strategies execute automatically without
    user approval.
    
    Features:
    - Save and read preferences from JSON file
    - Check if strategy should execute automatically (ALWAYS mode)
    - Enable/disable ALWAYS mode for specific strategies
    - Persistent storage with atomic writes
    """
    
    DEFAULT_STORAGE_PATH = "config/user_preferences.json"
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize user control with path to preferences file.
        
        Args:
            storage_path: Path to preferences JSON file (default: config/user_preferences.json)
        """
        self.storage_path = Path(storage_path or self.DEFAULT_STORAGE_PATH)
        self._preferences: Dict[str, bool] = {}
        
        # Ensure config directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing preferences
        self._load_preferences()
        
        logger.info(f"UserControl initialized with storage: {self.storage_path}")
    
    def should_execute(self, strategy_name: str) -> bool:
        """
        Check if strategy is in ALWAYS mode.
        
        Args:
            strategy_name: Name of the strategy to check
        
        Returns:
            True if strategy should execute automatically, False otherwise
        """
        return self._preferences.get(strategy_name, False)
    
    def set_always(self, strategy_name: str):
        """
        Enable ALWAYS mode for strategy.
        
        Args:
            strategy_name: Name of the strategy to enable
        """
        self._preferences[strategy_name] = True
        self._save_preferences()
        logger.info(f"ALWAYS mode enabled for strategy: {strategy_name}")
    
    def set_ask(self, strategy_name: str):
        """
        Disable ALWAYS mode for strategy.
        
        Args:
            strategy_name: Name of the strategy to disable
        """
        self._preferences[strategy_name] = False
        self._save_preferences()
        logger.info(f"ALWAYS mode disabled for strategy: {strategy_name}")
    
    def get_preferences(self) -> Dict[str, bool]:
        """
        Return all preferences.
        
        Returns:
            Dictionary mapping strategy names to ALWAYS mode status
        """
        return self._preferences.copy()
    
    def _load_preferences(self):
        """Load preferences from JSON file."""
        if not self.storage_path.exists():
            logger.info("No existing preferences file, starting with empty preferences")
            self._preferences = {}
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Validate that all values are booleans
                if not isinstance(data, dict):
                    raise ValueError("Preferences must be a dictionary")
                
                for key, value in data.items():
                    if not isinstance(value, bool):
                        raise ValueError(f"Preference value for '{key}' must be boolean, got {type(value)}")
                
                self._preferences = data
                logger.info(f"Loaded {len(self._preferences)} preferences from {self.storage_path}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse preferences JSON: {e}, starting with empty preferences")
            self._preferences = {}
        except Exception as e:
            logger.error(f"Failed to load preferences: {e}, starting with empty preferences")
            self._preferences = {}
    
    def _save_preferences(self):
        """Save preferences to JSON file with atomic write."""
        try:
            # Write to temporary file first (atomic write)
            temp_path = self.storage_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self._preferences, f, indent=2, sort_keys=True)
            
            # Atomic rename
            temp_path.replace(self.storage_path)
            
            logger.debug(f"Saved preferences to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()


def main():
    """Test user control functionality."""
    print("🌾 Testing Harvest User Control\n")
    
    # Create user control with test path
    test_path = "config/test_preferences.json"
    user_control = UserControl(storage_path=test_path)
    
    # Test setting preferences
    print("Setting preferences...")
    user_control.set_always("liquid_staking")
    user_control.set_always("airdrop_farmer")
    user_control.set_ask("nft_flipper")
    
    # Test checking preferences
    print("\nChecking preferences...")
    strategies = ["liquid_staking", "airdrop_farmer", "nft_flipper", "arbitrage"]
    for strategy in strategies:
        should_execute = user_control.should_execute(strategy)
        status = "ALWAYS" if should_execute else "ASK"
        print(f"  {strategy}: {status}")
    
    # Test getting all preferences
    print("\nAll preferences:")
    prefs = user_control.get_preferences()
    for strategy, always_mode in prefs.items():
        print(f"  {strategy}: {always_mode}")
    
    # Test persistence by creating new instance
    print("\nTesting persistence...")
    user_control2 = UserControl(storage_path=test_path)
    prefs2 = user_control2.get_preferences()
    print(f"Loaded {len(prefs2)} preferences from file")
    
    # Verify round-trip
    assert prefs == prefs2, "Preferences not persisted correctly"
    print("✅ Round-trip test passed")
    
    # Clean up test file
    Path(test_path).unlink(missing_ok=True)
    
    print("\n✅ User control test complete")


if __name__ == "__main__":
    main()
