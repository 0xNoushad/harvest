# 🚀 Deployment Checklist

This checklist ensures safe and successful deployment of the Harvest trading agent to production. Follow each step carefully to minimize risk and maximize performance.

---

## Pre-Deployment Checklist

### ✅ Environment Setup

- [ ] Production `.env` file created from `.env.production.template`
- [ ] All required environment variables set:
  - [ ] `TELEGRAM_BOT_TOKEN`
  - [ ] `TELEGRAM_CHAT_ID`
  - [ ] `GROQ_API_KEY`
  - [ ] `SOLANA_NETWORK=mainnet`
  - [ ] `WALLET_ADDRESS` (deprecated - for backward compatibility only)
  - [ ] `WALLET_PRIVATE_KEY` (deprecated - for backward compatibility only)
- [ ] Optional but recommended variables set:
  - [ ] `HELIUS_API_KEY` (for faster RPC)
  - [ ] `JUPITER_API_KEY` (for better swap rates)
  - [ ] `DISCORD_WEBHOOK_URL` (for additional alerts)

### ✅ Multi-User Mode Configuration

**NEW: Harvest now supports multiple users with isolated wallets**

- [ ] Multi-user mode enabled (default in latest version)
- [ ] Database initialized for wallet storage
- [ ] Secure wallet storage directory created (`config/secure_wallets/`)
- [ ] Minimum trading balance configured:
  ```bash
  # Users need at least 0.01 SOL to trade
  # This is hardcoded but can be adjusted in AgentLoop initialization
  MIN_TRADING_BALANCE=0.01
  ```
- [ ] Stagger window configured for large user bases:
  ```bash
  # Spread user scans over 60 seconds (default)
  SCAN_STAGGER_WINDOW=60
  ```
- [ ] Batch RPC settings optimized:
  ```bash
  # Process 10 users per batch (default)
  RPC_BATCH_SIZE=10
  ```

**Multi-User Features:**
- Each user creates their own wallet via `/createwallet` or `/importwallet`
- Wallets are encrypted and stored securely in the database
- Trading activates automatically when user balance >= 0.01 SOL
- Bot runs 24/7 regardless of individual user balances
- Each user's performance tracked separately
- Error isolation - one user's failure doesn't affect others

### ✅ Wallet Preparation

**IMPORTANT: Multi-user mode changes wallet setup**

In multi-user mode, each user creates their own wallet via Telegram commands. The bot operator no longer needs to provide a single wallet.

**For Bot Operators:**
- [ ] Database initialized and accessible
- [ ] Secure wallet storage directory created with proper permissions
- [ ] Backup strategy for encrypted wallet files
- [ ] No need to set `WALLET_ADDRESS` or `WALLET_PRIVATE_KEY` in `.env`

**For Users (via Telegram):**
- [ ] Users instructed to use `/createwallet` or `/importwallet`
- [ ] Users informed about 0.01 SOL minimum balance requirement
- [ ] Security best practices communicated to users
- [ ] Users know how to use `/exportkey` to backup their wallet

**Testing Multi-User Setup:**
- [ ] Create test wallet via `/createwallet`
- [ ] Verify wallet stored in database
- [ ] Check encrypted file created in `config/secure_wallets/`
- [ ] Test `/balance` command
- [ ] Test `/exportkey` command
- [ ] Verify wallet loads correctly after bot restart

### ✅ Risk Configuration

**Start with conservative settings for first 100 trades:**

- [ ] Position sizing configured conservatively:
  ```bash
  MAX_POSITION_PCT=0.05          # Start with 5% max
  HIGH_RISK_POSITION_PCT=0.02    # 2% for high risk
  MEDIUM_RISK_POSITION_PCT=0.05  # 5% for medium risk
  LOW_RISK_POSITION_PCT=0.10     # 10% for low risk
  ```

- [ ] Circuit breakers enabled:
  ```bash
  MAX_DAILY_LOSS_PCT=0.10        # Start with 10% daily limit
  MIN_BALANCE_SOL=0.1            # Maintain minimum balance
  CONSECUTIVE_LOSS_THRESHOLD=3   # Reduce after 3 losses
  ```

- [ ] Fee protection enabled:
  ```bash
  MAX_FEE_PCT_OF_PROFIT=0.05     # Skip if fees > 5% of profit
  ```

### ✅ Strategy Configuration

**Start with one strategy, add more after validation:**

- [ ] Initial strategy selection:
  ```bash
  # Option 1: Start with staking (lowest risk)
  ENABLE_JUPITER_SWAP=false
  ENABLE_MARINADE_STAKE=true
  ENABLE_AIRDROP_HUNTER=false
  
  # Option 2: Start with swaps (medium risk)
  ENABLE_JUPITER_SWAP=true
  ENABLE_MARINADE_STAKE=false
  ENABLE_AIRDROP_HUNTER=false
  
  # Option 3: Start with airdrops (low risk, low frequency)
  ENABLE_JUPITER_SWAP=false
  ENABLE_MARINADE_STAKE=false
  ENABLE_AIRDROP_HUNTER=true
  ```

### ✅ Monitoring Setup

- [ ] Telegram bot configured and tested
- [ ] Discord webhook configured (optional)
- [ ] Log directory created and writable
- [ ] Log rotation configured (if needed)
- [ ] Monitoring dashboard set up (optional)
- [ ] Alert thresholds configured

### ✅ Testing

- [ ] Agent tested on devnet successfully
- [ ] All strategies tested individually
- [ ] Risk limits tested and verified
- [ ] Circuit breakers tested
- [ ] Notification system tested
- [ ] Error handling tested
- [ ] Recovery from crashes tested

---

## Deployment Steps

### Phase 1: Initial Deployment (Days 1-7)

**Goal:** Validate agent behavior with minimal risk

#### Day 1: Deploy with Minimal Capital

**Multi-User Mode Deployment:**

1. **Start the bot (no wallet funding needed initially)**
   ```bash
   python -m harvest.agent.main
   ```
   
   The bot will start and remain online even with no users registered.

2. **Register first test user**
   - [ ] Send `/createwallet` command via Telegram
   - [ ] Save the 12-word mnemonic phrase securely
   - [ ] Note the wallet address provided
   - [ ] Verify wallet appears in database

3. **Fund test user's wallet**
   - [ ] Transfer 0.5-1 SOL to the wallet address
   - [ ] Verify balance with `/balance` command
   - [ ] Wait for automatic trading activation notification
   - [ ] Confirm trading activated (balance >= 0.01 SOL)

4. **Monitor first hour closely**
   - [ ] Watch console output for multi-user scan cycles
   - [ ] Verify Telegram notifications working for test user
   - [ ] Check for any errors in wallet loading
   - [ ] Verify opportunities being detected for test user
   - [ ] Confirm risk limits being enforced per user
   - [ ] Test balance threshold detection (add/remove funds)

**Multi-User Specific Checks:**
- [ ] Verify user wallet loaded from database on startup
- [ ] Check encrypted wallet file exists in `config/secure_wallets/`
- [ ] Confirm balance cache working (check logs)
- [ ] Test automatic activation when balance crosses 0.01 SOL
- [ ] Test automatic deactivation when balance drops below 0.01 SOL
- [ ] Verify user can export their key with `/exportkey`

#### Days 1-3: Monitor First 10 Trades

- [ ] Review each trade execution
- [ ] Verify expected vs actual profit
- [ ] Check gas fees are reasonable
- [ ] Confirm slippage protection working
- [ ] Monitor for any errors or issues
- [ ] Track performance metrics

**Success Criteria:**
- ✅ No critical errors
- ✅ Trades executing successfully
- ✅ Risk limits being enforced
- ✅ Notifications working
- ✅ Positive or break-even performance

**If issues found:**
- ⚠️ Stop agent immediately
- ⚠️ Review logs thoroughly
- ⚠️ Fix issues before continuing
- ⚠️ Test fixes on devnet first

#### Days 4-7: Monitor First 100 Trades

- [ ] Daily performance review
- [ ] Check win rate by strategy
- [ ] Verify risk management working
- [ ] Monitor gas fee costs
- [ ] Track total profit/loss
- [ ] Review any circuit breaker activations

**Success Criteria:**
- ✅ At least 100 trades executed
- ✅ Win rate > 50%
- ✅ Total profit > total fees
- ✅ No critical errors
- ✅ Circuit breakers working as expected

**Performance Targets:**
- Win rate: 50-70%
- Average profit per trade: > gas fees
- Daily profit: Positive or break-even
- Max drawdown: < 10%

---

### Phase 2: Scale Up (Days 8-30)

**Goal:** Gradually increase position sizes and capital

#### Week 2: Increase Position Sizes

**If Phase 1 successful:**

1. **Increase position limits gradually**
   ```bash
   # Week 2 settings
   MAX_POSITION_PCT=0.08          # Increase to 8%
   HIGH_RISK_POSITION_PCT=0.03    # 3% for high risk
   MEDIUM_RISK_POSITION_PCT=0.08  # 8% for medium risk
   LOW_RISK_POSITION_PCT=0.15     # 15% for low risk
   ```

2. **Monitor for 50 more trades**
   - [ ] Performance still positive
   - [ ] Risk limits still effective
   - [ ] No increase in error rate

#### Week 3: Add More Capital

**If Week 2 successful:**

1. **Increase wallet balance**
   - [ ] Add 2-5 SOL to wallet
   - [ ] Verify balance updated
   - [ ] Monitor first trades with larger capital

2. **Enable second strategy**
   ```bash
   # Enable second strategy
   ENABLE_JUPITER_SWAP=true
   ENABLE_MARINADE_STAKE=true
   ENABLE_AIRDROP_HUNTER=false
   ```

3. **Monitor for 50 more trades**
   - [ ] Both strategies performing well
   - [ ] No conflicts between strategies
   - [ ] Risk limits still effective

#### Week 4: Full Production Settings

**If Week 3 successful:**

1. **Use production position sizes**
   ```bash
   # Production settings
   MAX_POSITION_PCT=0.10          # Full 10%
   HIGH_RISK_POSITION_PCT=0.05    # 5% for high risk
   MEDIUM_RISK_POSITION_PCT=0.10  # 10% for medium risk
   LOW_RISK_POSITION_PCT=0.20     # 20% for low risk
   ```

2. **Enable all strategies**
   ```bash
   ENABLE_JUPITER_SWAP=true
   ENABLE_MARINADE_STAKE=true
   ENABLE_AIRDROP_HUNTER=true
   ```

3. **Add full production capital**
   - [ ] Fund wallet to desired level
   - [ ] Keep 10-20% in reserve
   - [ ] Monitor closely for first day

4. **Scale to multiple users (Multi-User Mode)**
   
   **Onboarding Additional Users:**
   - [ ] Invite additional users to the bot
   - [ ] Each user creates wallet via `/createwallet` or `/importwallet`
   - [ ] Users fund their own wallets (minimum 0.01 SOL)
   - [ ] Monitor bot performance with multiple users
   
   **Multi-User Scaling Checklist:**
   - [ ] Verify all users' wallets load correctly on startup
   - [ ] Check scan cycle iterates through all users
   - [ ] Confirm error isolation (one user's error doesn't affect others)
   - [ ] Monitor RPC rate limits with multiple users
   - [ ] Verify batch balance checks working efficiently
   - [ ] Test staggered scanning if >100 users
   
   **Performance Monitoring Per User:**
   - [ ] Each user can check their stats with `/stats`
   - [ ] Leaderboard shows anonymized rankings with `/leaderboard`
   - [ ] User data isolated (users only see their own trades)
   - [ ] Performance tracking persists across restarts
   
   **Scaling Thresholds:**
   - **1-10 users:** Standard configuration works well
   - **10-50 users:** Enable batch RPC requests
   - **50-100 users:** Optimize cache TTL settings
   - **100-500 users:** Enable staggered scanning and multi-API keys
   - **500+ users:** Consider horizontal scaling or sharding

---

### Phase 3: Ongoing Operations (Day 31+)

**Goal:** Maintain and optimize performance

#### Daily Tasks

- [ ] Check Telegram notifications
- [ ] Review daily performance summary
- [ ] Check for any errors in logs
- [ ] Verify agent is running
- [ ] Monitor wallet balance

#### Weekly Tasks

- [ ] Review weekly performance metrics
- [ ] Analyze win rate by strategy
- [ ] Check total profit vs fees
- [ ] Review any circuit breaker activations
- [ ] Optimize configuration if needed
- [ ] Update API keys if needed

#### Monthly Tasks

- [ ] Full performance review
- [ ] Calculate monthly ROI
- [ ] Review and adjust risk parameters
- [ ] Update dependencies
- [ ] Backup performance data
- [ ] Review and optimize strategies

---

## Emergency Procedures

### 🚨 Stop Trading Immediately If:

- Critical error in logs
- Unexpected large loss (> 20% in short time)
- Wallet compromised or suspicious activity
- Exchange/DEX issues reported
- Network-wide Solana issues

**How to stop:**
```bash
# Graceful shutdown
Ctrl+C

# Or set position size to 0
MAX_POSITION_PCT=0
```

### 🔧 Troubleshooting During Deployment

#### High Loss Rate

**Symptoms:** Win rate < 40%, consistent losses

**Actions:**
1. Stop agent immediately
2. Review recent trades in logs
3. Check if market conditions changed
4. Verify strategy logic is correct
5. Test on devnet before resuming

#### Excessive Gas Fees

**Symptoms:** Fees > 10% of profits

**Actions:**
1. Increase `MAX_FEE_PCT_OF_PROFIT` threshold
2. Reduce trading frequency
3. Wait for lower network congestion
4. Consider using priority fee optimization

#### Circuit Breakers Triggering Frequently

**Symptoms:** Trading paused multiple times per day

**Actions:**
1. Review what's triggering the breaker
2. Adjust thresholds if too conservative
3. Improve strategy selection logic
4. Reduce position sizes

#### Rate Limiting Issues

**Symptoms:** Frequent rate limit errors

**Actions:**
1. Add more Helius API keys
2. Increase scan interval
3. Enable caching
4. Reduce number of strategies

**Multi-User Specific:**
- Check number of active users (may need to scale RPC)
- Enable batch balance checks: `RPC_BATCH_SIZE=15`
- Increase stagger window: `SCAN_STAGGER_WINDOW=90`
- Consider adding multiple API keys for load distribution

---

### 🔧 Multi-User Mode Troubleshooting

#### User Wallet Not Loading

**Symptoms:** User reports wallet not found after bot restart

**Actions:**
1. Check database for user's wallet entry
2. Verify encrypted wallet file exists in `config/secure_wallets/`
3. Check file permissions on wallet storage directory
4. Review logs for wallet loading errors
5. Test wallet decryption manually

#### Trading Not Activating for User

**Symptoms:** User has sufficient balance but no trades executing

**Actions:**
1. Verify balance >= 0.01 SOL with `/balance`
2. Check if user is in scan cycle (review logs)
3. Confirm strategies are enabled
4. Verify no errors in user's scan cycle
5. Check if market has opportunities

#### Multiple Users Experiencing Errors

**Symptoms:** Several users report issues simultaneously

**Actions:**
1. Check RPC provider status (Helius/Solana)
2. Review rate limiting statistics
3. Check database connectivity
4. Verify sufficient system resources
5. Consider scaling infrastructure

#### Wallet Export Fails

**Symptoms:** `/exportkey` command returns error

**Actions:**
1. Verify user owns the wallet (authorization check)
2. Check encrypted wallet file exists
3. Verify decryption password matches
4. Review security logs for details
5. Test wallet file integrity

---

## Performance Monitoring

### Key Metrics to Track

#### Daily Metrics
- Total trades executed
- Win rate (%)
- Total profit/loss (SOL)
- Average profit per trade
- Total gas fees paid
- Circuit breaker activations

#### Weekly Metrics
- Weekly ROI (%)
- Profit by strategy
- Best performing strategy
- Worst performing strategy
- Average daily profit
- Max drawdown

#### Monthly Metrics
- Monthly ROI (%)
- Total profit (SOL and USD)
- Sharpe ratio (if applicable)
- Max drawdown
- Recovery time from drawdowns
- Strategy allocation changes

### Performance Targets

**Conservative (Low Risk):**
- Monthly ROI: 5-10%
- Win rate: 60-70%
- Max drawdown: < 10%

**Moderate (Medium Risk):**
- Monthly ROI: 10-20%
- Win rate: 55-65%
- Max drawdown: < 15%

**Aggressive (High Risk):**
- Monthly ROI: 20-50%
- Win rate: 50-60%
- Max drawdown: < 25%

---

## Configuration Optimization

### After 100 Trades

Review and optimize based on performance:

#### If Win Rate > 70%
- Consider increasing position sizes
- Enable more aggressive strategies
- Reduce slippage tolerance slightly

#### If Win Rate 50-70%
- Keep current settings
- Monitor for another 100 trades
- Make small adjustments if needed

#### If Win Rate < 50%
- Reduce position sizes
- Increase slippage tolerance
- Disable underperforming strategies
- Review strategy logic

### After 500 Trades

Consider advanced optimizations:

- [ ] Implement custom strategy allocation
- [ ] Adjust risk parameters based on volatility
- [ ] Optimize scan intervals by time of day
- [ ] Enable advanced features (if available)
- [ ] Consider multi-wallet setup

---

## Security Best Practices

### Wallet Security

- [ ] Private key encrypted at rest
- [ ] Private key never in version control
- [ ] Use hardware wallet for large amounts
- [ ] Separate wallets for dev/prod
- [ ] Regular security audits

### API Key Security

- [ ] API keys in environment variables only
- [ ] Rotate API keys monthly
- [ ] Use separate keys for dev/prod
- [ ] Monitor API key usage
- [ ] Revoke unused keys

### Operational Security

- [ ] Server access restricted
- [ ] Logs don't contain sensitive data
- [ ] Regular backups of performance data
- [ ] Monitoring for suspicious activity
- [ ] Incident response plan documented

---

## Rollback Procedure

If deployment fails or issues arise:

1. **Stop the agent**
   ```bash
   Ctrl+C
   ```

2. **Assess the situation**
   - Review logs for errors
   - Check wallet balance
   - Verify no pending transactions

3. **Rollback configuration**
   ```bash
   # Restore previous .env
   cp .env.backup .env
   ```

4. **Test on devnet**
   ```bash
   SOLANA_NETWORK=devnet python -m harvest.agent.main
   ```

5. **Fix issues before redeploying**

---

## Success Criteria

### Phase 1 Success (First 100 Trades)
- ✅ No critical errors
- ✅ Win rate > 50%
- ✅ Positive net profit
- ✅ Risk limits working
- ✅ Notifications working

### Phase 2 Success (First 500 Trades)
- ✅ Consistent profitability
- ✅ Win rate > 55%
- ✅ Monthly ROI > 5%
- ✅ Max drawdown < 15%
- ✅ All strategies performing

### Phase 3 Success (Ongoing)
- ✅ Sustained profitability
- ✅ Meeting performance targets
- ✅ Minimal manual intervention
- ✅ Stable operation
- ✅ Continuous improvement

---

## Support and Resources

### Documentation
- [README.md](README.md) - Main documentation
- [Agent Architecture](agent/README.md) - Code structure
- [Configuration Guide](.env.production.template) - All settings

### Getting Help
- Check logs first: `logs/harvest_YYYY-MM-DD.log`
- Enable debug logging: `LOG_LEVEL=DEBUG`
- Review troubleshooting guide in README
- Open GitHub issue with logs (redact keys!)

### Community
- Discord: [Join server]
- GitHub: [Open issues]
- Twitter: [Follow updates]

---

## Final Checklist

Before going live:

- [ ] All pre-deployment checks completed
- [ ] Conservative settings configured
- [ ] Monitoring and alerts set up
- [ ] Emergency procedures documented
- [ ] Team trained on operations
- [ ] Backup and recovery tested
- [ ] Security review completed
- [ ] Performance targets defined
- [ ] Rollback procedure tested
- [ ] Support contacts documented

**Remember:** Start small, monitor closely, scale gradually!

🌾 Good luck with your deployment! 🚀
