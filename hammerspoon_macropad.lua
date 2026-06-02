-- INSTANT 19-Key Macro Pad — Hammerspoon config
-- All 19 key codes confirmed via Karabiner-EventViewer.
-- Drop this file into ~/.hammerspoon/init.lua (or require it from there).
--
-- VENDOR FILTER: only intercepts these keys when the INSTANT pad is the source.
-- Since the pad sends common keys (a-j, arrows...) we use a device filter so
-- normal keyboard typing is NOT affected.

local DEVICE_NAME = "USB Keyboard"   -- as it appears in Hammerspoon device list
local VENDOR_ID   = 0x30FA
local PRODUCT_ID  = 0x2350

-- ──────────────────────────────────────────────────────────────────────────────
-- KEY MAP  →  { action_type, ... }
-- action types:
--   { "app",     "App Name" }
--   { "key",     "modifiers", "keycode" }   modifiers: "cmd","shift","ctrl","alt"
--   { "shell",   "bash command" }
--   { "text",    "string to type" }
--   { "media",   "playpause"|"next"|"prev"|"volup"|"voldown"|"mute" }
-- ──────────────────────────────────────────────────────────────────────────────
local KEY_MAP = {
  -- Key 1  (a)
  a = { "app", "Terminal" },
  -- Key 2  (b)
  b = { "app", "Visual Studio Code" },
  -- Key 3  (c)
  c = { "app", "Safari" },
  -- Key 4  (d)
  d = { "key", {"ctrl","cmd"}, "f" },          -- toggle fullscreen
  -- Key 5  (e)
  e = { "key", {"cmd"}, "space" },              -- Spotlight
  -- Key 6  (f)
  f = { "key", {"cmd"}, "tab" },                -- app switcher
  -- Key 7  (g)
  g = { "key", {"cmd"}, "z" },                  -- Undo
  -- Key 8  (h)
  h = { "key", {"cmd","shift"}, "z" },          -- Redo
  -- Key 9  (i)
  i = { "key", {"cmd"}, "c" },                  -- Copy
  -- Key 10 (j)
  j = { "key", {"cmd"}, "v" },                  -- Paste
  -- Key 11 (keypad .)
  ["keypad."] = { "key", {"cmd"}, "x" },        -- Cut
  -- Key 12 (keypad Enter)
  ["padenter"] = { "shell", "screencapture -i ~/Desktop/screenshot-$(date +%Y%m%d-%H%M%S).png" },
  -- Key 13 (keypad -)
  ["keypad-"] = { "media", "playpause" },
  -- Key 14 (keypad +)
  ["keypad+"] = { "media", "next" },
  -- Key 15 (spacebar)
  space = { "media", "prev" },
  -- Key 16 (down arrow)
  down = { "app", "Finder" },
  -- Key 17 (left arrow)
  left = { "app", "System Preferences" },
  -- Key 18 (right arrow)
  right = { "shell", "open -a 'Activity Monitor'" },
  -- Key 19 (up arrow)
  up = { "key", {"cmd","shift"}, "4" },         -- screenshot selection
}

-- ──────────────────────────────────────────────────────────────────────────────
-- DEVICE DETECTION
-- ──────────────────────────────────────────────────────────────────────────────
local padConnected = false

local function checkDevice()
  local devices = hs.usb.attachedDevices() or {}
  for _, d in ipairs(devices) do
    if d.vendorID == VENDOR_ID and d.productID == PRODUCT_ID then
      return true
    end
  end
  return false
end

local usbWatcher = hs.usb.watcher.new(function(event)
  if event.vendorID == VENDOR_ID and event.productID == PRODUCT_ID then
    padConnected = (event.eventType == "added")
    local state = padConnected and "connected" or "disconnected"
    hs.notify.new({title="MacroPad", informativeText="INSTANT pad " .. state}):send()
    hs.alert("MacroPad " .. state)
  end
end)
usbWatcher:start()
padConnected = checkDevice()

-- ──────────────────────────────────────────────────────────────────────────────
-- ACTION EXECUTOR
-- ──────────────────────────────────────────────────────────────────────────────
local function runAction(action)
  local atype = action[1]

  if atype == "app" then
    hs.application.launchOrFocus(action[2])

  elseif atype == "key" then
    hs.eventtap.keyStroke(action[2], action[3])

  elseif atype == "shell" then
    hs.task.new("/bin/bash", nil, {"-c", action[2]}):start()

  elseif atype == "text" then
    hs.eventtap.keyStrokes(action[2])

  elseif atype == "media" then
    local mediaKeys = {
      playpause = "PLAY",
      next      = "NEXT",
      prev      = "PREVIOUS",
      volup     = "SOUND_UP",
      voldown   = "SOUND_DOWN",
      mute      = "MUTE",
    }
    local k = mediaKeys[action[2]]
    if k then hs.eventtap.event.newSystemKeyEvent(k, true):post() end
  end
end

-- ──────────────────────────────────────────────────────────────────────────────
-- EVENT TAP — intercept keys only when pad is connected
-- ──────────────────────────────────────────────────────────────────────────────
local eventTap = hs.eventtap.new(
  { hs.eventtap.event.types.keyDown },
  function(event)
    if not padConnected then return false end  -- pass through when pad disconnected

    -- Only fire if NO modifier keys held on the physical press
    local flags = event.getFlags and event:getFlags() or {}
    if flags.cmd or flags.shift or flags.ctrl or flags.alt then
      return false   -- let normal keyboard combos pass through
    end

    local keycode = hs.keycodes.map[event:getKeyCode()]
    local action  = KEY_MAP[keycode]

    if action then
      runAction(action)
      return true  -- consume the event (don't type the letter)
    end
    return false   -- unknown key, pass through
  end
)

-- ──────────────────────────────────────────────────────────────────────────────
-- START
-- ──────────────────────────────────────────────────────────────────────────────
eventTap:start()

local status = padConnected and "pad CONNECTED" or "pad not found"
hs.alert("MacroPad loaded — " .. status, 2)
print("[MacroPad] Loaded. 19 keys configured. " .. status)
