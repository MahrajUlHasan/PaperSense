from services.retrieval import build_context_blocks, dedupe_hits, normalize_scores


def hit(order, text, score, section="1 Intro", doc="d1", ctype="text"):
    return {"document_id": doc, "order": order, "text": text, "score": score, "section": section,
            "content_type": ctype, "pages": [1], "boxes": [{"page": 1, "l": 0, "t": 0, "r": 1, "b": 1}],
            "filename": "a.pdf"}


def test_duplicates_are_removed():
    hits = [hit(1, "attention is all you need", 3.0), hit(1, "attention is all you need", 2.0),
            hit(5, "attention is all you need indeed", 1.0)]
    assert [h["order"] for h in dedupe_hits(hits)] == [1]


def test_consecutive_hits_merge_into_one_block():
    hits = normalize_scores([hit(3, "part a", 2.0), hit(4, "part b", 1.0), hit(9, "other", 0.5, section="5 End")])
    blocks = build_context_blocks(hits)
    assert [b.orders for b in blocks] == [[3, 4], [9]]
    assert blocks[0].relevance == 1.0


def test_tables_never_merge_with_text():
    hits = normalize_scores([hit(3, "text", 2.0), hit(4, "| a | b |", 1.0, ctype="table")])
    assert len(build_context_blocks(hits)) == 2
