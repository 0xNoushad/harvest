"""
Initial database schema.

Creates the base tables for Harvest.
"""


async def upgrade(db):
    """Create initial schema."""
    
    # Users table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(255) PRIMARY KEY,
            preferences JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✓ Created users table")
    
    # Conversations table
    await db.execute("""
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
    await db.execute("""
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
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
        ON conversations(user_id)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
        ON conversations(timestamp)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_user_id 
        ON trades(user_id)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
        ON trades(timestamp)
    """)
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_strategy 
        ON trades(strategy_name)
    """)
    print("   ✓ Created indexes")


async def downgrade(db):
    """Drop initial schema."""
    await db.execute("DROP TABLE IF EXISTS trades CASCADE")
    await db.execute("DROP TABLE IF EXISTS conversations CASCADE")
    await db.execute("DROP TABLE IF EXISTS users CASCADE")
    print("   ✓ Dropped all tables")
