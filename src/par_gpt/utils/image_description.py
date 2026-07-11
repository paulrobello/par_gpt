"""Image description via LLM utilities."""

from __future__ import annotations

from pathlib import Path

from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_image_utils import image_to_base64, image_to_chat_message, try_get_image_type
from par_ai_core.llm_providers import LlmProvider

from ._singletons import cache_manager


def describe_image_with_llm(img: str | Path, llm_config: LlmConfig | None = None) -> str:
    """
    Describes the image using a LLM.

    Args:
        img (str | Path): The image file path or URL.
        llm_config (LlmConfig | None): The LLM configuration. Defaults to None = OpenAI GPT-4o.

    Returns:
        str: A description of the image.
    """
    if isinstance(img, str):
        if not img.startswith("data:image/"):
            if img.startswith("http"):
                img = cache_manager.download(img)
            else:
                img = Path(img)
            if not img.is_file():
                raise ValueError(f"No such file or directory: {img}")
            img = image_to_base64(img.read_bytes(), try_get_image_type(img))
    msg = image_to_chat_message(str(img))
    chat = (llm_config or LlmConfig(LlmProvider.OPENAI, "gpt-4.1")).build_chat_model()
    return str(
        chat.invoke(
            [
                ("system", "Describe the image in great detail"),
                ("user", [{"type": "text", "text": "describe the image"}, msg]),  # type: ignore
            ]
        ).content
    )
