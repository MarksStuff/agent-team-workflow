"""State management for agent design sessions."""

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class RoundState:
    """State for a design session.

    Attributes:
        feature_slug: Short identifier for the feature (e.g., 'news-admin-cli')
        feature_request: Full feature request text
        target_repo: Absolute path to target repository
        discussion_turns: Number of discussion turns completed
        baseline_commit: Git commit SHA of baseline analysis (if completed)
        completed: List of completed phase names
        pr_url: GitHub PR URL (if created)
        checkpoint_tag: Most recent checkpoint tag
    """

    feature_slug: str
    feature_request: str
    target_repo: str
    discussion_turns: int = 0
    baseline_commit: str | None = None
    completed: list[str] = field(default_factory=list)
    pr_url: str | None = None
    checkpoint_tag: str | None = None


def load_round_state(worktree_path: Path) -> RoundState:
    """Load round state from ROUND_STATE.json.

    Args:
        worktree_path: Path to the .agent-design worktree

    Returns:
        RoundState object

    Raises:
        FileNotFoundError: If ROUND_STATE.json doesn't exist
        ValueError: If JSON is invalid
    """
    state_file = worktree_path / "ROUND_STATE.json"
    if not state_file.exists():
        raise FileNotFoundError(f"ROUND_STATE.json not found at {state_file}")

    try:
        with open(state_file) as f:
            data = json.load(f)
        # Strip unknown keys for backward-compat with old ROUND_STATE.json
        # files that may contain legacy fields (e.g. 'phase').
        known_fields = {f.name for f in fields(RoundState)}
        data = {k: v for k, v in data.items() if k in known_fields}
        return RoundState(**data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in ROUND_STATE.json: {e}") from e


def save_round_state(worktree_path: Path, state: RoundState) -> None:
    """Save round state to ROUND_STATE.json.

    Args:
        worktree_path: Path to the .agent-design worktree
        state: RoundState object to save
    """
    state_file = worktree_path / "ROUND_STATE.json"
    with open(state_file, "w") as f:
        json.dump(asdict(state), f, indent=2)


def generate_slug(feature_request: str) -> str:
    """Generate a slug from a feature request.

    Converts to lowercase, replaces spaces and special chars with hyphens,
    and truncates to 40 characters.

    Args:
        feature_request: Full feature request text

    Returns:
        Slug string (e.g., 'news-admin-cli')
    """
    import re

    # Convert to lowercase
    slug = feature_request.lower()

    # Replace spaces and special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)

    # Remove leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to 40 chars
    if len(slug) > 40:
        slug = slug[:40].rstrip("-")

    return slug
