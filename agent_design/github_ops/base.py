"""Abstract base class for GitHub operations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class GitHubOperationsBase(ABC):
    """Abstract base class for GitHub and Git operations.

    This class defines the interface for all GitHub/Git operations used in the workflow.
    Implementations should provide concrete versions for production (using PyGithub/GitPython)
    and testing (using fakes/mocks).
    """

    @abstractmethod
    def git_create_and_push_branch(self, repo_path: Path, branch_name: str) -> dict[str, Any]:
        """Create and push a new git branch.

        Args:
            repo_path: Path to git repository
            branch_name: Name of branch to create

        Returns:
            Dictionary with success status and branch info or error
        """
        raise NotImplementedError

    @abstractmethod
    def git_extract_commit_info(self, agent_output: str) -> tuple[str | None, list[str], list[str]]:
        """Extract commit SHA and file lists from agent output.

        Args:
            agent_output: Raw output from agent execution

        Returns:
            Tuple of (commit_sha, files_created, files_modified)
            commit_sha will be None if not found
        """
        raise NotImplementedError

    @abstractmethod
    def git_verify_commit_exists(self, repo_path: Path, commit_sha: str) -> bool:
        """Verify git commit exists in repository.

        Args:
            repo_path: Repository path
            commit_sha: Commit SHA to verify

        Returns:
            True if commit exists, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def git_check_commit_is_head(self, repo_path: Path, commit_sha: str) -> bool:
        """Check if given commit is the current HEAD.

        Args:
            repo_path: Repository path
            commit_sha: Commit SHA to check

        Returns:
            True if commit is at HEAD, False if other commits exist on top
        """
        raise NotImplementedError

    @abstractmethod
    def git_rollback_commit(self, repo_path: Path, commit_sha: str) -> bool:
        """Rollback (hard reset) to the commit before the given commit SHA.

        This is equivalent to: git reset --hard <commit_sha>~1

        Args:
            repo_path: Repository path
            commit_sha: Commit SHA to rollback (will reset to parent of this commit)

        Returns:
            True if rollback succeeded, False otherwise

        Raises:
            ValueError: If commit doesn't exist or has no parent
            git.GitCommandError: If git operation fails
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_commit_file_list(
        self,
        repo_path: Path,
        commit_sha: str,
    ) -> tuple[list[str], list[str]]:
        """Get lists of created and modified files from git commit.

        Args:
            repo_path: Repository path
            commit_sha: Commit SHA to analyze

        Returns:
            Tuple of (files_created, files_modified) with paths relative to repo root

        Raises:
            RuntimeError: If git command fails
        """
        raise NotImplementedError

    @abstractmethod
    def git_commit_changes(
        self,
        repo_path: Path,
        commit_message: str,
    ) -> str:
        """Commit all changes in working tree with given message.

        Args:
            repo_path: Repository path
            commit_message: Commit message

        Returns:
            Commit SHA of the created commit

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_discard_changes(self, repo_path: Path) -> None:
        """Discard all uncommitted changes in working tree.

        This resets the working tree to HEAD and removes untracked files.

        Args:
            repo_path: Repository path

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_is_clean(self, repo_path: Path) -> bool:
        """Check if a Git repository has a clean working tree.

        A repository is considered clean if:
        - No uncommitted changes (staged or unstaged)
        - No untracked files

        Args:
            repo_path: Path to the Git repository root

        Returns:
            True if the repository is clean, False if dirty

        Raises:
            ValueError: If repo_path is not a valid Git repository

        Example:
            if not git_is_clean(Path("/path/to/repo")):
                raise ValueError("Repository must be clean")
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_working_tree_file_lists(self, repo_path: Path) -> tuple[list[str], list[str]]:
        """Get lists of created and modified files from working tree.

        Args:
            repo_path: Repository path

        Returns:
            Tuple of (files_created, files_modified) - paths relative to repo root

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_stage_files(self, repo_path: Path, file_paths: list[str] | list[Path]) -> None:
        """Stage specific files for commit.

        Args:
            repo_path: Repository path
            file_paths: List of file paths to stage (can be absolute or relative to repo)

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_commit_staged(self, repo_path: Path, commit_message: str) -> str:
        """Commit already-staged changes with given message.

        Args:
            repo_path: Repository path
            commit_message: Commit message

        Returns:
            Commit SHA of the created commit

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_head_sha(self, repo_path: Path) -> str:
        """Get the SHA of the current HEAD commit.

        Args:
            repo_path: Repository path

        Returns:
            SHA of HEAD commit

        Raises:
            RuntimeError: If git operations fail or no commits exist
        """
        raise NotImplementedError

    @abstractmethod
    def git_push_to_remote(self, repo_path: Path, remote_name: str = "origin") -> None:
        """Push current branch to remote repository.

        Args:
            repo_path: Repository path
            remote_name: Name of remote (default: "origin")

        Raises:
            RuntimeError: If git operations fail

        Note:
            If the remote doesn't exist (e.g., in test environments), this logs a warning
            and returns gracefully instead of raising an error.
        """
        raise NotImplementedError

    @abstractmethod
    def git_check_file_tracked(self, repo_path: Path, file_path: Path) -> bool:
        """Check if a file is tracked by git (exists in git index).

        Args:
            repo_path: Repository path
            file_path: Path to file to check

        Returns:
            True if file is tracked in git, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def git_restore_file_from_head(self, repo_path: Path, file_path: Path) -> None:
        """Restore a file to its state at HEAD.

        This is equivalent to: git checkout HEAD -- <file>

        Args:
            repo_path: Repository path
            file_path: Path to file to restore

        Raises:
            RuntimeError: If git operations fail
            ValueError: If file doesn't exist in git HEAD
        """
        raise NotImplementedError

    @abstractmethod
    def git_revert_commit(self, repo_path: Path, commit_sha: str) -> str:
        """Revert a commit by creating a new commit that undoes its changes.

        This is equivalent to: git revert --no-edit <commit_sha>

        Args:
            repo_path: Repository path
            commit_sha: Commit SHA to revert

        Returns:
            SHA of the revert commit

        Raises:
            RuntimeError: If git operations fail (e.g., conflicts)
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_commit_sha(self, repo_path: Path, ref: str) -> str:
        """Get the commit SHA for a given ref.

        Args:
            repo_path: Repository path
            ref: Git ref (branch, tag, HEAD, etc.)

        Returns:
            Commit SHA

        Raises:
            RuntimeError: If ref doesn't exist or git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_worktree_add(self, repo_path: Path, worktree_path: Path, base_ref: str, branch: str | None = None) -> None:
        """Create a Git worktree.

        Args:
            repo_path: Main repository path
            worktree_path: Path where worktree should be created
            base_ref: Ref to base the worktree on
            branch: Optional branch name to create in worktree

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_clone(self, source_path: Path, dest_path: Path, base_ref: str, branch: str | None = None) -> None:
        """Clone a Git repository from local path.

        Args:
            source_path: Source repository path
            dest_path: Destination path for clone
            base_ref: Ref to checkout after cloning
            branch: Optional branch name to create

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_status(self, repo_path: Path) -> dict[str, Any]:
        """Get repository status.

        Returns:
            Dictionary with:
                - untracked_files: List of untracked file paths
                - modified_files: List of modified unstaged file paths
                - staged_files: List of staged file paths
                - dirty: Boolean indicating if repo is dirty
                - head_sha: SHA of HEAD commit
                - commit_count: Number of commits

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_ref_exists(self, repo_path: Path, ref: str) -> bool:
        """Check if a ref exists.

        Args:
            repo_path: Repository path
            ref: Git ref to check

        Returns:
            True if ref exists, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def git_get_merge_base(self, repo_path: Path, ref1: str, ref2: str) -> str | None:
        """Get merge base between two refs.

        Args:
            repo_path: Repository path
            ref1: First ref
            ref2: Second ref

        Returns:
            SHA of merge base commit, or None if no common ancestor
        """
        raise NotImplementedError

    @abstractmethod
    def git_checkout(self, repo_path: Path, ref: str, create_branch: bool = False) -> None:
        """Checkout a ref, optionally creating a new branch.

        Args:
            repo_path: Repository path
            ref: Ref to checkout
            create_branch: If True, create a new branch

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_merge(
        self, repo_path: Path, ref: str, ff_only: bool = False, no_ff: bool = False, message: str | None = None
    ) -> None:
        """Merge a ref into current branch.

        Args:
            repo_path: Repository path
            ref: Ref to merge
            ff_only: If True, only allow fast-forward merge
            no_ff: If True, create merge commit even if fast-forward is possible
            message: Optional merge commit message

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_reset_hard(self, repo_path: Path, ref: str) -> None:
        """Hard reset to a ref.

        Args:
            repo_path: Repository path
            ref: Ref to reset to

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_add_remote(self, repo_path: Path, name: str, url: str) -> None:
        """Add or update a remote.

        Args:
            repo_path: Repository path
            name: Remote name
            url: Remote URL

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_fetch(self, repo_path: Path, remote: str) -> None:
        """Fetch from a remote.

        Args:
            repo_path: Repository path
            remote: Remote name

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_push(self, repo_path: Path, remote: str, refspec: str) -> None:
        """Push to a remote with specific refspec.

        Args:
            repo_path: Repository path
            remote: Remote name
            refspec: Refspec to push (e.g., "main:main", "HEAD:refs/heads/feature")

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_clone_from_url(self, url: str, dest_path: Path, branch: str | None = None) -> None:
        """Clone a repository from a URL.

        Args:
            url: Repository URL
            dest_path: Destination path for clone
            branch: Optional branch to checkout

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_add_all(self, repo_path: Path) -> None:
        """Stage all changes in a repository.

        Args:
            repo_path: Repository path

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_is_dirty(self, repo_path: Path, untracked_files: bool = False) -> bool:
        """Check if repository has uncommitted changes.

        Args:
            repo_path: Repository path
            untracked_files: Whether to consider untracked files as dirty

        Returns:
            True if repository has uncommitted changes, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def git_commit(self, repo_path: Path, message: str) -> str:
        """Create a commit and return its SHA.

        Args:
            repo_path: Repository path
            message: Commit message

        Returns:
            SHA of the created commit

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_revert(self, repo_path: Path, ref: str, mainline: int | None = None) -> None:
        """Revert a commit.

        Args:
            repo_path: Repository path
            ref: Commit reference to revert
            mainline: Parent number for merge commits (1-indexed)

        Raises:
            RuntimeError: If git operations fail
        """
        raise NotImplementedError

    # GitHub API methods

    @abstractmethod
    def get_current_commit(self) -> dict[str, Any]:
        """Get current local commit details.

        Returns:
            Dictionary with commit information
        """
        raise NotImplementedError

    @abstractmethod
    def get_current_branch(self) -> dict[str, Any]:
        """Get currently checked out branch.

        Returns:
            Dictionary with branch information
        """
        raise NotImplementedError

    @abstractmethod
    def find_pr_for_branch(self, branch_name: str | None = None) -> dict[str, Any]:
        """Find PR associated with branch.

        Args:
            branch_name: Branch name. If None, uses current branch.

        Returns:
            Dictionary with PR information or None if not found
        """
        raise NotImplementedError

    @abstractmethod
    def get_pr_comments(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve PR comments and threads.

        Args:
            pr_number: PR number. If None, finds PR for branch.
            branch_name: Branch name. If None, uses current branch.

        Returns:
            Dictionary with comments and review threads
        """
        raise NotImplementedError

    @abstractmethod
    def post_pr_reply(
        self,
        body: str,
        pr_number: int | None = None,
        branch_name: str | None = None,
        comment_id: int | None = None,
    ) -> dict[str, Any]:
        """Post replies to PR comments.

        Args:
            body: Comment body
            pr_number: PR number. If None, finds PR for branch.
            branch_name: Branch name. If None, uses current branch.
            comment_id: ID of comment to reply to. If None, posts as issue comment.

        Returns:
            Dictionary with posted comment information
        """
        raise NotImplementedError

    @abstractmethod
    def create_pr(
        self,
        title: str,
        body: str | None = None,
        branch_name: str | None = None,
        base_branch: str = "main",
    ) -> dict[str, Any]:
        """Create a pull request.

        Args:
            title: PR title
            body: PR body/description (optional)
            branch_name: Source branch name (optional, defaults to current branch)
            base_branch: Target branch name (default: "main")

        Returns:
            Dictionary with success status and PR info or error
        """
        raise NotImplementedError

    @abstractmethod
    def check_ci_build_and_test_errors(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Check CI build/test status for PR or commit.

        Args:
            pr_number: PR number. If None, finds PR for branch.
            branch_name: Branch name. If None, uses current branch.
            commit_sha: Commit SHA. If None, uses current commit.

        Returns:
            Dictionary with CI status and errors
        """
        raise NotImplementedError

    @abstractmethod
    def check_ci_lint_errors(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Check CI lint errors for PR or commit.

        Args:
            pr_number: PR number. If None, finds PR for branch.
            branch_name: Branch name. If None, uses current branch.
            commit_sha: Commit SHA. If None, uses current commit.

        Returns:
            Dictionary with lint status and errors
        """
        raise NotImplementedError

    @abstractmethod
    def get_build_status(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive build status.

        Args:
            pr_number: PR number. If None, finds PR for branch.
            branch_name: Branch name. If None, uses current branch.
            commit_sha: Commit SHA. If None, uses current commit.

        Returns:
            Dictionary with comprehensive build status
        """
        raise NotImplementedError

    @abstractmethod
    def get_pr_body(self, pr_number: int) -> str | None:
        """Get the body text of a pull request.

        Args:
            pr_number: Pull request number

        Returns:
            PR body text or None if PR not found or has no body

        Raises:
            RuntimeError: If GitHub API operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def update_pr_body(self, pr_number: int, body: str) -> None:
        """Update the body text of a pull request.

        Args:
            pr_number: Pull request number
            body: New body text

        Raises:
            RuntimeError: If GitHub API operations fail
        """
        raise NotImplementedError

    @abstractmethod
    def git_show_commit(self, repo_path: Path, commit_sha: str) -> str:
        """Get full commit diff (equivalent to git show).

        Args:
            repo_path: Path to repository
            commit_sha: Commit SHA to show

        Returns:
            Full diff output from git show

        Raises:
            RuntimeError: If git show fails
        """
        raise NotImplementedError

    @abstractmethod
    def git_diff_range(self, repo_path: Path, base_ref: str, head_ref: str = "HEAD") -> str:
        """Get diff between two refs (equivalent to git diff base_ref...head_ref).

        This shows all changes from base_ref to head_ref, which is useful for reviewing
        all changes in a feature branch or validation shadow.

        Args:
            repo_path: Path to repository
            base_ref: Base reference (e.g., "main", commit SHA, or merge-base)
            head_ref: Head reference to compare to (defaults to "HEAD")

        Returns:
            Full diff output from git diff

        Raises:
            RuntimeError: If git diff fails
        """
        raise NotImplementedError
