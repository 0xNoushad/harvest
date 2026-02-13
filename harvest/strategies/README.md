# Harvest Trading Strategies

This directory contains all trading strategies for the Harvest autonomous agent.

## Available Strategies

### 1. Airdrop Farmer (`airdrop_farmer.py`)

**Status**: ✅ Implemented

**Purpose**: Interact with DeFi protocols weekly to qualify for potential airdrops

**Supported Protocols**:
- Drift (perpetual futures)
- MarginFi (lending/borrowing)
- Kamino (yield vaults)

**Key Features**:
- Weekly scheduling with configurable intervals
- Small transactions (0.01 SOL/USDC default)
- State persistence for tracking interactions
- Graceful error handling (continues with other protocols if one fails)
- Transaction hash logging for all interactions

**Usage**:
```python
from harvest.strategies import AirdropFarmer

farmer = AirdropFarmer(
    wallet=wallet,
    protocols=["drift", "marginfi", "kamino"],
    interaction_amount=0.01,
    interaction_interval_days=7
)

# Scan for opportunities
opportunities = farmer.scan()

# Execute interactions
for opp in opportunities:
    result = await farmer.execute(opp)
```

**Documentation**: See `harvest/docs/AIRDROP_FARMING.md`

**Tests**: `harvest/tests/test_airdrop_farmer.py` (10 tests, all passing)

**Demo**: `harvest/examples/demo_airdrop_farmer.py`

---

## Strategy Interface

All strategies implement the `Strategy` abstract base class:

```python
from abc import ABC, abstractmethod
from typing import List
from harvest.agent.scanner import Opportunity

class Strategy(ABC):
    @abstractmethod
    def scan(self) -> List[Opportunity]:
        """Scan for opportunities."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return strategy name."""
        pass
```

## Creating a New Strategy

1. Create a new file in this directory (e.g., `my_strategy.py`)
2. Import the Strategy base class: `from harvest.agent.scanner import Strategy`
3. Implement the required methods: `scan()` and `get_name()`
4. Add an optional `execute()` method for execution logic
5. Export the strategy in `__init__.py`
6. Write tests in `harvest/tests/test_my_strategy.py`
7. Create documentation in `harvest/docs/MY_STRATEGY.md`

## Upcoming Strategies

The following strategies are planned for implementation:

### 2. Airdrop Claimer
- Claims and sells airdrops when available
- Hourly checks for claimable tokens
- Automatic selling on Jupiter DEX

### 3. Liquid Staking
- Stakes idle SOL on Marinade
- Minimum threshold: 0.1 SOL
- Receives mSOL tokens

### 4. Yield Farmer
- Deposits stablecoins in Kamino vaults
- Selects highest APY vaults
- Auto-compounds rewards weekly

### 5. NFT Flipper
- Buys underpriced NFTs on Magic Eden
- 10% profit threshold
- Lists at floor price for quick sale

### 6. Arbitrage Trader
- Exploits price differences across DEXs
- Monitors Jupiter and Orca
- 0.5% minimum profit threshold

## Testing

Run all strategy tests:
```bash
python -m pytest harvest/tests/test_*.py -v
```

Run specific strategy tests:
```bash
python -m pytest harvest/tests/test_airdrop_farmer.py -v
```

## Integration

Strategies integrate with the main agent loop via the Scanner:

```python
from harvest.agent.scanner import Scanner
from harvest.strategies import AirdropFarmer

# Create strategies
strategies = [
    AirdropFarmer(wallet=wallet),
    # Add more strategies here
]

# Create scanner
scanner = Scanner(strategies=strategies)

# Scan all strategies
opportunities = scanner.scan_all()
```

## Requirements Mapping

Each strategy implements specific requirements from the design document:

- **Airdrop Farmer**: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
- **Airdrop Claimer**: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
- **Liquid Staking**: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
- **Yield Farmer**: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
- **NFT Flipper**: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
- **Arbitrage Trader**: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
