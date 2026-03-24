# Extract — Mining Intelligence Platform

## What This Is
A full-stack desktop application for mining project technical analysis. It ingests
source documents (PDFs, Excel models, CAD files, images, Word docs), runs them through
an LLM pipeline, and produces structured consulting-style reports (PEA/PFS/FS style).
Built for internal research use at a mining consulting firm. Never investment advice.

## Repository
https://github.com/jopagaro/extract

## Platform Root
/Users/johnpaulroche/coding projects/extract/

## Project Data (lives outside platform)
~/Documents/Extract Projects/   (configurable via MINING_PROJECTS_ROOT env var)

---

## Architecture

```
extract/
  engine/          Python core — LLM routing, document parsing, economic models
  api/             FastAPI layer — routers (projects, ingest, analyze, reports, export, settings, activate)
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
- **Market data:** yfinance (live commodity prices + macro indicators)
- **Web search:** gpt-4o-search-preview (real-time market intelligence)
- **Frontend:** React 18, TypeScript, React Router, Vite
- **Desktop shell:** Tauri 1.6 (Rust), spawns uvicorn as sidecar process
- **PDF export:** fpdf2

## How to Run (3 terminals)
```bash
# Terminal 1 — Python API
cd "/Users/johnpaulroche/coding projects/extract"
source .venv/bin/activate
MINING_PROJECTS_ROOT="$HOME/Documents/Extract Projects" \
EXTRACT_DATA_DIR="$HOME/Library/Application Support/com.extract.app" \
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
3. Gather market intelligence — live prices via yfinance + web search via gpt-4o-search-preview → `02_market_intelligence.json`
4. Extract economic assumptions + mine plan inputs in parallel → fed into DCF model
5. Run DCF model (non-fatal fallback if insufficient data) → `06_dcf_model.json`
6. In parallel: `write_geology_section`, `write_economics_section`, `write_risk_section` → `03–05_*.json`
7. `assemble_report_sections` — narrative synthesis → `07_assembly.json`
8. Save `00_data_sources.json` with source file list and AI notice

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
  extraction/      extract_project_facts, extract_economic_assumptions, extract_mine_plan_inputs
  reporting/       write_geology_section, write_economics_section,
                   write_risk_section, assemble_report_sections
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
DELETE /projects/{id}/runs/{run_id}
GET    /projects/{id}/reports/{run_id}
GET    /projects/{id}/reports/{run_id}/export?format=pdf|md|json|txt
GET    /settings
POST   /settings
POST   /activate
```

---

## Key Preferences / Rules
- Never add co-author lines to git commits — commits are the user's own
- No arbitrary level/score ratings in AI output
- Report viewer renders prose as flowing paragraphs, not key:value dumps
- Sidebar shows a project tree with expandable file lists
- PDF export uses fpdf2 with Latin-1 safe text; prose renders without bold labels
- All text passed to fpdf2 must go through `_safe()` to handle unicode

---

## What's Working
- Full upload → analyze → report → export pipeline
- PDF, Excel, Word, image, DXF document ingestion
- Real-time market intelligence: live commodity prices (yfinance) + web search (gpt-4o-search-preview)
- DCF economic model with sensitivity analysis
- React web UI with project management, file upload, live run polling
- Report viewer with clean prose rendering and 6-step progress pills
- Export to PDF, Markdown, JSON, TXT
- Tauri desktop shell (builds and runs, spawns/kills uvicorn)
- API key settings UI + activation/license gate
- PyInstaller sidecar bundle (dist/api-server/) for Tauri packaging

## What's Not Yet Built (next priorities)
- Scoring pipeline (score_geology, score_economics etc.) — prompts and stubs exist
- Critique/contradiction checker — prompts exist, not wired in
- Proper .app bundle with icon and DMG for distribution
- Anthropic API key support (currently OpenAI only in market intelligence)
