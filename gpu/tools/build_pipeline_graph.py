#!/usr/bin/env python3
"""Build the whole skit pipeline as one ComfyUI graph from the official UI workflows (gpu/workflows/ui).

    python3 gpu/tools/build_pipeline_graph.py [--ui DIR] [--out FILE]

Layout (graph_layout.py does the work):
- The GPU stages stand on a grid that the annealer picks for the shortest, least bent wiring of all the links between
  them (each pair weighted by its number of links); the steps on the user's computer are a note on each side. One "Run"
  runs every stage except MiniMax H3 (muted, mode 2: it needs MiniMax's written consent).
- Inside a stage, and inside every subgraph, the nodes stand in data-flow columns, each level with the node feeding it
  when there is room; no node covers a link.
- Links run orthogonally (render mode "Straight", reroutes only where the frontend's own corner would miss the lane):
  one lane per source, links of different sources never overlap, lanes ordered for the fewest crossings.
- Node boxes and socket rows come from comfy_geometry.json, measured in the browser with measure_geometry.js; measure
  again after changing node sizes, templates or the theme (gpu/server/live_refresh/web/theme.js).

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

from graph_layout import (TITLE_H, CHANNEL_DY, LANE_DX, LANE_X0, Geometry, build_reroutes, drawn_pieces, lane_items, lane_paths,
                          layout_block, overlaps, place_stages, simplify)

HERE = Path(__file__).resolve().parent
DEFAULT_UI = HERE.parent / "workflows" / "ui"
DEFAULT_OUT = HERE.parent / "workflows" / "pipeline" / "yesopen-skit-pipeline.json"
# node boxes and socket rows as the ComfyUI frontend draws them, measured in the browser (see graph_layout.Geometry)
GEOMETRY = HERE / "comfy_geometry.json"

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
SAVE_SIZES = {"SaveImage": (290, 500), "SaveImageAdvanced": (290, 500), "SaveVideo": (290, 560)}   # portrait 9:16 previews
REMOVABLE = LOADERS + ("ResolutionSelector",)     # source nodes that vanish when their last link is rewired
SETTINGS = "__settings__"                         # the stage that holds the shared skit settings (no template file)
SETTINGS_STAGE = "cfg"
MIX = "__mix__"                                   # the preview of a take with the music (core nodes only, no template file)
# stages made of the YesOpen nodes (gpu/server/yesopen_pipeline) and core nodes, no template file
PROJECT_STAGE, FIT_STAGE, EDIT_STAGE, FORMATS_STAGE, DELIVER_STAGE = "__project__", "__fit__", "__edit__", "__formats__", "__deliver__"
BUILT = {MIX, PROJECT_STAGE, FIT_STAGE, EDIT_STAGE, FORMATS_STAGE, DELIVER_STAGE}
DEMO_PROJECT = "gym-breakup-gpu"                  # examples/gym-breakup-gpu, pushed to /work on the server

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
# One Dark (VS Code), as in gpu/server/live_refresh/web/theme.js
OD = {"bg": "#282c34", "bg_dark": "#21252b", "bg_light": "#2c313a", "line": "#3e4451", "comment": "#5c6370",
      "red": "#e06c75", "orange": "#d19a66", "yellow": "#e5c07b", "green": "#98c379", "cyan": "#56b6c2", "blue": "#61afef",
      "purple": "#c678dd"}
# node colours by role: (title bar, body); the title bars are the One Dark accents darkened so light text reads on them
ROLE = {"input": ("#4a6b3a", OD["bg"]), "model": ("#2f5f8f", OD["bg"]), "output": ("#8f4a52", OD["bg"]),
        "setting": ("#6f4a8a", OD["bg"])}
NOTE_COLORS = ("#6e5f36", OD["bg_light"])          # stage notes
TITLE_COLORS = (OD["line"], OD["bg_dark"])         # the pipeline title
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


PAD = 50                       # group padding
COL_GAP = 160                  # least room between stage columns (more when the lanes need it)
ROW_GAP = 160                  # least room between rows (more when the channels need it)
GROUP_TITLE_H = 50             # a group's title strip
NOTE_MIN_W = 360               # a stage note is at least this wide when its text is longer
NOTE_MAX_W = 640               # ... and at most this wide (the computer steps), the title at most TITLE_MAX_W
TITLE_MAX_W = 1400
# a Note as the frontend draws it (Vue nodes): 10 px JetBrains Mono, 6 px a character, 14.5 px a line, 48 px of side
# padding, 58 px of frame and label around the text
NOTE_CHAR_W, NOTE_LINE_H, NOTE_PAD_X, NOTE_PAD_Y = 6, 14.5, 48, 58


def note_size(text, max_w, min_w=NOTE_MIN_W):
    """(width, height) of a Note that fits its text: as wide as its longest line within the limits, as high as its
    wrapped lines."""
    lines = text.split("\n")
    w = max(min(max(len(l) for l in lines) * NOTE_CHAR_W + NOTE_PAD_X + 6, max_w), min(min_w, max_w))
    per_line = max(1, int((w - NOTE_PAD_X) // NOTE_CHAR_W))
    rows = sum(max(1, -(-len(l) // per_line)) for l in lines)
    return round(w), round(NOTE_PAD_Y + NOTE_LINE_H * rows + 4)
MUTE = 2                       # ComfyUI node mode "never": skipped by Run
TOP_PAD = {"cfg": 100, "tts": 20}            # a stage whose first output would sit at the same height as a neighbour's input (links must not overlap)
MUTED = {"h3"}                 # stages Run skips: MiniMax H3 needs the vendor's written consent

# (key, template file or None, title, note, colour, row, column): columns are the stages in the order of the data flow,
# parallel alternatives sit under each other; column 0 and 5 are the steps on the user's computer
STAGES = [
    ("proj", PROJECT_STAGE, "0-2 · Projekt, referencja, scenariusz",
     "Projekt z /work (gpu.py push <projekt>). Referencję analizujesz na komputerze: nigdy nie trafia na serwer. "
     "Bramki 1-3 włączasz, gdy analiza, scenariusz (Twoje TAK) i obsada są gotowe. Kwestia: id z lines.json.",
     OD["comment"], 0, 0),
    ("tts", "audio-chatterbox_tts_multilingual", "4a · Kwestia (Chatterbox Multilingual)",
     "Tekst, głos, ekspresja i seed z projektu. Język ustaw jak w projekcie (węzeł kwestii to sprawdza). ASR to nie zgoda na głos: odsłuchaj.",
     OD["green"], 0, 1),
    ("z", "image_z_image_turbo_int8", "3 · Still postaci (Z-Image Turbo)",
     "Prompt = look postaci z lines.json. Kandydat ląduje w stills/; wybrany wpisz do lines.json (Bramka 3).",
     OD["blue"], 1, 1),
    ("cfg", SETTINGS, "USTAWIENIA SKECZU (wspólne)",
     "Rozmiar 9:16 i seed dla wariantów (LTX-2.5, H3, Qwen, upscale). Ujęcie z lip syncem bierze prompt, długość i seed z projektu.",
     OD["purple"], 2, 1),
    ("fit", FIT_STAGE, "4a · Dopasowanie kwestii i still ujęcia",
     "fit_lines.py tnie nagranie do słów scenariusza; gpu_batches.py takes daje prompt, długość i seed ujęcia. "
     "Still: wybrany z projektu, a gdy go brak, ten z Z-Image.", OD["green"], 1, 2),

    ("ltx23", "video_ltx2_3_ia2v", "4b · Mówiąca postać, lip sync (LTX-2.3)",
     "Still + dopasowana kwestia -> ujęcie z lip syncem, 704x1280, 24 fps; zapis do takes/<id>.video.mp4 i inspect_take.py.",
     OD["yellow"], 0, 2),
    ("h3", "video_minimax_h3_i2v", "4b · MiniMax H3 (wyciszony: tylko za zgodą MiniMax)",
     "Wymaga pisemnej zgody MiniMax (licencja wyklucza UE, UK, USA, Koreę Płd.) i oznaczenia 'machine-generated'. Włącz: Ctrl+M.",
     OD["red"], 1, 2),
    ("qwen", "image_qwen_image_edit_2511_int8", "3b · Wariant pozy / rekwizytu (Qwen-Image-Edit 2511)",
     "Ta sama osoba, inna poza lub rekwizyt; fast=true trzyma twarz, ubranie i plan. Telefon zawsze tyłem do kamery.", OD["blue"], 2, 2),

    ("up", "utility_seedvr2_3b_int8_upscale_video", "4d · Upscale (SeedVR2 3B)",
     "704x1280 -> 1056x1920, ok. 63 s na ujęcie 4,4 s.", OD["orange"], 0, 3),
    ("dlg", "audio-chatterbox_tts_dialog", "4a · Rozmowa dwóch głosów (Chatterbox)",
     "Cała rozmowa po angielsku i jedna ścieżka na mówcę (SPEAKER A: ...). Próbki głosów wgraj już przycięte.", OD["green"], 1, 3),
    ("ltx25", "video_ltx2_5_i2v", "4b · Cichy ruch / B-roll (LTX-2.5)",
     "Still po Qwenie -> ciche reakcje i B-roll z dźwiękiem pokoju. Wymaga licencji Lightricks/LTX-2.5 na Hugging Face.", OD["yellow"], 2, 3),

    ("film", "utility_video_frame_interpolation", "4d · Interpolacja klatek (FILM)",
     "24 -> 48 fps, gdy ruch szarpie.", OD["orange"], 0, 4),
    ("ace", "audio_ace_step1_5_xl_turbo", "4c · Podkład muzyczny (ACE-Step 1.5 XL Turbo)",
     "Podkład instrumentalny, co najmniej 10 s dłuższy niż montaż. music.py kładzie downbeat na cięciu do end card i przycisza 12 dB pod kwestiami.",
     OD["purple"], 1, 4),
    ("mix", MIX, "5a · Podgląd ujęcia z muzyką",
     "Ujęcie po interpolacji + podkład przycięty do długości ujęcia i ściszony o 12 dB. Tylko odsłuch: montaż robi assemble.py.",
     OD["cyan"], 0, 5),
    ("edit", EDIT_STAGE, "5 · Montaż (assemble.py)",
     "Gdy wszystkie ujęcia są i edit/cuts.json gotowy, włącz Bramkę 4: assety, EDL i render 9:16 (crop-safe).",
     OD["cyan"], 0, 6),
    ("formats", FORMATS_STAGE, "6 · Formaty i QA",
     "Bramka 5: 4:5 i 1:1 z mastera, 16:9 z ujęć, raport QA z Whisperem (-14 LUFS, true peak <= -1 dBTP, słowa ~1.0).",
     OD["blue"], 0, 7),
    ("deliver", DELIVER_STAGE, "7 · Dostawa",
     "Bramka 6: wersja do wysyłki (25 MiB), web (15 MB) i plakat w final/. Nic nie publikujemy bez Twojej prośby. "
     "Potem: 'Po produkcji' w script.md i skasowanie maszyny (dysk zostaje).", OD["green"], 0, 8),
]

# nodes the templates do not have, by stage: (title, type, inputs (name, type, is a widget), outputs (name, type), widgets, size).
# They are created after the template stages, so the template nodes keep their ids (comfy_geometry.json is keyed by id).
EXTRA_NODES = {
    "cfg": [("Rozmowa zamiast kwestii", "PrimitiveBoolean", [], [("BOOLEAN", "BOOLEAN")], [False], (230, 90))],
    "ltx23": [("Głos: kwestia / rozmowa", "ComfySwitchNode",
               [("on_false", "AUDIO", False), ("on_true", "AUDIO", False), ("switch", "BOOLEAN", True)],
               [("output", "AUDIO")], [False], (270, 130))],
    "mix": [
        ("Rozbij ujęcie", "GetVideoComponents", [("video", "VIDEO", False)],
         [("images", "IMAGE"), ("audio", "AUDIO"), ("fps", "FLOAT"), ("bit_depth", "COMBO"), ("color_space", "COMBO")], [], (300, 160)),
        ("Muzyka: długość ujęcia", "TrimAudioDuration", [("audio", "AUDIO", False), ("duration", "FLOAT", True)],
         [("AUDIO", "AUDIO")], [0.0, SECONDS], (300, 120)),
        ("Muzyka: -12 dB", "AudioAdjustVolume", [("audio", "AUDIO", False)], [("AUDIO", "AUDIO")], [-12], (300, 100)),
        ("Miks: ujęcie + muzyka", "AudioMerge", [("audio1", "AUDIO", False), ("audio2", "AUDIO", False)],
         [("AUDIO", "AUDIO")], ["add"], (300, 120)),
        ("Złóż wideo", "CreateVideo", [("images", "IMAGE", False), ("fps", "FLOAT", True), ("audio", "AUDIO", False)],
         [("VIDEO", "VIDEO")], [24.0, "auto", "sRGB"], (300, 150)),
        ("Podgląd z muzyką", "SaveVideo", [("video", "VIDEO", False)], [], ["yesopen/take-preview-music", "auto", "auto"], (290, 560)),
    ],
}

# the YesOpen nodes (gpu/server/yesopen_pipeline): the project, its gates and the steps on the skill's scripts; made
# after EXTRA_NODES, so the nodes measured before keep their ids
PIPELINE_NODES = {
    "proj": [
        ("Projekt", "YesOpenProject", [], [("project", "YESOPEN_PROJECT"), ("summary", "STRING")], [DEMO_PROJECT], (320, 120)),
        ("Bramka 1 · Referencja", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["1 · Referencja", False], (320, 120)),
        ("Bramka 2 · Scenariusz", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["2 · Scenariusz (Twoje TAK)", False], (320, 120)),
        ("Bramka 3 · Obsada", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["3 · Obsada (wybrane stille)", False], (320, 120)),
        ("Kwestia z projektu", "YesOpenLine", [("project", "YESOPEN_PROJECT", False)],
         [("text", "STRING"), ("voice", "AUDIO"), ("exaggeration", "FLOAT"), ("cfg_weight", "FLOAT"), ("seed", "INT"),
          ("look", "STRING"), ("who", "STRING"), ("line", "STRING")], ["l01", 0], (320, 240)),
    ],
    "fit": [
        ("Dopasuj kwestię", "YesOpenFitLine",
         [("project", "YESOPEN_PROJECT", False), ("line", "STRING", True), ("audio", "AUDIO", False), ("seed", "INT", True)],
         [("line_audio", "AUDIO"), ("take_prompt", "STRING"), ("seconds", "FLOAT"), ("take_seed", "INT"), ("still", "IMAGE"),
          ("has_still", "BOOLEAN"), ("report", "STRING")], ["l01", 100], (320, 230)),
        ("Still: wybrany / z Z-Image", "ComfySwitchNode",
         [("on_false", "IMAGE", False), ("on_true", "IMAGE", False), ("switch", "BOOLEAN", True)],
         [("output", "IMAGE")], [False], (270, 130)),
    ],
    "z": [("Still do projektu", "YesOpenSaveStill",
           [("project", "YESOPEN_PROJECT", False), ("who", "STRING", True), ("image", "IMAGE", False), ("seed", "INT", True)],
           [("path", "STRING")], ["char1", 0], (300, 140))],
    "ltx23": [("Ujęcie do projektu", "YesOpenSaveTake",
               [("project", "YESOPEN_PROJECT", False), ("line", "STRING", True), ("video", "VIDEO", False)],
               [("project", "YESOPEN_PROJECT"), ("report", "STRING")], ["l01"], (300, 120))],
    "ace": [("Muzyka do projektu", "YesOpenSaveMusic", [("project", "YESOPEN_PROJECT", False), ("audio", "AUDIO", False)],
             [("path", "STRING")], ["bed"], (300, 110))],
    "edit": [
        ("Bramka 4 · Ujęcia", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["4 · Ujęcia", False], (320, 120)),
        ("Assety montażu", "YesOpenBuildAssets", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("log", "STRING")], [], (300, 90)),
        ("EDL", "YesOpenMakeEDL", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT"), ("log", "STRING")],
         [], (300, 90)),
        ("Render 9:16", "YesOpenAssemble", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("video", "VIDEO"), ("log", "STRING")], ["9:16", True], (300, 140)),
        ("Podgląd 9:16", "SaveVideo", [("video", "VIDEO", False)], [], ["yesopen/final-9x16", "auto", "auto"], (290, 560)),
    ],
    "formats": [
        ("Bramka 5 · Montaż", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["5 · Montaż", False], (320, 120)),
        ("Formaty 4:5 i 1:1", "YesOpenCropFormats", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("log", "STRING")], [], (300, 90)),
        ("Render 16:9", "YesOpenAssemble", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("video", "VIDEO"), ("log", "STRING")], ["16:9", False], (300, 140)),
        ("Raport QA", "YesOpenQAReport", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("log", "STRING")], ["9:16", True], (300, 140)),
        ("Wynik QA", "PreviewAny", [("source", "*", False)], [("STRING", "STRING")], [], (420, 300)),
    ],
    "deliver": [
        ("Bramka 6 · Formaty i QA", "YesOpenGate", [("project", "YESOPEN_PROJECT", False)], [("project", "YESOPEN_PROJECT")],
         ["6 · Formaty i QA", False], (320, 120)),
        ("Wersje do wysyłki", "YesOpenEncodeVariants", [("project", "YESOPEN_PROJECT", False)],
         [("project", "YESOPEN_PROJECT"), ("log", "STRING")], [], (300, 90)),
        ("Pliki w final/", "PreviewAny", [("source", "*", False)], [("STRING", "STRING")], [], (420, 240)),
    ],
}

# (source stage, source node, source slot), (target stage, target node, target slot): the data flow
LINKS = [
    # the project and its gates
    (("proj", "Projekt", 0), ("proj", "Bramka 1 · Referencja", "project")),
    (("proj", "Bramka 1 · Referencja", 0), ("proj", "Bramka 2 · Scenariusz", "project")),
    (("proj", "Bramka 2 · Scenariusz", 0), ("proj", "Bramka 3 · Obsada", "project")),
    (("proj", "Bramka 2 · Scenariusz", 0), ("proj", "Kwestia z projektu", "project")),
    # the line into Chatterbox, the speaker's look into Z-Image, the candidate still into the project
    (("proj", "Kwestia z projektu", 0), ("tts", "FL_ChatterboxMultilingualTTS", "text")),
    (("proj", "Kwestia z projektu", 1), ("tts", "FL_ChatterboxMultilingualTTS", "audio_prompt")),
    (("proj", "Kwestia z projektu", 2), ("tts", "FL_ChatterboxMultilingualTTS", "exaggeration")),
    (("proj", "Kwestia z projektu", 3), ("tts", "FL_ChatterboxMultilingualTTS", "cfg_weight")),
    (("proj", "Kwestia z projektu", 4), ("tts", "FL_ChatterboxMultilingualTTS", "seed")),
    (("proj", "Kwestia z projektu", 5), ("z", "Text to Image (Z-Image-Turbo)", "text")),
    (("proj", "Bramka 2 · Scenariusz", 0), ("z", "Still do projektu", "project")),
    (("proj", "Kwestia z projektu", 6), ("z", "Still do projektu", "who")),
    (("proj", "Kwestia z projektu", 4), ("z", "Still do projektu", "seed")),
    (("z", "Text to Image (Z-Image-Turbo)", 0), ("z", "Still do projektu", "image")),
    # the recorded line is fitted; the take uses the fitted line, the project's prompt, length, seed and still
    (("proj", "Bramka 3 · Obsada", 0), ("fit", "Dopasuj kwestię", "project")),
    (("proj", "Kwestia z projektu", 7), ("fit", "Dopasuj kwestię", "line")),
    (("proj", "Kwestia z projektu", 4), ("fit", "Dopasuj kwestię", "seed")),
    (("tts", "FL_ChatterboxMultilingualTTS", 0), ("fit", "Dopasuj kwestię", "audio")),
    (("fit", "Dopasuj kwestię", 4), ("fit", "Still: wybrany / z Z-Image", "on_true")),
    (("z", "Text to Image (Z-Image-Turbo)", 0), ("fit", "Still: wybrany / z Z-Image", "on_false")),
    (("fit", "Dopasuj kwestię", 5), ("fit", "Still: wybrany / z Z-Image", "switch")),
    (("fit", "Still: wybrany / z Z-Image", 0), ("qwen", "Image Edit (Qwen-Image 2511 Int8)", 0)),
    (("fit", "Still: wybrany / z Z-Image", 0), ("ltx23", "Video Generation (LTX-2.3)", 0)),
    (("fit", "Still: wybrany / z Z-Image", 0), ("h3", "Image to Video (MiniMax H3)", 0)),
    (("fit", "Dopasuj kwestię", 1), ("ltx23", "Video Generation (LTX-2.3)", "value")),
    (("fit", "Dopasuj kwestię", 2), ("ltx23", "Video Generation (LTX-2.3)", "value_4")),
    (("fit", "Dopasuj kwestię", 3), ("ltx23", "Video Generation (LTX-2.3)", "noise_seed")),
    (("fit", "Dopasuj kwestię", 2), ("h3", "Image to Video (MiniMax H3)", "value_1")),
    (("qwen", "Image Edit (Qwen-Image 2511 Int8)", 0), ("ltx25", "Image to Video (LTX-2.5)", 0)),       # b-roll from the edited still
    # the talking take speaks the line, or the two-voice dialog when "Rozmowa zamiast kwestii" is on
    (("fit", "Dopasuj kwestię", 0), ("ltx23", "Głos: kwestia / rozmowa", "on_false")),
    (("dlg", "FL_ChatterboxDialogTTS", 0), ("ltx23", "Głos: kwestia / rozmowa", "on_true")),
    (("cfg", "Rozmowa zamiast kwestii", 0), ("ltx23", "Głos: kwestia / rozmowa", "switch")),
    (("ltx23", "Głos: kwestia / rozmowa", 0), ("ltx23", "Video Generation (LTX-2.3)", 1)),
    (("ltx23", "Video Generation (LTX-2.3)", 0), ("up", "Upscale Video (SeedVR2 3B Int8)", 0)),
    (("up", "Upscale Video (SeedVR2 3B Int8)", 0), ("film", "Frame Interpolation", 0)),
    # the preview with music: the finished take and the music bed, cut to the take and 12 dB down
    (("film", "Frame Interpolation", 0), ("mix", "Rozbij ujęcie", "video")),
    (("ace", "VAEDecodeAudio", 0), ("mix", "Muzyka: długość ujęcia", "audio")),
    (("fit", "Dopasuj kwestię", 2), ("mix", "Muzyka: długość ujęcia", "duration")),
    (("mix", "Muzyka: długość ujęcia", 0), ("mix", "Muzyka: -12 dB", "audio")),
    (("mix", "Rozbij ujęcie", 1), ("mix", "Miks: ujęcie + muzyka", "audio1")),
    (("mix", "Muzyka: -12 dB", 0), ("mix", "Miks: ujęcie + muzyka", "audio2")),
    (("mix", "Rozbij ujęcie", 0), ("mix", "Złóż wideo", "images")),
    (("mix", "Rozbij ujęcie", 2), ("mix", "Złóż wideo", "fps")),
    (("mix", "Miks: ujęcie + muzyka", 0), ("mix", "Złóż wideo", "audio")),
    (("mix", "Złóż wideo", 0), ("mix", "Podgląd z muzyką", "video")),
    # the shared settings panel (a target slot may be given by input name)
    (("cfg", "Szerokość", 0), ("ltx23", "Video Generation (LTX-2.3)", "value_1")),
    (("cfg", "Szerokość", 0), ("ltx25", "Image to Video (LTX-2.5)", "value_3")),
    (("cfg", "Szerokość", 0), ("h3", "Image to Video (MiniMax H3)", "width")),
    (("cfg", "Wysokość", 0), ("ltx23", "Video Generation (LTX-2.3)", "value_2")),
    (("cfg", "Wysokość", 0), ("ltx25", "Image to Video (LTX-2.5)", "value_4")),
    (("cfg", "Wysokość", 0), ("h3", "Image to Video (MiniMax H3)", "height")),
    (("cfg", "Seed", 0), ("ltx25", "Image to Video (LTX-2.5)", "noise_seed")),
    (("cfg", "Seed", 0), ("h3", "Image to Video (MiniMax H3)", "noise_seed")),
    (("cfg", "Seed", 0), ("qwen", "Image Edit (Qwen-Image 2511 Int8)", "seed")),
    (("cfg", "Seed", 0), ("up", "Upscale Video (SeedVR2 3B Int8)", "seed_1")),
    # the take and the music into the project
    (("proj", "Bramka 3 · Obsada", 0), ("ltx23", "Ujęcie do projektu", "project")),
    (("proj", "Kwestia z projektu", 7), ("ltx23", "Ujęcie do projektu", "line")),
    (("ltx23", "Video Generation (LTX-2.3)", 0), ("ltx23", "Ujęcie do projektu", "video")),
    (("proj", "Bramka 2 · Scenariusz", 0), ("ace", "Muzyka do projektu", "project")),
    (("ace", "VAEDecodeAudio", 0), ("ace", "Muzyka do projektu", "audio")),
    # the edit, the formats, QA and delivery: the skill's scripts on the project, each behind its gate
    (("ltx23", "Ujęcie do projektu", 0), ("edit", "Bramka 4 · Ujęcia", "project")),
    (("edit", "Bramka 4 · Ujęcia", 0), ("edit", "Assety montażu", "project")),
    (("edit", "Assety montażu", 0), ("edit", "EDL", "project")),
    (("edit", "EDL", 0), ("edit", "Render 9:16", "project")),
    (("edit", "Render 9:16", 1), ("edit", "Podgląd 9:16", "video")),
    (("edit", "Render 9:16", 0), ("formats", "Bramka 5 · Montaż", "project")),
    (("formats", "Bramka 5 · Montaż", 0), ("formats", "Formaty 4:5 i 1:1", "project")),
    (("formats", "Formaty 4:5 i 1:1", 0), ("formats", "Render 16:9", "project")),
    (("formats", "Render 16:9", 0), ("formats", "Raport QA", "project")),
    (("formats", "Raport QA", 1), ("formats", "Wynik QA", "source")),
    (("formats", "Raport QA", 0), ("deliver", "Bramka 6 · Formaty i QA", "project")),
    (("deliver", "Bramka 6 · Formaty i QA", 0), ("deliver", "Wersje do wysyłki", "project")),
    (("deliver", "Wersje do wysyłki", 1), ("deliver", "Pliki w final/", "source")),
]

TITLE = (
    "YESOPEN SKIT PIPELINE  ·  silnik GPU\n\n"
    "Cały pipeline, od projektu do dostawy. Wybierz projekt z /work i id kwestii; jeden Run nagrywa kwestię, dopasowuje "
    "ją (fit_lines), filmuje ujęcie z lip syncem i zapisuje je w projekcie. Kroki po bramkach (montaż, formaty, QA, "
    "dostawa) robią skrypty skilla w kontenerze edytora; bramka przepuszcza dalej dopiero po włączeniu 'approved'. "
    "Obok: MiniMax H3 (wyciszony), Qwen -> B-roll LTX-2.5, rozmowa dwóch głosów ('Rozmowa zamiast kwestii'), muzyka, "
    "podgląd z muzyką. Wskaźnik u góry mówi, czy ktoś już generuje."
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


def optimise_subgraph(sg, data):
    """Lay out a subgraph's inside like a stage: its input node in the first column, its output node in the last, the
    nodes in data-flow columns, links routed with reroutes. The template's notes and groups inside it are dropped."""
    sg["nodes"] = [n for n in sg.get("nodes", []) if n["type"] not in NOTE_TYPES]
    sg["groups"] = []
    for n in sg["nodes"]:
        (n.get("flags") or {}).pop("collapsed", None)
    io = data.get("io", {}).get(sg["id"], {})
    pseudo = {}
    for nid, side, key in ((-10, "inputNode", "in"), (-20, "outputNode", "out")):
        b = sg[side]["bounding"]
        count = len(sg["inputs" if key == "in" else "outputs"])
        m = io.get(key) or {"w": b[2], "h": b[3], "slots": [24 + 20 * i for i in range(count)]}
        slots = [{}] * count
        pseudo[nid] = {"id": nid, "_io": True, "size": [m["w"], m["h"]], "_slots": m["slots"], "pos": [0, 0],
                       "inputs": slots if key == "out" else [], "outputs": slots if key == "in" else []}
    links = [(l["id"], l["origin_id"], l["origin_slot"], l["target_id"], l["target_slot"]) for l in sg.get("links", [])]
    geo = Geometry(data, sg["id"])
    _, _, paths = layout_block(sg["nodes"], links, geo, io_in=pseudo[-10], io_out=pseudo[-20])
    for nid, side in ((-10, "inputNode"), (-20, "outputNode")):
        p = pseudo[nid]
        sg[side]["bounding"] = [p["pos"][0], p["pos"][1], p["size"][0], p["size"][1]]
    nodes = {n["id"]: n for n in sg["nodes"]} | pseudo
    ends = {l[0]: ((nodes[l[1]]["pos"][0] + geo.size(nodes[l[1]])[0], nodes[l[1]]["pos"][1] + geo.out_y(nodes[l[1]], l[2])),
                   (nodes[l[3]]["pos"][0], nodes[l[3]]["pos"][1] + geo.in_y(nodes[l[3]], l[4])))
            for l in links if l[1] in nodes and l[3] in nodes}
    boxes = [(n["pos"][0], n["pos"][1] - (0 if n.get("_io") else TITLE_H), n["pos"][0] + geo.size(n)[0], n["pos"][1] + geo.size(n)[1])
             for n in nodes.values()]
    simplify(paths, ends, boxes)
    for l1, l2, a1, a2 in overlaps(drawn_pieces(paths, ends)):
        print(f"  overlap in {sg['name']}: link {l1} and link {l2} at {a1} / {a2}")
    reroutes, last = build_reroutes(paths)
    sg["reroutes"] = reroutes
    print(f"  subgraph {sg['name']}: nodes {len(sg['nodes'])}, links {len(links)}, reroutes {len(reroutes)}")
    for l in sg.get("links", []):
        l.pop("parentId", None)
        if l["id"] in last:
            l["parentId"] = last[l["id"]]


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
        n = {"id": next_id, "type": kind, "pos": [0, 0], "size": [230, 110], "flags": {}, "order": 0, "mode": 0, "inputs": [],
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
        if not file or file in BUILT:
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
            (n.get("flags") or {}).pop("collapsed", None)          # every node open: its sockets are where the links go
        for sg in wf.get("definitions", {}).get("subgraphs", []):
            apply_subgraph_defaults(key, sg)
        for n in ns:
            apply_node_defaults(key, n)
            if n["type"] == "SaveAudioMP3":              # deprecated in ComfyUI 0.35: the same MP3 V0 through SaveAudioAdvanced
                n["type"] = "SaveAudioAdvanced"
                n["properties"]["Node name for S&R"] = "SaveAudioAdvanced"
                n["widgets_values"] = [n["widgets_values"][0], "mp3", n["widgets_values"][1]]
                n["size"] = [300, 150]
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

    for key, specs in list(EXTRA_NODES.items()) + list(PIPELINE_NODES.items()):
        for title, kind, ins, outs, widgets, size in specs:
            nodes_all.append({"id": next_id, "type": kind, "pos": [0, 0], "size": list(size), "flags": {}, "order": 0, "mode": 0,
                              "inputs": [dict({"name": n, "type": t, "link": None}, **({"widget": {"name": n}} if w else {}))
                                         for n, t, w in ins],
                              "outputs": [{"name": n, "type": t, "links": []} for n, t in outs], "title": title,
                              "properties": {"Node name for S&R": kind}, "widgets_values": list(widgets), "_stage": key,
                              **({"_role": "setting"} if key == SETTINGS_STAGE else {})})
            next_id += 1

    # 2. wire the stages together; a Load node that fed a rewired input is removed
    def find(stage, name):
        return next(n for n in nodes_all if n["_stage"] == stage and name in (n["type"], n.get("title"), sg_names.get(n["type"])))

    def connect(src, sslot, dst, dslot):
        nonlocal next_link
        if isinstance(dslot, str):
            if not any(x["name"] == dslot for x in dst["inputs"]):       # a promoted widget the template did not expose as a socket
                d = next((i for sg in subgraphs if sg["id"] == dst["type"] for i in sg["inputs"] if i["name"] == dslot),
                         {"type": src["outputs"][sslot]["type"]})
                dst["inputs"].append({"name": dslot, "type": d["type"], "widget": {"name": dslot}, "link": None})
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

    # 2b. drop nodes whose outputs go nowhere (e.g. GetImageSize once the settings panel feeds the sizes)
    gone_any = True
    while gone_any:
        gone_any = False
        for n in list(nodes_all):
            outs = n.get("outputs") or []
            if not outs or n["type"] in sg_names or n["type"].startswith(("Save", "Preview")) or any(o.get("links") for o in outs):
                continue
            for i in n.get("inputs") or []:
                if i.get("link") is not None:
                    lk = next(l for l in links_out if l[0] == i["link"])
                    links_out.remove(lk)
                    origin = next(o for o in nodes_all if o["id"] == lk[1])
                    origin["outputs"][lk[2]]["links"].remove(lk[0])
            nodes_all.remove(n)
            gone_any = True

    # 3. the insides of the subgraphs
    data = json.load(open(GEOMETRY)) if GEOMETRY.exists() else {}
    for sg in subgraphs:
        optimise_subgraph(sg, data)

    # 4. every stage on its own, relative to its corner
    geo = Geometry(data, "root")
    stage_of = {n["id"]: n["_stage"] for n in nodes_all}
    by_id = {n["id"]: n for n in nodes_all}
    lks = [tuple(l[:5]) for l in links_out]
    cross = [l for l in lks if stage_of[l[1]] != stage_of[l[3]]]
    exports, imports = {(l[1], l[2]) for l in cross}, {(l[3], l[4]) for l in cross}
    inner, box, content_w, header, content_y = {}, {}, {}, {}, {}
    for key, file, title, text, *_ in STAGES:
        if file:
            w, h, paths = layout_block([n for n in nodes_all if n["_stage"] == key], lks, geo, exports, imports)
            if key == SETTINGS_STAGE:                    # a staircase: each setting's wire gets its own halfway line
                panel = sorted((n for n in nodes_all if n["_stage"] == key), key=lambda n: n["pos"][1])
                for i, n in enumerate(panel):
                    n["pos"][0] += 2 * LANE_DX * i
                w += 2 * LANE_DX * (len(panel) - 1)
            inner[key] = paths
            content_w[key] = w
            header[key] = note_size(text, max(w, NOTE_MIN_W))
            content_y[key] = GROUP_TITLE_H + TITLE_H + header[key][1] + 30          # the nodes start below the note
            box[key] = [max(w, header[key][0]) + 2 * PAD, content_y[key] + h + PAD]
        else:
            header[key] = note_size(text, NOTE_MAX_W)
            box[key] = [header[key][0] + 2 * PAD, GROUP_TITLE_H + TITLE_H + header[key][1] + PAD]

    # 5. the stages on the grid: the arrangement with the shortest, least bent wiring for all the links
    weights = {}
    for l in cross:
        k = (stage_of[l[1]], stage_of[l[3]])
        weights[k] = weights.get(k, 0) + 1
    gpu = [s[0] for s in STAGES if s[1]]
    cells, score = place_stages({s[0]: (s[6], s[5]) for s in STAGES if s[1]}, weights, {k: box[k] for k in gpu})
    last_col = max(c for c, _ in cells.values())

    # a stage moves down to put its main incoming link level with its source (same row, next column); when the target
    # sits lower already, the source moves down instead, unless it is aligned with its own source
    dy = {k: 0 for k in cells}
    aligned = set()
    for key in sorted(gpu, key=lambda k: cells[k][0]):
        votes = {}
        for l in cross:
            s, t = stage_of[l[1]], stage_of[l[3]]
            if t == key and cells[s][1] == cells[t][1] and cells[t][0] - cells[s][0] == 1:
                want = (dy[s] + by_id[l[1]]["pos"][1] + geo.out_y(by_id[l[1]], l[2])
                        - by_id[l[3]]["pos"][1] - geo.in_y(by_id[l[3]], l[4]))
                if -400 <= want <= 400 and want:
                    votes.setdefault((want, s), 0)
                    votes[(want, s)] += 1
        if votes:
            want, s = max(votes, key=lambda v: (votes[v], -abs(v[0])))
            if want > 0:
                dy[key] += want
                aligned.add(key)
            elif s not in aligned:
                dy[s] -= want
    for k in dy:
        if k in box:
            box[k][1] += dy[k]

    # corridors as wide as their lanes, row gaps as high as their channels
    lanes, chans = {}, {}
    for l in cross:
        (cs, rs), (ct, rt) = cells[stage_of[l[1]]], cells[stage_of[l[3]]]
        lanes.setdefault(cs, set()).add((l[1], l[2]))
        if ct - cs > 1:
            lanes.setdefault(ct - 1, set()).add((l[1], l[2], "h", rt))
            chans.setdefault(rt, set()).add((l[1], l[2]))
    # a stage that only sends is as wide as its column and its nodes stand at the right: its wires start at the corridor
    wired = {stage_of[l[1]] for l in cross} | {stage_of[l[3]] for l in cross}
    sends_only = {stage_of[l[1]] for l in cross} - {stage_of[l[3]] for l in cross}
    link_w = {}
    for k in wired:
        link_w[cells[k][0]] = max(link_w.get(cells[k][0], 0), box[k][0])
    for k in sends_only:
        box[k][0] = max(box[k][0], max(box[o][0] for o in cells if o in box and cells[o][0] == cells[k][0]))
    col_w, row_h = {}, {}
    for k, (c, r) in cells.items():
        col_w[c] = max(col_w.get(c, 0), box[k][0])
        row_h[r] = max(row_h.get(r, 0), box[k][1])
    col_x, x = {}, 0
    for c in sorted(col_w):
        col_x[c] = x
        x += col_w[c] + max(COL_GAP, 2 * LANE_X0 + LANE_DX * len(lanes.get(c, ())))
    total_w = x
    row_y, y = {}, 0
    for r in sorted(row_h):
        y += max(ROW_GAP, 80 + CHANNEL_DY * len(chans.get(r, ()))) if r else 0
        row_y[r] = y
        y += row_h[r]
    total_h = y

    # 6. place the stages, their notes and groups
    notes_out, stage_groups, paths = [], [], {}
    for key, file, title, text, color, *_ in STAGES:
        c, r = cells[key]
        bw, bh = box[key]
        sx, sy = col_x[c], row_y[r]
        notes_out.append(note(next_id, sx + PAD, sy + GROUP_TITLE_H + TITLE_H, *header[key], text, *NOTE_COLORS))
        next_id += 1
        if file:
            ox, oy = sx + PAD, sy + content_y[key] + dy[key]
            if key in sends_only:                                    # its wires out start right at the corridor
                ox += bw - 2 * PAD - content_w[key]
            for n in nodes_all:
                if n["_stage"] == key:
                    n["pos"] = [n["pos"][0] + ox, n["pos"][1] + oy]
                    if key in MUTED:                                 # skipped by Run
                        n["mode"] = MUTE
            for lid, (src, pts) in inner[key].items():
                paths[lid] = (src, [(px + ox, py + oy) for px, py in pts])
        stage_groups.append({"title": title, "bounding": [sx, sy, bw, bh], "color": color, "font_size": 30, "flags": {}})

    # 7. the links between stages: one lane per source in the corridor next to it, channels above the rows
    specs, ends = [], {}
    for l in cross:
        o, t = by_id[l[1]], by_id[l[3]]
        yo, yi = o["pos"][1] + geo.out_y(o, l[2]), t["pos"][1] + geo.in_y(t, l[4])
        specs.append((l[0], (l[1], l[2]), yo, yi, cells[stage_of[l[1]]][0], cells[stage_of[l[3]]][0], cells[stage_of[l[3]]][1]))
    items, chan_y = lane_items(specs, lambda r, k: row_y[r] - 40 - CHANNEL_DY * k)
    for l in lks:
        o, t = by_id[l[1]], by_id[l[3]]
        ends[l[0]] = ((o["pos"][0] + geo.size(o)[0], o["pos"][1] + geo.out_y(o, l[2])), (t["pos"][0], t["pos"][1] + geo.in_y(t, l[4])))
    corridors = {c: (col_x[c] + col_w[c], col_x.get(c + 1, col_x[c] + col_w[c] + COL_GAP)) for c in col_x}
    paths.update(lane_paths(specs, items, chan_y, corridors, {k: (v[0][0], v[1][0]) for k, v in ends.items()}))
    boxes = [(n["pos"][0], n["pos"][1] - TITLE_H, n["pos"][0] + geo.size(n)[0], n["pos"][1] + geo.size(n)[1]) for n in nodes_all]
    boxes += [(n["pos"][0], n["pos"][1] - TITLE_H, n["pos"][0] + n["size"][0], n["pos"][1] + n["size"][1]) for n in notes_out]
    simplify(paths, ends, boxes)
    for l1, l2, a1, a2 in overlaps(drawn_pieces(paths, ends)):
        print(f"  overlap: link {l1} and link {l2} at {a1} / {a2}")
    reroutes, last = build_reroutes(paths)
    link_extensions = [{"id": lid, "parentId": rid} for lid, rid in sorted(last.items())]

    gpu_x0, gpu_x1 = col_x[1] - 60, col_x[last_col] + col_w[last_col] + 60
    groups_out = [{"id": 1, "title": "YESOPEN SKIT PIPELINE  ·  od projektu do dostawy",
                   "bounding": [gpu_x0, -120, gpu_x1 - gpu_x0, total_h + 180], "color": OD["line"], "font_size": 54, "flags": {}}]
    for g in stage_groups:
        g["id"] = len(groups_out) + 1
        groups_out.append(g)

    sub_types = set(sg_names)
    for n in nodes_all:
        role = (n.pop("_role", None) or ("input" if n["type"] in LOADERS else "output" if n["type"].startswith("Save")
                else "model" if n["type"] in sub_types else None))
        if role and not n.get("color"):
            n["color"], n["bgcolor"] = ROLE[role]

    tw, th = note_size(TITLE, min(gpu_x1 - gpu_x0, TITLE_MAX_W))
    title_note = note(next_id, gpu_x0, -120 - 40 - th, tw, th, TITLE, *TITLE_COLORS)
    next_id += 1
    nodes_final = [title_note] + notes_out + nodes_all
    for n in nodes_final:
        n.pop("_stage", None)

    out = {
        "id": "yesopen-skit-pipeline", "revision": 0, "last_node_id": next_id, "last_link_id": next_link,
        "nodes": nodes_final, "links": links_out, "groups": groups_out, "config": {},
        "extra": {"ds": {"scale": 0.25, "offset": [150, 560]}, "reroutes": reroutes, "linkExtensions": link_extensions},
        "version": 0.4, "definitions": {"subgraphs": subgraphs},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{args.out}: nodes {len(nodes_final)}, links {len(links_out)}, groups {len(groups_out)}, subgraphs {len(subgraphs)}, "
          f"reroutes {len(reroutes)}, canvas {round(total_w)} x {round(total_h)}")
    print("  grid (column, row): " + ", ".join(f"{k} {cells[k]}" for k in gpu) + f"  (score {score:.0f})")


if __name__ == "__main__":
    main()
