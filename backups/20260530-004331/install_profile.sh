#!/usr/bin/env bash
# Installs the macro pad profile into Karabiner-Elements config.
# Run after Karabiner-Elements is installed and launched once.

set -euo pipefail

KARABINER_CONFIG="$HOME/.config/karabiner/karabiner.json"
PROFILE_SRC="$(cd "$(dirname "$0")" && pwd)/karabiner_profile.json"

if [[ ! -f "$KARABINER_CONFIG" ]]; then
  echo "ERROR: $KARABINER_CONFIG not found."
  echo "Install Karabiner-Elements and launch it once first."
  exit 1
fi

python3 - "$KARABINER_CONFIG" "$PROFILE_SRC" <<'PYEOF'
import json, sys

config_path, profile_src = sys.argv[1], sys.argv[2]
profile_name = "INSTANT 19-Key Macro Pad"

with open(config_path) as f:
    config = json.load(f)

with open(profile_src) as f:
    rules_data = json.load(f)

new_profile = {
    "name": profile_name,
    "virtual_hid_keyboard": {"keyboard_type_v2": "ansi"},
    "complex_modifications": {
        "rules": [
            {
                "description": profile_name,
                "manipulators": rules_data["manipulators"]
            }
        ]
    }
}

profiles = config.setdefault("profiles", [])
replaced = False
for i, p in enumerate(profiles):
    if p.get("name") == profile_name:
        profiles[i] = new_profile
        replaced = True
        break

if not replaced:
    profiles.append(new_profile)

# Make it the selected profile
config["selected"] = profile_name

with open(config_path, "w") as f:
    json.dump(config, f, indent=4)

action = "Updated" if replaced else "Added"
print(f"{action} profile '{profile_name}' in Karabiner config.")
print("Switch to it in Karabiner-Elements > Profiles tab if not auto-selected.")
PYEOF
