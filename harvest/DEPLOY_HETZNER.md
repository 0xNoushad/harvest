# 🇩🇪 Hetzner Deployment - Best Price/Performance

Deploy Harvest on Hetzner for **maximum cost efficiency**.

---

## Why Hetzner?

### Cost Comparison (500 users):

| Provider | Specs | Cost/Month |
|----------|-------|------------|
| Railway | 20GB RAM, 20 vCPU | $200 |
| DigitalOcean | 32GB RAM, 8 vCPU | $160 |
| **Hetzner** | **32GB RAM, 8 vCPU** | **€40 (~$43)** ✅ |

**Hetzner is 4-5x cheaper!**

---

## Server Options

### Option 1: Single Server (Recommended Start)
**CPX31** - €15.30/month (~$16)
- 4 vCPU
- 8GB RAM
- 160GB SSD
- 20TB traffic

**Good for:** 200-300 users

### Option 2: Dedicated Server (Best Value)
**AX41** - €39/month (~$42)
- AMD Ryzen 5 3600 (6 cores, 12 threads)
- 64GB DDR4 RAM
- 2x 512GB NVMe SSD
- Unlimited traffic

**Good for:** 1000-2000 users

### Option 3: Multi-Server Setup
**3x CPX21** - €13.50/month each (~$14)
- 3 vCPU each
- 4GB RAM each
- Total: 9 vCPU, 12GB RAM
- €40.50/month total (~$43)

**Good for:** 500-800 users with redundancy

---

## Quick Deploy (Single Server)

### Step 1: Create Hetzner Account

```bash
1. Go to hetzner.com
2. Sign up (requires credit card)
3. Verify email
4. Add payment method
```

### Step 2: Create Server

```bash
# In Hetzner Cloud Console:
1. New Project → "harvest-bot"
2. Add Server
3. Location: Nuremberg (EU) or Ashburn (US)
4. Image: Ubuntu 22.04
5. Type: CPX31 (8GB RAM)
6. SSH Key: Add your public key
7. Create & Start
```

### Step 3: Initial Server Setup

```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y

# Create app directory
mkdir -p /opt/harvest
cd /opt/harvest
```

### Step 4: Deploy Application

```bash
# Clone your repo
git clone https://github.com/your-repo/harvest.git
cd harvest

# Create .env file
nano .env
# Paste your configuration (see below)

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## Configuration for Hetzner

### .env file:

```bash
# === INFRASTRUCTURE ===
REDIS_URL=redis://redis:6379
DATABASE_URL=postgresql://harvest:password@postgres:5432/harvest

# === WORKER CONFIG ===
NUM_WORKERS=10
USERS_PER_WORKER=50

# === OPTIMIZATION ===
SCAN_INTERVAL=600  # 10 minutes
PRICE_CACHE_TTL=180  # 3 minutes
STRATEGY_CACHE_TTL=90  # 90 seconds
RPC_BATCH_SIZE=10
SCAN_STAGGER_WINDOW=120

# === SOLANA & APIS ===
SOLANA_NETWORK=mainnet-beta
GROQ_API_KEY=your_groq_key

# === HELIUS API KEYS ===
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

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN=your_bot_token

# === POSTGRES ===
POSTGRES_PASSWORD=secure_random_password_here

# === PLATFORM FEE ===
PLATFORM_WALLET=BnepSp5cyDkpszTMfrq3iVEH6cMpiappY2hLxTjjLYyc
MONTHLY_FEE_PERCENTAGE=0.02
```

---

## docker-compose.yml for Hetzner

```yaml
version: '3.8'

services:
  # Redis
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    networks:
      - harvest

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: harvest
      POSTGRES_USER: harvest
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - harvest

  # Worker Manager
  manager:
    build: .
    restart: unless-stopped
    command: python -m agent.distributed.worker_manager
    env_file: .env
    depends_on:
      - redis
      - postgres
    networks:
      - harvest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Nginx (optional - for monitoring dashboard)
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - harvest

volumes:
  redis_data:
  postgres_data:

networks:
  harvest:
    driver: bridge
```

---

## Firewall Setup

```bash
# Install UFW
apt install ufw -y

# Allow SSH
ufw allow 22/tcp

# Allow HTTP/HTTPS (if using nginx)
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall
ufw enable

# Check status
ufw status
```

---

## Monitoring Setup

### Install monitoring tools:

```bash
# Install htop
apt install htop -y

# Install docker stats
docker stats

# Install netdata (optional)
bash <(curl -Ss https://my-netdata.io/kickstart.sh)
# Access at http://your-ip:19999
```

---

## Cost Breakdown (Hetzner)

### Single Server (CPX31):
```
Server (8GB RAM):       €15.30/month (~$16)
Helius API (5 paid):    $250/month
─────────────────────────────────────
Total:                  ~$266/month
Per user (500):         $0.53/user
```

### Dedicated Server (AX41):
```
Server (64GB RAM):      €39/month (~$42)
Helius API (10 paid):   $500/month
─────────────────────────────────────
Total:                  ~$542/month
Per user (2000):        $0.27/user
```

### Multi-Server (3x CPX21):
```
3 Servers (12GB total): €40.50/month (~$43)
Helius API (5 paid):    $250/month
─────────────────────────────────────
Total:                  ~$293/month
Per user (800):         $0.37/user
```

---

## Scaling on Hetzner

### 100 users:
```
Server: CPX11 (2GB RAM) - €4.15/month
API: 2 free Helius keys
Total: ~$5/month
```

### 500 users:
```
Server: CPX31 (8GB RAM) - €15.30/month
API: 5 paid Helius keys - $250/month
Total: ~$266/month
```

### 1000 users:
```
Server: AX41 (64GB RAM) - €39/month
API: 10 paid Helius keys - $500/month
Total: ~$542/month
```

### 5000 users:
```
Servers: 3x AX41 - €117/month
API: 30 paid keys - $1500/month
Load Balancer: €5/month
Total: ~$1622/month
```

---

## Backup Strategy

### Automated Backups:

```bash
# Create backup script
cat > /opt/harvest/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec harvest_postgres_1 pg_dump -U harvest harvest > $BACKUP_DIR/db_$DATE.sql

# Backup Redis
docker exec harvest_redis_1 redis-cli SAVE
docker cp harvest_redis_1:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Compress
tar -czf $BACKUP_DIR/harvest_backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "harvest_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/harvest/backup.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add: 0 2 * * * /opt/harvest/backup.sh
```

---

## SSL Setup (Optional)

### Using Let's Encrypt:

```bash
# Install certbot
apt install certbot python3-certbot-nginx -y

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

---

## Maintenance

### Update application:

```bash
cd /opt/harvest/harvest
git pull
docker-compose build
docker-compose up -d
```

### View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f manager

# Last 100 lines
docker-compose logs --tail=100
```

### Restart services:

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart manager
```

### Check resource usage:

```bash
# CPU and memory
htop

# Docker stats
docker stats

# Disk usage
df -h
```

---

## Migration from Free Tier

### Step 1: Backup Data

```bash
# On free tier (Render/Supabase)
# Export PostgreSQL
pg_dump $DATABASE_URL > backup.sql

# Download backup
scp backup.sql root@hetzner-ip:/opt/harvest/
```

### Step 2: Import to Hetzner

```bash
# On Hetzner server
cd /opt/harvest
docker-compose up -d postgres

# Import data
docker exec -i harvest_postgres_1 psql -U harvest harvest < backup.sql
```

### Step 3: Update DNS

```bash
# Point your domain to Hetzner IP
# Update Telegram webhook URL
# Test everything works
```

### Step 4: Shutdown Free Tier

```bash
# Once verified, shutdown old services
# Cancel Render/Supabase
```

---

## Troubleshooting

### Out of memory:

```bash
# Check memory usage
free -h

# Increase swap
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Docker issues:

```bash
# Restart Docker
systemctl restart docker

# Clean up
docker system prune -a

# Check logs
journalctl -u docker
```

### Network issues:

```bash
# Check firewall
ufw status

# Check ports
netstat -tulpn

# Test connectivity
ping 8.8.8.8
```

---

## Best Practices

1. **Use SSH keys** - Disable password auth
2. **Enable firewall** - Only open necessary ports
3. **Regular backups** - Automated daily backups
4. **Monitor resources** - Set up alerts
5. **Update regularly** - Keep system and Docker updated
6. **Use swap** - Add swap for memory spikes
7. **Log rotation** - Prevent disk fill-up

---

## Quick Commands Reference

```bash
# Deploy
docker-compose up -d

# Logs
docker-compose logs -f

# Restart
docker-compose restart

# Stop
docker-compose down

# Update
git pull && docker-compose up -d --build

# Backup
/opt/harvest/backup.sh

# Monitor
htop
docker stats
```

---

## Support

- Hetzner Docs: docs.hetzner.com
- Community: community.hetzner.com
- Status: status.hetzner.com

---

**Hetzner = Best bang for your buck! 🚀**

4-5x cheaper than AWS/Railway with same performance.
