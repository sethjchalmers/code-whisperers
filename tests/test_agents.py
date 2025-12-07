"""
Tests for the agent base classes.
"""

import pytest
from agents.base_agent import (
    ReviewFinding,
    AgentResponse,
    Severity,
    FindingCategory,
)
from datetime import datetime


class TestReviewFinding:
    """Test the ReviewFinding dataclass."""
    
    def test_create_finding(self):
        """Test creating a review finding."""
        finding = ReviewFinding(
            category=FindingCategory.SECURITY,
            severity=Severity.HIGH,
            title="SQL Injection Vulnerability",
            description="Possible SQL injection in user input.",
            file_path="app.py",
            line_number=42,
            suggested_fix="Use parameterized queries.",
        )
        
        assert finding.category == FindingCategory.SECURITY
        assert finding.severity == Severity.HIGH
        assert finding.title == "SQL Injection Vulnerability"
        assert finding.file_path == "app.py"
        assert finding.line_number == 42
    
    def test_finding_to_dict(self):
        """Test converting finding to dictionary."""
        finding = ReviewFinding(
            category=FindingCategory.BEST_PRACTICE,
            severity=Severity.LOW,
            title="Missing docstring",
            description="Function lacks documentation.",
        )
        
        d = finding.to_dict()
        assert d["category"] == "best_practice"
        assert d["severity"] == "low"
        assert d["title"] == "Missing docstring"


class TestAgentResponse:
    """Test the AgentResponse dataclass."""
    
    def test_create_response(self):
        """Test creating an agent response."""
        findings = [
            ReviewFinding(
                category=FindingCategory.SECURITY,
                severity=Severity.CRITICAL,
                title="Hardcoded secret",
                description="API key exposed in code.",
            ),
            ReviewFinding(
                category=FindingCategory.QUALITY,
                severity=Severity.LOW,
                title="Long function",
                description="Function exceeds 50 lines.",
            ),
        ]
        
        response = AgentResponse(
            agent_name="security_expert",
            timestamp=datetime.now(),
            files_reviewed=["app.py", "config.py"],
            findings=findings,
            summary="Found 2 issues",
            execution_time_seconds=5.5,
        )
        
        assert response.agent_name == "security_expert"
        assert len(response.findings) == 2
        assert response.critical_count == 1
        assert response.high_count == 0
        assert response.has_blocking_issues is True
    
    def test_response_without_blocking_issues(self):
        """Test response without blocking issues."""
        findings = [
            ReviewFinding(
                category=FindingCategory.QUALITY,
                severity=Severity.INFO,
                title="Suggestion",
                description="Consider refactoring.",
            ),
        ]
        
        response = AgentResponse(
            agent_name="python_expert",
            timestamp=datetime.now(),
            files_reviewed=["app.py"],
            findings=findings,
            summary="Found 1 suggestion",
        )
        
        assert response.critical_count == 0
        assert response.high_count == 0
        assert response.has_blocking_issues is False
    
    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = AgentResponse(
            agent_name="terraform_expert",
            timestamp=datetime.now(),
            files_reviewed=["main.tf"],
            findings=[],
            summary="No issues found",
            execution_time_seconds=2.0,
        )
        
        d = response.to_dict()
        assert d["agent_name"] == "terraform_expert"
        assert d["files_reviewed"] == ["main.tf"]
        assert d["summary"] == "No issues found"
        assert d["execution_time_seconds"] == 2.0
        assert d["error"] is None


class TestSeverity:
    """Test severity levels."""
    
    def test_severity_values(self):
        """Test severity enum values."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"


class TestFindingCategory:
    """Test finding categories."""
    
    def test_category_values(self):
        """Test category enum values."""
        assert FindingCategory.SECURITY.value == "security"
        assert FindingCategory.BEST_PRACTICE.value == "best_practice"
        assert FindingCategory.COST.value == "cost"
        assert FindingCategory.PERFORMANCE.value == "performance"
        assert FindingCategory.QUALITY.value == "quality"
        assert FindingCategory.HALLUCINATION.value == "hallucination"
