"""Tests for centuria.config module."""

import os
from unittest.mock import patch

from centuria.config import (
    OCCUPATION_CATEGORIES,
    PROVIDER_MODELS,
    get_available_models,
    get_cors_origins,
    match_occupation_category,
)


class TestOccupationCategories:
    def test_categories_not_empty(self):
        assert len(OCCUPATION_CATEGORIES) > 0

    def test_has_other_category(self):
        assert "Other" in OCCUPATION_CATEGORIES

    def test_match_exact(self):
        assert match_occupation_category("Software/Engineering") == "Software/Engineering"

    def test_match_fuzzy(self):
        assert match_occupation_category("software engineer") == "Software/Engineering"

    def test_match_fallback_to_other(self):
        assert match_occupation_category("Underwater Basket Weaving") == "Other"


class TestProviderModels:
    def test_has_openai(self):
        assert "OpenAI" in PROVIDER_MODELS

    def test_openai_has_env_key(self):
        assert PROVIDER_MODELS["OpenAI"]["env_key"] == "OPENAI_API_KEY"

    def test_openai_has_models(self):
        assert len(PROVIDER_MODELS["OpenAI"]["models"]) > 0


class TestGetAvailableModels:
    def test_no_keys_returns_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            # Clear any existing API keys
            for provider in PROVIDER_MODELS.values():
                os.environ.pop(provider["env_key"], None)
            models = get_available_models()
            assert models == []

    def test_with_openai_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            models = get_available_models()
            openai_models = [m for m in models if m["provider"] == "OpenAI"]
            assert len(openai_models) > 0
            assert all(m["provider"] == "OpenAI" for m in openai_models)


class TestGetCorsOrigins:
    def test_default_origins(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CORS_ORIGINS", None)
            origins = get_cors_origins()
            assert "http://localhost:5173" in origins

    def test_custom_origins(self):
        with patch.dict(os.environ, {"CORS_ORIGINS": "https://example.com,https://other.com"}):
            origins = get_cors_origins()
            assert origins == ["https://example.com", "https://other.com"]
