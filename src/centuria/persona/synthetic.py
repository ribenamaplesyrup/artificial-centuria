"""Synthetic persona generation - file-first approach.

Workflow:
1. Generate a synthetic identity (name, age, location, occupation)
2. Generate 2-5 personal data files for that identity
3. Save files to data/synthetic/{name}/
4. Use the same extraction pipeline as real data to create the persona
"""

import asyncio
import random
import uuid
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from centuria.config import (
    AGE_ADULT_MIN,
    AGE_DATING_MAX,
    AGE_DATING_MIN,
    AGE_FACEBOOK_MIN,
    AGE_HEALTH_TRACKING_MIN,
    AGE_INSTAGRAM_MAX,
    AGE_INSTAGRAM_MIN,
    AGE_MIDDLE_MAX,
    AGE_MIDDLE_MIN,
    AGE_NEXTDOOR_MIN,
    AGE_OLDER_MIN,
    AGE_PROFESSIONAL_MIN,
    AGE_REDDIT_MAX,
    AGE_REDDIT_MIN,
    AGE_RETIREMENT,
    AGE_TIKTOK_MAX,
    AGE_TIKTOK_MIN,
    AGE_TWITTER_MAX,
    AGE_TWITTER_MIN,
    AGE_WORKING_MIN,
    AGE_YOUNG_MAX,
    PROFESSIONAL_KEYWORDS,
)

# =============================================================================
# Identity Generation Prompt
# =============================================================================

IDENTITY_GENERATION_PROMPT = """Generate a realistic synthetic identity for a person.

{constraints}

CRITICAL - AVOID LLM BIAS:
LLMs default to generating progressive, educated, urban professionals in their 30s-40s with creative hobbies.
You MUST actively counteract this to create realistic population diversity.

Ensure genuine diversity across these dimensions:
- Gender: ~50% male, ~50% female. Occasionally non-binary.
- Age: Full adult range 18-80. Include young adults (18-25), middle-aged (40-55), elderly (65+).
- Education: Only 35% of adults have degrees. Include: high school only, trade certificates, some college no degree, GED, no formal qualifications.
- Occupation: Most people work in retail, trades, healthcare support, transport, admin, food service, manufacturing, agriculture - NOT tech/creative/consulting.
- Location: Include small towns, rural areas, suburbs, unfashionable cities, non-Western countries. Not just coastal liberal metros.
- Politics: Include conservatives, libertarians, apolitical people, single-issue voters, nationalists, traditionalists. Most people don't call themselves "progressive."
- Interests: Include TV, sports, church, video games, hunting, fishing, cars, crafts, family time. Not everyone does yoga and watercolor painting.

CRITICAL - AVOID SYCOPHANTIC LANGUAGE IN PERSONALITY SKETCH:
Do NOT write personality sketches that sound like dating profiles, LinkedIn summaries, or marketing copy.

BANNED PHRASES (never use these or similar):
- "passionate about", "driven professional", "dedicated to"
- "in their free time", "enjoys exploring", "loves discovering"
- "cozy/cozying up with", "curling up with a good book"
- "weekends are spent", "can often be found"
- "balance of", "blend of", "mix of work and play"
- "community-minded", "family-oriented", "health-conscious"
- Any phrase that sounds like an advert or self-promotional content

GOOD personality sketches are NEUTRAL and FACTUAL:
- "Watches football most weekends. Goes fishing with his brother occasionally. Doesn't read much."
- "Works overtime frequently. Spends evenings on TikTok or with her kids. Attends church on Sundays."
- "Plays video games after work. Orders takeaway most nights. Sees friends at the pub on Fridays."
- "Commutes 45 minutes each way. Too tired for hobbies most days. Watches reality TV to unwind."

Real people are often tired, have mundane routines, and don't have "passions" - they have habits and obligations.

Return a JSON object with:
{{
    "name": "Full Name",
    "age": integer,
    "gender": "string",
    "location": "City/Town, Country",
    "occupation": "Job title",
    "industry": "Industry sector",
    "education": "Highest education (e.g., 'High school diploma', 'Trade certificate in plumbing', 'Some college', 'No formal qualifications')",
    "political_lean": "Be specific and realistic (e.g., 'Conservative Republican', 'Apolitical - doesn't follow politics', 'Libertarian', 'Pro-union Democrat', 'Traditionalist Catholic')",
    "personality_sketch": "2-3 NEUTRAL, FACTUAL sentences. State what they DO, not what they 'love' or are 'passionate about'. Include mundane reality: tiredness, routine, obligations."
}}

Return ONLY the JSON object."""


def format_identity_text(identity) -> str:
    """Format a SyntheticIdentity for use in prompts.

    Args:
        identity: A SyntheticIdentity object with name, age, gender, location,
                  occupation, industry, education, political_lean, personality_sketch

    Returns:
        Formatted string for embedding in prompts
    """
    return f"""Name: {identity.name}
Age: {identity.age}
Gender: {identity.gender}
Location: {identity.location}
Occupation: {identity.occupation}
Industry: {identity.industry}
Education: {identity.education}
Political lean: {identity.political_lean}

Personality: {identity.personality_sketch}"""
from centuria.data import process_personal_folder
from centuria.llm import complete, estimate_cost, CostEstimate
from centuria.models import Persona
from centuria.persona.file_types import FILE_TYPES, list_file_types
from centuria.utils import parse_json_response


class SyntheticPersonaSpec(BaseModel):
    """Specification for generating a synthetic persona."""

    # Demographics
    age_range: tuple[int, int] = (25, 65)
    locations: list[str] | None = None
    gender: str | None = None

    # Professional constraints
    industries: list[str] | None = None
    education_levels: list[str] | None = None

    # Worldview constraints
    political_spectrum: list[str] | None = None

    # File generation
    min_files: int = 2
    max_files: int = 5


class SyntheticIdentity(BaseModel):
    """Basic identity for a synthetic person - used to generate files."""

    name: str
    age: int
    gender: str
    location: str
    occupation: str
    industry: str
    education: str
    political_lean: str
    personality_sketch: str  # Brief sketch to maintain consistency across files


def _build_identity_constraints(
    spec: SyntheticPersonaSpec,
    existing_identities: list[SyntheticIdentity] | None = None
) -> str:
    """Build constraints text for identity generation."""
    constraints = []

    if spec.age_range:
        constraints.append(f"Age: between {spec.age_range[0]} and {spec.age_range[1]}")
    if spec.locations:
        constraints.append(f"Location: one of {', '.join(spec.locations)}")
    if spec.gender:
        constraints.append(f"Gender: {spec.gender}")
    if spec.industries:
        constraints.append(f"Industry: one of {', '.join(spec.industries)}")
    if spec.education_levels:
        constraints.append(f"Education: {', '.join(spec.education_levels)}")
    if spec.political_spectrum:
        constraints.append(f"Political lean: {', '.join(spec.political_spectrum)}")

    # Diversity guidance
    if existing_identities:
        recent = existing_identities[-5:]
        existing_summary = "\n".join(
            f"- {p.name}: {p.age}yo {p.occupation} in {p.location}, {p.political_lean}"
            for p in recent
        )
        constraints.append(
            f"\nFor diversity, create someone different from these recent personas:\n{existing_summary}"
        )

    if constraints:
        return "Constraints:\n" + "\n".join(f"- {c}" for c in constraints if not c.startswith("\n")) + \
               "\n".join(c for c in constraints if c.startswith("\n"))
    return "No specific constraints - create any realistic person."


async def generate_identity(
    spec: SyntheticPersonaSpec | None = None,
    existing_identities: list[SyntheticIdentity] | None = None,
) -> SyntheticIdentity:
    """Generate a synthetic identity."""
    spec = spec or SyntheticPersonaSpec()
    constraints = _build_identity_constraints(spec, existing_identities)

    prompt = IDENTITY_GENERATION_PROMPT.format(constraints=constraints)
    result = await complete(prompt)

    data = parse_json_response(result.content)
    return SyntheticIdentity(**data)


async def generate_file_content(identity: SyntheticIdentity, file_type: str) -> str:
    """Generate content for a specific file type."""
    if file_type not in FILE_TYPES:
        raise ValueError(f"Unknown file type: {file_type}")

    file_config = FILE_TYPES[file_type]
    identity_text = format_identity_text(identity)

    prompt = file_config["prompt"].format(identity=identity_text)
    result = await complete(prompt)
    return result.content.strip()


async def generate_synthetic_files(
    identity: SyntheticIdentity,
    output_dir: str | Path,
    file_types: list[str] | None = None,
    num_files: int | None = None,
) -> dict[str, Path]:
    """
    Generate synthetic data files for an identity.

    Args:
        identity: The synthetic identity
        output_dir: Directory to save files
        file_types: Specific file types to generate (None = random selection)
        num_files: Number of files to generate (ignored if file_types specified)

    Returns:
        Dict mapping file type to saved file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which files to generate
    if file_types is None:
        # Always include CV and one of reading_list/subscriptions
        required = ["cv"]
        optional = [k for k in FILE_TYPES.keys() if k != "cv"]

        # Randomly select additional files
        num_additional = (num_files or random.randint(2, 5)) - len(required)
        num_additional = max(1, min(num_additional, len(optional)))
        additional = random.sample(optional, num_additional)

        file_types = required + additional

    # Generate all files in parallel
    contents = await asyncio.gather(*[
        generate_file_content(identity, file_type)
        for file_type in file_types
    ])

    # Save files
    saved_files = {}
    for file_type, content in zip(file_types, contents):
        config = FILE_TYPES[file_type]
        file_path = output_dir / config["filename"]
        file_path.write_text(content)
        saved_files[file_type] = file_path

    # Also save the identity for reference
    identity_path = output_dir / "identity.json"
    identity_path.write_text(identity.model_dump_json(indent=2))

    return saved_files


async def generate_synthetic_persona(
    spec: SyntheticPersonaSpec | None = None,
    output_base_dir: str | Path = "data/synthetic",
    existing_identities: list[SyntheticIdentity] | None = None,
    file_types: list[str] | None = None,
) -> tuple[Persona, SyntheticIdentity, Path]:
    """
    Generate a complete synthetic persona with data files.

    Workflow:
    1. Generate synthetic identity
    2. Generate 2-5 data files for that identity
    3. Save to data/synthetic/{name}/
    4. Use process_personal_folder() to create persona

    Returns:
        Tuple of (Persona, SyntheticIdentity, folder_path)
    """
    spec = spec or SyntheticPersonaSpec()
    output_base_dir = Path(output_base_dir)

    # Generate identity
    identity = await generate_identity(spec, existing_identities)

    # Create folder name from identity
    folder_name = identity.name.lower().replace(" ", "_").replace("'", "")
    folder_path = output_base_dir / folder_name

    # Handle existing folder
    if folder_path.exists():
        # Add random suffix
        folder_path = output_base_dir / f"{folder_name}_{uuid.uuid4().hex[:6]}"

    # Generate files
    num_files = random.randint(spec.min_files, spec.max_files)
    await generate_synthetic_files(
        identity=identity,
        output_dir=folder_path,
        file_types=file_types,
        num_files=num_files,
    )

    # Use the same pipeline as real data
    profile, context_statement = await process_personal_folder(str(folder_path))

    # Create persona
    persona = Persona(
        id=str(uuid.uuid4()),
        name=identity.name,
        context=context_statement,
    )

    return persona, identity, folder_path


async def generate_persona_batch(
    count: int,
    spec: SyntheticPersonaSpec | None = None,
    output_base_dir: str | Path = "data/synthetic",
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[tuple[Persona, SyntheticIdentity, Path]]:
    """
    Generate a batch of synthetic personas.

    Args:
        count: Number of personas to generate
        spec: Constraints for generation
        output_base_dir: Base directory for synthetic data folders
        progress_callback: Optional callback(current, total)

    Returns:
        List of (Persona, SyntheticIdentity, folder_path) tuples
    """
    results = []
    existing_identities = []

    for i in range(count):
        persona, identity, folder_path = await generate_synthetic_persona(
            spec=spec,
            output_base_dir=output_base_dir,
            existing_identities=existing_identities,
        )
        results.append((persona, identity, folder_path))
        existing_identities.append(identity)

        if progress_callback:
            progress_callback(i + 1, count)

    return results


def list_available_file_types() -> dict[str, str]:
    """List available file types and their descriptions."""
    return list_file_types()


def infer_file_types_for_identity(identity: SyntheticIdentity, num_files: int = 3) -> list[str]:
    """
    Infer appropriate file types for a person based on their characteristics.

    Not everyone has a CV (retirees, students, children). Not everyone uses
    LinkedIn or Twitter. This function selects realistic file types
    based on the person's age, occupation, and lifestyle.

    Args:
        identity: The synthetic identity
        num_files: Target number of files (2-5)

    Returns:
        List of file type keys to generate
    """
    occupation_lower = identity.occupation.lower()
    age = identity.age

    # Build weighted pool of appropriate file types
    # (file_type, weight) - higher weight = more likely to be selected
    weighted_pool = []

    # Determine characteristics
    is_working_adult = (
        age >= AGE_WORKING_MIN and age < AGE_RETIREMENT and
        "retired" not in occupation_lower and
        "student" not in occupation_lower and
        "child" not in occupation_lower and
        "unemployed" not in occupation_lower
    )
    is_professional = any(word in occupation_lower for word in PROFESSIONAL_KEYWORDS)
    is_young = age < AGE_YOUNG_MAX
    is_middle_aged = AGE_MIDDLE_MIN <= age < AGE_MIDDLE_MAX
    is_older = age >= AGE_OLDER_MIN

    # ==========================================================================
    # PROFESSIONAL / CAREER
    # ==========================================================================
    if is_working_adult:
        weighted_pool.append(("cv", 3))
        weighted_pool.append(("work_calendar", 2))
        weighted_pool.append(("email_signature", 2))
    if is_professional and age >= AGE_PROFESSIONAL_MIN:
        weighted_pool.append(("linkedin_summary", 3))

    # ==========================================================================
    # SOCIAL MEDIA - varies by age
    # ==========================================================================
    if AGE_TWITTER_MIN <= age < AGE_TWITTER_MAX:
        weighted_pool.append(("twitter_bio", 1))
    if AGE_INSTAGRAM_MIN <= age < AGE_INSTAGRAM_MAX:
        weighted_pool.append(("instagram_bio", 2))
    if age >= AGE_FACEBOOK_MIN:
        weighted_pool.append(("facebook_about", 2 if is_older else 1))
    if AGE_REDDIT_MIN <= age < AGE_REDDIT_MAX:
        weighted_pool.append(("reddit_profile", 1))
    if AGE_TIKTOK_MIN <= age < AGE_TIKTOK_MAX:
        weighted_pool.append(("tiktok_profile", 2))
    if age >= AGE_NEXTDOOR_MIN:
        weighted_pool.append(("nextdoor_activity", 1))

    # ==========================================================================
    # MEDIA CONSUMPTION - universal but weighted
    # ==========================================================================
    weighted_pool.append(("reading_list", 2))
    weighted_pool.append(("subscriptions", 3))
    weighted_pool.append(("spotify_favorites", 2 if is_young else 1))
    weighted_pool.append(("netflix_history", 3))
    weighted_pool.append(("youtube_subscriptions", 2))
    weighted_pool.append(("podcast_subscriptions", 2 if is_middle_aged else 1))

    # ==========================================================================
    # SHOPPING & CONSUMER - universal
    # ==========================================================================
    weighted_pool.append(("amazon_wishlist", 2))
    weighted_pool.append(("shopping_history", 2))
    weighted_pool.append(("grocery_list", 2))
    weighted_pool.append(("loyalty_programs", 1))

    # ==========================================================================
    # REVIEWS - some people write them
    # ==========================================================================
    weighted_pool.append(("google_reviews", 1))
    weighted_pool.append(("product_reviews", 1))
    weighted_pool.append(("yelp_reviews", 1))

    # ==========================================================================
    # PERSONAL NOTES & COMMUNICATION - universal
    # ==========================================================================
    weighted_pool.append(("notes_snippet", 2))
    weighted_pool.append(("bookmarks", 2))
    weighted_pool.append(("text_messages", 2))
    weighted_pool.append(("voicemail_greeting", 1))

    # ==========================================================================
    # HEALTH & FITNESS - varies
    # ==========================================================================
    if age >= AGE_HEALTH_TRACKING_MIN:
        weighted_pool.append(("fitness_tracker", 1))
        weighted_pool.append(("health_goals", 1))

    # ==========================================================================
    # TRAVEL & LOCATION - universal
    # ==========================================================================
    weighted_pool.append(("travel_history", 1))
    weighted_pool.append(("location_history", 2))

    # ==========================================================================
    # FINANCIAL - adults
    # ==========================================================================
    if age >= AGE_ADULT_MIN:
        weighted_pool.append(("bank_categories", 2))
        weighted_pool.append(("charity_donations", 1))

    # ==========================================================================
    # HOME & LIFESTYLE - varies
    # ==========================================================================
    weighted_pool.append(("home_description", 2))
    weighted_pool.append(("pet_profile", 1))
    weighted_pool.append(("vehicle_info", 1))
    weighted_pool.append(("recipe_collection", 1))

    # ==========================================================================
    # DATING - single adults
    # ==========================================================================
    if AGE_DATING_MIN <= age < AGE_DATING_MAX:
        weighted_pool.append(("dating_profile", 1))

    # ==========================================================================
    # COMMUNITY - varies
    # ==========================================================================
    weighted_pool.append(("forum_posts", 1))
    weighted_pool.append(("event_attendance", 1))

    # Weighted random selection without replacement
    selected = []
    pool = list(weighted_pool)

    for _ in range(min(num_files, len(pool))):
        if not pool:
            break
        types, weights = zip(*pool)
        chosen = random.choices(types, weights=weights, k=1)[0]
        selected.append(chosen)
        pool = [(t, w) for t, w in pool if t != chosen]

    return selected


def estimate_persona_cost(num_files: int = 3, model: str | None = None) -> CostEstimate:
    """Estimate cost for generating one persona."""
    # Identity generation: ~200 prompt, ~150 completion
    # Per file: ~300 prompt, ~200 completion
    # Context extraction: ~1500 prompt, ~100 completion
    # Context statement: ~1200 prompt, ~400 completion

    prompt_tokens = 200 + (300 * num_files) + 1500 + 1200
    completion_tokens = 150 + (200 * num_files) + 100 + 400

    estimate = estimate_cost(
        prompt="x" * prompt_tokens,
        estimated_completion_tokens=completion_tokens,
        model=model,
    )

    return CostEstimate(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=estimate.cost,
    )


def estimate_batch_cost(count: int, avg_files: int = 3, model: str | None = None) -> CostEstimate:
    """Estimate cost for generating a batch of personas."""
    single = estimate_persona_cost(avg_files, model)
    return CostEstimate(
        prompt_tokens=single.prompt_tokens * count,
        completion_tokens=single.completion_tokens * count,
        cost=single.cost * count,
    )
