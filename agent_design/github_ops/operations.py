"""Real implementation of GitHub operations using PyGithub and GitPython."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

import git
from github import Auth, Github, GithubException
from github.PullRequest import PullRequest
from github.Repository import Repository

from .base import GitHubOperationsBase
from .types import BranchResponse, CommitInfo, CommitResponse, PRInfo, PRResponse

logger = logging.getLogger(__name__)


def parse_github_remote_url(remote_url: str) -> tuple[str, str, str] | None:
    """Parse GitHub remote URL to extract owner, repo, and base URL.

    Supports both SSH and HTTPS formats for github.com and GitHub Enterprise.

    Args:
        remote_url: Git remote URL (SSH or HTTPS)

    Returns:
        Tuple of (owner, repo, base_url) or None if parsing fails

    Examples:
        >>> parse_github_remote_url("git@github.com:owner/repo.git")
        ('owner', 'repo', 'https://api.github.com')

        >>> parse_github_remote_url("https://github.com/owner/repo.git")
        ('owner', 'repo', 'https://api.github.com')

        >>> parse_github_remote_url("git@github.pie.apple.com:owner/repo.git")
        ('owner', 'repo', 'https://github.pie.apple.com/api/v3')
    """
    import re

    # SSH format: git@hostname:owner/repo.git
    ssh_pattern = r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?$"
    # HTTPS format: https://hostname/owner/repo.git
    https_pattern = r"https://([^/]+)/([^/]+)/(.+?)(?:\.git)?$"

    for pattern in [ssh_pattern, https_pattern]:
        match = re.match(pattern, remote_url)
        if match:
            hostname, owner, repo = match.groups()

            # Determine base URL based on hostname
            base_url = "https://api.github.com" if hostname == "github.com" else f"https://{hostname}/api/v3"

            return (owner, repo, base_url)

    # Could not parse
    logger.warning(f"Could not parse GitHub remote URL: {remote_url}")
    return None


class RepositoryConfig:
    """Temporary placeholder for repository configuration.

    This will be replaced with proper import once mcp_server imports are refactored.
    """

    def __init__(
        self,
        workspace: str | None = None,
        github_owner: str = "",
        github_repo: str = "",
        remote_url: str = "",
    ):
        """Initialize repository configuration.

        Args:
            workspace: Optional path to local repository workspace (not needed for shadow-based workflows)
            github_owner: GitHub repository owner (optional, will be parsed from remote_url if not provided)
            github_repo: GitHub repository name (optional, will be parsed from remote_url if not provided)
            remote_url: Git remote URL (optional, used to auto-detect owner/repo)
        """
        self.workspace = workspace
        self.github_owner = github_owner
        self.github_repo = github_repo
        self.remote_url = remote_url


class GitHubOperations(GitHubOperationsBase):
    """Real implementation of GitHub operations using PyGithub and GitPython."""

    # Class attributes - type annotations for optional instances
    git_repo: git.Repo | None
    repo_path: Path | None

    def __init__(self, repo_config: RepositoryConfig, comment_tracker: Any | None = None):
        """Initialize GitHub operations.

        Args:
            repo_config: Repository configuration
            comment_tracker: Optional CommentTracker instance for reply tracking
        """
        self.repo_config = repo_config
        self.comment_tracker = comment_tracker

        # Only initialize git_repo if workspace is provided
        # Shadow-based workflows don't need a long-lived repo instance
        if repo_config.workspace:
            self.repo_path = Path(repo_config.workspace)
            try:
                self.git_repo = git.Repo(repo_config.workspace)
            except git.InvalidGitRepositoryError:
                raise ValueError(f"Invalid git repository: {repo_config.workspace}") from None
        else:
            self.repo_path = None
            self.git_repo = None

        # Determine GitHub owner and repo (either explicit or parsed from remote URL)
        github_owner = repo_config.github_owner
        github_repo = repo_config.github_repo
        github_base_url_parsed: str | None = None

        # If owner/repo not provided but remote_url is, try to parse them
        if (not github_owner or not github_repo) and repo_config.remote_url:
            parsed = parse_github_remote_url(repo_config.remote_url)
            if parsed:
                github_owner, github_repo, github_base_url_parsed = parsed
                logger.info(f"Parsed GitHub remote: {github_owner}/{github_repo}")

        # Only initialize GitHub API if owner and repo are available
        # This allows local-only git operations without GitHub API access
        if github_owner and github_repo:
            # Load token from ~/.roxy_github_token first, fall back to GITHUB_TOKEN env var
            _roxy_token_path = Path.home() / ".roxy_github_token"
            if _roxy_token_path.exists():
                self.github_token = _roxy_token_path.read_text().strip() or None
            else:
                self.github_token = None
            if not self.github_token:
                self.github_token = os.getenv("GITHUB_TOKEN")
            if not self.github_token:
                raise ValueError("GitHub token required: set GITHUB_TOKEN or create ~/.roxy_github_token")

            # Use parsed base URL if available, otherwise use environment variable
            if github_base_url_parsed:
                self.github_base_url: str | None = github_base_url_parsed
                logger.debug(f"Using base URL from remote URL: {self.github_base_url}")
            else:
                self.github_base_url = os.getenv("GITHUB_BASE_URL", "https://github.pie.apple.com/api/v3")

            # Check SSL verification setting
            verify_ssl = os.getenv("GITHUB_VERIFY_SSL", "true").lower()
            self.verify_ssl = verify_ssl not in ("false", "0", "no", "off")

            # Configure SSL verification
            if not self.verify_ssl:
                logger.warning("SSL verification is disabled for GitHub API requests")
                # Disable SSL warnings when verification is disabled
                import urllib3

                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Initialize GitHub client with Enterprise URL
            auth = Auth.Token(self.github_token)
            if self.github_base_url and self.github_base_url != "https://api.github.com":
                logger.info(f"Using GitHub Enterprise at: {self.github_base_url}")
                self.github = Github(base_url=self.github_base_url, auth=auth, verify=self.verify_ssl)
            else:
                logger.info("Using public GitHub API")
                self.github = Github(auth=auth, verify=self.verify_ssl)

            # Get the GitHub repo
            self.repo: Repository | None = self.github.get_repo(f"{github_owner}/{github_repo}")
            logger.info(f"GitHub API initialized for {github_owner}/{github_repo}")

            # Store parsed owner/repo as instance variables for later use
            self.github_owner = github_owner
            self.github_repo = github_repo
        else:
            # Local git operations only - no GitHub API needed
            self.github_token = None
            self.github_base_url = None
            self.verify_ssl = True
            self.github = None  # type: ignore[assignment]
            self.repo = None
            self.github_owner = ""
            self.github_repo = ""
            logger.debug("GitHub API not initialized (local git operations only)")

    def status_clean(self) -> bool:
        """Check if repository has a clean working tree.

        A repository is considered clean if:
        - No uncommitted changes (staged or unstaged)
        - No untracked files

        Returns:
            True if repository is clean, False if dirty

        Raises:
            ValueError: If repo_path is not a valid Git repository or workspace not initialized
        """
        if self.git_repo is None:
            raise ValueError("Workspace not initialized - cannot check status")
        return not self.git_repo.is_dirty(untracked_files=True)

    # Git methods
    def git_create_and_push_branch(self, repo_path: Path, branch_name: str) -> dict[str, Any]:
        """Create and push a new git branch.

        If the branch already exists locally, resets it to current HEAD and force pushes.
        This allows re-running workflows with the same branch name.
        """
        try:
            repo = git.Repo(repo_path)

            # Check if branch already exists
            branch_existed = False
            try:
                existing_branch = repo.heads[branch_name]
                branch_existed = True
                logger.info(f"Branch '{branch_name}' already exists, resetting to current HEAD")
                # Reset existing branch to current HEAD
                existing_branch.set_commit(repo.head.commit)
                existing_branch.checkout()
            except IndexError:
                # Branch doesn't exist, create it
                logger.info(f"Creating new branch: {branch_name}")
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()

            # Push branch with upstream tracking (force push if branch existed)
            if branch_existed:
                # Force push since we reset existing branch
                repo.remote("origin").push(refspec=f"{branch_name}:{branch_name}", force=True)
            else:
                repo.remote("origin").push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)

            return {
                "success": True,
                "branch_name": branch_name,
                "message": f"{'Updated and force-pushed' if branch_existed else 'Created and pushed'} branch: {branch_name}",
                "existing": branch_existed,
            }

        except (git.GitCommandError, git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            logger.error(f"Git operation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to create/push branch '{branch_name}': {e}",
            }

    def git_extract_commit_info(self, agent_output: str) -> tuple[str | None, list[str], list[str]]:
        """Extract commit SHA and file lists from agent output."""
        import re

        # Look for "Commit SHA: <sha>" pattern
        sha_pattern = r"Commit SHA:\s*([0-9a-f]{40})"
        sha_match = re.search(sha_pattern, agent_output, re.IGNORECASE)

        commit_sha = sha_match.group(1) if sha_match else None

        # Extract file lists from output
        files_created = []
        files_modified = []

        # Look for "Files Created: [...]" pattern
        created_pattern = r"Files Created:\s*\[(.*?)\]"
        created_match = re.search(created_pattern, agent_output, re.IGNORECASE | re.DOTALL)
        if created_match:
            files_str = created_match.group(1)
            files_created = [f.strip().strip("'\"") for f in files_str.split(",") if f.strip()]

        # Look for "Files Modified: [...]" pattern
        modified_pattern = r"Files Modified:\s*\[(.*?)\]"
        modified_match = re.search(modified_pattern, agent_output, re.IGNORECASE | re.DOTALL)
        if modified_match:
            files_str = modified_match.group(1)
            files_modified = [f.strip().strip("'\"") for f in files_str.split(",") if f.strip()]

        return commit_sha, files_created, files_modified

    def git_verify_commit_exists(self, repo_path: Path, commit_sha: str) -> bool:
        """Verify git commit exists in repository."""
        try:
            repo = git.Repo(repo_path)
            repo.commit(commit_sha)
            return True
        except (git.BadName, git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
            return False

    def git_check_commit_is_head(self, repo_path: Path, commit_sha: str) -> bool:
        """Check if given commit is the current HEAD."""
        try:
            repo = git.Repo(repo_path)
            head_sha = repo.head.commit.hexsha
            return head_sha == commit_sha
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False

    def git_rollback_commit(self, repo_path: Path, commit_sha: str) -> bool:
        """Rollback (hard reset) to the commit before the given commit SHA."""
        try:
            repo = git.Repo(repo_path)

            # Get the commit object
            commit = repo.commit(commit_sha)

            # Ensure commit has a parent
            if not commit.parents:
                raise ValueError(f"Commit {commit_sha} has no parent (cannot rollback root commit)")

            # Get parent commit
            parent_commit = commit.parents[0]

            # Hard reset to parent
            repo.head.reset(parent_commit, index=True, working_tree=True)

            return True

        except (git.BadName, git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise ValueError(f"Cannot rollback commit {commit_sha}: {e}") from e
        except git.GitCommandError as e:
            raise git.GitCommandError(f"Git rollback failed: {e}") from e

    def git_get_commit_file_list(self, repo_path: Path, commit_sha: str) -> tuple[list[str], list[str]]:
        """Get lists of created and modified files from git commit."""
        try:
            repo = git.Repo(repo_path)
            commit = repo.commit(commit_sha)

            files_created = []
            files_modified = []

            # Get diffs against parent commit (or empty tree for first commit)
            if commit.parents:
                parent = commit.parents[0]
                diffs = parent.diff(commit)
            else:
                # First commit - compare against empty tree
                diffs = commit.diff(git.NULL_TREE)

            for diff in diffs:
                if diff.new_file and diff.b_path:
                    files_created.append(diff.b_path)
                elif (diff.renamed_file or diff.deleted_file or diff.a_path) and diff.a_path:
                    files_modified.append(diff.a_path)

            return files_created, files_modified

        except (git.BadName, git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to get file list from commit {commit_sha}: {e}") from e

    def git_commit_changes(self, repo_path: Path, commit_message: str) -> str:
        """Commit all changes in working tree with given message."""
        try:
            repo = git.Repo(repo_path)

            # Stage all changes (new, modified, deleted)
            repo.git.add("-A")

            # Create commit
            commit = repo.index.commit(commit_message)

            return str(commit.hexsha)

        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to commit changes: {e}") from e

    def git_discard_changes(self, repo_path: Path) -> None:
        """Discard all uncommitted changes in working tree."""
        try:
            repo = git.Repo(repo_path)

            # Reset working tree to HEAD (discards changes to tracked files)
            # Use --quiet to suppress errors when there are no changes
            try:
                repo.git.restore(".", quiet=True)
            except git.GitCommandError as e:
                # Ignore errors when there's nothing to restore
                if "did not match any file" not in str(e):
                    raise

            # Remove untracked files and directories
            try:
                repo.git.clean("-fd")
            except git.GitCommandError as e:
                # Ignore errors when there are no untracked files
                if "No untracked files" not in str(e):
                    raise

        except (git.InvalidGitRepositoryError, RuntimeError) as e:
            raise RuntimeError(f"Failed to discard changes: {e}") from e

    def git_is_clean(self, repo_path: Path) -> bool:
        """Check if a Git repository has a clean working tree."""
        try:
            repo = git.Repo(repo_path)
            # is_dirty() returns True if there are changes
            # untracked_files=True includes untracked files in the check
            return not repo.is_dirty(untracked_files=True)

        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise ValueError(f"Not a Git repository: {repo_path}") from e

    def git_get_working_tree_file_lists(self, repo_path: Path) -> tuple[list[str], list[str]]:
        """Get lists of created and modified files from working tree."""
        try:
            repo = git.Repo(repo_path)

            # Get untracked files (new files)
            files_created = repo.untracked_files

            # Get modified files (staged and unstaged) - filter out None values
            # Handle case where repo has no commits yet (HEAD doesn't exist)
            try:
                files_modified = [item.a_path for item in repo.index.diff("HEAD") if item.a_path]
            except git.BadName:
                # No HEAD yet (empty repo), all tracked files are "created"
                files_modified = []

            return files_created, files_modified

        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to get working tree file lists: {e}") from e

    def git_stage_files(self, repo_path: Path, file_paths: list[str] | list[Path]) -> None:
        """Stage specific files for commit."""
        try:
            repo = git.Repo(repo_path)

            # Convert paths to strings relative to repo root
            paths_to_add = []
            for file_path in file_paths:
                if isinstance(file_path, Path):
                    # If absolute, make relative to repo root
                    if file_path.is_absolute():
                        try:
                            rel_path = file_path.relative_to(repo_path)
                            paths_to_add.append(str(rel_path))
                        except ValueError:
                            # Path is outside repo, use as-is
                            paths_to_add.append(str(file_path))
                    else:
                        paths_to_add.append(str(file_path))
                else:
                    paths_to_add.append(file_path)

            # Stage the files
            repo.index.add(paths_to_add)

        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to stage files: {e}") from e

    def git_commit_staged(self, repo_path: Path, commit_message: str) -> str:
        """Commit already-staged changes with given message."""
        try:
            repo = git.Repo(repo_path)

            # Create commit from staged changes
            commit = repo.index.commit(commit_message)

            return str(commit.hexsha)

        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to commit staged changes: {e}") from e

    def git_get_head_sha(self, repo_path: Path) -> str:
        """Get the SHA of the current HEAD commit."""
        try:
            repo = git.Repo(repo_path)
            return str(repo.head.commit.hexsha)

        except (git.InvalidGitRepositoryError, git.GitCommandError, ValueError) as e:
            raise RuntimeError(f"Failed to get HEAD SHA: {e}") from e

    def git_push_to_remote(self, repo_path: Path, remote_name: str = "origin") -> None:
        """Push current branch to remote repository."""
        try:
            repo = git.Repo(repo_path)

            # Check if remote exists
            try:
                remote = repo.remote(remote_name)
            except ValueError:
                # Remote doesn't exist - log warning and return gracefully
                logger.warning(f"Remote '{remote_name}' doesn't exist in repository at {repo_path} - skipping push")
                return

            # Push to remote
            remote.push()

        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to push to remote: {e}") from e

    def git_check_file_tracked(self, repo_path: Path, file_path: Path) -> bool:
        """Check if a file is tracked by git (exists in git index)."""
        try:
            repo = git.Repo(repo_path)

            # Make path relative to repo root if absolute
            if file_path.is_absolute():
                try:
                    rel_path = str(file_path.relative_to(repo_path))
                except ValueError:
                    # Path is outside repo
                    return False
            else:
                rel_path = str(file_path)

            # Check if file exists in git index
            # This is equivalent to: git ls-files --error-unmatch <file>
            try:
                # If the file is in the index, this won't raise an error
                _ = repo.git.ls_files("--error-unmatch", rel_path)
                return True
            except git.GitCommandError:
                return False

        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False

    def git_restore_file_from_head(self, repo_path: Path, file_path: Path) -> None:
        """Restore a file to its state at HEAD."""
        try:
            repo = git.Repo(repo_path)

            # Make path relative to repo root if absolute
            if file_path.is_absolute():
                try:
                    rel_path = str(file_path.relative_to(repo_path))
                except ValueError:
                    raise ValueError(f"File path {file_path} is outside repository {repo_path}") from None
            else:
                rel_path = str(file_path)

            # Restore file from HEAD
            repo.git.checkout("HEAD", "--", rel_path)

        except git.GitCommandError as e:
            if "did not match any file" in str(e):
                raise ValueError(f"File {file_path} does not exist in git HEAD") from e
            raise RuntimeError(f"Failed to restore file from HEAD: {e}") from e
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise RuntimeError(f"Failed to restore file from HEAD: {e}") from e

    def git_revert_commit(self, repo_path: Path, commit_sha: str) -> str:
        """Revert a commit by creating a new commit that undoes its changes."""
        try:
            repo = git.Repo(repo_path)

            # Revert the commit
            repo.git.revert("--no-edit", commit_sha)

            # Get the SHA of the revert commit (current HEAD)
            return str(repo.head.commit.hexsha)

        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to revert commit {commit_sha}: {e}") from e
        except (git.InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise RuntimeError(f"Failed to revert commit: {e}") from e

    def git_get_commit_sha(self, repo_path: Path, ref: str) -> str:
        """Get the commit SHA for a given ref."""
        try:
            repo = git.Repo(repo_path)
            return repo.commit(ref).hexsha
        except (git.GitCommandError, git.BadName, git.InvalidGitRepositoryError, ValueError) as e:
            raise RuntimeError(f"Failed to get commit SHA for {ref}: {e}") from e

    def git_worktree_add(self, repo_path: Path, worktree_path: Path, base_ref: str, branch: str | None = None) -> None:
        """Create a Git worktree."""
        try:
            repo = git.Repo(repo_path)
            if branch:
                repo.git.worktree("add", "-b", branch, str(worktree_path), base_ref)
            else:
                repo.git.worktree("add", str(worktree_path), base_ref)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to create worktree: {e.stderr}") from e

    def git_clone(
        self,
        source_path: Path,
        dest_path: Path,
        base_ref: str,
        branch: str | None = None,
        disable_gpg_signing: bool = True,
    ) -> None:
        """Clone a Git repository from local path.

        Args:
            source_path: Path to source repository
            dest_path: Path where clone will be created
            base_ref: Git ref to checkout after cloning
            branch: Optional branch name to create
            disable_gpg_signing: If True, disable GPG signing in cloned repo (default: True)
        """
        try:
            cloned_repo = git.Repo.clone_from(str(source_path), str(dest_path))
            if disable_gpg_signing:
                # Disable commit signing
                subprocess.run(
                    ["git", "config", "--local", "commit.gpgsign", "false"],
                    cwd=str(dest_path),
                    check=True,
                    capture_output=True,
                )
                # Override gpg.x509.program (for X.509 signing like ac-sign)
                subprocess.run(
                    ["git", "config", "--local", "gpg.x509.program", ""],
                    cwd=str(dest_path),
                    check=True,
                    capture_output=True,
                )
                # Override gpg.program (for regular GPG signing)
                subprocess.run(
                    ["git", "config", "--local", "gpg.program", ""],
                    cwd=str(dest_path),
                    check=True,
                    capture_output=True,
                )
                logger.debug(f"Disabled GPG signing in cloned repo: {dest_path}")
            cloned_repo.git.checkout(base_ref)
            if branch:
                cloned_repo.git.checkout("-b", branch)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to create clone: {e.stderr}") from e

    def git_get_status(self, repo_path: Path) -> dict[str, Any]:
        """Get repository status."""
        try:
            repo = git.Repo(repo_path)
            return {
                "untracked_files": repo.untracked_files,
                "modified_files": [item.a_path for item in repo.index.diff(None)],
                "staged_files": [item.a_path for item in repo.index.diff("HEAD")],
                "dirty": repo.is_dirty(untracked_files=True),
                "head_sha": repo.head.commit.hexsha,
                "commit_count": len(list(repo.iter_commits())),
            }
        except (git.GitCommandError, git.InvalidGitRepositoryError) as e:
            raise RuntimeError(f"Failed to get status: {e}") from e

    def git_ref_exists(self, repo_path: Path, ref: str) -> bool:
        """Check if a ref exists."""
        try:
            repo = git.Repo(repo_path)
            repo.commit(ref)
            return True
        except (git.BadName, git.GitCommandError):
            return False

    def git_get_merge_base(self, repo_path: Path, ref1: str, ref2: str) -> str | None:
        """Get merge base between two refs."""
        try:
            repo = git.Repo(repo_path)
            merge_base = repo.merge_base(ref1, ref2)
            return merge_base[0].hexsha if merge_base else None
        except git.GitCommandError:
            return None

    def git_get_root_commit(self, repo_path: Path) -> str:
        """Get the root commit (first commit with no parents) of the repository.

        Args:
            repo_path: Path to git repository

        Returns:
            SHA of the root commit

        Raises:
            RuntimeError: If unable to find root commit
        """
        try:
            repo = git.Repo(repo_path)
            root_commits_output = repo.git.rev_list("--max-parents=0", "HEAD").strip()
            root_commits = root_commits_output.split("\n")
            if not root_commits or not root_commits[0]:
                raise RuntimeError("No root commit found")
            return str(root_commits[0])
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to get root commit: {e.stderr}") from e

    def git_checkout(self, repo_path: Path, ref: str, create_branch: bool = False) -> None:
        """Checkout a ref, optionally creating a new branch."""
        try:
            repo = git.Repo(repo_path)
            if create_branch:
                repo.git.checkout("-b", ref)
            else:
                repo.git.checkout(ref)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to checkout {ref}: {e.stderr}") from e

    def git_merge(
        self, repo_path: Path, ref: str, ff_only: bool = False, no_ff: bool = False, message: str | None = None
    ) -> None:
        """Merge a ref into current branch."""
        try:
            logger.debug(f"merge: repo_path={repo_path}, ref={ref}, ff_only={ff_only}, no_ff={no_ff}")
            repo = git.Repo(repo_path)
            if ff_only:
                repo.git.merge(ref, ff_only=True)
            elif no_ff:
                repo.git.merge(ref, no_ff=True, m=message)
            else:
                repo.git.merge(ref)
            logger.info(f"Merged {ref} into current branch at {repo_path}")
        except git.GitCommandError as e:
            logger.error(f"Failed to merge {ref} at {repo_path}: {e.stderr}")
            raise RuntimeError(f"Failed to merge: {e.stderr}") from e

    def run_precommit_hooks(self, repo_path: Path) -> dict[str, Any]:
        """Run Git pre-commit hook and capture results.

        Args:
            repo_path: Path to repository

        Returns:
            Dictionary with:
            - exit_code: int
            - stdout: str
            - stderr: str
            - success: bool (True if exit code is 0)
            - duration: float (execution time in seconds)
        """
        import os
        import subprocess
        import time

        start_time = time.time()

        try:
            logger.debug(f"run_precommit_hooks: repo_path={repo_path}")

            # Check if Git hook exists
            hook_path = repo_path / "scripts" / "pre-commit-hook.sh"
            if not hook_path.exists():
                duration = time.time() - start_time
                error_msg = f"Pre-commit hook not found at: {hook_path}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Create isolated environment with PYTHONPATH set to shadow's src/ and test/ only
            # This prevents cross-shadow contamination where pytest imports from wrong shadows
            # We prepend shadow paths so they take precedence over any other paths
            isolated_env = os.environ.copy()
            shadow_src_path = repo_path / "src"
            shadow_test_path = repo_path / "test"

            # Prepend shadow paths to existing PYTHONPATH (if any)
            # This ensures shadow src/ and test/ have priority, but venv packages are still accessible
            existing_pythonpath = isolated_env.get("PYTHONPATH", "")
            if existing_pythonpath:
                isolated_env["PYTHONPATH"] = f"{shadow_src_path}:{shadow_test_path}:{existing_pythonpath}"
            else:
                isolated_env["PYTHONPATH"] = f"{shadow_src_path}:{shadow_test_path}"

            logger.debug(f"Isolated PYTHONPATH set to: {isolated_env['PYTHONPATH']}")

            # Run Git pre-commit hook directly
            result = subprocess.run(
                [str(hook_path)],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=isolated_env,  # Use isolated environment
            )

            duration = time.time() - start_time

            output = {
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
                "duration": duration,
            }

            if result.returncode == 0:
                logger.info(f"Pre-commit hooks passed in {duration:.2f}s at {repo_path}")
            else:
                logger.warning(f"Pre-commit hooks failed with exit code {result.returncode} in {duration:.2f}s")

            return output

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            error_msg = f"Pre-commit hooks timed out after {duration:.2f}s"
            logger.error(error_msg)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "success": False,
                "duration": duration,
            }
        except PermissionError as e:
            duration = time.time() - start_time
            error_msg = f"Permission denied executing pre-commit hook: {e}"
            logger.error(error_msg)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "success": False,
                "duration": duration,
            }
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to run pre-commit hooks: {e}"
            logger.error(error_msg)
            return {
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "success": False,
                "duration": duration,
            }

    def git_reset_hard(self, repo_path: Path, ref: str) -> None:
        """Hard reset to a ref."""
        try:
            repo = git.Repo(repo_path)
            repo.git.reset("--hard", ref)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to reset: {e.stderr}") from e

    def git_add_remote(self, repo_path: Path, name: str, url: str) -> None:
        """Add or update a remote."""
        try:
            repo = git.Repo(repo_path)
            try:
                repo.create_remote(name, url)
            except git.GitCommandError:
                # Remote exists, update URL
                remote = repo.remote(name)
                remote.set_url(url)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to add remote: {e.stderr}") from e

    def git_fetch(self, repo_path: Path, remote: str) -> None:
        """Fetch from a remote."""
        try:
            repo = git.Repo(repo_path)
            repo.git.fetch(remote)
        except git.GitCommandError as e:
            raise RuntimeError(f"Failed to fetch: {e.stderr}") from e

    def git_get_remote_ref_sha(self, remote_url: str, ref: str = "refs/heads/main") -> str:
        """Get SHA of a remote ref without cloning the repository.

        Uses git ls-remote to query the remote repository for the SHA
        of the specified ref. This is useful for getting the latest commit
        from a remote branch without needing a local clone.

        Args:
            remote_url: URL of the remote repository (e.g., "https://github.com/user/repo.git")
            ref: Git ref to query (default: "refs/heads/main")
                 Examples: "refs/heads/main", "refs/heads/develop", "HEAD"

        Returns:
            SHA of the remote ref (40-character hex string)

        Raises:
            RuntimeError: If git ls-remote fails or ref not found

        Example:
            >>> ops = GitHubOperations(config)
            >>> sha = ops.git_get_remote_ref_sha("https://github.com/user/repo.git", "refs/heads/main")
            >>> print(sha)
            'a1b2c3d4e5f6...'
        """
        try:
            result = subprocess.run(
                ["git", "ls-remote", remote_url, ref],
                capture_output=True,
                text=True,
                check=True,
                timeout=30,  # Prevent hanging on network issues
            )

            if not result.stdout.strip():
                raise RuntimeError(f"Remote ref not found: {ref} in {remote_url}")

            # Output format: "<sha>\t<ref>"
            sha = result.stdout.split()[0]

            # Validate SHA format (40 hex characters)
            if len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha):
                raise RuntimeError(f"Invalid SHA format from ls-remote: {sha}")

            logger.debug(f"git ls-remote {remote_url} {ref} -> {sha[:8]}")
            return sha

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else "No error output"
            raise RuntimeError(f"Failed to get remote ref SHA: {stderr}") from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Timeout getting remote ref SHA after 30s: {remote_url}") from e

    def git_push(self, repo_path: Path, remote: str, refspec: str, force: bool = False) -> None:
        """Push to a remote with specific refspec.

        Args:
            repo_path: Path to repository
            remote: Remote name (e.g., "origin")
            refspec: Refspec to push (e.g., "main", "feature-branch")
            force: If True, use --force to overwrite remote branch
        """
        try:
            logger.debug(f"push: repo_path={repo_path}, remote={remote}, refspec={refspec}, force={force}")
            repo = git.Repo(repo_path)
            if force:
                repo.git.push("--force", remote, refspec)
                logger.info(f"Force-pushed {refspec} to {remote} at {repo_path}")
            else:
                repo.git.push(remote, refspec)
                logger.info(f"Pushed {refspec} to {remote} at {repo_path}")
        except git.GitCommandError as e:
            logger.error(f"Failed to push {refspec} to {remote} at {repo_path}: {e.stderr}")
            raise RuntimeError(f"Failed to push: {e.stderr}") from e

    def git_clone_from_url(
        self, url: str, dest_path: Path, branch: str | None = None, disable_gpg_signing: bool = True
    ) -> None:
        """Clone a repository from a URL.

        Args:
            url: URL of repository to clone
            dest_path: Path where clone will be created
            branch: Optional branch name to checkout/create
            disable_gpg_signing: If True, disable GPG signing in cloned repo (default: True)
        """
        try:
            logger.debug(f"clone_from_url: url={url}, dest_path={dest_path}, branch={branch}")
            if branch:
                # Try to clone specific branch, but fallback to default if it doesn't exist
                try:
                    repo = git.Repo.clone_from(url, str(dest_path), branch=branch)
                    if disable_gpg_signing:
                        subprocess.run(
                            ["git", "config", "--local", "commit.gpgsign", "false"],
                            cwd=str(dest_path),
                            check=True,
                            capture_output=True,
                        )
                        subprocess.run(
                            ["git", "config", "--local", "gpg.x509.program", ""],
                            cwd=str(dest_path),
                            check=True,
                            capture_output=True,
                        )
                        subprocess.run(
                            ["git", "config", "--local", "gpg.program", ""],
                            cwd=str(dest_path),
                            check=True,
                            capture_output=True,
                        )
                        logger.debug(f"Disabled GPG signing in cloned repo: {dest_path}")
                    logger.info(f"Cloned {url} to {dest_path} (branch={branch})")
                except git.GitCommandError as e:
                    if "Remote branch" in str(e) and "not found" in str(e):
                        # Branch doesn't exist, clone without specifying branch
                        logger.debug(f"Branch {branch} not found, cloning default branch")
                        repo = git.Repo.clone_from(url, str(dest_path))
                        if disable_gpg_signing:
                            subprocess.run(
                                ["git", "config", "--local", "commit.gpgsign", "false"],
                                cwd=str(dest_path),
                                check=True,
                                capture_output=True,
                            )
                            subprocess.run(
                                ["git", "config", "--local", "gpg.x509.program", ""],
                                cwd=str(dest_path),
                                check=True,
                                capture_output=True,
                            )
                            subprocess.run(
                                ["git", "config", "--local", "gpg.program", ""],
                                cwd=str(dest_path),
                                check=True,
                                capture_output=True,
                            )
                            logger.debug(f"Disabled GPG signing in cloned repo: {dest_path}")
                        # Then checkout the branch if we can
                        try:
                            repo.git.checkout(branch)
                        except git.GitCommandError:
                            # Branch doesn't exist locally either, create it
                            repo.git.checkout("-b", branch)
                        logger.info(f"Cloned {url} to {dest_path} (created branch={branch})")
                    else:
                        raise
            else:
                repo = git.Repo.clone_from(url, str(dest_path))
                if disable_gpg_signing:
                    subprocess.run(
                        ["git", "config", "--local", "commit.gpgsign", "false"],
                        cwd=str(dest_path),
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "config", "--local", "gpg.x509.program", ""],
                        cwd=str(dest_path),
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        ["git", "config", "--local", "gpg.program", ""],
                        cwd=str(dest_path),
                        check=True,
                        capture_output=True,
                    )
                    logger.debug(f"Disabled GPG signing in cloned repo: {dest_path}")
                logger.info(f"Cloned {url} to {dest_path}")
        except git.GitCommandError as e:
            logger.error(f"Failed to clone from {url}: {e.stderr}")
            raise RuntimeError(f"Failed to clone from {url}: {e.stderr}") from e

    def git_add_all(self, repo_path: Path) -> None:
        """Stage all changes in a repository."""
        try:
            repo = git.Repo(repo_path)
            repo.git.add("-A")
            logger.debug(f"Staged all changes in {repo_path}")
        except (git.GitCommandError, git.InvalidGitRepositoryError) as e:
            logger.error(f"Failed to add files in {repo_path}: {e}")
            raise RuntimeError(f"Failed to add files: {e}") from e

    def git_is_dirty(self, repo_path: Path, untracked_files: bool = False) -> bool:
        """Check if repository has uncommitted changes."""
        repo = git.Repo(repo_path)
        return repo.is_dirty(untracked_files=untracked_files)

    def git_commit(self, repo_path: Path, message: str) -> str:
        """Create a commit and return its SHA."""
        try:
            logger.debug(f"commit: repo_path={repo_path}, message={message[:50]}")
            repo = git.Repo(repo_path)
            commit = repo.index.commit(message)
            logger.info(f"Created commit: repo_path={repo_path}, commit_sha={commit.hexsha}")
            return commit.hexsha
        except (git.GitCommandError, git.InvalidGitRepositoryError) as e:
            logger.error(f"Failed to commit at {repo_path}: {e}")
            raise RuntimeError(f"Failed to commit: {e}") from e

    def git_revert(self, repo_path: Path, ref: str, mainline: int | None = None) -> None:
        """Revert a commit."""
        try:
            repo = git.Repo(repo_path)
            if mainline is not None:
                repo.git.revert(ref, "-m", str(mainline), "--no-edit")
                logger.info(f"Reverted {ref} with mainline={mainline} in {repo_path}")
            else:
                repo.git.revert(ref, "--no-edit")
                logger.info(f"Reverted {ref} in {repo_path}")
        except git.GitCommandError as e:
            logger.error(f"Failed to revert {ref} in {repo_path}: {e.stderr}")
            raise RuntimeError(f"Failed to revert: {e.stderr}") from e

    # Helper methods for GitHub API
    def _get_current_commit_sha(self) -> str:
        """Get current commit SHA from git_repo.

        Raises:
            ValueError: If workspace not initialized
        """
        if self.git_repo is None:
            raise ValueError("Workspace not initialized - cannot get commit SHA")
        return self.git_repo.head.commit.hexsha

    def _get_current_branch_name(self) -> str:
        """Get current branch name from git_repo.

        Raises:
            ValueError: If workspace not initialized
        """
        if self.git_repo is None:
            raise ValueError("Workspace not initialized - cannot get branch name")
        return self.git_repo.active_branch.name

    def _find_pr_for_branch_internal(self, branch_name: str | None = None) -> PullRequest | None:
        """Find PR associated with branch (internal PyGithub PullRequest object).

        Args:
            branch_name: Branch name. If None, uses current branch.

        Returns:
            PullRequest object or None if not found
        """
        assert self.repo is not None, "GitHub repo required for PR operations"

        if branch_name is None:
            branch_name = self._get_current_branch_name()

        try:
            prs = self.repo.get_pulls(state="open", head=f"{self.github_owner}:{branch_name}")
            for pr in prs:
                return pr
            return None
        except GithubException as e:
            logger.error(f"Error finding PR for branch {branch_name}: {e}")
            return None

    # GitHub API methods
    def get_current_commit(self) -> dict[str, Any]:
        """Get current local commit details."""
        if self.git_repo is None:
            return CommitResponse(success=False, error="Workspace not initialized").to_dict()

        try:
            commit_sha = self._get_current_commit_sha()
            commit = self.git_repo.head.commit

            commit_info = CommitInfo(
                sha=commit_sha,
                short_sha=commit_sha[:7],
                message=str(commit.message).strip(),
                author=str(commit.author),
                date=commit.committed_datetime.isoformat(),
            )
            response = CommitResponse(success=True, commit=commit_info)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error getting current commit: {e}")
            response = CommitResponse(success=False, error=str(e))
            return response.to_dict()

    def get_current_branch(self) -> dict[str, Any]:
        """Get currently checked out branch."""
        try:
            branch_name = self._get_current_branch_name()
            response = BranchResponse(success=True, branch=branch_name)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error getting current branch: {e}")
            response = BranchResponse(success=False, error=str(e))
            return response.to_dict()

    def find_pr_for_branch(self, branch_name: str | None = None) -> dict[str, Any]:
        """Find PR associated with branch."""
        try:
            if branch_name is None:
                branch_name = self._get_current_branch_name()

            pr = self._find_pr_for_branch_internal(branch_name)

            if pr is None:
                response = PRResponse(
                    success=True,
                    pr=None,
                    message=f"No open PR found for branch: {branch_name}",
                )
                return response.to_dict()

            pr_info = PRInfo(
                number=pr.number,
                title=pr.title,
                url=pr.html_url,
                state=pr.state,
                head_sha=pr.head.sha,
                base_branch=pr.base.ref,
                head_branch=pr.head.ref,
                author=pr.user.login,
                created_at=pr.created_at.isoformat() if pr.created_at else None,
                updated_at=pr.updated_at.isoformat() if pr.updated_at else None,
            )
            response = PRResponse(success=True, pr=pr_info)
            return response.to_dict()
        except Exception as e:
            logger.error(f"Error finding PR for branch {branch_name}: {e}")
            response = PRResponse(success=False, error=str(e))
            return response.to_dict()

    def get_pr_comments(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve PR comments and threads."""
        try:
            # Find PR if not provided
            if pr_number is None:
                if branch_name is None:
                    branch_name = self._get_current_branch_name()

                pr = self._find_pr_for_branch_internal(branch_name)
                if pr is None:
                    return {
                        "success": False,
                        "error": f"No PR found for branch: {branch_name}",
                    }
                pr_number = pr.number
            else:
                assert self.repo is not None, "GitHub repo required for PR operations"
                pr = self.repo.get_pull(pr_number)

            # Get replied comment IDs if tracker is available
            replied_comment_ids = set()
            if self.comment_tracker is not None:
                replied_comment_ids = self.comment_tracker.get_replied_comments(
                    self.github_owner, self.github_repo, pr_number
                )

            # Get issue comments
            issue_comments = []
            for comment in pr.get_issue_comments():
                comment_dict = {
                    "id": comment.id,
                    "author": comment.user.login,
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                    "updated_at": comment.updated_at.isoformat(),
                    "url": comment.html_url,
                }
                if comment.id in replied_comment_ids:
                    comment_dict["already_replied"] = True
                issue_comments.append(comment_dict)

            # Get review comments
            review_comments = []
            for review_comment in pr.get_review_comments():
                comment_dict = {
                    "id": review_comment.id,
                    "author": review_comment.user.login,
                    "body": review_comment.body,
                    "path": review_comment.path,
                    "line": review_comment.line,
                    "created_at": review_comment.created_at.isoformat() if review_comment.created_at else None,
                    "updated_at": review_comment.updated_at.isoformat() if review_comment.updated_at else None,
                    "url": review_comment.html_url,
                    "in_reply_to_id": review_comment.in_reply_to_id,
                }
                if review_comment.id in replied_comment_ids:
                    comment_dict["already_replied"] = True
                review_comments.append(comment_dict)

            # Get reviews
            reviews = []
            for review in pr.get_reviews():
                reviews.append(
                    {
                        "id": review.id,
                        "author": review.user.login if review.user else None,
                        "state": review.state,
                        "body": review.body,
                        "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
                        "commit_id": review.commit_id,
                    }
                )

            return {
                "success": True,
                "pr_number": pr_number,
                "issue_comments": issue_comments,
                "review_comments": review_comments,
                "reviews": reviews,
                "total_comments": len(issue_comments) + len(review_comments),
            }

        except Exception as e:
            logger.error(f"Error getting PR comments: {e}")
            return {"success": False, "error": str(e)}

    def post_pr_reply(
        self,
        body: str,
        pr_number: int | None = None,
        branch_name: str | None = None,
        comment_id: int | None = None,
    ) -> dict[str, Any]:
        """Post replies to PR comments."""
        try:
            # Find PR if not provided
            if pr_number is None:
                if branch_name is None:
                    branch_name = self._get_current_branch_name()

                pr = self._find_pr_for_branch_internal(branch_name)
                if pr is None:
                    return {
                        "success": False,
                        "error": f"No PR found for branch: {branch_name}",
                    }
                pr_number = pr.number
            else:
                assert self.repo is not None, "GitHub repo required for PR operations"
                pr = self.repo.get_pull(pr_number)

            comment_data = None
            comment_type = None

            if comment_id is not None:
                # Reply to specific review comment
                try:
                    original_comment = pr.get_review_comment(comment_id)
                    review_reply = pr.create_review_comment(
                        body=body,
                        commit=original_comment.commit_id,
                        path=original_comment.path,
                        line=original_comment.line,
                        in_reply_to=comment_id,
                    )
                    comment_type = "review_comment_reply"
                    comment_data = {
                        "id": review_reply.id,
                        "type": comment_type,
                        "body": review_reply.body,
                        "author": review_reply.user.login,
                        "created_at": review_reply.created_at.isoformat() if review_reply.created_at else None,
                        "url": review_reply.html_url,
                    }

                    # Record successful reply
                    if self.comment_tracker is not None:
                        self.comment_tracker.record_reply(
                            self.github_owner,
                            self.github_repo,
                            pr_number,
                            comment_id,
                            "review",
                            review_reply.id,
                        )
                        # CRITICAL: Also mark the NEW reply comment as "already replied"
                        # so we don't try to respond to our own replies in the next iteration
                        self.comment_tracker.record_reply(
                            self.github_owner,
                            self.github_repo,
                            pr_number,
                            review_reply.id,  # Mark the NEW comment ID
                            "review",
                            None,  # No reply_comment_id for self-tracking
                        )

                except Exception:
                    # Fallback to issue comment
                    issue_reply = pr.create_issue_comment(body)
                    comment_type = "issue_comment"
                    comment_data = {
                        "id": issue_reply.id,
                        "type": comment_type,
                        "body": issue_reply.body,
                        "author": issue_reply.user.login,
                        "created_at": issue_reply.created_at.isoformat() if issue_reply.created_at else None,
                        "url": issue_reply.html_url,
                    }

                    # Record successful reply (fallback)
                    if self.comment_tracker is not None:
                        self.comment_tracker.record_reply(
                            self.github_owner,
                            self.github_repo,
                            pr_number,
                            comment_id,
                            "issue",
                            issue_reply.id,
                        )
                        # CRITICAL: Also mark the NEW reply comment as "already replied"
                        # so we don't try to respond to our own replies in the next iteration
                        self.comment_tracker.record_reply(
                            self.github_owner,
                            self.github_repo,
                            pr_number,
                            issue_reply.id,  # Mark the NEW comment ID
                            "issue",
                            None,  # No reply_comment_id for self-tracking
                        )
            else:
                # Post as issue comment
                issue_reply = pr.create_issue_comment(body)
                comment_type = "issue_comment"
                comment_data = {
                    "id": issue_reply.id,
                    "type": comment_type,
                    "body": issue_reply.body,
                    "author": issue_reply.user.login,
                    "created_at": issue_reply.created_at.isoformat() if issue_reply.created_at else None,
                    "url": issue_reply.html_url,
                }

            return {
                "success": True,
                "comment": comment_data,
            }

        except Exception as e:
            logger.error(f"Error posting PR reply: {e}")
            return {"success": False, "error": str(e)}

    def create_pr(
        self,
        title: str,
        body: str | None = None,
        branch_name: str | None = None,
        # TODO: Make base_branch configurable per repository (not all repos use "main")
        base_branch: str = "main",
    ) -> dict[str, Any]:
        """Create a pull request."""
        assert self.repo is not None, "GitHub repo required for PR operations"
        try:
            # Get branch name if not provided
            if branch_name is None:
                branch_name = self._get_current_branch_name()

            # Check if PR already exists
            existing_pr = self._find_pr_for_branch_internal(branch_name)
            if existing_pr:
                return {
                    "success": False,
                    "error": f"PR already exists for branch {branch_name}: #{existing_pr.number}",
                    "pr_number": existing_pr.number,
                    "pr_url": existing_pr.html_url,
                }

            # Create PR
            logger.info(f"Creating PR: {branch_name} -> {base_branch}")
            pr = self.repo.create_pull(
                title=title,
                body=body or "",
                head=branch_name,
                base=base_branch,
            )

            return {
                "success": True,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "pr_title": pr.title,
                "pr_state": pr.state,
            }

        except GithubException as e:
            logger.error(f"GitHub API error creating PR: {e}")
            return {"success": False, "error": f"GitHub API error: {e.data.get('message', str(e))}"}
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return {"success": False, "error": str(e)}

    def check_ci_build_and_test_errors(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Check CI build/test status for PR or commit."""
        assert self.repo is not None, "GitHub repo required for CI operations"
        try:
            # Determine commit SHA
            if commit_sha is None:
                if pr_number is None:
                    if branch_name is None:
                        branch_name = self._get_current_branch_name()

                    pr = self._find_pr_for_branch_internal(branch_name)
                    if pr is None:
                        commit_sha = self._get_current_commit_sha()
                    else:
                        commit_sha = pr.head.sha
                        pr_number = pr.number
                else:
                    pr = self.repo.get_pull(pr_number)
                    commit_sha = pr.head.sha

            # Get commit status
            commit = self.repo.get_commit(commit_sha)
            combined_status = commit.get_combined_status()

            # Get check runs
            check_runs = []
            try:
                check_runs_page = commit.get_check_runs()
                for check_run in check_runs_page:
                    check_runs.append(
                        {
                            "name": check_run.name,
                            "status": check_run.status,
                            "conclusion": check_run.conclusion,
                            "url": check_run.html_url,
                            "started_at": check_run.started_at.isoformat() if check_run.started_at else None,
                            "completed_at": check_run.completed_at.isoformat() if check_run.completed_at else None,
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not get check runs: {e}")

            # Get status checks
            statuses = []
            for status in combined_status.statuses:
                statuses.append(
                    {
                        "context": status.context,
                        "state": status.state,
                        "description": status.description,
                        "target_url": status.target_url,
                        "created_at": status.created_at.isoformat(),
                        "updated_at": status.updated_at.isoformat(),
                    }
                )

            # Determine overall status
            failed_checks = [cr for cr in check_runs if cr["conclusion"] == "failure"]
            failed_statuses = [s for s in statuses if s["state"] == "failure"]

            has_failures = len(failed_checks) > 0 or len(failed_statuses) > 0
            overall_state = combined_status.state

            return {
                "success": True,
                "commit_sha": commit_sha,
                "pr_number": pr_number,
                "overall_state": overall_state,
                "has_failures": has_failures,
                "check_runs": check_runs,
                "statuses": statuses,
                "failed_checks": failed_checks,
                "failed_statuses": failed_statuses,
                "total_checks": len(check_runs) + len(statuses),
            }

        except Exception as e:
            logger.error(f"Error checking CI status: {e}")
            return {"success": False, "error": str(e)}

    def check_ci_lint_errors(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Check CI lint errors for PR or commit."""
        try:
            # Get CI status first
            ci_result = self.check_ci_build_and_test_errors(pr_number, branch_name, commit_sha)

            if not ci_result["success"]:
                return ci_result

            # Filter for lint-related checks
            lint_keywords = [
                "lint",
                "style",
                "format",
                "ruff",
                "black",
                "eslint",
                "prettier",
            ]

            lint_check_runs = []
            for check_run in ci_result["check_runs"]:
                if any(keyword in check_run["name"].lower() for keyword in lint_keywords):
                    lint_check_runs.append(check_run)

            lint_statuses = []
            for status in ci_result["statuses"]:
                if any(keyword in status["context"].lower() for keyword in lint_keywords):
                    lint_statuses.append(status)

            failed_lint_checks = [cr for cr in lint_check_runs if cr["conclusion"] == "failure"]
            failed_lint_statuses = [s for s in lint_statuses if s["state"] == "failure"]

            has_lint_failures = len(failed_lint_checks) > 0 or len(failed_lint_statuses) > 0

            return {
                "success": True,
                "commit_sha": ci_result["commit_sha"],
                "pr_number": ci_result.get("pr_number"),
                "has_lint_failures": has_lint_failures,
                "lint_check_runs": lint_check_runs,
                "lint_statuses": lint_statuses,
                "failed_lint_checks": failed_lint_checks,
                "failed_lint_statuses": failed_lint_statuses,
                "total_lint_checks": len(lint_check_runs) + len(lint_statuses),
            }

        except Exception as e:
            logger.error(f"Error checking lint status: {e}")
            return {"success": False, "error": str(e)}

    def get_build_status(
        self,
        pr_number: int | None = None,
        branch_name: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Get comprehensive build status."""
        try:
            # Get CI status
            ci_result = self.check_ci_build_and_test_errors(pr_number, branch_name, commit_sha)

            if not ci_result["success"]:
                return ci_result

            # Get lint status
            lint_result = self.check_ci_lint_errors(pr_number, branch_name, commit_sha)

            # Combine results
            return {
                "success": True,
                "commit_sha": ci_result["commit_sha"],
                "pr_number": ci_result.get("pr_number"),
                "overall_state": ci_result["overall_state"],
                "summary": {
                    "has_failures": ci_result["has_failures"],
                    "has_lint_failures": lint_result.get("has_lint_failures", False),
                    "total_checks": ci_result["total_checks"],
                    "total_lint_checks": lint_result.get("total_lint_checks", 0),
                    "failed_checks_count": len(ci_result["failed_checks"]) + len(ci_result["failed_statuses"]),
                    "failed_lint_checks_count": len(lint_result.get("failed_lint_checks", []))
                    + len(lint_result.get("failed_lint_statuses", [])),
                },
                "ci_details": {
                    "check_runs": ci_result["check_runs"],
                    "statuses": ci_result["statuses"],
                    "failed_checks": ci_result["failed_checks"],
                    "failed_statuses": ci_result["failed_statuses"],
                },
                "lint_details": {
                    "lint_check_runs": lint_result.get("lint_check_runs", []),
                    "lint_statuses": lint_result.get("lint_statuses", []),
                    "failed_lint_checks": lint_result.get("failed_lint_checks", []),
                    "failed_lint_statuses": lint_result.get("failed_lint_statuses", []),
                },
            }

        except Exception as e:
            logger.error(f"Error getting build status: {e}")
            return {"success": False, "error": str(e)}

    def get_pr_body(self, pr_number: int) -> str | None:
        """Get the body text of a pull request."""
        assert self.repo is not None, "GitHub repo required for PR operations"
        try:
            pr = self.repo.get_pull(pr_number)
            return pr.body
        except GithubException as e:
            logger.error(f"Failed to get PR #{pr_number} body: {e}")
            raise RuntimeError(f"Failed to get PR body: {e}") from e
        except Exception as e:
            logger.error(f"Failed to get PR #{pr_number} body: {e}")
            raise RuntimeError(f"Failed to get PR body: {e}") from e

    def update_pr_body(self, pr_number: int, body: str) -> None:
        """Update the body text of a pull request."""
        assert self.repo is not None, "GitHub repo required for PR operations"
        try:
            pr = self.repo.get_pull(pr_number)
            pr.edit(body=body)
            logger.info(f"Updated PR #{pr_number} body")
        except GithubException as e:
            logger.error(f"Failed to update PR #{pr_number} body: {e}")
            raise RuntimeError(f"Failed to update PR body: {e}") from e
        except Exception as e:
            logger.error(f"Failed to update PR #{pr_number} body: {e}")
            raise RuntimeError(f"Failed to update PR body: {e}") from e

    def git_get_conflicted_files(self, repo_path: Path) -> list[str]:
        """Get list of files with merge conflicts.

        Args:
            repo_path: Path to repository

        Returns:
            List of file paths with conflicts
        """
        try:
            repo = git.Repo(repo_path)
            # git diff --name-only --diff-filter=U
            result = repo.git.diff("--name-only", "--diff-filter=U")
            if not result:
                return []
            return [f.strip() for f in result.split("\n") if f.strip()]
        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to get conflicted files: {e}") from e

    def git_checkout_ours(self, repo_path: Path, file_paths: list[str]) -> None:
        """Resolve conflicts by accepting 'ours' version.

        Args:
            repo_path: Path to repository
            file_paths: List of file paths to resolve
        """
        try:
            repo = git.Repo(repo_path)
            for file_path in file_paths:
                repo.git.checkout("--ours", file_path)
                repo.index.add([file_path])
        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to checkout --ours: {e}") from e

    def git_checkout_theirs(self, repo_path: Path, file_paths: list[str]) -> None:
        """Resolve conflicts by accepting 'theirs' version.

        Args:
            repo_path: Path to repository
            file_paths: List of file paths to resolve
        """
        try:
            repo = git.Repo(repo_path)
            for file_path in file_paths:
                repo.git.checkout("--theirs", file_path)
                repo.index.add([file_path])
        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to checkout --theirs: {e}") from e

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
        try:
            repo = git.Repo(repo_path)
            return str(repo.git.show(commit_sha))
        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to show commit {commit_sha}: {e}") from e

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
        try:
            repo = git.Repo(repo_path)
            # Use triple-dot syntax to diff from merge-base to head_ref
            return str(repo.git.diff(f"{base_ref}...{head_ref}"))
        except (git.InvalidGitRepositoryError, git.GitCommandError) as e:
            raise RuntimeError(f"Failed to diff {base_ref}...{head_ref}: {e}") from e
