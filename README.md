# Kingly

AI agent app: generate business logic, PRD, and build prompts from an app description. React frontend, Python FastAPI + Google ADK backend, Supabase (auth, Postgres + pgvector, storage).

## Setup

## Deploy (Render.com — single Web Service)

You can deploy Kingly as **one Render Web Service** by serving the built frontend from FastAPI.

- **Root Directory**: `kingly`
- **Build Command**:

```bash
./render-build.sh
```

- **Start Command**:

```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

- **Environment variables** (Render → Environment): set the same backend vars you use locally (`GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, optional `SUPABASE_JWT_SECRET`, etc.).\n

### 1. Supabase

- Create a project at [supabase.com](https://supabase.com).
- In SQL Editor, run the migration: `supabase/migrations/001_initial_schema.sql`.
- In Storage, create a bucket named `project-uploads` (private; RLS as needed).
- In Project Settings > API: copy **URL**, **anon key**, **service_role key**, and **JWT Secret**.

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env: GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Edit .env: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173. Register, create a project, add an app description, and use the buttons to generate business logic, PRD, prompts, or download all as a zip.

## Env vars

- **Backend** (`.env`): `GOOGLE_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`; optional `MODEL`, `YOCO_SECRET_KEY`.
- **Frontend** (`.env`): `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` (e.g. `http://localhost:8000`).

## Features

- **Auth**: Login/register via Supabase Auth.
- **Projects**: Create, list, update, delete projects.
- **Documents**: Generated markdown (business logic, PRD, prompts) and uploads (PDF, DOCX, MD). View in app.
- **Agents**: Generate business logic, PRD, or 3–5 build prompts; or generate all and download zip.
- **Uploads**: Multi-modal PDF/DOCX/Markdown upload per project; text extracted and stored.
- **pgvector**: Schema and RPC for document embeddings; use for RAG in agents when embeddings are populated.
