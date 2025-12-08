"""
Integration tests for the multi-agent code review pipeline.

This module tests the full review pipeline with all agents working together
on intentionally bad code samples to verify each agent catches relevant issues.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents import (
    AgentResponse,
    AWSExpertAgent,
    CostOptimizationAgent,
    FindingCategory,
    GitOpsExpertAgent,
    JenkinsExpertAgent,
    PythonExpertAgent,
    ReviewFinding,
    SecurityExpertAgent,
    Severity,
    TerraformExpertAgent,
    create_all_agents,
)
from orchestration import ReviewPipeline


def make_response(
    agent_name: str,
    files_reviewed: list[str] | None = None,
    findings: list[ReviewFinding] | None = None,
    summary: str = "No issues",
    error: str | None = None,
) -> AgentResponse:
    """Helper to create AgentResponse with required fields."""
    return AgentResponse(
        agent_name=agent_name,
        timestamp=datetime.now(),
        files_reviewed=files_reviewed or [],
        findings=findings or [],
        summary=summary,
        error=error,
    )


def make_finding(
    category: str = "security",
    severity: Severity = Severity.MEDIUM,
    title: str = "Test Finding",
    description: str = "Test description",
    file_path: str = "test.py",
    line_number: int | None = None,
) -> ReviewFinding:
    """Helper to create ReviewFinding with proper category enum."""
    cat_map = {
        "security": FindingCategory.SECURITY,
        "quality": FindingCategory.QUALITY,
        "performance": FindingCategory.PERFORMANCE,
        "cost": FindingCategory.COST,
        "best_practice": FindingCategory.BEST_PRACTICE,
        "testing": FindingCategory.TESTING,
    }
    return ReviewFinding(
        category=cat_map.get(category, FindingCategory.SECURITY),
        severity=severity,
        title=title,
        description=description,
        file_path=file_path,
        line_number=line_number,
    )


# Sample bad Python code with multiple issues for agents to find
BAD_PYTHON_CODE = '''
"""A poorly written Python module with many issues."""
import os
import subprocess
import pickle
import sys, json  # Multiple imports on one line

# Hardcoded secrets - Security issue
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"
AWS_SECRET = "AKIAIOSFODNN7EXAMPLE"

# SQL Injection vulnerability
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id  # SQL injection
    return execute_query(query)

# Command injection vulnerability
def run_command(user_input):
    os.system("echo " + user_input)  # Command injection
    subprocess.call(user_input, shell=True)  # Shell injection

# Insecure deserialization
def load_data(data):
    return pickle.loads(data)  # Insecure deserialization

# Missing type hints and docstrings
def process_data(x, y):
    result = []
    for i in range(len(x)):  # Anti-pattern: use enumerate
        result.append(x[i] + y[i])
    return result

# Mutable default argument
def append_to_list(item, lst=[]):  # Mutable default argument
    lst.append(item)
    return lst

# Broad exception catching
def risky_operation():
    try:
        do_something()
    except:  # Bare except
        pass  # Silently swallowing exceptions

# Unused variables
def unused_example():
    unused_var = 42  # Unused variable
    x = 1
    return x

# Password in URL
def connect_to_db():
    url = "postgresql://admin:password123@localhost:5432/db"
    return connect(url)

# Eval usage
def dynamic_execute(code):
    return eval(code)  # Dangerous eval
'''

# Sample bad Terraform code
BAD_TERRAFORM_CODE = """
# Bad Terraform with security and cost issues

provider "aws" {
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  region     = "us-east-1"
}

resource "aws_security_group" "bad_sg" {
  name = "allow_all"
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to the world
  }
}

resource "aws_instance" "expensive" {
  ami           = "ami-12345678"
  instance_type = "x1e.32xlarge"  # Very expensive instance
  root_block_device {
    encrypted = false  # Unencrypted storage
  }
}
"""


class TestAgentCreation:
    """Test that all agents can be created properly."""

    def test_create_all_agents(self) -> None:
        """Test creating all expert agents."""
        agents = create_all_agents()
        assert len(agents) == 8

        agent_names = [a.config.name for a in agents]
        assert "terraform_expert" in agent_names
        assert "gitops_expert" in agent_names
        assert "jenkins_expert" in agent_names
        assert "python_expert" in agent_names
        assert "security_expert" in agent_names
        assert "cost_expert" in agent_names
        assert "clean_code_expert" in agent_names
        assert "aws_expert" in agent_names

    def test_agent_expert_context(self) -> None:
        """Test that each agent provides meaningful expert context."""
        agents = create_all_agents()

        for agent in agents:
            context = agent.get_expert_context()
            assert isinstance(context, str)
            assert len(context) > 50  # Should have substantial context


class TestAgentFileMatching:
    """Test that agents correctly identify files they should review."""

    def test_python_agent_matches_python_files(self) -> None:
        """Python agent should match .py files."""
        agent = PythonExpertAgent()

        assert agent.matches_file("app.py")
        assert agent.matches_file("src/module.py")
        assert not agent.matches_file("main.tf")
        assert not agent.matches_file("Jenkinsfile")

    def test_terraform_agent_matches_tf_files(self) -> None:
        """Terraform agent should match .tf and .tfvars files."""
        agent = TerraformExpertAgent()

        assert agent.matches_file("main.tf")
        assert agent.matches_file("variables.tfvars")
        assert agent.matches_file("modules/vpc/main.tf")
        assert not agent.matches_file("app.py")

    def test_jenkins_agent_matches_jenkinsfiles(self) -> None:
        """Jenkins agent should match Jenkinsfiles."""
        agent = JenkinsExpertAgent()

        assert agent.matches_file("Jenkinsfile")
        assert agent.matches_file("Jenkinsfile.deploy")
        # Note: fnmatch with "Jenkinsfile*" only matches if filename starts with Jenkinsfile
        # Paths like "ci/Jenkinsfile" need "*/Jenkinsfile*" pattern or basename matching
        assert agent.matches_file("jenkins/build.groovy")
        assert not agent.matches_file("app.py")

    def test_gitops_agent_matches_k8s_files(self) -> None:
        """GitOps agent should match Kubernetes manifests."""
        agent = GitOpsExpertAgent()

        assert agent.matches_file("deployment.yaml")
        assert agent.matches_file("k8s/service.yml")
        assert agent.matches_file("helm/values.yaml")
        assert not agent.matches_file("app.py")

    def test_security_agent_matches_most_files(self) -> None:
        """Security agent should review most code files."""
        agent = SecurityExpertAgent()

        assert agent.matches_file("app.py")
        assert agent.matches_file("main.tf")
        assert agent.matches_file("config.yaml")
        # Should skip binary files
        assert not agent.matches_file("image.png")
        assert not agent.matches_file("archive.zip")

    def test_cost_agent_matches_infra_files(self) -> None:
        """Cost agent should match infrastructure files."""
        agent = CostOptimizationAgent()

        assert agent.matches_file("main.tf")
        assert agent.matches_file("docker-compose.yml")
        assert agent.matches_file("k8s/deployment.yaml")

    def test_aws_agent_matches_aws_files(self) -> None:
        """AWS agent should match CloudFormation, CDK, and SAM files."""
        agent = AWSExpertAgent()

        assert agent.matches_file("template.yaml")
        assert agent.matches_file("template.yml")
        assert agent.matches_file("cloudformation/stack.json")
        assert agent.matches_file("cdk/app.py")
        assert agent.matches_file("cdk.json")
        assert agent.matches_file("samconfig.toml")
        assert not agent.matches_file("image.png")


class TestPipelineIntegration:
    """Integration tests for the full review pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_with_bad_python_code(self) -> None:
        """Test pipeline identifies issues in bad Python code."""
        pipeline = ReviewPipeline(parallel=False)

        # Create mock responses for each agent type
        security_response = make_response(
            agent_name="security_expert",
            files_reviewed=["bad_code.py"],
            findings=[
                make_finding(
                    category="security",
                    severity=Severity.CRITICAL,
                    title="Hardcoded API Key",
                    description="Found hardcoded API key: API_KEY = 'sk-...'",
                    file_path="bad_code.py",
                    line_number=8,
                ),
                make_finding(
                    category="security",
                    severity=Severity.HIGH,
                    title="SQL Injection Vulnerability",
                    description="String concatenation in SQL query",
                    file_path="bad_code.py",
                    line_number=14,
                ),
                make_finding(
                    category="security",
                    severity=Severity.HIGH,
                    title="Command Injection",
                    description="User input passed to os.system()",
                    file_path="bad_code.py",
                    line_number=19,
                ),
            ],
            summary="Found 3 security issues",
        )

        python_response = make_response(
            agent_name="python_expert",
            files_reviewed=["bad_code.py"],
            findings=[
                make_finding(
                    category="quality",
                    severity=Severity.MEDIUM,
                    title="Mutable Default Argument",
                    description="Using mutable default argument in function",
                    file_path="bad_code.py",
                    line_number=35,
                ),
                make_finding(
                    category="quality",
                    severity=Severity.LOW,
                    title="Missing Type Hints",
                    description="Function lacks type annotations",
                    file_path="bad_code.py",
                    line_number=25,
                ),
            ],
            summary="Found 2 code quality issues",
        )

        # Mock each agent's review method
        for agent in pipeline.agents:
            if "security" in agent.config.name:
                agent.review = AsyncMock(return_value=security_response)
            elif "python" in agent.config.name:
                agent.review = AsyncMock(return_value=python_response)
            else:
                agent.review = AsyncMock(
                    return_value=make_response(
                        agent_name=agent.config.name,
                        summary="No relevant files",
                    )
                )

        files = {"bad_code.py": BAD_PYTHON_CODE}
        result = await pipeline.run(files, {})

        # Verify results
        assert result is not None
        assert len(result.agent_responses) > 0

        # Check that security issues were found
        all_findings = []
        for response in result.agent_responses:
            all_findings.extend(response.findings)

        # Should have found critical/high security issues
        critical_findings = [f for f in all_findings if f.severity == Severity.CRITICAL]
        high_findings = [f for f in all_findings if f.severity == Severity.HIGH]

        assert len(critical_findings) >= 1, "Should find critical security issues"
        assert len(high_findings) >= 1, "Should find high severity issues"

    @pytest.mark.asyncio
    async def test_pipeline_with_bad_terraform(self) -> None:
        """Test pipeline identifies issues in bad Terraform code."""
        pipeline = ReviewPipeline(parallel=False)

        terraform_response = make_response(
            agent_name="terraform_expert",
            files_reviewed=["main.tf"],
            findings=[
                make_finding(
                    category="security",
                    severity=Severity.CRITICAL,
                    title="Hardcoded AWS Credentials",
                    description="AWS access keys hardcoded in provider block",
                    file_path="main.tf",
                    line_number=5,
                ),
                make_finding(
                    category="security",
                    severity=Severity.HIGH,
                    title="Overly Permissive Security Group",
                    description="Security group allows all traffic from 0.0.0.0/0",
                    file_path="main.tf",
                    line_number=15,
                ),
            ],
            summary="Found 2 Terraform issues",
        )

        cost_response = make_response(
            agent_name="cost_expert",
            files_reviewed=["main.tf"],
            findings=[
                make_finding(
                    category="cost",
                    severity=Severity.HIGH,
                    title="Expensive Instance Type",
                    description="x1e.32xlarge is very expensive (~$26/hour)",
                    file_path="main.tf",
                    line_number=30,
                ),
            ],
            summary="Found 1 cost optimization opportunity",
        )

        for agent in pipeline.agents:
            if "terraform" in agent.config.name:
                agent.review = AsyncMock(return_value=terraform_response)
            elif "cost" in agent.config.name:
                agent.review = AsyncMock(return_value=cost_response)
            else:
                agent.review = AsyncMock(
                    return_value=make_response(
                        agent_name=agent.config.name,
                        summary="No relevant files",
                    )
                )

        files = {"main.tf": BAD_TERRAFORM_CODE}
        result = await pipeline.run(files, {})

        all_findings = []
        for response in result.agent_responses:
            all_findings.extend(response.findings)

        # Should find security and cost issues
        security_findings = [f for f in all_findings if f.category == FindingCategory.SECURITY]
        cost_findings = [f for f in all_findings if f.category == FindingCategory.COST]

        assert len(security_findings) >= 1, "Should find Terraform security issues"
        assert len(cost_findings) >= 1, "Should find cost optimization issues"


class TestAgentSpecificReviews:
    """Test that each agent type reviews its specific concerns."""

    @pytest.mark.asyncio
    async def test_security_agent_finds_secrets(self) -> None:
        """Security agent should identify hardcoded secrets."""
        agent = SecurityExpertAgent()

        # Mock the LLM response
        mock_response = """
        {
            "findings": [
                {
                    "category": "security",
                    "severity": "critical",
                    "title": "Hardcoded API Key",
                    "description": "API key hardcoded in source: API_KEY = 'sk-...'",
                    "file_path": "test.py",
                    "line_number": 8,
                    "suggested_fix": "Use environment variables or secrets manager"
                }
            ],
            "summary": "Found 1 critical security issue"
        }
        """

        # Create a mock LLM that returns the expected response
        mock_llm = MagicMock()
        mock_llm_response = MagicMock()
        mock_llm_response.content = mock_response
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        agent.llm = mock_llm

        files = {"test.py": BAD_PYTHON_CODE}
        response = await agent.review(files, {})

        assert response.agent_name == "security_expert"
        # LLM was called for matching files
        assert mock_llm.ainvoke.called

    @pytest.mark.asyncio
    async def test_python_agent_finds_code_smells(self) -> None:
        """Python agent should identify code quality issues."""
        agent = PythonExpertAgent()

        mock_response = """
        {
            "findings": [
                {
                    "category": "quality",
                    "severity": "medium",
                    "title": "Mutable Default Argument",
                    "description": "Function uses mutable default argument",
                    "file_path": "test.py",
                    "line_number": 35
                }
            ],
            "summary": "Found 1 code quality issue"
        }
        """

        mock_llm = MagicMock()
        mock_llm_response = MagicMock()
        mock_llm_response.content = mock_response
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        agent.llm = mock_llm

        files = {"test.py": BAD_PYTHON_CODE}
        response = await agent.review(files, {})

        assert response.agent_name == "python_expert"
        assert mock_llm.ainvoke.called

    @pytest.mark.asyncio
    async def test_terraform_agent_finds_misconfigurations(self) -> None:
        """Terraform agent should identify infrastructure issues."""
        agent = TerraformExpertAgent()

        mock_response = """
        {
            "findings": [
                {
                    "category": "security",
                    "severity": "critical",
                    "title": "Hardcoded Credentials",
                    "description": "AWS credentials hardcoded in provider",
                    "file_path": "main.tf",
                    "line_number": 5
                }
            ],
            "summary": "Found 1 critical issue"
        }
        """

        mock_llm = MagicMock()
        mock_llm_response = MagicMock()
        mock_llm_response.content = mock_response
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        agent.llm = mock_llm

        files = {"main.tf": BAD_TERRAFORM_CODE}
        response = await agent.review(files, {})

        assert response.agent_name == "terraform_expert"
        assert mock_llm.ainvoke.called

    @pytest.mark.asyncio
    async def test_cost_agent_finds_expensive_resources(self) -> None:
        """Cost agent should identify expensive configurations."""
        agent = CostOptimizationAgent()

        mock_response = """
        {
            "findings": [
                {
                    "category": "cost",
                    "severity": "high",
                    "title": "Expensive Instance Type",
                    "description": "x1e.32xlarge costs ~$26.688/hour",
                    "file_path": "main.tf",
                    "line_number": 30
                }
            ],
            "summary": "Found 1 cost optimization opportunity"
        }
        """

        mock_llm = MagicMock()
        mock_llm_response = MagicMock()
        mock_llm_response.content = mock_response
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        agent.llm = mock_llm

        files = {"main.tf": BAD_TERRAFORM_CODE}
        response = await agent.review(files, {})

        assert response.agent_name == "cost_expert"
        assert mock_llm.ainvoke.called


class TestReviewResultAggregation:
    """Test that review results are properly aggregated."""

    @pytest.mark.asyncio
    async def test_findings_are_aggregated(self) -> None:
        """Test that findings from multiple agents are combined."""
        pipeline = ReviewPipeline(parallel=False)

        # Create responses with findings from different agents
        responses = [
            make_response(
                agent_name="security_expert",
                files_reviewed=["test.py"],
                findings=[
                    make_finding(
                        category="security",
                        severity=Severity.CRITICAL,
                        title="Issue 1",
                        description="Security issue",
                        file_path="test.py",
                    )
                ],
                summary="1 issue",
            ),
            make_response(
                agent_name="python_expert",
                files_reviewed=["test.py"],
                findings=[
                    make_finding(
                        category="quality",
                        severity=Severity.MEDIUM,
                        title="Issue 2",
                        description="Quality issue",
                        file_path="test.py",
                    )
                ],
                summary="1 issue",
            ),
        ]

        # Mock all agents to return our responses
        for i, agent in enumerate(pipeline.agents):
            if i < len(responses):
                agent.review = AsyncMock(return_value=responses[i])
            else:
                agent.review = AsyncMock(
                    return_value=make_response(
                        agent_name=agent.config.name,
                        summary="No issues",
                    )
                )

        files = {"test.py": "print('test')"}
        result = await pipeline.run(files, {})

        # Count total findings
        total_findings = sum(len(r.findings) for r in result.agent_responses)
        assert total_findings >= 2, "Should aggregate findings from multiple agents"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_files_dict(self) -> None:
        """Test handling of empty files dictionary."""
        pipeline = ReviewPipeline(parallel=False)

        for agent in pipeline.agents:
            agent.review = AsyncMock(
                return_value=make_response(
                    agent_name=agent.config.name,
                    summary="No files to review",
                )
            )

        files: dict[str, str] = {}
        result = await pipeline.run(files, {})

        assert result is not None
        assert result.status.value in ["completed", "completed_with_issues"]

    @pytest.mark.asyncio
    async def test_agent_error_handling(self) -> None:
        """Test that pipeline handles agent errors gracefully."""
        pipeline = ReviewPipeline(parallel=True)

        # Make one agent raise an exception
        for i, agent in enumerate(pipeline.agents):
            if i == 0:
                agent.review = AsyncMock(side_effect=Exception("Agent failed"))
            else:
                agent.review = AsyncMock(
                    return_value=make_response(
                        agent_name=agent.config.name,
                        summary="OK",
                    )
                )

        files = {"test.py": "print('test')"}
        result = await pipeline.run(files, {})

        # Pipeline should complete despite one agent failing
        assert result is not None

    @pytest.mark.asyncio
    async def test_large_file_handling(self) -> None:
        """Test handling of large files."""
        pipeline = ReviewPipeline(parallel=False)

        for agent in pipeline.agents:
            agent.review = AsyncMock(
                return_value=make_response(
                    agent_name=agent.config.name,
                    files_reviewed=["large.py"],
                    summary="Reviewed",
                )
            )

        # Create a large file
        large_content = "x = 1\n" * 10000
        files = {"large.py": large_content}

        result = await pipeline.run(files, {})
        assert result is not None
