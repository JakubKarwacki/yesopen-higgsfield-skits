"""Re-render the ready-made overlays in assets/: brand pack, notification banners, end cards and caption samples.

usage: python3 render_asset_library.py

Every banner text below is a claim checked in business-card/messages/en (see references/scriptwriting.md).
Add new ones only after the same check.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from brand import FORMATS, SKILL, caption, endcard, notification, render_brand_pack  # noqa: E402

OUT = SKILL / "assets" / "overlays"

NOTIFICATIONS = {
    "question-answered": "Answered your question. Anything else?",
    "reviews-answered": "12 new reviews answered",
    "review-reply": "Replied to a new 5-star review",
    "post-live-meta": "Your post is live on Instagram and Facebook",
    "google-post": "New post published on your Google profile",
    "rank-gym": "You're #1 for “gym near me”",
    "ranking-up": "Your Google Maps ranking went up",
}

ENDCARDS = {
    "its-your-invoices": [[("It’s not you.", "ink")], [("It’s your ", "ink"), ("invoices.", "blue")]],
    "be-number-one": [[("Be the #1 business", "ink")], [("on ", "ink"), ("Google Maps.", "blue")]],
}


def main():
    for name in render_brand_pack():
        print("assets/brand/" + name)
    (OUT / "notifications").mkdir(parents=True, exist_ok=True)
    for key, body in NOTIFICATIONS.items():
        target = OUT / "notifications" / f"notif-{key}.png"
        notification(body).save(target)
        print(target.relative_to(SKILL))
    (OUT / "endcards").mkdir(parents=True, exist_ok=True)
    (OUT / "captions").mkdir(parents=True, exist_ok=True)
    for fmt, layout in FORMATS.items():
        for key, tagline in ENDCARDS.items():
            target = OUT / "endcards" / f"endcard-{key}-{layout['slug']}.png"
            endcard(tagline, "yesopens.com", layout["size"]).save(target)
            print(target.relative_to(SKILL))
        target = OUT / "captions" / f"caption-sample-{layout['slug']}.png"
        caption("It's not you.", width=layout["size"][0], size=layout["caption_size"]).save(target)
        print(target.relative_to(SKILL))


if __name__ == "__main__":
    main()
