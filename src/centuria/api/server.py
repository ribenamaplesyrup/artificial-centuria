"""Simple FastAPI server for Centuria experiments."""

import asyncio
import base64
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Cookie, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from PIL import Image

from centuria.config import (
    DEFAULT_MODEL,
    OCCUPATION_CATEGORIES,
    get_available_models,
    get_cors_origins,
    match_occupation_category,
)
from centuria.llm.client import complete
from centuria.models import Persona, Question, Survey
from centuria.survey import ask_question, estimate_survey_cost
from centuria.utils import parse_json_response

# =============================================================================
# Persona Generation Prompts
# =============================================================================

PERSONA_GENERATION_PROMPT = """Generate a random person.

Return ONLY valid JSON with these exact fields:
{
  "name": "Full name",
  "age": number between 18-85,
  "gender": "Male" or "Female" or "Non-binary",
  "occupation": "Their specific job or role",
  "education": "Highest education level (e.g., High school, Bachelor's, Master's, PhD, Trade school, Some college)",
  "political_leaning": "Political orientation (e.g., Liberal, Conservative, Moderate, Libertarian, Progressive, Apolitical)",
  "location": "City, State/Region",
  "country": "Country name",
  "continent": "One of: North America, South America, Europe, Africa, Asia, Oceania",
  "latitude": number (precise latitude of their home address, not just city center),
  "longitude": number (precise longitude of their home address, not just city center),
  "brief": "2-3 sentence description of who they are, their background, interests"
}"""

OCCUPATION_CLASSIFY_PROMPT = """Classify this occupation into exactly one category.

Occupation: {occupation}
Person description: {brief}

Categories:
{categories}

Return ONLY the category name, nothing else."""


def format_classify_prompt(occupation: str, brief: str) -> str:
    """Format the occupation classification prompt."""
    categories_list = "\n".join(f"- {cat}" for cat in OCCUPATION_CATEGORIES)
    return OCCUPATION_CLASSIFY_PROMPT.format(
        occupation=occupation,
        brief=brief,
        categories=categories_list,
    )

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")

# =============================================================================
# Session-based API Key Storage
# =============================================================================
# Store API keys per-session to prevent key leakage between users
_session_keys: dict[str, dict[str, str]] = {}


def get_or_create_session(session_id: str | None) -> str:
    """Get existing session or create a new one."""
    if session_id and session_id in _session_keys:
        return session_id
    new_session = secrets.token_urlsafe(32)
    _session_keys[new_session] = {}
    return new_session


def get_session_keys(session_id: str | None) -> dict[str, str]:
    """Get API keys for a session, falling back to environment variables."""
    session_keys = _session_keys.get(session_id, {}) if session_id else {}
    return {
        "openai": session_keys.get("openai") or os.getenv("OPENAI_API_KEY") or "",
        "anthropic": session_keys.get("anthropic") or os.getenv("ANTHROPIC_API_KEY") or "",
        "gemini": session_keys.get("gemini") or os.getenv("GEMINI_API_KEY") or "",
    }


def set_session_key(session_id: str, provider: str, key: str) -> None:
    """Set an API key for a session."""
    if session_id not in _session_keys:
        _session_keys[session_id] = {}
    _session_keys[session_id][provider] = key


class GeneratedPersona(BaseModel):
    """A generated persona with location and classifications."""

    name: str
    age: int
    gender: str
    occupation: str
    occupation_category: str
    education: str
    political_leaning: str
    location: str
    country: str
    continent: str
    latitude: float
    longitude: float
    brief: str


class GenerateRequest(BaseModel):
    """Request body for persona generation."""

    model: str = DEFAULT_MODEL


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Centuria API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - serves SPA if available, otherwise API info."""
    # Check if frontend build exists
    index_file = _project_root / "web" / "build" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    # Fall back to API info when no frontend is built
    return {
        "name": "Centuria API",
        "description": "Generate LLM personas to model groups of humans and survey them",
        "docs": "/docs",
        "health": "/api/health",
        "endpoints": [
            "/api/health",
            "/api/models",
            "/api/generate-persona",
            "/api/survey/run",
            "/api/survey/estimate",
        ]
    }


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/keys/status")
async def get_api_key_status(
    response: Response,
    centuria_session: str | None = Cookie(default=None),
):
    """Check which API keys are configured for this session."""
    # Ensure session exists
    session_id = get_or_create_session(centuria_session)
    if session_id != centuria_session:
        response.set_cookie(
            key="centuria_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
        )

    keys = get_session_keys(session_id)
    return {
        "openai": bool(keys["openai"]),
        "anthropic": bool(keys["anthropic"]),
        "gemini": bool(keys["gemini"]),
        "has_llm_key": bool(keys["openai"] or keys["anthropic"]),
    }


class SetApiKeysRequest(BaseModel):
    """Request to set API keys."""

    openai_key: str | None = None
    anthropic_key: str | None = None
    gemini_key: str | None = None


@app.post("/api/keys/set")
async def set_api_keys(
    request: SetApiKeysRequest,
    response: Response,
    centuria_session: str | None = Cookie(default=None),
):
    """Set API keys for this session only (isolated per user)."""
    # Ensure session exists
    session_id = get_or_create_session(centuria_session)
    if session_id != centuria_session:
        response.set_cookie(
            key="centuria_session",
            value=session_id,
            httponly=True,
            samesite="lax",
            secure=False,  # Set to True in production with HTTPS
        )

    # Store keys in session, not globally
    if request.openai_key:
        set_session_key(session_id, "openai", request.openai_key)
    if request.anthropic_key:
        set_session_key(session_id, "anthropic", request.anthropic_key)
    if request.gemini_key:
        set_session_key(session_id, "gemini", request.gemini_key)

    keys = get_session_keys(session_id)
    return {
        "success": True,
        "openai": bool(keys["openai"]),
        "anthropic": bool(keys["anthropic"]),
        "gemini": bool(keys["gemini"]),
        "has_llm_key": bool(keys["openai"] or keys["anthropic"]),
    }


@app.get("/api/prompt")
async def get_prompt():
    """Return the naive prompt being used."""
    return {"prompt": PERSONA_GENERATION_PROMPT}


@app.get("/api/models")
async def get_models(centuria_session: str | None = Cookie(default=None)):
    """Return available models based on configured API keys for this session."""
    keys = get_session_keys(centuria_session)
    return {"models": get_available_models(api_keys=keys)}


@app.get("/api/occupation-categories")
async def get_occupation_categories():
    """Return the list of occupation categories for the frontend."""
    return {"categories": OCCUPATION_CATEGORIES}


@app.post("/api/generate-persona", response_model=GeneratedPersona)
async def generate_persona(
    request: GenerateRequest = None,
    centuria_session: str | None = Cookie(default=None),
):
    """Generate a random persona using a naive LLM prompt, then classify."""
    model = request.model if request else DEFAULT_MODEL
    api_keys = get_session_keys(centuria_session)

    # Step 1: Generate the base persona
    result = await complete(
        prompt=PERSONA_GENERATION_PROMPT,
        model=model,
        api_keys=api_keys,
    )
    persona_data = parse_json_response(result.content)

    # Step 2: Classify occupation
    classify_result = await complete(
        prompt=format_classify_prompt(
            occupation=persona_data.get("occupation", "Unknown"),
            brief=persona_data.get("brief", ""),
        ),
        model=model,
        api_keys=api_keys,
    )
    category = match_occupation_category(classify_result.content.strip())

    persona_data["occupation_category"] = category

    # Ensure all required fields have defaults
    persona_data.setdefault("gender", "Unknown")
    persona_data.setdefault("education", "Unknown")
    persona_data.setdefault("political_leaning", "Unknown")
    persona_data.setdefault("country", "Unknown")
    persona_data.setdefault("continent", "Unknown")

    return GeneratedPersona(**persona_data)


# ============================================================================
# Survey API Endpoints
# ============================================================================


class SurveyQuestionRequest(BaseModel):
    """Request for a single-question survey."""

    question_id: str
    question_text: str
    options: list[str]
    model: str = DEFAULT_MODEL


class PersonaData(BaseModel):
    """Persona data from the frontend."""

    id: str
    name: str
    context: str


class SurveyRequest(BaseModel):
    """Request for running a survey on multiple personas."""

    question: SurveyQuestionRequest
    personas: list[PersonaData]


class SurveyEstimateRequest(BaseModel):
    """Request for estimating survey cost."""

    question: SurveyQuestionRequest
    sample_persona: PersonaData
    num_personas: int


class SurveyResponse(BaseModel):
    """Response for a single persona."""

    persona_id: str
    persona_name: str
    response: str
    justification: str = ""
    cost: float


class SurveyResultsResponse(BaseModel):
    """Full survey results."""

    responses: list[SurveyResponse]
    total_cost: float


class EstimateResponse(BaseModel):
    """Cost estimate response."""

    prompt_tokens: int
    completion_tokens: int
    cost_per_agent: float
    total_cost: float
    num_agents: int


@app.post("/api/survey/estimate", response_model=EstimateResponse)
async def estimate_survey(request: SurveyEstimateRequest):
    """Estimate the cost of running a survey before executing it."""
    persona = Persona(
        id=request.sample_persona.id,
        name=request.sample_persona.name,
        context=request.sample_persona.context,
    )

    question = Question(
        id=request.question.question_id,
        text=request.question.question_text,
        question_type="single_select",
        options=request.question.options,
    )

    survey = Survey(id="estimate", name="Cost Estimate", questions=[question])

    estimate = estimate_survey_cost(
        persona=persona,
        survey=survey,
        num_agents=request.num_personas,
        model=request.question.model,
    )

    return EstimateResponse(
        prompt_tokens=estimate.prompt_tokens,
        completion_tokens=estimate.completion_tokens,
        cost_per_agent=estimate.cost_per_agent,
        total_cost=estimate.total_cost,
        num_agents=estimate.num_agents,
    )


@app.post("/api/survey/run", response_model=SurveyResultsResponse)
async def run_survey_endpoint(
    request: SurveyRequest,
    centuria_session: str | None = Cookie(default=None),
):
    """Run a survey on multiple personas concurrently."""
    question = Question(
        id=request.question.question_id,
        text=request.question.question_text,
        question_type="single_select",
        options=request.question.options,
    )
    api_keys = get_session_keys(centuria_session)

    async def survey_persona(p: PersonaData) -> SurveyResponse:
        persona = Persona(id=p.id, name=p.name, context=p.context)
        result = await ask_question(
            persona, question, model=request.question.model, api_keys=api_keys
        )
        return SurveyResponse(
            persona_id=p.id,
            persona_name=p.name,
            response=result.response,
            justification=result.justification,
            cost=result.cost,
        )

    # Run all surveys concurrently
    tasks = [survey_persona(p) for p in request.personas]
    responses = await asyncio.gather(*tasks)

    total_cost = sum(r.cost for r in responses)

    return SurveyResultsResponse(responses=list(responses), total_cost=total_cost)


@app.get("/api/personas/dalston-clt")
async def get_dalston_personas():
    """Load the Dalston CLT personas for the Testing space before it happens experiment."""
    personas_file = _project_root / "data" / "synthetic" / "dalston_clt" / "personas_for_survey.json"

    if not personas_file.exists():
        return {"error": "Personas file not found", "personas": []}

    with open(personas_file) as f:
        personas_data = json.load(f)

    return {"personas": personas_data}


@app.get("/api/households/dalston-clt")
async def get_dalston_households():
    """Load the Dalston CLT neighbourhood with households."""
    neighbourhood_file = _project_root / "data" / "synthetic" / "dalston_clt" / "neighbourhood.json"

    if not neighbourhood_file.exists():
        return {"error": "Neighbourhood file not found", "households": []}

    with open(neighbourhood_file) as f:
        data = json.load(f)

    return data


@app.get("/api/persona-files/{persona_id}")
async def get_persona_files(persona_id: str):
    """Get the synthetic files for a specific persona."""
    persona_dir = _project_root / "data" / "synthetic" / "dalston_clt" / "personas" / persona_id

    if not persona_dir.exists():
        return {"error": "Persona not found", "files": []}

    files = []
    for file_path in sorted(persona_dir.iterdir()):
        if file_path.is_file() and not file_path.name.startswith('.'):
            files.append({
                "name": file_path.name,
                "content": file_path.read_text()
            })

    return {"persona_id": persona_id, "files": files}


# ============================================================================
# Image Generation API Endpoints
# ============================================================================


class ImageGenerationRequest(BaseModel):
    """Request for generating a garden design image."""

    winning_option: str
    design_choices: list[dict]  # [{question: str, answer: str}, ...]


class ImageGenerationResponse(BaseModel):
    """Response containing the generated image."""

    image_base64: str
    prompt_used: str


@app.post("/api/generate-image")
async def generate_image(
    request: ImageGenerationRequest,
    centuria_session: str | None = Cookie(default=None),
):
    """Generate an image of the design using Google Gemini."""
    # Load the original plot image
    # Check build directory first (for deployed app), then static (for local dev)
    plot_image_path = _project_root / "web" / "build" / "images" / "plot_1.png"
    if not plot_image_path.exists():
        plot_image_path = _project_root / "web" / "static" / "images" / "plot_1.png"
    if not plot_image_path.exists():
        return {"error": f"Plot image not found at {plot_image_path}"}

    # Build a detailed prompt from the survey results
    design_description = "\n".join([f"- {d['question']}: {d['answer']}" for d in request.design_choices])

    prompt = f"""Transform this small empty urban plot into: {request.winning_option}.

Design specifications from community vote:
{design_description}

Important: This is a small 0.3-acre urban plot. Keep the exact same size, proportions, and boundaries as shown. Do not expand or enlarge the space. Keep the same camera angle and perspective. Keep the Victorian brick walls and terraced houses visible around the edges. Make it look like a professional architectural rendering of the completed space, appropriately scaled to fit this compact urban plot. Show the space as newly built and in use with a few people. British overcast weather lighting."""

    try:
        # Get Gemini API key from session
        api_keys = get_session_keys(centuria_session)
        gemini_key = api_keys.get("gemini")
        if not gemini_key:
            return {"error": "Gemini API key not configured"}

        # Initialize Gemini client with session key
        client = genai.Client(api_key=gemini_key)

        # Load the source image
        source_image = Image.open(plot_image_path)

        # Generate content with image and prompt
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, source_image],
        )

        # Extract the generated image from response
        generated_image = None
        for part in response.parts:
            if part.inline_data is not None:
                # Get the raw image data and convert to base64
                image_bytes = part.inline_data.data
                generated_image = base64.standard_b64encode(image_bytes).decode("utf-8")
                break

        if not generated_image:
            return {"error": "No image generated in response"}

    except Exception as e:
        return {"error": f"Image generation failed: {str(e)}"}

    return {"image_base64": generated_image, "prompt_used": prompt}


# ============================================================================
# Static File Serving (for single-service deployment)
# ============================================================================

# Path to the built frontend (web/build from SvelteKit)
_static_dir = _project_root / "web" / "build"

# Mount static assets if the build directory exists
if _static_dir.exists():
    # Mount the _app directory for SvelteKit's hashed assets
    _app_dir = _static_dir / "_app"
    if _app_dir.exists():
        app.mount("/_app", StaticFiles(directory=str(_app_dir)), name="svelte_app")

    # Mount other static assets (images, sample-data, etc.)
    _static_assets = _static_dir
    if _static_assets.exists():
        app.mount("/images", StaticFiles(directory=str(_static_dir / "images")), name="images")
        _sample_data_dir = _static_dir / "sample-data"
        if _sample_data_dir.exists():
            app.mount("/sample-data", StaticFiles(directory=str(_sample_data_dir)), name="sample_data")

    # Catch-all route for SPA - serve index.html for non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SvelteKit SPA for any non-API routes."""
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}

        # Check if it's a static file request
        static_file = _static_dir / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)

        # For SPA routes, check if there's a prerendered HTML file
        # SvelteKit static adapter creates /route/index.html for each route
        if full_path:
            prerendered = _static_dir / full_path / "index.html"
            if prerendered.exists():
                return FileResponse(prerendered)

        # Fall back to main index.html for client-side routing
        index_file = _static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return {"error": "Not found"}


def run():
    """Run the server."""
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
