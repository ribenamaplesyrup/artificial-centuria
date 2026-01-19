"""Centralized configuration for Centuria.

Keeps hard-coded values in one place for easy modification.
"""

import os

# =============================================================================
# LLM Provider Configuration
# =============================================================================

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

DEFAULT_MODEL = "gpt-4o-mini"


def get_available_models(api_keys: dict[str, str] | None = None) -> list[dict]:
    """Return models for providers that have API keys configured.

    Args:
        api_keys: Optional dict with session-specific keys (openai, anthropic, gemini).
                  Falls back to environment variables if not provided.
    """
    available = []
    # Map provider names to session key names
    session_key_map = {
        "OpenAI": "openai",
        "Anthropic": "anthropic",
        "Google": "gemini",
    }

    for provider, config in PROVIDER_MODELS.items():
        # Check session keys first, then fall back to env vars
        session_key = session_key_map.get(provider)
        has_key = False
        if api_keys and session_key:
            has_key = bool(api_keys.get(session_key))
        if not has_key:
            has_key = bool(os.getenv(config["env_key"]))

        if has_key:
            for model in config["models"]:
                available.append({
                    "id": model["id"],
                    "name": model["name"],
                    "provider": provider,
                })
    return available


# =============================================================================
# Occupation Categories
# =============================================================================

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


def match_occupation_category(category: str) -> str:
    """Match a category string to a known category, with fuzzy fallback."""
    if category in OCCUPATION_CATEGORIES:
        return category

    # Try fuzzy match
    category_lower = category.lower()
    for cat in OCCUPATION_CATEGORIES:
        if cat.lower() in category_lower or category_lower in cat.lower():
            return cat

    return "Other"


# =============================================================================
# CORS Configuration
# =============================================================================

DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://localhost:4173"]


def get_cors_origins() -> list[str]:
    """Get CORS origins from environment or use defaults."""
    cors_env = os.getenv("CORS_ORIGINS", "")
    if cors_env:
        return [o.strip() for o in cors_env.split(",") if o.strip()]
    return DEFAULT_CORS_ORIGINS


# =============================================================================
# Age Thresholds for File Type Selection
# =============================================================================

# Social media platform age ranges
AGE_TWITTER_MIN = 16
AGE_TWITTER_MAX = 55
AGE_INSTAGRAM_MIN = 16
AGE_INSTAGRAM_MAX = 45
AGE_FACEBOOK_MIN = 25
AGE_TIKTOK_MIN = 16
AGE_TIKTOK_MAX = 35
AGE_REDDIT_MIN = 18
AGE_REDDIT_MAX = 50
AGE_NEXTDOOR_MIN = 30
AGE_DATING_MIN = 18
AGE_DATING_MAX = 55

# Life stage thresholds
AGE_WORKING_MIN = 18
AGE_RETIREMENT = 65
AGE_YOUNG_MAX = 30
AGE_MIDDLE_MIN = 30
AGE_MIDDLE_MAX = 55
AGE_OLDER_MIN = 55
AGE_PROFESSIONAL_MIN = 22
AGE_ADULT_MIN = 18
AGE_HEALTH_TRACKING_MIN = 20

# Professional occupation keywords
PROFESSIONAL_KEYWORDS = [
    "manager", "director", "consultant", "analyst", "engineer",
    "developer", "designer", "teacher", "nurse", "doctor", "lawyer",
    "accountant", "executive", "coordinator", "specialist"
]
