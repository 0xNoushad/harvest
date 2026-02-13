"""
Common API response fixtures for testing.

This module provides a comprehensive library of mock API responses for all
external services used by the Harvest bot. These fixtures ensure consistent
and realistic test data across all test suites.

Services covered:
- Helius RPC (Solana blockchain data)
- Solana RPC (blockchain transactions)
- Jupiter API (token swaps)
- Marinade API (liquid staking)
- Groq API (AI chat)
- CoinGecko API (price data)
- Telegram API (bot messaging)

Usage:
    from tests.fixtures import HELIUS_FIXTURES, JUPITER_FIXTURES
    
    # Get a mock balance response
    balance_response = HELIUS_FIXTURES["get_balance_success"]
    
    # Get a mock Jupiter quote
    quote_response = JUPITER_FIXTURES["quote_success"]
"""

from typing import Dict, Any


# ============================================================================
# Helius RPC Fixtures
# ============================================================================

HELIUS_FIXTURES: Dict[str, Dict[str, Any]] = {
    "get_balance_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": 1000000000  # 1 SOL in lamports
        }
    },
    
    "get_balance_zero": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": 0
        }
    },
    
    "get_account_info_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": {
                "data": ["", "base64"],
                "executable": False,
                "lamports": 1000000000,
                "owner": "11111111111111111111111111111111",
                "rentEpoch": 361
            }
        }
    },
    
    "get_account_info_not_found": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": None
        }
    },
    
    "get_token_accounts_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": [
                {
                    "account": {
                        "data": {
                            "parsed": {
                                "info": {
                                    "mint": "So11111111111111111111111111111111111111112",
                                    "owner": "TestWallet1234567890123456789012345",
                                    "tokenAmount": {
                                        "amount": "1000000000",
                                        "decimals": 9,
                                        "uiAmount": 1.0,
                                        "uiAmountString": "1.0"
                                    }
                                },
                                "type": "account"
                            },
                            "program": "spl-token",
                            "space": 165
                        },
                        "executable": False,
                        "lamports": 2039280,
                        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                        "rentEpoch": 361
                    },
                    "pubkey": "TokenAccount1234567890123456789012345"
                }
            ]
        }
    },
    
    "get_recent_blockhash_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "context": {"slot": 123456789},
            "value": {
                "blockhash": "EkSnNWid2cvwEVnVx9aBqawnmiCNiDgp3gUdkDPTKN1N",
                "lastValidBlockHeight": 123456789
            }
        }
    },
    
    "send_transaction_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW"
    },
    
    "get_transaction_success": {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "slot": 123456789,
            "transaction": {
                "message": {
                    "accountKeys": [],
                    "header": {
                        "numReadonlySignedAccounts": 0,
                        "numReadonlyUnsignedAccounts": 1,
                        "numRequiredSignatures": 1
                    },
                    "instructions": [],
                    "recentBlockhash": "EkSnNWid2cvwEVnVx9aBqawnmiCNiDgp3gUdkDPTKN1N"
                },
                "signatures": [
                    "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW"
                ]
            },
            "meta": {
                "err": None,
                "fee": 5000,
                "postBalances": [995000000],
                "preBalances": [1000000000],
                "status": {"Ok": None}
            }
        }
    },
    
    "rpc_error_invalid_params": {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32602,
            "message": "Invalid params: invalid type: string \"invalid\", expected a valid Pubkey"
        }
    },
    
    "rpc_error_rate_limit": {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": 429,
            "message": "Too many requests"
        }
    }
}


# ============================================================================
# Jupiter API Fixtures
# ============================================================================

JUPITER_FIXTURES: Dict[str, Dict[str, Any]] = {
    "quote_success": {
        "inputMint": "So11111111111111111111111111111111111111112",
        "inAmount": "1000000000",
        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "outAmount": "100000000",
        "otherAmountThreshold": "95000000",
        "swapMode": "ExactIn",
        "slippageBps": 50,
        "priceImpactPct": "0.1",
        "routePlan": [
            {
                "swapInfo": {
                    "ammKey": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
                    "label": "Raydium",
                    "inputMint": "So11111111111111111111111111111111111111112",
                    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "inAmount": "1000000000",
                    "outAmount": "100000000",
                    "feeAmount": "25000",
                    "feeMint": "So11111111111111111111111111111111111111112"
                },
                "percent": 100
            }
        ]
    },
    
    "quote_no_route": {
        "error": "No routes found for the given input and output mints"
    },
    
    "swap_success": {
        "swapTransaction": "base64_encoded_transaction_data",
        "lastValidBlockHeight": 123456789
    },
    
    "swap_error_slippage": {
        "error": "Slippage tolerance exceeded"
    },
    
    "tokens_list": {
        "tokens": [
            {
                "address": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "name": "Wrapped SOL",
                "decimals": 9,
                "logoURI": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/So11111111111111111111111111111111111111112/logo.png"
            },
            {
                "address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "symbol": "USDC",
                "name": "USD Coin",
                "decimals": 6,
                "logoURI": "https://raw.githubusercontent.com/solana-labs/token-list/main/assets/mainnet/EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v/logo.png"
            }
        ]
    }
}


# ============================================================================
# Marinade API Fixtures
# ============================================================================

MARINADE_FIXTURES: Dict[str, Dict[str, Any]] = {
    "stake_success": {
        "transaction": "base64_encoded_transaction_data",
        "msolAmount": "950000000",  # Slightly less due to fees
        "solAmount": "1000000000"
    },
    
    "unstake_success": {
        "transaction": "base64_encoded_transaction_data",
        "solAmount": "1050000000",  # Slightly more due to rewards
        "msolAmount": "1000000000"
    },
    
    "state_success": {
        "msolPrice": 1.05,
        "tvl": 5000000000000000,
        "apy": 6.5,
        "validatorCount": 450
    }
}


# ============================================================================
# Groq API Fixtures
# ============================================================================

GROQ_FIXTURES: Dict[str, Dict[str, Any]] = {
    "chat_completion_success": {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "mixtral-8x7b-32768",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Your current balance is 1.5 SOL (approximately $190). You have 3 active strategies running."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70
        }
    },
    
    "chat_completion_error_rate_limit": {
        "error": {
            "message": "Rate limit exceeded",
            "type": "rate_limit_error",
            "code": "rate_limit_exceeded"
        }
    },
    
    "chat_completion_error_context_length": {
        "error": {
            "message": "Context length exceeded",
            "type": "invalid_request_error",
            "code": "context_length_exceeded"
        }
    }
}


# ============================================================================
# CoinGecko API Fixtures
# ============================================================================

COINGECKO_FIXTURES: Dict[str, Dict[str, Any]] = {
    "simple_price_success": {
        "solana": {
            "usd": 127.50,
            "usd_24h_change": 5.2,
            "usd_market_cap": 55000000000,
            "last_updated_at": 1677652288
        }
    },
    
    "simple_price_multiple": {
        "solana": {
            "usd": 127.50,
            "usd_24h_change": 5.2
        },
        "usd-coin": {
            "usd": 1.00,
            "usd_24h_change": 0.01
        },
        "bonk": {
            "usd": 0.00001234,
            "usd_24h_change": -2.5
        }
    },
    
    "coin_not_found": {
        "error": "coin not found"
    },
    
    "rate_limit_error": {
        "status": {
            "error_code": 429,
            "error_message": "You've exceeded the Rate Limit. Please visit https://www.coingecko.com/en/api/pricing to subscribe to a plan."
        }
    }
}


# ============================================================================
# Telegram API Fixtures
# ============================================================================

TELEGRAM_FIXTURES: Dict[str, Dict[str, Any]] = {
    "send_message_success": {
        "ok": True,
        "result": {
            "message_id": 123,
            "from": {
                "id": 987654321,
                "is_bot": True,
                "first_name": "HarvestBot",
                "username": "harvest_bot"
            },
            "chat": {
                "id": 12345,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1677652288,
            "text": "Welcome to Harvest Bot!"
        }
    },
    
    "send_message_error_blocked": {
        "ok": False,
        "error_code": 403,
        "description": "Forbidden: bot was blocked by the user"
    },
    
    "send_message_error_chat_not_found": {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: chat not found"
    },
    
    "get_updates_success": {
        "ok": True,
        "result": [
            {
                "update_id": 123456789,
                "message": {
                    "message_id": 123,
                    "from": {
                        "id": 12345,
                        "is_bot": False,
                        "first_name": "Test",
                        "username": "testuser"
                    },
                    "chat": {
                        "id": 12345,
                        "first_name": "Test",
                        "username": "testuser",
                        "type": "private"
                    },
                    "date": 1677652288,
                    "text": "/start"
                }
            }
        ]
    },
    
    "callback_query_success": {
        "ok": True,
        "result": True
    }
}


# ============================================================================
# Airdrop/Bounty Fixtures
# ============================================================================

AIRDROP_FIXTURES: Dict[str, Dict[str, Any]] = {
    "available_airdrops": [
        {
            "name": "BONK Airdrop",
            "token": "BONK",
            "amount": "1000000",
            "claimable": True,
            "expires_at": "2024-12-31T23:59:59Z",
            "claim_url": "https://bonk.com/claim"
        },
        {
            "name": "JUP Airdrop",
            "token": "JUP",
            "amount": "500",
            "claimable": True,
            "expires_at": "2024-12-31T23:59:59Z",
            "claim_url": "https://jup.ag/claim"
        }
    ],
    
    "claim_success": {
        "success": True,
        "signature": "5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW",
        "amount": "1000000",
        "token": "BONK"
    },
    
    "claim_already_claimed": {
        "success": False,
        "error": "Airdrop already claimed"
    }
}


# ============================================================================
# Portfolio Fixtures
# ============================================================================

PORTFOLIO_FIXTURES: Dict[str, Dict[str, Any]] = {
    "portfolio_with_tokens": {
        "tokens": [
            {
                "mint": "So11111111111111111111111111111111111111112",
                "symbol": "SOL",
                "name": "Wrapped SOL",
                "amount": 1.5,
                "decimals": 9,
                "uiAmount": 1.5,
                "price": 127.50,
                "value": 191.25
            },
            {
                "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "symbol": "USDC",
                "name": "USD Coin",
                "amount": 100.0,
                "decimals": 6,
                "uiAmount": 100.0,
                "price": 1.00,
                "value": 100.00
            }
        ],
        "totalValue": 291.25,
        "tokenCount": 2
    },
    
    "portfolio_empty": {
        "tokens": [],
        "totalValue": 0.0,
        "tokenCount": 0
    },
    
    "portfolio_with_nfts": {
        "tokens": [],
        "nfts": [
            {
                "mint": "NFT1234567890123456789012345678901234",
                "name": "Degen Ape #1234",
                "collection": "Degen Ape Academy",
                "floorPrice": 50.0,
                "imageUrl": "https://example.com/nft.png"
            }
        ],
        "totalValue": 50.0,
        "tokenCount": 0,
        "nftCount": 1
    }
}


# ============================================================================
# Error Fixtures (Common Errors)
# ============================================================================

ERROR_FIXTURES: Dict[str, Dict[str, Any]] = {
    "network_timeout": {
        "error": "Request timeout",
        "code": "ETIMEDOUT"
    },
    
    "connection_refused": {
        "error": "Connection refused",
        "code": "ECONNREFUSED"
    },
    
    "service_unavailable": {
        "error": "Service temporarily unavailable",
        "code": 503
    },
    
    "unauthorized": {
        "error": "Unauthorized",
        "code": 401,
        "message": "Invalid API key"
    },
    
    "forbidden": {
        "error": "Forbidden",
        "code": 403,
        "message": "Access denied"
    },
    
    "not_found": {
        "error": "Not found",
        "code": 404,
        "message": "Resource not found"
    },
    
    "internal_server_error": {
        "error": "Internal server error",
        "code": 500,
        "message": "An unexpected error occurred"
    }
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_fixture(service: str, fixture_name: str) -> Dict[str, Any]:
    """
    Get a fixture by service and name.
    
    Args:
        service: Service name (helius, jupiter, marinade, groq, coingecko, telegram)
        fixture_name: Fixture name
        
    Returns:
        Fixture dictionary
        
    Raises:
        KeyError: If service or fixture not found
        
    Example:
        balance = get_fixture("helius", "get_balance_success")
    """
    fixtures_map = {
        "helius": HELIUS_FIXTURES,
        "jupiter": JUPITER_FIXTURES,
        "marinade": MARINADE_FIXTURES,
        "groq": GROQ_FIXTURES,
        "coingecko": COINGECKO_FIXTURES,
        "telegram": TELEGRAM_FIXTURES,
        "airdrop": AIRDROP_FIXTURES,
        "portfolio": PORTFOLIO_FIXTURES,
        "error": ERROR_FIXTURES
    }
    
    if service not in fixtures_map:
        raise KeyError(f"Unknown service: {service}")
    
    fixtures = fixtures_map[service]
    if fixture_name not in fixtures:
        raise KeyError(f"Unknown fixture '{fixture_name}' for service '{service}'")
    
    return fixtures[fixture_name]


def list_fixtures(service: Optional[str] = None) -> Dict[str, list]:
    """
    List all available fixtures.
    
    Args:
        service: Optional service name to filter by
        
    Returns:
        Dictionary mapping service names to lists of fixture names
        
    Example:
        all_fixtures = list_fixtures()
        helius_fixtures = list_fixtures("helius")
    """
    fixtures_map = {
        "helius": HELIUS_FIXTURES,
        "jupiter": JUPITER_FIXTURES,
        "marinade": MARINADE_FIXTURES,
        "groq": GROQ_FIXTURES,
        "coingecko": COINGECKO_FIXTURES,
        "telegram": TELEGRAM_FIXTURES,
        "airdrop": AIRDROP_FIXTURES,
        "portfolio": PORTFOLIO_FIXTURES,
        "error": ERROR_FIXTURES
    }
    
    if service:
        if service not in fixtures_map:
            raise KeyError(f"Unknown service: {service}")
        return {service: list(fixtures_map[service].keys())}
    
    return {svc: list(fixtures.keys()) for svc, fixtures in fixtures_map.items()}
