"""agent-design remember — broadcast a human correction to agent memory files."""

from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_print_team
from agent_design.prompts import build_remember_start

console = Console()


def _get_project_slug(repo_path: Path) -> str:
    """Derive a project slug from ROUND_STATE.json or fall back to directory name.

    Args:
        repo_path: Path to the target repository

    Returns:
        Project slug string
    """
    worktree_path = repo_path / ".agent-design"
    state_file = worktree_path / "ROUND_STATE.json"
    if state_file.exists():
        try:
            import json

            data = json.loads(state_file.read_text())
            slug = data.get("feature_slug")
            if slug:
                return str(slug)
        except Exception:
            pass
    return repo_path.name


@click.command()
@click.argument("correction")
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def remember(correction: str, repo_path: Path) -> None:
    """Broadcast a human correction or override to all agent memory files.

    Launches a --print multi-agent session where each agent reads the
    correction and self-updates their own memory file if it is relevant
    to their role.

    CORRECTION is the text of the human override or decision to record.
    Example: agent-design remember "Mark prefers sync pipelines at small scale"
    """
    repo_path = repo_path.resolve()

    if not correction.strip():
        console.print("[red]✗ Correction text cannot be empty.[/red]")
        raise click.Abort() from None

    project_slug = _get_project_slug(repo_path)
    today = date.today().isoformat()

    console.print(f"\n[bold]agent-design remember[/bold] — [cyan]{project_slug}[/cyan]\n")
    console.print(
        Panel(
            f"Correction: [dim]{correction[:120]}{'…' if len(correction) > 120 else ''}[/dim]\n"
            f"Project:    [dim]{project_slug}[/dim]\n"
            f"Date:       [dim]{today}[/dim]",
            title="Memory Update Session",
            border_style="blue",
        )
    )

    start_message = build_remember_start(
        correction=correction,
        project_slug=project_slug,
        date=today,
    )
    worktree_path = repo_path / ".agent-design"
    rc = run_print_team(worktree_path, repo_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Memory update session complete.\n")
