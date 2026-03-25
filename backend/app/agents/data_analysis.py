from __future__ import annotations

import re
from typing import Any

import pandas as pd

from backend.app.agents.base import AgentResult, SourceChunk
from backend.app.rag.citations import excerpt_for, source_id_for
from backend.app.rag.chains import answer_with_context, format_history
from backend.app.ingestion.index import hybrid_retrieve
from backend.app.services.tabular_store import tabular_store


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = { _norm(c): c for c in df.columns }
    for cand in candidates:
        key = _norm(cand)
        if key in cols:
            return cols[key]
    return None


def _to_num(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(",", "", regex=False)
    s = s.str.replace(r"[^0-9\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def _summarize_financials(dfs: list[pd.DataFrame]) -> dict[str, Any] | None:
    totals = {"budget": 0.0, "actual": 0.0, "forecast": 0.0, "variance": 0.0}
    found_any = False

    for df in dfs:
        budget_col = _find_col(df, ["budget", "baselinebudget", "approvedbudget"])
        actual_col = _find_col(df, ["actual", "actualcost", "spent", "costtodate"])
        forecast_col = _find_col(df, ["forecast", "eac", "estimateatcompletion"])
        variance_col = _find_col(df, ["variance", "budgetvariance", "var"])

        if not any([budget_col, actual_col, forecast_col, variance_col]):
            continue

        found_any = True
        if budget_col:
            totals["budget"] += float(_to_num(df[budget_col]).sum(skipna=True))
        if actual_col:
            totals["actual"] += float(_to_num(df[actual_col]).sum(skipna=True))
        if forecast_col:
            totals["forecast"] += float(_to_num(df[forecast_col]).sum(skipna=True))
        if variance_col:
            totals["variance"] += float(_to_num(df[variance_col]).sum(skipna=True))
        elif budget_col and forecast_col:
            totals["variance"] += float(_to_num(df[budget_col]).sum(skipna=True) - _to_num(df[forecast_col]).sum(skipna=True))

    if not found_any:
        return None

    # Derived metric
    if totals["budget"] > 0:
        totals["burn_pct"] = round((totals["actual"] / totals["budget"]) * 100.0, 2)
    return totals


class DataAnalysisAgent:
    name = "data_analysis"

    async def run(self, message: str, *, session_id: str, chat_history: list[dict[str, Any]]) -> AgentResult:
        assets = tabular_store.list(session_id)
        dfs = [a.df for a in assets]

        computed = _summarize_financials(dfs) if dfs else None
        if computed:
            # Provide computed figures + cite the table docs via retrieval (so the UI can show sources).
            docs = hybrid_retrieve(session_id, message)
            source_ids = [source_id_for(d) for d in docs]
            history = format_history(chat_history)

            question = (
                f"{message}\n\n"
                f"Computed aggregates from uploaded tabular data (use these numbers, do not change them):\n"
                f"- total_budget: {computed.get('budget')}\n"
                f"- total_actual: {computed.get('actual')}\n"
                f"- total_forecast: {computed.get('forecast')}\n"
                f"- total_variance: {computed.get('variance')}\n"
                f"- burn_pct: {computed.get('burn_pct')}\n"
            )
            answer, usage = await answer_with_context(question, history=history, docs=docs, source_ids=source_ids)

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

        # Fallback: treat as table RAG over indexed table previews
        docs = hybrid_retrieve(session_id, message)
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

