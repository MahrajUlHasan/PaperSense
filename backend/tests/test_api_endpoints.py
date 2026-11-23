"""Endpoint behaviour beyond workspace isolation: upload checks, keys, questions, research."""
import uuid

import pytest
from fastapi.testclient import TestClient

import main
from config import settings
from services.llm import ProviderError
from services.registry import DocumentRegistry
from services.storage import DocumentStorage

WS = {"X-Workspace-Id": "ws-test-cccccccc"}
WITH_KEY = {**WS, "X-LLM-Key": "test-key-0000000000"}
PDF = b"%PDF-1.4\n% tiny test file\n"


class FakeStore:
    def delete_document(self, document_id):
        self.deleted = document_id


class FakeIngestion:
    def __init__(self, registry, storage):
        self.registry, self.storage = registry, storage

    def submit(self, *, pdf_bytes, filename, workspace_id, **_kwargs):
        doc_id = str(uuid.uuid4())
        self.storage.save_pdf(doc_id, pdf_bytes)
        return self.registry.create(doc_id, workspace_id, filename)


class FakePipeline:
    def __init__(self):
        self.calls = []

    def answer(self, **kwargs):
        self.calls.append(kwargs)
        return {"answer": "Adam was used [1].", "citations": [], "search_query": kwargs["question"], "contexts": []}


class FakeProvider:
    """Stands in for an LLM provider: answers "OK" or raises the given error."""

    def __init__(self, error=None):
        self.error = error

    def generate(self, *args, **kwargs):
        if self.error:
            raise self.error
        return "OK"


@pytest.fixture
def svc(tmp_path, monkeypatch):
    """Fake services, and no server key, so requests behave as on a public deployment."""
    monkeypatch.setattr(settings, "allow_server_key", False)
    registry = DocumentRegistry(tmp_path / "reg.sqlite3")
    storage = DocumentStorage(tmp_path)
    services = main.Services(registry=registry, storage=storage, store=FakeStore(),
                             ingestion=FakeIngestion(registry, storage), pipeline=FakePipeline())
    monkeypatch.setattr(main, "services", services)
    return services


@pytest.fixture
def client(svc):
    return TestClient(main.app)


def upload(client, content=PDF, headers=WS):
    return client.post("/documents", headers=headers, files={"file": ("a.pdf", content, "application/pdf")})


def test_empty_and_oversized_uploads_are_rejected(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 64)
    assert upload(client, content=b"").status_code == 400
    assert upload(client, content=PDF + b"x" * 100).status_code == 413


def test_provider_list(client):
    body = client.get("/config/providers").json()
    assert [p["id"] for p in body["providers"]] == ["gemini", "groq", "openrouter"]
    assert body["server_key_available"] is False


@pytest.mark.parametrize("error, ok, code", [
    (None, True, None),
    (ProviderError("rejected", kind="invalid_key", provider="gemini"), False, "invalid_key"),
    (ProviderError("slow down", kind="rate_limited", provider="gemini"), True, None),
])
def test_key_test_reports_the_outcome(client, monkeypatch, error, ok, code):
    monkeypatch.setattr(main, "build_provider", lambda creds: FakeProvider(error))
    body = client.post("/keys/test", json={"provider": "gemini", "api_key": "test-key-0000000000"}).json()
    assert body["ok"] is ok and body.get("code") == code


def test_key_test_rejects_unknown_providers(client):
    assert client.post("/keys/test", json={"provider": "nope", "api_key": "x"}).status_code == 400


def test_question_without_a_key_asks_for_one(client):
    r = client.post("/query", headers=WS, json={"question": "Which optimizer was used?"})
    assert r.status_code == 401
    detail = r.json()["detail"]
    assert detail["code"] == "missing_key"
    assert detail["help_url"] == "https://aistudio.google.com/apikey"


def test_question_passes_session_and_scope(client, svc):
    doc_id = upload(client).json()["id"]
    headers = {**WITH_KEY, "X-Session-Id": "chat-12345678"}
    r = client.post("/query", headers=headers, json={"question": "Which optimizer?", "document_ids": [doc_id]})
    assert r.status_code == 200 and r.json()["answer"] == "Adam was used [1]."
    call = svc.pipeline.calls[0]
    assert call["session_id"] == "chat-12345678" and call["document_ids"] == [doc_id]


def test_question_about_someone_elses_paper_is_404(client):
    r = client.post("/query", headers=WITH_KEY, json={"question": "x", "document_ids": ["not-my-paper-0000"]})
    assert r.status_code == 404


def test_unknown_provider_header_is_400(client):
    assert client.get("/documents", headers={**WS, "X-LLM-Provider": "nope"}).status_code == 400


def test_scoring_needs_a_research_topic(client):
    doc_id = upload(client).json()["id"]
    assert client.post(f"/documents/{doc_id}/score", headers=WITH_KEY).status_code == 400


def test_summary_waits_until_the_paper_is_ready(client, monkeypatch):
    monkeypatch.setattr(main, "build_provider", lambda creds: FakeProvider())
    doc_id = upload(client).json()["id"]
    assert client.get(f"/documents/{doc_id}/analysis", headers=WITH_KEY).status_code == 409
