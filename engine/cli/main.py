"""
mip — Mining Intelligence Platform CLI

Entry point defined in pyproject.toml:
    [project.scripts]
    mip = "engine.cli.main:app"

Command structure:
    mip new <project_id>     — create a new project
    mip ingest add <path>    — ingest a file or directory into a project
    mip ingest status        — show what's been ingested
    mip analyze run          — run the analysis engine on a project
    mip status               — show project status and source summary
    mip projects             — list all projects in the configured root
    mip version              — print engine version

All commands that require a project accept --project / -p <project_id>.
"""

from __future__ import annotations

import typer
from typing_extensions import Annotated

from engine.cli.ingest import ingest_app
from engine.cli.analyze import analyze_app
from engine.core.logging import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="mip",
    help="Mining Intelligence Platform — project analysis and reporting engine.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.add_typer(ingest_app, name="ingest", help="Ingest raw files into a project.")
app.add_typer(analyze_app, name="analyze", help="Run the analysis engine on a project.")


# ---------------------------------------------------------------------------
# mip new
# ---------------------------------------------------------------------------

@app.command("new")
def cmd_new(
    project_id: Annotated[str, typer.Argument(help="Project slug (lowercase, underscores OK)")],
    name: Annotated[str, typer.Option("--name", "-n", help="Human-readable project name")] = "",
    company: Annotated[str, typer.Option("--company", "-c", help="Owner / operator company")] = "",
    location: Annotated[str, typer.Option("--location", "-l", help="Country or region")] = "",
    element: Annotated[str, typer.Option("--element", "-e", help="Primary element (e.g. Au, Cu)")] = "",
    mine_type: Annotated[str, typer.Option("--mine-type", help="open_pit / underground / heap_leach")] = "open_pit",
    study_level: Annotated[str, typer.Option("--study", help="pea / pfs / fs / scoping")] = "unknown",
    jurisdiction: Annotated[str, typer.Option("--jurisdiction", "-j", help="Fiscal jurisdiction slug")] = "",
) -> None:
    """Create a new mining project and initialise its folder structure."""
    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    try:
        from engine.project.bootstrap import bootstrap_project
        meta, config = bootstrap_project(
            project_id,
            name=name,
            company=company,
            location=location,
            primary_element=element,
            mine_type=mine_type,
            study_level=study_level,
            jurisdiction=jurisdiction,
        )
        console.print(Panel(
            f"[bold green]Project created[/bold green]\n\n"
            f"  ID:        [cyan]{meta.project_id}[/cyan]\n"
            f"  Name:      {meta.name}\n"
            f"  Element:   {config.primary_element or '(not set)'}\n"
            f"  Study:     {config.study_level}\n"
            f"  Status:    {meta.status}\n"
            f"  Run ID:    {meta.last_run_id}",
            title="[bold]mip new[/bold]",
            border_style="green",
        ))
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# mip status
# ---------------------------------------------------------------------------

@app.command("status")
def cmd_status(
    project_id: Annotated[str, typer.Argument(help="Project ID to inspect")],
) -> None:
    """Show project status, source summary, and last run info."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    try:
        from engine.project.project_manifest import read_project_metadata
        from engine.project.project_config import read_project_config
        from engine.project.source_registry import source_summary

        meta = read_project_metadata(project_id)
        config = read_project_config(project_id)
        summary = source_summary(project_id)

        console.print()
        console.print(f"[bold]Project:[/bold] {meta.name} [dim]({meta.project_id})[/dim]")
        console.print(f"[bold]Status:[/bold]  {meta.status}")
        console.print(f"[bold]Element:[/bold] {config.primary_element or '(not set)'}")
        console.print(f"[bold]Study:[/bold]   {config.study_level}")
        if meta.last_run_id:
            console.print(f"[bold]Last run:[/bold] {meta.last_run_id}")
        if meta.last_ingested_at:
            console.print(f"[bold]Last ingest:[/bold] {meta.last_ingested_at[:19]}")

        if summary["total_files"] > 0:
            console.print(f"\n[bold]Ingested sources[/bold] — {summary['total_files']} file(s):")
            tbl = Table(show_header=True, header_style="bold cyan", box=None)
            tbl.add_column("Category")
            tbl.add_column("Files", justify="right")
            for cat, count in summary["categories"].items():
                tbl.add_row(cat.replace("_", " "), str(count))
            console.print(tbl)
        else:
            console.print(
                "\n[dim]No files ingested yet. "
                "Use [bold]mip ingest add <path> --project " + project_id + "[/bold] to add data.[/dim]"
            )

    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# mip projects
# ---------------------------------------------------------------------------

@app.command("projects")
def cmd_projects() -> None:
    """List all projects in the configured projects root."""
    from rich.console import Console
    from rich.table import Table
    from engine.core.paths import get_projects_root
    from engine.project.project_manifest import read_project_metadata

    console = Console()
    root = get_projects_root()

    if not root.exists():
        console.print(f"[yellow]Projects root does not exist: {root}[/yellow]")
        console.print("Set MINING_PROJECTS_ROOT environment variable or create the directory.")
        raise typer.Exit()

    project_dirs = [d for d in sorted(root.iterdir()) if d.is_dir()]
    if not project_dirs:
        console.print(f"[dim]No projects found in {root}[/dim]")
        raise typer.Exit()

    tbl = Table(show_header=True, header_style="bold cyan")
    tbl.add_column("Project ID")
    tbl.add_column("Name")
    tbl.add_column("Element")
    tbl.add_column("Status")
    tbl.add_column("Last Run")

    for pdir in project_dirs:
        try:
            meta = read_project_metadata(pdir.name)
            tbl.add_row(
                meta.project_id,
                meta.name or "—",
                meta.primary_element or "—",
                meta.status,
                (meta.last_run_id or "—")[-22:],
            )
        except Exception:
            tbl.add_row(pdir.name, "—", "—", "unknown", "—")

    console.print(f"\n[bold]Projects root:[/bold] {root}\n")
    console.print(tbl)


# ---------------------------------------------------------------------------
# mip version
# ---------------------------------------------------------------------------

@app.command("version")
def cmd_version() -> None:
    """Print the engine version."""
    from engine.core.constants import ENGINE_VERSION
    typer.echo(f"mip {ENGINE_VERSION}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()
