"""
Command-line interface for the agent-to-agent code review pipeline.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from git_integration import GitIntegration
from orchestration import AgentCoordinator, ReviewPipeline
from testing import CodeValidator, TestRunner
from testing.test_runner import TestStatus


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the CLI."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Agent-to-Agent Code Review Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Review changed files in current branch vs main
  python -m cli.main review --base main

  # Review specific files
  python -m cli.main review --files src/main.py src/utils.py

  # Review with git diff context
  python -m cli.main review --diff HEAD~3..HEAD

  # Run with specific agents only
  python -m cli.main review --agents terraform python security

  # Validate files without AI review
  python -m cli.main validate --files *.tf *.py

  # Run tests on changed files
  python -m cli.main test --base main
        """,
    )

    parser.add_argument("--version", action="version", version="agent-to-agent 0.1.0")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Review command
    review_parser = subparsers.add_parser("review", help="Run AI-powered code review")
    review_parser.add_argument("--files", "-f", nargs="+", help="Specific files to review")
    review_parser.add_argument(
        "--base", "-b", default="main", help="Base branch/commit for diff (default: main)"
    )
    review_parser.add_argument(
        "--head", default="HEAD", help="Head branch/commit for diff (default: HEAD)"
    )
    review_parser.add_argument("--diff", help="Git diff range (e.g., HEAD~3..HEAD)")
    review_parser.add_argument(
        "--repo", "-r", help="Path to git repository (default: current directory)"
    )
    review_parser.add_argument(
        "--agents",
        "-a",
        nargs="+",
        choices=[
            "terraform",
            "gitops",
            "jenkins",
            "python",
            "security",
            "cost",
            "clean_code",
            "aws",
        ],
        help="Specific agents to run",
    )
    review_parser.add_argument(
        "--parallel",
        action="store_true",
        default=True,
        help="Run agents in parallel (default: True)",
    )
    review_parser.add_argument("--sequential", action="store_true", help="Run agents sequentially")
    review_parser.add_argument("--output", "-o", help="Output file for report (default: stdout)")
    review_parser.add_argument(
        "--format",
        choices=["markdown", "json", "text"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    review_parser.add_argument(
        "--include-codebase",
        action="store_true",
        help="Include relevant codebase context in review",
    )
    review_parser.add_argument(
        "--no-repo-context",
        action="store_true",
        help="Skip including repo context files (.gitignore, pyproject.toml, etc.)",
    )
    review_parser.add_argument(
        "--cross-validate", action="store_true", help="Enable cross-validation between agents"
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate files without AI review")
    validate_parser.add_argument(
        "--files", "-f", nargs="+", required=True, help="Files to validate"
    )
    validate_parser.add_argument("--repo", "-r", help="Path to repository")
    validate_parser.add_argument("--output", "-o", help="Output file")
    validate_parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="Output format"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests on files")
    test_parser.add_argument("--files", "-f", nargs="+", help="Specific files to test")
    test_parser.add_argument("--base", "-b", default="main", help="Base branch for changed files")
    test_parser.add_argument("--repo", "-r", help="Path to repository")
    test_parser.add_argument(
        "--types",
        "-t",
        nargs="+",
        choices=["python", "terraform", "kubernetes", "jenkins"],
        help="Specific test types to run",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Show or modify configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")
    config_parser.add_argument("--validate", action="store_true", help="Validate configuration")

    # Common arguments
    for subparser in [review_parser, validate_parser, test_parser]:
        subparser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
        subparser.add_argument("--quiet", "-q", action="store_true", help="Quiet output")

    return parser


async def run_review(args) -> int:
    """Run the code review command."""
    settings = get_settings()

    # Validate settings
    errors = settings.validate()
    if errors:
        for error in errors:
            print(f"Configuration error: {error}", file=sys.stderr)
        return 1

    # Initialize git integration
    repo_path = args.repo or os.getcwd()
    git = GitIntegration(repo_path)

    # Collect files to review
    if args.files:
        files = git.collect_files_by_paths(args.files)
    else:
        # Get changed files
        base_ref = args.base
        head_ref = args.head

        if args.diff:
            # Parse diff range
            if ".." in args.diff:
                base_ref, head_ref = args.diff.split("..", 1)
            else:
                base_ref = args.diff

        files = git.collect_changed_files_content(base_ref, head_ref)

    if not files:
        print("No files to review.", file=sys.stderr)
        return 0

    print(f"Reviewing {len(files)} file(s)...")

    # Collect context (optionally including repo context files)
    include_repo_context = not getattr(args, "no_repo_context", False)
    context = git.collect_context(args.base, args.head, include_repo_context=include_repo_context)

    # Include codebase context if requested
    if args.include_codebase:
        codebase_files = git.collect_codebase_files()
        context["codebase_files"] = codebase_files

    # Run review
    parallel = not args.sequential if hasattr(args, "sequential") else args.parallel

    if args.cross_validate:
        coordinator = AgentCoordinator()
        coord_result = await coordinator.coordinate_review(files, context, cross_validate=True)

        # Format output
        if args.format == "json":
            output = json.dumps(coord_result, indent=2)
        else:
            output = coord_result.get("summary", "")
            for response in coord_result.get("agent_responses", []):
                output += f"\n\n## {response.get('agent_name', 'Unknown')}\n"
                output += response.get("summary", "")
    else:
        pipeline = ReviewPipeline(parallel=parallel)
        result = await pipeline.run(files, context)

        # Format output
        if args.format == "json":
            output = json.dumps(result.to_dict(), indent=2)
        elif args.format == "text":
            output = result.summary
            for response in result.agent_responses:
                output += f"\n\n{response.agent_name}: {response.summary}"
        else:
            # Markdown format - generate full report
            output = generate_markdown_report(result)

    # Output results
    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)

    # Return non-zero if blocking issues found
    if hasattr(result, "has_critical_issues") and result.has_critical_issues:
        return 1

    return 0


def generate_markdown_report(result) -> str:
    """Generate a markdown report from review result."""
    lines = [
        "# Code Review Report\n",
        f"**Status:** {result.status.value}",
        f"**Execution Time:** {result.total_execution_time:.2f}s\n",
        "---\n",
        "## Summary\n",
        result.summary,
        "\n---\n",
    ]

    # Findings by severity
    for severity in ["critical", "high", "medium", "low", "info"]:
        severity_findings = [
            f for f in result.consolidated_findings if f.severity.value == severity
        ]
        if severity_findings:
            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(
                severity, "⚪"
            )
            lines.append(f"\n## {emoji} {severity.upper()} ({len(severity_findings)})\n")

            for finding in severity_findings:
                lines.append(f"### {finding.title}\n")
                if finding.file_path:
                    lines.append(f"**File:** `{finding.file_path}`")
                    if finding.line_number:
                        lines.append(f" (line {finding.line_number})")
                    lines.append("\n")
                lines.append(f"\n{finding.description}\n")
                if finding.suggested_fix:
                    lines.append(f"\n**Suggested Fix:**\n```\n{finding.suggested_fix}\n```\n")

    # Agent details
    lines.append("\n---\n")
    lines.append("## Agent Details\n")

    for response in result.agent_responses:
        lines.append(f"\n### {response.agent_name.replace('_', ' ').title()}\n")
        lines.append(f"- Files Reviewed: {len(response.files_reviewed)}")
        lines.append(f"- Findings: {len(response.findings)}")
        lines.append(f"- Execution Time: {response.execution_time_seconds:.2f}s")
        if response.error:
            lines.append(f"- ⚠️ Error: {response.error}")
        lines.append("\n")

    return "\n".join(lines)


async def run_validate(args) -> int:
    """Run the validation command."""
    repo_path = args.repo or os.getcwd()
    git = GitIntegration(repo_path)

    # Collect files
    files = git.collect_files_by_paths(args.files)

    if not files:
        print("No files found to validate.", file=sys.stderr)
        return 1

    print(f"Validating {len(files)} file(s)...")

    # Run validation
    validator = CodeValidator()
    results = validator.validate_files(files)
    summary = validator.get_validation_summary(results)

    # Output results
    if args.format == "json":
        output = json.dumps(
            {
                "summary": summary,
                "results": [r.to_dict() for r in results],
            },
            indent=2,
        )
    else:
        output = "Validation Summary:\n"
        output += f"  Total Files: {summary['total_files']}\n"
        output += f"  Valid: {summary['valid']}\n"
        output += f"  Invalid: {summary['invalid']}\n"
        output += f"  Warnings: {summary['warnings']}\n"
        output += f"  Errors: {summary['error_count']}\n"

        if summary["all_issues"]:
            output += "\nIssues:\n"
            for issue in summary["all_issues"]:
                severity = issue.get("severity", "info").upper()
                file_path = issue.get("file", "unknown")
                message = issue.get("message", "")
                line = issue.get("line_number")
                loc = f" (line {line})" if line else ""
                output += f"  [{severity}] {file_path}{loc}: {message}\n"

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Results saved to {args.output}")
    else:
        print(output)

    return 1 if summary["invalid"] > 0 else 0


async def run_test(args) -> int:
    """Run the test command."""
    repo_path = args.repo or os.getcwd()
    git = GitIntegration(repo_path)

    # Collect files
    if args.files:
        files = git.collect_files_by_paths(args.files)
    else:
        files = git.collect_changed_files_content(args.base, "HEAD")

    if not files:
        print("No files to test.", file=sys.stderr)
        return 0

    print(f"Running tests for {len(files)} file(s)...")

    # Run tests
    runner = TestRunner(repo_path)
    results = await runner.run_all_tests(files, args.types)

    # Output results
    total_passed = 0
    total_failed = 0

    for suite_name, suite in results.items():
        print(f"\n{suite_name.upper()} Tests:")
        print(f"  Passed: {suite.passed}")
        print(f"  Failed: {suite.failed}")
        print(f"  Errors: {suite.errors}")
        print(f"  Duration: {suite.total_duration:.2f}s")

        total_passed += suite.passed
        total_failed += suite.failed + suite.errors

        # Show failed tests
        for result in suite.results:
            if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                print(f"\n  ❌ {result.name}")
                if result.error_message:
                    print(f"     Error: {result.error_message[:200]}")

    print(f"\n{'='*50}")
    print(f"Total: {total_passed} passed, {total_failed} failed")

    return 1 if total_failed > 0 else 0


def run_config(args) -> int:
    """Run the config command."""
    settings = get_settings()

    if args.show:
        print("Current Configuration:")
        print(f"  LLM Provider: {settings.llm_provider}")
        print(f"  LLM Model: {settings.llm_model}")
        print(f"  Git Repo Path: {settings.git_repo_path}")
        print(f"  Git Base Branch: {settings.git_base_branch}")
        print(f"  Max File Size: {settings.max_file_size_kb} KB")
        print(f"  Parallel Agents: {settings.parallel_agents}")
        print(f"  E2E Tests Enabled: {settings.enable_e2e_tests}")
        print(f"  Output Format: {settings.output_format}")
        print(f"  Reports Directory: {settings.reports_dir}")

    if args.validate:
        errors = settings.validate()
        if errors:
            print("Configuration Errors:")
            for error in errors:
                print(f"  ❌ {error}")
            return 1
        else:
            print("✅ Configuration is valid")

    return 0


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Setup logging
    if hasattr(args, "verbose") and args.verbose:
        setup_logging("DEBUG")
    elif hasattr(args, "quiet") and args.quiet:
        setup_logging("ERROR")
    else:
        setup_logging("INFO")

    # Run the appropriate command
    if args.command == "review":
        return asyncio.run(run_review(args))
    elif args.command == "validate":
        return asyncio.run(run_validate(args))
    elif args.command == "test":
        return asyncio.run(run_test(args))
    elif args.command == "config":
        return run_config(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
