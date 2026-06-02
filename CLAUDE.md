# CLAUDE.md — K809 Macro Pad Configurator

## Project Overview

Native macOS configurator for the **INSTANT K809 USB-C 20-key programmable macro keypad**. The device has no official Mac driver; all remapping is done via Karabiner-Elements complex_modifications scoped to the device's VID/PID.

**Decision (ADR-001, 2026-06-03):** Migrate from a Flask server + browser workflow to a **Tauri v2 native Mac app** (Rust backend + macOS WKWebView frontend). The existing ~137KB HTML/CSS/JS codebase is reused as-is (~90% code retention). See `docs/adr/ADR-001-native-mac-app.md` for full rationale.

---

## Hardware

| Attribute | Value |
|---|---|
| Device | INSTANT K809 USB-C 20-key macro keypad |
| VID | `0x30FA` (12538) |
| PID | `0x2350` (9040) |
| Key codes | All `key_code` type — **NOT** `consumer_key_code` |
| Rotary knob | `volume_increment` / `volume_decrement` (native, no remap) |
| Key 20 | D-pad center press — raw keycode still unknown |

All Karabiner manipulators must include a `device_if` condition with `vendor_id: 12538, product_id: 9040` to avoid intercepting regular keyboards.

---

## Current Stack (pre-Tauri)

| File | Role |
|---|---|
| `index.html` | Configurator UI — single-file, interactive 3D CSS model, JSON export/import |
| `test.html` | Key Tester UI — HID event detection, pass/fail tracking per key |
| `server.py` | Local Flask server on port 8080 — exposes `POST /api/apply` to write `karabiner_profile.json` and run `install_profile.sh` |
| `install_profile.sh` | Idempotent installer — backs up, patches live `~/.config/karabiner/karabiner.json`, triggers reload |
| `karabiner_profile.json` | Active 20-key remap rules in Karabiner JSON format |
| `karabiner_generator.js` | Dead code — `eval_js` path doesn't run in Karabiner. Candidate for deletion. |
| `test_macropad.py` | 41-test automated verification suite (JSON structure, key codes, round-trip export/import) |
| `backups/` | Timestamped Karabiner config backups — never delete |

---

## Target Architecture (Tauri v2)

```
MacroPad.app
├── Frontend (WKWebView)
│   ├── Tab Router (JS) — switches Configurator / Tester views
│   ├── Configurator View (migrated from index.html)
│   └── Tester View (migrated from test.html)
└── Backend (Rust)
    ├── Karabiner Manager — reads/writes ~/.config/karabiner/karabiner.json
    ├── USB HID Monitor — IOKit background thread for K809 attach/detach
    ├── System Tray — menubar icon, connection status
    └── Profile Store — ~/Library/Application Support/com.macropad.app/
```

### Tauri IPC Commands (replacing Flask)

| Rust Command | Replaces | Purpose |
|---|---|---|
| `save_profile(json)` | `POST /save` | Write key mappings to profile store |
| `install_profile()` | `POST /run-command` + `install_profile.sh` | Inject profile into live Karabiner config |
| `export_json() → String` | `GET /export` | Return current profile as JSON string |
| `import_json(json)` | `POST /import` | Load profile from external JSON |
| `get_device_status() → bool` | (new) | Check if K809 is currently connected |
| `get_karabiner_status() → Status` | (new) | Check Karabiner-Elements install + active profile |

---

## v1.0 Scope

**In scope:**
- Key Configurator (full key action editing, JSON export/import)
- Key Tester (HID event detection, pass/fail tracking)
- One-click Karabiner install (no terminal needed)
- USB device auto-detection via IOKit
- Menubar tray icon (connection status + quick actions)

**Deferred to v1.1:**
- Interactive 3D CSS viewport (verify WKWebView CSS 3D compat first)
- Karabiner auto-install prompt (guide users if missing)
- Auto-update via Tauri updater
- Code signing / notarization

---

## Distribution

- **Channel:** GitHub Releases (`.dmg`)
- **Signing:** Unsigned initially — users right-click → Open
- **Target:** Universal binary (`--target universal-apple-darwin`, arm64 + x86_64)
- **Min macOS:** 13.0 Ventura (Tauri v2 requirement)
- **Cost:** Free (no Apple Developer Program required)

---

## Key Risks

| Risk | Mitigation |
|---|---|
| WKWebView CSS 3D rendering differences | Defer 3D viewport to v1.1; fall back to 2D grid if needed |
| Karabiner not installed on user machine | Detect on startup, show guided `brew install --cask karabiner-elements` prompt |
| Gatekeeper blocks unsigned app | Document right-click → Open in README |
| IOKit HID entitlements | Test sandboxed vs non-sandboxed; use `core-foundation` + `io-kit-sys` crates |

---

## Development Rules

- **No git repo yet** — run `git init` before starting Tauri scaffolding; keep `backups/` in `.gitignore`
- **Python**: use `uv run` — never `pip` or `venv`
- **Rust/Tauri**: Tauri v2 only (`cargo tauri dev`, `cargo tauri build`)
- **No secrets** in source — Karabiner paths are discovered at runtime
- **Karabiner writes**: always back up `~/.config/karabiner/karabiner.json` before any write
- **`karabiner_generator.js`**: dead code, safe to delete in Tauri migration
- **`server.py`**: replaced entirely by Tauri Rust commands — do not extend it

---

## 3D CSS Model Notes

The interactive 3D model in `index.html` / `test.html` uses pure CSS 3D transforms (zero dependencies). Key technical details:
- All keycap side faces use edge-aligned absolute positioning to eliminate subpixel gaps
- Orbital dragging: mouse drag rotates model; vertical pitch clamped 20°–80°
- Watertight box construction: front/back/left/right edges use `rotateX`/`rotateY` on `transform-origin`
- Key states: Yellow = selected (configurator), Green = pass, Red = fail (tester)

**Future enhancement (logged, not in v1.0):** Replace CSS model with a photogrammetry-reconstructed WebGL model via Three.js + Draco-compressed `.glb`. See `tasks/3d-view-feature.md`.
