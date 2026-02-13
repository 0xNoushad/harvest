#!/bin/bash
# Emergency rollback script

set -e

echo "🔙 EMERGENCY ROLLBACK"
echo "===================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Confirm rollback
echo -e "${RED}⚠️  WARNING: This will rollback to the previous version!${NC}"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

echo ""
echo "Rolling back..."

# Check platform
if [ -n "$RAILWAY_ENVIRONMENT" ]; then
    echo "Platform: Railway"
    echo ""
    echo "To rollback on Railway:"
    echo "1. Go to https://railway.app"
    echo "2. Select your project"
    echo "3. Go to Deployments"
    echo "4. Find previous successful deployment"
    echo "5. Click 'Redeploy'"
    echo ""
    echo "Or use Railway CLI:"
    echo "  railway rollback"
    
else
    echo "Platform: Hetzner/Docker"
    echo ""
    
    # Check if blue version exists
    if docker ps -a | grep -q harvest_worker_blue; then
        echo "✅ Found blue version"
        
        # Switch nginx back to blue
        if [ -f nginx-blue.conf ]; then
            echo "Switching traffic to blue..."
            cp nginx-blue.conf /etc/nginx/nginx.conf
            nginx -s reload
        fi
        
        # Start blue
        echo "Starting blue version..."
        docker-compose up -d worker-blue
        
        # Stop green
        echo "Stopping green version..."
        docker-compose --profile green down worker-green || true
        
        # Wait for health check
        echo "Waiting for health check..."
        sleep 10
        
        MAX_RETRIES=12
        RETRY=0
        until curl -f http://localhost:8080/health > /dev/null 2>&1; do
            RETRY=$((RETRY+1))
            if [ $RETRY -ge $MAX_RETRIES ]; then
                echo -e "${RED}❌ Health check failed!${NC}"
                exit 1
            fi
            echo "Waiting for blue to be healthy... ($RETRY/$MAX_RETRIES)"
            sleep 5
        done
        
        echo -e "${GREEN}✅ Rollback complete!${NC}"
        echo ""
        echo "Blue version is now running."
        
    else
        echo -e "${RED}❌ No previous version found!${NC}"
        echo "Cannot rollback."
        exit 1
    fi
fi

echo ""
echo "===================="
echo -e "${GREEN}✅ Rollback successful${NC}"
echo "===================="
echo ""
echo "Next steps:"
echo "1. Check logs: docker-compose logs -f"
echo "2. Monitor metrics: python scripts/monitor_deployment.py"
echo "3. Investigate what went wrong"
echo ""
