from __future__ import annotations

import hashlib
from langchain_core.documents import Document


def source_id_for(doc: Document) -> str:
    meta = doc.metadata or {}
    raw = f"{meta.get('filename','unknown')}|{meta.get('page','')}|{meta.get('sheet','')}|{meta.get('chunk_id','')}|{doc.page_content[:80]}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def excerpt_for(doc: Document, max_chars: int = 340) -> str:
    text = " ".join((doc.page_content or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"

