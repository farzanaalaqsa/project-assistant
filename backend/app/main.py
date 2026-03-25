from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.app.agents.router import route_query
from backend.app.agents.registry import AGENTS
from backend.app.core.config import settings
from backend.app.core.logging import LogEvent, log_event, setup_logging
from backend.app.core.session import session_store
from backend.app.ingestion.index import upsert_documents
from backend.app.ingestion.loaders import load_any
from backend.app.services.tabular_store import TabularAsset, tabular_store


logger = logging.getLogger("project_assistant")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class SourceOut(BaseModel):
    source_id: str
    filename: str
    excerpt: str
    page: int | None = None
    sheet: str | None = None
    asset_type: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    trace_id: str
    agent: str
    answer: str
    sources: list[SourceOut]
    usage: dict[str, Any] | None = None
    latency_ms: int


def create_app() -> FastAPI:
    setup_logging(settings.log_level)
    app = FastAPI(title="AI-Powered Project Intelligence Assistant", version="0.1.0")

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "env": settings.app_env}

    @app.post("/api/upload")
    async def upload(files: list[UploadFile] = File(...), session_id: str | None = None) -> dict[str, Any]:
        trace_id = str(uuid.uuid4())
        sess = session_store.get_or_create(session_id)
        try:
            upload_dir = Path(settings.storage_dir) / "uploads" / sess.session_id
            upload_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log_event(
                logger,
                LogEvent(
                    event="upload_storage_init_failed",
                    trace_id=trace_id,
                    session_id=sess.session_id,
                    extra={"storage_dir": settings.storage_dir, "error": str(e)},
                ),
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to initialize upload storage. "
                    "Set STORAGE_DIR to a writable path (e.g. /tmp/storage on Render Free)."
                ),
            ) from e

        ingested: list[str] = []
        total_docs = 0
        total_tables = 0

        for f in files:
            try:
                dest = upload_dir / f.filename
                content = await f.read()
                dest.write_bytes(content)

                loaded = load_any(dest, sess.session_id)
                upsert_documents(sess.session_id, loaded.documents)
                ingested.append(f.filename)
                total_docs += len(loaded.documents)

                table_assets: list[TabularAsset] = []
                for sheet, df in loaded.tables:
                    table_assets.append(TabularAsset(filename=f.filename, sheet=sheet, df=df))
                if table_assets:
                    tabular_store.add(sess.session_id, table_assets)
                    total_tables += len(table_assets)
            except HTTPException:
                raise
            except Exception as e:
                log_event(
                    logger,
                    LogEvent(
                        event="upload_ingest_failed",
                        trace_id=trace_id,
                        session_id=sess.session_id,
                        extra={"filename": f.filename, "error": str(e)},
                    ),
                )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Upload failed while processing `{f.filename}`. "
                        f"Common fixes: set `GEMINI_API_KEY` (for embeddings + LLM), or set "
                        f"`STORAGE_DIR=/tmp/storage` on Render Free. Error: {type(e).__name__}: {e}"
                    ),
                ) from e

        return {
            "session_id": sess.session_id,
            "trace_id": trace_id,
            "ingested_files": ingested,
            "documents_indexed": total_docs,
            "tables_loaded": total_tables,
        }

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> ChatResponse:
        trace_id = str(uuid.uuid4())
        started = time.perf_counter()

        sess = session_store.get_or_create(req.session_id)
        session_store.append(sess.session_id, "user", req.message)

        decision = await route_query(req.message)
        agent = AGENTS[decision.route]

        log_event(
            logger,
            LogEvent(
                event="agent_call_start",
                trace_id=trace_id,
                session_id=sess.session_id,
                agent=agent.name,
                input={"message": req.message, "router": decision.model_dump()},
            ),
        )

        result = await agent.run(req.message, session_id=sess.session_id, chat_history=sess.chat_history)

        session_store.append(sess.session_id, "assistant", result.answer)

        latency_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            logger,
            LogEvent(
                event="agent_call_end",
                trace_id=trace_id,
                session_id=sess.session_id,
                agent=result.agent,
                latency_ms=latency_ms,
                output={"answer_chars": len(result.answer), "sources": len(result.sources)},
                usage=result.usage,
            ),
        )

        return ChatResponse(
            session_id=sess.session_id,
            trace_id=trace_id,
            agent=result.agent,
            answer=result.answer,
            sources=[SourceOut(**s.__dict__) for s in result.sources],
            usage=result.usage,
            latency_ms=latency_ms,
        )

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()

