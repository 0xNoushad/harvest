# 📊 API Usage Calculator

## Helius Free Tier: 1M Credits/Month!

### What You Get (Per Key):
- **1,000,000 credits/month** (~33,333 credits/day)
- **10 requests/second**
- **1 sendTransaction/second**

**This is WAY more than the old 3,300/day limit!**

---

## The Math (Updated)

### Credits Per Request:
- Basic RPC call: 1 credit
- getProgramAccounts: 10 credits
- getTokenAccounts: 5 credits
- Average per scan: ~5 credits

### Per User Per Day:
```
Scans per day: 96 (every 15 min)
Credits per scan: ~5
Cache hit rate: 70% (with Redis)

Actual credits: 96 × 5 × 0.3 = 144 credits/day per user
```

### Total Credits Needed:

| Users | Credits/Day | Credits/Month | Keys Needed |
|-------|-------------|---------------|-------------|
| 50    | 7,200       | 216,000       | 1 key ✅    |
| 100   | 14,400      | 432,000       | 1 key ✅    |
| 200   | 28,800      | 864,000       | 1 key ✅    |
| 300   | 43,200      | 1,296,000     | 2 keys ✅   |
| 500   | 72,000      | 2,160,000     | 3 keys ✅   |
| 1000  | 144,000     | 4,320,000     | 5 keys      |

**With 3 keys, you can handle 500+ users! 🚀**

---

## Updated Recommendations

### With 1 Helius Key:
```
Credits: 1M/month
Users: 100-200 comfortably
Cost: $0
```

### With 3 Helius Keys:
```
Credits: 3M/month
Users: 500-700 comfortably
Cost: $0
```

### With 5 Helius Keys:
```
Credits: 5M/month
Users: 1000+ comfortably
Cost: $0
```

---

## What This Means for You

### Before (Old Limit):
```
3,300 calls/day per key
3 keys = 9,900 calls/day
Max users: 50-75
```

### Now (New Limit):
```
33,333 credits/day per key
3 keys = 100,000 credits/day
Max users: 500-700! 🎉
```

**You can scale 10x more on free tier!**

---

## Optimization Still Helps

### Without Optimization:
```
Per user: 480 credits/day (no cache)
100 users: 48,000 credits/day
1 key handles: 694 users
```

### With Optimization (70% cache):
```
Per user: 144 credits/day (with cache)
100 users: 14,400 credits/day
1 key handles: 2,314 users!
```

**Optimization = 3x more users per key!**

---

## Rate Limits

### Per Key:
- **10 requests/second** = 600 requests/minute
- **1 sendTransaction/second** = 60 tx/minute

### For 100 Users:
```
Scans: Every 15 minutes
Peak load: 100 users × 5 calls = 500 calls
Time needed: 500 / 10 = 50 seconds

✅ Well under rate limit!
```

### For 500 Users:
```
Peak load: 500 users × 5 calls = 2,500 calls
Time needed: 2,500 / 10 = 250 seconds (4 min)

With 3 keys: 2,500 / 30 = 83 seconds
✅ Still good!
```

---

## Updated Strategy

### Start with 1 Key:
- 0-100 users
- Test and optimize
- $0 cost

### Add 2nd & 3rd Key:
- 100-500 users
- More redundancy
- Still $0 cost

### Add 4-5 Keys:
- 500-1000 users
- Production scale
- Still $0 cost!

---

## Cost Comparison

### Free Tier (3 keys):
```
Cost: $0/month
Credits: 3M/month
Users: 500-700
Revenue: $100-200/month (2% fees)
Net: +$100-200/month 💰
```

### Paid Tier (3 keys):
```
Cost: $150/month ($50 each)
Credits: 15M/month (5M each)
Users: 2000+
Revenue: $400+/month
Net: +$250+/month 💰
```

**Stay on free tier way longer!**

---

## Monitoring

### Check Usage:
```bash
# In Helius dashboard
Dashboard → Usage → Credits Used

# Should see:
Day 1: 7,200 credits (50 users)
Day 30: 216,000 credits total
Remaining: 784,000 credits
```

### Set Alerts:
```bash
# Alert at 80% usage
800,000 / 1M credits used
Time to add another key!
```

---

## Bottom Line

**With 1M credits per key:**

✅ **1 key = 100-200 users**
✅ **3 keys = 500-700 users**
✅ **All FREE!**

**You can bootstrap to profitability without spending a dime! 🚀**

---

## Quick Reference

| Users | Credits/Month | Keys Needed | Cost |
|-------|---------------|-------------|------|
| 50    | 216K          | 1           | $0   |
| 100   | 432K          | 1           | $0   |
| 200   | 864K          | 1           | $0   |
| 300   | 1.3M          | 2           | $0   |
| 500   | 2.2M          | 3           | $0   |
| 1000  | 4.3M          | 5           | $0   |

**Start with 1 key, add more as you grow!**
