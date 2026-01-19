"""Shared utilities for Centuria."""

import json
import re


def parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks.

    LLMs often wrap JSON in ```json ... ``` blocks. This extracts and parses
    the JSON regardless of formatting.
    """
    content = content.strip()

    # Handle markdown code blocks
    if content.startswith("```"):
        # Split on ``` and take the content between first pair
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            # Remove language identifier if present (e.g., "json")
            if content.startswith("json"):
                content = content[4:]
            elif content.startswith("\n"):
                content = content[1:]
        content = content.strip()

    return json.loads(content)


def extract_json_from_text(text: str) -> dict | None:
    """Try to extract JSON object from text that may contain other content.

    Useful when LLM includes explanation before/after the JSON.
    Returns None if no valid JSON found.
    """
    text = text.strip()

    # First try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try markdown code block extraction
    try:
        return parse_json_response(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object with regex
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return None
