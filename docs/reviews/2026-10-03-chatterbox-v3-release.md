# Chatterbox V3 multilingual and voice-quality release

## Scope

- Explicit, pinned V3 T3 weights and build-time patch for the existing multilingual ComfyUI node.
- Language propagation, Unicode-aware QA and caption handling, transcript provenance, invalid-audio rejection.
- Portable planner/CPU-stage module, which depends on the already published coordinator state module.
  This does not publish the remaining local shared-server service/client/deployment integration.
- Dedicated voice-quality procedure and report; integration of reviewed Demoforge Chatterbox practices.

## Validation

Clean worktree based on remote main `cc37be5`:
`python3 -m unittest discover -s gpu/tests -v` — 71 tests, 65 passed, 6 skipped because ComfyUI is unavailable.
Python syntax and JSON checked; local documentation links and whitespace checked.
The V3 build patch was validated against the exact pinned upstream source and compiled without loading models.
The voice-cloning skill was read as source guidance; its CLI and hosted alternatives were not installed or run.

The multilingual tests check 23 language codes in plans and mocked ASR routing; fitter tests write real WAV
files from fixture waveforms. These are not synthesized V3 audio and not perceptual listening tests.
No GPU generation, rebuilt container, real V3 voice audition, language pronunciation certification or live
lip-sync verification was performed. No paid server was started. Real target-language samples and listening
remain required before a production is marked voice-quality accepted.

Existing unrelated local performance, shared-server integration and production files are excluded from this
release. The legacy English dialog template remains unchanged; multilingual dialogue uses per-line TTS.
