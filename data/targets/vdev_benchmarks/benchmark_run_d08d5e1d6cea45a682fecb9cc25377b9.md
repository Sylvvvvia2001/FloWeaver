# VDev Benchmark Run Report

- Run ID: `d08d5e1d6cea45a682fecb9cc25377b9`
- Case Count: `5`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_profile_01 | Profile Coverage - Morning Routines | ok | 11 | 6 | 0 | yes |
| vdev_vacation_departure_final_audit_01 | Profile Coverage - Arrival and Departure Routines | ok | 13 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_profile_01 | Profile Coverage - Monitoring and Audit Routines | ok | 11 | 6 | 0 | yes |
| vdev_holiday_vacation_mode_full_audit_01 | Profile Coverage - Realistic Stress Routines | ok | 17 | 6 | 0 | yes |
| vdev_ble_safety_sweep_routine_01 | Profile Coverage - Realistic Stress Routines | ok | 17 | 6 | 0 | yes |

## Case Details

### Morning Wake-Up Readiness Profile Coverage (`vdev_morning_wakeup_readiness_profile_01`)

- Story: After residents wake up, the routine quickly checks bedroom and hallway readiness across curtains, bedside lamps, environmental sensors, local lights, local TV state, cloud climate, and thermostat runtime.
- Protocol Mix: BLE 8 / CLOUD 2 / LOCAL 2 / HA 4
- Main Action Types: write x4, get_state x2, read_sensor x2, read_status x2, refresh_cover x2
- Final Schedule: `11` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01`

**Schedule Interpretation**

The first 0 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_000. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:3, hue:1, philips_js:1, qingping:1, sensorpush:1, switchbot:3, tplink:1, tuya:2, xiaomi_ble:2` | `vdev_vdev_morning_wakeup_readiness_profile_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/sensorpush/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Vacation Departure Final Audit (`vdev_vacation_departure_final_audit_01`)

- Story: Before a long trip, the routine performs a final whole-home audit across curtains, door or window sensors, temperature sensors, local lights or plugs, media devices, cloud lights or switches, thermostat, and security state.
- Protocol Mix: BLE 10 / CLOUD 10 / LOCAL 9 / HA 4
- Main Action Types: get_state x9, status x8, read_sensor x6, refresh_cover x4, write x4
- Final Schedule: `13` batches, max `6` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/reassembly/vdev_vdev_vacation_departure_final_audit_01/custom_components/vdev_vdev_vacation_departure_final_audit_01`

**Schedule Interpretation**

The first 0 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_000, batch_001, batch_002. Writeback follows lane updates and then the overall update: batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

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

### Weekend Whole-Home Snapshot Profile Coverage (`vdev_weekend_whole_home_snapshot_profile_01`)

- Story: On a weekend, the routine builds a whole-home snapshot of lights, curtains, temperature, energy, air quality, local media, and climate state.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 7 / HA 4
- Main Action Types: status x8, get_state x7, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `11` batches, max `6` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_profile_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_profile_01`

**Schedule Interpretation**

The first 0 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_000, batch_001, batch_002. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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

### Holiday Vacation Mode Full Audit (`vdev_holiday_vacation_mode_full_audit_01`)

- Story: Before a holiday trip, the routine performs the largest whole-home audit across curtains, doors, windows, environmental sensors, ESPHome transport, local lights, plugs, TVs, and cloud HVAC or security systems.
- Protocol Mix: BLE 14 / CLOUD 12 / LOCAL 8 / HA 4
- Main Action Types: status x10, get_state x8, read_sensor x8, refresh_cover x4, write x4
- Final Schedule: `17` batches, max `6` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/reassembly/vdev_vdev_holiday_vacation_mode_full_audit_01/custom_components/vdev_vdev_holiday_vacation_mode_full_audit_01`

**Schedule Interpretation**

The first 0 BLE actions run serially to avoid shared-radio conflicts. Local reads overlap other reads in batch_002, batch_003, batch_004. Writeback follows lane updates and then the overall update: batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01`

**Schedule Interpretation**

The first 15 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:3, ruuvitag_ble:1, switchbot:4, xiaomi_ble:8` | `vdev_vdev_ble_safety_sweep_routine_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/airthings_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_ble_safety_sweep_routine_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_routine_01/reassembly/vdev_vdev_ble_safety_sweep_routine_01/custom_components/vdev_vdev_ble_safety_sweep_routine_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
