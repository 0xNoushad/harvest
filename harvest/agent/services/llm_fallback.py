"""
LLM Fallback Manager

Provides automatic fallback between multiple LLM providers:
- Groq (primary, free tier)
- OpenRouter (fallback, pay-as-you-go)
- Local fallback (simple rule-based decisions)

Handles rate limiting and quota exhaustion gracefully.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import asyncio
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class LLMProvider:
    """LLM provider configuration."""
    name: str
    priority: int
    is_available: bool = True
    failure_count: int = 0
    max_failures: int = 3
    requests_today: int = 0
    daily_limit: Optional[int] = None


class LLMFallbackManager:
    """
    Manages multiple LLM providers with automatic fallback.
    
    Priority order:
    1. Groq (free, 14,400 req/day)
    2. OpenRouter (paid, unlimited)
    3. Local rules (free, always available)
    """
    
    def __init__(self):
        """Initialize LLM fallback manager."""
        self.providers: List[LLMProvider] = []
        self._setup_providers()
        
        # Import providers
        self.groq_client = None
        self.openrouter_client = None
        
        self._init_clients()
        
        logger.info(f"Initialized LLM fallback with {len(self.providers)} providers")
    
    def _setup_providers(self):
        """Setup LLM providers in priority order."""
        # Primary: Groq (free tier)
        if os.getenv("GROQ_API_KEY"):
            self.providers.append(LLMProvider(
                name="Groq",
                priority=1,
                daily_limit=14400  # Free tier limit
            ))
        
        # Fallback 1: OpenRouter (paid)
        if os.getenv("OPENROUTER_API_KEY"):
            self.providers.append(LLMProvider(
                name="OpenRouter",
                priority=2,
                daily_limit=None  # Unlimited (paid)
            ))
        
        # Fallback 2: Local rules (always available)
        self.providers.append(LLMProvider(
            name="LocalRules",
            priority=3,
            daily_limit=None  # Unlimited
        ))
        
        self.providers.sort(key=lambda p: p.priority)
    
    def _init_clients(self):
        """Initialize API clients."""
        try:
            from groq import AsyncGroq
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                self.groq_client = AsyncGroq(api_key=groq_key)
        except ImportError:
            logger.warning("Groq client not available")
        
        # OpenRouter uses standard OpenAI-compatible API
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.openrouter_client = openrouter_key  # Will use aiohttp
    
    def get_current_provider(self) -> LLMProvider:
        """Get the current best available provider."""
        for provider in self.providers:
            # Check if available
            if not provider.is_available:
                continue
            
            # Check daily limit
            if provider.daily_limit and provider.requests_today >= provider.daily_limit:
                logger.warning(f"{provider.name} daily limit reached")
                continue
            
            return provider
        
        # If all failed, reset and use local rules
        logger.warning("All LLM providers exhausted, using local rules")
        return next(p for p in self.providers if p.name == "LocalRules")
    
    async def make_decision(
        self,
        opportunity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make decision about an opportunity with fallback.
        
        Args:
            opportunity: Opportunity details
        
        Returns:
            Decision dict with action, reasoning, confidence
        """
        provider = self.get_current_provider()
        
        try:
            if provider.name == "Groq":
                decision = await self._call_groq(opportunity)
            elif provider.name == "OpenRouter":
                decision = await self._call_openrouter(opportunity)
            else:
                decision = self._local_rules(opportunity)
            
            # Success
            provider.failure_count = 0
            provider.requests_today += 1
            
            return decision
        
        except Exception as e:
            logger.error(f"LLM call failed on {provider.name}: {e}")
            provider.failure_count += 1
            
            if provider.failure_count >= provider.max_failures:
                provider.is_available = False
                logger.error(f"Marking {provider.name} as unavailable")
            
            # Try next provider
            return await self.make_decision(opportunity)
    
    async def _call_groq(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Call Groq API."""
        if not self.groq_client:
            raise Exception("Groq client not initialized")
        
        prompt = self._build_prompt(opportunity)
        
        response = await self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.7,
        )
        
        content = response.choices[0].message.content
        return self._parse_decision(content)
    
    async def _call_openrouter(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenRouter API."""
        if not self.openrouter_client:
            raise Exception("OpenRouter client not initialized")
        
        prompt = self._build_prompt(opportunity)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_client}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3.1-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    raise Exception(f"OpenRouter API error: {response.status}")
                
                data = await response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_decision(content)
    
    def _local_rules(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simple rule-based decision making (no API needed).
        
        Rules:
        - High risk + low profit = skip
        - Low risk + high profit = execute
        - Everything else = notify user
        """
        risk = opportunity.get("risk_level", "medium").lower()
        profit = opportunity.get("expected_profit", 0)
        amount = opportunity.get("amount", 0)
        
        # Calculate profit ratio
        profit_ratio = profit / amount if amount > 0 else 0
        
        # Decision logic
        if risk == "high" and profit_ratio < 0.1:
            return {
                "action": "skip",
                "reasoning": "High risk with low profit ratio (<10%)",
                "confidence": 0.8
            }
        
        if risk == "low" and profit_ratio > 0.2:
            return {
                "action": "execute",
                "reasoning": "Low risk with high profit ratio (>20%)",
                "confidence": 0.7
            }
        
        # Default to notify for user approval
        return {
            "action": "notify",
            "reasoning": f"Medium confidence opportunity ({risk} risk, {profit_ratio:.1%} profit)",
            "confidence": 0.5
        }
    
    def _build_prompt(self, opportunity: Dict[str, Any]) -> str:
        """Build decision prompt."""
        return f"""Evaluate this crypto opportunity and decide: execute, notify, or skip.

Opportunity:
- Strategy: {opportunity.get('strategy_name')}
- Action: {opportunity.get('action')}
- Amount: {opportunity.get('amount')} SOL
- Expected Profit: {opportunity.get('expected_profit')} SOL
- Risk Level: {opportunity.get('risk_level')}

Respond in JSON:
{{
  "action": "execute|notify|skip",
  "reasoning": "brief explanation",
  "confidence": 0.0-1.0
}}"""
    
    def _parse_decision(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into decision."""
        import json
        
        try:
            # Extract JSON from response
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
            else:
                json_str = content
            
            data = json.loads(json_str)
            
            return {
                "action": data.get("action", "notify"),
                "reasoning": data.get("reasoning", "No reasoning provided"),
                "confidence": float(data.get("confidence", 0.5))
            }
        
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return {
                "action": "notify",
                "reasoning": "Failed to parse LLM response",
                "confidence": 0.0
            }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available,
                    "requests_today": p.requests_today,
                    "daily_limit": p.daily_limit,
                    "failures": p.failure_count
                }
                for p in self.providers
            ],
            "current": self.get_current_provider().name
        }
    
    def reset_daily_counters(self):
        """Reset daily request counters (call at midnight)."""
        for provider in self.providers:
            provider.requests_today = 0
            provider.is_available = True
            provider.failure_count = 0
        
        logger.info("Reset daily LLM counters")
