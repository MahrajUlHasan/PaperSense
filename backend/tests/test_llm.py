from google.genai import errors as genai_errors

from services.llm import LLMCredentials, MissingKeyError, ProviderError, build_provider, call_with_retries
from services.llm.gemini import GeminiProvider, map_gemini_error
from services.llm.openai_compat import OpenAICompatibleProvider


def test_factory_picks_the_right_class():
    assert isinstance(build_provider(LLMCredentials("gemini", "k" * 20, "m")), GeminiProvider)
    groq = build_provider(LLMCredentials("groq", "k" * 20, "m"))
    assert isinstance(groq, OpenAICompatibleProvider) and groq.name == "groq"


def test_credentials_never_show_the_key():
    assert "secret" not in repr(LLMCredentials("gemini", "secret-key-123", "m"))


def test_gemini_rate_limit_is_mapped_with_retry_delay():
    err = genai_errors.APIError(429, {"error": {"message": "Quota exceeded. Please retry in 12.5s.",
                                                "status": "RESOURCE_EXHAUSTED"}})
    mapped = map_gemini_error(err)
    assert mapped.kind == "rate_limited" and mapped.retry_after == 12.5 and mapped.status_code == 429


def test_gemini_bad_key_is_mapped():
    err = genai_errors.APIError(400, {"error": {"message": "API key not valid. Please pass a valid API key.",
                                                "status": "INVALID_ARGUMENT"}})
    assert map_gemini_error(err).kind == "invalid_key"


def test_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("services.llm.base.time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ProviderError("busy", kind="unavailable", provider="gemini")
        return "ok"

    assert call_with_retries(flaky) == "ok" and calls["n"] == 3


def test_missing_key_points_to_help():
    data = MissingKeyError("groq").to_dict()
    assert data["code"] == "missing_key" and data["help_url"] == "https://console.groq.com/keys"
