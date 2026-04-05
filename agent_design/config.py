"""Global plugin path configuration.

PLUGIN_CORE and PLUGIN_LOCAL are the single source of truth for where agents,
memory files, and skills live. Nothing else in the codebase should hardcode
~/.claude/agents/, ~/.claude/agent-memory/, or plugin directory paths.

Usage:
    from agent_design.config import PLUGIN_CORE, PLUGIN_LOCAL

    agents_dir = PLUGIN_CORE / "agents"
    memory_dir = PLUGIN_CORE / "memory"
"""

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent

# General-purpose agents (architect, developer, tdd_focused_engineer, …)
PLUGIN_CORE: Path = _REPO_ROOT / "plugins" / "core"

# Project/domain-specific agents for this installation
PLUGIN_LOCAL: Path = _REPO_ROOT / "plugins" / "local"
