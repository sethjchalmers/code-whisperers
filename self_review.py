"""
Self-review script for the agent-to-agent pipeline.
Runs all validators and tests to review its own implementation.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from git_integration import GitIntegration
from testing.test_runner import TestRunner
from testing.validators import CodeValidator


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")


def print_severity_icon(severity: str) -> str:
    """Get icon for severity level."""
    icons = {
        "error": "🔴",
        "warning": "🟠",
        "info": "🔵",
    }
    return icons.get(severity, "⚪")


async def run_self_review():
    """Run a comprehensive self-review of the implementation."""

    print_header("🤖 Agent-to-Agent Pipeline Self-Review")
    print(f"Started at: {datetime.now().isoformat()}\n")

    # Initialize components
    git = GitIntegration(".")
    validator = CodeValidator()
    test_runner = TestRunner(".")

    # Collect all Python files
    python_files = [
        "agents/__init__.py",
        "agents/base_agent.py",
        "agents/expert_agents.py",
        "cli/__init__.py",
        "cli/main.py",
        "config/__init__.py",
        "config/agent_config.py",
        "config/settings.py",
        "git_integration/__init__.py",
        "git_integration/git_utils.py",
        "orchestration/__init__.py",
        "orchestration/coordinator.py",
        "orchestration/pipeline.py",
        "testing/__init__.py",
        "testing/test_runner.py",
        "testing/validators.py",
    ]

    # Collect file contents
    files = git.collect_files_by_paths(python_files)

    print(f"📁 Files to review: {len(files)}")
    for f in sorted(files.keys()):
        print(f"   - {f}")

    # ==========================================================================
    # PHASE 1: Syntax Validation
    # ==========================================================================
    print_header("📋 Phase 1: Syntax & Structure Validation")

    validation_results = validator.validate_files(files)
    summary = validator.get_validation_summary(validation_results)

    print(f"Total Files: {summary['total_files']}")
    print(f"✅ Valid: {summary['valid']}")
    print(f"❌ Invalid: {summary['invalid']}")
    print(f"⚠️  With Warnings: {summary['warnings']}")

    if summary["all_issues"]:
        print("\n📝 Issues Found:")
        for issue in summary["all_issues"]:
            icon = print_severity_icon(issue.get("severity", "info"))
            file_path = issue.get("file", "unknown")
            message = issue.get("message", "")
            line = issue.get("line_number")
            loc = f" (line {line})" if line else ""
            print(f"   {icon} [{issue.get('severity', 'info').upper()}] {file_path}{loc}")
            print(f"      {message}")
    else:
        print("\n✅ No syntax issues found!")

    # ==========================================================================
    # PHASE 2: Code Quality Analysis
    # ==========================================================================
    print_header("🔍 Phase 2: Code Quality Analysis")

    quality_findings = []

    for file_path, content in files.items():
        lines = content.split("\n")

        # Check for missing docstrings
        if not content.strip().startswith('"""'):
            quality_findings.append(
                {
                    "file": file_path,
                    "issue": "Missing module docstring",
                    "severity": "warning",
                }
            )

        # Check for long functions
        in_function = False
        func_name = ""
        func_start = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track function definitions
            if stripped.startswith("def ") or stripped.startswith("async def "):
                if in_function and (i - func_start) > 50:
                    quality_findings.append(
                        {
                            "file": file_path,
                            "line": func_start,
                            "issue": f"Function '{func_name}' is {i - func_start} lines (>50)",
                            "severity": "info",
                        }
                    )

                in_function = True
                func_start = i
                func_name = stripped.split("(")[0].replace("def ", "").replace("async ", "")

            # Check for TODO/FIXME
            if "TODO" in line or "FIXME" in line:
                quality_findings.append(
                    {
                        "file": file_path,
                        "line": i,
                        "issue": "Found TODO/FIXME comment",
                        "severity": "info",
                    }
                )

            # Check for bare except
            if stripped == "except:" or stripped.startswith("except Exception:"):
                quality_findings.append(
                    {
                        "file": file_path,
                        "line": i,
                        "issue": "Broad exception handler - consider catching specific exceptions",
                        "severity": "warning",
                    }
                )

        # Check for type hints
        import re

        functions = re.findall(r"def (\w+)\([^)]*\):", content)
        typed_functions = re.findall(r"def (\w+)\([^)]*\)\s*->", content)

        if len(functions) > len(typed_functions):
            missing = len(functions) - len(typed_functions)
            quality_findings.append(
                {
                    "file": file_path,
                    "issue": f"{missing} function(s) missing return type hints",
                    "severity": "info",
                }
            )

    if quality_findings:
        print(f"Found {len(quality_findings)} code quality suggestions:\n")
        for finding in quality_findings[:20]:  # Limit output
            icon = print_severity_icon(finding.get("severity", "info"))
            line_info = f" (line {finding['line']})" if "line" in finding else ""
            print(f"   {icon} {finding['file']}{line_info}")
            print(f"      {finding['issue']}")
    else:
        print("✅ No code quality issues found!")

    # ==========================================================================
    # PHASE 3: Security Analysis
    # ==========================================================================
    print_header("🔐 Phase 3: Security Analysis")

    security_findings = []

    for file_path, content in files.items():
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            lower_line = line.lower()

            # Check for hardcoded secrets patterns
            secret_patterns = [
                ("password", "Potential hardcoded password"),
                ("api_key", "Potential hardcoded API key"),
                ("secret", "Potential hardcoded secret"),
                ("token", "Potential hardcoded token"),
            ]

            for pattern, message in secret_patterns:
                if f"{pattern}=" in lower_line.replace(" ", "") or f"{pattern} =" in lower_line:
                    # Skip if it's a variable/parameter definition or env var access
                    if "os.getenv" in line or "environ" in line or "Optional[" in line:
                        continue
                    if "field(default" in line:
                        continue
                    if '= ""' in line or "= ''" in line or "= None" in line:
                        continue

                    # Check if value is hardcoded
                    if '= "' in line and '= ""' not in line:
                        # More specific check - is there an actual value?
                        import re

                        match = re.search(r'=\s*["\'][^"\']+["\']', line)
                        if match and "your-" not in line and "example" not in line.lower():
                            security_findings.append(
                                {
                                    "file": file_path,
                                    "line": i,
                                    "issue": message,
                                    "severity": "warning",
                                }
                            )

            # Check for dangerous eval/exec
            if "eval(" in line and "evaluate" not in line.lower():
                security_findings.append(
                    {
                        "file": file_path,
                        "line": i,
                        "issue": "Use of eval() - potential code injection risk",
                        "severity": "error",
                    }
                )
            if (
                "exec(" in line
                and "execute" not in line.lower()
                and "subprocess_exec" not in line
                and "create_subprocess_exec" not in line
            ):
                security_findings.append(
                    {
                        "file": file_path,
                        "line": i,
                        "issue": "Use of exec() - potential code injection risk",
                        "severity": "error",
                    }
                )

            # Check for shell=True in subprocess
            if "shell=True" in line:
                security_findings.append(
                    {
                        "file": file_path,
                        "line": i,
                        "issue": "subprocess with shell=True - potential command injection",
                        "severity": "warning",
                    }
                )

    if security_findings:
        print(f"Found {len(security_findings)} security considerations:\n")
        for finding in security_findings:
            icon = print_severity_icon(finding.get("severity", "warning"))
            print(f"   {icon} {finding['file']} (line {finding['line']})")
            print(f"      {finding['issue']}")
    else:
        print("✅ No security issues found!")

    # ==========================================================================
    # PHASE 4: Architecture Analysis
    # ==========================================================================
    print_header("🏗️  Phase 4: Architecture Analysis")

    # Count classes and functions per module
    print("Module structure:\n")

    import re

    for file_path, content in sorted(files.items()):
        classes = re.findall(r"^class (\w+)", content, re.MULTILINE)
        functions = re.findall(r"^(?:async )?def (\w+)", content, re.MULTILINE)
        lines = len(content.split("\n"))

        print(f"   📄 {file_path}")
        print(f"      Lines: {lines} | Classes: {len(classes)} | Functions: {len(functions)}")
        if classes:
            print(f"      Classes: {', '.join(classes)}")

    # ==========================================================================
    # PHASE 5: Unit Tests
    # ==========================================================================
    print_header("🧪 Phase 5: Unit Test Execution")

    test_files = git.collect_files_by_paths(
        [
            "tests/test_agents.py",
            "tests/test_validators.py",
            "tests/test_git_integration.py",
        ]
    )

    test_results = await test_runner.run_python_tests(test_files)

    print(f"Test Suite: {test_results.suite_name}")
    print(f"✅ Passed: {test_results.passed}")
    print(f"❌ Failed: {test_results.failed}")
    print(f"⚠️  Errors: {test_results.errors}")
    print(f"⏭️  Skipped: {test_results.skipped}")
    print(f"⏱️  Duration: {test_results.total_duration:.2f}s")

    if test_results.failed > 0 or test_results.errors > 0:
        print("\nFailed tests:")
        for result in test_results.results:
            if result.status.value in ["failed", "error"]:
                print(f"   ❌ {result.name}")
                if result.error_message:
                    print(f"      {result.error_message[:200]}")

    # ==========================================================================
    # FINAL SUMMARY
    # ==========================================================================
    print_header("📊 Final Review Summary")

    total_issues = (
        summary["error_count"]
        + summary["warning_count"]
        + len(quality_findings)
        + len(security_findings)
    )

    critical_issues = (
        summary["invalid"]
        + test_results.failed
        + test_results.errors
        + len([f for f in security_findings if f.get("severity") == "error"])
    )

    print(f"📁 Files Reviewed: {len(files)}")
    print(f"📝 Total Lines of Code: {sum(len(c.split(chr(10))) for c in files.values())}")
    print(f"🔍 Total Issues Found: {total_issues}")
    print(f"🔴 Critical Issues: {critical_issues}")
    print(
        f"🧪 Tests: {test_results.passed} passed / {test_results.failed + test_results.errors} failed"
    )

    if critical_issues == 0:
        print("\n✅ REVIEW PASSED - No critical issues found!")
        print("   The implementation is ready for use.")
    else:
        print(f"\n⚠️ REVIEW NEEDS ATTENTION - {critical_issues} critical issue(s) found")

    print(f"\nCompleted at: {datetime.now().isoformat()}")

    # Return exit code
    return 1 if critical_issues > 0 else 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_self_review())
    sys.exit(exit_code)
