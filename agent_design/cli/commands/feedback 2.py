"""agent-design feedback — inject human feedback mid-session."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import checkpoint, detect_existing_worktree
from agent_design.launcher import run_team_in_repo
from agent_design.prompts import build_continue_start
from agent_design.state import load_round_state, save_round_state

console = Console()


@click.command()
@click.argument("comment")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current dir)",
)
def feedback(comment: str, repo_path: Path) -> None:
    """Add human feedback directly and run a team session to incorporate it.

    COMMENT: your feedback (quote it if it contains spaces)
    """
    repo_path = repo_path.resolve()
    worktree_path = repo_path / ".agent-design"

    if not detect_existing_worktree(repo_path):
        console.print("[red]✗ No active session found. Run 'agent-design init' first.[/red]")
        raise click.Abort() from None

    state = load_round_state(worktree_path)
    round_num = state.discussion_turns + 1

    # Write feedback to file
    feedback_dir = worktree_path / "feedback"
    feedback_dir.mkdir(exist_ok=True)
    feedback_file = feedback_dir / f"human-round-{round_num}.md"
    feedback_file.write_text(f"# Human Feedback — Round {round_num}\n\n{comment}\n")
    console.print(f"[green]✓[/green] Feedback written to {feedback_file.name}\n")

    # Launch agent team to incorporate it
    console.print(
        Panel(
            f"Launching agent team to incorporate feedback (round {round_num})",
            border_style="magenta",
        )
    )
    start_message = build_continue_start(state.feature_request)
    rc = run_team_in_repo(Path(state.target_repo), worktree_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    state.discussion_turns += 1
    tag = f"chk-feedback-{round_num}"
    save_round_state(worktree_path, state)
    checkpoint(worktree_path, f"feedback round {round_num} incorporated", tag)
    console.print(f"[green]✓[/green] Checkpoint: {tag}")
