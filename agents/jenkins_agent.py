"""
Jenkins pipeline expert agent.
"""

from config.agent_config import JENKINS_AGENT_CONFIG

from .base_agent import BaseAgent


class JenkinsExpertAgent(BaseAgent):
    """Expert agent for Jenkins pipeline review."""

    def __init__(self):
        super().__init__(JENKINS_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional Jenkins Review Context:
        - Prefer declarative pipelines over scripted when possible
        - Check for proper credential binding
        - Validate agent labels and resource constraints
        - Ensure proper post-build actions
        - Check for shared library best practices
        """
