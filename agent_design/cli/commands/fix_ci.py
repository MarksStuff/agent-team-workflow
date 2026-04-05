"""agent-design fix-ci — fix CI failures on a PR branch."""

import json
import os
import subprocess
from pathlib import Path

import click
from rich.console import Console

from agent_design.git_ops import _nosign_flags, _run_git_in_target
from agent_design.launcher import run_team_in_repo
from agent_design.prompts import build_fix_ci_start
from agent_design.state import load_round_state

console = Console()

ROXY_GITHUB_TOKEN = Path.home() / ".roxy_github_token"


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command using Roxy's token."""
    env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


def _get_pr_url(repo_path: Path) -> str | None:
    """Detect the PR URL for the current branch in repo_path.

    Returns the URL string or None if not on a PR branch.
    """
    result = _gh("pr", "view", "--json", "url", "-q", ".url")
    if result.returncode == 0:
        url = result.stdout.strip()
        return url if url else None
    return None


def _fetch_ci_failures(pr_url: str) -> str | None:
    """Fetch CI check results for the given PR URL.

    Returns a formatted failure string describing the failing checks,
    or None if all checks are passing / no failures found.
    """
    json_result = _gh("pr", "checks", pr_url, "--json", "name,state,conclusion")
    if json_result.returncode != 0:
        return None

    try:
        checks = json.loads(json_result.stdout)
    except json.JSONDecodeError:
        return None

    failing = [c for c in checks if c.get("state") == "fail"]
    if not failing:
        return None

    # Also fetch human-readable detail
    text_result = _gh("pr", "checks", pr_url)
    detail = text_result.stdout.strip() if text_result.returncode == 0 else ""

    failing_names = "\n".join(f"  • {c['name']}" for c in failing)
    parts = [f"Failing checks:\n{failing_names}"]
    if detail:
        parts.append(f"\nFull check output:\n{detail}")
    return "\n".join(parts)


def _get_repo_name(repo_path: Path) -> str:
    """Extract owner/repo from git remote."""
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    url = result.stdout.strip()
    url = url.replace("git@github.com:", "").replace("https://github.com/", "")
    return url.removesuffix(".git")


def _commit_and_push(repo_path: Path, branch_name: str, slug: str) -> None:
    """Commit CI fix changes and push."""
    repo_env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        repo_env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()

    _run_git_in_target(
        ["add", "."],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to stage CI fix changes",
    )

    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_path,
        env=repo_env,
    )
    if diff_result.returncode == 0:
        console.print("[yellow]⚠ No changes to commit.[/yellow]")
        return

    _run_git_in_target(
        [
            *_nosign_flags(repo_path),
            "commit",
            "--no-verify",
            "-m",
            f"fix: ci failures for {slug}",
        ],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to commit CI fix",
    )
    console.print(f"[green]✓[/green] CI fix committed to {branch_name}")

    _run_git_in_target(
        ["push", "origin", branch_name],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to push CI fix",
    )
    console.print(f"[green]✓[/green] Pushed {branch_name} to origin")


def _current_branch(repo_path: Path) -> str:
    """Return the current git branch name."""
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@click.command(name="fix-ci")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
@click.option(
    "--pr",
    "pr_url",
    default=None,
    help="PR URL (auto-detected from current branch if omitted)",
)
def fix_ci(repo_path: Path, pr_url: str | None) -> None:
    """Fix CI failures on a PR branch.

    Reads the CI failure output for the given PR and invokes the agent
    team to fix only the failing checks.
    """
    repo_path = repo_path.resolve()

    # ── Resolve PR URL ───────────────────────────────────────────────────────
    if pr_url is None:
        pr_url = _get_pr_url(repo_path)
    if not pr_url:
        raise click.UsageError("Could not determine PR URL. Pass --pr <url> or run from a branch with an open PR.")

    console.print(f"\n[bold]agent-design fix-ci[/bold] — [cyan]{pr_url}[/cyan]\n")

    # ── Fetch CI failures ────────────────────────────────────────────────────
    console.print("[dim]Fetching CI check results...[/dim]")
    failures = _fetch_ci_failures(pr_url)

    if failures is None:
        console.print("[green]✓ CI is passing — nothing to fix.[/green]")
        return

    console.print("[red]✗ CI failures detected:[/red]")
    console.print(failures)

    # ── Determine worktree and slug ──────────────────────────────────────────
    worktree_path = repo_path / ".agent-design"
    slug = "ci-fix"
    try:
        state = load_round_state(worktree_path)
        slug = state.feature_slug
    except (FileNotFoundError, ValueError):
        pass

    # ── Launch team session ──────────────────────────────────────────────────
    start_message = build_fix_ci_start(ci_failures=failures, pr_url=pr_url)
    rc = run_team_in_repo(repo_path, worktree_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    # ── Commit and push ──────────────────────────────────────────────────────
    branch_name = _current_branch(repo_path)
    console.print("\n[dim]Committing and pushing CI fix...[/dim]")
    _commit_and_push(repo_path, branch_name, slug)
