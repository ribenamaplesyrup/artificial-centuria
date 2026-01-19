"""Simple FastAPI server for Centuria experiments."""

import asyncio
import base64
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import httpx
import litellm
from google import genai
from PIL import Image

from centuria.llm.client import complete
from centuria.models import Persona, Question, Survey
from centuria.survey import ask_question, estimate_survey_cost

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(_project_root / ".env")


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

    model: str = "gpt-4o-mini"


# Models organized by provider with their required API key env var
PROVIDER_MODELS = {
    "OpenAI": {
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-4", "name": "GPT-4"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
            {"id": "o1", "name": "o1"},
        ],
    },
    "Anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4"},
            {"id": "claude-3-7-sonnet-20250219", "name": "Claude 3.7 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
        ],
    },
    "Google": {
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini/gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
            {"id": "gemini/gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite"},
            {"id": "gemini/gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini/gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini/gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash 8B"},
        ],
    },
    "Mistral": {
        "env_key": "MISTRAL_API_KEY",
        "models": [
            {"id": "mistral/mistral-large-latest", "name": "Mistral Large"},
            {"id": "mistral/mistral-medium-latest", "name": "Mistral Medium"},
            {"id": "mistral/mistral-small-latest", "name": "Mistral Small"},
            {"id": "mistral/open-mistral-nemo", "name": "Mistral Nemo"},
            {"id": "mistral/codestral-latest", "name": "Codestral"},
        ],
    },
    "Groq": {
        "env_key": "GROQ_API_KEY",
        "models": [
            {"id": "groq/llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
            {"id": "groq/llama-3.1-8b-instant", "name": "Llama 3.1 8B"},
            {"id": "groq/mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
            {"id": "groq/gemma2-9b-it", "name": "Gemma 2 9B"},
        ],
    },
    "Together": {
        "env_key": "TOGETHER_API_KEY",
        "models": [
            {"id": "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo", "name": "Llama 3.3 70B Turbo"},
            {"id": "together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", "name": "Llama 3.1 405B Turbo"},
            {"id": "together_ai/meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "name": "Llama 3.1 70B Turbo"},
            {"id": "together_ai/mistralai/Mixtral-8x22B-Instruct-v0.1", "name": "Mixtral 8x22B"},
            {"id": "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo", "name": "Qwen 2.5 72B Turbo"},
        ],
    },
    "Cohere": {
        "env_key": "COHERE_API_KEY",
        "models": [
            {"id": "cohere/command-r-plus", "name": "Command R+"},
            {"id": "cohere/command-r", "name": "Command R"},
            {"id": "cohere/command-light", "name": "Command Light"},
        ],
    },
    "DeepSeek": {
        "env_key": "DEEPSEEK_API_KEY",
        "models": [
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek/deepseek-reasoner", "name": "DeepSeek Reasoner"},
        ],
    },
}


def get_available_models() -> list[dict]:
    """Return models for providers that have API keys configured."""
    available = []
    for provider, config in PROVIDER_MODELS.items():
        if os.getenv(config["env_key"]):
            for model in config["models"]:
                available.append({
                    "id": model["id"],
                    "name": model["name"],
                    "provider": provider,
                })
    return available


NAIVE_PROMPT = """Generate a random person.

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


OCCUPATION_CATEGORIES = [
    # Healthcare
    "Physician/Doctor",
    "Nurse/Nursing",
    "Mental Health",
    "Allied Health",
    # Education
    "K-12 Education",
    "Higher Education",
    "Training/Coaching",
    # Technology
    "Software/Engineering",
    "IT/Systems",
    "Data/Analytics",
    # Business
    "Finance/Banking",
    "Accounting",
    "Management/Executive",
    "Marketing/Advertising",
    "Human Resources",
    "Consulting",
    # Trades
    "Construction",
    "Electrical/Plumbing",
    "Automotive/Mechanical",
    # Creative
    "Visual Arts/Design",
    "Performing Arts",
    "Writing/Journalism",
    "Media/Entertainment",
    # Service
    "Food Service/Hospitality",
    "Retail/Sales",
    "Personal Services",
    "Customer Service",
    # Public Sector
    "Government/Civil Service",
    "Military/Defense",
    "Law Enforcement",
    "Legal/Law",
    # Science
    "Research/Academia",
    "Laboratory/Technical",
    "Environmental/Conservation",
    # Other
    "Agriculture/Farming",
    "Transportation/Logistics",
    "Manufacturing/Production",
    "Real Estate",
    "Non-profit/Social Work",
    "Religious/Ministry",
    "Student",
    "Retired",
    "Homemaker",
    "Unemployed",
    "Other",
]

CLASSIFY_PROMPT = """Classify this occupation into exactly one category.

Occupation: {occupation}
Person description: {brief}

Categories:
{categories}

Return ONLY the category name, nothing else."""


def parse_json_response(content: str) -> dict:
    """Parse JSON from LLM response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Centuria API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/keys/status")
async def get_api_key_status():
    """Check which API keys are configured."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "has_llm_key": bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
    }


class SetApiKeysRequest(BaseModel):
    """Request to set API keys."""

    openai_key: str | None = None
    anthropic_key: str | None = None
    gemini_key: str | None = None


@app.post("/api/keys/set")
async def set_api_keys(request: SetApiKeysRequest):
    """Set API keys at runtime (session only, not persisted to .env)."""
    if request.openai_key:
        os.environ["OPENAI_API_KEY"] = request.openai_key
    if request.anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = request.anthropic_key
    if request.gemini_key:
        os.environ["GEMINI_API_KEY"] = request.gemini_key

    return {
        "success": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "has_llm_key": bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
    }


@app.get("/api/prompt")
async def get_prompt():
    """Return the naive prompt being used."""
    return {"prompt": NAIVE_PROMPT}


@app.get("/api/models")
async def get_models():
    """Return available models based on configured API keys."""
    return {"models": get_available_models()}


@app.get("/api/occupation-categories")
async def get_occupation_categories():
    """Return the list of occupation categories for the frontend."""
    return {"categories": OCCUPATION_CATEGORIES}


@app.post("/api/generate-persona", response_model=GeneratedPersona)
async def generate_persona(request: GenerateRequest = None):
    """Generate a random persona using a naive LLM prompt, then classify."""
    model = request.model if request else "gpt-4o-mini"

    # Step 1: Generate the base persona
    result = await complete(
        prompt=NAIVE_PROMPT,
        model=model,
    )
    persona_data = parse_json_response(result.content)

    # Step 2: Classify occupation
    categories_list = "\n".join(f"- {cat}" for cat in OCCUPATION_CATEGORIES)
    classify_result = await complete(
        prompt=CLASSIFY_PROMPT.format(
            occupation=persona_data.get("occupation", "Unknown"),
            brief=persona_data.get("brief", ""),
            categories=categories_list,
        ),
        model=model,
    )
    category = classify_result.content.strip()

    # Validate category is one of our known categories
    if category not in OCCUPATION_CATEGORIES:
        # Try to find a close match
        category_lower = category.lower()
        matched = False
        for cat in OCCUPATION_CATEGORIES:
            if cat.lower() in category_lower or category_lower in cat.lower():
                category = cat
                matched = True
                break
        if not matched:
            category = "Other"

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
    model: str = "gpt-4o-mini"


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
async def run_survey(request: SurveyRequest):
    """Run a survey on multiple personas concurrently."""
    question = Question(
        id=request.question.question_id,
        text=request.question.question_text,
        question_type="single_select",
        options=request.question.options,
    )

    async def survey_persona(p: PersonaData) -> SurveyResponse:
        persona = Persona(id=p.id, name=p.name, context=p.context)
        result = await ask_question(persona, question, model=request.question.model)
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
async def generate_image(request: ImageGenerationRequest):
    """Generate an image of the design using Google Gemini."""
    # Load the original plot image
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
        # Initialize Gemini client
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

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


def run():
    """Run the server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
