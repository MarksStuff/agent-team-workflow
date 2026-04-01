"""Launch claude sessions for each design stage.

Two modes:
- run_solo(): non-interactive --print session (Architect writing baseline/design draft)
- run_team(): interactive agent team session handed off to the terminal
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def _get_api_key() -> str | None:
    """Get Anthropic API key from environment or ~/.anthropic_api_key.

    Returns None if neither is present — Claude will authenticate via its
    own configured method (e.g. OAuth login session or apiKeyHelper script).
    """
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key
    key_file = Path.home() / ".anthropic_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return None


def run_solo(
    agent_name: str,
    task_prompt: str,
    worktree_path: Path,
    target_repo: Path,
) -> int:
    """Run a non-interactive single-agent claude session.

    Used for automated stages: baseline analysis and initial design draft.
    Claude writes directly to files in worktree_path.

    Args:
        agent_name: Name of the agent to run (e.g., 'architect'). Claude Code
                    will load its definition from ~/.claude/agents/{agent_name}.md
        task_prompt: Stage-specific task instructions
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)

    Returns:
        Exit code from claude process
    """
    env = os.environ.copy()
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as mcp_file:
        json.dump({"mcpServers": {}}, mcp_file)
        mcp_config_path = mcp_file.name

    try:
        result = subprocess.run(
            [
                "claude",
                "--print",
                "--dangerously-skip-permissions",
                "--strict-mcp-config",
                "--mcp-config",
                mcp_config_path,
                "--add-dir",
                str(target_repo),
                "--agent",  # Use --agent flag here
                agent_name,
                "--",
                task_prompt,
            ],
            cwd=str(worktree_path),
            env=env,
        )
    finally:
        os.unlink(mcp_config_path)

    return result.returncode


def run_team(
    worktree_path: Path,
    target_repo: Path,
    start_message: str,
) -> int:
    """Launch an interactive claude agent team session.

    Hands the terminal over to claude. The user sees the session live and
    can interact (Shift+Down to cycle teammates, type to message them).
    Returns when the user exits claude or the session completes.

    The start_message is printed to the console before launching so the
    user can paste it as the first message to kick off the team.

    Args:
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)
        start_message: Initial message to paste into claude to start the team

    Returns:
        Exit code from claude process
    """
    env = os.environ.copy()
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--agent",
        "eng_manager",
        "--add-dir",
        str(target_repo),
    ]

    console.print(
        Panel(
            start_message,
            title="[bold cyan]Paste this to start the agent team[/bold cyan]",
            subtitle="[dim]Copy the text above and paste it when Claude starts[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    result = subprocess.run(
        cmd,
        cwd=str(worktree_path),
        env=env,
    )
    return result.returncode


def run_team_in_repo(
    repo_path: Path,
    worktree_path: Path,
    start_message: str,
) -> int:
    """Launch an interactive claude agent team session in the target repo root.

    Like run_team() but the working directory is the target repo root so
    agents can read and write source files directly. The worktree is added
    as an extra directory so agents can read .agent-design/DESIGN.md.

    Args:
        repo_path: Path to target repo (claude's working dir)
        worktree_path: Path to .agent-design/ worktree (added as readable dir)
        start_message: Initial message to paste into claude to start the team

    Returns:
        Exit code from claude process
    """
    env = os.environ.copy()
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--agent",
        "eng_manager",
        "--add-dir",
        str(worktree_path),
    ]

    console.print(
        Panel(
            start_message,
            title="[bold cyan]Paste this to start the implementation sprint[/bold cyan]",
            subtitle="[dim]Copy the text above and paste it when Claude starts[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    result = subprocess.run(
        cmd,
        cwd=str(repo_path),
        env=env,
    )
    return result.returncode
