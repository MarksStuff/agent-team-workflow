"""agent-design refresh-domain — refresh a domain expert's volatile knowledge."""

from pathlib import Path

import click
from rich.console import Console

from agent_design.config import PLUGIN_CORE
from agent_design.launcher import run_solo
from agent_design.prompts import build_refresh_domain_start

console = Console()


@click.command(name="refresh-domain")
@click.option(
    "--agent",
    "agent_name",
    required=True,
    help="Name of the domain expert to refresh (e.g. claude_expert)",
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the target repository (default: current dir)",
)
def refresh_domain(agent_name: str, repo_path: Path) -> None:
    """Refresh the volatile knowledge of a domain expert agent.

    AGENT is the bare name of the domain expert (e.g. claude_expert).
    """
    repo_path = repo_path.resolve()

    # Strip .md suffix if present
    if agent_name.endswith(".md"):
        agent_name = agent_name[:-3]

    memory_path = PLUGIN_CORE / "memory" / f"{agent_name}.md"
    if not memory_path.exists():
        console.print(f"[red]✗ Memory file not found at {memory_path}[/red]")
        raise click.Abort() from None

    console.print(f"\n[bold]agent-design refresh-domain[/bold] — [cyan]{agent_name}[/cyan]\n")

    task_prompt = build_refresh_domain_start(agent_name, memory_path)
    worktree_path = repo_path / ".agent-design"
    rc = run_solo(agent_name, task_prompt, worktree_path, repo_path)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print(f"[green]✓[/green] Refresh domain session complete for [cyan]{agent_name}[/cyan].\n")
