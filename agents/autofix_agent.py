"""
Auto-fix agent that applies fixes for review findings.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage

from agents.base_agent import BaseAgent, ReviewFinding
from config.agent_config import AgentConfig
from config.settings import get_settings

logger = logging.getLogger(__name__)


AUTOFIX_SYSTEM_PROMPT = """You are a code fixer. Your job is to fix issues identified in code reviews.

For each issue, you will receive:
1. The file path and content
2. The issue description and suggested fix
3. The line number (if available)

Return ONLY valid JSON with the fix. No markdown, no explanation outside JSON:

{
    "file_path": "path/to/file.py",
    "original_code": "the exact code to replace (copy verbatim from file)",
    "fixed_code": "the corrected code",
    "explanation": "brief explanation of the fix"
}

CRITICAL RULES:
- Copy the original_code EXACTLY as it appears in the file (whitespace matters!)
- Include the entire line or lines that need to be changed
- If the issue is on a specific line, include that COMPLETE line as original_code
- If you cannot fix the issue, return: {"file_path": "...", "skip": true, "reason": "why"}
- Only fix ONE issue at a time
- For security issues like hardcoded credentials, replace with environment variables or config
"""

AUTOFIX_LITE_PROMPT = """Fix code issues. Return ONLY JSON:
{"file_path": "file.py", "original_code": "exact COMPLETE line(s) to replace", "fixed_code": "fixed code", "explanation": "brief why"}
If can't fix: {"file_path": "file.py", "skip": true, "reason": "why"}

IMPORTANT: Copy the COMPLETE LINE from the file exactly as shown. Include the whole line, not just part of it."""


@dataclass
class FixResult:
    """Result of attempting to fix an issue."""

    finding: ReviewFinding
    success: bool
    file_path: str | None = None
    original_code: str | None = None
    fixed_code: str | None = None
    explanation: str | None = None
    error: str | None = None


class AutofixAgent:
    """Agent that automatically fixes issues found during code review."""

    def __init__(self):
        self.settings = get_settings()
        self.config = AgentConfig(
            name="autofix_agent",
            description="Automatically fixes code review issues",
            system_prompt=AUTOFIX_SYSTEM_PROMPT,
            file_patterns=["*"],  # Can fix any file
        )
        # Create a temporary BaseAgent-like object for LLM access
        self._base = _AutofixBaseAgent(self.config)
        self.logger = logging.getLogger("autofix")

    async def fix_findings(
        self, findings: list[ReviewFinding], files: dict[str, str], repo_path: str | None = None
    ) -> list[FixResult]:
        """
        Attempt to fix all findings.

        Args:
            findings: List of review findings to fix
            files: Dictionary of file_path -> content
            repo_path: Optional path to repository root

        Returns:
            List of FixResult objects
        """
        results = []

        # Group findings by file for efficiency
        findings_by_file: dict[str, list[ReviewFinding]] = {}
        for finding in findings:
            if finding.file_path:
                if finding.file_path not in findings_by_file:
                    findings_by_file[finding.file_path] = []
                findings_by_file[finding.file_path].append(finding)

        # Track which files have been modified (to re-read updated content)
        modified_files: dict[str, str] = dict(files)

        total = len(findings)
        for idx, finding in enumerate(findings, 1):
            if not finding.file_path:
                results.append(
                    FixResult(
                        finding=finding, success=False, error="No file path specified for finding"
                    )
                )
                continue

            print(f"  [{idx}/{total}] Fixing: {finding.title[:50]}...", flush=True)

            # Get current file content (may have been modified)
            file_content = modified_files.get(finding.file_path)
            if not file_content and repo_path:
                # Try to read from disk
                full_path = os.path.join(repo_path, finding.file_path)
                if os.path.exists(full_path):
                    with open(full_path, encoding="utf-8") as f:
                        file_content = f.read()
                    modified_files[finding.file_path] = file_content

            if not file_content:
                results.append(
                    FixResult(
                        finding=finding,
                        success=False,
                        file_path=finding.file_path,
                        error=f"Could not read file: {finding.file_path}",
                    )
                )
                continue

            # Generate fix
            result = await self._generate_fix(finding, file_content)
            results.append(result)

            # If successful, apply the fix and update our tracking
            if result.success and result.original_code and result.fixed_code:
                applied = False

                # Try exact match first
                if result.original_code in file_content:
                    new_content = file_content.replace(result.original_code, result.fixed_code, 1)
                    applied = True
                else:
                    # Try normalized matching (strip whitespace from both)
                    orig_normalized = result.original_code.strip()
                    if orig_normalized in file_content:
                        new_content = file_content.replace(
                            orig_normalized, result.fixed_code.strip(), 1
                        )
                        applied = True
                    else:
                        # Try line-based matching if we have a line number
                        if finding.line_number:
                            lines = file_content.split("\n")
                            if 1 <= finding.line_number <= len(lines):
                                # Find the line and replace
                                target_line = lines[finding.line_number - 1]
                                orig_lines = result.original_code.strip().split("\n")
                                fixed_lines = result.fixed_code.strip().split("\n")

                                # Try to match just the target line
                                for i, orig_line in enumerate(orig_lines):
                                    if (
                                        orig_line.strip() in target_line
                                        or target_line.strip() in orig_line
                                    ):
                                        # Found it - replace this line
                                        if i < len(fixed_lines):
                                            lines[finding.line_number - 1] = fixed_lines[i]
                                        else:
                                            lines[finding.line_number - 1] = (
                                                "# REMOVED: " + target_line
                                            )
                                        new_content = "\n".join(lines)
                                        applied = True
                                        break

                if applied:
                    modified_files[finding.file_path] = new_content

                    # Write to disk
                    if repo_path:
                        full_path = os.path.join(repo_path, finding.file_path)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"      ✓ Applied fix to {finding.file_path}", flush=True)
                else:
                    result.success = False
                    result.error = (
                        "Original code not found in file (may have already been modified)"
                    )
                    print("      ✗ Could not apply: code not found", flush=True)

        return results

    async def _generate_fix(self, finding: ReviewFinding, file_content: str) -> FixResult:
        """Generate a fix for a single finding."""
        try:
            # Build prompt
            prompt = f"""Fix this issue in the code:

## File: {finding.file_path}
```
{file_content}
```

## Issue to Fix
- **Title**: {finding.title}
- **Severity**: {finding.severity.value}
- **Description**: {finding.description}
"""
            if finding.line_number:
                prompt += f"- **Line Number**: {finding.line_number}\n"
            if finding.suggested_fix:
                prompt += f"- **Suggested Fix**: {finding.suggested_fix}\n"
            if finding.code_snippet:
                prompt += f"- **Problematic Code**:\n```\n{finding.code_snippet}\n```\n"

            prompt += "\nReturn the fix as JSON."

            # Use lite prompt for Ollama
            use_lite = self.settings.lite_prompts or self.settings.llm_provider == "ollama"
            system_prompt = AUTOFIX_LITE_PROMPT if use_lite else AUTOFIX_SYSTEM_PROMPT

            # Call LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt),
            ]

            response = await self._base.llm.ainvoke(messages)
            raw_response = response.content

            # Parse response
            return self._parse_fix_response(raw_response, finding)

        except Exception as e:
            self.logger.exception(f"Error generating fix: {e}")
            return FixResult(
                finding=finding, success=False, file_path=finding.file_path, error=str(e)
            )

    def _parse_fix_response(self, raw_response: str, finding: ReviewFinding) -> FixResult:
        """Parse the LLM response into a FixResult."""
        try:
            # Extract JSON from response
            json_str = raw_response.strip()

            # Handle markdown code blocks
            if "```json" in raw_response:
                start = raw_response.find("```json") + 7
                end = raw_response.find("```", start)
                json_str = raw_response[start:end].strip()
            elif "```" in raw_response:
                start = raw_response.find("```") + 3
                end = raw_response.find("```", start)
                json_str = raw_response[start:end].strip()

            # Try to find JSON object in the response
            if not json_str.startswith("{"):
                # Look for JSON object anywhere in the string
                start = raw_response.find("{")
                end = raw_response.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = raw_response[start:end]

            # Clean up common JSON issues
            # Remove trailing commas before closing braces
            import re

            json_str = re.sub(r",\s*}", "}", json_str)
            json_str = re.sub(r",\s*]", "]", json_str)

            data = json.loads(json_str)

            # Check if skipped
            if data.get("skip"):
                return FixResult(
                    finding=finding,
                    success=False,
                    file_path=data.get("file_path", finding.file_path),
                    error=data.get("reason", "Fix skipped by agent"),
                )

            return FixResult(
                finding=finding,
                success=True,
                file_path=data.get("file_path", finding.file_path),
                original_code=data.get("original_code"),
                fixed_code=data.get("fixed_code"),
                explanation=data.get("explanation"),
            )

        except json.JSONDecodeError as e:
            return FixResult(
                finding=finding,
                success=False,
                file_path=finding.file_path,
                error=f"Failed to parse LLM response: {e}",
            )


class _AutofixBaseAgent(BaseAgent):
    """Internal helper to get LLM instance."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)

    def get_expert_context(self) -> str:
        return ""


def open_vscode_git_view():
    """Open VS Code's Source Control view to show changes."""
    try:
        # Use VS Code CLI to focus the Source Control view
        # On Windows, use code.cmd
        import platform

        code_cmd = "code.cmd" if platform.system() == "Windows" else "code"
        subprocess.run(
            [code_cmd, "--command", "workbench.view.scm"],
            check=False,
            capture_output=True,
            shell=True,  # Needed for Windows to find code.cmd in PATH
        )
        print("\n📝 Opening VS Code Source Control view...", flush=True)
        print("   Review your changes in the Git panel.", flush=True)
    except Exception as e:
        logger.warning(f"Could not open VS Code: {e}")
        print("\n📝 Review your changes with: git diff", flush=True)


def show_git_diff_summary(repo_path: str):
    """Show a summary of changes made."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"], cwd=repo_path, capture_output=True, text=True, check=False
        )
        if result.stdout:
            print("\n📊 Changes Summary:")
            print(result.stdout)
    except Exception as e:
        logger.warning(f"Could not get git diff: {e}")
