"""Lazy import management for command-specific imports to optimize startup time."""

from __future__ import annotations

import importlib
from typing import Any


class LazyImportManager:
    """Manages lazy imports for different command categories."""

    def __init__(self) -> None:
        """Initialize the lazy import manager."""
        self._import_cache: dict[str, Any] = {}

    def get_cached_import(self, module_path: str, item_name: str | None = None) -> Any:
        """Get a cached import or import and cache it."""
        cache_key = f"{module_path}.{item_name}" if item_name else module_path

        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        # Import the module
        module = importlib.import_module(module_path)

        if item_name:
            # Get specific item from module
            item = getattr(module, item_name)
            self._import_cache[cache_key] = item
            return item
        else:
            # Cache entire module
            self._import_cache[cache_key] = module
            return module

    def load_minimal_imports(self) -> dict[str, Any]:
        """Load only the imports needed for minimal commands (version, help)."""
        return {}

    def load_basic_llm_imports(self) -> dict[str, Any]:
        """Load imports needed for basic LLM mode."""
        imports = {}

        # Core LLM functionality
        imports["LlmConfig"] = self.get_cached_import("par_ai_core.llm_config", "LlmConfig")
        imports["LlmMode"] = self.get_cached_import("par_ai_core.llm_config", "LlmMode")
        imports["llm_run_manager"] = self.get_cached_import("par_ai_core.llm_config", "llm_run_manager")

        # Provider functionality
        imports["LlmProvider"] = self.get_cached_import("par_ai_core.llm_providers", "LlmProvider")
        imports["is_provider_api_key_set"] = self.get_cached_import(
            "par_ai_core.llm_providers", "is_provider_api_key_set"
        )
        imports["provider_default_models"] = self.get_cached_import(
            "par_ai_core.llm_providers", "provider_default_models"
        )

        # Output utilities
        imports["DisplayOutputFormat"] = self.get_cached_import("par_ai_core.output_utils", "DisplayOutputFormat")
        imports["display_formatted_output"] = self.get_cached_import(
            "par_ai_core.output_utils", "display_formatted_output"
        )

        # Pricing
        imports["PricingDisplay"] = self.get_cached_import("par_ai_core.pricing_lookup", "PricingDisplay")
        imports["show_llm_cost"] = self.get_cached_import("par_ai_core.pricing_lookup", "show_llm_cost")

        return imports

    def load_agent_imports(self) -> dict[str, Any]:
        """Load imports needed for agent mode."""
        imports = self.load_basic_llm_imports()

        # Agent-specific functionality
        imports["do_tool_agent"] = self.get_cached_import("par_gpt.agents", "do_tool_agent")
        imports["build_ai_tool_list"] = self.get_cached_import("par_gpt.lazy_tool_loader", "build_ai_tool_list")

        return imports

    def load_media_imports(self) -> dict[str, Any]:
        """Load imports needed for media operations (images, TTS, etc.)."""
        imports = {}

        # Image utilities
        imports["image_to_base64"] = self.get_cached_import("par_ai_core.llm_image_utils", "image_to_base64")
        imports["try_get_image_type"] = self.get_cached_import("par_ai_core.llm_image_utils", "try_get_image_type")
        imports["UnsupportedImageTypeError"] = self.get_cached_import(
            "par_ai_core.llm_image_utils", "UnsupportedImageTypeError"
        )

        # TTS functionality
        imports["TTSManger"] = self.get_cached_import("par_gpt.tts_manager", "TTSManger")
        imports["TTSProvider"] = self.get_cached_import("par_gpt.tts_manager", "TTSProvider")
        imports["summarize_for_tts"] = self.get_cached_import("par_gpt.tts_manager", "summarize_for_tts")

        # Voice input
        imports["VoiceInputManager"] = self.get_cached_import("par_gpt.voice_input_manager", "VoiceInputManager")

        return imports

    def load_clipboard_imports(self) -> dict[str, Any]:
        """Load clipboard functionality when needed."""
        imports = {}

        # Import clipboard dynamically
        clipboard_module = self.get_cached_import("clipman")
        imports["clipboard"] = clipboard_module

        return imports

    def load_json_imports(self) -> dict[str, Any]:
        """Load JSON functionality when needed."""
        imports = {}

        # Import orjson dynamically
        imports["json"] = self.get_cached_import("orjson")

        return imports

    def load_git_imports(self) -> dict[str, Any]:
        """Load Git functionality when needed."""
        imports = {}

        imports["GitRepo"] = self.get_cached_import("par_gpt.repo.repo", "GitRepo")

        return imports

    def load_timing_imports(self) -> dict[str, Any]:
        """Load timing functionality when needed."""
        imports = {}

        imports["enable_timing"] = self.get_cached_import("par_gpt.utils.timing", "enable_timing")
        imports["show_timing_summary"] = self.get_cached_import("par_gpt.utils.timing", "show_timing_summary")
        imports["show_timing_details"] = self.get_cached_import("par_gpt.utils.timing", "show_timing_details")

        return imports

    def load_web_imports(self) -> dict[str, Any]:
        """Load web functionality when needed."""
        imports = {}

        imports["fetch_url_and_convert_to_markdown"] = self.get_cached_import(
            "par_ai_core.web_tools", "fetch_url_and_convert_to_markdown"
        )

        return imports

    def load_sandbox_imports(self) -> dict[str, Any]:
        """Load sandbox functionality when needed."""
        imports = {}

        imports["SandboxAction"] = self.get_cached_import("sandbox", "SandboxAction")
        imports["install_sandbox"] = self.get_cached_import("sandbox", "install_sandbox")
        imports["start_sandbox"] = self.get_cached_import("sandbox", "start_sandbox")
        imports["stop_sandbox"] = self.get_cached_import("sandbox", "stop_sandbox")

        return imports

    def load_path_security_imports(self) -> dict[str, Any]:
        """Load path security functionality when needed."""
        imports = {}

        imports["PathSecurityError"] = self.get_cached_import("par_gpt.utils.path_security", "PathSecurityError")
        imports["sanitize_filename"] = self.get_cached_import("par_gpt.utils.path_security", "sanitize_filename")
        imports["validate_relative_path"] = self.get_cached_import(
            "par_gpt.utils.path_security", "validate_relative_path"
        )
        imports["validate_within_base"] = self.get_cached_import("par_gpt.utils.path_security", "validate_within_base")

        return imports

    def load_tts_imports(self) -> dict[str, Any]:
        """Load TTS functionality when needed."""
        imports = {}
        imports["pyttsx3"] = self.get_cached_import("pyttsx3")
        imports["ElevenLabs"] = self.get_cached_import("elevenlabs.client", "ElevenLabs")
        imports["OpenAI"] = self.get_cached_import("openai", "OpenAI")
        imports["Kokoro"] = self.get_cached_import("kokoro_onnx", "Kokoro")
        imports["play"] = self.get_cached_import("elevenlabs", "play")
        imports["numpy"] = self.get_cached_import("numpy")
        return imports

    def load_voice_input_imports(self) -> dict[str, Any]:
        """Load voice input functionality when needed."""
        imports = {}
        imports["AudioToTextRecorder"] = self.get_cached_import("RealtimeSTT", "AudioToTextRecorder")
        return imports

    def load_github_imports(self) -> dict[str, Any]:
        """Load GitHub API functionality when needed."""
        imports = {}
        imports["Github"] = self.get_cached_import("github", "Github")
        imports["Auth"] = self.get_cached_import("github", "Auth")
        imports["AuthenticatedUser"] = self.get_cached_import("github", "AuthenticatedUser")
        return imports

    def load_feed_imports(self) -> dict[str, Any]:
        """Load feed processing functionality when needed."""
        imports = {}
        imports["feedparser"] = self.get_cached_import("feedparser")
        return imports

    def load_rich_imports(self) -> dict[str, Any]:
        """Load Rich UI components when needed."""
        imports = {}
        imports["Panel"] = self.get_cached_import("rich.panel", "Panel")
        imports["Prompt"] = self.get_cached_import("rich.prompt", "Prompt")
        imports["Text"] = self.get_cached_import("rich.text", "Text")
        imports["Pretty"] = self.get_cached_import("rich.pretty", "Pretty")
        imports["Markdown"] = self.get_cached_import("rich.markdown", "Markdown")
        return imports


# Global lazy import manager instance
_lazy_import_manager = LazyImportManager()


def get_command_imports(command: str, **kwargs) -> dict[str, Any]:
    """Get imports for a specific command type."""
    if command in ["version", "help", "show_env"]:
        return _lazy_import_manager.load_minimal_imports()
    elif command == "llm":
        imports = _lazy_import_manager.load_basic_llm_imports()
        # Add media imports if needed for vision models
        if kwargs.get("has_image_context", False):
            imports.update(_lazy_import_manager.load_media_imports())
        return imports
    elif command == "agent":
        imports = _lazy_import_manager.load_agent_imports()
        # Add additional imports based on agent requirements
        if kwargs.get("has_tts", False):
            imports.update(_lazy_import_manager.load_media_imports())
        return imports
    elif command == "git":
        imports = _lazy_import_manager.load_basic_llm_imports()
        imports.update(_lazy_import_manager.load_git_imports())
        return imports
    elif command == "sandbox":
        return _lazy_import_manager.load_sandbox_imports()
    else:
        # For unknown commands, load basic imports
        return _lazy_import_manager.load_basic_llm_imports()


def lazy_import(module_path: str, item_name: str | None = None) -> Any:
    """Convenience function for lazy importing."""
    return _lazy_import_manager.get_cached_import(module_path, item_name)


def initialize_globals_for_command(command: str) -> None:
    """Initialize global state based on command requirements."""
    # Only initialize globals when needed for specific commands
    if command in ["agent", "llm", "git", "code-review"]:
        from par_gpt import ensure_initialized

        ensure_initialized()
