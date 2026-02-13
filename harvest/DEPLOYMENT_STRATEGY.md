# 🚀 Zero-Downtime Deployment Strategy

## The Problem

You're right - if you just `git pull && docker-compose restart`, your bot will:
- ❌ Stop processing trades
- ❌ Lose active user sessions
- ❌ Drop pending notifications
- ❌ Crash mid-transaction

**This is BAD for a trading bot!**

---

## Solution: Blue-Green Deployment

### How It Works:

```
┌─────────────────────────────────────────┐
│  Users → Load Balancer                  │
└────────────┬────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐      ┌────▼───┐
│ BLUE   │      │ GREEN  │
│ (old)  │      │ (new)  │
│ v1.0   │      │ v1.1   │
└────────┘      └────────┘

Step 1: Deploy GREEN (new version)
Step 2: Test GREEN
Step 3: Switch traffic to GREEN
Step 4: Shutdown BLUE
```

**Zero downtime! Users never notice.**

---

## Implementation for Railway

### Option 1: Railway's Built-in Deployments (Easiest)

Railway automatically does zero-downtime deployments!

```bash
# Just push to GitHub
git add .
git commit -m "Update trading logic"
git push origin main

# Railway automatically:
# 1. Builds new version
# 2. Starts new container
# 3. Health checks pass
# 4. Switches traffic
# 5. Shuts down old container
```

**That's it! Railway handles everything.**

### Option 2: Manual Blue-Green (More Control)

```bash
# Deploy two services on Railway
Service 1: harvest-blue (current)
Service 2: harvest-green (new)

# Update green
git push origin main

# Test green
curl https://harvest-green.railway.app/health

# Switch traffic (update DNS/load balancer)
# Shutdown blue
```

---

## Implementation for Hetzner

### Using Docker Compose:

```yaml
# docker-compose.blue-green.yml
version: '3.8'

services:
  # Blue (current version)
  worker-blue:
    image: harvest:blue
    container_name: harvest_worker_blue
    environment:
      - VERSION=blue
    networks:
      - harvest

  # Green (new version)
  worker-green:
    image: harvest:green
    container_name: harvest_worker_green
    environment:
      - VERSION=green
    networks:
      - harvest
    profiles:
      - green  # Only start when explicitly enabled

  # Nginx load balancer
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-blue-green.conf:/etc/nginx/nginx.conf
    networks:
      - harvest
```

### Deployment Script:

```bash
#!/bin/bash
# deploy.sh - Zero-downtime deployment

set -e

echo "🚀 Starting zero-downtime deployment..."

# Build new version
echo "📦 Building new version..."
docker build -t harvest:green .

# Start green (new version)
echo "🟢 Starting green version..."
docker-compose --profile green up -d worker-green

# Wait for health check
echo "🏥 Waiting for health check..."
sleep 10
until curl -f http://localhost:8080/health; do
    echo "Waiting for green to be healthy..."
    sleep 5
done

# Switch nginx to green
echo "🔄 Switching traffic to green..."
cp nginx-green.conf /etc/nginx/nginx.conf
nginx -s reload

# Wait a bit for connections to drain
echo "⏳ Draining connections from blue..."
sleep 30

# Stop blue (old version)
echo "🔵 Stopping blue version..."
docker-compose stop worker-blue

# Promote green to blue
echo "✅ Promoting green to blue..."
docker tag harvest:green harvest:blue
docker-compose --profile green down worker-green
docker-compose up -d worker-blue

echo "🎉 Deployment complete!"
```

---

## Database Migrations (Critical!)

### The Problem:

```
Old code expects: users table with 3 columns
New code expects: users table with 4 columns
→ CRASH if you deploy without migration!
```

### Solution: Backward-Compatible Migrations

```python
# migrations/001_add_user_tier.py
"""
Add user_tier column to users table.

This migration is BACKWARD COMPATIBLE:
- Old code ignores new column
- New code uses new column
"""

async def upgrade(db):
    # Add column with default value
    await db.execute("""
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS user_tier VARCHAR(20) DEFAULT 'free'
    """)
    print("✅ Added user_tier column")

async def downgrade(db):
    # Remove column
    await db.execute("""
        ALTER TABLE users 
        DROP COLUMN IF EXISTS user_tier
    """)
    print("✅ Removed user_tier column")
```

### Migration Runner:

```python
# scripts/run_migrations.py
import asyncio
import asyncpg
import os
from pathlib import Path

async def run_migrations():
    """Run all pending migrations."""
    db = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    # Create migrations table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get applied migrations
    applied = await db.fetch("SELECT name FROM migrations")
    applied_names = {row['name'] for row in applied}
    
    # Find migration files
    migrations_dir = Path("migrations")
    migration_files = sorted(migrations_dir.glob("*.py"))
    
    for migration_file in migration_files:
        name = migration_file.stem
        
        if name in applied_names:
            print(f"⏭️  Skipping {name} (already applied)")
            continue
        
        print(f"🔄 Running migration: {name}")
        
        # Import and run migration
        spec = importlib.util.spec_from_file_location(name, migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        await module.upgrade(db)
        
        # Record migration
        await db.execute(
            "INSERT INTO migrations (name) VALUES ($1)",
            name
        )
        
        print(f"✅ Applied {name}")
    
    await db.close()
    print("🎉 All migrations complete!")

if __name__ == "__main__":
    asyncio.run(run_migrations())
```

---

## Safe Deployment Checklist

### Before Deploying:

- [ ] Run tests locally
- [ ] Check database migrations
- [ ] Review breaking changes
- [ ] Backup database
- [ ] Test on staging environment

### During Deployment:

- [ ] Run migrations first
- [ ] Deploy new version
- [ ] Health check passes
- [ ] Monitor error logs
- [ ] Check key metrics

### After Deployment:

- [ ] Verify trades executing
- [ ] Check user notifications
- [ ] Monitor for errors
- [ ] Keep old version for 24h (rollback ready)

---

## Rollback Strategy

### If Something Goes Wrong:

```bash
# Quick rollback script
#!/bin/bash
# rollback.sh

echo "🔙 Rolling back to previous version..."

# Switch nginx back to blue
cp nginx-blue.conf /etc/nginx/nginx.conf
nginx -s reload

# Start blue (old version)
docker-compose up -d worker-blue

# Stop green (new version)
docker-compose --profile green down worker-green

echo "✅ Rollback complete!"
```

### Railway Rollback:

```bash
# In Railway dashboard:
1. Go to Deployments
2. Find previous successful deployment
3. Click "Redeploy"
4. Done!
```

---

## Testing Strategy

### 1. Local Testing

```bash
# Run tests
pytest

# Run integration tests
pytest tests/test_integration_e2e.py

# Test with real APIs (devnet)
SOLANA_NETWORK=devnet python -m agent.main
```

### 2. Staging Environment

```bash
# Deploy to staging first
git push origin staging

# Test with small amount of real money
# Monitor for 24 hours
# If good, deploy to production
```

### 3. Canary Deployment

```bash
# Deploy to 10% of users first
# Monitor for issues
# Gradually increase to 100%
```

---

## Monitoring During Deployment

### Key Metrics to Watch:

```python
# scripts/monitor_deployment.py
import asyncio
import asyncpg
import time

async def monitor():
    """Monitor key metrics during deployment."""
    db = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    while True:
        # Check error rate
        errors = await db.fetchval("""
            SELECT COUNT(*) FROM trades 
            WHERE was_successful = false 
            AND timestamp > NOW() - INTERVAL '5 minutes'
        """)
        
        # Check trade volume
        trades = await db.fetchval("""
            SELECT COUNT(*) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
        """)
        
        # Check active users
        users = await db.fetchval("""
            SELECT COUNT(DISTINCT user_id) FROM trades 
            WHERE timestamp > NOW() - INTERVAL '5 minutes'
        """)
        
        print(f"📊 Metrics (last 5 min):")
        print(f"   Trades: {trades}")
        print(f"   Errors: {errors}")
        print(f"   Users: {users}")
        print(f"   Error rate: {errors/trades*100 if trades > 0 else 0:.1f}%")
        print()
        
        # Alert if error rate > 10%
        if trades > 0 and errors/trades > 0.1:
            print("🚨 HIGH ERROR RATE! Consider rollback!")
        
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(monitor())
```

---

## CI/CD Pipeline (GitHub Actions)

### .github/workflows/deploy.yml

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest
      - name: Run linter
        run: flake8 agent/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        run: |
          # Railway auto-deploys on push
          echo "✅ Tests passed, Railway will auto-deploy"
      
      - name: Wait for deployment
        run: sleep 60
      
      - name: Health check
        run: |
          curl -f ${{ secrets.RAILWAY_URL }}/health || exit 1
      
      - name: Notify success
        run: |
          curl -X POST ${{ secrets.TELEGRAM_WEBHOOK }} \
            -d "text=✅ Deployment successful!"
```

---

## Best Practices

### 1. Always Use Migrations

```bash
# Before deploying
python scripts/run_migrations.py

# Then deploy
git push origin main
```

### 2. Deploy During Low Traffic

```bash
# Best times:
- 2-4 AM (lowest user activity)
- Weekdays (avoid weekends)
- After market close (for trading bots)
```

### 3. Monitor for 1 Hour After Deploy

```bash
# Watch logs
docker-compose logs -f

# Monitor metrics
python scripts/monitor_deployment.py

# Check error rate
# If > 5% errors, rollback immediately
```

### 4. Keep Rollback Ready

```bash
# Always keep previous version running for 24h
# Can switch back instantly if needed
```

### 5. Test Migrations Separately

```bash
# Test migration on staging first
python scripts/run_migrations.py --dry-run

# Then run on production
python scripts/run_migrations.py
```

---

## Railway-Specific Tips

### Railway Auto-Deploys Safely:

1. ✅ Builds new version
2. ✅ Runs health checks
3. ✅ Switches traffic gradually
4. ✅ Keeps old version for rollback
5. ✅ Zero downtime

### To Disable Auto-Deploy:

```bash
# In railway.toml
[deploy]
autoDeployEnabled = false
```

### Manual Deploy:

```bash
railway up
```

---

## Quick Reference

### Safe Deployment:

```bash
# 1. Run tests
pytest

# 2. Run migrations
python scripts/run_migrations.py

# 3. Deploy
git push origin main

# 4. Monitor
docker-compose logs -f
python scripts/monitor_deployment.py

# 5. If issues, rollback
./rollback.sh
```

### Emergency Rollback:

```bash
# Railway: Click "Redeploy" on previous version
# Hetzner: ./rollback.sh
# Docker: docker-compose up -d worker-blue
```

---

## Bottom Line

**Railway handles zero-downtime automatically!**

Just:
1. Run migrations first
2. Push to GitHub
3. Railway deploys safely
4. Monitor for issues
5. Rollback if needed

**Your users won't even notice! 🚀**
