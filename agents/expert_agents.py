"""
Specialized expert agents for different domains.
"""

from typing import Any, Optional

from config.agent_config import (
    TERRAFORM_AGENT_CONFIG,
    GITOPS_AGENT_CONFIG,
    JENKINS_AGENT_CONFIG,
    PYTHON_AGENT_CONFIG,
    SECURITY_AGENT_CONFIG,
    COST_OPTIMIZATION_AGENT_CONFIG,
)
from .base_agent import BaseAgent, AgentResponse


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
        self,
        files: dict[str, str],
        context: Optional[dict[str, Any]] = None
    ) -> AgentResponse:
        """Enhanced review with Terraform-specific checks."""
        # Add expert context
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()
        
        return await super().review(files, enhanced_context)


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
        self,
        files: dict[str, str],
        context: Optional[dict[str, Any]] = None
    ) -> AgentResponse:
        """Enhanced review with GitOps-specific checks."""
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()
        
        return await super().review(files, enhanced_context)


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
        self,
        files: dict[str, str],
        context: Optional[dict[str, Any]] = None
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
            ".png", ".jpg", ".jpeg", ".gif", ".ico",
            ".pdf", ".zip", ".tar", ".gz",
            ".exe", ".dll", ".so", ".dylib",
            ".lock", ".sum"
        ]
        return not any(file_path.lower().endswith(ext) for ext in excluded_extensions)


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
        self,
        files: dict[str, str],
        context: Optional[dict[str, Any]] = None
    ) -> AgentResponse:
        """Enhanced review with cost-specific analysis."""
        enhanced_context = context or {}
        enhanced_context["expert_context"] = self.get_expert_context()
        
        # Look for resource definitions to analyze
        resources_found = []
        for path, content in files.items():
            if path.endswith(".tf"):
                # Extract Terraform resources
                import re
                resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"'
                matches = re.findall(resource_pattern, content)
                for resource_type, resource_name in matches:
                    resources_found.append(f"{resource_type}.{resource_name}")
        
        if resources_found:
            enhanced_context["resources"] = resources_found
        
        return await super().review(files, enhanced_context)


# Factory function to create all agents
def create_all_agents() -> list[BaseAgent]:
    """Create instances of all expert agents."""
    return [
        TerraformExpertAgent(),
        GitOpsExpertAgent(),
        JenkinsExpertAgent(),
        PythonExpertAgent(),
        SecurityExpertAgent(),
        CostOptimizationAgent(),
    ]
