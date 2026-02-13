"""
Setup script for test environment.

This script sets up the test environment including:
- Test database initialization
- Mock service configuration
- Test data seeding
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_test_environment():
    """Set up the test environment with required configuration."""
    
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "TELEGRAM_BOT_TOKEN": "test_token_123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        "HELIUS_API_KEY": "test_helius_key_123",
        "HELIUS_API_KEY_1": "test_helius_key_1",
        "HELIUS_API_KEY_2": "test_helius_key_2",
        "HELIUS_API_KEY_3": "test_helius_key_3",
        "GROQ_API_KEY": "test_groq_key_123",
        "PRICE_CACHE_TTL": "60",
        "STRATEGY_CACHE_TTL": "30",
        "RPC_BATCH_SIZE": "10",
        "SCAN_STAGGER_WINDOW": "60",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
        "LOG_LEVEL": "ERROR",  # Reduce noise in tests
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("✓ Test environment variables configured")


def create_test_directories():
    """Create necessary test directories."""
    test_dirs = [
        Path(__file__).parent / "fixtures",
        Path(__file__).parent / "data",
        Path(__file__).parent / "reports",
    ]
    
    for directory in test_dirs:
        directory.mkdir(exist_ok=True)
    
    print("✓ Test directories created")


def verify_dependencies():
    """Verify that required test dependencies are installed."""
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "hypothesis",
    ]
    
    optional_packages = [
        "pytest-cov",
        "pytest-mock",
    ]
    
    missing_required = []
    missing_optional = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_required.append(package)
    
    for package in optional_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_optional.append(package)
    
    if missing_required:
        print(f"✗ Missing required packages: {', '.join(missing_required)}")
        print(f"  Install with: pip install {' '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"⚠ Missing optional packages: {', '.join(missing_optional)}")
        print(f"  Install with: pip install {' '.join(missing_optional)}")
    
    print("✓ Required dependencies installed")
    return True


def main():
    """Main setup function."""
    print("Setting up test environment...")
    print()
    
    # Verify dependencies
    if not verify_dependencies():
        sys.exit(1)
    
    # Setup environment
    setup_test_environment()
    
    # Create directories
    create_test_directories()
    
    print()
    print("Test environment setup complete!")
    print()
    print("Run tests with:")
    print("  pytest tests/")
    print()
    print("Run with coverage:")
    print("  pytest tests/ --cov=agent --cov-report=html")
    print()
    print("Run specific test categories:")
    print("  pytest tests/ -m unit")
    print("  pytest tests/ -m integration")
    print("  pytest tests/ -m property")
    print()


if __name__ == "__main__":
    main()
