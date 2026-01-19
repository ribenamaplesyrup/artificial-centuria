"""Extract structured information from personal data files using LLM."""

import json
from pathlib import Path

from pydantic import BaseModel, field_validator

from centuria.data import load_text
from centuria.llm import complete
from centuria.utils import parse_json_response

# =============================================================================
# Extraction Prompts
# =============================================================================

# Maximum characters of raw context to include in prompts
RAW_CONTEXT_CHAR_LIMIT = 8000

PROFILE_EXTRACTION_PROMPT = """Analyze the following personal data and extract a structured profile.

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

CRITICAL - WRITE LIKE A NEUTRAL OBSERVER, NOT AN ADVERTISER:
Your output must read like a researcher's field notes, not a LinkedIn profile or dating app bio.

BANNED PHRASES (never use these or similar):
- "passionate about", "driven", "dedicated to", "committed to"
- "in their free time", "enjoys exploring", "loves discovering"
- "well-rounded", "diverse interests", "eclectic taste"
- "balance of", "blend of", "mix of work and play"
- "community-minded", "family-oriented", "health-conscious"
- "thrives on", "finds joy in", "takes pride in"
- "keen interest", "deep appreciation", "strong believer"
- Any phrase that sounds promotional or self-congratulatory

GOOD NEUTRAL PHRASING:
- "Works as a..." NOT "accomplished professional who..."
- "Watches..." NOT "enjoys watching..." or "passionate about..."
- "Reads..." NOT "avid reader of..."
- "Goes to church on Sundays" NOT "deeply spiritual" or "faith-driven"
- "Spends evenings on social media" NOT "stays connected with..."
- "Doesn't exercise regularly" NOT "focused on other priorities"

Include mundane and unflattering details where relevant:
- Long commutes, overtime, tiredness
- Routine habits, not just interesting hobbies
- Things they don't do (doesn't read, doesn't travel, doesn't cook)
- Ordinary entertainment (TV, social media scrolling, gaming)

The context statement should be written in third person, factual, and suitable for use as system prompt context.

Write the context statement now:"""


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

    @field_validator(
        "key_skills",
        "reading_genres",
        "media_diet",
        "intellectual_interests",
        "key_values",
        "causes_care_about",
        mode="before",
    )
    @classmethod
    def none_to_empty_list(cls, v):
        """Convert None to empty list for list fields."""
        return v if v is not None else []


async def extract_profile_from_text(content: str) -> ExtractedProfile:
    """Extract a structured profile from raw text content."""
    prompt = PROFILE_EXTRACTION_PROMPT.format(content=content)
    result = await complete(prompt)

    try:
        data = parse_json_response(result.content)
        return ExtractedProfile(raw_context=content, **data)
    except (json.JSONDecodeError, TypeError):
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


async def build_context_statement(profile: ExtractedProfile) -> str:
    """Build a rich context statement from an extracted profile."""
    # Convert profile to JSON, excluding raw_context for the structured view
    profile_dict = profile.model_dump(exclude={"raw_context"})
    profile_json = json.dumps(profile_dict, indent=2)

    prompt = CONTEXT_STATEMENT_PROMPT.format(
        profile_json=profile_json,
        raw_context=profile.raw_context[:RAW_CONTEXT_CHAR_LIMIT],
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
