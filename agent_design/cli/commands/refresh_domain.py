"""agent-design refresh-domain — refresh a domain expert's volatile knowledge."""

from datetime import date
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.launcher import run_solo
from agent_design.prompts import build_refresh_domain_start

console = Console()


def _get_local_agents_dir(repo_path: Path) -> Path:
    """Return the local agents directory for the given repo."""
    return repo_path / "plugins" / "local" / "agents"


@click.command(name="refresh-domain")
@click.option(
    "--agent",
    "agent_name",
    required=True,
    help="Name of the domain expert agent to refresh (e.g., claude_expert)",
)
@click.option(
    "--repo-path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository containing the agent file (default: current dir)",
)
def refresh_domain(agent_name: str, repo_path: Path) -> None:
    """Refresh a domain expert's volatile knowledge from its authoritative sources.

    Runs a --print session where the named agent reads its memory file,
    checks its authoritative sources for changes, and updates the
    Volatile Knowledge section with current information.

    The agent file must exist at plugins/local/agents/<AGENT>.md in the repo.
    """
    repo_path = repo_path.resolve()

    agent_file = _get_local_agents_dir(repo_path) / f"{agent_name}.md"
    if not agent_file.exists():
        console.print(f"[red]✗ Agent not found: {agent_file}[/red]")
        raise click.Abort() from None

    today = date.today().isoformat()

    console.print(f"\n[bold]agent-design refresh-domain[/bold] — [cyan]{agent_name}[/cyan]\n")
    console.print(
        Panel(
            f"Agent:  [dim]{agent_name}[/dim]\n"
            f"Date:   [dim]{today}[/dim]\n"
            f"Action: [dim]refresh volatile knowledge from authoritative sources[/dim]",
            title="Domain Expert Refresh",
            border_style="blue",
        )
    )

    start_message = build_refresh_domain_start(agent_name=agent_name, today=today)
    worktree_path = repo_path / ".agent-design"
    rc = run_solo(agent_name, start_message, worktree_path, repo_path)
    if rc != 0:
        console.print(f"[yellow]⚠ Claude exited with code {rc}[/yellow]")

    console.print("[green]✓[/green] Domain expert refresh complete.\n")
