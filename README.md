# 🎭 The Code Whisperers

### _Your Personal Army of Mass Code Reviewers_

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Mypy: strict-ish](https://img.shields.io/badge/mypy-strict--ish-blue)](http://mypy-lang.org/)

> _"Why have one code reviewer when you can have seven AI experts arguing about your semicolons?"_

Tired of begging colleagues for code reviews? Sick of waiting three days for a "LGTM"? **The Code Whisperers** assembles a crack team of AI specialists who'll dissect your code with the enthusiasm of a caffeinated senior developer at 2 AM.

Each agent brings their own brand of _constructive criticism_ (read: they have opinions and they're not afraid to share them).

## 🦸 Meet The Squad

| Agent                    | Expertise                                                  |
| ------------------------ | ---------------------------------------------------------- |
| 🏗️ **Terraform Expert**  | IaC best practices, security, compliance, module design    |
| 🚀 **GitOps Expert**     | Kubernetes, Helm, ArgoCD, Flux, deployment patterns        |
| 🔧 **Jenkins Expert**    | CI/CD pipelines, Groovy, shared libraries, security        |
| 🐍 **Python Expert**     | Pythonic code, type hints, testing, framework patterns     |
| 🔒 **Security Expert**   | OWASP Top 10, secrets detection, vulnerability analysis    |
| 💰 **Cost Expert**       | Cloud cost optimization, resource right-sizing, FinOps     |
| 📚 **Clean Code Expert** | Software craftsmanship, SOLID principles, DRY, code smells |
| ☁️ **AWS Expert**        | CloudFormation, IAM, CDK, SAM, Well-Architected Framework  |

## ✨ What You Get

- **8 specialized reviewers** who never call in sick, never need coffee breaks, and won't passive-aggressively Slack you about your code style
- **Free AI options** - Because your code deserves judgment that doesn't cost $0.03 per snarky comment
- **Git-aware reviews** - They know what you changed and they're ready to talk about it
- **Actually useful output** - Markdown reports, JSON for the robots, or just straight to your terminal

## 🚀 Quick Start (60 Seconds to Your First Roast)

```bash
# Summon the squad
git clone https://github.com/sethjchalmers/code-whisperers.git
cd code-whisperers

# Prepare the ritual circle (virtual environment)
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# Install their dependencies (they're high maintenance)
pip install -r requirements.txt

# Get a free GitHub token (no special permissions needed)
# https://github.com/settings/tokens
export GITHUB_TOKEN=ghp_your_token_here

# Unleash them on your code
python -m cli.main review --staged
```

Watch as eight AI experts simultaneously tell you everything wrong with your code! _Fun!_

## 🆓 Running the Squad (For Free!)

### Option 1: GitHub Models API (The Recommended Free Lunch)

GitHub gives you **free access** to GPT-4o, Llama, and Mistral. Yes, _free_. No, it's not a trap.

```bash
# Get token: github.com/settings/tokens (no scopes needed)
export GITHUB_TOKEN=ghp_your_token_here

# Let them loose
python -m cli.main review --provider github-models
```

**Model Menu:**

- `gpt-4o` - The overachiever (default)
- `gpt-4o-mini` - Faster, still judges you
- `meta-llama-3.1-70b-instruct` - Open source and opinionated
- `mistral-large-2411` - French, sophisticated, will critique your architecture

### Option 2: Ollama (The Paranoid's Choice)

Run everything locally. Your code never leaves your machine. Perfect for when you're working on _totally-not-skynet_.

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1

# Summon local spirits
python -m cli.main review --provider ollama --model llama3.1
```

### Option 3: GitHub Copilot (If You're Already Paying)

Got a Copilot subscription? Put it to work:

```bash
# Terminal 1: Start the séance
python copilot_proxy.py

# Terminal 2: Channel the reviews
python -m cli.main review --provider copilot
```

## 📖 Battle Commands

```bash
# The basics
python -m cli.main review                    # Review staged changes (the coward's choice)
python -m cli.main review --files *.py       # Review specific files (targeted strike)
python -m cli.main review --files "**/*.tf"  # Review all Terraform (Terry's favorite)

# Speed vs thoroughness
python -m cli.main review --parallel         # All agents at once (chaos mode)
python -m cli.main review --no-repo-context  # Skip context (speed run)

# Output options
python -m cli.main review --output roast.md  # Save the burns for later

# The full arsenal
python -m cli.main agents                    # See who's on duty
python -m cli.main validate --files *.py     # Syntax check (no AI required)
```

## 🎯 Example Output

```
🎭 The Code Whisperers - Code Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Files to review: 3
🦸 Agents: 7

Running terraform_expert... ✓ (2.3s)
Running security_expert... ✓ (3.1s)
Running python_expert... ✓ (2.8s)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Review Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Findings: 8
  🔴 Critical: 1
  🟠 High: 2
  🟡 Medium: 3
  🔵 Low: 2

🔴 [CRITICAL] Hardcoded AWS Credentials
   File: main.tf:15
   Agent: security_expert

   AWS access key hardcoded in provider configuration.
   This could lead to credential exposure if committed.

   Fix: Use environment variables or AWS credentials file
```

## 🧩 Recruiting New Agents

Want an agent for your specific needs? Create your own specialist:

```python
# agents/react_rachel.py
from agents.base_agent import BaseAgent
from config.agent_config import AgentConfig

REACT_CONFIG = AgentConfig(
    name="react_rachel",
    description="React Expert with Opinions™",
    file_patterns=["*.jsx", "*.tsx"],
    priority=2,
    system_prompt="""You are React Rachel, a frontend expert who has mass
    reviewed on too many useEffect dependency arrays to count.

    You care deeply about:
    1. Hook rules (they're not suggestions!)
    2. Performance (useMemo exists for a reason)
    3. Accessibility (not everyone uses a mouse, Karen)
    4. State management (Redux trauma is real)

    Be helpful but don't sugarcoat it. Return findings as JSON.""",
)

class ReactRachel(BaseAgent):
    def __init__(self):
        super().__init__(REACT_CONFIG)

    def get_expert_context(self) -> str:
        return "I've mass reviewed more React components than I've had hot dinners."
```

## ⚙️ Configuration (Teaching Them Manners)

### Environment Variables

| Variable           | What It Does                            | Default                  |
| ------------------ | --------------------------------------- | ------------------------ |
| `GITHUB_TOKEN`     | Your ticket to free AI                  | -                        |
| `LLM_PROVIDER`     | Which AI backend to bother              | `github-models`          |
| `LLM_MODEL`        | Specifically which AI to bother         | `gpt-4o`                 |
| `LLM_TEMPERATURE`  | How spicy their responses get (0.0-1.0) | `0.1`                    |
| `OLLAMA_ENDPOINT`  | Where your local Ollama lives           | `http://localhost:11434` |
| `MAX_FILE_SIZE_KB` | "That file's too big, I'm not reading"  | `500`                    |

### .env File

```env
LLM_PROVIDER=github-models
LLM_MODEL=gpt-4o
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
LLM_TEMPERATURE=0.1  # Keep them professional (mostly)
```

## 🏗️ How The Magic Happens

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Your Code  │────▶│  Git Picks   │────▶│  Agents Fight   │
│  (a mess)   │     │  The Victims │     │  Over Who       │
└─────────────┘     └──────────────┘     │  Reviews What   │
                                         └────────┬────────┘
                    ┌─────────────────────────────┘
                    ▼
        ┌───────────────────────┐
        │  The Squad Reviews    │
        │  ┌─────┐ ┌─────┐     │
        │  │🏗️   │ │ 🔒  │ ... │
        │  └─────┘ └─────┘     │
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Findings Compiled    │
        │  Ego Bruised          │
        │  Code Improved        │
        └───────────────────────┘
```

## 🧪 Testing (Yes, We Test Our Code Review Tool)

```bash
# Run the full test suite
pytest tests/ -v

# With coverage (we're thorough like that)
pytest tests/ --cov=agents --cov=orchestration --cov-report=html

# 49 tests. All passing. We're not hypocrites.
```

## 🐳 Integration Options (Get Them Into Your Workflow)

### Dev Container (VS Code)

Open in a pre-configured development environment with one click:

```bash
# Clone and open in VS Code
git clone https://github.com/sethjchalmers/code-whisperers.git
code code-whisperers
# VS Code will prompt: "Reopen in Container" - click it!
```

### Docker (Review Any Repo)

```bash
# Build the image
docker build -t code-whisperers .

# Review your current directory
docker run -v $(pwd):/repo -e GITHUB_TOKEN=$GITHUB_TOKEN \
    code-whisperers review /repo --provider github-models

# Or use docker-compose
docker-compose run --rm review
```

### Quick Install Script

```bash
# Linux/macOS
curl -fsSL https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.sh | bash

# Windows PowerShell
iwr -useb https://raw.githubusercontent.com/sethjchalmers/code-whisperers/master/scripts/install.ps1 | iex

# Then use anywhere:
code-whisperers review --staged
```

### GitHub Action (Auto-Review PRs)

Add `.github/workflows/code-review.yml` to your repo - see `scripts/github-action-example.yml` for a complete template that:

- Reviews every PR automatically
- Posts findings as PR comments
- Runs on push to main/master

### Git Hook (Pre-Push Review)

```bash
# Install the hook
cp scripts/git-hooks/pre-push .git/hooks/
chmod +x .git/hooks/pre-push

# Now every push gets reviewed first!
```

### VS Code Tasks

Copy `.vscode/tasks.json` to your project for quick access:

- `Ctrl+Shift+P` → "Tasks: Run Task"
- 🎭 Code Review: Staged Changes
- 🎭 Code Review: Current File
- 🎭 Code Review: Last Commit

## 🤝 Join The Team

Found a bug? Want to add an agent? Have opinions about our opinions?

1. Fork it
2. Branch it (`git checkout -b feature/agent-who-judges-css`)
3. Test it (`pytest tests/ -v`)
4. Lint it (`pre-commit run --all-files`)
5. Ship it (`git commit -m 'feat: add CSS Critic agent'`)
6. PR it

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full onboarding process.

## 📄 License

MIT - Do whatever you want, just don't blame us when Security Sam roasts your production credentials.

## 🙏 Standing On The Shoulders Of Giants

- [LangChain](https://github.com/langchain-ai/langchain) - Making AI orchestration almost easy
- [GitHub Models](https://github.com/marketplace/models) - Free AI for the masses
- Uncle Bob, Martin Fowler, and every developer who ever said "we should probably review this"

---

<p align="center">
  <i>Built with ❤️, mass reviewed by The Code Whisperers themselves</i>
  <br><br>
  <b>Remember: They're not mean, they're <i>thorough</i>.</b>
</p>
