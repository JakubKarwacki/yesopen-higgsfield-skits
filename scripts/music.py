"""Music bed under the edit: find the track's beat grid, put a downbeat on the end card, duck the music under
speech, fade it in and out, and write the stem the final mix uses (edit/work/<format>/music-bed.wav).

assemble.py calls build_bed() when edit/edl.json has a `music` block (make_edl.py copies it from project.json):

  "music": {"file": "music/bed.flac", "bpm": 100}

`bpm` is the tempo the track was made at (the ACE-Step `bpm` parameter, or the library track's tempo); the real
tempo is searched within 3 % of it, because generated music rarely holds the requested tempo exactly. Optional
keys and defaults: see DEFAULTS and references/edit-pipeline.md.

usage: python3 music.py <music file> --bpm 100 [--beats-per-bar 4]    # print the beat grid, render nothing
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from media import HOP, envelope, loudness, probe_duration  # noqa: E402

SR = 48000
PLR_DB = 12.0  # the bed's peaks stay at most this far above its loudness: tames very peaky tracks, leaves mastered music
ONSET_SR, ONSET_FFT, ONSET_HOP = 16000, 512, 80  # 5 ms steps for the beat search
DEFAULTS = {
    "beats_per_bar": 4,
    "first_downbeat": "auto",  # or seconds into the file
    "anchor": "endcard",       # a downbeat lands here: "endcard", "start", a timeline second, or null
    "start": 0.0,              # timeline second where the bed comes in
    "level_db": -9.0,          # bed loudness against the dialogue's integrated loudness, between lines
    "duck_db": -12.0,          # extra level under speech
    "attack": 0.15,            # the dip starts this long before a line (the edit is offline, so it can look ahead)
    "release": 0.5,            # and comes back up over this long after it
    "hold": 0.6,               # pauses shorter than this stay ducked, so the bed does not pump between words
    "thr": -26.0,              # speech threshold in dB (make_edl.py fills it from speech.thr)
    "fade_in": 0.4,
    "fade_out": 1.5,
}


def decode(path, sr, channels=1, start=None, dur=None):
    args = ["ffmpeg", "-v", "error"] + (["-ss", f"{start:.6f}"] if start is not None else []) + ["-i", str(path)]
    args += (["-t", f"{dur:.6f}"] if dur is not None else []) + ["-vn", "-ac", str(channels), "-ar", str(sr),
                                                                  "-f", "f32le", "-"]
    audio = np.frombuffer(subprocess.check_output(args), np.float32)
    return audio.reshape(-1, channels) if channels > 1 else audio


def onset_strength(audio):
    """Spectral flux: the new energy every 5 ms brings, minus its local average. Beats are its regular peaks."""
    window = np.hanning(ONSET_FFT).astype(np.float32)
    n = 1 + (len(audio) - ONSET_FFT) // ONSET_HOP
    flux, previous = [], None
    for first in range(0, n, 4096):  # in blocks, so a long track does not need a large array
        idx = np.arange(ONSET_FFT)[None, :] + ONSET_HOP * np.arange(first, min(n, first + 4096))[:, None]
        mag = np.log1p(100 * np.abs(np.fft.rfft(audio[idx] * window, axis=1))).astype(np.float32)
        if previous is not None:
            mag = np.vstack([previous[None], mag])
        flux.append(np.maximum(np.diff(mag, axis=0), 0).sum(axis=1))
        previous = mag[-1]
    flux = np.concatenate(flux)
    # the flux peaks when a hit is three quarters into the analysis window (measured on click tracks; the grid then lands within 3 ms)
    times = (np.arange(1, n) * ONSET_HOP + 0.75 * ONSET_FFT) / ONSET_SR
    local = np.convolve(flux, np.ones(101) / 101, mode="same")
    return times, np.maximum(flux - local, 0)


def comb(times, flux, period, duration, step):
    """Mean onset strength on a beat grid of `period`, for every phase in [0, period)."""
    phases = np.arange(0, period, step)
    beats = np.arange(max(1, int((duration - period) / period))) * period
    return phases, np.interp(phases[:, None] + beats[None, :], times, flux, left=0, right=0).mean(axis=1)


def beat_grid(path, bpm, beats_per_bar=4, search=0.03):
    """Tempo and first downbeat of a track made at about `bpm`. A downbeat is the beat of the bar whose hits are
    strongest on average (the kick on the one)."""
    audio = decode(path, ONSET_SR)
    duration = len(audio) / ONSET_SR
    times, flux = onset_strength(audio)
    step = ONSET_HOP / ONSET_SR
    best = (-1.0, 0.0, 0.0)
    for spread, count in ((search, 121), (search / 60, 21)):  # 0.05 % steps, then 0.005 % around the best
        centre = 60 / bpm if best[0] < 0 else best[1]
        for period in centre * (1 + np.linspace(-spread, spread, count)):
            phases, score = comb(times, flux, period, duration, step)
            i = int(score.argmax())
            if score[i] > best[0]:
                best = (float(score[i]), float(period), float(phases[i]))
    _, period, phase = best
    phases, score = comb(times, flux, period, duration, step)
    i = int(np.abs(phases - phase).argmin())
    if 0 < i < len(score) - 1:  # parabolic peak between the 5 ms steps
        a, b, c = score[i - 1], score[i], score[i + 1]
        if a - 2 * b + c < 0:
            phase += 0.5 * (a - c) / (a - 2 * b + c) * step
    bar = period * beats_per_bar
    bars = np.arange(max(1, int((duration - bar) / bar))) * bar
    strength = [float(np.interp(phase + j * period + bars, times, flux).mean()) for j in range(beats_per_bar)]
    j = int(np.argmax(strength))
    return {"tempo_bpm": round(60 / period, 3), "beat": period, "bar": bar,
            "first_downbeat": round((phase + j * period) % bar, 4),
            "beat_clarity": round(best[0] / max(float(score.mean()), 1e-9), 2),  # about 1: no clear beat
            "downbeat_contrast": round(strength[j] / max(float(np.mean(strength)), 1e-9), 2),
            "duration": round(duration, 3)}


def offset_for(cfg, grid, anchor_time):
    """Seconds into the file where the bed starts, so that a downbeat falls on `anchor_time`."""
    if cfg.get("offset") is not None:
        return float(cfg["offset"])
    if anchor_time is None:
        return 0.0
    since_start = anchor_time - cfg["start"]
    if since_start < 0:
        raise SystemExit(f"music anchor {anchor_time:.2f} s is before the bed starts ({cfg['start']} s)")
    k = max(0, math.ceil((since_start - grid["first_downbeat"]) / grid["bar"] - 1e-9))
    return grid["first_downbeat"] + k * grid["bar"] - since_start


def speech_regions(dialogue, thr, hold, timeline):
    """[start, end] spans where the cut dialogue is above `thr` dB, pauses shorter than `hold` filled in."""
    loud = envelope(dialogue) > thr
    regions, open_at, last = [], None, -1e9
    for i, on in enumerate(loud):
        t = i * HOP
        if on:
            if open_at is None or t - last > hold:
                if open_at is not None:
                    regions.append([open_at, last])
                open_at = t
            last = t + HOP
    if open_at is not None:
        regions.append([open_at, last])
    return [[round(s, 2), round(min(e, timeline), 2)] for s, e in regions if e - s >= 0.08]


def gain_curve(n, regions, cfg, timeline):
    """Per-sample gain: duck_db under speech with look-ahead and release ramps, the fades, 0 dB elsewhere."""
    t = np.arange(int(math.ceil(timeline / HOP)) + 1) * HOP
    db = np.zeros_like(t)
    attack, release = max(cfg["attack"], 1e-3), max(cfg["release"], 1e-3)
    for s, e in regions:
        depth = np.minimum(np.clip((t - (s - attack)) / attack, 0, 1), np.clip((e + release - t) / release, 0, 1))
        db = np.minimum(db, cfg["duck_db"] * depth)
    seconds = np.arange(n) / SR
    gain = 10 ** (np.interp(seconds, t, db) / 20)
    start = cfg["start"]
    gain *= np.clip((seconds - start) / max(cfg["fade_in"], 1e-3), 0, 1)
    gain *= np.clip((timeline - seconds) / max(cfg["fade_out"], 1e-3), 0, 1)
    gain[seconds < start] = 0
    return gain


def build_bed(music, root, dialogue, timeline, endcard_at, work):
    """Write work/music-bed.wav, exactly `timeline` seconds long, and return its path and what was decided."""
    cfg = {**DEFAULTS, **music}
    source = (root / cfg["file"]).resolve()
    if not source.exists():
        raise SystemExit(f"music file {source} is missing")
    if "bpm" not in cfg and cfg.get("offset") is None and cfg["anchor"] is not None:
        raise SystemExit("music needs `bpm` (the tempo it was made at) to put a downbeat on the anchor")
    grid = beat_grid(source, cfg["bpm"], cfg["beats_per_bar"]) if "bpm" in cfg else None
    if grid and cfg["first_downbeat"] != "auto":
        grid["first_downbeat"] = float(cfg["first_downbeat"])
    anchor = cfg["anchor"]
    anchor_time = {"endcard": endcard_at, "start": cfg["start"]}.get(anchor, anchor) if anchor is not None else None
    offset = offset_for(cfg, grid, None if anchor_time is None else float(anchor_time))
    length = timeline - cfg["start"]
    file_seconds = probe_duration(source)
    if offset + length > file_seconds + 0.01:
        raise SystemExit(f"music too short: the bed needs {length:.1f} s from {offset:.2f} s, the file has "
                         f"{file_seconds:.1f} s; make a longer track (at least {offset + length + 1:.0f} s)")
    n = int(round(timeline * SR))
    segment = work / "music-segment.wav"
    cut = ["ffmpeg", "-v", "error", "-y", "-ss", f"{offset:.6f}", "-i", str(source), "-t", f"{length:.6f}", "-vn",
           "-ac", "2"]
    subprocess.run(cut + ["-ar", str(SR), "-c:a", "pcm_f32le", str(segment)], check=True)
    raw_lufs = loudness(segment)["integrated_lufs"]
    if raw_lufs is None:
        raise SystemExit(f"music file {source} is silent from {offset:.2f} s")
    # at -23 LUFS through a 4x oversampled lookahead limiter (close to a true-peak limit), so a peaky track cannot
    # push the final mix over -1 dBTP after AAC; latency=true keeps the beat where it was
    limit = 10 ** ((-23 + PLR_DB) / 20)
    subprocess.run(cut + ["-af", f"volume={-23 - raw_lufs:.3f}dB,aresample=192000,alimiter=limit={limit:.5f}:attack=2:"
                          f"release=60:level=false:latency=true,aresample={SR}", "-c:a", "pcm_f32le", str(segment)],
                   check=True)
    music_lufs = loudness(segment)["integrated_lufs"]
    dialogue_lufs = loudness(dialogue)["integrated_lufs"]
    level = ((dialogue_lufs if dialogue_lufs is not None else -23.0) + cfg["level_db"]) - music_lufs
    audio = np.zeros((n, 2), np.float32)
    body = decode(segment, SR, channels=2)[: n - int(round(cfg["start"] * SR))]
    first = int(round(cfg["start"] * SR))
    audio[first:first + len(body)] = body
    regions = speech_regions(dialogue, cfg["thr"], cfg["hold"], timeline)
    audio *= (gain_curve(n, regions, cfg, timeline) * 10 ** (level / 20)).astype(np.float32)[:, None]
    bed = work / "music-bed.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(bed)], input=audio.tobytes(), check=True)
    segment.unlink()
    info = {"file": str(cfg["file"]), "offset": round(offset, 4), "anchor": anchor,
            "anchor_time": None if anchor_time is None else round(float(anchor_time), 3),
            "level_gain_db": round(level + (-23 - raw_lufs), 2), "dialogue_lufs": dialogue_lufs, "music_lufs": raw_lufs,
            "duck_db": cfg["duck_db"], "speech_regions": len(regions), "grid": grid}
    (work / "music.json").write_text(json.dumps({**info, "regions": regions}, indent=1) + "\n")
    return bed, info


# -2 dBFS at 192 kHz is close to -2 dBTP; AAC adds a few tenths, which keeps the file under the -1 dBTP of QA
MASTER_LIMIT = "aresample=192000,alimiter=limit=0.7943:attack=2:release=60:level=false:latency=true,aresample=48000"


def master(listing, bed, work, target=-14.0):
    """Filter graph for the final mix with the bed: one static gain to `target` LUFS and an oversampled peak
    limiter. A static gain keeps the ducking exactly as set (loudnorm's dynamic mode would ride the music up in
    every pause). The limiter takes a little loudness away, so the gain is measured twice."""
    mix = "[0:a][1:a]amix=inputs=2:normalize=0:duration=first"
    probe = work / "music-mix.wav"
    gain = 0.0
    for _ in range(2):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(bed),
                        "-filter_complex", f"{mix},volume={gain:.3f}dB,{MASTER_LIMIT}[a]", "-map", "[a]",
                        "-c:a", "pcm_f32le", str(probe)], check=True)
        gain += target - loudness(probe)["integrated_lufs"]
    probe.unlink()
    return f"{mix},volume={gain:.3f}dB,{MASTER_LIMIT}[a]", round(gain, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--bpm", type=float, required=True, help="the tempo the track was made at")
    ap.add_argument("--beats-per-bar", type=int, default=4)
    a = ap.parse_args()
    print(json.dumps(beat_grid(pathlib.Path(a.file), a.bpm, a.beats_per_bar)))


if __name__ == "__main__":
    main()
