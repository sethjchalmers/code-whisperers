# Changelog - The Code Whisperers

All notable changes to your favorite judgmental AI squad.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-12-07

### Added

- **7 Expert Agents** for comprehensive code review:
  - Terraform Expert - IaC best practices, security, compliance
  - GitOps Expert - Kubernetes, Helm, ArgoCD patterns
  - Jenkins Expert - CI/CD pipeline optimization
  - Python Expert - Code quality, typing, testing
  - Security Expert - OWASP vulnerabilities, secrets detection
  - Cost Optimization Expert - Cloud cost analysis
  - Clean Code Expert - Software craftsmanship principles

- **Multiple AI Provider Support**:
  - GitHub Models API (free tier with GPT-4o, Llama, Mistral)
  - Ollama for fully local/private reviews
  - GitHub Copilot proxy integration
  - OpenAI and Azure OpenAI support

- **Git Integration**:
  - Review staged/unstaged changes
  - Collect repository context automatically
  - Smart file filtering by agent expertise

- **CLI Interface**:
  - `review` command for code reviews
  - `validate` command for syntax checking
  - `agents` command to list available agents
  - Multiple output formats (terminal, markdown, JSON)

- **Code Quality**:
  - Pre-commit hooks (black, isort, ruff, mypy, bandit)
  - Comprehensive test suite (48 tests)
  - Type annotations throughout

- **Documentation**:
  - Comprehensive README with examples
  - Contributing guidelines
  - API documentation

### Security

- No hardcoded credentials - all API keys via environment variables
- Support for fully local AI with Ollama
- Secrets detection in reviewed code

---

## Version History

- `1.0.0` - Initial public release
