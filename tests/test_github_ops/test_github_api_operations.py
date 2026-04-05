"""Tests for GitHub API methods that use git operations.

Note: This file only tests methods that can be tested with real git repositories.
Methods that require actual GitHub API calls are not tested here.
"""

import git
import pytest


class TestGitCreateAndPushBranch:
    """Tests for git_create_and_push_branch method."""

    @pytest.fixture
    def remote_repo(self, tmp_path):
        """Create a bare git repository to act as remote."""
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        git.Repo.init(remote_path, bare=True)
        return remote_path

    @pytest.fixture
    def temp_git_repo_with_remote(self, temp_git_repo, remote_repo):
        """Add a remote to the temp git repo."""
        repo = git.Repo(temp_git_repo)
        repo.create_remote("origin", str(remote_repo))
        return temp_git_repo

    def test_create_new_branch_success(self, github_ops, temp_git_repo_with_remote):
        """Test successfully creating a new branch."""
        repo = git.Repo(temp_git_repo_with_remote)

        result = github_ops.git_create_and_push_branch(temp_git_repo_with_remote, "feature/new-branch")

        assert result["success"] is True
        assert result["branch_name"] == "feature/new-branch"
        assert result["existing"] is False
        assert "Created and pushed" in result["message"]

        # Verify branch was created and checked out
        assert repo.active_branch.name == "feature/new-branch"
        assert "feature/new-branch" in [h.name for h in repo.heads]

    def test_reset_existing_branch_success(self, github_ops, temp_git_repo_with_remote):
        """Test resetting an existing branch to current HEAD."""
        repo = git.Repo(temp_git_repo_with_remote)

        # Create initial branch pointing to current HEAD
        initial_commit = repo.head.commit
        test_branch = repo.create_head("feature/existing-branch", commit=initial_commit.hexsha)

        # Add another commit to move HEAD forward
        test_file = temp_git_repo_with_remote / "new_file.txt"
        test_file.write_text("New content")
        repo.index.add(["new_file.txt"])
        new_commit = repo.index.commit("Second commit")

        # Verify branch still points to old commit
        assert test_branch.commit.hexsha == initial_commit.hexsha
        assert repo.head.commit.hexsha == new_commit.hexsha

        # Now call git_create_and_push_branch with existing branch
        result = github_ops.git_create_and_push_branch(temp_git_repo_with_remote, "feature/existing-branch")

        assert result["success"] is True
        assert result["branch_name"] == "feature/existing-branch"
        assert result["existing"] is True
        assert "Updated and force-pushed" in result["message"]

        # Verify branch was reset to current HEAD
        assert repo.active_branch.name == "feature/existing-branch"
        assert test_branch.commit.hexsha == new_commit.hexsha

    def test_create_branch_invalid_repo(self, github_ops, tmp_path):
        """Test error handling with invalid repository."""
        invalid_path = tmp_path / "nonexistent"

        result = github_ops.git_create_and_push_branch(invalid_path, "feature/test")

        assert result["success"] is False
        assert "error" in result
        assert "feature/test" in result["error"]

    def test_create_branch_with_special_characters(self, github_ops, temp_git_repo_with_remote):
        """Test creating branch with special characters in name."""
        repo = git.Repo(temp_git_repo_with_remote)

        # Branch names can have slashes and dashes
        result = github_ops.git_create_and_push_branch(temp_git_repo_with_remote, "feature/US-04/add-auth")

        assert result["success"] is True
        assert result["branch_name"] == "feature/US-04/add-auth"
        assert result["existing"] is False

        # Verify branch was created
        assert repo.active_branch.name == "feature/US-04/add-auth"


class TestGetCurrentCommit:
    """Tests for get_current_commit method."""

    def test_get_current_commit_success(self, github_ops, temp_git_repo):
        """Test successfully getting current commit."""
        repo = git.Repo(temp_git_repo)
        commit = repo.head.commit

        result = github_ops.get_current_commit()

        assert result["success"] is True
        assert result["commit"]["sha"] == commit.hexsha
        assert result["commit"]["short_sha"] == commit.hexsha[:7]
        assert result["commit"]["message"] == "Initial commit"
        assert "author" in result["commit"]
        assert "date" in result["commit"]

    def test_get_current_commit_error(self, github_ops):
        """Test error handling when getting current commit."""
        # Make git_repo invalid
        github_ops.git_repo = None

        result = github_ops.get_current_commit()

        assert result["success"] is False
        assert "error" in result


class TestGetCurrentBranch:
    """Tests for get_current_branch method."""

    def test_get_current_branch_success(self, github_ops):
        """Test successfully getting current branch."""
        result = github_ops.get_current_branch()

        assert result["success"] is True
        assert "branch" in result
        # Default branch name varies, just check it's a string
        assert isinstance(result["branch"], str)

    def test_get_current_branch_error(self, github_ops):
        """Test error handling when getting current branch."""
        github_ops.git_repo = None

        result = github_ops.get_current_branch()

        assert result["success"] is False
        assert "error" in result
