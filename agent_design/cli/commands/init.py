"""Initialize a new agent design session."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.discussion import run_baseline_phase, run_initial_draft_phase
from agent_design.git_ops import (
    checkpoint,
    detect_existing_worktree,
    get_current_commit,
    setup_worktree,
)
from agent_design.state import RoundState, generate_slug, save_round_state

console = Console()


@click.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("feature_request", type=str)
def init(repo_path: Path, feature_request: str):
    """Initialize a new agent design session.

    REPO_PATH: Path to target repository
    FEATURE_REQUEST: Feature request description
    """
    asyncio.run(async_init(repo_path, feature_request))


async def async_init(repo_path: Path, feature_request: str):
    """Async implementation of init command."""
    repo_path = repo_path.resolve()

    console.print(Panel.fit("🚀 Initializing Agent Design Session", style="bold blue"))

    # Generate slug
    slug = generate_slug(feature_request)
    console.print(f"Feature slug: [bold]{slug}[/bold]")

    # Check for existing worktree
    existing_worktree = detect_existing_worktree(repo_path)
    if existing_worktree:
        console.print(
            "[yellow]⚠ Existing .agent-design worktree detected. Use 'agent-design resume' instead.[/yellow]"
        )
        return

    try:
        # Setup worktree
        console.print("\n[bold]Setting up git worktree...[/bold]")
        worktree_path = setup_worktree(repo_path, slug)
        console.print(f"✓ Worktree created at: {worktree_path}")

        # Get baseline commit
        baseline_commit = get_current_commit(repo_path)

        # Create initial state
        state = RoundState(
            feature_slug=slug,
            feature_request=feature_request,
            target_repo=str(repo_path),
            phase="baseline",
            baseline_commit=baseline_commit,
        )
        save_round_state(worktree_path, state)
        console.print("✓ ROUND_STATE.json created")

        # Phase 0: Baseline analysis
        console.print("\n[bold cyan]Phase 0: Baseline Analysis[/bold cyan]")
        await run_baseline_phase(worktree_path, state)

        # Checkpoint Phase 0
        state.phase = "baseline"
        state.completed.append("baseline")
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, "checkpoint: phase-0 baseline analysis complete", "chk-phase-0")
        console.print("✓ Checkpoint: chk-phase-0")

        # Phase 1: Initial design draft
        console.print("\n[bold cyan]Phase 1: Initial Design Draft[/bold cyan]")
        state.phase = "initial_draft"
        save_round_state(worktree_path, state)
        await run_initial_draft_phase(worktree_path, state)

        # Checkpoint Phase 1
        state.completed.append("initial_draft")
        state.phase = "open_discussion"
        save_round_state(worktree_path, state)
        checkpoint(worktree_path, "checkpoint: phase-1 initial design draft complete", "chk-phase-1")
        console.print("✓ Checkpoint: chk-phase-1")

        console.print("\n[bold green]✓ Initialization complete![/bold green]")
        console.print(f"\nNext steps:")
        console.print("  1. Review DESIGN.md in .agent-design/")
        console.print("  2. Run 'agent-design next' to start discussion phase")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort()
