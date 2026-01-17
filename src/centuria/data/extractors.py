"""Extract structured information from personal data files using LLM."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from centuria.data import load_text
from centuria.llm import complete


class ExtractedProfile(BaseModel):
    """Structured profile extracted from personal data."""

    # Demographics
    name: str | None = None
    location: str | None = None
    age_range: str | None = None  # e.g., "30-35"

    # Professional
    current_role: str | None = None
    industry: str | None = None
    years_experience: int | None = None
    key_skills: list[str] = []
    education_level: str | None = None
    education_field: str | None = None

    # Intellectual interests
    reading_genres: list[str] = []
    media_diet: list[str] = []  # Types of media consumed
    intellectual_interests: list[str] = []

    # Values and worldview
    political_lean: str | None = None  # e.g., "left", "right", "heterodox", "apolitical"
    key_values: list[str] = []
    causes_care_about: list[str] = []

    # Personality indicators
    communication_style: str | None = None
    work_style: str | None = None
    risk_tolerance: str | None = None

    # Raw context for LLM prompting
    raw_context: str = ""


EXTRACTION_PROMPT = """Analyze the following personal data and extract a structured profile.

<personal_data>
{content}
</personal_data>

Based on this data, extract the following information. For each field, provide your best inference based on the available evidence. If something cannot be reasonably inferred, leave it as null.

Return a JSON object with these fields:
{{
    "name": "string or null",
    "location": "string or null (city/country)",
    "age_range": "string or null (e.g., '30-35')",
    "current_role": "string or null",
    "industry": "string or null",
    "years_experience": "number or null",
    "key_skills": ["list", "of", "skills"],
    "education_level": "string or null (e.g., 'Masters', 'PhD', 'Bachelors')",
    "education_field": "string or null",
    "reading_genres": ["list", "of", "genres"],
    "media_diet": ["types", "of", "media", "consumed"],
    "intellectual_interests": ["list", "of", "topics"],
    "political_lean": "string or null (left/right/center/heterodox/apolitical)",
    "key_values": ["list", "of", "core", "values"],
    "causes_care_about": ["list", "of", "causes"],
    "communication_style": "string or null (e.g., 'direct', 'diplomatic', 'analytical')",
    "work_style": "string or null (e.g., 'collaborative', 'independent', 'mixed')",
    "risk_tolerance": "string or null (e.g., 'risk-averse', 'moderate', 'risk-seeking')"
}}

Return ONLY the JSON object, no other text."""


async def extract_profile_from_text(content: str) -> ExtractedProfile:
    """Extract a structured profile from raw text content."""
    import json

    prompt = EXTRACTION_PROMPT.format(content=content)
    result = await complete(prompt)

    # Parse the JSON response
    try:
        # Handle potential markdown code blocks
        response_text = result.content.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        data = json.loads(response_text)
        return ExtractedProfile(raw_context=content, **data)
    except (json.JSONDecodeError, TypeError) as e:
        # If parsing fails, return profile with just raw context
        return ExtractedProfile(raw_context=content)


async def extract_profile_from_files(paths: list[str]) -> ExtractedProfile:
    """Extract a structured profile from multiple personal data files."""
    # Load and tag each file
    sections = []
    for path in paths:
        p = Path(path)
        content = load_text(path)
        filename = p.name
        sections.append(f"=== {filename} ===\n{content}")

    combined = "\n\n".join(sections)
    return await extract_profile_from_text(combined)


CONTEXT_STATEMENT_PROMPT = """You are creating a factual persona context statement for use in LLM role-playing.

Based on the following structured profile and raw personal data, write a clear, objective context statement.

<structured_profile>
{profile_json}
</structured_profile>

<raw_data>
{raw_context}
</raw_data>

Write a context statement (300-500 words) that:
1. States factual information about this person's work, education, and background
2. Lists their intellectual interests and media consumption without editorializing
3. Notes any genuinely unusual or contradictory elements (e.g., if their media diet spans opposing political viewpoints, state this plainly)
4. Infers likely opinions and worldview based strictly on evidence, using hedged language ("likely", "suggests", "probably")
5. Describes observable patterns in their career or interests

CRITICAL RULES:
- Do NOT use flattering or praising language (no "accomplished", "impressive", "key player", "dynamic", "formidable", etc.)
- Do NOT use superlatives or hyperbole
- State facts plainly. "Works as X at Y" not "excels as X at Y"
- If something is genuinely notable or unusual, state what it is factually without calling it "remarkable" or "unique"
- Write like a neutral researcher documenting a subject, not like a LinkedIn recommendation
- Avoid corporate buzzwords and inflated language

The context statement should be written in third person, factual, and suitable for use as system prompt context.

Write the context statement now:"""


async def build_context_statement(profile: ExtractedProfile) -> str:
    """Build a rich context statement from an extracted profile."""
    import json

    # Convert profile to JSON, excluding raw_context for the structured view
    profile_dict = profile.model_dump(exclude={"raw_context"})
    profile_json = json.dumps(profile_dict, indent=2)

    prompt = CONTEXT_STATEMENT_PROMPT.format(
        profile_json=profile_json,
        raw_context=profile.raw_context[:8000],  # Limit raw context size
    )

    result = await complete(prompt)
    return result.content.strip()


async def process_personal_folder(folder_path: str) -> tuple[ExtractedProfile, str]:
    """
    Process all files in a personal data folder.

    Returns:
        Tuple of (extracted_profile, context_statement)
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"Not a directory: {folder_path}")

    # Find all processable files
    valid_extensions = {".pdf", ".txt", ".md"}
    files = [
        str(f) for f in folder.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions
    ]

    if not files:
        raise ValueError(f"No valid files found in {folder_path}")

    # Extract profile and build context
    profile = await extract_profile_from_files(files)
    context_statement = await build_context_statement(profile)

    return profile, context_statement
