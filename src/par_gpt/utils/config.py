"""Centralized configuration management for environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from par_ai_core.par_logging import console_err
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from par_gpt import __env_var_prefix__


class EnvironmentConfig(BaseSettings):
    """Centralized configuration for PAR GPT environment variables."""

    model_config = SettingsConfigDict(
        env_prefix=f"{__env_var_prefix__}_",
        env_file=Path.home() / ".par_gpt.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # AI Provider Settings
    ai_provider: str = Field(default="OpenAI", description="AI provider to use")
    model: str | None = Field(default=None, description="AI model to use")
    fallback_models: list[str] = Field(default_factory=list, description="Fallback models")
    light_model: bool = Field(default=False, description="Use light model")
    ai_base_url: str | None = Field(default=None, description="Override base URL for AI provider")
    temperature: float = Field(default=0.5, description="Temperature for AI generation")
    user_agent_appid: str | None = Field(default=None, description="Extra User-Agent data")
    max_context_size: int = Field(default=0, description="Maximum context size")
    reasoning_effort: str | None = Field(default=None, description="Reasoning effort level")
    reasoning_budget: int | None = Field(default=None, description="Reasoning budget")

    # Display Settings
    pricing: str = Field(default="none", description="Pricing display mode")
    display_output: str = Field(default="md", description="Output display format")
    debug: bool = Field(default=False, description="Enable debug mode")
    show_config: bool = Field(default=False, description="Show configuration")

    # User and Session Settings
    user: str | None = Field(default=None, description="User for memory and preferences")
    chat_history: str | None = Field(default=None, description="Chat history file")
    loop_mode: str = Field(default="one_shot", description="Loop mode")

    # Redis Settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: SecretStr | None = Field(default=None, description="Redis password")

    # Neo4j Settings
    neo4j_host: str = Field(default="localhost", description="Neo4j host")
    neo4j_port: int = Field(default=7687, description="Neo4j port")
    neo4j_user: str = Field(default="neo4j", description="Neo4j user")
    neo4j_pass: SecretStr = Field(default=SecretStr("neo4j"), description="Neo4j password")

    # Agent Settings
    max_iterations: int = Field(default=5, description="Max iterations for agent mode")
    show_tool_calls: bool = Field(default=True, description="Show tool calls")
    yes_to_all: bool = Field(default=False, description="Yes to all prompts")
    repl: bool = Field(default=False, description="Enable REPL tool")
    code_sandbox: bool = Field(default=False, description="Enable code sandbox")

    # TTS Settings
    tts: bool = Field(default=False, description="Use TTS for responses")
    tts_provider: str | None = Field(default=None, description="TTS provider")
    tts_voice: str | None = Field(default=None, description="TTS voice")

    # API Keys (as SecretStr for security)
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    xai_api_key: SecretStr | None = Field(default=None, alias="XAI_API_KEY")
    google_api_key: SecretStr | None = Field(default=None, alias="GOOGLE_API_KEY")
    mistral_api_key: SecretStr | None = Field(default=None, alias="MISTRAL_API_KEY")
    github_token: SecretStr | None = Field(default=None, alias="GITHUB_TOKEN")
    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    deepseek_api_key: SecretStr | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    github_personal_access_token: SecretStr | None = Field(default=None, alias="GITHUB_PERSONAL_ACCESS_TOKEN")

    # Search API Keys
    google_cse_id: str | None = Field(default=None, alias="GOOGLE_CSE_ID")
    google_cse_api_key: SecretStr | None = Field(default=None, alias="GOOGLE_CSE_API_KEY")
    serper_api_key: SecretStr | None = Field(default=None, alias="SERPER_API_KEY")
    serper_api_key_google: SecretStr | None = Field(default=None, alias="SERPER_API_KEY_GOOGLE")
    tavily_api_key: SecretStr | None = Field(default=None, alias="TAVILY_API_KEY")
    jina_api_key: SecretStr | None = Field(default=None, alias="JINA_API_KEY")
    brave_api_key: SecretStr | None = Field(default=None, alias="BRAVE_API_KEY")
    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: SecretStr | None = Field(default=None, alias="REDDIT_CLIENT_SECRET")

    # Misc API Keys
    weatherapi_key: SecretStr | None = Field(default=None, alias="WEATHERAPI_KEY")
    tinify_key: SecretStr | None = Field(default=None, alias="TINIFY_KEY")
    elevenlabs_api_key: SecretStr | None = Field(default=None, alias="ELEVENLABS_API_KEY")

    # Vector Store
    vector_store_url: str | None = Field(default=None, alias="VECTOR_STORE_URL")

    @field_validator("redis_port", "neo4j_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port numbers are in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v

    def get_api_key(self, key_name: str) -> str | None:
        """
        Get an API key value as a string.

        Args:
            key_name: Name of the API key attribute.

        Returns:
            API key as string or None if not set.
        """
        value = getattr(self, key_name, None)
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        return value

    def validate_env_file_permissions(self) -> None:
        """Check that .env file has secure permissions."""
        env_file = Path.home() / ".par_gpt.env"
        if env_file.exists():
            mode = env_file.stat().st_mode & 0o777
            if mode != 0o600:
                console_err.print(
                    f"[yellow]Warning: {env_file} has insecure permissions {oct(mode)}. "
                    f"Consider running: chmod 600 {env_file}[/yellow]"
                )

    def display_config(self, show_secrets: bool = False) -> dict[str, Any]:
        """
        Get configuration for display purposes.

        Args:
            show_secrets: Whether to show secret values (default: False).

        Returns:
            Dictionary of configuration values with secrets masked.
        """
        config_dict = self.model_dump()

        if not show_secrets:
            # Mask all SecretStr fields
            for field_name, field_info in self.model_fields.items():
                if field_info.annotation and "SecretStr" in str(field_info.annotation):
                    value = config_dict.get(field_name)
                    if value:
                        # Show first 3 and last 3 characters
                        if len(value) > 6:
                            config_dict[field_name] = f"{value[:3]}...{value[-3:]}"
                        else:
                            config_dict[field_name] = "*" * len(value)

        return config_dict


# Global configuration instance
_config: EnvironmentConfig | None = None


def get_config() -> EnvironmentConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        # Load .env file if it exists
        env_file = Path.home() / ".par_gpt.env"
        if env_file.exists():
            load_dotenv(env_file)

        _config = EnvironmentConfig()
        _config.validate_env_file_permissions()

    return _config


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config
    _config = None


def update_config(**kwargs: Any) -> EnvironmentConfig:
    """
    Update configuration values.

    Args:
        **kwargs: Configuration values to update.

    Returns:
        Updated configuration instance.
    """
    config = get_config()
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config
