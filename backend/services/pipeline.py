"""Question answering: retrieve → context blocks → LLM → answer with citations."""
from __future__ import annotations

from loguru import logger

from config import settings
from services.citations import renumber_citations
from services.embeddings import EmbeddingService
from services.llm import ImageInput, LLMCredentials, LLMProvider, ProviderError, build_provider
from services.prompts import REWRITE_PROMPT, SYSTEM_PROMPT, build_answer_prompt
from services.qdrant_store import QdrantStore
from services.retrieval import ContextBlock, build_context_blocks, normalize_scores
from services.storage import DocumentStorage

NO_CONTEXT_ANSWER = (
    "I couldn't find anything relevant in your papers. Check that the paper has finished "
    "processing, or ask using the paper's own terms."
)


def citation_from_block(index: int, block: ContextBlock) -> dict:
    return {
        "index": index,
        "document_id": block.document_id,
        "filename": block.filename,
        "section": block.section,
        "content_type": block.content_type,
        "pages": block.pages,
        "page": block.pages[0] if block.pages else None,
        "boxes": block.boxes,
        "relevance": block.relevance,
        "text": block.text,
        "figure_index": block.figure_index,
    }


class QueryPipeline:
    def __init__(self, *, embedder: EmbeddingService, store: QdrantStore, storage: DocumentStorage, memory=None):
        self.embedder = embedder
        self.store = store
        self.storage = storage
        self.memory = memory

    def retrieve(self, query: str, workspace_id: str, document_ids: list[str] | None,
                 top_k: int, use_hybrid: bool) -> list[ContextBlock]:
        """Context blocks for a query. Twice top_k hits are fetched, because duplicates get removed."""
        vector = self.embedder.embed_query(query)
        limit = top_k * 2
        if use_hybrid:
            hits = self.store.hybrid_search(query, vector, workspace_id, document_ids,
                                            limit=limit, prefetch_limit=settings.prefetch_limit)
        else:
            hits = self.store.dense_search(vector, workspace_id, document_ids, limit=limit)
        return build_context_blocks(normalize_scores(hits), fetch_neighbors=self.store.fetch_chunks,
                                    max_blocks=top_k)

    def _search_query(self, provider: LLMProvider, question: str, history: str) -> str:
        """Turn a follow-up ("And on English-French?") into a standalone search query.

        Costs one small request, and only when there is history. Key problems are raised;
        any other failure just keeps the original question.
        """
        if not history or not settings.rewrite_followups:
            return question
        try:
            rewritten = provider.generate(REWRITE_PROMPT.format(history=history[-2000:], question=question),
                                          temperature=0.0, max_output_tokens=512)
        except ProviderError as err:
            if err.kind in ("invalid_key", "missing_key"):
                raise
            logger.warning(f"Follow-up rewrite skipped: {err.kind}")
            return question
        rewritten = rewritten.strip().strip('"').strip()
        return rewritten if 3 <= len(rewritten) <= 500 else question

    def _figure_images(self, blocks: list[ContextBlock], max_images: int = 3) -> tuple[list[ImageInput], list[int]]:
        """PNGs of retrieved figure blocks (up to max_images) and the source numbers they belong to."""
        images, refs = [], []
        for number, block in enumerate(blocks, start=1):
            if block.content_type != "figure" or not block.figure_index or len(images) >= max_images:
                continue
            path = self.storage.figure_path(block.document_id, block.figure_index)
            if path.exists():
                images.append(ImageInput(path.read_bytes()))
                refs.append(number)
        return images, refs

    def answer(self, *, question: str, creds: LLMCredentials, workspace_id: str, session_id: str,
               document_ids: list[str] | None = None, top_k: int | None = None,
               use_hybrid: bool = True) -> dict:
        provider = build_provider(creds)
        top_k = top_k or settings.top_k
        history = self.memory.history(workspace_id, session_id) if self.memory else ""
        search_query = self._search_query(provider, question, history)

        blocks = self.retrieve(search_query, workspace_id, document_ids, top_k, use_hybrid)
        if not blocks:
            return {"answer": NO_CONTEXT_ANSWER, "citations": [], "search_query": search_query, "contexts": []}

        images, image_refs = self._figure_images(blocks) if provider.supports_images else ([], [])
        raw = provider.generate(build_answer_prompt(question, blocks, history, image_refs),
                                system=SYSTEM_PROMPT, images=images, temperature=0.2,
                                max_output_tokens=settings.llm_max_output_tokens)
        answer, used = renumber_citations(raw, len(blocks))
        citations = [citation_from_block(new, blocks[old - 1]) for new, old in enumerate(used, start=1)]
        if self.memory:
            self.memory.add_turn(workspace_id, session_id, question, answer)
        return {"answer": answer, "citations": citations, "search_query": search_query,
                "contexts": [b.text for b in blocks]}
