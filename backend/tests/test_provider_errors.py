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
