# Voice validation: multilingual Chatterbox V3

Required reading before generating dialogue, selecting a voice, changing language/model, or accepting a final
film. The aim is the best version within the approved scope, with evidence of listening and correction.
No model name, ASR score or technical test alone establishes natural, high-quality speech.

## 1. Establish the voice and runtime

- Record target language, intended accent, character, emotion, pace, and pronunciation of names and numbers.
  Retain established choices. Ask about material missing creative decisions; do not invent a new accent or persona.
- Use an authorized synthetic voice or a speaker with recorded permission. Select a clean 5–15 second reference:
  one speaker, natural speech, no music, overlapping voices, clipping, heavy denoising or long silence. Listen
  to it. Preserve the reference file/hash and character mapping across scenes and language versions.
- Verify the actual deployed loader and model, not only project configuration. The V3 filename, pinned revision
  and SHA-256 must match `references/multilingual.md`; record the runtime version and loader log. Existing V2
  cache files are not evidence of a V3 run. Do not substitute English `tts-dialog` for multilingual line generation.
- Record nonsecret generation parameters and seed per candidate. Version changes invalidate previous quality
  validation; keep older approved audio available for comparison rather than overwriting it.

## 2. Validate a representative sample before the full voice batch

Apply [the Chatterbox skill adaptation](chatterbox-practice.md): compare two clean reference excerpts with
identical text/settings/seed when choosing a new voice; record duration and listen for accent transfer.
Use only controls actually exposed by our wrapper. Lock the reference before comparing generation seeds.


Use approved script lines covering: a neutral sentence, a question/emotional beat, a key joke, and difficult
names/numbers or sounds in that language. Include a longer line with a pause if present. Reuse a line for
several checks; avoid unrelated paid samples. Compare the standard two candidates per line at matched playback
level, using the same reference and text. Do not select a louder candidate simply because it sounds stronger.

For every new target language, assess both pronunciation/naturalness and retention of character identity.
A good Polish sample does not validate German or Japanese. A translated line must sound natural in its target
language; translation, model coverage and voice quality are separate checks.

Record the chosen candidate and the reason. A shared defect (wrong accent, persistent noise, unstable identity)
blocks the affected full batch until the reference/settings/model integration are corrected. This is an
operator quality gate within existing authorization, not an extra approval request for every line.

## 3. Check each line before generating its video

First run fitting/ASR in the declared language. Compare with the approved spoken script, including sentence
endings, negation, brand names, dates and quantities. Unicode character similarity is a screening measure:
`0.9` is the implementation's triage threshold, not an acceptance threshold for a wrong word. Even a high
score must fail a meaning-changing substitution, omitted punchline or incorrect number. Never edit expected
text merely to make a bad recording pass. Approved numeric aliases describe an intended reading; they must
not hide an error. Captions/transcripts generated from that same bad audio are not independent script evidence.

Then listen to every selected fitted line, including the beginning, all internal pauses and the last syllable:

| Check | Required result | Reject examples |
| --- | --- | --- |
| Wording | Exact intended meaning and all approved words | Added phrase, missing negation, wrong price, truncated ending |
| Pronunciation | Correct target-language sounds, stress, names and numbers | Misread brand, foreign accent inconsistent with brief |
| Naturalness | Human-like rhythm and connected phrases | Robotic stresses, stretched vowel, syllable repeats |
| Acting | Intended question, emotion, comic emphasis and pause | Flat punchline, question intonation on an intended statement |
| Identity | Same character and consistent voice within the film | Pitch/timbre drift, sudden speaker change |
| Signal quality | Clean, intelligible speech without unwanted artefacts | Click, clipping, buzz, hum, metallic warble or unintended breath |
| Boundaries | Complete first/last syllables and intentional pauses retained | Hard cutoff, shortened dramatic beat, appended mumbling |

Log pass/fail and a short timecoded note for defects. A reviewer must actually hear the file; viewing a waveform
or reading ASR does not count as listening. Where the agent cannot listen, or cannot assess the target language,
mark the respective checks `not_reviewed` and obtain a competent listener's assessment before calling the voice
quality-validated. Do not label a guessed assessment as native review or claim “highest quality” without evidence.

## 4. Fix the cause and recheck only affected material

1. Wrong wording/pronunciation: verify the script, spoken number form and language; regenerate the line with
   a new seed. A pronunciation spelling may be used for TTS while retaining the approved caption spelling.
2. Wrong rhythm/acting: adjust punctuation, pause or supported delivery controls; change one variable at a time.
   Keep intentional comic pauses; automated silence shortening must be listened to afterwards.
3. Unstable character/noisy signal: replace or clean the reference only if doing so preserves authorization and
   the agreed voice. Recheck the representative set and affected lines for identity consistency.
4. Clipped beginning/end: correct fitting boundaries or regenerate. Do not conceal missing speech with captions,
   a fade or a cutaway. Avoid aggressive denoising, time stretching and volume boosting as repairs for bad synthesis.
5. Make bounded retries within the authorized budget. After two additional failed candidates for the same defect,
   stop automatic retries and diagnose it before spending more. Escalate only a genuine scope/budget/creative decision.

Keep rejected candidates and reasons in the production log. Once a line is accepted, lock its file/hash before
lip-sync generation. A visual retake reuses approved audio unless there is an audio defect. A subsequent change
to audio invalidates its word times, lip-sync take, affected edit segments and final QA.

## 5. Validate voice in the assembled film

- Listen once to the entire final export while watching, then replay every questionable join and key joke.
  Check lip sync at normal speed and around visible plosives/word endings; timestamps alone cannot prove it.
- Check voice identity across consecutive shots, natural loudness between characters, complete words at cuts,
  conversational pace, and whether music/effects obscure speech. Check on headphones and a phone speaker when
  available; explicitly record an unavailable playback condition rather than claiming it was tested.
- Run technical QA on the final mix: integrated loudness −14 ±1 LUFS and true peak ≤ −1.0 dBTP under the current
  project policy. These are final-mix targets, not a reason to normalize each raw syllable or overcompress acting.
- Run final ASR against the approved edited dialogue in the target language. For a captionless/partial/reordered
  edit, supply `speech.expected_text` when the line map cannot represent what is actually intended to be heard.
  Verify caption spelling separately; captions must not be used to disguise incorrect pronunciation.
- A regenerated, recut, time-stretched or remixed version requires rechecking its affected checks and listening
  to the final assembled result. Do not carry approval from a different file hash.

## 6. Evidence and acceptance

Use `templates/voice-validation.md` in the production directory, one report per language/version. Record model,
code, reference and output hashes; candidate parameters; automatic checks; listening reviewer/method/date;
line decisions and unresolved defects; and final playback/mix/lip-sync results.

Accept only when required checks are passed and no critical defects or unreviewed required checks remain.
Report `needs_review` for missing listening evidence and `rejected` for defects; technical pass alone remains
`technical_only`. Distinguish “model supports this language” from “this exact voice and film were reviewed”.
The Markdown report is an operator gate; it does not claim that the current coordinator automatically parses
or enforces human listening approval. Existing runtime review gates must be used honestly.

After verification and confirmed local downloads, execute the current authorized retirement operation and
preserve protected disks. Waiting for final review is not active compute; follow `gpu/SHUTDOWN.md` rather than
leaving an idle paid server running solely for listening/review.

## Explicitly deferred listening

If the user explicitly asks to continue without their current voice audition and review the finished film later,
record the instruction, date and scope in the checkpoint and voice report. Continue authorized generation and
editing after automatic checks and operator visual inspection. Keep listening-dependent fields `not_reviewed`,
voice quality `technical_only`, and final acceptance `needs_review`. Do not mark a runtime human-review gate
approved, fabricate a reviewer, or silently bypass a coordinator gate that does not support this state. Prepare
independent work and report the exact runtime limitation if such a gate truly blocks execution.

This is permission to defer missing listening evidence, not permission to ignore known wrong words, missing
syllables, clipping, unknown voice rights or a budget limit. Record uncertain brand pronunciation separately;
never add an ASR alias merely to obtain a passing score. User unavailability alone is not this authorization.
Do not repeat audition requests covered by the instruction. A later request to send the finished file to a
specified group authorizes that delivery; it does not retroactively prove listening or erase QA limitations.

## Source verification before the first TTS/video batch

For each selected character, record in `voices/provenance.json`: selected local file, SHA-256, original source,
synthetic origin or written consent evidence, intended character/voice description, and review state. Inspect the
actual catalog or consent evidence; a filename such as `customer-synthetic.wav` is not sufficient provenance.
Check that `lines.json` and `project.json` point to the same selected voice. A reused voice from another film
must pass this check again for the intended role before spending time on its TTS and lip-sync takes.

Record the selected reference hash with the line generation inputs, then lock each selected fitted WAV hash
before video generation. A changed reference invalidates that character's generated lines, corresponding
lip-sync takes, edit selections and QA; a changed WAV invalidates its take and descendants. Preserve old files
as rejected/superseded, give replacements new job identities, and explicitly exclude old selections from the
final manifest. These are required operator checks, not a claim that all legacy clients enforce them.

Before preparing or submitting dialogue batches, run this free local preflight and retain its output:

```bash
python3 "$SK/scripts/verify_voice_sources.py" "$PROJECT"
```

The selected record requires `character`, `candidate`, `sha256`, `source`, `rights_basis` (`synthetic` or
`written_consent`), `evidence` (catalog/consent reference) and `voice_description` (intended role and voice).
Historical manifests lacking these fields must be reconciled against actual evidence, never auto-filled from
a filename. The checker rejects missing/ambiguous records, mismatched cast paths and changed file hashes.
It validates declarations and identity, not their truth, acoustic gender, audition quality or written consent
itself. The operator must read the evidence. This standalone check does not automatically intercept direct
ComfyUI requests or coordinator submissions; run it explicitly before both TTS and take batches.
