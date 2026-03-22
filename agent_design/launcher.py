"""Launch claude sessions for each design stage.

Two modes:
- run_solo(): Architect-only session for baseline analysis and initial design draft.
  With API key: non-interactive --print (fully automated).
  Without API key: interactive session handed to terminal (e.g. Apple internal build).
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
    """Run a single-agent Architect session.

    With API key: fully automated via claude --print (no user interaction needed).
    Without API key: hands the terminal to an interactive Claude session. Claude
    receives the task as its opening message and works autonomously; close the
    session (Ctrl+C or /exit) when it signals it's done writing files.

    Args:
        system_prompt: Agent identity/persona (passed via --append-system-prompt)
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
        return _run_solo_print(system_prompt, task_prompt, worktree_path, target_repo, env)
    else:
        return _run_solo_interactive(system_prompt, task_prompt, worktree_path, target_repo, env)


def _run_solo_print(
    system_prompt: str,
    task_prompt: str,
    worktree_path: Path,
    target_repo: Path,
    env: dict[str, str],
) -> int:
    """Non-interactive --print mode. Requires API key."""
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
                "--append-system-prompt",
                system_prompt,
                "--",
                task_prompt,
            ],
            cwd=str(worktree_path),
            env=env,
        )
    finally:
        os.unlink(mcp_config_path)

    return result.returncode


def _run_solo_interactive(
    system_prompt: str,
    task_prompt: str,
    worktree_path: Path,
    target_repo: Path,
    env: dict[str, str],
) -> int:
    """Interactive fallback for environments where --print is unavailable (e.g. Apple internal build).

    Launches bare `claude` with no positional args or extra flags (passing args
    triggers the same broken non-interactive code path as --print on Apple's build).
    The task is shown in a panel for the user to paste as the first message.
    """
    full_prompt = f"{task_prompt}\n\n[System context — add to your system prompt mentally]\n{system_prompt}"
    console.print(
        Panel(
            full_prompt,
            title="[bold yellow]Paste this into Claude to start (no API key — interactive mode)[/bold yellow]",
            subtitle="[dim]Copy the text above · paste when Claude opens · /exit when done writing files[/dim]",
            border_style="yellow",
        )
    )
    console.print()

    result = subprocess.run(
        ["claude"],
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
