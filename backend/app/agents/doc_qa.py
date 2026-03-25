from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from backend.app.agents.base import AgentResult, SourceChunk
from backend.app.core.config import settings
from backend.app.ingestion.index import hybrid_retrieve
from backend.app.rag.citations import excerpt_for, source_id_for
from backend.app.rag.chains import answer_with_context, format_history


def _maybe_rerank(query: str, docs: list[Document]) -> list[Document]:
    if not settings.enable_rerank or len(docs) <= 2:
        return docs
    try:
        from sentence_transformers import CrossEncoder
    except Exception:
        return docs

    # Lightweight cross-encoder rerank
    model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    pairs = [[query, d.page_content] for d in docs]
    scores = model.predict(pairs).tolist()
    ranked = sorted(zip(docs, scores, strict=False), key=lambda x: x[1], reverse=True)
    return [d for d, _s in ranked[: settings.top_k]]


class DocumentQAAgent:
    name = "document_qa"

    async def run(self, message: str, *, session_id: str, chat_history: list[dict[str, Any]]) -> AgentResult:
        docs = hybrid_retrieve(session_id, message)
        docs = _maybe_rerank(message, docs)

        source_ids = [source_id_for(d) for d in docs]
        history = format_history(chat_history)
        answer, usage = await answer_with_context(message, history=history, docs=docs, source_ids=source_ids)

        sources: list[SourceChunk] = []
        for doc, sid in zip(docs, source_ids, strict=False):
            meta = doc.metadata or {}
            sources.append(
                SourceChunk(
                    source_id=sid,
                    filename=str(meta.get("filename", "unknown")),
                    excerpt=excerpt_for(doc),
                    page=meta.get("page"),
                    sheet=meta.get("sheet"),
                    asset_type=meta.get("asset_type"),
                )
            )

        return AgentResult(
            agent=self.name,
            answer=answer,
            sources=sources,
            contexts=[d.page_content for d in docs],
            usage=usage,
        )

