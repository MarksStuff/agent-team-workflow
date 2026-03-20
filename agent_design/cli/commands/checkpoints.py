"""List all checkpoints for the current session."""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from agent_design.git_ops import detect_existing_worktree, get_checkpoints

console = Console()


@click.command()
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current directory)",
)
def checkpoints(repo_path: Path) -> None:
    """List all checkpoints for the current session."""
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Get checkpoints
        chks = get_checkpoints(worktree_path)

        if not chks:
            console.print("[yellow]No checkpoints found.[/yellow]")
            return

        # Create table
        table = Table(title="Checkpoints", show_header=True)
        table.add_column("Tag", style="bold cyan")
        table.add_column("Message")
        table.add_column("Date", style="dim")

        for chk in chks:
            table.add_row(chk.tag, chk.message, chk.date)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort() from e
