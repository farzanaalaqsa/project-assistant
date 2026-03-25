from __future__ import annotations

from langchain_core.embeddings import Embeddings

from backend.app.core.config import settings


def _gemini_model_variants(model: str) -> list[str]:
    m = (model or "").strip()
    if not m:
        return ["gemini-embedding-001", "models/gemini-embedding-001"]
    # Commonly supported names in the Gemini API docs:
    # - gemini-embedding-001
    # - models/gemini-embedding-001 (some SDKs accept this form)
    variants = [m]
    if m.startswith("models/"):
        variants.append(m.removeprefix("models/"))
    else:
        variants.append(f"models/{m}")
    # Ensure stable known-good fallback.
    for fallback in ["gemini-embedding-001", "models/gemini-embedding-001"]:
        if fallback not in variants:
            variants.append(fallback)
    # De-dupe while preserving order
    out: list[str] = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out


def get_embeddings() -> Embeddings:
    # Prefer lightweight hosted embeddings when available, to avoid shipping torch-heavy
    # dependencies in the default runtime.
    if settings.gemini_api_key:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        class GeminiEmbeddingsWithFallback(Embeddings):
            def __init__(self) -> None:
                self._models = [
                    GoogleGenerativeAIEmbeddings(model=m, google_api_key=settings.gemini_api_key)
                    for m in _gemini_model_variants(settings.gemini_embed_model)
                ]

            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                last_err: Exception | None = None
                for emb in self._models:
                    try:
                        return emb.embed_documents(texts)
                    except Exception as e:
                        last_err = e
                raise last_err or RuntimeError("Gemini embeddings failed")

            def embed_query(self, text: str) -> list[float]:
                last_err: Exception | None = None
                for emb in self._models:
                    try:
                        return emb.embed_query(text)
                    except Exception as e:
                        last_err = e
                raise last_err or RuntimeError("Gemini embeddings failed")

        return GeminiEmbeddingsWithFallback()
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
            "No embeddings provider available. Set GEMINI_API_KEY or OPENAI_API_KEY for hosted embeddings "
            "or install local extras (see backend/requirements-local.txt)."
        ) from e

