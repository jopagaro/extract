#!/usr/bin/env bash
# Run before `tauri build`. Builds PyInstaller sidecar only if missing.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAC_EXE="$REPO_ROOT/desktop/src-tauri/binaries/api-server/api-server"
WIN_EXE="$REPO_ROOT/desktop/src-tauri/binaries/api-server/api-server.exe"

if [[ -x "$MAC_EXE" ]] || [[ -f "$WIN_EXE" ]]; then
  echo "[ensure_sidecar] Bundled API already present — skipping PyInstaller."
  exit 0
fi

echo "[ensure_sidecar] No api-server bundle — running scripts/build_sidecar.sh"
echo "[ensure_sidecar] (First run can take several minutes.)"
exec bash "$REPO_ROOT/scripts/build_sidecar.sh"
