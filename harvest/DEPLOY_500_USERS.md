# 🚀 Deploy for 500 Users

Complete guide to deploying Harvest for 500+ concurrent users.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│                  (Railway / Cloudflare)                 │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
   │Worker 1│  │Worker 2│  │Worker N│
   │50 users│  │50 users│  │50 users│
   └────┬───┘  └────┬───┘  └────┬───┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼────┐  ┌───▼────┐  ┌───▼────┐
   │  Redis  │  │Postgres│  │Telegram│
   │  Cache  │  │   DB   │  │   Bot  │
   └─────────┘  └────────┘  └────────┘
```

---

## Option 1: Railway Deployment (Recommended)

### Cost: ~$150-200/month for 500 users

### Step 1: Set Up Services

#### 1.1 Deploy Redis
```bash
# On Railway dashboard
1. New Project → Add Service → Redis
2. Note the REDIS_URL (e.g., redis://default:password@host:6379)
```

#### 1.2 Deploy PostgreSQL
```bash
# On Railway dashboard
1. Add Service → PostgreSQL
2. Note the DATABASE_URL
```

#### 1.3 Deploy Worker Manager
```bash
# Clone repo
git clone your-repo
cd harvest

# Create railway.toml for manager
cat > railway.toml << EOF
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "python -m agent.distributed.worker_manager"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
EOF

# Deploy
railway up
```

### Step 2: Configure Environment Variables

Add these in Railway dashboard (Settings → Variables):

```bash
# Redis & Database
REDIS_URL=redis://default:password@host:6379
DATABASE_URL=postgresql://user:pass@host:5432/harvest

# Worker Configuration
NUM_WORKERS=10
USERS_PER_WORKER=50

# Solana & APIs
SOLANA_NETWORK=mainnet-beta
GROQ_API_KEY=your_groq_key

# Helius API Keys (need 10+ for 500 users)
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

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Optimization
SCAN_INTERVAL=600  # 10 minutes for 500 users
PRICE_CACHE_TTL=180  # 3 minutes
STRATEGY_CACHE_TTL=90  # 90 seconds
RPC_BATCH_SIZE=10
SCAN_STAGGER_WINDOW=120  # 2 minutes
```

### Step 3: Scale Workers

```bash
# In Railway dashboard
Settings → Scaling
- Instances: 10 (one per worker)
- RAM per instance: 2GB
- vCPU per instance: 2

Total: 20GB RAM, 20 vCPU
```

### Step 4: Monitor

```bash
# Check logs
railway logs

# Check Redis
redis-cli -u $REDIS_URL
> KEYS worker_heartbeat:*
> GET worker_heartbeat:worker_1

# Check active workers
> KEYS user_assignment:*
```

---

## Option 2: Docker Compose (Self-Hosted)

### Cost: ~$50-100/month on DigitalOcean/AWS

### Step 1: Provision Server

```bash
# DigitalOcean Droplet or AWS EC2
- 32GB RAM
- 8 vCPU
- 100GB SSD
- Ubuntu 22.04

Cost: ~$80/month on DigitalOcean
```

### Step 2: Install Docker

```bash
# SSH into server
ssh root@your-server

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt-get install docker-compose-plugin
```

### Step 3: Deploy

```bash
# Clone repo
git clone your-repo
cd harvest

# Create .env file
cat > .env << EOF
POSTGRES_PASSWORD=secure_password_here
NUM_WORKERS=10
USERS_PER_WORKER=50
SOLANA_NETWORK=mainnet-beta
GROQ_API_KEY=your_groq_key
TELEGRAM_BOT_TOKEN=your_bot_token
HELIUS_API_KEY_1=key1
HELIUS_API_KEY_2=key2
# ... add all 10 keys
SCAN_INTERVAL=600
EOF

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f manager
```

### Step 4: Monitor

```bash
# Check logs
docker-compose logs -f

# Check Redis
docker-compose exec redis redis-cli
> KEYS worker_heartbeat:*

# Check Postgres
docker-compose exec postgres psql -U harvest
> SELECT COUNT(*) FROM users;

# Access Grafana
http://your-server:3000
```

---

## Option 3: Kubernetes (Production Scale)

### Cost: ~$200-500/month on GKE/EKS

For 1000+ users, use Kubernetes for auto-scaling.

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: harvest-workers
spec:
  replicas: 10
  selector:
    matchLabels:
      app: harvest-worker
  template:
    metadata:
      labels:
        app: harvest-worker
    spec:
      containers:
      - name: worker
        image: your-registry/harvest:latest
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: harvest-secrets
              key: redis-url
        resources:
          requests:
            memory: "2Gi"
            cpu: "2"
          limits:
            memory: "4Gi"
            cpu: "4"
```

---

## API Key Requirements

### For 500 Users:

```
API calls per user per day:
- Scans: 144 (every 10 min)
- API calls per scan: ~7
- Total per user: ~1,000 calls/day

500 users × 1,000 calls = 500,000 calls/day

Helius free tier: 3,300 calls/day per key
Keys needed: 500,000 / 3,300 = ~152 keys

SOLUTION: Use Helius paid tier
- $50/month = 1M calls/month (~33k/day)
- Need ~15 paid keys = $750/month
```

### Alternative: Optimize API Usage

```bash
# Reduce API calls by 70%
SCAN_INTERVAL=600  # 10 min instead of 5 min
PRICE_CACHE_TTL=300  # 5 min cache
STRATEGY_CACHE_TTL=180  # 3 min cache

New calls per user: ~300/day
500 users × 300 = 150,000 calls/day
Keys needed: 150,000 / 3,300 = ~45 free keys

OR: 5 paid keys ($250/month)
```

---

## Cost Breakdown

### Railway (Recommended for Simplicity)

```
Workers (10 × 2GB):     $120/month
Redis (512MB):          $10/month
PostgreSQL (2GB):       $20/month
Helius API (5 paid):    $250/month
─────────────────────────────────
Total:                  $400/month
Per user:               $0.80/month
```

### Self-Hosted (Cheapest)

```
DigitalOcean Droplet:   $80/month
Helius API (5 paid):    $250/month
─────────────────────────────────
Total:                  $330/month
Per user:               $0.66/month
```

### Kubernetes (Most Scalable)

```
GKE Cluster:            $200/month
Helius API (10 paid):   $500/month
Monitoring:             $50/month
─────────────────────────────────
Total:                  $750/month
Per user:               $1.50/month
```

---

## Performance Tuning

### For 500 Users:

```bash
# Scan Configuration
SCAN_INTERVAL=600  # 10 minutes (reduce API load)
MIN_SCAN_INTERVAL=60  # 1 minute minimum
SCAN_STAGGER_WINDOW=180  # 3 minutes (spread load)

# Caching (aggressive)
PRICE_CACHE_TTL=300  # 5 minutes
STRATEGY_CACHE_TTL=180  # 3 minutes

# Batching
RPC_BATCH_SIZE=20  # Process 20 users at once

# Workers
NUM_WORKERS=10
USERS_PER_WORKER=50

# Memory Optimization
MAX_CONVERSATION_HISTORY=10  # Reduce from 50
LOG_LEVEL=WARNING  # Less verbose logging
```

---

## Monitoring & Alerts

### Key Metrics to Track:

1. **Worker Health**
   - Active workers count
   - Heartbeat status
   - Crash rate

2. **API Usage**
   - Calls per key per day
   - Rate limit hits
   - Failed requests

3. **Performance**
   - Scan cycle duration
   - Trade execution time
   - Queue depth

4. **Business Metrics**
   - Active users
   - Trades per day
   - Total profit
   - Win rate

### Set Up Alerts:

```python
# In worker_manager.py
if active_workers < num_workers * 0.8:
    send_alert("80% of workers down!")

if api_usage > daily_limit * 0.9:
    send_alert("API usage at 90%!")

if queue_depth > 1000:
    send_alert("Job queue backing up!")
```

---

## Scaling Beyond 500 Users

### 1000 Users:
```
Workers: 20 × 2GB = 40GB RAM
Cost: ~$600-800/month
```

### 5000 Users:
```
Workers: 100 × 2GB = 200GB RAM
Use Kubernetes auto-scaling
Cost: ~$2000-3000/month
```

### 10000+ Users:
```
Multi-region deployment
CDN for static assets
Dedicated RPC nodes
Cost: ~$5000+/month
```

---

## Troubleshooting

### Workers Not Starting
```bash
# Check logs
docker-compose logs manager

# Check Redis connection
redis-cli -u $REDIS_URL ping

# Check environment variables
docker-compose exec manager env | grep REDIS
```

### High Memory Usage
```bash
# Reduce conversation history
MAX_CONVERSATION_HISTORY=5

# Increase cache TTL
PRICE_CACHE_TTL=600

# Reduce workers
NUM_WORKERS=8
```

### API Rate Limits
```bash
# Add more keys
HELIUS_API_KEY_11=new_key

# Increase scan interval
SCAN_INTERVAL=900  # 15 minutes

# Increase cache TTL
PRICE_CACHE_TTL=600
```

---

## Quick Start Commands

### Railway:
```bash
railway login
railway init
railway up
railway logs
```

### Docker Compose:
```bash
docker-compose up -d
docker-compose ps
docker-compose logs -f
docker-compose down
```

### Kubernetes:
```bash
kubectl apply -f k8s/
kubectl get pods
kubectl logs -f deployment/harvest-workers
kubectl scale deployment/harvest-workers --replicas=20
```

---

## Success Checklist

- [ ] Redis deployed and accessible
- [ ] PostgreSQL deployed and migrated
- [ ] 10+ Helius API keys configured
- [ ] Worker manager running
- [ ] All 10 workers spawned
- [ ] Users assigned to workers
- [ ] Heartbeats showing in Redis
- [ ] First scans completing
- [ ] Telegram notifications working
- [ ] Monitoring dashboard set up
- [ ] Alerts configured
- [ ] Backup strategy in place

---

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Check Redis: `redis-cli -u $REDIS_URL`
3. Check workers: `KEYS worker_heartbeat:*`
4. Open GitHub issue with logs

---

**You're ready to serve 500 users! 🚀**

Start with 50 users, monitor for a week, then scale up gradually.
