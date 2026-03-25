from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from backend.app.services.llm import get_chat_model, extract_usage


DOC_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a Project Intelligence Assistant. Answer strictly using the provided CONTEXT.\n"
            "If the context is insufficient, say what is missing and what document would contain it.\n"
            "Include explicit citations by referencing the provided source_ids like [a1b2c3d4e5f6].\n"
            "Do not invent numbers or dates.\n",
        ),
        ("human", "QUESTION:\n{question}\n\nCHAT HISTORY (for follow-ups):\n{history}\n\nCONTEXT:\n{context}\n\nAnswer:"),
    ]
)


def format_history(chat_history: list[dict[str, Any]], max_turns: int = 8) -> str:
    turns = chat_history[-max_turns:]
    lines: list[str] = []
    for t in turns:
        role = t.get("role", "user")
        content = t.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def format_context(docs: list[Document], source_ids: list[str]) -> str:
    blocks: list[str] = []
    for doc, sid in zip(docs, source_ids, strict=False):
        meta = doc.metadata or {}
        header = f"[{sid}] {meta.get('filename','unknown')}"
        if meta.get("asset_type") == "pdf" and meta.get("page") is not None:
            header += f" (page {meta.get('page')})"
        if meta.get("asset_type") == "table" and meta.get("sheet"):
            header += f" (sheet {meta.get('sheet')})"
        blocks.append(header + "\n" + doc.page_content)
    return "\n\n---\n\n".join(blocks)


async def answer_with_context(question: str, *, history: str, docs: list[Document], source_ids: list[str]) -> tuple[str, dict | None]:
    llm = get_chat_model(temperature=0.1)
    context = format_context(docs, source_ids)
    msg = DOC_QA_PROMPT.format_messages(question=question, history=history, context=context)
    try:
        resp = await llm.ainvoke(msg)
        text = getattr(resp, "content", str(resp))
        return text, extract_usage(resp)
    except Exception as e:
        # Keep the prototype usable even when the LLM provider isn't available.
        from backend.app.rag.citations import excerpt_for

        excerpts = []
        for doc, sid in zip(docs, source_ids, strict=False):
            excerpts.append(f"- [{sid}] {excerpt_for(doc)}")
        fallback = (
            "LLM is unavailable (check `LLM_PROVIDER` and credentials / local model). "
            "I can’t generate a full answer, but here are the most relevant excerpts with citations:\n\n"
            + "\n".join(excerpts[:8])
        )
        return fallback, None

