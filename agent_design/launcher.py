"""Launch claude sessions for each design stage.

Two modes:
- run_solo(): non-interactive --print session (Architect writing baseline/design draft)
- run_team(): interactive agent team session handed off to the terminal
"""

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()


def _get_api_key() -> str | None:
    """Get Anthropic API key from environment or ~/.anthropic_api_key.

    Returns None if neither is present — callers should proceed without
    setting the key and rely on claude's existing login session.
    """
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key
    key_file = Path.home() / ".anthropic_api_key"
    if key_file.exists():
        return key_file.read_text().strip()
    return None


def run_solo(
    system_prompt: str,
    task_prompt: str,
    worktree_path: Path,
    target_repo: Path,
) -> int:
    """Run a non-interactive single-agent claude session.

    Used for automated stages: baseline analysis and initial design draft.
    Claude writes directly to files in worktree_path.

    Args:
        system_prompt: Agent identity/persona (passed via --append-system-prompt)
        task_prompt: Stage-specific task instructions (sent via stdin)
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)

    Returns:
        Exit code from claude process
    """
    env = os.environ.copy()
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key

    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--add-dir",
        str(target_repo),
        "--append-system-prompt",
        system_prompt,
        task_prompt,
    ]

    result = subprocess.run(
        cmd,
        cwd=str(worktree_path),
        env=env,
    )
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
