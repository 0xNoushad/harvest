# 🚀 Quick Start - Free Tier ($0/month)

Deploy Harvest for 100 users with **ZERO upfront cost**.

---

## 5-Minute Setup

### 1. Sign Up for Free Services (No Credit Card)

**Redis Cloud** (30MB free)
```
1. Go to redis.com/try-free
2. Sign up with email
3. Create database
4. Copy REDIS_URL
```

**Supabase** (500MB PostgreSQL free)
```
1. Go to supabase.com
2. Create project
3. Settings → Database → Copy connection string
4. Save as DATABASE_URL
```

**Render** (750 hours/month free)
```
1. Go to render.com
2. Sign up with GitHub
3. Connect your repo
4. We'll deploy in step 3
```

### 2. Get 10 Free Helius API Keys

```bash
# Create 10 Gmail accounts (use + trick)
yourname+helius1@gmail.com
yourname+helius2@gmail.com
...
yourname+helius10@gmail.com

# Sign up each at helius.dev
# Copy all 10 API keys
```

### 3. Deploy on Render

```bash
# Push code to GitHub
git add .
git commit -m "Ready for free tier deployment"
git push origin main

# On Render dashboard:
1. New → Web Service
2. Connect your GitHub repo
3. Select "Docker" environment
4. Plan: FREE
5. Add environment variables (see below)
6. Create Web Service
```

### 4. Add Environment Variables

In Render dashboard, add these:

```bash
# Infrastructure
REDIS_URL=redis://default:xxx@redis-xxxxx.cloud.redislabs.com:12345
DATABASE_URL=postgresql://postgres:xxx@db.supabase.co:5432/postgres

# Worker
WORKER_ID=worker_1

# Optimization
SCAN_INTERVAL=900
PRICE_CACHE_TTL=600
STRATEGY_CACHE_TTL=300

# APIs
SOLANA_NETWORK=mainnet-beta
GROQ_API_KEY=your_groq_key
TELEGRAM_BOT_TOKEN=your_telegram_token

# Helius Keys (all 10)
HELIUS_API_KEY_1=key1
HELIUS_API_KEY_2=key2
HELIUS_API_KEY_3=key3
HELIUS_API_KEY_4=key4
HELIUS_API_KEY_5=key5
HELIUS_API_KEY_6=key6
HELIUS_API_KEY_7=key7
HELIUS_API_KEY_8=key8
HELIUS_API_KEY_9=key9
HELIUS_API_KEY_10=key10
```

### 5. Deploy Second Worker (Optional)

Repeat step 3 for worker_2:
- Same repo
- Change WORKER_ID=worker_2
- Use HELIUS_API_KEY_6 through 10

---

## Verify Deployment

```bash
# Check Render logs
# Should see:
✓ Worker worker_1 starting...
✓ Health server started on port 8080
✓ Connected to Redis
✓ Initialized loops for 50 users
✓ Starting scan loop for user_1
```

---

## Monitor Usage

### Redis Cloud
```
Dashboard → Database → Metrics
- Memory: Should stay under 30MB
- Connections: Should stay under 30
```

### Supabase
```
Dashboard → Database → Usage
- Database size: Should stay under 500MB
- Bandwidth: Should stay under 2GB/month
```

### Render
```
Dashboard → Service → Metrics
- Hours used: Should stay under 750/month
- Memory: Should stay under 512MB
```

---

## Cost Breakdown

```
Infrastructure:     $0 (free tier)
API keys:           $0 (10 free Helius)
Total:              $0 ✅

Users supported:    100
Revenue potential:  $2-20/month (2% fees)
Net profit:         +$2-20/month
```

---

## When to Upgrade

### Upgrade when:
- Users > 100
- Revenue > $50/month
- Free tier limits hit

### Upgrade to:
- Render Starter: $7/month per worker
- Redis Cloud 100MB: $10/month
- Keep Supabase free (500MB enough)

**Total: ~$25/month for 200 users**

---

## Troubleshooting

### Worker sleeps after 15 min
```
✓ Health server prevents this
✓ Render pings /health endpoint
✓ Worker stays awake
```

### Out of Redis memory
```
Increase cache TTLs:
PRICE_CACHE_TTL=1200  # 20 min
STRATEGY_CACHE_TTL=600  # 10 min
```

### API rate limits
```
Add more Helius accounts:
HELIUS_API_KEY_11=new_key
HELIUS_API_KEY_12=new_key
```

---

## Next Steps

1. **Deploy** - Follow steps above
2. **Onboard** - Add first 10 users
3. **Monitor** - Watch for 1 week
4. **Scale** - Add more users gradually
5. **Collect** - Start earning 2% fees
6. **Upgrade** - When revenue > $50/month

---

**You're live with $0 upfront! 🎉**
