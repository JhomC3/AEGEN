"""Tests de deteccion de provider LLM en metrics_processor."""

import pytest

from src.core.observability.metrics_processor import (
    estimate_cost_usd,
    extract_model_info,
)


@pytest.mark.parametrize(
    "serialized,expected_provider,expected_model",
    [
        (
            {
                "id": ["langchain_google_genai", "ChatGoogleGenerativeAI"],
                "kwargs": {"model": "gemini-2.5-flash"},
            },
            "google",
            "gemini-2.5-flash",
        ),
        (
            {
                "id": ["langchain_groq", "ChatGroq"],
                "kwargs": {"model_name": "openai/gpt-oss-120b"},
            },
            "groq",
            "openai/gpt-oss-120b",
        ),
        (
            {
                "id": ["langchain_openai", "ChatOpenAI"],
                "kwargs": {
                    "model_name": "minimax/minimax-m2.5:free",
                    "openai_api_base": "https://openrouter.ai/api/v1",
                },
            },
            "openrouter",
            "minimax/minimax-m2.5:free",
        ),
        (
            {
                "id": ["langchain_openai", "ChatOpenAI"],
                "kwargs": {
                    "model_name": "gpt-4o",
                    "openai_api_base": "https://api.openai.com/v1",
                },
            },
            "openai",
            "gpt-4o",
        ),
        (
            {
                "id": ["langchain_openai", "ChatOpenAI"],
                "kwargs": {
                    "model_name": "gpt-4o",
                    "openai_api_base": "https://myresource.openai.azure.com",
                },
            },
            "azure_openai",
            "gpt-4o",
        ),
        (
            {
                "id": ["langchain_openai", "ChatOpenAI"],
                "kwargs": {"model_name": "gpt-4o-mini"},
            },
            "openai",
            "gpt-4o-mini",
        ),
        (
            {
                "id": ["langchain_unknown", "SomeRandomLLM"],
                "kwargs": {},
            },
            "unknown",
            "unknown",
        ),
    ],
)
def test_extract_model_info(serialized, expected_provider, expected_model):
    provider, model = extract_model_info(serialized)
    assert (
        provider == expected_provider
    ), f"Provider: got {provider!r}, expected {expected_provider!r}"
    assert model == expected_model, f"Model: got {model!r}, expected {expected_model!r}"


def test_estimate_cost_groq_is_zero():
    """Groq free tier no tiene costo."""
    cost = estimate_cost_usd("groq", input_tokens=1000, output_tokens=500)
    assert cost == 0.0


def test_estimate_cost_google_gemini():
    """Gemini Flash tiene costo por tokens."""
    cost = estimate_cost_usd("google", input_tokens=1000, output_tokens=1000)
    assert abs(cost - 0.000375) < 1e-8


def test_estimate_cost_unknown_provider_is_zero():
    """Provider desconocido no debe generar costo."""
    cost = estimate_cost_usd("unknown", input_tokens=9999, output_tokens=9999)
    assert cost == 0.0
