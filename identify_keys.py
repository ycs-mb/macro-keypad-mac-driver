#!/usr/bin/env python3
"""
Identify keycodes sent by the INSTANT 19-key macro pad.
Run this, then press each key on the macro pad to see what code it sends.

Usage: uv run identify_keys.py
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["hid"]
# ///

import hid
import time

VENDOR_ID  = 0x30FA
PRODUCT_ID = 0x2350

HID_KEY_NAMES = {
    0x00: "none", 0x04: "a", 0x05: "b", 0x06: "c", 0x07: "d",
    0x08: "e", 0x09: "f", 0x0A: "g", 0x0B: "h", 0x0C: "i",
    0x0D: "j", 0x0E: "k", 0x0F: "l", 0x10: "m", 0x11: "n",
    0x12: "o", 0x13: "p", 0x14: "q", 0x15: "r", 0x16: "s",
    0x17: "t", 0x18: "u", 0x19: "v", 0x1A: "w", 0x1B: "x",
    0x1C: "y", 0x1D: "z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4", 0x22: "5",
    0x23: "6", 0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "return", 0x29: "escape", 0x2A: "backspace", 0x2B: "tab",
    0x2C: "spacebar", 0x2D: "hyphen", 0x2E: "equal",
    0x3A: "F1", 0x3B: "F2", 0x3C: "F3", 0x3D: "F4", 0x3E: "F5",
    0x3F: "F6", 0x40: "F7", 0x41: "F8", 0x42: "F9", 0x43: "F10",
    0x44: "F11", 0x45: "F12", 0x46: "F13", 0x47: "F14", 0x48: "F15",
    0x49: "F16", 0x4A: "F17", 0x4B: "F18", 0x4C: "F19", 0x4D: "F20",
    0x4E: "F21", 0x4F: "F22", 0x50: "F23", 0x51: "F24",
    0x53: "keypad_num_lock", 0x54: "keypad_slash", 0x55: "keypad_asterisk",
    0x56: "keypad_hyphen", 0x57: "keypad_plus", 0x58: "keypad_enter",
    0x59: "keypad_1", 0x5A: "keypad_2", 0x5B: "keypad_3",
    0x5C: "keypad_4", 0x5D: "keypad_5", 0x5E: "keypad_6",
    0x5F: "keypad_7", 0x60: "keypad_8", 0x61: "keypad_9",
    0x62: "keypad_0", 0x63: "keypad_period",
}

MOD_NAMES = {
    0x01: "left_control", 0x02: "left_shift", 0x04: "left_option",
    0x08: "left_command", 0x10: "right_control", 0x20: "right_shift",
    0x40: "right_option", 0x80: "right_command",
}

def decode_report(data: bytes) -> str:
    if len(data) < 8:
        return f"short report: {data.hex()}"
    modifiers = data[1]
    keys = [data[i] for i in range(3, 8) if data[i] != 0]
    mod_parts = [name for bit, name in MOD_NAMES.items() if modifiers & bit]
    key_parts  = [HID_KEY_NAMES.get(k, f"0x{k:02X}") for k in keys]
    all_parts = mod_parts + key_parts
    return " + ".join(all_parts) if all_parts else "(released)"


def find_keyboard_interface() -> hid.Device | None:
    """Try interfaces in preference order: keyboard HID, then any that opens."""
    # Prefer Interface 0 usage_page=0x01 usage=0x06 (boot keyboard)
    candidates = sorted(
        hid.enumerate(VENDOR_ID, PRODUCT_ID),
        key=lambda d: (0 if (d["usage_page"] == 0x01 and d["usage"] == 0x06) else 1)
    )
    for info in candidates:
        try:
            dev = hid.Device(path=info["path"])
            return dev
        except Exception as e:
            print(f"  skip {info['path']}: {e}")
    return None


def main() -> None:
    devices = hid.enumerate(VENDOR_ID, PRODUCT_ID)
    if not devices:
        print(f"Device not found (VID=0x{VENDOR_ID:04X} PID=0x{PRODUCT_ID:04X})")
        print("Make sure the keypad is plugged in.")
        return

    print(f"Found {len(devices)} interface(s) for INSTANT macro pad:")
    for d in devices:
        print(f"  Interface {d['interface_number']}: usage_page=0x{d['usage_page']:04X} usage=0x{d['usage']:04X} path={d['path']}")

    dev = find_keyboard_interface()
    if not dev:
        print("Could not open device — try running with sudo if needed.")
        return

    dev.set_nonblocking(False)
    print("\nPress keys on the macro pad (Ctrl-C to quit):\n")

    prev: list[int] = []
    try:
        while True:
            data = dev.read(64, timeout_ms=100)
            if data and data != prev:
                label = decode_report(bytes(data))
                if label:
                    print(f"  raw={bytes(data[:8]).hex()}  ->  {label}")
                prev = data
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        dev.close()


if __name__ == "__main__":
    main()
