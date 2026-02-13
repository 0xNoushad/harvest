"""Context loader for Harvest agent - loads workspace files into memory."""

import platform
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ContextLoader:
    """
    Loads workspace files into agent context.
    
    Reads AGENTS.md, SOUL.md, USER.md, TOOLS.md from workspace directory
    and caches them in memory for use in LLM prompts.
    
    Handles missing files gracefully with warnings.
    """
    
    WORKSPACE_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]
    
    def __init__(self, workspace_path: str = "workspace/"):
        """
        Initialize context loader.
        
        Args:
            workspace_path: Path to workspace directory (relative or absolute)
        """
        self.workspace_path = Path(workspace_path)
        self._cache: Dict[str, str] = {}
        self._last_load_time: datetime | None = None
    
    def load_all(self) -> Dict[str, str]:
        """
        Load all workspace files and return as dictionary.
        
        Returns:
            Dictionary mapping filename to content
        """
        context = {}
        
        for filename in self.WORKSPACE_FILES:
            try:
                content = self.load_file(filename)
                context[filename] = content
            except FileNotFoundError:
                logger.warning(f"Workspace file not found: {filename}, using empty content")
                context[filename] = ""
            except Exception as e:
                logger.warning(f"Error loading {filename}: {e}, using empty content")
                context[filename] = ""
        
        # Update cache and timestamp
        self._cache = context
        self._last_load_time = datetime.now()
        
        return context
    
    def load_file(self, filename: str) -> str:
        """
        Load a specific workspace file.
        
        Args:
            filename: Name of file to load (e.g., "AGENTS.md")
        
        Returns:
            File content as string
        
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.workspace_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        return file_path.read_text(encoding="utf-8")
    
    def get_context_string(self) -> str:
        """
        Return all context formatted as a single string.
        
        Returns:
            Formatted context string with all workspace files
        """
        if not self._cache:
            self.load_all()
        
        parts = []
        for filename, content in self._cache.items():
            if content:  # Only include non-empty files
                parts.append(f"# {filename}\n\n{content}")
        
        return "\n\n---\n\n".join(parts)
    
    def get_cached_context(self) -> Dict[str, str]:
        """
        Get cached context without reloading.
        
        Returns:
            Cached context dictionary
        """
        if not self._cache:
            return self.load_all()
        return self._cache.copy()
    
    def should_reload(self, max_age_seconds: int = 3600) -> bool:
        """
        Check if cache should be reloaded based on age.
        
        Args:
            max_age_seconds: Maximum cache age in seconds (default 1 hour)
        
        Returns:
            True if cache should be reloaded
        """
        if not self._last_load_time:
            return True
        
        age = (datetime.now() - self._last_load_time).total_seconds()
        return age > max_age_seconds


class ContextBuilder:
    """
    Builds context for Harvest agent from workspace files.
    
    Loads AGENTS.md, SOUL.md, USER.md, TOOLS.md, and MEMORY.md
    to create the agent's system prompt.
    """
    
    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md"]
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
    
    def build_system_prompt(self) -> str:
        """Build complete system prompt from workspace files."""
        parts = []
        
        # Core identity
        parts.append(self._get_identity())
        
        # Bootstrap files from workspace/
        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)
        
        # Memory context
        memory = self._load_memory()
        if memory:
            parts.append(f"# Memory\n\n{memory}")
        
        return "\n\n---\n\n".join(parts)
    
    def _get_identity(self) -> str:
        """Get core identity section."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"
        
        return f"""# Harvest 🌾

You are Harvest - an autonomous AI agent that hunts for money on Solana.

## Current Time
{now}

## Runtime
{runtime}

## Workspace
{workspace_path}

Your mission: Turn $1 into $100+ by autonomously executing profitable strategies across the Solana ecosystem."""
    
    def _load_bootstrap_files(self) -> str:
        """Load bootstrap files from workspace/."""
        parts = []
        workspace_dir = self.workspace / "workspace"
        
        for filename in self.BOOTSTRAP_FILES:
            file_path = workspace_dir / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        
        return "\n\n".join(parts) if parts else ""
    
    def _load_memory(self) -> str:
        """Load memory from workspace/memory/MEMORY.md."""
        memory_file = self.workspace / "workspace" / "memory" / "MEMORY.md"
        if memory_file.exists():
            return memory_file.read_text(encoding="utf-8")
        return ""
    
    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
    ) -> list[dict[str, Any]]:
        """
        Build complete message list for LLM call.
        
        Args:
            history: Previous conversation messages
            current_message: New user message
        
        Returns:
            List of messages including system prompt
        """
        messages = []
        
        # System prompt
        system_prompt = self.build_system_prompt()
        messages.append({"role": "system", "content": system_prompt})
        
        # History
        messages.extend(history)
        
        # Current message
        messages.append({"role": "user", "content": current_message})
        
        return messages
    
    def add_assistant_message(
        self,
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Add assistant message to message list."""
        msg: dict[str, Any] = {"role": "assistant", "content": content or ""}
        
        if tool_calls:
            msg["tool_calls"] = tool_calls
        
        messages.append(msg)
        return messages
    
    def add_tool_result(
        self,
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str
    ) -> list[dict[str, Any]]:
        """Add tool result to message list."""
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result
        })
        return messages
