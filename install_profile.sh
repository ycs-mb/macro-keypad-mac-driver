#!/usr/bin/env bash
# Installs / updates the "INSTANT 19-Key Macro Pad" profile in Karabiner-Elements.
#
# Idempotent: safe to run repeatedly — produces the same result each time.
# Backs up the live config before writing. Run after Karabiner-Elements is
# installed and has been launched at least once.
#
# Input: karabiner_profile.json (next to this script), shape: { "manipulators": [...] }
#        — this is exactly what index.html's Export button produces.

set -euo pipefail

PROFILE_NAME="INSTANT 19-Key Macro Pad"
VENDOR_ID=12538
PRODUCT_ID=9040

KARABINER_CONFIG="$HOME/.config/karabiner/karabiner.json"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROFILE_SRC="$SCRIPT_DIR/karabiner_profile.json"
BACKUP_DIR="$SCRIPT_DIR/backups"

if [[ ! -f "$KARABINER_CONFIG" ]]; then
  echo "ERROR: $KARABINER_CONFIG not found."
  echo "Install Karabiner-Elements and launch it once first."
  exit 1
fi
if [[ ! -f "$PROFILE_SRC" ]]; then
  echo "ERROR: $PROFILE_SRC not found (the exported key map)."
  exit 1
fi

# --- Self-backup before any write ---
mkdir -p "$BACKUP_DIR"
TS="$(date +%Y%m%d-%H%M%S)"
cp "$KARABINER_CONFIG" "$BACKUP_DIR/karabiner.json.$TS.bak"
echo "Backed up live config -> $BACKUP_DIR/karabiner.json.$TS.bak"

python3 - "$KARABINER_CONFIG" "$PROFILE_SRC" "$PROFILE_NAME" "$VENDOR_ID" "$PRODUCT_ID" <<'PYEOF'
import json, sys

config_path, profile_src, profile_name = sys.argv[1], sys.argv[2], sys.argv[3]
vid, pid = int(sys.argv[4]), int(sys.argv[5])

with open(config_path) as f:
    config = json.load(f)
with open(profile_src) as f:
    src = json.load(f)

manipulators = src.get("manipulators")
if not isinstance(manipulators, list) or not manipulators:
    sys.exit("ERROR: %s has no non-empty 'manipulators' array." % profile_src)

profiles = config.setdefault("profiles", [])
prof = next((p for p in profiles if p.get("name") == profile_name), None)
if prof is None:
    prof = {"name": profile_name}
    profiles.append(prof)
    action = "Added"
else:
    action = "Updated"

# Replace this profile's rules with one canonical, ENABLED rule.
prof.setdefault("complex_modifications", {})["rules"] = [{
    "description": profile_name,
    "enabled": True,
    "manipulators": manipulators,
}]

# Normalize devices: keep non-pad entries; collapse the pad to a single entry
# with ignore=false (Modify events ON) and no stray simple_modifications.
pad, other = [], []
for d in prof.get("devices", []):
    idn = d.get("identifiers", {})
    (pad if idn.get("vendor_id") == vid and idn.get("product_id") == pid else other).append(d)
if pad:
    base = next((d for d in pad if d.get("identifiers", {}).get("is_pointing_device")), pad[0])
    ident = dict(base.get("identifiers", {}))
else:
    ident = {}
ident["is_keyboard"] = True
ident["vendor_id"] = vid
ident["product_id"] = pid
prof["devices"] = other + [{"identifiers": ident, "ignore": False}]

# Defaults / selection (preserve any other profile fields untouched).
prof.setdefault("virtual_hid_keyboard", {"keyboard_type_v2": "ansi"})
prof["selected"] = True
for p in profiles:
    if p is not prof and isinstance(p, dict) and p.get("selected"):
        p["selected"] = False
config["selected"] = profile_name

out = json.dumps(config, indent=4)
json.loads(out)  # validate before writing
with open(config_path, "w") as f:
    f.write(out + "\n")

print("%s profile '%s' (%d keys, rule active, device ignore=false, selected)."
      % (action, profile_name, len(manipulators)))
PYEOF

# --- Best-effort live reload ---
CLI="/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli"
if [[ -x "$CLI" ]]; then
  "$CLI" --select-profile "$PROFILE_NAME" >/dev/null 2>&1 || true
  echo "Asked Karabiner-Elements to select '$PROFILE_NAME'."
else
  echo "Karabiner-Elements reloads automatically when the file changes."
fi

echo "Done."
