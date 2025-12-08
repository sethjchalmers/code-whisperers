"""
Specialized expert agents for different domains.

This module re-exports all expert agents for backward compatibility.
Each agent is now in its own file for better organization:
- terraform_agent.py - Terraform/IaC expert
- gitops_agent.py - GitOps/Kubernetes expert
- jenkins_agent.py - Jenkins/CI-CD expert
- python_agent.py - Python code review expert
- security_agent.py - Security vulnerability expert
- cost_agent.py - Cloud cost optimization expert
- clean_code_agent.py - Clean code and software craftsmanship expert
- aws_agent.py - AWS cloud and infrastructure expert
"""

from .aws_agent import AWSExpertAgent
from .base_agent import BaseAgent
from .clean_code_agent import CleanCodeExpertAgent
from .cost_agent import CostOptimizationAgent
from .gitops_agent import GitOpsExpertAgent
from .jenkins_agent import JenkinsExpertAgent
from .python_agent import PythonExpertAgent
from .security_agent import SecurityExpertAgent
from .terraform_agent import TerraformExpertAgent


def create_all_agents() -> list[BaseAgent]:
    """Create instances of all expert agents."""
    return [
        TerraformExpertAgent(),
        GitOpsExpertAgent(),
        JenkinsExpertAgent(),
        PythonExpertAgent(),
        SecurityExpertAgent(),
        CostOptimizationAgent(),
        CleanCodeExpertAgent(),
        AWSExpertAgent(),
    ]


__all__ = [
    "TerraformExpertAgent",
    "GitOpsExpertAgent",
    "JenkinsExpertAgent",
    "PythonExpertAgent",
    "SecurityExpertAgent",
    "CostOptimizationAgent",
    "CleanCodeExpertAgent",
    "AWSExpertAgent",
    "create_all_agents",
]
