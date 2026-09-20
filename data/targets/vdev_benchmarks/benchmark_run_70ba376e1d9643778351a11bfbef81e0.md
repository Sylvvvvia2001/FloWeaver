# VDev Benchmark Run Report

- Run ID: `70ba376e1d9643778351a11bfbef81e0`
- Case Count: `3`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_workday_focus_mode_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_guest_suite_welcome_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_storm_lockdown_safety_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |

## Case Details

### Workday Focus Mode Routine (`vdev_workday_focus_mode_01`)

- Story: At the start of a work block, the routine repositions shades, enables desk airflow and task lighting, applies a focused lighting and climate profile, then verifies representative cloud and local state before publishing one focus-mode summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: turn_on x5, status x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:4, esphome:1, hue:2, mqtt:1, switchbot:6, tplink:1, tuya:9, xiaomi_ble:2` | `vdev_vdev_workday_focus_mode_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/light.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_workday_focus_mode_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/counterexamples.json`
- Generated Component: `missing`

### Guest Suite Welcome Routine (`vdev_guest_suite_welcome_01`)

- Story: Before guests arrive, the routine opens suite shades, enables airflow and welcome lighting, applies a comfort preset, then verifies representative scene state before publishing a guest-suite readiness summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: status x4, turn_on x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:3, esphome:1, hue:2, mqtt:1, switchbot:6, tplink:1, tuya:10, xiaomi_ble:2` | `vdev_vdev_guest_suite_welcome_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/light.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_guest_suite_welcome_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/counterexamples.json`
- Generated Component: `missing`

### Storm Lockdown Safety Routine (`vdev_storm_lockdown_safety_01`)

- Story: Before a storm front arrives, the routine closes exposed shades, powers down selected outdoor loads, enables safety lighting and HVAC lockdown settings, then verifies representative state before publishing a whole-home storm-lockdown summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x4, write x4, set_cover_position x3, turn_off x3, turn_on x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:4, esphome:1, hue:2, mqtt:1, switchbot:5, tplink:1, tuya:10, xiaomi_ble:2` | `vdev_vdev_storm_lockdown_safety_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_storm_lockdown_safety_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/counterexamples.json`
- Generated Component: `missing`
