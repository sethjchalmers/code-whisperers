"""
Test runner for end-to-end validation of code changes.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from config.settings import get_settings


logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Status of a test execution."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TestResult:
    """Result of a single test execution."""
    
    name: str
    status: TestStatus
    duration_seconds: float = 0.0
    output: str = ""
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "output": self.output[:1000] if self.output else "",  # Truncate
            "error_message": self.error_message,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class TestSuiteResult:
    """Result of a test suite execution."""
    
    suite_name: str
    results: list[TestResult] = field(default_factory=list)
    total_duration: float = 0.0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)
    
    @property
    def errors(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)
    
    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
    
    @property
    def success_rate(self) -> float:
        total = len(self.results)
        if total == 0:
            return 1.0
        return self.passed / total
    
    def to_dict(self) -> dict:
        return {
            "suite_name": self.suite_name,
            "results": [r.to_dict() for r in self.results],
            "total_duration": self.total_duration,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "success_rate": self.success_rate,
        }


class TestRunner:
    """
    Runs tests to validate code changes.
    
    Supports:
    - Python tests (pytest)
    - Terraform validation
    - Kubernetes manifest validation
    - Jenkins pipeline linting
    - Custom test commands
    """
    
    def __init__(self, working_dir: Optional[str] = None):
        self.settings = get_settings()
        self.working_dir = Path(working_dir or ".").resolve()
        self.logger = logging.getLogger("test_runner")
        self.timeout = self.settings.test_timeout_seconds
    
    async def run_all_tests(
        self,
        files: dict[str, str],
        test_types: Optional[list[str]] = None
    ) -> dict[str, TestSuiteResult]:
        """
        Run all applicable tests for the given files.
        
        Args:
            files: Dictionary of file paths to contents
            test_types: Specific test types to run (python, terraform, k8s, jenkins)
        
        Returns:
            Dictionary mapping test type to results
        """
        results = {}
        
        # Determine which tests to run
        if test_types is None:
            test_types = self._detect_test_types(files)
        
        for test_type in test_types:
            if test_type == "python":
                results["python"] = await self.run_python_tests(files)
            elif test_type == "terraform":
                results["terraform"] = await self.run_terraform_validation(files)
            elif test_type == "kubernetes":
                results["kubernetes"] = await self.run_kubernetes_validation(files)
            elif test_type == "jenkins":
                results["jenkins"] = await self.run_jenkins_lint(files)
        
        return results
    
    def _detect_test_types(self, files: dict[str, str]) -> list[str]:
        """Detect which test types are applicable based on file extensions."""
        types = set()
        
        for file_path in files.keys():
            if file_path.endswith(".py"):
                types.add("python")
            elif file_path.endswith(".tf") or file_path.endswith(".tfvars"):
                types.add("terraform")
            elif file_path.endswith(".yaml") or file_path.endswith(".yml"):
                # Check if it's a Kubernetes manifest
                content = files[file_path]
                if "apiVersion:" in content and "kind:" in content:
                    types.add("kubernetes")
            elif "jenkinsfile" in file_path.lower() or file_path.endswith(".groovy"):
                types.add("jenkins")
        
        return list(types)
    
    async def run_python_tests(
        self,
        files: dict[str, str],
        test_path: Optional[str] = None
    ) -> TestSuiteResult:
        """Run Python tests using pytest."""
        suite = TestSuiteResult(suite_name="python", started_at=datetime.now())
        
        # Check if pytest is available
        result = await self._run_command(["python", "-m", "pytest", "--version"])
        if result.status == TestStatus.ERROR:
            suite.results.append(TestResult(
                name="pytest_check",
                status=TestStatus.SKIPPED,
                error_message="pytest not available",
            ))
            suite.finished_at = datetime.now()
            return suite
        
        # Run pytest with JSON output
        test_args = [
            "python", "-m", "pytest",
            "-v",
            "--tb=short",
            "-q",
        ]
        
        if test_path:
            test_args.append(test_path)
        
        result = await self._run_command(test_args)
        
        # Parse pytest output
        if result.status == TestStatus.PASSED:
            suite.results.append(TestResult(
                name="pytest",
                status=TestStatus.PASSED,
                output=result.output,
                duration_seconds=result.duration_seconds,
            ))
        else:
            suite.results.append(TestResult(
                name="pytest",
                status=result.status,
                output=result.output,
                error_message=result.error_message,
                duration_seconds=result.duration_seconds,
            ))
        
        suite.finished_at = datetime.now()
        suite.total_duration = (suite.finished_at - suite.started_at).total_seconds()
        
        return suite
    
    async def run_terraform_validation(
        self,
        files: dict[str, str]
    ) -> TestSuiteResult:
        """Run Terraform validation on .tf files."""
        suite = TestSuiteResult(suite_name="terraform", started_at=datetime.now())
        
        # Find directories containing .tf files
        tf_dirs = set()
        for file_path in files.keys():
            if file_path.endswith(".tf"):
                tf_dirs.add(str(Path(file_path).parent))
        
        if not tf_dirs:
            suite.results.append(TestResult(
                name="terraform_check",
                status=TestStatus.SKIPPED,
                error_message="No Terraform files found",
            ))
            suite.finished_at = datetime.now()
            return suite
        
        for tf_dir in tf_dirs:
            dir_path = self.working_dir / tf_dir if tf_dir != "." else self.working_dir
            
            # Run terraform init (if not already initialized)
            init_result = await self._run_command(
                ["terraform", "init", "-backend=false"],
                cwd=str(dir_path)
            )
            
            if init_result.status == TestStatus.ERROR:
                suite.results.append(TestResult(
                    name=f"terraform_init_{tf_dir}",
                    status=TestStatus.ERROR,
                    error_message=init_result.error_message,
                    output=init_result.output,
                ))
                continue
            
            # Run terraform validate
            validate_result = await self._run_command(
                ["terraform", "validate", "-json"],
                cwd=str(dir_path)
            )
            
            suite.results.append(TestResult(
                name=f"terraform_validate_{tf_dir}",
                status=validate_result.status,
                output=validate_result.output,
                error_message=validate_result.error_message,
                duration_seconds=validate_result.duration_seconds,
            ))
            
            # Run terraform fmt check
            fmt_result = await self._run_command(
                ["terraform", "fmt", "-check", "-diff"],
                cwd=str(dir_path)
            )
            
            suite.results.append(TestResult(
                name=f"terraform_fmt_{tf_dir}",
                status=fmt_result.status,
                output=fmt_result.output,
                error_message=fmt_result.error_message if fmt_result.status != TestStatus.PASSED else None,
            ))
        
        suite.finished_at = datetime.now()
        suite.total_duration = (suite.finished_at - suite.started_at).total_seconds()
        
        return suite
    
    async def run_kubernetes_validation(
        self,
        files: dict[str, str]
    ) -> TestSuiteResult:
        """Validate Kubernetes manifests."""
        suite = TestSuiteResult(suite_name="kubernetes", started_at=datetime.now())
        
        # Check for kubectl
        result = await self._run_command(["kubectl", "version", "--client"])
        has_kubectl = result.status == TestStatus.PASSED
        
        # Check for kubeval
        result = await self._run_command(["kubeval", "--version"])
        has_kubeval = result.status == TestStatus.PASSED
        
        for file_path, content in files.items():
            if not (file_path.endswith(".yaml") or file_path.endswith(".yml")):
                continue
            
            # Check if it looks like a K8s manifest
            if "apiVersion:" not in content or "kind:" not in content:
                continue
            
            # Validate with kubectl dry-run if available
            if has_kubectl:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    f.write(content)
                    temp_path = f.name
                
                try:
                    result = await self._run_command([
                        "kubectl", "apply", "--dry-run=client", "-f", temp_path
                    ])
                    
                    suite.results.append(TestResult(
                        name=f"kubectl_validate_{file_path}",
                        status=result.status,
                        file_path=file_path,
                        output=result.output,
                        error_message=result.error_message,
                    ))
                finally:
                    os.unlink(temp_path)
            
            # Validate with kubeval if available
            if has_kubeval:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".yaml", delete=False
                ) as f:
                    f.write(content)
                    temp_path = f.name
                
                try:
                    result = await self._run_command([
                        "kubeval", "--strict", temp_path
                    ])
                    
                    suite.results.append(TestResult(
                        name=f"kubeval_{file_path}",
                        status=result.status,
                        file_path=file_path,
                        output=result.output,
                        error_message=result.error_message,
                    ))
                finally:
                    os.unlink(temp_path)
        
        if not suite.results:
            suite.results.append(TestResult(
                name="kubernetes_check",
                status=TestStatus.SKIPPED,
                error_message="No Kubernetes validation tools available",
            ))
        
        suite.finished_at = datetime.now()
        suite.total_duration = (suite.finished_at - suite.started_at).total_seconds()
        
        return suite
    
    async def run_jenkins_lint(
        self,
        files: dict[str, str]
    ) -> TestSuiteResult:
        """Lint Jenkins pipeline files."""
        suite = TestSuiteResult(suite_name="jenkins", started_at=datetime.now())
        
        jenkins_files = [
            f for f in files.keys()
            if "jenkinsfile" in f.lower() or f.endswith(".groovy")
        ]
        
        if not jenkins_files:
            suite.results.append(TestResult(
                name="jenkins_check",
                status=TestStatus.SKIPPED,
                error_message="No Jenkins files found",
            ))
            suite.finished_at = datetime.now()
            return suite
        
        # Check for npm-groovy-lint
        result = await self._run_command(["npm-groovy-lint", "--version"])
        has_lint = result.status == TestStatus.PASSED
        
        if not has_lint:
            # Basic syntax check - just verify Groovy structure
            for file_path in jenkins_files:
                content = files[file_path]
                
                # Basic structural validation
                issues = self._basic_jenkinsfile_check(content)
                
                if issues:
                    suite.results.append(TestResult(
                        name=f"jenkins_basic_{file_path}",
                        status=TestStatus.FAILED,
                        file_path=file_path,
                        error_message="; ".join(issues),
                    ))
                else:
                    suite.results.append(TestResult(
                        name=f"jenkins_basic_{file_path}",
                        status=TestStatus.PASSED,
                        file_path=file_path,
                    ))
        else:
            for file_path in jenkins_files:
                full_path = self.working_dir / file_path
                if full_path.exists():
                    result = await self._run_command([
                        "npm-groovy-lint", "--files", str(full_path)
                    ])
                    
                    suite.results.append(TestResult(
                        name=f"jenkins_lint_{file_path}",
                        status=result.status,
                        file_path=file_path,
                        output=result.output,
                        error_message=result.error_message,
                    ))
        
        suite.finished_at = datetime.now()
        suite.total_duration = (suite.finished_at - suite.started_at).total_seconds()
        
        return suite
    
    def _basic_jenkinsfile_check(self, content: str) -> list[str]:
        """Basic structural check for Jenkinsfile."""
        issues = []
        
        # Check for basic structure
        if "pipeline" in content:
            if "agent" not in content:
                issues.append("Missing 'agent' directive in declarative pipeline")
            if "stages" not in content:
                issues.append("Missing 'stages' directive in declarative pipeline")
        
        # Check for balanced braces
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            issues.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # Check for common issues
        if "credentials(" in content and "withCredentials" not in content:
            issues.append("Consider using withCredentials block for better security")
        
        return issues
    
    async def _run_command(
        self,
        args: list[str],
        cwd: Optional[str] = None
    ) -> TestResult:
        """Run a command and return the result."""
        import time
        start = time.time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or str(self.working_dir),
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return TestResult(
                    name=" ".join(args[:2]),
                    status=TestStatus.TIMEOUT,
                    error_message=f"Command timed out after {self.timeout}s",
                    duration_seconds=time.time() - start,
                )
            
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")
            
            status = TestStatus.PASSED if process.returncode == 0 else TestStatus.FAILED
            
            return TestResult(
                name=" ".join(args[:2]),
                status=status,
                output=output + error,
                error_message=error if status == TestStatus.FAILED else None,
                duration_seconds=time.time() - start,
            )
            
        except FileNotFoundError:
            return TestResult(
                name=" ".join(args[:2]),
                status=TestStatus.ERROR,
                error_message=f"Command not found: {args[0]}",
                duration_seconds=time.time() - start,
            )
        except Exception as e:
            return TestResult(
                name=" ".join(args[:2]),
                status=TestStatus.ERROR,
                error_message=str(e),
                duration_seconds=time.time() - start,
            )
    
    async def run_custom_test(
        self,
        command: list[str],
        name: str,
        cwd: Optional[str] = None
    ) -> TestResult:
        """Run a custom test command."""
        return await self._run_command(command, cwd)
