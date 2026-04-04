"""agent-design apply-suggestion — apply a prompt suggestion from RETRO.md to an agent file."""

import re
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_solo
from agent_design.prompts import build_apply_suggestion_start

console = Console()


def _parse_retro_suggestion(content: str, suggestion_id: str) -> str | None:
    """Extract the suggestion text for a given ID from RETRO.md content.

    Args:
        content: Full text content of RETRO.md
        suggestion_id: Suggestion ID to find (e.g. 'PS-1', 'ps-1'). Normalised to uppercase.

    Returns:
        The suggestion text (first line + any indented continuation lines, whitespace stripped),
        or None if not found.
    """
    normalised_id = suggestion_id.upper()

    # The ID must be in "PS-N" format — need at least one char after "PS-"
    # "PS-" alone (no suffix) should not match anything
    id_match = re.match(r"^PS-(.+)$", normalised_id)
    if not id_match:
        return None

    # Build pattern to find "- [PS-N] ..." line
    # Escape any regex metacharacters in the normalised ID
    escaped_id = re.escape(normalised_id)
    pattern = rf"^- \[{escaped_id}\] (.+)$"

    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = re.match(pattern, line, re.IGNORECASE)
        if m:
            first_line = m.group(1)
            # Collect continuation lines: lines that start with 2+ spaces
            continuation_parts = []
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if next_line == "" or (len(next_line) > 0 and len(next_line) - len(next_line.lstrip()) < 2):
                    # Blank line or less than 2 leading spaces — end of entry
                    break
                continuation_parts.append(next_line.strip())

            parts = [first_line] + continuation_parts
            return " ".join(parts)

    return None


@click.command(name="apply-suggestion")
@click.argument("suggestion_id")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def apply_suggestion(suggestion_id: str, repo_path: Path) -> None:
    """Apply a prompt suggestion from RETRO.md to the relevant agent definition file.

    SUGGESTION_ID is the suggestion identifier from RETRO.md (e.g. PS-1, ps-1).
    The ID is normalised to uppercase before searching.

    Launches a --print single-agent (architect) session that reads the suggestion
    and edits the relevant agent definition file in ~/.claude/agents/.
    """
    repo_path = repo_path.resolve()
    retro_path = repo_path / ".agent-design" / "RETRO.md"

    if not retro_path.exists():
        raise click.UsageError(f"No RETRO.md found at {retro_path}. Run `agent-design retro` first.")

    retro_content = retro_path.read_text()
    normalised_id = suggestion_id.upper()

    suggestion_text = _parse_retro_suggestion(retro_content, normalised_id)
    if suggestion_text is None:
        raise click.UsageError(f"Suggestion {normalised_id!r} not found in RETRO.md")

    agents_dir = str(Path.home() / ".claude" / "agents")

    console.print(f"\n[bold]agent-design apply-suggestion[/bold] — [cyan]{normalised_id}[/cyan]\n")
    console.print(
        Panel(
            f"Suggestion: [dim]{normalised_id}[/dim]\nAgents dir: [dim]{agents_dir}[/dim]",
            title="Apply Suggestion Session",
            border_style="blue",
        )
    )

    task_prompt = build_apply_suggestion_start(
        suggestion_id=normalised_id,
        suggestion_text=suggestion_text,
        agents_dir=agents_dir,
    )

    worktree_path = repo_path / ".agent-design"
    rc = run_solo(
        agent_name="architect",
        task_prompt=task_prompt,
        worktree_path=worktree_path,
        target_repo=repo_path,
    )
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Apply suggestion session complete.\n")
