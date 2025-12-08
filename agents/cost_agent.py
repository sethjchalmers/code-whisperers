"""
Cloud cost optimization expert agent.
"""

import re
from typing import Any

from config.agent_config import COST_OPTIMIZATION_AGENT_CONFIG

from .base_agent import AgentResponse, BaseAgent


class CostOptimizationAgent(BaseAgent):
    """Expert agent for cloud cost optimization."""

    def __init__(self):
        super().__init__(COST_OPTIMIZATION_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional Cost Optimization Context:
        - AWS pricing tiers and reserved capacity options
        - Azure cost management recommendations
        - GCP committed use discounts
        - Multi-cloud cost comparison
        - FinOps best practices
        """

    async def review(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """Enhanced review with cost-specific analysis."""
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()

        # Look for resource definitions to analyze
        resources_found = []
        for path, content in files.items():
            if path.endswith(".tf"):
                # Extract Terraform resources
                resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"'
                matches = re.findall(resource_pattern, content)
                for resource_type, resource_name in matches:
                    resources_found.append(f"{resource_type}.{resource_name}")

        if resources_found:
            enhanced_context["resources"] = resources_found

        return await super().review(files, enhanced_context)
