use crate::{error::AppError, karabiner, profile_store};

/// Receives the already-built `{description, manipulators}` profile from JS buildProfile().
/// Backs up karabiner.json, injects manipulators, writes config, reloads Karabiner.
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
    })()
    .map_err(|e| e.0)
}

/// Persists key mappings to Application Support without touching Karabiner.
/// Replaces POST /save. Useful for draft saves before applying.
#[tauri::command]
pub async fn save_profile(json: String) -> Result<(), String> {
    let v: serde_json::Value =
        serde_json::from_str(&json).map_err(|e| format!("Invalid JSON: {}", e))?;
    profile_store::save_profile(&v).map_err(|e| e.0)
}

#[tauri::command]
pub async fn export_json() -> Result<String, String> {
    profile_store::load_profile()
        .map(|v| serde_json::to_string_pretty(&v).unwrap_or_default())
        .map_err(|e| e.0)
}

#[tauri::command]
pub async fn import_json(json: String) -> Result<(), String> {
    let v: serde_json::Value =
        serde_json::from_str(&json).map_err(|e| format!("Invalid JSON: {}", e))?;
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
