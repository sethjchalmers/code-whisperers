"""
Quick Start: Model Configuration Examples

This file shows the simplest ways to configure different LLM models.
"""

import os

# =============================================================================
# OPTION 1: OpenAI (GPT-4)
# =============================================================================
# Cost: ~$0.01-0.03 per 1K tokens
# Best for: High-quality analysis, complex reasoning


def configure_openai():
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "sk-your-key-here"
    os.environ["LLM_MODEL"] = "gpt-4-turbo-preview"  # or gpt-4, gpt-4o
    os.environ["LLM_TEMPERATURE"] = "0.1"


# =============================================================================
# OPTION 2: Anthropic (Claude 4.5 Sonnet)
# =============================================================================
# Cost: ~$0.003-0.015 per 1K tokens
# Best for: Nuanced analysis, following complex instructions


def configure_claude():
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-your-key-here"
    os.environ["LLM_MODEL"] = "claude-sonnet-4-20250514"  # Claude 4.5 Sonnet
    # Other options:
    #   "claude-3-opus-20240229"    - Most capable
    #   "claude-3-haiku-20240307"   - Fastest
    os.environ["LLM_TEMPERATURE"] = "0.1"


# =============================================================================
# OPTION 3: Ollama (Local - FREE!)
# =============================================================================
# Cost: FREE (runs on your machine)
# Best for: Privacy, no API costs, offline usage
#
# Setup:
#   1. Install Ollama: https://ollama.ai
#   2. Pull a model: ollama pull llama3.1
#   3. Ollama runs automatically on localhost:11434


def configure_ollama():
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["LLM_MODEL"] = "llama3.1"
    # Other good models for code:
    #   "codellama"        - Code-specialized
    #   "deepseek-coder"   - Strong code understanding
    #   "mistral"          - Fast and capable
    os.environ["LLM_TEMPERATURE"] = "0.1"


# =============================================================================
# OPTION 4: Azure OpenAI
# =============================================================================
# Cost: Varies by deployment
# Best for: Enterprise, compliance requirements


def configure_azure():
    os.environ["LLM_PROVIDER"] = "azure"
    os.environ["AZURE_OPENAI_API_KEY"] = "your-azure-key"
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://your-resource.openai.azure.com/"
    os.environ["LLM_MODEL"] = "your-deployment-name"
    os.environ["LLM_TEMPERATURE"] = "0.1"


# =============================================================================
# OPTION 5: GitHub Copilot (if you have subscription)
# =============================================================================
# Cost: Included with Copilot subscription
# Best for: If you already pay for Copilot
#
# Setup:
#   1. Have VS Code open with Copilot extension
#   2. Run: python copilot_proxy.py
#   3. Then run your review


def configure_copilot():
    os.environ["LLM_PROVIDER"] = "copilot"
    os.environ["LLM_MODEL"] = "gpt-4"  # Copilot uses GPT-4 under the hood


# =============================================================================
# USAGE
# =============================================================================

if __name__ == "__main__":
    # Pick one and configure it
    # configure_openai()
    # configure_claude()
    configure_ollama()  # Free option!
    # configure_azure()
    # configure_copilot()

    # Now run the review

    # This will use whatever provider you configured above
    print(f"Using provider: {os.environ.get('LLM_PROVIDER')}")
    print(f"Using model: {os.environ.get('LLM_MODEL')}")

    # Example: Run a review
    # asyncio.run(main(["review", "--base", "main"]))


# =============================================================================
# .env FILE ALTERNATIVE
# =============================================================================
"""
Instead of setting environment variables in code, create a .env file:

# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxx
LLM_MODEL=claude-sonnet-4-20250514
LLM_TEMPERATURE=0.1

Then just run:
    python -m cli.main review --base main
"""


# =============================================================================
# POWERSHELL COMMANDS
# =============================================================================
"""
# For OpenAI:
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "sk-xxx"
$env:LLM_MODEL = "gpt-4-turbo-preview"

# For Claude:
$env:LLM_PROVIDER = "anthropic"
$env:ANTHROPIC_API_KEY = "sk-ant-xxx"
$env:LLM_MODEL = "claude-sonnet-4-20250514"

# For Ollama (free!):
$env:LLM_PROVIDER = "ollama"
$env:LLM_MODEL = "llama3.1"

# Then run:
python -m cli.main review --base main
"""
