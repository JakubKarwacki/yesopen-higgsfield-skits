# Formats and delivery

## The four formats

One edit (`edit/edl.json`) renders into every format. The takes are 9:16, so 9:16 is the master and the other
formats crop or pillarbox it. Layout constants live in `scripts/brand.py` (`FORMATS`).

| Format | Size | Picture | Caption y / size | Banner top / scale | Where it goes |
| --- | --- | --- | --- | --- | --- |
| 9:16 | 1080x1920 | full take | 0.646 (1240 px) / 66 px | 70 px / 1.00 | TikTok, Reels, Shorts, Stories, WhatsApp status |
| 4:5 | 1080x1350 | crop around `cy` | 0.70 / 62 px | 40 px / 0.92 | Instagram and Facebook feed |
| 1:1 | 1080x1080 | crop around `cy` | 0.74 / 60 px | 30 px / 0.88 | feeds, LinkedIn, ads |
| 16:9 | 1920x1080 | 9:16 picture 608x1080 in the middle over a blurred, darkened copy (pillarbox) | 0.80 / 58 px | 30 px / 0.85 | YouTube, website, presentations |

Render one or all:

```bash
python3 $SK/scripts/assemble.py . --format 4:5
python3 $SK/scripts/assemble.py . --format all
```

The pillarbox graph (16:9):

```text
split=2[bgsrc][fgsrc];
[bgsrc]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,gblur=sigma=40,eq=brightness=-0.06:saturation=0.85[bg];
[fgsrc]crop=<9:16 crop with zoom>,scale=608:1080:flags=lanczos[fg];
[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps=30:start_time=0
```

End cards are laid out per format by `brand.endcard`: scale `s = min(W/1080, 0.82*H/974, 1)`, top
`y0 = round(1047/1920*H - 487*s)`; icon at `y0` (210·s px), wordmark at `y0+260·s` (Manrope 500, 168·s px,
tracking −0.05 em, "Yes" ink + "Open" blue), tagline from `y0+550·s` (Manrope 700, 76·s px, 98·s px line step),
URL at `y0+920·s` (Manrope 600, 54·s px, slate-500). At 1080x1920 this is exactly the first skit's card.
Keep the tagline to 1–3 short lines; a line wider than 90% of the frame is shrunk to fit.

Check every new format with a checkpoint sheet before delivering: faces must not sit under a banner,
captions must not cover the mouth or the phone joke, the zooms must still frame the face.

```bash
python3 $SK/scripts/qa_report.py . --format 4:5          # writes edit/frames/qa-4x5-captions.jpg
python3 $SK/scripts/qa_sheet.py final/<name>-4x5.mp4 edit/frames/sheet-4x5.jpg --step 2
```

## Sizes for sharing

```bash
python3 $SK/scripts/encode_variants.py final/<name>-9x16.mp4
```

| Variant | Settings | Gym result | Limit it serves |
| --- | --- | --- | --- |
| master `final/<name>-<fmt>.mp4` | crf 17, AAC 192k | 58.9 MB (9:16) | archive, upload to the platforms |
| share `final/<name>-<fmt>-share.mp4` | same size, two-pass 2450k, AAC 160k | 24.1 MB (23.0 MiB) | 25 MiB mail/chat attachment limit |
| web `final/web/<name>-<fmt>.mp4` | shorter side 720, two-pass 1350k, AAC 128k | 13.6 MB | 15 MB claude.ai Artifact file limit |
| poster `final/web/<name>-<fmt>-poster.jpg` | frame at 3.3 s | 60 KB | page and chat previews |

## Handing the video over

1. **Clickable local links first.** Give the absolute paths of the master, share and web files as Markdown
   links in the reply, before anything else. Marcin asked for this explicitly ("gdzie są pliki na dysku");
   do not make him wait for an upload or a page.
2. **A preview in chat**: use the current app’s supported local video preview. In Codex, use Markdown image
   syntax with the absolute MP4 path. Use `SendUserFile` only when available; do not search indefinitely for an
   unavailable tool. Verify files exist locally and compare their hashes with the server copies first.
3. **A page to share** (optional, when asked): a private claude.ai Artifact with the web mp4 and the poster
   (each file under 15 MB). Use the Artifact tool's own flow; do not detour through other hosting.
4. **Never post** to TikTok, Instagram, YouTube or any account without an explicit request for that post.

Report: length, formats, loudness (−14 LUFS), the files with links, and anything that differs from the
approved script.

## WhatsApp delivery when explicitly requested

Use the requested computer-use interface and the native WhatsApp app when available. Confirm the group name
in the open chat and again in the media preview; do not infer a recipient from chat recency. Select the verified
final master with Photos and videos. In the macOS file dialog, open Go to Folder, inspect its current state,
set the path field explicitly, and verify the selected basename/path before Open. A paste attempt is not proof
that the file picker received the intended path.

Check the preview shows the intended full duration, unmuted audio and one correct attachment. Select HD for
normal video sharing; this may still recompress the video and is not byte-identical master delivery. If the user
requires the exact original, send it as a file/document instead. Do not invent a caption or additional recipients.
Send under the user's existing specific authorization. Wait for upload completion and inspect Sent/Delivered;
report exactly the status shown. Uploading, a local bubble or a clicked Send button alone is not delivery.
Never retry an uncertain send without first reconciling the existing message, to avoid duplicates.
