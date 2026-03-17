"""
engine.cli — command-line interface for the Mining Intelligence Platform.

Entry point defined in pyproject.toml:
    [project.scripts]
    mip = "engine.cli.main:app"

Command groups:
    mip new          — create a new project
    mip ingest       — file ingestion sub-commands
    mip analyze      — analysis engine sub-commands
    mip status       — project status summary
    mip projects     — list all projects
    mip version      — print engine version
"""
