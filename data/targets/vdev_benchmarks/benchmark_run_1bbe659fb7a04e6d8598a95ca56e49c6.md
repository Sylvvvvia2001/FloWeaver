# VDev Benchmark Run Report

- Run ID: `1bbe659fb7a04e6d8598a95ca56e49c6`
- Case Count: `16`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_party_scene_activation_01 | Scene Activation and Comfort Control Routines | ok | 18 | 6 | 0 | yes |
| vdev_morning_wakeup_ramp_01 | Scene Activation and Comfort Control Routines | ok | 18 | 6 | 0 | yes |
| vdev_workday_focus_mode_01 | Scene Activation and Comfort Control Routines | ok | 18 | 6 | 0 | yes |
| vdev_guest_suite_welcome_01 | Scene Activation and Comfort Control Routines | ok | 19 | 6 | 0 | yes |
| vdev_storm_lockdown_safety_01 | Scene Activation and Comfort Control Routines | ok | 18 | 6 | 0 | yes |
| vdev_whole_family_morning_comfort_snapshot_01 | Profile Coverage - Morning Routines | ok | 11 | 6 | 0 | yes |
| vdev_bad_air_morning_recovery_01 | Profile Coverage - Morning Routines | ok | 8 | 6 | 0 | yes |
| vdev_leave_home_safety_sweep_profile_01 | Profile Coverage - Arrival and Departure Routines | ok | 19 | 6 | 0 | yes |
| vdev_vacation_departure_final_audit_01 | Profile Coverage - Arrival and Departure Routines | ok | 28 | 6 | 0 | yes |
| vdev_late_night_entertainment_shutdown_01 | Profile Coverage - Evening and Overnight Routines | ok | 12 | 6 | 0 | yes |
| vdev_overnight_quiet_hours_snapshot_01 | Profile Coverage - Evening and Overnight Routines | ok | 10 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_profile_01 | Profile Coverage - Monitoring and Audit Routines | ok | 23 | 6 | 0 | yes |
| vdev_indoor_air_climate_audit_01 | Profile Coverage - Monitoring and Audit Routines | ok | 10 | 6 | 0 | yes |
| vdev_party_preparation_full_sweep_01 | Profile Coverage - Realistic Stress Routines | ok | 17 | 6 | 0 | yes |
| vdev_holiday_vacation_mode_full_audit_01 | Profile Coverage - Realistic Stress Routines | ok | 33 | 6 | 0 | yes |
| vdev_ble_safety_sweep_routine_01 | Profile Coverage - Realistic Stress Routines | error | - | - | - | no |

## Case Details

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Story: Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `18` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|party_scene_light_controls groups 4 actions into 2 chunks; tuya|party_scene_hvac_controls groups 2 actions into 1 chunks. Local reads overlap other reads in batch_013. Writeback follows lane updates and then the overall update: batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:1, mqtt:1, switchbot:5, tplink:2, tuya:13, xiaomi_ble:2` | `vdev_vdev_party_scene_activation_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_scene_activation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Morning Wake-Up Ramp Routine (`vdev_morning_wakeup_ramp_01`)

- Story: At wake-up time, the routine opens multiple covers, ramps key lights to morning brightness and color temperature, nudges HVAC and fan comfort, then verifies representative state before publishing one wake-up summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `18` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|wakeup_light_controls groups 4 actions into 2 chunks; tuya|wakeup_hvac_controls groups 2 actions into 1 chunks. Local reads overlap other reads in batch_013. Writeback follows lane updates and then the overall update: batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, mqtt:1, switchbot:5, tuya:13, xiaomi_ble:2` | `vdev_vdev_morning_wakeup_ramp_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_morning_wakeup_ramp_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Workday Focus Mode Routine (`vdev_workday_focus_mode_01`)

- Story: At the start of a work block, the routine repositions shades, enables desk airflow and task lighting, applies a focused lighting and climate profile, then verifies representative cloud and local state before publishing one focus-mode summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: turn_on x5, status x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `18` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_focus_mode_01/reassembly/vdev_vdev_workday_focus_mode_01/custom_components/vdev_vdev_workday_focus_mode_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|focus_light_controls groups 3 actions into 1 chunks; ecobee|focus_hvac_controls groups 3 actions into 1 chunks. Local reads overlap other reads in batch_013. Writeback follows lane updates and then the overall update: batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

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

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Guest Suite Welcome Routine (`vdev_guest_suite_welcome_01`)

- Story: Before guests arrive, the routine opens suite shades, enables airflow and welcome lighting, applies a comfort preset, then verifies representative scene state before publishing a guest-suite readiness summary.
- Protocol Mix: BLE 7 / CLOUD 12 / LOCAL 3 / HA 4
- Main Action Types: status x4, turn_on x4, write x4, set_cover_position x3, get_state x2
- Final Schedule: `19` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_guest_suite_welcome_01/reassembly/vdev_vdev_guest_suite_welcome_01/custom_components/vdev_vdev_guest_suite_welcome_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|guest_light_controls groups 3 actions into 1 chunks; ecobee|guest_runtime_controls groups 2 actions into 1 chunks. Local reads overlap other reads in batch_014. Writeback follows lane updates and then the overall update: batch_017 -> batch_018. M6 found no counterexamples in the evaluated replay scenarios.

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

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Storm Lockdown Safety Routine (`vdev_storm_lockdown_safety_01`)

- Story: Before a storm front arrives, the routine closes exposed shades, powers down selected outdoor loads, enables safety lighting and HVAC lockdown settings, then verifies representative state before publishing a whole-home storm-lockdown summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x4, write x4, set_cover_position x3, turn_off x3, turn_on x3
- Final Schedule: `18` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_storm_lockdown_safety_01/reassembly/vdev_vdev_storm_lockdown_safety_01/custom_components/vdev_vdev_storm_lockdown_safety_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|storm_light_controls groups 2 actions into 1 chunks; tuya|storm_switch_controls groups 2 actions into 1 chunks; ecobee|storm_hvac_controls groups 3 actions into 1 chunks. Local reads overlap other reads in batch_013. Writeback follows lane updates and then the overall update: batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

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

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Whole-Family Morning Comfort Snapshot (`vdev_whole_family_morning_comfort_snapshot_01`)

- Story: Before the whole family wakes up, the routine snapshots comfort state across multiple rooms, including BLE environment sensors, SwitchBot curtains, local lighting systems, Tuya climate or lights, and Netatmo runtime.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: read_sensor x4, write x4, get_state x3, status x3, refresh_cover x2
- Final Schedule: `11` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:1, hue:2, nanoleaf:1, netatmo:1, ruuvitag_ble:2, switchbot:3, thermobeacon:1, tplink:1, tuya:4` | `vdev_vdev_whole_family_morning_comfort_snapshot_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py; data/repo_snapshot/thermobeacon/sensor.py; data/repo_snapshot/switchbot/cover.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/reassembly/vdev_vdev_whole_family_morning_comfort_snapshot_01/custom_components/vdev_vdev_whole_family_morning_comfort_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Bad-Air Morning Recovery (`vdev_bad_air_morning_recovery_01`)

- Story: When indoor air quality is poor in the morning, the routine checks purifier state, curtains, climate, local ambience lights, and Netatmo environment state before recommending recovery actions.
- Protocol Mix: BLE 4 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, get_state x2, refresh_cover x2, status x2, read_runtime x1
- Final Schedule: `8` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_004. Writeback follows lane updates and then the overall update: batch_006 -> batch_007. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `10` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:1, hue:1, nanoleaf:1, netatmo:1, switchbot:4, tplink:1, tuya:3` | `vdev_vdev_bad_air_morning_recovery_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 10 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_bad_air_morning_recovery_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/reassembly/vdev_vdev_bad_air_morning_recovery_01/custom_components/vdev_vdev_bad_air_morning_recovery_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Leave-Home Safety Sweep Profile Coverage (`vdev_leave_home_safety_sweep_profile_01`)

- Story: After residents leave, the routine checks lights, plugs, curtains, door or window sensors, climate, and entertainment devices to confirm the home is safe and energy efficient.
- Protocol Mix: BLE 7 / CLOUD 7 / LOCAL 6 / HA 4
- Main Action Types: get_state x6, status x6, read_sensor x4, write x4, refresh_cover x3
- Final Schedule: `19` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_017 -> batch_018. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `denonavr:1, ecobee:1, esphome:1, hue:2, roku:1, switchbot:4, tplink:3, tuya:7, xiaomi_ble:4` | `vdev_vdev_leave_home_safety_sweep_profile_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/reassembly/vdev_vdev_leave_home_safety_sweep_profile_01/custom_components/vdev_vdev_leave_home_safety_sweep_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Vacation Departure Final Audit (`vdev_vacation_departure_final_audit_01`)

- Story: Before a long trip, the routine performs a final whole-home audit across curtains, door or window sensors, temperature sensors, local lights or plugs, media devices, cloud lights or switches, thermostat, and security state.
- Protocol Mix: BLE 10 / CLOUD 10 / LOCAL 9 / HA 4
- Main Action Types: get_state x9, status x8, read_sensor x6, refresh_cover x4, write x4
- Final Schedule: `28` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01`

**Schedule Interpretation**

The first 10 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_026 -> batch_027. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `13` integrations / `16` files | `1` generated custom component |
| Main Source Integrations | `blink:1, denonavr:1, ecobee:1, esphome:1, hue:3, roku:1, ruuvitag_ble:1, sensorpush:1, switchbot:5, tplink:4, tuya:9, webostv:1, xiaomi_ble:4` | `vdev_vdev_vacation_departure_final_audit_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/sensorpush/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 13 integrations and approximately 16 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_vacation_departure_final_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Late-Night Entertainment Shutdown (`vdev_late_night_entertainment_shutdown_01`)

- Story: After watching TV at night, the routine checks whether the living-room entertainment area is fully shut down.
- Protocol Mix: BLE 2 / CLOUD 3 / LOCAL 7 / HA 4
- Main Action Types: get_state x7, write x4, status x3, read_sensor x1, refresh_cover x1
- Final Schedule: `12` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_010 -> batch_011. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `denonavr:1, esphome:1, hue:2, roku:1, switchbot:2, tplink:3, tuya:4, webostv:1, xiaomi_ble:1` | `vdev_vdev_late_night_entertainment_shutdown_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/reassembly/vdev_vdev_late_night_entertainment_shutdown_01/custom_components/vdev_vdev_late_night_entertainment_shutdown_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Overnight Quiet-Hours Snapshot (`vdev_overnight_quiet_hours_snapshot_01`)

- Story: At a fixed overnight time, the routine snapshots the family's quiet-hours state across environmental sensors, door or window sensors, Hue groups, thermostats, power strips, and Netatmo environment runtime.
- Protocol Mix: BLE 5 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: read_sensor x5, write x4, read_runtime x3, get_state x2, status x2
- Final Schedule: `10` batches, max `5` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_008 -> batch_009. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, ecobee:2, esphome:1, hue:2, netatmo:1, ruuvitag_ble:2, switchbot:1, tplink:1, tuya:3, xiaomi_ble:2` | `vdev_vdev_overnight_quiet_hours_snapshot_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/reassembly/vdev_vdev_overnight_quiet_hours_snapshot_01/custom_components/vdev_vdev_overnight_quiet_hours_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Weekend Whole-Home Snapshot Profile Coverage (`vdev_weekend_whole_home_snapshot_profile_01`)

- Story: On a weekend, the routine builds a whole-home snapshot of lights, curtains, temperature, energy, air quality, local media, and climate state.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 7 / HA 4
- Main Action Types: status x8, get_state x7, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `23` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_021 -> batch_022. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `15` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:3, nanoleaf:1, netatmo:1, roku:1, switchbot:4, tplink:3, tuya:9, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_profile_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/esphome/__init__.py; data/repo_snapshot/esphome/manager.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 15 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Indoor Air and Climate Audit (`vdev_indoor_air_climate_audit_01`)

- Story: The routine audits air quality and climate state across BLE environmental sensors, local ambience lights, Tuya climates, Ecobee thermostats, and Netatmo station runtime.
- Protocol Mix: BLE 5 / CLOUD 6 / LOCAL 1 / HA 4
- Main Action Types: read_sensor x5, write x4, read_runtime x3, status x3, get_state x1
- Final Schedule: `10` batches, max `5` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_007. Writeback follows lane updates and then the overall update: batch_008 -> batch_009. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, ecobee:2, esphome:1, nanoleaf:1, netatmo:1, qingping:2, sensorpush:2, switchbot:1, tplink:1, tuya:4` | `vdev_vdev_indoor_air_climate_audit_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/sensorpush/sensor.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_indoor_air_climate_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/reassembly/vdev_vdev_indoor_air_climate_audit_01/custom_components/vdev_vdev_indoor_air_climate_audit_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Party Preparation Full Sweep (`vdev_party_preparation_full_sweep_01`)

- Story: Before a party, the routine checks living-room and dining-room lighting, curtains, climate, entertainment devices, and air quality.
- Protocol Mix: BLE 4 / CLOUD 6 / LOCAL 8 / HA 4
- Main Action Types: get_state x8, status x6, write x4, read_sensor x2, refresh_cover x2
- Final Schedule: `17` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `11` integrations / `15` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, denonavr:1, esphome:1, hue:4, nanoleaf:1, roku:1, switchbot:3, tplink:1, tuya:7, webostv:1, xiaomi_ble:1` | `vdev_vdev_party_preparation_full_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 11 integrations and approximately 15 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_preparation_full_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/reassembly/vdev_vdev_party_preparation_full_sweep_01/custom_components/vdev_vdev_party_preparation_full_sweep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Holiday Vacation Mode Full Audit (`vdev_holiday_vacation_mode_full_audit_01`)

- Story: Before a holiday trip, the routine performs the largest whole-home audit across curtains, doors, windows, environmental sensors, ESPHome transport, local lights, plugs, TVs, and cloud HVAC or security systems.
- Protocol Mix: BLE 14 / CLOUD 12 / LOCAL 8 / HA 4
- Main Action Types: status x10, get_state x8, read_sensor x8, refresh_cover x4, write x4
- Final Schedule: `33` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01`

**Schedule Interpretation**

The first 14 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_031 -> batch_032. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `12` integrations / `18` files | `1` generated custom component |
| Main Source Integrations | `blink:1, ecobee:1, esphome:3, hue:3, qingping:1, roku:1, sensorpush:2, switchbot:5, tplink:4, tuya:11, webostv:1, xiaomi_ble:5` | `vdev_vdev_holiday_vacation_mode_full_audit_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/sensorpush/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 12 integrations and approximately 18 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### BLE Safety Sweep Routine (`vdev_ble_safety_sweep_routine_01`)

- Story: At a fixed time, the routine performs a whole-home BLE safety sweep over curtains, doors, windows, motion sensors, bedside lamps, environmental sensors, and ESPHome transport state.
- Protocol Mix: BLE 15 / HA 2
- Main Action Types: read_sensor x8, refresh_cover x3, read_status x2, write x2, connect x1
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:3, ruuvitag_ble:1, switchbot:4, xiaomi_ble:8` | `vdev_vdev_ble_safety_sweep_routine_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/airthings_ble/sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_ble_safety_sweep_routine_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/counterexamples.json`
- Generated Component: `missing`
