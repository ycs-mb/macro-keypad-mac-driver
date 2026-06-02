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

pub fn backup_config(config: &Value) -> AppResult<String> {
    // Backups go to Application Support, not the source tree — works on all machines
    let backup_dir = crate::profile_store::store_dir().join("backups");
    std::fs::create_dir_all(&backup_dir)?;
    let ts = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let path = backup_dir.join(format!("karabiner.json.{}.bak", ts));
    std::fs::write(&path, serde_json::to_string_pretty(config)?)?;
    Ok(path.to_string_lossy().to_string())
}

pub fn inject_profile(config: &mut Value, manipulators: &Value) -> AppResult<()> {
    let profiles = config["profiles"]
        .as_array_mut()
        .ok_or("no profiles array in karabiner.json")?;

    let profile = profiles
        .iter_mut()
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

#[derive(Debug, Serialize)]
pub struct KarabinerStatus {
    pub installed: bool,
    pub config_readable: bool,
    pub profile_active: bool,
}

pub fn get_karabiner_status() -> KarabinerStatus {
    let cli = "/Library/Application Support/org.pqrs/Karabiner-Elements/bin/karabiner_cli";
    let installed = std::path::Path::new(cli).exists();
    let config_path = karabiner_config_path();
    let config_readable = config_path.exists();
    let profile_active = config_readable
        && read_config(&config_path)
            .ok()
            .and_then(|c| {
                c["profiles"].as_array().and_then(|ps| {
                    ps.iter()
                        .find(|p| p["selected"].as_bool() == Some(true))
                        .map(|p| p["name"].as_str() == Some(PROFILE_NAME))
                })
            })
            .unwrap_or(false);
    KarabinerStatus {
        installed,
        config_readable,
        profile_active,
    }
}

// ─── tests ────────────────────────────────────────────────────────────────────
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
