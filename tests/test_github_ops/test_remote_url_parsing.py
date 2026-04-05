"""Tests for GitHub remote URL parsing and auto-initialization.

This module tests the new functionality added to auto-parse GitHub owner/repo
from git remote URLs, eliminating the need for explicit --github-owner/--github-repo flags.
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from agent_design.github_ops.operations import GitHubOperations, RepositoryConfig, parse_github_remote_url


class TestParseGitHubRemoteURL:
    """Tests for parse_github_remote_url() utility function."""

    def test_parse_github_ssh_url(self):
        """Test parsing SSH URL for github.com."""
        url = "git@github.com:owner/repo.git"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://api.github.com"

    def test_parse_github_ssh_url_without_git_suffix(self):
        """Test parsing SSH URL without .git suffix."""
        url = "git@github.com:owner/repo"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://api.github.com"

    def test_parse_github_https_url(self):
        """Test parsing HTTPS URL for github.com."""
        url = "https://github.com/owner/repo.git"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://api.github.com"

    def test_parse_github_https_url_without_git_suffix(self):
        """Test parsing HTTPS URL without .git suffix."""
        url = "https://github.com/owner/repo"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://api.github.com"

    def test_parse_enterprise_ssh_url(self):
        """Test parsing SSH URL for GitHub Enterprise."""
        url = "git@github.pie.apple.com:owner/repo.git"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://github.pie.apple.com/api/v3"

    def test_parse_enterprise_https_url(self):
        """Test parsing HTTPS URL for GitHub Enterprise."""
        url = "https://github.pie.apple.com/owner/repo.git"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "owner"
        assert repo == "repo"
        assert base_url == "https://github.pie.apple.com/api/v3"

    def test_parse_invalid_url(self):
        """Test parsing invalid URL returns None."""
        url = "not-a-valid-git-url"
        result = parse_github_remote_url(url)

        assert result is None

    def test_parse_empty_url(self):
        """Test parsing empty URL returns None."""
        url = ""
        result = parse_github_remote_url(url)

        assert result is None

    def test_parse_url_with_special_characters_in_repo(self):
        """Test parsing URL with hyphens and underscores in repo name."""
        url = "git@github.com:my-org/my_repo-v2.git"
        result = parse_github_remote_url(url)

        assert result is not None
        owner, repo, base_url = result
        assert owner == "my-org"
        assert repo == "my_repo-v2"


class TestRepositoryConfig:
    """Tests for RepositoryConfig with remote_url parameter."""

    def test_repository_config_with_explicit_owner_repo(self):
        """Test RepositoryConfig with explicit owner and repo."""
        config = RepositoryConfig(
            workspace="/path/to/repo",
            github_owner="explicit-owner",
            github_repo="explicit-repo",
            remote_url="",
        )

        assert config.workspace == "/path/to/repo"
        assert config.github_owner == "explicit-owner"
        assert config.github_repo == "explicit-repo"
        assert config.remote_url == ""

    def test_repository_config_with_remote_url_only(self):
        """Test RepositoryConfig with only remote_url (will be parsed later by GitHubOperations)."""
        config = RepositoryConfig(
            workspace="/path/to/repo",
            github_owner="",
            github_repo="",
            remote_url="git@github.com:owner/repo.git",
        )

        assert config.workspace == "/path/to/repo"
        assert config.github_owner == ""
        assert config.github_repo == ""
        assert config.remote_url == "git@github.com:owner/repo.git"

    def test_repository_config_shadow_mode(self):
        """Test RepositoryConfig for shadow-only mode (no workspace)."""
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:owner/repo.git",
        )

        assert config.workspace is None
        assert config.remote_url == "git@github.com:owner/repo.git"


class TestGitHubOperationsAutoInitialization:
    """Tests for GitHubOperations auto-parsing owner/repo from remote_url."""

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_auto_parse_owner_repo_from_remote_url(self, mock_github_class):
        """Test GitHubOperations auto-parses owner/repo from remote_url when not explicitly provided."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with only remote_url (no explicit owner/repo)
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:auto-owner/auto-repo.git",
        )

        # Create GitHubOperations (should auto-parse)
        github_ops = GitHubOperations(config)

        # Verify GitHub API was initialized with parsed owner/repo
        mock_github_instance.get_repo.assert_called_once_with("auto-owner/auto-repo")
        assert github_ops.repo is not None
        assert github_ops.repo == mock_repo

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_explicit_owner_repo_takes_precedence(self, mock_github_class):
        """Test explicit owner/repo takes precedence over parsed values from remote_url."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with BOTH explicit values AND remote_url
        config = RepositoryConfig(
            workspace=None,
            github_owner="explicit-owner",
            github_repo="explicit-repo",
            remote_url="git@github.com:url-owner/url-repo.git",
        )

        # Create GitHubOperations
        github_ops = GitHubOperations(config)

        # Verify explicit values were used (not parsed values)
        mock_github_instance.get_repo.assert_called_once_with("explicit-owner/explicit-repo")
        assert github_ops.repo is not None

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_partial_explicit_triggers_auto_parse(self, mock_github_class):
        """Test that missing either owner OR repo triggers auto-parsing."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with only owner (missing repo)
        config = RepositoryConfig(
            workspace=None,
            github_owner="partial-owner",
            github_repo="",  # Missing
            remote_url="git@github.com:url-owner/url-repo.git",
        )

        # Create GitHubOperations (should auto-parse)
        github_ops = GitHubOperations(config)

        # Verify parsed values were used
        mock_github_instance.get_repo.assert_called_once_with("url-owner/url-repo")
        assert github_ops.repo is not None

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_enterprise_url_uses_parsed_base_url(self, mock_github_class):
        """Test enterprise GitHub URL uses parsed base_url."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with enterprise URL
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.pie.apple.com:owner/repo.git",
        )

        # Create GitHubOperations
        GitHubOperations(config)

        # Verify Github() was called with enterprise base_url
        mock_github_class.assert_called_once()
        call_kwargs = mock_github_class.call_args[1]
        assert call_kwargs["base_url"] == "https://github.pie.apple.com/api/v3"

    def test_no_github_api_without_owner_repo(self):
        """Test GitHub API is NOT initialized when owner/repo cannot be determined."""
        # Create config with no explicit values and no remote_url
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="",
        )

        # Create GitHubOperations
        github_ops = GitHubOperations(config)

        # Verify GitHub API was NOT initialized
        assert github_ops.repo is None

    def test_no_github_api_with_invalid_remote_url(self):
        """Test GitHub API is NOT initialized when remote_url is invalid."""
        # Create config with invalid remote_url
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="not-a-valid-url",
        )

        # Create GitHubOperations
        github_ops = GitHubOperations(config)

        # Verify GitHub API was NOT initialized
        assert github_ops.repo is None

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_github_token_raises_error(self, tmp_path):
        """Test missing GITHUB_TOKEN (and no roxy token file) raises ValueError."""
        # Redirect Path.home() so no roxy token is found
        with patch("agent_design.github_ops.operations.Path.home", return_value=tmp_path):
            config = RepositoryConfig(
                workspace=None,
                github_owner="",
                github_repo="",
                remote_url="git@github.com:owner/repo.git",
            )
            with pytest.raises(ValueError, match="GitHub token required"):
                GitHubOperations(config)

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_auto_parse_logs_parsed_values(self, mock_github_class, caplog):
        """Test that auto-parsed owner/repo are logged."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with remote_url
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:logged-owner/logged-repo.git",
        )

        # Create GitHubOperations with logging
        with caplog.at_level(logging.INFO):
            github_ops = GitHubOperations(config)

        # Verify logging occurred
        assert "Parsed GitHub remote: logged-owner/logged-repo" in caplog.text
        assert github_ops.repo is not None

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_instance_variables_set_from_auto_parse(self, mock_github_class):
        """Test that instance variables github_owner and github_repo are set from auto-parsed values."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with only remote_url (no explicit owner/repo)
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:parsed-owner/parsed-repo.git",
        )

        # Create GitHubOperations (should auto-parse and store as instance variables)
        github_ops = GitHubOperations(config)

        # Verify instance variables are set to parsed values
        assert github_ops.github_owner == "parsed-owner"
        assert github_ops.github_repo == "parsed-repo"

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_instance_variables_set_from_explicit_values(self, mock_github_class):
        """Test that instance variables are set from explicit owner/repo values."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with explicit owner/repo
        config = RepositoryConfig(
            workspace=None,
            github_owner="explicit-owner",
            github_repo="explicit-repo",
            remote_url="",
        )

        # Create GitHubOperations
        github_ops = GitHubOperations(config)

        # Verify instance variables are set to explicit values
        assert github_ops.github_owner == "explicit-owner"
        assert github_ops.github_repo == "explicit-repo"

    def test_instance_variables_empty_when_api_not_initialized(self):
        """Test that instance variables are empty strings when GitHub API is not initialized."""
        # Create config with no values (API won't initialize)
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="",
        )

        # Create GitHubOperations (no API initialization)
        github_ops = GitHubOperations(config)

        # Verify instance variables are empty strings
        assert github_ops.github_owner == ""
        assert github_ops.github_repo == ""
        assert github_ops.repo is None

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_find_pr_uses_instance_variables(self, mock_github_class):
        """Test that _find_pr_for_branch_internal uses instance variables not repo_config."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_pr.number = 42
        mock_pr.html_url = "https://github.com/test-owner/test-repo/pull/42"

        # Mock get_pulls to return our PR
        mock_repo.get_pulls.return_value = [mock_pr]
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create config with auto-parsed values
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:test-owner/test-repo.git",
        )

        # Create GitHubOperations
        github_ops = GitHubOperations(config)

        # Call _find_pr_for_branch_internal
        result = github_ops._find_pr_for_branch_internal("test-branch")

        # Verify get_pulls was called with correct head format using instance variables
        mock_repo.get_pulls.assert_called_once_with(state="open", head="test-owner:test-branch")
        assert result == mock_pr

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_get_pr_comments_uses_instance_variables_for_tracking(self, mock_github_class):
        """Test that get_pr_comments uses instance variables for comment tracker."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()

        # Mock empty comment lists
        mock_pr.get_issue_comments.return_value = []
        mock_pr.get_review_comments.return_value = []
        mock_pr.get_reviews.return_value = []

        mock_repo.get_pull.return_value = mock_pr
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create mock comment tracker
        mock_tracker = MagicMock()
        mock_tracker.get_replied_comments.return_value = set()

        # Create config with auto-parsed values
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:tracker-owner/tracker-repo.git",
        )

        # Create GitHubOperations with comment tracker
        github_ops = GitHubOperations(config, comment_tracker=mock_tracker)

        # Call get_pr_comments
        result = github_ops.get_pr_comments(pr_number=123)

        # Verify comment tracker was called with instance variables (not repo_config)
        mock_tracker.get_replied_comments.assert_called_once_with("tracker-owner", "tracker-repo", 123)
        assert result["success"] is True

    @patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}, clear=False)
    @patch("agent_design.github_ops.operations.Github")
    def test_post_pr_reply_uses_instance_variables_for_tracking(self, mock_github_class):
        """Test that post_pr_reply uses instance variables for comment tracker."""
        # Setup mock GitHub API
        mock_github_instance = MagicMock()
        mock_repo = MagicMock()
        mock_pr = MagicMock()
        mock_issue_comment = MagicMock()
        mock_issue_comment.id = 999
        mock_issue_comment.body = "test reply"
        mock_issue_comment.user.login = "bot"
        mock_issue_comment.created_at.isoformat.return_value = "2025-01-15T10:00:00Z"
        mock_issue_comment.html_url = "https://github.com/test/repo/issues/123#issuecomment-999"

        mock_pr.create_issue_comment.return_value = mock_issue_comment
        mock_repo.get_pull.return_value = mock_pr
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github_class.return_value = mock_github_instance

        # Create mock comment tracker
        mock_tracker = MagicMock()

        # Create config with auto-parsed values
        config = RepositoryConfig(
            workspace=None,
            github_owner="",
            github_repo="",
            remote_url="git@github.com:reply-owner/reply-repo.git",
        )

        # Create GitHubOperations with comment tracker
        github_ops = GitHubOperations(config, comment_tracker=mock_tracker)

        # Call post_pr_reply (issue comment, no specific comment_id)
        result = github_ops.post_pr_reply(body="test reply", pr_number=123)

        # Verify comment was posted
        assert result["success"] is True

        # Note: record_reply is only called when replying to a specific comment_id
        # For issue comments without comment_id, it's not tracked
        mock_tracker.record_reply.assert_not_called()
