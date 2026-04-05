"""agent-design fix-ci — fix CI failures on a PR branch."""

import json
import os
import re
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


def _parse_pr_url(pr_url: str) -> tuple[str, str] | None:
    """Parse 'owner/repo' and PR number from a GitHub PR URL.

    Returns (repo, pr_number) or None if the URL doesn't match.
    """
    m = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
    if not m:
        return None
    return m.group(1), m.group(2)


def _get_pr_url(repo_path: Path) -> str | None:
    """Detect the PR URL for the current branch in repo_path via REST API.

    Gets the current branch from git, then queries the GitHub REST API
    to find an open PR for that branch. Avoids GraphQL dependency.
    Returns the URL string or None if not on a PR branch.
    """
    # Get current branch name
    branch_result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if branch_result.returncode != 0:
        return None
    branch = branch_result.stdout.strip()
    if not branch or branch == "HEAD":
        return None

    # Get owner/repo from remote
    remote_result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if remote_result.returncode != 0:
        return None
    remote_url = remote_result.stdout.strip()
    m = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?$", remote_url)
    if not m:
        return None
    repo = m.group(1)

    # Find open PRs for this branch via REST
    result = _gh("api", f"repos/{repo}/pulls?head={repo.split('/')[0]}:{branch}&state=open")
    if result.returncode != 0:
        return None
    try:
        pulls = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not pulls:
        return None
    return str(pulls[0].get("html_url", "")) or None


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


def _fetch_job_log_failures(repo: str, job_id: str | int) -> str | None:
    """Download a GitHub Actions job log and return the failure section.

    Uses the REST endpoint that redirects to a plain-text log file.
    Returns None if the log cannot be fetched.
    """
    result = _gh("api", f"repos/{repo}/actions/jobs/{job_id}/logs")
    if result.returncode != 0 or not result.stdout:
        console.print(f"[dim]  ↳ job logs API rc={result.returncode}, stderr={result.stderr[:120].strip()}[/dim]")
        return None
    return _extract_test_failures(result.stdout)


def _fetch_check_run_details(repo: str, check_run: dict) -> str:
    """Fetch detailed failure info for a single check run.

    For GitHub Actions check runs, downloads the actual job log and extracts
    the failure section (pytest FAILURES block, etc.).
    Falls back to annotations for non-Actions checks.
    """
    name = check_run.get("name", "unknown")
    conclusion = check_run.get("conclusion", "")
    check_run_id = check_run.get("id")
    lines: list[str] = [f"### {name} ({conclusion})"]

    # Include structured output if present (often empty for GHA)
    output = check_run.get("output") or {}
    if output.get("title"):
        lines.append(f"Title: {output['title']}")
    if output.get("summary"):
        lines.append(output["summary"].strip())
    if output.get("text"):
        lines.append(output["text"].strip())

    # For GitHub Actions jobs, fetch the real log output.
    # The numeric job ID lives in details_url (.../jobs/{id}), not in
    # external_id (which is a UUID for GHA check runs).
    app = check_run.get("app") or {}
    app_slug = app.get("slug", "")
    external_id = check_run.get("external_id", "")
    details_url = check_run.get("details_url", "")
    job_id_match = re.search(r"/jobs?/(\d+)", details_url)
    job_id = job_id_match.group(1) if job_id_match else (external_id if external_id.isdigit() else "")
    console.print(
        f"[dim]  ↳ check run: app={app_slug!r} job_id={job_id!r} id={check_run_id} details_url={details_url!r}[/dim]"
    )
    if app_slug == "github-actions" and job_id:
        log_section = _fetch_job_log_failures(repo, job_id)
        if log_section:
            lines.append("Job log (failure section):")
            lines.append(log_section)
        else:
            console.print("[dim]  ↳ no log section extracted[/dim]")
    elif check_run_id:
        # Non-Actions check: use annotations
        ann_result = _gh("api", f"repos/{repo}/check-runs/{check_run_id}/annotations")
        console.print(f"[dim]  ↳ annotations API rc={ann_result.returncode}[/dim]")
        if ann_result.returncode == 0:
            try:
                annotations = json.loads(ann_result.stdout)
            except json.JSONDecodeError:
                annotations = []
            failure_anns = [a for a in annotations if a.get("annotation_level") in ("failure", "warning")]
            if failure_anns:
                lines.append("Annotations:")
                for ann in failure_anns[:20]:
                    path = ann.get("path", "")
                    start_line = ann.get("start_line", "")
                    msg = ann.get("message", "").strip()
                    title = ann.get("title", "")
                    loc = f"{path}:{start_line}" if path else ""
                    label = title or msg[:80]
                    detail = msg if title and msg != title else ""
                    ann_line = f"  [{loc}] {label}"
                    if detail:
                        ann_line += f"\n    {detail[:200]}"
                    lines.append(ann_line)

    return "\n".join(lines)


def _fetch_ci_failures(pr_url: str) -> str | None:
    """Fetch CI check results for the given PR URL via the REST API.

    Returns a formatted failure string with check names, output summaries,
    and annotations for each failing check, or None if all checks are passing.
    """
    parsed = _parse_pr_url(pr_url)
    if not parsed:
        return None
    repo, pr_number = parsed

    # Get PR head SHA via REST
    pr_result = _gh("api", f"repos/{repo}/pulls/{pr_number}", "--jq", ".head.sha")
    if pr_result.returncode != 0:
        return None
    sha = pr_result.stdout.strip()
    if not sha:
        return None

    # Get check runs for that commit via REST
    runs_result = _gh("api", f"repos/{repo}/commits/{sha}/check-runs")
    if runs_result.returncode != 0:
        return None

    try:
        data = json.loads(runs_result.stdout)
    except json.JSONDecodeError:
        return None

    check_runs = data.get("check_runs", [])
    failing = [c for c in check_runs if c.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required")]
    if not failing:
        return None

    sections = [_fetch_check_run_details(repo, c) for c in failing]
    return "Failing checks:\n\n" + "\n\n".join(sections)


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
