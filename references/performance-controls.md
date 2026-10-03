# Talk workflow controls

## Corrected CFG mapping and optional negative conditioning

`cfg_first` now targets `340:315`, the guider feeding initial sampler `340:291` (sigmas begin at 1.0).
The previous mapping targeted `340:290`, the second-stage guider feeding sampler `340:310`; old experiments
labelled first-stage CFG therefore cannot be treated as first-stage evidence. Default CFG remains 1.0, so
this mapping correction leaves default graphs unchanged. Revalidate any explicitly configured CFG experiment.

`take.negative_prompt` / `lines[].negative_prompt` is now forwarded to `340:314`, the negative text encoder
connected to first-stage conditioning. A line overrides the project setting; omission preserves the workflow's
existing text. Use the supported parameter rather than a project-local hardcoded node override. On the Polish
salon pilot, first-stage CFG 2.0 plus targeted negatives removed invented subtitles, but that combined observation
is not a universal optimum or an isolated proof of causation. Keep the second stage unchanged and inspect a pilot.
