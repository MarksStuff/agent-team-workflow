"""Response types for GitHub operations.

Dataclasses for GitHub API and Git responses with proper type safety.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class BaseResponse:
    """Base response type with success/error pattern."""

    success: bool
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CommitInfo:
    """Git commit information."""

    sha: str
    short_sha: str
    message: str
    author: str
    date: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CommitResponse(BaseResponse):
    """Response containing commit information."""

    commit: CommitInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {"success": self.success}
        if self.error:
            result["error"] = self.error
        if self.commit:
            result["commit"] = self.commit.to_dict()
        return result


@dataclass
class BranchResponse(BaseResponse):
    """Response containing branch information."""

    branch: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {"success": self.success}
        if self.error:
            result["error"] = self.error
        if self.branch:
            result["branch"] = self.branch
        return result


@dataclass
class PRInfo:
    """Pull request information."""

    number: int
    title: str
    url: str
    state: str
    head_sha: str
    base_branch: str
    head_branch: str
    author: str
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PRResponse(BaseResponse):
    """Response containing pull request information."""

    pr: PRInfo | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, including pr field even when None."""
        result: dict[str, Any] = {"success": self.success}
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message
        # Always include pr field, even when None
        result["pr"] = self.pr.to_dict() if self.pr else None
        return result


@dataclass
class CommentInfo:
    """Comment information."""

    id: int
    type: str  # "issue_comment" or "review_comment_reply"
    body: str
    author: str
    created_at: str
    url: str
    in_reply_to_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class CommentResponse(BaseResponse):
    """Response containing comment information."""

    comment: CommentInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: dict[str, Any] = {"success": self.success}
        if self.error:
            result["error"] = self.error
        if self.comment:
            result["comment"] = self.comment.to_dict()
        return result
