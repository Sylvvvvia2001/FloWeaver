# Independent Device-State Audit Files

This directory records the local audit run for FloWeaver's independent device-state experiment.

## Scope

- Smart-home dataset: 20 validator-accepted routines, including 17 IFTTT-derived rows and 3 vdev mixed routines.
- Long-chain dataset: 10 validator-accepted routines from the long-chain sheet.
- Repeated runs: configured by `--runs`; the default local run uses 5 paired baseline/optimized executions per routine.
- Oracle mode: `simulated`. This validates the audit pipeline and file formats only; replace the execution adapter with real vendor/device queries before reporting real-device results.

## Reset and Audit Model

Each paired run records reset verification, baseline execution, optimized execution, device-side snapshots, platform-side snapshots, required events, lifecycle events, exception category, and pairwise comparison results. Timing/order changes are treated as descriptive differences, not failures, when final states and required observables match.

## Files

- `experiment_config.json`: reproducible run configuration and selected sample IDs.
- `sampling_manifest.csv`: selected routines, groups, modalities, validator/rollback metadata, and selection reasons.
- `oracle_specs.json`: per-routine oracle fields, required events, lifecycle events, and comparison rules.
- `execution_audit.jsonl`: one record per baseline or optimized execution.
- `pair_comparison.csv`: one record per paired baseline/optimized run.
- `summary.json`: machine-readable aggregate metrics.
- `SUMMARY.md`: paper-facing aggregate summary table.
