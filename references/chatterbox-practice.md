# Chatterbox skill integration for YesOpen

## Sources and adaptation boundary

Reviewed on 2026-10-03:

- Community skill [Demoforge voice-cloning](https://github.com/itsskofficial/demoforge/blob/906276e190561b7b367d4703e64dad46a30a209e/skills/voice-cloning/SKILL.md),
  revision `906276e190561b7b367d4703e64dad46a30a209e`.
- Primary model documentation [Resemble Chatterbox](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/README.md),
  revision `5de7a54aa4e5e2baadb0182dde554908b48b85c2`.

The community skill is useful operational guidance, not an official Resemble skill or evidence of V3 quality
in our environment. We integrated the practices below into this skill, without installing its CLI, replacing
our scheduler, uploading reference audio, or adding a hosted provider. The reference is pinned for review;
external instructions do not override the user's scope, voice permissions or resource-retirement policy.

## Practices carried into the voice-quality procedure

From Demoforge: audition two different clean excerpts of the same authorized voice, measure delivery duration,
and generate dialogue before committing scene lengths. Prefer speech-friendly sentences and explicitly
written number readings. Keep reference audio private and preserve the chosen voice across revisions.

Our adaptation: use the existing 5–15 second reference contract, hold text/settings/seed constant when comparing
reference excerpts, then lock the winner. Record audible results rather than assuming a longer clip helps.
Measure pace within the target language and scene; a universal narration words-per-minute target is unsuitable
for comedy and languages whose writing does not separate words with spaces. Resolve script changes under
existing approval rules. No default time stretching: a changed waveform requires new timestamps and lip sync.

## Parameter audition for the installed multilingual node

Use the existing `tts` workflow. Begin with the production's accepted settings, or model defaults of
`exaggeration=0.5` and `cfg_weight=0.5` for a new voice. These are starting points, not a quality guarantee.
The manufacturer's general guidance suggests trying lower `cfg_weight` around `0.3` for an overly fast
reference and balancing stronger exaggeration with lower guidance. Compare one changed control at a time.
The guidance predates some V3 validation: recheck naturalness, identity and intelligibility on V3 samples.

Prefer a reference in the intended spoken language. When an authorized cross-language reference transfers an
unwanted accent, the manufacturer suggests testing `cfg_weight=0`; treat it as a candidate requiring a fresh
identity/pronunciation review, not an automatic correction. Never use Turbo-specific `[laugh]` or `[cough]`
tags as if the multilingual node supported them.

Map supported project controls to actual inputs:

| Our input | Meaning | Validation |
| --- | --- | --- |
| `lines.json.language` / `project.json.language` | Same declared language, label/code respectively | Must resolve to the same supported code |
| `characters.<actor>.voice` | Authorized reference audio path | Audition, file hash, no noise/overlap |
| Line `exaggeration` | Expressiveness control | Listen for unwanted speed/intensity changes |
| Line `cfg_weight`, falling back to `voice.cfg_weight` | Guidance control | Compare pace, accent and identity |
| Candidate `seed` | Recorded generation variation | Log it; a seed alone is not a voice identity |

Do not copy Demoforge-specific `--pace`, `--gap` or `--max-chars` into our CLI: those switches are not exposed
by the YesOpen `tts` wrapper. Avoid inventing a direct speech-rate parameter. The actual node schema and our
parameter mapping take precedence over examples from another tool.

## Where this runs in the production

1. Before the voice batch: confirm deployed V3, approved voice and language; compare reference candidates.
2. During sample selection: record duration, settings, pronunciation and acting; select and lock the reference.
3. Before video generation: complete per-line fitting and listening from [voice validation](voice-validation.md).
4. After editing: independently check dialogue, lip sync and the final mix, saving the report from
   [the validation template](../templates/voice-validation.md).

The implementation supplies language propagation and V3 selection. Actual listening and production-language
acceptance remain explicit checks. No paid session or hosted fallback is started by this integration.
