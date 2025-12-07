# Agent-to-Agent Code Review Pipeline

A multi-agent AI system for comprehensive code reviews, featuring specialized expert agents for Terraform/IaC, GitOps, Jenkins, Python, Security, and Cost Optimization.

## Features

- 🤖 **Multi-Agent Architecture**: Specialized AI agents for different domains
- 🔄 **LangGraph Orchestration**: Coordinate multiple agents efficiently
- 🔍 **Git Integration**: Review changed files automatically
- ✅ **Validation & Testing**: Built-in code validation and test execution
- 📊 **Comprehensive Reports**: Detailed markdown or JSON reports
- 🔐 **Security Analysis**: Detect vulnerabilities and secrets
- 💰 **Cost Optimization**: Cloud cost recommendations
- 🎯 **Hallucination Detection**: Verify AI-generated code accuracy

## Expert Agents

| Agent | Expertise |
|-------|-----------|
| **Terraform Expert** | IaC best practices, security, cost optimization |
| **GitOps Expert** | Kubernetes, Helm, ArgoCD, Flux configurations |
| **Jenkins Expert** | CI/CD pipelines, Groovy, shared libraries |
| **Python Expert** | Code quality, testing, security |
| **Security Expert** | OWASP, secrets, vulnerabilities |
| **Cost Expert** | Cloud cost optimization, FinOps |

## Installation

### Prerequisites

- Python 3.10+
- Git
- API key for OpenAI, Anthropic, or Azure OpenAI

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/agent-to-agent.git
cd agent-to-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Usage

### Command Line Interface

```bash
# Review changed files (compares current branch to main)
python -m cli.main review --base main

# Review specific files
python -m cli.main review --files src/main.py terraform/main.tf

# Review with git diff range
python -m cli.main review --diff HEAD~5..HEAD

# Include full codebase context
python -m cli.main review --base main --include-codebase

# Run specific agents only
python -m cli.main review --agents terraform security python

# Enable cross-validation between agents
python -m cli.main review --cross-validate

# Output to file
python -m cli.main review --output report.md --format markdown

# Validate files (no AI, just syntax/structure)
python -m cli.main validate --files *.tf *.py

# Run tests
python -m cli.main test --base main

# Show configuration
python -m cli.main config --show
```

### Python API

```python
import asyncio
from orchestration import ReviewPipeline
from git_integration import GitIntegration

async def main():
    # Initialize git integration
    git = GitIntegration("/path/to/repo")
    
    # Collect changed files
    files = git.collect_changed_files_content(base_ref="main")
    context = git.collect_context(base_ref="main")
    
    # Run review pipeline
    pipeline = ReviewPipeline(parallel=True)
    result = await pipeline.run(files, context)
    
    # Process results
    print(f"Status: {result.status.value}")
    print(f"Total findings: {len(result.consolidated_findings)}")
    
    for finding in result.consolidated_findings:
        print(f"[{finding.severity.value}] {finding.title}")
        print(f"  {finding.description}")
        if finding.suggested_fix:
            print(f"  Fix: {finding.suggested_fix}")

asyncio.run(main())
```

### Using the Coordinator

```python
from orchestration import AgentCoordinator

async def coordinated_review():
    coordinator = AgentCoordinator()
    
    files = {"main.tf": "...", "app.py": "..."}
    result = await coordinator.coordinate_review(
        files=files,
        context={"git_diff": "..."},
        cross_validate=True  # Agents validate each other's findings
    )
    
    print(result["summary"])
    for escalation in result["escalations"]:
        print(f"⚠️ {escalation['type']}: {escalation['recommended_action']}")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (openai/anthropic/azure) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `LLM_MODEL` | Model to use | `gpt-4-turbo-preview` |
| `LLM_TEMPERATURE` | Temperature for responses | `0.1` |
| `GIT_BASE_BRANCH` | Default base branch | `main` |
| `MAX_FILE_SIZE_KB` | Max file size to review | `500` |
| `PARALLEL_AGENTS` | Run agents in parallel | `true` |

### Custom Agent Configuration

```python
from config.agent_config import AgentConfig
from agents.base_agent import BaseAgent

# Create a custom agent
custom_config = AgentConfig(
    name="custom_expert",
    description="Custom Expert Agent",
    file_patterns=["*.custom"],
    priority=1,
    system_prompt="You are an expert in custom files..."
)

class CustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(custom_config)
    
    def get_expert_context(self) -> str:
        return "Additional context for custom files..."
```

## Output Formats

### Markdown Report

```markdown
# Code Review Report

**Status:** ⛔ BLOCKING ISSUES FOUND

## Summary
- Total Findings: 12
- Agents Executed: 6

### Findings by Severity
- 🔴 Critical: 1
- 🟠 High: 3
- 🟡 Medium: 5
- 🔵 Low: 3

---

## Terraform Expert

### 🔴 CRITICAL Severity

#### Hardcoded AWS Access Key
**Location:** `terraform/main.tf` (line 15)

AWS access key is hardcoded in the configuration...

**Suggested Fix:**
```hcl
variable "aws_access_key" {
  type      = string
  sensitive = true
}
```
```

### JSON Output

```json
{
  "status": "completed",
  "agent_responses": [...],
  "consolidated_findings": [
    {
      "category": "security",
      "severity": "critical",
      "title": "Hardcoded AWS Access Key",
      "description": "...",
      "file_path": "terraform/main.tf",
      "line_number": 15,
      "suggested_fix": "..."
    }
  ],
  "summary": "...",
  "total_execution_time": 45.2
}
```

## Architecture

```
agent-to-agent/
├── agents/                 # Expert agent implementations
│   ├── base_agent.py      # Abstract base class
│   └── expert_agents.py   # Specialized agents
├── cli/                   # Command-line interface
│   └── main.py
├── config/                # Configuration management
│   ├── settings.py       # Global settings
│   └── agent_config.py   # Agent configurations
├── git_integration/       # Git utilities
│   └── git_utils.py
├── orchestration/         # Pipeline orchestration
│   ├── pipeline.py       # LangGraph pipeline
│   └── coordinator.py    # Agent coordinator
├── testing/              # Validation and testing
│   ├── test_runner.py
│   └── validators.py
└── reports/              # Generated reports
```

## Workflow

1. **File Collection**: Git integration collects changed files and diff
2. **Validation**: Syntax and structure validation (optional)
3. **Agent Dispatch**: Files routed to relevant expert agents
4. **Parallel Review**: Agents analyze files concurrently
5. **Cross-Validation**: Agents validate critical findings (optional)
6. **Consolidation**: Findings merged and deduplicated
7. **Report Generation**: Markdown/JSON report created

## Best Practices

### For Terraform Reviews
- Ensure Terraform is initialized (`terraform init`)
- Include `.tfvars` files if needed for context

### For Kubernetes Reviews
- Include related manifests (Deployments + Services)
- Consider using `--include-codebase` for full context

### For Python Reviews
- Include `requirements.txt` or `pyproject.toml`
- Include test files for complete analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
