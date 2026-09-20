# VDev Benchmark Run Report

- Run ID: `a39144a9e50e4836b7b9fcdb72a82679`
- Case Count: `3`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_workday_focus_mode_01 | Scene Activation and Comfort Control Routines | ok | 13 | 0 | 6 | yes |
| vdev_guest_suite_welcome_01 | Scene Activation and Comfort Control Routines | ok | 14 | 0 | 6 | yes |
| vdev_storm_lockdown_safety_01 | Scene Activation and Comfort Control Routines | ok | 13 | 0 | 6 | yes |

## Case Details

### Workday Focus Mode Routine (`vdev_workday_focus_mode_01`)

- Story: At the start of a work block, the routine repositions shades, enables desk airflow and task lighting, applies a focused lighting and climate profile, then verifies representative cloud and local state before publishing one focus-mode summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: turn_on x5, status x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 4 actions into 1 chunks; ecobee groups 3 actions into 1 chunks; tuya|focus_light_verify groups 3 actions into 1 chunks. Local reads overlap other reads in batch_010. Writeback follows lane updates and then the overall update: batch_011 -> batch_012.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:4, esphome:1, hue:2, mqtt:1, switchbot:6, tplink:1, tuya:9, xiaomi_ble:2` | `vdev_vdev_workday_focus_mode_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/light.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_workday_focus_mode_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01`

**M6 Proof Summary**

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Guest Suite Welcome Routine (`vdev_guest_suite_welcome_01`)

- Story: Before guests arrive, the routine opens suite shades, enables airflow and welcome lighting, applies a comfort preset, then verifies representative scene state before publishing a guest-suite readiness summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: status x4, turn_on x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `14` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 4 actions into 1 chunks; ecobee groups 2 actions into 1 chunks; tuya|guest_light_verify groups 3 actions into 1 chunks. Local reads overlap other reads in batch_011. Writeback follows lane updates and then the overall update: batch_012 -> batch_013.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:3, esphome:1, hue:2, mqtt:1, switchbot:6, tplink:1, tuya:10, xiaomi_ble:2` | `vdev_vdev_guest_suite_welcome_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/light.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_guest_suite_welcome_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01`

**M6 Proof Summary**

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Storm Lockdown Safety Routine (`vdev_storm_lockdown_safety_01`)

- Story: Before a storm front arrives, the routine closes exposed shades, powers down selected outdoor loads, enables safety lighting and HVAC lockdown settings, then verifies representative state before publishing a whole-home storm-lockdown summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x4, write x4, set_cover_position x3, turn_off x3, turn_on x3
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 4 actions into 1 chunks; ecobee groups 3 actions into 1 chunks; tuya|storm_light_verify groups 2 actions into 1 chunks. Local reads overlap other reads in batch_010. Writeback follows lane updates and then the overall update: batch_011 -> batch_012.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:4, esphome:1, hue:2, mqtt:1, switchbot:5, tplink:1, tuya:10, xiaomi_ble:2` | `vdev_vdev_storm_lockdown_safety_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_storm_lockdown_safety_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01`

**M6 Proof Summary**

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`
