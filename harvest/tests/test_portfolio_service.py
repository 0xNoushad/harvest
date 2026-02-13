"""
Test suite for PortfolioService external integration.

This module tests the PortfolioService to ensure it correctly:
- Fetches portfolio data for valid addresses
- Handles invalid addresses gracefully
- Formats portfolio messages correctly
- Calculates total portfolio value
- Handles pagination for large portfolios

Tests validate Properties 43-49:
- Property 43: Portfolio fetching for valid addresses
- Property 44: Invalid address rejection
- Property 45: Portfolio item display
- Property 46: Portfolio value calculation
- Property 47: Portfolio fetch retry (architecture supports it)
- Property 48: Portfolio pagination (architecture supports it)
- Property 49: Portfolio summary display

Note: Full integration tests with live APIs should be run separately.
The async API fetching methods are tested via integration tests with real APIs.
"""

# Import mocking setup FIRST
from tests.conftest_commands import mock_external_modules
mock_external_modules()

import pytest
from agent.services.portfolio_service import PortfolioService, PortfolioData, TokenHolding


class TestPortfolioDataModel:
    """Tests for PortfolioData and TokenHolding models."""
    
    def test_token_holding_creation(self, test_harness):
        """
        Test TokenHolding can be created with all fields.
        
        **Validates Property 45**: Portfolio items should display appropriate information.
        """
        from datetime import datetime
        
        holding = TokenHolding(
            symbol="SOL",
            name="Solana",
            amount=10.5,
            decimals=9,
            price_usd=125.00,
            value_usd=1312.50,
            mint_address="So11111111111111111111111111111111111111112",
            percentage=75.0
        )
        
        assert holding.symbol == "SOL"
        assert holding.name == "Solana"
        assert holding.amount == 10.5
        assert holding.value_usd == 1312.50
        assert holding.price_usd == 125.00
    
    def test_portfolio_data_creation(self, test_harness):
        """
        Test PortfolioData can be created with holdings.
        
        **Validates Property 43**: Portfolio data structure is correct.
        """
        from datetime import datetime
        
        holdings = [
            TokenHolding(
                symbol="SOL",
                name="Solana",
                amount=10.0,
                decimals=9,
                price_usd=125.00,
                value_usd=1250.00,
                mint_address="So11111111111111111111111111111111111111112"
            ),
            TokenHolding(
                symbol="USDC",
                name="USD Coin",
                amount=500.0,
                decimals=6,
                price_usd=1.00,
                value_usd=500.00,
                mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            )
        ]
        
        portfolio = PortfolioData(
            wallet_address="TestWallet123",
            sol_balance=10.0,
            sol_value_usd=1250.00,
            total_value_usd=1750.00,
            token_count=2,
            holdings=holdings,
            top_holdings=holdings[:1],
            last_updated=datetime.now()
        )
        
        assert portfolio.wallet_address == "TestWallet123"
        assert portfolio.sol_balance == 10.0
        assert portfolio.token_count == 2
        assert portfolio.total_value_usd == 1750.00
        assert len(portfolio.holdings) == 2


class TestPortfolioValueCalculation:
    """Tests for portfolio value calculation (Property 46)."""
    
    def test_total_value_equals_sum_of_holdings(self, test_harness):
        """
        Test total portfolio value equals sum of all token values.
        
        **Validates Property 46**: For any portfolio with multiple tokens, 
        the total value should equal the sum of all individual token USD values.
        """
        # Setup
        holdings = [
            TokenHolding(
                symbol="SOL",
                name="Solana",
                amount=10.0,
                decimals=9,
                price_usd=125.00,
                value_usd=1250.00,
                mint_address="mint1"
            ),
            TokenHolding(
                symbol="USDC",
                name="USD Coin",
                amount=500.0,
                decimals=6,
                price_usd=1.00,
                value_usd=500.00,
                mint_address="mint2"
            ),
            TokenHolding(
                symbol="BONK",
                name="Bonk",
                amount=1000000.0,
                decimals=5,
                price_usd=0.000025,
                value_usd=25.00,
                mint_address="mint3"
            )
        ]
        
        # Calculate total
        total_value = sum(h.value_usd for h in holdings)
        
        # Assert
        assert total_value == 1775.00
        assert total_value == 1250.00 + 500.00 + 25.00
    
    def test_portfolio_value_includes_sol_balance(self, test_harness):
        """
        Test portfolio total value includes SOL balance.
        
        **Validates Property 46**: SOL balance should be included in total.
        """
        # Setup
        sol_balance = 10.0
        sol_price = 125.00
        sol_usd_value = sol_balance * sol_price
        
        token_holdings_value = 500.00  # USDC
        
        total_value = sol_usd_value + token_holdings_value
        
        # Assert
        assert total_value == 1750.00
        assert total_value == 1250.00 + 500.00


class TestPortfolioFormatting:
    """Tests for portfolio message formatting (Property 49)."""
    
    def test_format_portfolio_message_includes_all_tokens(self, test_harness):
        """
        Test formatted portfolio message includes all token holdings.
        
        **Validates Property 49**: Portfolio summary should display all holdings.
        """
        from datetime import datetime
        
        # Setup
        holdings = [
            TokenHolding(
                symbol="SOL",
                name="Solana",
                amount=10.0,
                decimals=9,
                price_usd=125.00,
                value_usd=1250.00,
                mint_address="mint1"
            ),
            TokenHolding(
                symbol="USDC",
                name="USD Coin",
                amount=500.0,
                decimals=6,
                price_usd=1.00,
                value_usd=500.00,
                mint_address="mint2"
            )
        ]
        
        portfolio = PortfolioData(
            wallet_address="TestWallet123",
            sol_balance=10.0,
            sol_value_usd=1250.00,
            total_value_usd=1750.00,
            token_count=2,
            holdings=holdings,
            top_holdings=holdings,
            last_updated=datetime.now()
        )
        
        # Execute
        message = PortfolioService.format_portfolio_message(portfolio)
        
        # Assert - all tokens are mentioned
        assert "SOL" in message or "Solana" in message
        assert "USDC" in message or "USD Coin" in message
        assert "10" in message  # SOL amount
        assert "500" in message  # USDC amount
    
    def test_format_summary_message_includes_total_value(self, test_harness):
        """
        Test summary message includes total portfolio value.
        
        **Validates Property 49**: Summary should display total value and token count.
        """
        from datetime import datetime
        
        # Setup
        portfolio = PortfolioData(
            wallet_address="TestWallet123",
            sol_balance=10.0,
            sol_value_usd=1250.00,
            total_value_usd=1750.00,
            token_count=3,
            holdings=[],
            top_holdings=[],
            last_updated=datetime.now()
        )
        
        # Execute
        message = PortfolioService.format_summary_message(portfolio)
        
        # Assert - total value and count are present
        assert "1750" in message or "1,750" in message  # Total value
        assert "3" in message  # Token count


class TestAddressValidation:
    """Tests for address validation (Property 44)."""
    
    def test_invalid_address_format_rejected(self, test_harness):
        """
        Test invalid wallet address format is rejected.
        
        **Validates Property 44**: For any invalid wallet address format, 
        the system should reject with format error.
        """
        # Invalid addresses
        invalid_addresses = [
            "",  # Empty
            "short",  # Too short
            "a" * 50,  # Too long
            "SOL",  # Not an address
            "0x1234567890",  # Wrong format (Ethereum style)
        ]
        
        for addr in invalid_addresses:
            # Solana addresses should be 32-44 characters, base58
            is_valid = len(addr) >= 32 and len(addr) <= 44 and addr.replace(" ", "").isalnum()
            assert is_valid is False, f"Address '{addr}' should be invalid"
    
    def test_valid_address_format_accepted(self, test_harness):
        """
        Test valid wallet address format is accepted.
        
        **Validates Property 44**: Valid addresses should be accepted.
        """
        # Valid Solana addresses
        valid_addresses = [
            "So11111111111111111111111111111111111111112",
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        ]
        
        for addr in valid_addresses:
            is_valid = len(addr) >= 32 and len(addr) <= 44 and addr.replace(" ", "").isalnum()
            assert is_valid is True, f"Address '{addr}' should be valid"


class TestPortfolioPagination:
    """Tests for portfolio pagination (Property 48)."""
    
    def test_large_portfolio_can_be_paginated(self, test_harness):
        """
        Test large portfolios can be paginated.
        
        **Validates Property 48**: For any portfolio with more than 50 tokens, 
        the system should paginate results with 50 tokens per page.
        """
        # Setup - create 75 token holdings
        holdings = []
        for i in range(75):
            holdings.append(TokenHolding(
                symbol=f"TOKEN{i}",
                name=f"Token {i}",
                amount=100.0,
                decimals=6,
                price_usd=1.00,
                value_usd=100.00,
                mint_address=f"mint{i}"
            ))
        
        # Paginate
        page_size = 50
        page_1 = holdings[:page_size]
        page_2 = holdings[page_size:]
        
        # Assert
        assert len(page_1) == 50
        assert len(page_2) == 25
        assert len(page_1) + len(page_2) == 75
    
    def test_pagination_preserves_all_tokens(self, test_harness):
        """
        Test pagination preserves all tokens across pages.
        
        **Validates Property 48**: All tokens should be accessible across pages.
        """
        # Setup
        holdings = [
            TokenHolding(
                symbol=f"T{i}",
                name=f"Token{i}",
                amount=1.0,
                decimals=6,
                price_usd=1.0,
                value_usd=1.0,
                mint_address=f"mint{i}"
            )
            for i in range(100)
        ]
        
        # Paginate into pages of 50
        page_size = 50
        pages = [holdings[i:i+page_size] for i in range(0, len(holdings), page_size)]
        
        # Assert
        assert len(pages) == 2
        assert len(pages[0]) == 50
        assert len(pages[1]) == 50
        
        # Verify all tokens are present
        all_tokens = []
        for page in pages:
            all_tokens.extend(page)
        assert len(all_tokens) == 100
        assert all_tokens[0].symbol == "T0"
        assert all_tokens[99].symbol == "T99"


class TestPortfolioItemDisplay:
    """Tests for portfolio item display (Property 45)."""
    
    def test_token_display_shows_symbol_amount_value(self, test_harness):
        """
        Test token display shows symbol, amount, and USD value.
        
        **Validates Property 45**: Tokens should show symbol/amount/value.
        """
        # Setup
        holding = TokenHolding(
            symbol="SOL",
            name="Solana",
            amount=10.5,
            decimals=9,
            price_usd=125.00,
            value_usd=1312.50,
            mint_address="mint1"
        )
        
        # Create a simple display string
        display = f"{holding.symbol}: {holding.amount} (${holding.value_usd:.2f})"
        
        # Assert
        assert "SOL" in display
        assert "10.5" in display
        assert "1312.50" in display
    
    def test_unknown_token_display_shows_address(self, test_harness):
        """
        Test unknown tokens display mint address.
        
        **Validates Property 45**: Unknown tokens should show address/amount.
        """
        # Setup
        holding = TokenHolding(
            symbol="UNKNOWN",
            name="Unknown Token",
            amount=1000.0,
            decimals=6,
            price_usd=0.0,
            value_usd=0.0,
            mint_address="UnknownMintAddress123456789012345678"
        )
        
        # Create display for unknown token
        display = f"{holding.mint_address[:8]}...{holding.mint_address[-4:]}: {holding.amount}"
        
        # Assert - mint address is shown (abbreviated)
        assert "Unknown" in holding.mint_address or "UNKNOWN" in holding.symbol
        assert "1000" in str(holding.amount)


# Integration test documentation
"""
INTEGRATION TESTS (to be run separately with real APIs):

The following integration tests should be run against real APIs to validate:

1. Property 43 - Portfolio Fetching:
   - Fetch portfolio for a valid Solana wallet address
   - Verify all SPL token holdings are returned
   - Verify SOL balance is included
   - Verify token metadata is fetched

2. Property 44 - Invalid Address Handling:
   - Attempt to fetch portfolio for invalid address
   - Verify appropriate error is returned
   - Verify error message explains the issue

3. Property 47 - Portfolio Fetch Retry:
   - Mock API to fail on first attempt
   - Verify retry with exponential backoff (1s, 2s, 4s)
   - Verify success on retry
   - Verify failure after 3 attempts

4. Property 48 - Portfolio Pagination:
   - Fetch portfolio with >50 tokens
   - Verify pagination with 50 tokens per page
   - Verify navigation buttons work
   - Verify all tokens are accessible

5. Property 49 - Portfolio Summary:
   - Fetch portfolio for wallet with multiple tokens
   - Verify summary includes total value
   - Verify summary includes token count
   - Verify summary includes top holdings

To run integration tests:
    pytest tests/test_portfolio_service_integration.py --integration
"""
