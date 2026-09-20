# Combined BLE and API Micro-Refinement

The combined refiner runs after macro scheduling. It evaluates BLE and API candidates, resolves conflicts, and projects accepted segments onto a shared simulation timeline.

## Validation

Accepted candidates must pass their protocol-specific validators. Combined validation checks:

- Disjoint action and batch scopes, including adjacent resource-domain constraints.
- Contiguous projection onto the macro execution plan.
- Segment duration and reported latency savings.
- Batch completion order and the timing of unrefined segments.
- BLE transfer and connection-preparation limits.
- Cloud host/bucket and local endpoint/session request limits.
- Backoff barriers and global parse/aggregate overlap limits.

The simulator replaces each accepted segment with its micro-event sequence and retains macro duration blocks elsewhere. Reported savings are calculated from this timeline. Validation applies to the modeled events and resource constraints.

## Policy

`CombinedMicroRefinementPolicy` uses `highest_saving_wins` for conflicts and requires component validation, disjoint scopes, contiguous batches, local refinement, and preserved batch order. Adjacent same-session BLE segments are rejected by default.

Default BLE transfer, BLE connection preparation, cloud host/bucket, local endpoint/session, and global parse concurrency limits are all one.

## Outputs

Run `scripts/run_combined_micro_refinement.py` for standalone evaluation. Each case produces:

- `combined_micro_refinement.json`
- `combined_micro_simulation.json`
- `combined_micro_refined_plan_overlay.json`

Aggregate results are written to `data/optimizer_runs/vdev_benchmarks_combined_micro_refined/summary.json` and `data/targets/vdev_benchmarks/COMBINED_MICRO_REFINEMENT_REPORT.md`.
