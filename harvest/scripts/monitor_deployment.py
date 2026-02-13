#!/usr/bin/env python3
"""
Monitor deployment metrics in real-time.

Tracks:
- Trade volume
- Error rate
- Active users
- Response times
"""

import asyncio
import asyncpg
import os
import sys
import time
from datetime import datetime
import argparse


class DeploymentMonitor:
    """Monitor key metrics during deployment."""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.db = None
        self.start_time = time.time()
    
    async def connect(self):
        """Connect to database."""
        self.db = await asyncpg.connect(self.db_url)
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.db:
            await self.db.close()
    
    async def get_metrics(self, minutes: int = 5):
        """Get metrics for last N minutes."""
        
        # Total trades
        total_trades = await self.db.fetchval(f"""
            SELECT COUNT(*) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
        """)
        
        # Failed trades
        failed_trades = await self.db.fetchval(f"""
            SELECT COUNT(*) FROM trades 
            WHERE was_successful = false 
            AND timestamp > NOW() - INTERVAL '{minutes} minutes'
        """)
        
        # Active users
        active_users = await self.db.fetchval(f"""
            SELECT COUNT(DISTINCT user_id) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
        """)
        
        # Average execution time
        avg_exec_time = await self.db.fetchval(f"""
            SELECT AVG(execution_time_ms) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
        """)
        
        # Total profit
        total_profit = await self.db.fetchval(f"""
            SELECT SUM(actual_profit) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '{minutes} minutes'
        """)
        
        return {
            'total_trades': total_trades or 0,
            'failed_trades': failed_trades or 0,
            'active_users': active_users or 0,
            'avg_exec_time': avg_exec_time or 0,
            'total_profit': total_profit or 0,
            'error_rate': (failed_trades / total_trades * 100) if total_trades > 0 else 0
        }
    
    def print_metrics(self, metrics: dict):
        """Print metrics in a nice format."""
        elapsed = int(time.time() - self.start_time)
        
        print(f"\n{'='*60}")
        print(f"📊 Deployment Metrics ({datetime.now().strftime('%H:%M:%S')})")
        print(f"   Elapsed: {elapsed}s")
        print(f"{'='*60}")
        print(f"📈 Trades (last 5 min):     {metrics['total_trades']}")
        print(f"❌ Failed:                  {metrics['failed_trades']}")
        print(f"👥 Active Users:            {metrics['active_users']}")
        print(f"⚡ Avg Execution Time:      {metrics['avg_exec_time']:.0f}ms")
        print(f"💰 Total Profit:            {metrics['total_profit']:.4f} SOL")
        print(f"📊 Error Rate:              {metrics['error_rate']:.1f}%")
        
        # Alert if error rate is high
        if metrics['error_rate'] > 10:
            print(f"\n🚨 HIGH ERROR RATE! Consider rollback!")
        elif metrics['error_rate'] > 5:
            print(f"\n⚠️  Elevated error rate. Monitor closely.")
        else:
            print(f"\n✅ Error rate is normal.")
        
        print(f"{'='*60}\n")
    
    async def monitor(self, duration: int = None, interval: int = 60):
        """
        Monitor metrics continuously.
        
        Args:
            duration: Total duration in seconds (None = forever)
            interval: Check interval in seconds
        """
        await self.connect()
        
        try:
            iterations = 0
            while True:
                # Get and print metrics
                metrics = await self.get_metrics()
                self.print_metrics(metrics)
                
                # Check if we should stop
                if duration:
                    elapsed = time.time() - self.start_time
                    if elapsed >= duration:
                        print(f"✅ Monitoring complete ({duration}s)")
                        break
                
                # Wait for next check
                await asyncio.sleep(interval)
                iterations += 1
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped by user")
        finally:
            await self.disconnect()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Monitor deployment metrics")
    parser.add_argument(
        '--duration',
        type=int,
        default=None,
        help='Duration to monitor in seconds (default: forever)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--db-url',
        default=os.getenv('DATABASE_URL'),
        help='Database URL (default: from DATABASE_URL env var)'
    )
    
    args = parser.parse_args()
    
    if not args.db_url:
        print("❌ Error: DATABASE_URL not set")
        print("Set DATABASE_URL environment variable or use --db-url flag")
        sys.exit(1)
    
    print("🔍 Starting deployment monitor...")
    print(f"   Duration: {args.duration or 'forever'}")
    print(f"   Interval: {args.interval}s")
    print(f"   Database: {args.db_url[:30]}...")
    print()
    
    monitor = DeploymentMonitor(args.db_url)
    await monitor.monitor(duration=args.duration, interval=args.interval)


if __name__ == "__main__":
    asyncio.run(main())
