#!/usr/bin/env bash
# Install Hammerspoon and set up the macro pad config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HS_DIR="$HOME/.hammerspoon"

echo "=== MacroPad Hammerspoon Setup ==="

# 1. Install Hammerspoon
if [ -d "/Applications/Hammerspoon.app" ]; then
  echo "✓ Hammerspoon already installed"
else
  echo "→ Installing Hammerspoon..."
  brew install --cask hammerspoon
fi

# 2. Create ~/.hammerspoon if needed
mkdir -p "$HS_DIR"

# 3. Install / update the macro pad module
cp "$SCRIPT_DIR/hammerspoon_macropad.lua" "$HS_DIR/macropad.lua"
echo "✓ Copied macropad.lua → $HS_DIR/macropad.lua"

# 4. Add require line to init.lua if not already there
INIT="$HS_DIR/init.lua"
touch "$INIT"
if grep -q 'require("macropad")' "$INIT" 2>/dev/null; then
  echo "✓ init.lua already requires macropad"
else
  echo '' >> "$INIT"
  echo '-- MacroPad (INSTANT 19-key)' >> "$INIT"
  echo 'require("macropad")' >> "$INIT"
  echo "✓ Added require(\"macropad\") to $INIT"
fi

echo ""
echo "=== Next steps ==="
echo "1. Open Hammerspoon from Applications"
echo "2. Click the menubar icon → 'Open Accessibility Preferences'"
echo "   Enable Hammerspoon in System Settings > Privacy & Security > Accessibility"
echo "3. Click 'Reload Config' from the menubar icon"
echo "4. You should see an alert: 'MacroPad loaded — pad CONNECTED'"
echo ""
echo "To customize keys: edit $HS_DIR/macropad.lua"
echo "then click Hammerspoon menubar → Reload Config"
