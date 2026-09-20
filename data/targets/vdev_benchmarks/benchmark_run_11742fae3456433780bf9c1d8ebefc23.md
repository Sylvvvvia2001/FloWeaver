# VDev Benchmark Run Report

- Run ID: `11742fae3456433780bf9c1d8ebefc23`
- Case Count: `1`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_party_scene_activation_01 | Scene Activation and Comfort Control Routines | pending | - | - | - | no |

## Case Details

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Story: Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:1, mqtt:1, switchbot:5, tplink:2, tuya:13, xiaomi_ble:2` | `vdev_vdev_party_scene_activation_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_scene_activation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/counterexamples.json`
- Generated Component: `missing`
