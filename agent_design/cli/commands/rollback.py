"""Roll back to a specific checkpoint."""

from pathlib import Path

import click
from rich.console import Console

from agent_design.git_ops import detect_existing_worktree, rollback_to
from agent_design.state import load_round_state, save_round_state

console = Console()


@click.command()
@click.argument("tag", type=str)
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current directory)",
)
def rollback(tag: str, repo_path: Path) -> None:
    """Roll back to a specific checkpoint.

    TAG: Checkpoint tag to roll back to (e.g., 'chk-phase-1')
    """
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Confirm rollback
        console.print(f"[bold yellow]⚠ Rolling back to {tag}[/bold yellow]")
        console.print("This will discard all changes after this checkpoint.")
        if not click.confirm("Continue?"):
            console.print("Rollback cancelled.")
            return

        # Perform rollback
        rollback_to(worktree_path, tag)
        console.print(f"✓ Rolled back to {tag}")

        # Update state to reflect checkpoint
        state = load_round_state(worktree_path)
        state.checkpoint_tag = tag

        save_round_state(worktree_path, state)
        console.print("✓ ROUND_STATE.json updated")

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort() from e
