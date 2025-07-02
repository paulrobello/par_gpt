"""LLM invocation utilities for consistent model interactions."""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from par_ai_core.llm_config import LlmConfig, llm_run_manager
from par_ai_core.par_logging import console_err
from rich.console import Console


class LLMInvoker:
    """Handles consistent LLM invocations across the application."""

    def __init__(self, config: LlmConfig, console: Console | None = None):
        """
        Initialize the LLM invoker.

        Args:
            config: LLM configuration to use.
            console: Optional console for output. Defaults to console_err.
        """
        self.config = config
        self.console = console or console_err
        self._chat_model: BaseChatModel | None = None

    @property
    def chat_model(self) -> BaseChatModel:
        """Get or build the chat model."""
        if self._chat_model is None:
            self._chat_model = self.config.build_chat_model()
        return self._chat_model

    def invoke(
        self,
        messages: list[BaseMessage] | list[tuple[str, str]],
        **kwargs: Any,
    ) -> BaseMessage:
        """
        Invoke the LLM with the given messages.

        Args:
            messages: List of messages to send to the LLM.
            **kwargs: Additional arguments to pass to the model.

        Returns:
            Message result from the model.
        """
        # Ensure we have the runnable config
        if "config" not in kwargs:
            kwargs["config"] = llm_run_manager.get_runnable_config(self.chat_model.name)

        try:
            return self.chat_model.invoke(messages, **kwargs)
        except Exception as e:
            self.console.print(f"[red]Error invoking LLM: {e}[/red]")
            raise

    def invoke_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        **kwargs: Any,
    ) -> BaseMessage:
        """
        Invoke the LLM with system and user prompts.

        Args:
            system_prompt: System prompt to use.
            user_prompt: User prompt to use.
            **kwargs: Additional arguments to pass to the model.

        Returns:
            Message result from the model.
        """
        messages = [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
        return self.invoke(messages, **kwargs)

    def get_text_response(
        self,
        messages: list[BaseMessage] | list[tuple[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Get a text response from the LLM.

        Args:
            messages: List of messages to send to the LLM.
            **kwargs: Additional arguments to pass to the model.

        Returns:
            Text content from the model response.
        """
        result = self.invoke(messages, **kwargs)
        return str(result.content) if hasattr(result, "content") else ""


# Convenience function for simple invocations
def invoke_llm(
    config: LlmConfig,
    messages: list[BaseMessage] | list[tuple[str, str]],
    console: Console | None = None,
    **kwargs: Any,
) -> BaseMessage:
    """
    Convenience function for simple LLM invocations.

    Args:
        config: LLM configuration to use.
        messages: List of messages to send to the LLM.
        console: Optional console for output.
        **kwargs: Additional arguments to pass to the model.

    Returns:
        Message result from the model.
    """
    invoker = LLMInvoker(config, console)
    return invoker.invoke(messages, **kwargs)
