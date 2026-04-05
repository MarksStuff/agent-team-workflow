"""Integration tests for CommentTracker with GitHub operations.

Tests verify:
- get_pr_comments adds already_replied flag for tracked comments
- get_pr_comments works correctly when no tracker is provided
- post_pr_reply records successful replies in tracker
- post_pr_reply handles both review comments and issue comments
- Integration works across multiple comment types

NOTE: These tests depend on CommentTracker (from the legacy mcp_server package)
and filter_unreplied_comments (from multi_agent_workflow). They are skipped until
those dependencies are available in this project.
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from agent_design.github_ops.operations import GitHubOperations, RepositoryConfig

pytestmark = pytest.mark.skip(reason="Requires CommentTracker from mcp_server and multi_agent_workflow packages")


@pytest.fixture
def repo_config():
    """Create test repository configuration."""
    return RepositoryConfig(
        workspace=None,  # Not needed for API tests
        github_owner="test-owner",
        github_repo="test-repo",
    )


@pytest.fixture
def mock_pr():
    """Create mock PR with issue and review comments."""
    pr = Mock()
    pr.number = 123

    # Create mock issue comments
    issue_comment_1 = Mock()
    issue_comment_1.id = 1001
    issue_comment_1.user.login = "user1"
    issue_comment_1.body = "This is an issue comment"
    issue_comment_1.created_at = datetime.now(UTC)
    issue_comment_1.updated_at = datetime.now(UTC)
    issue_comment_1.html_url = "https://github.com/test/pr/1001"

    issue_comment_2 = Mock()
    issue_comment_2.id = 1002
    issue_comment_2.user.login = "user2"
    issue_comment_2.body = "Another issue comment"
    issue_comment_2.created_at = datetime.now(UTC)
    issue_comment_2.updated_at = datetime.now(UTC)
    issue_comment_2.html_url = "https://github.com/test/pr/1002"

    pr.get_issue_comments.return_value = [issue_comment_1, issue_comment_2]

    # Create mock review comments
    review_comment_1 = Mock()
    review_comment_1.id = 2001
    review_comment_1.user.login = "reviewer1"
    review_comment_1.body = "This is a review comment"
    review_comment_1.path = "src/main.py"
    review_comment_1.line = 42
    review_comment_1.created_at = datetime.now(UTC)
    review_comment_1.updated_at = datetime.now(UTC)
    review_comment_1.html_url = "https://github.com/test/pr/2001"
    review_comment_1.in_reply_to_id = None

    review_comment_2 = Mock()
    review_comment_2.id = 2002
    review_comment_2.user.login = "reviewer2"
    review_comment_2.body = "Another review comment"
    review_comment_2.path = "src/utils.py"
    review_comment_2.line = 10
    review_comment_2.created_at = datetime.now(UTC)
    review_comment_2.updated_at = datetime.now(UTC)
    review_comment_2.html_url = "https://github.com/test/pr/2002"
    review_comment_2.in_reply_to_id = None

    pr.get_review_comments.return_value = [review_comment_1, review_comment_2]

    # Create mock reviews
    review = Mock()
    review.id = 3001
    review.user.login = "reviewer1"
    review.state = "approved"
    review.body = "LGTM"
    review.submitted_at = datetime.now(UTC)
    review.commit_id = "abc123"

    pr.get_reviews.return_value = [review]

    return pr


@pytest.fixture
def github_ops_with_tracker(repo_config, comment_tracker, monkeypatch):
    """Create GitHubOperations instance with CommentTracker."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_BASE_URL", "https://api.github.com")

    with patch("agent_design.github_ops.operations.Github") as mock_github_class:
        mock_github = Mock()
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        ops = GitHubOperations(repo_config, comment_tracker=comment_tracker)
        return ops


@pytest.fixture
def github_ops_without_tracker(repo_config, monkeypatch):
    """Create GitHubOperations instance without CommentTracker."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_BASE_URL", "https://api.github.com")

    with patch("agent_design.github_ops.operations.Github") as mock_github_class:
        mock_github = Mock()
        mock_repo = Mock()
        mock_github.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github

        ops = GitHubOperations(repo_config, comment_tracker=None)
        return ops


class TestGetPRCommentsWithTracker:
    """Tests for get_pr_comments with CommentTracker integration."""

    def test_adds_already_replied_flag_to_issue_comments(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify already_replied flag is added to issue comments that have been replied to."""
        # Record one issue comment as replied
        comment_tracker.record_reply("test-owner", "test-repo", 123, 1001, "issue")

        # Mock PR retrieval
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Get PR comments
        result = github_ops_with_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True
        assert len(result["issue_comments"]) == 2

        # First comment should have already_replied flag
        comment_1 = next(c for c in result["issue_comments"] if c["id"] == 1001)
        assert "already_replied" in comment_1
        assert comment_1["already_replied"] is True

        # Second comment should not have the flag
        comment_2 = next(c for c in result["issue_comments"] if c["id"] == 1002)
        assert "already_replied" not in comment_2

    def test_adds_already_replied_flag_to_review_comments(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify already_replied flag is added to review comments that have been replied to."""
        # Record one review comment as replied
        comment_tracker.record_reply("test-owner", "test-repo", 123, 2001, "review")

        # Mock PR retrieval
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Get PR comments
        result = github_ops_with_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True
        assert len(result["review_comments"]) == 2

        # First comment should have already_replied flag
        comment_1 = next(c for c in result["review_comments"] if c["id"] == 2001)
        assert "already_replied" in comment_1
        assert comment_1["already_replied"] is True

        # Second comment should not have the flag
        comment_2 = next(c for c in result["review_comments"] if c["id"] == 2002)
        assert "already_replied" not in comment_2

    def test_handles_multiple_replied_comments(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify multiple replied comments are tracked correctly."""
        # Record multiple comments as replied
        comment_tracker.record_reply("test-owner", "test-repo", 123, 1001, "issue")
        comment_tracker.record_reply("test-owner", "test-repo", 123, 2002, "review")

        # Mock PR retrieval
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Get PR comments
        result = github_ops_with_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True

        # Check issue comment
        issue_comment = next(c for c in result["issue_comments"] if c["id"] == 1001)
        assert issue_comment.get("already_replied") is True

        # Check review comment
        review_comment = next(c for c in result["review_comments"] if c["id"] == 2002)
        assert review_comment.get("already_replied") is True

        # Other comments should not have flag
        assert "already_replied" not in next(c for c in result["issue_comments"] if c["id"] == 1002)
        assert "already_replied" not in next(c for c in result["review_comments"] if c["id"] == 2001)

    def test_no_already_replied_flags_when_no_replies(self, github_ops_with_tracker, mock_pr):
        """Verify no already_replied flags when no comments have been replied to."""
        # Mock PR retrieval (without recording any replies)
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Get PR comments
        result = github_ops_with_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True

        # No comments should have already_replied flag
        for comment in result["issue_comments"]:
            assert "already_replied" not in comment

        for comment in result["review_comments"]:
            assert "already_replied" not in comment


class TestGetPRCommentsWithoutTracker:
    """Tests for get_pr_comments without CommentTracker."""

    def test_works_without_tracker(self, github_ops_without_tracker, mock_pr):
        """Verify get_pr_comments works correctly when no tracker is provided."""
        # Mock PR retrieval
        github_ops_without_tracker.repo.get_pull.return_value = mock_pr

        # Get PR comments
        result = github_ops_without_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True
        assert len(result["issue_comments"]) == 2
        assert len(result["review_comments"]) == 2

        # No comments should have already_replied flag
        for comment in result["issue_comments"]:
            assert "already_replied" not in comment

        for comment in result["review_comments"]:
            assert "already_replied" not in comment


class TestPostPRReplyRecording:
    """Tests for post_pr_reply recording behavior."""

    def test_records_review_comment_reply(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify review comment replies are recorded in tracker."""
        # Mock PR and review comment
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        original_comment = Mock()
        original_comment.id = 2001
        original_comment.commit_id = "abc123"
        original_comment.path = "src/main.py"
        original_comment.line = 42

        mock_pr.get_review_comment.return_value = original_comment

        # Mock successful reply
        reply_comment = Mock()
        reply_comment.id = 2999
        reply_comment.body = "Thanks for the feedback!"
        reply_comment.user.login = "bot"
        reply_comment.created_at = datetime.now(UTC)
        reply_comment.html_url = "https://github.com/test/pr/2999"

        mock_pr.create_review_comment.return_value = reply_comment

        # Post reply
        result = github_ops_with_tracker.post_pr_reply(body="Thanks for the feedback!", pr_number=123, comment_id=2001)

        assert result["success"] is True
        assert result["comment"]["id"] == 2999

        # Verify reply was recorded
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 2001) is True

    def test_records_issue_comment_reply(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify issue comment replies are recorded in tracker."""
        # Mock PR - simulate review comment failure to trigger fallback
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Mock review comment failure
        mock_pr.get_review_comment.side_effect = Exception("Not a review comment")

        # Mock successful issue comment
        issue_reply = Mock()
        issue_reply.id = 1999
        issue_reply.body = "Thanks!"
        issue_reply.user.login = "bot"
        issue_reply.created_at = datetime.now(UTC)
        issue_reply.html_url = "https://github.com/test/pr/1999"

        mock_pr.create_issue_comment.return_value = issue_reply

        # Post reply
        result = github_ops_with_tracker.post_pr_reply(body="Thanks!", pr_number=123, comment_id=1001)

        assert result["success"] is True
        assert result["comment"]["id"] == 1999

        # Verify reply was recorded (fallback to issue type)
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 1001) is True

    def test_records_standalone_issue_comment(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify standalone issue comments (no comment_id) are not recorded."""
        # Mock PR
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        # Mock successful issue comment
        issue_comment = Mock()
        issue_comment.id = 1999
        issue_comment.body = "New comment"
        issue_comment.user.login = "bot"
        issue_comment.created_at = datetime.now(UTC)
        issue_comment.html_url = "https://github.com/test/pr/1999"

        mock_pr.create_issue_comment.return_value = issue_comment

        # Post comment (no comment_id = standalone comment)
        result = github_ops_with_tracker.post_pr_reply(body="New comment", pr_number=123, comment_id=None)

        assert result["success"] is True
        assert result["comment"]["id"] == 1999

        # Verify no reply was recorded (standalone comments are not tracked)
        replied_comments = comment_tracker.get_replied_comments("test-owner", "test-repo", 123)
        assert len(replied_comments) == 0

    def test_multiple_replies_to_same_comment(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify multiple replies to the same comment update the tracking."""
        # Mock PR and review comment
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr

        original_comment = Mock()
        original_comment.id = 2001
        original_comment.commit_id = "abc123"
        original_comment.path = "src/main.py"
        original_comment.line = 42

        mock_pr.get_review_comment.return_value = original_comment

        # First reply
        reply_1 = Mock()
        reply_1.id = 2998
        reply_1.body = "First reply"
        reply_1.user.login = "bot"
        reply_1.created_at = datetime.now(UTC)
        reply_1.html_url = "https://github.com/test/pr/2998"

        mock_pr.create_review_comment.return_value = reply_1

        result_1 = github_ops_with_tracker.post_pr_reply(body="First reply", pr_number=123, comment_id=2001)

        assert result_1["success"] is True
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 2001) is True

        # Second reply to same comment
        reply_2 = Mock()
        reply_2.id = 2999
        reply_2.body = "Second reply"
        reply_2.user.login = "bot"
        reply_2.created_at = datetime.now(UTC)
        reply_2.html_url = "https://github.com/test/pr/2999"

        mock_pr.create_review_comment.return_value = reply_2

        result_2 = github_ops_with_tracker.post_pr_reply(body="Second reply", pr_number=123, comment_id=2001)

        assert result_2["success"] is True
        # Should still be marked as replied
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 2001) is True

    def test_reply_comment_is_tracked_to_prevent_infinite_loop(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify NEW reply comments are marked as already_replied to prevent infinite loops.

        This is critical to prevent the agent from responding to its own replies.
        When replying to comment 1001, a NEW comment 1999 is created. We must track
        BOTH the original (1001) and the new reply (1999) as already_replied.
        """
        # Mock PR - simulate review comment failure to trigger issue comment fallback
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr
        mock_pr.get_review_comment.side_effect = Exception("Not a review comment")

        # Mock successful issue comment reply
        issue_reply = Mock()
        issue_reply.id = 1999  # This is the NEW comment created by the agent
        issue_reply.body = "Thanks!"
        issue_reply.user.login = "bot"
        issue_reply.created_at = datetime.now(UTC)
        issue_reply.html_url = "https://github.com/test/pr/1999"

        mock_pr.create_issue_comment.return_value = issue_reply

        # Post reply to comment 1001
        result = github_ops_with_tracker.post_pr_reply(body="Thanks!", pr_number=123, comment_id=1001)

        assert result["success"] is True
        assert result["comment"]["id"] == 1999

        # Verify BOTH comments are tracked as replied:
        # 1. Original comment (1001) - we replied to it
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 1001) is True

        # 2. NEW reply comment (1999) - agent's own reply should be marked to prevent infinite loop
        assert comment_tracker.is_replied("test-owner", "test-repo", 123, 1999) is True

    def test_agent_reply_excluded_in_subsequent_fetch(self, github_ops_with_tracker, comment_tracker, mock_pr):
        """Verify agent's own replies are excluded from unreplied comments in subsequent fetches.

        Simulates the full cycle:
        1. Agent posts reply to comment 1001, creating new comment 1999
        2. Next get_pr_comments call includes comment 1999 in the list
        3. Comment 1999 should have already_replied=True flag
        4. filter_unreplied_comments should exclude it
        """
        # Post a reply (same setup as previous test)
        github_ops_with_tracker.repo.get_pull.return_value = mock_pr
        mock_pr.get_review_comment.side_effect = Exception("Not a review comment")

        issue_reply = Mock()
        issue_reply.id = 1999
        issue_reply.body = "Thanks!"
        issue_reply.user.login = "bot"
        issue_reply.created_at = datetime.now(UTC)
        issue_reply.html_url = "https://github.com/test/pr/1999"

        mock_pr.create_issue_comment.return_value = issue_reply

        # Post reply
        github_ops_with_tracker.post_pr_reply(body="Thanks!", pr_number=123, comment_id=1001)

        # Now simulate next iteration: get_pr_comments includes the agent's reply
        agent_reply_comment = Mock()
        agent_reply_comment.id = 1999  # Agent's own reply
        agent_reply_comment.user.login = "bot"
        agent_reply_comment.body = "Thanks!"
        agent_reply_comment.created_at = datetime.now(UTC)
        agent_reply_comment.updated_at = datetime.now(UTC)
        agent_reply_comment.html_url = "https://github.com/test/pr/1999"

        # Update mock to include ONLY agent's reply in next fetch (clear previous mocks)
        mock_pr.get_issue_comments.return_value = [agent_reply_comment]
        mock_pr.get_review_comments.return_value = []  # Clear review comments
        mock_pr.get_reviews.return_value = []  # Clear reviews

        # Reset side effect for get_pr_comments to work
        mock_pr.get_review_comment.side_effect = None

        # Fetch comments again
        result = github_ops_with_tracker.get_pr_comments(pr_number=123)

        assert result["success"] is True
        assert len(result["issue_comments"]) == 1

        # The agent's own reply should have already_replied flag
        agent_comment = result["issue_comments"][0]
        assert agent_comment["id"] == 1999
        assert agent_comment.get("already_replied") is True

        # Verify filter would exclude it
        from multi_agent_workflow.handlers.comment_utils import filter_unreplied_comments

        unreplied = filter_unreplied_comments(result)
        assert len(unreplied) == 0, "Agent's own reply should be filtered out"


class TestPostPRReplyWithoutTracker:
    """Tests for post_pr_reply without CommentTracker."""

    def test_works_without_tracker(self, github_ops_without_tracker, mock_pr):
        """Verify post_pr_reply works correctly when no tracker is provided."""
        # Mock PR and review comment
        github_ops_without_tracker.repo.get_pull.return_value = mock_pr

        original_comment = Mock()
        original_comment.id = 2001
        original_comment.commit_id = "abc123"
        original_comment.path = "src/main.py"
        original_comment.line = 42

        mock_pr.get_review_comment.return_value = original_comment

        # Mock successful reply
        reply_comment = Mock()
        reply_comment.id = 2999
        reply_comment.body = "Thanks!"
        reply_comment.user.login = "bot"
        reply_comment.created_at = datetime.now(UTC)
        reply_comment.html_url = "https://github.com/test/pr/2999"

        mock_pr.create_review_comment.return_value = reply_comment

        # Post reply - should work without errors
        result = github_ops_without_tracker.post_pr_reply(body="Thanks!", pr_number=123, comment_id=2001)

        assert result["success"] is True
        assert result["comment"]["id"] == 2999
