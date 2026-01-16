"""LLM client using LiteLLM."""

import os
import warnings
from pathlib import Path

import litellm
from dotenv import load_dotenv

# Load .env from project root (handles running from notebooks/)
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Suppress litellm noise
litellm.suppress_debug_info = True
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


async def complete(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
) -> str:
    """
    Get a completion from an LLM.

    Args:
        prompt: The user prompt
        system: Optional system prompt
        model: Model to use (defaults to DEFAULT_MODEL env var or gpt-4o)

    Returns:
        The completion text
    """
    model = model or os.getenv("DEFAULT_MODEL", "gpt-4o")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = await litellm.acompletion(model=model, messages=messages)
    return response.choices[0].message.content
