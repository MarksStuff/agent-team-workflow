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

from agent_design.config import PLUGIN_CORE, PLUGIN_LOCAL


def _plugin_flags() -> list[str]:
    """Return --plugin-dir flags for the two bundled plugins.

    Only includes a plugin directory if it actually exists on disk, so the
    launcher degrades gracefully on machines where the repo is partially cloned.
    """
    flags: list[str] = []
    for plugin_dir in (PLUGIN_CORE, PLUGIN_LOCAL):
        if plugin_dir.exists():
            flags += ["--plugin-dir", str(plugin_dir)]
    return flags


def _plugin_env(base: dict[str, str]) -> dict[str, str]:
    """Inject AGENT_CORE_PLUGIN_DIR and AGENT_LOCAL_PLUGIN_DIR into an env dict.

    Agents read these variables to locate their memory files and peer agent
    definitions without hardcoding any paths.
    """
    env = base.copy()
    env["AGENT_CORE_PLUGIN_DIR"] = str(PLUGIN_CORE)
    env["AGENT_LOCAL_PLUGIN_DIR"] = str(PLUGIN_LOCAL)
    return env


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
        agent_name: Name of the agent to run (e.g., 'architect'). Loaded from
                    plugins/core/agents/{agent_name}.md via --plugin-dir.
        task_prompt: Stage-specific task instructions
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)

    Returns:
        Exit code from claude process
    """
    env = _plugin_env(os.environ.copy())
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
                *_plugin_flags(),
                "--add-dir",
                str(target_repo),
                "--agent",
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


def run_print_team(
    worktree_path: Path,
    target_repo: Path,
    start_message: str,
) -> int:
    """Run a non-interactive agent team session in --print mode.

    Used for memory update sessions (remember, review-feedback) where the
    output is consumed programmatically rather than displayed interactively.
    Combines --print mode (like run_solo) with CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
    (like run_team), so multiple agents collaborate in a headless session.

    Args:
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)
        start_message: Initial message delivered as the first turn

    Returns:
        Exit code from claude process
    """
    env = _plugin_env(os.environ.copy())
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

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
                *_plugin_flags(),
                "--add-dir",
                str(target_repo),
                "--agent",
                "eng_manager",
                "--",
                start_message,
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

    The start_message is passed as a positional argument to claude so the
    session begins immediately without requiring the user to copy-paste.

    Args:
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)
        start_message: Initial message delivered as the first turn

    Returns:
        Exit code from claude process
    """
    env = _plugin_env(os.environ.copy())
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    result = subprocess.run(
        [
            "claude",
            "--dangerously-skip-permissions",
            *_plugin_flags(),
            "--agent",
            "eng_manager",
            "--add-dir",
            str(target_repo),
            "--",
            start_message,
        ],
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

    The start_message is passed as a positional argument to claude so the
    session begins immediately without requiring the user to copy-paste.

    Args:
        repo_path: Path to target repo (claude's working dir)
        worktree_path: Path to .agent-design/ worktree (added as readable dir)
        start_message: Initial message delivered as the first turn

    Returns:
        Exit code from claude process
    """
    env = _plugin_env(os.environ.copy())
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    result = subprocess.run(
        [
            "claude",
            "--dangerously-skip-permissions",
            *_plugin_flags(),
            "--agent",
            "eng_manager",
            "--add-dir",
            str(worktree_path),
            "--",
            start_message,
        ],
        cwd=str(repo_path),
        env=env,
    )
    return result.returncode
