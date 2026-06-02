# INSTANT 20-Key Macro Pad — Project Summary

## Hardware
- **Device**: INSTANT USB-C 20-key programmable macro keypad (K809)
- **VID**: 12538 (0x30FA) | **PID**: 9040 (0x2350)
- **No official Mac driver** — uses standard HID keyboard protocol
- **Rotary encoder**: sends volume_increment / volume_decrement (separate from 20 keys)
- **Physical layout**: 3 rows of keys + circular D-pad + rotary volume knob

## Confirmed Key Codes (all are `key_code` type, NOT consumer_key_code)

| Pad Key | Raw keycode sent | Assigned action |
|---------|-----------------|-----------------|
| Key 1   | `keypad_1`      | escape |
| Key 2   | `keypad_2`      | open VS Code |
| Key 3   | `keypad_3`      | open Microsoft Edge |
| Key 4   | `keypad_4`      | play_or_pause (media) |
| Key 5   | `keypad_5`      | rewind (media) |
| Key 6   | `keypad_6`      | fast_forward (media) |
| Key 7   | `keypad_7`      | cmd+z (Undo) |
| Key 8   | `keypad_8`      | cmd+shift+z (Redo) |
| Key 9   | `keypad_9`      | cmd+c (Copy) |
| Key 10  | `keypad_0`      | cmd+v (Paste) |
| Key 11  | `keypad_period` | cmd+x (Cut) |
| Key 12  | `keypad_enter`  | screencapture interactive |
| Key 13  | `keypad_hyphen` | mission_control |
| Key 14  | `keypad_plus`   | cmd+shift+period (show hidden files) |
| Key 15  | `spacebar`      | cmd+space (Spotlight) |
| Key 16  | `down_arrow`    | down_arrow (passthrough) |
| Key 17  | `left_arrow`    | left_arrow (passthrough) |
| Key 18  | `right_arrow`   | right_arrow (passthrough) |
| Key 19  | `up_arrow`      | up_arrow (passthrough) |
| Key 20  | **Unknown**     | cmd+tab (app switcher) — *D-pad center press, raw code pending discovery* |

## Solution: Karabiner-Elements (device-scoped complex_modifications)

**Why Karabiner**: Only tool that filters remaps by VID/PID — so normal keyboard keys (a, b, arrows, spacebar) are NOT intercepted. Hammerspoon's eventtap cannot filter by source device.

**Status**: Karabiner-Elements is installed and fully configured.
- Profile: `INSTANT 19-Key Macro Pad` (selected: true)
- 20 manipulators with `device_if` condition (vendor_id: 12538, product_id: 9040)
- Device "Modify events" is ON (ignore=false)

## Files at ~/Developer/macro-keypad/

| File | Purpose |
|------|---------|
| `karabiner_profile.json` | The 20-key remap rules in Karabiner JSON format |
| `karabiner_generator.js` | ES5.1 JavaScript that generates the same rules programmatically |
| `install_profile.sh` | Injects karabiner_profile.json into ~/.config/karabiner/karabiner.json |
| `index.html` | **Configurator UI** — single-file web app with interactive 3D CSS model, key configuration, JSON export/import, and live server sync |
| `test.html` | **Key Tester UI** — single-file web app with interactive 3D CSS model, HID event detection, pass/fail tracking for all 20 keys |
| `server.py` | Local Flask server for JSON export automation and shell command execution from the UI |
| `test_macropad.py` | Automated verification suite (41 tests: JSON structure, key codes, actions, live config sync, round-trip export/import) |
| `watch_and_install.sh` | File watcher that auto-installs profile on changes |
| `identify_keys.py` | HID reader (blocked by macOS TCC — used Karabiner-EventViewer instead) |
| `hammerspoon_macropad.lua` | Hammerspoon approach (abandoned — can't filter by device source) |
| `install_hammerspoon.sh` | Hammerspoon installer (not needed) |
| `probe_serial.py` | CH340 serial probe (device has serial port but no response at any baud) |
| `product-photo/` | 4 reference product photos of the physical K809 macro pad |
| `backups/` | Timestamped backups of karabiner.json (20 backup snapshots) |

## Interactive 3D CSS Model

Both `index.html` and `test.html` include a fully interactive, mouse-rotatable 3D CSS model of the K809 keypad:

- **Engine**: Pure CSS 3D transforms (`perspective`, `transform-style: preserve-3d`, absolute coordinate layers). Zero external dependencies, 100% offline.
- **Chassis**: 6-face solid box (380×250×30px) with silver metallic bezel and brushed "CAM" logo.
- **Keycaps**: 20 watertight volumetric boxes (16px depth) with directional light-source shading:
  - **Red** keycaps: Keys 1, 12 (Enter), 13 (−), D-pad arrows, D-pad center
  - **Black** keycaps: Keys 2, 3, 4, 7, 8, 14 (+), 15 (Space)
  - **Gray** keycaps: Keys 5, 6, 9, 10, 11
  - **Yellow** (selected state in configurator), **Green** (pass), **Red** (fail) in tester
- **Rotary Volume Knob**: 16-sided cylinder with trigonometric radial positioning (`Math.cos`/`Math.sin`) for watertight solid rendering. Red metallic gradient with white indicator line.
- **Orbital Dragging**: Mouse left-click drag rotates the 3D model. Vertical pitch clamped between 20°–80° to prevent flipping underneath.
- **Micro-interactions**: Physics-based `cubic-bezier(0.25, 0.8, 0.25, 1)` transitions. Keys rise +3px and brighten on hover, compress −6px on click/active.

### Watertight Boundary Coordinate System

All keycap side faces use edge-aligned absolute positioning to eliminate subpixel rendering gaps:
- **Front**: `bottom: 0; transform-origin: bottom center; rotateX(90deg)`
- **Back**: `top: 0; transform-origin: top center; rotateX(-90deg)`
- **Left**: `left: 0; transform-origin: left center; rotateY(90deg)`
- **Right**: `right: 0; transform-origin: right center; rotateY(-90deg)`
- **Top**: `translateZ(16px)` (full width/height of parent)

## Current State

- ✅ Profile installed and active in `~/.config/karabiner/karabiner.json`
- ✅ Device "Modify events" enabled for INSTANT pad
- ✅ Configurator UI (`index.html`) with 3D view, key editing, JSON export/import, server sync
- ✅ Key Tester UI (`test.html`) with 3D view, HID event detection, pass/fail tracking
- ✅ Local server (`server.py`) for JSON export and shell command automation
- ✅ Automated test suite: **41 tests passing** (0 failures)
- ✅ 20 backup snapshots of karabiner config preserved

## Known Issues / Troubleshooting

- macOS TCC blocks direct HID reads — `hid` Python library gives "not permitted" (0xE00002E2)
- `sudo` does NOT bypass TCC — it's not Unix permissions
- Karabiner brew cask needs interactive sudo (run `brew install --cask karabiner-elements` in terminal directly)
- Key codes were discovered via Karabiner-EventViewer
- Key 20 (D-pad center press) raw keycode is still unknown — needs physical discovery

## Future: 3D WebGL Photogrammetry Model

A planned enhancement to replace the CSS 3D model with a photorealistic WebGL canvas reconstructed from a 360° video of the physical device:

1. **Capture**: 360° video of the K809 keypad (4K, 60fps, consistent lighting)
2. **Reconstruction**: Cloud photogrammetry via Luma AI / Polycam / Kiri Engine (avoids M2 8GB memory limits)
3. **Segmentation**: Blender (Metal GPU) — cut keycaps, knob, chassis into separate named mesh objects, set local origins, decimate polygons, bake normal maps
4. **Web Integration**: Three.js GLTFLoader with Draco-compressed `.glb` model, PBR materials, shadow maps
5. **Animation**: GSAP `elastic.out(1, 0.4)` spring physics for mechanical keypress feedback via raycasting
6. **Constraints**: Mac M2 8GB — textures capped at 2K WebP, reconstruction offloaded to cloud
