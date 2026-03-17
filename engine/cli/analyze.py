"""
mip analyze — analysis engine commands.

Sub-commands:
    mip analyze run --project <id>   — run the full LLM extraction pipeline
    mip analyze runs --project <id>  — list past runs for a project

The ``run`` command:
  1. Verifies the project has staged documents (from ``mip ingest add``).
  2. Creates a tracked run record (run_manager).
  3. For each staged section JSON file, sends the text to the LLM extraction
     layer (``extract_project_facts``) via asyncio.run().
  4. Writes JSON results to  <project>/normalized/interpreted/project_facts/.
  5. Marks the run complete / failed and updates project metadata.

LLM calls require at least one API key:
    ANTHROPIC_API_KEY   or   OPENAI_API_KEY
Set them in a .env file at the platform root or in the shell environment.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from engine.core.logging import get_logger

log = get_logger(__name__)

analyze_app = typer.Typer(
    name="analyze",
    help="Run the analysis engine on a project.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# mip analyze run
# ---------------------------------------------------------------------------

@analyze_app.command("run")
def cmd_analyze_run(
    project: Annotated[str, typer.Argument(help="Project ID to analyse")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Re-extract even if output already exists")] = False,
    step: Annotated[Optional[str], typer.Option("--step", help="Run only a specific extraction step (project_facts)")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be extracted without calling the LLM")] = False,
) -> None:
    """Run the LLM extraction pipeline on all staged documents."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn

    console = Console()

    # ---- Verify project exists ----------------------------------------------
    try:
        from engine.project.project_manifest import read_project_metadata
        meta = read_project_metadata(project)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Could not load project '{project}': {exc}")
        raise typer.Exit(code=1)

    # ---- Find staged section files ------------------------------------------
    from engine.core.paths import project_normalized
    staging_dir = project_normalized(project) / "staging" / "entity_extraction" / "project_facts"

    if not staging_dir.exists():
        console.print(
            f"\n[yellow]No staged documents found for project:[/yellow] [cyan]{project}[/cyan]\n"
            f"Run [bold]mip ingest add <path> -p {project}[/bold] first to ingest documents.\n"
        )
        raise typer.Exit()

    section_files = sorted(staging_dir.glob("*_sections.json"))
    if not section_files:
        console.print(
            f"\n[yellow]No section files found in staging area.[/yellow]\n"
            f"Staging directory: {staging_dir}\n"
            f"Run [bold]mip ingest add <path> -p {project}[/bold] to stage documents.\n"
        )
        raise typer.Exit()

    # ---- Dry run: just list what would be processed -------------------------
    if dry_run:
        console.print(f"\n[bold]Dry run — would extract from {len(section_files)} file(s):[/bold]\n")
        for sf in section_files:
            data = _load_json_safe(sf)
            n_sections = data.get("section_count", "?")
            console.print(f"  [cyan]{sf.name}[/cyan]  ({n_sections} sections)")
        console.print()
        return

    # ---- Check LLM config ---------------------------------------------------
    try:
        from engine.core.config import settings
        if not settings.has_anthropic and not settings.has_openai:
            console.print(
                "[bold red]Error:[/bold red] No LLM API keys configured.\n"
                "Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env file."
            )
            raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] Could not load LLM config: {exc}")
        raise typer.Exit(code=1)

    # ---- Create and start run -----------------------------------------------
    from engine.core.ids import run_id as make_run_id
    from engine.runs.run_manager import create_run, start_run, complete_run, fail_run

    run_id = make_run_id(project)
    create_run(project, run_id, config={"step": step or "all", "force": force})
    start_run(project, run_id)

    console.print(Panel(
        f"[bold]Project:[/bold] [cyan]{project}[/cyan]  ({meta.name or ''})\n"
        f"[bold]Run ID:[/bold]  {run_id}\n"
        f"[bold]Files:[/bold]   {len(section_files)} staged document(s)",
        title="[bold]mip analyze run[/bold]",
        border_style="blue",
    ))

    # ---- Output directory ---------------------------------------------------
    output_dir = project_normalized(project) / "interpreted" / "project_facts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Run extractions ----------------------------------------------------
    from engine.llm.extraction.extract_project_facts import extract_project_facts

    results_ok: list[str] = []
    results_skipped: list[str] = []
    results_failed: list[tuple[str, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        ptask = progress.add_task("Extracting…", total=None)

        for sf in section_files:
            stem = sf.stem.replace("_sections", "")
            out_path = output_dir / f"{stem}_extracted.json"

            if out_path.exists() and not force:
                results_skipped.append(sf.name)
                progress.update(ptask, description=f"[yellow]skip[/yellow] {sf.name}")
                continue

            progress.update(ptask, description=f"[cyan]{sf.name}[/cyan]")

            try:
                section_data = _load_json_safe(sf)
                sections = section_data.get("sections", [])
                source_file = section_data.get("source_file", sf.name)

                if not sections:
                    results_skipped.append(sf.name)
                    continue

                # Concatenate all section texts into one extraction pass
                # (for large docs this should be done per-section; for now batch)
                combined_text = "\n\n---\n\n".join(
                    f"## {s.get('title', '')}\n\n{s.get('text', '')}"
                    for s in sections
                )

                response = asyncio.run(
                    extract_project_facts(
                        combined_text,
                        run_id=run_id,
                        extra_context=f"Source document: {source_file}",
                    )
                )

                # Write output
                payload = {
                    "project_id": project,
                    "run_id": run_id,
                    "source_file": source_file,
                    "section_count": len(sections),
                    "extracted": response.merged if hasattr(response, "merged") else response.to_dict() if hasattr(response, "to_dict") else str(response),
                    "disagreements": response.disagreements if hasattr(response, "disagreements") else [],
                    "providers_used": response.providers if hasattr(response, "providers") else [],
                }
                out_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                results_ok.append(sf.name)

            except Exception as exc:
                log.error("Extraction failed for %s: %s", sf.name, exc, exc_info=True)
                results_failed.append((sf.name, str(exc)))

    # ---- Finalise run -------------------------------------------------------
    if results_failed and not results_ok:
        fail_run(project, run_id, reason=f"{len(results_failed)} extraction(s) failed")
        outcome = "failed"
    else:
        from engine.project.project_manifest import update_project_metadata
        from engine.core.enums import ProjectStatus
        update_project_metadata(
            project,
            last_run_id=run_id,
            status=ProjectStatus.ANALYSED.value if hasattr(ProjectStatus, "ANALYSED") else "analysed",
        )
        complete_run(project, run_id)
        outcome = "complete"

    # ---- Summary ------------------------------------------------------------
    console.print()
    tbl = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    tbl.add_column("File")
    tbl.add_column("Result")

    for name in results_ok:
        tbl.add_row(name, "[green]extracted[/green]")
    for name in results_skipped:
        tbl.add_row(name, "[yellow]skipped (exists)[/yellow]")
    for name, err in results_failed:
        tbl.add_row(name, f"[red]failed[/red]")

    console.print(tbl)
    console.print()
    console.print(
        f"  [green]✓ {len(results_ok)} extracted[/green]  "
        f"[yellow]⊘ {len(results_skipped)} skipped[/yellow]  "
        f"[red]✗ {len(results_failed)} failed[/red]  "
        f"— run {outcome}: [dim]{run_id}[/dim]"
    )

    for name, err in results_failed:
        console.print(f"  [red]error:[/red] {name}: {err}")

    console.print()

    if outcome == "failed":
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# mip analyze runs
# ---------------------------------------------------------------------------

@analyze_app.command("runs")
def cmd_analyze_runs(
    project: Annotated[str, typer.Argument(help="Project ID")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum runs to show")] = 10,
) -> None:
    """List recent analysis runs for a project."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        from engine.runs.run_manager import list_runs
        runs = list_runs(project)
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    if not runs:
        console.print(f"\n[dim]No runs found for project:[/dim] [cyan]{project}[/cyan]\n")
        return

    runs = runs[:limit]
    console.print(f"\n[bold]Runs for project:[/bold] [cyan]{project}[/cyan]\n")

    tbl = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    tbl.add_column("Run ID")
    tbl.add_column("Status")
    tbl.add_column("Created")
    tbl.add_column("Completed")

    _STATUS_COLORS = {
        "complete": "green",
        "running": "blue",
        "failed": "red",
        "pending": "yellow",
    }

    for r in runs:
        status = r.get("status", "unknown")
        color = _STATUS_COLORS.get(status, "white")
        created = (r.get("created_at") or "")[:19].replace("T", " ")
        completed = (r.get("completed_at") or r.get("failed_at") or "—")[:19].replace("T", " ")
        tbl.add_row(
            r.get("run_id", "—"),
            f"[{color}]{status}[/{color}]",
            created,
            completed,
        )

    console.print(tbl)
    console.print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json_safe(path: Path) -> dict:
    """Load a JSON file, returning an empty dict on error."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
