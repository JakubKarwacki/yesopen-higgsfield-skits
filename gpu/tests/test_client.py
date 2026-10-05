"""Tests for client/gpu.py.

Unit tests need nothing. The end-to-end tests talk to a real ComfyUI (GPU_TEST_COMFY_URL, default
http://127.0.0.1:8188, e.g. a local CPU install of the same version) with small core-node workflows from
tests/fixtures, so they exercise upload, queue, wait, download and jobs.jsonl without any model.

  python3 -m unittest discover -s tests -v
"""
import json
import random
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "client"))
import gpu  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
COMFY_URL = __import__("os").environ.get("GPU_TEST_COMFY_URL", "http://127.0.0.1:8188")


def comfy_available() -> bool:
    try:
        with urllib.request.urlopen(COMFY_URL + "/system_stats", timeout=3):
            return True
    except OSError:
        return False


def probe(path: Path, entries: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


class UseFixtures:
    """Point the client at tests/fixtures instead of the real templates."""

    def setUp(self):
        self._dirs = gpu.API_DIR, gpu.PARAMS_DIR
        gpu.API_DIR, gpu.PARAMS_DIR = FIXTURES / "api", FIXTURES / "params"

    def tearDown(self):
        gpu.API_DIR, gpu.PARAMS_DIR = self._dirs


class TemplateTests(unittest.TestCase):
    def test_every_param_map_points_at_literal_inputs(self):
        for params in sorted(gpu.PARAMS_DIR.glob("*.json")):
            prompt, spec = gpu.load_template(params.stem)
            for name, param in spec["params"].items():
                for node, field in param["targets"]:
                    self.assertIn(node, prompt, f"{params.stem}.{name}")
                    self.assertIn(field, prompt[node]["inputs"], f"{params.stem}.{name}")
                    self.assertNotIsInstance(prompt[node]["inputs"][field], list, f"{params.stem}.{name} is a link")
            for label, node in spec["outputs"].items():
                self.assertIn(node, prompt, f"{params.stem} output {label}")

    def test_required_and_unknown_parameters_are_reported(self):
        _, spec = gpu.load_template("talk")
        with self.assertRaises(SystemExit) as missing:
            gpu.resolve_values(spec, {"prompt": "x"}, random.Random(1))
        self.assertIn("required", str(missing.exception))
        with self.assertRaises(SystemExit) as unknown:
            gpu.resolve_values(spec, {"promt": "x"}, random.Random(1))
        self.assertIn("unknown parameter", str(unknown.exception))

    def test_defaults_and_random_seed(self):
        _, spec = gpu.load_template("talk")
        given = {"image": "a.png", "audio": "a.wav", "prompt": "p", "seconds": "3.2"}
        values = gpu.resolve_values(spec, given, random.Random(7))
        self.assertEqual((values["width"], values["height"], values["fps"]), (704, 1280, 24))
        self.assertIs(values["enhance_prompt"], False)
        self.assertEqual(values["seconds"], 3.2)
        self.assertEqual(values["seed"], random.Random(7).randint(0, gpu.SEED_MAX))
        self.assertEqual(gpu.resolve_values(spec, {**given, "seed": "5"}, random.Random(7))["seed"], 5)

    def test_ltx_float_seconds_round_up_to_eight_frame_groups(self):
        _, spec = gpu.load_template("talk")
        values = {"seconds": 3.2, "fps": 24}
        info = gpu.ltx_frames(spec, values)
        # 3.2 s * 24 = 76.8 frames -> 80 frames (10 groups of 8) -> 3.3333 s; the graph adds 1 -> 81 = 8n+1
        self.assertEqual(info["frames"], 81)
        self.assertAlmostEqual(info["seconds"], 80 / 24)
        self.assertEqual(int(values["seconds"] * 24 + 1), 81)  # what the graph's math node computes
        self.assertEqual(info["pad_audio"], ["audio"])

    def test_ltx_exact_lengths_survive_float_truncation(self):
        _, spec = gpu.load_template("talk")
        for frames in range(8, 24 * 20, 8):
            values = {"seconds": frames / 24, "fps": 24}
            gpu.ltx_frames(spec, values)
            self.assertEqual(int(values["seconds"] * 24 + 1), frames + 1, frames)

    def test_ltx_integer_seconds(self):
        _, spec = gpu.load_template("action")
        values = {"seconds": 5, "fps": 24}
        self.assertEqual(gpu.ltx_frames(spec, values)["frames"], 121)
        self.assertEqual(values["seconds"], 5)
        with self.assertRaises(SystemExit):
            gpu.ltx_frames(spec, {"seconds": 5, "fps": 25})

    def test_h3_seconds_round_up_to_the_17k_plus_5_grid(self):
        _, spec = gpu.load_template("h3-talk")
        values = {"seconds": 5.17}
        info = gpu.frame_grid(spec, values)
        # 5.17 s * 24 = 124.08 frames -> 125 -> next 17k+5 = 141 frames
        self.assertEqual((info["frames"], info["pad_audio"]), (141, ["audio"]))
        self.assertAlmostEqual(values["seconds"], 141 / 24)
        for seconds in (0.1, 3.2, 5.1, 124 / 24, 9.99, 15.0):
            values = {"seconds": seconds}
            frames = gpu.frame_grid(spec, values)["frames"]
            self.assertEqual(frames % 17, 5, seconds)
            self.assertGreaterEqual(frames / 24, min(seconds, frames / 24), seconds)
            self.assertLess(frames / 24 - seconds, 17 / 24, seconds)
            # what the graph's math node computes from the seconds we send
            a = values["seconds"]
            graph = max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17
            self.assertEqual(graph, frames, seconds)

    def test_h3_talk_pads_the_line_to_the_whole_take(self):
        with tempfile.TemporaryDirectory() as tmp:
            line, still = Path(tmp) / "line.wav", Path(tmp) / "still.png"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2.4",
                            "-ar", "24000", str(line)], check=True)
            still.write_bytes(gpu.png_rgba(9, 16, lambda x, y: 255))
            job = gpu.prepare_job("h3-talk", {"image": str(still), "audio": str(line), "prompt": "x",
                                              "seconds": "5.17", "seed": "1"}, random.Random(1), Path(tmp))
            padded = job["files"]["audio"]
            duration = float(probe(padded, "format=duration")["format"]["duration"])
            self.assertAlmostEqual(duration, 141 / 24, delta=0.002)
            self.assertEqual(job["prompt"]["115"]["inputs"]["megapixels"], 0.98)
            self.assertEqual(job["prompt"]["105:16"]["inputs"]["conditioning"], ["902", 0])
            self.assertEqual(job["prompt"]["105:13"]["inputs"]["clip_name"],
                             "qwen3vl_32b_minimax_h3_int8_convrot.safetensors")

    def test_coerce(self):
        self.assertIs(gpu.coerce("bool", "yes"), True)
        self.assertIs(gpu.coerce("bool", "off"), False)
        self.assertEqual(gpu.coerce("float", "1.5"), 1.5)
        with self.assertRaises(ValueError):
            gpu.coerce("bool", "maybe")

    def test_parse_sets_keeps_equals_in_values(self):
        self.assertEqual(gpu.parse_sets(["prompt=a=b", "seconds=2"]), {"prompt": "a=b", "seconds": "2"})

    def test_describe_rejection(self):
        body = json.dumps({"error": {"message": "Prompt outputs failed validation", "details": ""},
                           "node_errors": {"9": {"class_type": "SaveImage",
                                                 "errors": [{"message": "Required input is missing", "details": "images"}]}}})
        text = gpu.describe_rejection(body)
        self.assertIn("node 9 (SaveImage): Required input is missing images", text)

    def test_mask_png_is_a_valid_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = gpu.mask_file("right", Path(tmp))
            info = probe(path, "stream=width,height,pix_fmt")["streams"][0]
            self.assertEqual((info["width"], info["height"], info["pix_fmt"]), (64, 64, "rgba"))


class ToolTests(unittest.TestCase):
    def test_ui_bypass_rewires_consumers(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import convert_templates
        template = {"nodes": [{"id": 1, "outputs": [{"links": [10]}]}, {"id": 2, "outputs": [{"links": [11]}]},
                              {"id": 3, "outputs": []}],
                    "links": [[10, 1, 0, 2, 0, "AUDIO"], [11, 2, 0, 3, 0, "AUDIO"]]}
        patched = convert_templates.apply_ui_patch(template, [{"op": "bypass_ui_node", "node": 2}])
        self.assertEqual([n["id"] for n in patched["nodes"]], [1, 3])
        self.assertEqual(patched["links"], [[11, 1, 0, 3, 0, "AUDIO"]])
        self.assertEqual(patched["nodes"][0]["outputs"][0]["links"], [11])

    def test_api_patches(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import convert_templates
        prompt = {"3": {"class_type": "SaveAudioMP3", "inputs": {"quality": "V0", "audio": ["1", 0]}, "_meta": {"title": "x"}}}
        patched = convert_templates.apply_patch(prompt, [
            {"op": "edit_node", "node": "3", "class_type": "SaveAudio", "title": "Save (FLAC)", "drop_inputs": ["quality"]},
            {"op": "add_node", "node": "9", "class_type": "SaveAudio", "inputs": {"audio": ["1", 1]}}])
        self.assertEqual(patched["3"], {"class_type": "SaveAudio", "inputs": {"audio": ["1", 0]},
                                        "_meta": {"title": "Save (FLAC)"}})
        self.assertEqual(patched["9"]["inputs"], {"audio": ["1", 1]})
        self.assertEqual(prompt["3"]["class_type"], "SaveAudioMP3")  # the input is not modified

    def test_converted_workflows_match_patches(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import convert_templates
        patches = json.loads(convert_templates.PATCHES.read_text())
        for raw in sorted(convert_templates.RAW_DIR.glob("*.json")):
            expected = convert_templates.apply_patch(json.loads(raw.read_text()),
                                                     patches.get(raw.stem, {}).get("steps", []))
            actual = json.loads((convert_templates.API_DIR / raw.name).read_text())
            self.assertEqual(actual, expected, raw.stem)

    def test_an_override_with_another_file_name_swaps_the_file(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import build_manifest
        declared = {"directory": "text_encoders", "name": "te_nvfp4.safetensors",
                    "url": "https://huggingface.co/a/b/resolve/main/text_encoders/te_nvfp4.safetensors"}
        new_url = "https://huggingface.co/a/b/resolve/main/text_encoders/te_int8.safetensors"
        swapped = build_manifest.override(declared, {declared["url"]: new_url})
        self.assertEqual((swapped["name"], swapped["url"], swapped["replaces_url"]),
                         ("te_int8.safetensors", new_url, declared["url"]))
        self.assertIs(build_manifest.override(declared, {}), declared)

    def test_h3_workflows_use_files_the_manifest_lists(self):
        manifest = json.loads(gpu.MANIFEST.read_text())
        for template in ("h3-i2v", "h3-r2v", "h3-talk"):
            listed = {f["name"] for f in manifest["files"] if template in f["templates"]}
            prompt, _ = gpu.load_template(template)
            used = {v for node in prompt.values() for v in node["inputs"].values()
                    if isinstance(v, str) and v.endswith(".safetensors")}
            self.assertEqual(used, listed, template)
            self.assertTrue(all(f["variant"] == "B" and f["stage"] == "manual"
                                for f in manifest["files"] if template in f["templates"]), template)


class MachineFixture:
    """A stand-in for the Verda CLI and a state file in a temporary folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._saved = gpu.STATE, gpu.KNOWN_HOSTS, gpu.CONFIG, gpu.verda, gpu.verda_check
        gpu.verda_check = lambda config: ("ready", [])  # the CLI is set up; VerdaCheckTests cover the rest
        gpu.STATE, gpu.KNOWN_HOSTS = Path(self.tmp.name) / "state.json", Path(self.tmp.name) / "known_hosts"
        gpu.CONFIG = Path(self.tmp.name) / "config.json"  # never the user's own settings
        self.calls, self.machines = [], []
        self.create_status, self.create_error = "running", None

        def fake_verda(args, capture=True):
            self.calls.append(args)
            if args[:2] == ["vm", "list"]:
                return self.machines
            if args[:2] == ["vm", "create"]:
                if self.create_error:
                    raise SystemExit(self.create_error)
                running = self.create_status == "running"
                self.machines.append({"id": "vm-1", "hostname": "yesopen-gpu", "status": self.create_status,
                                      "ip": "192.0.2.7" if running else None, "os_volume_id": "vol-9",
                                      "jupyter_token": "secret-token"})
            if args[:2] == ["vm", "action"]:
                self.machines.clear()
            return ""

        gpu.verda = fake_verda
        self.config = json.loads(gpu.EXAMPLE_CONFIG.read_text())
        self.config["verda"].update({"instance_type": "1B200.30V", "ssh_key_id": "key-1"})

    def tearDown(self):
        gpu.STATE, gpu.KNOWN_HOSTS, gpu.CONFIG, gpu.verda, gpu.verda_check = self._saved
        self.tmp.cleanup()

    def run_command(self, func, **flags):
        out = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(out):
            self.code = func(__import__("argparse").Namespace(**{"first": False, "yes": False, **flags}), self.config)
        return out.getvalue()

    def created(self):
        return [c for c in self.calls if c[:2] == ["vm", "create"]]


class MachineTests(MachineFixture, unittest.TestCase):
    """up / down / use / tunnel: nothing is created or deleted without --yes."""

    def test_up_without_yes_only_prints_the_command(self):
        out = self.run_command(gpu.cmd_up)
        self.assertEqual(self.created(), [])
        self.assertIn("--os ubuntu-24.04-cuda-13.0-open-docker --os-volume-size 300", out)

    def test_up_boots_the_kept_disk_and_hides_secrets(self):
        gpu.save_state({"os_volume_id": "vol-9"})
        out = self.run_command(gpu.cmd_up, yes=True)
        command = self.created()[0]
        self.assertEqual(command[command.index("--os") + 1], "vol-9")
        self.assertNotIn("--os-volume-size", command)
        self.assertEqual(gpu.load_state()["ip"], "192.0.2.7")
        self.assertNotIn("secret-token", out)

    def test_up_gives_every_team_key_to_the_machine(self):
        self.config["verda"]["ssh_key_id"] = ["key-1", "key-2"]
        self.run_command(gpu.cmd_up, yes=True)
        command = self.created()[0]
        self.assertEqual([command[i + 1] for i, flag in enumerate(command) if flag == "--ssh-key"], ["key-1", "key-2"])

    def test_up_first_uses_a_fresh_image(self):
        gpu.save_state({"os_volume_id": "vol-9"})
        self.run_command(gpu.cmd_up, first=True, yes=True)
        command = self.created()[0]
        self.assertEqual(command[command.index("--os") + 1], "ubuntu-24.04-cuda-13.0-open-docker")

    def test_up_forgets_the_old_host_key_of_the_address(self):
        gpu.KNOWN_HOSTS.write_text("192.0.2.7 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOldKeyOldKeyOldKeyOldKeyOldKeyOldKeyOldKe\n"
                                   "198.51.100.1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOtherKeyOtherKeyOtherKeyOtherKeyOtherKey1\n")
        self.run_command(gpu.cmd_up, yes=True)
        remaining = gpu.KNOWN_HOSTS.read_text()
        self.assertNotIn("192.0.2.7", remaining)
        self.assertIn("198.51.100.1", remaining)

    def test_a_deleted_machine_does_not_block_up(self):
        self.machines.append({"id": "vm-0", "hostname": "yesopen-gpu", "status": "discontinued", "ip": None,
                              "os_volume_id": "vol-9"})
        self.run_command(gpu.cmd_up, yes=True)
        self.assertEqual(len(self.created()), 1)
        self.assertEqual(gpu.load_state()["instance_id"], "vm-1")

    def test_up_reports_an_order_without_capacity(self):
        self.create_status = "no_capacity"
        out = self.run_command(gpu.cmd_up, yes=True)
        self.assertEqual(self.code, 1)
        self.assertIn("no_capacity, not running", out)
        self.assertIn("gpu.py down --yes", out)
        self.assertIn("verda availability --type 1B200.30V", out)
        with self.assertRaises(SystemExit) as again:
            self.run_command(gpu.cmd_up, yes=True)
        self.assertIn("already exists (no_capacity)", str(again.exception))

    def test_a_failed_order_points_at_status_and_down(self):
        self.create_error = "verda vm create --kind failed:\ntimed out waiting for the instance"
        with self.assertRaises(SystemExit) as failed:
            self.run_command(gpu.cmd_up, yes=True)
        self.assertIn("timed out", str(failed.exception))
        self.assertIn("gpu.py status and remove it with gpu.py down --yes", str(failed.exception))

    def test_down_keeps_the_disk(self):
        self.run_command(gpu.cmd_up, yes=True)
        self.run_command(gpu.cmd_down)
        self.assertFalse([c for c in self.calls if c[:2] == ["vm", "action"]])
        self.run_command(gpu.cmd_down, yes=True)
        delete = [c for c in self.calls if c[:2] == ["vm", "action"]][0]
        self.assertNotIn("--with-volumes", delete)
        self.assertEqual(gpu.load_state(), {"instance_id": None, "ip": None, "os_volume_id": "vol-9"})

    def test_use_records_and_forgets_a_hand_made_machine(self):
        gpu.STATE = Path(self.tmp.name) / "home" / "state.json"  # the settings folder may not exist yet
        gpu.KNOWN_HOSTS.write_text("203.0.113.5 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOldKeyOldKeyOldKeyOldKeyOldKeyOldKeyOldKe\n"
                                   "198.51.100.1 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOtherKeyOtherKeyOtherKeyOtherKeyOtherKey1\n")
        self.run_command(gpu.cmd_use, address="203.0.113.5", clear=False)
        self.assertEqual(gpu.load_state()["ip"], "203.0.113.5")
        self.assertNotIn("203.0.113.5", gpu.KNOWN_HOSTS.read_text())
        self.assertIn("198.51.100.1", gpu.KNOWN_HOSTS.read_text())
        self.run_command(gpu.cmd_use, address=None, clear=True)
        self.assertIsNone(gpu.load_state()["ip"])
        self.assertEqual(self.calls, [], "use never calls Verda")

    def test_use_says_when_a_fixed_host_still_wins(self):
        gpu.CONFIG.write_text(json.dumps({"host": "198.51.100.9"}))
        out = self.run_command(gpu.cmd_use, address="203.0.113.5", clear=False)
        self.assertIn("198.51.100.9", out)
        self.assertIn("still wins", out)

    def test_keychain_is_optional(self):
        saved_which, saved_run = gpu.shutil.which, gpu.subprocess.run
        gpu.shutil.which = lambda name: None  # Linux: no security command

        def no_run(*args, **kwargs):
            raise AssertionError("must not run the missing security command")

        gpu.subprocess.run = no_run
        try:
            self.assertIsNone(gpu.keychain_secret("huggingface", "token"))
        finally:
            gpu.shutil.which, gpu.subprocess.run = saved_which, saved_run

    def test_tunnel_close_does_not_hang_when_the_machine_is_gone(self):
        saved_socket, saved_run = gpu.TUNNEL_SOCKET, gpu.subprocess.run
        gpu.TUNNEL_SOCKET = Path(self.tmp.name) / "tunnel.sock"
        gpu.TUNNEL_SOCKET.write_text("")
        commands = []

        def fake_run(command, **kwargs):
            commands.append(command)
            if "-O" in command:
                raise gpu.subprocess.TimeoutExpired(command, kwargs.get("timeout"))
            return gpu.subprocess.CompletedProcess(command, 0)

        gpu.subprocess.run = fake_run
        try:
            out = self.run_command(gpu.cmd_tunnel, close=True, **{"yes": False})
        finally:
            gpu.TUNNEL_SOCKET, gpu.subprocess.run = saved_socket, saved_run
        self.assertIn("did not answer", out)
        self.assertEqual(commands[1][:3], ["pkill", "-f", "--"])
        self.assertFalse((Path(self.tmp.name) / "tunnel.sock").exists())


class SessionFixture(MachineFixture):
    """Fake SSH, stack stamp, bootstrap, tunnel and health around the Verda stand-in."""

    def setUp(self):
        super().setUp()
        self.events, self.server = [], {"stamp": None, "ssh": True, "comfy": True}
        names = ("verda_ready", "remote_text", "remote", "cmd_bootstrap", "cmd_tunnel", "cmd_health")
        self._session_saved = {name: getattr(gpu, name) for name in names}
        self._sleep = gpu.time.sleep
        gpu.time.sleep = lambda seconds: None
        gpu.verda_ready = lambda config: True

        def remote_text(config, command, timeout=60):
            self.events.append(("check", command.split()[0]))
            if not self.server["ssh"]:
                return None
            if command.startswith("cat "):
                return self.server["stamp"]
            if command.startswith("curl "):
                return "" if self.server["comfy"] else None
            return ""

        def remote(config, command, stdin=None):
            self.events.append(("remote", command))
            if command.startswith("echo "):
                self.server["stamp"] = command.split()[1]

        gpu.remote_text, gpu.remote = remote_text, remote
        gpu.cmd_bootstrap = lambda args, config: self.events.append(("bootstrap", config["host"]))
        gpu.cmd_tunnel = lambda args, config: self.events.append(("tunnel", "close" if args.close else config["host"]))
        gpu.cmd_health = lambda args, config: self.events.append(("health", args.templates)) or 0

    def tearDown(self):
        for name, value in self._session_saved.items():
            setattr(gpu, name, value)
        gpu.time.sleep = self._sleep
        super().tearDown()

    def did(self, kind):
        return [event for event in self.events if event[0] == kind]


class SessionTests(SessionFixture, unittest.TestCase):
    """start / stop: use the machine that is there, make one only with --yes, install the stack only when needed."""

    def test_start_without_a_machine_and_without_yes_makes_nothing(self):
        out = self.run_command(gpu.cmd_start, bootstrap=False)
        self.assertEqual(self.code, 2)
        self.assertEqual(self.created(), [])
        self.assertIn("gpu.py start --yes", out)
        self.assertEqual(self.did("tunnel"), [])

    def test_start_yes_makes_the_machine_installs_and_connects(self):
        self.run_command(gpu.cmd_start, yes=True, bootstrap=False)
        self.assertEqual(self.code, 0)
        self.assertEqual(len(self.created()), 1)
        self.assertEqual(self.did("bootstrap"), [("bootstrap", "192.0.2.7")])
        self.assertEqual(self.server["stamp"], gpu.stack_stamp())
        self.assertEqual(self.did("tunnel"), [("tunnel", "192.0.2.7")])
        self.assertEqual(self.did("health"), [("health", gpu.CORE_TEMPLATES)])
        self.assertEqual(gpu.load_state()["ip"], "192.0.2.7")

    def test_start_connects_to_the_running_machine_without_a_new_order(self):
        self.machines.append({"id": "vm-1", "hostname": "yesopen-gpu", "status": "running", "ip": "192.0.2.8",
                              "os_volume_id": "vol-9"})
        self.server["stamp"] = gpu.stack_stamp()
        self.run_command(gpu.cmd_start, yes=True, bootstrap=False)
        self.assertEqual(self.code, 0)
        self.assertEqual(self.created(), [])
        self.assertEqual(self.did("bootstrap"), [])
        self.assertIn(("remote", "cd /srv/yesopen/stack/server && docker compose up -d comfyui >/dev/null 2>&1"),
                      self.events)
        self.assertEqual(self.did("tunnel"), [("tunnel", "192.0.2.8")])
        self.assertEqual(gpu.load_state()["ip"], "192.0.2.8")

    def test_start_reinstalls_a_kept_disk_from_another_stack(self):
        self.machines.append({"id": "vm-1", "hostname": "yesopen-gpu", "status": "running", "ip": "192.0.2.8",
                              "os_volume_id": "vol-9"})
        self.server["stamp"] = "older-stack"
        self.run_command(gpu.cmd_start, bootstrap=False)
        self.assertEqual(self.did("bootstrap"), [("bootstrap", "192.0.2.8")])

    def test_start_refuses_an_order_that_will_not_run(self):
        self.machines.append({"id": "vm-1", "hostname": "yesopen-gpu", "status": "no_capacity", "ip": None,
                              "os_volume_id": None})
        with self.assertRaises(SystemExit) as refused:
            self.run_command(gpu.cmd_start, yes=True, bootstrap=False)
        self.assertIn("gpu.py down --yes", str(refused.exception))
        self.assertEqual(self.created(), [])

    def test_start_uses_a_machine_made_by_hand(self):
        gpu.verda_ready = lambda config: False
        self.config["host"] = "203.0.113.5"
        self.server["stamp"] = gpu.stack_stamp()
        self.run_command(gpu.cmd_start, bootstrap=False)
        self.assertEqual(self.code, 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.did("tunnel"), [("tunnel", "203.0.113.5")])

    def test_start_without_any_machine_or_verda_explains_both_ways(self):
        gpu.verda_ready = lambda config: False
        self.config["host"] = None
        with self.assertRaises(SystemExit) as refused:
            self.run_command(gpu.cmd_start, yes=True, bootstrap=False)
        self.assertIn("gpu.py use ADDRESS", str(refused.exception))
        self.assertIn("verda auth login", str(refused.exception))

    def test_start_gives_up_when_ssh_never_answers(self):
        self.machines.append({"id": "vm-1", "hostname": "yesopen-gpu", "status": "running", "ip": "192.0.2.8",
                              "os_volume_id": "vol-9"})
        self.server["ssh"] = False
        clock = iter(range(0, 10_000, 30))
        saved = gpu.time.time
        gpu.time.time = lambda: next(clock)
        try:
            with self.assertRaises(SystemExit) as failed:
                self.run_command(gpu.cmd_start, bootstrap=False)
        finally:
            gpu.time.time = saved
        self.assertIn("SSH on 192.0.2.8: not ready", str(failed.exception))
        self.assertEqual(self.did("tunnel"), [])

    def test_stop_names_a_machine_made_by_hand(self):
        gpu.verda_ready = lambda config: False
        self.config["host"] = "203.0.113.5"
        out = self.run_command(gpu.cmd_stop, yes=True)
        self.assertEqual(self.events[0], ("tunnel", "close"))
        self.assertIn("203.0.113.5", out)
        self.assertIn("gpu.py use --clear", out)
        self.assertEqual(self.calls, [])

    def test_stop_without_any_machine_says_so(self):
        gpu.verda_ready = lambda config: False
        self.config["host"] = None
        out = self.run_command(gpu.cmd_stop, yes=True)
        self.assertIn("No machine is known here", out)
        self.assertEqual(self.calls, [])

    def test_stop_closes_the_tunnel_before_deleting(self):
        self.run_command(gpu.cmd_start, yes=True, bootstrap=False)
        self.events.clear()
        self.run_command(gpu.cmd_stop, yes=True)
        self.assertEqual(self.events[0], ("tunnel", "close"))
        self.assertEqual(len([c for c in self.calls if c[:2] == ["vm", "action"]]), 1)
        self.assertIsNone(gpu.load_state()["ip"])


class VerdaCheckTests(unittest.TestCase):
    """verda-check: Verda machines need the Verda CLI set up; the user is told what to do, and never asked for secrets."""

    def setUp(self):
        self._saved = gpu.shutil.which, gpu.subprocess.run, gpu.CONFIG
        self.tmp = tempfile.TemporaryDirectory()
        gpu.CONFIG = Path(self.tmp.name) / "config.json"
        self.config = json.loads(gpu.EXAMPLE_CONFIG.read_text())
        self.config["verda"].update({"instance_type": "1B200.30V", "ssh_key_id": ["key-1"]})
        self.installed = True
        self.doctor = {"Credentials found": "ok", "API reachable": "ok", "Authentication valid": "ok"}
        self.ran = []
        gpu.shutil.which = lambda name: "/usr/local/bin/verda" if self.installed and name == "verda" else None

        self.env_login_works = True
        self.environ = dict(gpu.os.environ)
        for name in ("VERDA_CLIENT_ID", "VERDA_CLIENT_SECRET"):
            gpu.os.environ.pop(name, None)

        def run(command, **kwargs):
            self.ran.append(command)
            if command[:4] == ["verda", "--agent", "vm", "list"]:
                self.assertEqual(kwargs["env"]["VERDA_DEBUG"], "false")
                return gpu.subprocess.CompletedProcess(command, 0 if self.env_login_works else 1, "[]", "")
            checks = [{"name": name, "status": status} for name, status in self.doctor.items()]
            return gpu.subprocess.CompletedProcess(command, 0, json.dumps({"checks": checks}), "")

        gpu.subprocess.run = run

    def tearDown(self):
        gpu.shutil.which, gpu.subprocess.run, gpu.CONFIG = self._saved
        gpu.os.environ.clear()
        gpu.os.environ.update(self.environ)
        self.tmp.cleanup()

    def check(self):
        out = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(out):
            code = gpu.cmd_verda_check(None, self.config)
        return code, out.getvalue()

    def test_ready_when_logged_in_with_type_and_keys(self):
        self.assertEqual(self.check(), (0, "Verda CLI: ready (logged in; instance type and SSH key ids are set)\n"))
        self.assertTrue(gpu.verda_ready(self.config))
        self.assertEqual(self.ran[0], ["verda", "doctor", "-o", "json"])

    def test_not_installed_says_how_to_set_it_up(self):
        self.installed = False
        code, out = self.check()
        self.assertEqual(code, 1)
        for step in ("brew install verda-cloud/tap/verda-cli", "Credentials", "verda auth login", "verda doctor",
                     "Never paste them into", "give them to an agent"):
            self.assertIn(step, out)
        self.assertEqual(self.ran, [])

    def test_a_failed_login_is_named(self):
        self.doctor["Authentication valid"] = "fail"
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("Authentication valid: fail", out)
        self.assertIn("verda auth login", out)

    def test_missing_key_ids_are_named(self):
        self.config["verda"]["ssh_key_id"] = None
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("verda.ssh_key_id is empty", out)
        self.assertIn("verda --agent ssh-key list -o json", out)

    def test_session_commands_stop_until_it_is_set_up(self):
        self.doctor["Credentials found"] = "warn"
        for command in (gpu.cmd_start, gpu.cmd_up, gpu.cmd_down, gpu.cmd_status, gpu.cmd_stop):
            if command is gpu.cmd_stop:
                saved, gpu.cmd_tunnel = gpu.cmd_tunnel, lambda args, config: 0
            try:
                with self.assertRaises(SystemExit) as stopped:
                    command(__import__("argparse").Namespace(yes=True, first=False, bootstrap=False), self.config)
            finally:
                if command is gpu.cmd_stop:
                    gpu.cmd_tunnel = saved
            self.assertIn("verda auth login", str(stopped.exception), command.__name__)
            self.assertIn("Credentials found: warn", str(stopped.exception), command.__name__)

    def test_an_api_outage_only_warns(self):
        self.doctor["API reachable"] = "fail"
        out = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(out):
            self.assertFalse(gpu.verda_ready(self.config))
        self.assertIn("maintenance window", out.getvalue())
        self.assertEqual(self.check()[0], 1)

    def test_credentials_in_the_environment_are_checked_with_a_real_call(self):
        # the way scripts/verda-vault.py passes them: no profile file, so doctor fails that check and skips the login
        gpu.os.environ.update(VERDA_CLIENT_ID="id-from-the-vault", VERDA_CLIENT_SECRET="secret-from-the-vault")
        self.doctor.update({"Credentials found": "fail", "Authentication valid": "skip"})
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(self.ran[-1], ["verda", "--agent", "vm", "list", "-o", "json"])
        self.env_login_works = False
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn("VERDA_CLIENT_ID and VERDA_CLIENT_SECRET in the environment were refused", out)
        self.assertNotIn("secret-from-the-vault", out)

    def test_another_provider_does_not_need_verda(self):
        self.config["provider"] = "other"
        self.installed = False
        self.assertFalse(gpu.verda_ready(self.config))
        self.assertEqual(self.check()[0], 0)
        self.assertEqual(self.ran, [])


class FetchCommandTests(SessionFixture, unittest.TestCase):
    """fetch: optional models on the server, MiniMax H3 only with --variant-b, only on a current stack."""

    def setUp(self):
        super().setUp()
        self.config["host"] = "192.0.2.8"
        self.ran = []
        self._run = gpu.subprocess.run
        gpu.subprocess.run = lambda command, **kw: self.ran.append(command) or __import__("types").SimpleNamespace(
            returncode=0)

    def tearDown(self):
        gpu.subprocess.run = self._run
        super().tearDown()

    def fetch(self, templates, variant_b=False, check=False):
        return self.run_command(gpu.cmd_fetch, templates=templates, variant_b=variant_b, check=check)

    def test_h3_needs_variant_b(self):
        self.server["stamp"] = gpu.stack_stamp()
        with self.assertRaises(SystemExit) as caught:
            self.fetch("h3-talk,h3-i2v")
        self.assertIn("--variant-b", str(caught.exception))
        self.assertEqual(self.ran, [])

    def test_refuses_a_server_with_another_stack(self):
        self.server["stamp"] = "older-stack"
        with self.assertRaises(SystemExit) as caught:
            self.fetch("h3-talk", variant_b=True)
        self.assertIn("gpu.py start", str(caught.exception))
        self.assertEqual(self.ran, [])

    def test_unknown_template(self):
        with self.assertRaises(SystemExit):
            self.fetch("h4-talk", variant_b=True)

    def test_runs_the_fetcher_on_the_server(self):
        self.server["stamp"] = gpu.stack_stamp()
        self.fetch("h3-talk,h3-i2v,h3-r2v", variant_b=True)
        self.assertEqual(self.code, 0)
        command = self.ran[-1][-1]
        self.assertIn("python3 fetch_models.py --models /srv/yesopen/models --templates h3-talk,h3-i2v,h3-r2v "
                      "--variant-b --jobs 6", command)
        self.assertNotIn("HF_TOKEN=", command)  # the token stays in the server's .env


@unittest.skipUnless(comfy_available(), f"no ComfyUI at {COMFY_URL}")
class EndToEndTests(UseFixtures, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.comfy = gpu.Comfy(COMFY_URL)

    def tearDown(self):
        self.tmp.cleanup()
        super().tearDown()

    def run_fixture(self, template, given, name, **kwargs):
        job = gpu.prepare_job(template, given, random.Random(3), self.dir, self.comfy.get("/object_info"))
        return gpu.run_job(self.comfy, job, self.dir / "out", name, timeout=120, say=lambda *_: None, **kwargs)

    def test_audio_is_padded_to_whole_frames_and_saved_lossless(self):
        source = self.dir / "line.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.3",
                        "-ar", "44100", str(source)], check=True)
        record = self.run_fixture("echo-audio", {"audio": str(source), "seconds": "1.3"}, "line-01")
        saved = Path(record["outputs"]["audio"][0])
        self.assertEqual(saved.suffix, ".flac")
        # 1.3 s * 24 = 31.2 frames -> 32 frames -> 1.3333 s of audio
        duration = float(probe(saved, "format=duration")["format"]["duration"])
        self.assertAlmostEqual(duration, 32 / 24, delta=0.002)
        self.assertEqual(record["frames"]["frames"], 33)
        log = [json.loads(line) for line in (self.dir / "out" / "jobs.jsonl").read_text().splitlines()]
        self.assertEqual(log[-1]["name"], "line-01")
        self.assertEqual(log[-1]["inputs"]["audio"]["sha256"], gpu.sha256(Path(log[-1]["inputs"]["audio"]["file"])))

    def test_image_round_trip_is_identical(self):
        source = self.dir / "still.png"
        source.write_bytes(gpu.png_rgba(32, 48, lambda x, y: 255))
        record = self.run_fixture("echo-image", {"image": str(source)}, "still-01")
        saved = Path(record["outputs"]["image"][0])
        size = probe(saved, "stream=width,height")["streams"][0]
        self.assertEqual((size["width"], size["height"]), (32, 48))

    def test_video_round_trip(self):
        source = self.dir / "take.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=128x72:rate=24:duration=1",
                        "-f", "lavfi", "-i", "sine=duration=1", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", str(source)], check=True)
        record = self.run_fixture("echo-video", {"video": str(source)}, "take-01")
        saved = Path(record["outputs"]["video"][0])
        stream = probe(saved, "stream=codec_type,width,height,nb_frames")["streams"]
        video = next(s for s in stream if s["codec_type"] == "video")
        self.assertEqual((video["width"], video["height"]), (128, 72))
        self.assertTrue(any(s["codec_type"] == "audio" for s in stream))

    def test_generated_mask_and_text_output(self):
        record = self.run_fixture("painter-mask", {"prompt": "zażółć gęślą jaźń line"}, "mask-01")
        image = Path(record["outputs"]["image"][0])
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(image), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout
        left, right = raw[64 * 32 + 5], raw[64 * 32 + 60]  # one pixel from each half of row 32
        self.assertGreater(left, 200)
        self.assertLess(right, 50)
        self.assertEqual(Path(record["outputs"]["final_prompt"][0]).read_text(), "zażółć gęślą jaźń line")

    def test_validate_only_queues_nothing(self):
        source = self.dir / "still.png"
        source.write_bytes(gpu.png_rgba(8, 8, lambda x, y: 255))
        record = self.run_fixture("echo-image", {"image": str(source)}, "check", validate_only=True)
        self.assertTrue(record["validated"])
        queue = self.comfy.get("/queue")
        queued = [item[1] for item in queue["queue_running"] + queue["queue_pending"]]
        self.assertNotIn(record["prompt_id"], queued)

    def test_bad_option_is_rejected_before_queueing(self):
        source = self.dir / "take.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=24:duration=0.5",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)], check=True)
        with self.assertRaises(SystemExit) as error:
            self.run_fixture("echo-video", {"video": str(source), "codec": "prores"}, "bad")
        self.assertIn("codec", str(error.exception))


if __name__ == "__main__":
    unittest.main()
