"""ffmpeg/ffprobe helpers shared by the skit scripts: probing, the loudness envelope,
speech boundaries, the per-format picture filter and caption chunking."""
import json
import pathlib
import re
import subprocess

FF = ["ffmpeg", "-v", "error", "-y"]
HOP = 0.01  # envelope resolution: one value per 10 ms


def run(args):
    subprocess.run(FF + [str(a) for a in args], check=True)


def probe_size(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height", "-of", "csv=p=0", str(path)]).decode().strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def probe_duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]).decode().strip())


def count_frames(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                                   "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(path)])
    return int(out.decode().strip().split(",")[0])


def streams(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,bit_rate"
                                   ":format=duration,size,bit_rate", "-of", "json", str(path)])
    return json.loads(out)


def loudness(path):
    """Integrated loudness (LUFS), loudness range and true peak (dBTP) from ffmpeg's ebur128."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]

    def grab(label):
        m = re.search(label + r":\s+(-?[\d.]+|-inf)", summary)
        return float(m.group(1)) if m and m.group(1) != "-inf" else None

    return {"integrated_lufs": grab("I"), "lra_lu": grab("LRA"), "true_peak_dbtp": grab("Peak")}


def max_volume(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = re.search(r"mean_volume:\s+(-?[\d.]+) dB", err)
    peak = re.search(r"max_volume:\s+(-?[\d.]+) dB", err)
    return {"mean_db": float(mean.group(1)) if mean else None, "max_db": float(peak.group(1)) if peak else None}


def envelope(path):
    """Loudness of a file's audio in dB, one value per 10 ms (16 kHz mono, 160-sample RMS windows)."""
    import numpy as np
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                                   "-f", "s16le", "-"])
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    n = len(a) // 160
    return 20 * np.log10(np.sqrt((a[: n * 160].reshape(n, 160) ** 2).mean(axis=1)) + 1e-9)


def refine(env, s, e, thr=-26.0, gap=0.12, reach=0.8):
    """Whisper's word times can be off by a few hundred ms. Walk outwards from [s, e] while the
    envelope stays above `thr` dB (allowing quiet dips shorter than `gap` s, at most `reach` s)
    and return where the speech really starts and ends."""
    def loud(t):
        i = int(round(t / HOP))
        return 0 <= i < len(env) and env[i] > thr

    onset, t, quiet = s, s, 0.0
    while t > max(0.0, s - reach):
        t -= HOP
        if loud(t):
            onset, quiet = t, 0.0
        else:
            quiet += HOP
            if quiet >= gap:
                break
    offset, t, quiet = e, e, 0.0
    while t < e + reach:
        t += HOP
        if loud(t):
            offset, quiet = t + HOP, 0.0
        else:
            quiet += HOP
            if quiet >= gap:
                break
    return round(onset, 2), round(offset, 2)


def crop_filter(sw, sh, W, H, zoom=1.0, cx=0.5, cy=0.4):
    """Crop a sw x sh picture to W:H, zoom in around (cx, cy) (fractions of the source) and scale to W x H."""
    target = W / H
    bw, bh = (sh * target, sh) if sw / sh > target else (sw, sw / target)
    cw, ch = bw / zoom, bh / zoom
    x = min(max(cx * sw - cw / 2, 0), sw - cw)
    y = min(max(cy * sh - ch / 2, 0), sh - ch)
    return f"crop={int(cw) // 2 * 2}:{int(ch) // 2 * 2}:{int(x)}:{int(y)},scale={W}:{H}:flags=lanczos"


def video_filter(src, layout, zoom=1.0, cx=0.5, cy=0.4, fps=30):
    """The -vf graph that turns one source clip into the format's frame.

    layout: brand.get_format(...). "crop" formats crop the 9:16 take to the frame;
    "pillarbox" (16:9) puts the whole 9:16 picture in the middle over a blurred copy.
    """
    sw, sh = probe_size(src)
    W, H = layout["size"]
    if layout["fit"] == "pillarbox":
        fw = round(H * 9 / 16 / 2) * 2
        fg = crop_filter(sw, sh, fw, H, zoom, cx, cy)
        return (f"split=2[bgsrc][fgsrc];[bgsrc]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"gblur=sigma=40,eq=brightness=-0.06:saturation=0.85[bg];[fgsrc]{fg}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={fps}:start_time=0")
    return crop_filter(sw, sh, W, H, zoom, cx, cy) + f",setsar=1,fps={fps}:start_time=0"


def chunks_of(words, max_words=3, max_chars=18, gap=0.35, tail=0.12, min_dur=0.35, language="en"):
    """Group caption words into on-screen chunks of up to `max_words` words / `max_chars` characters.
    A chunk also ends after punctuation or a pause longer than `gap`. Each chunk stays up `tail` s
    after its last word, at least `min_dur` s, and never past the next chunk's start."""
    from languages import language_code
    separator = '' if language_code(language) in {'zh', 'ja'} else ' '
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or len(separator.join(x["w"] for x in cur + [w])) > max_chars
                    or cur[-1]["w"][-1:] in ".?!,…。？！،؟" or w["s"] - cur[-1]["e"] > gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    out = []
    for i, c in enumerate(chunks):
        start = c[0]["s"]
        end = c[-1]["e"] + tail
        if i + 1 < len(chunks):
            end = min(max(end, start + min_dur), chunks[i + 1][0]["s"])
        out.append({"text": separator.join(x["w"] for x in c), "s": start, "e": end})
    return out


def find_project(path):
    """The project folder: the given folder, or the first parent that has project.json."""
    p = pathlib.Path(path).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "project.json").exists():
            return candidate
    raise SystemExit(f"no project.json in {p} or its parents (create one with new_project.py)")


def load_project(project):
    return json.loads((pathlib.Path(project) / "project.json").read_text())
