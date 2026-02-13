"""
Pytest configuration for command tests with comprehensive mocking.

This module sets up all necessary mocks to allow command tests to run
without requiring full dependency installation.
"""

import sys
from unittest.mock import Mock, MagicMock

# Mock all problematic external dependencies
def mock_external_modules():
    """Mock all external modules that aren't needed for command testing."""
    
    # Cryptography mocks
    crypto_mock = Mock()
    crypto_mock.hazmat = Mock()
    crypto_mock.hazmat.primitives = Mock()
    crypto_mock.hazmat.primitives.ciphers = Mock()
    crypto_mock.hazmat.primitives.ciphers.aead = Mock()
    crypto_mock.hazmat.primitives.kdf = Mock()
    crypto_mock.hazmat.primitives.kdf.pbkdf2 = Mock()
    crypto_mock.hazmat.backends = Mock()
    crypto_mock.fernet = Mock()
    
    sys.modules['cryptography'] = crypto_mock
    sys.modules['cryptography.hazmat'] = crypto_mock.hazmat
    sys.modules['cryptography.hazmat.primitives'] = crypto_mock.hazmat.primitives
    sys.modules['cryptography.hazmat.primitives.ciphers'] = crypto_mock.hazmat.primitives.ciphers
    sys.modules['cryptography.hazmat.primitives.ciphers.aead'] = crypto_mock.hazmat.primitives.ciphers.aead
    sys.modules['cryptography.hazmat.primitives.kdf'] = crypto_mock.hazmat.primitives.kdf
    sys.modules['cryptography.hazmat.primitives.kdf.pbkdf2'] = crypto_mock.hazmat.primitives.kdf.pbkdf2
    sys.modules['cryptography.hazmat.backends'] = crypto_mock.hazmat.backends
    sys.modules['cryptography.fernet'] = crypto_mock.fernet
    
    # Solana/Solders mocks
    solders_mock = Mock()
    solders_mock.keypair = Mock()
    solders_mock.keypair.Keypair = Mock
    solders_mock.pubkey = Mock()
    # Create a mock Pubkey class with from_string method
    mock_pubkey_class = Mock()
    mock_pubkey_class.from_string = Mock(return_value=Mock())
    solders_mock.pubkey.Pubkey = mock_pubkey_class
    solders_mock.transaction = Mock()
    solders_mock.system_program = Mock()
    solders_mock.rpc = Mock()
    solders_mock.rpc.requests = Mock()
    solders_mock.rpc.requests.GetBalance = Mock
    solders_mock.rpc.requests.GetAccountInfo = Mock
    solders_mock.rpc.responses = Mock()
    solders_mock.instruction = Mock()
    solders_mock.instruction.Instruction = Mock
    solders_mock.instruction.AccountMeta = Mock
    solders_mock.message = Mock()
    solders_mock.hash = Mock()
    
    sys.modules['solders'] = solders_mock
    sys.modules['solders.keypair'] = solders_mock.keypair
    sys.modules['solders.pubkey'] = solders_mock.pubkey
    sys.modules['solders.transaction'] = solders_mock.transaction
    sys.modules['solders.system_program'] = solders_mock.system_program
    sys.modules['solders.rpc'] = solders_mock.rpc
    sys.modules['solders.rpc.requests'] = solders_mock.rpc.requests
    sys.modules['solders.rpc.responses'] = solders_mock.rpc.responses
    sys.modules['solders.instruction'] = solders_mock.instruction
    sys.modules['solders.message'] = solders_mock.message
    sys.modules['solders.hash'] = solders_mock.hash
    
    # Solana mocks - more comprehensive
    solana_mock = Mock()
    solana_mock.rpc = Mock()
    solana_mock.rpc.api = Mock()
    solana_mock.rpc.async_api = Mock()
    solana_mock.rpc.commitment = Mock()
    solana_mock.rpc.commitment.Confirmed = Mock()
    solana_mock.rpc.commitment.Finalized = Mock()
    solana_mock.rpc.types = Mock()
    solana_mock.transaction = Mock()
    solana_mock.system_program = Mock()
    
    sys.modules['solana'] = solana_mock
    sys.modules['solana.rpc'] = solana_mock.rpc
    sys.modules['solana.rpc.api'] = solana_mock.rpc.api
    sys.modules['solana.rpc.async_api'] = solana_mock.rpc.async_api
    sys.modules['solana.rpc.commitment'] = solana_mock.rpc.commitment
    sys.modules['solana.rpc.types'] = solana_mock.rpc.types
    sys.modules['solana.transaction'] = solana_mock.transaction
    sys.modules['solana.system_program'] = solana_mock.system_program
    
    # Other security/crypto mocks
    sys.modules['argon2'] = Mock()
    sys.modules['argon2.low_level'] = Mock()
    sys.modules['mnemonic'] = Mock()
    sys.modules['bip_utils'] = Mock()
    
    # Groq API mock
    groq_mock = Mock()
    groq_mock.AsyncGroq = Mock
    sys.modules['groq'] = groq_mock
    
    # HTTP client mocks
    sys.modules['aiohttp'] = Mock()
    sys.modules['requests'] = Mock()
    
    # Database mocks
    sys.modules['psycopg2'] = Mock()
    sys.modules['psycopg2.pool'] = Mock()
    
    # Telegram bot mocks
    telegram_mock = Mock()
    telegram_mock.Update = Mock
    telegram_mock.InlineKeyboardButton = Mock
    telegram_mock.InlineKeyboardMarkup = Mock
    telegram_mock.ext = Mock()
    telegram_mock.ext.ContextTypes = Mock()
    sys.modules['telegram'] = telegram_mock
    sys.modules['telegram.ext'] = telegram_mock.ext

# Call the mocking function before any imports
mock_external_modules()
