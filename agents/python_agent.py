"""
Python code review expert agent.
"""

from typing import Any

from config.agent_config import PYTHON_AGENT_CONFIG

from .base_agent import AgentResponse, BaseAgent


class PythonExpertAgent(BaseAgent):
    """Expert agent for Python code review."""

    def __init__(self):
        super().__init__(PYTHON_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional Python Review Context:
        - Check for Python 3.9+ features usage
        - Validate type hints with mypy compatibility
        - Check for async/await best practices
        - Ensure proper exception handling
        - Validate dependency security (pip-audit recommendations)
        """

    async def review(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """Enhanced review with Python-specific checks."""
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()

        # Add import analysis for Python files
        imports_found = []
        for path, content in files.items():
            if path.endswith(".py"):
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("import ") or line.startswith("from "):
                        imports_found.append(line)

        if imports_found:
            enhanced_context["imports"] = imports_found

        return await super().review(files, enhanced_context)
