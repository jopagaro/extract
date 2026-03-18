# Mining Intelligence Platform — Project Context

## What This Is
A full-stack desktop application for mining project technical analysis. It ingests
source documents (PDFs, Excel models, CAD files, images, Word docs), runs them through
an LLM pipeline, and produces structured consulting-style reports (PEA/PFS/FS style).
Built for internal research use at a mining consulting firm. Never investment advice.

## Repository
https://github.com/jopagaro/mining-intelligence-engine

## Platform Root
/Users/johnpaulroche/Desktop/mining_intelligence_platform/

## Project Data (lives outside platform)
~/Desktop/mining_projects/   (configurable via MINING_PROJECTS_ROOT env var)

---

## Architecture

```
mining_intelligence_platform/
  engine/          Python core — LLM routing, document parsing, economic models
  api/             FastAPI layer — 5 routers (projects, ingest, analyze, reports, export)
  web/             React + TypeScript UI (Vite)
  desktop/         Tauri native shell (wraps web UI, spawns Python sidecar)
  prompts/         LLM prompts — system/, extraction/, reporting/, scoring/, critique/
  schemas/         JSON schemas for all data types
  configs/         YAML configs for LLM routing, economics, fiscal regimes
  _project_template/  Canonical per-project folder layout (copied on project create)
```

## Tech Stack
- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic, Polars
- **LLM:** OpenAI API (primary) + Anthropic API (fallback/dual-run)
- **Document parsing:** pymupdf (PDF), openpyxl (Excel), python-docx (Word),
  ezdxf + matplotlib (CAD/DXF), vision API (images)
- **Frontend:** React 18, TypeScript, React Router, Vite
- **Desktop shell:** Tauri 1.6 (Rust), spawns uvicorn as sidecar process
- **PDF export:** fpdf2

## How to Run (3 terminals)
```bash
# Terminal 1 — Python API
cd /Users/johnpaulroche/Desktop/mining_intelligence_platform
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Terminal 2 — React frontend
cd web && pnpm dev

# Terminal 3 — Tauri desktop (optional, for native app)
pnpm --filter desktop dev
```

---

## Analysis Pipeline (api/routers/analyze.py)

1. Load all files from `raw/documents/` using `engine/core/document_loader.py`
2. `extract_project_facts` — dual LLM run (both providers), reconciled → `01_project_facts.json`
3. In parallel: `write_executive_summary`, `write_geology_section`,
   `write_economics_section`, `write_risk_section` → `02–05_*.json`
4. Save `00_data_sources.json` with source file list and AI notice

## Document Loader (engine/core/document_loader.py)
Handles all formats via `load_document(path)`:
- `.txt / .md / .csv` — plain text read
- `.pdf` — pymupdf page-by-page text
- `.xlsx / .xls` — openpyxl sheet tables
- `.docx` — python-docx paragraphs + tables
- `.png / .jpg / .tiff` — vision API (Anthropic or OpenAI GPT-4o)
- `.dxf / .dwg` — ezdxf structured extraction + matplotlib render → vision

---

## Prompt Architecture
```
prompts/
  system/          Role identity prompts (base_system, report_writer, data_extractor, etc.)
  extraction/      extract_project_facts (dual-LLM)
  reporting/       write_executive_summary, write_geology_section,
                   write_economics_section, write_risk_section
  summarization/   Stubs — not yet wired into active pipeline
  scoring/         Stubs — not yet wired into active pipeline
  critique/        Stubs — not yet wired into active pipeline
```

Key rules baked into all prompts:
- Never use numbered level ratings (Level 2, Score 3/5) — describe in plain language
- No investment advice language
- Flag missing data explicitly rather than inferring

---

## API Endpoints
```
GET    /health
GET    /projects
POST   /projects
GET    /projects/{id}
DELETE /projects/{id}
POST   /projects/{id}/files           (multipart upload)
GET    /projects/{id}/files
DELETE /projects/{id}/files/{filename}
POST   /projects/{id}/analyze         (starts background thread)
GET    /projects/{id}/runs
GET    /projects/{id}/runs/{run_id}
GET    /projects/{id}/reports/{run_id}
GET    /projects/{id}/reports/{run_id}/export?format=pdf|md|json|txt
```

---

## Key Preferences / Rules
- Never add co-author lines to git commits — commits are the user's own
- No arbitrary level/score ratings in AI output
- Report viewer renders prose as flowing paragraphs, not key:value dumps
- Sidebar shows a project tree with expandable file lists
- PDF export uses fpdf2 with Latin-1 safe text; prose renders without bold labels

---

## What's Working
- Full upload → analyze → report → export pipeline
- PDF, Excel, Word, image, DXF document ingestion
- React web UI with project management, file upload, live run polling
- Report viewer with clean prose rendering
- Export to PDF, Markdown, JSON, TXT
- Tauri desktop shell (builds and runs, spawns/kills uvicorn)

## What's Not Yet Built (next priorities)
- Economic models (DCF, NPV, IRR, sensitivity) — stubs exist in engine/models/
- Scoring pipeline (score_geology, score_economics etc.) — prompts and stubs exist
- Critique/contradiction checker — prompts exist, not wired in
- Proper .app bundle with icon for distribution
- Anthropic API key (currently OpenAI only)
