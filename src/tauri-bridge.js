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
