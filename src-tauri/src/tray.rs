use tauri::{tray::TrayIconBuilder, AppHandle, Runtime};

pub fn setup_tray<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    TrayIconBuilder::with_id("main")
        .tooltip("MacroPad ○ Checking…")
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
