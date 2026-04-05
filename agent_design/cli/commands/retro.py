"""agent-design retro — run a sprint retrospective session."""

import json
from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_print_team
from agent_design.prompts import build_retro_start

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
            data = json.loads(state_file.read_text())
            slug = data.get("feature_slug")
            if slug:
                return str(slug)
        except Exception:
            pass
    return repo_path.name


@click.command()
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
@click.option(
    "--observation",
    default=None,
    help="Human observation to seed the retrospective as a first-class input",
)
def retro(repo_path: Path, observation: str | None) -> None:
    """Run a sprint retrospective session for the current project.

    Launches a multi-agent retrospective: the Facilitator shares sprint
    artifacts with the full team, each agent reflects independently, the
    team votes on the top good/bad items, discusses root causes and
    improvements, claims action items for their own memory, and produces
    RETRO.md. Unclaimed items are flagged as possible missing agent roles.
    """
    repo_path = repo_path.resolve()
    project_slug = _get_project_slug(repo_path)
    today = date.today().isoformat()

    console.print(f"\n[bold]agent-design retro[/bold] — [cyan]{project_slug}[/cyan]\n")
    console.print(
        Panel(
            f"Project: [dim]{project_slug}[/dim]\nDate:    [dim]{today}[/dim]",
            title="Retrospective Session",
            border_style="blue",
        )
    )

    start_message = build_retro_start(project_slug=project_slug, date=today, human_observation=observation)
    worktree_path = repo_path / ".agent-design"
    rc = run_print_team(worktree_path, repo_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Retrospective session complete.\n")
