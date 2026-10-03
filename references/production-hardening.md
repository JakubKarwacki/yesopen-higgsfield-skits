# Production hardening: Polish salon film

This supplements the production procedure with observed failure modes. Apply it within the current user's
scope; do not start paid GPU jobs, change the server or publish a skill merely to test these rules.

## Before generation

- Resolve the latest language, script, server instruction and listening mode from the conversation into the
  current checkpoint. Retain superseded decisions as history, not competing current instructions.
- Verify each voice's original catalog/consent evidence, intended role, file hash and mappings before TTS.
  Follow [voice-validation.md](voice-validation.md), including explicit user-deferred listening.
- Confirm server identity and actual scheduler. Use one queue and separate project/revision/artifact paths.
  Local dirty code is not deployed code. Do not alter another production's services or shared dependencies.
- Run `python3 "$SK/scripts/verify_voice_sources.py" "$PROJECT"` before dialogue batches and keep the result.
- Lock fitted audio before lip sync; any replacement invalidates dependent takes and QA.

## Dialogue prompt and retry checklist

Use START → ACTION → END → HOLD → NEXT. For a reverse-angle dialogue shot explicitly specify one visible
speaker, a stable off-camera gaze target and locked framing. During speech, lips and jaw visibly articulate
the supplied audio; only after speech do the lips close and the character hold the final pose. A prompt that
emphasizes a closed mouth throughout can suppress articulation. Do not force off-camera gaze for a script
that actually requires talking to the viewer.

Exclude only relevant defects through `negative_prompt`: generated subtitles/text, extra people or foreground
heads, unwanted eye contact, zoom and cuts. Inspect actual frames and motion; negative text cannot guarantee
compliance. Use the corrected `cfg_first` setting only as a pilot-tested experiment, not a new universal default.
Record full parameters, seeds, input hashes and failed candidates. See [performance-controls.md](performance-controls.md).

When a two-person shot assigns speech to the wrong person or fails to finish a gesture, diagnose before another
retry. A speaker close-up followed by a complete silent reaction is allowed when it preserves the approved joke,
action and continuity. It must actually show the reaction and hold, not conceal a missing event behind a cut.
After two further failures of the same defect, change the cause (prompt conflict, framing, starting still or
speaker assignment) instead of blindly generating more seeds. Reuse the locked dialogue for visual retakes.

## Before delivery

- Use the common brand font/overlay helpers; inspect a phone-sized caption sample before a full render.
- Sum the actual fitted dialogue, completed actions, holds and end card to the approved frame count.
- Review both sides of every cut and dense frames around rapid events. Verify the exact exported revision,
  not an earlier preview. Keep human listening unreviewed when deferred; record uncertain names honestly.
- Check delivered master and compressed copy: frame count, complete dialogue, levels, captions and filenames.
  Verify local downloads with hashes. Use native local previews and truthful status messages.
- Send only to the explicitly requested destination; WhatsApp steps are in [formats-delivery.md](formats-delivery.md).
- Follow the latest server instruction. An explicit leave-running instruction forbids automatic drain/stop/delete.

## Implementation boundaries

The workflow mapping, optional negative-prompt forwarding and offline voice-source checker have regression tests. Voice provenance,
listening deferral, native-queue selection and visual judgment above are operator obligations; this document
does not claim that legacy clients or the shared coordinator automatically enforce them. Never manufacture
an approved runtime gate to conceal unsupported behavior.
