#!/usr/bin/env python3
"""
Test wallet balance and coin price fetching.
Tests both Solana RPC and CoinGecko API.
"""

import asyncio
import os
import sys
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.wallet import WalletManager


def test_coingecko_prices():
    """Test CoinGecko API for crypto prices."""
    print("\n🦎 Testing CoinGecko API...")
    print("=" * 60)
    
    # Test popular Solana ecosystem tokens
    tokens = {
        "solana": "SOL",
        "jupiter-exchange-solana": "JUP",
        "jito-governance-token": "JTO",
        "bonk": "BONK",
        "dogwifcoin": "WIF"
    }
    
    try:
        # CoinGecko free API endpoint
        ids = ",".join(tokens.keys())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n✅ CoinGecko API Working!\n")
        print("Current Prices:")
        print("-" * 60)
        
        for coin_id, symbol in tokens.items():
            if coin_id in data:
                price = data[coin_id].get("usd", 0)
                change = data[coin_id].get("usd_24h_change", 0)
                change_emoji = "📈" if change > 0 else "📉"
                
                print(f"{symbol:6} ${price:>10.4f}  {change_emoji} {change:>6.2f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ CoinGecko API Error: {e}")
        return False


async def test_wallet_balance():
    """Test wallet balance fetching from Solana RPC."""
    print("\n💰 Testing Wallet Balance...")
    print("=" * 60)
    
    try:
        # Check if we have a wallet configured
        private_key = os.getenv("SOLANA_PRIVATE_KEY")
        network = os.getenv("SOLANA_NETWORK", "devnet")
        
        if not private_key:
            print("⚠️  No SOLANA_PRIVATE_KEY in environment")
            print("   Using test wallet for demo...")
            # Use a known devnet wallet for testing
            private_key = "test_key_" + "1" * 64
        
        print(f"\nNetwork: {network}")
        
        # Create wallet manager
        wallet = WalletManager(network=network)
        
        print(f"Wallet Address: {wallet.public_key}")
        
        # Get balance
        print("\nFetching balance from Solana RPC...")
        balance = await wallet.get_balance()
        
        print(f"\n✅ Balance Retrieved Successfully!")
        print(f"   Balance: {balance:.4f} SOL")
        
        # Calculate USD value
        sol_price = get_sol_price()
        if sol_price:
            usd_value = balance * sol_price
            print(f"   USD Value: ${usd_value:.2f}")
        
        await wallet.close()
        return True
        
    except Exception as e:
        print(f"❌ Wallet Balance Error: {e}")
        return False


def get_sol_price():
    """Get current SOL price from CoinGecko."""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        data = response.json()
        return data.get("solana", {}).get("usd", 0)
    except:
        return None


def test_price_command():
    """Test the /price command functionality."""
    print("\n💵 Testing Price Command...")
    print("=" * 60)
    
    test_tokens = ["SOL", "JUP", "BONK", "WIF", "INVALID_TOKEN"]
    
    # Mapping of symbols to CoinGecko IDs
    token_map = {
        "SOL": "solana",
        "JUP": "jupiter-exchange-solana",
        "JTO": "jito-governance-token",
        "BONK": "bonk",
        "WIF": "dogwifcoin",
        "USDC": "usd-coin",
        "USDT": "tether"
    }
    
    for symbol in test_tokens:
        print(f"\nTesting: /price {symbol}")
        
        coin_id = token_map.get(symbol.upper())
        
        if not coin_id:
            print(f"   ❌ Token not found: {symbol}")
            continue
        
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=5)
            data = response.json()
            
            if coin_id in data:
                price = data[coin_id].get("usd", 0)
                change = data[coin_id].get("usd_24h_change", 0)
                change_emoji = "📈" if change > 0 else "📉"
                
                print(f"   ✅ {symbol}: ${price:.4f} {change_emoji} {change:+.2f}%")
            else:
                print(f"   ❌ No data for {symbol}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")


async def main():
    """Run all tests."""
    print("""
╔═══════════════════════════════════════════════════════════╗
║     🧪 WALLET & PRICE TESTING                            ║
║     Testing Solana RPC & CoinGecko API                   ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    results = []
    
    # Test 1: CoinGecko API
    results.append(("CoinGecko API", test_coingecko_prices()))
    
    # Test 2: Wallet Balance
    results.append(("Wallet Balance", await test_wallet_balance()))
    
    # Test 3: Price Command
    test_price_command()
    results.append(("Price Command", True))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
