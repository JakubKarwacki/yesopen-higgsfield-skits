# Example: "It's not you. It's your invoices."

The first YesOpen skit, complete. A gym owner breaks up with his marketing agency; every "I don't know" is
answered by a YesOpen notification on his phone. 73.5 s, English, made on 2026-10-01.
The full story of how it was made is in `../../references/case-study-gym-breakup.md`.

![Poster](final/web/its-not-you-its-your-invoices-9x16-poster.jpg)

## Watch

| File | Format | Size |
| --- | --- | --- |
| [final/its-not-you-its-your-invoices-9x16.mp4](final/its-not-you-its-your-invoices-9x16.mp4) | 9:16 master, 1080x1920 | 58.9 MB |
| [final/its-not-you-its-your-invoices-9x16-share.mp4](final/its-not-you-its-your-invoices-9x16-share.mp4) | 9:16, for mail and chat | 24.1 MB |
| [final/web/its-not-you-its-your-invoices-9x16.mp4](final/web/its-not-you-its-your-invoices-9x16.mp4) | 9:16, 720x1280 | 13.6 MB |
| [final/web/its-not-you-its-your-invoices-4x5.mp4](final/web/its-not-you-its-your-invoices-4x5.mp4) | 4:5 | 13.6 MB |
| [final/web/its-not-you-its-your-invoices-1x1.mp4](final/web/its-not-you-its-your-invoices-1x1.mp4) | 1:1 | 13.6 MB |
| [final/web/its-not-you-its-your-invoices-16x9.mp4](final/web/its-not-you-its-your-invoices-16x9.mp4) | 16:9 | 13.6 MB |

## What is here

| Path | Content |
| --- | --- |
| `script.md` | the approved script (in Polish, dialogue in English), decisions, claims, production notes and "Po produkcji" |
| `project.json` | cast, takes, speech threshold, caption style and fixes, banner texts, end card |
| `reference/analysis.md` | our analysis of the reference video (link only; its frames and transcript are not here) |
| `args/` | every request body sent to Higgsfield: 5 Soul batches, takes at 1080p, 720p and 480p, the 4 s probe |
| `stills/` | all 20 Soul candidates (JPG), the two picked originals (PNG), sheets, `picked.json`, `jobs.jsonl` |
| `takes/` | the four 720p takes used in the edit and the 480p agency take, each with Whisper word timestamps; `jobs.jsonl` with every request |
| `edit/cuts.json` | the edit: 21 shots with notes |
| `edit/edl.json` | the generated edit decision list |
| `edit/assets/` | the ding and, per format, the four banners, the end card and a caption sample |
| `edit/frames/` | the sheets used for QA: takes, preview, final checkpoints, captions per format |
| `edit/qa-summary.json` | QA numbers of all four formats |
| `edit/original-scripts/` | the one-off scripts the skit was first cut with, and their EDL, for comparison |

## Rebuild it

From the skill folder:

```bash
python3 scripts/make_edl.py examples/gym-breakup            # cuts.json + transcripts -> edl.json
python3 scripts/assemble.py examples/gym-breakup --format 9:16
md5 -q examples/gym-breakup/final/its-not-you-its-your-invoices-9x16.mp4   # 095ffdca450db823b26fd76fa89a1204
python3 scripts/assemble.py examples/gym-breakup --format all              # 4:5, 1:1 and 16:9 masters too
python3 scripts/qa_report.py examples/gym-breakup --format 9:16 --whisper
```

The masters of 4:5, 1:1 and 16:9 are not stored, to keep the repository small; the command above renders them
in about 40 s each. The byte-identical check holds with the same ffmpeg build (8.x on macOS); another build can differ
in bytes but not in timing.
