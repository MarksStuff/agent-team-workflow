"""Close an agent design session."""

from pathlib import Path

import click
from rich.console import Console

from agent_design.git_ops import (
    checkpoint,
    delete_orphan_branch,
    detect_existing_worktree,
    remove_worktree,
)
from agent_design.state import load_round_state, save_round_state

console = Console()


@click.command()
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current directory)",
)
@click.option(
    "--delete-branch",
    is_flag=True,
    help="Delete the orphan branch (local and remote)",
)
def close(repo_path: Path, delete_branch: bool) -> None:
    """Close an agent design session.

    Removes worktree and optionally deletes the orphan branch.
    """
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Load state
        state = load_round_state(worktree_path)

        # Confirm close
        console.print(f"[bold yellow]⚠ Closing session:[/bold yellow] {state.feature_slug}")
        if not click.confirm("Continue?"):
            console.print("Close cancelled.")
            return

        # Final checkpoint
        console.print("\n[bold]Creating final checkpoint...[/bold]")
        state.phase = "complete"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, "checkpoint: session complete", "chk-complete")
        console.print("✓ Final checkpoint created")

        # Remove worktree
        console.print("\n[bold]Removing worktree...[/bold]")
        remove_worktree(repo_path)
        console.print("✓ Worktree removed")

        # Delete branch if requested
        if delete_branch:
            branch_name = f"agent-design/{state.feature_slug}"
            console.print(f"\n[bold]Deleting branch {branch_name}...[/bold]")

            # Confirm branch deletion
            if click.confirm("Delete branch locally and on remote?"):
                try:
                    delete_orphan_branch(repo_path, branch_name, remote=True)
                    console.print("✓ Branch deleted (local and remote)")
                except Exception as e:
                    console.print(f"[yellow]⚠ Branch deletion failed: {e}[/yellow]")
            else:
                console.print("[dim]Branch not deleted (can be deleted manually later)[/dim]")
        else:
            console.print(
                f"\n[dim]Orphan branch 'agent-design/{state.feature_slug}' remains (use --delete-branch to remove)[/dim]"
            )

        console.print("\n[bold green]✓ Session closed successfully![/bold green]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort() from e
