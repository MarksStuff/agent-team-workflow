"""Show diff between checkpoint and current state."""

import subprocess
from pathlib import Path

import click
from rich.console import Console

from agent_design.git_ops import detect_existing_worktree

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
def diff(tag: str, repo_path: Path) -> None:
    """Show diff between checkpoint and current state.

    TAG: Checkpoint tag to diff against (e.g., 'chk-phase-1')
    """
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Run git diff
        result = subprocess.run(
            ["git", "diff", tag, "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout:
            console.print(result.stdout)
        else:
            console.print("[dim]No changes since checkpoint.[/dim]")

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e.stderr}")
        raise click.Abort() from e
