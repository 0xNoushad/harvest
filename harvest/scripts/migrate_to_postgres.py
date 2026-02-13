"""
Migrate from SQLite to PostgreSQL for distributed deployment.

This script:
1. Reads data from SQLite
2. Creates PostgreSQL schema
3. Migrates all data
4. Verifies migration
"""

import sqlite3
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def migrate_database(
    sqlite_path: str = "config/harvest.db",
    postgres_url: str = None
):
    """
    Migrate from SQLite to PostgreSQL.
    
    Args:
        sqlite_path: Path to SQLite database
        postgres_url: PostgreSQL connection URL
    """
    print("🔄 Starting database migration...")
    print(f"   SQLite: {sqlite_path}")
    print(f"   PostgreSQL: {postgres_url}")
    
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to PostgreSQL
    pg_conn = await asyncpg.connect(postgres_url)
    
    try:
        # Create PostgreSQL schema
        print("\n📋 Creating PostgreSQL schema...")
        await create_postgres_schema(pg_conn)
        
        # Migrate users
        print("\n👥 Migrating users...")
        await migrate_users(sqlite_cursor, pg_conn)
        
        # Migrate conversations
        print("\n💬 Migrating conversations...")
        await migrate_conversations(sqlite_cursor, pg_conn)
        
        # Migrate trades
        print("\n📊 Migrating trades...")
        await migrate_trades(sqlite_cursor, pg_conn)
        
        # Verify migration
        print("\n✅ Verifying migration...")
        await verify_migration(sqlite_cursor, pg_conn)
        
        print("\n🎉 Migration complete!")
        
    finally:
        sqlite_conn.close()
        await pg_conn.close()


async def create_postgres_schema(conn):
    """Create PostgreSQL schema."""
    
    # Users table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            preferences JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✓ Created users table")
    
    # Conversations table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) REFERENCES users(user_id),
            role VARCHAR(50),
            message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✓ Created conversations table")
    
    # Trades table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) REFERENCES users(user_id),
            strategy_name VARCHAR(255),
            timestamp TIMESTAMP,
            expected_profit DECIMAL(20, 10),
            actual_profit DECIMAL(20, 10),
            transaction_hash VARCHAR(255),
            was_successful BOOLEAN,
            error_message TEXT,
            gas_fees DECIMAL(20, 10),
            execution_time_ms INTEGER
        )
    """)
    print("   ✓ Created trades table")
    
    # Create indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
        ON conversations(user_id)
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_user_id 
        ON trades(user_id)
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
        ON trades(timestamp)
    """)
    print("   ✓ Created indexes")


async def migrate_users(sqlite_cursor, pg_conn):
    """Migrate users table."""
    sqlite_cursor.execute("SELECT * FROM users")
    users = sqlite_cursor.fetchall()
    
    count = 0
    for user in users:
        await pg_conn.execute("""
            INSERT INTO users (user_id, preferences, created_at, last_active)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE
            SET preferences = EXCLUDED.preferences,
                last_active = EXCLUDED.last_active
        """, user['user_id'], user['preferences'], 
             user['created_at'], user['last_active'])
        count += 1
    
    print(f"   ✓ Migrated {count} users")


async def migrate_conversations(sqlite_cursor, pg_conn):
    """Migrate conversations table."""
    sqlite_cursor.execute("SELECT * FROM conversations")
    conversations = sqlite_cursor.fetchall()
    
    count = 0
    for conv in conversations:
        await pg_conn.execute("""
            INSERT INTO conversations (user_id, role, message, timestamp)
            VALUES ($1, $2, $3, $4)
        """, conv['user_id'], conv['role'], 
             conv['message'], conv['timestamp'])
        count += 1
    
    print(f"   ✓ Migrated {count} conversations")


async def migrate_trades(sqlite_cursor, pg_conn):
    """Migrate trades table."""
    try:
        sqlite_cursor.execute("SELECT * FROM trades")
        trades = sqlite_cursor.fetchall()
        
        count = 0
        for trade in trades:
            await pg_conn.execute("""
                INSERT INTO trades (
                    user_id, strategy_name, timestamp, expected_profit,
                    actual_profit, transaction_hash, was_successful,
                    error_message, gas_fees, execution_time_ms
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, 
                trade.get('user_id'),
                trade.get('strategy_name'),
                trade.get('timestamp'),
                trade.get('expected_profit'),
                trade.get('actual_profit'),
                trade.get('transaction_hash'),
                trade.get('was_successful'),
                trade.get('error_message'),
                trade.get('gas_fees'),
                trade.get('execution_time_ms')
            )
            count += 1
        
        print(f"   ✓ Migrated {count} trades")
    except sqlite3.OperationalError:
        print("   ⚠ Trades table doesn't exist in SQLite, skipping")


async def verify_migration(sqlite_cursor, pg_conn):
    """Verify migration was successful."""
    
    # Count users
    sqlite_cursor.execute("SELECT COUNT(*) FROM users")
    sqlite_users = sqlite_cursor.fetchone()[0]
    
    pg_users = await pg_conn.fetchval("SELECT COUNT(*) FROM users")
    
    print(f"   Users: SQLite={sqlite_users}, PostgreSQL={pg_users}")
    assert sqlite_users == pg_users, "User count mismatch!"
    
    # Count conversations
    sqlite_cursor.execute("SELECT COUNT(*) FROM conversations")
    sqlite_convs = sqlite_cursor.fetchone()[0]
    
    pg_convs = await pg_conn.fetchval("SELECT COUNT(*) FROM conversations")
    
    print(f"   Conversations: SQLite={sqlite_convs}, PostgreSQL={pg_convs}")
    assert sqlite_convs == pg_convs, "Conversation count mismatch!"
    
    print("   ✓ All counts match!")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument(
        "--sqlite",
        default="config/harvest.db",
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--postgres",
        default=os.getenv("DATABASE_URL"),
        help="PostgreSQL connection URL"
    )
    
    args = parser.parse_args()
    
    if not args.postgres:
        print("❌ Error: PostgreSQL URL not provided")
        print("   Set DATABASE_URL environment variable or use --postgres flag")
        sys.exit(1)
    
    await migrate_database(args.sqlite, args.postgres)


if __name__ == "__main__":
    asyncio.run(main())
