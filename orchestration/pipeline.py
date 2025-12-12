"""
LangGraph-based pipeline for orchestrating agent reviews.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from agents.base_agent import AgentResponse, ReviewFinding, Severity
from agents.expert_agents import create_all_agents
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Status of the review pipeline."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineState(TypedDict):
    """State maintained throughout the pipeline execution."""

    # Input
    files: dict[str, str]  # file_path -> content
    context: dict[str, Any]  # Additional context (git diff, etc.)

    # Processing state
    current_agent_index: int
    agent_responses: list[dict]  # Serialized AgentResponse objects

    # Output
    status: str
    final_report: str | None
    has_blocking_issues: bool
    error: str | None


@dataclass
class ReviewResult:
    """Final result of a review pipeline execution."""

    status: ReviewStatus
    agent_responses: list[AgentResponse]
    consolidated_findings: list[ReviewFinding]
    summary: str
    report_path: str | None = None
    total_execution_time: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "agent_responses": [r.to_dict() for r in self.agent_responses],
            "consolidated_findings": [f.to_dict() for f in self.consolidated_findings],
            "summary": self.summary,
            "report_path": self.report_path,
            "total_execution_time": self.total_execution_time,
        }

    @property
    def has_critical_issues(self) -> bool:
        return any(f.severity == Severity.CRITICAL for f in self.consolidated_findings)

    @property
    def has_high_issues(self) -> bool:
        return any(f.severity == Severity.HIGH for f in self.consolidated_findings)

    def get_findings_by_severity(self, severity: Severity) -> list[ReviewFinding]:
        return [f for f in self.consolidated_findings if f.severity == severity]

    def get_findings_by_file(self, file_path: str) -> list[ReviewFinding]:
        return [f for f in self.consolidated_findings if f.file_path == file_path]


class ReviewPipeline:
    """
    LangGraph-based pipeline for orchestrating multi-agent code reviews.

    The pipeline:
    1. Initializes with files to review and optional context
    2. Routes files to appropriate expert agents based on file patterns
    3. Runs agents in parallel or sequence based on configuration
    4. Consolidates findings from all agents
    5. Generates a final report
    """

    def __init__(self, parallel: bool = True, agent_names: list[str] | None = None):
        self.settings = get_settings()
        # Force sequential mode for Ollama (can only handle one request at a time)
        if self.settings.llm_provider == "ollama":
            self.parallel = False
        else:
            self.parallel = parallel
        self.all_agents = create_all_agents()
        # Filter agents if specific names provided
        if agent_names:
            agent_name_set = {name.lower() for name in agent_names}
            self.agents = [
                agent
                for agent in self.all_agents
                if agent.config.name.lower().replace("_expert", "") in agent_name_set
                or agent.config.name.lower() in agent_name_set
            ]
            if not self.agents:
                # No matches found, use all agents
                self.agents = self.all_agents
        else:
            self.agents = self.all_agents
        self.graph = self._build_graph()
        self.logger = logging.getLogger("pipeline")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph for the pipeline."""

        # Create the state graph
        workflow = StateGraph(PipelineState)

        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("run_agents", self._run_agents_node)
        workflow.add_node("consolidate", self._consolidate_node)
        workflow.add_node("generate_report", self._generate_report_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Add edges
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "run_agents")
        workflow.add_conditional_edges(
            "run_agents",
            self._check_agent_errors,
            {
                "success": "consolidate",
                "error": "handle_error",
            },
        )
        workflow.add_edge("consolidate", "generate_report")
        workflow.add_edge("generate_report", END)
        workflow.add_edge("handle_error", END)

        return workflow.compile()

    async def _initialize_node(self, state: PipelineState) -> PipelineState:
        """Initialize the pipeline state."""
        self.logger.info(f"Initializing review for {len(state['files'])} files")

        return {
            **state,
            "status": ReviewStatus.IN_PROGRESS.value,
            "current_agent_index": 0,
            "agent_responses": [],
            "has_blocking_issues": False,
        }

    async def _run_agents_node(self, state: PipelineState) -> PipelineState:
        """Run all expert agents on the files."""
        self.logger.info(f"Running {len(self.agents)} expert agents")

        files = state["files"]
        context = state.get("context", {})
        responses: list[AgentResponse] = []

        if self.parallel and self.settings.parallel_agents:
            # Run agents in parallel
            tasks = [agent.review(files, context) for agent in self.agents]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for agent, result in zip(self.agents, results, strict=False):
                if isinstance(result, Exception):
                    self.logger.error(f"Agent {agent.config.name} failed: {result}")
                    responses.append(
                        AgentResponse(
                            agent_name=agent.config.name,
                            timestamp=datetime.now(),
                            files_reviewed=[],
                            findings=[],
                            summary="",
                            error=str(result),
                        )
                    )
                elif isinstance(result, AgentResponse):
                    responses.append(result)
        else:
            # Run agents sequentially
            for i, agent in enumerate(self.agents, 1):
                print(f"  [{i}/{len(self.agents)}] Running {agent.config.name}...", flush=True)
                try:
                    response = await agent.review(files, context)
                    responses.append(response)
                    print(
                        f"  [{i}/{len(self.agents)}] {agent.config.name} ✓ ({response.execution_time_seconds:.1f}s)",
                        flush=True,
                    )
                except Exception as e:
                    self.logger.error(f"Agent {agent.config.name} failed: {e}")
                    print(f"  [{i}/{len(self.agents)}] {agent.config.name} ✗ (error)", flush=True)
                    responses.append(
                        AgentResponse(
                            agent_name=agent.config.name,
                            timestamp=datetime.now(),
                            files_reviewed=[],
                            findings=[],
                            summary="",
                            error=str(e),
                        )
                    )

        # Check for blocking issues
        has_blocking = any(r.has_blocking_issues for r in responses)

        return {
            **state,
            "agent_responses": [r.to_dict() for r in responses],
            "has_blocking_issues": has_blocking,
        }

    def _check_agent_errors(self, state: PipelineState) -> str:
        """Check if there were any critical errors during agent execution."""
        responses = state.get("agent_responses", [])

        # Check if all agents failed
        all_failed = all(r.get("error") for r in responses)

        if all_failed:
            return "error"
        return "success"

    async def _consolidate_node(self, state: PipelineState) -> PipelineState:
        """Consolidate findings from all agents."""
        self.logger.info("Consolidating agent findings")

        # Findings are already in the agent_responses
        return state

    async def _generate_report_node(self, state: PipelineState) -> PipelineState:
        """Generate the final review report."""
        self.logger.info("Generating final report")

        responses = state["agent_responses"]
        has_blocking = state["has_blocking_issues"]

        # Generate markdown report
        report = self._generate_markdown_report(responses, has_blocking)

        # Save report if configured
        if self.settings.save_reports:
            self._save_report(report)

        return {
            **state,
            "status": ReviewStatus.COMPLETED.value,
            "final_report": report,
        }

    async def _handle_error_node(self, state: PipelineState) -> PipelineState:
        """Handle pipeline errors."""
        self.logger.error("Pipeline encountered errors")

        return {
            **state,
            "status": ReviewStatus.FAILED.value,
            "error": "All agents failed to execute",
        }

    def _generate_markdown_report(self, responses: list[dict], has_blocking: bool) -> str:
        """Generate a markdown report from agent responses."""

        lines = [
            "# Code Review Report",
            f"\n**Generated:** {datetime.now().isoformat()}",
            f"\n**Status:** {'⛔ BLOCKING ISSUES FOUND' if has_blocking else '✅ Review Complete'}",
            "\n---\n",
        ]

        # Summary section
        total_findings = sum(len(r.get("findings", [])) for r in responses)
        lines.append("## Summary\n")
        lines.append(f"- **Total Findings:** {total_findings}")
        lines.append(f"- **Agents Executed:** {len(responses)}\n")

        # Severity breakdown
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for response in responses:
            for finding in response.get("findings", []):
                severity = finding.get("severity", "info")
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

        lines.append("### Findings by Severity\n")
        lines.append(f"- 🔴 Critical: {severity_counts['critical']}")
        lines.append(f"- 🟠 High: {severity_counts['high']}")
        lines.append(f"- 🟡 Medium: {severity_counts['medium']}")
        lines.append(f"- 🔵 Low: {severity_counts['low']}")
        lines.append(f"- ⚪ Info: {severity_counts['info']}\n")

        # Agent sections
        lines.append("---\n")

        for response in responses:
            agent_name = response.get("agent_name", "Unknown Agent")
            findings = response.get("findings", [])
            summary = response.get("summary", "")
            error = response.get("error")

            lines.append(f"## {agent_name.replace('_', ' ').title()}\n")

            if error:
                lines.append(f"⚠️ **Error:** {error}\n")
                continue

            if not findings:
                lines.append("✅ No issues found.\n")
                continue

            lines.append(f"*{summary}*\n")

            # Group findings by severity
            for severity in ["critical", "high", "medium", "low", "info"]:
                severity_findings = [f for f in findings if f.get("severity") == severity]
                if not severity_findings:
                    continue

                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵",
                    "info": "⚪",
                }.get(severity, "⚪")

                lines.append(f"\n### {severity_emoji} {severity.upper()} Severity\n")

                for finding in severity_findings:
                    title = finding.get("title", "Untitled")
                    description = finding.get("description", "")
                    file_path = finding.get("file_path")
                    line_number = finding.get("line_number")
                    suggested_fix = finding.get("suggested_fix")

                    lines.append(f"#### {title}\n")

                    if file_path:
                        location = f"`{file_path}`"
                        if line_number:
                            location += f" (line {line_number})"
                        lines.append(f"**Location:** {location}\n")

                    lines.append(f"{description}\n")

                    if suggested_fix:
                        lines.append(f"\n**Suggested Fix:**\n```\n{suggested_fix}\n```\n")

            lines.append("\n---\n")

        return "\n".join(lines)

    def _save_report(self, report: str) -> str:
        """Save the report to a file."""
        import os

        os.makedirs(self.settings.reports_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"review_report_{timestamp}.md"
        filepath = os.path.join(self.settings.reports_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        self.logger.info(f"Report saved to {filepath}")
        return filepath

    async def run(
        self, files: dict[str, str], context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        Run the review pipeline.

        Args:
            files: Dictionary mapping file paths to their contents
            context: Optional context (git diff, commit message, etc.)

        Returns:
            ReviewResult with consolidated findings
        """
        import time

        start_time = time.time()

        # Initialize state
        initial_state: PipelineState = {
            "files": files,
            "context": context or {},
            "current_agent_index": 0,
            "agent_responses": [],
            "status": ReviewStatus.PENDING.value,
            "final_report": None,
            "has_blocking_issues": False,
            "error": None,
        }

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)

        # Build result
        agent_responses = []
        all_findings = []

        for response_dict in final_state.get("agent_responses", []):
            # Reconstruct AgentResponse (simplified)
            findings = []
            for f in response_dict.get("findings", []):
                from agents.base_agent import FindingCategory

                finding = ReviewFinding(
                    category=FindingCategory(f.get("category", "quality")),
                    severity=Severity(f.get("severity", "info")),
                    title=f.get("title", ""),
                    description=f.get("description", ""),
                    file_path=f.get("file_path"),
                    line_number=f.get("line_number"),
                    suggested_fix=f.get("suggested_fix"),
                    code_snippet=f.get("code_snippet"),
                )
                findings.append(finding)
                all_findings.append(finding)

            agent_response = AgentResponse(
                agent_name=response_dict.get("agent_name", ""),
                timestamp=datetime.fromisoformat(
                    response_dict.get("timestamp", datetime.now().isoformat())
                ),
                files_reviewed=response_dict.get("files_reviewed", []),
                findings=findings,
                summary=response_dict.get("summary", ""),
                execution_time_seconds=response_dict.get("execution_time_seconds", 0),
                error=response_dict.get("error"),
            )
            agent_responses.append(agent_response)

        # Generate summary
        status = ReviewStatus(final_state.get("status", ReviewStatus.FAILED.value))
        summary = self._generate_summary(all_findings, status)

        return ReviewResult(
            status=status,
            agent_responses=agent_responses,
            consolidated_findings=all_findings,
            summary=summary,
            total_execution_time=time.time() - start_time,
        )

    def _generate_summary(self, findings: list[ReviewFinding], status: ReviewStatus) -> str:
        """Generate an executive summary of the review."""
        if status == ReviewStatus.FAILED:
            return "Review pipeline failed. Please check the logs for details."

        if not findings:
            return "No issues found. The code looks good!"

        critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in findings if f.severity == Severity.HIGH)
        medium = sum(1 for f in findings if f.severity == Severity.MEDIUM)
        low = sum(1 for f in findings if f.severity == Severity.LOW)

        parts = [f"Found {len(findings)} issue(s): "]

        if critical > 0:
            parts.append(f"{critical} critical")
        if high > 0:
            parts.append(f"{high} high")
        if medium > 0:
            parts.append(f"{medium} medium")
        if low > 0:
            parts.append(f"{low} low")

        if critical > 0 or high > 0:
            parts.append(". ⚠️ BLOCKING ISSUES require immediate attention.")

        return ", ".join(parts[1:]) if len(parts) > 1 else parts[0]
