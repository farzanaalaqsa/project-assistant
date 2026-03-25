from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    # Chunking tuned for messy project docs: keep enough context to preserve
    # key-number associations (budget, dates), while limiting prompt bloat.
    return RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)

