"""agent-design apply-proposal — write an approved agent definition to disk."""

import re
from pathlib import Path

import click
from rich.console import Console

console = Console()


def _parse_proposed_location(content: str) -> str | None:
    """Extract path from '**Proposed location:** `<path>`' line.

    Returns the path string (may contain ~), or None if not found.
    Backticks around the path are stripped.
    """
    match = re.search(r"\*\*Proposed location:\*\*\s+`([^`]+)`", content)
    if match:
        return match.group(1)
    # Fallback: no backticks
    match = re.search(r"\*\*Proposed location:\*\*\s+(\S+)", content)
    if match:
        return match.group(1)
    return None


def _parse_agent_definition(content: str) -> str | None:
    """Extract the content of the fenced block under ## Agent Definition.

    Handles two formats:
    1. Triple-backtick fenced block after '## Agent Definition' heading
    2. Raw content (including --- YAML delimiters) after the heading

    Returns the block content without fence markers, or None if not found.
    """
    # Find the ## Agent Definition heading (flexible match)
    heading_match = re.search(r"^## Agent Definition[^\n]*\n", content, re.MULTILINE)
    if not heading_match:
        return None

    after_heading = content[heading_match.end():]

    # Check for triple-backtick fence first
    backtick_match = re.search(r"^```[^\n]*\n(.*?)^```", after_heading, re.MULTILINE | re.DOTALL)
    if backtick_match:
        return backtick_match.group(1)

    # No backtick fence — extract raw content until next ## heading or end of file
    next_heading = re.search(r"^##", after_heading, re.MULTILINE)
    if next_heading:
        raw = after_heading[: next_heading.start()]
    else:
        raw = after_heading

    stripped = raw.strip()
    return stripped if stripped else None


@click.command(name="apply-proposal")
@click.argument("name")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def apply_proposal(name: str, repo_path: Path) -> None:
    """Write an approved agent definition from a proposal file to disk.

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

    location_str = _parse_proposed_location(content)
    if location_str is None:
        console.print(
            "[red]✗ Malformed proposal: missing '**Proposed location:**' field.[/red]"
        )
        raise click.Abort() from None

    agent_def = _parse_agent_definition(content)
    if agent_def is None:
        console.print(
            "[red]✗ Malformed proposal: missing '## Agent Definition' section or fenced block.[/red]"
        )
        raise click.Abort() from None

    dest = Path(location_str).expanduser()

    if dest.exists():
        console.print(
            f"[red]✗ Destination already exists: {dest}[/red]\n"
            "  The file was NOT overwritten. Remove it manually if you want to apply this proposal."
        )
        raise click.Abort() from None

    if not dest.parent.exists():
        console.print(
            f"[red]✗ Parent directory does not exist: {dest.parent}[/red]\n"
            "  Create the directory first, then run apply-proposal again."
        )
        raise click.Abort() from None

    dest.write_text(agent_def)
    console.print(f"[green]✓[/green] Applied proposal [cyan]{name}[/cyan] — written to [cyan]{dest}[/cyan]\n")
