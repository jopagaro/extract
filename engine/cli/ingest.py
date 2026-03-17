"""
mip ingest — file ingestion commands.

Sub-commands:
    mip ingest add <path> --project <id>   — ingest a file or directory
    mip ingest status --project <id>       — show what's been ingested

The ``add`` command routes every file through ``ingest_document()`` which
handles parsing for known formats (PDF, XLSX, DOCX, TXT) and falls back to
bare registry-only registration for everything else (CAD, GIS, photos, etc.).

All registry entries are persisted to:
    <project>/normalized/metadata/source_manifest.json
"""

from __future__ import annotations

import typer
from pathlib import Path
from typing import Annotated, Optional

from engine.core.logging import get_logger

log = get_logger(__name__)

ingest_app = typer.Typer(
    name="ingest",
    help="Ingest raw files into a project.",
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# mip ingest add
# ---------------------------------------------------------------------------

@ingest_app.command("add")
def cmd_ingest_add(
    path: Annotated[Path, typer.Argument(help="File or directory to ingest")],
    project: Annotated[str, typer.Option("--project", "-p", help="Project ID")] = "",
    force: Annotated[bool, typer.Option("--force", "-f", help="Re-ingest even if already ingested")] = False,
    no_tables: Annotated[bool, typer.Option("--no-tables", help="Skip table extraction")] = False,
    no_sections: Annotated[bool, typer.Option("--no-sections", help="Skip section splitting")] = False,
    max_pages: Annotated[Optional[int], typer.Option("--max-pages", help="Only parse first N pages of PDFs")] = None,
    recurse: Annotated[bool, typer.Option("--recurse", "-r", help="Recurse into sub-directories")] = True,
) -> None:
    """Ingest a file or directory of files into a project."""
    from rich.console import Console
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    console = Console()

    if not project:
        console.print("[bold red]Error:[/bold red] --project / -p is required.")
        raise typer.Exit(code=1)

    path = path.resolve()
    if not path.exists():
        console.print(f"[bold red]Error:[/bold red] Path does not exist: {path}")
        raise typer.Exit(code=1)

    # ---- Gather files -------------------------------------------------------
    if path.is_file():
        files = [path]
    elif path.is_dir():
        if recurse:
            files = [
                f for f in sorted(path.rglob("*"))
                if f.is_file() and not f.name.startswith(".")
            ]
        else:
            files = [
                f for f in sorted(path.iterdir())
                if f.is_file() and not f.name.startswith(".")
            ]
    else:
        console.print(f"[bold red]Error:[/bold red] Not a file or directory: {path}")
        raise typer.Exit(code=1)

    if not files:
        console.print(f"[yellow]No files found at:[/yellow] {path}")
        raise typer.Exit()

    console.print(f"\n[bold]Ingesting {len(files)} file(s) into project:[/bold] [cyan]{project}[/cyan]\n")

    # ---- Ingest each file ---------------------------------------------------
    from engine.ingest.document_ingest import ingest_document

    results_ok: list = []
    results_skipped: list = []
    results_failed: list = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Ingesting…", total=len(files))

        for file_path in files:
            progress.update(task, description=f"[cyan]{file_path.name}[/cyan]")
            try:
                result = ingest_document(
                    project_id=project,
                    file_path=file_path,
                    force=force,
                    extract_tables=not no_tables,
                    split_sections=not no_sections,
                    max_pages=max_pages,
                )
                if result.status == "ok":
                    results_ok.append(result)
                elif result.status == "skipped":
                    results_skipped.append(result)
                else:
                    results_failed.append(result)
            except Exception as exc:
                log.error("Unexpected error ingesting %s: %s", file_path.name, exc, exc_info=True)
                results_failed.append(_fake_failed_result(project, file_path, str(exc)))
            progress.advance(task)

    # ---- Summary table ------------------------------------------------------
    console.print()

    tbl = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    tbl.add_column("File")
    tbl.add_column("Status")
    tbl.add_column("Category")
    tbl.add_column("Parser")
    tbl.add_column("Pages", justify="right")
    tbl.add_column("Tables", justify="right")
    tbl.add_column("Sections", justify="right")
    tbl.add_column("Words", justify="right")

    for r in results_ok:
        tbl.add_row(
            r.file_name,
            "[green]ok[/green]",
            r.category,
            r.parser_used or "—",
            str(r.page_count) if r.page_count else "—",
            str(r.table_count) if r.table_count else "—",
            str(r.section_count) if r.section_count else "—",
            str(r.word_count) if r.word_count else "—",
        )
    for r in results_skipped:
        tbl.add_row(
            r.file_name,
            "[yellow]skipped[/yellow]",
            r.category or "—",
            "—", "—", "—", "—", "—",
        )
    for r in results_failed:
        tbl.add_row(
            r.file_name,
            "[red]failed[/red]",
            r.category or "—",
            "—", "—", "—", "—", "—",
        )

    console.print(tbl)
    console.print()
    console.print(
        f"  [green]✓ {len(results_ok)} ingested[/green]  "
        f"[yellow]⊘ {len(results_skipped)} skipped[/yellow]  "
        f"[red]✗ {len(results_failed)} failed[/red]"
    )

    # Print warnings and errors
    for r in results_ok:
        for w in r.warnings:
            console.print(f"  [yellow]warn:[/yellow] {r.file_name}: {w}")
    for r in results_failed:
        if r.error:
            console.print(f"  [red]error:[/red] {r.file_name}: {r.error}")

    console.print()

    if results_failed:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# mip ingest status
# ---------------------------------------------------------------------------

@ingest_app.command("status")
def cmd_ingest_status(
    project: Annotated[str, typer.Argument(help="Project ID to inspect")],
) -> None:
    """Show all ingested files in a project's source registry."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    try:
        from engine.io.file_registry import load_registry

        entries = load_registry(project)
        if not entries:
            console.print(f"\n[dim]No files ingested yet for project:[/dim] [cyan]{project}[/cyan]")
            console.print(
                f"[dim]Use [bold]mip ingest add <path> -p {project}[/bold] to add data.[/dim]\n"
            )
            return

        console.print(f"\n[bold]Source registry:[/bold] [cyan]{project}[/cyan] — {len(entries)} file(s)\n")

        tbl = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
        tbl.add_column("Source ID")
        tbl.add_column("File")
        tbl.add_column("Category")
        tbl.add_column("Ext")
        tbl.add_column("Size", justify="right")
        tbl.add_column("Ingested")

        for e in sorted(entries, key=lambda x: x.ingested_at):
            size_str = _human_size(e.file_size_bytes)
            ingested_str = e.ingested_at[:19].replace("T", " ")
            tbl.add_row(
                e.source_id,
                Path(e.file_path).name,
                e.category,
                e.extension,
                size_str,
                ingested_str,
            )

        console.print(tbl)
        console.print()

    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _human_size(n: int) -> str:
    """Return a human-readable file size string."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _fake_failed_result(project_id: str, file_path: Path, error: str):
    """Create a minimal failed DocumentIngestResult for display purposes."""
    from engine.ingest.document_ingest import DocumentIngestResult
    r = DocumentIngestResult(
        project_id=project_id,
        file_path=str(file_path),
        file_name=file_path.name,
        status="failed",
        error=error,
    )
    return r
