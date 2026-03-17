"""
create_structure.py

Run once to scaffold the full mining_intelligence_platform directory tree.
Creates all folders and seeds stub files. Safe to re-run — never overwrites
existing files that already have content.

Usage:
    python scripts/create_structure.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Stub content generators
# ---------------------------------------------------------------------------

def py_stub(title: str) -> str:
    return f'"""{title}\n\nStub — to be implemented.\n"""\n'


def md_stub(title: str) -> str:
    return f"# {title}\n\n> Stub — to be filled in.\n"


def yaml_stub(title: str) -> str:
    return f"# {title}\n# Stub — to be filled in.\n"


def json_schema_stub(title: str) -> str:
    return json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "description": "Stub — to be defined.",
        "type": "object",
        "properties": {}
    }, indent=2) + "\n"


def empty() -> str:
    return ""


# ---------------------------------------------------------------------------
# File writer — never overwrites non-empty files
# ---------------------------------------------------------------------------

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return
    path.write_text(content, encoding="utf-8")


def touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()


# ---------------------------------------------------------------------------
# Root-level files
# ---------------------------------------------------------------------------

def root_files() -> None:
    write(ROOT / "README.md", "# Mining Intelligence Platform\n\n> Stub — to be filled in.\n")
    write(ROOT / "LICENSE", "MIT License\n\nCopyright (c) 2026\n")
    write(ROOT / ".gitignore", "\n".join([
        ".env", "__pycache__/", "*.pyc", "*.pyo", ".venv/", "venv/",
        "node_modules/", ".DS_Store", "dist/", "build/", "*.egg-info/",
        ".ruff_cache/", ".mypy_cache/", ".pytest_cache/",
        "projects/", "*.parquet", "*.db",
    ]) + "\n")
    write(ROOT / ".env.example", "\n".join([
        "# Copy to .env and fill in values",
        "",
        "# LLM APIs",
        "OPENAI_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "",
        "# Paths",
        "MINING_PROJECTS_ROOT=../mining_projects",
        "MINING_ENGINE_ROOT=.",
        "",
        "# API",
        "API_HOST=127.0.0.1",
        "API_PORT=8000",
        "",
        "# Environment",
        "ENV=development",
        "LOG_LEVEL=INFO",
    ]) + "\n")
    write(ROOT / "pyproject.toml", """\
[build-system]
requires = ["setuptools>=72", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "mining-intelligence-platform"
version = "0.1.0"
description = "Mining Project Economic Analysis Engine"
requires-python = ">=3.12"
dependencies = [
    "typer>=0.12",
    "rich>=13",
    "polars>=0.20",
    "pyarrow>=15",
    "pydantic>=2.6",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "python-dotenv>=1.0",
    "openai>=1.30",
    "anthropic>=0.28",
    "tiktoken>=0.7",
    "httpx>=0.27",
    "pyyaml>=6",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "mypy>=1.10",
    "httpx>=0.27",
]

[project.scripts]
mip = "engine.cli.main:app"

[tool.setuptools.packages.find]
where = ["."]
include = ["engine*", "api*"]

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
""")
    write(ROOT / "package.json", json.dumps({
        "name": "mining-intelligence-platform",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "pnpm --filter web dev",
            "build": "pnpm --filter web build",
            "desktop": "pnpm --filter desktop tauri dev"
        }
    }, indent=2) + "\n")
    write(ROOT / "pnpm-workspace.yaml", "packages:\n  - 'web'\n  - 'desktop'\n")
    write(ROOT / "Makefile", """\
.PHONY: install dev api web desktop test lint

install:
\tpip install -e ".[dev]"
\tpnpm install

dev:
\tuvicorn api.main:app --reload --host 127.0.0.1 --port 8000

api:
\tuvicorn api.main:app --host 127.0.0.1 --port 8000

web:
\tpnpm --filter web dev

desktop:
\tpnpm --filter desktop tauri dev

test:
\tpytest

lint:
\truff check . && mypy engine/ api/
""")
    write(ROOT / "docker-compose.yml", """\
version: "3.9"
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ../mining_projects:/projects
""")
    write(ROOT / "project_architecture.md", md_stub("Project Architecture"))


# ---------------------------------------------------------------------------
# docs/
# ---------------------------------------------------------------------------

def docs() -> None:
    d = ROOT / "docs"
    for name in [
        "system_overview", "data_model", "geology_pipeline",
        "economics_pipeline", "cad_pipeline", "reporting_pipeline",
        "review_workflow", "evaluation_framework", "desktop_app_plan",
        "naming_conventions", "folder_conventions",
        "units_and_coordinate_systems", "security_and_access",
    ]:
        write(d / f"{name}.md", md_stub(name.replace("_", " ").title()))

    rb = d / "runbook"
    for name in [
        "ingest_new_project", "rerun_pipeline", "override_bad_extraction",
        "review_geology", "review_economics", "export_client_report",
    ]:
        write(rb / f"{name}.md", md_stub(name.replace("_", " ").title()))


# ---------------------------------------------------------------------------
# configs/
# ---------------------------------------------------------------------------

def configs() -> None:
    c = ROOT / "configs"

    for name in [
        "app", "logging", "paths", "units", "coordinate_systems",
        "commodity_defaults", "report_templates", "scoring_rules",
        "risk_taxonomy", "extraction_rules", "supported_formats", "model_registry",
    ]:
        write(c / "global" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for name in [
        "openai", "anthropic", "prompt_policies", "routing", "retrieval",
        "extraction", "summarization", "critique", "report_generation",
    ]:
        write(c / "llm" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for name in [
        "conversion_profiles", "mesh_cleanup", "section_defaults",
        "snapshot_profiles", "semantic_mapping",
    ]:
        write(c / "cad" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for name in [
        "domain_mapping", "drillhole_normalization", "compositing",
        "geostatistics", "gempy_profiles", "validation",
    ]:
        write(c / "geology" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for case in ["base_case", "bull_case", "bear_case", "lender_case"]:
        write(c / "economics" / "price_decks" / f"{case}.yaml", yaml_stub(case.replace("_", " ").title()))

    for regime in ["usa", "canada", "chile", "peru", "mexico"]:
        write(c / "economics" / "fiscal_regimes" / f"{regime}.yaml", yaml_stub(f"Fiscal Regime — {regime.upper()}"))

    for name in [
        "discount_rate_defaults", "capex_buckets", "opex_buckets",
        "sensitivity_axes", "valuation_metrics", "financing_profiles",
    ]:
        write(c / "economics" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for name in [
        "institutional_v1", "institutional_v2", "committee_pack",
        "client_pack", "memo_pack", "appendix_pack",
    ]:
        write(c / "reports" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))

    for name in ["table_views", "chart_views", "3d_views", "desktop_layouts"]:
        write(c / "ui" / f"{name}.yaml", yaml_stub(name.replace("_", " ").title()))


# ---------------------------------------------------------------------------
# prompts/  — system prompts have real content; task prompts are stubs
# ---------------------------------------------------------------------------

def prompts() -> None:
    p = ROOT / "prompts"

    # --- System prompts — these have real content ---
    write(p / "system" / "base_system.md", """\
# Base System Prompt

You are a specialist mining project analyst and technical report writer working
for a mining-focused consulting and research firm.

## Your Role
You assist engineers and analysts in processing technical mining data and
producing structured economic evaluations of mining projects.

## What You Do
- Extract structured data from technical documents, reports, and datasets
- Summarize geological, engineering, metallurgical, and economic information
- Generate sections of technical reports in the style of a PEA, PFS, or Feasibility Study
- Identify risks, data gaps, and inconsistencies in project data
- Score and evaluate projects across geological, economic, and operational dimensions

## What You Never Do
- You NEVER provide investment advice
- You NEVER say whether a stock will go up or down
- You NEVER recommend buying or selling any security
- You NEVER make statements about a company's attractiveness as an investment
- You NEVER speculate on share price performance

## Output Standard
Your outputs are neutral technical assessments. Every conclusion must be:
- Grounded in the data provided
- Qualified by the assumptions and limitations of that data
- Free from investment-oriented language

Acceptable: "The project demonstrates positive economics under the base case assumptions."
Unacceptable: "This is a compelling investment opportunity."

## Domain Agnosticism
You operate across all commodity types, deposit styles, and jurisdictions.
Do not assume any specific mineral, mining method, or country unless it is
explicitly stated in the data you are given.

## Uncertainty and Data Gaps
If data is missing, incomplete, or inconsistent, you must flag this explicitly.
Do not invent or assume data that has not been provided.
State confidence levels where appropriate.

## Source Discipline
All claims in your outputs must be traceable to a source in the project data.
When citing a figure, state where it came from.
""")

    write(p / "system" / "geology_analyst.md", """\
# Role Prompt — Geology Analyst

You are acting as the geology analyst on this project.

Your focus is on:
- The geological setting and deposit model
- Drillhole data quality and coverage
- Resource estimation inputs and methodology
- Geological continuity and structural controls
- Data gaps that affect geological confidence

When reviewing geological data, assess:
1. How well the deposit is defined (drilling density, spacing, coverage)
2. Whether the deposit model is geologically reasonable
3. What data is missing that would reduce uncertainty
4. Whether resource classification is consistent with the data

Flag any geological risks clearly and specifically.
Do not overstate geological confidence beyond what the data supports.
""")

    write(p / "system" / "economics_analyst.md", """\
# Role Prompt — Economics Analyst

You are acting as the economics analyst on this project.

Your focus is on:
- Capital cost (CAPEX) estimates and their basis
- Operating cost (OPEX) estimates and their basis
- Production schedule and throughput assumptions
- Revenue projections based on price decks and recoveries
- Discounted cash flow (DCF) model structure
- NPV, IRR, and payback metrics
- Sensitivity to key input variables

When reviewing economic data, assess:
1. Whether cost estimates are supported by engineering work or are conceptual
2. Whether the production schedule is consistent with the mine plan
3. What assumptions are driving the economics
4. How sensitive the project is to commodity price, CAPEX, OPEX, and recovery

All conclusions must be framed as technical assessments, not investment opinions.
Do not recommend the project as an investment.
State clearly which scenarios produce positive economics and under what conditions.
""")

    write(p / "system" / "report_writer.md", """\
# Role Prompt — Technical Report Writer

You are acting as the technical report writer on this project.

You write in the style of a professional mining technical report (PEA, PFS, or FS level).

Your writing standards:
- Clear, precise, and professional
- Third person throughout
- Passive or neutral voice for conclusions
- Every material claim supported by data or clearly qualified as an assumption
- No promotional language
- No investment-oriented language
- Consistent use of units throughout each section

When writing report sections:
1. Open with a brief scope statement (what this section covers)
2. Present data systematically before drawing conclusions
3. Qualify all conclusions with the assumptions they depend on
4. End each section with a clear summary of key findings and limitations

Report sections you may be asked to write:
- Executive Summary
- Project Overview
- Geological Setting and Mineralization
- Mineral Resource Estimate
- Mining Method and Mine Plan
- Metallurgy and Processing
- Capital Cost Estimate
- Operating Cost Estimate
- Economic Analysis
- Sensitivity Analysis
- Risk Factors
- Conclusions and Recommendations
""")

    write(p / "system" / "data_extractor.md", """\
# Role Prompt — Data Extractor

You are acting as the data extraction specialist on this project.

Your job is to read technical documents, reports, tables, and notes and extract
specific structured data fields as defined in the extraction task.

Your extraction standards:
- Extract only what is explicitly stated in the source
- Never infer or interpolate values that are not present
- Record the source location (page, section, table number) for every extracted value
- Flag ambiguous or conflicting values rather than choosing one silently
- Use null or "not stated" for fields that are not present in the source
- Preserve original units — do not convert unless instructed

Output format: structured JSON matching the schema provided with each task.
""")

    write(p / "system" / "critic.md", """\
# Role Prompt — Technical Critic

You are acting as the independent technical reviewer on this project.

Your job is to critically evaluate the outputs produced by other analysis steps.
You are looking for:
- Assumptions that are not supported by data
- Internal inconsistencies between sections or datasets
- Claims that exceed what the data can support
- Missing data that materially affects conclusions
- Language that could be interpreted as investment advice (compliance check)
- Arithmetic errors or unit inconsistencies

You are not trying to find reasons to reject the project.
You are ensuring the analysis is rigorous, honest, and defensible.

Report your findings as a structured list of flags, each with:
- Category (assumption / inconsistency / missing data / compliance / arithmetic)
- Severity (high / medium / low)
- Description of the issue
- Suggested resolution
""")

    # --- Task prompts — stubs ---
    for name in [
        "extract_project_facts", "extract_resource_summary",
        "extract_financial_terms", "extract_mine_plan_inputs",
        "extract_metallurgy", "extract_permitting",
        "extract_management_claims", "extract_cad_semantics",
    ]:
        write(p / "extraction" / f"{name}.md", md_stub(name.replace("_", " ").title()))

    for name in [
        "summarize_geology", "summarize_economics", "summarize_financing_risk",
        "summarize_cad_model", "summarize_permitting", "summarize_risks",
    ]:
        write(p / "summarization" / f"{name}.md", md_stub(name.replace("_", " ").title()))

    for name in [
        "write_executive_summary", "write_geology_section",
        "write_economics_section", "write_cad_section", "write_risk_section",
        "write_methodology", "write_appendix", "assemble_full_report",
    ]:
        write(p / "reporting" / f"{name}.md", md_stub(name.replace("_", " ").title()))

    for name in [
        "challenge_assumptions", "check_missing_data",
        "compare_report_to_sources", "identify_contradictions",
        "evaluate_tone_for_compliance",
    ]:
        write(p / "critique" / f"{name}.md", md_stub(name.replace("_", " ").title()))

    for name in [
        "score_geology", "score_economics", "score_financing",
        "score_permitting", "score_overall_project",
    ]:
        write(p / "scoring" / f"{name}.md", md_stub(name.replace("_", " ").title()))


# ---------------------------------------------------------------------------
# schemas/
# ---------------------------------------------------------------------------

def schemas() -> None:
    s = ROOT / "schemas"

    groups = {
        "common": [
            "source_reference", "units", "coordinates", "money",
            "date_range", "entity_review", "confidence",
        ],
        "project": [
            "project_metadata", "source_registry",
            "version_registry", "project_config",
        ],
        "drilling": [
            "collars", "surveys", "intervals", "lithology",
            "structures", "geotech", "qaqc",
        ],
        "geology": [
            "domains", "interpretations", "resource_estimate",
            "deposit_model_hypothesis", "continuity_assessment",
        ],
        "metallurgy": ["testwork", "recoveries", "concentrate_terms"],
        "engineering": [
            "mine_plan_inputs", "throughput_schedule", "production_schedule",
            "capex_line_items", "opex_line_items", "closure_assumptions",
        ],
        "economics": [
            "price_deck", "fiscal_terms", "financing_assumptions",
            "cashflow_inputs", "dcf_outputs", "sensitivity_outputs",
            "viability_summary", "breakeven_analysis",
        ],
        "financial": [
            "cap_table", "debt_schedule", "royalty_streams", "treasury_summary",
        ],
        "cad": [
            "object_inventory", "geometry_metadata", "object_relationships",
            "semantic_summary", "mesh_stats",
        ],
        "gis": ["claims", "infrastructure", "hydrology", "topo_metadata"],
        "notes": [
            "engineer_note", "analyst_note",
            "management_note", "site_visit_note",
        ],
        "reports": [
            "report_manifest", "report_section",
            "appendix_manifest", "chart_manifest",
        ],
        "review": ["override", "approval", "dispute", "signoff"],
    }

    for group, names in groups.items():
        for name in names:
            write(
                s / group / f"{name}.schema.json",
                json_schema_stub(name.replace("_", " ").title()),
            )


# ---------------------------------------------------------------------------
# engine/  — Python package
# ---------------------------------------------------------------------------

def engine() -> None:
    e = ROOT / "engine"
    write(e / "__init__.py", py_stub("Mining Intelligence Platform — Engine"))

    # cli
    cli = e / "cli"
    for name in [
        "__init__", "main", "ingest", "normalize", "analyze",
        "render", "report", "review", "rerun", "export",
    ]:
        write(cli / f"{name}.py", py_stub(f"CLI — {name}"))

    # core
    core = e / "core"
    for name in [
        "config", "paths", "constants", "enums", "logging",
        "errors", "hashing", "ids", "manifests", "validation", "provenance",
    ]:
        write(core / f"{name}.py", py_stub(f"Core — {name}"))

    # io
    io = e / "io"
    for name in [
        "file_registry", "json_io", "yaml_io", "parquet_io",
        "csv_io", "image_io", "pdf_io", "excel_io", "cad_io", "gis_io",
    ]:
        write(io / f"{name}.py", py_stub(f"IO — {name}"))

    # project
    proj = e / "project"
    for name in [
        "bootstrap", "create_project", "init_structure",
        "project_config", "project_manifest", "source_registry",
    ]:
        write(proj / f"{name}.py", py_stub(f"Project — {name}"))

    # scaffold
    scaffold = e / "scaffold"
    write(scaffold / "__init__.py", py_stub("Scaffold"))
    write(scaffold / "schema.py", py_stub("Scaffold — folder schema definition"))
    write(scaffold / "builder.py", py_stub("Scaffold — folder builder"))

    # ingest
    ingest = e / "ingest"
    for name in [
        "__init__", "dispatcher", "document_ingest", "drillhole_ingest",
        "assay_ingest", "cad_ingest", "gis_ingest", "market_ingest",
        "financial_ingest", "notes_ingest", "photo_ingest", "video_ingest",
    ]:
        write(ingest / f"{name}.py", py_stub(f"Ingest — {name}"))

    # parsing
    parsing = e / "parsing"
    for name in [
        "parse_pdf", "parse_docx", "parse_xlsx", "parse_pptx",
        "extract_tables", "split_sections", "build_document_index", "detect_citations",
    ]:
        write(parsing / "documents" / f"{name}.py", py_stub(f"Parse documents — {name}"))

    for name in [
        "parse_collars", "parse_surveys", "parse_intervals",
        "parse_lithology", "parse_structures", "parse_geotech", "parse_qaqc",
    ]:
        write(parsing / "drilling" / f"{name}.py", py_stub(f"Parse drilling — {name}"))

    for name in [
        "convert_dwg", "convert_dxf", "convert_obj", "convert_stl",
        "convert_gltf", "convert_omf", "build_object_catalog",
        "extract_layers", "compute_mesh_stats",
        "generate_section_planes", "render_cad_snapshots",
    ]:
        write(parsing / "cad" / f"{name}.py", py_stub(f"Parse CAD — {name}"))

    for name in [
        "parse_shapefiles", "parse_geojson", "parse_geotiff", "build_spatial_index",
    ]:
        write(parsing / "gis" / f"{name}.py", py_stub(f"Parse GIS — {name}"))

    # normalize
    normalize = e / "normalize"
    for name in [
        "__init__", "orchestrator", "metadata_normalizer", "drilling_normalizer",
        "assay_normalizer", "geology_normalizer", "metallurgy_normalizer",
        "engineering_normalizer", "economics_normalizer", "financial_normalizer",
        "permitting_normalizer", "cad_normalizer", "gis_normalizer",
        "notes_normalizer", "document_index_normalizer",
    ]:
        write(normalize / f"{name}.py", py_stub(f"Normalize — {name}"))

    # llm
    llm = e / "llm"
    write(llm / "__init__.py", py_stub("LLM module"))

    for name in ["openai_client", "anthropic_client", "router"]:
        write(llm / "providers" / f"{name}.py", py_stub(f"LLM provider — {name}"))

    for name in ["chunking", "embeddings", "index_builder", "query_engine", "citation_builder"]:
        write(llm / "retrieval" / f"{name}.py", py_stub(f"LLM retrieval — {name}"))

    for name in [
        "extract_project_facts", "extract_resource_summary",
        "extract_mine_plan_inputs", "extract_economic_assumptions",
        "extract_cad_semantics", "extract_risks",
    ]:
        write(llm / "extraction" / f"{name}.py", py_stub(f"LLM extraction — {name}"))

    for name in [
        "summarize_geology", "summarize_economics", "summarize_cad",
        "summarize_permitting", "summarize_notes",
    ]:
        write(llm / "summarization" / f"{name}.py", py_stub(f"LLM summarization — {name}"))

    for name in [
        "challenge_assumptions", "compare_to_sources",
        "flag_contradictions", "flag_missing_data",
    ]:
        write(llm / "critique" / f"{name}.py", py_stub(f"LLM critique — {name}"))

    for name in [
        "write_executive_summary", "write_geology_section",
        "write_economics_section", "write_cad_section", "write_risk_section",
        "write_methodology", "assemble_report_sections",
    ]:
        write(llm / "reporting" / f"{name}.py", py_stub(f"LLM reporting — {name}"))

    for name in [
        "score_geology", "score_economics", "score_financing",
        "score_permitting", "score_overall",
    ]:
        write(llm / "scoring" / f"{name}.py", py_stub(f"LLM scoring — {name}"))

    # geology
    geology = e / "geology"
    write(geology / "__init__.py", py_stub("Geology module"))
    for name in [
        "drillhole_compositor", "domain_classifier", "continuity_analyzer",
        "geological_risk_assessor", "resource_summary_builder",
        "deposit_model_hypothesizer", "missing_data_checker",
    ]:
        write(geology / f"{name}.py", py_stub(f"Geology — {name}"))

    # economics
    economics = e / "economics"
    write(economics / "__init__.py", py_stub("Economics module"))
    for name in [
        "production_schedule_builder", "revenue_model",
        "capex_model", "opex_model", "dcf_model",
        "npv_irr_calculator", "payback_calculator",
        "sensitivity_runner", "scenario_runner",
        "breakeven_analyzer", "economic_risk_assessor",
    ]:
        write(economics / f"{name}.py", py_stub(f"Economics — {name}"))

    # engineering
    engineering = e / "engineering"
    write(engineering / "__init__.py", py_stub("Engineering module"))
    for name in [
        "mine_plan_validator", "throughput_builder",
        "equipment_list_normalizer", "schedule_builder",
        "closure_cost_estimator",
    ]:
        write(engineering / f"{name}.py", py_stub(f"Engineering — {name}"))

    # reporting
    reporting = e / "reporting"
    write(reporting / "__init__.py", py_stub("Reporting module"))
    for name in [
        "report_assembler", "chart_builder", "table_builder",
        "pdf_exporter", "docx_exporter", "appendix_builder",
        "export_packager",
    ]:
        write(reporting / f"{name}.py", py_stub(f"Reporting — {name}"))

    # review
    review = e / "review"
    write(review / "__init__.py", py_stub("Review module"))
    for name in [
        "override_manager", "signoff_manager",
        "dispute_tracker", "review_diff_builder",
    ]:
        write(review / f"{name}.py", py_stub(f"Review — {name}"))

    # scoring
    scoring = e / "scoring"
    write(scoring / "__init__.py", py_stub("Scoring module"))
    for name in [
        "scorecard_builder", "subfactor_scorer",
        "evidence_linker", "confidence_scorer",
    ]:
        write(scoring / f"{name}.py", py_stub(f"Scoring — {name}"))

    # runs
    runs = e / "runs"
    for name in [
        "run_manager", "run_logger", "artifact_tracker",
        "prompt_recorder", "diff_builder", "environment_snapshot",
    ]:
        write(runs / f"{name}.py", py_stub(f"Runs — {name}"))


# ---------------------------------------------------------------------------
# api/
# ---------------------------------------------------------------------------

def api() -> None:
    a = ROOT / "api"
    write(a / "__init__.py", py_stub("API package"))
    write(a / "main.py", """\
\"\"\"FastAPI application entry point.\"\"\"

from fastapi import FastAPI

app = FastAPI(
    title="Mining Intelligence Platform API",
    version="0.1.0",
    description="Internal API — not for public access.",
)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
""")

    for name in [
        "projects", "ingest", "normalize", "analyze",
        "llm", "reports", "review", "export",
    ]:
        write(a / "routers" / f"{name}.py", py_stub(f"API router — {name}"))

    for name in ["cors", "auth", "logging", "error_handlers"]:
        write(a / "middleware" / f"{name}.py", py_stub(f"API middleware — {name}"))

    for name in ["engine", "projects_root", "auth"]:
        write(a / "dependencies" / f"{name}.py", py_stub(f"API dependency — {name}"))

    for name in [
        "project", "ingest_request", "normalize_request",
        "llm_request", "report_request", "review_request",
    ]:
        write(a / "models" / f"{name}.py", py_stub(f"API model — {name}"))


# ---------------------------------------------------------------------------
# web/  — React + TypeScript frontend
# ---------------------------------------------------------------------------

def web() -> None:
    w = ROOT / "web"
    write(w / "package.json", json.dumps({
        "name": "mining-intelligence-web",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "vite",
            "build": "tsc && vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^18",
            "react-dom": "^18",
            "react-router-dom": "^6"
        },
        "devDependencies": {
            "typescript": "^5",
            "vite": "^5",
            "@vitejs/plugin-react": "^4",
            "@types/react": "^18",
            "@types/react-dom": "^18"
        }
    }, indent=2) + "\n")
    write(w / "tsconfig.json", json.dumps({
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["ES2022", "DOM"],
            "module": "ESNext",
            "moduleResolution": "bundler",
            "strict": True,
            "jsx": "react-jsx"
        }
    }, indent=2) + "\n")
    write(w / "vite.config.ts", """\
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000'
    }
  }
})
""")
    write(w / "index.html", """\
<!DOCTYPE html>
<html lang="en">
  <head><meta charset="UTF-8" /><title>Mining Intelligence Platform</title></head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""")

    src = w / "src"
    write(src / "main.tsx", "// Entry point — stub\n")
    write(src / "App.tsx", "// App root — stub\n")

    for folder in [
        "components/layout", "components/project", "components/geology",
        "components/economics", "components/reports", "components/review",
        "components/shared",
        "pages", "hooks", "store", "api", "types",
    ]:
        touch(src / folder / ".gitkeep")

    write(src / "api" / "client.ts", "// API client — stub\n")
    write(src / "types" / "index.ts", "// Shared TypeScript types — stub\n")


# ---------------------------------------------------------------------------
# desktop/  — Tauri shell
# ---------------------------------------------------------------------------

def desktop() -> None:
    d = ROOT / "desktop"
    write(d / "package.json", json.dumps({
        "name": "mining-intelligence-desktop",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "tauri": "tauri"
        },
        "devDependencies": {
            "@tauri-apps/cli": "^1"
        },
        "dependencies": {
            "@tauri-apps/api": "^1"
        }
    }, indent=2) + "\n")

    tauri = d / "src-tauri"
    write(tauri / "tauri.conf.json", json.dumps({
        "package": {"productName": "Mining Intelligence Platform", "version": "0.1.0"},
        "build": {
            "beforeDevCommand": "pnpm --filter web dev",
            "beforeBuildCommand": "pnpm --filter web build",
            "devPath": "http://localhost:5173",
            "distDir": "../web/dist"
        },
        "tauri": {
            "windows": [{"title": "Mining Intelligence Platform", "width": 1400, "height": 900}],
            "security": {"csp": None}
        }
    }, indent=2) + "\n")
    write(tauri / "Cargo.toml", "# Tauri Rust manifest — stub\n")
    write(tauri / "src" / "main.rs", "// Tauri main — stub\n")


# ---------------------------------------------------------------------------
# scripts/
# ---------------------------------------------------------------------------

def scripts_dir() -> None:
    s = ROOT / "scripts"
    write(s / "setup_dev.sh", "#!/bin/bash\n# Development setup — stub\n")
    write(s / "export_pack.py", py_stub("Export package builder"))


# ---------------------------------------------------------------------------
# Project template (what gets copied to mining_projects/company_x/)
# ---------------------------------------------------------------------------

PROJECT_RAW_TREE = {
    "technical_reports": {
        "ni_43_101": None, "jorc": None, "pea": None, "pfs": None, "fs": None,
        "scoping": None, "appendices": None, "historical": None, "third_party": None,
    },
    "drillhole_csv": {
        "collars": None, "surveys": None, "lithology_logs": None,
        "structure_logs": None, "geotech_logs": None, "downhole_geophysics": None,
        "drill_program_summaries": None, "legacy_exports": None,
    },
    "assays": {
        "assay_csv": None, "assay_certificates": None, "lab_exports": None,
        "composites": None,
        "qaqc": {
            "standards": None, "blanks": None, "duplicates": None,
            "umpire": None, "qaqc_summaries": None,
        },
    },
    "maps": {
        "regional": None, "property": None, "geology": None, "surface": None,
        "underground": None, "sections": None, "long_sections": None,
        "cross_sections": None, "historical": None, "annotated": None,
    },
    "photos": {
        "site_visit": None, "outcrop": None, "core": None, "infrastructure": None,
        "plant": None, "drone": None, "maps_photographed": None, "misc": None,
    },
    "management_notes": {
        "meeting_notes": None, "call_notes": None, "site_visit_notes": None,
        "interview_notes": None, "internal_memos": None, "transcripts": None,
    },
    "financials": {
        "cap_table": None, "debt": None, "royalties": None, "streams": None,
        "warrants": None, "options": None, "cash_balance": None,
        "financing_history": None, "budgets": None, "treasury": None,
    },
    "presentations": {
        "investor_decks": None, "conference_decks": None,
        "webcast_slides": None, "internal_presentations": None,
    },
    "company_filings": {
        "annual_reports": None, "quarterly_reports": None, "md_and_a": None,
        "press_releases": None, "resource_updates": None,
        "financing_announcements": None, "shareholder_materials": None,
    },
    "metallurgy": {
        "testwork_reports": None, "recovery_curves": None, "flowsheets": None,
        "concentrate_specs": None, "reagent_data": None, "variability_tests": None,
    },
    "engineering": {
        "mine_plan": None, "processing_plant": None, "infrastructure": None,
        "tailings": None, "water": None, "closure": None,
        "capex_support": None, "opex_support": None, "schedules": None,
    },
    "cad": {
        "dwg": None, "dxf": None, "obj": None, "stl": None, "gltf": None,
        "glb": None, "omf": None, "vendor_exports": None, "mine_designs": None,
        "pit_shells": None, "underground_shapes": None, "infrastructure": None,
        "sections": None, "surfaces": None, "wireframes": None, "block_models": None,
    },
    "gis": {
        "shapefiles": None, "geojson": None, "geotiff": None, "raster": None,
        "terrain": None, "claims": None, "roads": None, "power": None,
        "hydrology": None, "boundaries": None,
    },
    "environmental": {
        "baseline_studies": None, "impact_assessments": None, "water_reports": None,
        "tailings_risk": None, "reclamation": None, "monitoring": None,
    },
    "permits": {
        "applications": None, "approvals": None, "timelines": None,
        "agency_correspondence": None, "compliance": None,
    },
    "site_visit": {
        "engineer_notes": None, "analyst_notes": None, "field_measurements": None,
        "checklists": None, "observations": None, "sketches": None,
    },
    "interviews": {
        "management": None, "consultants": None, "engineers": None,
        "geologists": None, "regulators": None, "community": None,
    },
    "market_data": {
        "commodity_prices": None, "fx_rates": None, "peer_metrics": None,
        "transaction_comps": None, "benchmark_curves": None,
    },
    "correspondence": {
        "email_exports": None, "consultant_qa": None,
        "advisor_notes": None, "internal_threads": None,
    },
    "videos": {
        "drone": None, "site_walkthrough": None, "webcast": None, "interviews": None,
    },
}

PROJECT_NORMALIZED_TREE = {
    "metadata": None,
    "drilling": None,
    "assays": None,
    "geology": None,
    "metallurgy": None,
    "engineering": None,
    "economics": {
        "price_decks": None, "fiscal_terms": None,
        "assumptions": None, "cashflow_inputs": None, "model_inputs": None,
    },
    "financial": None,
    "permitting": None,
    "market": None,
    "cad": {
        "converted_assets": {
            "sections": None, "plans": None, "snapshots": None,
            "meshes": None, "surfaces": None,
        },
        "object_stats": None,
    },
    "gis": None,
    "notes": None,
    "document_index": None,
    "staging": {
        "parsed_documents": {
            "technical_reports": None, "filings": None,
            "presentations": None, "notes": None,
        },
        "extracted_tables": {
            "technical_reports": None, "filings": None, "spreadsheets": None,
        },
        "ocr": {"scanned_reports": None, "maps": None, "figures": None},
        "cad_converted": {
            "glb": None, "obj": None, "vtk": None,
            "screenshots": None, "object_catalogs": None,
        },
        "gis_converted": {"normalized_layers": None, "raster_previews": None},
        "image_annotations": {"maps": None, "core": None, "site_photos": None},
        "transcript_text": {"webcast": None, "interviews": None, "meetings": None},
        "entity_extraction": {
            "project_facts": None, "economic_facts": None,
            "geological_facts": None, "management_facts": None,
        },
        "temporary_merges": {
            "drillhole_merges": None, "assay_merges": None, "document_merges": None,
        },
    },
    "interpreted": {
        "geology": None, "economics": None, "financial": None,
        "risk": None, "scoring": None, "investment_memo_support": None,
    },
    "models": {
        "geology": None,
        "economics": None,
        "cad": None,
        "valuation": {"relative_valuation": None, "transaction_valuation": None},
        "scoring": None,
        "llm": {
            "extraction": {"schemas": None, "prompts": None, "outputs": None},
            "summarization": {"prompts": None, "outputs": None},
            "report_generation": {
                "prompts": None, "section_drafts": None, "final_drafts": None,
            },
            "critique": {
                "prompts": None, "review_flags": None, "contradiction_checks": None,
            },
        },
    },
    "review": {
        "engineer": None, "analyst": None,
        "approvals": None, "overrides": None, "disputes": None,
    },
}

PROJECT_OUTPUTS_TREE = {
    "charts": {
        "production_profile": None, "cashflow": None, "sensitivities": None,
        "cost_breakdown": None, "peer_comps": None, "drilling": None,
        "qaqc": None, "metallurgy": None, "valuation": None,
    },
    "tables": {
        "resource_summary": None, "economic_summary": None, "risk_summary": None,
        "cap_table_summary": None, "drilling_summary": None,
        "assay_summary": None, "peer_comp_summary": None,
    },
    "geology": {
        "maps": None, "sections": None, "long_sections": None,
        "cross_sections": None, "domain_views": None,
        "drillhole_views": None, "interpretation_views": None,
    },
    "reports": {
        "draft": {"markdown": None, "docx": None, "pdf": None},
        "final": {"markdown": None, "docx": None, "pdf": None},
        "supporting_appendices": {
            "charts": None, "tables": None, "figures": None, "citations": None,
        },
    },
    "economics": {
        "summary_tables": None, "sensitivity_tables": None,
        "cashflow_books": None, "valuation_books": None, "breakeven_tables": None,
    },
    "cad": {
        "rendered_views": None, "animated_turntables": None,
        "section_snapshots": None, "annotation_views": None, "model_previews": None,
    },
    "export_packages": None,
    "presentations": {"internal": None, "client": None, "committee": None},
}


def _walk_and_touch(tree: dict | None, base: Path) -> None:
    if tree is None:
        touch(base / ".gitkeep")
        return
    for name, subtree in tree.items():
        _walk_and_touch(subtree, base / name)


def project_template() -> None:
    """
    Writes a _template/ folder inside the platform that shows the canonical
    per-project structure. The engine copies this when creating a new project
    inside mining_projects/.
    """
    t = ROOT / "_project_template"
    write(t / "README.md", """\
# Project Template

This folder defines the canonical structure for a mining project.
When you run `mip scaffold new <project_id>`, this template is copied
to your configured mining_projects/ directory.

Do not store real project data here.
""")
    _walk_and_touch(PROJECT_RAW_TREE, t / "raw")
    _walk_and_touch(PROJECT_NORMALIZED_TREE, t / "normalized")
    _walk_and_touch(PROJECT_OUTPUTS_TREE, t / "outputs")
    touch(t / "runs" / ".gitkeep")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Scaffolding platform at: {ROOT}")
    root_files()
    print("  ✓ root files")
    docs()
    print("  ✓ docs/")
    configs()
    print("  ✓ configs/")
    prompts()
    print("  ✓ prompts/")
    schemas()
    print("  ✓ schemas/")
    engine()
    print("  ✓ engine/")
    api()
    print("  ✓ api/")
    web()
    print("  ✓ web/")
    desktop()
    print("  ✓ desktop/")
    scripts_dir()
    print("  ✓ scripts/")
    project_template()
    print("  ✓ _project_template/")

    total_files = sum(1 for _ in ROOT.rglob("*") if _.is_file())
    total_dirs = sum(1 for _ in ROOT.rglob("*") if _.is_dir())
    print(f"\nDone. {total_dirs} folders, {total_files} files.")
    print(f"\nNext: pip install -e . && mip scaffold new <your_first_project>")


if __name__ == "__main__":
    main()
