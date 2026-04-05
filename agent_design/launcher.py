"""Launch claude sessions for each design stage.

Three modes:
- run_solo(): non-interactive --print session (Architect writing BASELINE.md)
- run_print_team(): non-interactive team session (remember, review-feedback)
- run_team_in_repo(): interactive team session rooted in the target repo
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


def _write_plugin_root() -> None:
    """Write the absolute PLUGIN_CORE path to ~/.agent-design/core_plugin_dir.

    Called before every Claude session. Agents read this file at session start
    (one Read tool call) to discover the absolute path to the core plugin
    without needing to expand environment variables.

    The file is machine-local ephemeral config — it changes whenever the repo
    is moved or cloned to a different location.
    """
    config_dir = Path.home() / ".agent-design"
    config_dir.mkdir(exist_ok=True)
    (config_dir / "core_plugin_dir").write_text(str(PLUGIN_CORE))


def _plugin_env(base: dict[str, str]) -> dict[str, str]:
    """Inject AGENT_CORE_PLUGIN_DIR and AGENT_LOCAL_PLUGIN_DIR into an env dict."""
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
    _write_plugin_root()
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
    _write_plugin_root()
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


def run_apply_suggestion(
    worktree_path: Path,
    target_repo: Path,
    task_prompt: str,
) -> int:
    """Run a non-interactive solo claude session to apply a prompt suggestion.

    Used by the apply-suggestion command to edit agent definition files.
    Unlike run_solo(), does NOT use --agent so Claude runs without a specific
    agent identity. Adds PLUGIN_CORE as an extra readable/writable directory
    so Claude can edit agent definition files.

    Args:
        worktree_path: Path to .agent-design/ worktree (claude's working dir)
        target_repo: Path to target repo (added as readable directory)
        task_prompt: Prompt describing which file to edit and what to change

    Returns:
        Exit code from claude process
    """
    _write_plugin_root()
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
                "--add-dir",
                str(PLUGIN_CORE),
                "--",
                task_prompt,
            ],
            cwd=str(worktree_path),
            env=env,
        )
    finally:
        os.unlink(mcp_config_path)

    return result.returncode


def run_team_in_repo(
    repo_path: Path,
    worktree_path: Path,
    start_message: str,
    test_cmd: str | None = None,
) -> int:
    """Launch an interactive claude agent team session rooted in the target repo.

    The working directory is the target repo root so agents can read and write
    source files directly. The worktree (.agent-design/) is added as an extra
    readable directory so agents can access DESIGN.md and other artefacts.

    Used for all interactive team sessions: design (init Stage 1, next,
    continue, feedback) and implementation (impl, fix-ci).

    Args:
        repo_path: Path to target repo (claude's working dir)
        worktree_path: Path to .agent-design/ worktree (added as readable dir)
        start_message: Initial message delivered as the first turn
        test_cmd: Optional shell command to run tests when gating task completion.
                  If provided, hook scripts are wired up via .claude/settings.json.

    Returns:
        Exit code from claude process
    """
    _write_plugin_root()
    env = _plugin_env(os.environ.copy())
    api_key = _get_api_key()
    if api_key:
        env["ANTHROPIC_API_KEY"] = api_key
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"

    settings_path: Path | None = None
    if test_cmd is not None:
        hooks_dir = Path(__file__).parent.parent / "scripts" / "hooks"
        settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "TaskUpdate",
                        "hooks": [{"type": "command", "command": str(hooks_dir / "task_completed.sh")}],
                    }
                ],
                "Stop": [{"hooks": [{"type": "command", "command": str(hooks_dir / "teammate_idle.sh")}]}],
            }
        }
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        settings_path = claude_dir / "settings.json"
        settings_path.write_text(json.dumps(settings, indent=2))
        env["TEST_CMD"] = test_cmd
        env["REPO_PATH"] = str(repo_path)

    try:
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
    finally:
        if settings_path is not None and settings_path.exists():
            settings_path.unlink()

    return result.returncode
