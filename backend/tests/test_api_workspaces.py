"""The API must keep every workspace (browser) separate."""
import uuid

import pytest
from fastapi.testclient import TestClient

import main
from services.registry import DocumentRegistry
from services.storage import DocumentStorage

A = {"X-Workspace-Id": "ws-test-aaaaaaaa"}
B = {"X-Workspace-Id": "ws-test-bbbbbbbb"}
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


@pytest.fixture
def client(tmp_path, monkeypatch):
    """An API client with fake services.

    The TestClient is not used as a context manager, so the real startup
    (models, Qdrant) never runs.
    """
    registry = DocumentRegistry(tmp_path / "reg.sqlite3")
    storage = DocumentStorage(tmp_path)
    fake = main.Services(registry=registry, storage=storage, store=FakeStore(),
                         ingestion=FakeIngestion(registry, storage))
    monkeypatch.setattr(main, "services", fake)
    return TestClient(main.app)


def upload(client, headers, content=PDF):
    return client.post("/documents", headers=headers, files={"file": ("a.pdf", content, "application/pdf")})


def test_documents_are_private_per_workspace(client):
    r = upload(client, A)
    assert r.status_code == 202
    doc_id = r.json()["id"]

    assert [d["id"] for d in client.get("/documents", headers=A).json()["documents"]] == [doc_id]
    assert client.get("/documents", headers=B).json()["documents"] == []
    assert client.get(f"/documents/{doc_id}", headers=B).status_code == 404
    assert client.get(f"/documents/{doc_id}/file", headers=B).status_code == 404
    assert client.delete(f"/documents/{doc_id}", headers=B).status_code == 404

    assert client.get(f"/documents/{doc_id}/file?ws=ws-test-aaaaaaaa").status_code == 200
    assert client.delete(f"/documents/{doc_id}", headers=A).status_code == 200


def test_workspace_header_is_required(client):
    assert client.get("/documents").status_code == 400


def test_rejects_files_that_are_not_pdfs(client):
    assert upload(client, A, content=b"hello").status_code == 400
