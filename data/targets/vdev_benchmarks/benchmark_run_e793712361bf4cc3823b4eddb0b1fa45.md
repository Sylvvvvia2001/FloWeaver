# VDev Benchmark Run Report

- Run ID: `e793712361bf4cc3823b4eddb0b1fa45`
- Case Count: `5`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_01 | Morning and Leaving Home Routines | ok | 11 | 6 | 0 | yes |
| vdev_arrival_comfort_preparation_01 | Coming Home and Evening Comfort Routines | ok | 9 | 6 | 0 | yes |
| vdev_night_shutdown_01 | Night and Energy Monitoring Routines | ok | 9 | 6 | 0 | yes |
| vdev_arrive_home_lighting_climate_prep_01 | Coming Home and Evening Comfort Routines | ok | 10 | 6 | 0 | yes |
| vdev_kids_room_comfort_safety_snapshot_01 | Family Care and Room-Level Snapshot Routines | ok | 9 | 6 | 0 | yes |

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

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|morning_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_007. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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

### Coming Home Comfort Preparation Routine (`vdev_arrival_comfort_preparation_01`)

- Story: Before arrival, the routine prepares a comfort snapshot by combining BLE sensors and curtains, cloud HVAC and lights, a Hue bridge read, and one MQTT air-quality read.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, read_sensor x2, refresh_cover x2, connect x1
- Final Schedule: `9` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|arrival_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

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

### Night Shutdown Routine (`vdev_night_shutdown_01`)

- Story: Before sleep, the routine confirms curtains, bedside lights, selected energy plugs, climate, and safety sensors, then writes a night shutdown summary.
- Protocol Mix: BLE 6 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, read_status x2
- Final Schedule: `9` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|night_lights groups 2 actions into 1 chunks; tuya|night_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

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

### Arrive-Home Lighting and Climate Prep (`vdev_arrive_home_lighting_climate_prep_01`)

- Story: Before residents get home, the routine checks living-room, hallway, and bedroom lights, curtains, climate, and air quality to decide whether the house is ready to enter a welcome-home state.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 4 / HA 4
- Main Action Types: get_state x4, write x4, status x3, read_sensor x2, refresh_cover x2
- Final Schedule: `10` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|arrive_home_welcome_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006, batch_007. Writeback follows lane updates and then the overall update: batch_008 -> batch_009. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:3, hue:5, switchbot:3, tuya:4, xiaomi_ble:2` | `vdev_vdev_arrive_home_lighting_climate_prep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/esphome/__init__.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Kids' Room Comfort and Safety Snapshot (`vdev_kids_room_comfort_safety_snapshot_01`)

- Story: Parents trigger a quick children’s-room snapshot covering temperature, lights, curtains, climate, door or window safety, and air quality.
- Protocol Mix: BLE 5 / CLOUD 2 / LOCAL 3 / HA 4
- Main Action Types: read_sensor x4, write x4, get_state x2, status x2, read_last_message x1
- Final Schedule: `9` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_005, batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:3, mqtt:1, switchbot:2, tuya:3, xiaomi_ble:4` | `vdev_vdev_kids_room_comfort_safety_snapshot_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/switchbot/cover.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
