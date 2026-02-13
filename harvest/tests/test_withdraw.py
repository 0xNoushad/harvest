#!/usr/bin/env python3
"""
Test withdraw functionality with devnet faucet.
"""
import asyncio
import os
from dotenv import load_dotenv
from agent.core.wallet import WalletManager

# Load environment variables
load_dotenv()

async def test_withdraw():
    """Test the withdraw/send functionality."""
    print("🧪 Testing Withdraw Functionality\n")
    
    # Initialize wallet
    private_key = os.getenv("SOLANA_PRIVATE_KEY")
    if not private_key:
        print("❌ SOLANA_PRIVATE_KEY not found in .env")
        return
    
    wallet = WalletManager(
        private_key=private_key,
        network="devnet"  # Use devnet for testing
    )
    
    print(f"📍 Wallet Address: {wallet.get_public_key()}\n")
    
    # Check initial balance
    print("1️⃣ Checking initial balance...")
    balance = await wallet.get_balance()
    print(f"   Balance: {balance:.4f} SOL\n")
    
    # Request airdrop if balance is low
    if balance < 0.5:
        print("2️⃣ Requesting devnet airdrop...")
        success = await wallet.airdrop(1.0)
        if success:
            print("   ✅ Airdrop successful!")
            balance = await wallet.get_balance()
            print(f"   New Balance: {balance:.4f} SOL\n")
        else:
            print("   ❌ Airdrop failed\n")
    
    # Test send to a different address (you can replace this with your own)
    test_recipient = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    send_amount = 0.1
    
    print(f"3️⃣ Testing send {send_amount} SOL to {test_recipient[:8]}...{test_recipient[-8:]}...")
    
    if balance < send_amount + 0.01:  # Need extra for fees
        print(f"   ❌ Insufficient balance. Need at least {send_amount + 0.01} SOL")
        await wallet.close()
        return
    
    tx_signature = await wallet.send_sol(test_recipient, send_amount)
    
    if tx_signature:
        print(f"   ✅ Transaction successful!")
        print(f"   📝 Signature: {tx_signature}")
        print(f"   🔗 View: https://solscan.io/tx/{tx_signature}?cluster=devnet\n")
        
        # Check new balance
        new_balance = await wallet.get_balance()
        print(f"4️⃣ Final balance: {new_balance:.4f} SOL")
        print(f"   Sent: {send_amount} SOL")
        print(f"   Fee: ~{balance - new_balance - send_amount:.6f} SOL\n")
    else:
        print("   ❌ Transaction failed\n")
    
    await wallet.close()
    print("✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_withdraw())
