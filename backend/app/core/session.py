from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass
class SessionState:
    session_id: str
    chat_history: list[dict[str, Any]]


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str | None) -> SessionState:
        if not session_id:
            session_id = str(uuid.uuid4())
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id, chat_history=[])
        return self._sessions[session_id]

    def append(self, session_id: str, role: str, content: str) -> None:
        sess = self.get_or_create(session_id)
        sess.chat_history.append({"role": role, "content": content})


session_store = SessionStore()

