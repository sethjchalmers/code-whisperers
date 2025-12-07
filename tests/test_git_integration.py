"""
Tests for the git integration module.
"""

import os
import tempfile
import pytest
from pathlib import Path
from git_integration import GitIntegration, ChangeType


class TestGitIntegration:
    """Test the GitIntegration class."""
    
    @pytest.fixture
    def temp_git_repo(self):
        """Create a temporary git repository for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize git repo
            os.system(f'cd "{tmpdir}" && git init')
            os.system(f'cd "{tmpdir}" && git config user.email "test@test.com"')
            os.system(f'cd "{tmpdir}" && git config user.name "Test User"')
            
            # Create initial commit
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("print('hello')")
            os.system(f'cd "{tmpdir}" && git add . && git commit -m "Initial commit"')
            
            yield tmpdir
    
    def test_is_git_repo(self, temp_git_repo):
        """Test detecting a git repository."""
        git = GitIntegration(temp_git_repo)
        assert git._is_git_repo() is True
    
    def test_not_git_repo(self):
        """Test detecting a non-git directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            git = GitIntegration(tmpdir)
            assert git._is_git_repo() is False
    
    def test_get_current_branch(self, temp_git_repo):
        """Test getting current branch name."""
        git = GitIntegration(temp_git_repo)
        branch = git.get_current_branch()
        assert branch in ["main", "master"]  # Depends on git version
    
    def test_get_file_content(self, temp_git_repo):
        """Test reading file content."""
        git = GitIntegration(temp_git_repo)
        content = git.get_file_content("test.py")
        assert content == "print('hello')"
    
    def test_get_file_content_not_found(self, temp_git_repo):
        """Test reading non-existent file."""
        git = GitIntegration(temp_git_repo)
        content = git.get_file_content("nonexistent.py")
        assert content is None
    
    def test_collect_files_by_paths(self, temp_git_repo):
        """Test collecting specific files."""
        git = GitIntegration(temp_git_repo)
        files = git.collect_files_by_paths(["test.py"])
        assert "test.py" in files
        assert files["test.py"] == "print('hello')"
    
    def test_get_changed_files_untracked(self, temp_git_repo):
        """Test detecting untracked files."""
        git = GitIntegration(temp_git_repo)
        
        # Create an untracked file
        new_file = Path(temp_git_repo) / "new.py"
        new_file.write_text("# new file")
        
        changes = git.get_changed_files(include_untracked=True)
        untracked = [c for c in changes if c.change_type == ChangeType.UNTRACKED]
        assert any(c.file_path == "new.py" for c in untracked)
    
    def test_get_commit_info(self, temp_git_repo):
        """Test getting commit information."""
        git = GitIntegration(temp_git_repo)
        info = git.get_commit_info("HEAD")
        
        assert "hash" in info
        assert len(info["hash"]) == 40  # Full SHA
        assert "Initial commit" in info["message"]
        assert "Test User" in info["author"]
    
    def test_collect_context(self, temp_git_repo):
        """Test collecting full context."""
        git = GitIntegration(temp_git_repo)
        context = git.collect_context()
        
        assert "commit_info" in context
        assert "current_branch" in context
        assert context["current_branch"] in ["main", "master"]


class TestFileChange:
    """Test the FileChange dataclass."""
    
    def test_to_dict(self):
        """Test converting FileChange to dictionary."""
        from git_integration import FileChange
        
        change = FileChange(
            file_path="test.py",
            change_type=ChangeType.MODIFIED,
            additions=10,
            deletions=5,
        )
        
        d = change.to_dict()
        assert d["file_path"] == "test.py"
        assert d["change_type"] == "modified"
        assert d["additions"] == 10
        assert d["deletions"] == 5
