# Shutdown checks for the shared coordinator

An explicit user request authorizes shutdown. A completed film waiting for human
review must not keep a paid server running.

`State.drain()` stops admission of new runs and returns:

- `outstanding`: unresolved tasks other than waiting approval gates;
- `blocking_tasks`: their run IDs, task IDs and states;
- `pending_reviews` and `review_tasks`: waiting gates, preserved without approval
  or cancellation;
- `safe_to_stop`: true when no blocking tasks remain.

A finished export followed only by `approve-final` is safe to stop. Running,
accepted, dispatching and unknown tasks still block, as does unfinished compute
work, including work behind a review gate. This is a coordinator-state check,
not proof that unrelated processes on the host are idle. Before provider
shutdown, check the actual ComfyUI queue and CPU/export/transfer processes,
verify required downloads, and stop the coordinator and workers.

Do not claim that a film is processing solely because it has a pending review.
Do not cancel or approve reviews merely to clear the shutdown counter. Stop and
Delete are different provider operations; retain disks when instructed.

The scheduler module and standalone regression tests can be used independently
of the remaining shared-pipeline integration:

```sh
python3 -m unittest discover -s gpu/tests -p test_shutdown_drain.py -v
```

Regression coverage includes a completed film awaiting review, a second film
with queued compute, active and unknown attempts after cancellation, work behind
a gate, admission blocking, resume, and preservation of review state/artifacts.
