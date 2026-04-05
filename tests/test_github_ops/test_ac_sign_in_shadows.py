"""Test to reproduce ac-sign issue in shadow repositories.

This test reproduces the exact scenario where:
1. Workflow creates a shadow repository (inherits global git config with ac-sign)
2. Code tries to commit in that shadow
3. ac-sign gets triggered and fails

This isolates the issue so we can fix it properly.
"""

import subprocess
from pathlib import Path

import git

from agent_design.github_ops.operations import GitHubOperations


class TestAcSignInShadows:
    """Test ac-sign behavior in shadow repositories."""

    def test_commit_in_cloned_shadow_from_local(self, tmp_path: Path, github_ops: GitHubOperations) -> None:
        """Test that we can commit in a shadow cloned from local repo.

        This reproduces the workflow scenario where:
        1. Base shadow is cloned from remote (or local)
        2. Working shadow is cloned from base shadow
        3. We try to commit in the working shadow
        """
        ops = github_ops

        # Create a source repo (simulating GitHub - signing disabled for test setup only)
        source_repo = tmp_path / "source"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=source_repo, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=source_repo, check=True, capture_output=True)

        # Create initial file and commit
        test_file = source_repo / "test.txt"
        test_file.write_text("initial content\n")
        subprocess.run(["git", "add", "test.txt"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=source_repo, check=True, capture_output=True)

        repo = git.Repo(source_repo)
        initial_sha = repo.head.commit.hexsha

        # Clone to create a shadow (this is what GitHubOperations.git_clone does)
        # The shadow will inherit global git config (with ac-sign) but our fix should disable it
        shadow = tmp_path / "shadow"
        ops.git_clone(source_path=source_repo, dest_path=shadow, base_ref=initial_sha)

        # Now try to commit in the shadow - this is the real test
        # If our fix works, the shadow should have signing disabled despite global config
        shadow_file = shadow / "new_file.txt"
        shadow_file.write_text("new content\n")

        # This is the operation that was failing in production workflow
        ops.git_commit_changes(repo_path=shadow, commit_message="Test commit in shadow")

        # If we get here, the commit succeeded
        shadow_repo = git.Repo(shadow)
        assert shadow_repo.head.commit.message.strip() == "Test commit in shadow"

    def test_commit_in_cloned_shadow_from_url(self, tmp_path: Path, github_ops: GitHubOperations) -> None:
        """Test that we can commit in a shadow cloned from URL.

        This reproduces the workflow scenario where:
        1. Base shadow is cloned from remote URL
        2. We try to commit in that base shadow
        """
        ops = github_ops

        # Create a "remote" repo (simulating GitHub - signing disabled for test setup only)
        remote_repo = tmp_path / "remote"
        remote_repo.mkdir()
        subprocess.run(["git", "init"], cwd=remote_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=remote_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=remote_repo, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=remote_repo, check=True, capture_output=True)

        # Create initial file and commit
        test_file = remote_repo / "test.txt"
        test_file.write_text("initial content\n")
        subprocess.run(["git", "add", "test.txt"], cwd=remote_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=remote_repo, check=True, capture_output=True)

        # Clone from "URL" (file path) to create base shadow
        # The shadow will inherit global git config (with ac-sign) but our fix should disable it
        base_shadow = tmp_path / "base_shadow"
        ops.git_clone_from_url(url=str(remote_repo), dest_path=base_shadow)

        # Now try to commit in the base shadow - this is the real test
        shadow_file = base_shadow / "new_file.txt"
        shadow_file.write_text("new content\n")

        # This is the operation that was failing in production workflow
        ops.git_commit_changes(repo_path=base_shadow, commit_message="Test commit in base shadow")

        # If we get here, the commit succeeded
        shadow_repo = git.Repo(base_shadow)
        assert shadow_repo.head.commit.message.strip() == "Test commit in base shadow"

    def test_subprocess_commit_in_shadow(self, tmp_path: Path, github_ops: GitHubOperations) -> None:
        """Test raw subprocess commit in shadow (like pre-commit hook would do).

        This tests if even direct subprocess git commands work in shadows.
        """
        ops = github_ops

        # Create a source repo (simulating GitHub - signing disabled for test setup only)
        source_repo = tmp_path / "source"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"], cwd=source_repo, check=True, capture_output=True
        )
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=source_repo, check=True, capture_output=True)

        # Create initial file and commit
        test_file = source_repo / "test.txt"
        test_file.write_text("initial content\n")
        subprocess.run(["git", "add", "test.txt"], cwd=source_repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=source_repo, check=True, capture_output=True)

        repo = git.Repo(source_repo)
        initial_sha = repo.head.commit.hexsha

        # Clone to create a shadow
        shadow = tmp_path / "shadow"
        ops.git_clone(source_path=source_repo, dest_path=shadow, base_ref=initial_sha)

        # Try to commit using raw subprocess (like what happens in pre-commit hooks)
        shadow_file = shadow / "new_file.txt"
        shadow_file.write_text("new content\n")

        subprocess.run(["git", "add", "new_file.txt"], cwd=shadow, check=True, capture_output=True)
        # This should work now that our fix disabled signing in the shadow
        subprocess.run(
            ["git", "commit", "-m", "Test subprocess commit"],
            cwd=shadow,
            check=True,
            capture_output=True,
        )

        # If we get here, the commit succeeded
        shadow_repo = git.Repo(shadow)
        assert shadow_repo.head.commit.message.strip() == "Test subprocess commit"
