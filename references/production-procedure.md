# Production procedure: readiness, pilots, recovery and retirement

These operational checks apply before full generation and on every resume. They supersede older automatic
stop/delete shortcuts. They prescribe the operator's actions; they do not imply that a CLI automatically
enforces every check. Existing user approval remains valid. Ask only for missing material decisions or a
change outside that approval.

## 1. Prepare a reproducible production before paid work

Record the approved script, language, formats, runtime constraint, cast, voice rights, source paths and
resource retirement instruction. Missing material requirements must be resolved rather than invented.
Record code commit plus any dirty changes, model identifiers and nonsecret configuration. Verify that the
installed release contains each required command, dependency and input, and that output directories are
writable. Do not treat an untracked local script as a published capability. Fix reproducibility gaps before
relying on unattended production; never publish private reference footage or credentials.

Language support is a preflight check. The local shared planner reviewed on 2026-10-03 rejects non-English
projects; the published shutdown fix does not supply a complete Polish pipeline. Do not merely remove a
language guard. Validate Polish normalization (including diacritics and numbers), ASR language, audio fitting
and captions together on a short sample. Preserve the validated implementation and version. If unavailable,
report the specific capability gap before paid video generation. Do not silently run English QA on Polish.

## 2. Lock audio and estimate the real edit length

Generate and fit voices before their video takes. Listen to key lines for wording, intonation and pauses;
ASR alone does not assess acting or naturalness. Reuse accepted audio when correcting only visual action.

Calculate the timeline from actual fitted audio, silent beats, completed movements, holds and the end card.
Count speech and movement that happen simultaneously only once. Record each shot's duration and the sum.
Resolve a conflict with the approved length before the full video batch; never remove an action's ending to
force an estimate. Treat earlier production durations and prices as historical measurements.

## 3. Run representative pilots before the full batch

Select a dialogue shot and each distinct risky action. For a salon film this usually means dialogue,
placing a prop and standing/changing position. Use only applicable categories; do not add unnecessary scenes.
Check actual text-free output, face/framing, voice, lip sync, completed action, hold and next-shot state.
A negative prompt is not evidence of absence of subtitles. OCR can flag suspicious frames but cannot certify
all frames. View the result; fix a shared defect and repeat the affected pilot before submitting its batch.
This is the operator's quality check, not an extra user permission request.

Every shot must specify START → ACTION/DIALOGUE → END → HOLD → NEXT before its still is made.
For risky motion use a supported final-frame reference where available; verify model and wrapper support.
If a pilot cannot both speak and finish a movement, separate them while preserving approved speech and
continuity. Do not assume every scene requires this split.

Review rapid events densely (at least eight frames per second around transitions), plus first/last frames
and both sides of each cut. Confirm the entire event visually. Select the cut after completion and its hold;
a longer generated tail alone does not retain it in the edit. Regenerated shots require new boundary review.
Cropping invented text must not remove faces or necessary action; regenerate when a usable crop is impossible.

## 4. Schedule and resume without paying twice

Use one scheduler for a shared host. Do not mix unmanaged batches with coordinator work. Keep one GPU worker
until a controlled measurement supports more. Overlap supported CPU QA, downloads and edit preparation with
GPU generation within measured host capacity. Group model-compatible work where this does not bypass pilots,
starve another production or delay necessary feedback.

Before claiming that two or three simultaneous generations help, compare the same representative batch at
one and two workers: total elapsed time, memory peak, failures and cost. Test three only if earlier results
justify it. A benchmark requires an authorized paid session; do not start a machine merely to update procedure.

Before every external batch log nonsecret configuration, operation and item IDs. Save each completed result
or small batch, accepted/skipped decisions, errors and retry/backoff reasons. Keep provider job IDs and input
hashes. On resume reconcile submitted, running, failed, unknown and completed jobs against provider/coordinator
evidence. An unknown result is not permission to resubmit. Report meaningful progress during long stages.

Reuse a result only if its inputs and relevant code/model/config versions still match. Rebuild affected
segments and descendants after a change. Reuse word times only when they match the exact edited audio;
trimming, tempo changes and removed pauses require transformed and verified times or a fresh transcription.
Cache reuse does not replace independent checks of the final export. Where automation is absent, perform and
record these steps explicitly rather than claiming they happened automatically.

## 5. Keep one current checkpoint, with separate history

The checkpoint must distinguish current state from past instructions/events. Record project/revision/run,
last verified stage, input versions, job attempts, selected takes, cut boundaries, pending work, actual blockers
and next action. Save updates atomically. Preserve prior decisions in an append-only event history.

Resource state records the latest authorized operation and its source/time, instance identity, protected
resources, verified downloads, actual blocking work, executed operation, provider evidence and verification
time. After completion clear obsolete *current* blockers and retain them only in history. A previous instruction
in a note or checkpoint must not override a newer explicit user instruction. Conflicting state requires
reconciliation with evidence, not an invented claim that work is still running.

These are a recording contract, not new CLI parameters or a guarantee of an implemented checkpoint schema.

## 6. Finish QA and retire resources as authorized

Verify every delivered format, caption framing, complete actions and audio. Watch the final with sound when
possible; state explicitly if listening or another required check was not performed. ASR similarity and
loudness are not a substitute for listening or visual lip-sync review.

Download finals and sources needed for corrections; compare manifests, file sizes and hashes before retiring
the host. Follow [the shutdown checks](../gpu/SHUTDOWN.md). A finished film waiting only for final review does
not represent running computation. The drain result describes coordinator tasks, so also check actual
ComfyUI queues, CPU exports and transfers across all projects. Never interrupt unrelated work.

Execute the operation already authorized by the user. A request to stop does not authorize Delete/Terminate;
protect every disk the user asked to retain. Verify provider state after the operation and write the evidence
to the current checkpoint. Report retained resources and possible storage charges. Do not claim all billing
has ended merely because computation stopped. A pending review must not become a reason to request redundant
permission or leave an otherwise idle paid host running.

## Acceptance of this procedure

The next production should demonstrate: validated language path; timed audio; accepted representative pilots
before their batch; visible completed actions and continuous joins; resume without duplicate completed jobs;
verified local deliverables; and provider-confirmed retirement consistent with the current instruction.
GPU throughput gains remain unverified until measured on an authorized session.
