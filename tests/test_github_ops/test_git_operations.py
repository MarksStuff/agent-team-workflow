"""Tests for git operations using real GitPython with temporary repositories."""

import git
import pytest


class TestGitCommitChanges:
    """Tests for git_commit_changes method."""

    def test_commit_changes_success(self, github_ops, temp_git_repo):
        """Test successful commit of changes."""
        # Create a new file
        new_file = temp_git_repo / "new_file.txt"
        new_file.write_text("New content")

        # Commit the changes
        result = github_ops.git_commit_changes(temp_git_repo, "Add new file")

        # Verify commit was created
        assert len(result) == 40  # SHA is 40 characters
        repo = git.Repo(temp_git_repo)
        assert repo.head.commit.message.strip() == "Add new file"
        assert "new_file.txt" in repo.head.commit.stats.files

    def test_commit_changes_multiple_files(self, github_ops, temp_git_repo):
        """Test committing multiple files."""
        # Create multiple files
        (temp_git_repo / "file1.txt").write_text("File 1")
        (temp_git_repo / "file2.txt").write_text("File 2")

        github_ops.git_commit_changes(temp_git_repo, "Add two files")

        repo = git.Repo(temp_git_repo)
        assert len(repo.head.commit.stats.files) == 2


class TestGitIsClean:
    """Tests for git_is_clean method."""

    def test_is_clean_when_clean(self, github_ops, temp_git_repo):
        """Test repository is clean."""
        result = github_ops.git_is_clean(temp_git_repo)
        assert result is True

    def test_is_clean_when_dirty_modified(self, github_ops, temp_git_repo):
        """Test repository is dirty with modified file."""
        # Modify existing file
        readme = temp_git_repo / "README.md"
        readme.write_text("Modified content")

        result = github_ops.git_is_clean(temp_git_repo)
        assert result is False

    def test_is_clean_when_dirty_untracked(self, github_ops, temp_git_repo):
        """Test repository is dirty with untracked file."""
        # Create new untracked file
        new_file = temp_git_repo / "untracked.txt"
        new_file.write_text("Untracked content")

        result = github_ops.git_is_clean(temp_git_repo)
        assert result is False

    def test_is_clean_invalid_repo(self, github_ops, tmp_path):
        """Test error when repository is invalid."""
        invalid_path = tmp_path / "not_a_repo"
        invalid_path.mkdir()

        with pytest.raises(ValueError, match="Not a Git repository"):
            github_ops.git_is_clean(invalid_path)


class TestGitVerifyCommitExists:
    """Tests for git_verify_commit_exists method."""

    def test_commit_exists(self, github_ops, temp_git_repo):
        """Test when commit exists."""
        repo = git.Repo(temp_git_repo)
        commit_sha = repo.head.commit.hexsha

        result = github_ops.git_verify_commit_exists(temp_git_repo, commit_sha)
        assert result is True

    def test_commit_does_not_exist(self, github_ops, temp_git_repo):
        """Test when commit does not exist."""
        # Use a valid-looking SHA that doesn't exist in the repo
        fake_sha = "ffffffffffffffffffffffffffffffffffffffff"

        result = github_ops.git_verify_commit_exists(temp_git_repo, fake_sha)
        assert result is False


class TestGitCheckCommitIsHead:
    """Tests for git_check_commit_is_head method."""

    def test_commit_is_head(self, github_ops, temp_git_repo):
        """Test when commit is at HEAD."""
        repo = git.Repo(temp_git_repo)
        head_sha = repo.head.commit.hexsha

        result = github_ops.git_check_commit_is_head(temp_git_repo, head_sha)
        assert result is True

    def test_commit_is_not_head(self, github_ops, temp_git_repo):
        """Test when commit is not at HEAD."""
        repo = git.Repo(temp_git_repo)
        old_sha = repo.head.commit.hexsha

        # Create a new commit
        new_file = temp_git_repo / "another.txt"
        new_file.write_text("Content")
        repo.index.add(["another.txt"])
        repo.index.commit("Another commit")

        result = github_ops.git_check_commit_is_head(temp_git_repo, old_sha)
        assert result is False


class TestGitGetCommitFileList:
    """Tests for git_get_commit_file_list method."""

    def test_get_commit_file_list_with_parent(self, github_ops, temp_git_repo):
        """Test getting file list from commit with parent."""
        # Create a new commit with files
        new_file = temp_git_repo / "new_file.py"
        new_file.write_text("print('hello')")
        existing_file = temp_git_repo / "README.md"
        existing_file.write_text("Updated README")

        repo = git.Repo(temp_git_repo)
        repo.index.add(["new_file.py", "README.md"])
        commit = repo.index.commit("Add new file and modify existing")

        files_created, files_modified = github_ops.git_get_commit_file_list(temp_git_repo, commit.hexsha)

        assert "new_file.py" in files_created
        assert "README.md" in files_modified

    def test_get_commit_file_list_first_commit(self, github_ops, tmp_path):
        """Test getting file list from first commit (no parent)."""
        # Create a new repo with just one commit
        repo_path = tmp_path / "new_repo"
        repo_path.mkdir()
        repo = git.Repo.init(repo_path)
        repo.config_writer().set_value("user", "name", "Test User").release()
        repo.config_writer().set_value("user", "email", "test@example.com").release()

        # Create first commit
        initial_file = repo_path / "initial.txt"
        initial_file.write_text("Initial content")
        repo.index.add(["initial.txt"])
        commit = repo.index.commit("First commit")

        files_created, files_modified = github_ops.git_get_commit_file_list(repo_path, commit.hexsha)

        assert "initial.txt" in files_created
        assert files_modified == []


class TestGitDiscardChanges:
    """Tests for git_discard_changes method."""

    def test_discard_changes_modified_file(self, github_ops, temp_git_repo):
        """Test discarding changes to modified file."""
        readme = temp_git_repo / "README.md"
        original_content = readme.read_text()
        readme.write_text("Modified content")

        github_ops.git_discard_changes(temp_git_repo)

        # File should be restored
        assert readme.read_text() == original_content

    def test_discard_changes_untracked_file(self, github_ops, temp_git_repo):
        """Test discarding untracked files."""
        untracked = temp_git_repo / "untracked.txt"
        untracked.write_text("Untracked content")
        assert untracked.exists()

        github_ops.git_discard_changes(temp_git_repo)

        # Untracked file should be removed
        assert not untracked.exists()

    def test_discard_changes_clean_repo(self, github_ops, temp_git_repo):
        """Test discarding changes on clean repository."""
        # Should not raise error
        github_ops.git_discard_changes(temp_git_repo)

        # Repo should still be clean
        assert github_ops.git_is_clean(temp_git_repo)


class TestGitStageFiles:
    """Tests for git_stage_files method."""

    def test_stage_files_relative_paths(self, github_ops, temp_git_repo):
        """Test staging files with relative paths."""
        file1 = temp_git_repo / "file1.py"
        file2 = temp_git_repo / "file2.py"
        file1.write_text("print('file1')")
        file2.write_text("print('file2')")

        github_ops.git_stage_files(temp_git_repo, ["file1.py", "file2.py"])

        repo = git.Repo(temp_git_repo)
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        assert "file1.py" in staged_files
        assert "file2.py" in staged_files

    def test_stage_files_absolute_paths(self, github_ops, temp_git_repo):
        """Test staging files with absolute paths."""
        file1 = temp_git_repo / "file1.py"
        file1.write_text("print('file1')")

        github_ops.git_stage_files(temp_git_repo, [file1])

        repo = git.Repo(temp_git_repo)
        staged_files = [item.a_path for item in repo.index.diff("HEAD")]
        assert "file1.py" in staged_files


class TestGitCommitStaged:
    """Tests for git_commit_staged method."""

    def test_commit_staged_changes(self, github_ops, temp_git_repo):
        """Test committing already-staged changes."""
        # Create and stage a file
        new_file = temp_git_repo / "staged.txt"
        new_file.write_text("Staged content")
        repo = git.Repo(temp_git_repo)
        repo.index.add(["staged.txt"])

        # Commit only staged changes
        result = github_ops.git_commit_staged(temp_git_repo, "Commit staged file")

        assert len(result) == 40  # SHA is 40 characters
        assert repo.head.commit.message.strip() == "Commit staged file"


class TestGitGetHeadSha:
    """Tests for git_get_head_sha method."""

    def test_get_head_sha(self, github_ops, temp_git_repo):
        """Test getting HEAD SHA."""
        repo = git.Repo(temp_git_repo)
        expected_sha = repo.head.commit.hexsha

        result = github_ops.git_get_head_sha(temp_git_repo)

        assert result == expected_sha
        assert len(result) == 40


class TestGitGetWorkingTreeFileLists:
    """Tests for git_get_working_tree_file_lists method."""

    def test_get_file_lists_with_changes(self, github_ops, temp_git_repo):
        """Test getting file lists with both created and modified files."""
        # Create new file (untracked)
        new_file = temp_git_repo / "new.txt"
        new_file.write_text("New content")

        # Modify existing file
        readme = temp_git_repo / "README.md"
        readme.write_text("Modified")
        repo = git.Repo(temp_git_repo)
        repo.index.add(["README.md"])

        files_created, files_modified = github_ops.git_get_working_tree_file_lists(temp_git_repo)

        assert "new.txt" in files_created
        assert "README.md" in files_modified

    def test_get_file_lists_clean_repo(self, github_ops, temp_git_repo):
        """Test getting file lists from clean repository."""
        files_created, files_modified = github_ops.git_get_working_tree_file_lists(temp_git_repo)

        assert files_created == []
        assert files_modified == []


class TestGitExtractCommitInfo:
    """Tests for git_extract_commit_info method."""

    def test_extract_full_info(self, github_ops):
        """Test extracting complete commit information."""
        agent_output = """
        Task completed successfully.
        Commit SHA: abc123def456789012345678901234567890abcd
        Files Created: ['new_file.py', 'another_file.py']
        Files Modified: ['existing_file.py']
        """

        commit_sha, files_created, files_modified = github_ops.git_extract_commit_info(agent_output)

        assert commit_sha == "abc123def456789012345678901234567890abcd"
        assert files_created == ["new_file.py", "another_file.py"]
        assert files_modified == ["existing_file.py"]

    def test_extract_no_commit_sha(self, github_ops):
        """Test when no commit SHA is present."""
        agent_output = "Task completed without commit."

        commit_sha, files_created, files_modified = github_ops.git_extract_commit_info(agent_output)

        assert commit_sha is None
        assert files_created == []
        assert files_modified == []

    def test_extract_empty_file_lists(self, github_ops):
        """Test with empty file lists."""
        agent_output = """
        Commit SHA: abc123def456789012345678901234567890abcd
        Files Created: []
        Files Modified: []
        """

        commit_sha, files_created, files_modified = github_ops.git_extract_commit_info(agent_output)

        assert commit_sha == "abc123def456789012345678901234567890abcd"
        assert files_created == []
        assert files_modified == []


class TestGitDiffRange:
    """Tests for git_diff_range method."""

    def test_diff_range_single_commit(self, github_ops, temp_git_repo):
        """Test diff range with a single commit difference."""
        repo = git.Repo(temp_git_repo)
        base_sha = repo.head.commit.hexsha

        # Create a new commit
        new_file = temp_git_repo / "feature.py"
        new_file.write_text("def feature(): pass")
        repo.index.add(["feature.py"])
        repo.index.commit("Add feature")

        # Get diff from base to HEAD
        diff_output = github_ops.git_diff_range(temp_git_repo, base_sha, "HEAD")

        # Verify diff contains the new file
        assert "feature.py" in diff_output
        assert "def feature(): pass" in diff_output
        assert "+++ b/feature.py" in diff_output

    def test_diff_range_multiple_commits(self, github_ops, temp_git_repo):
        """Test diff range with multiple commits."""
        repo = git.Repo(temp_git_repo)
        base_sha = repo.head.commit.hexsha

        # Create first commit
        file1 = temp_git_repo / "file1.py"
        file1.write_text("print('file1')")
        repo.index.add(["file1.py"])
        repo.index.commit("Add file1")

        # Create second commit
        file2 = temp_git_repo / "file2.py"
        file2.write_text("print('file2')")
        repo.index.add(["file2.py"])
        repo.index.commit("Add file2")

        # Get cumulative diff from base to HEAD
        diff_output = github_ops.git_diff_range(temp_git_repo, base_sha, "HEAD")

        # Verify diff contains both files
        assert "file1.py" in diff_output
        assert "file2.py" in diff_output
        assert "print('file1')" in diff_output
        assert "print('file2')" in diff_output

    def test_diff_range_with_modifications(self, github_ops, temp_git_repo):
        """Test diff range showing file modifications."""
        repo = git.Repo(temp_git_repo)
        base_sha = repo.head.commit.hexsha

        # Modify existing file
        readme = temp_git_repo / "README.md"
        readme.write_text("# Modified Test Repository\nWith new content")
        repo.index.add(["README.md"])
        repo.index.commit("Update README")

        diff_output = github_ops.git_diff_range(temp_git_repo, base_sha, "HEAD")

        # Verify diff shows modification
        assert "README.md" in diff_output
        assert "+# Modified Test Repository" in diff_output
        assert "+With new content" in diff_output

    def test_diff_range_triple_dot_syntax(self, github_ops, temp_git_repo):
        """Test that triple-dot syntax is used (merge-base comparison)."""
        repo = git.Repo(temp_git_repo)

        # Create a branch from current HEAD
        repo.create_head("feature-branch")
        repo.heads["feature-branch"].checkout()

        # Add commit on feature branch
        feature_file = temp_git_repo / "feature.txt"
        feature_file.write_text("Feature work")
        repo.index.add(["feature.txt"])
        repo.index.commit("Feature commit")

        # Get diff using branch name as base
        diff_output = github_ops.git_diff_range(temp_git_repo, "main", "HEAD")

        # Should show the feature file
        assert "feature.txt" in diff_output
        assert "+Feature work" in diff_output

    def test_diff_range_defaults_to_head(self, github_ops, temp_git_repo):
        """Test that head_ref defaults to HEAD."""
        repo = git.Repo(temp_git_repo)
        base_sha = repo.head.commit.hexsha

        # Create a new commit
        new_file = temp_git_repo / "test.txt"
        new_file.write_text("test content")
        repo.index.add(["test.txt"])
        repo.index.commit("Add test file")

        # Call without head_ref (should default to HEAD)
        diff_output = github_ops.git_diff_range(temp_git_repo, base_sha)

        assert "test.txt" in diff_output
        assert "+test content" in diff_output

    def test_diff_range_no_changes(self, github_ops, temp_git_repo):
        """Test diff range when base and head are the same."""
        repo = git.Repo(temp_git_repo)
        current_sha = repo.head.commit.hexsha

        # Diff from current commit to itself
        diff_output = github_ops.git_diff_range(temp_git_repo, current_sha, "HEAD")

        # Should be empty (no changes)
        assert diff_output.strip() == ""

    def test_diff_range_invalid_ref(self, github_ops, temp_git_repo):
        """Test error handling with invalid ref."""
        with pytest.raises(RuntimeError, match="Failed to diff"):
            github_ops.git_diff_range(temp_git_repo, "nonexistent-ref", "HEAD")

    def test_diff_range_complex_changes(self, github_ops, temp_git_repo):
        """Test diff range with mixed additions, modifications, and deletions."""
        repo = git.Repo(temp_git_repo)
        base_sha = repo.head.commit.hexsha

        # Add a new file
        new_file = temp_git_repo / "new.py"
        new_file.write_text("# New file")

        # Modify existing file
        readme = temp_git_repo / "README.md"
        readme.write_text("# Updated")

        # Stage and commit
        repo.index.add(["new.py", "README.md"])
        repo.index.commit("Add and modify files")

        # Get cumulative diff
        diff_output = github_ops.git_diff_range(temp_git_repo, base_sha, "HEAD")

        # Verify all changes appear
        assert "new.py" in diff_output
        assert "README.md" in diff_output
        assert "+# New file" in diff_output
        assert "+# Updated" in diff_output


class TestGitGetRootCommit:
    """Tests for git_get_root_commit method."""

    def test_get_root_commit_success(self, github_ops, temp_git_repo):
        """Test getting root commit from repository."""
        root_sha = github_ops.git_get_root_commit(temp_git_repo)

        # Verify it's a valid SHA (40 hex characters)
        assert len(root_sha) == 40
        assert all(c in "0123456789abcdef" for c in root_sha)

        # Verify it's the actual root commit (has no parents)
        repo = git.Repo(temp_git_repo)
        root_commit = repo.commit(root_sha)
        assert len(root_commit.parents) == 0

    def test_get_root_commit_with_multiple_commits(self, github_ops, temp_git_repo):
        """Test getting root commit when repository has multiple commits."""
        repo = git.Repo(temp_git_repo)

        # Remember the initial root commit
        initial_root = github_ops.git_get_root_commit(temp_git_repo)

        # Create several more commits
        for i in range(3):
            test_file = temp_git_repo / f"file{i}.txt"
            test_file.write_text(f"Content {i}")
            repo.index.add([f"file{i}.txt"])
            repo.index.commit(f"Commit {i}")

        # Root commit should still be the same
        root_sha = github_ops.git_get_root_commit(temp_git_repo)
        assert root_sha == initial_root

        # Verify it has no parents
        root_commit = repo.commit(root_sha)
        assert len(root_commit.parents) == 0


class TestGitGetRemoteRefSHA:
    """Tests for git_get_remote_ref_sha method."""

    def test_get_remote_ref_sha_success(self, github_ops, monkeypatch):
        """Test successfully getting remote ref SHA."""
        import subprocess
        from unittest.mock import MagicMock

        # Mock subprocess.run to return a valid SHA
        mock_result = MagicMock()
        mock_result.stdout = "a1b2c3d4e5f6789012345678901234567890abcd\trefs/heads/main\n"
        mock_result.returncode = 0

        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        # Call method
        sha = github_ops.git_get_remote_ref_sha("https://github.com/user/repo.git", "refs/heads/main")

        # Verify result
        assert sha == "a1b2c3d4e5f6789012345678901234567890abcd"

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "ls-remote", "https://github.com/user/repo.git", "refs/heads/main"]
        assert call_args[1]["capture_output"] is True
        assert call_args[1]["text"] is True
        assert call_args[1]["check"] is True
        assert call_args[1]["timeout"] == 30

    def test_get_remote_ref_sha_default_ref(self, github_ops, monkeypatch):
        """Test getting remote ref SHA with default ref (refs/heads/main)."""
        import subprocess
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.stdout = "1234567890abcdef1234567890abcdef12345678\trefs/heads/main\n"

        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        sha = github_ops.git_get_remote_ref_sha("https://github.com/user/repo.git")

        assert sha == "1234567890abcdef1234567890abcdef12345678"
        call_args = mock_run.call_args
        assert "refs/heads/main" in call_args[0][0]

    def test_get_remote_ref_sha_custom_ref(self, github_ops, monkeypatch):
        """Test getting remote ref SHA with custom ref."""
        import subprocess
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_result.stdout = "fedcba0987654321fedcba0987654321fedcba09\trefs/heads/develop\n"

        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        sha = github_ops.git_get_remote_ref_sha("https://github.com/user/repo.git", "refs/heads/develop")

        assert sha == "fedcba0987654321fedcba0987654321fedcba09"
        call_args = mock_run.call_args
        assert "refs/heads/develop" in call_args[0][0]

    def test_get_remote_ref_sha_not_found(self, github_ops, monkeypatch):
        """Test error when remote ref not found."""
        import subprocess
        from unittest.mock import MagicMock

        # Mock empty output (ref not found)
        mock_result = MagicMock()
        mock_result.stdout = ""

        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Remote ref not found"):
            github_ops.git_get_remote_ref_sha("https://github.com/user/repo.git", "refs/heads/nonexistent")

    def test_get_remote_ref_sha_invalid_format(self, github_ops, monkeypatch):
        """Test error when SHA has invalid format."""
        import subprocess
        from unittest.mock import MagicMock

        # Mock invalid SHA (wrong length)
        mock_result = MagicMock()
        mock_result.stdout = "invalid123\trefs/heads/main\n"

        mock_run = MagicMock(return_value=mock_result)
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Invalid SHA format"):
            github_ops.git_get_remote_ref_sha("https://github.com/user/repo.git")

    def test_get_remote_ref_sha_git_command_error(self, github_ops, monkeypatch):
        """Test error when git ls-remote fails."""
        import subprocess
        from unittest.mock import MagicMock

        # Mock CalledProcessError
        mock_run = MagicMock(
            side_effect=subprocess.CalledProcessError(
                returncode=128, cmd="git ls-remote", stderr="fatal: repository not found"
            )
        )
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Failed to get remote ref SHA"):
            github_ops.git_get_remote_ref_sha("https://github.com/user/invalid.git")

    def test_get_remote_ref_sha_timeout(self, github_ops, monkeypatch):
        """Test error when git ls-remote times out."""
        import subprocess
        from unittest.mock import MagicMock

        # Mock TimeoutExpired
        mock_run = MagicMock(side_effect=subprocess.TimeoutExpired(cmd="git ls-remote", timeout=30))
        monkeypatch.setattr(subprocess, "run", mock_run)

        with pytest.raises(RuntimeError, match="Timeout getting remote ref SHA"):
            github_ops.git_get_remote_ref_sha("https://github.com/slow-server/repo.git")
