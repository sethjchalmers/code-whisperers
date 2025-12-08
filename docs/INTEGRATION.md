# 🔌 Integration Guide

This guide covers all the ways to integrate Code Whisperers into your development workflow.

## Table of Contents

- [Quick Install](#quick-install)
- [Docker](#docker)
- [Dev Container (VS Code)](#dev-container-vs-code)
- [VS Code Tasks](#vs-code-tasks)
- [GitHub Action](#github-action)
- [Git Hooks](#git-hooks)
- [Environment Variables](#environment-variables)

---

## Quick Install

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.sh | bash
```

### Windows PowerShell

```powershell
iwr -useb https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.ps1 | iex
```

### Manual Installation

```bash
git clone https://github.com/sethjchalmers/code-whisperers.git
cd code-whisperers
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .
```

After installation:

```bash
# Set your GitHub token for free AI access
export GITHUB_TOKEN=ghp_your_token_here  # or $env:GITHUB_TOKEN on Windows

# Run a review
code-whisperers review --diff HEAD~1
```

---

## Docker

### Build the Image

```bash
docker build -t code-whisperers .
```

### Run a Review

```bash
# Review current directory against main branch
docker run --rm \
  -v $(pwd):/repo \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  code-whisperers review --base main

# Review last commit
docker run --rm \
  -v $(pwd):/repo \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  code-whisperers review --diff HEAD~1

# Review specific files
docker run --rm \
  -v $(pwd):/repo \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  code-whisperers review --files /repo/src/main.py
```

### Docker Compose

```bash
# Use the included docker-compose.yml
docker-compose run --rm review

# Or with custom diff range
docker-compose run --rm review review --diff HEAD~3..HEAD
```

### Using Ollama Locally (Air-Gapped)

```bash
# Start Ollama service
docker-compose --profile local-llm up -d ollama

# Pull a model
docker exec code-whisperers-ollama-1 ollama pull llama3.1

# Run review with local LLM
docker-compose run --rm -e LLM_PROVIDER=ollama review
```

---

## Dev Container (VS Code)

The repository includes a complete dev container configuration.

### One-Click Setup

1. Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
2. Clone the repository
3. Open in VS Code
4. Click "Reopen in Container" when prompted

### What's Included

- Python 3.12 environment
- All dependencies pre-installed
- Git and GitHub CLI
- VS Code extensions:
  - Python
  - Pylance
  - Black formatter
  - Ruff linter
  - YAML support

### Environment Variables

The dev container passes through your local `GITHUB_TOKEN`:

```bash
# Set before opening VS Code
export GITHUB_TOKEN=ghp_your_token_here
```

---

## VS Code Tasks

Copy `.vscode/tasks.json` to your project for integrated review commands.

### Available Tasks

| Task                              | Description                       | Shortcut |
| --------------------------------- | --------------------------------- | -------- |
| 🎭 Code Review: Last Commit       | Review changes in HEAD~1          | -        |
| 🎭 Code Review: vs Main           | Review all changes vs main branch | -        |
| 🎭 Code Review: Current File      | Review the currently open file    | -        |
| 🎭 Code Review: Custom Diff Range | Prompts for a git range           | -        |
| 🔍 Validate: Current File         | Syntax validation without AI      | -        |
| 🧪 Run Tests                      | Run pytest suite                  | -        |
| ⚙️ Show Config                    | Display current configuration     | -        |

### Running Tasks

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Tasks: Run Task"
3. Select the desired task

### Custom Keyboard Shortcuts

Add to your `keybindings.json`:

```json
{
  "key": "ctrl+shift+r",
  "command": "workbench.action.tasks.runTask",
  "args": "🎭 Code Review: Last Commit"
}
```

---

## GitHub Action

Add automated code reviews to your CI/CD pipeline.

### Basic Setup

Create `.github/workflows/code-review.yml`:

```yaml
name: 🎭 Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Code Whisperers
        run: pip install git+https://github.com/sethjchalmers/code-whisperers.git

      - name: Run Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m cli.main review \
            --base ${{ github.event.pull_request.base.sha }} \
            --head ${{ github.event.pull_request.head.sha }} \
            --output review-report.md

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: code-review
          path: review-report.md
```

### With PR Comments

See `scripts/github-action-example.yml` for a complete example that:

- Reviews PR changes automatically
- Posts findings as PR comments
- Updates existing comments on new pushes
- Uploads reports as artifacts

### Required Permissions

```yaml
permissions:
  contents: read
  pull-requests: write # For posting comments
```

---

## Git Hooks

### Pre-Push Hook

Prevent pushing code that fails review:

```bash
# Install the hook
cp scripts/git-hooks/pre-push .git/hooks/
chmod +x .git/hooks/pre-push
```

The hook will:

1. Run a code review on commits being pushed
2. Block the push if critical issues are found
3. Allow bypassing with `git push --no-verify`

### Pre-Commit Hook (Optional)

For faster feedback during development:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Only review staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM)

if [ -n "$STAGED_FILES" ]; then
    python -m cli.main review --files $STAGED_FILES --format text
fi
```

### Using with pre-commit Framework

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: code-whisperers
        name: Code Whisperers Review
        entry: python -m cli.main review --files
        language: system
        types: [python, terraform, yaml]
        pass_filenames: true
```

---

## Environment Variables

### Required

| Variable       | Description                                      | Example    |
| -------------- | ------------------------------------------------ | ---------- |
| `GITHUB_TOKEN` | GitHub personal access token (for GitHub Models) | `ghp_xxxx` |

### Optional

| Variable           | Description                                       | Default                  |
| ------------------ | ------------------------------------------------- | ------------------------ |
| `LLM_PROVIDER`     | AI provider (`github-models`, `ollama`, `openai`) | `github-models`          |
| `LLM_MODEL`        | Model to use                                      | `gpt-4o`                 |
| `LLM_TEMPERATURE`  | Response creativity (0.0-1.0)                     | `0.1`                    |
| `OLLAMA_ENDPOINT`  | Ollama server URL                                 | `http://localhost:11434` |
| `MAX_FILE_SIZE_KB` | Skip files larger than this                       | `500`                    |
| `GIT_BASE_BRANCH`  | Default branch for comparisons                    | `main`                   |

### .env File

Create a `.env` file in your project root:

```env
GITHUB_TOKEN=ghp_your_token_here
LLM_PROVIDER=github-models
LLM_MODEL=gpt-4o
LLM_TEMPERATURE=0.1
```

---

## CLI Reference

```bash
# Review commands
python -m cli.main review --diff HEAD~1          # Last commit
python -m cli.main review --base main            # Changes vs main
python -m cli.main review --files src/*.py       # Specific files
python -m cli.main review --agents python aws    # Specific agents

# Output options
python -m cli.main review --output report.md     # Save to file
python -m cli.main review --format json          # JSON output
python -m cli.main review --format text          # Plain text

# Performance options
python -m cli.main review --sequential           # One agent at a time
python -m cli.main review --no-repo-context      # Skip context files

# Other commands
python -m cli.main validate --files *.py         # Syntax validation
python -m cli.main config --show                 # Show configuration
python -m cli.main --help                        # Full help
```

---

## Troubleshooting

### "GITHUB_TOKEN not set"

```bash
# Linux/macOS
export GITHUB_TOKEN=ghp_your_token_here

# Windows PowerShell
$env:GITHUB_TOKEN = "ghp_your_token_here"
```

### "Rate limit exceeded"

GitHub Models has rate limits. Options:

1. Wait and retry
2. Switch to Ollama for local unlimited usage
3. Use a different model (`--model gpt-4o-mini`)

### "Docker: permission denied"

```bash
# Add your user to the docker group
sudo usermod -aG docker $USER
# Then log out and back in
```

### "Module not found"

Ensure you're in the virtual environment:

```bash
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1
```

---

## Getting Help

- 📖 [README](README.md) - Overview and quick start
- 🐛 [Issues](https://github.com/sethjchalmers/code-whisperers/issues) - Bug reports
- 💡 [Discussions](https://github.com/sethjchalmers/code-whisperers/discussions) - Questions and ideas
