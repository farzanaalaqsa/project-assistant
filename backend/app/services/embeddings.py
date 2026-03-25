from __future__ import annotations

from langchain_core.embeddings import Embeddings

from backend.app.core.config import settings


def get_embeddings() -> Embeddings:
    # Prefer lightweight hosted embeddings when available, to avoid shipping torch-heavy
    # dependencies in the default runtime.
    if settings.openai_api_key:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    # Local fallback (requires `backend/requirements-local.txt`)
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        raise RuntimeError(
            "No embeddings provider available. Set OPENAI_API_KEY for hosted embeddings "
            "or install local extras (see backend/requirements-local.txt)."
        ) from e

