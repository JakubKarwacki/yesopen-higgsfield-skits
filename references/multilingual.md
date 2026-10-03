# Multilingual speech with Chatterbox Multilingual V3

## Current implementation

`tts` uses the pinned Fill Chatterbox node with a source-hash-checked build patch selecting
`t3_mtl23ls_v3.safetensors`. The model URL is pinned to Hugging Face revision
`5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18`; SHA-256 is
`5abca8321ede76f8e61f1cc0d19aea6c946b28871017ce8726f8a69203f05953`.
The patch rejects changed upstream sources and missing preloaded model files. Existing V2 files can remain
on preserved disks but are not selected by the patched multilingual loader. Rebuild the ComfyUI image and
fetch verified models before using V3; changing client code alone does not upgrade a running server.

Upstream evidence: [Resemble loader](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/mtl_tts.py)
and [model files](https://huggingface.co/ResembleAI/chatterbox/tree/5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18).
The upstream multilingual loader switches the T3 file for V3 while retaining `s3gen.pt`; similarly named
`s3gen_v3` files are not substituted speculatively. The legacy `tts-dialog` English node is unchanged;
multilingual dialogue uses one `tts` task per speaker/line and audio-driven video takes.

## Project settings

Create a project with `python3 scripts/new_project.py demo --language pl`. Both JSON files get matching
settings. Existing projects accept `pl`, `Polish`, or `Polish (pl)`; canonical project code is `pl` and the
ComfyUI label is `Polish (pl)`. If only one file declares a language, the other inherits it. Conflicting
explicit values fail before submission. Undeclared legacy projects remain English. Region codes and mixed
language lines fail instead of being silently guessed; use separate project revisions for each language.
Template dialogue is illustrative: this option sets language metadata, it does not translate the script.

Supported model language codes:
`ar da de el en es fi fr he hi it ja ko ms nl no pl pt ru sv sw tr zh`.

The same language reaches fitting, take inspection, fallback caption transcription and final audio QA.
English-only Whisper weights are rejected for non-English inspection/fitting. Text comparison preserves
Unicode letters, marks and numbers; final QA reports `character_match` and `metric`, replacing the misleading
English-centric `word_match`. Character units handle languages without space-separated words. The default
minimum similarity remains 0.9; final shared QA now blocks export when speech QA fails. This score does not
certify meaning, pronunciation, acting or voice identity. Fitting failure removes stale selected audio,
writes a failed checkpoint and returns a nonzero exit status.

Write numbers as intended spoken words. Do not automatically apply English number expansion to other
languages. When ASR consistently writes digits, an approved project setting can resolve that specific reading:

```json
{"speech": {"number_aliases": {"15": "piętnastej"}}}
```

This is a project-specific reading, not a general Polish inflection rule. Unmapped numerical differences
remain visible; they are not erased. For a captionless spoken edit, QA uses selected line IDs or explicit
`speech.expected_text`; provide that text for edits whose take IDs do not match script lines. A silent edit
passes speech comparison only if its expected and recognized normalized texts are both empty.

`inspect_take.py --no-whisper` requires a transcript metadata sidecar matching source hash, language and
Whisper model. Old transcripts without provenance must be regenerated once. Japanese/Chinese caption chunks
do not insert artificial spaces. Captions check glyph coverage and require RAQM for RTL/Devanagari shaping.
Use `YESOPEN_FONT` with a suitable font on the render host for scripts not covered by bundled Manrope;
missing glyphs produce an explicit error rather than broken exported captions. Check visual layout for each
language; this change does not bundle fonts for all writing systems or certify all caption layouts.

## Verification and release boundary

Run `python3 -m unittest discover -s gpu/tests -v`. Portable tests cover all 23 language codes through the
planner, Unicode comparisons, conflicts, numerical readings, ASR language arguments, fitted WAV writing,
failed speech/export gates, CJK spacing, glyph guards and V3 manifest selection. Fitter integration tests use
mocked ASR and waveform fixtures, not synthesized Chatterbox output. The build patch was also checked against
the actual pinned upstream files, including Python compilation, without loading weights.

A production claim requires a rebuilt runtime and real samples: generate key lines in each target language
using an authorized voice, fit/transcribe, listen for pronunciation and speaker identity, then inspect a short
lip-synced take and rendered captions. Save model/version/seed, language, audio hash, ASR result and listening
status. Do not mark a language quality-validated from unit tests alone. No paid server is started by these tests.

Voice-quality acceptance follows [the dedicated validation procedure](voice-validation.md), with an explicit
listening record from [the report template](../templates/voice-validation.md).
