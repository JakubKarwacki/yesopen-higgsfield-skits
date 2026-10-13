# Graph routing optimisation — 12 October 2026

Context: continuation of the chat “Rozbudowaw pipeline”, after commit `16a2562`.
This work concerns graph geometry and wiring, independently of production execution.

`graph_layout.best_order` now uses exact subset dynamic programming for corridors
with up to 12 lanes, replacing exhaustive permutations for up to seven lanes.
The crossing objective is unchanged: pair costs include fan-out multiplicity and
the existing penalty for nearby horizontal segments. Larger corridors reuse pair
costs and evaluate insertion moves by their delta rather than rescoring both full
orders. Natural lane midpoints are counted once and ties select the smallest
midpoint deterministically.

Local full-generator comparison with the bundled Python runtime:

| Measurement | Before | After |
| --- | ---: | ---: |
| Elapsed time, one run each | 11.066 s | 5.438 s |
| Root reroutes | 44 | 39 |
| LTX-2.3 subgraph reroutes | 62 | 60 |
| Qwen subgraph reroutes | 30 | 29 |
| Canvas | 16398 × 3681 | 16398 × 3681 |
| Stage placement objective | 81893 | 81893 |

Times are indicative, not a repeated statistical benchmark. The generated root
links and node IDs are identical before/after. The generator reported no overlapping
segments in either run. All 434 root/subgraph links were visited by the verification
script, root slot references were checked, and reroute parent chains were checked
for missing parents and cycles. Four unit tests cover exhaustive optimality and
height tie behaviour through seven lanes, deterministic twelve-lane ordering,
insertion optimality on a larger corridor, and separation of overlapping vertical
runs from different sources.

Run the regression tests without ComfyUI:

```powershell
python -m unittest discover -s gpu/tests -p test_graph_layout.py -v
```

The browser-saved workflow is preserved. A separate generated preview is stored in
the chat artifact directory as `yesopen-skit-pipeline-layout-preview.json`.
No live deployment or visual browser validation was performed, and geometry was
not remeasured. The preview is built from source templates; it should not replace
the browser-saved workflow without checking its saved widget state. The next layout
iteration should remeasure the new YesOpen nodes and assess stage spacing against
the actual frontend rendering.

## Follow-up: rendered geometry and compact layout

The root graph was subsequently measured through the rendered DOM in ComfyUI.
All 63 non-note root nodes now have measured boxes and socket offsets. In
particular, YesOpenLine renders at 282 px body height rather than the old 260 px
estimate, and YesOpenFitLine at 242 px rather than 230 px. Generated node sizes
now match the measured boxes, avoiding frontend resizing on import.

Group padding is 36 px, stage corridor/row minimum spacing 128 px, and local
column/stack spacing 72/28 px. Corridors still widen when routing lanes need it.
The v3 preview has 36 root reroutes and a 15720 × 3581 canvas, versus v2's 39
reroutes and 16398 × 3681. Its root topology is unchanged. Five routing tests
passed. DOM measurements of the imported v3 graph found no overlapping node
rectangles and no differences between generated and rendered non-note sizes.
Internal subgraph geometry remains based on the earlier measurements; its
visual validation is still outstanding.

## Follow-up: redundant waypoints on buses

The final simplification pass now removes waypoints that leave the drawn
polyline unchanged, and collision-free private tails of shared buses that the
old solo-only pass skipped. Prefix ownership is recomputed until no further
deletion is accepted. Shared trunk points remain protected unless their removal
leaves the drawn path identical. Six tests passed, including a horizontal bus
with targets at different midpoints that needs no waypoint.

The saved v5 preview has 34 root reroutes (v4: 36). LTX-2.3 has 59 (61), MiniMax
24 (25), and LTX-2.5 45 (47). Canvas size and stage placement are unchanged. The
generator reports no overlapping segments. UTF-8 output is now explicit, fixing
the Windows default-encoding issue observed in Polish labels in v3.

## Follow-up: audit of every remaining waypoint

The deletion audit found four collision-free branch shortcuts blocked by shared
prefix ownership. A branch can now bypass a point still needed by another branch
when its drawn length does not increase. In v7 the root links traverse 38 reroutes
in total (v5: 39), and the subgraph links 225 (228). Unique visible reroutes remain
34 at root because the other users still need the shared points. Seven tests pass,
including a branch leaving a trunk required to bypass an obstacle for its sibling.
Root nodes and links are identical to v5. Four additional stage-placement seeds
were evaluated; none reduced the root reroute count, so the default placement was
retained. The v7 preview is saved in ComfyUI.
