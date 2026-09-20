# VDev Benchmark Run Report

- Run ID: `consolidated`
- Case Count: `10`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_01 | Morning and Leaving Home Routines | ok | 11 | 6 | 0 | yes |
| vdev_leaving_home_safety_check_01 | Morning and Leaving Home Routines | ok | 9 | 6 | 0 | yes |
| vdev_arrival_comfort_preparation_01 | Coming Home and Evening Comfort Routines | ok | 14 | 6 | 0 | yes |
| vdev_dinner_home_mode_01 | Coming Home and Evening Comfort Routines | ok | 13 | 6 | 0 | yes |
| vdev_night_shutdown_01 | Night and Energy Monitoring Routines | ok | 14 | 6 | 0 | yes |
| vdev_overnight_health_safety_monitoring_01 | Night and Energy Monitoring Routines | ok | 12 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_01 | Night and Energy Monitoring Routines | ok | 13 | 6 | 0 | yes |
| vdev_party_preparation_01 | Coming Home and Evening Comfort Routines | ok | 9 | 6 | 0 | yes |
| vdev_ble_safety_sweep_stress_01 | Household Stress and Abnormality Routines | ok | 11 | 6 | 0 | yes |
| vdev_energy_hvac_audit_01 | Household Stress and Abnormality Routines | ok | 5 | 6 | 0 | yes |


## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Story: Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.
- Protocol Mix: BLE 7 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, get_state x2, read_status x2, refresh_cover x2
- Final Schedule: `11` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|morning_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:3, switchbot:3, tuya:4, xiaomi_ble:3` | `vdev_vdev_morning_wakeup_readiness_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/xiaomi_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_morning_wakeup_readiness_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Leaving Home Safety Check Routine (`vdev_leaving_home_safety_check_01`)

- Story: Before residents leave, the routine checks curtains, key lights, energy strips, climate, and entry sensors, then writes one leave-home safety summary.
- Protocol Mix: BLE 5 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, refresh_cover x2
- Final Schedule: `9` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|leave_home_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, switchbot:3, tplink:2, tuya:6, xiaomi_ble:3` | `vdev_vdev_leaving_home_safety_check_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/device.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_leaving_home_safety_check_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Coming Home Comfort Preparation Routine (`vdev_arrival_comfort_preparation_01`)

- Story: Before arrival, the routine prepares a comfort snapshot by combining BLE sensors and curtains, cloud HVAC and lights, a Hue bridge read, and one MQTT air-quality read.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, read_sensor x2, refresh_cover x2, connect x1
- Final Schedule: `14` batches, max `2` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|arrival_lights groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_010 -> batch_011 -> batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:3, hue:1, mqtt:1, switchbot:3, tplink:1, tuya:4, xiaomi_ble:2` | `vdev_vdev_arrival_comfort_preparation_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/esphome/__init__.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_arrival_comfort_preparation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Dinner Time Home Mode Routine (`vdev_dinner_home_mode_01`)

- Story: Before dinner, the routine checks dining, kitchen, and living-room readiness across curtains, lights, HVAC, and energy sensors to decide whether the home is ready for dinner mode.
- Protocol Mix: BLE 4 / CLOUD 5 / LOCAL 3 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, refresh_cover x2
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|dinner_lights groups 3 actions into 2 chunks. Writeback follows lane updates and then the overall update: batch_009 -> batch_010 -> batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, mqtt:1, switchbot:3, tplink:2, tuya:6, xiaomi_ble:2` | `vdev_vdev_dinner_home_mode_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_dinner_home_mode_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Night Shutdown Routine (`vdev_night_shutdown_01`)

- Story: Before sleep, the routine confirms curtains, bedside lights, selected energy plugs, climate, and safety sensors, then writes a night shutdown summary.
- Protocol Mix: BLE 6 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, read_status x2
- Final Schedule: `14` batches, max `2` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|night_lights groups 2 actions into 1 chunks; tuya|night_energy groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_010 -> batch_011 -> batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, switchbot:3, tplink:2, tuya:6, xiaomi_ble:4` | `vdev_vdev_night_shutdown_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/xiaomi_ble/event.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_night_shutdown_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Overnight Health & Safety Monitoring Routine (`vdev_overnight_health_safety_monitoring_01`)

- Story: During the night, the routine snapshots temperature, door and window safety, air quality, power usage, and remote HVAC state into one overnight monitoring summary.
- Protocol Mix: BLE 4 / CLOUD 6 / LOCAL 2 / HA 4
- Main Action Types: read_sensor x4, status x4, write x4, read_last_message x2, read_runtime x2
- Final Schedule: `12` batches, max `2` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|overnight_tuya_hvac groups 2 actions into 1 chunks; tuya|overnight_energy groups 2 actions into 1 chunks; ecobee|overnight_ecobee groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_008 -> batch_009 -> batch_010 -> batch_011. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, mqtt:2, switchbot:1, tplink:1, tuya:5, xiaomi_ble:4` | `vdev_vdev_overnight_health_safety_monitoring_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Story: During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 4 / HA 4
- Main Action Types: status x7, write x4, get_state x3, read_sensor x3, refresh_cover x3
- Final Schedule: `13` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|weekend_lights groups 3 actions into 2 chunks; tuya|weekend_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_010. Writeback follows lane updates and then the overall update: batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:2, mqtt:1, switchbot:4, tplink:2, tuya:8, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/esphome/__init__.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Party Preparation Routine (`vdev_party_preparation_01`)

- Story: Before guests arrive, the routine checks party-scene lighting, curtains, climate, speaker power, TV power, and air quality to decide whether the home is ready for a party scene.
- Protocol Mix: BLE 4 / CLOUD 6 / LOCAL 3 / HA 4
- Main Action Types: status x6, write x4, get_state x2, read_sensor x2, refresh_cover x2
- Final Schedule: `9` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|party_lights groups 3 actions into 2 chunks; tuya|party_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, mqtt:1, switchbot:3, tplink:2, tuya:7, xiaomi_ble:2` | `vdev_vdev_party_preparation_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_preparation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### BLE Congestion Routine Stress (`vdev_ble_safety_sweep_stress_01`)

- Story: A fast whole-home BLE safety sweep checks curtains, room sensors, and one ESPHome transport pair, acting as a realistic high-contention BLE routine rather than an abstract stress synthetic.
- Protocol Mix: BLE 9 / HA 2
- Main Action Types: read_sensor x4, refresh_cover x3, write x2, connect x1, subscribe x1
- Final Schedule: `11` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01`

**Schedule Interpretation**

The first 9 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `3` integrations / `8` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, switchbot:4, xiaomi_ble:4` | `vdev_vdev_ble_safety_sweep_stress_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 3 integrations and approximately 8 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_ble_safety_sweep_stress_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_ble_safety_sweep_stress_01/reassembly/vdev_vdev_ble_safety_sweep_stress_01/custom_components/vdev_vdev_ble_safety_sweep_stress_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Cloud Burst Energy & HVAC Audit Routine (`vdev_energy_hvac_audit_01`)

- Story: At a fixed audit time, the routine gathers multiple Tuya lights, energy strips, climate states, and two Ecobee runtime reads to generate one energy and HVAC audit summary.
- Protocol Mix: CLOUD 10 / HA 2
- Main Action Types: status x8, read_runtime x2, write x2
- Final Schedule: `5` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01`

**Schedule Interpretation**

Cloud reads are grouped by provider and endpoint: tuya|energy_hvac_lights groups 3 actions into 2 chunks; tuya|energy_hvac_energy groups 2 actions into 1 chunks; tuya|energy_hvac_climate groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_003 -> batch_004. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `3` integrations / `7` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, tuya:9` | `vdev_vdev_energy_hvac_audit_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 3 integrations and approximately 7 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_energy_hvac_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
