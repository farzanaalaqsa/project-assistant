# Project Intelligence Assistant — Architecture

## System overview
This system ingests **messy project documents (PDF)** and **tabular data (CSV/Excel)**, then answers user questions via a **multi-agent RAG** backend (Python + LangChain) exposed through a **REST API**, with a **React** UI. It supports **follow-up questions** by preserving conversation state per `session_id`.

### High-level diagram

```mermaid
flowchart LR
  U[User (React UI)] -->|Upload PDF/CSV/XLSX| API[FastAPI Backend]
  U -->|Chat question + session_id| API

  subgraph Ingestion
    API --> LDR[Loaders: PyPDF / pandas]
    LDR --> SPLIT[Chunking: RecursiveCharacterTextSplitter]
    SPLIT --> EMB[Embeddings: local Sentence-Transformers]
    EMB --> VDB[(Chroma Vector DB)]
    SPLIT --> BM25[(In-memory BM25 index per session)]
    LDR --> TAB[(In-memory TabularStore per session)]
  end

  subgraph Orchestration
    API --> ROUTER[Router Agent]
    ROUTER --> DOC[Document Q&A Agent]
    ROUTER --> DATA[Data Analysis Agent]
    DOC --> RET[Hybrid Retrieval: BM25 + Vector]
    DATA --> RET
    RET --> LLM[LLM (Ollama or OpenAI-compatible)]
    DOC -->|Answer + citations| API
    DATA -->|Answer + citations| API
  end

  API --> OBS[Structured JSON Logs (trace_id)]
```

## Technology selection (and trade-offs)

### Backend framework: FastAPI
- **Chosen**: FastAPI for simple REST endpoints (`/api/upload`, `/api/chat`) and async support.
- **Alternatives**: Flask, Django.
- **Trade-offs**: FastAPI is lightweight and fast for a prototype; Django would help if we needed auth/admin quickly.

### Orchestration: LangChain
- **Chosen**: Required by assessment; used for LLM calls, document types, retrievers, and prompts.
- **Alternatives**: LlamaIndex, custom orchestration.
- **Trade-offs**: LangChain gives composable building blocks; you must be careful about version churn.

### Vector DB: Chroma (local persistence)
- **Chosen**: Chroma for local-first persistence and straightforward metadata filtering by `session_id`.
- **Alternatives**: FAISS (no metadata filtering), Qdrant (great for production), Pinecone (managed).
- **Trade-offs**: Chroma is ideal for a take-home demo; for production/multi-tenant, Qdrant or a managed service would be preferred.

### Embeddings: Sentence-Transformers (local)
- **Chosen**: `all-MiniLM-L6-v2` via `HuggingFaceEmbeddings` to keep the system runnable without API keys.
- **Alternatives**: OpenAI embeddings, Cohere, Voyage.
- **Trade-offs**: Local embeddings are cheaper and simpler for a demo, but may underperform domain-tuned/large embeddings.

### LLM: pluggable (Ollama or OpenAI-compatible)
- **Chosen**: Provider switch via env (`LLM_PROVIDER=ollama|openai_compat`) so the same app can run locally or on a hosted API.
- **Alternatives**: Gemini direct integration.
- **Trade-offs**: This keeps deployment flexible; on-prem/no-external-API constraints become feasible by switching to Ollama.

## Data pipeline design

### Ingestion
- **PDF**: `PyPDFLoader` extracts per-page text with metadata (`filename`, `page`, `session_id`).
- **CSV/XLSX**: `pandas` loads tables; tables are converted to a readable markdown preview Document (for citation) and also stored as DataFrames for numeric aggregation.

### Chunking strategy
- **Splitter**: `RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)`.
- **Why**: Project documents often tie numbers to surrounding narrative (assumptions, dates). A ~900 char chunk preserves enough context for “what changed and why” questions, while overlap reduces boundary losses.

### Indexing
- **Dense**: Chroma stores embedded chunks with `session_id` for retrieval filtering.
- **Sparse**: BM25 index is maintained per session in-memory for hybrid retrieval.

## Retrieval beyond naive similarity search
The system uses **hybrid retrieval**:
- **BM25** to catch exact-match terms (risk IDs like `R-07`, vendor names, acronyms).
- **Vector similarity** for semantic matching.
Results are combined using LangChain’s `EnsembleRetriever`.

Optional: **Cross-encoder reranking** can be enabled (`ENABLE_RERANK=true`) to improve precision on long-context queries at extra latency.

## Agent orchestration

### Agents
- **Router Agent**: classifies a user query into `document_qa` vs `data_analysis`.
- **Document Q&A Agent**: retrieves document chunks and generates a grounded answer with citations.
- **Data Analysis Agent**: computes numeric aggregates when possible (budget/actual/forecast/variance), otherwise falls back to table-RAG.

### Routing
- Default is LLM-based JSON routing; it falls back to heuristics if the LLM is unavailable.

### Failures and fallbacks
- If ingestion fails for an unsupported file type, upload returns a 4xx/5xx and logs the error.
- If routing fails, heuristic routing triggers (ensures the request still completes).
- If data analysis cannot find usable numeric columns, the agent falls back to retrieval-only responses with citations.

## Scalability, cost, and production readiness

### Rough cost-per-query (order of magnitude)
Varies by provider:
- **Ollama local**: ~$0 API cost, but compute-bound (latency + CPU/GPU).
- **Hosted LLM (OpenAI-compatible)**: cost dominated by prompt size. Key drivers are number of retrieved chunks and chunk length.

### Top bottlenecks + mitigations
- **LLM latency**: cache retrieval results; reduce context size via reranking; use smaller model for routing.
- **Embedding/indexing time on upload**: batch embedding; background ingestion job queue (Celery/RQ); incremental updates.
- **In-memory session stores (BM25 + DataFrames)**: move to Redis/Postgres for sessions; persist BM25 or replace with production hybrid search in Qdrant/Elastic.

### Observability
- Structured JSON logs include `trace_id`, `session_id`, agent name, and latency.
- Next step: add distributed tracing headers and per-agent spans.

### Security considerations (prototype → production)
- **Prompt injection**: enforce “context-only” instruction, limit tool execution (no arbitrary code), and sanitize citations.
- **API keys**: stored only in environment variables (never returned to users).
- **Data privacy**: session-scoped retrieval filter prevents cross-session leakage; for production add auth + per-tenant storage isolation.

## Adapting to “on-prem, no external API calls”
- Set `LLM_PROVIDER=ollama` and run a local model.
- Keep local embeddings (already default).
- Replace Chroma with an on-prem store if needed (Qdrant local), or keep Chroma for a single-node deployment.

