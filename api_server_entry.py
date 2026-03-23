"""
Standalone entry point for the Extract API server.

This module is used by PyInstaller to produce the bundled `api-server`
binary that ships inside the Tauri desktop app.  It is NOT used during
normal development (uvicorn is invoked directly there).

At startup it:
  1. Calls multiprocessing.freeze_support() — required on Windows when frozen.
  2. Sets MINING_PROJECTS_ROOT to ~/Documents/Extract Projects if not already set.
  3. Sets EXTRACT_DATA_DIR to ~/Library/Application Support/com.extract.app
     (or platform equivalent) if not already set by the Tauri shell.
  4. Starts the FastAPI app via uvicorn on 127.0.0.1:8000.
"""
from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path


def _default_data_dir() -> Path:
    """Platform-appropriate application data directory."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "com.extract.app"
    elif sys.platform == "win32":
        appdata = os.getenv("APPDATA") or str(Path.home())
        return Path(appdata) / "com.extract.app"
    else:
        return Path.home() / ".config" / "com.extract.app"


def _default_projects_dir() -> Path:
    return Path.home() / "Documents" / "Extract Projects"


def main() -> None:
    # Required for multiprocessing in frozen Windows executables
    multiprocessing.freeze_support()

    # ── Data directory (settings, etc.) ──────────────────────────────────────
    if not os.getenv("EXTRACT_DATA_DIR"):
        data_dir = _default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ["EXTRACT_DATA_DIR"] = str(data_dir)

    # ── Project data directory ────────────────────────────────────────────────
    if not os.getenv("MINING_PROJECTS_ROOT"):
        projects_dir = _default_projects_dir()
        projects_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MINING_PROJECTS_ROOT"] = str(projects_dir)

    # ── Start the API server ──────────────────────────────────────────────────
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        # Disable reload — not compatible with frozen executables
        reload=False,
    )


if __name__ == "__main__":
    main()
