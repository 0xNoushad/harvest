# 🚀 Deployment Quick Reference

## TL;DR - Safe Deployment

```bash
# 1. Test locally
pytest

# 2. Run migrations
python scripts/run_migrations.py

# 3. Deploy
git push origin main

# 4. Monitor
python scripts/monitor_deployment.py

# 5. If issues, rollback
./scripts/rollback.sh
```

---

## Railway (Auto-Deploy)

### Normal Deployment:
```bash
git push origin main
# Railway handles everything automatically!
```

### Manual Deployment:
```bash
railway up
```

### Rollback:
```bash
# In Railway dashboard:
Deployments → Previous Version → Redeploy

# Or CLI:
railway rollback
```

---

## Hetzner (Manual)

### Deployment:
```bash
./scripts/deploy.sh
```

### Rollback:
```bash
./scripts/rollback.sh
```

### Manual Steps:
```bash
# Build
docker build -t harvest:green .

# Deploy green
docker-compose --profile green up -d worker-green

# Health check
curl http://localhost:8080/health

# Switch traffic
cp nginx-green.conf /etc/nginx/nginx.conf
nginx -s reload

# Stop blue
docker-compose stop worker-blue

# Promote green to blue
docker tag harvest:green harvest:blue
docker-compose up -d worker-blue
```

---

## Database Migrations

### Run migrations:
```bash
python scripts/run_migrations.py
```

### Dry run (test):
```bash
python scripts/run_migrations.py --dry-run
```

### Create new migration:
```bash
# Create file: migrations/002_add_feature.py

async def upgrade(db):
    await db.execute("""
        ALTER TABLE users 
        ADD COLUMN new_field VARCHAR(255)
    """)

async def downgrade(db):
    await db.execute("""
        ALTER TABLE users 
        DROP COLUMN new_field
    """)
```

---

## Monitoring

### Real-time monitoring:
```bash
python scripts/monitor_deployment.py
```

### Monitor for 5 minutes:
```bash
python scripts/monitor_deployment.py --duration 300
```

### Check logs:
```bash
# Railway
railway logs

# Hetzner
docker-compose logs -f
```

---

## Emergency Procedures

### High Error Rate:
```bash
# 1. Check logs
docker-compose logs -f | grep ERROR

# 2. Check metrics
python scripts/monitor_deployment.py

# 3. If > 10% errors, rollback immediately
./scripts/rollback.sh
```

### Service Down:
```bash
# 1. Check status
docker-compose ps

# 2. Restart service
docker-compose restart

# 3. If still down, rollback
./scripts/rollback.sh
```

### Database Issues:
```bash
# 1. Check database connection
psql $DATABASE_URL

# 2. Check migrations
python scripts/run_migrations.py --dry-run

# 3. Rollback if needed
./scripts/rollback.sh
```

---

## Pre-Deployment Checklist

- [ ] Tests pass locally (`pytest`)
- [ ] Migrations tested (`--dry-run`)
- [ ] No breaking changes
- [ ] Database backed up
- [ ] Low traffic time (2-4 AM)
- [ ] Team notified
- [ ] Rollback plan ready

---

## Post-Deployment Checklist

- [ ] Health check passes
- [ ] Error rate < 5%
- [ ] Trades executing
- [ ] Users receiving notifications
- [ ] No database errors
- [ ] Monitor for 1 hour
- [ ] Keep old version for 24h

---

## Common Issues

### "Migration failed"
```bash
# Check database connection
psql $DATABASE_URL

# Run migration manually
python scripts/run_migrations.py

# If still fails, check migration file
```

### "Health check failed"
```bash
# Check logs
docker-compose logs -f

# Check if service is running
docker-compose ps

# Restart service
docker-compose restart
```

### "High error rate"
```bash
# Check recent errors
docker-compose logs -f | grep ERROR

# Monitor metrics
python scripts/monitor_deployment.py

# Rollback if > 10%
./scripts/rollback.sh
```

---

## GitHub Actions

### Trigger deployment:
```bash
git push origin main
# GitHub Actions runs automatically
```

### View logs:
```
GitHub → Actions → Latest workflow run
```

### Required secrets:
- `DATABASE_URL` - PostgreSQL connection
- `RAILWAY_URL` - Railway app URL (optional)
- `TELEGRAM_BOT_TOKEN` - For notifications (optional)
- `TELEGRAM_CHAT_ID` - For notifications (optional)

---

## Best Practices

1. **Always run migrations first**
   ```bash
   python scripts/run_migrations.py
   ```

2. **Deploy during low traffic**
   - 2-4 AM local time
   - Weekdays (not weekends)
   - After market close

3. **Monitor for 1 hour**
   ```bash
   python scripts/monitor_deployment.py --duration 3600
   ```

4. **Keep rollback ready**
   - Old version running for 24h
   - Can rollback instantly

5. **Test on staging first**
   ```bash
   git push origin staging
   # Test for 24h
   # Then deploy to production
   ```

---

## Quick Commands

```bash
# Deploy
./scripts/deploy.sh

# Rollback
./scripts/rollback.sh

# Migrations
python scripts/run_migrations.py

# Monitor
python scripts/monitor_deployment.py

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Restart
docker-compose restart
```

---

## Support

- Deployment issues: Check `DEPLOYMENT_STRATEGY.md`
- Railway: `QUICKSTART_FREE.md`
- Hetzner: `DEPLOY_HETZNER.md`
- Architecture: `ARCHITECTURE_500_USERS.md`
