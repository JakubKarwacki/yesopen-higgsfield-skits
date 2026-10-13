# ComfyUI pipeline coverage — 12 October 2026

> Zapis historyczny implementacji lub wykonanej produkcji. Od 13 października 2026 głównym wyborem projektu jest MiniMax H3, a Wan 3.0 hostowany lokalnie jest alternatywą do testów. Nazwy poprzednich modeli i wyniki poniżej opisują stan z daty raportu; bieżące instrukcje i status migracji: references/video-models.md.

## Implemented after the audit

The findings below describe the pre-fix state. The production workflow now maps `*` over all project lines,
uses the project's language, aggregates the completed takes before editing, and saves the processed video
after upscale/interpolation. Optional branches start muted; the dialog no longer bypasses the production
audio approval. A B-roll saver is present in the optional LTX-2.5 branch.

Fitted audio, finished takes and the music bed support lazy reuse with source signatures and file hashes.
The music saver updates the project music path; the editor waits for it. A separate audio approval records
hashes and rejects changed audio until reviewed again. QA checks all four formats, fails on negative checks,
and delivery verifies QA against current master hashes. Encoding covers all formats; a final file manifest
and a client-side download verifier were added. Cache lookup follows the selected project and unchanged
checkpoint writes preserve timestamps.

Verification: nine node regressions passed in the CPU ComfyUI image. The live API accepted a batch/language
prompt and executed its closed gate without producing media. All 81 root nodes and 92 links were checked;
the deployed graph matches the repository. The rebuilt stage layout has a finite score and 44 root reroutes.
No GPU generation or complete multi-line film render was run. Browser geometry was not remeasured.

Human tasks remain explicit: local reference analysis, authoring/approval of script and cuts, cast selection,
audio/visual review, verification of the downloaded project and shared-workload checks before retirement.
The CPU preview is intentionally kept available during this work; the graph never retires infrastructure.

## Conclusion

The graph covers generation and post-production stages visually, and its YesOpen nodes execute real scripts. It is not yet a complete project orchestrator. A Run generates one selected line; a complete film still depends on externally prepared inputs, previously generated takes and manual review.

## Findings from the generator and node implementation

1. **One selected line, not a project batch.** `YesOpenLine` selects one ID (default `l01`) and `YesOpenFitLine` builds a take batch with `--only`. No graph loop schedules the other lines or resumes missing jobs. The separately configured two-speaker dialog is not populated from the project and retains the selected line's prompt/duration when switched into the talk branch.
2. **Preparation remains external.** The graph selects an existing project, but does not edit the script, `lines.json`, cast choices or `edit/cuts.json`. Reference analysis is deliberately local. `YesOpenNewProject` exists in the node package but is absent from the generated graph.
3. **Finished shot processing does not feed the edit.** `Ujęcie do projektu` receives the raw LTX-2.3 VIDEO. Upscale and interpolation feed previews, while the edit reads `takes/<line>.video.mp4`. The Qwen/LTX-2.5 branch has no project take saver.
4. **Music has no edit dependency.** `YesOpenSaveMusic` writes `music/bed.flac`, but does not set `project.json -> music.file`, and its output is not a prerequisite for EDL or assembly. The edit may omit the new bed or run before it is saved.
5. **Approval gates are manual switches.** A closed gate emits `ExecutionBlocker`, but blocks its descendants only. Other output branches can execute. Gates do not validate completeness or record an approval tied to input hashes. There is no separate voice listening approval between fitting and lip-sync generation.
6. **QA failure does not automatically block delivery.** `qa_report.py` prints checks containing `ok: false` without returning a failure exit status. `YesOpenQAReport` inherits the generic Step handler and passes the project onward on exit code zero. Only 9:16 QA is wired; the other formats lack their own QA nodes/previews.
7. **Delivery and infrastructure completion are partial.** EncodeVariants creates share/web/poster files for 9:16. The graph does not verify downloads, provide a manifest with hashes, update the production checkpoint, or retire compute. Gate 7 is defined but not instantiated; infrastructure completion stays outside ComfyUI.
8. **Independent branches and cache state need hardening.** Save outputs make optional generation branches execution roots. Editing nodes fingerprint all projects when their project input arrives through a link, so unrelated project changes can invalidate renders. This is not a reliable staged, selective resume mechanism.

## Recommended implementation order

1. Add project readiness/status and explicit stage selection, with a separate audio approval before paid lip sync.
2. Connect final processed takes and optional B-roll to the project; connect music to the edit and project settings.
3. Make QA machine-readable and blocking for every output format; preserve human listening/visual review separately.
4. Add batch scheduling/resume for the project's lines and shots, then project-specific cache invalidation and persisted checkpoints.
5. Complete final-file manifests, download verification and infrastructure completion outside the generation graph.

## Verification limits

This review inspects `build_pipeline_graph.py`, `yesopen_pipeline/__init__.py`, the editor API and called scripts against `references/qa-checklist.md`. No GPU generation was submitted. The CPU preview API responds through the tunnel; all 14 YesOpen classes are registered. The root graph has 82 nodes and 92 links. `PrimitiveNode` is a frontend virtual node, so its absence from backend `/object_info` alone is not evidence of an invalid workflow. Import success does not establish end-to-end execution or visual layout correctness.
