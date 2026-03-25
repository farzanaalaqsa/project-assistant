from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class TabularAsset:
    filename: str
    sheet: str | None
    df: pd.DataFrame


class TabularStore:
    def __init__(self) -> None:
        self._by_session: dict[str, list[TabularAsset]] = {}

    def add(self, session_id: str, assets: list[TabularAsset]) -> None:
        self._by_session.setdefault(session_id, [])
        self._by_session[session_id].extend(assets)

    def list(self, session_id: str) -> list[TabularAsset]:
        return list(self._by_session.get(session_id, []))


tabular_store = TabularStore()

