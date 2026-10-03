# Pre-push review: multilingual V3 and voice validation

## Review boundary

Reviewed remote `d378877` against the requested language support, explicit Chatterbox Multilingual V3,
voice-quality instructions, community-skill integration and publication to main. Reviewed a clean checkout,
not only the dirty local index. All files in that remote commit also exist locally. Local “untracked” status
for some published files comes from the working branch still pointing to an earlier commit; it is not proof
that the files were omitted from remote.

## Findings fixed before this push

1. **P1 — Circular final speech QA.** Expected dialogue preferred generated captions, allowing a generated
   speech error to agree with its own transcription. QA now uses approved lines in edit order or explicit
   `speech.expected_text`. Ambiguous/partial edits require explicit text; silence must be declared explicitly.
2. **P1 — Stale voice reuse.** A padded voice was reused when durations matched even if the source changed.
   Reuse now requires matching source SHA-256 and padding; metadata is invalidated before rebuilding.
3. **P1 — Parallel fitting lost updates.** Independent workers could overwrite shared fit.json and its fixed
   temporary path. Results now merge under a process lock with per-line receipts; CPU stages read that receipt.
4. **P2 — Inconsistent language inheritance in editing.** Takes read project.json alone. They now resolve both
   files and reject conflicts, matching the rest of the language path.
5. **P2 — Validation report not bootstrapped.** New projects now receive voice-validation.md automatically.
   Unknown --only line IDs now fail rather than silently reporting success with no fitting work.

## Requirements coverage

| Requirement | Included evidence |
| --- | --- |
| Explicit V3 rather than implicit V2 | Docker build patch with source hashes; pinned model filename/revision/SHA-256; templates manifest |
| Language propagation | languages.py; project creation; TTS batches; fitting; inspection; edit; fallback transcription; final QA |
| Unicode and non-Latin text | Unicode normalization; CJK caption spacing; glyph and shaping guards; supported-code tests |
| Voice selection and validation | voice-validation.md; report template; SKILL.md entry; QA checklist gate |
| Chatterbox community skill integration | pinned Demoforge source and explicit adapter mapping in chatterbox-practice.md |
| Safe resource completion | already published SHUTDOWN.md and drain tests; voice procedure preserves current user instruction and disks |
| Reproducible scoped release | clean checkout tests and staged-file scan; unrelated local experiments excluded |

## Validation

Clean checkout suite after fixes: 76 tests, 70 passed and 6 skipped because ComfyUI is unavailable.
Regression coverage includes independent script reference, explicit silence, changed audio of identical
duration, 20 concurrent checkpoint writers, language inheritance/conflicts and automatic report creation.
Syntax, JSON and documentation links checked; staged files scanned before commit.

## Limits that remain explicit

No paid server was started. Real V3 synthesis, a rebuilt GPU container, per-language listening and lip-sync
quality remain unverified. Model support and portable tests do not certify pronunciation or “highest quality”.
Non-Latin caption rendering may require a suitable font and RAQM on the render host. Human/listening review
is an operator gate, not an automatic coordinator guarantee. The complete local shared-server service/client
and unrelated performance experiments were deliberately outside the language/voice release; its portable
planner module does not itself install or expose that service.
