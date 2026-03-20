"""Run the next discussion round."""

import asyncio
import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.discussion import run_discussion_turn
from agent_design.git_ops import checkpoint, detect_existing_worktree
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
def next_round(repo_path: Path) -> None:
    """Run the next discussion round.

    Fetches PR comments (if PR exists), runs a discussion turn, and checkpoints.
    """
    asyncio.run(async_next_round(repo_path))


async def async_next_round(repo_path: Path) -> None:
    """Async implementation of next command."""
    repo_path = repo_path.resolve()

    # Detect worktree
    worktree_path = detect_existing_worktree(repo_path)
    if not worktree_path:
        console.print("[yellow]No active agent-design session found.[/yellow]")
        return

    try:
        # Load state
        state = load_round_state(worktree_path)

        console.print(Panel.fit(f"🔄 Discussion Round {state.discussion_turns + 1}", style="bold blue"))

        # Fetch PR comments if PR exists
        if state.pr_url:
            console.print("\n[bold]Fetching PR comments...[/bold]")
            try:
                result = subprocess.run(
                    ["gh", "pr", "view", state.pr_url, "--json", "comments", "--jq", ".comments[].body"],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                if result.stdout.strip():
                    # Write to feedback file
                    feedback_dir = worktree_path / "feedback"
                    feedback_dir.mkdir(exist_ok=True)
                    feedback_file = feedback_dir / f"human-round-{state.discussion_turns + 1}.md"
                    feedback_file.write_text(result.stdout)

                    # Append to DISCUSSION.md
                    discussion_file = worktree_path / "DISCUSSION.md"
                    with open(discussion_file, "a") as f:
                        f.write(f"\n\n## [Human/Mark]\n\n{result.stdout}\n")

                    console.print("✓ PR comments added to DISCUSSION.md")
                else:
                    console.print("(No new PR comments)")

            except subprocess.CalledProcessError:
                console.print("[yellow]⚠ Could not fetch PR comments (gh CLI required)[/yellow]")

        # Run discussion turn
        console.print("\n[bold cyan]Running discussion turn...[/bold cyan]")
        convergence = await run_discussion_turn(worktree_path, state)

        # Update state
        if convergence:
            state.phase = "awaiting_human"
            console.print("\n[bold green]✓ Convergence achieved![/bold green]")
            console.print("Review the design and provide feedback, or approve the PR.")

        save_round_state(worktree_path, state)

        # Checkpoint
        round_num = state.discussion_turns
        tag = f"chk-round-{round_num}"
        checkpoint(worktree_path, f"checkpoint: discussion round {round_num} complete", tag)
        state.checkpoint_tag = tag
        save_round_state(worktree_path, state)
        console.print(f"\n✓ Checkpoint: {tag}")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {e}")
        raise click.Abort() from e
