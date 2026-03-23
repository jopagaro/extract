#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
# scripts/release.sh
# Build, sign, tag, and publish a new Extract release to GitHub.
#
# Usage:
#   ./scripts/release.sh 0.2.0 "Fixed report layout; improved PDF export"
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

VERSION="${1:?Usage: release.sh <version> <release-notes>}"
NOTES="${2:?Usage: release.sh <version> <release-notes>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── 0. Require env vars ──────────────────────────────────────────
: "${TAURI_PRIVATE_KEY:?Set TAURI_PRIVATE_KEY to the path of ~/.tauri/extract.key}"
export TAURI_KEY_PASSWORD="${TAURI_KEY_PASSWORD:-}"

# ── 1. Bump version in tauri.conf.json ──────────────────────────
CONF="$ROOT/desktop/src-tauri/tauri.conf.json"
sed -i '' "s/\"version\": \".*\"/\"version\": \"$VERSION\"/" "$CONF"
echo "✓ Bumped version to $VERSION"

# ── 2. Build the app ─────────────────────────────────────────────
source "$HOME/.cargo/env"
cd "$ROOT/desktop"
npx tauri build
echo "✓ App built"

BUNDLE="$ROOT/desktop/src-tauri/target/release/bundle"
DMG="$BUNDLE/dmg/Extract_${VERSION}_aarch64.dmg"
SIG="${DMG}.sig"

# ── 3. Sign the DMG ──────────────────────────────────────────────
SIGN_OUT=$(cd "$ROOT/desktop" && npx tauri signer sign "$DMG" --private-key "$TAURI_PRIVATE_KEY" --password "$TAURI_KEY_PASSWORD" 2>&1)
SIGNATURE=$(echo "$SIGN_OUT" | grep -o 'Signature:.*' | cut -d' ' -f2-)
echo "✓ Signed DMG"

# ── 4. Write latest.json ─────────────────────────────────────────
PUB_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
cat > "$ROOT/latest.json" <<EOF
{
  "version": "v${VERSION}",
  "notes": "${NOTES}",
  "pub_date": "${PUB_DATE}",
  "platforms": {
    "darwin-aarch64": {
      "signature": "${SIGNATURE}",
      "url": "https://github.com/jopagaro/mining-intelligence-engine/releases/download/v${VERSION}/Extract_${VERSION}_aarch64.dmg"
    }
  }
}
EOF
echo "✓ latest.json written"

# ── 5. Commit + tag ──────────────────────────────────────────────
cd "$ROOT"
git add desktop/src-tauri/tauri.conf.json latest.json
git commit -m "Release v${VERSION}"
git tag "v${VERSION}"
git push origin master
git push origin "v${VERSION}"
echo "✓ Committed and tagged v${VERSION}"

# ── 6. Create GitHub release with DMG attached ───────────────────
gh release create "v${VERSION}" "$DMG" "latest.json" \
  --title "Extract v${VERSION}" \
  --notes "$NOTES"
echo ""
echo "✅ Release v${VERSION} published!"
echo "   DMG: https://github.com/jopagaro/mining-intelligence-engine/releases/download/v${VERSION}/Extract_${VERSION}_aarch64.dmg"
