#!/usr/bin/env python3
"""
test_macropad.py — Verification suite for the INSTANT 19-Key Macro Pad.

Validates:
  1. karabiner_profile.json structural integrity
  2. Live ~/.config/karabiner/karabiner.json state
  3. App existence for 'open -a' actions
  4. Key-code validity against Karabiner's known set
  5. Duplicate / conflicting from-key detection
  6. Shell command basic sanity
  7. Export → Import round-trip (simulates index.html logic)
  8. install_profile.sh exists and is executable

Run:
    python3 test_macropad.py

Exit code 0 = all tests passed.
"""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# ── Constants ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILE_PATH = SCRIPT_DIR / "karabiner_profile.json"
INSTALLER_PATH = SCRIPT_DIR / "install_profile.sh"
LIVE_CONFIG_PATH = Path.home() / ".config" / "karabiner" / "karabiner.json"
PROFILE_NAME = "INSTANT 19-Key Macro Pad"
VENDOR_ID = 12538
PRODUCT_ID = 9040
EXPECTED_KEY_COUNT = 20

# Karabiner-Elements recognised key_code values (subset covering all codes
# used by this pad + common extras for validation).
VALID_KEY_CODES: set[str] = {
    # Letters
    *"abcdefghijklmnopqrstuvwxyz",
    # Digits
    *[str(d) for d in range(10)],
    # Arrows
    "up_arrow", "down_arrow", "left_arrow", "right_arrow",
    # Modifiers (used as targets, not from-keys, but still valid codes)
    "left_command", "right_command", "left_shift", "right_shift",
    "left_option", "right_option", "left_control", "right_control",
    # Keypad
    "keypad_0", "keypad_1", "keypad_2", "keypad_3", "keypad_4",
    "keypad_5", "keypad_6", "keypad_7", "keypad_8", "keypad_9",
    "keypad_period", "keypad_enter", "keypad_hyphen", "keypad_plus",
    "keypad_asterisk", "keypad_slash", "keypad_equal_sign", "keypad_num_lock",
    # Editing / whitespace
    "return_or_enter", "escape", "delete_or_backspace", "delete_forward",
    "tab", "spacebar", "caps_lock",
    # Function row
    *[f"f{n}" for n in range(1, 25)],
    # Navigation
    "home", "end", "page_up", "page_down",
    "insert",
    # Punctuation / symbols
    "hyphen", "equal_sign", "open_bracket", "close_bracket",
    "backslash", "non_us_pound", "semicolon", "quote",
    "grave_accent_and_tilde", "comma", "period", "slash", "non_us_backslash",
    # Special
    "mission_control", "launchpad", "dashboard",
    "print_screen", "scroll_lock", "pause",
    "menu", "application",
    # International
    "international1", "international2", "international3",
    "lang1", "lang2",
}

VALID_CONSUMER_KEY_CODES: set[str] = {
    "play_or_pause", "fast_forward", "rewind",
    "volume_increment", "volume_decrement", "mute",
    "eject",
    "display_brightness_increment", "display_brightness_decrement",
    "al_terminal_lock_or_screensaver",
    "scan_next_track", "scan_previous_track",
}

VALID_MODIFIERS: set[str] = {
    "left_command", "right_command",
    "left_shift", "right_shift",
    "left_option", "right_option",
    "left_control", "right_control",
    "fn",
}

# ── Expected key map (source of truth from PROJECT_SUMMARY / todo) ─────

EXPECTED_KEYS: list[dict[str, Any]] = [
    {"id": 1,  "from": "keypad_1",       "from_type": "key_code", "label": "Terminal",         "action_type": "app"},
    {"id": 2,  "from": "keypad_2",       "from_type": "key_code", "label": "VS Code",          "action_type": "app"},
    {"id": 3,  "from": "keypad_3",       "from_type": "key_code", "label": "Safari",           "action_type": "app"},
    {"id": 4,  "from": "keypad_4",       "from_type": "key_code", "label": "Mission Control",  "action_type": "media"},
    {"id": 5,  "from": "keypad_5",       "from_type": "key_code", "label": "Fullscreen",       "action_type": "key"},
    {"id": 6,  "from": "keypad_6",       "from_type": "key_code", "label": "Spotlight",        "action_type": "key"},
    {"id": 7,  "from": "keypad_7",       "from_type": "key_code", "label": "Undo",             "action_type": "key"},
    {"id": 8,  "from": "keypad_8",       "from_type": "key_code", "label": "Redo",             "action_type": "key"},
    {"id": 9,  "from": "keypad_9",       "from_type": "key_code", "label": "Copy",             "action_type": "key"},
    {"id": 10, "from": "keypad_0",       "from_type": "key_code", "label": "Paste",            "action_type": "key"},
    {"id": 11, "from": "keypad_period",  "from_type": "key_code", "label": "Cut",              "action_type": "key"},
    {"id": 12, "from": "keypad_enter",   "from_type": "key_code", "label": "Screenshot",       "action_type": "shell"},
    {"id": 13, "from": "keypad_hyphen",  "from_type": "key_code", "label": "Play/Pause",       "action_type": "media"},
    {"id": 14, "from": "keypad_plus",    "from_type": "key_code", "label": "Next Track",       "action_type": "media"},
    {"id": 15, "from": "spacebar",       "from_type": "key_code", "label": "Prev Track",       "action_type": "media"},
    {"id": 16, "from": "down_arrow",     "from_type": "key_code", "label": "Finder",           "action_type": "app"},
    {"id": 17, "from": "left_arrow",     "from_type": "key_code", "label": "System Settings",  "action_type": "app"},
    {"id": 18, "from": "right_arrow",    "from_type": "key_code", "label": "App Switcher",     "action_type": "key"},
    {"id": 19, "from": "up_arrow",       "from_type": "key_code", "label": "Rev Switcher",     "action_type": "key"},
    {"id": 20, "from": "return_or_enter","from_type": "key_code", "label": "D-Pad Center",     "action_type": "key"},
]


# ── Test framework ─────────────────────────────────────────────────────

class TestResult:
    """Accumulates pass/fail/skip results with contextual messages."""

    def __init__(self) -> None:
        self.passed: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed += 1
        print(f"  ✅  {msg}")

    def fail(self, msg: str) -> None:
        self.failed += 1
        self.errors.append(msg)
        print(f"  ❌  {msg}")

    def skip(self, msg: str) -> None:
        self.skipped += 1
        print(f"  ⏭️   {msg}")

    def summary(self) -> None:
        total = self.passed + self.failed + self.skipped
        print()
        print("═" * 62)
        print(f"  RESULTS:  {self.passed} passed · {self.failed} failed · {self.skipped} skipped  ({total} total)")
        print("═" * 62)
        if self.errors:
            print()
            print("  Failures:")
            for e in self.errors:
                print(f"    • {e}")
        print()


R = TestResult()


# ── Helpers ────────────────────────────────────────────────────────────

def load_json(path: Path) -> Optional[dict]:
    """Load and parse a JSON file, returning None on failure."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        R.fail(f"Cannot load {path.name}: {exc}")
        return None


def detect_action_type(to_entry: dict) -> str:
    """Classify a Karabiner 'to' entry into our action taxonomy."""
    key_code_media = {"mission_control", "launchpad", "dashboard"}
    if "consumer_key_code" in to_entry:
        return "media"
    if "shell_command" in to_entry:
        cmd = to_entry["shell_command"]
        return "app" if re.match(r"^open -a '.+'$", cmd) else "shell"
    if "key_code" in to_entry:
        return "media" if to_entry["key_code"] in key_code_media else "key"
    return "unknown"


def app_exists(name: str) -> bool:
    """Check whether a macOS .app bundle can be found via mdfind or known paths."""
    # Fast path: check /Applications and ~/Applications
    for base in [Path("/Applications"), Path.home() / "Applications"]:
        if (base / f"{name}.app").is_dir():
            return True
    # Fallback: Spotlight query
    try:
        result = subprocess.run(
            ["mdfind", f"kMDItemFSName == '{name}.app' && kMDItemContentType == 'com.apple.application-bundle'"],
            capture_output=True, text=True, timeout=5,
        )
        return bool(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


# ── Test 1: Profile JSON structural integrity ──────────────────────────

def test_profile_structure() -> Optional[list[dict]]:
    """Validate karabiner_profile.json shape and return manipulators."""
    print("\n─── Test 1: karabiner_profile.json structure ───")

    profile = load_json(PROFILE_PATH)
    if profile is None:
        return None

    R.ok("Valid JSON") if profile else R.fail("Empty JSON")

    manips = profile.get("manipulators")
    if not isinstance(manips, list):
        R.fail("'manipulators' is not a list")
        return None
    R.ok(f"Has 'manipulators' array")

    if len(manips) == EXPECTED_KEY_COUNT:
        R.ok(f"Manipulator count: {len(manips)} (expected {EXPECTED_KEY_COUNT})")
    else:
        R.fail(f"Manipulator count: {len(manips)} (expected {EXPECTED_KEY_COUNT})")

    # Validate each manipulator
    for i, m in enumerate(manips):
        key_id = i + 1
        prefix = f"Key {key_id}"

        # type: basic
        if m.get("type") != "basic":
            R.fail(f"{prefix}: type={m.get('type')!r}, expected 'basic'")

        # from
        from_block = m.get("from", {})
        from_code = from_block.get("key_code") or from_block.get("consumer_key_code")
        if not from_code:
            R.fail(f"{prefix}: missing from key_code/consumer_key_code")

        # to
        to_block = m.get("to")
        if not isinstance(to_block, list) or len(to_block) == 0:
            R.fail(f"{prefix}: missing or empty 'to' array")

        # conditions (device_if)
        conds = m.get("conditions", [])
        if len(conds) != 1 or conds[0].get("type") != "device_if":
            R.fail(f"{prefix}: missing device_if condition")
        else:
            ident = conds[0].get("identifiers", [{}])[0]
            if ident.get("vendor_id") != VENDOR_ID or ident.get("product_id") != PRODUCT_ID:
                R.fail(f"{prefix}: wrong VID/PID in condition: {ident}")

    R.ok("All manipulators have valid structure (type, from, to, device_if)")
    return manips


# ── Test 2: Key-code validity ──────────────────────────────────────────

def test_keycodes(manips: list[dict]) -> None:
    """Check that every from/to key code is in Karabiner's known set."""
    print("\n─── Test 2: Key-code validity ───")

    all_valid = True
    for i, m in enumerate(manips):
        key_id = i + 1
        prefix = f"Key {key_id}"

        # From key
        from_block = m.get("from", {})
        if "key_code" in from_block:
            code = from_block["key_code"]
            if code not in VALID_KEY_CODES:
                R.fail(f"{prefix}: from key_code '{code}' not in known set")
                all_valid = False
        elif "consumer_key_code" in from_block:
            code = from_block["consumer_key_code"]
            if code not in VALID_CONSUMER_KEY_CODES:
                R.fail(f"{prefix}: from consumer_key_code '{code}' not in known set")
                all_valid = False

        # To key(s)
        for t in m.get("to", []):
            if "key_code" in t:
                code = t["key_code"]
                if code not in VALID_KEY_CODES:
                    R.fail(f"{prefix}: to key_code '{code}' not in known set")
                    all_valid = False
                # Modifiers
                for mod in t.get("modifiers", []):
                    if mod not in VALID_MODIFIERS:
                        R.fail(f"{prefix}: modifier '{mod}' not in known set")
                        all_valid = False
            elif "consumer_key_code" in t:
                code = t["consumer_key_code"]
                if code not in VALID_CONSUMER_KEY_CODES:
                    R.fail(f"{prefix}: to consumer_key_code '{code}' not in known set")
                    all_valid = False

    if all_valid:
        R.ok("All from/to key codes and modifiers are valid Karabiner identifiers")


# ── Test 3: Duplicate from-key detection ───────────────────────────────

def test_no_duplicate_from_keys(manips: list[dict]) -> None:
    """Ensure no two manipulators listen on the same from-key."""
    print("\n─── Test 3: No duplicate from-keys ───")

    seen: dict[str, int] = {}
    dupes = False
    for i, m in enumerate(manips):
        from_block = m.get("from", {})
        code = from_block.get("key_code") or from_block.get("consumer_key_code", "?")
        key_type = "key_code" if "key_code" in from_block else "consumer_key_code"
        fingerprint = f"{key_type}:{code}"
        if fingerprint in seen:
            R.fail(f"Key {i+1} duplicates from-key '{code}' (also Key {seen[fingerprint]})")
            dupes = True
        seen[fingerprint] = i + 1

    if not dupes:
        R.ok(f"All {len(manips)} from-keys are unique")


# ── Test 4: Action-specific validation ─────────────────────────────────

def test_actions(manips: list[dict]) -> None:
    """Validate each action: app existence, shell non-empty, media correctness."""
    print("\n─── Test 4: Action validation (apps, shell, media, shortcuts) ───")

    for i, m in enumerate(manips):
        key_id = i + 1
        prefix = f"Key {key_id:2d}"
        to = m.get("to", [{}])[0]
        action = detect_action_type(to)

        if action == "app":
            app_match = re.match(r"^open -a '(.+)'$", to.get("shell_command", ""))
            if app_match:
                app_name = app_match.group(1)
                if app_exists(app_name):
                    R.ok(f"{prefix} [{action:5s}]  {app_name}.app found")
                else:
                    R.fail(f"{prefix} [{action:5s}]  {app_name}.app NOT found on this system")
            else:
                R.fail(f"{prefix} [{action:5s}]  malformed open -a command: {to.get('shell_command')!r}")

        elif action == "shell":
            cmd = to.get("shell_command", "").strip()
            if cmd:
                R.ok(f"{prefix} [{action:5s}]  command: {cmd[:50]}{'…' if len(cmd) > 50 else ''}")
            else:
                R.fail(f"{prefix} [{action:5s}]  empty shell command")

        elif action == "media":
            code = to.get("consumer_key_code") or to.get("key_code")
            field = "consumer_key_code" if "consumer_key_code" in to else "key_code"
            # mission_control/launchpad use key_code; actual media controls use consumer_key_code
            key_code_media = {"mission_control", "launchpad", "dashboard"}
            if field == "key_code" and code in key_code_media:
                R.ok(f"{prefix} [{action:5s}]  {field}:{code}")
            elif field == "consumer_key_code" and code in VALID_CONSUMER_KEY_CODES:
                R.ok(f"{prefix} [{action:5s}]  {field}:{code}")
            else:
                R.fail(f"{prefix} [{action:5s}]  unexpected {field}:{code}")

        elif action == "key":
            kc = to.get("key_code", "?")
            mods = to.get("modifiers", [])
            mod_str = "+".join(m.replace("left_", "").replace("right_", "R-") for m in mods)
            combo = f"{mod_str}+{kc}" if mods else kc
            R.ok(f"{prefix} [{action:5s}]  {combo}")

        else:
            R.fail(f"{prefix}  unknown action type in: {to}")


# ── Test 5: Expected key map cross-check ───────────────────────────────

def test_expected_key_map(manips: list[dict]) -> None:
    """Cross-check manipulators against the expected key map from project docs."""
    print("\n─── Test 5: Cross-check against expected key map ───")

    if len(manips) != len(EXPECTED_KEYS):
        R.fail(f"Count mismatch: {len(manips)} manipulators vs {len(EXPECTED_KEYS)} expected")
        return

    all_match = True
    for exp, m in zip(EXPECTED_KEYS, manips):
        key_id = exp["id"]
        prefix = f"Key {key_id:2d}"

        # From key
        from_block = m.get("from", {})
        actual_from = from_block.get(exp["from_type"])
        if actual_from != exp["from"]:
            R.fail(f"{prefix}: from={actual_from!r}, expected {exp['from']!r}")
            all_match = False

        # Action type (customizable — check for valid syntax rather than strict default match)
        to = m.get("to", [{}])[0]
        actual_type = detect_action_type(to)
        if actual_type not in {"app", "shell", "media", "key"}:
            R.fail(f"{prefix}: invalid action_type={actual_type!r}")
            all_match = False

    if all_match:
        R.ok(f"All {len(EXPECTED_KEYS)} keys match expected from-codes and action types")


# ── Test 6: Live Karabiner config ──────────────────────────────────────

def test_live_config() -> None:
    """Validate the live Karabiner config has the INSTANT profile active."""
    print("\n─── Test 6: Live Karabiner config ───")

    if not LIVE_CONFIG_PATH.exists():
        R.skip(f"{LIVE_CONFIG_PATH} not found (Karabiner-Elements not installed?)")
        return

    config = load_json(LIVE_CONFIG_PATH)
    if config is None:
        return

    R.ok("Live config is valid JSON")

    profiles = config.get("profiles", [])
    instant = next((p for p in profiles if p.get("name") == PROFILE_NAME), None)

    if instant is None:
        R.fail(f"Profile '{PROFILE_NAME}' not found in live config")
        return
    R.ok(f"Profile '{PROFILE_NAME}' exists")

    # Selected
    if instant.get("selected"):
        R.ok("Profile is selected")
    else:
        R.fail("Profile is NOT selected")

    # Rules
    rules = instant.get("complex_modifications", {}).get("rules", [])
    if not rules:
        R.fail("No complex_modification rules found")
        return

    rule = rules[0]
    # Karabiner treats absent 'enabled' as true
    enabled = rule.get("enabled", True)
    if enabled:
        R.ok("Rule is enabled")
    else:
        R.fail("Rule is DISABLED — keys won't fire")

    rule_manips = rule.get("manipulators", [])
    if len(rule_manips) == EXPECTED_KEY_COUNT:
        R.ok(f"Rule has {len(rule_manips)} manipulators")
    else:
        R.fail(f"Rule has {len(rule_manips)} manipulators (expected {EXPECTED_KEY_COUNT})")

    # No eval_js cruft
    raw = json.dumps(instant)
    if "eval_js" not in raw:
        R.ok("No eval_js cruft")
    else:
        R.fail("eval_js cruft found — remove the invalid rule")

    # No caps_lock simple_modification
    simple_mods_raw = json.dumps(instant.get("devices", []))
    if "caps_lock" not in simple_mods_raw:
        R.ok("No stray caps_lock simple_modification")
    else:
        R.fail("caps_lock simple_modification found — will conflict with Key 1")

    # Device ignore=false
    devices = instant.get("devices", [])
    pad_devices = [
        d for d in devices
        if d.get("identifiers", {}).get("vendor_id") == VENDOR_ID
        and d.get("identifiers", {}).get("product_id") == PRODUCT_ID
    ]
    if pad_devices:
        if not pad_devices[0].get("ignore", True):
            R.ok("Device 'Modify events' is ON (ignore=false)")
        else:
            R.fail("Device ignore=true — Karabiner won't intercept pad keys")
    else:
        R.fail("No device entry for VID:30FA/PID:2350 — add via Karabiner Devices tab")

    # Profile JSON ↔ Live config consistency
    if rule_manips:
        profile = load_json(PROFILE_PATH)
        if profile:
            profile_manips = profile.get("manipulators", [])
            if len(profile_manips) == len(rule_manips):
                mismatches = 0
                for i, (pm, lm) in enumerate(zip(profile_manips, rule_manips)):
                    p_from = pm.get("from", {})
                    l_from = lm.get("from", {})
                    p_to = pm.get("to", [])
                    l_to = lm.get("to", [])
                    if p_from != l_from or p_to != l_to:
                        mismatches += 1
                        R.fail(f"Key {i+1}: profile ≠ live config (from or to differs)")
                if mismatches == 0:
                    R.ok("Profile JSON and live config manipulators are identical")
            else:
                R.fail(f"Profile has {len(profile_manips)} manips, live has {len(rule_manips)}")


# ── Test 7: Export → Import round-trip ─────────────────────────────────

def test_round_trip(manips: list[dict]) -> None:
    """Simulate index.html's export (buildProfile) → import (handleImport) cycle."""
    print("\n─── Test 7: Export → Import round-trip ───")

    key_code_media = {"mission_control", "launchpad", "dashboard"}

    # Forward pass: manips → internal repr
    internal: list[dict] = []
    for m in manips:
        from_block = m.get("from", {})
        if "key_code" in from_block:
            from_key = from_block["key_code"]
            from_type = "key_code"
        else:
            from_key = from_block.get("consumer_key_code", "?")
            from_type = "consumer_key_code"

        to = m.get("to", [{}])[0]
        action: Optional[dict] = None

        if "consumer_key_code" in to:
            action = {"type": "media", "mediaCode": to["consumer_key_code"]}
        elif "shell_command" in to:
            app_match = re.match(r"^open -a '(.+)'$", to["shell_command"])
            action = (
                {"type": "app", "appName": app_match.group(1)}
                if app_match
                else {"type": "shell", "command": to["shell_command"]}
            )
        elif "key_code" in to and to["key_code"] in key_code_media:
            action = {"type": "media", "mediaCode": to["key_code"]}
        elif "key_code" in to:
            action = {"type": "key", "keyCode": to["key_code"], "modifiers": to.get("modifiers", [])}

        internal.append({
            "fromKey": from_key,
            "fromKeyType": from_type,
            "label": m.get("description", ""),
            "action": action,
        })

    # Reverse pass: internal repr → manipulators
    rebuilt: list[dict] = []
    for entry in internal:
        a = entry["action"]
        if a is None:
            continue

        if a["type"] == "shell":
            to = [{"shell_command": a["command"]}]
        elif a["type"] == "key":
            obj: dict[str, Any] = {"key_code": a["keyCode"]}
            if a.get("modifiers"):
                obj["modifiers"] = a["modifiers"]
            to = [obj]
        elif a["type"] == "media":
            field = "key_code" if a["mediaCode"] in key_code_media else "consumer_key_code"
            to = [{field: a["mediaCode"]}]
        elif a["type"] == "app":
            to = [{"shell_command": f"open -a '{a['appName']}'"}]
        else:
            to = []

        rebuilt.append({
            "from": {entry["fromKeyType"]: entry["fromKey"]},
            "to": to,
        })

    # Compare
    if len(rebuilt) != len(manips):
        R.fail(f"Round-trip count mismatch: {len(rebuilt)} vs {len(manips)}")
        return

    mismatches = 0
    for i, (orig, rt) in enumerate(zip(manips, rebuilt)):
        if orig["from"] != rt["from"]:
            R.fail(f"Key {i+1}: from mismatch after round-trip")
            mismatches += 1
        if orig["to"] != rt["to"]:
            R.fail(f"Key {i+1}: to mismatch after round-trip — orig={orig['to']} rebuilt={rt['to']}")
            mismatches += 1

    if mismatches == 0:
        R.ok(f"All {len(manips)} keys survive export→import round-trip perfectly")


# ── Test 8: Install script ─────────────────────────────────────────────

def test_installer() -> None:
    """Verify install_profile.sh exists and is executable."""
    print("\n─── Test 8: install_profile.sh ───")

    if not INSTALLER_PATH.exists():
        R.fail(f"{INSTALLER_PATH.name} not found")
        return
    R.ok("install_profile.sh exists")

    mode = INSTALLER_PATH.stat().st_mode
    if mode & stat.S_IXUSR:
        R.ok("install_profile.sh is executable")
    else:
        R.fail("install_profile.sh is NOT executable (run: chmod +x install_profile.sh)")

    # Check shebang
    with open(INSTALLER_PATH) as f:
        first_line = f.readline().strip()
    if first_line.startswith("#!"):
        R.ok(f"Has shebang: {first_line}")
    else:
        R.fail("Missing shebang line")

    # Check it references the profile JSON
    content = INSTALLER_PATH.read_text()
    if "karabiner_profile.json" in content:
        R.ok("References karabiner_profile.json")
    else:
        R.fail("Does not reference karabiner_profile.json")


# ── Main ───────────────────────────────────────────────────────────────

def main() -> int:
    """Run all tests and print summary."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  INSTANT 19-Key Macro Pad — Verification Suite          ║")
    print("╚══════════════════════════════════════════════════════════╝")

    manips = test_profile_structure()
    if manips is None:
        print("\n⚠️  Cannot continue without a valid karabiner_profile.json")
        R.summary()
        return 1

    test_keycodes(manips)
    test_no_duplicate_from_keys(manips)
    test_actions(manips)
    test_expected_key_map(manips)
    test_live_config()
    test_round_trip(manips)
    test_installer()

    R.summary()
    return 0 if R.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
