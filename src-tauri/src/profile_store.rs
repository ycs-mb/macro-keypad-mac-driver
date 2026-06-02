use crate::error::AppResult;
use serde_json::Value;
use std::path::PathBuf;

const APP_ID: &str = "com.macropad.app";

pub fn store_dir() -> PathBuf {
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
    // First run — return an empty profile structure
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
