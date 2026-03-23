#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/build_app.sh
#
# Full pipeline: sidecar → React build → Tauri bundle.
# Produces a distributable .dmg (macOS), .msi/.exe (Windows), or .AppImage
# (Linux) in desktop/src-tauri/target/release/bundle/.
#
# Usage (macOS, unsigned/unsigned):
#   ./scripts/build_app.sh
#
# Usage (macOS, signed + notarised for distribution):
#   APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)" \
#   APPLE_ID="you@example.com" \
#   APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx" \   # App-specific password
#   APPLE_TEAM_ID="XXXXXXXXXX" \
#   ./scripts/build_app.sh --sign
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIGN=false

for arg in "$@"; do
  [[ "$arg" == "--sign" ]] && SIGN=true
done

echo "═══════════════════════════════════════"
echo "  Extract — App Build"
echo "  Root: $REPO_ROOT"
[[ "$SIGN" == "true" ]] && echo "  Mode: signed + notarised"
echo "═══════════════════════════════════════"
echo

# ── 1. Build Python sidecar ───────────────────────────────────────────────────
echo "[ 1/4 ] Building Python API server sidecar…"
"$REPO_ROOT/scripts/build_sidecar.sh"
echo

# ── 2. Install JS dependencies ────────────────────────────────────────────────
echo "[ 2/4 ] Installing JS dependencies…"
cd "$REPO_ROOT"
pnpm install --frozen-lockfile
echo

# ── 3. Build React frontend ───────────────────────────────────────────────────
echo "[ 3/4 ] Building React frontend…"
pnpm --filter web build
echo

# ── 4. Build Tauri app ────────────────────────────────────────────────────────
echo "[ 4/4 ] Building Tauri desktop app…"
cd "$REPO_ROOT"

if [[ "$SIGN" == "true" ]]; then
  # Signed build — requires Apple Developer credentials in environment
  : "${APPLE_SIGNING_IDENTITY:?Set APPLE_SIGNING_IDENTITY for signed build}"
  : "${APPLE_ID:?Set APPLE_ID for notarisation}"
  : "${APPLE_PASSWORD:?Set APPLE_PASSWORD (app-specific) for notarisation}"
  : "${APPLE_TEAM_ID:?Set APPLE_TEAM_ID for notarisation}"

  pnpm --filter desktop tauri build
else
  # Unsigned local build (good for testing, not for distribution via Gatekeeper)
  pnpm --filter desktop tauri build -- --config '{"tauri":{"bundle":{"macOS":{"signingIdentity":null}}}}'
fi

echo
echo "═══════════════════════════════════════"
echo "  ✓ Build complete"
BUNDLE_DIR="$REPO_ROOT/desktop/src-tauri/target/release/bundle"
if [[ -d "$BUNDLE_DIR" ]]; then
  echo
  echo "  Artifacts:"
  find "$BUNDLE_DIR" -name "*.dmg" -o -name "*.msi" -o -name "*.exe" \
    -o -name "*.AppImage" -o -name "*.deb" 2>/dev/null \
    | while read -r f; do
        echo "    $(du -sh "$f" | cut -f1)  $f"
      done
fi
echo "═══════════════════════════════════════"
