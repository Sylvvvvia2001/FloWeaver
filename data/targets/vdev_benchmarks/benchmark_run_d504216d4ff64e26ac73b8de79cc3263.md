# VDev Benchmark Run Report

- Run ID: `d504216d4ff64e26ac73b8de79cc3263`
- Case Count: `6`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_arrival_comfort_preparation_01 | Coming Home and Evening Comfort Routines | error | - | - | - | no |
| vdev_dinner_home_mode_01 | Coming Home and Evening Comfort Routines | error | - | - | - | no |
| vdev_weekend_whole_home_snapshot_01 | Night and Energy Monitoring Routines | error | - | - | - | no |
| vdev_good_morning_whole_floor_readiness_01 | Morning and Leaving Home Routines | error | - | - | - | no |
| vdev_weekend_whole_home_snapshot_extended_01 | Whole-Home Survey and Audit Routines | error | - | - | - | no |
| vdev_vacation_mode_house_sweep_01 | Whole-Home Survey and Audit Routines | error | - | - | - | no |

## Case Details

### Coming Home Comfort Preparation Routine (`vdev_arrival_comfort_preparation_01`)

- Story: Before arrival, the routine prepares a comfort snapshot by combining BLE sensors and curtains, cloud HVAC and lights, a Hue bridge read, and one MQTT air-quality read.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, read_sensor x2, refresh_cover x2, connect x1
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:3, hue:1, mqtt:1, switchbot:3, tplink:1, tuya:4, xiaomi_ble:2` | `vdev_vdev_arrival_comfort_preparation_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/esphome/__init__.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_arrival_comfort_preparation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/counterexamples.json`
- Generated Component: `missing`

### Dinner Time Home Mode Routine (`vdev_dinner_home_mode_01`)

- Story: Before dinner, the routine checks dining, kitchen, and living-room readiness across curtains, lights, HVAC, and energy sensors to decide whether the home is ready for dinner mode.
- Protocol Mix: BLE 4 / CLOUD 5 / LOCAL 3 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, refresh_cover x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, mqtt:1, switchbot:3, tplink:2, tuya:6, xiaomi_ble:2` | `vdev_vdev_dinner_home_mode_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `` |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_dinner_home_mode_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/counterexamples.json`
- Generated Component: `missing`

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Story: During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 4 / HA 4
- Main Action Types: status x7, write x4, get_state x3, read_sensor x3, refresh_cover x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:2, mqtt:1, switchbot:4, tplink:2, tuya:8, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/esphome/__init__.py` ... | `` |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/counterexamples.json`
- Generated Component: `missing`

### Good-Morning Whole-Floor Readiness (`vdev_good_morning_whole_floor_readiness_01`)

- Story: After wake-up time, the routine collects bedroom, living-room, and dining-room temperatures, lights, curtains, and climate states to decide whether the floor is already in morning mode.
- Protocol Mix: BLE 6 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: status x4, write x4, get_state x2, read_sensor x2, read_status x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, switchbot:3, tuya:5, xiaomi_ble:4` | `vdev_vdev_good_morning_whole_floor_readiness_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py` ... | `` |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/counterexamples.json`
- Generated Component: `missing`

### Weekend Whole-Home Snapshot Extended (`vdev_weekend_whole_home_snapshot_extended_01`)

- Story: On a weekend morning, the routine produces a larger whole-home snapshot of curtains, temperatures, air quality, lights, plugs, and climate to give the household a quick status overview.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 5 / HA 4
- Main Action Types: status x7, get_state x4, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:2, mqtt:1, switchbot:4, tplink:3, tuya:8, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_extended_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/esphome/__init__.py; data/repo_snapshot/esphome/manager.py` ... | `` |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/counterexamples.json`
- Generated Component: `missing`

### Vacation-Mode House Sweep (`vdev_vacation_mode_house_sweep_01`)

- Story: Before a longer trip, the routine runs one final whole-home sweep across curtains, sensors, lights, plugs, climate, and thermostat runtime to validate vacation-mode readiness.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 4 / HA 4
- Main Action Types: status x8, read_sensor x5, get_state x4, write x4, refresh_cover x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:2, switchbot:4, tplink:3, tuya:9, xiaomi_ble:5` | `vdev_vdev_vacation_mode_house_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_vacation_mode_house_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/counterexamples.json`
- Generated Component: `missing`
