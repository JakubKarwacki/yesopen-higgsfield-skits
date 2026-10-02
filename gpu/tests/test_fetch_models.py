"""Tests for server/fetch_models.py against two local HTTP servers: one plays huggingface.co (checks the token,
redirects), the other plays the storage the download is redirected to (serves bytes, supports ranges)."""
import hashlib
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
import fetch_models  # noqa: E402

PAYLOAD = bytes(range(256)) * 4096  # 1 MiB
TOKEN = "hf_test_token"


class Recorder:
    def __init__(self):
        self.requests = []


def make_handler(recorder, routes):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            recorder.requests.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                      "range": self.headers.get("Range")})
            routes(self)

    return Handler


def serve(handler):
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.storage_log, self.hub_log = Recorder(), Recorder()

        def storage_routes(handler):
            data = PAYLOAD
            start = 0
            if handler.headers.get("Range"):
                start = int(handler.headers["Range"].split("=")[1].rstrip("-"))
                handler.send_response(206)
                handler.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
            else:
                handler.send_response(200)
            handler.send_header("Content-Length", str(len(data) - start))
            handler.end_headers()
            handler.wfile.write(data[start:])

        self.storage = serve(make_handler(self.storage_log, storage_routes))
        storage_url = f"http://localhost:{self.storage.server_address[1]}/blob"

        def hub_routes(handler):
            if "gated" in handler.path and handler.headers.get("Authorization") != f"Bearer {TOKEN}":
                handler.send_response(401)
                handler.end_headers()
                return
            handler.send_response(302)
            handler.send_header("Location", storage_url)
            handler.end_headers()

        self.hub = serve(make_handler(self.hub_log, hub_routes))
        self.hub_url = f"http://127.0.0.1:{self.hub.server_address[1]}"
        self._hosts = fetch_models.TOKEN_HOSTS
        fetch_models.TOKEN_HOSTS = ("127.0.0.1",)  # the hub plays huggingface.co; "localhost" is the storage
        self.tmp = tempfile.TemporaryDirectory()
        self.models = Path(self.tmp.name)

    def tearDown(self):
        fetch_models.TOKEN_HOSTS = self._hosts
        self.hub.shutdown()
        self.storage.shutdown()
        self.tmp.cleanup()

    def entry(self, name="model.safetensors", gated=False, sha=hashlib.sha256(PAYLOAD).hexdigest()):
        return {"name": name, "directory": "diffusion_models", "size": len(PAYLOAD), "sha256": sha,
                "url": f"{self.hub_url}/org/{'gated' if gated else 'open'}/resolve/abc/{name}",
                "gated": gated, "stage": "before_start", "variant": "A", "templates": ["talk"]}

    def fetch(self, entry, token=TOKEN):
        with redirect_stdout(io.StringIO()):
            return fetch_models.fetch_one(entry, self.models, token, timeout=10, retries=2, verify=False)

    def test_token_goes_to_the_hub_only(self):
        result = self.fetch(self.entry(gated=True))
        self.assertIn("SHA-256 ok", result)
        self.assertEqual((self.models / "diffusion_models" / "model.safetensors").read_bytes(), PAYLOAD)
        self.assertEqual(self.hub_log.requests[0]["auth"], f"Bearer {TOKEN}")
        self.assertTrue(self.storage_log.requests)
        self.assertTrue(all(r["auth"] is None for r in self.storage_log.requests))

    def test_resume_from_partial_file(self):
        target = self.models / "diffusion_models" / "model.safetensors"
        target.parent.mkdir(parents=True)
        Path(str(target) + ".part").write_bytes(PAYLOAD[:300_000])
        self.fetch(self.entry())
        self.assertEqual(target.read_bytes(), PAYLOAD)
        self.assertEqual(self.storage_log.requests[-1]["range"], "bytes=300000-")

    def test_hash_mismatch_removes_the_file(self):
        with self.assertRaises(RuntimeError) as error:
            self.fetch(self.entry(sha="0" * 64))
        self.assertIn("mismatch", str(error.exception))
        self.assertFalse((self.models / "diffusion_models" / "model.safetensors").exists())

    def test_gated_without_token_fails_fast(self):
        with self.assertRaises(RuntimeError) as error:
            self.fetch(self.entry(gated=True), token=None)
        self.assertIn("HF_TOKEN", str(error.exception))
        self.assertEqual(self.hub_log.requests, [])  # refused before any request

    def test_wrong_token_reports_gating(self):
        with self.assertRaises(RuntimeError) as error:
            self.fetch(self.entry(gated=True), token="hf_wrong")
        self.assertIn("access denied", str(error.exception))
        self.assertEqual(len(self.hub_log.requests), 1)  # no pointless retries

    def test_present_file_is_not_downloaded_again(self):
        target = self.models / "diffusion_models" / "model.safetensors"
        target.parent.mkdir(parents=True)
        target.write_bytes(PAYLOAD)
        self.assertEqual(self.fetch(self.entry()), "present")
        self.assertEqual(self.hub_log.requests + self.storage_log.requests, [])

    def test_two_runs_fetch_a_file_once(self):
        results = []

        def run():
            results.append(self.fetch(self.entry()))

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(r == "present" for r in results), [False, True])
        self.assertEqual(len(self.storage_log.requests), 1)
        self.assertEqual((self.models / "diffusion_models" / "model.safetensors").read_bytes(), PAYLOAD)

    def test_stage_and_variant_selection(self):
        manifest = json.loads((ROOT / "server" / "manifest.json").read_text())
        before = fetch_models.select(manifest, "before_start", None, False)
        self.assertTrue(before and all(e["stage"] == "before_start" for e in before))
        everything = fetch_models.select(manifest, "all", None, False)
        self.assertFalse(any(e["variant"] == "B" for e in everything))
        two_shot = fetch_models.select(manifest, "all", ["two-shot"], False)
        self.assertEqual({e["directory"] for e in two_shot} >= {"model_patches", "audio_encoders"}, True)
        with_b = fetch_models.select(manifest, "manual", None, True)
        self.assertTrue(any(e["variant"] == "B" for e in with_b))


if __name__ == "__main__":
    unittest.main()
