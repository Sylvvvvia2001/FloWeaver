# VDev Benchmark Run Report

- Run ID: `2fcd4c94897a4eaca294ea378ed67d06`
- Case Count: `11`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_01 | Morning and Leaving Home Routines | ok | 10 | 6 | 0 | yes |
| vdev_arrival_comfort_preparation_01 | Coming Home and Evening Comfort Routines | ok | 9 | 6 | 0 | yes |
| vdev_dinner_home_mode_01 | Coming Home and Evening Comfort Routines | ok | 7 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_01 | Night and Energy Monitoring Routines | ok | 11 | 6 | 0 | yes |
| vdev_leave_home_safety_energy_sweep_01 | Morning and Leaving Home Routines | ok | 9 | 6 | 0 | yes |
| vdev_good_morning_whole_floor_readiness_01 | Morning and Leaving Home Routines | ok | 9 | 6 | 0 | yes |
| vdev_bedtime_lockdown_routine_01 | Night and Energy Monitoring Routines | ok | 9 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_extended_01 | Whole-Home Survey and Audit Routines | ok | 11 | 6 | 0 | yes |
| vdev_kids_room_comfort_safety_snapshot_01 | Family Care and Room-Level Snapshot Routines | ok | 8 | 6 | 0 | yes |
| vdev_vacation_mode_house_sweep_01 | Whole-Home Survey and Audit Routines | ok | 11 | 6 | 0 | yes |
| vdev_cloud_burst_living_conditions_snapshot_01 | Whole-Home Survey and Audit Routines | ok | 4 | 6 | 0 | yes |

## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Story: Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.
- Protocol Mix: BLE 7 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, get_state x2, read_status x2, refresh_cover x2
- Final Schedule: `10` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|morning_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_007. Writeback follows lane updates and then the overall update: batch_008 -> batch_009. M6 found no counterexamples in the evaluated replay scenarios.

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

### Dinner Time Home Mode Routine (`vdev_dinner_home_mode_01`)

- Story: Before dinner, the routine checks dining, kitchen, and living-room readiness across curtains, lights, HVAC, and energy sensors to decide whether the home is ready for dinner mode.
- Protocol Mix: BLE 4 / CLOUD 5 / LOCAL 3 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, refresh_cover x2
- Final Schedule: `7` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|dinner_lights groups 3 actions into 1 chunks. Local reads overlap other reads in batch_004. Writeback follows lane updates and then the overall update: batch_005 -> batch_006. M6 found no counterexamples in the evaluated replay scenarios.

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

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Story: During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 4 / HA 4
- Main Action Types: status x7, write x4, get_state x3, read_sensor x3, refresh_cover x3
- Final Schedule: `11` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|weekend_lights groups 3 actions into 1 chunks; tuya|weekend_hvac groups 2 actions into 1 chunks; tuya|weekend_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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

### Leave-Home Safety and Energy Sweep (`vdev_leave_home_safety_energy_sweep_01`)

- Story: When everyone leaves, the routine checks lights, curtains, plugs, climate, and entry sensors, then publishes one leave-home safety and energy summary.
- Protocol Mix: BLE 6 / CLOUD 6 / LOCAL 4 / HA 4
- Main Action Types: status x6, get_state x4, write x4, refresh_cover x3, read_sensor x2
- Final Schedule: `9` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|leave_energy_switches groups 3 actions into 1 chunks; tuya|leave_energy_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:2, switchbot:4, tplink:3, tuya:7, xiaomi_ble:3` | `vdev_vdev_leave_home_safety_energy_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/device.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Good-Morning Whole-Floor Readiness (`vdev_good_morning_whole_floor_readiness_01`)

- Story: After wake-up time, the routine collects bedroom, living-room, and dining-room temperatures, lights, curtains, and climate states to decide whether the floor is already in morning mode.
- Protocol Mix: BLE 6 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: status x4, write x4, get_state x2, read_sensor x2, read_status x2
- Final Schedule: `9` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|morning_floor_hvac groups 2 actions into 1 chunks; tuya|morning_floor_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, switchbot:3, tuya:5, xiaomi_ble:4` | `vdev_vdev_good_morning_whole_floor_readiness_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Bedtime Lockdown Routine (`vdev_bedtime_lockdown_routine_01`)

- Story: Before everyone goes to sleep, the routine checks lights, curtains, plugs, climate, and door or window sensors, then publishes a bedtime lockdown summary.
- Protocol Mix: BLE 6 / CLOUD 6 / LOCAL 3 / HA 4
- Main Action Types: status x6, write x4, get_state x3, read_sensor x2, read_status x2
- Final Schedule: `9` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|bedtime_lights groups 3 actions into 1 chunks; tuya|bedtime_switches groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, switchbot:3, tplink:3, tuya:7, xiaomi_ble:4` | `vdev_vdev_bedtime_lockdown_routine_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_bedtime_lockdown_routine_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Weekend Whole-Home Snapshot Extended (`vdev_weekend_whole_home_snapshot_extended_01`)

- Story: On a weekend morning, the routine produces a larger whole-home snapshot of curtains, temperatures, air quality, lights, plugs, and climate to give the household a quick status overview.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 5 / HA 4
- Main Action Types: status x7, get_state x4, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `11` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|weekend_ext_lights groups 3 actions into 1 chunks; tuya|weekend_ext_hvac groups 2 actions into 1 chunks; tuya|weekend_ext_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:2, mqtt:1, switchbot:4, tplink:3, tuya:8, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_extended_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/esphome/__init__.py; data/repo_snapshot/esphome/manager.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Kids' Room Comfort and Safety Snapshot (`vdev_kids_room_comfort_safety_snapshot_01`)

- Story: Parents trigger a quick children’s-room snapshot covering temperature, lights, curtains, climate, door or window safety, and air quality.
- Protocol Mix: BLE 5 / CLOUD 2 / LOCAL 3 / HA 4
- Main Action Types: read_sensor x4, write x4, get_state x2, status x2, read_last_message x1
- Final Schedule: `8` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_005. Writeback follows lane updates and then the overall update: batch_006 -> batch_007. M6 found no counterexamples in the evaluated replay scenarios.

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

### Vacation-Mode House Sweep (`vdev_vacation_mode_house_sweep_01`)

- Story: Before a longer trip, the routine runs one final whole-home sweep across curtains, sensors, lights, plugs, climate, and thermostat runtime to validate vacation-mode readiness.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 4 / HA 4
- Main Action Types: status x8, read_sensor x5, get_state x4, write x4, refresh_cover x3
- Final Schedule: `11` batches, max `5` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|vacation_lights groups 3 actions into 1 chunks; tuya|vacation_switches groups 3 actions into 1 chunks; tuya|vacation_hvac groups 2 actions into 1 chunks. Local reads overlap other reads in batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:2, switchbot:4, tplink:3, tuya:9, xiaomi_ble:5` | `vdev_vdev_vacation_mode_house_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_vacation_mode_house_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Cloud Burst Living-Conditions Snapshot (`vdev_cloud_burst_living_conditions_snapshot_01`)

- Story: At a scheduled mode-change checkpoint, the routine bursts through lighting, switch, and HVAC endpoints to build one cloud-only living-conditions snapshot.
- Protocol Mix: CLOUD 12 / HA 2
- Main Action Types: status x10, read_runtime x2, write x2
- Final Schedule: `4` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01`

**Schedule Interpretation**

Cloud reads are grouped by provider and endpoint: tuya|cloud_snapshot_lights groups 4 actions into 2 chunks; tuya|cloud_snapshot_switches groups 4 actions into 2 chunks; tuya|cloud_snapshot_hvac groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_002 -> batch_003. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `3` integrations / `6` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, tuya:11` | `vdev_vdev_cloud_burst_living_conditions_snapshot_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 3 integrations and approximately 6 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
