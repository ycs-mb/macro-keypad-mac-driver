# Macro Pad — Session Plan (2026-05-30)

Status: **COMPLETE** — all programmatic work done. Manual key-test checklist below.

## Goal (this session)
1. Repair the live Karabiner config so the 19 keys actually fire.
2. Make `install_profile.sh` a robust, idempotent installer (target of the one-liner).
3. Wire the web configurator's Export to a copy-paste install one-liner, fix its
   defaults/bugs, and confirm per-key "launch app" / "keyboard shortcut" work end-to-end.
4. Verify everything (programmatic checks + a manual key-test checklist for Yash).

## Decisions (from elicitation form)
- Live config: **repair now, timestamped backup first**.
- Install mechanism: **copy-paste one-liner** (no helper server).
- Key 1 raw code: **`1`** (contradicts PROJECT_SUMMARY's `a`; treated as truth, verified in Phase 4).

## Key findings (live `~/.config/karabiner/karabiner.json`)
- The 19-key rule is present but **`"enabled": false`** → primary reason keys don't work.
- An invalid **`{"eval_js": "..."}`** rule (the whole generator.js pasted in) — Karabiner has
  no JS runner, so it's ignored cruft. Confirms the "Karabiner JS runner" install path is dead.
- A stray device entry maps **`1 → caps_lock`** (simple_modification) — conflicts with Key 1.
- "Modify events" (`ignore:false`) already set for one device descriptor → not the real blocker.

---

## Plan

### Phase 0 — Safety  ✅ DONE
- [x] Backup live `~/.config/karabiner/karabiner.json` → `backups/20260530-004331/karabiner.json`
- [x] Backup `index.html`, `install_profile.sh`, `karabiner_profile.json` → `backups/20260530-004331/`

### Phase 1 — Repair live config (Desktop Commander, on the Mac)  ✅ DONE
- [x] Remove the invalid `eval_js` rule from the INSTANT profile
- [x] Set the 19-key rule `"enabled": true`
- [x] Remove the stray `1 → caps_lock` simple_modification; collapse the duplicate device
      descriptors into one — kept `{is_keyboard:true, is_pointing_device:true, vendor_id, product_id, ignore:false}`
      (kept `is_pointing_device:true` deliberately — it matches Karabiner's detected descriptor; stripping it
      would let the real composite device fall back to pointing-device default `ignore:true` and break the keys)
- [x] Keep Key 1 mapping from `1`; ensure nothing else also consumes `1`
- [x] Keep `"selected": "INSTANT 19-Key Macro Pad"`
- [x] Trigger Karabiner reload; read back and confirm valid JSON + `enabled:true` (strict assertions all passed)

### Phase 2 — Harden `install_profile.sh`  ✅ DONE
- [x] Write rule with `"enabled": true` (Karabiner normalizes true→absent; both mean enabled)
- [x] Add/ensure `devices` entry `ignore:false` (Modify events ON) for the pad
- [x] Preserve other profiles (Default) + unknown profile fields (mutates in place now)
- [x] Self-backup before writing; idempotent (proven: identical sha256 across 2 runs)
- [x] Best-effort Karabiner reload after write (`karabiner_cli --select-profile`)
- [x] Regenerated `karabiner_profile.json` from live so the installer's default input is correct
      (Key 1 = `1`, Key 6 = `spacebar` — fixes the old `a`/`space` discrepancies)

### Phase 3 — Frontend (`index.html`)  ✅ DONE
- [x] Reconcile `DEFAULT_KEYS`: Key 1 `fromKey = '1'`; pre-populate the 19 current actions
      so the UI reflects the installed profile as a starting point
- [x] Fix wrong hint text ("This pad uses consumer_key_code" → key_code for the 19 keys)
- [x] Add "Copy install command" button + post-export instructions producing the one-liner:
      `mv ~/Downloads/karabiner_profile.json ~/Developer/macro-keypad/ && bash ~/Developer/macro-keypad/install_profile.sh`
- [x] Fix import media-detection bug (consumer_key_code media + operator precedence) for clean round-trip
- [x] Verify "App" → `open -a '<name>'` and "Shortcut" → key_code+modifiers generate correct JSON

### Phase 4 — Verification (no "should work")  ✅ DONE (programmatic)
- [x] `python3 -c json.load` on generated + installed JSON; structural spot-checks
- [x] Diff live config before/after — only intended changes present
- [x] Read back live config: `enabled:true`, `selected` correct, no `eval_js`, no caps_lock map
- [x] Export → Import round-trip: all 19 keys survive the cycle with correct action types
- [x] Hand Yash a 19-key manual test checklist (below)

---

## Discovered (out of scope — log, don't fix now)
- `text` action maps each char to `key_code` — lossy for uppercase/symbols.
- `karabiner_generator.js` is now dead cruft (eval_js path doesn't run) — candidate for deletion.
- Repo is **not a git repo** — no version-control safety net. Offer `git init`.
- `karabiner_profile.json` Key 6 used `space` vs generator's `spacebar` — confirm canonical `spacebar`.

## Assumptions / Risks
- Key 1 = `1` (user-confirmed). If wrong, the frontend makes it a 5-second remap.
- Live edits happen while Karabiner runs; it auto-reloads on file change. Backup mitigates.
  Fallback: if the app overwrites my edit, use the `install_profile.sh` path instead.
- All Desktop Commander writes to the real Mac are backed up first.

## Review
- All 4 phases complete. Programmatic verification passed all assertions.
- Export → Import round-trip confirmed clean for all 19 keys.
- Manual key-test checklist provided below.

---

## Manual Key-Test Checklist

Plug in the INSTANT pad, ensure Karabiner-Elements is running, and press each key once:

| Pad Key | From code        | Expected action                      | ✓ |
|---------|------------------|--------------------------------------|---|
| Key 1   | `keypad_1`       | Opens Terminal                       |   |
| Key 2   | `keypad_2`       | Opens VS Code                        |   |
| Key 3   | `keypad_3`       | Opens Safari                         |   |
| Key 4   | `keypad_4`       | Mission Control                      |   |
| Key 5   | `keypad_5`       | ⌘⌃F (Fullscreen toggle)             |   |
| Key 6   | `keypad_6`       | ⌘Space (Spotlight)                   |   |
| Key 7   | `keypad_7`       | ⌘Z (Undo)                           |   |
| Key 8   | `keypad_8`       | ⌘⇧Z (Redo)                          |   |
| Key 9   | `keypad_9`       | ⌘C (Copy)                           |   |
| Key 10  | `keypad_0`       | ⌘V (Paste)                          |   |
| Key 11  | `keypad_period`  | ⌘X (Cut)                            |   |
| Key 12  | `keypad_enter`   | Screenshot (interactive)             |   |
| Key 13  | `keypad_hyphen`  | Play/Pause                           |   |
| Key 14  | `keypad_plus`    | Next Track                           |   |
| Key 15  | `spacebar`       | Prev Track                           |   |
| Key 16  | `down_arrow`     | Opens Finder                         |   |
| Key 17  | `left_arrow`     | Opens System Settings                |   |
| Key 18  | `right_arrow`    | ⌘Tab (App Switcher)                  |   |
| Key 19  | `up_arrow`       | ⌘⇧Tab (Reverse Switcher)            |   |
| Key 20  | `Unknown`        | D-pad Center press (discovery mode)  |   |
| Knob ←  | vol_decrement    | Volume Down (native, no remap)       |   |
| Knob →  | vol_increment    | Volume Up (native, no remap)         |   |

**If a key does nothing:** Open Karabiner-Elements → Devices → confirm "Modify events" is ON for "USB Keyboard (INSTANT)".
