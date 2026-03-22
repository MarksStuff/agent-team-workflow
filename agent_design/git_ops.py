"""Git operations for worktree management and checkpointing."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


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

    flags = ["-c", "commit.gpgsign=false", "-c", "tag.gpgSign=false"]
    if not _get("user.name"):
        flags += ["-c", "user.name=agent-design"]
    if not _get("user.email"):
        flags += ["-c", "user.email=agent-design@localhost"]
    return flags


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

    # Ensure the orphan branch does not exist (delete if it does)
    try:
        subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        # If show-ref returns 0, branch exists. Delete it.
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # Branch does not exist, or delete failed (this is handled by check=True)
        pass

    # Create orphan branch
    subprocess.run(
        ["git", "checkout", "--orphan", branch_name],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Remove all files from staging
    subprocess.run(
        ["git", "rm", "-rf", "."],
        cwd=repo_path,
        check=False,  # May fail if no files exist
        capture_output=True,
    )

    # Create initial empty commit
    subprocess.run(
        ["git", *_nosign_flags(repo_path), "commit", "--allow-empty", "-m", f"init: agent design session — {slug}"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Return to main branch
    subprocess.run(
        ["git", "checkout", "main"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Add worktree
    subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch_name],
        cwd=repo_path,
        check=True,
        capture_output=True,
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
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=worktree_path,
                check=True,
                capture_output=True,
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
    # Stage all changes
    subprocess.run(
        ["git", "add", "-A"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Commit
    subprocess.run(
        ["git", *_nosign_flags(worktree_path), "commit", "-m", message],
        cwd=worktree_path,
        check=True,
        capture_output=True,
    )

    # Create tag (force-overwrite in case a previous failed run left one behind)
    subprocess.run(
        ["git", *_nosign_flags(worktree_path), "tag", "-f", tag],
        cwd=worktree_path,
        check=True,
        capture_output=True,
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
    subprocess.run(
        ["git", "checkout", tag],
        cwd=worktree_path,
        check=True,
        capture_output=True,
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
    # Get all tags with commit info
    result = subprocess.run(
        ["git", "log", "--oneline", "--decorate", "--tags", "--no-walk"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        text=True,
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
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
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
        subprocess.run(
            ["git", "worktree", "remove", str(worktree_path)],
            cwd=repo_path,
            check=True,
            capture_output=True,
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
    # Delete local branch
    subprocess.run(
        ["git", "branch", "-D", branch_name],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Delete remote branch if requested
    if remote:
        subprocess.run(
            ["git", "push", "origin", "--delete", branch_name],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
