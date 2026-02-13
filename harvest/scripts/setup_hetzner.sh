#!/bin/bash
# Hetzner Server Setup Script
# Run this on a fresh Ubuntu 22.04 server

set -e

echo "🚀 Harvest Hetzner Setup Script"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential tools
echo "🔧 Installing essential tools..."
apt install -y \
    curl \
    wget \
    git \
    htop \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-transport-https \
    ca-certificates \
    software-properties-common

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
echo "🐳 Installing Docker Compose..."
apt install -y docker-compose-plugin

# Configure firewall
echo "🔥 Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
echo "✅ Firewall configured"

# Configure fail2ban
echo "🛡️  Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban
echo "✅ Fail2ban configured"

# Enable automatic security updates
echo "🔒 Enabling automatic security updates..."
dpkg-reconfigure -plow unattended-upgrades
echo "✅ Automatic updates enabled"

# Create app directory
echo "📁 Creating application directory..."
mkdir -p /opt/harvest
cd /opt/harvest

# Create backup directory
mkdir -p /opt/backups

# Set up swap (if not exists)
if [ ! -f /swapfile ]; then
    echo "💾 Creating swap file (4GB)..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap file created"
else
    echo "✅ Swap file already exists"
fi

# Optimize system for Docker
echo "⚙️  Optimizing system..."
cat >> /etc/sysctl.conf << EOF

# Harvest optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=1024
net.ipv4.tcp_max_syn_backlog=2048
EOF
sysctl -p

# Create log rotation config
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/harvest << EOF
/opt/harvest/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF

# Create backup script
echo "💾 Creating backup script..."
cat > /opt/harvest/backup.sh << 'BACKUP_SCRIPT'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec harvest_postgres pg_dump -U harvest harvest > $BACKUP_DIR/db_$DATE.sql

# Backup Redis
docker exec harvest_redis redis-cli SAVE
docker cp harvest_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Compress
tar -czf $BACKUP_DIR/harvest_backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*
rm $BACKUP_DIR/db_$DATE.sql $BACKUP_DIR/redis_$DATE.rdb

# Remove old backups (keep last 7 days)
find $BACKUP_DIR -name "harvest_backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
BACKUP_SCRIPT

chmod +x /opt/harvest/backup.sh

# Add backup to crontab
echo "⏰ Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/harvest/backup.sh >> /var/log/harvest_backup.log 2>&1") | crontab -

# Create monitoring script
echo "📊 Creating monitoring script..."
cat > /opt/harvest/monitor.sh << 'MONITOR_SCRIPT'
#!/bin/bash
echo "=== Harvest System Status ==="
echo ""
echo "📊 System Resources:"
free -h
echo ""
df -h /
echo ""
echo "🐳 Docker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "📈 Docker Stats:"
docker stats --no-stream
echo ""
echo "🔥 Recent Logs (last 20 lines):"
docker-compose -f /opt/harvest/harvest/docker-compose.hetzner.yml logs --tail=20
MONITOR_SCRIPT

chmod +x /opt/harvest/monitor.sh

# Print summary
echo ""
echo "================================"
echo "✅ Hetzner setup complete!"
echo "================================"
echo ""
echo "📋 Next steps:"
echo "1. Clone your repo: cd /opt/harvest && git clone <your-repo>"
echo "2. Create .env file with your configuration"
echo "3. Start services: docker-compose -f docker-compose.hetzner.yml up -d"
echo "4. Check logs: docker-compose -f docker-compose.hetzner.yml logs -f"
echo ""
echo "🔧 Useful commands:"
echo "- Monitor: /opt/harvest/monitor.sh"
echo "- Backup: /opt/harvest/backup.sh"
echo "- Logs: docker-compose logs -f"
echo "- Restart: docker-compose restart"
echo ""
echo "🔒 Security:"
echo "- Firewall: ufw status"
echo "- Fail2ban: fail2ban-client status"
echo "- Updates: unattended-upgrades --dry-run"
echo ""
echo "💾 Backups:"
echo "- Location: /opt/backups"
echo "- Schedule: Daily at 2 AM"
echo "- Retention: 7 days"
echo ""
echo "🚀 Happy deploying!"
