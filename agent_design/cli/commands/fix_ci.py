"""agent-design fix-ci — fix CI failures on a PR branch."""

import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from agent_design.git_ops import _nosign_flags, _run_git_in_target
from agent_design.github_ops.operations import GitHubOperations, RepositoryConfig, parse_github_remote_url
from agent_design.launcher import run_team_in_repo
from agent_design.prompts import build_fix_ci_start
from agent_design.state import load_round_state

console = Console()


def _make_ops(repo_path: Path) -> GitHubOperations | None:
    """Create a GitHubOperations instance from a local repo path."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        remote_url = result.stdout.strip()
        parsed = parse_github_remote_url(remote_url)
        if not parsed:
            return None
        owner, repo_name, _ = parsed
        config = RepositoryConfig(
            workspace=str(repo_path),
            github_owner=owner,
            github_repo=repo_name,
            remote_url=remote_url,
        )
        return GitHubOperations(config)
    except Exception as e:
        console.print(f"[dim]Could not initialise GitHubOperations: {e}[/dim]")
        return None


def _get_pr_info(repo_path: Path) -> dict[str, Any] | None:
    """Return PR info dict (number, url, head_sha) for the current branch, or None."""
    ops = _make_ops(repo_path)
    if ops is None:
        return None
    result = ops.find_pr_for_branch()
    if not result.get("success") or result.get("pr") is None:
        return None
    pr: dict[str, Any] = result["pr"]
    return pr


def _fetch_job_log(owner: str, repo_name: str, job_id: str, token: str) -> str | None:
    """Download GitHub Actions job log and return the failure section."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}/actions/jobs/{job_id}/logs"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            log_text = resp.read().decode("utf-8", errors="replace")
        return _extract_test_failures(log_text)
    except Exception as e:
        console.print(f"[dim]  ↳ log fetch failed for job {job_id}: {e}[/dim]")
        return None


def _extract_test_failures(log_text: str) -> str:
    """Extract the test failure section from a GitHub Actions log.

    GitHub Actions log lines are prefixed with an ISO timestamp.
    We strip those, then look for the pytest FAILURES / short test summary
    sections. Falls back to the last 60 lines if no pytest markers are found.
    """
    # Strip "2024-01-01T00:00:00.000Z " prefix from each line
    cleaned = []
    for line in log_text.splitlines():
        m = re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z (.*)", line)
        cleaned.append(m.group(1) if m else line)
    text = "\n".join(cleaned)

    # Prefer the ===== FAILURES ===== block
    failures_m = re.search(
        r"(={5,} FAILURES ={5,}.*?)(?=={5,} (?:short test summary info|warnings summary|ERROR) ={5,}|$)",
        text,
        re.DOTALL,
    )
    if failures_m:
        return failures_m.group(1)[:4000]

    # Fall back to short test summary info block
    summary_m = re.search(r"(={5,} short test summary info ={5,}.*?)(?=={5,}|$)", text, re.DOTALL)
    if summary_m:
        return summary_m.group(1)[:2000]

    # Last resort: tail of the log
    return "\n".join(cleaned[-60:])


def _fetch_ci_failures(repo_path: Path, pr_number: int) -> str | None:
    """Return a formatted failure string for failing CI checks, or None if CI is green.

    Uses GitHubOperations to find failing check runs and fetches their job logs
    directly via the GitHub REST API.
    """
    ops = _make_ops(repo_path)
    if ops is None:
        return None

    ci = ops.check_ci_build_and_test_errors(pr_number=pr_number)
    if not ci.get("success"):
        console.print(f"[dim]CI check failed: {ci.get('error')}[/dim]")
        return None

    if not ci.get("has_failures"):
        return None

    commit_sha = ci["commit_sha"]
    token = ops.github_token or ""
    owner = ops.github_owner
    repo_name = ops.github_repo

    # Get raw PyGithub CheckRun objects so we have details_url
    assert ops.repo is not None
    failing_conclusions = {"failure", "timed_out", "cancelled", "action_required"}
    sections: list[str] = []

    try:
        check_runs_page = ops.repo.get_commit(commit_sha).get_check_runs()
        for cr in check_runs_page:
            if cr.conclusion not in failing_conclusions:
                continue
            lines = [f"### {cr.name} ({cr.conclusion})"]

            # Parse job ID from details_url
            job_id_match = re.search(r"/jobs?/(\d+)", cr.details_url or "")
            job_id = job_id_match.group(1) if job_id_match else ""

            if job_id and token:
                log_section = _fetch_job_log(owner, repo_name, job_id, token)
                if log_section:
                    lines.append("Job log (failure section):")
                    lines.append(log_section)
            sections.append("\n".join(lines))
    except Exception as e:
        console.print(f"[dim]Could not retrieve check runs: {e}[/dim]")
        # Fall back to the dicts from check_ci_build_and_test_errors
        for cr in ci.get("failed_checks", []):
            sections.append(f"### {cr['name']} ({cr['conclusion']})")

    if not sections:
        return None

    return "Failing checks:\n\n" + "\n\n".join(sections)


def _commit_and_push(repo_path: Path, branch_name: str, slug: str) -> None:
    """Commit CI fix changes and push."""
    roxy_token_path = Path.home() / ".roxy_github_token"
    repo_env = os.environ.copy()
    if roxy_token_path.exists():
        repo_env["GH_TOKEN"] = roxy_token_path.read_text().strip()

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

    # ── Resolve PR info ───────────────────────────────────────────────────────
    pr_number: int | None = None
    if pr_url is None:
        pr_info = _get_pr_info(repo_path)
        if pr_info:
            pr_url = pr_info.get("url") or pr_info.get("html_url")
            pr_number = pr_info.get("number")
    else:
        # Parse PR number from URL
        m = re.search(r"/pull/(\d+)", pr_url)
        if m:
            pr_number = int(m.group(1))

    if not pr_url or pr_number is None:
        raise click.UsageError("Could not determine PR URL. Pass --pr <url> or run from a branch with an open PR.")

    console.print(f"\n[bold]agent-design fix-ci[/bold] — [cyan]{pr_url}[/cyan]\n")

    # ── Fetch CI failures ────────────────────────────────────────────────────
    console.print("[dim]Fetching CI check results...[/dim]")
    failures = _fetch_ci_failures(repo_path, pr_number)

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
