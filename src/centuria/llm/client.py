"""LLM client using LiteLLM."""

import os

import litellm
from dotenv import load_dotenv

load_dotenv()

# Suppress litellm logging
litellm.suppress_debug_info = True


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
