# Technical Decisions & Trade-offs

This log records key decisions made during the take-home prototype, including alternatives considered, rationale, trade-offs accepted, and when I would revisit each decision. It’s intentionally opinionated and tied to what I actually deployed.

## D1 — Use Gemini as the hosted LLM provider (with a pluggable interface)
- **Decision**: Default to `LLM_PROVIDER=gemini` using LangChain’s `ChatGoogleGenerativeAI` (model configurable via `GEMINI_MODEL`).
- **Alternatives**: OpenAI-compatible endpoints (`openai_compat`); local Ollama.
- **Rationale**: Fast to deploy on free tier; avoids managing local model hosting; aligns with the assessment requirement to show production thinking with a working deployment.
- **Trade-offs**: External dependency + model availability/version drift (404s if a model is removed). Requires careful env/config management.
- **Revisit when**: If the deployment must run on-prem/no external calls → switch to Ollama. If Gemini quotas/rate limits become a bottleneck → consider OpenAI-compatible or multi-provider failover.

## D2 — Use Gemini embeddings for indexing (fallback between model name variants)
- **Decision**: Use `GoogleGenerativeAIEmbeddings` with default `GEMINI_EMBED_MODEL=gemini-embedding-001`, and implement fallback between `gemini-embedding-001` and `models/gemini-embedding-001`.
- **Alternatives**: OpenAI embeddings; local `sentence-transformers` embeddings.
- **Rationale**: Keeps the deployed container lighter (no Torch by default) while still providing high-quality embeddings for RAG. The name-fallback prevents “works locally, fails in prod” issues across SDK/model naming conventions.
- **Trade-offs**: Vendor lock-in; embedding compatibility issues if switching models later (requires re-embedding).
- **Revisit when**: Need fully offline indexing → use local embeddings. Need stronger retrieval quality on domain docs → evaluate alternative embedding models and re-index.

## D3 — Chroma as the vector store + session-scoped filtering
- **Decision**: Use Chroma with metadata filtering by `session_id` to prevent cross-session leakage.
- **Alternatives**: Qdrant (production-grade); Pinecone (managed); FAISS (fast but weaker filtering/metadata story).
- **Rationale**: Chroma is easy to run locally and in a single-container demo; filtering by `session_id` gives privacy isolation without implementing auth.
- **Trade-offs**: Not ideal for multi-tenant scale. On Render Free (no persistent disks), storage is ephemeral.
- **Revisit when**: Multi-user production deployment → move sessions + index to durable storage and adopt a production vector DB (Qdrant/managed).

## D4 — Hybrid retrieval without relying on LangChain “ensemble” APIs
- **Decision**: Implement hybrid retrieval as “top-\(k\) BM25 + top-\(k\) vector” + de-duplication, instead of depending on a specific `EnsembleRetriever` import path.
- **Alternatives**: Vector-only similarity; LangChain ensemble retriever; HyDE; re-ranking-only approaches.
- **Rationale**: Hybrid retrieval improves recall on project artifacts (risk IDs like `R-07`, vendor names, acronyms). The custom merge keeps the prototype resilient to LangChain module layout/version churn encountered during development.
- **Trade-offs**: The merge strategy is simpler than a learned ranker; BM25 is in-memory per session (not durable).
- **Revisit when**: If precision becomes an issue → add reranking (cross-encoder) or adopt a production hybrid engine (Elastic/Qdrant sparse+dense).

## D5 — Multi-agent split to support “add a new agent live”
- **Decision**: Keep clear boundaries: Router → Document Q&A Agent → Data Analysis Agent.
- **Alternatives**: Single monolithic agent; tool/function-calling without explicit agent classes.
- **Rationale**: The interview explicitly expects adding a new agent live. A registry-based design means adding a new agent is mostly “new file + register + router update”.
- **Trade-offs**: Added orchestration complexity; routing errors possible (handled with heuristic fallback).
- **Revisit when**: As the agent set grows → add confidence thresholds, multi-route execution, and better evaluation-driven routing.

## D6 — Tabular analysis: deterministic aggregates first, “table-RAG” fallback second
- **Decision**: For common finance questions, compute totals (budget/actual/forecast/variance) from uploaded tables when columns can be recognized; otherwise answer using retrieval over table previews with citations.
- **Alternatives**: “code interpreter” agent that executes generated pandas code; full SQL ingestion + query planner; BI semantic layer.
- **Rationale**: Deterministic computation avoids unsafe arbitrary code execution and produces stable results. The fallback still demonstrates RAG behavior when table semantics are messy.
- **Trade-offs**: Limited flexibility for arbitrary analytics; heuristics for column detection can miss edge cases.
- **Revisit when**: Need broader analytics → introduce a sandboxed execution environment or translate queries to SQL with strict allowlists.

## D7 — Deployment simplicity: single container serves UI + API
- **Decision**: Build the React app in Docker and serve it from the FastAPI container (UI at `/`, API at `/api/*`).
- **Alternatives**: Separate Vercel frontend + API backend; two services (frontend + backend) on the same platform; CDN + API.
- **Rationale**: Lowest operational complexity for a take-home; fewer moving parts; easiest to demo.
- **Trade-offs**: Less flexible scaling (UI and API scale together); caching/CDN optimizations are limited.
- **Revisit when**: Real user traffic → split UI to CDN/Vercel and scale API independently.

## D8 — Observability + debuggability: `x-trace-id` + structured logs + user-facing error details
- **Decision**: Attach `x-trace-id` per request, log structured JSON events (agent start/end, upload failures), and return actionable error messages from `/api/upload` instead of silent 500s.
- **Alternatives**: LangSmith; Arize Phoenix; full OpenTelemetry tracing.
- **Rationale**: Interview expects tracing a request + diagnosing failures. The trace id and explicit errors made cloud debugging (Render) practical.
- **Trade-offs**: No trace UI; logs-only observability.
- **Revisit when**: Production → OpenTelemetry spans + a trace backend; add log redaction and PII policies.

## D9 — “Degraded but honest” behavior when the LLM is unavailable
- **Decision**: If the LLM call fails, return a response containing the underlying provider error and the most relevant retrieved excerpts with citations.
- **Alternatives**: Hard fail; retry loops; queue requests; return “try again later” only.
- **Rationale**: Prevents broken demos and supports debugging. Also reduces hallucination risk (it never invents an answer without a model).
- **Trade-offs**: User experience is worse than a successful answer; still requires the user to read excerpts.
- **Revisit when**: Add retries/backoff, fallback to a secondary provider, and better partial-answer strategies.

