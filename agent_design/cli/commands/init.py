"""agent-design init — set up worktree, run Architect stages 0 and 1."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.git_ops import checkpoint, detect_existing_worktree, setup_worktree
from agent_design.launcher import run_solo
from agent_design.prompts import AGENT_ARCHITECT, STAGE_0_BASELINE, STAGE_1_INITIAL_DRAFT
from agent_design.state import RoundState, generate_slug, load_round_state, save_round_state

console = Console()


@click.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("feature_request")
def init(repo_path: Path, feature_request: str) -> None:
    """Initialize a new agent design session.

    REPO_PATH: path to the target repository
    FEATURE_REQUEST: description of the feature to design
    """
    repo_path = repo_path.resolve()
    slug = generate_slug(feature_request)

    console.print(f"\n[bold]agent-design init[/bold] — [cyan]{slug}[/cyan]")
    console.print(f"Target repo: {repo_path}")
    console.print(f"Feature:     {feature_request}\n")

    # ── Crash recovery: detect existing worktree ─────────────────────────────
    worktree_path = repo_path / ".agent-design"
    if detect_existing_worktree(repo_path):
        existing = load_round_state(worktree_path)
        console.print(
            Panel(
                f"Found existing session: [cyan]{existing.feature_slug}[/cyan] "
                f"(phase: {existing.phase})\n"
                "Use [bold]agent-design resume[/bold] to continue, or delete "
                ".agent-design manually to start fresh.",
                title="[yellow]Session already exists[/yellow]",
                border_style="yellow",
            )
        )
        raise click.Abort() from None

    # ── Set up git worktree and orphan branch ────────────────────────────────
    console.print("[dim]Setting up git worktree...[/dim]")
    worktree_path = setup_worktree(repo_path, slug)
    console.print(f"[green]✓[/green] Worktree ready at {worktree_path}")

    # ── Initial state ─────────────────────────────────────────────────────────
    state = RoundState(
        feature_slug=slug,
        feature_request=feature_request,
        target_repo=str(repo_path),
        phase="baseline",
    )
    save_round_state(worktree_path, state)
    checkpoint(worktree_path, "init: session created", "chk-init")
    console.print("[green]✓[/green] Checkpoint: chk-init\n")

    # ── Stage 0: Architect writes BASELINE.md ────────────────────────────────
    console.print(Panel("Stage 0 — Architect: codebase analysis", border_style="blue"))
    rc = run_solo(
        system_prompt=AGENT_ARCHITECT,
        task_prompt=STAGE_0_BASELINE.format(
            target_repo=repo_path,
            feature_request=feature_request,
        ),
        worktree_path=worktree_path,
        target_repo=repo_path,
    )
    if rc != 0:
        console.print(f"[red]✗ Stage 0 failed (exit {rc})[/red]")
        raise click.Abort() from None

    state.phase = "initial_draft"
    state.completed.append("baseline")
    save_round_state(worktree_path, state)
    checkpoint(worktree_path, "stage 0: baseline analysis complete", "chk-baseline")
    console.print("[green]✓[/green] BASELINE.md written — checkpoint: chk-baseline\n")

    # ── Stage 1: Architect writes DESIGN.md v1 ───────────────────────────────
    console.print(Panel("Stage 1 — Architect: initial design draft", border_style="blue"))
    rc = run_solo(
        system_prompt=AGENT_ARCHITECT,
        task_prompt=STAGE_1_INITIAL_DRAFT.format(feature_request=feature_request),
        worktree_path=worktree_path,
        target_repo=repo_path,
    )
    if rc != 0:
        console.print(f"[red]✗ Stage 1 failed (exit {rc})[/red]")
        raise click.Abort() from None

    state.phase = "open_discussion"
    state.completed.append("initial_draft")
    save_round_state(worktree_path, state)
    checkpoint(worktree_path, "stage 1: initial design draft complete", "chk-initial-draft")
    console.print("[green]✓[/green] DESIGN.md written — checkpoint: chk-initial-draft\n")

    # ── Done ──────────────────────────────────────────────────────────────────
    console.print(
        Panel(
            "[green]Stages 0 and 1 complete.[/green]\n\n"
            "Review [bold].agent-design/BASELINE.md[/bold] and "
            "[bold].agent-design/DESIGN.md[/bold], then run:\n\n"
            "  [bold cyan]agent-design next[/bold cyan]\n\n"
            "to start the agent team design review.",
            title="[green]✓ Init complete[/green]",
            border_style="green",
        )
    )
