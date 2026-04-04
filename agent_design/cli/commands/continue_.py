"""agent-design continue — continue the design workflow (team session)."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import checkpoint, detect_existing_worktree
from agent_design.launcher import run_team
from agent_design.prompts import build_continue_start
from agent_design.state import load_round_state, save_round_state

console = Console()


@click.command(name="continue")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def continue_cmd(repo_path: Path) -> None:
    """Continue the design workflow for an active session.

    Loads the current state, builds a generic continue prompt, and launches
    the agent team. The EM reads the worktree and determines the appropriate
    phase (design review, feedback incorporation, etc.).
    """
    repo_path = repo_path.resolve()
    worktree_path = repo_path / ".agent-design"

    if not detect_existing_worktree(repo_path):
        console.print("[red]✗ No active session found. Run 'agent-design init' first.[/red]")
        raise click.Abort() from None

    state = load_round_state(worktree_path)
    console.print(f"\n[bold]agent-design continue[/bold] — [cyan]{state.feature_slug}[/cyan]\n")

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
