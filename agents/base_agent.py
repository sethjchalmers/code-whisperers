"""
Base agent class and common utilities for all expert agents.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from fnmatch import fnmatch
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.agent_config import AgentConfig
from config.settings import get_settings

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for review findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Categories for review findings."""

    BEST_PRACTICE = "best_practice"
    SECURITY = "security"
    COST = "cost"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    HALLUCINATION = "hallucination"
    TESTING = "testing"
    COMPLIANCE = "compliance"


@dataclass
class ReviewFinding:
    """A single finding from a code review."""

    category: FindingCategory
    severity: Severity
    title: str
    description: str
    file_path: str | None = None
    line_number: int | None = None
    suggested_fix: str | None = None
    code_snippet: str | None = None
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert finding to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suggested_fix": self.suggested_fix,
            "code_snippet": self.code_snippet,
            "references": self.references,
        }


@dataclass
class AgentResponse:
    """Response from an expert agent."""

    agent_name: str
    timestamp: datetime
    files_reviewed: list[str]
    findings: list[ReviewFinding]
    summary: str
    raw_response: str | None = None
    execution_time_seconds: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert response to dictionary."""
        return {
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "files_reviewed": self.files_reviewed,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "execution_time_seconds": self.execution_time_seconds,
            "error": self.error,
        }

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @property
    def has_blocking_issues(self) -> bool:
        """Check if there are any critical or high severity issues."""
        return self.critical_count > 0 or self.high_count > 0


class BaseAgent(ABC):
    """Abstract base class for expert agents."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.settings = get_settings()
        self.llm = self._create_llm()
        self.logger = logging.getLogger(f"agent.{config.name}")

    def _create_llm(self):
        """Create the LLM instance based on settings."""
        model = self.config.model_override or self.settings.llm_model
        temperature = self.config.temperature_override or self.settings.llm_temperature

        if self.settings.llm_provider == "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=self.settings.openai_api_key,
            )
        elif self.settings.llm_provider == "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                api_key=self.settings.anthropic_api_key,
            )
        elif self.settings.llm_provider == "azure":
            from langchain_openai import AzureChatOpenAI

            return AzureChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=self.settings.azure_openai_api_key,
                azure_endpoint=self.settings.azure_openai_endpoint,
            )
        elif self.settings.llm_provider == "copilot":
            # Use Copilot through OpenAI-compatible endpoint
            # Option 1: VS Code extension (recommended) - see vscode-extension/
            # Option 2: Legacy proxy script - see copilot_proxy.py
            # Add /v1 to base_url since ChatOpenAI appends /chat/completions
            base_url = self.settings.copilot_endpoint
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            return ChatOpenAI(
                model=model or "gpt-4o",
                temperature=temperature,
                base_url=base_url,
                api_key="copilot",  # Placeholder, auth handled by VS Code extension
            )
        elif self.settings.llm_provider == "ollama":
            # Use Ollama for local models
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=model or "llama3.1",
                temperature=temperature,
                base_url=self.settings.ollama_endpoint,
            )
        else:
            raise ValueError(f"Unknown LLM provider: {self.settings.llm_provider}")

    def matches_file(self, file_path: str) -> bool:
        """Check if this agent should review the given file."""
        for pattern in self.config.file_patterns:
            if fnmatch(file_path, pattern):
                return True
            # Also check if pattern matches as a prefix
            if "/" in pattern and file_path.startswith(pattern.rstrip("*")):
                return True
        return False

    def filter_relevant_files(self, files: dict[str, str]) -> dict[str, str]:
        """Filter files to only those relevant to this agent."""
        return {path: content for path, content in files.items() if self.matches_file(path)}

    async def review(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> AgentResponse:
        """
        Review the provided files and return findings.

        Args:
            files: Dictionary mapping file paths to their contents
            context: Optional context information (git diff, related files, etc.)

        Returns:
            AgentResponse with findings and summary
        """
        import time

        start_time = time.time()

        # Filter to relevant files
        relevant_files = self.filter_relevant_files(files)

        if not relevant_files:
            return AgentResponse(
                agent_name=self.config.name,
                timestamp=datetime.now(),
                files_reviewed=[],
                findings=[],
                summary=f"No files matching patterns {self.config.file_patterns} found.",
                execution_time_seconds=0.0,
            )

        try:
            # Build the review prompt
            prompt = self._build_review_prompt(relevant_files, context)

            # Call the LLM
            messages = [
                SystemMessage(content=self.config.system_prompt),
                HumanMessage(content=prompt),
            ]

            response = await self.llm.ainvoke(messages)
            raw_response = response.content

            # Parse the response
            findings = self._parse_response(raw_response, list(relevant_files.keys()))
            summary = self._generate_summary(findings)

            execution_time = time.time() - start_time

            return AgentResponse(
                agent_name=self.config.name,
                timestamp=datetime.now(),
                files_reviewed=list(relevant_files.keys()),
                findings=findings,
                summary=summary,
                raw_response=raw_response,
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            self.logger.exception(f"Error during review: {e}")
            return AgentResponse(
                agent_name=self.config.name,
                timestamp=datetime.now(),
                files_reviewed=list(relevant_files.keys()),
                findings=[],
                summary="",
                execution_time_seconds=time.time() - start_time,
                error=str(e),
            )

    def _build_review_prompt(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> str:
        """Build the review prompt for the LLM."""
        prompt_parts = ["# Code Review Request\n"]

        # Add repository context files first (for understanding project setup)
        if context and "repo_context_files" in context:
            prompt_parts.append("## Repository Context\n")
            prompt_parts.append(
                "The following files provide context about the repository setup:\n\n"
            )

            # Prioritize most important context files
            priority_files = [
                ".gitignore",
                "pyproject.toml",
                "requirements.txt",
                ".pre-commit-config.yaml",
                ".env.example",
                "README.md",
            ]

            repo_files = context["repo_context_files"]
            shown_files = set()

            # Show priority files first
            for priority_file in priority_files:
                for file_path, content in repo_files.items():
                    if file_path.endswith(priority_file) or file_path == priority_file:
                        prompt_parts.append(f"### {file_path}\n```\n{content}\n```\n\n")
                        shown_files.add(file_path)

            # Show remaining context files (limited to avoid token overflow)
            remaining = [(k, v) for k, v in repo_files.items() if k not in shown_files]
            for file_path, content in remaining[:5]:  # Limit to 5 more
                # Truncate if needed
                if len(content) > 2000:
                    content = content[:2000] + "\n... [TRUNCATED]"
                prompt_parts.append(f"### {file_path}\n```\n{content}\n```\n\n")

        # Add git diff context
        if context:
            if "git_diff" in context and context["git_diff"]:
                prompt_parts.append("## Git Diff (Changes)\n```diff\n")
                prompt_parts.append(context["git_diff"])
                prompt_parts.append("\n```\n\n")

            if "commit_message" in context:
                prompt_parts.append(f"## Commit Message\n{context['commit_message']}\n\n")

        # Add files to review
        prompt_parts.append("## Files to Review\n\n")

        for file_path, content in files.items():
            # Truncate very large files
            max_size = self.settings.max_file_size_kb * 1024
            if len(content) > max_size:
                content = content[:max_size] + "\n\n... [FILE TRUNCATED] ..."

            prompt_parts.append(f"### {file_path}\n```\n{content}\n```\n\n")

        prompt_parts.append(
            """
## Review Instructions
Please review the code above and provide your analysis.
Return your response as valid JSON with the following structure:
{
    "findings": [
        {
            "category": "string (one of: best_practice, security, cost, performance, quality, hallucination, testing, compliance)",
            "severity": "string (one of: critical, high, medium, low, info)",
            "title": "string",
            "description": "string",
            "file_path": "string or null",
            "line_number": "number or null",
            "suggested_fix": "string or null",
            "code_snippet": "string or null"
        }
    ],
    "summary": "string"
}
"""
        )

        return "".join(prompt_parts)

    def _parse_response(self, raw_response: str, file_paths: list[str]) -> list[ReviewFinding]:
        """Parse the LLM response into ReviewFindings."""
        findings = []

        try:
            # Try to extract JSON from the response
            json_str = raw_response

            # Handle markdown code blocks
            if "```json" in raw_response:
                start = raw_response.find("```json") + 7
                end = raw_response.find("```", start)
                json_str = raw_response[start:end]
            elif "```" in raw_response:
                start = raw_response.find("```") + 3
                end = raw_response.find("```", start)
                json_str = raw_response[start:end]

            data = json.loads(json_str.strip())

            for item in data.get("findings", []):
                try:
                    finding = ReviewFinding(
                        category=FindingCategory(item.get("category", "quality")),
                        severity=Severity(item.get("severity", "info")),
                        title=item.get("title", "Untitled Finding"),
                        description=item.get("description", ""),
                        file_path=item.get("file_path"),
                        line_number=item.get("line_number"),
                        suggested_fix=item.get("suggested_fix"),
                        code_snippet=item.get("code_snippet"),
                    )
                    findings.append(finding)
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Failed to parse finding: {e}")
                    continue

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            # Create a generic finding from the raw response
            findings.append(
                ReviewFinding(
                    category=FindingCategory.QUALITY,
                    severity=Severity.INFO,
                    title="Raw Review Output",
                    description=raw_response[:2000],
                )
            )

        return findings

    def _generate_summary(self, findings: list[ReviewFinding]) -> str:
        """Generate a summary of the findings."""
        if not findings:
            return "No issues found."

        severity_counts: dict[str, int] = {}
        for finding in findings:
            severity_counts[finding.severity.value] = (
                severity_counts.get(finding.severity.value, 0) + 1
            )

        parts = [f"Found {len(findings)} issue(s):"]
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                parts.append(f"{count} {severity}")

        return " | ".join(parts)

    @abstractmethod
    def get_expert_context(self) -> str:
        """Return additional expert-specific context for the review."""
        pass
