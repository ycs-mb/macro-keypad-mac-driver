// Wraps Tauri IPC. Works in both the top-level window and inside iframes
// (configurator/tester are loaded in <iframe> — fall back to window.parent.__TAURI__).
window.TauriBridge = (function() {
    function getTauri() {
        if (window.__TAURI__ && window.__TAURI__.core) return window.__TAURI__;
        try {
            if (window.parent && window.parent.__TAURI__ && window.parent.__TAURI__.core)
                return window.parent.__TAURI__;
        } catch (e) {}
        return null;
    }

    return {
        invoke: function(cmd, args) {
            var t = getTauri();
            if (t) return t.core.invoke(cmd, args || {});
            console.warn('[TauriBridge] Not in Tauri — ignored:', cmd, args);
            return Promise.reject(new Error('Not running in Tauri'));
        },
        listen: function(event, handler) {
            var t = getTauri();
            if (t) return t.event.listen(event, function(e) { handler(e.payload); });
            console.warn('[TauriBridge] Not in Tauri — cannot listen:', event);
            return Promise.resolve(function() {});
        }
    };
})();
