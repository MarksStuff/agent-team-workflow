"""Show current session status."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from agent_design.git_ops import detect_existing_worktree
from agent_design.state import load_round_state

console = Console()


@click.command()
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current directory)",
)
def status(repo_path: Path):
    """Show current session status."""
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        console.print("Run 'agent-design init <repo> <feature_request>' to start a new session.")
        return

    try:
        # Load state
        state = load_round_state(worktree_path)

        # Create status table
        table = Table(title="Agent Design Session Status", show_header=False, box=None)
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")

        table.add_row("Feature", state.feature_slug)
        table.add_row("Phase", state.phase)
        table.add_row("Discussion Turns", str(state.discussion_turns))
        table.add_row("Target Repo", state.target_repo)
        table.add_row("Baseline Commit", state.baseline_commit or "N/A")
        table.add_row("Checkpoint", state.checkpoint_tag or "N/A")
        table.add_row("PR URL", state.pr_url or "Not created")
        table.add_row("Completed Phases", ", ".join(state.completed) if state.completed else "None")

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()
