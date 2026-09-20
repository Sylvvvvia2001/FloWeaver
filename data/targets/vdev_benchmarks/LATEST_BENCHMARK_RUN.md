# VDev Benchmark Run Report

- Run ID: `48830afc55c3493f9b52958b22cecce4`
- Case Count: `1`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_homecoming_security_ambience_merge_01 | Scene Activation and Comfort Control Routines | ok | 6 | 6 | 0 | yes |

## Case Details

### Homecoming Security and Ambience Merge (`vdev_homecoming_security_ambience_merge_01`)

- Story: At arrival time, the routine merges a small security reassurance sweep with lighting and comfort checks to decide whether the home is ready for a safe, pleasant arrival.
- Protocol Mix: BLE 2 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x3, status x3, read_runtime x1, read_sensor x1
- Final Schedule: `6` batches, max `5` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01`

**Schedule Interpretation**

The first 1 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_001. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:4, switchbot:2, tuya:4, xiaomi_ble:1` | `vdev_vdev_homecoming_security_ambience_merge_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
