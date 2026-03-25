from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="backend/.env", extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"

    llm_provider: str = "ollama"  # ollama | openai_compat | gemini
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embed_model: str = "gemini-embedding-001"

    top_k: int = 6
    enable_rerank: bool = False

    storage_dir: str = "backend/storage"


settings = Settings()

