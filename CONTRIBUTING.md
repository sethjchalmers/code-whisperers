# Contributing to The Code Whisperers

Want to join the squad? We're always looking for new opinionated agents. This document explains how to contribute without getting roasted by our own tools.

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/sethjchalmers/code-whisperers.git
   cd agent-to-agent
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If exists, or:
   pip install pre-commit pytest pytest-asyncio pytest-cov
   ```

4. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Verify setup**
   ```bash
   pytest tests/ -v
   pre-commit run --all-files
   ```

## 📝 How to Contribute

### Reporting Bugs

- Check existing issues first to avoid duplicates
- Use the bug report template
- Include:
  - Python version
  - Operating system
  - Steps to reproduce
  - Expected vs actual behavior
  - Error messages/stack traces

### Suggesting Features

- Open an issue with the feature request template
- Describe the use case and expected behavior
- Consider if it fits the project's scope

### Submitting Changes

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   # or: git checkout -b fix/bug-description
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow existing code style
   - Add tests for new functionality

3. **Run quality checks**

   ```bash
   # Format code
   black .
   isort .

   # Lint
   ruff check .

   # Type check
   mypy .

   # Run all pre-commit hooks
   pre-commit run --all-files
   ```

4. **Run tests**

   ```bash
   pytest tests/ -v
   ```

5. **Commit with conventional commits**

   ```bash
   git commit -m "feat: add new terraform validation rule"
   git commit -m "fix: handle empty file list gracefully"
   git commit -m "docs: update API documentation"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Code Style

### Python Style

- **Formatter**: Black (line length 88)
- **Import sorting**: isort (black profile)
- **Linting**: Ruff
- **Type hints**: Required for all public functions

### Example

```python
"""Module docstring explaining purpose."""

from typing import Any

from agents.base_agent import BaseAgent


def process_files(
    files: dict[str, str],
    context: dict[str, Any] | None = None,
) -> list[str]:
    """
    Process files for review.

    Args:
        files: Dictionary mapping file paths to contents.
        context: Optional context information.

    Returns:
        List of processed file paths.

    Raises:
        ValueError: If files dict is empty.
    """
    if not files:
        raise ValueError("Files dictionary cannot be empty")

    return list(files.keys())
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, no code change
- `refactor:` - Code change without feature/fix
- `test:` - Adding/updating tests
- `chore:` - Maintenance tasks

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_agents.py -v

# Specific test
pytest tests/test_agents.py::TestAgentResponse -v

# With coverage
pytest tests/ --cov=agents --cov=orchestration --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use pytest fixtures for common setup
- Test both success and error cases

```python
import pytest
from agents import PythonExpertAgent


class TestPythonAgent:
    """Tests for Python expert agent."""

    def test_matches_python_files(self) -> None:
        """Agent should match .py files."""
        agent = PythonExpertAgent()
        assert agent.matches_file("app.py")
        assert not agent.matches_file("app.js")

    @pytest.mark.asyncio
    async def test_review_returns_response(self) -> None:
        """Review should return AgentResponse."""
        agent = PythonExpertAgent()
        # ... test implementation
```

## 🏗️ Adding a New Agent

1. **Create the agent file** (`agents/my_agent.py`):

   ```python
   from agents.base_agent import BaseAgent
   from config.agent_config import AgentConfig

   MY_AGENT_CONFIG = AgentConfig(
       name="my_expert",
       description="My Expert Description",
       file_patterns=["*.ext"],
       priority=2,
       system_prompt="...",
   )

   class MyExpertAgent(BaseAgent):
       def __init__(self) -> None:
           super().__init__(MY_AGENT_CONFIG)

       def get_expert_context(self) -> str:
           return "Context about expertise..."
   ```

2. **Export from `agents/__init__.py`**

3. **Add to `agents/expert_agents.py`** `create_all_agents()`

4. **Add tests** in `tests/`

5. **Update documentation**

## 📚 Documentation

- Update README.md for user-facing changes
- Add docstrings to all public functions/classes
- Update type hints
- Add examples for new features

## ❓ Questions?

- Open a GitHub Discussion for questions
- Check existing issues and discussions first
- Be respectful and constructive

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.
