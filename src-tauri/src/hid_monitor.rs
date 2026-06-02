pub const K809_VID: u16 = 0x30FA;
pub const K809_PID: u16 = 0x2350;

/// Returns true if the K809 is currently connected.
pub fn is_k809_connected() -> bool {
    match hidapi::HidApi::new() {
        Ok(api) => api
            .device_list()
            .any(|d| d.vendor_id() == K809_VID && d.product_id() == K809_PID),
        Err(_) => false,
    }
}

/// Spawns a background thread polling every 2s; calls `on_change(connected)` on state change.
/// Emits initial state immediately on first call.
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
        // Hardware-independent: verifies no panic
        let _ = is_k809_connected();
    }
}
