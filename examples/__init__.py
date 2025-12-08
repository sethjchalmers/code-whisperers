"""
Examples module for the agent-to-agent pipeline.

This module contains examples showing:
- How to configure different LLM providers and models
- How to create custom agents for any task
- How to use the agent factory pattern

Quick Start:
    from examples.model_config import configure_ollama
    configure_ollama()  # Free, local model

    # Then run your review
    python -m cli.main review --base main

Custom Agents:
    from examples.custom_agents import AgentFactory

    agent = AgentFactory.create_generic_agent(
        name="my_expert",
        description="My Custom Expert",
        system_prompt="You are an expert in...",
        file_patterns=["*.py"],
    )
"""

from .custom_agents import (
    AgentFactory,
    APIDesignAgent,
    DatabaseAgent,
    DocumentationAgent,
    TypeScriptAgent,
)

__all__ = [
    "AgentFactory",
    "DocumentationAgent",
    "APIDesignAgent",
    "DatabaseAgent",
    "TypeScriptAgent",
]
