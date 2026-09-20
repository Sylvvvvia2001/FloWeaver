# VDev Benchmark Run Report

- Run ID: `82672592194b4ece924bb3fe3e6c9d35`
- Case Count: `20`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_arrive_home_lighting_climate_prep_01 | Coming Home and Evening Comfort Routines | ok | 10 | 6 | 0 | yes |
| vdev_leave_home_safety_energy_sweep_01 | Morning and Leaving Home Routines | ok | 11 | 6 | 0 | yes |
| vdev_good_morning_whole_floor_readiness_01 | Morning and Leaving Home Routines | ok | 10 | 0 | 6 | yes |
| vdev_bedtime_lockdown_routine_01 | Night and Energy Monitoring Routines | ok | 11 | 6 | 0 | yes |
| vdev_rain_coming_indoor_adjustment_01 | Weather and Contextual Adjustment Routines | ok | 7 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_extended_01 | Whole-Home Survey and Audit Routines | ok | 13 | 6 | 0 | yes |
| vdev_dinner_preparation_readiness_01 | Coming Home and Evening Comfort Routines | ok | 7 | 6 | 0 | yes |
| vdev_party_preparation_ambience_check_01 | Coming Home and Evening Comfort Routines | ok | 9 | 6 | 0 | yes |
| vdev_workday_departure_office_zone_shutdown_01 | Morning and Leaving Home Routines | ok | 6 | 6 | 0 | yes |
| vdev_kids_room_comfort_safety_snapshot_01 | Family Care and Room-Level Snapshot Routines | ok | 9 | 6 | 0 | yes |
| vdev_elderly_care_daily_check_01 | Family Care and Room-Level Snapshot Routines | ok | 7 | 6 | 0 | yes |
| vdev_laundry_utility_room_sweep_01 | Family Care and Room-Level Snapshot Routines | ok | 6 | 6 | 0 | yes |
| vdev_air_quality_recovery_routine_01 | Family Care and Room-Level Snapshot Routines | ok | 6 | 6 | 0 | yes |
| vdev_vacation_mode_house_sweep_01 | Whole-Home Survey and Audit Routines | ok | 13 | 0 | 6 | yes |
| vdev_homecoming_security_ambience_merge_01 | Scene Activation and Comfort Control Routines | ok | 6 | 6 | 0 | yes |
| vdev_school_night_quiet_hours_01 | Night and Energy Monitoring Routines | ok | 8 | 6 | 0 | yes |
| vdev_rainy_commute_preparation_01 | Weather and Contextual Adjustment Routines | ok | 6 | 6 | 0 | yes |
| vdev_energy_hvac_audit_expanded_01 | Whole-Home Survey and Audit Routines | ok | 5 | 6 | 0 | yes |
| vdev_whole_home_ble_safety_sweep_01 | Household Stress and Abnormality Routines | ok | 15 | 6 | 0 | yes |
| vdev_cloud_burst_living_conditions_snapshot_01 | Whole-Home Survey and Audit Routines | ok | 6 | 6 | 0 | yes |

## Case Details

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

### Leave-Home Safety and Energy Sweep (`vdev_leave_home_safety_energy_sweep_01`)

- Story: When everyone leaves, the routine checks lights, curtains, plugs, climate, and entry sensors, then publishes one leave-home safety and energy summary.
- Protocol Mix: BLE 6 / CLOUD 6 / LOCAL 4 / HA 4
- Main Action Types: status x6, get_state x4, write x4, refresh_cover x3, read_sensor x2
- Final Schedule: `11` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|leave_energy_switches groups 3 actions into 1 chunks; tuya|leave_energy_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_007, batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `10` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|morning_floor_hvac groups 2 actions into 1 chunks; tuya|morning_floor_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_006. Writeback follows lane updates and then the overall update: batch_008 -> batch_009.

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

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Bedtime Lockdown Routine (`vdev_bedtime_lockdown_routine_01`)

- Story: Before everyone goes to sleep, the routine checks lights, curtains, plugs, climate, and door or window sensors, then publishes a bedtime lockdown summary.
- Protocol Mix: BLE 6 / CLOUD 6 / LOCAL 3 / HA 4
- Main Action Types: status x6, write x4, get_state x3, read_sensor x2, read_status x2
- Final Schedule: `11` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|bedtime_lights groups 3 actions into 1 chunks; tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_007, batch_008. Writeback follows lane updates and then the overall update: batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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

### Rain-Coming Indoor Adjustment (`vdev_rain_coming_indoor_adjustment_01`)

- Story: When rain starts, the routine checks window-side curtains, nearby lights, indoor climate, air quality, and one comfort thermostat to publish a rainy-day indoor adjustment suggestion.
- Protocol Mix: BLE 3 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: write x4, status x3, get_state x2, refresh_cover x2, read_last_message x1
- Final Schedule: `7` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|rain_window_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_003, batch_004. Writeback follows lane updates and then the overall update: batch_005 -> batch_006. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `10` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, mqtt:1, switchbot:3, tuya:4, xiaomi_ble:1` | `vdev_vdev_rain_coming_indoor_adjustment_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 10 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Weekend Whole-Home Snapshot Extended (`vdev_weekend_whole_home_snapshot_extended_01`)

- Story: On a weekend morning, the routine produces a larger whole-home snapshot of curtains, temperatures, air quality, lights, plugs, and climate to give the household a quick status overview.
- Protocol Mix: BLE 8 / CLOUD 7 / LOCAL 5 / HA 4
- Main Action Types: status x7, get_state x4, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|weekend_ext_lights groups 3 actions into 1 chunks; tuya|weekend_ext_energy groups 2 actions into 1 chunks. Local reads overlap other reads in batch_009, batch_010. Writeback follows lane updates and then the overall update: batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

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

### Dinner Preparation Readiness (`vdev_dinner_preparation_readiness_01`)

- Story: Before dinner, the routine checks dining lights, kitchen lights, dining climate, a kitchen plug, curtains, and indoor air quality to decide whether dinner mode is ready.
- Protocol Mix: BLE 3 / CLOUD 5 / LOCAL 3 / HA 4
- Main Action Types: status x5, write x4, get_state x2, read_sensor x2, read_last_message x1
- Final Schedule: `7` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|dinner_prep_lights groups 3 actions into 1 chunks. Local reads overlap other reads in batch_004. Writeback follows lane updates and then the overall update: batch_005 -> batch_006. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, mqtt:1, switchbot:2, tplink:2, tuya:6, xiaomi_ble:2` | `vdev_vdev_dinner_preparation_readiness_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_dinner_preparation_readiness_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Party Preparation and Ambience Check (`vdev_party_preparation_ambience_check_01`)

- Story: Before a gathering, the routine checks room lights, color ambience, curtains, climate, speaker plugs, and purifier state to decide whether the party setup is ready.
- Protocol Mix: BLE 4 / CLOUD 6 / LOCAL 4 / HA 4
- Main Action Types: status x6, get_state x4, write x4, refresh_cover x2, read_sensor x1
- Final Schedule: `9` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|party_ambience_lights groups 3 actions into 1 chunks; tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_005, batch_006. Writeback follows lane updates and then the overall update: batch_007 -> batch_008. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:5, switchbot:4, tuya:7, xiaomi_ble:1` | `vdev_vdev_party_preparation_ambience_check_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_preparation_ambience_check_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Workday Departure Office-Zone Shutdown (`vdev_workday_departure_office_zone_shutdown_01`)

- Story: After leaving for work, the routine does one compact office-zone sweep across curtains, desk lights, monitor plugs, printer plug, and study climate.
- Protocol Mix: BLE 2 / CLOUD 2 / LOCAL 4 / HA 4
- Main Action Types: get_state x4, write x4, status x2, read_sensor x1, refresh_cover x1
- Final Schedule: `6` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_002, batch_003. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:2, switchbot:2, tplink:3, tuya:3, xiaomi_ble:1` | `vdev_vdev_workday_departure_office_zone_shutdown_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01`

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

### Elderly Care Daily Check (`vdev_elderly_care_daily_check_01`)

- Story: At a fixed time each day, the system checks one elder room’s climate, lighting, temperature, curtain, motion, and air quality state and writes a care-oriented daily summary.
- Protocol Mix: BLE 3 / CLOUD 3 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x2, read_sensor x2, status x2, read_last_message x1
- Final Schedule: `7` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_003, batch_004. Writeback follows lane updates and then the overall update: batch_005 -> batch_006. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, mqtt:1, switchbot:2, tuya:3, xiaomi_ble:2` | `vdev_vdev_elderly_care_daily_check_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_elderly_care_daily_check_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Laundry and Utility Room Sweep (`vdev_laundry_utility_room_sweep_01`)

- Story: On a utility-room schedule, the system checks washer and dryer plugs, ventilation, light, door sensor, and temperature to produce one laundry-area health summary.
- Protocol Mix: BLE 2 / CLOUD 2 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x2, read_sensor x2, status x2, read_last_message x1
- Final Schedule: `6` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_002, batch_003. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, mqtt:1, switchbot:1, tplink:3, tuya:3, xiaomi_ble:2` | `vdev_vdev_laundry_utility_room_sweep_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_laundry_utility_room_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Air Quality Recovery Routine (`vdev_air_quality_recovery_routine_01`)

- Story: After indoor air quality drops, the routine checks purifier state, nearby temperature, climate, switches, lights, and air-quality feeds to decide whether recovery is progressing normally.
- Protocol Mix: BLE 2 / CLOUD 3 / LOCAL 4 / HA 4
- Main Action Types: write x4, status x3, get_state x2, read_last_message x2, read_sensor x1
- Final Schedule: `6` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|air_recovery_switches groups 2 actions into 1 chunks. Local reads overlap other reads in batch_002, batch_003. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `8` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:3, mqtt:2, switchbot:2, tuya:4, xiaomi_ble:1` | `vdev_vdev_air_quality_recovery_routine_01` |
| Main Source Files | `data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/tuya/switch.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 8 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_air_quality_recovery_routine_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Vacation-Mode House Sweep (`vdev_vacation_mode_house_sweep_01`)

- Story: Before a longer trip, the routine runs one final whole-home sweep across curtains, sensors, lights, plugs, climate, and thermostat runtime to validate vacation-mode readiness.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 4 / HA 4
- Main Action Types: status x8, read_sensor x5, get_state x4, write x4, refresh_cover x3
- Final Schedule: `13` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `0`, tolerant `0`, counterexamples `6`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|vacation_lights groups 3 actions into 1 chunks; tuya|vacation_switches groups 2 actions into 1 chunks; tuya|vacation_hvac groups 2 actions into 1 chunks. Local reads overlap other reads in batch_009, batch_010. Writeback follows lane updates and then the overall update: batch_011 -> batch_012.

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

- Strict pass scenarios: `0`
- Tolerant pass scenarios: `0`
- Counterexample count: `6`

### Homecoming Security and Ambience Merge (`vdev_homecoming_security_ambience_merge_01`)

- Story: At arrival time, the routine merges a small security reassurance sweep with lighting and comfort checks to decide whether the home is ready for a safe, pleasant arrival.
- Protocol Mix: BLE 2 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x3, status x3, read_runtime x1, read_sensor x1
- Final Schedule: `6` batches, max `4` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya|homecoming_lights groups 2 actions into 1 chunks. Local reads overlap other reads in batch_002, batch_003. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:4, switchbot:2, tuya:4, xiaomi_ble:1` | `vdev_vdev_homecoming_security_ambience_merge_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### School-Night Quiet Hours Routine (`vdev_school_night_quiet_hours_01`)

- Story: At a fixed school-night quiet-hours time, the routine checks curtains, bedside lights, hallway lights, heater plug, window state, and climate to confirm the house is in a quieter night state.
- Protocol Mix: BLE 5 / CLOUD 3 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x3, status x3, read_status x2, refresh_cover x2
- Final Schedule: `8` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 3 actions into 1 chunks. Local reads overlap other reads in batch_005. Writeback follows lane updates and then the overall update: batch_006 -> batch_007. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:2, switchbot:3, tplink:2, tuya:4, xiaomi_ble:3` | `vdev_vdev_school_night_quiet_hours_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/xiaomi_ble/event.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_school_night_quiet_hours_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Rainy Commute Preparation (`vdev_rainy_commute_preparation_01`)

- Story: When rain overlaps with the morning commute window, the routine checks entry lights, curtain, door state, and a small comfort set to decide whether rainy-commute preparation is needed.
- Protocol Mix: BLE 2 / CLOUD 2 / LOCAL 2 / HA 4
- Main Action Types: write x4, get_state x2, status x2, read_sensor x1, refresh_cover x1
- Final Schedule: `6` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Cloud reads are grouped by provider and endpoint: tuya groups 2 actions into 1 chunks. Local reads overlap other reads in batch_002. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `5` integrations / `8` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:3, switchbot:2, tuya:3, xiaomi_ble:1` | `vdev_vdev_rainy_commute_preparation_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 5 integrations and approximately 8 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_rainy_commute_preparation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Energy and HVAC Audit Expanded (`vdev_energy_hvac_audit_expanded_01`)

- Story: At a fixed audit time, the routine collects whole-home lights, plugs, climates, thermostats, and two local smart-plug checks to produce one expanded energy and HVAC audit.
- Protocol Mix: CLOUD 10 / LOCAL 2 / HA 3
- Main Action Types: status x8, write x3, get_state x2, read_runtime x2
- Final Schedule: `5` batches, max `3` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01`

**Schedule Interpretation**

Cloud reads are grouped by provider and endpoint: tuya|energy_expanded_lights groups 3 actions into 1 chunks; tuya|energy_expanded_switches groups 2 actions into 1 chunks; tuya|energy_expanded_hvac groups 2 actions into 1 chunks. Local reads overlap other reads in batch_001, batch_002. Writeback follows lane updates and then the overall update: batch_003 -> batch_004. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `4` integrations / `7` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, tplink:3, tuya:9` | `vdev_vdev_energy_hvac_audit_expanded_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 4 integrations and approximately 7 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Whole-Home BLE Safety Sweep (`vdev_whole_home_ble_safety_sweep_01`)

- Story: At a fixed time, the routine performs one realistic whole-home BLE sweep over curtains, door or window sensors, motion sensors, temperatures, and one ESPHome transport pair.
- Protocol Mix: BLE 13 / HA 2
- Main Action Types: read_sensor x8, refresh_cover x3, write x2, connect x1, subscribe x1
- Final Schedule: `15` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01`

**Schedule Interpretation**

The first 13 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_013 -> batch_014. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `3` integrations / `8` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, switchbot:4, xiaomi_ble:8` | `vdev_vdev_whole_home_ble_safety_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/event.py; data/repo_snapshot/xiaomi_ble/sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 3 integrations and approximately 8 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_ble_safety_sweep_01/reassembly/vdev_vdev_whole_home_ble_safety_sweep_01/custom_components/vdev_vdev_whole_home_ble_safety_sweep_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Cloud Burst Living-Conditions Snapshot (`vdev_cloud_burst_living_conditions_snapshot_01`)

- Story: At a scheduled mode-change checkpoint, the routine bursts through lighting, switch, and HVAC endpoints to build one cloud-only living-conditions snapshot.
- Protocol Mix: CLOUD 12 / HA 2
- Main Action Types: status x10, read_runtime x2, write x2
- Final Schedule: `6` batches, max `2` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01`

**Schedule Interpretation**

Cloud reads are grouped by provider and endpoint: tuya|cloud_snapshot_lights groups 4 actions into 2 chunks; tuya|cloud_snapshot_switches groups 4 actions into 2 chunks; tuya|cloud_snapshot_hvac groups 2 actions into 1 chunks. Writeback follows lane updates and then the overall update: batch_004 -> batch_005. M6 found no counterexamples in the evaluated replay scenarios.

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
