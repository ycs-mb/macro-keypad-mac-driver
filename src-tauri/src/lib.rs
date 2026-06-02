pub mod commands;
pub mod error;
pub mod hid_monitor;
pub mod karabiner;
pub mod profile_store;
pub mod tray;

use tauri::{Emitter, Manager};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
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
