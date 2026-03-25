# AI-Powered Project Intelligence Assistant (Take-Home)

Backend: **Python + FastAPI + LangChain**  
Frontend: **React (Vite)**  
Core features: **multi-agent RAG**, **hybrid retrieval**, **file upload (PDF/CSV/XLSX)**, **source citations**, **conversation sessions**, **RAGAS evaluation**, **Docker**

## Live demo
- **App URL**: _TODO: add deployed URL_
- **Screen recording (3–5 min)**: _TODO: add link_

## Quickstart (local dev)

### 1) Generate synthetic sample data

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
# Optional (only if you do NOT set OPENAI_API_KEY for embeddings)
pip install -r backend\requirements-local.txt
python scripts\generate_sample_data.py
```

This creates realistic-but-synthetic messy documents in `sample_data/`:
- 2× status report PDFs
- 1× risk workshop PDF
- 1× financial summary Excel
- 1× risk register CSV

### 2) Run the backend (FastAPI)

```bash
set APP_ENV=dev
set LLM_PROVIDER=ollama
python -m uvicorn backend.app.main:app --reload --port 8000
```

Backend will be at `http://localhost:8000`.

### 3) Run the frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Frontend will be at `http://localhost:5173` and talks to `http://localhost:8000`.

## Usage
1. Open the UI.
2. Upload files (PDF/CSV/XLSX). Upload/indexing is scoped to the current `session_id`.
3. Ask questions. The response shows:
   - **which agent** handled the query (`document_qa` or `data_analysis`)
   - **citations** with source ids and excerpts

## API
- `POST /api/upload` (multipart form-data `files=...`, optional query `session_id=...`)
- `POST /api/chat` JSON `{ "message": "...", "session_id": "..." }`
- `GET /api/health`

## Configuration
Copy `backend/.env.example` to `backend/.env` and adjust as needed.

### LLM providers
- **Ollama (local)**:
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_MODEL=llama3.1`
- **Gemini (Google AI Studio)**:
  - `LLM_PROVIDER=gemini`
  - set `GEMINI_API_KEY`, `GEMINI_MODEL`
- **OpenAI-compatible (Groq/OpenRouter/etc)**:
  - `LLM_PROVIDER=openai_compat`
  - set `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`

### Embeddings
- If `GEMINI_API_KEY` is set, the backend will use Gemini embeddings (default: `gemini-embedding-001`).
- Else if `OPENAI_API_KEY` is set, the backend will use lightweight hosted embeddings (`text-embedding-3-small`).
- Otherwise, install local embeddings with:

```bash
pip install -r backend\requirements-local.txt
```

## RAGAS evaluation
After generating sample data, run:

```bash
pip install -r evaluation\requirements.txt
python evaluation\run_ragas.py
```

This will write `evaluation/ragas_results.csv` and print a markdown table of scores. The query set is in `evaluation/queries.jsonl` (8 queries across easy/medium/hard/adversarial).

## Docker (single-container: backend + built frontend)

```bash
docker build -t project-assistant .
docker run -p 8000:8000 --env-file backend/.env project-assistant
```

Then open `http://localhost:8000` (frontend is served by the backend container).

## Minimal deployment (Render, Docker, single service)

This repo is set up so **one container** serves:
- the **FastAPI API** at `/api/*`
- the **built React UI** at `/`

### Steps
1. Push this repo to GitHub.
2. In Render, create a **New → Web Service** and connect the repo.
3. Set:
   - **Runtime**: Docker
   - **Plan**: Free (or any)
   - **Health check path**: `/api/health`
4. Add a **Persistent Disk** (recommended so Chroma + uploads survive deploys):
   - **Mount path**: `/app/backend/storage`
   - **Size**: 1 GB
5. Add these **Environment Variables** (Render “Environment” tab):
   - `APP_ENV=prod`
   - `LOG_LEVEL=INFO`
   - `CORS_ORIGINS=https://project-assistant-lk5w.onrender.com`
   - `LLM_PROVIDER=gemini`
   - `GEMINI_API_KEY=<>`
   - `GEMINI_MODEL=gemini-2.5-flash` (pick from https://ai.google.dev/gemini-api/docs/models)
   - `GEMINI_EMBED_MODEL=gemini-embedding-001`
   - `STORAGE_DIR=/tmp/storage` (Render Free has no persistent disk; this avoids permission issues)
6. Deploy. When it’s live:
   - UI: `https://<your-render-service>.onrender.com/`
   - API health: `https://<your-render-service>.onrender.com/api/health`

### Notes
- For hosted deployments, **use `LLM_PROVIDER=gemini` or `LLM_PROVIDER=openai_compat`** (Ollama typically isn’t available on free-tier web runtimes).
- The backend stores Chroma + uploads under `backend/storage`. Without a persistent disk, this data is **ephemeral**.

## Required docs
- `ARCHITECTURE.md`: system design, pipeline, agent orchestration, scale/security notes
- `DECISIONS.md`: decision log with alternatives and trade-offs
