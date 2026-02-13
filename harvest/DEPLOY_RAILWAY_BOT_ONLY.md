# 🚀 Deploy Bot Only to Railway (No Website)

## Your Setup

You have:
- ✅ Convex Database (giant-lobster-195.convex.cloud)
- ✅ Redis Cloud (redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com)
- ✅ 3 Helius API keys
- ✅ 2 Groq API keys
- ✅ Jupiter API

You need:
- ⏳ Telegram bot (2 min)
- ⏳ Solana wallet (5 min)
- ⏳ Railway account (2 min)

**Deploy just the bot, no website!**

---

## Why This Setup is Perfect

### Convex vs PostgreSQL:
```
Convex:
✅ Real-time sync
✅ Serverless
✅ Free tier (1M reads/month)
✅ Built-in auth
✅ TypeScript SDK
✅ No migrations needed

PostgreSQL:
❌ Need to manage
❌ Migrations required
❌ More complex
```

### Redis + Convex:
```
Redis: Fast cache (prices, strategies)
Convex: Persistent data (users, trades)

Perfect combo! 🎯
```

### Railway Bot Only:
```
✅ Just run the bot
✅ No website hosting
✅ Cheaper ($5/month)
✅ Simpler deployment
✅ Easy to migrate to Hetzner
```

---

## Architecture

```
┌─────────────────────────────────────┐
│   Railway (Bot Only)                │
│   - Worker process                  │
│   - Telegram bot                    │
│   - Trading logic                   │
└──────────┬──────────────────────────┘
           │
    ┌──────┼──────┐
    │      │      │
┌───▼──┐ ┌─▼───┐ ┌▼─────┐
│Redis │ │Convex│ │Telegram│
│Cache │ │  DB  │ │  API   │
└──────┘ └──────┘ └────────┘
```

**No website, just pure bot! 🤖**

---

## Step 1: Set Up Telegram Bot (2 min)

```bash
# 1. Open Telegram
# 2. Search @BotFather
# 3. Send: /newbot
# 4. Follow instructions
# 5. Copy token

# Get your chat ID:
# 1. Start chat with your bot
# 2. Run:
python scripts/get_chat_id.py

# Save both:
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

---

## Step 2: Generate Solana Wallet (5 min)

```bash
# Install Solana CLI (if not installed)
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"

# Generate wallet
solana-keygen new --outfile wallet.json

# Get public key
solana-keygen pubkey wallet.json
# Save as: WALLET_ADDRESS

# Get private key (base58)
cat wallet.json
# Save as: WALLET_PRIVATE_KEY

# Fund wallet (devnet for testing)
solana airdrop 2 $(solana-keygen pubkey wallet.json) --url devnet

# Or fund with real SOL (mainnet)
# Send 0.5-1 SOL to your WALLET_ADDRESS
```

---

## Step 3: Configure Convex Integration

### Create Convex Adapter:

```python
# agent/core/convex_db.py
"""
Convex database adapter.
Replaces PostgreSQL with Convex.
"""

import os
import httpx
from typing import Optional, List, Dict

class ConvexDB:
    """Convex database client."""
    
    def __init__(self, url: str = None):
        self.url = url or os.getenv("CONVEX_URL")
        self.site_url = os.getenv("CONVEX_SITE_URL")
        self.client = httpx.AsyncClient()
    
    async def query(self, function: str, args: dict = None):
        """Query Convex function."""
        response = await self.client.post(
            f"{self.url}/api/query",
            json={
                "path": function,
                "args": args or {}
            }
        )
        return response.json()
    
    async def mutation(self, function: str, args: dict = None):
        """Run Convex mutation."""
        response = await self.client.post(
            f"{self.url}/api/mutation",
            json={
                "path": function,
                "args": args or {}
            }
        )
        return response.json()
    
    # User methods
    async def create_user(self, user_id: str):
        """Create user in Convex."""
        return await self.mutation("users:create", {"userId": user_id})
    
    async def get_user(self, user_id: str):
        """Get user from Convex."""
        return await self.query("users:get", {"userId": user_id})
    
    async def update_user(self, user_id: str, data: dict):
        """Update user in Convex."""
        return await self.mutation("users:update", {
            "userId": user_id,
            "data": data
        })
    
    # Trade methods
    async def create_trade(self, trade_data: dict):
        """Create trade in Convex."""
        return await self.mutation("trades:create", trade_data)
    
    async def get_trades(self, user_id: str, limit: int = 100):
        """Get user trades from Convex."""
        return await self.query("trades:list", {
            "userId": user_id,
            "limit": limit
        })
    
    async def close(self):
        """Close client."""
        await self.client.aclose()
```

---

## Step 4: Deploy to Railway (10 min)

### A. Create Railway Account
```bash
1. Go to railway.app
2. Sign up with GitHub
3. Verify email
```

### B. Create New Project
```bash
1. New Project
2. Deploy from GitHub repo
3. Select your harvest repo
4. Wait for initial build
```

### C. Add Environment Variables

In Railway dashboard → Variables, add:

```bash
# Convex
CONVEX_URL=https://giant-lobster-195.convex.cloud
CONVEX_SITE_URL=https://giant-lobster-195.convex.site

# Redis
REDIS_URL=redis://default:PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135

# Helius
HELIUS_API_KEY_1=key1
HELIUS_API_KEY_2=key2
HELIUS_API_KEY_3=key3

# Groq
GROQ_API_KEY=primary_key
GROQ_API_KEY_BACKUP=backup_key

# Jupiter
JUPITER_API_KEY=your_key

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Solana
SOLANA_NETWORK=devnet  # or mainnet-beta
WALLET_ADDRESS=your_public_key
WALLET_PRIVATE_KEY=your_private_key

# Config
WORKER_ID=worker_1
SCAN_INTERVAL=900
PRICE_CACHE_TTL=600
STRATEGY_CACHE_TTL=300
LOG_LEVEL=WARNING

# Platform
PLATFORM_WALLET=BnepSp5cyDkpszTMfrq3iVEH6cMpiappY2hLxTjjLYyc
MONTHLY_FEE_PERCENTAGE=0.02
```

### D. Deploy
```bash
# Railway auto-deploys after adding variables
# Check logs for:
✅ Worker starting...
✅ Connected to Redis
✅ Connected to Convex
✅ Telegram bot initialized
```

---

## Step 5: Verify Deployment

### Check Railway Logs:
```
Railway Dashboard → Logs

Should see:
✅ Worker worker_1 starting...
✅ Connected to Redis
✅ Convex client initialized
✅ Telegram bot started
✅ Starting scan loop
```

### Test Telegram:
```bash
# Send to your bot:
/start

# Should receive:
🌾 Harvest Bot Started!
💰 Balance: X.XX SOL
🌐 Network: devnet
```

### Check Redis:
```bash
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          KEYS '*'

# Should see:
worker_heartbeat:worker_1
price:SOL
...
```

### Check Convex:
```bash
# In Convex dashboard:
# Should see users table with data
```

---

## Cost Breakdown

### Month 1 (Railway Free):
```
Railway:        $0 (500 hrs free)
Convex:         $0 (free tier)
Redis:          $0 (free tier)
Helius:         $0 (free tier)
Groq:           $0 (free tier)
Telegram:       $0 (free)
─────────────────────────────
Total:          $0 ✅
```

### Month 2+ (Railway Paid):
```
Railway:        $5/month
Everything else: $0
─────────────────────────────
Total:          $5/month
```

### After Moving to Hetzner:
```
Hetzner:        $16/month (CPX31)
Everything else: $0
─────────────────────────────
Total:          $16/month
Savings:        $0 (Railway was $5)
```

---

## Migration Path

### Month 1: Railway Free
```
Cost: $0
Users: 50-100
Revenue: $10-20
Action: Bootstrap, test, optimize
```

### Month 2: Railway Paid
```
Cost: $5
Users: 100-200
Revenue: $20-40
Action: Collect fees, prepare migration
```

### Month 3: Move to Hetzner
```
Cost: $16
Users: 200-500
Revenue: $40-100
Action: Scale, become profitable
```

---

## Advantages of This Setup

### 1. Convex > PostgreSQL
```
✅ No migrations
✅ Real-time sync
✅ Serverless
✅ Free tier
✅ TypeScript SDK
```

### 2. Redis for Speed
```
✅ Cache prices
✅ Cache strategies
✅ Worker coordination
✅ 30MB free
```

### 3. Bot Only
```
✅ No website hosting
✅ Cheaper
✅ Simpler
✅ Easy to migrate
```

### 4. Easy Migration
```
✅ Same code works on Hetzner
✅ Just change deployment
✅ No code changes needed
```

---

## Troubleshooting

### "Cannot connect to Convex"
```bash
# Check URL is correct
curl https://giant-lobster-195.convex.cloud

# Check Convex dashboard
# Verify project is active
```

### "Redis connection failed"
```bash
# Test connection
redis-cli -h redis-18135... -a PASSWORD ping

# Check password
# Check URL format
```

### "Telegram bot not responding"
```bash
# Check token is correct
# Check bot is started
# Send /start first
```

---

## Next Steps

1. ✅ Set up Telegram bot (2 min)
2. ✅ Generate Solana wallet (5 min)
3. ✅ Deploy to Railway (10 min)
4. ✅ Test everything (5 min)
5. ✅ Onboard first users (ongoing)
6. ⏳ Collect fees for 2 months
7. ⏳ Migrate to Hetzner (month 3)

**Total setup: ~22 minutes**
**Cost: $0 first month, $5 second month**

---

## You're Ready!

What you have:
- ✅ Convex database
- ✅ Redis cache
- ✅ All APIs configured
- ✅ Code ready

What you need:
- ⏳ Telegram bot (2 min)
- ⏳ Solana wallet (5 min)
- ⏳ Deploy to Railway (10 min)

**17 minutes to production! 🚀**
