# Benchmark Expansion Notes (2026-04-10)

## Scope

This note records the rationale behind the 20 additional routine benchmark cases added on 2026-04-10.

## Sanity Check

These 20 cases are reasonable for the current benchmark for four reasons:

1. They are still built around realistic household routines rather than transport-only synthetic patterns.
2. They reuse integration families and action vocabularies that already exist in the current benchmark suite.
3. They enlarge device counts and room coverage without forcing the benchmark to adopt a new semantics model.
4. They expand the suite along several missing dimensions: weather-triggered routines, family-care snapshots, office-zone routines, larger whole-home surveys, and more realistic BLE-heavy sweeps.

## Conservative Normalization

To keep the benchmark compatible with the current pipeline and avoid conflating "new routine coverage" with "new action semantics", the new cases were normalized conservatively:

1. Only currently-used action families were reused.
   - BLE: `refresh_cover`, `read_sensor`, `read_status`, `connect`, `subscribe`
   - CLOUD: `status`, `read_runtime`
   - LOCAL: `get_state`, `read_last_message`
   - HA: `publish`
2. New cases do not introduce new control verbs or new runtime marker families.
3. Cases that conceptually overlap with existing benchmarks were added as expanded variants rather than replacing existing cases.
   - Example: weekend snapshot, energy/HVAC audit, and BLE whole-home sweep now each have a larger companion case.
4. Local API lanes remain modeled as cheap local reads rather than introducing new local control semantics.

## Expected Use

These additional cases are intended to stress:

- larger mixed BLE/CLOUD/LOCAL routines
- room-level family-care and utility-room monitoring
- weather-triggered and commute-triggered routines
- whole-home survey and audit workloads
- more realistic BLE-heavy sweeps that are still understandable as household automation

## Source of Truth

The active source of truth remains:

- Generator script: `scripts/run_vdev_benchmarks.py`
- Generated manifest: `data/targets/vdev_benchmarks/manifest.json`
- Generated README: `data/targets/vdev_benchmarks/README.md`

The 20 new cases were added through the generator and then materialized into the benchmark target directory via `--targets-only` regeneration.
