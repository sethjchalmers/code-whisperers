"""
Global settings and environment configuration for the agent pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from functools import lru_cache


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    azure_openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY"))
    azure_openai_endpoint: Optional[str] = field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT"))
    
    # Default LLM provider and model
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4-turbo-preview"))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1")))
    
    # Git Configuration
    git_repo_path: str = field(default_factory=lambda: os.getenv("GIT_REPO_PATH", "."))
    git_base_branch: str = field(default_factory=lambda: os.getenv("GIT_BASE_BRANCH", "main"))
    
    # Review Configuration
    max_file_size_kb: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_KB", "500")))
    parallel_agents: bool = field(default_factory=lambda: os.getenv("PARALLEL_AGENTS", "true").lower() == "true")
    
    # Testing Configuration
    enable_e2e_tests: bool = field(default_factory=lambda: os.getenv("ENABLE_E2E_TESTS", "true").lower() == "true")
    test_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("TEST_TIMEOUT_SECONDS", "300")))
    
    # Output Configuration
    output_format: str = field(default_factory=lambda: os.getenv("OUTPUT_FORMAT", "markdown"))
    save_reports: bool = field(default_factory=lambda: os.getenv("SAVE_REPORTS", "true").lower() == "true")
    reports_dir: str = field(default_factory=lambda: os.getenv("REPORTS_DIR", "./reports"))
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    def validate(self) -> list[str]:
        """Validate that required settings are present."""
        errors = []
        
        if self.llm_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required when using OpenAI provider")
        elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic provider")
        elif self.llm_provider == "azure":
            if not self.azure_openai_api_key:
                errors.append("AZURE_OPENAI_API_KEY is required when using Azure provider")
            if not self.azure_openai_endpoint:
                errors.append("AZURE_OPENAI_ENDPOINT is required when using Azure provider")
        
        return errors


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
