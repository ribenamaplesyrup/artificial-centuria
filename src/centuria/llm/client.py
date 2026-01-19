"""LLM client using LiteLLM."""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path

import litellm
from dotenv import load_dotenv

from centuria.config import DEFAULT_MODEL

# Load .env from project root (handles running from notebooks/)
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# Suppress litellm noise
litellm.suppress_debug_info = True
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


@dataclass
class CompletionResult:
    """Result from an LLM completion with usage stats."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    cost: float  # USD


@dataclass
class CostEstimate:
    """Estimated cost for a completion."""

    prompt_tokens: int
    completion_tokens: int  # estimated
    cost: float  # USD


def estimate_cost(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    estimated_completion_tokens: int = 10,
) -> CostEstimate:
    """
    Estimate the cost of a completion before sending it.

    Args:
        prompt: The user prompt
        system: Optional system prompt
        model: Model to use (defaults to DEFAULT_MODEL env var or gpt-4o)
        estimated_completion_tokens: Expected output tokens (default 10 for short responses)

    Returns:
        CostEstimate with token counts and estimated cost
    """
    model = model or os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Count prompt tokens
    prompt_tokens = litellm.token_counter(model=model, messages=messages)

    # Build full prompt string for cost calculation
    full_prompt = (system or "") + prompt
    # Estimate completion as roughly N tokens worth of text
    estimated_completion = "word " * estimated_completion_tokens

    total_cost = litellm.completion_cost(
        model=model,
        prompt=full_prompt,
        completion=estimated_completion,
    )

    return CostEstimate(
        prompt_tokens=prompt_tokens,
        completion_tokens=estimated_completion_tokens,
        cost=total_cost,
    )


async def complete(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    api_keys: dict[str, str] | None = None,
) -> CompletionResult:
    """
    Get a completion from an LLM.

    Args:
        prompt: The user prompt
        system: Optional system prompt
        model: Model to use (defaults to DEFAULT_MODEL env var or gpt-4o)
        api_keys: Optional dict with provider keys (openai, anthropic, gemini)
                  to use instead of environment variables

    Returns:
        CompletionResult with content and usage stats
    """
    model = model or os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    # Build kwargs with optional API key override
    kwargs: dict = {"model": model, "messages": messages}

    if api_keys:
        # LiteLLM accepts api_key parameter to override env vars
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            if api_keys.get("openai"):
                kwargs["api_key"] = api_keys["openai"]
        elif model.startswith("claude"):
            if api_keys.get("anthropic"):
                kwargs["api_key"] = api_keys["anthropic"]
        elif model.startswith("gemini"):
            if api_keys.get("gemini"):
                kwargs["api_key"] = api_keys["gemini"]

    response = await litellm.acompletion(**kwargs)

    # Calculate cost using litellm's built-in pricing
    cost = litellm.completion_cost(completion_response=response)

    return CompletionResult(
        content=response.choices[0].message.content,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        cost=cost,
    )
