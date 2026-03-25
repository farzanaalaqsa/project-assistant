from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pandas as pd
from datasets import Dataset

from backend.app.agents.registry import AGENTS
from backend.app.agents.router import route_query
from backend.app.core.session import session_store
from backend.app.ingestion.index import upsert_documents
from backend.app.ingestion.loaders import load_any
from backend.app.services.tabular_store import TabularAsset, tabular_store


ROOT = Path(__file__).resolve().parents[1]


def load_queries(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


async def ingest_sample_data(session_id: str) -> None:
    data_dir = ROOT / "sample_data"
    files = sorted([p for p in data_dir.iterdir() if p.suffix.lower() in {".pdf", ".csv", ".xlsx", ".xls"}])
    if not files:
        raise RuntimeError("No sample_data files found. Run scripts/generate_sample_data.py first.")

    for p in files:
        loaded = load_any(p, session_id)
        upsert_documents(session_id, loaded.documents)
        if loaded.tables:
            tabular_store.add(
                session_id,
                [TabularAsset(filename=p.name, sheet=sheet, df=df) for sheet, df in loaded.tables],
            )


async def answer_one(session_id: str, question: str) -> dict:
    sess = session_store.get_or_create(session_id)
    decision = await route_query(question)
    agent = AGENTS[decision.route]
    res = await agent.run(question, session_id=session_id, chat_history=sess.chat_history)
    return {
        "question": question,
        "answer": res.answer,
        "contexts": res.contexts or [],
        "agent": res.agent,
    }


async def main() -> None:
    session_id = "eval_session"
    session_store.get_or_create(session_id)
    await ingest_sample_data(session_id)

    queries = load_queries(ROOT / "evaluation" / "queries.jsonl")
    records = []
    for q in queries:
        out = await answer_one(session_id, q["question"])
        out["ground_truth"] = q.get("ground_truth", "")
        out["difficulty"] = q.get("difficulty", "")
        out["id"] = q.get("id", "")
        records.append(out)

    ds = Dataset.from_dict(
        {
            "question": [r["question"] for r in records],
            "answer": [r["answer"] for r in records],
            "contexts": [r["contexts"] for r in records],
            "ground_truth": [r["ground_truth"] for r in records],
        }
    )

    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy

    metrics = [faithfulness, answer_relevancy]

    # Bonus metrics (best-effort)
    try:
        from ragas.metrics import context_precision, context_recall

        metrics.extend([context_precision, context_recall])
    except Exception:
        pass

    try:
        from ragas.metrics import answer_correctness

        metrics.append(answer_correctness)
    except Exception:
        pass

    results = evaluate(ds, metrics=metrics)
    df = results.to_pandas()
    df.insert(0, "id", [r["id"] for r in records])
    df.insert(1, "difficulty", [r["difficulty"] for r in records])
    df.insert(2, "agent", [r["agent"] for r in records])

    out_path = ROOT / "evaluation" / "ragas_results.csv"
    df.to_csv(out_path, index=False)

    print("\nRAGAS results saved to:", out_path)
    print(df.to_markdown(index=False))


if __name__ == "__main__":
    asyncio.run(main())

