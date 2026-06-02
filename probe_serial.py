#!/usr/bin/env python3
"""
Probe the INSTANT macro pad's CH340 serial config interface.
Tries both ports, multiple baud rates, and common protocol patterns.

Usage: uv run probe_serial.py
"""
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyserial"]
# ///

import serial
import serial.tools.list_ports
import time
import sys

PORTS = ["/dev/cu.usbmodem12301", "/dev/cu.usbmodemSN234567892"]
BAUDS = [9600, 115200, 57600, 38400, 19200]

# Common probe payloads used by cheap macro pad firmware
PROBES = [
    b"\x00",                          # null
    b"\x02",                          # STX
    b"\xAA",                          # common sync byte
    b"\xAA\x55",                      # sync pair
    b"\xAA\x55\x00",
    b"\x00\x00\x00\x00\x00\x00\x00\x00",  # 8-byte null
    b"\x01\x00\x00\x00\x00\x00\x00\x00",  # cmd 0x01
    b"\x02\x00\x00\x00\x00\x00\x00\x00",  # cmd 0x02
    b"\xFE",
    b"\xFF",
    b"\xA5\x5A",
    b"HELLO\r\n",                     # ASCII probe
    b"VER\r\n",
    b"?\r\n",
]

def probe_port(port: str, baud: int) -> bool:
    """Returns True if device responded to anything."""
    try:
        ser = serial.Serial(port, baud, timeout=0.3,
                            bytesize=8, parity='N', stopbits=1)
    except serial.SerialException as e:
        print(f"  cannot open {port}@{baud}: {e}")
        return False

    responded = False
    for payload in PROBES:
        try:
            ser.reset_input_buffer()
            ser.write(payload)
            time.sleep(0.15)
            resp = ser.read(64)
            if resp:
                print(f"\n  *** RESPONSE at {port} baud={baud} ***")
                print(f"      sent : {payload.hex()} ({payload!r})")
                print(f"      got  : {resp.hex()}")
                print(f"      ascii: {resp!r}")
                responded = True
        except Exception as e:
            print(f"  write error: {e}")

    ser.close()
    return responded


def main():
    print("=== CH340 Serial Probe ===")
    print(f"Ports: {PORTS}")
    print(f"Bauds: {BAUDS}\n")

    any_response = False
    for port in PORTS:
        print(f"\n--- Port: {port} ---")
        for baud in BAUDS:
            print(f"  trying {baud} baud...", end=" ", flush=True)
            got = probe_port(port, baud)
            if got:
                any_response = True
            else:
                print("no response")

    if not any_response:
        print("\n\nNo response on any port/baud combination.")
        print("Trying passive listen (waiting for device to speak first)...")
        for port in PORTS:
            try:
                ser = serial.Serial(port, 9600, timeout=2.0)
                print(f"  listening on {port}@9600 for 2s...", end=" ", flush=True)
                data = ser.read(128)
                if data:
                    print(f"device sent: {data.hex()} / {data!r}")
                else:
                    print("silence")
                ser.close()
            except Exception as e:
                print(f"  error: {e}")


if __name__ == "__main__":
    main()
