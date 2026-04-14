"""Configuration management for LLM Chatbot."""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    model: str = ""
    temperature: float = 0.7
    timeout: int = 30
    log_level: str = "INFO"

    # Keep backward-compatible property
    @property
    def api_key(self) -> str:
        """Return the API key for the active provider."""
        if self.provider == "gemini":
            return self.gemini_api_key
        return self.openai_api_key

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Returns:
            Config: Configuration instance with values from environment.

        Raises:
            ConfigurationError: If required variables are missing or invalid.
        """
        load_dotenv()

        provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        openai_api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("LLM_MODEL", "")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        log_level = os.getenv("LOG_LEVEL", "INFO")

        # Set default model based on provider
        if not model:
            model = "gemini-2.5-flash" if provider == "gemini" else "gpt-3.5-turbo"

        config = cls(
            provider=provider,
            gemini_api_key=gemini_api_key,
            openai_api_key=openai_api_key,
            model=model,
            temperature=temperature,
            timeout=timeout,
            log_level=log_level
        )

        config.validate()
        return config

    def validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If any configuration value is invalid.
        """
        if self.provider not in ("gemini", "openai"):
            raise ConfigurationError(
                f"Configuration error: LLM_PROVIDER must be 'gemini' or 'openai', "
                f"got '{self.provider}'"
            )

        # Must have at least one valid API key
        has_gemini = bool(self.gemini_api_key and self.gemini_api_key.strip())
        has_openai = bool(self.openai_api_key and self.openai_api_key.strip())

        if not has_gemini and not has_openai:
            raise ConfigurationError(
                "Configuration error: No API key found. "
                "Please set GEMINI_API_KEY or OPENAI_API_KEY in your .env file."
            )

        if not (0.0 <= self.temperature <= 2.0):
            raise ConfigurationError(
                f"Configuration error: LLM_TEMPERATURE must be between 0.0 and 2.0, "
                f"got {self.temperature}"
            )

        if self.timeout <= 0:
            raise ConfigurationError(
                f"Configuration error: LLM_TIMEOUT must be positive, "
                f"got {self.timeout}"
            )
