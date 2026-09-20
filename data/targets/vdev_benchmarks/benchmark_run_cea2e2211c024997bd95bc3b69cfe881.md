# VDev Benchmark Run Report

- Run ID: `cea2e2211c024997bd95bc3b69cfe881`
- Case Count: `56`

## Overview

| Case | Group | Status | Batches | Strict Pass | Counterexamples | M7 Reassembly |
| --- | --- | --- | ---: | ---: | ---: | --- |
| vdev_morning_wakeup_readiness_01 | Morning and Leaving Home Routines | ok | 16 | 6 | 0 | yes |
| vdev_leaving_home_safety_check_01 | Morning and Leaving Home Routines | ok | 16 | 6 | 0 | yes |
| vdev_arrival_comfort_preparation_01 | Coming Home and Evening Comfort Routines | ok | 16 | 6 | 0 | yes |
| vdev_dinner_home_mode_01 | Coming Home and Evening Comfort Routines | ok | 16 | 6 | 0 | yes |
| vdev_night_shutdown_01 | Night and Energy Monitoring Routines | ok | 17 | 6 | 0 | yes |
| vdev_overnight_health_safety_monitoring_01 | Night and Energy Monitoring Routines | ok | 16 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_01 | Night and Energy Monitoring Routines | ok | 23 | 6 | 0 | yes |
| vdev_party_preparation_01 | Coming Home and Evening Comfort Routines | ok | 17 | 6 | 0 | yes |
| vdev_party_scene_activation_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_movie_night_blackout_01 | Scene Activation and Comfort Control Routines | ok | 26 | 6 | 0 | yes |
| vdev_morning_wakeup_ramp_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_workday_focus_mode_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_guest_suite_welcome_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_storm_lockdown_safety_01 | Scene Activation and Comfort Control Routines | error | - | - | - | no |
| vdev_ble_safety_sweep_stress_01 | Household Stress and Abnormality Routines | ok | 11 | 6 | 0 | yes |
| vdev_energy_hvac_audit_01 | Household Stress and Abnormality Routines | ok | 12 | 6 | 0 | yes |
| vdev_arrive_home_lighting_climate_prep_01 | Coming Home and Evening Comfort Routines | ok | 18 | 6 | 0 | yes |
| vdev_leave_home_safety_energy_sweep_01 | Morning and Leaving Home Routines | ok | 20 | 6 | 0 | yes |
| vdev_good_morning_whole_floor_readiness_01 | Morning and Leaving Home Routines | ok | 17 | 6 | 0 | yes |
| vdev_bedtime_lockdown_routine_01 | Night and Energy Monitoring Routines | ok | 19 | 6 | 0 | yes |
| vdev_rain_coming_indoor_adjustment_01 | Weather and Contextual Adjustment Routines | ok | 14 | 6 | 0 | yes |
| vdev_weekend_whole_home_snapshot_extended_01 | Whole-Home Survey and Audit Routines | ok | 24 | 6 | 0 | yes |
| vdev_dinner_preparation_readiness_01 | Coming Home and Evening Comfort Routines | ok | 15 | 6 | 0 | yes |
| vdev_party_preparation_ambience_check_01 | Coming Home and Evening Comfort Routines | ok | 18 | 6 | 0 | yes |
| vdev_workday_departure_office_zone_shutdown_01 | Morning and Leaving Home Routines | ok | 12 | 6 | 0 | yes |
| vdev_kids_room_comfort_safety_snapshot_01 | Family Care and Room-Level Snapshot Routines | ok | 14 | 6 | 0 | yes |
| vdev_elderly_care_daily_check_01 | Family Care and Room-Level Snapshot Routines | ok | 13 | 6 | 0 | yes |
| vdev_laundry_utility_room_sweep_01 | Family Care and Room-Level Snapshot Routines | ok | 11 | 6 | 0 | yes |
| vdev_air_quality_recovery_routine_01 | Family Care and Room-Level Snapshot Routines | ok | 13 | 6 | 0 | yes |
| vdev_vacation_mode_house_sweep_01 | Whole-Home Survey and Audit Routines | ok | 25 | 6 | 0 | yes |
| vdev_homecoming_security_ambience_merge_01 | Scene Activation and Comfort Control Routines | ok | 13 | 6 | 0 | yes |
| vdev_school_night_quiet_hours_01 | Night and Energy Monitoring Routines | ok | 15 | 6 | 0 | yes |
| vdev_rainy_commute_preparation_01 | Weather and Contextual Adjustment Routines | ok | 10 | 6 | 0 | yes |
| vdev_energy_hvac_audit_expanded_01 | Whole-Home Survey and Audit Routines | ok | 15 | 6 | 0 | yes |
| vdev_whole_home_ble_safety_sweep_01 | Household Stress and Abnormality Routines | ok | 15 | 6 | 0 | yes |
| vdev_cloud_burst_living_conditions_snapshot_01 | Whole-Home Survey and Audit Routines | ok | 14 | 6 | 0 | yes |
| vdev_morning_wakeup_readiness_profile_01 | Profile Coverage - Morning Routines | ok | 16 | 6 | 0 | yes |
| vdev_whole_family_morning_comfort_snapshot_01 | Profile Coverage - Morning Routines | error | - | - | - | no |
| vdev_school_day_quiet_start_check_01 | Profile Coverage - Morning Routines | ok | 13 | 6 | 0 | yes |
| vdev_bad_air_morning_recovery_01 | Profile Coverage - Morning Routines | error | - | - | - | no |
| vdev_leave_home_safety_sweep_profile_01 | Profile Coverage - Arrival and Departure Routines | error | - | - | - | no |
| vdev_arrival_home_preparation_profile_01 | Profile Coverage - Arrival and Departure Routines | ok | 15 | 6 | 0 | yes |
| vdev_vacation_departure_final_audit_01 | Profile Coverage - Arrival and Departure Routines | error | - | - | - | no |
| vdev_come_home_security_comfort_merge_01 | Profile Coverage - Arrival and Departure Routines | ok | 14 | 6 | 0 | yes |
| vdev_bedtime_lockdown_profile_01 | Profile Coverage - Evening and Overnight Routines | ok | 19 | 6 | 0 | yes |
| vdev_kids_room_night_safety_check_01 | Profile Coverage - Evening and Overnight Routines | ok | 12 | 6 | 0 | yes |
| vdev_late_night_entertainment_shutdown_01 | Profile Coverage - Evening and Overnight Routines | error | - | - | - | no |
| vdev_overnight_quiet_hours_snapshot_01 | Profile Coverage - Evening and Overnight Routines | error | - | - | - | no |
| vdev_weekend_whole_home_snapshot_profile_01 | Profile Coverage - Monitoring and Audit Routines | error | - | - | - | no |
| vdev_whole_home_energy_hvac_audit_profile_01 | Profile Coverage - Monitoring and Audit Routines | ok | 21 | 6 | 0 | yes |
| vdev_indoor_air_climate_audit_01 | Profile Coverage - Monitoring and Audit Routines | error | - | - | - | no |
| vdev_security_presence_fabric_snapshot_01 | Profile Coverage - Monitoring and Audit Routines | ok | 17 | 6 | 0 | yes |
| vdev_party_preparation_full_sweep_01 | Profile Coverage - Realistic Stress Routines | error | - | - | - | no |
| vdev_holiday_vacation_mode_full_audit_01 | Profile Coverage - Realistic Stress Routines | error | - | - | - | no |
| vdev_ble_safety_sweep_routine_01 | Profile Coverage - Realistic Stress Routines | error | - | - | - | no |
| vdev_cloud_burst_living_conditions_snapshot_profile_01 | Profile Coverage - Realistic Stress Routines | ok | 22 | 6 | 0 | yes |

## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Story: Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.
- Protocol Mix: BLE 7 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, get_state x2, read_status x2, refresh_cover x2
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_01/reassembly/vdev_vdev_morning_wakeup_readiness_01/custom_components/vdev_vdev_morning_wakeup_readiness_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leaving_home_safety_check_01/reassembly/vdev_vdev_leaving_home_safety_check_01/custom_components/vdev_vdev_leaving_home_safety_check_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_comfort_preparation_01/reassembly/vdev_vdev_arrival_comfort_preparation_01/custom_components/vdev_vdev_arrival_comfort_preparation_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_home_mode_01/reassembly/vdev_vdev_dinner_home_mode_01/custom_components/vdev_vdev_dinner_home_mode_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_night_shutdown_01/reassembly/vdev_vdev_night_shutdown_01/custom_components/vdev_vdev_night_shutdown_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_013 -> batch_014 -> batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_health_safety_monitoring_01/reassembly/vdev_vdev_overnight_health_safety_monitoring_01/custom_components/vdev_vdev_overnight_health_safety_monitoring_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `23` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_019 -> batch_020 -> batch_021 -> batch_022. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_01/reassembly/vdev_vdev_party_preparation_01/custom_components/vdev_vdev_party_preparation_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_013 -> batch_014 -> batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

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

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Story: Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:1, mqtt:1, switchbot:5, tplink:2, tuya:13, xiaomi_ble:2` | `vdev_vdev_party_scene_activation_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_scene_activation_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_scene_activation_01/counterexamples.json`
- Generated Component: `missing`

### Movie Night Blackout Routine (`vdev_movie_night_blackout_01`)

- Story: Before a movie starts, the routine darkens the viewing area by closing multiple covers, shifting lights into a dim warm scene, adjusting climate and fan comfort, then verifying the blackout state before publishing movie-night readiness summaries.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, write x4, turn_on x3, get_state x2
- Final Schedule: `26` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_movie_night_blackout_01/reassembly/vdev_vdev_movie_night_blackout_01/custom_components/vdev_vdev_movie_night_blackout_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_022 -> batch_023 -> batch_024 -> batch_025. M6 found no counterexamples in the evaluated replay scenarios.

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

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Morning Wake-Up Ramp Routine (`vdev_morning_wakeup_ramp_01`)

- Story: At wake-up time, the routine opens multiple covers, ramps key lights to morning brightness and color temperature, nudges HVAC and fan comfort, then verifies representative state before publishing one wake-up summary.
- Protocol Mix: BLE 6 / CLOUD 13 / LOCAL 3 / HA 4
- Main Action Types: status x5, set_cover_position x4, turn_on x4, write x4, get_state x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `14` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:3, mqtt:1, switchbot:5, tuya:13, xiaomi_ble:2` | `vdev_vdev_morning_wakeup_ramp_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `` |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 14 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_morning_wakeup_ramp_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_ramp_01/counterexamples.json`
- Generated Component: `missing`

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
- Final Schedule: `12` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_01/reassembly/vdev_vdev_energy_hvac_audit_01/custom_components/vdev_vdev_energy_hvac_audit_01`

**Schedule Interpretation**

Writeback follows lane updates and then the overall update: batch_010 -> batch_011. M6 found no counterexamples in the evaluated replay scenarios.

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

### Arrive-Home Lighting and Climate Prep (`vdev_arrive_home_lighting_climate_prep_01`)

- Story: Before residents get home, the routine checks living-room, hallway, and bedroom lights, curtains, climate, and air quality to decide whether the house is ready to enter a welcome-home state.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 4 / HA 4
- Main Action Types: get_state x4, write x4, status x3, read_sensor x2, refresh_cover x2
- Final Schedule: `18` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrive_home_lighting_climate_prep_01/reassembly/vdev_vdev_arrive_home_lighting_climate_prep_01/custom_components/vdev_vdev_arrive_home_lighting_climate_prep_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_014 -> batch_015 -> batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `20` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_energy_sweep_01/reassembly/vdev_vdev_leave_home_safety_energy_sweep_01/custom_components/vdev_vdev_leave_home_safety_energy_sweep_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_016 -> batch_017 -> batch_018 -> batch_019. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_good_morning_whole_floor_readiness_01/reassembly/vdev_vdev_good_morning_whole_floor_readiness_01/custom_components/vdev_vdev_good_morning_whole_floor_readiness_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_013 -> batch_014 -> batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `19` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_routine_01/reassembly/vdev_vdev_bedtime_lockdown_routine_01/custom_components/vdev_vdev_bedtime_lockdown_routine_01`

**Schedule Interpretation**

The first 6 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_015 -> batch_016 -> batch_017 -> batch_018. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `14` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rain_coming_indoor_adjustment_01/reassembly/vdev_vdev_rain_coming_indoor_adjustment_01/custom_components/vdev_vdev_rain_coming_indoor_adjustment_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_010 -> batch_011 -> batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `24` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_extended_01/reassembly/vdev_vdev_weekend_whole_home_snapshot_extended_01/custom_components/vdev_vdev_weekend_whole_home_snapshot_extended_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_020 -> batch_021 -> batch_022 -> batch_023. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `15` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_dinner_preparation_readiness_01/reassembly/vdev_vdev_dinner_preparation_readiness_01/custom_components/vdev_vdev_dinner_preparation_readiness_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_011 -> batch_012 -> batch_013 -> batch_014. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `18` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_ambience_check_01/reassembly/vdev_vdev_party_preparation_ambience_check_01/custom_components/vdev_vdev_party_preparation_ambience_check_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_014 -> batch_015 -> batch_016 -> batch_017. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `12` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_workday_departure_office_zone_shutdown_01/reassembly/vdev_vdev_workday_departure_office_zone_shutdown_01/custom_components/vdev_vdev_workday_departure_office_zone_shutdown_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_008 -> batch_009 -> batch_010 -> batch_011. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `14` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_comfort_safety_snapshot_01/reassembly/vdev_vdev_kids_room_comfort_safety_snapshot_01/custom_components/vdev_vdev_kids_room_comfort_safety_snapshot_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_010 -> batch_011 -> batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `13` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_elderly_care_daily_check_01/reassembly/vdev_vdev_elderly_care_daily_check_01/custom_components/vdev_vdev_elderly_care_daily_check_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_009 -> batch_010 -> batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `11` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_laundry_utility_room_sweep_01/reassembly/vdev_vdev_laundry_utility_room_sweep_01/custom_components/vdev_vdev_laundry_utility_room_sweep_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_007 -> batch_008 -> batch_009 -> batch_010. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `13` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_air_quality_recovery_routine_01/reassembly/vdev_vdev_air_quality_recovery_routine_01/custom_components/vdev_vdev_air_quality_recovery_routine_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_009 -> batch_010 -> batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `25` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_mode_house_sweep_01/reassembly/vdev_vdev_vacation_mode_house_sweep_01/custom_components/vdev_vdev_vacation_mode_house_sweep_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_021 -> batch_022 -> batch_023 -> batch_024. M6 found no counterexamples in the evaluated replay scenarios.

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

### Homecoming Security and Ambience Merge (`vdev_homecoming_security_ambience_merge_01`)

- Story: At arrival time, the routine merges a small security reassurance sweep with lighting and comfort checks to decide whether the home is ready for a safe, pleasant arrival.
- Protocol Mix: BLE 2 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x3, status x3, read_runtime x1, read_sensor x1
- Final Schedule: `13` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_homecoming_security_ambience_merge_01/reassembly/vdev_vdev_homecoming_security_ambience_merge_01/custom_components/vdev_vdev_homecoming_security_ambience_merge_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_009 -> batch_010 -> batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `15` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_night_quiet_hours_01/reassembly/vdev_vdev_school_night_quiet_hours_01/custom_components/vdev_vdev_school_night_quiet_hours_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_011 -> batch_012 -> batch_013 -> batch_014. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `10` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_rainy_commute_preparation_01/reassembly/vdev_vdev_rainy_commute_preparation_01/custom_components/vdev_vdev_rainy_commute_preparation_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_006 -> batch_007 -> batch_008 -> batch_009. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `15` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_energy_hvac_audit_expanded_01/reassembly/vdev_vdev_energy_hvac_audit_expanded_01/custom_components/vdev_vdev_energy_hvac_audit_expanded_01`

**Schedule Interpretation**

Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014. M6 found no counterexamples in the evaluated replay scenarios.

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
- Final Schedule: `14` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_01`

**Schedule Interpretation**

Writeback follows lane updates and then the overall update: batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

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

### Morning Wake-Up Readiness Profile Coverage (`vdev_morning_wakeup_readiness_profile_01`)

- Story: After residents wake up, the routine quickly checks bedroom and hallway readiness across curtains, bedside lamps, environmental sensors, local lights, local TV state, cloud climate, and thermostat runtime.
- Protocol Mix: BLE 8 / CLOUD 2 / LOCAL 2 / HA 4
- Main Action Types: write x4, get_state x2, read_sensor x2, read_status x2, refresh_cover x2
- Final Schedule: `16` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_morning_wakeup_readiness_profile_01/reassembly/vdev_vdev_morning_wakeup_readiness_profile_01/custom_components/vdev_vdev_morning_wakeup_readiness_profile_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_012 -> batch_013 -> batch_014 -> batch_015. M6 found no counterexamples in the evaluated replay scenarios.

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

### Whole-Family Morning Comfort Snapshot (`vdev_whole_family_morning_comfort_snapshot_01`)

- Story: Before the whole family wakes up, the routine snapshots comfort state across multiple rooms, including BLE environment sensors, SwitchBot curtains, local lighting systems, Tuya climate or lights, and Netatmo runtime.
- Protocol Mix: BLE 6 / CLOUD 4 / LOCAL 3 / HA 4
- Main Action Types: read_sensor x4, write x4, get_state x3, status x3, refresh_cover x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:1, hue:2, nanoleaf:1, netatmo:1, ruuvitag_ble:2, switchbot:3, thermobeacon:1, tplink:1, tuya:4` | `vdev_vdev_whole_family_morning_comfort_snapshot_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py; data/repo_snapshot/thermobeacon/sensor.py; data/repo_snapshot/switchbot/cover.py` ... | `` |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_whole_family_morning_comfort_snapshot_01/counterexamples.json`
- Generated Component: `missing`

### School-Day Quiet Start Check (`vdev_school_day_quiet_start_check_01`)

- Story: On school-day mornings, the routine checks hallway, kids-room, and study state to avoid noisy or incorrect wake-up behavior.
- Protocol Mix: BLE 3 / CLOUD 3 / LOCAL 3 / HA 4
- Main Action Types: write x4, get_state x3, read_runtime x2, read_sensor x2, refresh_cover x1
- Final Schedule: `13` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01`

**Schedule Interpretation**

The first 3 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_009 -> batch_010 -> batch_011 -> batch_012. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:2, qingping:1, smartthings:1, switchbot:2, tplink:1, tuya:2, webostv:1, xiaomi_ble:1` | `vdev_vdev_school_day_quiet_start_check_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_school_day_quiet_start_check_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_school_day_quiet_start_check_01/reassembly/vdev_vdev_school_day_quiet_start_check_01/custom_components/vdev_vdev_school_day_quiet_start_check_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Bad-Air Morning Recovery (`vdev_bad_air_morning_recovery_01`)

- Story: When indoor air quality is poor in the morning, the routine checks purifier state, curtains, climate, local ambience lights, and Netatmo environment state before recommending recovery actions.
- Protocol Mix: BLE 4 / CLOUD 3 / LOCAL 2 / HA 4
- Main Action Types: write x4, get_state x2, refresh_cover x2, status x2, read_runtime x1
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `10` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, esphome:1, hue:1, nanoleaf:1, netatmo:1, switchbot:4, tplink:1, tuya:3` | `vdev_vdev_bad_air_morning_recovery_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/switchbot/fan.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/climate.py` ... | `` |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 10 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_bad_air_morning_recovery_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_bad_air_morning_recovery_01/counterexamples.json`
- Generated Component: `missing`

### Leave-Home Safety Sweep Profile Coverage (`vdev_leave_home_safety_sweep_profile_01`)

- Story: After residents leave, the routine checks lights, plugs, curtains, door or window sensors, climate, and entertainment devices to confirm the home is safe and energy efficient.
- Protocol Mix: BLE 7 / CLOUD 7 / LOCAL 6 / HA 4
- Main Action Types: get_state x6, status x6, read_sensor x4, write x4, refresh_cover x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `denonavr:1, ecobee:1, esphome:1, hue:2, roku:1, switchbot:4, tplink:3, tuya:7, xiaomi_ble:4` | `vdev_vdev_leave_home_safety_sweep_profile_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py` ... | `` |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_leave_home_safety_sweep_profile_01/counterexamples.json`
- Generated Component: `missing`

### Arrival Home Preparation Profile Coverage (`vdev_arrival_home_preparation_profile_01`)

- Story: When a family member is near home, the routine checks entry lighting, living-room ambience, climate, curtains, and air-node state before preparing arrival context.
- Protocol Mix: BLE 5 / CLOUD 4 / LOCAL 2 / HA 4
- Main Action Types: write x4, status x3, get_state x2, refresh_cover x2, connect x1
- Final Schedule: `15` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01`

**Schedule Interpretation**

The first 5 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_011 -> batch_012 -> batch_013 -> batch_014. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `13` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:1, nanoleaf:1, smartthings:1, switchbot:3, tplink:1, tuya:4, xiaomi_ble:1` | `vdev_vdev_arrival_home_preparation_profile_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/esphome/__init__.py; data/repo_snapshot/esphome/manager.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 13 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_arrival_home_preparation_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_arrival_home_preparation_profile_01/reassembly/vdev_vdev_arrival_home_preparation_profile_01/custom_components/vdev_vdev_arrival_home_preparation_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Vacation Departure Final Audit (`vdev_vacation_departure_final_audit_01`)

- Story: Before a long trip, the routine performs a final whole-home audit across curtains, door or window sensors, temperature sensors, local lights or plugs, media devices, cloud lights or switches, thermostat, and security state.
- Protocol Mix: BLE 10 / CLOUD 10 / LOCAL 9 / HA 4
- Main Action Types: get_state x9, status x8, read_sensor x6, refresh_cover x4, write x4
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `13` integrations / `16` files | `1` generated custom component |
| Main Source Integrations | `blink:1, denonavr:1, ecobee:1, esphome:1, hue:3, roku:1, ruuvitag_ble:1, sensorpush:1, switchbot:5, tplink:4, tuya:9, webostv:1, xiaomi_ble:4` | `vdev_vdev_vacation_departure_final_audit_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/sensorpush/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 13 integrations and approximately 16 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_vacation_departure_final_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_vacation_departure_final_audit_01/counterexamples.json`
- Generated Component: `missing`

### Come-Home Security and Comfort Merge (`vdev_come_home_security_comfort_merge_01`)

- Story: When residents come home, the routine merges security, lighting, and comfort state into one concise arrival summary.
- Protocol Mix: BLE 2 / CLOUD 4 / LOCAL 4 / HA 4
- Main Action Types: get_state x4, write x4, read_runtime x2, status x2, read_sensor x1
- Final Schedule: `14` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01`

**Schedule Interpretation**

The first 2 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_010 -> batch_011 -> batch_012 -> batch_013. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `blink:1, ecobee:1, esphome:1, hue:3, philips_js:1, switchbot:2, tplink:1, tuya:3, xiaomi_ble:1` | `vdev_vdev_come_home_security_comfort_merge_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/blink/sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_come_home_security_comfort_merge_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_come_home_security_comfort_merge_01/reassembly/vdev_vdev_come_home_security_comfort_merge_01/custom_components/vdev_vdev_come_home_security_comfort_merge_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Bedtime Lockdown Profile Coverage (`vdev_bedtime_lockdown_profile_01`)

- Story: Before sleep, the routine checks bedroom, hallway, living-room, door or window, plug, and climate state before publishing a night lockdown summary.
- Protocol Mix: BLE 7 / CLOUD 5 / LOCAL 3 / HA 4
- Main Action Types: status x4, write x4, get_state x3, read_sensor x3, read_status x2
- Final Schedule: `19` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01`

**Schedule Interpretation**

The first 7 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_015 -> batch_016 -> batch_017 -> batch_018. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `ecobee:1, esphome:1, hue:1, switchbot:3, tplink:3, tuya:5, xiaomi_ble:5` | `vdev_vdev_bedtime_lockdown_profile_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/device.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/tuya/light.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_bedtime_lockdown_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_bedtime_lockdown_profile_01/reassembly/vdev_vdev_bedtime_lockdown_profile_01/custom_components/vdev_vdev_bedtime_lockdown_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Kids' Room Night Safety Check (`vdev_kids_room_night_safety_check_01`)

- Story: Before sleep, the routine checks a kids-room temperature, humidity, lighting, curtain, AC, and window state.
- Protocol Mix: BLE 4 / CLOUD 3 / LOCAL 1 / HA 4
- Main Action Types: write x4, read_sensor x3, status x2, get_state x1, read_runtime x1
- Final Schedule: `12` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01`

**Schedule Interpretation**

The first 4 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_008 -> batch_009 -> batch_010 -> batch_011. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `esphome:1, hue:1, qingping:1, sensorpush:1, smartthings:1, switchbot:2, tplink:1, tuya:3, xiaomi_ble:1` | `vdev_vdev_kids_room_night_safety_check_01` |
| Main Source Files | `data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/sensorpush/sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_kids_room_night_safety_check_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_kids_room_night_safety_check_01/reassembly/vdev_vdev_kids_room_night_safety_check_01/custom_components/vdev_vdev_kids_room_night_safety_check_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Late-Night Entertainment Shutdown (`vdev_late_night_entertainment_shutdown_01`)

- Story: After watching TV at night, the routine checks whether the living-room entertainment area is fully shut down.
- Protocol Mix: BLE 2 / CLOUD 3 / LOCAL 7 / HA 4
- Main Action Types: get_state x7, write x4, status x3, read_sensor x1, refresh_cover x1
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `12` files | `1` generated custom component |
| Main Source Integrations | `denonavr:1, esphome:1, hue:2, roku:1, switchbot:2, tplink:3, tuya:4, webostv:1, xiaomi_ble:1` | `vdev_vdev_late_night_entertainment_shutdown_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py` ... | `` |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 12 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_late_night_entertainment_shutdown_01/counterexamples.json`
- Generated Component: `missing`

### Overnight Quiet-Hours Snapshot (`vdev_overnight_quiet_hours_snapshot_01`)

- Story: At a fixed overnight time, the routine snapshots the family's quiet-hours state across environmental sensors, door or window sensors, Hue groups, thermostats, power strips, and Netatmo environment runtime.
- Protocol Mix: BLE 5 / CLOUD 5 / LOCAL 2 / HA 4
- Main Action Types: read_sensor x5, write x4, read_runtime x3, get_state x2, status x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, ecobee:2, esphome:1, hue:2, netatmo:1, ruuvitag_ble:2, switchbot:1, tplink:1, tuya:3, xiaomi_ble:2` | `vdev_vdev_overnight_quiet_hours_snapshot_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/ruuvitag_ble/sensor.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/ecobee/climate.py` ... | `` |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_overnight_quiet_hours_snapshot_01/counterexamples.json`
- Generated Component: `missing`

### Weekend Whole-Home Snapshot Profile Coverage (`vdev_weekend_whole_home_snapshot_profile_01`)

- Story: On a weekend, the routine builds a whole-home snapshot of lights, curtains, temperature, energy, air quality, local media, and climate state.
- Protocol Mix: BLE 8 / CLOUD 9 / LOCAL 7 / HA 4
- Main Action Types: status x8, get_state x7, write x4, read_sensor x3, refresh_cover x3
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `9` integrations / `15` files | `1` generated custom component |
| Main Source Integrations | `esphome:3, hue:3, nanoleaf:1, netatmo:1, roku:1, switchbot:4, tplink:3, tuya:9, xiaomi_ble:3` | `vdev_vdev_weekend_whole_home_snapshot_profile_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/sensor.py; data/repo_snapshot/esphome/__init__.py; data/repo_snapshot/esphome/manager.py` ... | `` |

**Refactor Characteristics**

- The source spans 9 integrations and approximately 15 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_weekend_whole_home_snapshot_profile_01/counterexamples.json`
- Generated Component: `missing`

### Whole-Home Energy and HVAC Audit Profile Coverage (`vdev_whole_home_energy_hvac_audit_profile_01`)

- Story: At a fixed time, the routine audits lights, plug strips, climates, thermostats, local plugs, and local entertainment devices for energy and HVAC state.
- Protocol Mix: CLOUD 13 / LOCAL 5 / HA 3
- Main Action Types: status x10, get_state x5, read_runtime x3, write x3
- Final Schedule: `21` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01`

**Schedule Interpretation**

Writeback follows lane updates and then the overall update: batch_018 -> batch_019 -> batch_020. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `7` integrations / `10` files | `1` generated custom component |
| Main Source Integrations | `denonavr:1, ecobee:2, esphome:1, smartthings:1, tplink:4, tuya:11, webostv:1` | `vdev_vdev_whole_home_energy_hvac_audit_profile_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 7 integrations and approximately 10 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_whole_home_energy_hvac_audit_profile_01/reassembly/vdev_vdev_whole_home_energy_hvac_audit_profile_01/custom_components/vdev_vdev_whole_home_energy_hvac_audit_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Indoor Air and Climate Audit (`vdev_indoor_air_climate_audit_01`)

- Story: The routine audits air quality and climate state across BLE environmental sensors, local ambience lights, Tuya climates, Ecobee thermostats, and Netatmo station runtime.
- Protocol Mix: BLE 5 / CLOUD 6 / LOCAL 1 / HA 4
- Main Action Types: read_sensor x5, write x4, read_runtime x3, status x3, get_state x1
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `10` integrations / `11` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, ecobee:2, esphome:1, nanoleaf:1, netatmo:1, qingping:2, sensorpush:2, switchbot:1, tplink:1, tuya:4` | `vdev_vdev_indoor_air_climate_audit_01` |
| Main Source Files | `data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/sensorpush/sensor.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/tuya/climate.py` ... | `` |

**Refactor Characteristics**

- The source spans 10 integrations and approximately 11 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_indoor_air_climate_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_indoor_air_climate_audit_01/counterexamples.json`
- Generated Component: `missing`

### Security and Presence Fabric Snapshot (`vdev_security_presence_fabric_snapshot_01`)

- Story: At a fixed time, the routine checks whole-home presence, doors, motion, curtains, security platform state, and essential lights.
- Protocol Mix: BLE 8 / CLOUD 4 / LOCAL 1 / HA 4
- Main Action Types: read_sensor x6, write x4, read_runtime x2, refresh_cover x2, status x2
- Final Schedule: `17` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01`

**Schedule Interpretation**

The first 8 BLE actions run serially to avoid shared-radio conflicts. Writeback follows lane updates and then the overall update: batch_013 -> batch_014 -> batch_015 -> batch_016. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `8` integrations / `10` files | `1` generated custom component |
| Main Source Integrations | `blink:1, esphome:1, hue:1, smartthings:1, switchbot:3, tplink:1, tuya:3, xiaomi_ble:6` | `vdev_vdev_security_presence_fabric_snapshot_01` |
| Main Source Files | `data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/blink/sensor.py; data/repo_snapshot/smartthings/entity.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 8 integrations and approximately 10 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_security_presence_fabric_snapshot_01/reassembly/vdev_vdev_security_presence_fabric_snapshot_01/custom_components/vdev_vdev_security_presence_fabric_snapshot_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`

### Party Preparation Full Sweep (`vdev_party_preparation_full_sweep_01`)

- Story: Before a party, the routine checks living-room and dining-room lighting, curtains, climate, entertainment devices, and air quality.
- Protocol Mix: BLE 4 / CLOUD 6 / LOCAL 8 / HA 4
- Main Action Types: get_state x8, status x6, write x4, read_sensor x2, refresh_cover x2
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `11` integrations / `15` files | `1` generated custom component |
| Main Source Integrations | `airthings_ble:1, denonavr:1, esphome:1, hue:4, nanoleaf:1, roku:1, switchbot:3, tplink:1, tuya:7, webostv:1, xiaomi_ble:1` | `vdev_vdev_party_preparation_full_sweep_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/airthings_ble/sensor.py; data/repo_snapshot/tuya/light.py` ... | `` |

**Refactor Characteristics**

- The source spans 11 integrations and approximately 15 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_party_preparation_full_sweep_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_party_preparation_full_sweep_01/counterexamples.json`
- Generated Component: `missing`

### Holiday Vacation Mode Full Audit (`vdev_holiday_vacation_mode_full_audit_01`)

- Story: Before a holiday trip, the routine performs the largest whole-home audit across curtains, doors, windows, environmental sensors, ESPHome transport, local lights, plugs, TVs, and cloud HVAC or security systems.
- Protocol Mix: BLE 14 / CLOUD 12 / LOCAL 8 / HA 4
- Main Action Types: status x10, get_state x8, read_sensor x8, refresh_cover x4, write x4
- Final Schedule: `-` batches, max `0` parallel groups in one batch
- M6 Evidence: strict `-`, tolerant `-`, counterexamples `-`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01`
- M7 Component Dir: `missing`

**Schedule Interpretation**

No execution batches are available.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `12` integrations / `18` files | `1` generated custom component |
| Main Source Integrations | `blink:1, ecobee:1, esphome:3, hue:3, qingping:1, roku:1, sensorpush:2, switchbot:5, tplink:4, tuya:11, webostv:1, xiaomi_ble:5` | `vdev_vdev_holiday_vacation_mode_full_audit_01` |
| Main Source Files | `data/repo_snapshot/switchbot/cover.py; data/repo_snapshot/xiaomi_ble/binary_sensor.py; data/repo_snapshot/qingping/sensor.py; data/repo_snapshot/sensorpush/sensor.py` ... | `` |

**Refactor Characteristics**

- The source spans 12 integrations and approximately 18 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_holiday_vacation_mode_full_audit_01/counterexamples.json`
- Generated Component: `missing`

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

### Cloud Burst Living Conditions Snapshot Profile Coverage (`vdev_cloud_burst_living_conditions_snapshot_profile_01`)

- Story: During a weather change or scheduled snapshot, the routine performs a burst read over whole-home lights, plug strips, climates, thermostats, Netatmo runtime, SmartThings aggregation, and a small local plug lane.
- Protocol Mix: CLOUD 17 / LOCAL 2 / HA 3
- Main Action Types: status x13, read_runtime x4, write x3, get_state x2
- Final Schedule: `22` batches, max `1` parallel groups in one batch
- M6 Evidence: strict `6`, tolerant `6`, counterexamples `0`
- Run Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01`
- M7 Component Dir: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01`

**Schedule Interpretation**

Writeback follows lane updates and then the overall update: batch_019 -> batch_020 -> batch_021. M6 found no counterexamples in the evaluated replay scenarios.

**Ground-Truth vs Generated Code**

| Dimension | Ground-Truth | Generated vDev |
| --- | --- | --- |
| Source Shape | `6` integrations / `9` files | `1` generated custom component |
| Main Source Integrations | `ecobee:2, esphome:1, netatmo:1, smartthings:1, tplink:3, tuya:14` | `vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01` |
| Main Source Files | `data/repo_snapshot/tuya/light.py; data/repo_snapshot/tuya/switch.py; data/repo_snapshot/tuya/climate.py; data/repo_snapshot/ecobee/climate.py` ... | `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/__init__.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/const.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/entities.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/executor.py; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/manifest.json; data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/plan.json` ... |

**Refactor Characteristics**

- The source spans 6 integrations and approximately 9 files, assembled into one `custom_components/vdev_*` component.
- State reads, coordinator refreshes, and BLE/cloud calls are represented as batches in `plan.json` and dispatched by `executor.py`.
- Batching, session, and fallback policies are recorded explicitly in the generated plan.
- The component contains `__init__.py`, `executor.py`, `plan.json`, `target.json`, and `services.yaml`.

**Key Evidence Files**

- Target: `data/targets/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01.json`
- M5 Plan: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/m5_execution_plan.json`
- M6 Certificate: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/execution_certificate.json`
- Counterexamples: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/counterexamples.json`
- Generated Component: `data/optimizer_runs/vdev_benchmarks/vdev_cloud_burst_living_conditions_snapshot_profile_01/reassembly/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01/custom_components/vdev_vdev_cloud_burst_living_conditions_snapshot_profile_01`

**M6 Proof Summary**

- Strict pass scenarios: `6`
- Tolerant pass scenarios: `6`
- Counterexample count: `0`
