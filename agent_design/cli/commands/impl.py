"""agent-design impl — run a self-organising implementation sprint."""

import os
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import (
    _nosign_flags,
    _run_git_in_target,
    create_impl_branch,
    detect_existing_worktree,
)
from agent_design.launcher import run_team_in_repo
from agent_design.prompts import build_impl_start
from agent_design.state import load_round_state

console = Console()

ROXY_GITHUB_TOKEN = Path.home() / ".roxy_github_token"


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command using Roxy's token."""
    env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


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


def _commit_and_push(
    repo_path: Path, branch_name: str, slug: str, feature_request: str, design_pr_url: str | None
) -> str | None:
    """Commit all implementation changes as Roxy and push, then open a PR.

    Returns the PR URL if created successfully, or None otherwise.
    """
    repo_env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        repo_env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()

    # Stage everything
    _run_git_in_target(
        ["add", "."],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to stage implementation changes",
    )

    # Check if there's anything to commit
    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_path,
        env=repo_env,
    )
    if diff_result.returncode == 0:
        console.print("[yellow]⚠ No changes to commit — did the agents write any files?[/yellow]")
        return None

    # Commit as Roxy
    _run_git_in_target(
        [
            *_nosign_flags(repo_path),
            "commit",
            "--no-verify",
            "-m",
            f"impl: {slug}",
        ],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to commit implementation",
    )
    console.print(f"[green]✓[/green] Implementation committed to {branch_name}")

    # Push
    _run_git_in_target(
        ["push", "-u", "origin", branch_name],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to push implementation branch",
    )
    console.print(f"[green]✓[/green] Pushed {branch_name} to origin")

    # Create PR
    design_ref = f"\n\nDesign doc PR: {design_pr_url}" if design_pr_url else ""
    gh_result = _gh(
        "pr",
        "create",
        "--repo",
        _get_repo_name(repo_path),
        "--title",
        f"impl: {slug}",
        "--body",
        f"Implementation for: {feature_request}{design_ref}",
        "--head",
        branch_name,
        "--base",
        "main",
    )
    if gh_result.returncode == 0:
        pr_url = gh_result.stdout.strip()
        console.print(f"[green]✓[/green] PR created: {pr_url}")
        return pr_url
    else:
        console.print(f"[yellow]⚠ PR creation failed: {gh_result.stderr.strip()}[/yellow]")
        console.print(f"[dim]  Branch is pushed — create the PR manually from {branch_name}[/dim]")
        return None


def _check_ci_status(pr_url: str | None) -> None:
    """Check CI status for the given PR URL and print a summary.

    Uses the REST API to avoid GraphQL dependency.
    Does nothing if pr_url is None (e.g. PR creation failed earlier).
    """
    import json as _json
    import re as _re

    if pr_url is None:
        return

    m = _re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if not m:
        console.print("[yellow]⚠ Could not parse PR URL — check CI manually.[/yellow]")
        return
    repo, pr_number = m.group(1), m.group(2)

    # Get PR head SHA via REST
    pr_result = _gh("api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha")
    if pr_result.returncode != 0:
        console.print("[yellow]⚠ Could not fetch PR info — check CI manually.[/yellow]")
        return
    sha = pr_result.stdout.strip()

    # Get check runs for that commit via REST
    runs_result = _gh("api", f"repos/{repo}/commits/{sha}/check-runs")
    if runs_result.returncode != 0:
        console.print("[yellow]⚠ Could not fetch CI status — check the PR manually.[/yellow]")
        return

    try:
        data = _json.loads(runs_result.stdout)
    except _json.JSONDecodeError:
        console.print("[yellow]⚠ Could not parse CI check output — check the PR manually.[/yellow]")
        return

    check_runs = data.get("check_runs", [])
    if not check_runs:
        console.print("[yellow]⚠ CI checks are still running — use fix-ci if they fail.[/yellow]")
        return

    failing = [
        c["name"] for c in check_runs if c.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")
    ]
    pending = [c for c in check_runs if c.get("status") in ("queued", "in_progress")]

    if failing:
        console.print("[red]✗ CI failed — run 'agent-design fix-ci' to fix.[/red]")
        for name in failing:
            console.print(f"[red]  • {name}[/red]")
    elif pending and not failing:
        console.print("[yellow]⚠ CI checks are still running — use fix-ci if they fail.[/yellow]")
    else:
        console.print("[green]✓ CI is green[/green]")


@click.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume an existing implementation sprint. Assumes impl branch exists.",
)
def impl(repo_path: Path, resume: bool) -> None:
    """Run a self-organising implementation sprint.

    The agent team reads the approved DESIGN.md, self-organises into a sprint,
    implements everything (tests first), then conducts a mandatory final review
    before handing off.

    Requires a completed design phase: run 'agent-design init' and
    'agent-design next' first.
    """
    repo_path = repo_path.resolve()
    worktree_path = repo_path / ".agent-design"

    # ── Pre-flight checks ───────────────────────────────────────────────────
    if not detect_existing_worktree(repo_path):
        console.print("[red]✗ No active session found.[/red]")
        console.print(
            "[dim]  Run 'agent-design init' and 'agent-design next' to complete the design phase first.[/dim]"
        )
        raise click.Abort() from None

    design_doc = worktree_path / "DESIGN.md"
    if not design_doc.exists():
        console.print("[red]✗ DESIGN.md not found in worktree.[/red]")
        console.print("[dim]  Complete the design phase with 'agent-design next' first.[/dim]")
        raise click.Abort() from None

    state = load_round_state(worktree_path)
    slug = state.feature_slug
    impl_branch_name = f"feat/impl-{slug}"
    repo_env = os.environ.copy()  # Define repo_env early

    console.print(f"\n[bold]agent-design impl[/bold] — [cyan]{state.feature_slug}[/cyan]\n")
    console.print(
        Panel(
            f"Design doc: [dim].agent-design/DESIGN.md[/dim]\n"
            f"Feature:    [dim]{state.feature_request[:120]}{'…' if len(state.feature_request) > 120 else ''}[/dim]",
            title="Implementation Sprint",
            border_style="magenta",
        )
    )

    # ── Branch handling ──────────────────────────────────────────────────
    if resume:
        console.print(
            f"\n[dim]Resuming implementation sprint on branch {impl_branch_name} in {repo_path.name}...[/dim]"
        )
        try:
            # Check if the branch actually exists
            subprocess.run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{impl_branch_name}"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                env=repo_env,
            )
            # Checkout and pull latest
            _run_git_in_target(
                ["checkout", impl_branch_name],
                cwd=repo_path,
                env=repo_env,
                error_msg=f"Failed to checkout existing branch {impl_branch_name}",
            )
            _run_git_in_target(
                ["pull", "origin", impl_branch_name],
                cwd=repo_path,
                env=repo_env,
                error_msg=f"Failed to pull latest changes for {impl_branch_name}",
            )
            console.print(f"[green]✓[/green] Resumed branch: [cyan]{impl_branch_name}[/cyan]\n")

        except subprocess.CalledProcessError:
            console.print(f"[red]✗ Implementation branch {impl_branch_name} not found for resume.[/red]")
            console.print(
                "[dim]  To start a new sprint, run without --resume. To resume, ensure the branch exists.[/dim]"
            )
            raise click.Abort() from None
    else:  # Start a new sprint
        console.print(f"\n[dim]Creating new implementation branch in {repo_path.name}...[/dim]")
        try:
            impl_branch_name = create_impl_branch(repo_path, state.feature_slug)
        except subprocess.CalledProcessError:
            console.print("[red]✗ Failed to create implementation branch. See error above.[/red]")
            raise click.Abort() from None
        console.print(f"[green]✓[/green] Branch: [cyan]{impl_branch_name}[/cyan]\n")

    # ── Launch team session ─────────────────────────────────────────────────
    start_message = build_impl_start(feature_request=state.feature_request, is_resume=resume)
    rc = run_team_in_repo(repo_path, worktree_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    # ── Commit and push ─────────────────────────────────────────────────────
    console.print("\n[dim]Committing and pushing implementation...[/dim]")
    pr_url = _commit_and_push(repo_path, impl_branch_name, state.feature_slug, state.feature_request, state.pr_url)
    _check_ci_status(pr_url)

    console.print(
        Panel(
            f"Branch [cyan]{impl_branch_name}[/cyan] is ready for review.\n\n"
            "Check the PR, verify CI passes, then merge when satisfied.",
            title="[green]✓ Implementation sprint complete[/green]",
            border_style="green",
        )
    )
