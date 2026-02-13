#!/usr/bin/env python3
"""
Database Viewer - View and manage Harvest Bot database

Shows:
- All users
- Trades
- Performance
- Fees
- Conversations
- Strategy states
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.database import Database


def print_header(title):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_table(headers, rows):
    """Print data as table."""
    if not rows:
        print("  (No data)")
        return
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    
    # Print header
    header_line = "  " + " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("  " + "-" * (len(header_line) - 2))
    
    # Print rows
    for row in rows:
        print("  " + " | ".join(str(cell).ljust(w) for cell, w in zip(row, widths)))


def view_users(db):
    """View all users."""
    print_header("USERS")
    
    users = db.get_all_users()
    
    if not users:
        print("  No users found")
        return
    
    headers = ["User ID", "Created", "Last Active", "Active"]
    rows = []
    
    for user in users:
        rows.append([
            user['user_id'],
            user['created_at'][:19],
            user['last_active'][:19],
            "✅" if user['is_active'] else "❌"
        ])
    
    print_table(headers, rows)
    print(f"\n  Total users: {len(users)}")


def view_trades(db, user_id=None, limit=10):
    """View recent trades."""
    print_header(f"RECENT TRADES (Last {limit})")
    
    if user_id:
        trades = db.get_user_trades(user_id, limit=limit)
    else:
        # Get all trades
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            trades = [dict(row) for row in cursor.fetchall()]
    
    if not trades:
        print("  No trades found")
        return
    
    headers = ["ID", "User", "Strategy", "Action", "Amount", "Profit", "Time"]
    rows = []
    
    for trade in trades:
        rows.append([
            trade['trade_id'],
            trade['user_id'][:12] + "...",
            trade['strategy_name'][:15],
            trade['action'][:10],
            f"{trade['amount']:.4f}",
            f"{trade['profit']:+.4f}",
            trade['timestamp'][:19]
        ])
    
    print_table(headers, rows)
    
    # Calculate totals
    total_profit = sum(t['profit'] for t in trades)
    winning = sum(1 for t in trades if t['profit'] > 0)
    losing = sum(1 for t in trades if t['profit'] < 0)
    
    print(f"\n  Total trades: {len(trades)}")
    print(f"  Total profit: {total_profit:+.4f} SOL")
    print(f"  Win rate: {winning}/{len(trades)} ({winning/len(trades)*100:.1f}%)")


def view_performance(db, user_id=None):
    """View performance stats."""
    print_header("PERFORMANCE")
    
    if user_id:
        perf = db.get_user_performance(user_id, days=30)
    else:
        # Get all performance
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM performance 
                ORDER BY date DESC 
                LIMIT 10
            """)
            perf = [dict(row) for row in cursor.fetchall()]
    
    if not perf:
        print("  No performance data found")
        return
    
    headers = ["User", "Date", "Trades", "Profit", "Win Rate", "Best", "Worst"]
    rows = []
    
    for p in perf:
        win_rate = 0
        if p['total_trades'] > 0:
            win_rate = p['winning_trades'] / p['total_trades'] * 100
        
        rows.append([
            p['user_id'][:12] + "...",
            p['date'],
            p['total_trades'],
            f"{p['total_profit']:+.4f}",
            f"{win_rate:.1f}%",
            f"{p['best_trade']:+.4f}",
            f"{p['worst_trade']:+.4f}"
        ])
    
    print_table(headers, rows)


def view_fees(db, user_id=None):
    """View fee history."""
    print_header("FEES")
    
    if user_id:
        fees = db.get_user_fees(user_id)
    else:
        # Get all fees
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fees 
                ORDER BY requested_at DESC 
                LIMIT 20
            """)
            fees = [dict(row) for row in cursor.fetchall()]
    
    if not fees:
        print("  No fees found")
        return
    
    headers = ["User", "Month", "Profit", "Fee", "Rate", "Status"]
    rows = []
    
    for fee in fees:
        status_emoji = {
            "pending": "⏳",
            "collected": "✅",
            "declined": "❌",
            "expired": "⏰"
        }.get(fee['status'], "❓")
        
        rows.append([
            fee['user_id'][:12] + "...",
            fee['month'],
            f"{fee['monthly_profit']:.4f}",
            f"{fee['fee_amount']:.4f}",
            f"{fee['fee_rate']*100:.0f}%",
            f"{status_emoji} {fee['status']}"
        ])
    
    print_table(headers, rows)
    
    # Calculate totals
    total_collected = sum(f['fee_amount'] for f in fees if f['status'] == 'collected')
    pending = sum(1 for f in fees if f['status'] == 'pending')
    
    print(f"\n  Total fees collected: {total_collected:.4f} SOL")
    print(f"  Pending approvals: {pending}")


def view_stats(db):
    """View platform statistics."""
    print_header("PLATFORM STATISTICS")
    
    stats = db.get_platform_stats()
    
    print(f"\n  👥 Total Users: {stats['total_users']}")
    print(f"  📊 Total Trades: {stats['total_trades']}")
    print(f"  💰 Total Profit: {stats['total_profit']:.4f} SOL")
    print(f"  💵 Total Fees Collected: {stats['total_fees']:.4f} SOL")
    
    # Calculate average profit per user
    if stats['total_users'] > 0:
        avg_profit = stats['total_profit'] / stats['total_users']
        print(f"  📈 Average Profit per User: {avg_profit:.4f} SOL")
    
    # Get wallet count
    wallets = db.get_all_wallets()
    print(f"  🔐 Secure Wallets: {len(wallets)}")


def view_wallets(db):
    """View all secure wallets."""
    print_header("SECURE WALLETS")
    
    wallets = db.get_all_wallets()
    
    if not wallets:
        print("  No wallets found")
        return
    
    headers = ["User", "Public Key", "Path", "Words", "KDF", "Created"]
    rows = []
    
    for wallet in wallets:
        rows.append([
            wallet['user_id'][:12] + "...",
            wallet['public_key'][:12] + "...",
            wallet['derivation_path'],
            wallet['mnemonic_words'],
            wallet['kdf_method'],
            wallet['created_at'][:19]
        ])
    
    print_table(headers, rows)
    print(f"\n  Total wallets: {len(wallets)}")


def view_user_detail(db, user_id):
    """View detailed info for a specific user."""
    print_header(f"USER DETAILS: {user_id}")
    
    # Get user
    user = db.get_user(user_id)
    if not user:
        print(f"  User not found: {user_id}")
        return
    
    print(f"\n  User ID: {user['user_id']}")
    print(f"  Created: {user['created_at']}")
    print(f"  Last Active: {user['last_active']}")
    print(f"  Active: {'✅ Yes' if user['is_active'] else '❌ No'}")
    
    # Get trades
    print("\n  Recent Trades:")
    view_trades(db, user_id, limit=5)
    
    # Get performance
    print("\n  Performance:")
    view_performance(db, user_id)
    
    # Get fees
    print("\n  Fees:")
    view_fees(db, user_id)
    
    # Get wallet
    wallet = db.get_user_wallet(user_id)
    if wallet:
        print("\n  Secure Wallet:")
        print(f"    Public Key: {wallet['public_key']}")
        print(f"    Derivation Path: {wallet['derivation_path']}")
        print(f"    Mnemonic Words: {wallet['mnemonic_words']}")
        print(f"    KDF Method: {wallet['kdf_method']}")
        print(f"    Encryption: {wallet['encryption_method']}")
        print(f"    Created: {wallet['created_at']}")
        if wallet['last_unlocked']:
            print(f"    Last Unlocked: {wallet['last_unlocked']}")
        print(f"    Solscan: https://solscan.io/account/{wallet['public_key']}")


def interactive_menu(db):
    """Interactive menu."""
    while True:
        print("\n" + "=" * 70)
        print("  HARVEST BOT - DATABASE VIEWER")
        print("=" * 70)
        print("\n  1. View all users")
        print("  2. View recent trades")
        print("  3. View performance")
        print("  4. View fees")
        print("  5. View platform stats")
        print("  6. View user details")
        print("  7. View secure wallets")
        print("  8. Export data")
        print("  0. Exit")
        
        choice = input("\n  Enter choice: ").strip()
        
        if choice == "1":
            view_users(db)
        elif choice == "2":
            limit = input("  How many trades? (default 10): ").strip()
            limit = int(limit) if limit else 10
            view_trades(db, limit=limit)
        elif choice == "3":
            view_performance(db)
        elif choice == "4":
            view_fees(db)
        elif choice == "5":
            view_stats(db)
        elif choice == "6":
            user_id = input("  Enter user ID: ").strip()
            if user_id:
                view_user_detail(db, user_id)
        elif choice == "7":
            view_wallets(db)
        elif choice == "8":
            export_data(db)
        elif choice == "0":
            print("\n  Goodbye! 👋")
            break
        else:
            print("\n  Invalid choice!")
        
        input("\n  Press Enter to continue...")


def export_data(db):
    """Export database to JSON."""
    print_header("EXPORT DATA")
    
    output_file = input("  Output file (default: database_export.json): ").strip()
    if not output_file:
        output_file = "database_export.json"
    
    data = {
        "exported_at": datetime.now().isoformat(),
        "users": db.get_all_users(),
        "stats": db.get_platform_stats()
    }
    
    # Get all trades
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT 1000")
        data["trades"] = [dict(row) for row in cursor.fetchall()]
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    print(f"\n  ✅ Data exported to: {output_file}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="View Harvest Bot database")
    parser.add_argument("--db", default="config/harvest.db", help="Database file path")
    parser.add_argument("--user", help="View specific user")
    parser.add_argument("--stats", action="store_true", help="Show platform stats")
    parser.add_argument("--trades", type=int, metavar="N", help="Show N recent trades")
    parser.add_argument("--export", metavar="FILE", help="Export data to JSON file")
    
    args = parser.parse_args()
    
    # Initialize database
    db = Database(args.db)
    
    # Check if database exists
    if not Path(args.db).exists():
        print(f"❌ Database not found: {args.db}")
        print(f"\n💡 The database will be created when you run the bot.")
        print(f"   Location: {Path(args.db).absolute()}")
        return
    
    # Execute commands
    if args.user:
        view_user_detail(db, args.user)
    elif args.stats:
        view_stats(db)
    elif args.trades:
        view_trades(db, limit=args.trades)
    elif args.export:
        data = {
            "exported_at": datetime.now().isoformat(),
            "users": db.get_all_users(),
            "stats": db.get_platform_stats()
        }
        with open(args.export, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Data exported to: {args.export}")
    else:
        # Interactive mode
        interactive_menu(db)


if __name__ == "__main__":
    main()
