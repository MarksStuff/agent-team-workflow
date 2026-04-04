"""agent-design retro — run a retrospective session to capture learnings."""

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
    help="Your observation about the sprint to include in the retrospective.",
)
def retro(repo_path: Path, observation: str | None) -> None:
    """Run a retrospective session on the most recent sprint.

    Launches a --print multi-agent retrospective session where the Retrospective
    Facilitator reads DISCUSSION.md, TASKS.md, and DECISIONS.md, identifies friction
    points, prompts each agent to self-update their memory, and produces RETRO.md.

    Requires .agent-design/DISCUSSION.md to exist (run `agent-design init` first).
    TASKS.md and DECISIONS.md are optional.
    """
    repo_path = repo_path.resolve()
    agent_design_dir = repo_path / ".agent-design"

    discussion_path = agent_design_dir / "DISCUSSION.md"
    if not discussion_path.exists():
        raise click.UsageError(f"No DISCUSSION.md found at {discussion_path}. Run `agent-design init` first.")

    tasks_file = repo_path / "TASKS.md"
    tasks_path = str(tasks_file) if tasks_file.exists() else None

    decisions_file = agent_design_dir / "DECISIONS.md"
    decisions_path = str(decisions_file) if decisions_file.exists() else None

    project_slug = _get_project_slug(repo_path)
    today = date.today().isoformat()

    console.print(f"\n[bold]agent-design retro[/bold] — [cyan]{project_slug}[/cyan]\n")
    console.print(
        Panel(
            f"Project:    [dim]{project_slug}[/dim]\n"
            f"Date:       [dim]{today}[/dim]\n"
            f"Discussion: [dim]{discussion_path}[/dim]",
            title="Retrospective Session",
            border_style="blue",
        )
    )

    start_message = build_retro_start(
        project_slug=project_slug,
        date=today,
        discussion_path=str(discussion_path),
        tasks_path=tasks_path,
        decisions_path=decisions_path,
        human_observation=observation,
    )
    worktree_path = repo_path / ".agent-design"
    rc = run_print_team(worktree_path, repo_path, start_message)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Retrospective session complete.\n")
