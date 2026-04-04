"""agent-design next — run the next design stage (team session)."""

import json as json_module
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import _nosign_flags, _run_git_in_target, checkpoint, detect_existing_worktree
from agent_design.launcher import run_team
from agent_design.prompts import build_continue_start
from agent_design.state import RoundState, load_round_state, save_round_state

console = Console()

ROXY_GITHUB_TOKEN = Path.home() / ".roxy_github_token"


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command using Roxy's token (used for PR creation/push only)."""
    env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


# ---------------------------------------------------------------------------
# GitHub REST API helpers — no gh CLI required, just a token
# ---------------------------------------------------------------------------


def _github_token() -> str | None:
    """Return a GitHub API token from ~/.roxy_github_token or env vars."""
    if ROXY_GITHUB_TOKEN.exists():
        return ROXY_GITHUB_TOKEN.read_text().strip()
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _github_get(path: str) -> object:
    """GET from the GitHub REST API and return parsed JSON.

    Args:
        path: e.g. 'repos/owner/repo/pulls/1/comments'

    Raises:
        click.Abort: On HTTP error with diagnostic output.
    """
    token = _github_token()
    url = f"https://api.github.com/{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json_module.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        console.print(f"[red]✗ GitHub API {url} → HTTP {e.code}[/red]")
        console.print(f"[red]  {body[:300]}[/red]")
        if e.code == 401:
            console.print("[dim]  Hint: provide ~/.roxy_github_token or set GITHUB_TOKEN env var[/dim]")
        raise click.Abort() from e


def _parse_pr_url(pr_url: str) -> tuple[str, str, str]:
    """Parse a GitHub PR URL into (owner, repo, number).

    e.g. https://github.com/owner/repo/pull/123 → ('owner', 'repo', '123')
    """
    url = pr_url.rstrip("/")
    parts = url.split("/")
    # ['https:', '', 'github.com', 'owner', 'repo', 'pull', '123']
    return parts[-4], parts[-3], parts[-1]


def _fetch_pr_feedback(pr_url: str, round_num: int, worktree_path: Path) -> Path:
    """Fetch PR review comments via GitHub REST API and write to feedback/human-round-N.md.

    Uses urllib directly — no gh CLI or gh auth required, only a GitHub token.

    Raises:
        click.Abort: On API or URL parse error.
    """
    feedback_dir = worktree_path / "feedback"
    feedback_dir.mkdir(exist_ok=True)
    feedback_file = feedback_dir / f"human-round-{round_num}.md"

    try:
        owner, repo, number = _parse_pr_url(pr_url)
    except (IndexError, ValueError) as e:
        console.print(f"[red]✗ Cannot parse PR URL '{pr_url}': {e}[/red]")
        raise click.Abort() from e

    console.print(f"[dim]Fetching PR feedback for {owner}/{repo}#{number}...[/dim]")
    lines: list[str] = [f"# Human Feedback — Round {round_num}\n"]

    # 1. Inline diff comments (line-level review comments)
    inline = _github_get(f"repos/{owner}/{repo}/pulls/{number}/comments")
    assert isinstance(inline, list)
    if inline:
        lines.append("## Inline Review Comments\n")
        for c in inline:
            author = c.get("user", {}).get("login", "unknown")
            path = c.get("path", "?")
            line = c.get("line") or c.get("original_line") or "?"
            body = c.get("body", "").strip()
            lines.append(f"### {author} on `{path}` line {line}\n\n{body}\n")

    # 2. General PR thread comments
    issue_comments = _github_get(f"repos/{owner}/{repo}/issues/{number}/comments")
    assert isinstance(issue_comments, list)

    # 3. Review submission bodies (the summary text on each review)
    reviews = _github_get(f"repos/{owner}/{repo}/pulls/{number}/reviews")
    assert isinstance(reviews, list)
    review_bodies = [r for r in reviews if r.get("body", "").strip()]

    thread = list(issue_comments) + review_bodies
    if thread:
        lines.append("## Reviews & General Comments\n")
        for item in thread:
            author = item.get("user", {}).get("login", "unknown")
            body = item.get("body", "").strip()
            lines.append(f"### {author}\n\n{body}\n")

    feedback_file.write_text("\n".join(lines) + "\n")
    total = len(inline) + len(thread)
    console.print(f"[green]✓[/green] PR feedback written to {feedback_file.name} ({total} comments)")
    return feedback_file


def _create_or_update_pr(worktree_path: Path, state: RoundState) -> str | None:
    """Create or update PR for design artifacts."""
    target_repo = Path(state.target_repo)
    slug = state.feature_slug
    pr_url = state.pr_url
    design_branch_name = f"feat/design-{slug}"
    repo_env = os.environ.copy()

    if ROXY_GITHUB_TOKEN.exists():
        repo_env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()

    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=target_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    original_branch = result.stdout.strip()

    try:
        if pr_url is None:
            console.print(f"[dim]Creating new branch {design_branch_name} in {target_repo.name}...[/dim]")
            _run_git_in_target(
                ["checkout", "-b", design_branch_name, f"origin/{original_branch}"],
                cwd=target_repo,
                env=repo_env,
                error_msg="Failed to create new branch",
            )
        else:
            console.print(f"[dim]Checking out branch {design_branch_name} in {target_repo.name}...[/dim]")
            _run_git_in_target(
                ["checkout", design_branch_name],
                cwd=target_repo,
                env=repo_env,
                error_msg="Failed to checkout existing branch",
            )
            console.print(f"[dim]Pulling latest from origin/{design_branch_name}...[/dim]")
            _run_git_in_target(
                ["pull", "origin", design_branch_name],
                cwd=target_repo,
                env=repo_env,
                error_msg="Failed to pull latest changes",
            )

        design_dir = target_repo / "docs" / "design" / slug
        design_dir.mkdir(parents=True, exist_ok=True)
        for artifact in ["DESIGN.md", "DECISIONS.md"]:
            src = worktree_path / artifact
            if src.exists():
                (design_dir / artifact).write_text(src.read_text())
                console.print(f"[green]✓[/green] Copied {artifact}")
            else:
                console.print(f"[yellow]⚠ {artifact} not found at {src}[/yellow]")

        _run_git_in_target(
            ["add", "."],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to add design artifacts",
        )
        _run_git_in_target(
            [*_nosign_flags(target_repo), "commit", "--no-verify", "-m", f"design: {slug} — update design artifacts"],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to commit design artifacts",
        )
        console.print(f"[green]✓[/green] Design artifacts committed to {design_branch_name}")

        _run_git_in_target(
            ["push", "-u", "origin", design_branch_name],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to push design branch",
        )
        console.print(f"[green]✓[/green] Branch {design_branch_name} pushed to origin")

        if pr_url is None:
            console.print("[dim]Creating GitHub PR...[/dim]")
            gh_result = _gh(
                "pr",
                "create",
                "--repo",
                _get_repo_name(target_repo),
                "--title",
                f"design: {slug}",
                "--body",
                f"Design document for: {state.feature_request}\n\nArtifacts: `docs/design/{slug}/`",
                "--head",
                design_branch_name,
                "--base",
                "main",
            )
            if gh_result.returncode == 0:
                url = gh_result.stdout.strip()
                console.print(f"[green]✓[/green] PR created: {url}")
                return url
            else:
                console.print(f"[red]✗ PR creation failed: {gh_result.stderr}[/red]")
        else:
            console.print(f"[green]✓[/green] PR updated: {pr_url}")

    except subprocess.CalledProcessError:
        console.print("[red]✗ Git/GitHub operation failed. Check logs above for details.[/red]")
        return None
    finally:
        console.print(f"[dim]Switching back to {original_branch}...[/dim]")
        _run_git_in_target(
            ["checkout", original_branch],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to switch back to original branch",
        )

    return pr_url


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


@click.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def next_round(repo_path: Path) -> None:
    """Run the next design stage.

    Deprecated: use 'agent-design continue' instead.
    This command is kept as a backward-compatible alias.
    """
    repo_path = repo_path.resolve()
    worktree_path = repo_path / ".agent-design"

    if not detect_existing_worktree(repo_path):
        console.print("[red]✗ No active session found. Run 'agent-design init' first.[/red]")
        raise click.Abort() from None

    state = load_round_state(worktree_path)
    console.print(f"\n[bold]agent-design next[/bold] — [cyan]{state.feature_slug}[/cyan]\n")

    console.print(Panel("Continuing design workflow — agent team session", border_style="magenta"))

    start_message = build_continue_start(state.feature_request)
    rc = run_team(worktree_path, Path(state.target_repo), start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    state.discussion_turns += 1
    tag = f"chk-continue-{state.discussion_turns}"
    save_round_state(worktree_path, state)
    checkpoint(worktree_path, f"continue: session {state.discussion_turns} complete", tag)
    console.print(f"[green]✓[/green] Checkpoint: {tag}\n")

    pr_url = _create_or_update_pr(worktree_path, state)
    if pr_url:
        state.pr_url = pr_url
        state.checkpoint_tag = tag
        save_round_state(worktree_path, state)
