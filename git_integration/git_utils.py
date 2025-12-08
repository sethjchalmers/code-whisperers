"""
Git integration utilities for collecting changed files and diffs.
"""

import logging
import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from config.settings import get_settings

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of file change in git."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"
    UNTRACKED = "untracked"


@dataclass
class FileChange:
    """Represents a changed file in git."""

    file_path: str
    change_type: ChangeType
    old_path: str | None = None  # For renamed/copied files
    additions: int = 0
    deletions: int = 0

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type.value,
            "old_path": self.old_path,
            "additions": self.additions,
            "deletions": self.deletions,
        }


class GitIntegration:
    """
    Git integration for collecting changed files and context.

    Features:
    - Get changed files between branches/commits
    - Get file diffs
    - Collect file contents
    - Parse commit information
    """

    def __init__(self, repo_path: str | None = None):
        self.settings = get_settings()
        self.repo_path = Path(repo_path or self.settings.git_repo_path).resolve()
        self.logger = logging.getLogger("git_integration")

        if not self._is_git_repo():
            self.logger.warning(f"{self.repo_path} is not a git repository")

    def _is_git_repo(self) -> bool:
        """Check if the path is a git repository."""
        git_dir = self.repo_path / ".git"
        return git_dir.exists()

    def _run_git(self, *args: str) -> tuple[str, str, int]:
        """Run a git command and return stdout, stderr, and return code."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            self.logger.error(f"Git command timed out: git {' '.join(args)}")
            return "", "Command timed out", 1
        except Exception as e:
            self.logger.error(f"Git command failed: {e}")
            return "", str(e), 1

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        stdout, _, code = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        if code == 0:
            return stdout.strip()
        return "unknown"

    def get_changed_files(
        self,
        base_ref: str | None = None,
        head_ref: str | None = None,
        include_untracked: bool = True,
    ) -> list[FileChange]:
        """
        Get list of changed files.

        Args:
            base_ref: Base reference (branch, commit, tag). Defaults to base branch.
            head_ref: Head reference. Defaults to HEAD.
            include_untracked: Include untracked files.

        Returns:
            List of FileChange objects.
        """
        changes = []

        # Default references
        base = base_ref or self.settings.git_base_branch
        head = head_ref or "HEAD"

        # Get changes between refs
        stdout, stderr, code = self._run_git(
            "diff", "--name-status", "--diff-filter=ACDMRT", f"{base}...{head}"
        )

        if code != 0:
            # Try without the ... syntax (for uncommitted changes)
            stdout, stderr, code = self._run_git("diff", "--name-status", "--cached")

        if code == 0:
            for line in stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 2:
                    status = parts[0][0]  # First character of status
                    file_path = parts[-1]  # Last part is the file path
                    old_path = parts[1] if len(parts) > 2 else None

                    change_type = self._parse_status(status)
                    changes.append(
                        FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            old_path=old_path,
                        )
                    )

        # Get staged changes
        stdout, _, code = self._run_git("diff", "--name-status", "--cached")
        if code == 0:
            for line in stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    file_path = parts[-1]
                    # Avoid duplicates
                    if not any(c.file_path == file_path for c in changes):
                        changes.append(
                            FileChange(
                                file_path=file_path,
                                change_type=self._parse_status(parts[0][0]),
                            )
                        )

        # Get unstaged changes
        stdout, _, code = self._run_git("diff", "--name-status")
        if code == 0:
            for line in stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    file_path = parts[-1]
                    if not any(c.file_path == file_path for c in changes):
                        changes.append(
                            FileChange(
                                file_path=file_path,
                                change_type=self._parse_status(parts[0][0]),
                            )
                        )

        # Include untracked files
        if include_untracked:
            stdout, _, code = self._run_git("ls-files", "--others", "--exclude-standard")
            if code == 0:
                for line in stdout.strip().split("\n"):
                    if line and not any(c.file_path == line for c in changes):
                        changes.append(
                            FileChange(
                                file_path=line,
                                change_type=ChangeType.UNTRACKED,
                            )
                        )

        return changes

    def _parse_status(self, status: str) -> ChangeType:
        """Parse git status character to ChangeType."""
        status_map = {
            "A": ChangeType.ADDED,
            "M": ChangeType.MODIFIED,
            "D": ChangeType.DELETED,
            "R": ChangeType.RENAMED,
            "C": ChangeType.COPIED,
        }
        return status_map.get(status, ChangeType.MODIFIED)

    def get_diff(
        self,
        base_ref: str | None = None,
        head_ref: str | None = None,
        file_path: str | None = None,
    ) -> str:
        """
        Get diff output.

        Args:
            base_ref: Base reference
            head_ref: Head reference
            file_path: Specific file to diff (optional)

        Returns:
            Diff string
        """
        base = base_ref or self.settings.git_base_branch
        head = head_ref or "HEAD"

        args = ["diff", f"{base}...{head}"]
        if file_path:
            args.extend(["--", file_path])

        stdout, stderr, code = self._run_git(*args)

        if code != 0:
            # Try getting working directory diff
            args = ["diff"]
            if file_path:
                args.extend(["--", file_path])
            stdout, stderr, code = self._run_git(*args)

        return stdout if code == 0 else ""

    def get_file_content(self, file_path: str, ref: str | None = None) -> str | None:
        """
        Get content of a file at a specific ref or from working directory.

        Args:
            file_path: Path to file relative to repo root
            ref: Git reference (branch, commit, tag). If None, read from disk.

        Returns:
            File content as string, or None if not found
        """
        if ref:
            stdout, stderr, code = self._run_git("show", f"{ref}:{file_path}")
            if code == 0:
                return stdout
            return None

        # Read from disk
        full_path = self.repo_path / file_path
        try:
            if full_path.exists():
                return full_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")

        return None

    def collect_changed_files_content(
        self,
        base_ref: str | None = None,
        head_ref: str | None = None,
        include_untracked: bool = True,
        max_file_size_kb: int | None = None,
    ) -> dict[str, str]:
        """
        Collect content of all changed files.

        Args:
            base_ref: Base reference
            head_ref: Head reference
            include_untracked: Include untracked files
            max_file_size_kb: Skip files larger than this (KB)

        Returns:
            Dictionary mapping file paths to contents
        """
        max_size = (max_file_size_kb or self.settings.max_file_size_kb) * 1024

        changes = self.get_changed_files(base_ref, head_ref, include_untracked)
        files = {}

        for change in changes:
            if change.change_type == ChangeType.DELETED:
                continue  # Skip deleted files

            content = self.get_file_content(change.file_path)

            if content is None:
                continue

            # Check file size
            if len(content) > max_size:
                self.logger.warning(
                    f"Skipping {change.file_path}: exceeds max size "
                    f"({len(content)} > {max_size} bytes)"
                )
                continue

            files[change.file_path] = content

        return files

    def collect_files_by_paths(
        self, file_paths: list[str], max_file_size_kb: int | None = None
    ) -> dict[str, str]:
        """
        Collect content of specific files.

        Args:
            file_paths: List of file paths to collect
            max_file_size_kb: Skip files larger than this (KB)

        Returns:
            Dictionary mapping file paths to contents
        """
        max_size = (max_file_size_kb or self.settings.max_file_size_kb) * 1024
        files = {}

        for file_path in file_paths:
            content = self.get_file_content(file_path)

            if content is None:
                self.logger.warning(f"File not found: {file_path}")
                continue

            if len(content) > max_size:
                self.logger.warning(f"Skipping {file_path}: exceeds max size")
                continue

            files[file_path] = content

        return files

    def get_commit_info(self, ref: str = "HEAD") -> dict:
        """Get information about a commit."""
        # Get commit hash
        stdout, _, code = self._run_git("rev-parse", ref)
        commit_hash = stdout.strip() if code == 0 else ""

        # Get commit message
        stdout, _, code = self._run_git("log", "-1", "--format=%B", ref)
        message = stdout.strip() if code == 0 else ""

        # Get author
        stdout, _, code = self._run_git("log", "-1", "--format=%an <%ae>", ref)
        author = stdout.strip() if code == 0 else ""

        # Get date
        stdout, _, code = self._run_git("log", "-1", "--format=%ci", ref)
        date = stdout.strip() if code == 0 else ""

        return {
            "hash": commit_hash,
            "message": message,
            "author": author,
            "date": date,
        }

    def collect_context(
        self,
        base_ref: str | None = None,
        head_ref: str | None = None,
        include_repo_context: bool = True,
    ) -> dict:
        """
        Collect full context for review.

        Args:
            base_ref: Base git reference
            head_ref: Head git reference
            include_repo_context: Include standard repo files (.gitignore, etc.)

        Returns:
            Dictionary with files, diff, commit info, and repo context
        """
        context = {
            "git_diff": self.get_diff(base_ref, head_ref),
            "commit_info": self.get_commit_info(head_ref or "HEAD"),
            "current_branch": self.get_current_branch(),
            "base_ref": base_ref or self.settings.git_base_branch,
            "head_ref": head_ref or "HEAD",
        }

        # Include standard repository context files
        if include_repo_context:
            repo_context = self.collect_repo_context_files()
            if repo_context:
                context["repo_context_files"] = repo_context
                # Create a summary for easy reference
                context["repo_context_summary"] = (
                    f"Repository includes: {', '.join(sorted(repo_context.keys()))}"
                )

        return context

    def collect_codebase_files(
        self,
        patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_files: int = 100,
        max_file_size_kb: int | None = None,
    ) -> dict[str, str]:
        """
        Collect files from the entire codebase matching patterns.

        Args:
            patterns: Glob patterns to include (e.g., ["*.py", "*.tf"])
            exclude_patterns: Patterns to exclude (e.g., ["*test*", "*.lock"])
            max_files: Maximum number of files to collect
            max_file_size_kb: Skip files larger than this

        Returns:
            Dictionary mapping file paths to contents
        """
        from fnmatch import fnmatch

        max_size = (max_file_size_kb or self.settings.max_file_size_kb) * 1024

        # Default patterns if none specified
        patterns = patterns or ["*.py", "*.tf", "*.yaml", "*.yml", "*.json", "Jenkinsfile*"]
        exclude_patterns = exclude_patterns or [
            "*test*",
            "*.lock",
            "node_modules/*",
            ".git/*",
            "__pycache__/*",
            "*.pyc",
            ".terraform/*",
        ]

        # Get all tracked files
        stdout, _, code = self._run_git("ls-files")
        if code != 0:
            return {}

        all_files = stdout.strip().split("\n")
        files = {}
        count = 0

        for file_path in all_files:
            if count >= max_files:
                break

            # Check if matches any pattern
            matches = any(
                fnmatch(file_path, p) or fnmatch(os.path.basename(file_path), p) for p in patterns
            )
            if not matches:
                continue

            # Check if excluded
            excluded = any(fnmatch(file_path, p) for p in exclude_patterns)
            if excluded:
                continue

            content = self.get_file_content(file_path)
            if content is None:
                continue

            if len(content) > max_size:
                continue

            files[file_path] = content
            count += 1

        return files

    def collect_repo_context_files(self) -> dict[str, str]:
        """
        Collect standard repository context files that help understand the project.

        These files provide important context for code reviews:
        - .gitignore: What files are excluded from version control
        - .pre-commit-config.yaml: Pre-commit hooks and checks
        - pyproject.toml: Python project configuration
        - setup.py, setup.cfg: Python package setup
        - requirements.txt: Python dependencies
        - package.json: Node.js dependencies
        - Makefile: Build commands
        - README.md, CONTRIBUTING.md: Documentation
        - .env.example: Environment variable templates
        - Dockerfile, docker-compose.yml: Container configuration
        - .github/workflows/*: CI/CD configuration

        Returns:
            Dictionary mapping file paths to contents
        """
        context_file_patterns = [
            # Git and version control
            ".gitignore",
            ".gitattributes",
            # Pre-commit and linting
            ".pre-commit-config.yaml",
            ".pre-commit-config.yml",
            ".eslintrc*",
            ".prettierrc*",
            ".flake8",
            "pyproject.toml",
            "setup.cfg",
            ".editorconfig",
            "tox.ini",
            "mypy.ini",
            ".pylintrc",
            "ruff.toml",
            # Dependencies
            "requirements.txt",
            "requirements*.txt",
            "setup.py",
            "package.json",
            "Pipfile",
            "poetry.lock",
            "Cargo.toml",
            "go.mod",
            # Documentation
            "README.md",
            "README.rst",
            "CONTRIBUTING.md",
            "CHANGELOG.md",
            "CODE_OF_CONDUCT.md",
            "LICENSE",
            "LICENSE.md",
            # Environment and config
            ".env.example",
            ".env.sample",
            ".env.template",
            "config.yaml",
            "config.yml",
            # Build and CI
            "Makefile",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Jenkinsfile",
            ".travis.yml",
            "azure-pipelines.yml",
            "bitbucket-pipelines.yml",
            ".circleci/config.yml",
            # Terraform/IaC
            "terraform.tfvars",
            "*.tfvars",
            "terragrunt.hcl",
            # Kubernetes
            "Chart.yaml",
            "values.yaml",
        ]

        # Also check for files in common directories
        context_directories = [
            ".github/workflows",
            ".github",
        ]

        context_files = {}
        max_size = self.settings.max_file_size_kb * 1024

        # Get all tracked files
        stdout, _, code = self._run_git("ls-files")
        if code != 0:
            # Fallback: read from disk
            all_files = []
            for item in self.repo_path.rglob("*"):
                if item.is_file() and ".git" not in str(item):
                    all_files.append(str(item.relative_to(self.repo_path)))
        else:
            all_files = stdout.strip().split("\n")

        from fnmatch import fnmatch

        for file_path in all_files:
            if not file_path:
                continue

            # Check if it matches any context file pattern
            file_name = os.path.basename(file_path)
            matches_pattern = any(
                fnmatch(file_name, pattern) or fnmatch(file_path, pattern)
                for pattern in context_file_patterns
            )

            # Check if it's in a context directory
            in_context_dir = any(
                file_path.startswith(d) or file_path.startswith(d.replace("/", os.sep))
                for d in context_directories
            )

            if matches_pattern or in_context_dir:
                content = self.get_file_content(file_path)
                if content and len(content) <= max_size:
                    context_files[file_path] = content

        return context_files
