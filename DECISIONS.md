# Technical Decisions & Trade-offs

This log records key decisions made during the take-home prototype, including alternatives considered, trade-offs accepted, and when I would revisit each decision.

## D1 — Local-first embeddings (Sentence-Transformers)
- **Decision**: Use `sentence-transformers/all-MiniLM-L6-v2` via `HuggingFaceEmbeddings` as the default embedding model.
- **Alternatives**: OpenAI embeddings; Cohere/Voyage embeddings; domain-tuned embeddings.
- **Rationale**: Keeps the system runnable without external API keys and reduces cost/complexity for a demo.
- **Trade-offs**: We accept potentially lower retrieval quality vs larger/domain embeddings.
- **Revisit when**: Retrieval quality is insufficient on real documents; move to better embeddings or fine-tuned models.

## D2 — Chroma as the vector store with metadata filtering
- **Decision**: Use Chroma with persistence under `backend/storage/chroma`.
- **Alternatives**: FAISS (fast but limited metadata filtering), Qdrant (production-grade), Pinecone (managed).
- **Rationale**: Chroma provides a simple developer experience and supports metadata filtering by `session_id`.
- **Trade-offs**: Not the best choice for multi-node scale or strict multi-tenant needs.
- **Revisit when**: Need concurrent users, high write throughput, or robust ops → Qdrant/managed vector DB.

## D3 — Hybrid retrieval (BM25 + vector) over naive similarity
- **Decision**: Implement hybrid retrieval with an `EnsembleRetriever`.
- **Alternatives**: Vector-only similarity; re-ranking only; HyDE query expansion.
- **Rationale**: Project domains have many exact identifiers (risk IDs, vendor names) and semi-structured phrases that BM25 captures well.
- **Trade-offs**: Maintains a per-session BM25 index in memory (prototype limitation).
- **Revisit when**: Need persistence and scale; consolidate retrieval in a single engine (e.g., Qdrant + BM25/keyword support).

## D4 — Multi-agent separation: Router + Document Q&A + Data Analysis
- **Decision**: Separate responsibilities into three agents with a router that selects the best specialist.
- **Alternatives**: Single “do everything” agent; tool-based function calling without explicit agents.
- **Rationale**: Matches the interview requirement of “add a new agent live” and keeps code modular for extension.
- **Trade-offs**: Slight overhead (routing step) and more moving parts.
- **Revisit when**: Routing becomes unstable; introduce explicit user controls or confidence thresholds + fallback.

## D5 — Session-scoped retrieval
- **Decision**: Tag all indexed chunks with `session_id` and filter retrieval by session.
- **Alternatives**: Global index shared by everyone; project-based partitions; user auth + per-tenant indices.
- **Rationale**: Prevents cross-session information leakage in a prototype without authentication.
- **Trade-offs**: Users can’t easily query across sessions unless they reuse the same session id.
- **Revisit when**: Introduce user accounts and “projects”; store a persistent project_id and allow controlled sharing.

## D6 — Tabular analysis approach (computed aggregates + citations)
- **Decision**: Data Analysis Agent computes key aggregates (budget/actual/forecast/variance) when columns are recognizable; otherwise it falls back to retrieval-style answers over table previews.
- **Alternatives**: Pandas “code interpreter” agent; SQL engine over normalized tables; dedicated BI semantics layer.
- **Rationale**: Safer and faster than executing arbitrary generated code; still demonstrates numeric reasoning.
- **Trade-offs**: Limited flexibility for arbitrary analytic questions.
- **Revisit when**: Need flexible analysis; add a sandboxed code execution tool or translate to SQL with strict controls.

## D7 — Observability via structured JSON logs
- **Decision**: Log agent calls with `trace_id`, `session_id`, agent, latency, and usage (when available).
- **Alternatives**: LangSmith; OpenTelemetry traces; Arize Phoenix.
- **Rationale**: Keeps the prototype self-contained while still enabling debugging and interview “trace a request” walkthroughs.
- **Trade-offs**: No UI for traces; no distributed tracing spans yet.
- **Revisit when**: Deploying beyond demo; add OpenTelemetry and a trace viewer.

