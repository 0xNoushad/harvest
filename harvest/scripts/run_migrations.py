#!/usr/bin/env python3
"""
Database migration runner.

Runs all pending migrations in order.
"""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path
import importlib.util
import argparse


class MigrationRunner:
    """Run database migrations."""
    
    def __init__(self, db_url: str, migrations_dir: str = "migrations"):
        self.db_url = db_url
        self.migrations_dir = Path(migrations_dir)
        self.db = None
    
    async def connect(self):
        """Connect to database."""
        self.db = await asyncpg.connect(self.db_url)
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.db:
            await self.db.close()
    
    async def init_migrations_table(self):
        """Create migrations tracking table."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def get_applied_migrations(self):
        """Get list of applied migrations."""
        rows = await self.db.fetch("SELECT name FROM migrations ORDER BY id")
        return {row['name'] for row in rows}
    
    def get_migration_files(self):
        """Get list of migration files."""
        if not self.migrations_dir.exists():
            return []
        
        files = sorted(self.migrations_dir.glob("*.py"))
        return [f for f in files if not f.name.startswith('__')]
    
    async def run_migration(self, migration_file: Path, dry_run: bool = False):
        """
        Run a single migration.
        
        Args:
            migration_file: Path to migration file
            dry_run: If True, don't actually apply migration
        """
        name = migration_file.stem
        
        print(f"🔄 Running migration: {name}")
        
        # Import migration module
        spec = importlib.util.spec_from_file_location(name, migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if migration has upgrade function
        if not hasattr(module, 'upgrade'):
            print(f"⚠️  Warning: {name} has no upgrade() function")
            return False
        
        if dry_run:
            print(f"   [DRY RUN] Would apply {name}")
            return True
        
        # Run upgrade
        try:
            await module.upgrade(self.db)
            
            # Record migration
            await self.db.execute(
                "INSERT INTO migrations (name) VALUES ($1)",
                name
            )
            
            print(f"✅ Applied {name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply {name}: {e}")
            return False
    
    async def run_all(self, dry_run: bool = False):
        """
        Run all pending migrations.
        
        Args:
            dry_run: If True, don't actually apply migrations
        """
        await self.connect()
        
        try:
            # Initialize migrations table
            await self.init_migrations_table()
            
            # Get applied migrations
            applied = await self.get_applied_migrations()
            print(f"📋 Found {len(applied)} applied migrations")
            
            # Get migration files
            migration_files = self.get_migration_files()
            print(f"📁 Found {len(migration_files)} migration files")
            
            if not migration_files:
                print("⚠️  No migrations found in migrations/ directory")
                return True
            
            # Run pending migrations
            pending = [f for f in migration_files if f.stem not in applied]
            
            if not pending:
                print("✅ All migrations already applied")
                return True
            
            print(f"\n🔄 Running {len(pending)} pending migrations...")
            if dry_run:
                print("   [DRY RUN MODE - No changes will be made]")
            print()
            
            success = True
            for migration_file in pending:
                if not await self.run_migration(migration_file, dry_run):
                    success = False
                    break
            
            if success:
                print(f"\n✅ All migrations complete!")
            else:
                print(f"\n❌ Migration failed!")
            
            return success
            
        finally:
            await self.disconnect()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without applying changes'
    )
    parser.add_argument(
        '--db-url',
        default=os.getenv('DATABASE_URL'),
        help='Database URL (default: from DATABASE_URL env var)'
    )
    parser.add_argument(
        '--migrations-dir',
        default='migrations',
        help='Migrations directory (default: migrations/)'
    )
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ Error: DATABASE_URL not set")
        print("Set DATABASE_URL environment variable or use --db-url flag")
        sys.exit(1)
    
    print("🚀 Database Migration Runner")
    print("="*60)
    print(f"Database: {args.db_url[:30]}...")
    print(f"Migrations: {args.migrations_dir}")
    if args.dry_run:
        print("Mode: DRY RUN")
    print("="*60)
    print()
    
    runner = MigrationRunner(args.db_url, args.migrations_dir)
    success = await runner.run_all(dry_run=args.dry_run)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
