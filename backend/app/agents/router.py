from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from backend.app.services.llm import get_chat_model


RouteName = Literal["document_qa", "data_analysis"]


class RouteDecision(BaseModel):
    route: RouteName = Field(..., description="Which specialist agent should handle the query.")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


ROUTER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a router for a project intelligence assistant.\n"
            "Decide which agent should handle the query:\n"
            "- document_qa: questions answered from PDFs / narrative docs / risks described in text\n"
            "- data_analysis: questions requiring numeric aggregation, filtering, or analysis over CSV/Excel tables\n"
            "Return ONLY valid JSON matching this schema: {\"route\": \"document_qa\"|\"data_analysis\", \"confidence\": 0-1, \"reason\": \"...\"}\n",
        ),
        ("human", "Query: {query}"),
    ]
)


def _heuristic_route(query: str) -> RouteDecision:
    q = query.lower()
    data_keywords = [
        "budget",
        "cost",
        "spent",
        "forecast",
        "variance",
        "sum",
        "total",
        "average",
        "percent",
        "trend",
        "burn",
        "eac",
        "csv",
        "excel",
        "xlsx",
        "table",
    ]
    if any(k in q for k in data_keywords) or re.search(r"\b\d+(\.\d+)?\b", q):
        return RouteDecision(route="data_analysis", confidence=0.62, reason="Heuristic: numeric / tabular intent.")
    return RouteDecision(route="document_qa", confidence=0.62, reason="Heuristic: narrative / document intent.")


async def route_query(query: str) -> RouteDecision:
    try:
        llm = get_chat_model(temperature=0.0)
        msgs = ROUTER_PROMPT.format_messages(query=query)
        resp = await llm.ainvoke(msgs)
        raw = getattr(resp, "content", "").strip()
        data = json.loads(raw)
        return RouteDecision.model_validate(data)
    except Exception:
        return _heuristic_route(query)

