from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama

from backend.app.core.config import settings


def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    provider = settings.llm_provider.lower().strip()
    if provider == "openai_compat":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM_PROVIDER=openai_compat")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=temperature,
        )
    if provider == "ollama":
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )
    raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")


def extract_usage(response: object) -> dict | None:
    # Best-effort across providers
    usage = getattr(response, "usage_metadata", None)
    if isinstance(usage, dict) and usage:
        return usage
    llm_output = getattr(response, "llm_output", None)
    if isinstance(llm_output, dict):
        u = llm_output.get("token_usage") or llm_output.get("usage")
        if isinstance(u, dict) and u:
            return u
    return None

