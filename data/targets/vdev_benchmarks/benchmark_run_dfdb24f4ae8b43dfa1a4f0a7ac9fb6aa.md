# VDev Benchmark Run Report

- Run ID: `dfdb24f4ae8b43dfa1a4f0a7ac9fb6aa`
- Case Count: `3`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_party_scene_activation_01 | Scene Activation and Comfort Control Routines | ok | 12 | 0 | 6 | yes |
| vdev_movie_night_blackout_01 | Scene Activation and Comfort Control Routines | ok | 12 | 0 | 6 | yes |
| vdev_morning_wakeup_ramp_01 | Scene Activation and Comfort Control Routines | ok | 12 | 0 | 6 | yes |

## Case Details

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Story: Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `12` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/reassembly/vdev_vdev_party_scene_activation_01/custom_components/vdev_vdev_party_scene_activation_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|party_scene_light_controls groups 4 actions into 2 chunks; tuya|party_scene_hvac_controls groups 2 actions into 1 chunks; tuya|party_scene_light_verify groups 3 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_010 -> batch_011.

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

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Movie Night Blackout Routine (`vdev_movie_night_blackout_01`)

- Story: Before a movie starts, the routine darkens the viewing area by closing multiple covers, shifting lights into a dim warm scene, adjusting climate and fan comfort, then verifying the blackout state before publishing movie-night readiness summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, write x4, turn_on x3, get_state x2
- Final Schedule: `12` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|movie_light_controls groups 4 actions into 2 chunks; tuya|movie_hvac_controls groups 2 actions into 1 chunks; tuya|movie_light_verify groups 3 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_010 -> batch_011.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:1, mqtt:1, switchbot:5, tplink:2, tuya:13, xiaomi_ble:2` | `vdev_vdev_movie_night_blackout_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_movie_night_blackout_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01`

**M6 Proof Summary**

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Morning Wake-Up Ramp Routine (`vdev_morning_wakeup_ramp_01`)

- Story: At wake-up time, the routine opens multiple covers, ramps key lights to morning brightness and color temperature, nudges HVAC and fan comfort, then verifies representative state before publishing one wake-up summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `12` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/reassembly/vdev_vdev_morning_wakeup_ramp_01/custom_components/vdev_vdev_morning_wakeup_ramp_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|wakeup_light_controls groups 4 actions into 2 chunks; tuya|wakeup_hvac_controls groups 2 actions into 1 chunks; tuya|wakeup_light_verify groups 3 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_010 -> batch_011.

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

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`
