"""agent-design next — run the next design stage (team session)."""

import os
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import _nosign_flags, checkpoint, detect_existing_worktree
from agent_design.launcher import run_team
from agent_design.prompts import build_feedback_start, build_review_start
from agent_design.state import RoundState, load_round_state, save_round_state

console = Console()

ROXY_GITHUB_TOKEN = Path.home() / ".roxy_github_token"


# Helper to run git commands with error reporting
def _run_git_in_target(cmd_args: list[str], cwd: Path, env: dict[str, str], error_msg: str) -> None:
    result = subprocess.run(
        ["git"] + cmd_args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]✗ {error_msg}: {result.returncode}[/red]")
        console.print(f"[dim]  stdout: {result.stdout.strip()}[/dim]")
        console.print(f"[dim]  stderr: {result.stderr.strip()}[/dim]")
        raise subprocess.CalledProcessError(result.returncode, cmd_args, result.stdout, result.stderr)


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a gh CLI command using Roxy's token."""
    env_token = ROXY_GITHUB_TOKEN.read_text().strip() if ROXY_GITHUB_TOKEN.exists() else None

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
        feedback_file.write_text(f"# Human Feedback — Round {round_num}\\n\\n(add feedback here)\\n")
    else:
        feedback_file.write_text(f"# Human Feedback — Round {round_num}\\n\\n{result.stdout.strip()}\\n")
        console.print(f"[green]✓[/green] PR feedback written to {feedback_file.name}")

    return feedback_file


def _create_or_update_pr(state_phase_before: str, worktree_path: Path, state: RoundState) -> str | None:
    """Create or update PR for design artifacts.

    Manages Git branch creation/checkout, copying artifacts, committing,
    pushing, and (for first time) creating the GitHub PR.
    """
    target_repo = Path(state.target_repo)
    slug = state.feature_slug
    pr_url = state.pr_url
    design_branch_name = f"feat/design-{slug}"
    repo_env = os.environ.copy()

    if ROXY_GITHUB_TOKEN.exists():
        repo_env["GH_TOKEN"] = ROXY_GITHUB_TOKEN.read_text().strip()

    # Get current branch to switch back to it later
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
            # First time — create new branch
            console.print(f"[dim]Creating new branch {design_branch_name} in {target_repo.name}...[/dim]")
            _run_git_in_target(
                ["checkout", "-b", design_branch_name, f"origin/{original_branch}"],  # Base on original branch
                cwd=target_repo,
                env=repo_env,
                error_msg="Failed to create new branch",
            )
        else:
            # Updating existing PR — checkout branch and pull latest
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

        # Copy design artifacts from worktree to target repo
        design_dir = target_repo / "docs" / "design" / slug
        design_dir.mkdir(parents=True, exist_ok=True)
        for artifact in ["DESIGN.md", "DECISIONS.md"]:
            src = worktree_path / artifact
            if src.exists():
                (design_dir / artifact).write_text(src.read_text())

        # Commit to target repo on the new branch
        _run_git_in_target(
            [*_nosign_flags(target_repo), "commit", "--no-verify", "-m", f"design: {slug} — update design artifacts"],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to commit design artifacts",
        )
        console.print(f"[green]✓[/green] Design artifacts committed to {design_branch_name}")

        # Push to remote
        console.print(f"[dim]Pushing {design_branch_name} to origin...[/dim]")
        _run_git_in_target(
            ["push", "-u", "origin", design_branch_name],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to push design branch",
        )
        console.print(f"[green]✓[/green] Branch {design_branch_name} pushed to origin")

        if pr_url is None:
            # First time — create PR
            console.print("[dim]Creating GitHub PR...[/dim]")
            result = _gh(
                "pr",
                "create",
                "--repo",
                _get_repo_name(target_repo),
                "--title",
                f"design: {slug}",
                "--body",
                f"Design document for: {state.feature_request}\\n\\nArtifacts: `docs/design/{slug}/`",
                "--head",
                design_branch_name,  # Specify head branch
                "--base",
                "main",  # Specify base branch
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                console.print(f"[green]✓[/green] PR created: {url}")
                return url
            else:
                console.print(f"[red]✗ PR creation failed: {result.stderr}[/red]")
        else:
            console.print(f"[green]✓[/green] PR updated: {pr_url}")

    except subprocess.CalledProcessError:
        console.print("[red]✗ Git/GitHub operation failed. Check logs above for details.[/red]")
        return None
    finally:
        # Always switch back to the original branch
        console.print(f"[dim]Switching back to original branch ({original_branch})...[/dim]")
        _run_git_in_target(
            ["checkout", original_branch],
            cwd=target_repo,
            env=repo_env,
            error_msg="Failed to switch back to original branch",
        )
        console.print(f"[green]✓[/green] Switched back to {original_branch}.")

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
    console.print(f"\\n[bold]agent-design next[/bold] — [cyan]{state.feature_slug}[/cyan] (phase: {state.phase})\\n")

    if state.phase == "open_discussion":
        # ── Stage 2: design review agent team ────────────────────────────────
        console.print(Panel("Stage 2 — Agent team: design review", border_style="magenta"))
        start_message = build_review_start(state.feature_request)
        rc = run_team(worktree_path, Path(state.target_repo), start_message)
        if rc != 0:
            console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

        state.discussion_turns += 1
        state.completed.append("open_discussion")
        state.phase = "awaiting_human"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, "stage 2: design review complete", "chk-review")
        console.print("[green]✓[/green] Checkpoint: chk-review\\n")

        # Push design artifacts and create PR
        pr_url = _create_or_update_pr("open_discussion", worktree_path, state)
        if pr_url:
            state.pr_url = pr_url
            state.checkpoint_tag = "chk-review"
            save_round_state(worktree_path, state)

        console.print(
            Panel(
                "Review the PR, leave comments, then run:\\n\\n"
                "  [bold cyan]agent-design next[/bold cyan]\\n\\n"
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

        start_message = build_feedback_start(round_num)
        rc = run_team(worktree_path, Path(state.target_repo), start_message)
        if rc != 0:
            console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

        state.discussion_turns += 1
        tag = f"chk-feedback-{round_num}"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, f"stage {round_num + 2}: feedback round {round_num} complete", tag)
        console.print(f"[green]✓[/green] Checkpoint: {tag}\\n")

        _create_or_update_pr("awaiting_human", worktree_path, state)

    else:
        console.print(f"[red]✗ Unexpected phase: {state.phase}[/red]")
        raise click.Abort() from None
