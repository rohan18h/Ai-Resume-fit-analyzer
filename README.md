# AI-Powered Resume Fit Analyzer

A web app that compares a PDF resume with a job description and tells a job seeker, before they apply: their fit
score, which skills they are missing, what to learn (with free links), and whether the resume format will survive ATS
screening.

TY Computer Engineering mini project · Team: [Names] · Guide: [Guide name]

The full specification is in [docs/PROJECT_SPEC.pdf](docs/PROJECT_SPEC.pdf). The architecture diagram is in
[docs/architecture.jpg](docs/architecture.jpg).

## Tech stack

| Layer | Tool |
| --- | --- |
| Frontend | React.js (Vite, JSX), Chart.js |
| Backend | Python 3.11+, FastAPI |
| NLP | pdfplumber, spaCy, NLTK |
| Matching | scikit-learn (TF-IDF), sentence-transformers |
| Database | SQLite |
| Deploy & tools | Render, Vercel, Git + GitHub |

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer (with npm)

## Run the backend

PowerShell (Windows):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

macOS / Linux: same steps, but activate with `source .venv/bin/activate`.

Installing the CPU-only PyTorch build first keeps the download much smaller (no GPU is needed).

Check it works: open http://localhost:8000/api/health. You should see
`{"status":"ok","model_loaded":false,"version":"1.0.0"}`. Interactive API docs are at http://localhost:8000/docs.

Run the tests (from `backend/`, with the venv active):

```powershell
pytest
```

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Analyzer page shows "Connected" when it can reach the backend.

The frontend reads the backend URL from `VITE_API_BASE_URL` (default `http://localhost:8000`). To change it, copy
`frontend/.env.example` to `frontend/.env.local` and edit it.

## Environment variables (backend)

All of these are optional. Defaults are in [backend/app/config.py](backend/app/config.py).

| Name | Default | Meaning |
| --- | --- | --- |
| `MAX_UPLOAD_MB` | 5 | Max PDF size |
| `MAX_PDF_PAGES` | 5 | Reject longer PDFs |
| `MIN_JD_CHARS` / `MAX_JD_CHARS` | 50 / 10000 | Job description length limits |
| `EMBEDDING_MODEL` | sentence-transformers/all-MiniLM-L6-v2 | Embedding model |
| `PRIMARY_METHOD` | embeddings | Main fit score: `tfidf` or `embeddings` |
| `TFIDF_CEILING` | 0.60 | Raw TF-IDF cosine mapped to 100% |
| `EMBED_CEILING` | 0.80 | Same, for embeddings |
| `LABEL_GOOD_MIN` / `LABEL_AVG_MIN` | 65 / 40 | Good / Average / Low fit thresholds |
| `ALLOWED_ORIGINS` | http://localhost:5173 | CORS origins, comma-separated |
| `DB_PATH` | data/app.db | SQLite file (relative to `backend/`) |

## Privacy

Uploaded resumes and job descriptions are processed in memory and never stored or logged. The fit score is an
estimate to help applicants improve; it must not be used to make hiring decisions about people.

## Build progress

Built step by step following Section 17 of the spec.

- [x] Step 0 — Repo scaffold (FastAPI + `/api/health`, Vite + routes + header/footer + design tokens)
- [ ] Step 1 — Parser
- [ ] Step 2 — SQLite schema, skills seed, link checker
- [ ] Step 3 — Skills extraction
- [ ] Step 4 — TF-IDF matcher + `POST /api/analyze` v0
- [ ] Step 5 — Evaluation dataset + `evaluate.py`
- [ ] Step 6 — Embedding matcher + explanations
- [ ] Step 7 — Gap analysis + roadmap
- [ ] Step 8 — ATS checks
- [ ] Step 9 — Analyzer page
- [ ] Step 10 — How it works, Evaluation, About pages
- [ ] Step 11 — Integration, performance, accessibility
- [ ] Step 12 — Deploy
