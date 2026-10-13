# Grill: decide with the user, one question at a time

Adapted from the idea of [robmitt/grill-me-skill](https://github.com/robmitt/grill-me-skill) (interview the user
until every branch of a plan is resolved; the repository has no licence, so nothing is copied). Here the interview
is bound to the skit's gates: it settles what changes the joke, the cast or the bill, and nothing else.

## When

| Grill | Where | Settles | Ends with |
| --- | --- | --- | --- |
| 1. Brief | Phase 0, before the reference is captured | who it is for, the pain, the YesOpen feature, language, length, number of characters, platform, tone, the reference link | `decisions.md` → Brief; Phase 1 starts |
| 2. Script | Phase 2, after the first draft of `script.md` and `lines.json` | the open decisions of the draft: frame, straight man, escalation steps, the turn, the product line, the button and end-card line, each character's look and voice | the script's yes (Gate 2), recorded in `script.md` |
| 3. Session | before anything is billed (GPU machine or Higgsfield jobs) | voices picked and listened to, provider and card, budget, what is reused, the Slack note | the yes to start the machine |

Skip a grill whose answers are already on record (an earlier `decisions.md`, the user's message). A re-cut or a new
format of a finished skit needs none.

## How to ask

- **Look it up before asking.** Anything the files answer is not a question: `project.json`, `script.md`,
  `lines.json`, `assets/cast/`, `references/asset-catalog.md`, the claims in `business-card/messages/en`, prices
  in `references/gpu-engine.md`, the provider's availability. Say what you found in one line instead.
- **One question per message, with AskUserQuestion.** Never a question in plain text, never several at once
  (the one exception: when the user asks for speed, up to four independent questions in one call).
- **2–4 concrete options**, each a real direction for this skit ("a job interview where the candidate is the
  owner's to-do list"), not "yes / no / maybe". Put the recommended option first and mark it "(Recommended)";
  the description says what it costs or changes. The user can always type their own.
- **Parents before children.** Resolve the decision others depend on first (frame before escalation steps,
  number of characters before their voices, language before voice candidates). Never ask about a branch an
  earlier answer has closed.
- **Acknowledge in one or two sentences**, then the next question. Write each answer to `decisions.md` as it
  comes, so a broken session resumes where it stopped.
- **Stop when the tree is resolved**, or when the user says to go on ("dalej", "you decide"): then take the
  recommended option for every open branch, list those defaults in the summary and mark them `default` in
  `decisions.md`.
- **Never grill past a rule.** The non-negotiables, the voice and face rights (rule 5), the model licences
  (MiniMax H3 only with written consent) and the provider rules are not options to offer.

## What to ask, by grill

**1. Brief.** Business type and the owner's daily pain; which YesOpen feature is the punchline (only claims that
exist in the business card); language; target length; how many characters; platform first (9:16 always made);
tone (deadpan, absurd, warm); the reference link, or a known frame (breakup, intervention, job interview, therapy,
parent-teacher meeting) when there is none.

**2. Script.** Only the draft's open decisions, in this order: the frame and who is the straight man; the engine
(what the audience sees that a character does not); the escalation steps and whether each has the same shape; the
turn; the one honest product line; the button and the end-card line; then per character, from the cast table:
look, place, START/END variants, and the voice (age, temperament, accent, source per rule 5). Offer two or three
alternative lines where a line is the decision. Do not re-open what the user approved.

**3. Session.** Each character's voice picked from auditioned candidates and listened to (or listening explicitly
deferred, `references/voice-validation.md`); what is reused from earlier projects (stills, voices) and what is new;
provider and card from the availability you just checked, with the price per hour; the budget ceiling and when to
stop; that the Slack note is out (one machine per disk, `references/nebius-operations.md`). End with the estimate
from `gpu_batches.py estimate` and ask for the yes to start.

## `decisions.md` (in the project folder)

```markdown
# Decisions: <slug>

## Brief (grill 1, 2026-10-08)
| # | Question | Answer | Source |
| --- | --- | --- | --- |
| 1 | Who is it for? | small business owners who are overworked | user |
| 2 | Language | English | user (recommended) |
| 3 | Number of characters | 2 | user |
| 4 | Platform first | 9:16 Reels/Shorts | default |

## Script (grill 2)
...

## Session (grill 3)
...
```

`Source` is `user`, `user (recommended)` when the user picked the recommended option, `files` when it was looked up,
or `default` when taken without asking. The summary at the end of each grill is this table, shortened, in the
user's language.
