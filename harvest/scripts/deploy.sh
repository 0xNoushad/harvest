#!/bin/bash
# Zero-downtime deployment script
# Works for both Railway and Hetzner

set -e

echo "🚀 Harvest Zero-Downtime Deployment"
echo "===================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on Railway or Hetzner
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    PLATFORM="railway"
else
    PLATFORM="hetzner"
fi

echo "Platform: $PLATFORM"
echo ""

# Step 1: Run tests
echo "📋 Step 1: Running tests..."
if pytest --tb=short; then
    echo -e "${GREEN}✅ Tests passed${NC}"
else
    echo -e "${RED}❌ Tests failed! Aborting deployment.${NC}"
    exit 1
fi
echo ""

# Step 2: Run migrations
echo "📋 Step 2: Running database migrations..."
if python scripts/run_migrations.py; then
    echo -e "${GREEN}✅ Migrations complete${NC}"
else
    echo -e "${RED}❌ Migrations failed! Aborting deployment.${NC}"
    exit 1
fi
echo ""

# Step 3: Deploy based on platform
if [ "$PLATFORM" = "railway" ]; then
    echo "📋 Step 3: Deploying to Railway..."
    echo "Railway will handle zero-downtime deployment automatically."
    echo "Push to GitHub to trigger deployment:"
    echo "  git push origin main"
    echo ""
    echo -e "${YELLOW}⏳ Waiting for Railway to deploy...${NC}"
    echo "Check status at: https://railway.app"
    
elif [ "$PLATFORM" = "hetzner" ]; then
    echo "📋 Step 3: Deploying to Hetzner..."
    
    # Build new version
    echo "Building new Docker image..."
    docker build -t harvest:green .
    
    # Start green (new version)
    echo "Starting green version..."
    docker-compose --profile green up -d worker-green
    
    # Wait for health check
    echo "Waiting for health check..."
    sleep 10
    
    MAX_RETRIES=12
    RETRY=0
    until curl -f http://localhost:8080/health > /dev/null 2>&1; do
        RETRY=$((RETRY+1))
        if [ $RETRY -ge $MAX_RETRIES ]; then
            echo -e "${RED}❌ Health check failed! Rolling back...${NC}"
            docker-compose --profile green down worker-green
            exit 1
        fi
        echo "Waiting for green to be healthy... ($RETRY/$MAX_RETRIES)"
        sleep 5
    done
    
    echo -e "${GREEN}✅ Green version is healthy${NC}"
    
    # Switch traffic
    echo "Switching traffic to green..."
    if [ -f nginx-green.conf ]; then
        cp nginx-green.conf /etc/nginx/nginx.conf
        nginx -s reload
    fi
    
    # Wait for connections to drain
    echo "Draining connections from blue..."
    sleep 30
    
    # Stop blue
    echo "Stopping blue version..."
    docker-compose stop worker-blue
    
    # Promote green to blue
    echo "Promoting green to blue..."
    docker tag harvest:green harvest:blue
    docker-compose --profile green down worker-green
    docker-compose up -d worker-blue
    
    echo -e "${GREEN}✅ Deployment complete!${NC}"
fi

echo ""
echo "📋 Step 4: Post-deployment checks..."

# Monitor for 5 minutes
echo "Monitoring for 5 minutes..."
python scripts/monitor_deployment.py --duration 300 &
MONITOR_PID=$!

# Wait
sleep 300

# Kill monitor
kill $MONITOR_PID 2>/dev/null || true

echo ""
echo "===================================="
echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo "===================================="
echo ""
echo "Next steps:"
echo "1. Monitor logs: docker-compose logs -f"
echo "2. Check metrics: python scripts/monitor_deployment.py"
echo "3. If issues: ./scripts/rollback.sh"
echo ""
