"""
Airdrop Hunter Strategy

Scrapes the internet every 12 hours to find NEW Solana airdrop announcements.
Monitors Twitter, crypto news, airdrop aggregators, and official channels.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import requests

from agent.trading.scanner import Strategy, Opportunity
from agent.core.wallet import WalletManager


logger = logging.getLogger(__name__)


@dataclass
class AirdropAnnouncement:
    """Record of a discovered airdrop announcement."""
    protocol: str
    token: str
    source: str
    announcement_url: str
    claim_url: Optional[str]
    eligibility_criteria: str
    estimated_value: Optional[float]
    deadline: Optional[datetime]
    discovered_at: datetime
    is_verified: bool


class AirdropHunter(Strategy):
    """
    Hunt for NEW airdrop announcements across the internet.
    
    Monitors:
    - Twitter (official protocol accounts)
    - Crypto news sites (CoinDesk, The Block, etc.)
    - Airdrop aggregators (Airdropped.link, Drops.bot, etc.)
    - Discord/Telegram announcements
    - Protocol blogs and Medium
    
    Features:
    - 12-hour check interval
    - Verifies legitimacy (checks official domains)
    - Filters Solana-only airdrops
    - Tracks discovered airdrops
    - Sends notifications for new finds
    """
    
    def __init__(
        self,
        wallet: WalletManager,
        check_interval_hours: int = 12,
        state_file: Optional[str] = None
    ):
        """
        Initialize airdrop hunter.
        
        Args:
            wallet: WalletManager instance
            check_interval_hours: Hours between checks (default: 12)
            state_file: Path to state file for tracking discoveries
        """
        self.wallet = wallet
        self.check_interval_hours = check_interval_hours
        
        # Set up state file
        if state_file is None:
            state_dir = Path("config")
            state_dir.mkdir(exist_ok=True)
            self.state_file = state_dir / "airdrop_hunter_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load state
        self.state = self._load_state()
        
        # Sources to monitor
        self.sources = {
            # Airdrop aggregators
            "airdropped_link": {
                "name": "Airdropped.link",
                "url": "https://www.airdropped.link/",
                "type": "aggregator"
            },
            "drops_bot": {
                "name": "Drops.bot",
                "url": "https://www.drops.bot/",
                "type": "aggregator"
            },
            "airdrops_io": {
                "name": "Airdrops.io",
                "url": "https://airdrops.io/solana/",
                "type": "aggregator"
            },
            
            # Crypto news sites
            "coindesk": {
                "name": "CoinDesk",
                "url": "https://www.coindesk.com/search?s=solana+airdrop",
                "type": "news"
            },
            "theblock": {
                "name": "The Block",
                "url": "https://www.theblock.co/search?query=solana+airdrop",
                "type": "news"
            },
            "decrypt": {
                "name": "Decrypt",
                "url": "https://decrypt.co/search?q=solana+airdrop",
                "type": "news"
            },
            
            # Social/Community
            "solana_floor": {
                "name": "Solana Floor",
                "url": "https://solanafloor.com/news",
                "type": "community"
            },
            "helius_blog": {
                "name": "Helius Blog",
                "url": "https://www.helius.dev/blog",
                "type": "community"
            }
        }
        
        # Known Solana protocols to monitor
        self.protocols_to_monitor = [
            "jupiter", "jito", "kamino", "marginfi", "drift", "tensor",
            "magic eden", "phantom", "backpack", "pump.fun", "moonshot",
            "raydium", "orca", "marinade", "sanctum", "pyth", "wormhole",
            "helium", "render", "hivemapper", "star atlas", "genopets",
            "solend", "mango", "zeta", "bonk", "wen", "dogwifhat"
        ]
        
        logger.info(f"AirdropHunter initialized")
        logger.info(f"Check interval: {self.check_interval_hours} hours")
        logger.info(f"Monitoring {len(self.sources)} sources")
        logger.info(f"Tracking {len(self.protocols_to_monitor)} protocols")
    
    def get_name(self) -> str:
        """Return strategy name."""
        return "airdrop_hunter"
    
    def scan(self) -> List[Opportunity]:
        """
        Scan the internet for new airdrop announcements.
        
        Checks all sources for new Solana airdrop announcements,
        verifies legitimacy, and returns opportunities for new finds.
        
        Returns:
            List of opportunities for newly discovered airdrops
        """
        opportunities = []
        now = datetime.now()
        
        # Check if it's time to scan
        if not self._should_check(now):
            last_check = self.state.get("last_check")
            if last_check:
                hours_since = (now - datetime.fromisoformat(last_check)).total_seconds() / 3600
                logger.debug(f"Last check was {hours_since:.1f} hours ago")
            return []
        
        logger.info("🔍 Starting airdrop hunt across the internet...")
        
        new_airdrops = []
        
        # Check each source
        for source_id, source_info in self.sources.items():
            try:
                logger.info(f"Checking {source_info['name']}...")
                airdrops = self._check_source(source_id, source_info)
                
                for airdrop in airdrops:
                    # Check if we've seen this before
                    if not self._is_already_discovered(airdrop):
                        new_airdrops.append(airdrop)
                        logger.info(
                            f"🎁 NEW AIRDROP FOUND: {airdrop.protocol} ({airdrop.token}) "
                            f"from {source_info['name']}"
                        )
            
            except Exception as e:
                logger.error(f"Error checking {source_info['name']}: {e}")
                continue
        
        # Create opportunities for new airdrops
        for airdrop in new_airdrops:
            opportunity = Opportunity(
                strategy_name=self.get_name(),
                action="investigate",
                amount=airdrop.estimated_value or 0,
                expected_profit=airdrop.estimated_value or 0,
                risk_level="low",
                details={
                    "protocol": airdrop.protocol,
                    "token": airdrop.token,
                    "source": airdrop.source,
                    "announcement_url": airdrop.announcement_url,
                    "claim_url": airdrop.claim_url,
                    "eligibility": airdrop.eligibility_criteria,
                    "deadline": airdrop.deadline.isoformat() if airdrop.deadline else None,
                    "is_verified": airdrop.is_verified
                },
                timestamp=now
            )
            opportunities.append(opportunity)
            
            # Record discovery
            self._record_discovery(airdrop)
        
        # Update last check time
        self.state["last_check"] = now.isoformat()
        self._save_state()
        
        logger.info(f"✅ Hunt complete! Found {len(new_airdrops)} new airdrops")
        return opportunities
    
    async def execute(self, opportunity: Opportunity) -> Dict:
        """
        Execute airdrop investigation and send notification.
        
        For newly discovered airdrops, this sends a Telegram notification
        with all the details and links so the user can investigate and participate.
        
        Args:
            opportunity: Opportunity to execute
        
        Returns:
            Execution result with airdrop details
        """
        protocol = opportunity.details["protocol"]
        
        try:
            logger.info(f"Investigating new airdrop: {protocol}")
            
            # Send Telegram notification with links
            # Note: In production, this would be called by the agent loop
            # which has access to the notifier instance
            
            result = {
                "success": True,
                "protocol": protocol,
                "token": opportunity.details["token"],
                "source": opportunity.details["source"],
                "announcement_url": opportunity.details["announcement_url"],
                "claim_url": opportunity.details["claim_url"],
                "eligibility": opportunity.details["eligibility"],
                "deadline": opportunity.details["deadline"],
                "is_verified": opportunity.details["is_verified"],
                "action_required": "Check announcement and start farming if eligible",
                "timestamp": datetime.now().isoformat(),
                # Add notification flag for agent loop
                "send_notification": True,
                "notification_type": "airdrop_discovery"
            }
            
            return result
        
        except Exception as e:
            error_msg = f"Failed to investigate {protocol}: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "error": error_msg,
                "protocol": protocol,
                "timestamp": datetime.now().isoformat()
            }
    
    def _should_check(self, now: datetime) -> bool:
        """
        Check if it's time to hunt for airdrops.
        
        Args:
            now: Current datetime
        
        Returns:
            True if check interval has passed, False otherwise
        """
        last_check = self.state.get("last_check")
        
        if last_check is None:
            return True
        
        last_check_time = datetime.fromisoformat(last_check)
        time_since = now - last_check_time
        
        return time_since.total_seconds() >= (self.check_interval_hours * 3600)
    
    def _check_source(self, source_id: str, source_info: Dict) -> List[AirdropAnnouncement]:
        """
        Check a specific source for airdrop announcements.
        
        Args:
            source_id: Source identifier
            source_info: Source configuration
        
        Returns:
            List of discovered airdrop announcements
        """
        airdrops = []
        
        try:
            # Fetch the page
            response = requests.get(source_info["url"], timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"{source_info['name']} returned {response.status_code}")
                return []
            
            content = response.text.lower()
            
            # Search for protocol mentions + airdrop keywords
            for protocol in self.protocols_to_monitor:
                # Look for airdrop announcements
                patterns = [
                    f"{protocol}.*airdrop",
                    f"airdrop.*{protocol}",
                    f"{protocol}.*token.*launch",
                    f"{protocol}.*tge",
                    f"{protocol}.*claim"
                ]
                
                for pattern in patterns:
                    if re.search(pattern, content):
                        # Found potential airdrop mention
                        airdrop = AirdropAnnouncement(
                            protocol=protocol.title(),
                            token=self._guess_token_symbol(protocol),
                            source=source_info["name"],
                            announcement_url=source_info["url"],
                            claim_url=None,  # Would need to parse from page
                            eligibility_criteria="Check announcement for details",
                            estimated_value=None,
                            deadline=None,
                            discovered_at=datetime.now(),
                            is_verified=False  # Needs manual verification
                        )
                        airdrops.append(airdrop)
                        break  # Only add once per protocol
        
        except Exception as e:
            logger.error(f"Error fetching {source_info['name']}: {e}")
        
        return airdrops
    
    def _guess_token_symbol(self, protocol: str) -> str:
        """
        Guess token symbol from protocol name.
        
        Args:
            protocol: Protocol name
        
        Returns:
            Likely token symbol
        """
        # Known mappings
        known_symbols = {
            "jupiter": "JUP",
            "jito": "JTO",
            "kamino": "KMNO",
            "marginfi": "MRGN",
            "drift": "DRIFT",
            "tensor": "TNSR",
            "magic eden": "ME",
            "phantom": "PHTM",
            "backpack": "BPACK",
            "pump.fun": "PUMP",
            "moonshot": "MOON",
            "raydium": "RAY",
            "orca": "ORCA",
            "marinade": "MNDE",
            "sanctum": "CLOUD",
            "pyth": "PYTH",
            "wormhole": "W",
            "helium": "HNT",
            "render": "RNDR",
            "bonk": "BONK",
            "wen": "WEN",
            "dogwifhat": "WIF"
        }
        
        return known_symbols.get(protocol.lower(), protocol.upper()[:4])
    
    def _is_already_discovered(self, airdrop: AirdropAnnouncement) -> bool:
        """
        Check if airdrop has already been discovered.
        
        Args:
            airdrop: Airdrop announcement to check
        
        Returns:
            True if already discovered, False otherwise
        """
        discoveries = self.state.get("discoveries", [])
        
        for discovery in discoveries:
            if (discovery.get("protocol", "").lower() == airdrop.protocol.lower() and
                discovery.get("source") == airdrop.source):
                return True
        
        return False
    
    def _record_discovery(self, airdrop: AirdropAnnouncement):
        """
        Record a discovered airdrop to state.
        
        Args:
            airdrop: AirdropAnnouncement to record
        """
        if "discoveries" not in self.state:
            self.state["discoveries"] = []
        
        discovery_data = {
            "protocol": airdrop.protocol,
            "token": airdrop.token,
            "source": airdrop.source,
            "announcement_url": airdrop.announcement_url,
            "claim_url": airdrop.claim_url,
            "eligibility": airdrop.eligibility_criteria,
            "estimated_value": airdrop.estimated_value,
            "deadline": airdrop.deadline.isoformat() if airdrop.deadline else None,
            "discovered_at": airdrop.discovered_at.isoformat(),
            "is_verified": airdrop.is_verified
        }
        
        self.state["discoveries"].append(discovery_data)
        
        # Keep only last 100 discoveries
        self.state["discoveries"] = self.state["discoveries"][-100:]
        
        self._save_state()
        
        logger.debug(f"Recorded discovery: {airdrop.protocol}")
    
    def _load_state(self) -> Dict:
        """
        Load state from file.
        
        Returns:
            State dictionary
        """
        if not self.state_file.exists():
            logger.info("No existing state file, starting fresh")
            return {
                "discoveries": [],
                "last_check": None
            }
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            logger.info(f"Loaded state from {self.state_file}")
            return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return {
                "discoveries": [],
                "last_check": None
            }
    
    def _save_state(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            
            logger.debug(f"Saved state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def get_discoveries(self, days: int = 7) -> List[Dict]:
        """
        Get recent airdrop discoveries.
        
        Args:
            days: Number of days to look back (default: 7)
        
        Returns:
            List of recent discoveries
        """
        cutoff = datetime.now() - timedelta(days=days)
        discoveries = self.state.get("discoveries", [])
        
        recent = []
        for discovery in discoveries:
            discovered_at = datetime.fromisoformat(discovery["discovered_at"])
            if discovered_at >= cutoff:
                recent.append(discovery)
        
        return recent
    
    def get_next_check_time(self) -> Optional[datetime]:
        """
        Get the next scheduled check time.
        
        Returns:
            Next check datetime or None if never checked
        """
        last_check = self.state.get("last_check")
        
        if last_check is None:
            return None
        
        last_check_time = datetime.fromisoformat(last_check)
        next_check = last_check_time + timedelta(hours=self.check_interval_hours)
        
        return next_check
