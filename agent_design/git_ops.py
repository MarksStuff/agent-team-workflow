"""Git operations for worktree management and checkpointing."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

console = Console()


def _nosign_flags(cwd: Path) -> list[str]:
    """Return git -c flags that disable signing and ensure an identity exists.

    Disables both commit and tag signing — these are internal tracking commits
    and tags on orphan branches; they don't need to satisfy signing policies
    enforced on main (e.g. Apple's ac-sign / tag.gpgSign).

    Only injects user.name / user.email when genuinely absent; leaves any
    already-configured identity untouched.
    """

    def _get(key: str) -> str | None:
        r = subprocess.run(
            ["git", "config", "--get", key],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None

    flags = ["-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false"]
    if not _get("user.name"):
        flags += ["-c", "user.name=agent-design"]
    if not _get("user.email"):
        flags += ["-c", "user.email=agent-design@localhost"]
    return flags


# Helper to run git commands with error reporting
def _run_git_in_target(cmd_args: list[str], cwd: Path, env: dict[str, str], error_msg: str) -> None:
    result = subprocess.run(
        ["git"] + cmd_args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]✗ {error_msg}: {result.returncode}[/red]")
        console.print(f"[dim]  stdout: {result.stdout.strip()}[/dim]")
        console.print(f"[dim]  stderr: {result.stderr.strip()}[/dim]")
        raise subprocess.CalledProcessError(result.returncode, cmd_args, result.stdout, result.stderr)


@dataclass
class Checkpoint:
    """Checkpoint metadata.

    Attributes:
        tag: Git tag name
        message: Commit message
        date: Commit date string
    """

    tag: str
    message: str
    date: str


def setup_worktree(repo_path: Path, slug: str) -> Path:
    """Create orphan branch and worktree for design session.

    Args:
        repo_path: Path to target repository
        slug: Feature slug for branch naming

    Returns:
        Path to the created worktree (.agent-design/)

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    branch_name = f"agent-design/{slug}"
    worktree_path = repo_path / ".agent-design"
    repo_env = os.environ.copy()

    # Ensure any previous worktree registration is cleared
    console.print(f"[dim]Pruning stale Git worktree entries in {repo_path.name}...[/dim]")
    _run_git_in_target(
        ["worktree", "prune"],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to prune stale worktree entries",
    )

    # If the worktree directory physically exists, remove it forcibly
    if worktree_path.exists():
        console.print(f"[dim]Removing existing worktree directory {worktree_path} in {repo_path.name}...[/dim]")
        _run_git_in_target(
            ["worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_path,
            env=repo_env,
            error_msg="Failed to remove existing worktree directory",
        )

    # Ensure the orphan branch does not exist (delete if it does)
    try:
        # Check if branch exists
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            cwd=repo_path,
            check=True,
            capture_output=True,
            env=repo_env,  # Added env
        )
        # If show-ref returns 0, branch exists. Delete it forcibly.
        console.print(f"[dim]Deleting existing branch {branch_name} in {repo_path.name}...[/dim]")
        _run_git_in_target(
            ["branch", "-D", "--force", branch_name],
            cwd=repo_path,
            env=repo_env,
            error_msg="Failed to delete existing orphan branch",
        )
        console.print(f"[green]✓[/green] Deleted old branch {branch_name}.")
    except subprocess.CalledProcessError:
        # Branch does not exist, or delete failed (this is handled by _run_git_in_target)
        console.print(
            f"[dim]Branch {branch_name} does not exist in {repo_path.name}, or could not be deleted (safe to ignore).[/dim]"
        )
        pass

    # Create orphan branch
    _run_git_in_target(
        ["checkout", "--orphan", branch_name],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to create orphan branch",
    )

    # Remove all files from staging
    _run_git_in_target(
        ["rm", "-rf", "."],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to remove files from staging",
    )

    # Create initial empty commit — --no-verify skips pre-commit hooks,
    # which don't apply to this internal bookkeeping commit on an orphan branch.
    _run_git_in_target(
        [
            *_nosign_flags(repo_path),
            "commit",
            "--allow-empty",
            "--no-verify",
            "-m",
            f"init: agent design session — {slug}",
        ],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to create initial empty commit",
    )

    # Return to main branch
    _run_git_in_target(
        ["checkout", "main"],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to switch back to main branch",
    )

    # Add worktree
    _run_git_in_target(
        ["worktree", "add", str(worktree_path), branch_name],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to add worktree",
    )

    # Add to .gitignore if not present
    gitignore_path = repo_path / ".gitignore"
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        if ".agent-design" not in gitignore_content:
            with open(gitignore_path, "a") as f:
                f.write("\n.agent-design\n")
    else:
        gitignore_path.write_text(".agent-design\n")

    return worktree_path


def detect_existing_worktree(repo_path: Path) -> Path | None:
    """Detect if .agent-design worktree already exists.

    Args:
        repo_path: Path to target repository

    Returns:
        Path to worktree if it exists, None otherwise
    """
    worktree_path = repo_path / ".agent-design"
    if worktree_path.exists() and worktree_path.is_dir():
        # Verify it's actually a git worktree
        try:
            repo_env = os.environ.copy()
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=worktree_path,
                check=True,
                capture_output=True,
                env=repo_env,  # Added env
            )
            return worktree_path
        except subprocess.CalledProcessError:
            return None
    return None


def checkpoint(worktree_path: Path, message: str, tag: str) -> None:
    """Create a checkpoint commit and tag.

    Args:
        worktree_path: Path to the .agent-design worktree
        message: Commit message
        tag: Tag name (e.g., 'chk-phase-1')

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    repo_env = os.environ.copy()

    # Stage all changes
    _run_git_in_target(
        ["add", "-A"],
        cwd=worktree_path,
        env=repo_env,
        error_msg="Failed to stage changes for checkpoint",
    )

    # Commit — --no-verify skips pre-commit hooks; _nosign_flags disables
    # GPG/ac-sign signing. Both are needed on Apple work machines.
    _run_git_in_target(
        [*_nosign_flags(worktree_path), "commit", "--no-verify", "-m", message],
        cwd=worktree_path,
        env=repo_env,
        error_msg="Failed to commit checkpoint",
    )

    # Create tag (force-overwrite in case a previous failed run left one behind)
    _run_git_in_target(
        ["tag", "-f", tag],
        cwd=worktree_path,
        env=repo_env,
        error_msg="Failed to create tag",
    )
    # Note: orphan branch is local crash-recovery state; no remote push needed.


def rollback_to(worktree_path: Path, tag: str) -> None:
    """Roll back worktree to a specific checkpoint.

    Args:
        worktree_path: Path to the .agent-design worktree
        tag: Tag name to roll back to

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    repo_env = os.environ.copy()
    _run_git_in_target(
        ["checkout", tag],
        cwd=worktree_path,
        env=repo_env,
        error_msg="Failed to rollback to tag",
    )


def get_checkpoints(worktree_path: Path) -> list[Checkpoint]:
    """Get list of all checkpoints.

    Args:
        worktree_path: Path to the .agent-design worktree

    Returns:
        List of Checkpoint objects, most recent first

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    repo_env = os.environ.copy()
    # Get all tags with commit info
    result = subprocess.run(
        ["git", "log", "--oneline", "--decorate", "--tags", "--no-walk"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        text=True,
        env=repo_env,
    )

    checkpoints = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # Parse format: "abc123 (tag: chk-phase-1) commit message"
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue

        rest = parts[1]
        if "(tag:" not in rest:
            continue

        # Extract tag name
        tag_start = rest.index("(tag:") + 5
        tag_end = rest.index(")", tag_start)
        tag = rest[tag_start:tag_end].strip()

        # Extract message (everything after the closing paren)
        message = rest[tag_end + 1 :].strip()

        # Get commit date
        date_result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", tag],
            cwd=worktree_path,
            check=True,
            capture_output=True,
            text=True,
            env=repo_env,
        )
        date = date_result.stdout.strip()

        checkpoints.append(Checkpoint(tag=tag, message=message, date=date))

    return checkpoints


def get_current_commit(repo_path: Path) -> str:
    """Get current commit SHA of the target repo.

    Args:
        repo_path: Path to target repository

    Returns:
        Commit SHA string

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    repo_env = os.environ.copy()
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        env=repo_env,
    )
    return result.stdout.strip()


def remove_worktree(repo_path: Path) -> None:
    """Remove the .agent-design worktree.

    Args:
        repo_path: Path to target repository

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    worktree_path = repo_path / ".agent-design"
    if worktree_path.exists():
        repo_env = os.environ.copy()
        _run_git_in_target(
            ["worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_path,
            env=repo_env,
            error_msg="Failed to remove worktree",
        )


def delete_orphan_branch(repo_path: Path, branch_name: str, remote: bool = True) -> None:
    """Delete the orphan branch locally and optionally on remote.

    Args:
        repo_path: Path to target repository
        branch_name: Name of the branch to delete (e.g., 'agent-design/news-admin-cli')
        remote: Whether to also delete from remote (default: True)

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    repo_env = os.environ.copy()
    # Delete local branch
    _run_git_in_target(
        ["branch", "-D", "--force", branch_name],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to delete local branch",
    )

    # Delete remote branch if requested
    if remote:
        _run_git_in_target(
            ["push", "origin", "--delete", branch_name],
            cwd=repo_path,
            env=repo_env,
            error_msg="Failed to delete remote branch",
        )


def create_impl_branch(repo_path: Path, slug: str) -> str:
    """Create feat/impl-{slug} branch from origin/main in the target repo.

    Args:
        repo_path: Path to target repository
        slug: Feature slug for branch naming

    Returns:
        The created branch name

    Raises:
        subprocess.CalledProcessError: If git commands fail
    """
    branch_name = f"feat/impl-{slug}"
    repo_env = os.environ.copy()

    # Fetch latest main so we branch from the current tip
    _run_git_in_target(
        ["fetch", "origin", "main"],
        cwd=repo_path,
        env=repo_env,
        error_msg="Failed to fetch origin/main",
    )

    # Create and checkout the impl branch from origin/main
    _run_git_in_target(
        ["checkout", "-b", branch_name, "origin/main"],
        cwd=repo_path,
        env=repo_env,
        error_msg=f"Failed to create branch {branch_name}",
    )

    return branch_name
