# 🔴 Redis Cloud Setup Guide

## Your Redis Details

```
Endpoint: redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135
Region: US East (AWS)
Size: 30 MB
Network: 5 GB/month
Eviction: volatile-lru ✅ (Good for cache)
Persistence: None (OK for cache)
```

---

## Step 1: Get Redis Password

1. Go to Redis Cloud dashboard
2. Click on your database
3. Click "Security" tab
4. Copy the default user password
5. Save it securely

---

## Step 2: Test Connection

```bash
# Install redis-cli (if not installed)
brew install redis  # macOS
# or
apt install redis-tools  # Linux

# Test connection
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          ping

# Should return: PONG
```

---

## Step 3: Configure Connection URL

### Format:
```
redis://default:PASSWORD@HOST:PORT
```

### Your URL:
```bash
REDIS_URL=redis://default:YOUR_PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135
```

**Replace `YOUR_PASSWORD` with actual password!**

---

## Step 4: Add to Railway

### In Railway Dashboard:

1. Go to your service
2. Click "Variables" tab
3. Add new variable:
   - Key: `REDIS_URL`
   - Value: `redis://default:YOUR_PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135`
4. Click "Add"
5. Service will restart automatically

---

## Step 5: Verify It Works

### Test with Python:

```python
import redis
import os

# Connect
r = redis.from_url(os.getenv("REDIS_URL"))

# Test
r.set("test", "hello")
print(r.get("test"))  # Should print: b'hello'

# Check memory
info = r.info("memory")
print(f"Used memory: {info['used_memory_human']}")
```

### Test with your app:

```bash
# In Railway logs, you should see:
✅ Connected to Redis
✅ Shared Price Cache initialized
✅ Strategy Cache initialized
```

---

## Redis Usage Optimization

### Your Limits:
- **Memory:** 30 MB (1.6 MB used currently)
- **Network:** 5 GB/month
- **Eviction:** volatile-lru (removes old cached items)

### How to Stay Under Limits:

#### 1. Aggressive Cache TTLs
```bash
PRICE_CACHE_TTL=600      # 10 minutes (not 60s)
STRATEGY_CACHE_TTL=300   # 5 minutes (not 30s)
```

#### 2. Limit Cache Size
```python
# In redis_cache.py, add max keys limit
MAX_PRICE_CACHE_KEYS = 100
MAX_STRATEGY_CACHE_KEYS = 50
```

#### 3. Monitor Usage
```bash
# Check memory usage
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          INFO memory

# Check key count
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          DBSIZE
```

---

## What Gets Cached

### Price Cache (~10 KB per token):
```
price:SOL → 150.50
price:USDC → 1.00
price:BONK → 0.00001234
...
```

### Strategy Cache (~5 KB per entry):
```
strategy:jupiter_swap:opportunities → [...]
strategy:marinade_stake:apy → 7.2
...
```

### API Usage Tracking (~1 KB per key):
```
api_usage:key1:2024-02-13 → 1234
api_usage:key2:2024-02-13 → 567
...
```

### User Assignments (~100 bytes per user):
```
user_assignment:user_1 → worker_1
user_assignment:user_2 → worker_1
...
```

### Worker Heartbeats (~100 bytes per worker):
```
worker_heartbeat:worker_1 → 2024-02-13T14:23:45
worker_heartbeat:worker_2 → 2024-02-13T14:23:46
...
```

---

## Estimated Usage (100 Users)

```
Price cache (50 tokens):        500 KB
Strategy cache (10 strategies): 50 KB
API usage (10 keys):            10 KB
User assignments (100 users):   10 KB
Worker heartbeats (2 workers):  1 KB
Misc overhead:                  100 KB
─────────────────────────────────────
Total:                          ~671 KB

Available: 30 MB
Used: 671 KB (2.2%)
Remaining: 29.3 MB ✅
```

**You have plenty of room!**

---

## Monitoring Redis

### Check Usage:

```bash
# Memory usage
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          INFO memory | grep used_memory_human

# Key count
redis-cli -h redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com \
          -p 18135 \
          -a YOUR_PASSWORD \
          DBSIZE

# Network usage
# Check in Redis Cloud dashboard
```

### Set Up Alerts:

In Redis Cloud dashboard:
1. Go to "Alerts" tab
2. Set alert for:
   - Memory usage > 25 MB (83%)
   - Network usage > 4 GB (80%)
3. Add your email

---

## Troubleshooting

### "Connection refused"
```bash
# Check if Redis is accessible
ping redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com

# Check port
telnet redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com 18135
```

### "Authentication failed"
```bash
# Check password in Redis Cloud dashboard
# Make sure no spaces in password
# Try connecting with redis-cli first
```

### "Out of memory"
```bash
# Check current usage
redis-cli INFO memory

# Clear cache if needed
redis-cli FLUSHDB

# Increase cache TTLs
PRICE_CACHE_TTL=1200  # 20 minutes
```

### "Network limit exceeded"
```bash
# Check usage in dashboard
# Reduce scan frequency
SCAN_INTERVAL=1800  # 30 minutes

# Increase cache TTLs
PRICE_CACHE_TTL=1200
```

---

## Redis Commands Reference

### Check what's cached:

```bash
# List all keys
redis-cli KEYS '*'

# Get specific value
redis-cli GET price:SOL

# Check TTL
redis-cli TTL price:SOL

# Delete key
redis-cli DEL price:SOL

# Clear all cache
redis-cli FLUSHDB
```

### Monitor in real-time:

```bash
# Watch commands
redis-cli MONITOR

# Watch memory
watch -n 1 'redis-cli INFO memory | grep used_memory_human'
```

---

## Security Best Practices

1. **Never commit password to git**
   ```bash
   # Add to .gitignore
   echo ".env*" >> .gitignore
   ```

2. **Use environment variables**
   ```bash
   # In Railway, not in code
   REDIS_URL=redis://...
   ```

3. **Rotate password monthly**
   ```bash
   # In Redis Cloud dashboard
   Security → Change Password
   ```

4. **Enable TLS (if available)**
   ```bash
   # Check if your plan supports TLS
   # Use rediss:// instead of redis://
   ```

---

## Upgrade Path

### When to Upgrade:

- Memory usage > 25 MB consistently
- Network usage > 4 GB/month
- Need persistence (data survives restarts)
- Need high availability (99.99% uptime)

### Next Tier:

```
Redis Cloud 100MB: $10/month
- 100 MB memory
- 10 GB network
- Data persistence
- High availability
```

---

## Quick Setup Checklist

- [ ] Get Redis password from dashboard
- [ ] Test connection with redis-cli
- [ ] Create REDIS_URL with password
- [ ] Add to Railway environment variables
- [ ] Deploy and check logs
- [ ] Verify cache is working
- [ ] Set up monitoring alerts
- [ ] Monitor usage for 24 hours

---

## Your Redis is Ready! 🚀

Connection URL:
```
redis://default:YOUR_PASSWORD@redis-18135.c8.us-east-1-3.ec2.cloud.redislabs.com:18135
```

Add this to Railway and you're good to go!
