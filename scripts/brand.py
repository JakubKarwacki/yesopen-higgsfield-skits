"""YesOpen brand for the skits: colours, the Manrope font, output formats and overlay images.

Every helper returns a PIL image; nothing here runs ffmpeg.

    python3 brand.py --render-brand-pack     # re-render assets/brand/*.png (wordmarks, lockups)
    python3 brand.py --font                  # print which Manrope file is used
"""
import json
import os
import pathlib
import sys
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = pathlib.Path(__file__).resolve().parent.parent
BRAND = SKILL / "assets" / "brand"
ICON = BRAND / "yesopen-icon-512.png"

INK = (15, 23, 42)              # slate-950, the "Yes" of the wordmark
BLUE = (8, 119, 255)            # #0877ff, the "Open" of the wordmark
MUTED = (100, 116, 139)         # slate-500, the URL on the end card
CAPTION_YELLOW = (255, 224, 75)
WHITE = (255, 255, 255)
COLOURS = {"ink": INK, "blue": BLUE, "muted": MUTED, "yellow": CAPTION_YELLOW, "white": WHITE}

# Output formats. Captions and banners are placed per format. 16:9 keeps the vertical
# picture whole in the middle (pillarbox) over a blurred, darkened copy of itself.
FORMATS = {
    "9:16": {"slug": "9x16", "size": (1080, 1920), "fit": "crop",
             "caption_y": 0.646, "caption_size": 66, "banner_top": 70, "banner_scale": 1.0},
    "4:5": {"slug": "4x5", "size": (1080, 1350), "fit": "crop",
            "caption_y": 0.70, "caption_size": 62, "banner_top": 40, "banner_scale": 0.92},
    "1:1": {"slug": "1x1", "size": (1080, 1080), "fit": "crop",
            "caption_y": 0.74, "caption_size": 60, "banner_top": 30, "banner_scale": 0.88},
    "16:9": {"slug": "16x9", "size": (1920, 1080), "fit": "pillarbox",
             "caption_y": 0.80, "caption_size": 58, "banner_top": 30, "banner_scale": 0.85},
}


def get_format(name: str) -> dict:
    """Accept "9:16" or "9x16"; return the layout with its name."""
    key = name.strip().replace("x", ":")
    if key not in FORMATS:
        raise SystemExit(f"unknown format {name!r}; use one of {', '.join(FORMATS)}")
    return {"name": key, **FORMATS[key]}


def colour(value):
    """A colour from a name in COLOURS, a hex string or an [r, g, b] list."""
    if isinstance(value, str):
        if value in COLOURS:
            return COLOURS[value]
        value = value.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(value)


def localesto_root():
    """The Localesto checkout (LOCALESTO_ROOT, or the first parent with business-card/package.json)."""
    env = os.environ.get("LOCALESTO_ROOT")
    if env:
        return pathlib.Path(env).expanduser()
    for start in (pathlib.Path.cwd(), SKILL):
        for parent in [start, *start.parents]:
            if (parent / "business-card" / "package.json").exists():
                return parent
    return None


def _font_candidates():
    env = os.environ.get("YESOPEN_FONT")
    if env:
        yield pathlib.Path(env).expanduser()
    yield from sorted((BRAND / "fonts").glob("Manrope*.ttf"))
    for folder in (pathlib.Path.home() / "Library" / "Fonts", pathlib.Path("/Library/Fonts"), pathlib.Path("/usr/share/fonts")):
        if folder.exists():
            yield from sorted(folder.rglob("Manrope*.ttf"))
    root = localesto_root()
    if root:
        yield from sorted((root / "business-card" / ".next" / "static" / "media").glob("*.woff2"))


@lru_cache(maxsize=None)
def manrope_path() -> str:
    """The first Manrope file that really has the Latin letters we draw."""
    def glyph(fnt, ch):
        im = Image.new("L", (64, 64), 0)
        ImageDraw.Draw(im).text((8, 4), ch, font=fnt, fill=255)
        return im.tobytes()

    for path in _font_candidates():
        try:
            fnt = ImageFont.truetype(str(path), 40)
        except OSError:
            continue
        if "Manrope" not in (fnt.getname()[0] or ""):
            continue
        missing = glyph(fnt, chr(0xE000))
        if all(glyph(fnt, ch) != missing for ch in "YesOpenIt'syourinvoices"):
            return str(path)
    raise SystemExit("Manrope not found: keep assets/brand/fonts/Manrope-Variable.ttf or set YESOPEN_FONT")


@lru_cache(maxsize=None)
def font(size: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    """Manrope at a pixel size and weight (200-800; the variable font's wght axis)."""
    f = ImageFont.truetype(manrope_path(), size)
    try:
        f.set_variation_by_axes([weight])
    except OSError:
        pass  # a static Manrope file has one fixed weight
    return f


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def icon(size: int, radius_ratio: float = 48 / 210) -> Image.Image:
    """The app icon (white square, blue Y) with rounded corners."""
    return rounded(Image.open(ICON).convert("RGBA").resize((size, size), Image.LANCZOS), round(size * radius_ratio))


def tracked_text(draw, xy, parts, fnt, tracking):
    """Draw [(text, colour), ...] char by char with letter spacing in px; returns the end x."""
    x, y = xy
    for text, col in parts:
        for ch in text:
            draw.text((x, y), ch, font=fnt, fill=col)
            x += fnt.getlength(ch) + tracking
    return x


def tracked_width(parts, fnt, tracking):
    return sum(fnt.getlength(ch) + tracking for text, _ in parts for ch in text) - tracking


def caption(text: str, width: int = 1080, size: int = 66) -> Image.Image:
    """Yellow caption with a black outline, centred on a transparent strip `width` px wide."""
    while True:
        fnt = font(size, 800)
        stroke = max(3, round(size * 8 / 66))
        w = int(fnt.getlength(text)) + 2 * stroke + 8
        if w <= width * 0.94 or size <= 30:
            break
        size -= 2  # a long chunk shrinks instead of running off the frame
    h = size + 2 * stroke + 24
    img = Image.new("RGBA", (max(w, 10), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((stroke + 4, stroke + 4), text, font=fnt, fill=CAPTION_YELLOW, stroke_width=stroke, stroke_fill=(0, 0, 0))
    canvas = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    canvas.paste(img, ((width - img.size[0]) // 2, 0), img)
    return canvas


def notification(body: str, when: str = "now", app: str = "YesOpen", scale: float = 1.0) -> Image.Image:
    """iOS-style banner: app icon, app name, time and one or two lines of text (1040 px wide at scale 1)."""
    W, M = 980, 30
    title, meta, text = font(40, 700), font(34, 500), font(39, 500)
    words, lines, line = body.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if text.getlength(trial) > W - 172 - 40 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    lines = lines[:2]
    H = 200 + 48 * (len(lines) - 1)
    canvas = Image.new("RGBA", (W + 2 * M, H + 2 * M + 10), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([M, M + 10, M + W, M + H + 10], 50, fill=(0, 0, 0, 70))
    canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(16)))
    card = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle([M, M, M + W, M + H], 50, fill=(248, 248, 250, 248))
    canvas = Image.alpha_composite(canvas, card)
    ico = rounded(Image.open(ICON).convert("RGBA").resize((112, 112), Image.LANCZOS), 26)
    canvas.paste(ico, (M + 34, M + (H - 112) // 2), ico)
    d = ImageDraw.Draw(canvas)
    d.text((M + 172, M + 34), app, font=title, fill=(17, 17, 17))
    d.text((M + W - 40 - meta.getlength(when), M + 38), when, font=meta, fill=(142, 142, 147))
    for i, ln in enumerate(lines):
        d.text((M + 172, M + 88 + i * 48), ln, font=text, fill=(28, 28, 30))
    if scale != 1.0:
        canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS)
    return canvas


def endcard(tagline_lines, url: str = "yesopens.com", size=(1080, 1920), background=WHITE) -> Image.Image:
    """White end card: icon, the YesOpen wordmark, a tagline and the URL, laid out for any frame size.

    tagline_lines: [[(text, colour), ...], ...] where colour is a name ("ink", "blue"), hex or RGB.
    At 1080x1920 this is the layout of the first skit: icon at y 560, wordmark 820, tagline 1110, URL 1480.
    """
    W, H = size
    s = min(W / 1080, 0.82 * H / 974, 1.0)
    y0 = round(1047 / 1920 * H - 487 * s)
    img = Image.new("RGB", size, background)
    d = ImageDraw.Draw(img)
    side = round(210 * s)
    ico = rounded(Image.open(ICON).convert("RGBA").resize((side, side), Image.LANCZOS), round(48 * s))
    img.paste(ico, ((W - side) // 2, y0), ico)
    mark = font(round(168 * s), 500)
    parts = [("Yes", INK), ("Open", BLUE)]
    tracking = -0.05 * round(168 * s)
    tracked_text(d, ((W - tracked_width(parts, mark, tracking)) / 2, y0 + round(260 * s)), parts, mark, tracking)
    tag = font(round(76 * s), 700)
    y = y0 + round(550 * s)
    for line in tagline_lines:
        line = [(t, colour(c)) for t, c in line]
        f = tag
        width = sum(f.getlength(t) for t, _ in line)
        if width > 0.9 * W:  # a long line shrinks to 90% of the frame width instead of running off the card
            f = font(int(round(76 * s) * 0.9 * W / width), 700)
            width = sum(f.getlength(t) for t, _ in line)
        x = (W - width) / 2
        for t, col in line:
            d.text((x, y), t, font=f, fill=col)
            x += f.getlength(t)
        y += round(98 * s)
    if url:
        link = font(round(54 * s), 600)
        d.text(((W - link.getlength(url)) / 2, y0 + round(920 * s)), url, font=link, fill=MUTED)
    return img


def wordmark(height: int = 168, dark_background: bool = False, pad: int = 0) -> Image.Image:
    """The "YesOpen" wordmark on a transparent background; `height` is the font size in px."""
    fnt = font(height, 500)
    tracking = -0.05 * height
    yes = WHITE if dark_background else INK
    parts = [("Yes", yes), ("Open", BLUE)]
    w = int(tracked_width(parts, fnt, tracking)) + 2 * pad + 4
    left, top, right, bottom = fnt.getbbox("YesOpen")
    img = Image.new("RGBA", (w, bottom - top + 2 * pad + 4), (0, 0, 0, 0))
    tracked_text(ImageDraw.Draw(img), (pad + 2 - left, pad + 2 - top), parts, fnt, tracking)
    return img


def lockup(height: int = 168, dark_background: bool = False, horizontal: bool = True) -> Image.Image:
    """Icon plus wordmark, side by side or stacked, transparent background."""
    mark = wordmark(height, dark_background)
    side = round(height * 1.25)
    ico = icon(side)
    if horizontal:
        gap = round(height * 0.35)
        img = Image.new("RGBA", (side + gap + mark.width, max(side, mark.height)), (0, 0, 0, 0))
        img.paste(ico, (0, (img.height - side) // 2), ico)
        img.paste(mark, (side + gap, (img.height - mark.height) // 2), mark)
    else:
        gap = round(height * 0.45)
        img = Image.new("RGBA", (max(side, mark.width), side + gap + mark.height), (0, 0, 0, 0))
        img.paste(ico, ((img.width - side) // 2, 0), ico)
        img.paste(mark, ((img.width - mark.width) // 2, side + gap), mark)
    return img


def render_brand_pack(out: pathlib.Path = BRAND) -> list:
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "yesopen-wordmark-on-light.png": wordmark(168),
        "yesopen-wordmark-on-dark.png": wordmark(168, dark_background=True),
        "yesopen-lockup-horizontal-on-light.png": lockup(140),
        "yesopen-lockup-horizontal-on-dark.png": lockup(140, dark_background=True),
        "yesopen-lockup-stacked-on-light.png": lockup(140, horizontal=False),
        "yesopen-lockup-stacked-on-dark.png": lockup(140, dark_background=True, horizontal=False),
        "yesopen-icon-rounded-1024.png": icon(1024, 0.2285),
    }
    for name, img in files.items():
        img.save(out / name)
    palette = {
        "ink": "#0f172a", "blue": "#0877ff", "muted": "#64748b", "caption_yellow": "#ffe04b",
        "icon_gradient": ["#0050c1", "#0064f1", "#99c1f9"],
        "font": "Manrope (variable, wght 200-800; wordmark 500, tracking -0.05em; captions 800)",
        "wordmark": "\"Yes\" in ink + \"Open\" in blue; on dark backgrounds \"Yes\" is white",
    }
    (out / "palette.json").write_text(json.dumps(palette, indent=1) + "\n")
    return sorted(files) + ["palette.json"]


if __name__ == "__main__":
    if "--render-brand-pack" in sys.argv:
        print("\n".join(render_brand_pack()))
    else:
        print(manrope_path())
