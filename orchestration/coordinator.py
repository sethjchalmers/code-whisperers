"""
Coordinator for managing agent-to-agent communication and workflow.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from agents.base_agent import AgentResponse, ReviewFinding, Severity
from agents.expert_agents import create_all_agents
from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorConfig:
    """Configuration for the agent coordinator."""

    max_iterations: int = 3  # Max rounds of agent communication
    consensus_threshold: float = 0.8  # Agreement threshold for findings
    enable_cross_validation: bool = True  # Agents validate each other's findings
    escalation_on_critical: bool = True  # Escalate critical findings


class AgentCoordinator:
    """
    Coordinates communication between expert agents.

    Features:
    - Cross-validation: Agents can review each other's findings
    - Consensus building: Aggregate similar findings
    - Escalation: Route critical issues to appropriate handlers
    - Conflict resolution: Handle disagreements between agents
    """

    def __init__(self, config: CoordinatorConfig | None = None):
        self.config = config or CoordinatorConfig()
        self.settings = get_settings()
        self.agents = create_all_agents()
        self.logger = logging.getLogger("coordinator")

    async def coordinate_review(
        self,
        files: dict[str, str],
        context: dict[str, Any] | None = None,
        cross_validate: bool = True,
    ) -> dict[str, Any]:
        """
        Coordinate a full review with agent collaboration.

        Args:
            files: Files to review
            context: Additional context
            cross_validate: Whether to have agents validate each other

        Returns:
            Coordinated review results
        """
        self.logger.info("Starting coordinated review")

        # Phase 1: Initial parallel review
        initial_responses = await self._run_parallel_review(files, context)

        # Phase 2: Cross-validation (optional)
        if cross_validate and self.config.enable_cross_validation:
            validated_responses = await self._cross_validate(initial_responses, files, context)
        else:
            validated_responses = initial_responses

        # Phase 3: Consolidate and deduplicate findings
        consolidated = self._consolidate_findings(validated_responses)

        # Phase 4: Build consensus on severity
        consensus_findings = self._build_consensus(consolidated)

        # Phase 5: Escalation check
        if self.config.escalation_on_critical:
            escalations = self._check_escalations(consensus_findings)
        else:
            escalations = []

        return {
            "agent_responses": [r.to_dict() for r in validated_responses],
            "consolidated_findings": [f.to_dict() for f in consensus_findings],
            "escalations": escalations,
            "summary": self._generate_coordinator_summary(
                validated_responses, consensus_findings, escalations
            ),
        }

    async def _run_parallel_review(
        self, files: dict[str, str], context: dict[str, Any] | None
    ) -> list[AgentResponse]:
        """Run all agents in parallel."""
        tasks = [agent.review(files, context) for agent in self.agents]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses: list[AgentResponse] = []
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

        return responses

    async def _cross_validate(
        self,
        responses: list[AgentResponse],
        files: dict[str, str],
        context: dict[str, Any] | None,
    ) -> list[AgentResponse]:
        """
        Have agents validate each other's critical/high findings.

        This helps reduce false positives and catch hallucinations.
        """
        self.logger.info("Starting cross-validation phase")

        # Collect high-priority findings for validation
        priority_findings = []
        for response in responses:
            for finding in response.findings:
                if finding.severity in [Severity.CRITICAL, Severity.HIGH]:
                    priority_findings.append(
                        {
                            "source_agent": response.agent_name,
                            "finding": finding,
                        }
                    )

        if not priority_findings:
            self.logger.info("No priority findings to cross-validate")
            return responses

        # For now, we'll mark findings as validated
        # In a full implementation, you'd have other agents review these
        # and potentially adjust severity based on agreement

        return responses

    def _consolidate_findings(self, responses: list[AgentResponse]) -> list[ReviewFinding]:
        """
        Consolidate findings from all agents.

        - Deduplicate similar findings
        - Merge related issues
        - Track which agents reported each issue
        """
        all_findings: list[ReviewFinding] = []
        finding_map: dict[tuple[str, str, str], ReviewFinding] = {}

        for response in responses:
            for finding in response.findings:
                # Create a key for deduplication
                key = (
                    finding.file_path,
                    finding.category.value,
                    finding.title.lower()[:50],  # First 50 chars of title
                )

                if key in finding_map:
                    # Merge with existing finding
                    existing = finding_map[key]
                    # Keep the higher severity
                    if self._severity_rank(finding.severity) > self._severity_rank(
                        existing.severity
                    ):
                        existing.severity = finding.severity
                    # Append to description if different
                    if finding.description not in existing.description:
                        existing.description += f"\n\n[Additional context from {response.agent_name}]: {finding.description}"
                else:
                    finding_map[key] = finding
                    all_findings.append(finding)

        return all_findings

    def _severity_rank(self, severity: Severity) -> int:
        """Get numeric rank for severity comparison."""
        ranks = {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }
        return ranks.get(severity, 0)

    def _build_consensus(self, findings: list[ReviewFinding]) -> list[ReviewFinding]:
        """
        Build consensus on findings based on multiple agent reports.

        Findings reported by multiple agents get higher confidence.
        """
        # For now, return findings as-is
        # In a full implementation, you'd adjust confidence scores
        return findings

    def _check_escalations(self, findings: list[ReviewFinding]) -> list[dict]:
        """
        Check for findings that need escalation.

        Returns a list of escalation actions.
        """
        escalations = []

        for finding in findings:
            if finding.severity == Severity.CRITICAL:
                escalation = {
                    "type": "critical_finding",
                    "finding": finding.to_dict(),
                    "recommended_action": "Immediate review required",
                    "suggested_escalation": [
                        "Block PR merge",
                        "Notify security team",
                        "Create incident ticket",
                    ],
                }
                escalations.append(escalation)

            # Check for specific escalation patterns
            if finding.category.value == "security" and "secret" in finding.description.lower():
                escalation = {
                    "type": "potential_secret_exposure",
                    "finding": finding.to_dict(),
                    "recommended_action": "Immediate secret rotation may be required",
                    "suggested_escalation": [
                        "Rotate affected credentials",
                        "Audit access logs",
                        "Notify security team",
                    ],
                }
                escalations.append(escalation)

        return escalations

    def _generate_coordinator_summary(
        self, responses: list[AgentResponse], findings: list[ReviewFinding], escalations: list[dict]
    ) -> str:
        """Generate a coordinator summary."""
        lines = [
            "## Coordinator Summary\n",
            f"- **Agents Executed:** {len(responses)}",
            f"- **Total Consolidated Findings:** {len(findings)}",
            f"- **Escalations Required:** {len(escalations)}",
        ]

        # Severity breakdown
        severity_counts: dict[str, int] = {}
        for f in findings:
            severity_counts[f.severity.value] = severity_counts.get(f.severity.value, 0) + 1

        lines.append("\n### Severity Distribution")
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                lines.append(f"- {severity.upper()}: {count}")

        if escalations:
            lines.append("\n### ⚠️ Escalations")
            for esc in escalations:
                lines.append(f"- **{esc['type']}**: {esc['recommended_action']}")

        return "\n".join(lines)

    async def validate_finding(
        self, finding: ReviewFinding, files: dict[str, str], validating_agents: list[str]
    ) -> dict[str, Any]:
        """
        Have specific agents validate a single finding.

        Useful for getting second opinions on critical issues.
        """
        validation_results = {}

        for agent in self.agents:
            if agent.config.name in validating_agents:
                # Create a focused validation prompt
                context = {
                    "validation_request": True,
                    "original_finding": finding.to_dict(),
                }

                response = await agent.review(files, context)

                # Check if the agent agrees with the finding
                validation_results[agent.config.name] = {
                    "response": response.to_dict(),
                    "agrees": self._check_agreement(finding, response),
                }

        return validation_results

    def _check_agreement(self, original: ReviewFinding, validation_response: AgentResponse) -> bool:
        """Check if the validation response agrees with the original finding."""
        # Simple check: look for similar findings in the response
        for finding in validation_response.findings:
            if finding.category == original.category and finding.file_path == original.file_path:
                return True
        return False
