"""agent-design apply-suggestion — apply a prompt suggestion from RETRO.md."""

import re
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_apply_suggestion
from agent_design.prompts import build_apply_suggestion_start

console = Console()


@click.command(name="apply-suggestion")
@click.argument("suggestion_id")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def apply_suggestion(suggestion_id: str, repo_path: Path) -> None:
    """Apply a prompt suggestion from RETRO.md to an agent definition file.

    SUGGESTION_ID is the identifier from RETRO.md (e.g. PS-1 or ps-1).
    """
    repo_path = repo_path.resolve()
    suggestion_id = suggestion_id.upper()

    retro_path = repo_path / ".agent-design" / "RETRO.md"
    if not retro_path.exists():
        console.print(f"[red]✗ RETRO.md not found at {retro_path}[/red]")
        raise click.Abort() from None

    retro_content = retro_path.read_text()
    pattern = r"\[" + re.escape(suggestion_id) + r"\]\s+(\S+\.md):\s+(.+)"
    match = re.search(pattern, retro_content)
    if not match:
        console.print(f"[red]✗ Suggestion {suggestion_id} not found in RETRO.md[/red]")
        raise click.Abort() from None

    agent_file = match.group(1)
    suggestion_text = match.group(2).strip()

    console.print(f"\n[bold]agent-design apply-suggestion[/bold] — [cyan]{suggestion_id}[/cyan]\n")
    console.print(
        Panel(
            f"Suggestion: [dim]{suggestion_id}[/dim]\n"
            f"Agent file: [dim]{agent_file}[/dim]\n"
            f"Change:     [dim]{suggestion_text[:120]}{'…' if len(suggestion_text) > 120 else ''}[/dim]",
            title="Apply Suggestion Session",
            border_style="blue",
        )
    )

    start_message = build_apply_suggestion_start(
        suggestion_id=suggestion_id,
        agent_file=agent_file,
        suggestion_text=suggestion_text,
    )
    worktree_path = repo_path / ".agent-design"
    rc = run_apply_suggestion(worktree_path, repo_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Apply suggestion session complete.\n")
