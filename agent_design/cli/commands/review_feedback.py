"""agent-design review-feedback — process PR review comments into agent memory files."""

import json
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_print_team
from agent_design.prompts import build_review_feedback_start

console = Console()


def _fetch_pr_comments(pr_url: str) -> str:
    """Fetch all review comments from a GitHub pull request via gh CLI.

    Uses `gh pr view --json` to retrieve PR comments and reviews.
    Returns a formatted string suitable for inclusion in an agent prompt.

    Args:
        pr_url: GitHub PR URL (e.g. https://github.com/owner/repo/pull/42)

    Returns:
        Formatted string of all review comments (empty string if none)

    Raises:
        click.UsageError: If the URL is invalid, gh is not installed, or gh fails
    """
    # Validate that it's a GitHub URL
    if not pr_url.startswith("https://github.com/"):
        raise click.UsageError(f"Invalid PR URL: {pr_url!r}. Must be a GitHub URL.")

    try:
        result = subprocess.run(
            ["gh", "pr", "view", pr_url, "--json", "comments,reviews"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise click.UsageError("gh CLI not found — install it from https://cli.github.com/") from None

    if result.returncode != 0:
        raise click.UsageError(
            f"gh CLI failed (exit {result.returncode}): {result.stderr.strip() or 'no error output'}"
        )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise click.UsageError(f"Could not parse gh output as JSON: {e}") from e

    lines: list[str] = []

    # Handle both list (plain array) and object formats ({"comments": [...], "reviews": [...]})
    if isinstance(data, list):
        comment_list: list = data
        review_list: list = []
    else:
        comment_list = data.get("comments", [])
        review_list = data.get("reviews", [])

    for comment in comment_list:
        body = comment.get("body", "").strip()
        user_info = comment.get("user", comment.get("author", {}))
        user = user_info.get("login", "reviewer") if isinstance(user_info, dict) else "reviewer"
        if body:
            lines.append(f"[{user}]: {body}")

    for review in review_list:
        body = review.get("body", "").strip()
        user_info = review.get("user", review.get("author", {}))
        user = user_info.get("login", "reviewer") if isinstance(user_info, dict) else "reviewer"
        if body:
            lines.append(f"[{user} review]: {body}")

    return "\n\n".join(lines) if lines else ""


def _get_project_slug(repo_path: Path) -> str:
    """Derive a project slug from ROUND_STATE.json or fall back to directory name."""
    worktree_path = repo_path / ".agent-design"
    state_file = worktree_path / "ROUND_STATE.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text())
            slug = data.get("feature_slug")
            if slug:
                return str(slug)
        except Exception:
            pass
    return repo_path.name


@click.command(name="review-feedback")
@click.option(
    "--pr",
    "pr_url",
    required=True,
    help="GitHub pull request URL to fetch review comments from",
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def review_feedback(pr_url: str, repo_path: Path) -> None:
    """Fetch PR review comments and broadcast them to agent memory files.

    Fetches all review comments from the given GitHub PR URL via the gh CLI,
    then launches a --print multi-agent session where each agent reads the
    comments and self-updates their own memory file if relevant.
    """
    repo_path = repo_path.resolve()
    project_slug = _get_project_slug(repo_path)

    console.print(f"\n[bold]agent-design review-feedback[/bold] — [cyan]{project_slug}[/cyan]\n")
    console.print(f"[dim]Fetching PR comments from {pr_url}...[/dim]")

    try:
        pr_comments = _fetch_pr_comments(pr_url)
    except click.UsageError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise click.Abort() from None

    if not pr_comments:
        console.print("[yellow]No review comments found on this PR.[/yellow]")
        return

    console.print(
        Panel(
            f"PR:      [dim]{pr_url}[/dim]\nProject: [dim]{project_slug}[/dim]",
            title="PR Feedback Memory Update Session",
            border_style="blue",
        )
    )

    start_message = build_review_feedback_start(
        pr_comments=pr_comments,
        pr_url=pr_url,
    )
    worktree_path = repo_path / ".agent-design"
    rc = run_print_team(worktree_path, repo_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] PR feedback memory update session complete.\n")
