"""Media generation utilities: text-to-speech (ElevenLabs) and DALL-E image generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from par_ai_core.llm_config import LlmConfig
from par_ai_core.llm_providers import LlmProvider, is_provider_api_key_set, provider_base_urls, provider_env_key_names
from par_ai_core.par_logging import console_err
from pydantic import SecretStr

from ._singletons import cache_manager


def speak(text: str) -> None:
    """Synthesize speech from ``text`` with ElevenLabs and play it immediately.

    Uses the ``eleven_flash_v2_5`` model and a fixed voice, reading the API key from the
    ``ELEVENLABS_API_KEY`` environment variable. Audio is generated synchronously (no
    streaming) and played back as soon as it is fully assembled.

    Args:
        text: The text to convert to speech.

    Raises:
        ImportError: If the ``elevenlabs`` package is not installed.
        Exception: Propagates any error from the ElevenLabs client or audio playback.
    """
    from elevenlabs import play  # type: ignore[reportMissingImports]
    from elevenlabs.client import ElevenLabs  # type: ignore[reportMissingImports]

    # start_time = time.time()
    model = "eleven_flash_v2_5"
    # model="eleven_flash_v2"
    # model = "eleven_turbo_v2"
    # model = "eleven_turbo_v2_5"
    # model="eleven_multilingual_v2"
    voice = "XB0fDUnXU5powFXDhCwa"  # Charlotte
    elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    audio_generator = elevenlabs_client.generate(  # type: ignore
        text=text,
        voice=voice,
        model=model,
        stream=False,
    )
    audio_bytes = b"".join(list(audio_generator))
    # duration = time.time() - start_time
    # console_err.print(f"Model {model} completed tts in {duration:.2f} seconds")
    play(audio_bytes)


def image_gen_dali(
    prompt: str, model_name: Literal["dall-e-2", "dall-e-3"] = "dall-e-3", upgrade_prompt: LlmConfig | None = None
) -> Path:
    from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper

    if upgrade_prompt:
        chat = upgrade_prompt.build_chat_model()
        prompt = str(
            chat.invoke(
                [
                    (
                        "system",
                        "Generate a detailed prompt under 800 chars in order to generate an image based on the users description. Only return the updated prompt. Do not include any intro or explanation.",
                    ),
                    ("user", prompt),
                ]
            ).content
        )
        console_err.print(prompt)
    img_gen = DallEAPIWrapper()
    img_gen.model_name = model_name
    if not is_provider_api_key_set(LlmProvider.OPENAI):
        img_gen.openai_api_key = SecretStr(os.environ[provider_env_key_names[LlmProvider.OPENAI]])
        img_gen.openai_api_base = provider_base_urls[LlmProvider.OPENAI]
    image_url = img_gen.run(prompt)
    return cache_manager.download(image_url)
