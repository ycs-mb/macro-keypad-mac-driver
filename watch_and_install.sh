#!/usr/bin/env bash
# watch_and_install.sh — Watches karabiner_profile.json for changes and
# auto-runs install_profile.sh when the file is updated.
#
# Start once in Terminal:
#     bash ~/Developer/macro-keypad/watch_and_install.sh
#
# Then every time you Export from index.html (saving to this folder),
# the profile is applied to Karabiner automatically — no manual steps.
#
# Press Ctrl+C to stop watching.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE="$SCRIPT_DIR/karabiner_profile.json"
INSTALLER="$SCRIPT_DIR/install_profile.sh"

if [[ ! -f "$INSTALLER" ]]; then
  echo "ERROR: $INSTALLER not found."
  exit 1
fi

LAST_HASH=""
POLL_INTERVAL=2

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  MacroPad · Auto-Installer                              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Watching: $PROFILE"
echo "  Polling every ${POLL_INTERVAL}s for changes."
echo "  Press Ctrl+C to stop."
echo ""

# Capture initial hash so we don't install on first run.
if [[ -f "$PROFILE" ]]; then
  LAST_HASH="$(shasum "$PROFILE" 2>/dev/null | cut -d' ' -f1)"
  echo "  Current hash: ${LAST_HASH:0:12}…"
fi
echo ""

while true; do
  if [[ -f "$PROFILE" ]]; then
    HASH="$(shasum "$PROFILE" 2>/dev/null | cut -d' ' -f1)"
    if [[ -n "$HASH" && "$HASH" != "$LAST_HASH" && -n "$LAST_HASH" ]]; then
      echo "───────────────────────────────────────────────────────"
      echo "  ⚡ Change detected at $(date +%H:%M:%S)"
      echo "───────────────────────────────────────────────────────"
      bash "$INSTALLER"
      echo ""
      echo "  ✅ Profile applied. Waiting for next change…"
      echo ""
    fi
    LAST_HASH="$HASH"
  fi
  sleep "$POLL_INTERVAL"
done
