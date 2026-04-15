"""
Analyze router — trigger and monitor analysis runs.

Endpoints:
  POST /projects/{project_id}/analyze              start a new analysis run
  GET  /projects/{project_id}/runs                 list all runs
  GET  /projects/{project_id}/runs/{run_id}        get run status and results summary
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from engine.core.paths import project_root, run_root

router = APIRouter(tags=["analyze"])

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    force: bool = False


class RunStatus(BaseModel):
    run_id: str
    project_id: str
    status: str  # pending | running | complete | failed
    started_at: str | None = None
    completed_at: str | None = None
    step: str | None = None
    error: str | None = None
    output_files: list[str] = []


class RunList(BaseModel):
    project_id: str
    runs: list[RunStatus]
    total: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project_exists(project_id: str) -> None:
    if not project_root(project_id).exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")


def _load_run_status(project_id: str, run_id: str) -> dict:
    status_file = run_root(project_id, run_id) / "run_status.json"
    if not status_file.exists():
        return {}
    with status_file.open() as f:
        return json.load(f)


def _save_run_status(project_id: str, run_id: str, data: dict) -> None:
    rdir = run_root(project_id, run_id)
    rdir.mkdir(parents=True, exist_ok=True)
    with (rdir / "run_status.json").open("w") as f:
        json.dump(data, f, indent=2)


def _generate_run_id() -> str:
    return datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")


def _collect_output_files(project_id: str, run_id: str) -> list[str]:
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        return []
    return [f.name for f in rdir.glob("*.json")]


def _save_section(project_id: str, run_id: str, section_key: str, data: dict) -> None:
    rdir = run_root(project_id, run_id)
    rdir.mkdir(parents=True, exist_ok=True)
    with (rdir / f"{section_key}.json").open("w") as f:
        json.dump(data, f, indent=2)


def _compute_doc_hash(raw_files: list) -> str:
    """Fast hash of file names + sizes + mtimes — invalidates when files change."""
    h = hashlib.sha256()
    for f in sorted(raw_files, key=lambda p: p.name):
        stat = f.stat()
        h.update(f.name.encode())
        h.update(str(stat.st_size).encode())
        h.update(str(int(stat.st_mtime)).encode())
    return h.hexdigest()


def _find_cached_section(project_id: str, doc_hash: str, section_key: str) -> dict | None:
    """Return a section result from the most recent completed run with the same doc hash."""
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return None
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        status_file = run_dir / "run_status.json"
        if not status_file.exists():
            continue
        try:
            status = json.loads(status_file.read_text())
            if status.get("status") != "complete":
                continue
            if status.get("doc_hash") != doc_hash:
                continue
            section_file = run_dir / f"{section_key}.json"
            if section_file.exists():
                return json.loads(section_file.read_text())
        except Exception:
            continue
    return None


async def _with_retry(coro_fn, retries: int = 3, base_delay: float = 2.0):
    """Call coro_fn() up to `retries` times with exponential backoff."""
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries):
        try:
            return await coro_fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                await asyncio.sleep(base_delay * (2 ** attempt))
    raise last_exc


def _extract_response_data(response) -> dict:
    """Safely extract dict from LLMResponse or DualLLMResponse."""
    if hasattr(response, "merged"):
        return response.merged or {}
    if hasattr(response, "structured") and response.structured:
        return response.structured
    if hasattr(response, "content"):
        return {"text": response.content}
    return {}


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def _run_analysis_in_background(project_id: str, run_id: str) -> None:
    """
    Full consulting report pipeline:
      1. Load documents
      2. Extract structured project facts
      3. Write executive summary, geology, economics, and risk sections
      4. Save data sources notice
    """
    def update(step: str, status: str = "running", error: str | None = None) -> None:
        current = _load_run_status(project_id, run_id)
        current["step"] = step
        current["status"] = status
        if error:
            current["error"] = error
        if status in ("complete", "failed"):
            current["completed_at"] = datetime.now(timezone.utc).isoformat()
        _save_run_status(project_id, run_id, current)

    try:
        # ── Step 1: Load documents ──────────────────────────────────────────
        update("Loading documents")

        raw_dir = project_root(project_id) / "raw" / "documents"
        raw_files = [f for f in raw_dir.glob("*") if f.is_file()] if raw_dir.exists() else []
        if not raw_files:
            update("failed", status="failed",
                   error="No files found. Upload documents first.")
            return

        # Compute a hash of the source files so we can skip re-extracting
        # unchanged documents on subsequent runs (saves LLM cost + time).
        doc_hash = _compute_doc_hash(raw_files)
        current = _load_run_status(project_id, run_id)
        current["doc_hash"] = doc_hash
        _save_run_status(project_id, run_id, current)

        from engine.core.document_loader import load_document

        _IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tiff", ".gif", ".webp"}
        _CAD_EXTS = {".dxf", ".dwg"}
        _OMF_EXTS = {".omf", ".vtk", ".vtu", ".obj", ".stl"}

        renders_dir = project_root(project_id) / "raw" / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        omf_renders_dir = project_root(project_id) / "normalized" / "renders"
        omf_renders_dir.mkdir(parents=True, exist_ok=True)

        text_parts = []
        source_files = []
        image_files: list[str] = []
        cad_text_parts: list[str] = []   # CAD/OMF descriptions for semantic extraction
        load_errors = []
        for rf in raw_files:
            try:
                # OMF / 3D files save renders to normalized/renders/
                if rf.suffix.lower() in _OMF_EXTS:
                    text = load_document(rf, save_render_dir=omf_renders_dir)
                else:
                    text = load_document(rf, save_render_dir=renders_dir)
                if text and text.strip():
                    text_parts.append(f"[Source: {rf.name}]\n{text}")
                    source_files.append(rf.name)
                    # Collect CAD/3D descriptions separately for semantic extraction
                    if rf.suffix.lower() in _CAD_EXTS | _OMF_EXTS:
                        cad_text_parts.append(f"[Source: {rf.name}]\n{text}")
                if rf.suffix.lower() in _IMAGE_EXTS:
                    image_files.append(rf.name)
            except Exception as exc:
                load_errors.append(f"{rf.name}: {exc}")

        if not text_parts:
            detail = "No readable content found in uploaded files."
            if load_errors:
                detail += " Errors: " + "; ".join(load_errors[:3])
            update("failed", status="failed", error=detail)
            return

        project_data = "\n\n---\n\n".join(text_parts)
        truncated = project_data[:50000]

        # ── Build figures context from OMF renders manifest (if present) ────
        figures_context = ""
        manifest_path = omf_renders_dir / "renders_manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                render_entries = manifest.get("renders", [])
                if render_entries:
                    lines = [f'{r["filename"]} — {r["description"]}' for r in render_entries]
                    figures_context = (
                        "\n\nAVAILABLE FIGURES FOR THIS REPORT:\n"
                        + "\n".join(lines)
                        + "\nInsert figures inline using: "
                        "{{FIGURE: filename | Figure N: Descriptive caption}}\n"
                    )
            except Exception as fig_exc:
                logger.warning("Could not read renders manifest: %s", fig_exc)

        # ── Step 2: Extract project facts ──────────────────────────────────
        facts = _find_cached_section(project_id, doc_hash, "01_project_facts")
        if facts is not None:
            update("Extracting project facts (cached)")
        else:
            update("Extracting project facts")
            from engine.llm.extraction.extract_project_facts import extract_project_facts

            async def _extract() -> dict:
                r = await _with_retry(lambda: extract_project_facts(truncated, run_id=run_id))
                return _extract_response_data(r)

            facts = asyncio.run(_extract())
            _save_section(project_id, run_id, "01_project_facts", facts)

        facts_str = json.dumps(facts, indent=2)

        # ── Step 2.1: Jurisdiction profile — live web search (non-fatal) ────
        # Detects jurisdiction from project facts then researches current tax
        # rates, royalty structures, and policy via gpt-4o-search-preview.
        # No hardcoded database — results reflect law as of analysis date.
        juris_data: dict = {}
        try:
            import os as _os
            from openai import OpenAI as _OAI
            from engine.market.jurisdiction_risk import detect_jurisdiction
            from engine.llm.extraction.research_jurisdiction_profile import research_jurisdiction_profile

            detected_jurisdiction = detect_jurisdiction(facts)
            if detected_jurisdiction:
                update(f"Researching jurisdiction profile: {detected_jurisdiction}")
                _oai_key = _os.getenv("OPENAI_API_KEY")
                if _oai_key:
                    _oai_client = _OAI(api_key=_oai_key)
                    juris_data = asyncio.run(
                        research_jurisdiction_profile(detected_jurisdiction, _oai_client)
                    )
                else:
                    juris_data = {
                        "jurisdiction": detected_jurisdiction,
                        "note": "OpenAI API key not configured — jurisdiction profile unavailable.",
                    }
            else:
                juris_data = {"note": "Jurisdiction could not be determined from project documents."}
            _save_section(project_id, run_id, "12_jurisdiction_risk", juris_data)
        except Exception as _juris_exc:
            logger.warning("Jurisdiction profile step failed (non-fatal): %s", _juris_exc)
            pass  # non-fatal — don't block the pipeline

        # ── Step 2.2: Extract structured data in parallel ─────────────────────
        # Tier 1/2 investor-relevant extractions all run concurrently.
        # Results persist to normalized/metadata/ across runs.
        update("Extracting resources, metallurgy, permitting, capital structure, and operator data")
        try:
            # Check cache for each extraction independently — allows partial cache hits
            _cached_keys = ["14_metallurgy", "15_permitting", "16_operator", "17_capital_structure"]
            _cached = {k: _find_cached_section(project_id, doc_hash, k) for k in _cached_keys}
            _all_cached = all(v is not None for v in _cached.values())

            from engine.llm.extraction.extract_resource_table import extract_resource_table
            from engine.llm.extraction.extract_royalties import extract_royalties
            from engine.llm.extraction.extract_comparable_transactions import extract_comparable_transactions
            from engine.llm.extraction.extract_metallurgy import extract_metallurgy
            from engine.llm.extraction.extract_permitting import extract_permitting
            from engine.llm.extraction.extract_operator_track_record import extract_operator_track_record
            from engine.llm.extraction.extract_capital_structure import extract_capital_structure

            async def _extract_detail_data():
                # Always re-extract resources/royalties/comparables (they go into the DB)
                # Cache-hit the expensive specialist extractions when docs haven't changed
                coros = [
                    _with_retry(lambda: extract_resource_table(truncated, run_id=run_id)),
                    _with_retry(lambda: extract_royalties(truncated, run_id=run_id)),
                    _with_retry(lambda: extract_comparable_transactions(truncated, run_id=run_id)),
                ]
                async def _passthrough(v):
                    return v

                # For each specialist extraction: use cache or run LLM
                for key, fn in [
                    ("14_metallurgy",         lambda: extract_metallurgy(truncated, run_id=run_id)),
                    ("15_permitting",          lambda: extract_permitting(truncated, run_id=run_id)),
                    ("16_operator",            lambda: extract_operator_track_record(truncated, run_id=run_id)),
                    ("17_capital_structure",   lambda: extract_capital_structure(truncated, run_id=run_id)),
                ]:
                    cached_val = _cached.get(key)
                    if cached_val is not None:
                        coros.append(_passthrough(cached_val))
                    else:
                        coros.append(_with_retry(fn))
                results = await asyncio.gather(*coros)
                return tuple(r if isinstance(r, dict) else _extract_response_data(r)
                             for r in results)

            (res_data, roy_data, comp_data,
             met_data, permit_data, operator_data, capstruct_data) = asyncio.run(_extract_detail_data())

            # Write to normalized/metadata/ using the same storage paths as the
            # royalties/resources/comparables routers, tagged with the run that
            # produced them so the UI can show provenance.
            import uuid
            from datetime import datetime, timezone as _tz
            now = datetime.now(_tz.utc).isoformat()
            meta_dir = project_root(project_id) / "normalized" / "metadata"
            meta_dir.mkdir(parents=True, exist_ok=True)

            # Resources — convert prompt rows → ResourceRow schema
            if not res_data.get("not_found") and res_data.get("rows"):
                resource_rows = []
                for row in res_data["rows"]:
                    resource_rows.append({
                        "row_id": str(uuid.uuid4()),
                        "classification": row.get("classification") or "Inferred",
                        "domain": row.get("domain"),
                        "tonnage_mt": row.get("tonnage_mt"),
                        "grade_value": row.get("grade_value"),
                        "grade_unit": row.get("grade_unit"),
                        "contained_metal": row.get("contained_metal"),
                        "metal_unit": row.get("metal_unit"),
                        "cut_off_grade": row.get("cut_off_grade"),
                        "notes": row.get("notes"),
                        "source": f"Extracted by AI · run {run_id}",
                        "created_at": now,
                        "updated_at": now,
                    })
                with (meta_dir / "resources.json").open("w") as f:
                    json.dump(resource_rows, f, indent=2)

            # Royalties — convert prompt agreements → Royalty schema
            if not roy_data.get("not_found") and roy_data.get("agreements"):
                royalty_rows = []
                for ag in roy_data["agreements"]:
                    royalty_rows.append({
                        "royalty_id": str(uuid.uuid4()),
                        "royalty_type": ag.get("royalty_type") or "Other",
                        "holder": ag.get("holder") or "Unknown",
                        "rate_pct": ag.get("rate_pct"),
                        "metals_covered": ag.get("metals_covered"),
                        "area_covered": ag.get("area_covered"),
                        "stream_pct": ag.get("stream_pct"),
                        "stream_purchase_price": ag.get("stream_purchase_price"),
                        "stream_purchase_unit": ag.get("stream_purchase_unit"),
                        "sliding_scale_notes": ag.get("sliding_scale_notes"),
                        "production_rate": ag.get("production_rate"),
                        "production_unit": ag.get("production_unit"),
                        "buyback_option": bool(ag.get("buyback_option")),
                        "buyback_price_musd": ag.get("buyback_price_musd"),
                        "recorded_instrument": ag.get("recorded_instrument"),
                        "notes": ag.get("notes"),
                        "source": f"Extracted by AI · run {run_id}",
                        "created_at": now,
                        "updated_at": now,
                    })
                with (meta_dir / "royalties.json").open("w") as f:
                    json.dump(royalty_rows, f, indent=2)

            # Comparables — convert prompt transactions → Comparable schema
            if not comp_data.get("not_found") and comp_data.get("transactions"):
                comp_rows = []
                for tx in comp_data["transactions"]:
                    comp_rows.append({
                        "comp_id": str(uuid.uuid4()),
                        "project_name": tx.get("project_name") or "Unknown",
                        "acquirer": tx.get("acquirer"),
                        "seller": tx.get("seller"),
                        "commodity": tx.get("commodity"),
                        "transaction_date": tx.get("transaction_date"),
                        "transaction_value_musd": tx.get("transaction_value_musd"),
                        "resource_moz_or_mlb": tx.get("resource_moz_or_mlb"),
                        "price_per_unit_usd": tx.get("price_per_unit_usd"),
                        "study_stage": tx.get("study_stage"),
                        "jurisdiction": tx.get("jurisdiction"),
                        "notes": tx.get("notes"),
                        "source": f"Extracted by AI · run {run_id}",
                        "created_at": now,
                        "updated_at": now,
                    })
                with (meta_dir / "comparables.json").open("w") as f:
                    json.dump(comp_rows, f, indent=2)

            # Metallurgy — save raw extracted data; feeds DCF recovery assumption
            if met_data and not met_data.get("not_found"):
                met_data["extracted_at"] = now
                met_data["source_run"] = run_id
                with (meta_dir / "metallurgy.json").open("w") as f:
                    json.dump(met_data, f, indent=2)
                # Also save to run dir so report writer can reference it
                _save_section(project_id, run_id, "14_metallurgy", met_data)

            # Permitting — save permit status, EA status, water rights, timeline
            if permit_data and not permit_data.get("not_found"):
                permit_data["extracted_at"] = now
                permit_data["source_run"] = run_id
                with (meta_dir / "permitting.json").open("w") as f:
                    json.dump(permit_data, f, indent=2)
                _save_section(project_id, run_id, "15_permitting", permit_data)

            # Operator track record — management bios, prior project outcomes
            if operator_data and not operator_data.get("not_found"):
                operator_data["extracted_at"] = now
                operator_data["source_run"] = run_id
                with (meta_dir / "operator.json").open("w") as f:
                    json.dump(operator_data, f, indent=2)
                _save_section(project_id, run_id, "16_operator", operator_data)

            # Capital structure — shares, warrants, streams, royalties, debt
            if capstruct_data and not capstruct_data.get("not_found"):
                capstruct_data["extracted_at"] = now
                capstruct_data["source_run"] = run_id
                with (meta_dir / "capital_structure.json").open("w") as f:
                    json.dump(capstruct_data, f, indent=2)
                _save_section(project_id, run_id, "17_capital_structure", capstruct_data)

        except Exception as detail_exc:
            import traceback
            logger.warning("Detail extraction failed (non-fatal): %s", detail_exc)

        # ── Step 2.3: CAD semantic extraction (if CAD/OMF files were loaded) ─
        if cad_text_parts:
            try:
                from engine.llm.extraction.extract_cad_semantics import extract_cad_semantics
                cad_combined = "\n\n---\n\n".join(cad_text_parts)[:30000]

                async def _extract_cad() -> dict:
                    r = await extract_cad_semantics(cad_combined, run_id=run_id)
                    # extract_cad_semantics uses dual runner — handle both response types
                    if hasattr(r, "reconciled"):
                        return r.reconciled or {}
                    return _extract_response_data(r)

                cad_semantics = asyncio.run(_extract_cad())
                if cad_semantics:
                    meta_dir = project_root(project_id) / "normalized" / "metadata"
                    meta_dir.mkdir(parents=True, exist_ok=True)
                    with (meta_dir / "cad_semantics.json").open("w") as f:
                        json.dump(cad_semantics, f, indent=2)
                    _save_section(project_id, run_id, "18_cad_semantics", cad_semantics)
            except Exception as cad_exc:
                logger.warning("CAD semantic extraction failed (non-fatal): %s", cad_exc)

        # ── Step 2.5: Gather market intelligence (live prices + web search) ─
        update("Gathering market intelligence")

        market_intel: dict = {}
        try:
            from engine.market.live_prices import (
                get_commodity_prices,
                get_macro_snapshot,
                build_price_context_string,
            )
            from engine.llm.extraction.gather_market_intelligence import (
                gather_market_intelligence,
            )

            commodity_field = (
                facts.get("commodity")
                or facts.get("primary_commodity")
                or facts.get("metal")
                or "gold"
            )

            # Fetch live prices and macro in a thread (yfinance is sync)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                price_future = pool.submit(get_commodity_prices, commodity_field)
                macro_future = pool.submit(get_macro_snapshot)
                commodity_prices = price_future.result(timeout=20)
                macro_snapshot   = macro_future.result(timeout=20)

            # Web intelligence searches (parallel, via GPT-4o search model)
            async def _gather() -> dict:
                return await gather_market_intelligence(
                    project_facts=facts,
                    commodity_prices=commodity_prices,
                    macro_snapshot=macro_snapshot,
                    run_id=run_id,
                )

            market_intel = asyncio.run(_gather())
            _save_section(project_id, run_id, "02_market_intelligence", market_intel)

            # Build a plain-text price context string to inject into downstream prompts
            price_context = build_price_context_string(
                commodity_prices, macro_snapshot,
                as_of_date=market_intel.get("gathered_at"),
            )

        except Exception as mi_exc:
            import traceback
            market_intel = {
                "error": f"Market intelligence unavailable: {mi_exc}",
                "traceback": traceback.format_exc()[:600],
            }
            _save_section(project_id, run_id, "02_market_intelligence", market_intel)
            price_context = ""

        # Build combined context — project facts + source docs + live market data
        market_context_block = ""
        if market_intel and not market_intel.get("error"):
            proj_intel   = market_intel.get("project_intelligence", {})
            comm_market  = market_intel.get("commodity_market", {})
            macro_ctx    = market_intel.get("macro_context", {})

            market_context_block = "\n\n---\n\nMARKET INTELLIGENCE (web-sourced, as of analysis date):\n"
            if price_context:
                market_context_block += f"\n{price_context}\n"
            if proj_intel.get("findings"):
                market_context_block += f"\nPROJECT INTELLIGENCE:\n{proj_intel['findings']}\n"
            if comm_market.get("analysis"):
                market_context_block += f"\nCOMMODITY MARKET:\n{comm_market['analysis']}\n"
            if macro_ctx.get("analysis"):
                market_context_block += f"\nMACROECONOMIC CONTEXT:\n{macro_ctx['analysis']}\n"

        # Build supplementary context blocks from the structured extractions
        # completed in Step 2.2 so the report writer LLMs have full context.
        supplementary_block = ""
        try:
            if met_data and not met_data.get("not_found"):
                supplementary_block += f"\n\nMETALLURGY (extracted):\n{json.dumps(met_data, indent=2)}"
            if permit_data and not permit_data.get("not_found"):
                supplementary_block += f"\n\nPERMITTING STATUS (extracted):\n{json.dumps(permit_data, indent=2)}"
            if operator_data and not operator_data.get("not_found"):
                supplementary_block += f"\n\nOPERATOR & MANAGEMENT TRACK RECORD (extracted):\n{json.dumps(operator_data, indent=2)}"
            if capstruct_data and not capstruct_data.get("not_found"):
                supplementary_block += f"\n\nCAPITAL STRUCTURE (extracted):\n{json.dumps(capstruct_data, indent=2)}"
        except Exception:
            pass  # non-fatal — report writers will work from source docs alone

        combined = (
            f"PROJECT FACTS:\n{facts_str}"
            f"\n\nSOURCE DOCUMENTS:\n{truncated}"
            f"{market_context_block}"
            f"{supplementary_block}"
        )

        # ── Step 2.6: Extract economic assumptions + mine plan in parallel ──
        update("Extracting economic data")

        from engine.llm.extraction.extract_economic_assumptions import extract_economic_assumptions
        from engine.llm.extraction.extract_mine_plan_inputs import extract_mine_plan_inputs

        async def _extract_econ() -> tuple[dict, dict]:
            econ, mine = await asyncio.gather(
                extract_economic_assumptions(truncated, run_id=run_id),
                extract_mine_plan_inputs(truncated, run_id=run_id),
            )
            return _extract_response_data(econ), _extract_response_data(mine)

        econ_assumptions, mine_plan = asyncio.run(_extract_econ())

        # ── Step 2.6: Run DCF model (non-fatal — falls back to LLM-only) ───
        update("Running economics model")

        dcf_output: dict | None = None
        try:
            import dataclasses
            from engine.economics.input_builder import build_input_book_from_llm
            from engine.economics.dcf_model import run_dcf
            from engine.economics.sensitivity_runner import run_sensitivity

            # Load metallurgy data if extracted — overrides the 90% default recovery
            _met_override: dict | None = None
            try:
                _met_path = project_root(project_id) / "normalized" / "metadata" / "metallurgy.json"
                if _met_path.exists():
                    _met_override = json.loads(_met_path.read_text())
            except Exception:
                pass

            input_book = build_input_book_from_llm(
                project_id=project_id,
                economic_assumptions=econ_assumptions,
                mine_plan=mine_plan,
                project_facts=facts,
                metallurgy=_met_override,
            )
            if input_book:
                cash_flows, summary = run_dcf(input_book)
                sensitivity = run_sensitivity(input_book)

                # Surface any defaults that were used — analysts must know which
                # inputs were assumed rather than extracted from the study
                defaults_used = [n for n in (input_book.notes or []) if "default" in n.lower()]
                dcf_output = {
                    "model_ran": True,
                    "assumptions_notes": input_book.notes,
                    "defaults_used": defaults_used,
                    "defaults_warning": (
                        f"{len(defaults_used)} input(s) used assumed defaults rather than "
                        "values extracted from the study documents: "
                        + "; ".join(defaults_used)
                    ) if defaults_used else None,
                    "summary": summary.to_dict(),
                    "cash_flow_table": [dataclasses.asdict(cf) for cf in cash_flows],
                    "sensitivity": sensitivity.to_dict(),
                }
            else:
                dcf_output = {
                    "model_ran": False,
                    "reason": "Insufficient data to build economics model from source documents.",
                    "hint": (
                        "The DCF model requires a production schedule (annual ore tonnes + grade), "
                        "capital cost estimate, operating cost, and commodity price assumption. "
                        "Check that the uploaded documents contain these sections."
                    ),
                }
        except Exception as dcf_exc:
            import traceback
            dcf_output = {
                "model_ran": False,
                "reason": f"DCF model error: {dcf_exc}",
            }

        _save_section(project_id, run_id, "06_dcf_model", dcf_output)

        # ── Step 3: Write specialist sections in parallel ──────────────────
        update("Writing report sections")

        from engine.llm.reporting.write_geology_section import write_geology_section
        from engine.llm.reporting.write_economics_section import write_economics_section
        from engine.llm.reporting.write_risk_section import write_risk_section
        from engine.llm.critique.flag_missing_data import flag_missing_data
        from engine.llm.critique.flag_contradictions import flag_contradictions
        from engine.llm.critique.check_compliance import check_compliance
        from engine.llm.scoring.assess_confidence import assess_confidence

        dcf_context = (
            "COMPUTED DCF MODEL:\n" + json.dumps(dcf_output, indent=2)
            if dcf_output and dcf_output.get("model_ran")
            else None
        )

        async def _write_sections() -> tuple[dict, dict, dict, dict, dict, dict, dict]:
            combined_with_figs = combined + figures_context if figures_context else combined
            results = await asyncio.gather(
                _with_retry(lambda: write_geology_section(combined_with_figs, run_id=run_id)),
                _with_retry(lambda: write_economics_section(combined_with_figs, run_id=run_id, extra_context=dcf_context)),
                _with_retry(lambda: write_risk_section(combined, run_id=run_id)),
                _with_retry(lambda: flag_missing_data(combined, run_id=run_id)),
                _with_retry(lambda: assess_confidence(combined, run_id=run_id)),
                _with_retry(lambda: flag_contradictions(combined, run_id=run_id, extra_context=dcf_context)),
                _with_retry(lambda: check_compliance(combined, run_id=run_id)),
            )
            return tuple(_extract_response_data(r) for r in results)

        geology, economics, risks, data_gaps, confidence, contradictions, compliance = asyncio.run(_write_sections())

        _save_section(project_id, run_id, "03_geology", geology)
        _save_section(project_id, run_id, "04_economics", economics)
        _save_section(project_id, run_id, "05_risks", risks)
        _save_section(project_id, run_id, "08_data_gaps", data_gaps)
        _save_section(project_id, run_id, "09_confidence", confidence)
        _save_section(project_id, run_id, "10_contradictions", contradictions)
        _save_section(project_id, run_id, "13_compliance", compliance)

        # ── Step 4: Assemble narrative synthesis ────────────────────────────
        update("Writing analyst narrative")

        from engine.llm.reporting.assemble_report_sections import assemble_report_sections

        assembly_input = json.dumps({
            "project_facts":      facts,
            "geology":            geology,
            "economics":          economics,
            "risks":              risks,
            "dcf_model":          dcf_output,
            "metallurgy":         met_data if met_data and not met_data.get("not_found") else None,
            "permitting":         permit_data if permit_data and not permit_data.get("not_found") else None,
            "operator":           operator_data if operator_data and not operator_data.get("not_found") else None,
            "capital_structure":  capstruct_data if capstruct_data and not capstruct_data.get("not_found") else None,
            "source_files":       source_files,
        }, indent=2)

        async def _assemble() -> dict:
            r = await _with_retry(lambda: assemble_report_sections(assembly_input, run_id=run_id))
            return _extract_response_data(r)

        assembly = asyncio.run(_assemble())
        _save_section(project_id, run_id, "07_assembly", assembly)

        # ── Step 4.5: Extract source citations ──────────────────────────────
        update("Extracting source citations")

        from engine.llm.extraction.extract_citations import extract_citations

        # Build a compact summary of what the report actually claimed
        report_sections_for_citation = json.dumps({
            "03_geology":   geology,
            "04_economics": economics,
            "05_risks":     risks,
            "06_dcf_model": dcf_output,
            "07_assembly":  assembly,
        }, indent=2)[:8000]  # cap to avoid token overflow

        citations_data: dict = {}
        try:
            async def _cite() -> dict:
                r = await _with_retry(lambda: extract_citations(
                    truncated,
                    run_id=run_id,
                    report_sections=report_sections_for_citation,
                ))
                return _extract_response_data(r)

            citations_data = asyncio.run(_cite())
        except Exception as cite_exc:
            citations_data = {
                "citations": [],
                "total_citations": 0,
                "not_found_count": 0,
                "citation_coverage_comment": f"Citation extraction failed: {cite_exc}",
                "uncited_sections": [],
            }

        _save_section(project_id, run_id, "11_citations", citations_data)

        # ── Step 5: Save data sources notice ───────────────────────────────
        update("Finalising report")

        render_files = [f.name for f in renders_dir.glob("*_render.png")] if renders_dir.exists() else []

        sources_notice = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "source_files": source_files,
            "file_count": len(source_files),
            "image_files": image_files,
            "render_files": render_files,
            "notice": (
                "This report was generated by AI from the source documents listed above. "
                "All figures and conclusions should be verified against the original documents. "
                "This report does not constitute investment advice or a formal technical study."
            ),
            "data_coverage": {
                "project_facts": bool(facts),
                "geology": bool(geology),
                "economics": bool(economics),
                "risks": bool(risks),
                "dcf_model_ran": bool(dcf_output and dcf_output.get("model_ran")),
                "narrative_assembled": bool(assembly),
                "contradictions_checked": bool(contradictions),
                "citations_extracted": bool(citations_data and citations_data.get("citations")),
                "jurisdiction_risk": bool(juris_data and not juris_data.get("not_found")),
                "compliance_checked": bool(compliance and compliance.get("overall_status")),
            }
        }
        _save_section(project_id, run_id, "00_data_sources", sources_notice)

        update("Complete", status="complete")

    except Exception as exc:
        import traceback
        update("failed", status="failed", error=f"{exc}\n{traceback.format_exc()[:500]}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/projects/{project_id}/analyze", response_model=RunStatus, status_code=202)
def start_analysis(
    project_id: str,
    body: AnalyzeRequest = AnalyzeRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> RunStatus:
    _project_exists(project_id)
    run_id = _generate_run_id()
    now = datetime.now(timezone.utc).isoformat()

    status_data = {
        "run_id": run_id,
        "project_id": project_id,
        "status": "pending",
        "started_at": now,
        "completed_at": None,
        "step": "queued",
        "error": None,
    }
    _save_run_status(project_id, run_id, status_data)

    t = threading.Thread(
        target=_run_analysis_in_background,
        args=(project_id, run_id),
        daemon=True,
    )
    t.start()

    return RunStatus(**status_data, output_files=[])


@router.get("/projects/{project_id}/runs", response_model=RunList)
def list_runs(project_id: str) -> RunList:
    _project_exists(project_id)
    runs_dir = project_root(project_id) / "runs"
    if not runs_dir.exists():
        return RunList(project_id=project_id, runs=[], total=0)

    runs = []
    for run_dir in sorted(runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        data = _load_run_status(project_id, run_dir.name)
        if not data:
            continue
        outputs = _collect_output_files(project_id, run_dir.name)
        runs.append(RunStatus(**data, output_files=outputs))

    return RunList(project_id=project_id, runs=runs, total=len(runs))


@router.get("/projects/{project_id}/runs/{run_id}", response_model=RunStatus)
def get_run(project_id: str, run_id: str) -> RunStatus:
    _project_exists(project_id)
    data = _load_run_status(project_id, run_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    outputs = _collect_output_files(project_id, run_id)
    return RunStatus(**data, output_files=outputs)


@router.get("/projects/{project_id}/runs/{run_id}/stream")
async def stream_run_status(project_id: str, run_id: str) -> StreamingResponse:
    """Server-sent events stream — pushes run status updates as they happen.

    The client subscribes with `new EventSource(url)`.  Each event is a JSON
    object matching the RunStatus schema.  The stream closes automatically when
    the run reaches `complete` or `failed`.
    """
    async def _event_gen():
        last_step: str | None = None
        last_status: str | None = None
        idle_ticks = 0
        while True:
            data = _load_run_status(project_id, run_id)
            step   = data.get("step")
            status = data.get("status")
            # Only push when something changed
            if step != last_step or status != last_status:
                yield f"data: {json.dumps(data)}\n\n"
                last_step, last_status = step, status
                idle_ticks = 0
            if status in ("complete", "failed"):
                break
            # Send a keep-alive comment every 15 s so proxies don't close the connection
            idle_ticks += 1
            if idle_ticks >= 30:  # 30 × 0.5 s = 15 s
                yield ": keep-alive\n\n"
                idle_ticks = 0
            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/projects/{project_id}/runs/{run_id}", status_code=204)
def delete_run(project_id: str, run_id: str) -> None:
    _project_exists(project_id)
    rdir = run_root(project_id, run_id)
    if not rdir.exists():
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    import shutil
    shutil.rmtree(rdir)

