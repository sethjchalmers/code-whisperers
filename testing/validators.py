"""
Code validators for syntax and semantic validation.
"""

import ast
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of a validation check."""

    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    SKIPPED = "skipped"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    message: str
    line_number: int | None = None
    column: int | None = None
    severity: str = "error"  # error, warning, info

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "line_number": self.line_number,
            "column": self.column,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    """Result of a validation check."""

    file_path: str
    file_type: str
    status: ValidationStatus
    issues: list[ValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "file_type": self.file_type,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "metadata": self.metadata,
        }

    @property
    def is_valid(self) -> bool:
        return self.status == ValidationStatus.VALID


class CodeValidator:
    """
    Validates code files for syntax and common issues.

    Supports:
    - Python syntax validation
    - JSON/YAML syntax validation
    - Terraform HCL validation (basic)
    - Kubernetes manifest validation (basic)
    """

    def __init__(self):
        self.logger = logging.getLogger("validator")

    def validate_files(self, files: dict[str, str]) -> list[ValidationResult]:
        """Validate all files and return results."""
        results = []

        for file_path, content in files.items():
            result = self.validate_file(file_path, content)
            results.append(result)

        return results

    def validate_file(self, file_path: str, content: str) -> ValidationResult:
        """Validate a single file based on its extension."""
        if file_path.endswith(".py"):
            return self.validate_python(file_path, content)
        elif file_path.endswith(".json"):
            return self.validate_json(file_path, content)
        elif file_path.endswith((".yaml", ".yml")):
            return self.validate_yaml(file_path, content)
        elif file_path.endswith(".tf"):
            return self.validate_terraform(file_path, content)
        elif "jenkinsfile" in file_path.lower() or file_path.endswith(".groovy"):
            return self.validate_jenkinsfile(file_path, content)
        else:
            return ValidationResult(
                file_path=file_path,
                file_type="unknown",
                status=ValidationStatus.SKIPPED,
            )

    def validate_python(self, file_path: str, content: str) -> ValidationResult:
        """Validate Python syntax."""
        issues = []
        metadata = {}

        try:
            tree = ast.parse(content)

            # Extract metadata
            metadata["functions"] = len(
                [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            )
            metadata["classes"] = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
            metadata["imports"] = len(
                [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
            )

            # Check for common issues
            issues.extend(self._check_python_issues(tree, content))

            status = (
                ValidationStatus.VALID
                if not any(i.severity == "error" for i in issues)
                else ValidationStatus.WARNING
            )

        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    message=f"Syntax error: {e.msg}",
                    line_number=e.lineno,
                    column=e.offset,
                    severity="error",
                )
            )
            status = ValidationStatus.INVALID

        return ValidationResult(
            file_path=file_path,
            file_type="python",
            status=status,
            issues=issues,
            metadata=metadata,
        )

    def _check_python_issues(self, tree: ast.AST, content: str) -> list[ValidationIssue]:
        """Check for common Python issues."""
        issues = []

        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(
                        ValidationIssue(
                            message="Bare 'except:' clause catches all exceptions including SystemExit and KeyboardInterrupt",
                            line_number=node.lineno,
                            severity="warning",
                        )
                    )

            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(
                            ValidationIssue(
                                message=f"Mutable default argument in function '{node.name}'",
                                line_number=node.lineno,
                                severity="warning",
                            )
                        )

            # Check for assert statements (might be stripped in optimized mode)
            if isinstance(node, ast.Assert):
                issues.append(
                    ValidationIssue(
                        message="Assert statement may be stripped in optimized mode (-O flag)",
                        line_number=node.lineno,
                        severity="info",
                    )
                )

        # Check for potential secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Potential hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Potential hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Potential hardcoded secret"),
        ]

        for pattern, message in secret_patterns:
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        ValidationIssue(
                            message=message,
                            line_number=i,
                            severity="warning",
                        )
                    )

        return issues

    def validate_json(self, file_path: str, content: str) -> ValidationResult:
        """Validate JSON syntax."""
        issues = []

        try:
            data = json.loads(content)

            return ValidationResult(
                file_path=file_path,
                file_type="json",
                status=ValidationStatus.VALID,
                metadata={"keys": list(data.keys()) if isinstance(data, dict) else []},
            )

        except json.JSONDecodeError as e:
            issues.append(
                ValidationIssue(
                    message=f"JSON parse error: {e.msg}",
                    line_number=e.lineno,
                    column=e.colno,
                    severity="error",
                )
            )

            return ValidationResult(
                file_path=file_path,
                file_type="json",
                status=ValidationStatus.INVALID,
                issues=issues,
            )

    def validate_yaml(self, file_path: str, content: str) -> ValidationResult:
        """Validate YAML syntax."""
        issues = []

        try:
            # Parse YAML (handles multi-document)
            documents = list(yaml.safe_load_all(content))

            metadata = {
                "document_count": len(documents),
            }

            # Check for Kubernetes manifests
            for doc in documents:
                if doc and isinstance(doc, dict):
                    if "apiVersion" in doc and "kind" in doc:
                        metadata["is_kubernetes"] = True
                        issues.extend(self._check_kubernetes_issues(doc, file_path))

            status = (
                ValidationStatus.VALID
                if not any(i.severity == "error" for i in issues)
                else ValidationStatus.WARNING
            )

            return ValidationResult(
                file_path=file_path,
                file_type="yaml",
                status=status,
                issues=issues,
                metadata=metadata,
            )

        except yaml.YAMLError as e:
            issues.append(
                ValidationIssue(
                    message=f"YAML parse error: {str(e)}",
                    severity="error",
                )
            )

            return ValidationResult(
                file_path=file_path,
                file_type="yaml",
                status=ValidationStatus.INVALID,
                issues=issues,
            )

    def _check_kubernetes_issues(self, doc: dict, file_path: str) -> list[ValidationIssue]:
        """Check for common Kubernetes manifest issues."""
        issues = []

        kind = doc.get("kind", "")

        # Check for latest tag
        if kind in ["Deployment", "Pod", "StatefulSet", "DaemonSet", "Job", "CronJob"]:
            spec = doc.get("spec", {})
            template = spec.get("template", spec)
            containers = template.get("spec", {}).get("containers", [])

            for container in containers:
                image = container.get("image", "")
                if ":latest" in image or ":" not in image:
                    issues.append(
                        ValidationIssue(
                            message=f"Container '{container.get('name')}' uses 'latest' tag or no tag - use specific versions",
                            severity="warning",
                        )
                    )

                # Check for resource limits
                resources = container.get("resources", {})
                if not resources.get("limits"):
                    issues.append(
                        ValidationIssue(
                            message=f"Container '{container.get('name')}' has no resource limits defined",
                            severity="warning",
                        )
                    )
                if not resources.get("requests"):
                    issues.append(
                        ValidationIssue(
                            message=f"Container '{container.get('name')}' has no resource requests defined",
                            severity="info",
                        )
                    )

        # Check for security context
        if kind in ["Deployment", "Pod", "StatefulSet"]:
            spec = doc.get("spec", {})
            template = spec.get("template", spec)
            security_context = template.get("spec", {}).get("securityContext", {})

            if not security_context:
                issues.append(
                    ValidationIssue(
                        message="No pod-level securityContext defined",
                        severity="info",
                    )
                )

        return issues

    def validate_terraform(self, file_path: str, content: str) -> ValidationResult:
        """Basic Terraform HCL validation."""
        issues = []
        metadata = {}

        # Count blocks
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"'
        data_pattern = r'data\s+"([^"]+)"\s+"([^"]+)"'
        variable_pattern = r'variable\s+"([^"]+)"'
        output_pattern = r'output\s+"([^"]+)"'

        resources = re.findall(resource_pattern, content)
        data_sources = re.findall(data_pattern, content)
        variables = re.findall(variable_pattern, content)
        outputs = re.findall(output_pattern, content)

        metadata["resources"] = [f"{r[0]}.{r[1]}" for r in resources]
        metadata["data_sources"] = [f"{d[0]}.{d[1]}" for d in data_sources]
        metadata["variables"] = list(variables)
        metadata["outputs"] = list(outputs)

        # Check for common issues

        # Check for hardcoded credentials
        secret_patterns = [
            (
                r'(password|secret|api_key|access_key)\s*=\s*"[^"]+"',
                "Potential hardcoded credential",
            ),
        ]

        for pattern, message in secret_patterns:
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(pattern, line, re.IGNORECASE):
                    # Skip if it's a variable reference
                    if "var." in line or "data." in line or "local." in line:
                        continue
                    issues.append(
                        ValidationIssue(
                            message=message,
                            line_number=i,
                            severity="warning",
                        )
                    )

        # Check for balanced braces
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            issues.append(
                ValidationIssue(
                    message=f"Unbalanced braces: {open_braces} open, {close_braces} close",
                    severity="error",
                )
            )

        # Check for missing descriptions on variables
        for var_match in re.finditer(r'variable\s+"([^"]+)"\s*{([^}]*)}', content, re.DOTALL):
            var_name = var_match.group(1)
            var_body = var_match.group(2)
            if "description" not in var_body:
                issues.append(
                    ValidationIssue(
                        message=f"Variable '{var_name}' has no description",
                        severity="info",
                    )
                )

        status = (
            ValidationStatus.VALID
            if not any(i.severity == "error" for i in issues)
            else ValidationStatus.INVALID
        )

        return ValidationResult(
            file_path=file_path,
            file_type="terraform",
            status=status,
            issues=issues,
            metadata=metadata,
        )

    def validate_jenkinsfile(self, file_path: str, content: str) -> ValidationResult:
        """Basic Jenkinsfile validation."""
        issues: list[ValidationIssue] = []
        metadata: dict[str, Any] = {}

        # Detect pipeline type
        if "pipeline {" in content or "pipeline{" in content:
            metadata["pipeline_type"] = "declarative"
        else:
            metadata["pipeline_type"] = "scripted"

        # Check for basic structure in declarative pipelines
        if metadata.get("pipeline_type") == "declarative":
            if "agent" not in content:
                issues.append(
                    ValidationIssue(
                        message="Missing 'agent' directive in declarative pipeline",
                        severity="error",
                    )
                )
            if "stages" not in content:
                issues.append(
                    ValidationIssue(
                        message="Missing 'stages' directive in declarative pipeline",
                        severity="error",
                    )
                )

        # Check for balanced braces
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            issues.append(
                ValidationIssue(
                    message=f"Unbalanced braces: {open_braces} open, {close_braces} close",
                    severity="error",
                )
            )

        # Check for potential security issues
        if "sh '" in content or 'sh "' in content:
            # Check for unquoted variables in shell commands
            shell_pattern = r'sh\s+[\'"].*\$\{?[A-Za-z_][A-Za-z0-9_]*\}?.*[\'"]'
            for i, line in enumerate(content.split("\n"), 1):
                if re.search(shell_pattern, line):
                    if "${" in line and "}" in line:
                        # Check if it's properly quoted
                        if '"${' not in line:
                            issues.append(
                                ValidationIssue(
                                    message="Unquoted variable in shell command - potential injection risk",
                                    line_number=i,
                                    severity="warning",
                                )
                            )

        # Count stages
        stages = re.findall(r'stage\s*\(\s*[\'"]([^\'"]+)[\'"]', content)
        metadata["stages"] = stages

        status = (
            ValidationStatus.VALID
            if not any(i.severity == "error" for i in issues)
            else ValidationStatus.INVALID
        )

        return ValidationResult(
            file_path=file_path,
            file_type="jenkinsfile",
            status=status,
            issues=issues,
            metadata=metadata,
        )

    def get_validation_summary(self, results: list[ValidationResult]) -> dict:
        """Generate a summary of validation results."""
        total = len(results)
        valid = sum(1 for r in results if r.status == ValidationStatus.VALID)
        invalid = sum(1 for r in results if r.status == ValidationStatus.INVALID)
        warnings = sum(1 for r in results if r.status == ValidationStatus.WARNING)
        skipped = sum(1 for r in results if r.status == ValidationStatus.SKIPPED)

        all_issues = []
        for r in results:
            for issue in r.issues:
                all_issues.append(
                    {
                        "file": r.file_path,
                        **issue.to_dict(),
                    }
                )

        return {
            "total_files": total,
            "valid": valid,
            "invalid": invalid,
            "warnings": warnings,
            "skipped": skipped,
            "all_issues": all_issues,
            "error_count": sum(1 for i in all_issues if i.get("severity") == "error"),
            "warning_count": sum(1 for i in all_issues if i.get("severity") == "warning"),
        }
