"""agent-design init — set up worktree, run Architect stages 0 and 1."""

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from agent_design.feature_extractor import extract_feature_from_doc
from agent_design.git_ops import checkpoint, detect_existing_worktree, setup_worktree
from agent_design.launcher import run_solo
from agent_design.prompts import AGENT_ARCHITECT, STAGE_0_BASELINE, STAGE_1_INITIAL_DRAFT
from agent_design.state import RoundState, generate_slug, load_round_state, save_round_state

console = Console()


@click.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("feature_request", required=False, default=None)
@click.option(
    "--doc",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path to a specification document to extract the feature from.",
)
@click.option(
    "--section",
    default=None,
    help="Heading text of the section in --doc to extract (case-sensitive, no # prefix).",
)
def init(
    repo_path: Path,
    feature_request: str | None,
    doc: Path | None,
    section: str | None,
) -> None:
    """Initialize a new agent design session.

    Provide the feature either as a free-text argument:

      agent-design init ~/repo "Build a news-admin CLI"

    Or by pointing to a section in a specification document:

      agent-design init ~/repo --doc docs/pipeline-architecture.md \\
          --section "Phase 6 — Admin & Re-run Tooling"

    The --doc/--section form makes one Claude call to extract a concise feature
    description from the document section before starting the session.
    """
    # ── Input validation ──────────────────────────────────────────────────────
    using_doc = doc is not None or section is not None

    if feature_request and using_doc:
        raise click.UsageError("Provide either a feature_request argument OR --doc/--section, not both.")
    if using_doc and not (doc and section):
        raise click.UsageError("--doc and --section must be used together.")
    if not feature_request and not using_doc:
        raise click.UsageError("Provide a feature_request argument or use --doc + --section.")

    # ── Extract feature from doc if needed ────────────────────────────────────
    if using_doc:
        assert doc is not None and section is not None  # mypy
        console.print(f"[dim]Extracting feature from {doc} § {section}...[/dim]")
        try:
            feature_request = extract_feature_from_doc(doc, section)
        except ValueError as e:
            raise click.ClickException(str(e)) from e
        except RuntimeError as e:
            raise click.ClickException(str(e)) from e
        console.print(Panel(feature_request, title="[cyan]Extracted feature[/cyan]", border_style="cyan"))

    assert feature_request is not None  # mypy — guaranteed by validation above
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
            f"  [bold cyan]agent-design next --repo-path {repo_path}[/bold cyan]\n\n"
            "to start the agent team design review.",
            title="[green]✓ Init complete[/green]",
            border_style="green",
        )
    )
