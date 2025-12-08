"""
Examples: Creating Custom Agents and Configuring Models

This file demonstrates:
1. How to configure different LLM providers/models
2. How to create custom agents for any task
3. How to use the agent factory pattern
"""

import asyncio

from agents.base_agent import BaseAgent
from config.agent_config import AgentConfig

# =============================================================================
# PART 1: MODEL CONFIGURATION EXAMPLES
# =============================================================================

# Example 1: Using Claude 4.5 Sonnet (Anthropic)
# Set these environment variables:
#   LLM_PROVIDER=anthropic
#   ANTHROPIC_API_KEY=sk-ant-xxx...
#   LLM_MODEL=claude-sonnet-4-20250514

CLAUDE_SONNET_CONFIG = AgentConfig(
    name="claude_sonnet_agent",
    description="Agent using Claude 4.5 Sonnet",
    file_patterns=["*.py", "*.js", "*.ts"],
    priority=1,
    model_override="claude-sonnet-4-20250514",  # Specific model for this agent
    temperature_override=0.2,  # Slightly creative
    system_prompt="You are a helpful code review assistant powered by Claude.",
)


# Example 2: Using GPT-4 Turbo (OpenAI)
# Set these environment variables:
#   LLM_PROVIDER=openai
#   OPENAI_API_KEY=sk-xxx...
#   LLM_MODEL=gpt-4-turbo-preview

GPT4_TURBO_CONFIG = AgentConfig(
    name="gpt4_turbo_agent",
    description="Agent using GPT-4 Turbo",
    file_patterns=["*.py"],
    priority=1,
    model_override="gpt-4-turbo-preview",
    temperature_override=0.1,
    system_prompt="You are a precise code review assistant.",
)


# Example 3: Using local Ollama models (free, no API key)
# Set these environment variables:
#   LLM_PROVIDER=ollama
#   LLM_MODEL=llama3.1  (or codellama, deepseek-coder, etc.)

OLLAMA_CODELLAMA_CONFIG = AgentConfig(
    name="codellama_agent",
    description="Agent using local CodeLlama model",
    file_patterns=["*.py", "*.js"],
    priority=1,
    model_override="codellama",  # Local model
    temperature_override=0.1,
    system_prompt="You are a code-focused AI assistant.",
)


# Example 4: Mixed model setup - different agents use different models
# This is useful when you want specialized models for different tasks

FAST_TRIAGE_CONFIG = AgentConfig(
    name="fast_triage",
    description="Quick triage using fast model",
    file_patterns=["*"],
    priority=1,
    model_override="gpt-3.5-turbo",  # Fast and cheap for initial triage
    temperature_override=0.0,
    system_prompt="Quickly identify critical issues in the code.",
)

DEEP_ANALYSIS_CONFIG = AgentConfig(
    name="deep_analysis",
    description="Deep analysis using powerful model",
    file_patterns=["*"],
    priority=2,
    model_override="claude-sonnet-4-20250514",  # Powerful model for deep analysis
    temperature_override=0.3,
    system_prompt="Perform thorough, nuanced code analysis.",
)


# =============================================================================
# PART 2: CUSTOM AGENT CREATION
# =============================================================================


class DocumentationAgent(BaseAgent):
    """
    Example: Custom agent for reviewing documentation quality.

    This agent reviews markdown files, docstrings, and comments
    for clarity, completeness, and accuracy.
    """

    def __init__(self, model_override: str | None = None):
        config = AgentConfig(
            name="documentation_expert",
            description="Documentation and API Reference Expert",
            file_patterns=["*.md", "*.rst", "*.txt", "README*", "CHANGELOG*", "docs/*"],
            priority=3,
            model_override=model_override,
            system_prompt="""You are a technical documentation expert.

Your responsibilities:
1. **Clarity**: Ensure documentation is clear and understandable
2. **Completeness**: Check for missing sections (installation, usage, API docs)
3. **Accuracy**: Verify code examples actually work
4. **Structure**: Evaluate organization and navigation
5. **Accessibility**: Check for proper headings, alt text, formatting

Provide feedback as structured findings with specific suggestions.""",
        )
        super().__init__(config)

    def get_expert_context(self) -> str:
        return """
        Documentation Review Context:
        - Check README has: description, installation, usage, contributing, license
        - Verify API documentation matches actual code
        - Ensure code examples are syntactically correct
        - Check for broken links or outdated references
        """


class APIDesignAgent(BaseAgent):
    """
    Example: Custom agent for reviewing API design patterns.

    Reviews REST APIs, GraphQL schemas, and RPC definitions.
    """

    def __init__(self, model_override: str | None = None):
        config = AgentConfig(
            name="api_design_expert",
            description="API Design and REST/GraphQL Expert",
            file_patterns=[
                "*.graphql",
                "*.gql",  # GraphQL
                "**/routes/*",
                "**/api/*",  # API routes
                "**/controllers/*",  # Controllers
                "openapi.yaml",
                "openapi.json",
                "swagger.*",  # OpenAPI
                "*.proto",  # Protocol Buffers
            ],
            priority=2,
            model_override=model_override,
            system_prompt="""You are an API design expert.

Your responsibilities:
1. **RESTful Design**: Proper HTTP methods, status codes, resource naming
2. **Versioning**: API versioning strategy
3. **Error Handling**: Consistent error response formats
4. **Pagination**: Proper pagination for list endpoints
5. **Security**: Authentication, rate limiting, input validation
6. **Documentation**: OpenAPI/Swagger completeness

Provide specific, actionable feedback on API design.""",
        )
        super().__init__(config)


class DatabaseAgent(BaseAgent):
    """
    Example: Custom agent for reviewing database schemas and queries.
    """

    def __init__(self, model_override: str | None = None):
        config = AgentConfig(
            name="database_expert",
            description="Database Schema and Query Expert",
            file_patterns=[
                "*.sql",
                "**/migrations/*",
                "**/models/*",
                "*.prisma",  # Prisma schema
                "schema.graphql",
            ],
            priority=2,
            model_override=model_override,
            system_prompt="""You are a database expert specializing in SQL and ORM design.

Your responsibilities:
1. **Schema Design**: Normalization, relationships, constraints
2. **Query Performance**: Index usage, N+1 queries, query optimization
3. **Security**: SQL injection prevention, access control
4. **Migrations**: Safe migration practices, rollback strategies
5. **Data Integrity**: Foreign keys, unique constraints, validation

Focus on performance and data integrity issues.""",
        )
        super().__init__(config)


class TypeScriptAgent(BaseAgent):
    """
    Example: Custom agent for TypeScript-specific review.
    """

    def __init__(self, model_override: str | None = None):
        config = AgentConfig(
            name="typescript_expert",
            description="TypeScript and React Expert",
            file_patterns=["*.ts", "*.tsx", "*.d.ts", "tsconfig.json"],
            priority=1,
            model_override=model_override,
            system_prompt="""You are a TypeScript and React expert.

Your responsibilities:
1. **Type Safety**: Proper type usage, avoid 'any', use generics
2. **React Patterns**: Hooks best practices, component design
3. **Performance**: Memoization, bundle size, lazy loading
4. **Testing**: Component testing, type testing
5. **Modern Features**: Proper use of latest TypeScript features

Focus on type safety and React best practices.""",
        )
        super().__init__(config)


# =============================================================================
# PART 3: AGENT FACTORY PATTERN
# =============================================================================


class AgentFactory:
    """
    Factory for creating agents dynamically.

    Use this to create agents with custom configurations at runtime,
    or to register and instantiate agents by name.
    """

    # Registry of agent classes
    _registry: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, agent_class: type) -> None:
        """Register an agent class with a name."""
        cls._registry[name] = agent_class

    @classmethod
    def create(cls, name: str, **kwargs: object) -> BaseAgent:
        """Create an agent instance by name."""
        if name not in cls._registry:
            raise ValueError(f"Unknown agent: {name}. Available: {list(cls._registry.keys())}")
        agent = cls._registry[name](**kwargs)
        assert isinstance(agent, BaseAgent)
        return agent

    @classmethod
    def create_from_config(cls, config: AgentConfig) -> BaseAgent:
        """
        Create a generic agent from an AgentConfig.

        This is useful for creating agents dynamically without
        defining a new class for each one.
        """

        class DynamicAgent(BaseAgent):
            def __init__(self, cfg: AgentConfig):
                super().__init__(cfg)

            def get_expert_context(self) -> str:
                return f"Expert context for {config.name}"

        return DynamicAgent(config)

    @classmethod
    def create_generic_agent(
        cls,
        name: str,
        description: str,
        system_prompt: str,
        file_patterns: list[str],
        model: str | None = None,
        temperature: float = 0.1,
    ) -> BaseAgent:
        """
        Convenience method to create a generic agent without defining a class.

        Example:
            agent = AgentFactory.create_generic_agent(
                name="rust_expert",
                description="Rust Code Review Expert",
                system_prompt="You are a Rust expert focusing on memory safety...",
                file_patterns=["*.rs", "Cargo.toml"],
                model="claude-sonnet-4-20250514",
            )
        """
        config = AgentConfig(
            name=name,
            description=description,
            system_prompt=system_prompt,
            file_patterns=file_patterns,
            model_override=model,
            temperature_override=temperature,
        )
        return cls.create_from_config(config)


# Register built-in custom agents
AgentFactory.register("documentation", DocumentationAgent)
AgentFactory.register("api_design", APIDesignAgent)
AgentFactory.register("database", DatabaseAgent)
AgentFactory.register("typescript", TypeScriptAgent)


# =============================================================================
# PART 4: USAGE EXAMPLES
# =============================================================================


async def example_custom_agents():
    """Example: Using custom agents."""

    # Method 1: Direct instantiation
    doc_agent = DocumentationAgent(model_override="claude-sonnet-4-20250514")

    # Method 2: Using the factory with registered agents
    ts_agent = AgentFactory.create("typescript", model_override="gpt-4-turbo-preview")

    # Method 3: Creating a completely custom agent dynamically
    rust_agent = AgentFactory.create_generic_agent(
        name="rust_expert",
        description="Rust Memory Safety Expert",
        system_prompt="""You are a Rust expert focusing on:
        1. Memory safety and ownership
        2. Lifetime annotations
        3. Error handling with Result/Option
        4. Async/await patterns
        5. Unsafe code review""",
        file_patterns=["*.rs", "Cargo.toml", "Cargo.lock"],
        model="claude-sonnet-4-20250514",
    )

    # Example files to review
    files = {
        "README.md": "# My Project\nA sample project.",
        "src/main.rs": 'fn main() { println!("Hello"); }',
        "src/app.tsx": "export const App = () => <div>Hello</div>;",
    }

    # Run reviews (only on matching files)
    print("=== Documentation Review ===")
    doc_result = await doc_agent.review(files)
    print(f"Files reviewed: {doc_result.files_reviewed}")
    print(f"Findings: {len(doc_result.findings)}")

    print("\n=== TypeScript Review ===")
    ts_result = await ts_agent.review(files)
    print(f"Files reviewed: {ts_result.files_reviewed}")

    print("\n=== Rust Review ===")
    rust_result = await rust_agent.review(files)
    print(f"Files reviewed: {rust_result.files_reviewed}")


async def example_mixed_models():
    """Example: Using different models for different agents."""

    # Create agents with different models for different purposes

    # Fast triage with GPT-3.5 (cheap, quick)
    triage_agent = AgentFactory.create_generic_agent(
        name="triage",
        description="Quick Issue Triage",
        system_prompt="Quickly identify critical security or syntax issues.",
        file_patterns=["*"],
        model="gpt-3.5-turbo",
        temperature=0.0,
    )

    # Deep analysis with Claude Sonnet (thorough, nuanced)
    deep_agent = AgentFactory.create_generic_agent(
        name="deep_analysis",
        description="Thorough Code Analysis",
        system_prompt="Perform comprehensive analysis of architecture and design.",
        file_patterns=["*.py", "*.ts"],
        model="claude-sonnet-4-20250514",
        temperature=0.2,
    )

    # Local analysis with Ollama (free, private)
    local_agent = AgentFactory.create_generic_agent(
        name="local_review",
        description="Local Privacy-Focused Review",
        system_prompt="Review code for basic issues. Keep analysis local.",
        file_patterns=["*"],
        model="llama3.1",  # Requires LLM_PROVIDER=ollama
        temperature=0.1,
    )

    print("Created agents with mixed models:")
    print(f"  - Triage: {triage_agent.config.model_override}")
    print(f"  - Deep: {deep_agent.config.model_override}")
    print(f"  - Local: {local_agent.config.model_override}")


# =============================================================================
# PART 5: CONFIGURATION QUICK REFERENCE
# =============================================================================

CONFIGURATION_REFERENCE = """
# =============================================================================
# MODEL CONFIGURATION QUICK REFERENCE
# =============================================================================

## OpenAI Models
   Set: LLM_PROVIDER=openai, OPENAI_API_KEY=sk-xxx

   Models:
   - gpt-4-turbo-preview     # Most capable, best for complex analysis
   - gpt-4                   # Stable, good balance
   - gpt-3.5-turbo          # Fast and cheap for simple tasks
   - gpt-4o                  # Multimodal, good for mixed content

## Anthropic (Claude) Models
   Set: LLM_PROVIDER=anthropic, ANTHROPIC_API_KEY=sk-ant-xxx

   Models:
   - claude-sonnet-4-20250514  # Claude 4.5 Sonnet - balanced
   - claude-3-opus-20240229      # Most capable Claude 3
   - claude-3-sonnet-20240229    # Good balance of speed/quality
   - claude-3-haiku-20240307     # Fastest Claude 3

## Azure OpenAI
   Set: LLM_PROVIDER=azure, AZURE_OPENAI_API_KEY=xxx,
        AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/

   Models: Use your deployed model names

## Ollama (Local, Free)
   Set: LLM_PROVIDER=ollama
   Install: https://ollama.ai

   Models (run: ollama pull <model>):
   - llama3.1                # Good general purpose
   - codellama               # Code-specialized
   - deepseek-coder          # Strong code understanding
   - mistral                 # Fast and capable
   - mixtral                 # MoE, good for complex tasks

## GitHub Copilot (Experimental)
   Set: LLM_PROVIDER=copilot
   Run: python copilot_proxy.py (requires VS Code with Copilot)

# =============================================================================
# PER-AGENT MODEL OVERRIDE
# =============================================================================

You can override the model for specific agents:

```python
config = AgentConfig(
    name="my_agent",
    model_override="claude-sonnet-4-20250514",  # This agent uses Claude
    temperature_override=0.2,  # Custom temperature
    ...
)
```

This works even when LLM_PROVIDER is set to a different provider,
as long as you have the API key for the model you're overriding to.

Note: model_override uses the SAME provider as LLM_PROVIDER.
To use different providers for different agents, you'd need to
modify the BaseAgent._create_llm() method or create separate
agent classes that override _create_llm().
"""


if __name__ == "__main__":
    print(CONFIGURATION_REFERENCE)
    print("\nRunning examples...")
    asyncio.run(example_mixed_models())
