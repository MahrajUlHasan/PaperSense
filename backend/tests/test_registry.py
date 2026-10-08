from services.registry import DocumentRegistry


def test_document_lifecycle(tmp_path):
    """Create, update, list and delete a document; other workspaces see nothing."""
    reg = DocumentRegistry(tmp_path / "reg.sqlite3")
    doc = reg.create("11111111-1111-4111-8111-111111111111", "ws-aaaaaaaa", "paper.pdf")
    assert doc["status"] == "queued"

    reg.update(doc["id"], status="ready", stats={"chunks": 12}, page_count=9)
    again = reg.get(doc["id"])
    assert again["status"] == "ready" and again["stats"] == {"chunks": 12} and again["page_count"] == 9

    assert [d["id"] for d in reg.list("ws-aaaaaaaa")] == [doc["id"]]
    assert reg.list("ws-bbbbbbbb") == []

    reg.delete(doc["id"])
    assert reg.get(doc["id"]) is None


def test_interrupted_jobs_become_errors(tmp_path):
    reg = DocumentRegistry(tmp_path / "reg.sqlite3")
    reg.create("22222222-2222-4222-8222-222222222222", "ws-aaaaaaaa", "a.pdf")
    assert reg.fail_interrupted() == 1
    assert reg.get("22222222-2222-4222-8222-222222222222")["status"] == "error"


def test_research_is_per_workspace(tmp_path):
    reg = DocumentRegistry(tmp_path / "reg.sqlite3")
    reg.set_research("ws-aaaaaaaa", "Sleep", "desc", "breakdown")
    assert reg.get_research("ws-aaaaaaaa")["topic"] == "Sleep"
    assert reg.get_research("ws-bbbbbbbb") is None
