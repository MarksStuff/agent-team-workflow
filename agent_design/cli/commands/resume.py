"""Resume an existing agent design session."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.cli.commands.status import status
from agent_design.git_ops import detect_existing_worktree
from agent_design.state import load_round_state

console = Console()


@click.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
def resume(repo_path: Path):
    """Resume an existing agent design session.

    REPO_PATH: Path to target repository
    """
    repo_path = repo_path.resolve()

    console.print(Panel.fit("🔄 Resuming Agent Design Session", style="bold blue"))

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found at this repository.[/yellow]")
        console.print("Run 'agent-design init <repo> <feature_request>' to start a new session.")
        return

    try:
        # Load and display state
        state = load_round_state(worktree_path)

        console.print(f"\n[bold green]✓ Session found![/bold green]")
        console.print(f"Feature: [bold]{state.feature_slug}[/bold]")
        console.print(f"Phase: [cyan]{state.phase}[/cyan]")
        console.print(f"Discussion turns: {state.discussion_turns}")

        console.print("\n[dim]Use 'agent-design status' for full details[/dim]")
        console.print("[dim]Use 'agent-design next' to continue[/dim]")

    except Exception as e:
        console.print(f"[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()
