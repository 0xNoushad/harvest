# ✅ Railway Free Tier Setup Checklist

Complete this checklist to deploy Harvest on Railway for FREE!

---

## Prerequisites

- [ ] GitHub account
- [ ] Railway account (sign up at railway.app)
- [ ] Redis Cloud account (sign up at redis.com/try-free)
- [ ] Supabase account (sign up at supabase.com)
- [ ] 10 Gmail accounts (for Helius keys)

---

## Step 1: Set Up Redis Cloud ✅ DONE

- [x] Sign up at redis.com/try-free
- [x] Create database
- [x] Note endpoint: `redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135`
- [ ] Get password from Security tab
- [ ] Test connection:
  ```bash
  python scripts/test_redis.py --redis-url 'redis://default:PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135'
  ```

---

## Step 2: Set Up Supabase

- [ ] Go to supabase.com
- [ ] Create new project
- [ ] Wait for database to provision (~2 minutes)
- [ ] Go to Settings → Database
- [ ] Copy connection string (starts with `postgresql://`)
- [ ] Save as `DATABASE_URL`

---

## Step 3: Get Helius API Keys

Create 3 Gmail accounts using the + trick:
```
yourname+helius1@gmail.com
yourname+helius2@gmail.com
yourname+helius3@gmail.com
```

For each account:
- [ ] Go to helius.dev
- [ ] Sign up with email
- [ ] Verify email
- [ ] Copy API key
- [ ] Save as `HELIUS_API_KEY_1`, `HELIUS_API_KEY_2`, `HELIUS_API_KEY_3`

**Note:** 3 keys = 3M credits/month. Enough for 500-700 users! 🚀

---

## Step 4: Get Groq API Key

- [ ] Go to console.groq.com
- [ ] Sign up (free, no credit card)
- [ ] Go to API Keys
- [ ] Create new key
- [ ] Save as `GROQ_API_KEY`

---

## Step 5: Set Up Telegram Bot

- [ ] Open Telegram
- [ ] Search for @BotFather
- [ ] Send `/newbot`
- [ ] Follow instructions
- [ ] Copy bot token
- [ ] Save as `TELEGRAM_BOT_TOKEN`

Get your chat ID:
- [ ] Start chat with your bot
- [ ] Run: `python scripts/get_chat_id.py`
- [ ] Save as `TELEGRAM_CHAT_ID`

---

## Step 6: Push Code to GitHub

- [ ] Create new GitHub repo
- [ ] Add remote:
  ```bash
  git remote add origin https://github.com/YOUR_USERNAME/harvest.git
  ```
- [ ] Push code:
  ```bash
  git add .
  git commit -m "Initial commit"
  git push -u origin main
  ```

---

## Step 7: Deploy to Railway

### Connect GitHub:
- [ ] Go to railway.app
- [ ] Click "New Project"
- [ ] Select "Deploy from GitHub repo"
- [ ] Authorize GitHub
- [ ] Select your harvest repo

### Configure Service:
- [ ] Railway creates service automatically
- [ ] Wait for initial build (~2 minutes)

---

## Step 8: Add Environment Variables

In Railway dashboard, go to Variables tab and add:

### Infrastructure:
- [ ] `REDIS_URL` = `redis://default:YOUR_PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135`
- [ ] `DATABASE_URL` = `postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres`

### Worker Config:
- [ ] `WORKER_ID` = `worker_1`
- [ ] `NUM_USERS` = `50`

### Optimization:
- [ ] `SCAN_INTERVAL` = `900`
- [ ] `PRICE_CACHE_TTL` = `600`
- [ ] `STRATEGY_CACHE_TTL` = `300`
- [ ] `LOG_LEVEL` = `WARNING`

### APIs:
- [ ] `SOLANA_NETWORK` = `mainnet-beta`
- [ ] `GROQ_API_KEY` = `your_groq_key`
- [ ] `TELEGRAM_BOT_TOKEN` = `your_bot_token`
- [ ] `TELEGRAM_CHAT_ID` = `your_chat_id`

### Helius Keys (3 to start):
- [ ] `HELIUS_API_KEY_1` = `key1`
- [ ] `HELIUS_API_KEY_2` = `key2`
- [ ] `HELIUS_API_KEY_3` = `key3`

(Add more later if you scale past 100 users)

### Platform:
- [ ] `PLATFORM_WALLET` = `BnepSp5cyDkpszTMfrq3iVEH6cMpiappY2hLxTjjLYyc`
- [ ] `MONTHLY_FEE_PERCENTAGE` = `0.02`

---

## Step 9: Deploy

- [ ] Railway redeploys automatically after adding variables
- [ ] Wait for deployment (~2 minutes)
- [ ] Check logs for errors

---

## Step 10: Verify Deployment

### Check Logs:
```
Railway Dashboard → Logs

Should see:
✅ Worker worker_1 starting...
✅ Health server started on port 8080
✅ Connected to Redis
✅ Initialized loops for 50 users
✅ Starting scan loop for user_1
```

### Test Redis:
```bash
# Locally
export REDIS_URL='redis://default:PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135'
python scripts/test_redis.py
```

### Test Telegram:
- [ ] Send `/start` to your bot
- [ ] Should receive welcome message

---

## Step 11: Monitor

### First Hour:
- [ ] Watch Railway logs
- [ ] Check Redis memory usage (should be < 5 MB)
- [ ] Check Supabase database (should have users table)
- [ ] Verify Telegram notifications working

### First Day:
- [ ] Check error rate (should be < 5%)
- [ ] Monitor API usage (should be < 3,300/day per key)
- [ ] Verify trades executing
- [ ] Check user onboarding works

---

## Step 12: Set Up Monitoring

### Redis Cloud Alerts:
- [ ] Go to Redis Cloud dashboard
- [ ] Alerts tab
- [ ] Add alert: Memory > 25 MB
- [ ] Add alert: Network > 4 GB

### Railway Alerts:
- [ ] Go to Railway dashboard
- [ ] Settings → Notifications
- [ ] Enable deployment notifications
- [ ] Add your email

---

## Troubleshooting

### "Cannot connect to Redis"
```bash
# Test connection
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          ping

# Check password has no spaces
# Check URL format is correct
```

### "Database connection failed"
```bash
# Test Supabase connection
psql "postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres"

# Check password is correct
# Check project is not paused
```

### "Worker not starting"
```bash
# Check Railway logs
# Look for error messages
# Verify all environment variables are set
# Check Docker build succeeded
```

---

## Cost Tracking

### Free Tier Limits:

| Service | Limit | Current | Status |
|---------|-------|---------|--------|
| Railway | 500 hrs/month | 0 | ✅ |
| Redis | 30 MB | 1.6 MB | ✅ |
| Redis Network | 5 GB/month | 0 | ✅ |
| Supabase | 500 MB | 0 | ✅ |
| Helius (3 keys) | 3M credits/month | 0 | ✅ |

**With 3 keys, you can handle 500-700 users! 🚀**

### Monitor Daily:
- [ ] Railway hours used
- [ ] Redis memory used
- [ ] Redis network used
- [ ] Supabase database size
- [ ] Helius API calls

---

## Success Criteria

After 24 hours, you should have:

- [ ] ✅ Bot running on Railway
- [ ] ✅ Redis connected and caching
- [ ] ✅ Database storing user data
- [ ] ✅ Telegram bot responding
- [ ] ✅ 0-10 users onboarded
- [ ] ✅ First trades executed
- [ ] ✅ Error rate < 5%
- [ ] ✅ All within free tier limits
- [ ] ✅ $0 spent

---

## Next Steps

### Week 1:
- [ ] Onboard 10 users
- [ ] Monitor performance
- [ ] Optimize if needed
- [ ] Collect first fees

### Month 1:
- [ ] Scale to 100 users
- [ ] Collect $2-20 in fees
- [ ] Stay on free tier
- [ ] Plan upgrade path

### Month 3:
- [ ] Migrate to Hetzner ($16/month)
- [ ] Scale to 500 users
- [ ] Use collected fees to pay hosting
- [ ] Become profitable

---

## Support

- Setup issues: Check `QUICKSTART_FREE.md`
- Redis issues: Check `SETUP_REDIS_CLOUD.md`
- Deployment issues: Check `DEPLOYMENT_STRATEGY.md`
- Scaling: Check `SCALING_GUIDE.md`

---

## You're Ready! 🚀

Your Redis is set up ✅
Now complete the rest of the checklist and deploy!

Total time: ~30 minutes
Total cost: $0
