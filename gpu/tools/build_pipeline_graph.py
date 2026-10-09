#!/usr/bin/env python3
"""Build the whole skit pipeline as one ComfyUI graph from the official UI workflows (gpu/workflows/ui).

    python3 gpu/tools/build_pipeline_graph.py [--ui DIR] [--out FILE]

Layout, three rows left to right:
- top row: the phases that run on the user's computer (0-2 before the GPU, 5-8 after it), notes only;
- main track (GPU): still -> line -> talking take -> upscale -> interpolation, the stages LINKED by their outputs, so
  one "Run" makes a finished take from a prompt;
- below it the other stages, all wired in and run by the same "Run": pose edit (Qwen) -> silent b-roll (LTX-2.5), the
  two-voice dialog and the music. Only MiniMax H3 is muted (mode 2): it needs MiniMax's written consent (MUTED).
Inside a stage the nodes follow the data flow (loaders, model, outputs).

Changes against the templates, all explained in the stage notes:
- The templates' own notes (model links, how-tos, reference tables) are dropped; the stage headers keep the warnings.
- AudioCrop (not a ComfyUI 0.35 core node; gpu/workflows/patches.json bypasses it too) is removed and its source wired
  straight on; the unused RecordAudio node is dropped.
- The templates' placeholder input files are replaced by files that exist on the kept disk (INPUTS), so the graph
  validates; pick your own in the Load nodes.
- Stage inputs that were Load nodes are wired to the previous stage (LINKS below) and the Load nodes are removed.
"""
import argparse
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_UI = HERE.parent / "workflows" / "ui"
DEFAULT_OUT = HERE.parent / "workflows" / "pipeline" / "yesopen-skit-pipeline.json"

# placeholder inputs of the official templates -> files in comfy/input of the kept disk (a still, two voices, a line, a clip)
INPUTS = {
    "lily_girl_blue.png": "562e5da24638c2a6-owner.png",
    "cactus_man.png": "562e5da24638c2a6-owner.png",
    "neon_cyborg_portrait.png": "562e5da24638c2a6-owner.png",
    "transparent_rgb_gaming_mouse.png": "562e5da24638c2a6-owner.png",
    "chatterbox_input_target_voice.mp3": "5a98d65c185ac9ff-owner.wav",
    "chatterbox_input_gettysburg.wav": "aac8220ef28b9fae-neighbour.wav",
    "ltx_23_audio.mp3": "8e4283f5b5f7c694-l01-4.6667s.wav",
    "grainy_perfume_shot_crf32.mp4": "yesopen-sample.mp4",
    "white_armored_warrior.mp4": "yesopen-sample.mp4",
}

# model files of the templates that the kept disk holds in another variant (gpu/workflows/patches.json, templates.json)
MODELS = {
    "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors": "qwen3vl_32b_minimax_h3_int8_convrot.safetensors",
}

NOTE_TYPES = ("Note", "MarkdownNote")
LOADERS = ("LoadImage", "LoadAudio", "LoadVideo")

# the Save nodes are the previews: one size each, so the rows stay compact
SAVE_SIZES = {"SaveImage": (520, 520), "SaveImageAdvanced": (560, 480), "SaveVideo": (520, 440)}
REMOVABLE = LOADERS + ("ResolutionSelector",)     # source nodes that vanish when their last link is rewired
SETTINGS = "__settings__"                         # the stage that holds the shared skit settings (no template file)

# the skit's own defaults instead of the templates' demo content (a cactus, Spanish, "I'm Purz")
STILL = ("Vertical smartphone photo, medium shot from mid-thigh up, eye level. A friendly woman in a white clinic coat, "
         "bright modern reception, natural window light, relaxed expression, slightly imperfect candid look.")
EDIT = "Same person, same clothes and room; she now holds a phone with its back to the camera and looks at it with a small smile."
LINE = "Cześć, tu Kasia z recepcji. Zapraszam na przegląd zębów i szybką konsultację."
DIALOG = ("SPEAKER A: Hey, did you book your check-up yet?\nSPEAKER B: Not yet, I keep forgetting.\n"
          "SPEAKER A: It takes five minutes, I will send you the link.\nSPEAKER B: Great, thanks!")
TALK = ("A person speaks directly to the camera in a natural, relaxed way, lips in sync with the audio. The framing stays exactly "
        "as in the still: no zoom, no push-in, static handheld smartphone look, soft natural light. No text, no captions, no black frames.")
ACTION = ("Use the provided start image as the first frame. A short silent reaction: the person glances at the phone, a small smile, "
          "subtle head movement. Static camera, same framing as the still, natural room sound. No text, no black frame.")
H3 = ("Vertical smartphone video. The scene opens exactly on image 1. Natural, subtle movement of the person, static camera, "
      "same framing, no zoom, constant environment. No text overlays.")
WIDTH, HEIGHT, SECONDS, SEED = 704, 1280, 5, 42            # the shared settings panel

# file name prefix of each stage's Save node, so results of different stages never share a name
SAVE_PREFIX = {"z": "yesopen/still", "qwen": "yesopen/still-edit", "tts": "yesopen/voice-line", "dlg": "yesopen/voice-dialog",
               "ltx23": "yesopen/take-talk", "ltx25": "yesopen/take-action", "h3": "yesopen/take-h3",
               "up": "yesopen/take-upscaled", "film": "yesopen/take-48fps", "ace": "yesopen/music"}

# node colours by role: (colour, background)
ROLE = {"input": ("#232", "#353"), "model": ("#223", "#335"), "output": ("#322", "#533"), "setting": ("#323", "#535")}
MAX_STAGE_W = 1900             # a wider stage wraps its node columns into a second band


def swap_models(obj):
    """Replace the template's model names by the variants on the disk, everywhere (widgets, named widgets, subgraphs).
    The `models` download hints of a replaced file are dropped: they would make the frontend ask for the missing one."""
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i] = swap_models(v)
    elif isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "models" and isinstance(v, list):
                obj[k] = [m for m in v if not (isinstance(m, dict) and m.get("name") in MODELS)]
            else:
                obj[k] = swap_models(v)
    elif isinstance(obj, str):
        return MODELS.get(obj, obj)
    return obj


GAP_X, GAP_Y = 90, 50          # between node columns / rows inside a stage
PAD = 50                       # group padding
COL_GAP = 260                  # between stage columns
ROW_GAP = 380                  # between rows (room for the row group's title)
HEADER_H = 160                 # a stage's own note above its flow
COLLAPSED = (330, 46)
MUTE = 2                       # ComfyUI node mode "never": skipped by Run
MUTED = {"h3"}                 # stages Run skips: MiniMax H3 needs the vendor's written consent

# (key, template file or None, title, note, colour, row, column); row 0 = computer, 1 = main track, 2 = alternatives
STAGES = [
    ("s0", None, "0 · Start", "new_project.py <slug> --title '<end-card line>' -> project.json, lines.json, script.md.\n"
     "Engine: gpu (default) or higgsfield.", "#666", 0, 0),
    ("s1", None, "1 · Referencja", "capture-reference <link> reference/private (Ego Browser), contact_sheet.py.\n"
     "Write analysis.md in your own words: mechanics only, never the reference's lines. Gate 1.", "#666", 0, 1),
    ("s2", None, "2 · Scenariusz  ->  Gate 2: Twoje TAK", "script.md + lines.json: line table, cast, START->ACTION->END->HOLD->NEXT per shot, "
     "claims table (product copy only), cost.\nNothing paid before an explicit yes to the script. "
     "gpu_batches.py estimate prints the GPU minutes.", "#8a5a1e", 0, 2),
    ("s5", None, "5 · Montaż", "make_edl.py -> assemble.py: scripted ffmpeg 8.x (libx264), Pillow for all text, Manrope.\n"
     "cuts.json per shot, banners, captions, end card, optional music on the beat. Gate 5.", "#666", 0, 3),
    ("s6", None, "6 · Formaty i QA", "assemble.py --format 9:16 --crop-safe, crop_formats.py (4:5, 1:1), 16:9; qa_report.py --whisper.\n"
     "-14 LUFS, true peak <= -1 dBTP, Whisper match about 1.0. Gate 6.", "#666", 0, 4),
    ("s7", None, "7 · Dostawa  ·  8 · Podsumowanie", "encode_variants.py: share (25 MiB), web (15 MB), poster. Links to local files first.\n"
     "Then: 'Po produkcji' in script.md, reusable cast to assets/, retire the GPU (delete the machine, keep the disk). Gate 7.", "#666", 0, 5),

    ("cfg", SETTINGS, "USTAWIENIA SKECZU (wspólne)",
     "Jedno miejsce na rozmiar (9:16), czas i seed. Połączone z ujęciami LTX-2.3, LTX-2.5, MiniMax H3 i upscalem.\n"
     "Zmień tu, nie w etapach. Still (Z-Image) ma własny rozmiar 1088x1920 w podgrafie.", "#7a5a9a", 1, -1),
    ("z", "image_z_image_turbo_int8", "FAZA 3 · Still postaci (Z-Image Turbo)",
     "Cast stills, 1088x1920. Open the prompt with the framing: 'Vertical smartphone photo, medium shot from mid-thigh up, eye level'.\n"
     "OUT: still -> pose edit, the three takes. CLI: gpu_batches.py stills -> gpu.py batch stills/batch.json (template: still). Gate 3.",
     "#3f789e", 1, 0),
    ("tts", "audio-chatterbox_tts_multilingual", "FAZA 4a · Kwestia (Chatterbox Multilingual)",
     "Record every line twice, then fit_lines.py checks it word by word. Always set the language (Polish (pl), English (en)).\n"
     "OUT: the line -> the talking take. Listen to the key lines: ASR is not voice approval. CLI: gpu_batches.py voice -> fit_lines.py.",
     "#4f8a4f", 1, 1),
    ("ltx23", "video_ltx2_3_ia2v", "FAZA 4b · Mówiąca postać, lip sync (LTX-2.3 audio->wideo)",
     "IN: still (Z-Image) + line (Chatterbox) -> a lip-synced take, 704x1280, 24 fps. The prompt must say: framing stays the same, "
     "no zoom, no push-in.\nCLI: gpu_batches.py takes -> gpu.py batch takes/batch.json (template: talk). Gate 4.", "#b58b2a", 1, 2),
    ("up", "utility_seedvr2_3b_int8_upscale_video", "FAZA 4d · Upscale (SeedVR2 3B)",
     "IN: the take. 704x1280 -> 1056x1920, about 63 s for a 4.4 s take. OUT: -> interpolation. CLI template: upscale.", "#b06634", 1, 3),
    ("film", "utility_video_frame_interpolation", "FAZA 4d · Interpolacja klatek (FILM)",
     "IN: the upscaled take. 24 -> 48 fps when the motion judders. CLI template: interpolate.", "#b06634", 1, 4),

    ("qwen", "image_qwen_image_edit_2511_int8", "ALT · Wariant pozy / rekwizytu (Qwen-Image-Edit 2511)",
     "IN: the still. Same person, another pose or prop; fast=true keeps face, clothes and set. Phones always show their back to the camera.\n"
     "CLI: gpu.py run still-edit -s image=... -s prompt=...", "#3f789e", 2, 0),
    ("dlg", "audio-chatterbox_tts_dialog", "ALT · Cała rozmowa (Chatterbox, dwa głosy)",
     "Whole English conversation plus one track per speaker (SPEAKER A: ...). CLI template: tts-dialog.\n"
     "AudioCrop was removed: send voice samples already trimmed.", "#4f8a4f", 2, 3),
    ("ltx25", "video_ltx2_5_i2v", "ALT · Cichy ruch / B-roll (LTX-2.5 obraz->wideo)",
     "IN: the Qwen-edited still. Silent reactions and B-roll, with room sound. Needs the gated Hugging Face licence of Lightricks/LTX-2.5.\n"
     "CLI template: action (also action-t2v, action-flf).", "#b58b2a", 2, 1),
    ("h3", "video_minimax_h3_i2v", "ALT · MiniMax H3 (tylko za zgodą MiniMax)",
     "IN: the still. Variant B: needs MiniMax's written consent (licence excludes EU, UK, US and South Korea) and a "
     "machine-generated label on publishing.\nCLI template: h3-i2v / h3-talk; gpu_batches.py takes --model h3.", "#9a6b1a", 2, 2),
    ("ace", "audio_ace_step1_5_xl_turbo", "FAZA 4c · Podkład muzyczny (ACE-Step 1.5 XL Turbo)",
     "Instrumental bed, at least 10 s longer than the edit. music.py puts a downbeat on the cut to the end card and ducks 12 dB "
     "under every line.\nCLI: gpu.py run music -s tags=... -s seconds=90 -s bpm=100.", "#a1309b", 2, 4),
]

# (source stage, source node, source slot, target stage, target node, target slot): the main track's data flow
LINKS = [
    (("z", "Text to Image (Z-Image-Turbo)", 0), ("qwen", "Image Edit (Qwen-Image 2511 Int8)", 0)),
    (("z", "Text to Image (Z-Image-Turbo)", 0), ("ltx23", "Video Generation (LTX-2.3)", 0)),
    (("qwen", "Image Edit (Qwen-Image 2511 Int8)", 0), ("ltx25", "Image to Video (LTX-2.5)", 0)),     # b-roll from the edited still
    (("z", "Text to Image (Z-Image-Turbo)", 0), ("h3", "Image to Video (MiniMax H3)", 0)),
    (("tts", "FL_ChatterboxMultilingualTTS", 0), ("ltx23", "Video Generation (LTX-2.3)", 1)),
    (("ltx23", "Video Generation (LTX-2.3)", 0), ("up", "Upscale Video (SeedVR2 3B Int8)", 0)),
    (("up", "Upscale Video (SeedVR2 3B Int8)", 0), ("film", "Frame Interpolation", 0)),
    # the shared settings panel (a target slot may be given by input name)
    (("cfg", "Szerokość", 0), ("ltx23", "Video Generation (LTX-2.3)", "value_1")),
    (("cfg", "Szerokość", 0), ("ltx25", "Image to Video (LTX-2.5)", "value_3")),
    (("cfg", "Szerokość", 0), ("h3", "Image to Video (MiniMax H3)", "width")),
    (("cfg", "Wysokość", 0), ("ltx23", "Video Generation (LTX-2.3)", "value_2")),
    (("cfg", "Wysokość", 0), ("ltx25", "Image to Video (LTX-2.5)", "value_4")),
    (("cfg", "Wysokość", 0), ("h3", "Image to Video (MiniMax H3)", "height")),
    (("cfg", "Czas (s)", 0), ("ltx23", "Video Generation (LTX-2.3)", "value_4")),
    (("cfg", "Czas (s)", 0), ("h3", "Image to Video (MiniMax H3)", "value_1")),
    (("cfg", "Seed", 0), ("ltx23", "Video Generation (LTX-2.3)", "noise_seed")),
    (("cfg", "Seed", 0), ("up", "Upscale Video (SeedVR2 3B Int8)", "seed_1")),
]

TITLE = (
    "YESOPEN SKIT PIPELINE  ·  silnik GPU\n\n"
    "Górny rząd: kroki na komputerze (przed GPU po lewej, po GPU po prawej). Środek: TOR GŁÓWNY, połączony liniami: "
    "still -> kwestia -> ujęcie z lip syncem -> upscale -> interpolacja. Dolny rząd: reszta GPU, też podpięta: "
    "wariant pozy (Qwen) -> ciche ujęcie LTX-2.5, rozmowa dwóch głosów, muzyka.\n"
    "Jeden 'Run' robi cały pipeline GPU (kroki na komputerze, górny rząd, to opisy). Wyciszony jest tylko MiniMax H3: "
    "wymaga pisemnej zgody MiniMax; włączysz go zaznaczając jego węzły i Ctrl+M. "
    "Wskaźnik u góry mówi, czy ktoś już generuje. "
    "Wejścia (Load Image/Audio) wskazują pliki z dysku; wybierz własne. Zwinięte notatki 'Model links' rozwiń kliknięciem.\n"
    "Podglądy: każdy etap kończy się węzłem Save (obraz, dźwięk, wideo), który pokazuje wynik w kanwie."
)


def set_widgets(widgets, **at):
    """widgets[index] = value for the pairs given as w<index>=value."""
    for k, v in at.items():
        widgets[int(k[1:])] = v


def apply_subgraph_defaults(key, sg):
    """Defaults that live inside a subgraph (promoted widgets read them): prompts and sizes of the skit."""
    inner = {n["id"]: n for n in sg.get("nodes", [])}
    if key == "z":
        inner[27]["widgets_values"][0] = STILL
        inner[13]["widgets_values"][:2] = [1088, 1920]
    elif key == "qwen":
        inner[151]["widgets_values"][0] = EDIT
    elif key == "ltx23":
        inner[319]["widgets_values"][0] = TALK
        set_widgets(inner[330]["widgets_values"], w0=WIDTH)
        set_widgets(inner[324]["widgets_values"], w0=HEIGHT)
        set_widgets(inner[331]["widgets_values"], w0=SECONDS)
    elif key == "ltx25":
        inner[376]["widgets_values"][0] = ACTION
        set_widgets(inner[372]["widgets_values"], w0=WIDTH)
        set_widgets(inner[360]["widgets_values"], w0=HEIGHT)


def apply_node_defaults(key, n):
    """Defaults in the widgets of a stage's own nodes (a subgraph node keeps its promoted widgets in widgets_values)."""
    w = n.get("widgets_values")
    if n["type"] == "FL_ChatterboxMultilingualTTS":
        w[0], w[1] = LINE, "Polish (pl)"
    elif n["type"] == "FL_ChatterboxDialogTTS":
        w[0] = DIALOG
    elif key == "ltx23" and w and len(w) > 7 and isinstance(w[0], str):    # prompt, enhance, width, height, start, seconds, fps, seed
        set_widgets(w, w0=TALK, w2=WIDTH, w3=HEIGHT, w5=SECONDS, w7=SEED)
    elif key == "ltx25" and w and len(w) > 5 and isinstance(w[0], str):    # prompt, enhance, seconds, width, height, seed
        set_widgets(w, w0=ACTION, w3=WIDTH, w4=HEIGHT, w5=SEED)
    elif key == "h3" and w and len(w) > 3 and isinstance(w[0], str):       # prompt, width, height, seconds
        set_widgets(w, w0=H3, w1=WIDTH, w2=HEIGHT, w3=SECONDS)


def drop_audiocrop(nodes, links):
    by_id = {n["id"]: n for n in nodes}
    for crop in [n for n in nodes if n["type"] == "AudioCrop"]:
        lin = next(link for link in links if link[3] == crop["id"])
        src = by_id[lin[1]]
        for out in [link for link in links if link[1] == crop["id"]]:
            out[1], out[2] = lin[1], lin[2]
            src["outputs"][lin[2]]["links"].append(out[0])
        src["outputs"][lin[2]]["links"].remove(lin[0])
        links.remove(lin)
        nodes.remove(crop)


def note(nid, x, y, w, h, text, color="#432", bgcolor="#653", collapsed=False):
    return {"id": nid, "type": "Note", "pos": [x, y], "size": [w, h], "flags": {"collapsed": True} if collapsed else {},
            "order": 0, "mode": 0, "inputs": [], "outputs": [], "properties": {}, "widgets_values": [text],
            "color": color, "bgcolor": bgcolor}


def size_of(node):
    if (node.get("flags") or {}).get("collapsed"):
        return COLLAPSED
    w, h = node.get("size") or [300, 100]
    return (w, max(h, 60))


def layout_stage(nodes, links, x0, y0):
    """Place a stage's nodes: columns by data-flow depth, notes collapsed in a row below. Returns (w, h)."""
    flow = [n for n in nodes if n["type"] not in NOTE_TYPES]
    notes = [n for n in nodes if n["type"] in NOTE_TYPES]
    ids = {n["id"] for n in flow}
    depth = {i: 0 for i in ids}
    for _ in range(len(ids)):                       # relax: depth = longest path from a source
        for _, o, _, t, _, _ in links:
            if o in ids and t in ids:
                depth[t] = max(depth[t], depth[o] + 1)
    columns = {}
    for n in sorted(flow, key=lambda n: n["pos"][1]):
        columns.setdefault(depth[n["id"]], []).append(n)
    x, band_y, band_h, flow_h, flow_w = x0, y0, 0, 0, 0
    for d in sorted(columns):
        col = columns[d]
        col_w = max(size_of(n)[0] for n in col)
        if x > x0 and x - x0 + col_w > MAX_STAGE_W:      # too wide: continue in a new band below
            band_y += band_h + GAP_Y * 2
            x, band_h = x0, 0
        y = band_y
        for n in col:
            n["pos"] = [x, y]
            y += size_of(n)[1] + GAP_Y
        band_h = max(band_h, y - band_y - GAP_Y)
        flow_h = band_y + band_h - y0
        x += col_w + GAP_X
        flow_w = max(flow_w, x - x0 - GAP_X)
    nx, ny = x0, y0 + flow_h + GAP_Y
    for n in notes:                                  # the long "Model links" notes: collapsed, one row
        n["flags"] = dict(n.get("flags") or {}, collapsed=True)
        n["pos"] = [nx, ny]
        nx += COLLAPSED[0] + 20
    w = max(flow_w, nx - x0 - 20)
    return w, flow_h + (GAP_Y + COLLAPSED[1] if notes else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ui", type=Path, default=DEFAULT_UI)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    nodes_all, links_out, subgraphs, seen_sg = [], [], [], set()
    next_id, next_link = 1000, 1                    # top-level ids above the subgraphs' inner ones (no remapping warnings)
    sg_names = {}

    # 1. load every template stage with global node and link ids
    def prim(kind, title, value):
        nonlocal next_id
        out = {"PrimitiveInt": "INT", "PrimitiveFloat": "FLOAT"}[kind]
        n = {"id": next_id, "type": kind, "pos": [0, 0], "size": [300, 110], "flags": {}, "order": 0, "mode": 0, "inputs": [],
             "outputs": [{"name": out, "type": out, "links": []}], "title": title,
             "properties": {"Node name for S&R": kind}, "widgets_values": [value, "fixed"] if kind == "PrimitiveInt" else [value],
             "_stage": "cfg", "_role": "setting"}
        next_id += 1
        return n

    for key, file, *_ in STAGES:
        if file == SETTINGS:
            nodes_all += [prim("PrimitiveInt", "Szerokość", WIDTH), prim("PrimitiveInt", "Wysokość", HEIGHT),
                          prim("PrimitiveFloat", "Czas (s)", SECONDS), prim("PrimitiveInt", "Seed", SEED)]
            continue
        if not file:
            continue
        wf = json.load(open(args.ui / f"{file}.json"))
        ns = copy.deepcopy(wf["nodes"])
        wf_links = copy.deepcopy(wf.get("links", []))
        drop_audiocrop(ns, wf_links)
        ns = [n for n in ns if n["type"] not in NOTE_TYPES + ("RecordAudio",)]     # template notes (model links, how-tos) are dropped
        swap_models(ns)
        for n in ns:
            if n["type"] in LOADERS and n.get("widgets_values"):
                n["widgets_values"][0] = INPUTS.get(n["widgets_values"][0], n["widgets_values"][0])
            if n["type"] in SAVE_SIZES:
                n["size"] = list(SAVE_SIZES[n["type"]])
        for sg in wf.get("definitions", {}).get("subgraphs", []):
            apply_subgraph_defaults(key, sg)
        for n in ns:
            apply_node_defaults(key, n)
        saves = [n for n in ns if n["type"].startswith("Save")]
        if saves and key in SAVE_PREFIX:
            saves[0]["widgets_values"][0] = SAVE_PREFIX[key]
        id_map = {}
        for n in ns:
            id_map[n["id"]] = next_id
            next_id += 1
        link_map = {}
        for link in wf_links:
            link_map[link[0]] = next_link
            next_link += 1
        for n in ns:
            n["id"] = id_map[n["id"]]
            n["_stage"] = key
            for i in n.get("inputs") or []:
                if i.get("link") is not None:
                    i["link"] = link_map[i["link"]]
            for o in n.get("outputs") or []:
                if o.get("links"):
                    o["links"] = [link_map[k] for k in o["links"]]
            nodes_all.append(n)
        for link in wf_links:
            links_out.append([link_map[link[0]], id_map[link[1]], link[2], id_map[link[3]], link[4], link[5]])
        for sg in wf.get("definitions", {}).get("subgraphs", []):
            sg_names[sg["id"]] = sg["name"]
            if sg["id"] not in seen_sg:
                seen_sg.add(sg["id"])
                swap_models(sg.get("nodes", []))
                subgraphs.append(sg)

    # 2. wire the stages together; a Load node that fed a rewired input is removed
    def find(stage, name):
        return next(n for n in nodes_all if n["_stage"] == stage and name in (n["type"], n.get("title"), sg_names.get(n["type"])))

    def connect(src, sslot, dst, dslot):
        nonlocal next_link
        if isinstance(dslot, str):
            dslot = next(i for i, x in enumerate(dst["inputs"]) if x["name"] == dslot)
        inp = dst["inputs"][dslot]
        old = inp.get("link")
        if old is not None:
            gone = next(l for l in links_out if l[0] == old)
            links_out.remove(gone)
            loader = next(n for n in nodes_all if n["id"] == gone[1])
            loader["outputs"][gone[2]]["links"].remove(old)
            if loader["type"] in REMOVABLE and not any(o.get("links") for o in loader["outputs"]):
                nodes_all.remove(loader)
        lid, next_link = next_link, next_link + 1
        inp["link"] = lid
        out = src["outputs"][sslot]
        out["links"] = (out.get("links") or []) + [lid]
        links_out.append([lid, src["id"], sslot, dst["id"], dslot, out["type"]])

    for (s_stage, s_node, s_slot), (d_stage, d_node, d_slot) in LINKS:
        connect(find(s_stage, s_node), s_slot, find(d_stage, d_node), d_slot)

    # 3. sizes of the grid: a column is as wide as its widest stage, a row as high as its highest
    rows = {0: [], 1: [], 2: []}
    measured = {}
    for key, file, title, text, color, row, col in STAGES:
        if file:
            ns = [n for n in nodes_all if n["_stage"] == key]
            w, h = layout_stage(ns, links_out, 0, 0)            # measure; placed for real below
        else:
            w, h = 720, 0
        stage_w = max(w, 760)
        box_h = PAD + HEADER_H + (40 + h if file else 0) + PAD
        measured[key] = (stage_w + 2 * PAD, box_h)
        rows[row].append(key)
    col_w = {}
    for key, _, _, _, _, row, col in STAGES:
        if row:
            col_w[col] = max(col_w.get(col, 0), measured[key][0])
    col_x, x = {}, 0
    for c in sorted(col_w):
        col_x[c] = x
        x += col_w[c] + COL_GAP
    total_w = x - COL_GAP
    row_h = {r: max(measured[k][1] for k in ks) for r, ks in rows.items()}
    row_y = {0: 0}
    row_y[1] = row_y[0] + row_h[0] + ROW_GAP
    row_y[2] = row_y[1] + row_h[1] + ROW_GAP

    # 4. place stages, notes and groups
    notes_out, stage_groups = [], []
    local_left = [s for s in STAGES if s[5] == 0 and s[0] in ("s0", "s1", "s2")]
    local_right = [s for s in STAGES if s[5] == 0 and s[0] in ("s5", "s6", "s7")]
    local_x = {}
    for i, s in enumerate(local_left):
        local_x[s[0]] = i * (measured[s[0]][0] + COL_GAP // 2)
    for i, s in enumerate(reversed(local_right)):
        local_x[s[0]] = total_w - (i + 1) * measured[s[0]][0] - i * (COL_GAP // 2)
    for key, file, title, text, color, row, col in STAGES:
        sx = local_x[key] if row == 0 else col_x[col]
        sy = row_y[row]
        bw, bh = measured[key]
        notes_out.append(note(next_id, sx + PAD, sy + PAD, bw - 2 * PAD, HEADER_H, text, "#432", "#653"))
        next_id += 1
        if file:
            layout_stage([n for n in nodes_all if n["_stage"] == key], links_out, sx + PAD, sy + PAD + HEADER_H + 40)
            if key in MUTED:                                         # skipped by Run
                for n in nodes_all:
                    if n["_stage"] == key and n["type"] not in NOTE_TYPES:
                        n["mode"] = MUTE
        stage_groups.append({"title": title, "bounding": [sx, sy, bw, bh], "color": color, "font_size": 30, "flags": {}})

    row_titles = {
        "left": ("KOMPUTER  ·  przed GPU", "#444"), "right": ("KOMPUTER  ·  po GPU (bez GPU)", "#444"),
        1: ("TOR GŁÓWNY  ·  GPU  ·  połączony: still -> kwestia -> ujęcie -> upscale -> interpolacja", "#3f789e"),
        2: ("POZOSTAŁE ETAPY GPU  ·  też w jednym Run (poza MiniMax H3, wyciszonym)", "#7a5a9a"),
    }
    groups_out, gid = [], 1
    lg = [g for g in stage_groups if g["bounding"][1] == row_y[0]]
    lg_left = [g for g in lg if g["bounding"][0] < total_w / 2]
    lg_right = [g for g in lg if g["bounding"][0] >= total_w / 2]
    for sel, k in ((lg_left, "left"), (lg_right, "right")):
        x0 = min(g["bounding"][0] for g in sel) - 40
        x1 = max(g["bounding"][0] + g["bounding"][2] for g in sel) + 40
        groups_out.append({"id": gid, "title": row_titles[k][0], "bounding": [x0, -140, x1 - x0, row_h[0] + 180],
                           "color": row_titles[k][1], "font_size": 54, "flags": {}})
        gid += 1
    for r in (1, 2):
        groups_out.append({"id": gid, "title": row_titles[r][0], "bounding": [-40, row_y[r] - 140, total_w + 80, row_h[r] + 180],
                           "color": row_titles[r][1], "font_size": 54, "flags": {}})
        gid += 1
    for g in stage_groups:
        g["id"] = gid
        gid += 1
        groups_out.append(g)

    sub_types = set(sg_names)
    for n in nodes_all:
        role = (n.pop("_role", None) or ("input" if n["type"] in LOADERS else "output" if n["type"].startswith("Save")
                else "model" if n["type"] in sub_types else None))
        if role and not n.get("color"):
            n["color"], n["bgcolor"] = ROLE[role]

    title_note = note(next_id, 0, -640, min(total_w, 2200), 330, TITLE, "#332", "#553")
    next_id += 1
    nodes_final = [title_note] + notes_out + nodes_all
    for n in nodes_final:
        n.pop("_stage", None)

    scale = 0.3
    out = {
        "id": "yesopen-skit-pipeline", "revision": 0, "last_node_id": next_id, "last_link_id": next_link,
        "nodes": nodes_final, "links": links_out, "groups": groups_out, "config": {},
        "extra": {"ds": {"scale": scale, "offset": [200, 700]}},
        "version": 0.4, "definitions": {"subgraphs": subgraphs},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{args.out}: nodes {len(nodes_final)}, links {len(links_out)}, groups {len(groups_out)}, "
          f"subgraphs {len(subgraphs)}, canvas {total_w} x {row_y[2] + row_h[2]}")


if __name__ == "__main__":
    main()
