# 🏥 ClarityGR - AI-Powered Medical Document Processing Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-blue.svg)](https://www.typescriptlang.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7.x-green.svg)](https://www.mongodb.com/)

> AI-powered platform to ingest clinical documents, extract structured medical entities, and generate MDT reports — with a modern React UI, robust security middleware, and MongoDB persistence.

## 🌟 Overview

ClarityGR automates extraction of structured medical entities from clinical documents and supports MDT (Multidisciplinary Team) report generation. It exposes a FastAPI backend, a React (Vite) frontend, and persists data in MongoDB.

### Key Features
- AI-assisted entity extraction workflow (Mistral/OpenAI-compatible via GPT-Open/Ollama; runtime-switchable)
- Universal document intake: PDF, images, text, XML, JSON (base64 or URL)
- OCR and text normalization pipeline (OCR via Mistral OCR client; normalization simplified)
- MDT report generation including SSE live progress
- Progressive rate limiting, strict input validation, and security headers
- React UI with uploads, progress, reports, entity viewing, bilingual support

---

## 🧱 Architecture

High-level components and data flow:

```
+-------------------+       upload/trigger        +------------------+
|       UI (Vite)   |  ─────────────────────────▶ |   FastAPI (app)  |
|  React + TS, 3000 |                              |  src/main.py     |
+---------┬---------+                              +-----┬------------+
          │  API calls (REST/SSE)                        │ include_router
          │                                              │
          │                               +--------------▼-----------------------+
          │                               |             Controllers              |
          │                               | patients/, reports/, settings/, ...  |
          │                               +--------------┬-----------------------+
          │                                              │ calls
          │                               +--------------▼-----------------------+
          │                               |               Services               |
          │                               | OCR, categorization (bypassed),      |
          │                               | data extraction (simplified),        |
          │                               | MDT report generator (NER workflow)  |
          │                               +--------------┬-----------------------+
          │                                              │ persist/query
          │                               +--------------▼-----------------------+
          │                               |            Repositories              |
          │                               | MongoDB collections:                 |
          │                               | documents, reports, generations,     |
          │                               | users, blacklisted_tokens            |
          │                               +--------------┬-----------------------+
          │                                              │ PyMongo
          │                               +--------------▼-----------------------+
          │                               |               MongoDB                |
          │                               | (docker-compose mongodb service)     |
          │                               +--------------------------------------+

Notes:
- Static UI (built) is served by backend at / (Docker build copies to ./static)
- Public UI assets mounted at /assets (src/frontend/public)
- Auth router exists but is NOT mounted by default
```

Project structure (excerpt):

```
poc-aifac-claritygr/
├── Dockerfile
├── docker-compose.yml
├── environment.template
├── generate_env.sh
├── gr_entities_definition.json
├── src/
│   ├── main.py                     # FastAPI app, routers, middleware, exceptions
│   ├── controllers/                # API endpoints (patients, reports, settings, ...)
│   ├── services/                   # OCR, extraction, MDT generator, auth utils
│   ├── repositories/               # Mongo repositories
│   ├── config/                     # env settings, database, NER/LLM config
│   ├── middleware/                 # rate limiter, input validator, auth helpers
│   ├── models/                     # Pydantic models stored in Mongo
│   └── api/schemas/                # Request/response schemas
└── frontend/                       # React app (Vite, Tailwind)
```

---

## ✅ Active Functionality and Toggles

- Auth endpoints exist (`src/controllers/auth_controller.py`) but are NOT mounted in `src/main.py` (commented). Enable with caution in secured environments.
- Document categorization is currently bypassed; normalization uses raw text (see `services/patient_document_service.py`).
- NER runtime configuration is adjustable via `GET/POST /settings/ner-config`.
- LLM provider and model routing is changeable at runtime via `/settings/llm-model` and `/settings/llm-models`.
- Observability (generation logs) and evaluation (SSE) are available.

---

## 🔧 Configuration

Backend settings are defined in `src/config/settings.py` (Pydantic BaseSettings). Create `.env` (or use Docker Compose env). Minimal recommended vars:

```bash
SECRET_KEY=replace-with-32-byte-minimum        # required; 32+ chars
MONGODB_URI=mongodb://localhost:27017/clarityGR
MONGODB_DB=clarityGR
# If using OpenAI-compatible local/OSS endpoints
GPT_OPEN_BASE_URL=http://localhost:8080
# If using Mistral cloud API
MISTRAL_API_KEY=
```

Additional notes:
- CORS: defaults allow localhost dev origins; configure via `ALLOWED_ORIGINS`.
- JWT settings exist but auth router is disabled by default.
- Script to generate a minimal `.env`:

```bash
cd poc-aifac-claritygr
./generate_env.sh
```

---

## 🚀 Run and Deploy

### Option A: Docker (backend + UI + MongoDB)

```bash
cd poc-aifac-claritygr
cp environment.template .env
# Edit .env (SECRET_KEY, GPT_OPEN_BASE_URL, etc.)

docker-compose up -d --build
```

Services:
- Backend: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health
- UI: served by backend at `/` (static) in this image

### Option B: Local development (separate processes)

Backend:
```bash
cd poc-aifac-claritygr
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start MongoDB (Docker suggested)
docker run -d -p 27017:27017 --name mongodb mongo:7

# Run the API
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:
```bash
cd poc-aifac-claritygr/frontend
npm install
npm run dev
# UI at http://localhost:3000 (proxies/targets API at http://localhost:8000)
```

---

## 🔗 API Surface

Base URL: `http://localhost:8000`

### Health and root
- `GET /health`, `HEAD /health`
- `GET /` (links to docs, health)

### Patients & Documents (`src/controllers/patient_document_controller.py`, prefix `/patients`)
- `GET /patients` — list distinct patient IDs in documents/reports
- `POST /patients/{patient_id}/document` — upload document (base64 or URL)
- `GET /patients/{patient_id}/documents` — list documents (pagination)
- `GET /patients/{patient_id}/document/{uuid}` — document details
- `POST /patients/{patient_id}/document/{uuid}/process` — trigger processing
- `GET /patients/{patient_id}/document/{uuid}/ocr` — get OCR text/metadata
- `GET /patients/{patient_id}/documents/by-filename/{filename}` — fetch by filename
- `GET /patients/{patient_id}/document/{document_uuid}/` — normalization results (if present)
- `DELETE /patients/{patient_id}/document/{document_uuid}` — delete document

### Reports (`src/controllers/report_controller.py`, prefix `/patients`)
- `POST /patients/{id}/reports` — create report record (PROCESSING); async generation
- `POST /patients/{id}/reports/stream` — generate with SSE progress
- `POST /patients/{id}/reports/json-filter-check` — preview JSON filter impact
- `GET /patients/{id}/reports` — list reports (pagination)
- `GET /patients/{id}/reports/{report_id}` — get one
- `GET /patients/{id}/reports/statistics` — patient report stats
- `DELETE /patients/{id}/reports/{report_id}` — delete

### Settings & Model Routing (`src/controllers/settings_controller.py`, prefix `/settings`)
- `GET /settings/llm-models` — enabled models + current settings
- `POST /settings/llm-models` — add model (persists in Mongo)
- `PUT /settings/llm-models` — edit existing model (by id+name)
- `POST /settings/llm-model` — switch provider/model; optionally update keys/base URL
- `POST /settings/set-env-var` — set limited env keys (e.g., MISTRAL_API_KEY)
- `POST /settings/gpt-open-url` — set GPT-Open base URL
- `GET /settings/ner-config` — get NER processing config
- `POST /settings/ner-config` — update NER processing config
- `POST /settings/master-delete` — delete all reports/documents (requires phrase "delete all")

### Entity Config (`src/controllers/entity_config_controller.py`)
- `GET /entity-config` — get effective entity config (DB or file)
- `PUT /entity-config` — replace entity config
- `POST /entity-config/reset` — reset from file baseline
- `GET /entity-config/validate` — validate config (duplicates, summary)

### Observability & Evaluation
- `GET /observability/generations` — list generation logs (filters: time range, llm, filenames_hash, patient)
- `GET /observability/generations/filters` — distinct filter values
- `GET /evaluate/pending` — pending generations to evaluate
- `POST /evaluate/stream` — run evaluation with SSE progress

---

## 🧩 Data Models (at a glance)

### PatientDocument (`src/models/patient_document.py`)
Fields include: `uuid`, `patient_id`, `type`, `source`, `status`, `filename`, `file_path`, `file_content (base64)`, timestamps, errors, and processing results:
- Categorization: `document_category`, `document_type`, `categorization_completed_at`
- Structured data extraction: `extracted_data`, `extraction_metadata`, `extraction_status`, `extraction_completed_at`
- OCR: `ocr_text`, `ocr_metadata`, `ocr_completed_at`, `character_count`, `word_count`

### Report (`src/models/report.py`)
Fields: `uuid`, `patient_id`, `status`, `title`, `filename`, `file_type`, `file_size`, `created_at`, `character_count`, `word_count`, optional `author/subject/keywords`, `elements`, `content`, `metadata`.

---

## 🧠 Processing Pipelines

### Upload → Process Document (`services/patient_document_service.py`)
1. Validate input; store base64 or file URL; deduplicate by filename per patient
2. Async processing steps:
   - OCR text extraction (PDF/images via Mistral OCR; text/XML handled directly)
   - Normalization: currently uses raw text as normalized text
   - Categorization: currently bypassed with default values
   - Structured data extraction: simplified text-only service; persists `extracted_data`
   - Status updates to `DONE` with timestamps and counts

### MDT Report Generation (`services/mdt_report_generator.py`)
- Loads entity definitions (DB first, falls back to `gr_entities_definition.json` and seeds DB if missing)
- Retrieves previously processed documents for a patient
- Extracts/filters text (JSON-specific preprocess supported via date or AUTO-RCP)
- Prepares NER inputs (no chunking per-doc for now; full-document chunks)
- Calls `ner_workflow_orchestrator.extract_entities_workflow` and normalizes results
- Adds programmatic entity (e.g., Date de présentation)
- Persists generation logs to `generations` (model, timing, entities found)
- Creates final `Report` (status COMPLETED or FAILED based on content/zero-entities)
- SSE endpoint streams stepwise progress (initializing → retrieving → extracting → NER → creating → saving)

---

## 🤖 LLM Routing and Modes

- Runtime switching via `/settings/llm-model` and `/settings/llm-models`:
  - Providers: `mistral api`, `openai`, `ollama` (via GPT-Open-compatible path)
  - Sets env `LLM_PROVIDER` and `LLM_MODEL`, and updates `GPT_OPEN_BASE_URL` / `OPENAI_API_KEY` / `MISTRAL_API_KEY` as needed
- `config/mistral_config.py` resolves Mistral clients (api/local). Current infra uses `infrastructure.llm.mistral_client` wrapper
- Key requirements enforced in `ReportService._check_llm_api_keys()`:
  - OpenAI endpoints require `OPENAI_API_KEY` only if base URL is `https://api.openai.com`
  - Mistral API mode requires `MISTRAL_API_KEY`

---

## 🔒 Security Posture

- CORS restricted by configured origins
- Progressive rate limiting middleware and general rate limiting
- Comprehensive input validation for SQL/NoSQL/XSS/command/path injections (`middleware/input_validator.py`)
- Security headers middleware (HSTS, X-Frame-Options, X-XSS-Protection, etc.)
- JWT scaffolding (HS256, blacklist support); auth router not mounted by default
- Security event logging utilities available

---

## 🧪 Testing

### Run Sanity Tests Before Push

Before pushing any changes, run the sanity tests to ensure critical functionality works:

```bash
# Option 1: Use the pre-push script
./scripts/pre-push-tests.sh

# Option 2: Run pytest directly
pytest tests/sanity/ -v
```

**Expected Output:**
```
====================== 15 passed in 0.33s ======================
✅ All sanity checks PASSED!
   You can safely push your changes.
```

### Test Categories

| Suite | Description |
|-------|-------------|
| `TestSourceFilterDepth` | Positive/negative/zero depth filtering |
| `TestSourceFilterLIBNATCR` | Report type filtering |
| `TestSourceFilterMultiple` | Multiple filters OR logic |
| `TestCriticalImports` | Core module imports |
| `TestEmptyInputs` | Edge cases |

### Run All Tests

```bash
cd poc-aifac-claritygr

# All tests
pytest tests/ -v

# Integration tests only
pytest tests/integration/ -v

# Sanity tests only
pytest tests/sanity/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Test File Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── sanity/                  # Pre-push sanity checks
│   ├── __init__.py
│   └── test_sanity_checks.py
├── integration/             # API endpoint tests
│   ├── test_api_endpoints.py
│   └── test_patient_document_endpoints.py
└── experiments/             # Exploratory tests
```

---

## 🛠️ Troubleshooting

- Mongo connection/indexes
  - On startup, `create_indexes()` ensures indexes for `users`, `documents`, `reports`, `generations`.
  - Use `MONGODB_URI` reachable from the running app/container. In docker-compose, the app uses `mongodb` host.
- Missing API keys / wrong provider
  - If provider is OpenAI and base URL is OpenAI, set `OPENAI_API_KEY`.
  - For Mistral API mode, set `MISTRAL_API_KEY`.
  - For local GPT-Open/Ollama endpoints, ensure `GPT_OPEN_BASE_URL` is reachable (e.g., `host.docker.internal`).
- 429 rate limits
  - General/API limits enforced in middleware; respect `Retry-After` headers. Consider increasing limits for dev only.
- OCR/model initialization warnings
  - OCR initializes lazily; startup warm-up tries to initialize processors and may log warnings if LLM not reachable.
- CORS or UI/API URL mismatch
  - Update `ALLOWED_ORIGINS` and UI base URL (Settings panel or `VITE_API_BASE_URL`).
- Health check
  - `GET /health` should return `{ status: "healthy" }`.
- Master delete
  - `POST /settings/master-delete` with body `{ "phrase": "delete all" }` to wipe `reports` and `documents` (irreversible).

---

## 📄 License

This project is licensed under the MIT License with Additional Terms. See the root `LICENSE` file.

- The Additional Terms grant MongoDB Inc. the right to use, modify, and distribute any components marked as "common" or "shared" in separate projects, regardless of modifications made by the licensee.
- The Named Entity Recognition (NER) component is the main "common/shared" component. This includes:
  - `src/services/entity_extraction_service.py`
  - `src/services/entity_extraction_service_old.py`
  - `src/services/entity_extraction_service_19thAug.py`
  - `src/services/ner_workflow_orchestrator.py`
  - `src/entity_extraction/` (directory)

---

Last updated: 2026-01-20

