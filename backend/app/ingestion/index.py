from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever

from backend.app.core.config import settings
from backend.app.ingestion.chunking import get_text_splitter
from backend.app.services.embeddings import get_embeddings


@dataclass
class RetrievalBundle:
    vectorstore: Chroma
    bm25_docs_by_session: dict[str, list[Document]]


_bundle: RetrievalBundle | None = None


def get_bundle() -> RetrievalBundle:
    global _bundle
    if _bundle is not None:
        return _bundle

    persist_dir = Path(settings.storage_dir) / "chroma"
    persist_dir.mkdir(parents=True, exist_ok=True)
    vs = Chroma(
        collection_name="project_assistant",
        persist_directory=str(persist_dir),
        embedding_function=get_embeddings(),
    )
    _bundle = RetrievalBundle(vectorstore=vs, bm25_docs_by_session={})
    return _bundle


def _vector_retriever(session_id: str):
    bundle = get_bundle()
    return bundle.vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": settings.top_k, "filter": {"session_id": session_id}},
    )


def _bm25_retriever(session_id: str) -> BM25Retriever | None:
    bundle = get_bundle()
    bm25_docs = bundle.bm25_docs_by_session.get(session_id, [])
    if not bm25_docs:
        return None
    bm25 = BM25Retriever.from_documents(bm25_docs)
    bm25.k = settings.top_k
    return bm25


def hybrid_retrieve(session_id: str, query: str) -> list[Document]:
    """
    Hybrid retrieval without depending on EnsembleRetriever (LangChain versions vary).
    Strategy: take top-k from BM25 and vector similarity, then de-duplicate.
    """
    vect = _vector_retriever(session_id)
    bm25 = _bm25_retriever(session_id)

    vect_docs = vect.invoke(query) or []
    bm25_docs = bm25.invoke(query) if bm25 else []

    seen: set[str] = set()
    out: list[Document] = []

    def key(d: Document) -> str:
        m = d.metadata or {}
        return f"{m.get('filename')}|{m.get('page')}|{m.get('sheet')}|{m.get('chunk_id')}|{hash(d.page_content)}"

    for d in (bm25_docs + vect_docs):
        k = key(d)
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
        if len(out) >= settings.top_k:
            break

    return out


def upsert_documents(session_id: str, docs: list[Document]) -> None:
    bundle = get_bundle()

    splitter = get_text_splitter()
    split_docs = splitter.split_documents(docs)
    for i, d in enumerate(split_docs):
        d.metadata.setdefault("chunk_id", i)

    bundle.vectorstore.add_documents(split_docs)

    # Keep a lightweight sparse index per session (in-memory for prototype)
    bundle.bm25_docs_by_session.setdefault(session_id, [])
    bundle.bm25_docs_by_session[session_id].extend(split_docs)

