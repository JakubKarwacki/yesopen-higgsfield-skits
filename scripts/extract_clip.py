"""Cut one shot out of a take (or any clip), framed for an output format: b-roll, reactions, GIF sources.

usage: python3 extract_clip.py <src.mp4> <in_seconds> <duration> <out.mp4>
                               [--format 9:16] [--zoom 1.0] [--cx 0.5] [--cy 0.4] [--no-audio] [--crf 20] [--native]

--native keeps the source frame size (only trims and re-encodes), the rest crops/pillarboxes
exactly like assemble.py does for that format.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import get_format  # noqa: E402
from media import run, video_filter  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("start", type=float)
    ap.add_argument("dur", type=float)
    ap.add_argument("out")
    ap.add_argument("--format", default="9:16")
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--cx", type=float, default=0.5)
    ap.add_argument("--cy", type=float, default=0.4)
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--native", action="store_true")
    a = ap.parse_args()
    vf = "fps=30:start_time=0,setsar=1" if a.native else video_filter(a.src, get_format(a.format), a.zoom, a.cx, a.cy)
    audio = ["-an"] if a.no_audio else ["-c:a", "aac", "-b:a", "128k", "-ar", "48000"]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    run(["-ss", f"{a.start:.3f}", "-i", a.src, "-t", f"{a.dur:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "slow",
         "-crf", str(a.crf), "-pix_fmt", "yuv420p", *audio, "-movflags", "+faststart", a.out])
    print(a.out)


if __name__ == "__main__":
    main()
