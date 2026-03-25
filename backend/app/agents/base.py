from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class SourceChunk:
    source_id: str
    filename: str
    excerpt: str
    page: int | None = None
    sheet: str | None = None
    asset_type: str | None = None


@dataclass
class AgentResult:
    agent: str
    answer: str
    sources: list[SourceChunk]
    contexts: list[str] | None = None
    usage: dict[str, Any] | None = None


class Agent(Protocol):
    name: str

    async def run(self, message: str, *, session_id: str, chat_history: list[dict[str, Any]]) -> AgentResult: ...

