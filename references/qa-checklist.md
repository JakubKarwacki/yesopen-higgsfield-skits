# QA checklist, gate by gate

Tick every item. A gate that fails stops the next paid step. Items marked GPU or Higgsfield apply to that
engine only.

## Gate 1: reference analysis

- [ ] `reference/analysis.md` written in our own words: form, beat map, engine, editing grammar.
- [ ] Frames and transcript only in `reference/private/` (git-ignored, never published).
- [ ] "What we take / what we do not take" filled in.

## Gate 2: script (needs the owner's explicit approval)

- [ ] Every edit shot has START, ACTION / DIALOGUE, END, HOLD and NEXT; endings are observable completed events.
- [ ] Adjacent shots and recurring characters preserve pose, gaze, prop state and screen direction; duration includes speech, completed action and hold.

- [ ] It is a skit, not a product demo: the first 10 seconds contain no feature.
- [ ] One familiar frame, one engine, 3–4 escalation steps, a turn, a button, an end-card line.
- [ ] Every product claim is in the claims table with a file and line in `business-card/messages/en`.
- [ ] No line, name or signature joke copied from the reference.
- [ ] Lines under ~12 words; numbers written as words for the take prompts.
- [ ] Cost estimate given. GPU: `gpu_batches.py estimate` and the session's hours at the machine's price.
      Higgsfield: `hf-job cost` for every take (the price per second depends on the resolution).
- [ ] GPU: `lines.json` written from the line table; every character has a voice sample (5–15 s, one clean
      synthetic voice) and a still or a `look`.
- [ ] Approval recorded in `script.md` (who, date). GPU: the yes covers starting the machine for this session.

## Pre-batch gate: readiness, audio and representative pilots

- [ ] Installed code/model/config versions and actual language support verified; no unpublished dependency assumed.
- [ ] Polish normalization, ASR, fitting and captions validated on a short sample if producing PL.
- [ ] Actual audio duration plus action, holds and end card calculated; any conflict with approved duration resolved.
- [ ] Representative dialogue and every distinct risky action tested before its full batch (e.g. prop placement and standing).
- [ ] Pilots checked for invented text, framing, identity, speech, completed action, hold and next-shot continuity.
- [ ] Shared failure corrected and pilot rechecked before submitting affected remaining takes.
- [ ] Checkpoints identify accepted inputs, attempts, job IDs and the next pending step.

## Gate 3: cast stills

- [ ] Every shot starting image matches its planned entry state; changed poses/props are not reset to the original cast portrait.

- [ ] Four candidates per character on one sheet.
- [ ] Picked still: no logos, no readable text, neutral face with lips closed, prop visible, face large enough
      for a 1.4x punch-in, real local business look, nobody in the background.
- [ ] Higgsfield: `stills/picked.json` and the args saved. GPU: the pick in `lines.json` →
      `characters.<name>.still`; the batch file and `jobs.jsonl` kept; phones with their back to the camera.

## Voice-quality gate before lip-sync generation

- [ ] `references/voice-validation.md` followed; report copied from `templates/voice-validation.md`.
- [ ] Actual runtime/model version confirmed; representative voice samples reviewed per target language.
- [ ] Every selected fitted line listened to against the approved script: pronunciation, meaning, acting, identity, signal and boundaries.
- [ ] Names/numbers checked independently of ASR similarity; no critical defect or missing required listening check.
- [ ] Accepted audio hashes locked; changing audio invalidates affected word times and lip-sync takes.

## Gate 4: takes

- [ ] Actual submitted prompts contain START, ACTION, END and HOLD, including each beat of a long take.
- [ ] Visually verified each required ending and usable settling beat; checked last frame against the next entry. A prompt or longer tail alone is not proof.

- [ ] Higgsfield: `hf-job` used (jobs.jsonl has every request id).
- [ ] GPU: `fit_lines.py` passed every line before any take was made (`lines/fit.json`); the key lines
      (`key_shots`) listened to: right words, the script's "?" and "!", no mumbling.
- [ ] `inspect_take.py` run on each take: all lines present and in order, right words, one voice.
- [ ] Lip sync holds on every line (sheet), no music, no extra people, no on-screen text.
- [ ] GPU: no zoom or push-in at the end of a take; no phone screen facing the camera.
- [ ] Silent actions happened where the jokes need them.
- [ ] Room tone at least 3 dB under `speech.thr`.
- [ ] Host requirements for remaining editing/QA are recorded; retirement follows the authorized operation,
      verified downloads and actual shared workload, not merely the end of GPU generation.

## Gate 5: edit

- [ ] Every cut follows completed speech/action and retains the scripted reaction; reviewed both sides of every join, including off-screen prop continuity.
- [ ] Missing required endings were corrected in the take; regenerated takes had their cut boundaries reviewed again.

- [ ] Preview of the first 8–10 cuts shown and approved before the full edit when the pacing is new.
- [ ] Every cut has a `note` with the script line.
- [ ] Banners show the exact approved text and appear on the ding; nothing covers a face.
- [ ] Captions: every chunk on the right speaker and shot (`qa-<fmt>-captions.jpg`), spelling and
      punctuation as in the script.
- [ ] End card: right tagline, URL, 2.6 s, ding.

## Gate 6: final, per format

- [ ] `qa_report.py`: frames actual = planned (`frames.ok`), loudness −14 ±1 LUFS, true peak ≤ −1.0 dBTP.
- [ ] `--whisper` on the 9:16 master: word match ≈ 1.0 with the caption words (the gym skit: 1.0, no differences).
- [ ] Watched once from start to end with sound; final voice-validation report records reviewer/method, file hash, lip sync, joins, identity and mix.
- [ ] Final ASR compared to approved edited dialogue; no incorrect meaning accepted because of a high similarity score.
- [ ] 4:5, 1:1, 16:9 checked with sheets: faces framed, captions readable, banners clear of faces.

## Gate 7: delivery

- [ ] Clickable local links to the master, share and web files in the reply.
- [ ] Web version sent for preview; Artifact page only if asked.
- [ ] Nothing posted publicly without an explicit request.
- [ ] `script.md` updated with what changed in production and the final files.

## Gate 8: infrastructure completion

- [ ] Required finals and correction sources downloaded; manifest, sizes and hashes verified.
- [ ] Current user instruction identifies Stop versus Delete and protected disks/resources.
- [ ] All shared compute/export/transfer work reconciled; waiting final review not mislabeled as running work.
- [ ] Admission drained where supported; actual queues/processes checked; unrelated work preserved.
- [ ] Authorized provider operation performed and resulting state verified with timestamp and instance ID.
- [ ] Current checkpoint has no obsolete active blocker; history retained separately.
- [ ] Retained resources and possible disk charges reported accurately.
