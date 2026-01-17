"""Synthetic persona generation - file-first approach.

Workflow:
1. Generate a synthetic identity (name, age, location, occupation)
2. Generate 2-5 personal data files for that identity
3. Save files to data/synthetic/{name}/
4. Use the same extraction pipeline as real data to create the persona
"""

import json
import random
import uuid
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from centuria.data import process_personal_folder
from centuria.llm import complete, estimate_cost, CostEstimate
from centuria.models import Persona


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


# Available file types and their generation prompts
FILE_TYPES = {
    "cv": {
        "filename": "cv.txt",
        "description": "CV/Resume",
        "prompt": """Generate a realistic CV/resume for this person as plain text.

{identity}

Write a CV that includes:
- Contact header (name, location - invent a plausible email)
- Professional summary (2-3 sentences)
- Work experience (2-4 positions with dates, company names, bullet points)
- Education
- Skills

Keep it factual and realistic. No flattery or puffery - write like a real CV.
Output only the CV text, no preamble."""
    },
    "reading_list": {
        "filename": "recent_reads.txt",
        "description": "Recent books read",
        "prompt": """Generate a list of 5-8 books this person has recently read.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- Most of what people read is NOT political or directly related to their job
- Include genre fiction (thrillers, romance, sci-fi), hobby books, self-help, popular non-fiction
- Only 1-2 books (if any) should relate to their political views
- A conservative might read Lee Child thrillers, a book about fishing, and a WWII history book - not 8 conservative political manifestos
- A liberal might read literary fiction, true crime, and a cookbook - not 8 books about social justice

The books should:
- Be real books that actually exist
- Reflect VARIED interests, not just politics/work
- Include popular mainstream titles that many people read

Format: One book per line as "Title - Author"
Output only the list, no preamble."""
    },
    "subscriptions": {
        "filename": "subscriptions.txt",
        "description": "Media subscriptions (publications, podcasts)",
        "prompt": """Generate a list of media subscriptions for this person.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- Most media consumption is entertainment, not politics
- Include: true crime podcasts, sports, comedy, hobby-related content, mainstream entertainment
- Only 1-2 items (if any) should be explicitly political
- A conservative truck driver might listen to: Joe Rogan, a true crime podcast, sports radio, country music station, AND some talk radio - not 10 conservative political shows
- People consume media for entertainment and escape, not just ideological reinforcement

Include a mix of:
- Podcasts (true crime, comedy, sports, storytelling, interview shows)
- Entertainment (streaming, YouTube channels, sports)
- Maybe 1-2 news sources or political content at most

Format: One item per line
Output only the list, no preamble."""
    },
    "spotify_favorites": {
        "filename": "spotify_favorites.txt",
        "description": "Favorite music artists/genres",
        "prompt": """Generate a Spotify favorites list for this person.

{identity}

Include:
- 8-12 favorite artists
- 2-3 favorite genres
- 2-3 favorite playlists they might have

The music taste should feel authentic to their age, background, and personality.

Format as a simple text list with sections for Artists, Genres, Playlists.
Output only the list, no preamble."""
    },
    "twitter_bio": {
        "filename": "twitter_bio.txt",
        "description": "Twitter/X profile bio and recent interests",
        "prompt": """Generate a Twitter/X profile for this person.

{identity}

Include:
- Bio (max 160 characters)
- Location as displayed
- 5-10 topics they frequently tweet/post about
- Their general posting style (lurker, occasional, frequent)

The profile should reflect their personality and views authentically.
Output as plain text with labeled sections, no preamble."""
    },
    "linkedin_summary": {
        "filename": "linkedin_summary.txt",
        "description": "LinkedIn about section",
        "prompt": """Generate a LinkedIn "About" section for this person.

{identity}

Write 2-3 paragraphs that:
- Summarize their professional focus
- Mention what they're interested in
- Reflect their communication style

Keep it professional but authentic to their personality. Avoid corporate buzzwords.
Output only the summary text, no preamble."""
    },
    "notes_snippet": {
        "filename": "notes.txt",
        "description": "Personal notes or journal snippets",
        "prompt": """Generate a few personal notes or journal snippets for this person.

{identity}

Write 3-5 short notes (1-3 sentences each) that might be from their notes app:
- A thought about something they're working on
- A reminder or goal
- A reaction to something they read/watched
- A personal reflection
- Mundane life stuff (groceries, appointments, gift ideas)

IMPORTANT: Most personal notes are mundane, not political or philosophical.
Include things like "pick up milk", "call mom", "look into that show Sarah mentioned", "dentist Tuesday 3pm".
These should feel authentic and unpolished - real notes, not a manifesto.

Output only the notes, no preamble."""
    },
    "bookmarks": {
        "filename": "bookmarks.txt",
        "description": "Saved articles and links",
        "prompt": """Generate a list of saved bookmarks/articles for this person.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- People bookmark practical stuff: recipes, how-to guides, travel ideas, product reviews, health tips
- Include entertainment: articles about TV shows, sports, celebrities, viral stories
- Only 1-2 (if any) should be explicitly political
- A conservative doesn't only bookmark conservative articles - they also save "best BBQ techniques", "NFL draft predictions", "how to fix leaky faucet"

List 8-12 articles/links they might have saved:
- Practical/how-to content
- Entertainment and lifestyle
- Hobby-related
- Maybe 1-2 news/opinion pieces at most

Format: "Article Title - Publication/Website" (one per line)
Use real publications but you can invent plausible article titles.
Output only the list, no preamble."""
    },
}


IDENTITY_PROMPT = """Generate a realistic synthetic identity for a person.

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
    "personality_sketch": "2-3 sentences with realistic interests. Include normal hobbies like TV, sports, family, church, gaming, cars."
}}

Return ONLY the JSON object."""


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

    prompt = IDENTITY_PROMPT.format(constraints=constraints)
    result = await complete(prompt)

    # Parse JSON
    response_text = result.content.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()

    data = json.loads(response_text)
    return SyntheticIdentity(**data)


async def generate_file_content(identity: SyntheticIdentity, file_type: str) -> str:
    """Generate content for a specific file type."""
    if file_type not in FILE_TYPES:
        raise ValueError(f"Unknown file type: {file_type}")

    file_config = FILE_TYPES[file_type]
    identity_text = f"""Name: {identity.name}
Age: {identity.age}
Gender: {identity.gender}
Location: {identity.location}
Occupation: {identity.occupation}
Industry: {identity.industry}
Education: {identity.education}
Political lean: {identity.political_lean}

Personality: {identity.personality_sketch}"""

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

    # Generate each file
    saved_files = {}
    for file_type in file_types:
        config = FILE_TYPES[file_type]
        content = await generate_file_content(identity, file_type)

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
    return {k: v["description"] for k, v in FILE_TYPES.items()}


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
