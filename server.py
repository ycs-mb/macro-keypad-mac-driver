#!/usr/bin/env python3
"""
server.py — Local HTTP backend server for the INSTANT Macro Pad Configurator.

Hosts the configurator at http://localhost:8080 and provides a secure,
one-click '/api/apply' endpoint to automatically save the JSON configuration
and execute the Karabiner reload shell script directly from the UI.
"""

import http.server
import socketserver
import subprocess
import json
import sys
from pathlib import Path

PORT = 8080
DIRECTORY = Path(__file__).resolve().parent

class MacroPadHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve from the directory where server.py is located
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def do_POST(self):
        if self.path == '/api/apply':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # Parse config from UI
                config_data = json.loads(post_data.decode('utf-8'))
                
                # 1. Build and save the karabiner_profile.json
                profile_path = DIRECTORY / "karabiner_profile.json"
                
                # Compile manipulators (mirrors buildProfile logic from index.html)
                manipulators = []
                for k in config_data:
                    if k.get("action") and k.get("fromKey") and k.get("fromKey") != "?":
                        from_type = k.get("fromKeyType", "key_code")
                        action = k["action"]
                        atype = action.get("type")
                        
                        to = []
                        if atype == "shell":
                            to = [{"shell_command": action["command"]}]
                        elif atype == "key":
                            obj = {"key_code": action["keyCode"]}
                            if action.get("modifiers"):
                                obj["modifiers"] = action["modifiers"]
                            to = [obj]
                        elif atype == "media":
                            media_code = action["mediaCode"]
                            # mission_control/launchpad use key_code; actual media controls use consumer_key_code
                            key_code_media = {"mission_control", "launchpad", "dashboard"}
                            field = "key_code" if media_code in key_code_media else "consumer_key_code"
                            to = [{field: media_code}]
                        elif atype == "app":
                            to = [{"shell_command": f"open -a '{action['appName']}'"}]
                            
                        manipulators.append({
                            "type": "basic",
                            "description": f"Key {k['id']} ({k.get('label', '')})",
                            "from": {from_type: k["fromKey"]},
                            "to": to,
                            "conditions": [
                                {
                                    "type": "device_if",
                                    "identifiers": [
                                        {"vendor_id": 12538, "product_id": 9040}
                                    ]
                                }
                            ]
                        })
                
                profile = {
                    "description": "INSTANT 19-Key Macro Pad",
                    "_note": "Generated dynamically by Local server.py",
                    "manipulators": manipulators
                }
                
                # Write karabiner_profile.json
                with open(profile_path, "w") as f:
                    json.dump(profile, f, indent=4)
                
                # 2. Run install_profile.sh
                installer_path = DIRECTORY / "install_profile.sh"
                result = subprocess.run(
                    ["bash", str(installer_path)],
                    capture_output=True, text=True, check=True
                )
                
                # Success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "success",
                    "message": "Configuration successfully saved and applied to Karabiner!",
                    "output": result.stdout
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except subprocess.CalledProcessError as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "error",
                    "message": f"Karabiner installer failed: {e.stderr or e.stdout}"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "error",
                    "message": f"Bad Request: {str(e)}"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run():
    # Enable address socket re-use to prevent "Address already in use" errors on restarts
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), MacroPadHTTPRequestHandler) as httpd:
        print(f"\n╔══════════════════════════════════════════════════════════╗")
        print(f"║  🚀 INSTANT Macro Pad Configurator Backend Serving       ║")
        print(f"╚══════════════════════════════════════════════════════════╝")
        print(f"\n  Configurator UI:  http://localhost:{PORT}")
        print(f"  Key Tester UI:    http://localhost:{PORT}/test.html")
        print(f"\n  Double-click either link to open on your Mac.")
        print("  Press Ctrl+C to shut down.")
        print()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == '__main__':
    run()
