"""Smaller copies of a finished master for sharing, plus a poster frame.

usage: python3 encode_variants.py <master.mp4> [--share-mib 25] [--web-mb 15] [--poster-at 3.3]
                                  [--outdir DIR] [--only share|web|poster]

  <name>-share.mp4   full resolution, two-pass, sized to fit --share-mib (25 MiB: mail and chat attachments)
  web/<name>.mp4     shorter side 720 px, two-pass, sized to fit --web-mb (15 MB: claude.ai Artifact files)
  web/<name>-poster.jpg  one frame at --poster-at seconds, web size

The bitrate comes from the duration: 92 % of the size budget minus the audio, rounded down to 50 kbit/s.
For the 73.6 s gym skit this gives the values used by hand then: 2450k (share) and 1350k (web).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from media import probe_duration, probe_size  # noqa: E402


def bitrate_kbps(limit_bytes, duration, audio_kbps, safety=0.92):
    total = limit_bytes * 8 * safety / duration / 1000
    return int((total - audio_kbps) // 50 * 50)


def two_pass(src, out, scale, kbps, audio_kbps):
    vf = ["-vf", f"scale={scale}:flags=lanczos"] if scale else []
    rate = ["-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.63)}k", "-bufsize", f"{int(kbps * 3.26)}k"]
    with tempfile.TemporaryDirectory() as tmp:
        log = str(pathlib.Path(tmp) / "pass")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), *vf, "-c:v", "libx264", "-preset", "slow", *rate,
                        "-pass", "1", "-passlogfile", log, "-an", "-f", "mp4", "/dev/null"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), *vf, "-c:v", "libx264", "-preset", "slow", *rate,
                        "-pass", "2", "-passlogfile", log, "-profile:v", "high", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", f"{audio_kbps}k", "-movflags", "+faststart", str(out)], check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("master")
    ap.add_argument("--share-mib", type=float, default=25.0)
    ap.add_argument("--web-mb", type=float, default=15.0)
    ap.add_argument("--poster-at", type=float, default=3.3)
    ap.add_argument("--outdir")
    ap.add_argument("--only", choices=["share", "web", "poster"])
    a = ap.parse_args()
    src = pathlib.Path(a.master).resolve()
    outdir = pathlib.Path(a.outdir).resolve() if a.outdir else src.parent
    outdir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(src)
    w, h = probe_size(src)
    web_scale = "720:-2" if w <= h else "-2:720"
    report = {"master": str(src), "duration": round(duration, 2), "size": [w, h]}
    if a.only in (None, "share"):
        kbps = bitrate_kbps(a.share_mib * 1048576, duration, 160)
        out = two_pass(src, outdir / f"{src.stem}-share.mp4", None, kbps, 160)
        report["share"] = {"file": str(out), "video_kbps": kbps, "mib": round(out.stat().st_size / 1048576, 2),
                           "limit_mib": a.share_mib}
    if a.only in (None, "web"):
        (outdir / "web").mkdir(parents=True, exist_ok=True)
        kbps = bitrate_kbps(a.web_mb * 1e6, duration, 128)
        out = two_pass(src, outdir / "web" / f"{src.stem}.mp4", web_scale, kbps, 128)
        report["web"] = {"file": str(out), "video_kbps": kbps, "mb": round(out.stat().st_size / 1e6, 2), "limit_mb": a.web_mb}
    if a.only in (None, "poster"):
        (outdir / "web").mkdir(parents=True, exist_ok=True)
        poster = outdir / "web" / f"{src.stem}-poster.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a.poster_at:.2f}", "-i", str(src), "-frames:v", "1",
                        "-vf", f"scale={web_scale}:flags=lanczos", "-q:v", "4", str(poster)], check=True)
        report["poster"] = str(poster)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
