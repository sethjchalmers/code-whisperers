"""
Security vulnerability analysis expert agent.
"""

from config.agent_config import SECURITY_AGENT_CONFIG

from .base_agent import BaseAgent


class SecurityExpertAgent(BaseAgent):
    """Expert agent for security vulnerability analysis."""

    def __init__(self):
        super().__init__(SECURITY_AGENT_CONFIG)

    def get_expert_context(self) -> str:
        return """
        Additional Security Review Context:
        - OWASP Top 10 2021 categories
        - CWE/SANS Top 25 vulnerabilities
        - Cloud security best practices (CSA guidelines)
        - Container security (Docker/Kubernetes hardening)
        - Secret scanning patterns
        """

    def matches_file(self, file_path: str) -> bool:
        """Security agent reviews all files."""
        # Exclude binary and non-code files
        excluded_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".pdf",
            ".zip",
            ".tar",
            ".gz",
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".lock",
            ".sum",
        ]
        return not any(file_path.lower().endswith(ext) for ext in excluded_extensions)
