"""Brand fonts, colours and image helpers for the YesOpen shorts."""
import glob
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = "/Users/Marcin_1/Documents/Behavio.one/Projects/localesto/business-card"
ICON = f"{ROOT}/public/icons/icon-512.png"
INK = (15, 23, 42)        # slate-950 / logo "Yes"
BLUE = (8, 119, 255)      # #0877ff / logo "Open"
MUTED = (100, 116, 139)
CAPTION_YELLOW = (255, 224, 75)


def _manrope_path() -> str:
    """Pick the Manrope subset from the Next build that has Latin glyphs."""
    def glyph(fnt, ch):
        im = Image.new("L", (64, 64), 0)
        ImageDraw.Draw(im).text((8, 4), ch, font=fnt, fill=255)
        return im.tobytes()

    for path in sorted(glob.glob(f"{ROOT}/.next/static/media/*.woff2")):
        fnt = ImageFont.truetype(path, 40)
        missing = glyph(fnt, chr(0xE000))
        if all(glyph(fnt, ch) != missing for ch in "YesOpenIt'syourinvoices"):
            return path
    raise RuntimeError("Manrope Latin subset not found in .next/static/media")


MANROPE = _manrope_path()


def font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(MANROPE, size)
    f.set_variation_by_axes([weight])
    return f


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def tracked_text(draw, xy, parts, fnt, tracking):
    """Draw [(text, colour), ...] char by char with letter spacing in px; returns end x."""
    x, y = xy
    for text, colour in parts:
        for ch in text:
            draw.text((x, y), ch, font=fnt, fill=colour)
            x += fnt.getlength(ch) + tracking
    return x


def tracked_width(parts, fnt, tracking):
    return sum(fnt.getlength(ch) + tracking for text, _ in parts for ch in text) - tracking


def caption(text: str, width: int = 1080, size: int = 66) -> Image.Image:
    """Yellow caption with a black outline, centred, like the reference short."""
    fnt = font(size, 800)
    stroke = 8
    w = int(fnt.getlength(text)) + 2 * stroke + 8
    h = size + 2 * stroke + 24
    img = Image.new("RGBA", (max(w, 10), h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((stroke + 4, stroke + 4), text, font=fnt, fill=CAPTION_YELLOW, stroke_width=stroke, stroke_fill=(0, 0, 0))
    canvas = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    canvas.paste(img, ((width - img.size[0]) // 2, 0), img)
    return canvas


def notification(body: str, when: str = "now") -> Image.Image:
    """iOS-style banner: YesOpen icon, app name, time and one or two lines of text."""
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
    icon = rounded(Image.open(ICON).convert("RGBA").resize((112, 112), Image.LANCZOS), 26)
    canvas.paste(icon, (M + 34, M + (H - 112) // 2), icon)
    d = ImageDraw.Draw(canvas)
    d.text((M + 172, M + 34), "YesOpen", font=title, fill=(17, 17, 17))
    d.text((M + W - 40 - meta.getlength(when), M + 38), when, font=meta, fill=(142, 142, 147))
    for i, ln in enumerate(lines):
        d.text((M + 172, M + 88 + i * 48), ln, font=text, fill=(28, 28, 30))
    return canvas


def endcard(tagline_lines, url: str = "yesopens.com", size=(1080, 1920)) -> Image.Image:
    W, H = size
    img = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(img)
    icon = rounded(Image.open(ICON).convert("RGBA").resize((210, 210), Image.LANCZOS), 48)
    img.paste(icon, ((W - 210) // 2, 560), icon)
    mark = font(168, 500)
    parts = [("Yes", INK), ("Open", BLUE)]
    tracking = -0.05 * 168
    tracked_text(d, ((W - tracked_width(parts, mark, tracking)) / 2, 820), parts, mark, tracking)
    tag = font(76, 700)
    y = 1110
    for parts in tagline_lines:
        tw = sum(tag.getlength(t) for t, _ in parts)
        x = (W - tw) / 2
        for t, colour in parts:
            d.text((x, y), t, font=tag, fill=colour)
            x += tag.getlength(t)
        y += 98
    link = font(54, 600)
    d.text(((W - link.getlength(url)) / 2, 1480), url, font=link, fill=MUTED)
    return img
