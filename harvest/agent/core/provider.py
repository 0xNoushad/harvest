"""LLM provider for Harvest using Groq."""

import json
import logging
import asyncio
from typing import Any
from dataclasses import dataclass
from groq import AsyncGroq

from agent.context import ContextLoader

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """
    Decision from LLM about an opportunity.
    
    Attributes:
        action: One of "execute", "notify", or "skip"
        reasoning: Explanation for the decision
        confidence: Confidence level (0.0 to 1.0)
    """
    action: str  # "execute", "notify", "skip"
    reasoning: str
    confidence: float  # 0.0 to 1.0
    
    def __post_init__(self):
        """Validate decision fields."""
        if self.action not in ["execute", "notify", "skip"]:
            raise ValueError(f"Invalid action: {self.action}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Invalid confidence: {self.confidence}")


@dataclass
class Opportunity:
    """
    Represents a money-making opportunity.
    
    Attributes:
        strategy_name: Name of the strategy that found this opportunity
        action: Action to take (e.g., "stake", "claim", "buy")
        amount: Amount involved in the opportunity
        expected_profit: Expected profit from the opportunity
        risk_level: Risk level ("low", "medium", "high")
        details: Additional details about the opportunity
        timestamp: When the opportunity was found
    """
    strategy_name: str
    action: str
    amount: float
    expected_profit: float
    risk_level: str
    details: dict[str, Any]
    timestamp: Any  # datetime


@dataclass
class ToolCallRequest:
    """Represents a tool call from the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from LLM."""
    content: str | None
    tool_calls: list[ToolCallRequest]
    finish_reason: str
    usage: dict[str, Any] | None = None
    
    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class Provider:
    """
    LLM provider for decision-making using Groq.
    
    Uses Groq's Llama 3.1 70B model to evaluate opportunities
    and make decisions about whether to execute, notify, or skip.
    
    Includes workspace context from ContextLoader in every prompt.
    """
    
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_TIMEOUT = 30  # seconds
    
    def __init__(self, api_key: str, context_loader: ContextLoader):
        """
        Initialize provider with Groq API key and context loader.
        
        Args:
            api_key: Groq API key
            context_loader: ContextLoader instance for workspace context
        """
        self.client = AsyncGroq(api_key=api_key)
        self.context_loader = context_loader
        self.default_model = self.DEFAULT_MODEL
    
    async def make_decision(self, opportunity: Opportunity) -> Decision:
        """
        Evaluate opportunity and return decision.
        
        Args:
            opportunity: Opportunity to evaluate
        
        Returns:
            Decision object with action, reasoning, and confidence
        """
        try:
            # Build prompt with context
            prompt = self.build_prompt(opportunity)
            
            # Call LLM with timeout
            messages = [{"role": "user", "content": prompt}]
            
            response = await asyncio.wait_for(
                self._call_llm(messages),
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Parse decision from response
            decision = self._parse_decision(response.content or "")
            
            logger.info(f"Decision for {opportunity.strategy_name}: {decision.action} (confidence: {decision.confidence})")
            return decision
            
        except asyncio.TimeoutError:
            logger.error(f"LLM timeout for {opportunity.strategy_name}, defaulting to 'notify'")
            return Decision(
                action="notify",
                reasoning="LLM timeout - defaulting to user notification",
                confidence=0.0
            )
        except Exception as e:
            logger.error(f"Error making decision for {opportunity.strategy_name}: {e}, defaulting to 'notify'")
            return Decision(
                action="notify",
                reasoning=f"Error: {str(e)} - defaulting to user notification",
                confidence=0.0
            )
    
    def build_prompt(self, opportunity: Opportunity) -> str:
        """
        Build prompt with context and opportunity details.
        
        Args:
            opportunity: Opportunity to evaluate
        
        Returns:
            Formatted prompt string
        """
        # Get workspace context
        context = self.context_loader.get_context_string()
        
        # Build opportunity description
        opp_details = f"""
## Opportunity to Evaluate

**Strategy**: {opportunity.strategy_name}
**Action**: {opportunity.action}
**Amount**: {opportunity.amount} SOL
**Expected Profit**: {opportunity.expected_profit} SOL
**Risk Level**: {opportunity.risk_level}
**Details**: {json.dumps(opportunity.details, indent=2)}

## Your Task

Evaluate this opportunity and decide whether to:
- **execute**: Execute immediately without user approval
- **notify**: Send notification to user for approval
- **skip**: Skip this opportunity entirely

Respond in JSON format:
{{
  "action": "execute|notify|skip",
  "reasoning": "explanation for your decision",
  "confidence": 0.0-1.0
}}

Consider:
1. Risk level and potential profit
2. User's risk tolerance from USER.md
3. Decision framework from AGENTS.md
4. Current market conditions
"""
        
        return f"{context}\n\n{opp_details}"
    
    async def _call_llm(self, messages: list[dict[str, Any]]) -> LLMResponse:
        """
        Call Groq LLM.
        
        Args:
            messages: List of message dicts
        
        Returns:
            LLMResponse
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Error calling Groq: {e}")
            return LLMResponse(
                content=f"Error calling Groq: {str(e)}",
                tool_calls=[],
                finish_reason="error",
            )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Groq response."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )
    
    def _parse_decision(self, content: str) -> Decision:
        """
        Parse decision from LLM response content.
        
        Args:
            content: LLM response content
        
        Returns:
            Decision object
        """
        try:
            # Try to extract JSON from response
            # Look for JSON block in markdown or plain JSON
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                # Try to find JSON object
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = content[json_start:json_end]
                else:
                    json_str = content
            
            data = json.loads(json_str)
            
            return Decision(
                action=data.get("action", "notify"),
                reasoning=data.get("reasoning", "No reasoning provided"),
                confidence=float(data.get("confidence", 0.5))
            )
        except Exception as e:
            logger.warning(f"Failed to parse decision from LLM response: {e}")
            # Default to notify on parse failure
            return Decision(
                action="notify",
                reasoning=f"Failed to parse LLM response: {content[:100]}",
                confidence=0.0
            )


class GroqProvider:
    """
    Groq LLM provider for Harvest.
    
    Uses Groq's FREE Llama 3.1 70B model.
    """
    
    def __init__(self, api_key: str, default_model: str = "llama-3.3-70b-versatile"):
        self.client = AsyncGroq(api_key=api_key)
        self.default_model = default_model
    
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Send chat completion request to Groq.
        
        Args:
            messages: List of message dicts
            tools: Optional tool definitions
            model: Model to use
            max_tokens: Max response tokens
            temperature: Sampling temperature
        
        Returns:
            LLMResponse
        """
        model = model or self.default_model
        
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = await self.client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            return LLMResponse(
                content=f"Error calling Groq: {str(e)}",
                tool_calls=[],
                finish_reason="error",
            )
    
    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Groq response."""
        choice = response.choices[0]
        message = choice.message
        
        tool_calls = []
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw": args}
                
                tool_calls.append(ToolCallRequest(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args,
                ))
        
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
            usage=usage,
        )
