from services.research import paper_digest


def test_digest_keeps_start_end_and_sections_in_order():
    chunks = [{"content_type": "text", "text": f"chunk {i} " * 50, "section": f"S{i // 5}", "order": i}
              for i in range(40)]
    chunks.append({"content_type": "figure", "text": "Figure 1", "caption": "Figure 1: Model", "order": 40})
    digest = paper_digest(chunks, max_chars=3000)
    assert digest.index("chunk 0") < digest.index("chunk 39")
    assert "Sections: S0; S1" in digest and "Figure 1: Model" in digest
    assert len(digest) < 3600
