from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


@dataclass
class LoadedAsset:
    documents: list[Document]
    tables: list[tuple[str | None, pd.DataFrame]]


def load_pdf(path: Path, session_id: str) -> LoadedAsset:
    loader = PyPDFLoader(str(path))
    docs = loader.load()
    for d in docs:
        d.metadata.update(
            {
                "session_id": session_id,
                "filename": path.name,
                "asset_type": "pdf",
            }
        )
    return LoadedAsset(documents=docs, tables=[])


def _df_to_documents(df: pd.DataFrame, *, session_id: str, filename: str, sheet: str | None) -> list[Document]:
    # Keep a human-readable representation that the LLM can cite.
    preview = df.head(60).to_markdown(index=False)
    meta = {
        "session_id": session_id,
        "filename": filename,
        "asset_type": "table",
        "sheet": sheet,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
    }
    return [
        Document(
            page_content=(
                f"TABLE SOURCE: {filename}"
                + (f" (sheet: {sheet})" if sheet else "")
                + "\n\n"
                + preview
            ),
            metadata=meta,
        )
    ]


def load_csv(path: Path, session_id: str) -> LoadedAsset:
    df = pd.read_csv(path)
    docs = _df_to_documents(df, session_id=session_id, filename=path.name, sheet=None)
    return LoadedAsset(documents=docs, tables=[(None, df)])


def load_xlsx(path: Path, session_id: str) -> LoadedAsset:
    raw = pd.read_excel(path, sheet_name=None)
    docs: list[Document] = []
    tables: list[tuple[str | None, pd.DataFrame]] = []
    for sheet, df in raw.items():
        tables.append((str(sheet), df))
        docs.extend(_df_to_documents(df, session_id=session_id, filename=path.name, sheet=str(sheet)))
    return LoadedAsset(documents=docs, tables=tables)


def load_any(path: Path, session_id: str) -> LoadedAsset:
    ext = path.suffix.lower().strip(".")
    if ext == "pdf":
        return load_pdf(path, session_id)
    if ext == "csv":
        return load_csv(path, session_id)
    if ext in {"xlsx", "xls"}:
        return load_xlsx(path, session_id)
    raise ValueError(f"Unsupported file type: {path.suffix}")

