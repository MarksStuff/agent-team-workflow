"""agent-design apply-proposal — write an approved agent proposal to disk."""

import re
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


def _parse_proposed_location(content: str) -> str | None:
    """Extract the proposed file path from a proposal."""
    match = re.search(r"\*\*Proposed location:\*\*\s+`?([^`\n]+)`?", content)
    if not match:
        return None
    return match.group(1).strip()


def _parse_agent_definition(content: str) -> str | None:
    """Extract the agent definition block from a proposal.

    Finds the '## Agent Definition (written verbatim if approved)' heading,
    then extracts from the first '---' YAML fence that follows to the end
    of the file.
    """
    # Find the Agent Definition heading
    heading_match = re.search(
        r"^## Agent Definition \(written verbatim if approved\)\s*$",
        content,
        re.MULTILINE,
    )
    if not heading_match:
        return None

    after_heading = content[heading_match.end() :]

    # Find the first '---' fence after the heading
    fence_match = re.search(r"^---\s*$", after_heading, re.MULTILINE)
    if not fence_match:
        return None

    # Extract from this '---' to end of content
    definition = after_heading[fence_match.start() :].strip()
    return definition


@click.command(name="apply-proposal")
@click.argument("name")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository (default: current dir)",
)
def apply_proposal(name: str, repo_path: Path) -> None:
    """Write an approved agent proposal to disk.

    NAME is the proposal name (e.g., cryptography_expert).
    The proposal file must exist at .agent-design/proposals/<NAME>.md.

    Reads the proposed location from the proposal, extracts the agent
    definition, and writes it to the proposed path. Creates parent
    directories as needed.
    """
    repo_path = repo_path.resolve()
    proposal_path = repo_path / ".agent-design" / "proposals" / f"{name}.md"

    if not proposal_path.exists():
        console.print(f"[red]✗ Proposal not found: {proposal_path}[/red]")
        raise click.Abort() from None

    content = proposal_path.read_text()

    proposed_location = _parse_proposed_location(content)
    if not proposed_location:
        console.print("[red]✗ Could not find 'Proposed location:' in the proposal.[/red]")
        raise click.Abort() from None

    agent_definition = _parse_agent_definition(content)
    if not agent_definition:
        console.print("[red]✗ Could not find 'Agent Definition' section in the proposal.[/red]")
        raise click.Abort() from None

    if proposed_location.startswith("~/"):
        target_path = Path.home() / proposed_location[2:]
    elif proposed_location == "~":
        target_path = Path.home()
    else:
        target_path = Path(proposed_location)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(agent_definition + "\n")

    console.print(f"\n[bold]agent-design apply-proposal[/bold] — [cyan]{name}[/cyan]\n")
    console.print(
        Panel(
            f"Proposal: [dim]{name}[/dim]\nWritten:  [dim]{target_path}[/dim]",
            title="Proposal Applied",
            border_style="green",
        )
    )
    console.print(f"[green]✓[/green] Agent definition written to [bold]{target_path}[/bold]\n")
