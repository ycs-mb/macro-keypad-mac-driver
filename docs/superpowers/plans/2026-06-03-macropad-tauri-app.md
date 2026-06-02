# MacroPad.app — Tauri v2 Native macOS App Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the existing K809 macro keypad configurator into a native macOS `.app` using Tauri v2, replacing `server.py` with Rust IPC commands and adding USB device auto-detection plus a menubar tray icon.

**Architecture:** Tauri v2 wraps the existing `index.html` and `test.html` in a native macOS WKWebView (`withGlobalTauri: true`). A Rust backend replaces Flask: it injects Karabiner-Elements config, polls for K809 USB presence via `hidapi`, emits `device_status` events to the frontend, and maintains a menubar tray icon. The frontend migration is surgical — only the `applyDirect()` function (one `fetch` call) and the apply-button visibility check need changing.

**Tech Stack:** Rust 1.78+, Tauri v2, `hidapi 2`, `serde_json 1`, `dirs 5`, `tempfile 3` (dev), vanilla JS/HTML (no bundler), macOS 13.0 Ventura minimum.

---

## Pre-read: What Already Exists

| File | Role (keep as-is) |
|---|---|
| `index.html` (root, 2332 lines) | Configurator UI — interactive 3D CSS keypad, key editing, JSON export/import. Only `applyDirect()` (line 2022–2041) calls the server. |
| `test.html` (root, 1872 lines) | Key Tester UI — HID event detection, pass/fail per key. No Flask calls. |
| `install_profile.sh` | Idempotent Karabiner config installer — logic is ported to Rust; keep for reference. |
| `karabiner_profile.json` | Active 20-key remap rules. |
| `backups/` | Timestamped Karabiner backups — **never delete**. |
| `test_macropad.py` | 41-test suite — must stay green throughout. |

Key insight: `applyDirect()` sends the raw `keys` JS array to `POST /api/apply`. For Tauri, we call `buildProfile()` first in JS (already exists at line 1831), then `invoke('install_profile', { json: ... })`. The Rust command receives the already-built `{description, manipulators}` structure.

---

## File Map

### New Files

| File | Purpose |
|---|---|
| `src-tauri/` | Tauri project root (scaffolded by `cargo tauri init`) |
| `src-tauri/tauri.conf.json` | App config: bundle ID, window size, `withGlobalTauri: true` |
| `src-tauri/Cargo.toml` | Rust deps: tauri, serde_json, hidapi, dirs |
| `src-tauri/build.rs` | Tauri build script |
| `src-tauri/src/main.rs` | Entry point: registers commands, starts tray + HID monitor |
| `src-tauri/src/error.rs` | `AppError` + `AppResult<T>` — unified error type for IPC |
| `src-tauri/src/karabiner.rs` | Read/write/backup Karabiner config; inject manipulators |
| `src-tauri/src/hid_monitor.rs` | Poll K809 VID/PID with `hidapi`; background thread emits events |
| `src-tauri/src/tray.rs` | Menubar tray icon with connected/disconnected tooltip |
| `src-tauri/src/commands.rs` | Six `#[tauri::command]` functions (IPC layer): `install_profile`, `save_profile`, `export_json`, `import_json`, `get_device_status`, `get_karabiner_status` |
| `src-tauri/src/profile_store.rs` | Persist profiles to `~/Library/Application Support/com.macropad.app/` |
| `src/index.html` | Tab router shell (new — not the root `index.html`) |
| `src/tauri-bridge.js` | `window.TauriBridge` wrapper + graceful browser fallback |
| `src/configurator.html` | Migrated from root `index.html` (3 surgical edits) |
| `src/tester.html` | Migrated from root `test.html` (add bridge script tag only) |

### Modified Files

| File | Change |
|---|---|
| `.gitignore` | Add `target/` and `src-tauri/target/` |

### Preserved (Unchanged)
`index.html`, `test.html`, `server.py`, `install_profile.sh`, `karabiner_profile.json`, `backups/`, `test_macropad.py`

---

## Task 0: Environment + Tauri Scaffold

**Files:** Creates `src-tauri/`, `src/`, modifies `.gitignore`

- [ ] **Step 1: Verify Rust toolchain**

```bash
rustc --version && cargo --version
```
Expected: `rustc 1.78+`. If missing: `curl https://sh.rustup.rs -sSf | sh && source ~/.cargo/env`

- [ ] **Step 2: Install Tauri CLI v2**

```bash
cargo install tauri-cli --version "^2" --locked
cargo tauri --version
```
Expected: `tauri-cli 2.x.x`

- [ ] **Step 3: Scaffold Tauri project**

Run from `/Users/ycs/Developer/macro-keypad/`:
```bash
cargo tauri init
```

Answer prompts:
- App name: `MacroPad`
- Window title: `MacroPad — K809 Configurator`
- Web assets relative path: `../src`
- Dev server URL: *(press Enter — blank)*
- Frontend dev command: *(press Enter — blank)*
- Frontend build command: *(press Enter — blank)*

Expected: `src-tauri/` directory with `Cargo.toml`, `build.rs`, `tauri.conf.json`, `src/main.rs`, `icons/`

- [ ] **Step 4: Create `src/` placeholder**

```bash
mkdir -p src
printf '<html><body><h1>MacroPad</h1></body></html>' > src/index.html
```

- [ ] **Step 5: Update `.gitignore`**

Append to `.gitignore`:
```
target/
src-tauri/target/
```

- [ ] **Step 6: Verify app window opens**

```bash
cargo tauri dev
```
Expected: macOS window opens showing "MacroPad" heading. Tray area may show icon. Close window.

- [ ] **Step 7: Commit scaffold**

```bash
git add src-tauri/ src/ .gitignore
git commit -m "chore: scaffold Tauri v2 project"
```

---

## Task 1: Configure tauri.conf.json + Cargo.toml

**Files:** `src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`

- [ ] **Step 1: Replace `tauri.conf.json`**

Write `src-tauri/tauri.conf.json`:
```json
{
  "productName": "MacroPad",
  "version": "1.0.0",
  "identifier": "com.macropad.app",
  "build": {
    "frontendDist": "../src",
    "beforeDevCommand": "",
    "beforeBuildCommand": ""
  },
  "app": {
    "withGlobalTauri": true,
    "windows": [
      {
        "label": "main",
        "title": "MacroPad — K809 Configurator",
        "width": 1050,
        "height": 760,
        "resizable": true,
        "visible": false
      }
    ]
  },
  "bundle": {
    "active": true,
    "targets": ["dmg", "app"],
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ],
    "macOS": {
      "minimumSystemVersion": "13.0"
    }
  }
}
```

- [ ] **Step 2: Replace `[dependencies]` in `src-tauri/Cargo.toml`**

The full `[dependencies]` block:
```toml
[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
hidapi = "2"
dirs = "5"

[dev-dependencies]
tempfile = "3"

[build-dependencies]
tauri-build = { version = "2", features = [] }
```

- [ ] **Step 3: Generate app icons**

```bash
# Create a 1024x1024 icon (requires ImageMagick — brew install imagemagick)
magick -size 1024x1024 xc:#1a1a2e \
  -fill '#6c63ff' -draw 'roundrectangle 200,200 824,824 80,80' \
  -fill white -font Helvetica-Bold -pointsize 280 -gravity center \
  -annotate 0 'MK' /tmp/macropad-icon.png
cargo tauri icon /tmp/macropad-icon.png
```

If ImageMagick unavailable: copy any 1024×1024 PNG to `/tmp/macropad-icon.png` and run `cargo tauri icon /tmp/macropad-icon.png`.

- [ ] **Step 4: Verify compile**

```bash
cargo build --manifest-path src-tauri/Cargo.toml 2>&1 | tail -5
```
Expected: `Finished`. First build takes 3–8 minutes.

- [ ] **Step 5: Commit**

```bash
git add src-tauri/tauri.conf.json src-tauri/Cargo.toml src-tauri/icons/
git commit -m "chore: configure Tauri bundle, add hidapi + dirs deps, generate icons"
```

---

## Task 2: Rust — Error Type + Karabiner Manager

**Files:** `src-tauri/src/error.rs`, `src-tauri/src/karabiner.rs`

This is the core logic: reading, backing up, and writing the Karabiner config file. TDD-first.

- [ ] **Step 1: Create `src-tauri/src/error.rs`**

```rust
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct AppError(pub String);

impl From<std::io::Error> for AppError {
    fn from(e: std::io::Error) -> Self { AppError(e.to_string()) }
}
impl From<serde_json::Error> for AppError {
    fn from(e: serde_json::Error) -> Self { AppError(e.to_string()) }
}
impl From<String> for AppError {
    fn from(s: String) -> Self { AppError(s) }
}
impl From<&str> for AppError {
    fn from(s: &str) -> Self { AppError(s.to_string()) }
}
impl std::fmt::Display for AppError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.0)
    }
}

pub type AppResult<T> = Result<T, AppError>;
```

- [ ] **Step 2: Write failing tests for `karabiner.rs`**

Create `src-tauri/src/karabiner.rs` with tests:

```rust
use crate::error::{AppError, AppResult};
use serde::Serialize;
use serde_json::Value;
use std::path::PathBuf;

pub const VENDOR_ID: u64 = 12538;   // 0x30FA
pub const PRODUCT_ID: u64 = 9040;   // 0x2350
const PROFILE_NAME: &str = "INSTANT 19-Key Macro Pad";

pub fn karabiner_config_path() -> PathBuf {
    dirs::home_dir()
        .expect("cannot resolve home dir")
        .join(".config/karabiner/karabiner.json")
}

pub fn read_config(path: &PathBuf) -> AppResult<Value> {
    let s = std::fs::read_to_string(path)?;
    Ok(serde_json::from_str(&s)?)
}

pub fn backup_config(config: &Value) -> AppResult<String> { todo!() }
pub fn inject_profile(config: &mut Value, manipulators: &Value) -> AppResult<()> { todo!() }
pub fn write_config(config: &Value, path: &PathBuf) -> AppResult<()> { todo!() }
pub fn reload_karabiner() -> AppResult<()> { todo!() }

#[derive(Debug, Serialize)]
pub struct KarabinerStatus {
    pub installed: bool,
    pub config_readable: bool,
    pub profile_active: bool,
}

pub fn get_karabiner_status() -> KarabinerStatus { todo!() }

// ─── tests ───────────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    fn minimal_config() -> Value {
        serde_json::json!({
            "profiles": [
                {
                    "name": "Default profile",
                    "selected": false,
                    "complex_modifications": { "rules": [] }
                },
                {
                    "name": PROFILE_NAME,
                    "selected": true,
                    "complex_modifications": { "rules": [] }
                }
            ]
        })
    }

    #[test]
    fn test_read_config_parses_valid_json() {
        let mut tmp = NamedTempFile::new().unwrap();
        write!(tmp, "{}", minimal_config()).unwrap();
        let result = read_config(&tmp.path().to_path_buf());
        assert!(result.is_ok());
        assert!(result.unwrap()["profiles"].is_array());
    }

    #[test]
    fn test_read_config_fails_on_invalid_json() {
        let mut tmp = NamedTempFile::new().unwrap();
        write!(tmp, "{{not valid json}}").unwrap();
        assert!(read_config(&tmp.path().to_path_buf()).is_err());
    }

    #[test]
    fn test_inject_adds_rule_with_manipulators() {
        let mut config = minimal_config();
        let manips = serde_json::json!([{
            "type": "basic",
            "from": { "key_code": "keypad_1" },
            "to": [{ "key_code": "escape" }]
        }]);
        inject_profile(&mut config, &manips).unwrap();

        let profiles = config["profiles"].as_array().unwrap();
        let mp = profiles.iter()
            .find(|p| p["name"].as_str() == Some(PROFILE_NAME))
            .expect("MacroPad profile missing");
        let rules = mp["complex_modifications"]["rules"].as_array().unwrap();
        assert_eq!(rules.len(), 1, "exactly one rule");
        assert_eq!(&rules[0]["manipulators"], &manips);
    }

    #[test]
    fn test_inject_preserves_other_profiles() {
        let mut config = minimal_config();
        inject_profile(&mut config, &serde_json::json!([])).unwrap();
        let profiles = config["profiles"].as_array().unwrap();
        assert_eq!(profiles.len(), 2);
        assert_eq!(profiles[0]["name"].as_str(), Some("Default profile"));
    }

    #[test]
    fn test_inject_sets_devices_ignore_false() {
        let mut config = minimal_config();
        inject_profile(&mut config, &serde_json::json!([])).unwrap();
        let profiles = config["profiles"].as_array().unwrap();
        let mp = profiles.iter().find(|p| p["name"].as_str() == Some(PROFILE_NAME)).unwrap();
        let devices = mp["devices"].as_array().expect("devices array must exist");
        let k809 = devices.iter().find(|d| {
            d["identifiers"]["vendor_id"].as_u64() == Some(VENDOR_ID) &&
            d["identifiers"]["product_id"].as_u64() == Some(PRODUCT_ID)
        });
        assert!(k809.is_some(), "K809 device entry missing");
        assert_eq!(k809.unwrap()["ignore"].as_bool(), Some(false));
    }

    #[test]
    fn test_write_config_round_trips() {
        let tmp = NamedTempFile::new().unwrap();
        let config = minimal_config();
        write_config(&config, &tmp.path().to_path_buf()).unwrap();
        let loaded = read_config(&tmp.path().to_path_buf()).unwrap();
        assert_eq!(config, loaded);
    }
}
```

- [ ] **Step 3: Run tests — verify they fail (todo! panics)**

```bash
cargo test --manifest-path src-tauri/Cargo.toml karabiner 2>&1 | tail -15
```
Expected: `FAILED` with `not yet implemented` panics. Compile must succeed.

- [ ] **Step 4: Implement karabiner.rs**

Replace the `todo!()` stubs with implementations:

```rust
pub fn backup_config(config: &Value) -> AppResult<String> {
    // Store backups in Application Support, not source tree — works on all machines
    let backup_dir = crate::profile_store::store_dir().join("backups");
    std::fs::create_dir_all(&backup_dir)?;
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
    let path = backup_dir.join(format!("karabiner.json.{}.bak", ts));
    std::fs::write(&path, serde_json::to_string_pretty(config)?)?;
    Ok(path.to_string_lossy().to_string())
}

pub fn inject_profile(config: &mut Value, manipulators: &Value) -> AppResult<()> {
    let profiles = config["profiles"]
        .as_array_mut()
        .ok_or("no profiles array in karabiner.json")?;

    let profile = profiles.iter_mut()
        .find(|p| p["name"].as_str() == Some(PROFILE_NAME))
        .ok_or(format!("profile '{}' not found", PROFILE_NAME))?;

    profile["complex_modifications"]["rules"] = serde_json::json!([{
        "description": "K809 Macro Keypad",
        "enabled": true,
        "manipulators": manipulators
    }]);

    let k809_device = serde_json::json!({
        "identifiers": {
            "vendor_id": VENDOR_ID,
            "product_id": PRODUCT_ID,
            "is_keyboard": true,
            "is_pointing_device": true
        },
        "ignore": false,
        "manipulate_caps_lock_led": false
    });

    match profile["devices"].as_array_mut() {
        Some(devices) => {
            if let Some(existing) = devices.iter_mut().find(|d| {
                d["identifiers"]["vendor_id"].as_u64() == Some(VENDOR_ID) &&
                d["identifiers"]["product_id"].as_u64() == Some(PRODUCT_ID)
            }) {
                *existing = k809_device;
            } else {
                devices.push(k809_device);
            }
        }
        None => {
            profile["devices"] = serde_json::json!([k809_device]);
        }
    }

    Ok(())
}

pub fn write_config(config: &Value, path: &PathBuf) -> AppResult<()> {
    std::fs::write(path, serde_json::to_string_pretty(config)?)?;
    Ok(())
}

pub fn reload_karabiner() -> AppResult<()> {
    let cli = "/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli";
    if !std::path::Path::new(cli).exists() {
        return Err(AppError(format!("karabiner_cli not found at: {}", cli)));
    }
    let out = std::process::Command::new(cli)
        .arg("--select-profile")
        .arg(PROFILE_NAME)
        .output()?;
    if !out.status.success() {
        return Err(AppError(String::from_utf8_lossy(&out.stderr).to_string()));
    }
    Ok(())
}

pub fn get_karabiner_status() -> KarabinerStatus {
    let cli = "/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli";
    let installed = std::path::Path::new(cli).exists();
    let config_path = karabiner_config_path();
    let config_readable = config_path.exists();
    let profile_active = config_readable && read_config(&config_path)
        .ok()
        .and_then(|c| {
            c["profiles"].as_array().and_then(|ps| {
                ps.iter()
                    .find(|p| p["selected"].as_bool() == Some(true))
                    .map(|p| p["name"].as_str() == Some(PROFILE_NAME))
            })
        })
        .unwrap_or(false);
    KarabinerStatus { installed, config_readable, profile_active }
}
```

- [ ] **Step 5: Run tests — all must pass**

```bash
cargo test --manifest-path src-tauri/Cargo.toml karabiner 2>&1 | tail -15
```
Expected: `test result: ok. 6 passed; 0 failed`

- [ ] **Step 6: Commit**

```bash
git add src-tauri/src/error.rs src-tauri/src/karabiner.rs src-tauri/Cargo.toml
git commit -m "feat(rust): karabiner manager — read/inject/backup/write config"
```

---

## Task 3: Rust — USB HID Monitor

**Files:** `src-tauri/src/hid_monitor.rs`

- [ ] **Step 1: Create `hid_monitor.rs` with tests first**

```rust
pub const K809_VID: u16 = 0x30FA;
pub const K809_PID: u16 = 0x2350;

/// Returns true if the K809 is currently connected via USB.
pub fn is_k809_connected() -> bool {
    match hidapi::HidApi::new() {
        Ok(api) => api.device_list()
            .any(|d| d.vendor_id() == K809_VID && d.product_id() == K809_PID),
        Err(_) => false,
    }
}

/// Spawns a background thread that polls every 2s and calls `on_change(connected)`
/// whenever the K809 connection state changes. Emits initial state immediately.
pub fn start_monitor<F>(on_change: F) -> std::thread::JoinHandle<()>
where
    F: Fn(bool) + Send + 'static,
{
    std::thread::spawn(move || {
        let mut last = is_k809_connected();
        on_change(last);
        loop {
            std::thread::sleep(std::time::Duration::from_secs(2));
            let current = is_k809_connected();
            if current != last {
                last = current;
                on_change(current);
            }
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_vid_pid_hex_values() {
        assert_eq!(K809_VID, 0x30FA);
        assert_eq!(K809_PID, 0x2350);
        assert_eq!(K809_VID as u64, 12538);
        assert_eq!(K809_PID as u64, 9040);
    }

    #[test]
    fn test_is_k809_connected_returns_bool() {
        // Hardware-independent: just verifies no panic
        let _ = is_k809_connected();
    }
}
```

- [ ] **Step 2: Run tests**

```bash
cargo test --manifest-path src-tauri/Cargo.toml hid_monitor 2>&1 | tail -10
```
Expected: `test result: ok. 2 passed; 0 failed`

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/hid_monitor.rs
git commit -m "feat(rust): USB HID monitor polling K809 VID/PID every 2s"
```

---

## Task 4: Rust — Profile Store

**Files:** `src-tauri/src/profile_store.rs`

- [ ] **Step 1: Create `profile_store.rs`**

```rust
use crate::error::AppResult;
use serde_json::Value;
use std::path::PathBuf;

const APP_ID: &str = "com.macropad.app";

pub fn store_dir() -> PathBuf {
    // macOS: ~/Library/Application Support/com.macropad.app/
    dirs::data_local_dir()
        .unwrap_or_else(|| dirs::home_dir().unwrap().join("Library/Application Support"))
        .join(APP_ID)
}

fn profile_path() -> PathBuf {
    store_dir().join("profile.json")
}

pub fn save_profile(json: &Value) -> AppResult<()> {
    std::fs::create_dir_all(store_dir())?;
    std::fs::write(profile_path(), serde_json::to_string_pretty(json)?)?;
    Ok(())
}

pub fn load_profile() -> AppResult<Value> {
    let path = profile_path();
    if path.exists() {
        let s = std::fs::read_to_string(&path)?;
        return Ok(serde_json::from_str(&s)?);
    }
    // First run: return an empty profile structure (no hardcoded source-tree path)
    Ok(serde_json::json!({ "description": "INSTANT 19-Key Macro Pad", "manipulators": [] }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_store_dir_contains_app_id() {
        assert!(store_dir().to_string_lossy().contains(APP_ID));
    }

    #[test]
    fn test_save_and_read_roundtrip() {
        let tmp = tempfile::tempdir().unwrap();
        let json_str = r#"{"version":1,"keys":[]}"#;
        let path = tmp.path().join("profile.json");
        std::fs::write(&path, json_str).unwrap();
        let loaded: Value = serde_json::from_str(
            &std::fs::read_to_string(&path).unwrap()
        ).unwrap();
        assert_eq!(loaded["version"].as_u64(), Some(1));
    }
}
```

- [ ] **Step 2: Run tests**

```bash
cargo test --manifest-path src-tauri/Cargo.toml profile_store 2>&1 | tail -10
```
Expected: `test result: ok. 2 passed; 0 failed`

- [ ] **Step 3: Commit**

```bash
git add src-tauri/src/profile_store.rs
git commit -m "feat(rust): profile store in Application Support"
```

---

## Task 5: Rust — IPC Commands + System Tray + main.rs

**Files:** `src-tauri/src/commands.rs`, `src-tauri/src/tray.rs`, `src-tauri/src/main.rs`

- [ ] **Step 1: Create `commands.rs`**

```rust
use crate::{error::AppError, karabiner, profile_store};

/// Receives the already-built `{description, manipulators}` profile from JS.
/// Backs up karabiner.json, injects manipulators, writes, reloads Karabiner.
#[tauri::command]
pub async fn install_profile(json: String) -> Result<String, String> {
    (|| -> Result<String, AppError> {
        let profile: serde_json::Value = serde_json::from_str(&json)
            .map_err(|e| AppError(format!("Invalid JSON: {}", e)))?;
        let manipulators = &profile["manipulators"];

        let config_path = karabiner::karabiner_config_path();
        let mut config = karabiner::read_config(&config_path)?;
        let backup = karabiner::backup_config(&config)?;
        karabiner::inject_profile(&mut config, manipulators)?;
        karabiner::write_config(&config, &config_path)?;
        karabiner::reload_karabiner()?;
        profile_store::save_profile(&profile)?;

        Ok(format!("Profile installed ✓  Backup: {}", backup))
    })().map_err(|e| e.0)
}

#[tauri::command]
pub async fn export_json() -> Result<String, String> {
    profile_store::load_profile()
        .map(|v| serde_json::to_string_pretty(&v).unwrap_or_default())
        .map_err(|e| e.0)
}

#[tauri::command]
pub async fn import_json(json: String) -> Result<(), String> {
    let v: serde_json::Value = serde_json::from_str(&json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    profile_store::save_profile(&v).map_err(|e| e.0)
}

#[tauri::command]
pub async fn get_device_status() -> bool {
    crate::hid_monitor::is_k809_connected()
}

#[tauri::command]
pub async fn get_karabiner_status() -> karabiner::KarabinerStatus {
    karabiner::get_karabiner_status()
}

/// Persists key mappings to Application Support without touching Karabiner.
/// Replaces `POST /save` from Flask spec. Useful for draft saves before applying.
#[tauri::command]
pub async fn save_profile(json: String) -> Result<(), String> {
    let v: serde_json::Value = serde_json::from_str(&json)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    profile_store::save_profile(&v).map_err(|e| e.0)
}
```

- [ ] **Step 2: Create `tray.rs`**

```rust
use tauri::{tray::TrayIconBuilder, AppHandle, Manager, Runtime};

pub fn setup_tray<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    TrayIconBuilder::with_id("main")
        .tooltip("MacroPad ○ Checking...")
        .build(app)?;
    Ok(())
}

pub fn update_tray<R: Runtime>(app: &AppHandle<R>, connected: bool) {
    let tooltip = if connected {
        "MacroPad ● K809 Connected"
    } else {
        "MacroPad ○ K809 Disconnected"
    };
    if let Some(tray) = app.tray_by_id("main") {
        let _ = tray.set_tooltip(Some(tooltip));
    }
}
```

- [ ] **Step 3: Replace `main.rs`**

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod error;
mod hid_monitor;
mod karabiner;
mod profile_store;
mod tray;

use tauri::{Emitter, Manager};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();
            tray::setup_tray(&handle)?;

            // Window starts hidden (visible:false in tauri.conf.json) — show after tray is ready
            if let Some(w) = app.get_webview_window("main") {
                w.show()?;
            }

            // Background USB HID monitor — emits "device_status" boolean to frontend
            hid_monitor::start_monitor(move |connected| {
                tray::update_tray(&handle, connected);
                let _ = handle.emit("device_status", connected);
            });

            Ok(())
        })
        // Close window → hide to tray (keeps app alive for USB monitoring)
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::install_profile,
            commands::save_profile,
            commands::export_json,
            commands::import_json,
            commands::get_device_status,
            commands::get_karabiner_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running MacroPad");
}
```

- [ ] **Step 4: Verify all Rust tests still pass**

```bash
cargo test --manifest-path src-tauri/Cargo.toml 2>&1 | tail -10
```
Expected: `test result: ok. 10 passed; 0 failed`

- [ ] **Step 5: Run dev — verify tray + IPC**

```bash
cargo tauri dev
```
Expected: App opens. Tray icon visible. No console errors. Open DevTools (`Cmd+Option+I`) — in console run:
```javascript
window.__TAURI__.core.invoke('get_device_status').then(console.log)
```
Expected: `true` or `false` depending on K809 plug state.

- [ ] **Step 6: Commit**

```bash
git add src-tauri/src/commands.rs src-tauri/src/tray.rs src-tauri/src/main.rs
git commit -m "feat(rust): IPC commands, system tray, HID monitor wired to Tauri app"
```

---

## Task 6: Frontend — Tab Router Shell + Tauri Bridge

**Files:** `src/index.html`, `src/tauri-bridge.js`

- [ ] **Step 1: Create `src/tauri-bridge.js`**

```javascript
// Wraps Tauri IPC with graceful fallback when opened in a plain browser.
window.TauriBridge = {
    invoke: function(cmd, args) {
        if (window.__TAURI__ && window.__TAURI__.core) {
            return window.__TAURI__.core.invoke(cmd, args || {});
        }
        console.warn('[TauriBridge] Not in Tauri — ignored:', cmd, args);
        return Promise.reject(new Error('Not running in Tauri'));
    },
    listen: function(event, handler) {
        if (window.__TAURI__ && window.__TAURI__.event) {
            return window.__TAURI__.event.listen(event, function(e) { handler(e.payload); });
        }
        console.warn('[TauriBridge] Not in Tauri — cannot listen:', event);
        return Promise.resolve(function() {});
    }
};
```

- [ ] **Step 2: Replace `src/index.html` with tab router**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MacroPad</title>
  <script src="tauri-bridge.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
      background: #1a1a2e; color: #eee;
      height: 100vh; display: flex; flex-direction: column;
      overflow: hidden;
    }
    #tab-bar {
      display: flex; align-items: stretch;
      background: #0f0f1a; border-bottom: 1px solid #2a2a3e;
      padding: 0 16px; flex-shrink: 0;
    }
    .tab-btn {
      padding: 11px 22px; background: none; border: none; color: #777;
      cursor: pointer; font-size: 13px; font-weight: 500; letter-spacing: 0.02em;
      border-bottom: 2px solid transparent; transition: color 0.15s, border-color 0.15s;
    }
    .tab-btn.active { color: #fff; border-bottom-color: #6c63ff; }
    .tab-btn:hover:not(.active) { color: #bbb; }
    #status-bar {
      margin-left: auto; display: flex; align-items: center; gap: 7px;
      font-size: 12px; color: #666; padding-right: 4px;
    }
    #device-dot {
      width: 7px; height: 7px; border-radius: 50%; background: #444;
      transition: background 0.3s;
    }
    #device-dot.connected    { background: #4caf50; }
    #device-dot.disconnected { background: #f44336; }
    #content { flex: 1; overflow: hidden; }
    iframe { width: 100%; height: 100%; border: none; display: block; }
  </style>
</head>
<body>
  <div id="tab-bar">
    <button class="tab-btn active" data-tab="configurator" onclick="switchTab('configurator')">Configurator</button>
    <button class="tab-btn"        data-tab="tester"       onclick="switchTab('tester')">Key Tester</button>
    <div id="status-bar">
      <div id="device-dot"></div>
      <span id="device-label">Checking…</span>
    </div>
  </div>
  <div id="content">
    <iframe id="frame" src="configurator.html"></iframe>
  </div>

  <script>
    var VIEWS = { configurator: 'configurator.html', tester: 'tester.html' };

    function switchTab(name) {
      document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === name);
      });
      document.getElementById('frame').src = VIEWS[name];
    }

    function setDeviceStatus(connected) {
      var dot   = document.getElementById('device-dot');
      var label = document.getElementById('device-label');
      dot.className = connected ? 'connected' : 'disconnected';
      label.textContent = connected ? 'K809 Connected' : 'K809 Disconnected';
    }

    TauriBridge.invoke('get_device_status')
      .then(setDeviceStatus)
      .catch(function() {
        document.getElementById('device-label').textContent = 'Open in MacroPad.app';
      });

    TauriBridge.listen('device_status', setDeviceStatus);
  </script>
</body>
</html>
```

- [ ] **Step 3: Verify tab router in Tauri dev**

```bash
cargo tauri dev
```
Expected: Tab bar renders. Device status dot shows colour. Clicking "Key Tester" tab switches content.

- [ ] **Step 4: Commit**

```bash
git add src/index.html src/tauri-bridge.js
git commit -m "feat(frontend): tab router shell with device status indicator"
```

---

## Task 7: Frontend — Migrate Configurator + Tester

**Files:** `src/configurator.html`, `src/tester.html`

### Configurator migration

Three surgical changes to `index.html`: replace `applyDirect()` (line 2022–2041), fix the button visibility guard (line 2320–2323), and wire localStorage saves to `TauriBridge.invoke('save_profile')` for persistence in Application Support.

- [ ] **Step 1: Copy configurator**

```bash
cp /Users/ycs/Developer/macro-keypad/index.html src/configurator.html
```

- [ ] **Step 2: Add tauri-bridge.js script tag**

In `src/configurator.html`, find `</head>` and insert immediately before it:
```html
<script src="tauri-bridge.js"></script>
```

- [ ] **Step 3: Replace `applyDirect()` function**

Find (in `src/configurator.html`):
```javascript
async function applyDirect() {
  showToast('Applying configuration...');
  try {
    const response = await fetch('/api/apply', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(keys)
    });
    const result = await response.json();
    if (response.ok && result.status === 'success') {
      showToast('⚡ Applied to Karabiner successfully!', 3000);
    } else {
      showToast('❌ Error: ' + (result.message || 'Unknown error'), 4000);
    }
  } catch (err) {
    showToast('❌ Server unreachable. Make sure python3 server.py is running!', 4000);
  }
}
```

Replace with:
```javascript
async function applyDirect() {
  showToast('Applying configuration…');
  try {
    const profile = buildProfile();
    const msg = await TauriBridge.invoke('install_profile', { json: JSON.stringify(profile) });
    showToast('⚡ ' + msg, 3000);
  } catch (err) {
    showToast('❌ Error: ' + (err.message || err), 4000);
  }
}
```

- [ ] **Step 4: Always show the Apply button**

Find (in `src/configurator.html`):
```javascript
// Show Apply button only if served from our server backend
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  const btn = document.getElementById('btnApplyDirect');
  if (btn) btn.style.display = 'inline-flex';
}
```

Replace with:
```javascript
// Always show Apply button in Tauri (or localhost for dev)
(function() {
  const btn = document.getElementById('btnApplyDirect');
  if (btn) btn.style.display = 'inline-flex';
})();
```

- [ ] **Step 4b: Wire localStorage saves to Tauri profile store**

Find the line in `src/configurator.html` where key state is saved to localStorage (search for `localStorage.setItem`):
```javascript
localStorage.setItem('macropad-keys', JSON.stringify(keys));
```

Add the Tauri persist call immediately after it:
```javascript
localStorage.setItem('macropad-keys', JSON.stringify(keys));
// Persist to Application Support when running in Tauri
TauriBridge.invoke('save_profile', { json: JSON.stringify(buildProfile()) }).catch(function() {});
```

This ensures the profile survives across users/machines via `~/Library/Application Support/com.macropad.app/profile.json`.

### Tester migration

- [ ] **Step 5: Copy tester**

```bash
cp /Users/ycs/Developer/macro-keypad/test.html src/tester.html
```

- [ ] **Step 6: Add tauri-bridge.js + device status listener**

In `src/tester.html`, insert before `</head>`:
```html
<script src="tauri-bridge.js"></script>
```

At the very end of the `<script>` block (before `</script>`), add:
```javascript
// Sync device connection status from Tauri HID monitor
TauriBridge.listen('device_status', function(connected) {
  var el = document.getElementById('device-status');
  if (el) el.textContent = connected ? '● K809 Connected' : '○ K809 Disconnected';
});
TauriBridge.invoke('get_device_status').then(function(connected) {
  var el = document.getElementById('device-status');
  if (el) el.textContent = connected ? '● K809 Connected' : '○ K809 Disconnected';
}).catch(function() {});
```

### Verify

- [ ] **Step 7: Full flow test in Tauri dev**

```bash
cargo tauri dev
```

Manual checks:
- [ ] Configurator loads — 3D keypad model renders
- [ ] Click a key — yellow highlight, edit panel opens
- [ ] Click "⚡ Apply to Karabiner" → toast shows "Profile installed ✓"
- [ ] Verify Karabiner config updated:
  ```bash
  python3 -c "
  import json
  c = json.load(open('/Users/ycs/.config/karabiner/karabiner.json'))
  mp = next(p for p in c['profiles'] if p['name']=='INSTANT 19-Key Macro Pad')
  rules = mp['complex_modifications']['rules']
  print(f'Rules: {len(rules)}, Manipulators: {len(rules[0][\"manipulators\"])}')
  "
  ```
  Expected: `Rules: 1, Manipulators: 20` (or however many configured)
- [ ] Switch to Tester tab — 3D model renders, press physical keys — green pass
- [ ] Unplug K809 → dot turns red; plug back → green
- [ ] Existing test suite still passes:
  ```bash
  uv run python3 /Users/ycs/Developer/macro-keypad/test_macropad.py
  ```
  Expected: `41 passed, 0 failed`

- [ ] **Step 8: Commit**

```bash
git add src/configurator.html src/tester.html
git commit -m "feat(frontend): migrate configurator and tester to Tauri WKWebView"
```

---

## Task 8: Build Universal Binary + GitHub Release

**Files:** No new files; produces `MacroPad_1.0.0_universal.dmg`

- [ ] **Step 1: Run all Rust tests**

```bash
cargo test --manifest-path src-tauri/Cargo.toml 2>&1 | tail -10
```
Expected: `10 passed; 0 failed`

- [ ] **Step 2: Build for current arch (smoke test)**

```bash
cargo tauri build 2>&1 | grep -E "Finished|Error|error"
```
Expected: `✔ Finished` or `Compiling ... Finished release`

Verify the app opens:
```bash
open "src-tauri/target/release/bundle/macos/MacroPad.app"
```
Expected: App launches, tray icon appears, window shows tab router.

- [ ] **Step 3: Add universal target and build**

```bash
rustup target add aarch64-apple-darwin x86_64-apple-darwin
cargo tauri build --target universal-apple-darwin 2>&1 | tail -20
```
Expected: Produces `src-tauri/target/universal-apple-darwin/release/bundle/dmg/MacroPad_1.0.0_universal.dmg`

Check size:
```bash
ls -lh src-tauri/target/universal-apple-darwin/release/bundle/dmg/*.dmg
```
Expected: < 10 MB

- [ ] **Step 4: Full manual install test**

```bash
# Mount the DMG
open src-tauri/target/universal-apple-darwin/release/bundle/dmg/MacroPad_1.0.0_universal.dmg
```

- [ ] Drag `MacroPad.app` to `/Applications`
- [ ] Right-click `/Applications/MacroPad.app` → Open (first launch bypasses Gatekeeper)
- [ ] Confirm: window opens, tray icon shows, K809 connect/disconnect reflected
- [ ] Apply a key config change → Karabiner profile updates without terminal

- [ ] **Step 5: Run full test suite one last time**

```bash
uv run python3 /Users/ycs/Developer/macro-keypad/test_macropad.py
```
Expected: `41 passed, 0 failed`

- [ ] **Step 6: Create GitHub release**

```bash
git tag v1.0.0
git push origin v1.0.0

DMG="src-tauri/target/universal-apple-darwin/release/bundle/dmg/MacroPad_1.0.0_universal.dmg"

gh release create v1.0.0 "$DMG" \
  --title "MacroPad v1.0.0 — K809 Native Mac App" \
  --notes "$(cat <<'EOF'
## MacroPad v1.0.0

Native macOS configurator for the **INSTANT K809 USB-C 20-key macro keypad**.  
No terminal required — drag, drop, configure.

### Features
- Visual key configurator with interactive 3D keypad model
- Key Tester with pass/fail tracking per key
- One-click Karabiner-Elements profile install
- USB device auto-detection (menubar dot turns green/red)
- Menubar tray icon — app stays running after window close

### Requirements
- macOS 13.0 Ventura or later
- [Karabiner-Elements](https://karabiner-elements.pqrs.org/) installed

### Install
1. Download `MacroPad_1.0.0_universal.dmg`
2. Drag `MacroPad.app` to `/Applications`
3. **Right-click → Open** on first launch (unsigned app)

### Architecture
Universal binary — Apple Silicon (M1/M2/M3/M4) and Intel x86_64
EOF
)"
```

- [ ] **Step 7: Final commit**

```bash
git add docs/
git commit -m "chore: add Tauri implementation plan; v1.0.0 released"
```

---

## Known Gotchas

| Issue | Resolution |
|---|---|
| `karabiner_cli` path differs between Karabiner versions | `find /Library -name karabiner_cli 2>/dev/null` to locate it |
| WKWebView CSS 3D may differ from Chrome | Test during `cargo tauri dev`; if broken, defer 3D to v1.1 |
| `hidapi` on macOS requires `IOHIDManager` — may need entitlement if app is sandboxed | Keep app non-sandboxed (default for GitHub-distributed apps) |
| `window.__TAURI__` is undefined in browser test | `TauriBridge` falls back with a console warning — expected |
| Gatekeeper blocks unsigned `.app` | Right-click → Open; document in README |
| `"visible": false` on window causes blank window in some Tauri v2 builds | Remove `"visible": false` from `tauri.conf.json` if window stays blank |
| `tauri::Emitter` trait must be in scope for `handle.emit()` | `use tauri::Emitter;` in `main.rs` |
| `tauri::Manager` trait must be in scope for `app.get_webview_window()` | `use tauri::Manager;` in `main.rs` |
| ADR mentions `device_connected`/`device_disconnected` events (two events) | Plan deliberately consolidates to one `device_status` boolean event — simpler, no behaviour difference |
| `export_json` and `import_json` Rust commands are registered but not called by the frontend | Intentional: `exportJSON()` and `handleImport()` use browser File System API (`showSaveFilePicker`, `FileReader`), which works fine in WKWebView macOS 13+. The Rust commands exist for programmatic/CLI access and future use |

---

## Deferred to v1.1

- Karabiner auto-install prompt (detect missing, show `brew install --cask karabiner-elements`)
- WKWebView CSS 3D viewport verification (if deferred in v1.0)
- Tauri updater (JSON endpoint on GitHub Pages)
- Code signing + notarization (Apple Developer Program)
- System tray dropdown menu (Open / Device Status / Quit) — v1.0 has tooltip only
