"""agent-design review-proposal — print a proposal file for human review."""

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
    help="Path to the target repository (default: current dir)",
)
def review_proposal(name: str, repo_path: Path) -> None:
    """Print a proposal file for human review.

    NAME is the proposal name (e.g. cryptography_expert).
    """
    repo_path = repo_path.resolve()

    # Strip .md suffix if present
    if name.endswith(".md"):
        name = name[:-3]

    proposal_path = repo_path / ".agent-design" / "proposals" / f"{name}.md"
    if not proposal_path.exists():
        console.print(
            f"[red]✗ Proposal not found: {proposal_path}[/red]\n"
            f"  Expected: .agent-design/proposals/{name}.md"
        )
        raise click.Abort() from None

    content = proposal_path.read_text()
    console.print(Panel(content, title=f"Agent Proposal: {name}", border_style="blue"))
