"""YesOpen pipeline nodes for ComfyUI: the skit project from its script to the delivered files, in one graph.

The project lives in /work/<date>-<slug> (the same folder gpu.py push/pull and the editor use: project.json, lines.json,
voice/, lines/, takes/, edit/, final/). These nodes read it, write the GPU results into it under the names the skill's
scripts expect (voice/<id>-s<seed>.audio.flac, takes/<id>.video.mp4, stills/still-<who>-<seed>.image.png) and run the
skill's scripts on it through the editor service (gpu/editor/api.py: the editor image, the same ffmpeg, Python and
Whisper as on the Mac). A gate passes its project on only when it is approved, so nothing after an open gate runs.
"""
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from .runtime import cached, checkpoint, digest, manifest, require_files, require_qa, require_takes, reusable, signature, verify_qa_files, write_json

WORK = Path(os.environ.get("YESOPEN_WORK", "/work"))
EDITOR = os.environ.get("YESOPEN_EDITOR_URL", "http://editor-api:8190")
PROJECT = "YESOPEN_PROJECT"
CATEGORY = "YesOpen"
GATES = ["1 · Referencja", "2 · Scenariusz (Twoje TAK)", "3 · Obsada (wybrane stille)", "4 · Ujęcia",
         "5 · Montaż", "6 · Formaty i QA", "7 · Dostawa"]
FORMATS = ["9:16", "4:5", "1:1", "16:9"]
LANGUAGE_LABELS = [f'{name} ({code})' for name, code in zip(
    'Arabic Danish German Greek English Spanish Finnish French Hebrew Hindi Italian Japanese Korean Malay Dutch Norwegian Polish Portuguese Russian Swedish Swahili Turkish Chinese'.split(),
    'ar da de el en es fi fr he hi it ja ko ms nl no pl pt ru sv sw tr zh'.split())]


# ---------- helpers ----------

def project_dir(name: str) -> Path:
    path = WORK / Path(name).name
    if not path.is_dir():
        raise RuntimeError(f"Nie ma projektu {name} w {WORK} (gpu.py push <projekt> albo węzeł 'Nowy projekt').")
    return path


def projects() -> list:
    try:
        names = sorted(p.name for p in WORK.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:
        names = []
    return names or ["(brak projektów w /work)"]


def editor(project, script: str, args: list, timeout=3600) -> str:
    """Run a skill script in the editor container; raise with its output when it fails."""
    body = json.dumps({"project": project, "script": script, "args": [str(a) for a in args], "timeout": timeout}).encode()
    request = urllib.request.Request(f"{EDITOR}/run", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout + 60) as response:
            result = json.load(response)
    except urllib.error.URLError as err:
        raise RuntimeError(f"Usługa edytora ({EDITOR}) nie odpowiada: {err}. Uruchom editor-api (compose.yaml).")
    if "error" in result:
        raise RuntimeError(f"{script}: {result['error']}")
    if result["code"] != 0:
        raise RuntimeError(f"{script} {' '.join(map(str, args))} zakończył się błędem:\n{result['output'][-4000:]}")
    return result["output"]


def state(project, *globs) -> str:
    """A fingerprint of the project files a node depends on, so it runs again exactly when they change. ComfyUI asks
    before the inputs that come through wires are known: then (project None) every project in /work counts."""
    roots = [project_dir(project)] if isinstance(project, str) else [WORK / p for p in projects() if (WORK / p).is_dir()]
    h = hashlib.sha256()
    for root in roots:
        for pattern in globs:
            for p in sorted(root.glob(pattern)):
                if p.is_file():
                    st = p.stat()
                    h.update(f"{root.name}/{p.relative_to(root)}:{st.st_size}:{st.st_mtime_ns}".encode())
    return h.hexdigest()


def selected_project(project, prompt=None, unique_id=None):
    if isinstance(project, str):
        return project
    todo, seen, found = [str(unique_id)], set(), set()
    while todo:
        nid = todo.pop()
        if nid in seen:
            continue
        seen.add(nid)
        node = (prompt or {}).get(nid, {})
        if node.get('class_type') == 'YesOpenProject':
            found.add(node['inputs']['project'])
        for value in node.get('inputs', {}).values():
            if isinstance(value, list) and len(value) == 2:
                todo.append(str(value[0]))
    if len(found) == 1:
        return found.pop()
    return project


def load_audio(path: Path, rate=48000) -> dict:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"])
    wave = torch.from_numpy(np.frombuffer(raw, np.float32).copy()).reshape(1, 1, -1)
    return {"waveform": wave, "sample_rate": rate}


def save_audio(audio: dict, path: Path) -> None:
    wave = audio["waveform"][0]                                   # [channels, samples]
    data = wave.t().contiguous().cpu().float().numpy().tobytes()   # interleaved
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(audio["sample_rate"]),
                    "-ac", str(wave.shape[0]), "-i", "-", str(path)], input=data, check=True)


def load_image(path: Path) -> torch.Tensor:
    img = Image.open(path).convert("RGB")
    return torch.from_numpy(np.asarray(img).astype(np.float32) / 255.0)[None]


def save_image(image: torch.Tensor, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)).save(path)


def blocked():
    from comfy_execution.graph_utils import ExecutionBlocker
    return ExecutionBlocker(None)


def batch_job(root: Path, batch: str, name: str) -> dict:
    jobs = json.loads((root / batch).read_text())["jobs"]
    job = next((j for j in jobs if j["name"] == name), None)
    if job is None:
        raise RuntimeError(f"{batch}: brak zadania {name}")
    return job["set"]


# ---------- the project and its gates ----------

class Project:
    DESCRIPTION = "The skit project in /work (project.json, lines.json, ...). New folders appear after 'Refresh'."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (projects(),)}}

    RETURN_TYPES = (PROJECT, "STRING")
    RETURN_NAMES = ("project", "summary")
    FUNCTION = "run"
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, project):
        return state(project, "project.json", "lines.json")

    def run(self, project):
        root = project_dir(project)
        doc = json.loads((root / "lines.json").read_text()) if (root / "lines.json").exists() else {}
        chars = doc.get("characters", {})
        missing = [f"{n}: still" for n, c in chars.items() if not (root / c.get("still", "-")).exists()]
        missing += [f"{n}: voice" for n, c in chars.items() if not (root / c.get("voice", "-")).exists()]
        summary = (f"{project}\nlanguage: {doc.get('language', '?')}\nlines: {len(doc.get('lines', []))}  "
                   f"characters: {', '.join(chars) or '-'}\n" + ("missing: " + ", ".join(missing) if missing else "cast complete"))
        return (project, summary)


class Status:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': (PROJECT,)}, 'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}
    RETURN_TYPES = ('STRING',)
    FUNCTION = 'run'
    OUTPUT_NODE = True
    CATEGORY = CATEGORY
    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        return state(selected_project(project, kw.get('prompt'), kw.get('unique_id')),
                     'edit/pipeline-state.json', 'lines/*.wav', 'takes/*.mp4', 'final/*', 'edit/qa-*.json')
    def run(self, project, **kw):
        root = project_dir(project)
        doc = json.loads((root / 'lines.json').read_text())
        ids = [line['id'] for line in doc['lines']]
        pending = [line for line in ids if not cached(root, 'take/' + line)]
        text = json.dumps({'project': project, 'lines': len(ids), 'takes_without_checkpoint': pending,
                           'checkpoint': 'edit/pipeline-state.json', 'delivery_manifest': (root / 'final/manifest.json').exists()},
                          ensure_ascii=False, indent=2)
        return {'ui': {'text': [text]}, 'result': (text,)}


class NewProject:
    DESCRIPTION = "Creates /work/<date>-<slug> from the skill's templates (new_project.py)."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"slug": ("STRING", {"default": "nowa-scenka"}),
                             "title": ("STRING", {"default": "End-card line"}),
                             "engine": (["gpu", "higgsfield"],)}}

    RETURN_TYPES = (PROJECT,)
    RETURN_NAMES = ("project",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    def run(self, slug, title, engine):
        before = set(projects())
        editor(None, "new_project.py", [slug, "--title", title, "--engine", engine, "--root", str(WORK)])
        made = sorted(set(projects()) - before) or [p for p in projects() if p.endswith(slug)]
        return (made[-1],)


class Gate:
    DESCRIPTION = ("A gate of the skill (references/qa-checklist.md): the project goes on only when 'approved' is on. "
                   "Everything after a closed gate is skipped.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "gate": (GATES,), "approved": ("BOOLEAN", {"default": False})}}

    RETURN_TYPES = (PROJECT,)
    RETURN_NAMES = ("project",)
    FUNCTION = "run"
    CATEGORY = CATEGORY

    def run(self, project, gate, approved):
        if approved and gate.startswith('3'):
            root = project_dir(project)
            doc = json.loads((root / 'lines.json').read_text())
            files = [c['voice'] for c in doc['characters'].values()]
            files += [line.get('still') or doc['characters'][line['who']].get('still', '') for line in doc['lines']]
            if not all(files):
                raise RuntimeError('Obsada: każda kwestia musi mieć wybrany still i głos.')
            require_files(root, files)
        if approved and gate.startswith('6'):
            verify_qa_files(project_dir(project), FORMATS)
        return (project if approved else blocked(),)


# ---------- the script into the GPU stages ----------

class Line:
    DESCRIPTION = ("One line of lines.json as the voice batch writes it (gpu_batches.py voice): text, voice sample, "
                   "exaggeration, CFG and seed for Chatterbox, and the speaker's look for Z-Image.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "line": ("STRING", {"default": "l01"}),
                             "take": ("INT", {"default": 0, "min": 0, "max": 1, "tooltip": "which of the two tts seeds"})},
                "hidden": {"prompt": "PROMPT", "unique_id": "UNIQUE_ID"}}

    RETURN_TYPES = ("STRING", "AUDIO", "FLOAT", "FLOAT", "INT", "STRING", "STRING", "STRING", LANGUAGE_LABELS)
    RETURN_NAMES = ("text", "voice", "exaggeration", "cfg_weight", "seed", "look", "who", "line", "language")
    OUTPUT_IS_LIST = (True,) * 9
    FUNCTION = "run"
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        project = selected_project(project, kw.get('prompt'), kw.get('unique_id'))
        return state(project, "lines.json", "project.json", "voices/*") + str(kw.get('line')) + str(kw.get('take'))

    def run(self, project, line, take, prompt=None, unique_id=None):
        root = project_dir(project)
        editor(project, "gpu_batches.py", ["voice", "."])
        doc = json.loads((root / "lines.json").read_text())
        ids = [entry['id'] for entry in doc['lines']] if line == '*' else [line]
        if not ids:
            raise RuntimeError('lines.json: brak kwestii.')
        rows = [self.one(root, item, take, doc) for item in ids]
        return tuple([row[column] for row in rows] for column in range(9))

    def one(self, root, line, take, doc):
        values = batch_job(root, "voice/batch.json", f"{line}-s{self.seed(root, line, take)}")
        entry = next(l for l in doc["lines"] if l["id"] == line)
        char = doc["characters"][entry["who"]]
        voice = load_audio((root / "voice" / values["voice"]).resolve())
        return (values["text"], voice, float(values["exaggeration"]), float(values["cfg_weight"]), int(values["seed"]),
                char.get("look", ""), entry["who"], line, values['language'])

    @staticmethod
    def seed(root, line, take):
        doc = json.loads((root / "lines.json").read_text())
        index = next(i for i, l in enumerate(doc["lines"]) if l["id"] == line)
        return 100 + 2 * index + take


class FitLine:
    DESCRIPTION = ("Saves the recorded line as voice/<id>-s<seed>.audio.flac, checks and cuts it (fit_lines.py) and "
                   "writes the take job (gpu_batches.py takes): the fitted audio, the take prompt, its length, its seed "
                   "and the picked still of the speaker.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "line": ("STRING", {"default": "l01"}), "audio": ("AUDIO", {'lazy': True}),
                             "seed": ("INT", {"default": 100, "min": 0, "max": 2 ** 31})},
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = ("AUDIO", "STRING", "FLOAT", "INT", "IMAGE", "BOOLEAN", "STRING")
    RETURN_NAMES = ("line_audio", "take_prompt", "seconds", "take_seed", "still", "has_still", "report")
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        return state(selected_project(project, kw.get('prompt'), kw.get('unique_id')),
                     'lines.json', 'project.json', 'voices/*', 'lines/*.wav', 'edit/pipeline-state.json')

    def check_lazy_status(self, project, line, seed, audio=None, prompt=None, unique_id=None):
        root = project_dir(project)
        expected = signature(root, line, seed, prompt, unique_id, 'audio')
        return [] if reusable(root, 'voice/' + line, f'lines/{line}.source.json', expected) or audio is not None else ['audio']

    def run(self, project, line, seed, audio=None, prompt=None, unique_id=None):
        root = project_dir(project)
        expected = signature(root, line, seed, prompt, unique_id, 'audio')
        if reusable(root, 'voice/' + line, f'lines/{line}.source.json', expected):
            report = f'{line}: wznowiono dopasowane audio z checkpointu.'
        else:
            save_audio(audio, root / "voice" / f"{line}-s{seed}.audio.flac")
            report = editor(project, "fit_lines.py", ["lines.json", "voice", "lines", "--only", line])
        fit = json.loads((root / "lines" / "fit.json").read_text()).get(line, {})
        if not fit.get("ok", False) or not (root / "lines" / f"{line}.wav").exists():
            raise RuntimeError(f"{line}: żadne nagranie nie przeszło fit_lines (zmień seed w 'Kwestia z projektu'):\n"
                               f"{report[-2000:]}")
        report += editor(project, "gpu_batches.py", ["takes", ".", "--only", line, "--out", f"takes/batch-{line}.json"])
        values = batch_job(root, f"takes/batch-{line}.json", line)
        if json.loads((root / f'takes/batch-{line}.json').read_text())['jobs'][0]['template'] != 'talk':
            raise RuntimeError(f'{line}: graf produkcyjny obsługuje LTX talk; H3 uruchom oddzielnie.')
        still_path = (root / "takes" / values["image"]).resolve()
        has_still = still_path.exists()
        if not has_still:
            raise RuntimeError(f'{line}: wybierz istniejący still w lines.json przed generowaniem ujęcia.')
        still = load_image(still_path)
        result = (load_audio((root / "takes" / values["audio"]).resolve()), values["prompt"], float(values["seconds"]),
                  int(values["seed"]), still, has_still, report[-3000:])
        checkpoint(root, 'voice/' + line, [root / 'lines' / f'{line}.wav'])
        write_json(root / f'lines/{line}.source.json', {'signature': expected})
        return {'ui': {'text': [report[-3000:]]}, 'result': result}


class VoiceApproval:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': (PROJECT,), 'audio': ('AUDIO',),
                             'approved': ('BOOLEAN', {'default': False})},
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}
    RETURN_TYPES = ('AUDIO',)
    OUTPUT_IS_LIST = (True,)
    INPUT_IS_LIST = True
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        return state(selected_project(project, kw.get('prompt'), kw.get('unique_id')), 'lines/*.wav')

    def run(self, project, audio, approved, **kw):
        root = project_dir(project[0])
        path = root / 'edit/pipeline-state.json'
        saved = json.loads(path.read_text()) if path.exists() else {}
        if not all(approved):
            saved.pop('approved-voices', None)
            write_json(path, saved)
            return ([blocked()],)
        files = sorted((root / 'lines').glob('*.wav'))
        now = {str(p.relative_to(root)): digest(p) for p in files}
        if saved.get('approved-voices') and saved['approved-voices'] != now:
            raise RuntimeError('Audio zmieniło się po odsłuchu. Wyłącz approved, uruchom odsłuch, zatwierdź ponownie.')
        checkpoint(root, 'approved-voices', files)
        return (audio,)


class JoinProduction:
    """Wait for all mapped takes and the bed before starting project-level edit steps."""
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'project': (PROJECT,), 'music': ('STRING',)}}
    INPUT_IS_LIST = True
    RETURN_TYPES = (PROJECT, 'STRING')
    FUNCTION = 'run'
    CATEGORY = CATEGORY
    def run(self, project, music):
        if len(set(project)) != 1:
            raise RuntimeError('Połącz ujęcia tylko jednego projektu.')
        root = project_dir(project[0])
        require_takes(root)
        require_files(root, [str(Path(p).relative_to(root)) for p in music])
        return (project[0], f'Gotowe: {len(project)} ujęć, muzyka zapisana.')


# ---------- GPU results into the project ----------

class SaveStill:
    DESCRIPTION = "A still candidate into stills/still-<who>-<seed>.image.png; pick one at gate 3 (lines.json -> still)."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "who": ("STRING", {"default": "char1"}), "image": ("IMAGE",),
                             "seed": ("INT", {"default": 0, "min": 0, "max": 2 ** 63 - 1})}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("path",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    def run(self, project, who, image, seed):
        path = project_dir(project) / "stills" / f"still-{who}-{seed}.image.png"
        save_image(image, path)
        return {"ui": {"text": [str(path)]}, "result": (str(path),)}


class SaveTake:
    DESCRIPTION = "The take into takes/<id>.video.mp4, then inspect_take.py: word timestamps, frame sheet, boundaries."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "line": ("STRING", {"default": "l01"}), "video": ("VIDEO", {'lazy': True}),
                             'suffix': ('STRING', {'default': ''})}, 'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = (PROJECT, "STRING")
    RETURN_NAMES = ("project", "report")
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        return state(selected_project(project, kw.get('prompt'), kw.get('unique_id')),
                     'lines.json', 'voices/*', 'stills/*', 'lines/*.wav', 'takes/*.mp4', 'edit/pipeline-state.json') + json.dumps(kw.get('prompt', {}), sort_keys=True)

    def check_lazy_status(self, project, line, suffix='', video=None, prompt=None, unique_id=None):
        root = project_dir(project)
        expected = signature(root, line, prompt=prompt, unique_id=unique_id, input_name='video')
        return [] if reusable(root, 'take/' + line + suffix, f'takes/{line}{suffix}.source.json', expected) or video is not None else ['video']

    def run(self, project, line, video=None, suffix='', prompt=None, unique_id=None):
        root = project_dir(project)
        expected = signature(root, line, prompt=prompt, unique_id=unique_id, input_name='video')
        line = line + suffix
        if reusable(root, 'take/' + line, f'takes/{line}.source.json', expected):
            return {'ui': {'text': [f'{line}: wznowiono gotowe ujęcie.']}, 'result': (project, f'{line}: checkpoint OK')}
        path = project_dir(project) / "takes" / f"{line}.video.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        video.save_to(str(path))
        report = editor(project, "inspect_take.py", [f"takes/{line}.video.mp4"])
        checkpoint(project_dir(project), 'take/' + line, [path])
        write_json(root / f'takes/{line}.source.json', {'signature': expected})
        return {"ui": {"text": [report[-3000:]]}, "result": (project, report[-3000:])}


class SaveMusic:
    DESCRIPTION = "The music bed into music/<name>.flac (project.json -> music.file, edit-pipeline.md section 8)."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "audio": ("AUDIO", {'lazy': True}), "name": ("STRING", {"default": "bed"})},
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("path",)
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY

    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        return state(selected_project(project, kw.get('prompt'), kw.get('unique_id')), 'music/*') + json.dumps(kw.get('prompt', {}), sort_keys=True)

    def check_lazy_status(self, project, name, audio=None, prompt=None, unique_id=None):
        root = project_dir(project)
        expected = signature(root, None, prompt=prompt, unique_id=unique_id, input_name='audio')
        return [] if reusable(root, 'music', f'music/{Path(name).name}.source.json', expected) or audio is not None else ['audio']

    def run(self, project, name, audio=None, prompt=None, unique_id=None):
        path = project_dir(project) / "music" / f"{Path(name).name}.flac"
        root = project_dir(project)
        expected = signature(root, None, prompt=prompt, unique_id=unique_id, input_name='audio')
        if not reusable(root, 'music', f'music/{Path(name).name}.source.json', expected):
            save_audio(audio, path)
        cfg = json.loads((root / 'project.json').read_text())
        cfg.setdefault('music', {})['file'] = str(path.relative_to(root))
        write_json(root / 'project.json', cfg)
        checkpoint(root, 'music', [path])
        write_json(root / f'music/{Path(name).name}.source.json', {'signature': expected})
        return {"ui": {"text": [str(path)]}, "result": (str(path),)}


# ---------- the edit, formats, QA and delivery (the skill's scripts in the editor) ----------

EDIT_INPUTS = ("project.json", "lines.json", "edit/cuts.json", "takes/*.mp4", "takes/*.words.json", "lines/*.wav", "music/*")


class Step:
    """A skill script on the whole project; passes the project on, so the steps run in the order they are wired."""
    SCRIPT, ARGS, DESCRIPTION = "", [], ""
    RETURN_TYPES = (PROJECT, "STRING")
    RETURN_NAMES = ("project", "log")
    FUNCTION = "run"
    OUTPUT_NODE = True
    CATEGORY = CATEGORY
    CACHE_INPUTS = EDIT_INPUTS

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,)}, 'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    @classmethod
    def IS_CHANGED(cls, project=None, **kw):
        project = selected_project(project, kw.get('prompt'), kw.get('unique_id'))
        settings = {k: v for k, v in kw.items() if k not in ('prompt', 'unique_id')}
        return state(project, *cls.CACHE_INPUTS) + json.dumps(settings, sort_keys=True, default=str)

    def args(self, **kw):
        return list(self.ARGS)

    def run(self, project, **kw):
        kw.pop('prompt', None)
        kw.pop('unique_id', None)
        log = editor(project, self.SCRIPT, self.args(**kw))
        return {"ui": {"text": [log[-3000:]]}, "result": (project, log[-3000:])}


class BuildAssets(Step):
    SCRIPT, ARGS = "build_assets.py", [".", "--sheet"]
    DESCRIPTION = "Ding, banners, end card and caption sample for every format (build_assets.py --sheet)."


class MakeEDL(Step):
    SCRIPT, ARGS = "make_edl.py", ["."]
    DESCRIPTION = "edit/cuts.json + word timestamps -> edit/edl.json (make_edl.py)."

    def run(self, project, **kw):
        require_takes(project_dir(project))
        return super().run(project, **kw)


def final_video(project: str, fmt: str):
    from comfy_api.input_impl import VideoFromFile
    tag = fmt.replace(":", "x")
    found = sorted((project_dir(project) / "final").glob(f"*-{tag}.mp4"), key=lambda p: p.stat().st_mtime)
    if not found:
        raise RuntimeError(f"Brak final/*-{tag}.mp4 po renderze.")
    return VideoFromFile(str(found[-1])), str(found[-1])


class Assemble(Step):
    SCRIPT = "assemble.py"
    DESCRIPTION = "Renders one format from edit/edl.json (assemble.py); 9:16 with crop-safe for the cropped formats."
    RETURN_TYPES = (PROJECT, "VIDEO", "STRING")
    RETURN_NAMES = ("project", "video", "log")
    CACHE_INPUTS = EDIT_INPUTS + ('edit/edl.json', 'edit/assets/**/*')

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "format": (FORMATS,), "crop_safe": ("BOOLEAN", {"default": True})},
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    def run(self, project, format, crop_safe, **kw):
        args = [".", "--format", format] + (["--crop-safe"] if crop_safe and format == "9:16" else [])
        log = editor(project, self.SCRIPT, args)
        video, path = final_video(project, format)
        checkpoint(project_dir(project), 'render/' + format, [Path(path)])
        return {"ui": {"text": [f"{path}\n{log[-2000:]}"]}, "result": (project, video, log[-3000:])}


class CropFormats(Step):
    SCRIPT, ARGS = "crop_formats.py", ["."]
    DESCRIPTION = "4:5 and 1:1 cut from the 9:16 master with their own end cards (crop_formats.py)."
    CACHE_INPUTS = EDIT_INPUTS + ('final/*-9x16.mp4', 'edit/assets/**/*')


class QAReport(Step):
    SCRIPT = "qa_report.py"
    DESCRIPTION = "Frames, loudness (-14 LUFS, true peak), caption sheet and, with Whisper, the word match (qa_report.py)."
    CACHE_INPUTS = EDIT_INPUTS + ('final/*.mp4', 'edit/edl.json')

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"project": (PROJECT,), "format": (FORMATS,), "whisper": ("BOOLEAN", {"default": True})},
                'hidden': {'prompt': 'PROMPT', 'unique_id': 'UNIQUE_ID'}}

    def args(self, format, whisper):
        return [".", "--format", format, '--out', f'edit/qa-{format.replace(":", "x")}.json'] + (["--whisper"] if whisper else [])

    def run(self, project, format, whisper, **kw):
        root = project_dir(project)
        log = editor(project, self.SCRIPT, self.args(format, whisper))
        path = root / f'edit/qa-{format.replace(":", "x")}.json'
        report = json.loads(path.read_text())
        require_qa(report, whisper)
        _, video = final_video(project, format)
        report['video_sha256'] = digest(video)
        write_json(path, report)
        checkpoint(root, 'qa/' + format, [path])
        return {'ui': {'text': [log[-3000:]]}, 'result': (project, log[-3000:])}


class EncodeVariants(Step):
    SCRIPT = "encode_variants.py"
    DESCRIPTION = "Share copy (25 MiB), web copy (15 MB) and poster of the 9:16 master (encode_variants.py)."
    CACHE_INPUTS = EDIT_INPUTS + ('final/*-9x16.mp4', 'final/*-4x5.mp4', 'final/*-1x1.mp4', 'final/*-16x9.mp4', 'edit/qa-*.json')

    def args(self):
        _, path = final_video(self.project, "9:16")
        return [str(Path(path).relative_to(project_dir(self.project)))]

    def run(self, project, **kw):
        verify_qa_files(project_dir(project), FORMATS)
        logs = []
        root = project_dir(project)
        for fmt in FORMATS:
            _, path = final_video(project, fmt)
            logs.append(editor(project, self.SCRIPT, [str(Path(path).relative_to(root))]))
        data = manifest(project_dir(project))
        text = json.dumps(data, ensure_ascii=False)
        checkpoint(root, 'delivery', [root / item['path'] for item in data['files']])
        return {'ui': {'text': [text]}, 'result': (project, text)}


NODES = {
    "YesOpenProject": (Project, "YesOpen · Projekt"),
    "YesOpenStatus": (Status, 'YesOpen · Status projektu'),
    "YesOpenNewProject": (NewProject, "YesOpen · Nowy projekt"),
    "YesOpenGate": (Gate, "YesOpen · Bramka"),
    "YesOpenLine": (Line, "YesOpen · Kwestia z projektu"),
    "YesOpenVoiceApproval": (VoiceApproval, 'YesOpen · Odsłuch zatwierdzony'),
    "YesOpenJoinProduction": (JoinProduction, 'YesOpen · Wszystkie ujęcia i muzyka'),
    "YesOpenFitLine": (FitLine, "YesOpen · Dopasuj kwestię (fit_lines)"),
    "YesOpenSaveStill": (SaveStill, "YesOpen · Still do projektu"),
    "YesOpenSaveTake": (SaveTake, "YesOpen · Ujęcie do projektu"),
    "YesOpenSaveMusic": (SaveMusic, "YesOpen · Muzyka do projektu"),
    "YesOpenBuildAssets": (BuildAssets, "YesOpen · Assety montażu"),
    "YesOpenMakeEDL": (MakeEDL, "YesOpen · EDL"),
    "YesOpenAssemble": (Assemble, "YesOpen · Render formatu"),
    "YesOpenCropFormats": (CropFormats, "YesOpen · Formaty 4:5 i 1:1"),
    "YesOpenQAReport": (QAReport, "YesOpen · Raport QA"),
    "YesOpenEncodeVariants": (EncodeVariants, "YesOpen · Wersje do wysyłki"),
}
NODE_CLASS_MAPPINGS = {k: v[0] for k, v in NODES.items()}
NODE_DISPLAY_NAME_MAPPINGS = {k: v[1] for k, v in NODES.items()}
