"""agent-design next — run the next design stage (team session)."""

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import checkpoint, detect_existing_worktree
from agent_design.launcher import run_team
from agent_design.prompts import ENG_MANAGER_FEEDBACK_START, ENG_MANAGER_REVIEW_START
from agent_design.state import RoundState, load_round_state, save_round_state

console = Console()

ROXY_GITHUB_TOKEN = Path.home() / ".roxy_github_token"


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command using Roxy's token."""
    env_token = ROXY_GITHUB_TOKEN.read_text().strip() if ROXY_GITHUB_TOKEN.exists() else None
    import os

    env = os.environ.copy()
    if env_token:
        env["GH_TOKEN"] = env_token
    return subprocess.run(["gh", *args], capture_output=True, text=True, env=env)


def _fetch_pr_feedback(pr_url: str, round_num: int, worktree_path: Path) -> Path:
    """Fetch PR review comments and write to feedback/human-round-N.md."""
    feedback_dir = worktree_path / "feedback"
    feedback_dir.mkdir(exist_ok=True)
    feedback_file = feedback_dir / f"human-round-{round_num}.md"

    result = _gh("pr", "view", pr_url, "--json", "reviews,comments", "--jq", ".reviews[].body, .comments[].body")
    if result.returncode != 0:
        console.print(f"[yellow]⚠ Could not fetch PR comments: {result.stderr}[/yellow]")
        console.print("Add feedback manually to: " + str(feedback_file))
        feedback_file.write_text(f"# Human Feedback — Round {round_num}\n\n(add feedback here)\n")
    else:
        feedback_file.write_text(f"# Human Feedback — Round {round_num}\n\n{result.stdout.strip()}\n")
        console.print(f"[green]✓[/green] PR feedback written to {feedback_file.name}")

    return feedback_file


def _create_or_update_pr(state_phase_before: str, worktree_path: Path, state: RoundState) -> str | None:
    """Create PR after first review, or push updates for subsequent rounds."""
    import os

    target_repo = Path(state.target_repo)
    slug = state.feature_slug
    pr_url = state.pr_url

    # Copy design artifacts from worktree to target repo
    design_dir = target_repo / "docs" / "design" / slug
    design_dir.mkdir(parents=True, exist_ok=True)
    for artifact in ["DESIGN.md", "DECISIONS.md"]:
        src = worktree_path / artifact
        if src.exists():
            (design_dir / artifact).write_text(src.read_text())

    # Commit to target repo
    env = os.environ.copy()
    if ROXY_GITHUB_TOKEN.exists():
        env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()

    subprocess.run(
        ["git", "add", f"docs/design/{slug}/"],
        cwd=target_repo,
        env=env,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "--no-verify", "-m", f"design: {slug} — update design artifacts"],
        cwd=target_repo,
        env=env,
        check=True,
    )
    subprocess.run(
        ["git", "push"],
        cwd=target_repo,
        env=env,
        check=True,
    )

    if pr_url is None:
        # First time — create PR
        result = _gh(
            "pr",
            "create",
            "--repo",
            _get_repo_name(target_repo),
            "--title",
            f"design: {slug}",
            "--body",
            f"Design document for: {state.feature_request}\n\nArtifacts: `docs/design/{slug}/`",
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            console.print(f"[green]✓[/green] PR created: {url}")
            return url
        else:
            console.print(f"[yellow]⚠ PR creation failed: {result.stderr}[/yellow]")
    else:
        console.print(f"[green]✓[/green] PR updated: {pr_url}")

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
    # Handle git@github.com:owner/repo.git or https://github.com/owner/repo
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

    Stage 2 (first call): agent team design review.
    Stage 3+ (subsequent calls): agent team incorporates your PR feedback.
    """
    repo_path = repo_path.resolve()
    worktree_path = repo_path / ".agent-design"

    if not detect_existing_worktree(repo_path):
        console.print("[red]✗ No active session found. Run 'agent-design init' first.[/red]")
        raise click.Abort() from None

    state = load_round_state(worktree_path)
    console.print(f"\n[bold]agent-design next[/bold] — [cyan]{state.feature_slug}[/cyan] (phase: {state.phase})\n")

    if state.phase == "open_discussion":
        # ── Stage 2: design review agent team ────────────────────────────────
        console.print(Panel("Stage 2 — Agent team: design review", border_style="magenta"))
        start_message = ENG_MANAGER_REVIEW_START.format(
            feature_request=state.feature_request,
        )
        rc = run_team(worktree_path, Path(state.target_repo), start_message)
        if rc != 0:
            console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

        state.discussion_turns += 1
        state.completed.append("open_discussion")
        state.phase = "awaiting_human"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, "stage 2: design review complete", "chk-review")
        console.print("[green]✓[/green] Checkpoint: chk-review\n")

        # Push design artifacts and create PR
        pr_url = _create_or_update_pr("open_discussion", worktree_path, state)
        if pr_url:
            state.pr_url = pr_url
            state.checkpoint_tag = "chk-review"
            save_round_state(worktree_path, state)

        console.print(
            Panel(
                "Review the PR, leave comments, then run:\n\n"
                "  [bold cyan]agent-design next[/bold cyan]\n\n"
                "to have the team incorporate your feedback.",
                title="[green]✓ Design review complete[/green]",
                border_style="green",
            )
        )

    elif state.phase == "awaiting_human":
        # ── Stage 3+: incorporate human feedback ─────────────────────────────
        round_num = state.discussion_turns + 1
        console.print(
            Panel(
                f"Stage {round_num + 2} — Agent team: incorporating feedback (round {round_num})",
                border_style="magenta",
            )
        )

        if state.pr_url:
            _fetch_pr_feedback(state.pr_url, round_num, worktree_path)
        else:
            console.print(
                f"[yellow]⚠ No PR URL in state — add feedback manually to feedback/human-round-{round_num}.md[/yellow]"
            )

        start_message = ENG_MANAGER_FEEDBACK_START.format(round_num=round_num)
        rc = run_team(worktree_path, Path(state.target_repo), start_message)
        if rc != 0:
            console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

        state.discussion_turns += 1
        tag = f"chk-feedback-{round_num}"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, f"stage {round_num + 2}: feedback round {round_num} complete", tag)
        console.print(f"[green]✓[/green] Checkpoint: {tag}\n")

        _create_or_update_pr("awaiting_human", worktree_path, state)

    else:
        console.print(f"[red]✗ Unexpected phase: {state.phase}[/red]")
        raise click.Abort() from None
