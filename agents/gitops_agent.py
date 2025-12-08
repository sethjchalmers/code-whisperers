"""
GitOps and Kubernetes configuration expert agent.
"""

from typing import Any

from config.agent_config import GITOPS_AGENT_CONFIG

from .base_agent import AgentResponse, BaseAgent


class GitOpsExpertAgent(BaseAgent):
    """Expert agent for GitOps and Kubernetes configuration review."""

    def __init__(self):
        super().__init__(GITOPS_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional GitOps Review Context:
        - Validate Kubernetes API versions (prefer stable over beta/alpha)
        - Check for proper namespace isolation
        - Ensure resource quotas and limits are defined
        - Validate RBAC configurations
        - Check for proper secrets management (external-secrets, sealed-secrets)
        """

    async def review(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """Enhanced review with GitOps-specific checks."""
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()

        return await super().review(files, enhanced_context)
