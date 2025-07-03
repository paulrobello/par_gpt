"""Comprehensive configuration validation using Pydantic models.

This module provides validated configuration models for all PAR GPT settings,
ensuring type safety and proper validation of user-provided configuration values.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RedisConfig(BaseModel):
    """Redis configuration validation."""

    host: str = Field(default="localhost", description="Redis server hostname")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis server port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")
    enabled: bool = Field(default=False, description="Enable Redis functionality")

    # noinspection PyNestedDecorators
    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate Redis hostname."""
        if not v or v.isspace():
            raise ValueError("Redis host cannot be empty")
        return v.strip()


class TTSConfig(BaseModel):
    """Text-to-Speech configuration validation."""

    enabled: bool = Field(default=False, description="Enable TTS functionality")
    provider: Literal["local", "kokoro", "elevenlabs", "openai"] | None = Field(
        default=None, description="TTS provider to use"
    )
    voice: str | None = Field(default=None, description="Voice to use for TTS")

    # noinspection PyNestedDecorators
    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str | None) -> str | None:
        """Validate TTS voice parameter."""
        if v is not None and (not v or v.isspace()):
            raise ValueError("TTS voice cannot be empty string")
        return v.strip() if v else None


class SecurityConfig(BaseModel):
    """Security configuration validation."""

    yes_to_all: bool = Field(default=False, description="Automatically accept all security warnings")
    max_file_size_mb: float = Field(default=10.0, gt=0, le=1000, description="Maximum file size in MB")
    allow_code_execution: bool = Field(default=False, description="Allow code execution via REPL")
    sandbox_enabled: bool = Field(default=False, description="Enable Docker sandbox for code execution")

    # noinspection PyNestedDecorators
    @field_validator("max_file_size_mb")
    @classmethod
    def validate_file_size(cls, v: float) -> float:
        """Validate maximum file size."""
        if v <= 0:
            raise ValueError("Maximum file size must be positive")
        if v > 1000:
            raise ValueError("Maximum file size cannot exceed 1000 MB")
        return v


class PerformanceConfig(BaseModel):
    """Performance configuration validation."""

    show_times: bool = Field(default=False, description="Show timing information")
    show_times_detailed: bool = Field(default=False, description="Show detailed timing breakdown")
    lazy_loading: bool = Field(default=True, description="Enable lazy loading for better startup performance")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to handle field dependencies."""
        # If detailed times is enabled, ensure basic times is also enabled
        if self.show_times_detailed and not self.show_times:
            self.show_times = True


class AIProviderConfig(BaseModel):
    """AI provider configuration validation."""

    provider: str = Field(default="OpenAI", description="AI provider name")
    model: str | None = Field(default=None, description="Specific model to use")
    fallback_models: list[str] = Field(default_factory=list, description="Fallback models if primary fails")
    light_model: bool = Field(default=False, description="Use light/fast model")
    temperature: float = Field(default=0.5, ge=0.0, le=2.0, description="Model temperature")
    max_context_size: int = Field(default=0, ge=0, description="Maximum context size (0 = default)")
    base_url: str | None = Field(default=None, description="Custom base URL for provider")

    # noinspection PyNestedDecorators
    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    # noinspection PyNestedDecorators
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None) -> str | None:
        """Validate base URL format."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("Base URL must start with http:// or https://")
        return v

    # noinspection PyNestedDecorators
    @field_validator("fallback_models")
    @classmethod
    def validate_fallback_models(cls, v: list[str]) -> list[str]:
        """Validate fallback models list."""
        return [model.strip() for model in v if model.strip()]


class OutputConfig(BaseModel):
    """Output configuration validation."""

    display_format: Literal["none", "plain", "md", "csv", "json"] = Field(
        default="md", description="Output display format"
    )
    pricing_display: Literal["none", "price", "details"] = Field(
        default="none", description="Pricing information display level"
    )
    copy_to_clipboard: bool = Field(default=False, description="Copy output to clipboard")
    copy_from_clipboard: bool = Field(default=False, description="Copy context from clipboard")


class InputConfig(BaseModel):
    """Input configuration validation."""

    voice_input: bool = Field(default=False, description="Enable voice input")
    context_location: str = Field(default="", description="Default context location")
    system_prompt: str | None = Field(default=None, description="Default system prompt")
    user_prompt: str | None = Field(default=None, description="Default user prompt")

    # noinspection PyNestedDecorators
    @field_validator("context_location")
    @classmethod
    def validate_context_location(cls, v: str) -> str:
        """Validate context location."""
        return v.strip()

    # noinspection PyNestedDecorators
    @field_validator("system_prompt", "user_prompt")
    @classmethod
    def validate_prompts(cls, v: str | None) -> str | None:
        """Validate prompt content."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class DebugConfig(BaseModel):
    """Debug and development configuration validation."""

    debug: bool = Field(default=False, description="Enable debug mode")
    show_config: bool = Field(default=False, description="Show configuration on startup")
    show_tool_calls: bool = Field(default=False, description="Show AI tool calls in agent mode")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to handle field dependencies."""
        # Automatically enable tool calls display in debug mode
        if self.debug and not self.show_tool_calls:
            self.show_tool_calls = True


class PARGPTConfig(BaseSettings):
    """Main PAR GPT configuration with comprehensive validation."""

    model_config = SettingsConfigDict(
        env_prefix="PARGPT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )

    # Core AI configuration
    ai: AIProviderConfig = Field(default_factory=AIProviderConfig, description="AI provider configuration")

    # Input/Output configuration
    input: InputConfig = Field(default_factory=InputConfig, description="Input configuration")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output configuration")

    # Optional services
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    tts: TTSConfig = Field(default_factory=TTSConfig, description="TTS configuration")

    # Security settings
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security configuration")

    # Performance settings
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig, description="Performance configuration")

    # Debug settings
    debug: DebugConfig = Field(default_factory=DebugConfig, description="Debug configuration")

    # Loop mode
    loop_mode: Literal["one_shot", "infinite"] = Field(default="one_shot", description="Command execution loop mode")

    # User identification
    user: str | None = Field(default=None, description="User identifier for memory and preferences")

    # Agent configuration
    max_iterations: int = Field(default=5, ge=1, le=100, description="Maximum agent iterations")

    # Chat history
    chat_history: str | None = Field(default=None, description="Chat history file path")

    # noinspection PyNestedDecorators
    @field_validator("user")
    @classmethod
    def validate_user(cls, v: str | None) -> str | None:
        """Validate user identifier."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Basic validation for user identifier
            if len(v) > 100:
                raise ValueError("User identifier cannot exceed 100 characters")
        return v

    # noinspection PyNestedDecorators
    @field_validator("chat_history")
    @classmethod
    def validate_chat_history(cls, v: str | None) -> str | None:
        """Validate chat history file path."""
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Basic path validation
            try:
                path = Path(v)
                if path.exists() and not path.is_file():
                    raise ValueError("Chat history path exists but is not a file")
                if path.suffix not in [".json", ".jsonl", ""]:
                    raise ValueError("Chat history file should have .json or .jsonl extension")
            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid chat history path: {e}") from e
        return v

    # noinspection PyNestedDecorators
    @field_validator("max_iterations")
    @classmethod
    def validate_max_iterations(cls, v: int) -> int:
        """Validate maximum iterations."""
        if not 1 <= v <= 100:
            raise ValueError("Maximum iterations must be between 1 and 100")
        return v

    def validate_provider_compatibility(self) -> None:
        """Validate that provider configuration is compatible."""
        if self.ai.provider == "Ollama" and self.ai.base_url is None:
            # Ollama typically runs on localhost:11434
            self.ai.base_url = "http://localhost:11434"

        if self.tts.enabled and self.tts.provider is None:
            raise ValueError("TTS provider must be specified when TTS is enabled")

        if self.security.sandbox_enabled and self.security.allow_code_execution:
            # Both can't be true - sandbox takes precedence
            self.security.allow_code_execution = False

    def get_env_file_path(self) -> Path | None:
        """Get the environment file path for this configuration."""
        home_dir = Path.home()
        env_file = home_dir / ".par_gpt.env"
        if env_file.exists():
            return env_file
        return None

    @classmethod
    def from_env_and_args(cls, **overrides: Any) -> PARGPTConfig:
        """Create configuration from environment variables and argument overrides."""
        # Load from environment first
        config = cls()

        # Apply any argument overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Validate provider compatibility
        config.validate_provider_compatibility()

        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return self.model_dump()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of key configuration values for display."""
        return {
            "ai_provider": self.ai.provider,
            "model": self.ai.model or "default",
            "temperature": self.ai.temperature,
            "output_format": self.output.display_format,
            "debug_mode": self.debug.debug,
            "redis_enabled": self.redis.enabled,
            "tts_enabled": self.tts.enabled,
            "security_mode": "yes_to_all" if self.security.yes_to_all else "interactive",
            "performance_timing": self.performance.show_times,
        }


def validate_config_dict(config_dict: dict[str, Any]) -> dict[str, str]:
    """Validate a configuration dictionary and return any errors."""
    errors: dict[str, str] = {}

    try:
        PARGPTConfig(**config_dict)
    except ValueError as e:
        errors["general"] = str(e)

    return errors


def load_and_validate_config(**overrides: Any) -> tuple[PARGPTConfig, list[str]]:
    """Load and validate configuration, returning config and any warnings."""
    warnings: list[str] = []

    try:
        config = PARGPTConfig.from_env_and_args(**overrides)
    except Exception as e:
        warnings.append(f"Configuration validation error: {e}")
        # Fallback to default configuration
        config = PARGPTConfig()

    # Check for common configuration issues
    if config.redis.enabled and not _redis_available():
        warnings.append("Redis is enabled but not available - memory features will be disabled")

    if config.tts.enabled and not _tts_provider_available(config.tts.provider):
        warnings.append(f"TTS provider '{config.tts.provider}' is not available")

    if config.ai.base_url and not config.ai.base_url.startswith(("http://", "https://")):
        warnings.append("AI base URL should start with http:// or https://")

    return config, warnings


def _redis_available() -> bool:
    """Check if Redis is available."""
    try:
        import redis

        client = redis.Redis(host="localhost", port=6379, db=0, socket_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def _tts_provider_available(provider: str | None) -> bool:
    """Check if TTS provider is available."""
    if not provider:
        return False

    try:
        if provider == "local":
            import importlib.util

            return importlib.util.find_spec("pyttsx3") is not None
        elif provider == "kokoro":
            import importlib.util

            return importlib.util.find_spec("kokoro_onnx") is not None
        elif provider == "elevenlabs":
            return bool(os.getenv("ELEVENLABS_API_KEY"))
        elif provider == "openai":
            return bool(os.getenv("OPENAI_API_KEY"))
    except ImportError:
        return False

    return False
