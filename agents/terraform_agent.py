"""
Terraform and Infrastructure as Code expert agent.
"""

from typing import Any

from config.agent_config import TERRAFORM_AGENT_CONFIG

from .base_agent import AgentResponse, BaseAgent


class TerraformExpertAgent(BaseAgent):
    """Expert agent for Terraform and Infrastructure as Code review."""

    def __init__(self):
        super().__init__(TERRAFORM_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional Terraform Review Context:
        - Check for AWS, Azure, GCP provider best practices
        - Validate resource dependencies and lifecycle rules
        - Ensure proper state backend configuration
        - Check for Terraform version constraints
        """

    async def review(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """Enhanced review with Terraform-specific checks."""
        # Add expert context
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()

        return await super().review(files, enhanced_context)
