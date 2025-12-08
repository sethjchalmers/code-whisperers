"""
Tests for the validation module.
"""

import pytest

from testing.validators import CodeValidator, ValidationStatus


class TestCodeValidator:
    """Test the CodeValidator class."""

    @pytest.fixture
    def validator(self):
        return CodeValidator()

    def test_validate_valid_python(self, validator):
        """Test validation of valid Python code."""
        content = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    print(hello("World"))
'''
        result = validator.validate_python("test.py", content)
        assert result.status == ValidationStatus.VALID
        assert result.metadata.get("functions") == 1

    def test_validate_invalid_python(self, validator):
        """Test validation of invalid Python code."""
        content = """
def hello(name
    return f"Hello, {name}!"
"""
        result = validator.validate_python("test.py", content)
        assert result.status == ValidationStatus.INVALID
        assert len(result.issues) > 0
        assert result.issues[0].severity == "error"

    def test_validate_python_with_warnings(self, validator):
        """Test validation of Python code with warnings."""
        content = '''
def process(data=[]):
    """Process data with mutable default."""
    data.append(1)
    return data
'''
        result = validator.validate_python("test.py", content)
        # Should have warning about mutable default argument
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert len(warnings) >= 1

    def test_validate_valid_json(self, validator):
        """Test validation of valid JSON."""
        content = '{"key": "value", "number": 42}'
        result = validator.validate_json("test.json", content)
        assert result.status == ValidationStatus.VALID

    def test_validate_invalid_json(self, validator):
        """Test validation of invalid JSON."""
        content = '{"key": "value", number: 42}'  # Missing quotes
        result = validator.validate_json("test.json", content)
        assert result.status == ValidationStatus.INVALID

    def test_validate_valid_yaml(self, validator):
        """Test validation of valid YAML."""
        content = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  key: value
"""
        result = validator.validate_yaml("test.yaml", content)
        assert result.status in [ValidationStatus.VALID, ValidationStatus.WARNING]
        assert result.metadata.get("is_kubernetes") is True

    def test_validate_invalid_yaml(self, validator):
        """Test validation of invalid YAML."""
        content = """
key: value
  bad_indent: true
"""
        result = validator.validate_yaml("test.yaml", content)
        assert result.status == ValidationStatus.INVALID

    def test_validate_terraform(self, validator):
        """Test validation of Terraform files."""
        content = """
resource "aws_instance" "web" {
  ami           = var.ami_id
  instance_type = "t3.micro"

  tags = {
    Name = "WebServer"
  }
}

variable "ami_id" {
  type = string
}
"""
        result = validator.validate_terraform("main.tf", content)
        assert result.status == ValidationStatus.VALID
        assert "aws_instance.web" in result.metadata.get("resources", [])
        # Should warn about missing description
        info_issues = [i for i in result.issues if i.severity == "info"]
        assert any("description" in i.message for i in info_issues)

    def test_validate_terraform_unbalanced_braces(self, validator):
        """Test Terraform validation with unbalanced braces."""
        content = """
resource "aws_instance" "web" {
  ami = "ami-12345"
"""
        result = validator.validate_terraform("main.tf", content)
        assert result.status == ValidationStatus.INVALID
        assert any("Unbalanced braces" in i.message for i in result.issues)

    def test_validate_jenkinsfile(self, validator):
        """Test validation of Jenkinsfile."""
        content = """
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'make build'
            }
        }
        stage('Test') {
            steps {
                sh 'make test'
            }
        }
    }
}
"""
        result = validator.validate_jenkinsfile("Jenkinsfile", content)
        assert result.status == ValidationStatus.VALID
        assert result.metadata.get("pipeline_type") == "declarative"
        assert "Build" in result.metadata.get("stages", [])

    def test_validate_jenkinsfile_missing_agent(self, validator):
        """Test Jenkinsfile validation with missing agent."""
        content = """
pipeline {
    stages {
        stage('Build') {
            steps {
                sh 'make build'
            }
        }
    }
}
"""
        result = validator.validate_jenkinsfile("Jenkinsfile", content)
        assert result.status == ValidationStatus.INVALID
        assert any("agent" in i.message for i in result.issues)

    def test_validate_files(self, validator):
        """Test validating multiple files."""
        files = {
            "app.py": "def main(): pass",
            "config.json": '{"key": "value"}',
            "unknown.xyz": "some content",
        }

        results = validator.validate_files(files)
        assert len(results) == 3

        # Python should be valid
        py_result = next(r for r in results if r.file_path == "app.py")
        assert py_result.status == ValidationStatus.VALID

        # JSON should be valid
        json_result = next(r for r in results if r.file_path == "config.json")
        assert json_result.status == ValidationStatus.VALID

        # Unknown should be skipped
        unknown_result = next(r for r in results if r.file_path == "unknown.xyz")
        assert unknown_result.status == ValidationStatus.SKIPPED

    def test_get_validation_summary(self, validator):
        """Test getting validation summary."""
        files = {
            "valid.py": "def main(): pass",
            "invalid.py": "def main(:",
            "config.json": '{"key": "value"}',
        }

        results = validator.validate_files(files)
        summary = validator.get_validation_summary(results)

        assert summary["total_files"] == 3
        assert summary["valid"] >= 1
        assert summary["invalid"] >= 1
