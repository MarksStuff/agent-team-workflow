"""Pytest fixtures for GitHub operations tests."""

from unittest.mock import patch

import git
import pytest

from agent_design.github_ops.operations import GitHubOperations, RepositoryConfig


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = git.Repo.init(repo_path)

    # Configure git user for commits
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return repo_path


@pytest.fixture
def repo_config(temp_git_repo):
    """Create a test repository configuration."""
    return RepositoryConfig(
        workspace=str(temp_git_repo),
        github_owner="test-owner",
        github_repo="test-repo",
    )


@pytest.fixture
def github_ops(repo_config, monkeypatch):
    """Create GitHubOperations instance for testing git operations.

    Note: This patches only the Github client to avoid network calls.
    The git operations use real GitPython against real temporary repositories.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_BASE_URL", "https://api.github.com")

    with patch("agent_design.github_ops.operations.Github"):
        ops = GitHubOperations(repo_config)
        return ops
