#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/build_sidecar.sh
#
# Build the Python API server as a self-contained PyInstaller binary and
# copy the result into the Tauri bundle directory.
#
# Usage:
#   cd <project-root>
#   ./scripts/build_sidecar.sh
#
# Requirements:
#   - Python 3.12 virtualenv at .venv/ with all deps installed
#   - PyInstaller:  pip install pyinstaller
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"
TAURI_BINARIES="$REPO_ROOT/desktop/src-tauri/binaries/api-server"

echo "▶ Building API server sidecar"
echo "  Project root : $REPO_ROOT"
echo "  Output dir   : $TAURI_BINARIES"
echo

# ── Activate venv ─────────────────────────────────────────────────────────────
if [[ ! -f "$VENV/bin/python" ]]; then
  echo "✗ .venv not found at $VENV"
  echo "  Run:  python3.12 -m venv .venv && .venv/bin/pip install -e .[dev]"
  exit 1
fi

source "$VENV/bin/activate"

# ── Ensure PyInstaller is available ──────────────────────────────────────────
if ! python -c "import PyInstaller" 2>/dev/null; then
  echo "→ Installing PyInstaller…"
  pip install pyinstaller --quiet
fi

# ── Run PyInstaller ───────────────────────────────────────────────────────────
echo "→ Running PyInstaller…"
cd "$REPO_ROOT"
pyinstaller api_server.spec \
  --noconfirm \
  --clean

echo "→ PyInstaller output: $REPO_ROOT/dist/api-server/"

# ── Copy to Tauri binaries directory ─────────────────────────────────────────
echo "→ Copying to $TAURI_BINARIES"
rm -rf "$TAURI_BINARIES"
mkdir -p "$(dirname "$TAURI_BINARIES")"
cp -R "$REPO_ROOT/dist/api-server" "$TAURI_BINARIES"

echo
echo "✓ Sidecar built successfully"
echo "  $TAURI_BINARIES/api-server  ($(du -sh "$TAURI_BINARIES" | cut -f1) on disk)"
