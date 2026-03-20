"""Add human feedback directly to the discussion."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

from agent_design.discussion import run_discussion_turn
from agent_design.git_ops import checkpoint, detect_existing_worktree
from agent_design.state import load_round_state, save_round_state

console = Console()


@click.command()
@click.argument("comment", type=str)
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to target repository (default: current directory)",
)
def feedback(comment: str, repo_path: Path):
    """Add human feedback directly to the discussion.

    COMMENT: Your feedback comment
    """
    asyncio.run(async_feedback(comment, repo_path))


async def async_feedback(comment: str, repo_path: Path):
    """Async implementation of feedback command."""
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Load state
        state = load_round_state(worktree_path)

        # Append to DISCUSSION.md
        discussion_file = worktree_path / "DISCUSSION.md"
        with open(discussion_file, "a") as f:
            f.write(f"\n\n## [Human/Mark]\n\n{comment}\n")

        console.print("✓ Feedback added to DISCUSSION.md")

        # Run discussion turn
        console.print("\n[bold cyan]Running discussion turn...[/bold cyan]")
        convergence = await run_discussion_turn(worktree_path, state)

        # Update state
        if convergence:
            state.phase = "awaiting_human"
            console.print("\n[bold green]✓ Convergence achieved![/bold green]")

        save_round_state(worktree_path, state)

        # Checkpoint
        round_num = state.discussion_turns
        tag = f"chk-round-{round_num}"
        checkpoint(worktree_path, f"checkpoint: discussion round {round_num} with feedback", tag)
        state.checkpoint_tag = tag
        save_round_state(worktree_path, state)
        console.print(f"\n✓ Checkpoint: {tag}")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()
