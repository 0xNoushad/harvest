# 🆓 Bootstrap on Free Tier - $0 for First Month

## The Problem
You need to serve users but have no money upfront. Solution: **100% FREE infrastructure** until you collect enough fees to pay for hosting.

---

## Free Tier Stack (100-200 Users)

### Infrastructure: **$0/month**

```
Railway Hobby:      $5 credit (free trial)
Redis Cloud:        30MB free tier
Supabase:           500MB PostgreSQL free
Cloudflare:         Free CDN/DNS
Render:             750 hours/month free
```

### API Keys: **$0/month**

```
Helius:             10 free accounts × 3,300 calls/day = 33k/day
Groq:               Free tier (14,400 requests/day)
```

### Total Cost: **$0** ✅

---

## Architecture for Free Tier

```
┌─────────────────────────────────────┐
│   Render (Free 750 hrs/month)      │
│   - 2 workers × 512MB               │
│   - 50 users per worker             │
│   - 100 users total                 │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼────┐ ┌──▼─────┐ ┌──▼──────┐
│ Redis  │ │Supabase│ │Telegram │
│ Cloud  │ │  Free  │ │   Bot   │
│  30MB  │ │ 500MB  │ │  Free   │
└────────┘ └────────┘ └─────────┘
```

---

## Step-by-Step Setup

### 1. Redis Cloud (Free 30MB)

```bash
# Sign up at redis.com/try-free
1. Create account (no credit card)
2. Create database
3. Copy connection URL
```

### 2. Supabase (Free PostgreSQL)

```bash
# Sign up at supabase.com
1. Create project (no credit card)
2. Get connection string from Settings → Database
3. Copy postgres:// URL
```

### 3. Helius API Keys (10 Free Accounts)

```bash
# Create 10 Gmail accounts
user+helius1@gmail.com
user+helius2@gmail.com
...
user+helius10@gmail.com

# Sign up each at helius.dev
# Get 10 API keys = 33k calls/day
```

### 4. Deploy on Render (Free)

```bash
# Sign up at render.com
1. Connect GitHub repo
2. Create Web Service
3. Select "Free" plan
4. Add environment variables
5. Deploy
```


---

## Render Configuration

### render.yaml (Free Tier)

```yaml
services:
  # Worker 1 (50 users)
  - type: web
    name: harvest-worker-1
    env: docker
    plan: free  # 750 hours/month
    dockerfilePath: ./Dockerfile
    envVars:
      - key: WORKER_ID
        value: worker_1
      - key: REDIS_URL
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: NUM_USERS
        value: 50
      - key: SCAN_INTERVAL
        value: 900  # 15 min to save API calls
      - key: PRICE_CACHE_TTL
        value: 600  # 10 min cache
      - key: HELIUS_API_KEY_1
        sync: false
      - key: HELIUS_API_KEY_2
        sync: false
      - key: HELIUS_API_KEY_3
        sync: false
      - key: HELIUS_API_KEY_4
        sync: false
      - key: HELIUS_API_KEY_5
        sync: false

  # Worker 2 (50 users)
  - type: web
    name: harvest-worker-2
    env: docker
    plan: free
    dockerfilePath: ./Dockerfile
    envVars:
      - key: WORKER_ID
        value: worker_2
      - key: REDIS_URL
        sync: false
      - key: DATABASE_URL
        sync: false
      - key: NUM_USERS
        value: 50
      - key: SCAN_INTERVAL
        value: 900
      - key: HELIUS_API_KEY_6
        sync: false
      - key: HELIUS_API_KEY_7
        sync: false
      - key: HELIUS_API_KEY_8
        sync: false
      - key: HELIUS_API_KEY_9
        sync: false
      - key: HELIUS_API_KEY_10
        sync: false
```

---

## Optimization for Free Tier

### Aggressive Settings to Stay Under Limits

```bash
# Scan less frequently
SCAN_INTERVAL=900  # 15 minutes (vs 5 min)

# Cache aggressively
PRICE_CACHE_TTL=600  # 10 minutes
STRATEGY_CACHE_TTL=300  # 5 minutes

# Reduce memory usage
MAX_CONVERSATION_HISTORY=5  # Keep only 5 messages
LOG_LEVEL=WARNING  # Less logging

# Batch more users
RPC_BATCH_SIZE=25  # Process 25 at once

# Stagger scans
SCAN_STAGGER_WINDOW=300  # 5 minute window
```

### API Usage Calculation

```
100 users × 96 scans/day × 5 calls = 48,000 calls/day
10 Helius keys × 3,300 calls = 33,000 calls/day

❌ Not enough! Need to optimize more:

100 users × 48 scans/day × 5 calls = 24,000 calls/day
With caching: 24,000 × 0.3 = 7,200 calls/day

✅ Fits in 10 free keys!
```

---

## Revenue Model (Bootstrap to Paid)

### Month 1: Free Tier (100 users)

```
Revenue:
- 100 users × $1 profit/month × 2% fee = $2/month
- Not enough to pay for hosting yet

Strategy: Stay on free tier, grow users
```

### Month 2: Collect Fees (200 users)

```
Revenue:
- 200 users × $5 profit/month × 2% fee = $20/month
- Still not enough for paid hosting

Strategy: Keep optimizing, grow to 500 users
```

### Month 3: Upgrade (500 users)

```
Revenue:
- 500 users × $10 profit/month × 2% fee = $100/month
- Enough to pay for $60-80 hosting!

Strategy: Upgrade to paid tier, scale to 1000 users
```

### Month 4+: Profitable

```
Revenue:
- 1000 users × $20 profit/month × 2% fee = $400/month
- Hosting cost: $150/month
- Net profit: $250/month

Strategy: Scale to 5000+ users
```

---

## Free Tier Limits

### Render Free Plan:
- 750 hours/month per service
- 512MB RAM
- Sleeps after 15 min inactivity
- 2 services = 1500 hours total

**Solution:** Keep-alive ping every 10 minutes

### Redis Cloud Free:
- 30MB storage
- 30 connections
- No persistence

**Solution:** Use only for cache, not persistent data

### Supabase Free:
- 500MB database
- 2GB bandwidth/month
- Paused after 1 week inactivity

**Solution:** Keep-alive query every 6 days

---

## Keep-Alive Script

```python
# scripts/keep_alive.py
import asyncio
import aiohttp
import os

async def keep_alive():
    """Ping services to prevent sleep."""
    urls = [
        os.getenv("WORKER_1_URL"),
        os.getenv("WORKER_2_URL"),
    ]
    
    while True:
        for url in urls:
            try:
                async with aiohttp.ClientSession() as session:
                    await session.get(f"{url}/health")
                print(f"✓ Pinged {url}")
            except Exception as e:
                print(f"✗ Failed to ping {url}: {e}")
        
        # Wait 10 minutes
        await asyncio.sleep(600)

if __name__ == "__main__":
    asyncio.run(keep_alive())
```

Run this on a free cron service like cron-job.org

---

## Migration Path

### Phase 1: Bootstrap (Month 1)
- Deploy on free tier
- 100 users
- $0 cost
- Collect first fees

### Phase 2: Grow (Month 2-3)
- Stay on free tier
- Scale to 200-300 users
- Optimize aggressively
- Build revenue

### Phase 3: Upgrade (Month 3-4)
- Migrate to paid tier
- Scale to 500-1000 users
- Use collected fees to pay
- Become profitable

---

## Quick Deploy (Free Tier)

```bash
# 1. Sign up for free services
- Render.com (no credit card)
- Redis Cloud (no credit card)
- Supabase (no credit card)

# 2. Get 10 Helius keys
- Create 10 Gmail accounts
- Sign up at helius.dev
- Copy all API keys

# 3. Deploy on Render
git push origin main
# Render auto-deploys from GitHub

# 4. Set environment variables
# In Render dashboard, add all keys

# 5. Monitor
# Check Render logs
# Check Redis usage
# Check Supabase usage
```

---

## Cost Comparison

### Free Tier (100 users):
```
Infrastructure:     $0
API keys:           $0
Total:              $0
Revenue:            $2-20/month
Net:                +$2-20/month ✅
```

### Paid Tier (500 users):
```
Infrastructure:     $60
API keys:           $50
Total:              $110
Revenue:            $100-200/month
Net:                -$10 to +$90/month
```

### Profitable (1000 users):
```
Infrastructure:     $150
API keys:           $100
Total:              $250
Revenue:            $400-800/month
Net:                +$150-550/month ✅
```

---

## Success Metrics

### Week 1:
- [ ] Deploy on free tier
- [ ] 10 users onboarded
- [ ] First trades executed
- [ ] $0 spent ✅

### Month 1:
- [ ] 100 users active
- [ ] $2-20 fees collected
- [ ] Still on free tier
- [ ] $0 spent ✅

### Month 3:
- [ ] 500 users active
- [ ] $100-200 fees collected
- [ ] Upgrade to paid tier
- [ ] Profitable ✅

---

## Bottom Line

**Start with $0, bootstrap to profitability:**

1. Deploy on 100% free tier
2. Onboard 100 users
3. Collect 2% fees for 2-3 months
4. Use collected fees to upgrade
5. Scale to 1000+ users
6. Become profitable

**No money needed upfront!** 🚀
