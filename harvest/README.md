# 🌾 HARVEST - Autonomous Money Hunter

**Turn $1 into $100 with AI on Solana**

An autonomous AI agent that hunts for money across the entire Solana ecosystem. Give it $1 and your Groq API key, and watch it autonomously claim airdrops, flip NFTs, farm yield, and do everything possible to maximize your returns.

---

## 🎯 What is Harvest?

Harvest is an AI agent that:
- ✅ Runs 24/7 autonomously
- ✅ Makes its own decisions using LLM
- ✅ Hunts for money across Solana
- ✅ Requires only $1 to start
- ✅ Sends you real-time updates

**No babysitting. No manual trading. Just pure autonomous money hunting.**

---

## 🚀 Quick Start

### 1. Get FREE Groq API Key
Visit [console.groq.com/keys](https://console.groq.com/keys) and sign up (no credit card needed)

### 2. Clone & Setup
```bash
git clone https://github.com/your-repo/harvest.git
cd harvest
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Edit .env with your keys
```

### 4. Run Agent
```bash
python agent/main.py
```

### 5. Create Your Wallet (Multi-User Mode)

Harvest now supports multiple users, each with their own isolated wallet. Set up your wallet via Telegram:

**Option A: Create New Wallet**
```
/createwallet
```
The bot will generate a new Solana wallet and send you a 12-word mnemonic phrase. **Save this phrase securely** - it's the only way to recover your wallet!

**Option B: Import Existing Wallet**
```
/importwallet your twelve word mnemonic phrase goes here like this example
```
Import your existing Solana wallet using your 12 or 24-word mnemonic phrase.

**Check Your Wallet**
```
/wallet    # View your wallet address
/balance   # Check your SOL balance
```

### 6. Fund Your Wallet

Transfer at least **0.01 SOL** to your wallet address to start trading. The bot will automatically activate trading when your balance reaches the minimum threshold.

**Minimum Balance Requirement:** 0.01 SOL
- Below 0.01 SOL: Trading paused (bot still responds to commands)
- At or above 0.01 SOL: Trading automatically activated

---

## � Wallet Management

### Available Commands

**Create New Wallet**
```
/createwallet
```
Generates a new Solana wallet with a 12-word mnemonic phrase. The bot will send you:
- Your wallet public address
- Your 12-word mnemonic phrase (save this securely!)
- Security warning about key management

**Import Existing Wallet**
```
/importwallet your twelve word mnemonic phrase goes here
```
Import an existing wallet using your 12 or 24-word mnemonic phrase. The bot will:
- Validate your mnemonic
- Associate the wallet with your Telegram account
- Confirm your wallet address

**View Wallet Address**
```
/wallet
```
Display your wallet's public address for receiving funds.

**Check Balance**
```
/balance
```
Check your current SOL balance and trading status.

**Export Private Key**
```
/exportkey
```
Retrieve your mnemonic phrase. **Use with extreme caution!** Only use this command in a private chat with the bot.

**View Performance**
```
/stats
```
View your personal trading performance metrics including:
- Total profit/loss
- Win rate
- Number of trades
- Best and worst trades
- Performance by strategy

**View Leaderboard**
```
/leaderboard
```
See anonymized rankings of top performers (no user identities revealed).

### Minimum Balance Requirement

**Trading Threshold:** 0.01 SOL

- **Below 0.01 SOL:** Trading is automatically paused
  - Bot remains online and responsive
  - All commands still work
  - You can still export your key
  - Add funds to resume trading

- **At or above 0.01 SOL:** Trading automatically activates
  - Bot scans for opportunities every 5 minutes
  - Executes profitable trades automatically
  - Sends notifications for all actions
  - You'll receive a notification when trading activates

**Automatic Activation:**
When you add funds to your wallet and your balance reaches 0.01 SOL, the bot will:
1. Detect the balance increase within the next scan cycle (5 minutes)
2. Send you a Telegram notification: "✅ Trading activated! Balance: X SOL"
3. Begin scanning for opportunities immediately

**Automatic Deactivation:**
If your balance drops below 0.01 SOL during trading:
1. Bot pauses opportunity scanning
2. Sends notification: "⚠️ Trading paused - balance below 0.01 SOL"
3. Remains online for commands
4. Will resume automatically when you add more funds

### Security Best Practices

**🔐 Protecting Your Mnemonic Phrase**

Your 12-word mnemonic phrase is the master key to your wallet. Anyone with this phrase has complete control over your funds.

**DO:**
- ✅ Write down your mnemonic phrase on paper
- ✅ Store it in a secure physical location (safe, safety deposit box)
- ✅ Keep multiple copies in different secure locations
- ✅ Use the `/exportkey` command only in private chats
- ✅ Delete the mnemonic message from Telegram after saving it
- ✅ Verify you've saved it correctly before funding the wallet

**DON'T:**
- ❌ Share your mnemonic phrase with anyone
- ❌ Store it in cloud storage (Google Drive, Dropbox, etc.)
- ❌ Take screenshots of your mnemonic phrase
- ❌ Send it via email or messaging apps
- ❌ Store it in plain text files on your computer
- ❌ Use the same mnemonic for multiple bots or services

**🛡️ Wallet Security**

- **One Wallet Per User:** Each Telegram user can only have one wallet registered
- **Isolated Funds:** Your wallet and funds are completely isolated from other users
- **Private Keys Never Shared:** Your private key never leaves the bot's secure storage
- **Encrypted Storage:** All wallet data is encrypted in the database
- **Authorization Checks:** All wallet operations verify you own the wallet

**⚠️ Risk Management**

- **Start Small:** Begin with small amounts (0.01-0.1 SOL) to test the system
- **Monitor Activity:** Check notifications and `/stats` regularly
- **Understand Risks:** Automated trading carries risks - only invest what you can afford to lose
- **Review Trades:** Use `/stats` to review performance and adjust strategies
- **Emergency Stop:** Press Ctrl+C to stop the bot, or use `/exportkey` to move funds elsewhere

**🚨 If Your Key is Compromised**

If you suspect your mnemonic phrase has been exposed:
1. Immediately use `/exportkey` to retrieve your phrase
2. Create a new wallet elsewhere (Phantom, Solflare, etc.)
3. Transfer all funds to the new wallet
4. Do NOT reuse the compromised wallet

**💡 Best Practice: Dedicated Trading Wallet**

Consider using a dedicated wallet for the bot:
- Keep only trading funds in the bot wallet (0.1-1 SOL)
- Store larger holdings in a separate hardware wallet
- Transfer profits out regularly to your main wallet
- This limits exposure if anything goes wrong

---

## 🔄 Multi-User Operation

Harvest now runs 24/7 serving multiple users simultaneously. Each user has:

**Isolated Wallet**
- Your own Solana keypair
- Your funds never mix with other users
- Complete control over your wallet

**Independent Trading**
- Bot scans for opportunities for all users
- Each user's trades execute with their own wallet
- One user's failure doesn't affect others
- Trades execute sequentially to avoid conflicts

**Personal Performance Tracking**
- Your stats show only your trades
- Leaderboard is anonymized (no user IDs)
- Historical data persists across bot restarts

**Continuous Operation**
- Bot runs 24/7 regardless of individual balances
- Remains responsive even when all users have 0 balance
- Automatically activates trading when you add funds
- No manual intervention needed

---

## 💰 What the Agent Does

### Airdrop Hunter 🎁
Automatically claims free tokens from airdrops

### NFT Flipper 💎
Buys underpriced NFTs and sells for profit

### Yield Farmer 📈
Stakes SOL and lends USDC for passive income

### Arbitrage Bot 🔄
Exploits price differences across DEXs

### Bounty Hunter 🏆
Completes on-chain tasks for rewards

---

## 📊 Example Run

```
🌾 HARVEST AGENT STARTING...
💼 Balance: 0.005 SOL ($1.00)

[10:00] 🔍 Scanning for opportunities...
[10:01] ✅ Found: Claim BONK airdrop (+$0.02)
[10:01] 🧠 Decision: Claim airdrop (free money, no risk)
[10:02] ✅ Claimed 50 BONK tokens
[10:02] 💰 Balance: 0.0052 SOL (+4%)

[10:05] 🔍 Scanning for opportunities...
[10:06] ✅ Found: Stake on Marinade (7.2% APY)
[10:06] 🧠 Decision: Stake 0.003 SOL
[10:07] ✅ Staked on Marinade
[10:07] 💰 Balance: 0.0052 SOL (earning 7.2% APY)

[10:10] 🔍 Scanning for opportunities...
[10:11] ✅ Found: NFT floor at 0.3 SOL (20% below avg)
[10:11] 🧠 Decision: Wait (not enough capital)
```

---

## 🏗️ Architecture

```
User → Onboarding UI → Agent → Strategies → Solana
                         ↓
                    Notifications
```

**Agent Loop (every 5 minutes):**
1. Scan for opportunities
2. Decide best action (using Groq LLM)
3. Execute action
4. Notify user
5. Repeat

---

## 🔧 Configuration

### Environment Variables

All configuration is done through environment variables in the `.env` file. Copy from the appropriate template:

```bash
# For development/testing
cp .env.development.template .env

# For production
cp .env.production.template .env
```

### Required Configuration

```bash
# Telegram notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# LLM provider (free from console.groq.com)
GROQ_API_KEY=your_groq_key

# Solana network
SOLANA_NETWORK=devnet  # or mainnet for production
```

### Risk Management Configuration

Control how the agent manages risk and sizes positions:

```bash
# Position sizing (Requirement 4.1-4.4)
MAX_POSITION_PCT=0.10              # Max 10% of balance per trade
HIGH_RISK_POSITION_PCT=0.05        # 5% for high-risk trades
MEDIUM_RISK_POSITION_PCT=0.10      # 10% for medium-risk trades
LOW_RISK_POSITION_PCT=0.20         # 20% for low-risk trades

# Circuit breakers (Requirement 4.5-4.7)
MAX_DAILY_LOSS_PCT=0.20            # Pause trading at 20% daily loss
MIN_BALANCE_SOL=0.1                # Maintain minimum 0.1 SOL
CONSECUTIVE_LOSS_THRESHOLD=3       # Reduce position after 3 losses
CONSECUTIVE_LOSS_REDUCTION=0.50    # Reduce by 50%
```

**Risk Management Features:**
- Automatic position sizing based on risk level
- Circuit breaker pauses trading after excessive losses
- Consecutive loss tracking reduces position sizes
- Minimum balance protection for transaction fees

### Fee and Slippage Configuration

Optimize transaction costs and protect against slippage:

```bash
# Priority fees (Requirement 6.1-6.6)
PRIORITY_FEE_THRESHOLD=0.001       # Congestion threshold (SOL)
PRIORITY_FEE_INCREASE=0.50         # Increase fee 50% on retry
MAX_FEE_PCT_OF_PROFIT=0.05         # Skip if fees > 5% of profit

# Slippage protection (Requirement 7.1-7.5)
SLIPPAGE_BPS=100                   # 1% slippage tolerance
HIGH_VOLATILITY_SLIPPAGE_BPS=200   # 2% during high volatility
MAX_PRICE_IMPACT_PCT=0.02          # Skip if impact > 2%
```

**Fee Optimization:**
- Queries priority fees before transactions
- Delays non-urgent trades during congestion
- Skips trades where fees eat into profits
- Adaptive fee increases on retry

**Slippage Protection:**
- Configurable slippage tolerance (1-2%)
- Automatic adjustment during volatility
- Price impact checking before execution
- Transaction reverts if slippage exceeded

### Scan Interval Configuration

Control how frequently the agent scans for opportunities:

```bash
# Rate limiting (Requirement 9.4-9.6)
SCAN_INTERVAL=300                  # Base interval (5 minutes)
MIN_SCAN_INTERVAL=5                # Minimum 5 seconds between scans
RATE_LIMIT_INTERVAL_INCREASE=0.50  # Increase 50% on rate limits
EMPTY_SCAN_THRESHOLD=10            # Empty scans before slowdown
EMPTY_SCAN_INTERVAL=30             # 30s interval after empty scans
```

**Adaptive Scanning:**
- Minimum 5-second delay between scans
- Automatically increases interval on rate limits
- Slows down after consecutive empty scans
- Resumes normal speed when opportunities found

### Strategy Configuration

Enable or disable individual trading strategies:

```bash
# Strategy enable/disable flags
ENABLE_JUPITER_SWAP=true           # Token swaps and arbitrage
ENABLE_MARINADE_STAKE=true         # Liquid staking
ENABLE_AIRDROP_HUNTER=true         # Airdrop claiming
```

**Available Strategies:**
- **Jupiter Swap**: Executes token swaps and cross-DEX arbitrage
- **Marinade Stake**: Stakes SOL for yield while maintaining liquidity
- **Airdrop Hunter**: Automatically claims eligible airdrops

### Transaction Execution Configuration

Control transaction confirmation and retry behavior:

```bash
# Confirmation and retries (Requirement 1.3-1.6)
CONFIRMATION_TIMEOUT=60            # Wait 60s for confirmation
MAX_RETRIES=3                      # Retry up to 3 times
```

### Performance Tuning

For high-volume operations (500+ users):

```bash
# Multi-API scaling
HELIUS_API_KEY_1=key1
HELIUS_API_KEY_2=key2
HELIUS_API_KEY_3=key3

# Caching
PRICE_CACHE_TTL=60                 # Cache prices for 60s
STRATEGY_CACHE_TTL=30              # Cache strategy results for 30s

# Batching
RPC_BATCH_SIZE=10                  # Batch 10 users per RPC call
SCAN_STAGGER_WINDOW=60             # Spread scans over 60s
```

---

## 🚀 Running the Agent

### Development Mode

For testing on Solana devnet with test tokens:

```bash
# 1. Set up environment
cp .env.development.template .env
# Edit .env with your credentials

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run agent
python -m harvest.agent.main
```

The agent will:
- Auto-generate a devnet wallet if needed
- Request test SOL airdrops automatically
- Scan for opportunities every 60 seconds
- Send notifications via Telegram

### Production Mode

For real trading on Solana mainnet:

```bash
# 1. Set up environment
cp .env.production.template .env
# Edit .env with your credentials
# Set SOLANA_NETWORK=mainnet

# 2. Fund your wallet
# Transfer SOL to your wallet address

# 3. Start with small amounts
# Set conservative risk parameters initially

# 4. Run agent
python -m harvest.agent.main
```

**Production Checklist:**
- ✅ Wallet funded with sufficient SOL
- ✅ Risk parameters configured conservatively
- ✅ All required API keys set
- ✅ Telegram notifications working
- ✅ Monitoring and alerts configured

### Running Specific Strategies

Disable strategies you don't want to use:

```bash
# Only run Jupiter swaps
ENABLE_JUPITER_SWAP=true
ENABLE_MARINADE_STAKE=false
ENABLE_AIRDROP_HUNTER=false
```

### Monitoring

The agent logs all activity to:
- Console (real-time)
- `logs/harvest_YYYY-MM-DD.log` (daily files)
- Telegram notifications (important events)

**What gets logged:**
- Opportunity detections with expected profit
- Trade executions with actual profit
- Risk limit violations and circuit breakers
- Errors with full context
- Performance metrics every 100 trades

---

## 🛡️ Risk Management Features

### Position Sizing

The agent automatically sizes positions based on risk:

| Risk Level | Position Size | Use Case |
|------------|---------------|----------|
| High | 5% of balance | Experimental strategies |
| Medium | 10% of balance | Standard trades |
| Low | 20% of balance | Proven opportunities |

**Absolute maximum:** 10% of balance per trade (configurable)

### Circuit Breakers

Automatic trading pauses protect your capital:

1. **Minimum Balance**: Pauses when balance < 0.1 SOL
2. **Daily Loss Limit**: Pauses for 24h after 20% daily loss
3. **Consecutive Losses**: Reduces position 50% after 3 losses

**Manual Override:**
- Stop: Press Ctrl+C to gracefully shut down
- Pause: Set `MAX_POSITION_PCT=0` to pause trading
- Resume: Restore original `MAX_POSITION_PCT` value

### Performance Tracking

The agent learns from every trade:

- Records expected vs actual profit
- Calculates win rate per strategy
- Adjusts allocations based on performance
- Persists data across restarts

**Adaptive Allocation:**
- Winning strategies get more capital
- Losing strategies get less capital
- Based on last 10 trades per strategy

---

## 🔍 Troubleshooting Guide

### Agent Won't Start

**Problem:** Missing environment variables

```
❌ Configuration Error: Missing required environment variables
```

**Solution:**
1. Check `.env` file exists
2. Verify all required variables are set
3. Compare with `.env.production.template`

---

**Problem:** Python version too old

```
❌ Python 3.8+ required, found 3.7
```

**Solution:**
```bash
# Install Python 3.8+
python3 --version  # Check version
# Update Python if needed
```

---

### No Opportunities Found

**Problem:** Agent scans but finds nothing

```
[10:00] 🔍 Scanning for opportunities...
[10:01] No opportunities found
```

**Possible Causes:**
1. **Market conditions**: No profitable opportunities exist
2. **Risk limits**: Opportunities rejected by risk manager
3. **Disabled strategies**: Check `ENABLE_*` flags
4. **Insufficient balance**: Need more SOL for trades

**Solutions:**
- Wait for better market conditions
- Lower risk thresholds (carefully!)
- Enable more strategies
- Add more capital to wallet

---

### Transactions Failing

**Problem:** Transactions submitted but fail

```
❌ Transaction failed: Blockhash expired
```

**Solutions:**
1. **Blockhash expiration**: Agent auto-retries with fresh blockhash
2. **Insufficient priority fee**: Agent increases fee 50% on retry
3. **Network congestion**: Agent delays non-urgent transactions
4. **Insufficient balance**: Add more SOL to wallet

**Check RPC endpoint:**
```bash
# Test RPC connection
curl https://api.mainnet-beta.solana.com -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"getHealth"}'
```

---

### High Gas Fees

**Problem:** Fees eating into profits

```
⚠️  Skipping trade: gas fees > 5% of expected profit
```

**This is normal!** The agent protects you by skipping unprofitable trades.

**To adjust:**
```bash
# Allow higher fees (not recommended)
MAX_FEE_PCT_OF_PROFIT=0.10  # 10% instead of 5%
```

---

### Slippage Errors

**Problem:** Trades reverting due to slippage

```
❌ Transaction failed: Slippage tolerance exceeded
```

**Solutions:**
1. **Increase slippage tolerance** (carefully):
```bash
SLIPPAGE_BPS=200  # 2% instead of 1%
```

2. **Reduce position sizes** to lower price impact:
```bash
MAX_POSITION_PCT=0.05  # 5% instead of 10%
```

3. **Wait for better liquidity** - agent will retry later

---

### Rate Limiting

**Problem:** API rate limits hit

```
⚠️  Rate limit hit, increasing scan interval by 50%
```

**This is normal!** The agent adapts automatically.

**To reduce rate limits:**
1. **Add more API keys**:
```bash
HELIUS_API_KEY_1=key1
HELIUS_API_KEY_2=key2
HELIUS_API_KEY_3=key3
```

2. **Increase scan interval**:
```bash
SCAN_INTERVAL=600  # 10 minutes instead of 5
```

3. **Enable caching**:
```bash
PRICE_CACHE_TTL=120  # Cache prices for 2 minutes
```

---

### Circuit Breaker Activated

**Problem:** Trading paused automatically

```
⚠️  Circuit breaker activated: Daily loss limit exceeded
Trading paused for 24 hours
```

**This is a safety feature!** It protects your capital.

**What happened:**
- Daily losses exceeded 20% threshold
- Agent paused all trading for 24 hours
- Will resume automatically after cooldown

**To override** (not recommended):
```bash
# Increase daily loss limit (risky!)
MAX_DAILY_LOSS_PCT=0.30  # 30% instead of 20%
```

---

### Performance Issues

**Problem:** Agent running slowly

**Solutions:**

1. **Enable caching**:
```bash
PRICE_CACHE_TTL=60
STRATEGY_CACHE_TTL=30
```

2. **Use Helius RPC**:
```bash
HELIUS_API_KEY=your_key_here
```

3. **Reduce scan frequency**:
```bash
SCAN_INTERVAL=600  # 10 minutes
```

4. **Disable unused strategies**:
```bash
ENABLE_AIRDROP_HUNTER=false  # If not needed
```

---

### Wallet Issues

**Problem:** Can't access wallet

```
❌ Critical Error: Wallet access failure
```

**Solutions:**
1. Check `WALLET_PRIVATE_KEY` is set correctly
2. Verify wallet has sufficient SOL
3. Check wallet permissions
4. Try regenerating wallet (devnet only!)

---

**Problem:** Already have a wallet registered

```
❌ You already have a wallet registered
```

**This is a security feature!** Each user can only have one wallet.

**Solutions:**
1. Use `/wallet` to view your current wallet address
2. Use `/exportkey` to retrieve your mnemonic phrase
3. If you want to use a different wallet:
   - Export your current wallet's key
   - Transfer funds out
   - Contact admin to reset your wallet (if needed)

---

**Problem:** Invalid mnemonic phrase

```
❌ Invalid mnemonic phrase. Please check and try again.
```

**Solutions:**
1. Verify you have exactly 12 or 24 words
2. Check for typos in the words
3. Ensure words are separated by single spaces
4. Use lowercase letters only
5. Verify words are from the BIP39 word list

---

**Problem:** No wallet registered

```
❌ You don't have a wallet registered. Use /createwallet or /importwallet first.
```

**Solution:**
Create or import a wallet before using trading commands:
```
/createwallet
# or
/importwallet your twelve word mnemonic phrase here
```

---

**Problem:** Trading not starting after funding wallet

```
Balance: 0.05 SOL but no trades executing
```

**Solutions:**
1. Wait for next scan cycle (up to 5 minutes)
2. Check if strategies are enabled in `.env`
3. Verify market conditions (may be no opportunities)
4. Check logs for errors: `logs/harvest_YYYY-MM-DD.log`
5. Ensure balance is actually >= 0.01 SOL with `/balance`

---

### Getting Help

If you're still stuck:

1. **Check logs**: `logs/harvest_YYYY-MM-DD.log`
2. **Enable debug logging**:
```bash
LOG_LEVEL=DEBUG
CONSOLE_LOG_LEVEL=DEBUG
```
3. **Open an issue**: Include logs and configuration (redact keys!)
4. **Join Discord**: Get help from the community

---

## 📱 Notifications

Get real-time updates via:
- **Telegram** (recommended)
- **Discord**

Example notification:
```
💰 HARVEST UPDATE

Action: Claimed airdrop
Tokens: 50 BONK
Value: +$0.02
Balance: 0.0052 SOL (+4%)

Next scan in 5 minutes...
```

---

## 🛡️ Security

- Your wallet stays in your control
- Agent only gets signing permission
- All transactions visible on-chain
- Can pause/stop anytime
- Risk controls built-in

---

## 📈 Performance

**Goal:** Turn $1 into $100 in 30 days (100x)

**Realistic:** $1 → $10-$20 in 30 days (10-20x)

**How:**
- Airdrops: $0.10-$5 per claim
- NFT flips: 10-50% profit per flip
- Yield farming: 0.02-0.05% daily
- Arbitrage: $0.01-$0.10 per trade

---

## 🧪 Development

### Run Tests
```bash
pytest tests/
```

### Run Locally
```bash
python agent/main.py
```

### Deploy
```bash
./scripts/deploy.sh
```

---

## 📚 Documentation

- [Agent Architecture](agent/README.md) - Code organization and design
- [Configuration Guide](.env.production.template) - Environment setup
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) - Production deployment guide
- [Testing Guide](tests/) - Running tests
- [Monitoring & Logging](MONITORING_LOGGING_IMPLEMENTATION.md) - Observability setup
- [Scaling Guide](SCALING.md) - Multi-user scaling

---

## 🏆 Project Background

**Built for Colosseum Agent Hackathon** (Feb 2-12, 2026)

An autonomous AI agent that demonstrates truly agentic behavior - making independent decisions, learning from outcomes, and adapting strategies in real-time.

---

## 🤝 Contributing

This is a hackathon project, but contributions welcome!

1. Fork the repo
2. Create feature branch
3. Make changes
4. Submit PR

---

## 📄 License

MIT License - see LICENSE file

---

## 🔗 Links

- **GitHub:** https://github.com/yourusername/harvest
- **Documentation:** See docs/ folder
- **Issues:** https://github.com/yourusername/harvest/issues

---

## ⚠️ Disclaimer

This is experimental software for educational purposes. Use at your own risk. Not financial advice. Always do your own research before investing.

---

**Built with ❤️ for the Solana ecosystem**

🌾 Give $1. Let it roam. Make $100. 🚀
