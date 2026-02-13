#!/usr/bin/env python3
"""
Integration Verification Script

Tests all external API integrations to ensure they're working correctly.
Run this after updating API endpoints or before deploying to production.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

console = Console()


def test_jupiter_api():
    """Test Jupiter API connectivity and quote functionality."""
    console.print("\n[bold cyan]Testing Jupiter API...[/bold cyan]")
    
    api_key = os.getenv("JUPITER_API_KEY")
    base_url = "https://api.jup.ag"
    
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
        console.print(f"  ✓ Using API key: {api_key[:10]}...")
    else:
        console.print("  ⚠ No API key found (will use public endpoint with 0.2% fee)")
    
    try:
        # Test quote endpoint
        params = {
            "inputMint": "So11111111111111111111111111111111111111112",  # SOL
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "amount": 100000000,  # 0.1 SOL
            "slippageBps": 50
        }
        
        response = requests.get(
            f"{base_url}/quote",
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            output_amount = int(data.get("outAmount", 0)) / 1e6
            console.print(f"  ✓ Quote successful: 0.1 SOL = {output_amount:.2f} USDC")
            return True, "Working"
        else:
            console.print(f"  ✗ Quote failed: {response.status_code} - {response.text}")
            return False, f"HTTP {response.status_code}"
    
    except Exception as e:
        console.print(f"  ✗ Error: {str(e)}")
        return False, str(e)


def test_magic_eden_api():
    """Test Magic Eden API connectivity."""
    console.print("\n[bold cyan]Testing Magic Eden API...[/bold cyan]")
    
    base_url_v2 = "https://api-mainnet.magiceden.dev/v2"
    
    try:
        # Test collection stats endpoint
        response = requests.get(
            f"{base_url_v2}/collections/degods/stats",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            floor_price = data.get("floorPrice", 0) / 1e9
            console.print(f"  ✓ API v2 working: DeGods floor = {floor_price:.2f} SOL")
            return True, "Working"
        else:
            console.print(f"  ✗ API v2 failed: {response.status_code}")
            return False, f"HTTP {response.status_code}"
    
    except Exception as e:
        console.print(f"  ✗ Error: {str(e)}")
        return False, str(e)


def test_helius_rpc():
    """Test Helius RPC connectivity."""
    console.print("\n[bold cyan]Testing Helius RPC...[/bold cyan]")
    
    api_key = os.getenv("HELIUS_API_KEY")
    
    if not api_key:
        console.print("  ⚠ No Helius API key found (using public RPC)")
        return None, "Not configured"
    
    rpc_url = f"https://rpc.helius.xyz/?api-key={api_key}"
    
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getHealth"
        }
        
        response = requests.post(rpc_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "result" in data and data["result"] == "ok":
                console.print("  ✓ Helius RPC healthy")
                return True, "Working"
            else:
                console.print(f"  ✗ Unexpected response: {data}")
                return False, "Unhealthy"
        else:
            console.print(f"  ✗ RPC failed: {response.status_code}")
            return False, f"HTTP {response.status_code}"
    
    except Exception as e:
        console.print(f"  ✗ Error: {str(e)}")
        return False, str(e)


def test_groq_api():
    """Test Groq API connectivity."""
    console.print("\n[bold cyan]Testing Groq API...[/bold cyan]")
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        console.print("  ✗ No Groq API key found")
        return False, "Not configured"
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": "Say 'test'"}],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            console.print("  ✓ Groq API working")
            return True, "Working"
        else:
            console.print(f"  ✗ Groq API failed: {response.status_code}")
            return False, f"HTTP {response.status_code}"
    
    except Exception as e:
        console.print(f"  ✗ Error: {str(e)}")
        return False, str(e)


def main():
    """Run all integration tests."""
    console.print(Panel.fit(
        "[bold green]🔍 Harvest Bot - Integration Verification[/bold green]\n"
        "Testing all external API integrations...",
        border_style="green"
    ))
    
    # Run tests
    results = {
        "Jupiter API": test_jupiter_api(),
        "Magic Eden API": test_magic_eden_api(),
        "Helius RPC": test_helius_rpc(),
        "Groq API": test_groq_api()
    }
    
    # Create results table
    table = Table(title="\n📊 Integration Test Results", show_header=True)
    table.add_column("Integration", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details")
    
    all_passed = True
    for name, (success, details) in results.items():
        if success is True:
            status = "[green]✓ PASS[/green]"
        elif success is False:
            status = "[red]✗ FAIL[/red]"
            all_passed = False
        else:
            status = "[yellow]⚠ SKIP[/yellow]"
        
        table.add_row(name, status, details)
    
    console.print(table)
    
    # Summary
    if all_passed:
        console.print("\n[bold green]✅ All integrations working![/bold green]")
        console.print("Your bot is ready to run.")
        return 0
    else:
        console.print("\n[bold red]❌ Some integrations failed![/bold red]")
        console.print("Please fix the issues above before running the bot.")
        console.print("\nCommon fixes:")
        console.print("  • Jupiter: Get API key from https://portal.jup.ag")
        console.print("  • Helius: Get API key from https://helius.dev")
        console.print("  • Groq: Get API key from https://console.groq.com")
        console.print("  • Magic Eden: Check if API is down at https://status.magiceden.io")
        return 1


if __name__ == "__main__":
    sys.exit(main())
