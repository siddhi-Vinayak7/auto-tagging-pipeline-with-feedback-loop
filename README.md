# Auto-Tagging Pipeline with Feedback Loop

An end-to-end topic tag suggestion service powered by FastAPI, PostgreSQL (Supabase), Groq (`llama-3.3-70b-versatile`), and React (Vite + Tailwind CSS).

The system classifies post titles and bodies into a fixed taxonomy, allows human reviewers to accept or refine tag suggestions, stores precomputed feedback metrics, and tracks model performance over time.

---

## Live Deployments

- **Frontend Application (Vercel)**: [https://auto-tagging-pipeline-with-feedback.vercel.app](https://auto-tagging-pipeline-with-feedback.vercel.app)
- **Backend Service (Render)**: [https://auto-tagging-pipeline-with-feedback-loop.onrender.com](https://auto-tagging-pipeline-with-feedback-loop.onrender.com)
- **Interactive OpenAPI Docs**: [https://auto-tagging-pipeline-with-feedback-loop.onrender.com/docs](https://auto-tagging-pipeline-with-feedback-loop.onrender.com/docs)

> **Note on Render Free-Tier Cold Starts**: The backend is deployed on Render's free Web Service tier. After periods of inactivity, the instance spins down to conserve resources. The first request may experience a **30–60 second cold-start delay** while the server boots. Subsequent requests are immediate.

---

## Fixed Tag Taxonomy

The LLM is explicitly constrained to assign between 1 and 3 tags exclusively from this fixed 8-item taxonomy:
- `AI/ML`
- `Frontend`
- `Backend`
- `Product`
- `Design`
- `Career`
- `Funding`
- `General`

---

## API Endpoints

### 1. `POST /api/suggest-tags`
- **Request**: `{ "title": "string", "body": "string" }`
- **Response**: `{ "post_id": "uuid", "suggestion_id": "uuid", "suggested_tags": ["string"], "was_fallback": bool }`
- **Behavior**: Creates a `posts` row, calls Groq LLM, validates output against the fixed taxonomy (capping at 3 tags), and persists a `model_suggestions` row.

### 2. `POST /api/confirm-tags`
- **Request**: `{ "suggestion_id": "uuid", "final_tags": ["string"] }`
- **Response**: `{ "correction_id": "uuid", "was_correct": bool, "tags_added": ["string"], "tags_removed": ["string"] }`
- **Behavior**: Validates taxonomy compliance and enforces a UNIQUE constraint on `suggestion_id` (returns HTTP 409 Conflict on duplicates). Precomputes `was_correct`, `tags_added`, and `tags_removed` at write time.

### 3. `GET /api/metrics`
- **Response**: `{ "total_suggestions": int, "total_corrections": int, "agreement_rate": float, "per_tag_stats": {...}, "top_tags_added": [...], "top_tags_removed": [...], "daily_trend": [...] }`
- **Behavior**: Aggregates real database counts across all suggestions and human corrections, including chronological daily agreement trend data (`daily_trend`).

---

## Local Development Setup

### Backend (Python 3.12 + FastAPI + SQLAlchemy)
1. Navigate to `backend/`
2. Create python environment and install requirements:
   ```bash
   pip install -r requirements.txt
   ```
3. Create `backend/.env` based on `backend/.env.example`:
   ```ini
   DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/<dbname>
   GROQ_API_KEY=gsk_...
   ```
4. Run Alembic migrations:
   ```bash
   python -m alembic upgrade head
   ```
5. Start Uvicorn server:
   ```bash
   python -m uvicorn main:app --host 127.0.0.1 --port 8000
   ```

### Frontend (React + Vite + Tailwind CSS)
1. Navigate to `frontend/`
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start Vite dev server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:5173](http://localhost:5173) in your browser.
