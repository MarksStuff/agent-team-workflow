"""agent-design review-proposal — print a pending agent proposal for review."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


@click.command(name="review-proposal")
@click.argument("name")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository (default: current dir)",
)
def review_proposal(name: str, repo_path: Path) -> None:
    """Print a pending agent proposal for human review.

    NAME is the proposal name (e.g., cryptography_expert).
    The proposal file must exist at .agent-design/proposals/<NAME>.md.

    After reviewing, run:
      agent-design apply-proposal <NAME>
    to write the agent definition to disk.
    """
    repo_path = repo_path.resolve()
    proposal_path = repo_path / ".agent-design" / "proposals" / f"{name}.md"

    if not proposal_path.exists():
        console.print(f"[red]✗ Proposal not found: {proposal_path}[/red]")
        raise click.Abort() from None

    content = proposal_path.read_text()

    console.print(f"\n[bold]agent-design review-proposal[/bold] — [cyan]{name}[/cyan]\n")
    console.print(Panel(content, title=f"Proposal: {name}", border_style="blue"))
    console.print(f"\n[dim]To apply this proposal, run:[/dim]\n  [bold]agent-design apply-proposal {name}[/bold]\n")
