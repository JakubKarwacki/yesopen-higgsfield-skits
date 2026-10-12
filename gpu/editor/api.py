#!/usr/bin/env python3
"""The skit editor as a small service for the YesOpen nodes in ComfyUI (gpu/server/yesopen_pipeline): it runs one script
of the skill in this container, so the edit renders with the same ffmpeg, Python and Whisper as the editor on the Mac.

  POST /run       {"project": "<folder in /work>", "script": "assemble.py", "args": [".", "--format", "9:16"],
                   "timeout": 3600}  ->  {"code": 0, "output": "<stdout and stderr, the last 20000 characters>"}
                  The project folder is the working directory (no project: /work itself, for new_project.py).
  GET  /projects  the project folders in /work
  GET  /health    {"ok": true}

compose.yaml starts it as the editor-api service, reachable from ComfyUI on the compose network only (no published
port). Only scripts in /skill/scripts run, only in folders inside /work.
"""
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WORK = Path(os.environ.get("WORK", "/work"))
SKILL = Path(os.environ.get("SKILL", "/skill"))
PORT = int(os.environ.get("PORT", "8190"))


class Handler(BaseHTTPRequestHandler):
    def send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            return self.send(200, {"ok": True})
        if self.path == "/projects":
            return self.send(200, sorted(p.name for p in WORK.iterdir() if p.is_dir() and not p.name.startswith(".")))
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/run":
            return self.send(404, {"error": "not found"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self.send(400, {"error": "the body is not JSON"})
        script = SKILL / "scripts" / Path(str(req.get("script", ""))).name
        if not script.is_file():
            return self.send(400, {"error": f"no script {script.name} in {SKILL / 'scripts'}"})
        cwd = WORK / Path(str(req["project"])).name if req.get("project") else WORK
        if not cwd.is_dir():
            return self.send(400, {"error": f"no project {cwd.name} in {WORK}"})
        args = [str(a) for a in req.get("args", [])]
        try:
            done = subprocess.run([sys.executable, str(script), *args], cwd=cwd, capture_output=True, text=True,
                                  timeout=float(req.get("timeout", 3600)))
        except subprocess.TimeoutExpired:
            return self.send(200, {"code": -1, "output": f"{script.name}: timed out"})
        self.send(200, {"code": done.returncode, "output": (done.stdout + done.stderr)[-20000:]})

    def log_message(self, fmt, *args):
        sys.stderr.write("[editor-api] " + fmt % args + "\n")


if __name__ == "__main__":
    print(f"[editor-api] scripts from {SKILL / 'scripts'}, projects in {WORK}, port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
