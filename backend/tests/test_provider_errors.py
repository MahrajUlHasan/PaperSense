from fastapi import FastAPI
from fastapi.testclient import TestClient

from main import provider_error_handler
from services.llm import MissingKeyError, ProviderError


def make_client(error):
    app = FastAPI()
    app.add_exception_handler(ProviderError, provider_error_handler)

    @app.get("/boom")
    def boom():
        raise error

    return TestClient(app)


def test_missing_key_is_401_with_help_link():
    r = make_client(MissingKeyError("gemini")).get("/boom")
    assert r.status_code == 401
    assert r.json()["detail"]["help_url"] == "https://aistudio.google.com/apikey"


def test_rate_limit_is_429_with_retry_after():
    r = make_client(ProviderError("slow down", kind="rate_limited", provider="groq", retry_after=12)).get("/boom")
    assert r.status_code == 429 and r.headers["retry-after"] == "12"


def test_dropped_gemini_connection_is_retried_as_busy(monkeypatch):
    import httpx

    from services.llm import GeminiProvider

    monkeypatch.setattr("services.llm.base.time.sleep", lambda s: None)
    provider = GeminiProvider("k" * 20, "gemini-test")
    calls = []

    def generate_content(**kwargs):
        calls.append(1)
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    monkeypatch.setattr(provider._client.models, "generate_content", generate_content)
    try:
        provider.generate("hi")
    except ProviderError as err:
        assert err.kind == "unavailable" and err.status_code == 503
    else:
        raise AssertionError("expected ProviderError")
    assert len(calls) == 3


def test_dropped_gemini_connection_is_retried_as_busy(monkeypatch):
    import httpx
    import pytest

    from services.llm import GeminiProvider

    monkeypatch.setattr("services.llm.base.time.sleep", lambda s: None)
    provider = GeminiProvider("k" * 20, "gemini-test")
    calls = []

    def generate_content(**kwargs):
        calls.append(1)
        raise httpx.RemoteProtocolError("Server disconnected without sending a response.")

    monkeypatch.setattr(provider._client.models, "generate_content", generate_content)
    with pytest.raises(ProviderError) as info:
        provider.generate("hi")
    assert info.value.kind == "unavailable" and info.value.status_code == 503
    assert len(calls) == 3
