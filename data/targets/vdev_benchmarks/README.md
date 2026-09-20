# vDev Benchmark Suite v2

This suite organizes benchmark cases around realistic household routines instead of abstract transport-only scenarios.

## Groups
- **Morning and Leaving Home Routines**: 5 cases
- **Coming Home and Evening Comfort Routines**: 6 cases
- **Night and Energy Monitoring Routines**: 5 cases
- **Scene Activation and Comfort Control Routines**: 7 cases
- **Household Stress and Abnormality Routines**: 3 cases
- **Weather and Contextual Adjustment Routines**: 2 cases
- **Whole-Home Survey and Audit Routines**: 4 cases
- **Family Care and Room-Level Snapshot Routines**: 4 cases
- **Profile Coverage - Morning Routines**: 4 cases
- **Profile Coverage - Arrival and Departure Routines**: 4 cases
- **Profile Coverage - Evening and Overnight Routines**: 4 cases
- **Profile Coverage - Monitoring and Audit Routines**: 4 cases
- **Profile Coverage - Realistic Stress Routines**: 4 cases

## Case Index

| Case | vdev_id | Group | Source actions | Writebacks |
| --- | --- | --- | ---: | ---: |
| 1. Morning Wake-Up Readiness Routine | `vdev_morning_wakeup_readiness_01` | Morning and Leaving Home Routines | 12 | 4 |
| 2. Leaving Home Safety Check Routine | `vdev_leaving_home_safety_check_01` | Morning and Leaving Home Routines | 12 | 4 |
| 3. Coming Home Comfort Preparation Routine | `vdev_arrival_comfort_preparation_01` | Coming Home and Evening Comfort Routines | 12 | 4 |
| 4. Dinner Time Home Mode Routine | `vdev_dinner_home_mode_01` | Coming Home and Evening Comfort Routines | 12 | 4 |
| 5. Night Shutdown Routine | `vdev_night_shutdown_01` | Night and Energy Monitoring Routines | 13 | 4 |
| 6. Overnight Health & Safety Monitoring Routine | `vdev_overnight_health_safety_monitoring_01` | Night and Energy Monitoring Routines | 12 | 4 |
| 7. Weekend Whole-Home Snapshot Routine | `vdev_weekend_whole_home_snapshot_01` | Night and Energy Monitoring Routines | 19 | 4 |
| 8. Party Preparation Routine | `vdev_party_preparation_01` | Coming Home and Evening Comfort Routines | 13 | 4 |
| 9. Party Scene Activation Routine | `vdev_party_scene_activation_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 10. Movie Night Blackout Routine | `vdev_movie_night_blackout_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 11. Morning Wake-Up Ramp Routine | `vdev_morning_wakeup_ramp_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 12. Workday Focus Mode Routine | `vdev_workday_focus_mode_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 13. Guest Suite Welcome Routine | `vdev_guest_suite_welcome_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 14. Storm Lockdown Safety Routine | `vdev_storm_lockdown_safety_01` | Scene Activation and Comfort Control Routines | 22 | 4 |
| 15. BLE Congestion Routine Stress | `vdev_ble_safety_sweep_stress_01` | Household Stress and Abnormality Routines | 9 | 2 |
| 16. Cloud Burst Energy & HVAC Audit Routine | `vdev_energy_hvac_audit_01` | Household Stress and Abnormality Routines | 10 | 2 |
| 17. Arrive-Home Lighting and Climate Prep | `vdev_arrive_home_lighting_climate_prep_01` | Coming Home and Evening Comfort Routines | 14 | 4 |
| 18. Leave-Home Safety and Energy Sweep | `vdev_leave_home_safety_energy_sweep_01` | Morning and Leaving Home Routines | 16 | 4 |
| 19. Good-Morning Whole-Floor Readiness | `vdev_good_morning_whole_floor_readiness_01` | Morning and Leaving Home Routines | 13 | 4 |
| 20. Bedtime Lockdown Routine | `vdev_bedtime_lockdown_routine_01` | Night and Energy Monitoring Routines | 15 | 4 |
| 21. Rain-Coming Indoor Adjustment | `vdev_rain_coming_indoor_adjustment_01` | Weather and Contextual Adjustment Routines | 10 | 4 |
| 22. Weekend Whole-Home Snapshot Extended | `vdev_weekend_whole_home_snapshot_extended_01` | Whole-Home Survey and Audit Routines | 20 | 4 |
| 23. Dinner Preparation Readiness | `vdev_dinner_preparation_readiness_01` | Coming Home and Evening Comfort Routines | 11 | 4 |
| 24. Party Preparation and Ambience Check | `vdev_party_preparation_ambience_check_01` | Coming Home and Evening Comfort Routines | 14 | 4 |
| 25. Workday Departure Office-Zone Shutdown | `vdev_workday_departure_office_zone_shutdown_01` | Morning and Leaving Home Routines | 8 | 4 |
| 26. Kids' Room Comfort and Safety Snapshot | `vdev_kids_room_comfort_safety_snapshot_01` | Family Care and Room-Level Snapshot Routines | 10 | 4 |
| 27. Elderly Care Daily Check | `vdev_elderly_care_daily_check_01` | Family Care and Room-Level Snapshot Routines | 9 | 4 |
| 28. Laundry and Utility Room Sweep | `vdev_laundry_utility_room_sweep_01` | Family Care and Room-Level Snapshot Routines | 7 | 4 |
| 29. Air Quality Recovery Routine | `vdev_air_quality_recovery_routine_01` | Family Care and Room-Level Snapshot Routines | 9 | 4 |
| 30. Vacation-Mode House Sweep | `vdev_vacation_mode_house_sweep_01` | Whole-Home Survey and Audit Routines | 21 | 4 |
| 31. Homecoming Security and Ambience Merge | `vdev_homecoming_security_ambience_merge_01` | Scene Activation and Comfort Control Routines | 9 | 4 |
| 32. School-Night Quiet Hours Routine | `vdev_school_night_quiet_hours_01` | Night and Energy Monitoring Routines | 11 | 4 |
| 33. Rainy Commute Preparation | `vdev_rainy_commute_preparation_01` | Weather and Contextual Adjustment Routines | 6 | 4 |
| 34. Energy and HVAC Audit Expanded | `vdev_energy_hvac_audit_expanded_01` | Whole-Home Survey and Audit Routines | 12 | 3 |
| 35. Whole-Home BLE Safety Sweep | `vdev_whole_home_ble_safety_sweep_01` | Household Stress and Abnormality Routines | 13 | 2 |
| 36. Cloud Burst Living-Conditions Snapshot | `vdev_cloud_burst_living_conditions_snapshot_01` | Whole-Home Survey and Audit Routines | 12 | 2 |
| 37. Morning Wake-Up Readiness Profile Coverage | `vdev_morning_wakeup_readiness_profile_01` | Profile Coverage - Morning Routines | 12 | 4 |
| 38. Whole-Family Morning Comfort Snapshot | `vdev_whole_family_morning_comfort_snapshot_01` | Profile Coverage - Morning Routines | 13 | 4 |
| 39. School-Day Quiet Start Check | `vdev_school_day_quiet_start_check_01` | Profile Coverage - Morning Routines | 9 | 4 |
| 40. Bad-Air Morning Recovery | `vdev_bad_air_morning_recovery_01` | Profile Coverage - Morning Routines | 9 | 4 |
| 41. Leave-Home Safety Sweep Profile Coverage | `vdev_leave_home_safety_sweep_profile_01` | Profile Coverage - Arrival and Departure Routines | 20 | 4 |
| 42. Arrival Home Preparation Profile Coverage | `vdev_arrival_home_preparation_profile_01` | Profile Coverage - Arrival and Departure Routines | 11 | 4 |
| 43. Vacation Departure Final Audit | `vdev_vacation_departure_final_audit_01` | Profile Coverage - Arrival and Departure Routines | 29 | 4 |
| 44. Come-Home Security and Comfort Merge | `vdev_come_home_security_comfort_merge_01` | Profile Coverage - Arrival and Departure Routines | 10 | 4 |
| 45. Bedtime Lockdown Profile Coverage | `vdev_bedtime_lockdown_profile_01` | Profile Coverage - Evening and Overnight Routines | 15 | 4 |
| 46. Kids' Room Night Safety Check | `vdev_kids_room_night_safety_check_01` | Profile Coverage - Evening and Overnight Routines | 8 | 4 |
| 47. Late-Night Entertainment Shutdown | `vdev_late_night_entertainment_shutdown_01` | Profile Coverage - Evening and Overnight Routines | 12 | 4 |
| 48. Overnight Quiet-Hours Snapshot | `vdev_overnight_quiet_hours_snapshot_01` | Profile Coverage - Evening and Overnight Routines | 12 | 4 |
| 49. Weekend Whole-Home Snapshot Profile Coverage | `vdev_weekend_whole_home_snapshot_profile_01` | Profile Coverage - Monitoring and Audit Routines | 24 | 4 |
| 50. Whole-Home Energy and HVAC Audit Profile Coverage | `vdev_whole_home_energy_hvac_audit_profile_01` | Profile Coverage - Monitoring and Audit Routines | 18 | 3 |
| 51. Indoor Air and Climate Audit | `vdev_indoor_air_climate_audit_01` | Profile Coverage - Monitoring and Audit Routines | 12 | 4 |
| 52. Security and Presence Fabric Snapshot | `vdev_security_presence_fabric_snapshot_01` | Profile Coverage - Monitoring and Audit Routines | 13 | 4 |
| 53. Party Preparation Full Sweep | `vdev_party_preparation_full_sweep_01` | Profile Coverage - Realistic Stress Routines | 18 | 4 |
| 54. Holiday Vacation Mode Full Audit | `vdev_holiday_vacation_mode_full_audit_01` | Profile Coverage - Realistic Stress Routines | 34 | 4 |
| 55. BLE Safety Sweep Routine | `vdev_ble_safety_sweep_routine_01` | Profile Coverage - Realistic Stress Routines | 15 | 2 |
| 56. Cloud Burst Living Conditions Snapshot Profile Coverage | `vdev_cloud_burst_living_conditions_snapshot_profile_01` | Profile Coverage - Realistic Stress Routines | 19 | 3 |

## Case 1. Morning Wake-Up Readiness Routine

- `vdev_id`: `vdev_morning_wakeup_readiness_01`
- Group: Morning and Leaving Home Routines
- Scenario: Before residents wake up, the system collects bedroom and hallway readiness signals to decide whether the home is already in a comfortable morning state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_bedroom_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_bedroom_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:bedside_lamp_left` -> `read_status` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:bedside_lamp_right` -> `read_status` (`device`)
  - `A5`: `ble:xiaomi_ble:temp_humidity_sensor_bedroom` -> `read_sensor` (`sensor`)
  - `A6`: `ble:esphome:air_node_bedroom` -> `connect` (`esphome`)
  - `A7`: `ble:esphome:relay_node_bedroom` -> `subscribe` (`manager`)
- Cloud lane:
  - `A8`: `tuya:climate.master_bedroom.status` -> `status` (`climate`)
  - `A9`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A10`: `tuya:light.living_room.status` -> `status` (`light`)
- Local lane:
  - `A11`: `hue:bridge_1:bedroom_ceiling_group` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:hallway_motion_sensor` -> `get_state` (`sensor`)
- Writeback:
  - `A13`: `sensor.vdev_morning_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_morning_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_morning_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_morning_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Three real lanes: BLE, cloud, and local Hue bridge reads.
- Contains BLE connect plus subscribe, not only status reads.
- Final aggregation is naturally lane-first, then overall.

### Main Optimization Focus
- BLE connect-before-subscribe
- BLE curtain refresh vs sensor/status gap control
- Cloud status batching
- Local API lane should stay cheap and independent
- Overall writeback should depend on lane-level publishes only

## Case 2. Leaving Home Safety Check Routine

- `vdev_id`: `vdev_leaving_home_safety_check_01`
- Group: Morning and Leaving Home Routines
- Scenario: Before residents leave, the routine checks curtains, key lights, energy strips, climate, and entry sensors, then writes one leave-home safety summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_study` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:door_sensor_entry` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:window_sensor_bedroom` -> `read_sensor` (`event`)
  - `A5`: `ble:xiaomi_ble:bedside_lamp_bedroom` -> `read_status` (`device`)
- Cloud lane:
  - `A6`: `tuya:light.living_room_1.status` -> `status` (`light`)
  - `A7`: `tuya:light.living_room_2.status` -> `status` (`light`)
  - `A8`: `tuya:climate.master_bedroom.status` -> `status` (`climate`)
  - `A9`: `tuya:switch.energy_strip_tv.status` -> `status` (`switch`)
  - `A10`: `tuya:switch.energy_strip_desk.status` -> `status` (`switch`)
- Local lane:
  - `A11`: `tplink:plug.coffee_machine` -> `get_state` (`switch`)
  - `A12`: `hue:bridge_1:dining_room_group` -> `get_state` (`light`)
- Writeback:
  - `A13`: `sensor.vdev_leave_home_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_leave_home_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_leave_home_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_leave_home_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Realistic safety checklist rather than an abstract transport test.
- Heavy Tuya status burst plus a smaller BLE sweep and local confirmation.
- Natural whole-home overall summary target.

### Main Optimization Focus
- Cloud burst batching
- BLE refresh and read ordering
- Local API should not be slowed by cloud or BLE noise
- Overall writeback should preserve a short hard-edge backbone

## Case 3. Coming Home Comfort Preparation Routine

- `vdev_id`: `vdev_arrival_comfort_preparation_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before arrival, the routine prepares a comfort snapshot by combining BLE sensors and curtains, cloud HVAC and lights, a Hue bridge read, and one MQTT air-quality read.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:motion_sensor_entry` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_living_room` -> `read_sensor` (`sensor`)
  - `A3`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:curtain_dining_room` -> `refresh_cover` (`cover`)
  - `A5`: `ble:esphome:air_node_living_room` -> `connect` (`esphome`)
  - `A6`: `ble:esphome:relay_node_living_room` -> `subscribe` (`manager`)
- Cloud lane:
  - `A7`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A8`: `tuya:light.living_room.status` -> `status` (`light`)
  - `A9`: `tuya:climate.living_room.status` -> `status` (`climate`)
  - `A10`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A11`: `hue:bridge_1:living_room_group` -> `get_state` (`light`)
  - `A12`: `mqtt:air_quality_node_living_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A13`: `sensor.vdev_arrival_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_arrival_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_arrival_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_arrival_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Natural arrival routine with cross-transport coordination.
- BLE and cloud both contain meaningful work, not padding.
- MQTT introduces a cheap local monitoring source inside a mixed case.

### Main Optimization Focus
- BLE connect-before-subscribe
- BLE refresh vs sensor reads
- Cloud batching across status calls
- MQTT and Hue local reads should remain cheap
- Lane-level publish and overall aggregation order

## Case 4. Dinner Time Home Mode Routine

- `vdev_id`: `vdev_dinner_home_mode_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before dinner, the routine checks dining, kitchen, and living-room readiness across curtains, lights, HVAC, and energy sensors to decide whether the home is ready for dinner mode.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_dining_room` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:temp_sensor_dining_room` -> `read_sensor` (`sensor`)
  - `A4`: `ble:xiaomi_ble:motion_sensor_kitchen_entry` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A5`: `tuya:light.dining_room_main.status` -> `status` (`light`)
  - `A6`: `tuya:light.kitchen_ceiling.status` -> `status` (`light`)
  - `A7`: `tuya:light.living_room_corner.status` -> `status` (`light`)
  - `A8`: `tuya:climate.dining_room.status` -> `status` (`climate`)
  - `A9`: `tuya:switch.energy_strip_kitchen.status` -> `status` (`switch`)
- Local lane:
  - `A10`: `hue:bridge_1:dining_room_group` -> `get_state` (`light`)
  - `A11`: `tplink:plug.rice_cooker` -> `get_state` (`switch`)
  - `A12`: `mqtt:power_meter_kitchen` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A13`: `sensor.vdev_dinner_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_dinner_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_dinner_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_dinner_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Heavy multi-light cloud lane plus local API and MQTT reads.
- BLE lane remains meaningful with both curtain and sensor state.
- Very natural room-based evening routine.

### Main Optimization Focus
- Cloud multi-light batching
- Local API plus MQTT should remain a cheap lane
- BLE curtain refresh ordering
- Short lane publish to overall publish hard-edge chain

## Case 5. Night Shutdown Routine

- `vdev_id`: `vdev_night_shutdown_01`
- Group: Night and Energy Monitoring Routines
- Scenario: Before sleep, the routine confirms curtains, bedside lights, selected energy plugs, climate, and safety sensors, then writes a night shutdown summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_bedroom_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_bedroom_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:bedside_lamp_left` -> `read_status` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:bedside_lamp_right` -> `read_status` (`device`)
  - `A5`: `ble:xiaomi_ble:window_sensor_bedroom` -> `read_sensor` (`event`)
  - `A6`: `ble:xiaomi_ble:door_sensor_balcony` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A7`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A8`: `tuya:light.living_room.status` -> `status` (`light`)
  - `A9`: `tuya:switch.energy_strip_tv.status` -> `status` (`switch`)
  - `A10`: `tuya:switch.energy_strip_desk.status` -> `status` (`switch`)
  - `A11`: `tuya:climate.bedroom.status` -> `status` (`climate`)
- Local lane:
  - `A12`: `tplink:plug.bedside_heater` -> `get_state` (`switch`)
  - `A13`: `hue:bridge_1:hallway_group` -> `get_state` (`light`)
- Writeback:
  - `A14`: `sensor.vdev_night_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_night_cloud_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_night_local_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_night_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Dense but realistic night routine with enough BLE and cloud work.
- Strong overall writeback semantics from three lanes.
- Energy and climate both present, not only lighting.

### Main Optimization Focus
- Large mixed BLE and cloud status collection
- Cloud grouping across lights and plugs
- Local cheap checks should stay separate
- Final overall summary should remain short and explainable

## Case 6. Overnight Health & Safety Monitoring Routine

- `vdev_id`: `vdev_overnight_health_safety_monitoring_01`
- Group: Night and Energy Monitoring Routines
- Scenario: During the night, the routine snapshots temperature, door and window safety, air quality, power usage, and remote HVAC state into one overnight monitoring summary.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:temp_sensor_bedroom` -> `read_sensor` (`sensor`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_baby_room` -> `read_sensor` (`sensor`)
  - `A3`: `ble:xiaomi_ble:door_sensor_entry` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:window_sensor_study` -> `read_sensor` (`event`)
- Cloud lane:
  - `A5`: `tuya:climate.bedroom.status` -> `status` (`climate`)
  - `A6`: `tuya:climate.baby_room.status` -> `status` (`climate`)
  - `A7`: `tuya:switch.energy_strip_server.status` -> `status` (`switch`)
  - `A8`: `tuya:switch.energy_strip_bedroom.status` -> `status` (`switch`)
  - `A9`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
  - `A10`: `ecobee:thermostat.home_2` -> `read_runtime` (`sensor`)
- Local lane:
  - `A11`: `mqtt:air_quality_node_bedroom` -> `read_last_message` (`mqtt`)
  - `A12`: `mqtt:air_quality_node_baby_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A13`: `sensor.vdev_overnight_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_overnight_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_overnight_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_overnight_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Monitoring-first routine, not control-heavy.
- Strong cloud burst plus cheap MQTT monitoring lane.
- Good benchmark for writeback-heavy aggregation with minimal actuation.

### Main Optimization Focus
- Burst cloud status scheduling
- BLE sensor sweep ordering
- MQTT lane should stay cheap
- Lane writeback and overall aggregation should remain compact

## Case 7. Weekend Whole-Home Snapshot Routine

- `vdev_id`: `vdev_weekend_whole_home_snapshot_01`
- Group: Night and Energy Monitoring Routines
- Scenario: During a weekend whole-home snapshot, the routine checks several curtains, rooms, sensors, climate endpoints, lights, plugs, and a few local monitoring sources to generate one house-wide summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_bedroom` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_study` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_living_room` -> `read_sensor` (`sensor`)
  - `A5`: `ble:xiaomi_ble:temp_sensor_bedroom` -> `read_sensor` (`sensor`)
  - `A6`: `ble:xiaomi_ble:motion_sensor_hallway` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:esphome:air_node_1` -> `connect` (`esphome`)
  - `A8`: `ble:esphome:relay_node_1` -> `subscribe` (`manager`)
- Cloud lane:
  - `A9`: `tuya:light.living_room_1.status` -> `status` (`light`)
  - `A10`: `tuya:light.living_room_2.status` -> `status` (`light`)
  - `A11`: `tuya:light.bedroom_1.status` -> `status` (`light`)
  - `A12`: `tuya:climate.living_room.status` -> `status` (`climate`)
  - `A13`: `tuya:climate.bedroom.status` -> `status` (`climate`)
  - `A14`: `tuya:switch.energy_strip_tv.status` -> `status` (`switch`)
  - `A15`: `tuya:switch.energy_strip_study.status` -> `status` (`switch`)
- Local lane:
  - `A16`: `hue:bridge_1:living_room_group` -> `get_state` (`light`)
  - `A17`: `hue:bridge_1:bedroom_group` -> `get_state` (`light`)
  - `A18`: `tplink:plug.coffee_machine` -> `get_state` (`switch`)
  - `A19`: `mqtt:power_meter_home_main` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A20`: `sensor.vdev_weekend_ble_lane` -> `publish` (`sensor`)
  - `A21`: `sensor.vdev_weekend_cloud_lane` -> `publish` (`sensor`)
  - `A22`: `sensor.vdev_weekend_local_lane` -> `publish` (`sensor`)
  - `A23`: `sensor.vdev_weekend_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Largest everyday mixed benchmark in the suite.
- Good single 'main benchmark' candidate because it is realistic and large.
- Exercises all three source lanes plus layered writeback.

### Main Optimization Focus
- BLE congestion with connect-plus-subscribe
- Cloud multi-room batching and grouping
- Cheap local lane parallelism
- Minimal overall aggregation chain under a large routine

## Case 8. Party Preparation Routine

- `vdev_id`: `vdev_party_preparation_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before guests arrive, the routine checks party-scene lighting, curtains, climate, speaker power, TV power, and air quality to decide whether the home is ready for a party scene.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_dining_room` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:motion_sensor_entry` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_living_room` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A5`: `tuya:light.living_room_main.status` -> `status` (`light`)
  - `A6`: `tuya:light.dining_room_main.status` -> `status` (`light`)
  - `A7`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A8`: `tuya:climate.living_room.status` -> `status` (`climate`)
  - `A9`: `tuya:switch.energy_strip_speaker.status` -> `status` (`switch`)
  - `A10`: `tuya:switch.energy_strip_tv.status` -> `status` (`switch`)
- Local lane:
  - `A11`: `hue:bridge_1:party_scene_group` -> `get_state` (`light`)
  - `A12`: `tplink:plug.coffee_machine` -> `get_state` (`switch`)
  - `A13`: `mqtt:air_quality_node_living_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A14`: `sensor.vdev_party_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_party_cloud_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_party_local_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_party_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Strong multi-light cloud lane with real local scene-group reads.
- BLE lane still matters for curtains and entry state.
- Balanced case for cloud, local, and overall publish structure.

### Main Optimization Focus
- Cloud batching under a dense lighting routine
- Local scene and plug reads should remain cheap
- BLE curtain refresh should stay ordered but not over-serialized
- Final party-readiness summary should keep a short dependency chain

## Case 9. Party Scene Activation Routine

- `vdev_id`: `vdev_party_scene_activation_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: Before guests arrive, the routine actively stages a party scene by repositioning curtains, setting multiple Tuya lights to party brightness and color temperature, adjusting comfort controls, then verifying key scene state before publishing summaries.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room_left` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_room_right` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:curtain_dining_room` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:roller_shade_balcony` -> `set_cover_position` (`cover`)
  - `A5`: `ble:xiaomi_ble:motion_sensor_entry` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:xiaomi_ble:temp_sensor_dining_room` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A7`: `tuya:light.living_room_main.turn_on` -> `turn_on` (`light`)
  - `A8`: `tuya:light.dining_room_main.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:light.hallway.turn_on` -> `turn_on` (`light`)
  - `A10`: `tuya:light.kitchen_ceiling.turn_on` -> `turn_on` (`light`)
  - `A11`: `tuya:climate.living_room.set_temperature` -> `set_temperature` (`climate`)
  - `A12`: `tuya:climate.living_room.set_fan_mode` -> `set_fan_mode` (`climate`)
  - `A13`: `tuya:fan.living_room_ceiling.set_percentage` -> `set_percentage` (`fan`)
  - `A14`: `tuya:light.living_room_main.status` -> `status` (`light`)
  - `A15`: `tuya:light.dining_room_main.status` -> `status` (`light`)
  - `A16`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A17`: `tuya:light.kitchen_ceiling.status` -> `status` (`light`)
  - `A18`: `tuya:climate.living_room.status` -> `status` (`climate`)
  - `A19`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:party_scene_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.speaker_power` -> `get_state` (`switch`)
  - `A22`: `mqtt:air_quality_node_living_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_party_scene_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_party_scene_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_party_scene_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_party_scene_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Control-heavy routine rather than a read-only snapshot.
- Large same-provider Tuya control wave followed by explicit verification reads.
- BLE curtain movement, cloud scene activation, and local readback all coexist in one realistic pre-party flow.

### Main Optimization Focus
- BLE physical-action serialization for multiple curtain moves
- Cloud control batching for same-provider light and climate commands
- Control-to-verify ordering inside the cloud lane
- Local readback should stay cheap while not overtaking scene activation
- Lane summaries should still collapse to a short overall writeback tail

## Case 10. Movie Night Blackout Routine

- `vdev_id`: `vdev_movie_night_blackout_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: Before a movie starts, the routine darkens the viewing area by closing multiple covers, shifting lights into a dim warm scene, adjusting climate and fan comfort, then verifying the blackout state before publishing movie-night readiness summaries.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room_left` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_room_right` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:roller_shade_study` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:curtain_corridor` -> `set_cover_position` (`cover`)
  - `A5`: `ble:xiaomi_ble:motion_sensor_living_room` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:xiaomi_ble:door_sensor_balcony` -> `read_sensor` (`event`)
- Cloud lane:
  - `A7`: `tuya:light.living_room_main.turn_on` -> `turn_on` (`light`)
  - `A8`: `tuya:light.tv_backlight.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:light.hallway.turn_on` -> `turn_on` (`light`)
  - `A10`: `tuya:light.kitchen_ceiling.turn_off` -> `turn_off` (`light`)
  - `A11`: `tuya:climate.living_room.set_hvac_mode` -> `set_hvac_mode` (`climate`)
  - `A12`: `tuya:climate.living_room.set_temperature` -> `set_temperature` (`climate`)
  - `A13`: `tuya:fan.living_room_ceiling.set_percentage` -> `set_percentage` (`fan`)
  - `A14`: `tuya:light.living_room_main.status` -> `status` (`light`)
  - `A15`: `tuya:light.tv_backlight.status` -> `status` (`light`)
  - `A16`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A17`: `tuya:light.kitchen_ceiling.status` -> `status` (`light`)
  - `A18`: `tuya:climate.living_room.status` -> `status` (`climate`)
  - `A19`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:theater_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.projector_strip` -> `get_state` (`switch`)
  - `A22`: `mqtt:air_quality_node_living_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_movie_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_movie_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_movie_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_movie_overall` -> `publish` (`sensor`)

### Why It Is Useful
- High-action-count scene orchestration rather than a read-only audit.
- Explicit control-to-verify structure inside the cloud lane.
- Naturally mixed routine with BLE cover movement, cloud lighting/HVAC control, and local confirmation reads.

### Main Optimization Focus
- Preserve blackout ordering while still batching cloud light controls
- Treat BLE cover movement as the conservative lane and overlap cloud/local where safe
- Keep verification reads after the corresponding scene-control actions
- Avoid over-stretching the writeback tail after a large control wave

## Case 11. Morning Wake-Up Ramp Routine

- `vdev_id`: `vdev_morning_wakeup_ramp_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: At wake-up time, the routine opens multiple covers, ramps key lights to morning brightness and color temperature, nudges HVAC and fan comfort, then verifies representative state before publishing one wake-up summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_master_bedroom_left` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:curtain_master_bedroom_right` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:curtain_living_room` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:roller_shade_kitchen` -> `set_cover_position` (`cover`)
  - `A5`: `ble:xiaomi_ble:temp_humidity_sensor_bedroom` -> `read_sensor` (`sensor`)
  - `A6`: `ble:xiaomi_ble:motion_sensor_hallway` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A7`: `tuya:light.hallway.turn_on` -> `turn_on` (`light`)
  - `A8`: `tuya:light.kitchen_ceiling.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:light.living_room.turn_on` -> `turn_on` (`light`)
  - `A10`: `tuya:light.master_bedroom.turn_on` -> `turn_on` (`light`)
  - `A11`: `tuya:climate.master_bedroom.set_hvac_mode` -> `set_hvac_mode` (`climate`)
  - `A12`: `tuya:climate.master_bedroom.set_temperature` -> `set_temperature` (`climate`)
  - `A13`: `tuya:fan.living_room_ceiling.set_percentage` -> `set_percentage` (`fan`)
  - `A14`: `tuya:light.hallway.status` -> `status` (`light`)
  - `A15`: `tuya:light.kitchen_ceiling.status` -> `status` (`light`)
  - `A16`: `tuya:light.living_room.status` -> `status` (`light`)
  - `A17`: `tuya:light.master_bedroom.status` -> `status` (`light`)
  - `A18`: `tuya:climate.master_bedroom.status` -> `status` (`climate`)
  - `A19`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:kitchen_group` -> `get_state` (`light`)
  - `A21`: `hue:bridge_1:hallway_motion_sensor` -> `get_state` (`sensor`)
  - `A22`: `mqtt:air_quality_node_living_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_wakeup_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_wakeup_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_wakeup_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_wakeup_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Transforms the old morning snapshot pattern into a true control-and-verify automation.
- Large cloud light-control wave with explicit comfort-setting and follow-up readback.
- Still realistic for a household with multiple curtains and staggered room lighting.

### Main Optimization Focus
- Keep BLE curtain movement conservative while compressing the cloud morning ramp
- Batch same-provider light controls before status verification
- Allow local confirmation reads to stay cheap without leapfrogging control intent
- Preserve a short writeback chain after a large mixed-lane morning orchestration

## Case 12. Workday Focus Mode Routine

- `vdev_id`: `vdev_workday_focus_mode_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: At the start of a work block, the routine repositions shades, enables desk airflow and task lighting, applies a focused lighting and climate profile, then verifies representative cloud and local state before publishing one focus-mode summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:roller_shade_office_left` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:roller_shade_office_right` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:roller_shade_study` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:desk_fan` -> `set_percentage` (`fan`)
  - `A5`: `ble:switchbot:task_light` -> `turn_on` (`light`)
  - `A6`: `ble:xiaomi_ble:motion_sensor_office_entry` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:xiaomi_ble:temp_sensor_office` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A8`: `tuya:light.office_main.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:light.office_task.turn_on` -> `turn_on` (`light`)
  - `A10`: `tuya:light.study_bookshelf.turn_on` -> `turn_on` (`light`)
  - `A11`: `tuya:switch.energy_strip_desk.turn_on` -> `turn_on` (`switch`)
  - `A12`: `ecobee:thermostat.office.set_hvac_mode` -> `set_hvac_mode` (`climate`)
  - `A13`: `ecobee:thermostat.office.set_fan_mode` -> `set_fan_mode` (`climate`)
  - `A14`: `ecobee:thermostat.office.set_temperature` -> `set_temperature` (`climate`)
  - `A15`: `tuya:light.office_main.status` -> `status` (`light`)
  - `A16`: `tuya:light.office_task.status` -> `status` (`light`)
  - `A17`: `tuya:light.study_bookshelf.status` -> `status` (`light`)
  - `A18`: `tuya:switch.energy_strip_desk.status` -> `status` (`switch`)
  - `A19`: `ecobee:thermostat.office` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:office_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.monitor_power` -> `get_state` (`switch`)
  - `A22`: `mqtt:desk_air_quality_node` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_workday_focus_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_workday_focus_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_workday_focus_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_workday_focus_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large mixed control routine with meaningful BLE device movement and cloud comfort changes.
- Separates control wave and verification wave, which is closer to a real scene activation than a status snapshot.
- Includes representative local verification without relying on unsupported local-control semantics.

### Main Optimization Focus
- BLE physical-device control serialization across multiple covers and near-desk peripherals
- Cloud control grouping across Tuya lighting and Ecobee comfort actions
- Post-control verification should remain a distinct phase instead of blending into acquisition
- Local verification should stay cheap and grouped behind the verification frontier
- Lane writeback should remain short and deterministic after a larger control routine

## Case 13. Guest Suite Welcome Routine

- `vdev_id`: `vdev_guest_suite_welcome_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: Before guests arrive, the routine opens suite shades, enables airflow and welcome lighting, applies a comfort preset, then verifies representative scene state before publishing a guest-suite readiness summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_guest_suite_left` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:curtain_guest_suite_right` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:roller_shade_guest_suite` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:guest_suite_fan` -> `set_percentage` (`fan`)
  - `A5`: `ble:switchbot:guest_suite_bedside_light` -> `turn_on` (`light`)
  - `A6`: `ble:xiaomi_ble:motion_sensor_guest_entry` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:xiaomi_ble:temp_sensor_guest_suite` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A8`: `tuya:light.guest_suite_main.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:light.guest_suite_bedside.turn_on` -> `turn_on` (`light`)
  - `A10`: `tuya:light.guest_suite_entry.turn_on` -> `turn_on` (`light`)
  - `A11`: `tuya:climate.guest_suite.set_hvac_mode` -> `set_hvac_mode` (`climate`)
  - `A12`: `tuya:climate.guest_suite.set_temperature` -> `set_temperature` (`climate`)
  - `A13`: `ecobee:thermostat.guest_suite.set_fan_mode` -> `set_fan_mode` (`climate`)
  - `A14`: `ecobee:thermostat.guest_suite.set_preset_mode` -> `set_preset_mode` (`climate`)
  - `A15`: `tuya:light.guest_suite_main.status` -> `status` (`light`)
  - `A16`: `tuya:light.guest_suite_bedside.status` -> `status` (`light`)
  - `A17`: `tuya:light.guest_suite_entry.status` -> `status` (`light`)
  - `A18`: `tuya:climate.guest_suite.status` -> `status` (`climate`)
  - `A19`: `ecobee:thermostat.guest_suite` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:guest_suite_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.guest_suite_heater` -> `get_state` (`switch`)
  - `A22`: `mqtt:guest_suite_air_quality_node` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_guest_suite_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_guest_suite_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_guest_suite_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_guest_suite_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Adds another large control-and-verify routine without reusing the exact same device mix as the earlier three control cases.
- Combines Tuya light and climate control with Ecobee comfort control and local welcome-state confirmation.
- Large enough to surface schedule-quality regressions in control sequencing and verification handling.

### Main Optimization Focus
- BLE cover and peripheral control ordering
- Cloud control grouping across welcome lighting and guest comfort settings
- Ecobee post-control verification should stay behind comfort-control actions
- Local verification should stay grouped without overtaking cloud verification
- Writeback tail should remain compact after a high-action-count routine

## Case 14. Storm Lockdown Safety Routine

- `vdev_id`: `vdev_storm_lockdown_safety_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: Before a storm front arrives, the routine closes exposed shades, powers down selected outdoor loads, enables safety lighting and HVAC lockdown settings, then verifies representative state before publishing a whole-home storm-lockdown summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:roller_shade_entry` -> `set_cover_position` (`cover`)
  - `A2`: `ble:switchbot:roller_shade_living_room` -> `set_cover_position` (`cover`)
  - `A3`: `ble:switchbot:roller_shade_study` -> `set_cover_position` (`cover`)
  - `A4`: `ble:switchbot:patio_fan` -> `turn_off` (`fan`)
  - `A5`: `ble:xiaomi_ble:window_sensor_study` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:xiaomi_ble:door_sensor_back_patio` -> `read_sensor` (`event`)
- Cloud lane:
  - `A7`: `tuya:light.entry.turn_on` -> `turn_on` (`light`)
  - `A8`: `tuya:light.porch.turn_on` -> `turn_on` (`light`)
  - `A9`: `tuya:switch.patio_heater.turn_off` -> `turn_off` (`switch`)
  - `A10`: `tuya:switch.fountain_pump.turn_off` -> `turn_off` (`switch`)
  - `A11`: `tuya:siren.entry.turn_on` -> `turn_on` (`siren`)
  - `A12`: `ecobee:thermostat.home_1.set_hvac_mode` -> `set_hvac_mode` (`climate`)
  - `A13`: `ecobee:thermostat.home_1.set_fan_mode` -> `set_fan_mode` (`climate`)
  - `A14`: `ecobee:thermostat.home_1.set_temperature` -> `set_temperature` (`climate`)
  - `A15`: `tuya:light.entry.status` -> `status` (`light`)
  - `A16`: `tuya:light.porch.status` -> `status` (`light`)
  - `A17`: `tuya:switch.patio_heater.status` -> `status` (`switch`)
  - `A18`: `tuya:switch.fountain_pump.status` -> `status` (`switch`)
  - `A19`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A20`: `hue:bridge_1:entry_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.emergency_backup` -> `get_state` (`switch`)
  - `A22`: `mqtt:weather_station_home` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A23`: `sensor.vdev_storm_lockdown_ble_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_storm_lockdown_cloud_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_storm_lockdown_local_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_storm_lockdown_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Control-heavy safety routine with a different device mix from party or wake-up scenes.
- Exercises light, switch, siren-adjacent, and climate control in one flow while still requiring a verification phase.
- Good generalization test because it is safety-oriented rather than ambience-oriented.

### Main Optimization Focus
- BLE cover-control ordering under a larger safety routine
- Cloud control grouping across lights, switches, and HVAC settings
- Verification phase should stay separate from control and preserve readback ordering
- Local verification should remain grouped but should not overtake cloud verification
- Writeback tail should remain compact and predictable under a larger control case

## Case 15. BLE Congestion Routine Stress

- `vdev_id`: `vdev_ble_safety_sweep_stress_01`
- Group: Household Stress and Abnormality Routines
- Scenario: A fast whole-home BLE safety sweep checks curtains, room sensors, and one ESPHome transport pair, acting as a realistic high-contention BLE routine rather than an abstract stress synthetic.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_bedroom` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_study` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_1` -> `read_sensor` (`sensor`)
  - `A5`: `ble:xiaomi_ble:temp_sensor_2` -> `read_sensor` (`sensor`)
  - `A6`: `ble:xiaomi_ble:temp_sensor_3` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:xiaomi_ble:door_sensor_entry` -> `read_sensor` (`event`)
  - `A8`: `ble:esphome:air_node_1` -> `connect` (`esphome`)
  - `A9`: `ble:esphome:relay_node_1` -> `subscribe` (`manager`)
- Writeback:
  - `A10`: `sensor.vdev_ble_safety_sweep_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_ble_safety_sweep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Still clearly a routine, but with maximal BLE contention.
- Contains both repeated reads and transport setup/subscription.
- Good upper-bound test for radio budget and min-gap handling.

### Main Optimization Focus
- BLE overlap budget
- MIN_GAP and NO_OVERLAP behavior
- Connect-before-subscribe under heavy BLE load
- BLE lane writeback should remain minimal and clean

## Case 16. Cloud Burst Energy & HVAC Audit Routine

- `vdev_id`: `vdev_energy_hvac_audit_01`
- Group: Household Stress and Abnormality Routines
- Scenario: At a fixed audit time, the routine gathers multiple Tuya lights, energy strips, climate states, and two Ecobee runtime reads to generate one energy and HVAC audit summary.

### Composition
- Cloud lane:
  - `A1`: `tuya:light.living_room_1.status` -> `status` (`light`)
  - `A2`: `tuya:light.living_room_2.status` -> `status` (`light`)
  - `A3`: `tuya:light.bedroom_1.status` -> `status` (`light`)
  - `A4`: `tuya:switch.energy_strip_1.status` -> `status` (`switch`)
  - `A5`: `tuya:switch.energy_strip_2.status` -> `status` (`switch`)
  - `A6`: `tuya:switch.energy_strip_3.status` -> `status` (`switch`)
  - `A7`: `tuya:climate.master_bedroom.status` -> `status` (`climate`)
  - `A8`: `tuya:climate.guest_room.status` -> `status` (`climate`)
  - `A9`: `ecobee:thermostat.home_1` -> `read_runtime` (`climate`)
  - `A10`: `ecobee:thermostat.home_2` -> `read_runtime` (`sensor`)
- Writeback:
  - `A11`: `sensor.vdev_energy_hvac_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_energy_hvac_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Realistic cloud burst instead of a bare synthetic provider stress case.
- Combines same-provider Tuya batching with cross-provider Ecobee reads.
- Good benchmark for cloud session reuse, batching, and backoff policy.

### Main Optimization Focus
- Tuya batching buckets
- Cross-provider parallelism
- Session reuse and host grouping
- Backoff and shrink-before-disable behavior
- Short overall writeback chain after a large cloud burst

## Case 17. Arrive-Home Lighting and Climate Prep

- `vdev_id`: `vdev_arrive_home_lighting_climate_prep_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before residents get home, the routine checks living-room, hallway, and bedroom lights, curtains, climate, and air quality to decide whether the house is ready to enter a welcome-home state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_room_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:motion_sensor_entry_arrival` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_bedroom_arrival` -> `read_sensor` (`sensor`)
  - `A5`: `ble:esphome:air_node_arrival` -> `connect` (`esphome`)
  - `A6`: `ble:esphome:relay_node_arrival` -> `subscribe` (`manager`)
- Cloud lane:
  - `A7`: `tuya:light.living_room_welcome_1.status` -> `status` (`light`)
  - `A8`: `tuya:light.living_room_welcome_2.status` -> `status` (`light`)
  - `A9`: `tuya:climate.bedroom_arrival.status` -> `status` (`climate`)
  - `A10`: `ecobee:thermostat.arrival_home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A11`: `hue:bridge_1:living_room_main_left` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:living_room_main_center` -> `get_state` (`light`)
  - `A13`: `hue:bridge_1:living_room_main_right` -> `get_state` (`light`)
  - `A14`: `hue:bridge_1:hallway_presence_arrival` -> `get_state` (`sensor`)
- Writeback:
  - `A15`: `sensor.vdev_arrive_home_lighting_climate_prep_ble_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_arrive_home_lighting_climate_prep_cloud_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_arrive_home_lighting_climate_prep_local_lane` -> `publish` (`sensor`)
  - `A18`: `sensor.vdev_arrive_home_lighting_climate_prep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Arrival routine is realistic and still mixed across BLE, cloud, and local lanes.
- Contains BLE connect plus subscribe instead of only stateless reads.
- Both Hue local states and cloud runtime reads contribute to the same welcome-home decision.

### Main Optimization Focus
- BLE connect-before-subscribe under a realistic arrival lane
- Cloud light plus climate batching
- Local Hue and sensor reads should stay cheap
- Lane-first publish followed by one overall welcome-home summary

## Case 18. Leave-Home Safety and Energy Sweep

- `vdev_id`: `vdev_leave_home_safety_energy_sweep_01`
- Group: Morning and Leaving Home Routines
- Scenario: When everyone leaves, the routine checks lights, curtains, plugs, climate, and entry sensors, then publishes one leave-home safety and energy summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_room_departure` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_bedroom_departure` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_study_departure` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:door_sensor_entry_departure` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:xiaomi_ble:window_sensor_kitchen_departure` -> `read_sensor` (`event`)
  - `A6`: `ble:xiaomi_ble:bedside_lamp_departure` -> `read_status` (`device`)
- Cloud lane:
  - `A7`: `tuya:switch.foyer_strip.status` -> `status` (`switch`)
  - `A8`: `tuya:switch.media_strip.status` -> `status` (`switch`)
  - `A9`: `tuya:switch.kitchen_strip.status` -> `status` (`switch`)
  - `A10`: `tuya:climate.master_departure.status` -> `status` (`climate`)
  - `A11`: `tuya:light.entry_departure.status` -> `status` (`light`)
  - `A12`: `tuya:light.hall_departure.status` -> `status` (`light`)
- Local lane:
  - `A13`: `tplink:plug.coffee_station_departure` -> `get_state` (`switch`)
  - `A14`: `tplink:plug.workstation_departure` -> `get_state` (`switch`)
  - `A15`: `hue:bridge_1:dining_group_left_home` -> `get_state` (`light`)
  - `A16`: `hue:bridge_1:dining_group_accent_left_home` -> `get_state` (`light`)
- Writeback:
  - `A17`: `sensor.vdev_leave_home_safety_energy_sweep_ble_lane` -> `publish` (`sensor`)
  - `A18`: `sensor.vdev_leave_home_safety_energy_sweep_cloud_lane` -> `publish` (`sensor`)
  - `A19`: `sensor.vdev_leave_home_safety_energy_sweep_local_lane` -> `publish` (`sensor`)
  - `A20`: `sensor.vdev_leave_home_safety_energy_sweep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Balanced mixed case with heavier cloud burst than the smaller leaving-home benchmark.
- BLE lane includes both curtain refresh and simple safety reads.
- Local TP-Link and Hue reads make the local lane materially useful.

### Main Optimization Focus
- Cloud burst batching across lights, switches, and climate
- BLE refresh versus read ordering under one departure sweep
- Cheap local lane should not be delayed by cloud burst
- Short publish chain from lane summaries to one overall result

## Case 19. Good-Morning Whole-Floor Readiness

- `vdev_id`: `vdev_good_morning_whole_floor_readiness_01`
- Group: Morning and Leaving Home Routines
- Scenario: After wake-up time, the routine collects bedroom, living-room, and dining-room temperatures, lights, curtains, and climate states to decide whether the floor is already in morning mode.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_master_morning` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_morning` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:temp_sensor_master_morning` -> `read_sensor` (`sensor`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_dining_morning` -> `read_sensor` (`sensor`)
  - `A5`: `ble:xiaomi_ble:bedside_lamp_left_morning` -> `read_status` (`binary_sensor`)
  - `A6`: `ble:xiaomi_ble:bedside_lamp_right_morning` -> `read_status` (`device`)
- Cloud lane:
  - `A7`: `tuya:climate.master_floor.status` -> `status` (`climate`)
  - `A8`: `tuya:climate.living_floor.status` -> `status` (`climate`)
  - `A9`: `tuya:light.master_floor.status` -> `status` (`light`)
  - `A10`: `tuya:light.dining_floor.status` -> `status` (`light`)
  - `A11`: `ecobee:thermostat.morning_floor_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A12`: `hue:bridge_1:bedroom_group_morning` -> `get_state` (`light`)
  - `A13`: `hue:bridge_1:hallway_group_morning` -> `get_state` (`light`)
- Writeback:
  - `A14`: `sensor.vdev_good_morning_whole_floor_readiness_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_good_morning_whole_floor_readiness_cloud_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_good_morning_whole_floor_readiness_local_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_good_morning_whole_floor_readiness_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Read-heavy whole-floor routine with no artificial padding.
- BLE lane is long enough to expose ordering and transport budget issues.
- Cloud climate plus light grouping is naturally present.

### Main Optimization Focus
- BLE read-heavy corridor ordering
- Cloud climate and light batching
- Local Hue groups should stay cheap
- Lane publish structure should remain explainable

## Case 20. Bedtime Lockdown Routine

- `vdev_id`: `vdev_bedtime_lockdown_routine_01`
- Group: Night and Energy Monitoring Routines
- Scenario: Before everyone goes to sleep, the routine checks lights, curtains, plugs, climate, and door or window sensors, then publishes a bedtime lockdown summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_master_lockdown` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_living_lockdown` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:window_sensor_master_lockdown` -> `read_sensor` (`event`)
  - `A4`: `ble:xiaomi_ble:window_sensor_guest_lockdown` -> `read_sensor` (`event`)
  - `A5`: `ble:xiaomi_ble:bedside_lamp_left_lockdown` -> `read_status` (`binary_sensor`)
  - `A6`: `ble:xiaomi_ble:bedside_lamp_right_lockdown` -> `read_status` (`device`)
- Cloud lane:
  - `A7`: `tuya:light.bedroom_lockdown.status` -> `status` (`light`)
  - `A8`: `tuya:light.hallway_lockdown.status` -> `status` (`light`)
  - `A9`: `tuya:light.living_lockdown.status` -> `status` (`light`)
  - `A10`: `tuya:switch.tv_lockdown.status` -> `status` (`switch`)
  - `A11`: `tuya:switch.heater_lockdown.status` -> `status` (`switch`)
  - `A12`: `tuya:climate.master_lockdown.status` -> `status` (`climate`)
- Local lane:
  - `A13`: `tplink:plug.bedside_lockdown_left` -> `get_state` (`switch`)
  - `A14`: `tplink:plug.bedside_lockdown_right` -> `get_state` (`switch`)
  - `A15`: `hue:bridge_1:hallway_group_lockdown` -> `get_state` (`light`)
- Writeback:
  - `A16`: `sensor.vdev_bedtime_lockdown_routine_ble_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_bedtime_lockdown_routine_cloud_lane` -> `publish` (`sensor`)
  - `A18`: `sensor.vdev_bedtime_lockdown_routine_local_lane` -> `publish` (`sensor`)
  - `A19`: `sensor.vdev_bedtime_lockdown_routine_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Long aggregation chain with natural room-by-room semantics.
- Mixes cloud lights, switches, and climate in one night routine.
- Local plugs and one Hue group keep the local lane meaningful.

### Main Optimization Focus
- Cloud grouping across lights and switches
- BLE curtain and safety-read ordering
- Local lane should stay inexpensive
- Night summary should preserve a clean writeback tail

## Case 21. Rain-Coming Indoor Adjustment

- `vdev_id`: `vdev_rain_coming_indoor_adjustment_01`
- Group: Weather and Contextual Adjustment Routines
- Scenario: When rain starts, the routine checks window-side curtains, nearby lights, indoor climate, air quality, and one comfort thermostat to publish a rainy-day indoor adjustment suggestion.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_window_left_rain` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_window_right_rain` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:temp_sensor_window_rain` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A4`: `tuya:light.window_accent_left.status` -> `status` (`light`)
  - `A5`: `tuya:light.window_accent_right.status` -> `status` (`light`)
  - `A6`: `tuya:climate.window_room.status` -> `status` (`climate`)
  - `A7`: `ecobee:thermostat.rain_home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A8`: `hue:bridge_1:window_light_left` -> `get_state` (`light`)
  - `A9`: `hue:bridge_1:window_light_right` -> `get_state` (`light`)
  - `A10`: `mqtt:air_quality_node_window_side` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A11`: `sensor.vdev_rain_coming_indoor_adjustment_ble_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_rain_coming_indoor_adjustment_cloud_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_rain_coming_indoor_adjustment_local_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_rain_coming_indoor_adjustment_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Weather trigger is natural but still uses only existing benchmark action families.
- Balanced mixed case with modest BLE, cloud, and local work.
- MQTT air quality keeps the local lane grounded in a real monitoring source.

### Main Optimization Focus
- Cloud light plus climate grouping
- BLE curtain refresh ordering under a short weather corridor
- Local Hue and MQTT reads should stay cheap
- Overall recommendation should depend only on lane summaries

## Case 22. Weekend Whole-Home Snapshot Extended

- `vdev_id`: `vdev_weekend_whole_home_snapshot_extended_01`
- Group: Whole-Home Survey and Audit Routines
- Scenario: On a weekend morning, the routine produces a larger whole-home snapshot of curtains, temperatures, air quality, lights, plugs, and climate to give the household a quick status overview.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_weekend_ext` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_master_weekend_ext` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_study_weekend_ext` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:temp_sensor_living_weekend_ext` -> `read_sensor` (`sensor`)
  - `A5`: `ble:xiaomi_ble:temp_sensor_bedroom_weekend_ext` -> `read_sensor` (`sensor`)
  - `A6`: `ble:xiaomi_ble:temp_sensor_study_weekend_ext` -> `read_sensor` (`sensor`)
  - `A7`: `ble:esphome:air_node_weekend_ext` -> `connect` (`esphome`)
  - `A8`: `ble:esphome:relay_node_weekend_ext` -> `subscribe` (`manager`)
- Cloud lane:
  - `A9`: `tuya:light.living_weekend_ext.status` -> `status` (`light`)
  - `A10`: `tuya:light.hallway_weekend_ext.status` -> `status` (`light`)
  - `A11`: `tuya:light.study_weekend_ext.status` -> `status` (`light`)
  - `A12`: `tuya:climate.master_weekend_ext.status` -> `status` (`climate`)
  - `A13`: `tuya:climate.guest_weekend_ext.status` -> `status` (`climate`)
  - `A14`: `tuya:switch.energy_strip_weekend_ext_1.status` -> `status` (`switch`)
  - `A15`: `tuya:switch.energy_strip_weekend_ext_2.status` -> `status` (`switch`)
- Local lane:
  - `A16`: `hue:bridge_1:living_group_weekend_ext` -> `get_state` (`light`)
  - `A17`: `hue:bridge_1:bedroom_group_weekend_ext` -> `get_state` (`light`)
  - `A18`: `tplink:plug.server_corner_weekend_ext` -> `get_state` (`switch`)
  - `A19`: `tplink:plug.media_corner_weekend_ext` -> `get_state` (`switch`)
  - `A20`: `mqtt:power_meter_whole_home_weekend_ext` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A21`: `sensor.vdev_weekend_whole_home_snapshot_extended_ble_lane` -> `publish` (`sensor`)
  - `A22`: `sensor.vdev_weekend_whole_home_snapshot_extended_cloud_lane` -> `publish` (`sensor`)
  - `A23`: `sensor.vdev_weekend_whole_home_snapshot_extended_local_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_weekend_whole_home_snapshot_extended_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Larger mixed baseline than the original weekend snapshot.
- Contains BLE connect plus subscribe in addition to many read actions.
- Includes local plugs, MQTT power, and multiple cloud buckets in one survey.

### Main Optimization Focus
- Large mixed-lane batching and overlap
- BLE transport setup inside a long read-heavy corridor
- Local lane should stay cheap despite more devices
- Whole-home summary should remain lane-first then overall

## Case 23. Dinner Preparation Readiness

- `vdev_id`: `vdev_dinner_preparation_readiness_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before dinner, the routine checks dining lights, kitchen lights, dining climate, a kitchen plug, curtains, and indoor air quality to decide whether dinner mode is ready.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_dining_prep` -> `refresh_cover` (`cover`)
  - `A2`: `ble:xiaomi_ble:motion_sensor_kitchen_prep` -> `read_sensor` (`binary_sensor`)
  - `A3`: `ble:xiaomi_ble:temp_sensor_dining_prep` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A4`: `tuya:light.dining_main_prep.status` -> `status` (`light`)
  - `A5`: `tuya:light.kitchen_main_prep.status` -> `status` (`light`)
  - `A6`: `tuya:light.kitchen_counter_prep.status` -> `status` (`light`)
  - `A7`: `tuya:climate.dining_prep.status` -> `status` (`climate`)
  - `A8`: `tuya:switch.kitchen_strip_prep.status` -> `status` (`switch`)
- Local lane:
  - `A9`: `hue:bridge_1:dining_group_prep` -> `get_state` (`light`)
  - `A10`: `tplink:plug.rice_cooker_prep` -> `get_state` (`switch`)
  - `A11`: `mqtt:kitchen_power_meter_prep` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A12`: `sensor.vdev_dinner_preparation_readiness_ble_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_dinner_preparation_readiness_cloud_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_dinner_preparation_readiness_local_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_dinner_preparation_readiness_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Natural dinner scenario with modest but meaningful three-lane work.
- Cloud lane has enough lights to exercise batching.
- MQTT power and one plug keep the local lane realistic.

### Main Optimization Focus
- Cloud light burst batching
- BLE read ordering under a shorter evening routine
- Local API plus MQTT should stay cheap
- Writeback chain should remain short and explicit

## Case 24. Party Preparation and Ambience Check

- `vdev_id`: `vdev_party_preparation_ambience_check_01`
- Group: Coming Home and Evening Comfort Routines
- Scenario: Before a gathering, the routine checks room lights, color ambience, curtains, climate, speaker plugs, and purifier state to decide whether the party setup is ready.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_party_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_party_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:air_purifier_party` -> `read_status` (`fan`)
  - `A4`: `ble:xiaomi_ble:motion_sensor_party` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A5`: `tuya:light.party_main_1.status` -> `status` (`light`)
  - `A6`: `tuya:light.party_main_2.status` -> `status` (`light`)
  - `A7`: `tuya:light.party_aux.status` -> `status` (`light`)
  - `A8`: `tuya:switch.party_speakers.status` -> `status` (`switch`)
  - `A9`: `tuya:switch.party_tv.status` -> `status` (`switch`)
  - `A10`: `tuya:climate.party_room.status` -> `status` (`climate`)
- Local lane:
  - `A11`: `hue:bridge_1:party_room_light_1` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:party_room_light_2` -> `get_state` (`light`)
  - `A13`: `hue:bridge_1:party_room_light_3` -> `get_state` (`light`)
  - `A14`: `hue:bridge_1:party_room_light_4` -> `get_state` (`light`)
- Writeback:
  - `A15`: `sensor.vdev_party_preparation_ambience_check_ble_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_party_preparation_ambience_check_cloud_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_party_preparation_ambience_check_local_lane` -> `publish` (`sensor`)
  - `A18`: `sensor.vdev_party_preparation_ambience_check_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Local Hue lane is intentionally larger than many other cases.
- BLE lane is short but semantically meaningful.
- Cloud lane mixes lights, switches, and climate in one ambience routine.

### Main Optimization Focus
- Local API lane should remain cheap even with several lights
- Cloud burst across lights and switches
- Short BLE lane should not dominate overall latency
- Lane summaries should stay clean and easy to reason about

## Case 25. Workday Departure Office-Zone Shutdown

- `vdev_id`: `vdev_workday_departure_office_zone_shutdown_01`
- Group: Morning and Leaving Home Routines
- Scenario: After leaving for work, the routine does one compact office-zone sweep across curtains, desk lights, monitor plugs, printer plug, and study climate.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_study_departure` -> `refresh_cover` (`cover`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_study_departure` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A3`: `tuya:switch.printer_departure.status` -> `status` (`switch`)
  - `A4`: `tuya:climate.study_departure.status` -> `status` (`climate`)
- Local lane:
  - `A5`: `tplink:plug.desk_lamp_departure` -> `get_state` (`switch`)
  - `A6`: `tplink:plug.monitor_departure` -> `get_state` (`switch`)
  - `A7`: `hue:bridge_1:desk_light_left_departure` -> `get_state` (`light`)
  - `A8`: `hue:bridge_1:desk_light_right_departure` -> `get_state` (`light`)
- Writeback:
  - `A9`: `sensor.vdev_workday_departure_office_zone_shutdown_ble_lane` -> `publish` (`sensor`)
  - `A10`: `sensor.vdev_workday_departure_office_zone_shutdown_cloud_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_workday_departure_office_zone_shutdown_local_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_workday_departure_office_zone_shutdown_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Small but realistic mixed routine rather than a synthetic toy.
- Good lower-bound case for the scheduler on short mixed workloads.
- Lets the benchmark suite include a believable office-only zone routine.

### Main Optimization Focus
- Small mixed-case overheads should remain low
- Local API should stay cheap
- Cloud lane should not dominate a compact routine
- Short writeback tail should stay intact

## Case 26. Kids' Room Comfort and Safety Snapshot

- `vdev_id`: `vdev_kids_room_comfort_safety_snapshot_01`
- Group: Family Care and Room-Level Snapshot Routines
- Scenario: Parents trigger a quick children’s-room snapshot covering temperature, lights, curtains, climate, door or window safety, and air quality.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:temp_sensor_kids_left` -> `read_sensor` (`sensor`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_kids_right` -> `read_sensor` (`sensor`)
  - `A3`: `ble:xiaomi_ble:door_sensor_kids_window` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:window_sensor_kids_balcony` -> `read_sensor` (`event`)
  - `A5`: `ble:switchbot:curtain_kids_room` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A6`: `tuya:climate.kids_room.status` -> `status` (`climate`)
  - `A7`: `tuya:light.kids_room.status` -> `status` (`light`)
- Local lane:
  - `A8`: `hue:bridge_1:kids_room_light_left` -> `get_state` (`light`)
  - `A9`: `hue:bridge_1:kids_room_light_right` -> `get_state` (`light`)
  - `A10`: `mqtt:air_quality_node_kids_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A11`: `sensor.vdev_kids_room_comfort_safety_snapshot_ble_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_kids_room_comfort_safety_snapshot_cloud_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_kids_room_comfort_safety_snapshot_local_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_kids_room_comfort_safety_snapshot_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Lightweight room-level case with a very understandable story.
- BLE lane is read-heavy and appropriate for child-room monitoring.
- MQTT keeps local monitoring realistic without making the case synthetic.

### Main Optimization Focus
- BLE read-heavy scheduling
- Cloud and local lanes should remain inexpensive
- Cheap local plus MQTT behavior
- Conservative but short writeback chain

## Case 27. Elderly Care Daily Check

- `vdev_id`: `vdev_elderly_care_daily_check_01`
- Group: Family Care and Room-Level Snapshot Routines
- Scenario: At a fixed time each day, the system checks one elder room’s climate, lighting, temperature, curtain, motion, and air quality state and writes a care-oriented daily summary.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:motion_sensor_elder_room` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_elder_room` -> `read_sensor` (`sensor`)
  - `A3`: `ble:switchbot:curtain_elder_room` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A4`: `ecobee:thermostat.elder_room` -> `read_runtime` (`climate`)
  - `A5`: `tuya:light.elder_room.status` -> `status` (`light`)
  - `A6`: `tuya:switch.elder_room_heater.status` -> `status` (`switch`)
- Local lane:
  - `A7`: `hue:bridge_1:elder_bedside_left` -> `get_state` (`light`)
  - `A8`: `hue:bridge_1:elder_bedside_right` -> `get_state` (`light`)
  - `A9`: `mqtt:air_quality_node_elder_room` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A10`: `sensor.vdev_elderly_care_daily_check_ble_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_elderly_care_daily_check_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_elderly_care_daily_check_local_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_elderly_care_daily_check_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Strong real-world care narrative makes the benchmark easy to interpret.
- Balanced across BLE, cloud, local, and MQTT without being oversized.
- Still uses the current action vocabulary, so it stays compatible with the suite.

### Main Optimization Focus
- BLE sensor plus curtain ordering
- Cloud plus local comfort checks
- Cheap MQTT and local reads should remain cheap
- Conservative daily-summary writeback structure

## Case 28. Laundry and Utility Room Sweep

- `vdev_id`: `vdev_laundry_utility_room_sweep_01`
- Group: Family Care and Room-Level Snapshot Routines
- Scenario: On a utility-room schedule, the system checks washer and dryer plugs, ventilation, light, door sensor, and temperature to produce one laundry-area health summary.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:temp_sensor_utility_room` -> `read_sensor` (`sensor`)
  - `A2`: `ble:xiaomi_ble:door_sensor_utility_room` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A3`: `tuya:switch.utility_vent.status` -> `status` (`switch`)
  - `A4`: `tuya:light.utility_room.status` -> `status` (`light`)
- Local lane:
  - `A5`: `tplink:plug.washer_utility` -> `get_state` (`switch`)
  - `A6`: `tplink:plug.dryer_utility` -> `get_state` (`switch`)
  - `A7`: `mqtt:utility_power_meter` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A8`: `sensor.vdev_laundry_utility_room_sweep_ble_lane` -> `publish` (`sensor`)
  - `A9`: `sensor.vdev_laundry_utility_room_sweep_cloud_lane` -> `publish` (`sensor`)
  - `A10`: `sensor.vdev_laundry_utility_room_sweep_local_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_laundry_utility_room_sweep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Practical room-level monitoring case with one small BLE lane.
- Good fit for local plugs and one MQTT-style utility metric if needed later.
- Compact enough to catch small-schedule overheads.

### Main Optimization Focus
- Small mixed-case scheduling overhead
- Local plug checks should stay cheap
- Cloud vent and utility light should not dominate
- Summary writeback should stay compact

## Case 29. Air Quality Recovery Routine

- `vdev_id`: `vdev_air_quality_recovery_routine_01`
- Group: Family Care and Room-Level Snapshot Routines
- Scenario: After indoor air quality drops, the routine checks purifier state, nearby temperature, climate, switches, lights, and air-quality feeds to decide whether recovery is progressing normally.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:air_purifier_recovery` -> `read_status` (`fan`)
  - `A2`: `ble:xiaomi_ble:temp_sensor_recovery_zone` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A3`: `tuya:climate.recovery_zone.status` -> `status` (`climate`)
  - `A4`: `tuya:switch.recovery_fan.status` -> `status` (`switch`)
  - `A5`: `tuya:switch.recovery_window_actuator.status` -> `status` (`switch`)
- Local lane:
  - `A6`: `hue:bridge_1:recovery_zone_light_left` -> `get_state` (`light`)
  - `A7`: `hue:bridge_1:recovery_zone_light_right` -> `get_state` (`light`)
  - `A8`: `mqtt:air_quality_node_recovery_1` -> `read_last_message` (`mqtt`)
  - `A9`: `mqtt:air_quality_node_recovery_2` -> `read_last_message` (`mqtt`)
- Writeback:
  - `A10`: `sensor.vdev_air_quality_recovery_routine_ble_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_air_quality_recovery_routine_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_air_quality_recovery_routine_local_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_air_quality_recovery_routine_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Good case for local and MQTT lanes being treated as cheap.
- BLE lane is small but semantically strong.
- Cloud lane mixes climate and switches without becoming synthetic.

### Main Optimization Focus
- MQTT and local-lane cheapness
- Cloud climate plus switch grouping
- Short BLE lane should not dominate
- Conservative summary writeback after one recovery sweep

## Case 30. Vacation-Mode House Sweep

- `vdev_id`: `vdev_vacation_mode_house_sweep_01`
- Group: Whole-Home Survey and Audit Routines
- Scenario: Before a longer trip, the routine runs one final whole-home sweep across curtains, sensors, lights, plugs, climate, and thermostat runtime to validate vacation-mode readiness.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_living_vacation` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_master_vacation` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_study_vacation` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:door_sensor_entry_vacation` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:xiaomi_ble:window_sensor_kitchen_vacation` -> `read_sensor` (`event`)
  - `A6`: `ble:xiaomi_ble:window_sensor_bedroom_vacation` -> `read_sensor` (`event`)
  - `A7`: `ble:xiaomi_ble:temp_sensor_living_vacation` -> `read_sensor` (`sensor`)
  - `A8`: `ble:xiaomi_ble:temp_sensor_study_vacation` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A9`: `tuya:light.living_vacation.status` -> `status` (`light`)
  - `A10`: `tuya:light.hallway_vacation.status` -> `status` (`light`)
  - `A11`: `tuya:light.bedroom_vacation.status` -> `status` (`light`)
  - `A12`: `tuya:switch.tv_vacation.status` -> `status` (`switch`)
  - `A13`: `tuya:switch.kitchen_vacation.status` -> `status` (`switch`)
  - `A14`: `tuya:switch.study_vacation.status` -> `status` (`switch`)
  - `A15`: `tuya:climate.master_vacation.status` -> `status` (`climate`)
  - `A16`: `tuya:climate.guest_vacation.status` -> `status` (`climate`)
  - `A17`: `ecobee:thermostat.vacation_home_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A18`: `hue:bridge_1:living_group_vacation` -> `get_state` (`light`)
  - `A19`: `hue:bridge_1:bedroom_group_vacation` -> `get_state` (`light`)
  - `A20`: `tplink:plug.router_backup_vacation` -> `get_state` (`switch`)
  - `A21`: `tplink:plug.media_backup_vacation` -> `get_state` (`switch`)
- Writeback:
  - `A22`: `sensor.vdev_vacation_mode_house_sweep_ble_lane` -> `publish` (`sensor`)
  - `A23`: `sensor.vdev_vacation_mode_house_sweep_cloud_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_vacation_mode_house_sweep_local_lane` -> `publish` (`sensor`)
  - `A25`: `sensor.vdev_vacation_mode_house_sweep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large realistic stress case rather than a synthetic transport-only stress.
- Contains enough devices to expose batching and long-tail issues.
- Still keeps a very understandable household routine story.

### Main Optimization Focus
- Large mixed-lane batching and aggregation
- Long BLE sweep ordering
- Cloud grouping across multiple resource families
- Local groups and plugs should stay cheaper than cloud

## Case 31. Homecoming Security and Ambience Merge

- `vdev_id`: `vdev_homecoming_security_ambience_merge_01`
- Group: Scene Activation and Comfort Control Routines
- Scenario: At arrival time, the routine merges a small security reassurance sweep with lighting and comfort checks to decide whether the home is ready for a safe, pleasant arrival.

### Composition
- BLE lane:
  - `A1`: `ble:xiaomi_ble:motion_sensor_homecoming` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:switchbot:curtain_entry_homecoming` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A3`: `tuya:light.entry_homecoming.status` -> `status` (`light`)
  - `A4`: `tuya:light.hallway_homecoming.status` -> `status` (`light`)
  - `A5`: `tuya:climate.living_homecoming.status` -> `status` (`climate`)
  - `A6`: `ecobee:thermostat.homecoming_1` -> `read_runtime` (`climate`)
- Local lane:
  - `A7`: `hue:bridge_1:entry_light_homecoming` -> `get_state` (`light`)
  - `A8`: `hue:bridge_1:hallway_light_left_homecoming` -> `get_state` (`light`)
  - `A9`: `hue:bridge_1:hallway_light_right_homecoming` -> `get_state` (`light`)
- Writeback:
  - `A10`: `sensor.vdev_homecoming_security_ambience_merge_ble_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_homecoming_security_ambience_merge_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_homecoming_security_ambience_merge_local_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_homecoming_security_ambience_merge_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Good merged arrival scenario rather than a synthetic cross-lane blend.
- Cloud climate and ecobee runtime naturally sit beside entry lighting.
- Smaller mixed case is useful as a medium-complexity benchmark.

### Main Optimization Focus
- Mixed arrival semantics with a short BLE lane
- Cloud comfort checks should batch cleanly
- Hue entry lights should remain cheap
- Overall summary should stay short and explainable

## Case 32. School-Night Quiet Hours Routine

- `vdev_id`: `vdev_school_night_quiet_hours_01`
- Group: Night and Energy Monitoring Routines
- Scenario: At a fixed school-night quiet-hours time, the routine checks curtains, bedside lights, hallway lights, heater plug, window state, and climate to confirm the house is in a quieter night state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_school_night_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_school_night_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:xiaomi_ble:bedside_lamp_school_night_left` -> `read_status` (`binary_sensor`)
  - `A4`: `ble:xiaomi_ble:bedside_lamp_school_night_right` -> `read_status` (`device`)
  - `A5`: `ble:xiaomi_ble:window_sensor_school_night` -> `read_sensor` (`event`)
- Cloud lane:
  - `A6`: `tuya:climate.school_night.status` -> `status` (`climate`)
  - `A7`: `tuya:switch.school_night_heater.status` -> `status` (`switch`)
  - `A8`: `tuya:light.school_night_room.status` -> `status` (`light`)
- Local lane:
  - `A9`: `hue:bridge_1:hallway_school_night_left` -> `get_state` (`light`)
  - `A10`: `hue:bridge_1:hallway_school_night_right` -> `get_state` (`light`)
  - `A11`: `tplink:plug.heater_school_night` -> `get_state` (`switch`)
- Writeback:
  - `A12`: `sensor.vdev_school_night_quiet_hours_ble_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_school_night_quiet_hours_cloud_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_school_night_quiet_hours_local_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_school_night_quiet_hours_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Natural bedtime variant with a slightly different device mix.
- Includes both local lights and one local heater plug.
- Mid-sized case with easy-to-understand semantics.

### Main Optimization Focus
- Mid-sized night routine scheduling
- BLE lamps and curtain ordering
- Cloud and local checks should remain compact
- Conservative writeback tail

## Case 33. Rainy Commute Preparation

- `vdev_id`: `vdev_rainy_commute_preparation_01`
- Group: Weather and Contextual Adjustment Routines
- Scenario: When rain overlaps with the morning commute window, the routine checks entry lights, curtain, door state, and a small comfort set to decide whether rainy-commute preparation is needed.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_entry_commute_rain` -> `refresh_cover` (`cover`)
  - `A2`: `ble:xiaomi_ble:door_sensor_commute_rain` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A3`: `tuya:climate.entry_commute_rain.status` -> `status` (`climate`)
  - `A4`: `tuya:light.entry_commute_rain.status` -> `status` (`light`)
- Local lane:
  - `A5`: `hue:bridge_1:entry_commute_rain_left` -> `get_state` (`light`)
  - `A6`: `hue:bridge_1:entry_commute_rain_right` -> `get_state` (`light`)
- Writeback:
  - `A7`: `sensor.vdev_rainy_commute_preparation_ble_lane` -> `publish` (`sensor`)
  - `A8`: `sensor.vdev_rainy_commute_preparation_cloud_lane` -> `publish` (`sensor`)
  - `A9`: `sensor.vdev_rainy_commute_preparation_local_lane` -> `publish` (`sensor`)
  - `A10`: `sensor.vdev_rainy_commute_preparation_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Small weather-triggered case with a strong story.
- Good for observing scheduler overhead on short mixed routines.
- Uses only current benchmark action families and integrations.

### Main Optimization Focus
- Small mixed-case scheduling overhead
- BLE lane should remain inexpensive
- Cloud and local entry lighting should not over-serialize
- Short overall summary path

## Case 34. Energy and HVAC Audit Expanded

- `vdev_id`: `vdev_energy_hvac_audit_expanded_01`
- Group: Whole-Home Survey and Audit Routines
- Scenario: At a fixed audit time, the routine collects whole-home lights, plugs, climates, thermostats, and two local smart-plug checks to produce one expanded energy and HVAC audit.

### Composition
- Cloud lane:
  - `A1`: `tuya:light.energy_audit_1.status` -> `status` (`light`)
  - `A2`: `tuya:light.energy_audit_2.status` -> `status` (`light`)
  - `A3`: `tuya:light.energy_audit_3.status` -> `status` (`light`)
  - `A4`: `tuya:switch.energy_audit_1.status` -> `status` (`switch`)
  - `A5`: `tuya:switch.energy_audit_2.status` -> `status` (`switch`)
  - `A6`: `tuya:switch.energy_audit_3.status` -> `status` (`switch`)
  - `A7`: `tuya:climate.energy_audit_master.status` -> `status` (`climate`)
  - `A8`: `tuya:climate.energy_audit_guest.status` -> `status` (`climate`)
  - `A9`: `ecobee:thermostat.energy_audit_1` -> `read_runtime` (`climate`)
  - `A10`: `ecobee:thermostat.energy_audit_2` -> `read_runtime` (`climate`)
- Local lane:
  - `A11`: `tplink:plug.energy_audit_local_1` -> `get_state` (`switch`)
  - `A12`: `tplink:plug.energy_audit_local_2` -> `get_state` (`switch`)
- Writeback:
  - `A13`: `sensor.vdev_energy_hvac_audit_expanded_cloud_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_energy_hvac_audit_expanded_local_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_energy_hvac_audit_expanded_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Cloud-heavy case with a little local confirmation mixed in.
- Good benchmark for cross-provider cloud parallelism plus a small local tail.
- Larger than the original cloud audit while staying very realistic.

### Main Optimization Focus
- Tuya bucket grouping across lights, switches, and climates
- Cross-provider Ecobee overlap
- Local plug checks should stay cheap
- Cloud and local writeback chain should remain short

## Case 35. Whole-Home BLE Safety Sweep

- `vdev_id`: `vdev_whole_home_ble_safety_sweep_01`
- Group: Household Stress and Abnormality Routines
- Scenario: At a fixed time, the routine performs one realistic whole-home BLE sweep over curtains, door or window sensors, motion sensors, temperatures, and one ESPHome transport pair.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:curtain_ble_sweep_living` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:curtain_ble_sweep_master` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:curtain_ble_sweep_study` -> `refresh_cover` (`cover`)
  - `A4`: `ble:xiaomi_ble:door_sensor_ble_sweep_entry` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:xiaomi_ble:window_sensor_ble_sweep_kitchen` -> `read_sensor` (`event`)
  - `A6`: `ble:xiaomi_ble:window_sensor_ble_sweep_bedroom` -> `read_sensor` (`event`)
  - `A7`: `ble:xiaomi_ble:door_sensor_ble_sweep_balcony` -> `read_sensor` (`binary_sensor`)
  - `A8`: `ble:xiaomi_ble:motion_sensor_ble_sweep_living` -> `read_sensor` (`binary_sensor`)
  - `A9`: `ble:xiaomi_ble:motion_sensor_ble_sweep_hall` -> `read_sensor` (`binary_sensor`)
  - `A10`: `ble:xiaomi_ble:temp_sensor_ble_sweep_1` -> `read_sensor` (`sensor`)
  - `A11`: `ble:xiaomi_ble:temp_sensor_ble_sweep_2` -> `read_sensor` (`sensor`)
  - `A12`: `ble:esphome:air_node_ble_sweep` -> `connect` (`esphome`)
  - `A13`: `ble:esphome:relay_node_ble_sweep` -> `subscribe` (`manager`)
- Writeback:
  - `A14`: `sensor.vdev_whole_home_ble_safety_sweep_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_whole_home_ble_safety_sweep_overall` -> `publish` (`sensor`)

### Why It Is Useful
- BLE-heavy case is realistic rather than purely synthetic.
- Includes both status-style reads and a connect plus subscribe pair.
- Useful upper-bound case for BLE lane conservatism and future micro refinements.

### Main Optimization Focus
- BLE corridor length and min-gap behavior
- Connect-before-subscribe under a larger BLE sweep
- Avoiding hidden lane inflation from non-BLE work
- Very short writeback tail after a long BLE lane

## Case 36. Cloud Burst Living-Conditions Snapshot

- `vdev_id`: `vdev_cloud_burst_living_conditions_snapshot_01`
- Group: Whole-Home Survey and Audit Routines
- Scenario: At a scheduled mode-change checkpoint, the routine bursts through lighting, switch, and HVAC endpoints to build one cloud-only living-conditions snapshot.

### Composition
- Cloud lane:
  - `A1`: `tuya:light.cloud_snapshot_1.status` -> `status` (`light`)
  - `A2`: `tuya:light.cloud_snapshot_2.status` -> `status` (`light`)
  - `A3`: `tuya:light.cloud_snapshot_3.status` -> `status` (`light`)
  - `A4`: `tuya:light.cloud_snapshot_4.status` -> `status` (`light`)
  - `A5`: `tuya:switch.cloud_snapshot_1.status` -> `status` (`switch`)
  - `A6`: `tuya:switch.cloud_snapshot_2.status` -> `status` (`switch`)
  - `A7`: `tuya:switch.cloud_snapshot_3.status` -> `status` (`switch`)
  - `A8`: `tuya:switch.cloud_snapshot_4.status` -> `status` (`switch`)
  - `A9`: `tuya:climate.cloud_snapshot_1.status` -> `status` (`climate`)
  - `A10`: `tuya:climate.cloud_snapshot_2.status` -> `status` (`climate`)
  - `A11`: `ecobee:thermostat.cloud_snapshot_1` -> `read_runtime` (`climate`)
  - `A12`: `ecobee:thermostat.cloud_snapshot_2` -> `read_runtime` (`climate`)
- Writeback:
  - `A13`: `sensor.vdev_cloud_burst_living_conditions_snapshot_cloud_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_cloud_burst_living_conditions_snapshot_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Pure cloud burst case without synthetic protocol noise.
- Useful for testing same-provider Tuya batching plus Ecobee overlap.
- Small writeback chain keeps the final observable semantics easy to review.

### Main Optimization Focus
- Tuya batching on a larger cloud burst
- Cross-provider cloud parallelism
- Host grouping and session reuse
- Short cloud-lane to overall writeback chain

## Case 37. Morning Wake-Up Readiness Profile Coverage

- `vdev_id`: `vdev_morning_wakeup_readiness_profile_01`
- Group: Profile Coverage - Morning Routines
- Scenario: After residents wake up, the routine quickly checks bedroom and hallway readiness across curtains, bedside lamps, environmental sensors, local lights, local TV state, cloud climate, and thermostat runtime.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:morning_curtain_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:morning_curtain_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:morning_bedside_lamp_left` -> `read_status` (`device`)
  - `A4`: `ble:switchbot:morning_bedside_lamp_right` -> `read_status` (`device`)
  - `A5`: `ble:qingping:bedroom_temp_humidity_left` -> `read_sensor` (`sensor`)
  - `A6`: `ble:sensorpush:bedroom_temp_humidity_right` -> `read_sensor` (`sensor`)
  - `A7`: `ble:switchbot:morning_air_node` -> `connect` (`esphome`)
  - `A8`: `ble:switchbot:morning_relay_node` -> `subscribe` (`manager`)
- Cloud lane:
  - `A9`: `tuya:climate.bedroom_ac.status` -> `status` (`climate`)
  - `A10`: `ecobee:thermostat.master_bedroom` -> `read_runtime` (`climate`)
- Local lane:
  - `A11`: `hue:bridge_1:bedroom_group` -> `get_state` (`light`)
  - `A12`: `philips_js:tv.bedroom` -> `get_state` (`media_player`)
- Writeback:
  - `A13`: `sensor.vdev_morning_wakeup_readiness_profile_01_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_morning_wakeup_readiness_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_morning_wakeup_readiness_profile_01_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_morning_wakeup_readiness_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Long BLE lane with connect-before-subscribe semantics.
- Cloud has two providers while the local lane stays cheap.
- Lane-level publishes and one overall publish mirror the requested aggregation structure.

### Main Optimization Focus
- BLE chain with connect before subscribe
- Cheap local API packing
- Cloud provider separation
- Lane-first writeback semantics

## Case 38. Whole-Family Morning Comfort Snapshot

- `vdev_id`: `vdev_whole_family_morning_comfort_snapshot_01`
- Group: Profile Coverage - Morning Routines
- Scenario: Before the whole family wakes up, the routine snapshots comfort state across multiple rooms, including BLE environment sensors, SwitchBot curtains, local lighting systems, Tuya climate or lights, and Netatmo runtime.

### Composition
- BLE lane:
  - `A1`: `ble:airthings_ble:living_room_air_quality` -> `read_sensor` (`sensor`)
  - `A2`: `ble:ruuvitag_ble:bedroom_environment` -> `read_sensor` (`sensor`)
  - `A3`: `ble:ruuvitag_ble:kids_room_environment` -> `read_sensor` (`sensor`)
  - `A4`: `ble:thermobeacon:hallway_environment` -> `read_sensor` (`sensor`)
  - `A5`: `ble:switchbot:living_room_curtain_left` -> `refresh_cover` (`cover`)
  - `A6`: `ble:switchbot:living_room_curtain_right` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A7`: `tuya:light.living_room_morning_1.status` -> `status` (`light`)
  - `A8`: `tuya:light.living_room_morning_2.status` -> `status` (`light`)
  - `A9`: `tuya:climate.kids_room_ac.status` -> `status` (`climate`)
  - `A10`: `netatmo:station.indoor_environment` -> `read_runtime` (`sensor`)
- Local lane:
  - `A11`: `hue:bridge_1:living_room_group` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:dining_room_group` -> `get_state` (`light`)
  - `A13`: `nanoleaf:panel.family_room` -> `get_state` (`light`)
- Writeback:
  - `A14`: `sensor.vdev_whole_family_morning_comfort_snapshot_01_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_whole_family_morning_comfort_snapshot_01_cloud_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_whole_family_morning_comfort_snapshot_01_local_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_whole_family_morning_comfort_snapshot_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Read-heavy mixed snapshot with no artificial hard action dependency.
- BLE sensor count is high enough to expose radio ordering pressure.
- Cloud and local lanes are naturally separable.

### Main Optimization Focus
- BLE read-heavy ordering
- Cloud/local frontier completeness
- Local Hue and Nanoleaf packing
- Single comfort summary tail

## Case 39. School-Day Quiet Start Check

- `vdev_id`: `vdev_school_day_quiet_start_check_01`
- Group: Profile Coverage - Morning Routines
- Scenario: On school-day mornings, the routine checks hallway, kids-room, and study state to avoid noisy or incorrect wake-up behavior.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:entry_motion_quiet_start` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:qingping:kids_room_temp_humidity` -> `read_sensor` (`sensor`)
  - `A3`: `ble:switchbot:kids_room_curtain` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A4`: `tuya:light.study_quiet_start.status` -> `status` (`light`)
  - `A5`: `smartthings:kids_room_device_snapshot` -> `read_runtime` (`sensor`)
  - `A6`: `ecobee:thermostat.school_day` -> `read_runtime` (`climate`)
- Local lane:
  - `A7`: `hue:bridge_1:hallway_quiet_light_left` -> `get_state` (`light`)
  - `A8`: `hue:bridge_1:hallway_quiet_light_right` -> `get_state` (`light`)
  - `A9`: `webostv:tv.living_room` -> `get_state` (`media_player`)
- Writeback:
  - `A10`: `sensor.vdev_school_day_quiet_start_check_01_ble_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_school_day_quiet_start_check_01_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_school_day_quiet_start_check_01_local_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_school_day_quiet_start_check_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Medium-size realistic mixed case.
- Cross-provider cloud reads can run independently.
- Local media state is present but cheap.

### Main Optimization Focus
- Cross-provider cloud readiness
- BLE plus local lightweight overlap
- No unnecessary hard dependency injection

## Case 40. Bad-Air Morning Recovery

- `vdev_id`: `vdev_bad_air_morning_recovery_01`
- Group: Profile Coverage - Morning Routines
- Scenario: When indoor air quality is poor in the morning, the routine checks purifier state, curtains, climate, local ambience lights, and Netatmo environment state before recommending recovery actions.

### Composition
- BLE lane:
  - `A1`: `ble:airthings_ble:bad_air_morning_sensor` -> `read_sensor` (`sensor`)
  - `A2`: `ble:switchbot:air_purifier_living_room` -> `read_status` (`fan`)
  - `A3`: `ble:switchbot:bad_air_curtain_left` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:bad_air_curtain_right` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A5`: `tuya:climate.living_room_bad_air_ac.status` -> `status` (`climate`)
  - `A6`: `tuya:climate.bedroom_bad_air_ac.status` -> `status` (`climate`)
  - `A7`: `netatmo:station.bad_air_runtime` -> `read_runtime` (`sensor`)
- Local lane:
  - `A8`: `nanoleaf:panel.bad_air_ambience` -> `get_state` (`light`)
  - `A9`: `hue:bridge_1:living_room_bad_air_group` -> `get_state` (`light`)
- Writeback:
  - `A10`: `sensor.vdev_bad_air_morning_recovery_01_ble_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_bad_air_morning_recovery_01_cloud_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_bad_air_morning_recovery_01_local_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_bad_air_morning_recovery_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Natural air-quality recovery scenario.
- BLE status reads mix with curtain refresh.
- Cloud climate endpoints are grouped but still provider separated from Netatmo.

### Main Optimization Focus
- BLE status versus cover refresh ordering
- Cloud climate grouping
- Local Nanoleaf and Hue cheap reads
- Overall recommendation writeback

## Case 41. Leave-Home Safety Sweep Profile Coverage

- `vdev_id`: `vdev_leave_home_safety_sweep_profile_01`
- Group: Profile Coverage - Arrival and Departure Routines
- Scenario: After residents leave, the routine checks lights, plugs, curtains, door or window sensors, climate, and entertainment devices to confirm the home is safe and energy efficient.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:front_door_departure` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:switchbot:side_door_departure` -> `read_sensor` (`binary_sensor`)
  - `A3`: `ble:switchbot:kitchen_window_departure` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:switchbot:bedroom_window_departure` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:switchbot:departure_curtain_living` -> `refresh_cover` (`cover`)
  - `A6`: `ble:switchbot:departure_curtain_bedroom` -> `refresh_cover` (`cover`)
  - `A7`: `ble:switchbot:departure_curtain_study` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A8`: `tuya:light.departure_light_1.status` -> `status` (`light`)
  - `A9`: `tuya:light.departure_light_2.status` -> `status` (`light`)
  - `A10`: `tuya:light.departure_light_3.status` -> `status` (`light`)
  - `A11`: `tuya:switch.departure_strip_1.status` -> `status` (`switch`)
  - `A12`: `tuya:switch.departure_strip_2.status` -> `status` (`switch`)
  - `A13`: `tuya:switch.departure_strip_3.status` -> `status` (`switch`)
  - `A14`: `ecobee:thermostat.departure` -> `read_runtime` (`climate`)
- Local lane:
  - `A15`: `tplink:plug.desk_left_departure` -> `get_state` (`switch`)
  - `A16`: `tplink:plug.desk_right_departure` -> `get_state` (`switch`)
  - `A17`: `hue:bridge_1:living_room_departure_group` -> `get_state` (`light`)
  - `A18`: `hue:bridge_1:dining_departure_group` -> `get_state` (`light`)
  - `A19`: `roku:media_player.family_room` -> `get_state` (`media_player`)
  - `A20`: `denonavr:media_player.main_avr` -> `get_state` (`media_player`)
- Writeback:
  - `A21`: `sensor.vdev_leave_home_safety_sweep_profile_01_ble_lane` -> `publish` (`sensor`)
  - `A22`: `sensor.vdev_leave_home_safety_sweep_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A23`: `sensor.vdev_leave_home_safety_sweep_profile_01_local_lane` -> `publish` (`sensor`)
  - `A24`: `sensor.vdev_leave_home_safety_sweep_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large mixed departure routine with many realistic device families.
- Cloud burst and local media or plug reads are both significant.
- BLE safety sensors and curtains stress the BLE lane without synthetic padding.

### Main Optimization Focus
- Cloud burst grouping
- Cheap local frontier packing
- BLE safety sensor sweep
- Short final safety summary tail

## Case 42. Arrival Home Preparation Profile Coverage

- `vdev_id`: `vdev_arrival_home_preparation_profile_01`
- Group: Profile Coverage - Arrival and Departure Routines
- Scenario: When a family member is near home, the routine checks entry lighting, living-room ambience, climate, curtains, and air-node state before preparing arrival context.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:entry_motion_arrival` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:switchbot:arrival_curtain_left` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:arrival_curtain_right` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:arrival_air_node` -> `connect` (`esphome`)
  - `A5`: `ble:switchbot:arrival_relay_node` -> `subscribe` (`manager`)
- Cloud lane:
  - `A6`: `tuya:light.arrival_living_light_1.status` -> `status` (`light`)
  - `A7`: `tuya:light.arrival_living_light_2.status` -> `status` (`light`)
  - `A8`: `tuya:climate.arrival_living_ac.status` -> `status` (`climate`)
  - `A9`: `smartthings:arrival_scene_devices` -> `read_runtime` (`sensor`)
- Local lane:
  - `A10`: `hue:bridge_1:entry_hall_group` -> `get_state` (`light`)
  - `A11`: `nanoleaf:panel.living_room_arrival` -> `get_state` (`light`)
- Writeback:
  - `A12`: `sensor.vdev_arrival_home_preparation_profile_01_ble_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_arrival_home_preparation_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_arrival_home_preparation_profile_01_local_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_arrival_home_preparation_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Realistic arrival routine with BLE connect-before-subscribe.
- Cloud scene aggregation is separate from local Hue and Nanoleaf reads.
- The final summary can validate lane-first aggregation.

### Main Optimization Focus
- BLE connect-before-subscribe
- Cloud light and climate status grouping
- Local Hue and Nanoleaf packing

## Case 43. Vacation Departure Final Audit

- `vdev_id`: `vdev_vacation_departure_final_audit_01`
- Group: Profile Coverage - Arrival and Departure Routines
- Scenario: Before a long trip, the routine performs a final whole-home audit across curtains, door or window sensors, temperature sensors, local lights or plugs, media devices, cloud lights or switches, thermostat, and security state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:vacation_curtain_living` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:vacation_curtain_bedroom` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:vacation_curtain_study` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:vacation_curtain_guest` -> `refresh_cover` (`cover`)
  - `A5`: `ble:switchbot:vacation_front_door` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:switchbot:vacation_back_door` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:switchbot:vacation_kitchen_window` -> `read_sensor` (`binary_sensor`)
  - `A8`: `ble:switchbot:vacation_bedroom_window` -> `read_sensor` (`binary_sensor`)
  - `A9`: `ble:sensorpush:vacation_temp_basement` -> `read_sensor` (`sensor`)
  - `A10`: `ble:ruuvitag_ble:vacation_temp_attic` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A11`: `tuya:light.vacation_light_1.status` -> `status` (`light`)
  - `A12`: `tuya:light.vacation_light_2.status` -> `status` (`light`)
  - `A13`: `tuya:light.vacation_light_3.status` -> `status` (`light`)
  - `A14`: `tuya:light.vacation_light_4.status` -> `status` (`light`)
  - `A15`: `tuya:switch.vacation_strip_1.status` -> `status` (`switch`)
  - `A16`: `tuya:switch.vacation_strip_2.status` -> `status` (`switch`)
  - `A17`: `tuya:switch.vacation_strip_3.status` -> `status` (`switch`)
  - `A18`: `tuya:switch.vacation_strip_4.status` -> `status` (`switch`)
  - `A19`: `ecobee:thermostat.vacation` -> `read_runtime` (`climate`)
  - `A20`: `blink:security.vacation_system` -> `read_runtime` (`sensor`)
- Local lane:
  - `A21`: `tplink:plug.vacation_router` -> `get_state` (`switch`)
  - `A22`: `tplink:plug.vacation_desk` -> `get_state` (`switch`)
  - `A23`: `tplink:plug.vacation_kitchen` -> `get_state` (`switch`)
  - `A24`: `hue:bridge_1:vacation_living_group` -> `get_state` (`light`)
  - `A25`: `hue:bridge_1:vacation_hall_group` -> `get_state` (`light`)
  - `A26`: `hue:bridge_1:vacation_bedroom_group` -> `get_state` (`light`)
  - `A27`: `webostv:media_player.vacation_living_tv` -> `get_state` (`media_player`)
  - `A28`: `roku:media_player.vacation_guest_roku` -> `get_state` (`media_player`)
  - `A29`: `denonavr:media_player.vacation_avr` -> `get_state` (`media_player`)
- Writeback:
  - `A30`: `sensor.vdev_vacation_departure_final_audit_01_ble_lane` -> `publish` (`sensor`)
  - `A31`: `sensor.vdev_vacation_departure_final_audit_01_cloud_lane` -> `publish` (`sensor`)
  - `A32`: `sensor.vdev_vacation_departure_final_audit_01_local_lane` -> `publish` (`sensor`)
  - `A33`: `sensor.vdev_vacation_departure_final_audit_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large realistic stress case for departure.
- Cloud burst and local frontier are both non-trivial.
- BLE lane is long but still semantically natural.

### Main Optimization Focus
- Whole-home BLE sweep
- Cloud same-provider grouping
- Local plug and media packing
- Vacation-mode writeback chain

## Case 44. Come-Home Security and Comfort Merge

- `vdev_id`: `vdev_come_home_security_comfort_merge_01`
- Group: Profile Coverage - Arrival and Departure Routines
- Scenario: When residents come home, the routine merges security, lighting, and comfort state into one concise arrival summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:come_home_entry_motion` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:switchbot:come_home_entry_curtain` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A3`: `blink:security.come_home` -> `read_runtime` (`sensor`)
  - `A4`: `tuya:light.come_home_living_1.status` -> `status` (`light`)
  - `A5`: `tuya:light.come_home_living_2.status` -> `status` (`light`)
  - `A6`: `ecobee:thermostat.come_home` -> `read_runtime` (`climate`)
- Local lane:
  - `A7`: `hue:bridge_1:entry_light` -> `get_state` (`light`)
  - `A8`: `hue:bridge_1:hallway_light_left` -> `get_state` (`light`)
  - `A9`: `hue:bridge_1:hallway_light_right` -> `get_state` (`light`)
  - `A10`: `philips_js:tv.entry_area` -> `get_state` (`media_player`)
- Writeback:
  - `A11`: `sensor.vdev_come_home_security_comfort_merge_01_ble_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_come_home_security_comfort_merge_01_cloud_lane` -> `publish` (`sensor`)
  - `A13`: `sensor.vdev_come_home_security_comfort_merge_01_local_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_come_home_security_comfort_merge_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Small but realistic arrival/security benchmark.
- Cloud security plus thermostat state is separated from local Hue and TV state.
- Useful sanity case for mixed schedule overhead.

### Main Optimization Focus
- Small mixed-lane schedule quality
- Security and comfort provider separation
- Short publish tail

## Case 45. Bedtime Lockdown Profile Coverage

- `vdev_id`: `vdev_bedtime_lockdown_profile_01`
- Group: Profile Coverage - Evening and Overnight Routines
- Scenario: Before sleep, the routine checks bedroom, hallway, living-room, door or window, plug, and climate state before publishing a night lockdown summary.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:bedtime_curtain_left` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:bedtime_curtain_right` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:bedtime_lamp_left` -> `read_status` (`device`)
  - `A4`: `ble:switchbot:bedtime_lamp_right` -> `read_status` (`device`)
  - `A5`: `ble:switchbot:bedtime_front_door` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:switchbot:bedtime_kitchen_window` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:switchbot:bedtime_bedroom_window` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A8`: `tuya:light.bedtime_light_1.status` -> `status` (`light`)
  - `A9`: `tuya:light.bedtime_light_2.status` -> `status` (`light`)
  - `A10`: `tuya:light.bedtime_light_3.status` -> `status` (`light`)
  - `A11`: `tuya:climate.bedtime_ac.status` -> `status` (`climate`)
  - `A12`: `ecobee:thermostat.bedtime` -> `read_runtime` (`climate`)
- Local lane:
  - `A13`: `hue:bridge_1:hallway_bedtime_group` -> `get_state` (`light`)
  - `A14`: `tplink:plug.bedtime_heater` -> `get_state` (`switch`)
  - `A15`: `tplink:plug.bedside` -> `get_state` (`switch`)
- Writeback:
  - `A16`: `sensor.vdev_bedtime_lockdown_profile_01_ble_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_bedtime_lockdown_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A18`: `sensor.vdev_bedtime_lockdown_profile_01_local_lane` -> `publish` (`sensor`)
  - `A19`: `sensor.vdev_bedtime_lockdown_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Very natural bedtime case for paper readers.
- BLE lane combines curtains, bedside lamps, and door or window sensors.
- Cloud and local lanes are both non-trivial.

### Main Optimization Focus
- BLE read/status chain
- Cloud light and climate grouping
- Local Hue and TP-Link packing
- Night summary writeback

## Case 46. Kids' Room Night Safety Check

- `vdev_id`: `vdev_kids_room_night_safety_check_01`
- Group: Profile Coverage - Evening and Overnight Routines
- Scenario: Before sleep, the routine checks a kids-room temperature, humidity, lighting, curtain, AC, and window state.

### Composition
- BLE lane:
  - `A1`: `ble:qingping:kids_room_night_temp_left` -> `read_sensor` (`sensor`)
  - `A2`: `ble:sensorpush:kids_room_night_temp_right` -> `read_sensor` (`sensor`)
  - `A3`: `ble:switchbot:kids_room_night_curtain` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:kids_room_window_night` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A5`: `tuya:climate.kids_room_night_ac.status` -> `status` (`climate`)
  - `A6`: `tuya:light.kids_room_night_light.status` -> `status` (`light`)
  - `A7`: `smartthings:kids_room_night_devices` -> `read_runtime` (`sensor`)
- Local lane:
  - `A8`: `hue:bridge_1:kids_room_night_group` -> `get_state` (`light`)
- Writeback:
  - `A9`: `sensor.vdev_kids_room_night_safety_check_01_ble_lane` -> `publish` (`sensor`)
  - `A10`: `sensor.vdev_kids_room_night_safety_check_01_cloud_lane` -> `publish` (`sensor`)
  - `A11`: `sensor.vdev_kids_room_night_safety_check_01_local_lane` -> `publish` (`sensor`)
  - `A12`: `sensor.vdev_kids_room_night_safety_check_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Small daily safety routine.
- BLE sensor mix covers Qingping, SensorPush, Xiaomi, and SwitchBot.
- Cloud SmartThings aggregation tests non-Tuya provider handling.

### Main Optimization Focus
- Small mixed case quality
- BLE read-heavy path
- Cloud provider separation

## Case 47. Late-Night Entertainment Shutdown

- `vdev_id`: `vdev_late_night_entertainment_shutdown_01`
- Group: Profile Coverage - Evening and Overnight Routines
- Scenario: After watching TV at night, the routine checks whether the living-room entertainment area is fully shut down.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:entertainment_shutdown_curtain` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:entertainment_shutdown_environment` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A3`: `tuya:light.shutdown_living_light_1.status` -> `status` (`light`)
  - `A4`: `tuya:light.shutdown_living_light_2.status` -> `status` (`light`)
  - `A5`: `tuya:switch.shutdown_entertainment_strip.status` -> `status` (`switch`)
- Local lane:
  - `A6`: `denonavr:media_player.shutdown_avr` -> `get_state` (`media_player`)
  - `A7`: `roku:media_player.shutdown_roku` -> `get_state` (`media_player`)
  - `A8`: `webostv:media_player.shutdown_tv` -> `get_state` (`media_player`)
  - `A9`: `hue:bridge_1:shutdown_living_light_left` -> `get_state` (`light`)
  - `A10`: `hue:bridge_1:shutdown_living_light_right` -> `get_state` (`light`)
  - `A11`: `tplink:plug.shutdown_speaker` -> `get_state` (`switch`)
  - `A12`: `tplink:plug.shutdown_tv` -> `get_state` (`switch`)
- Writeback:
  - `A13`: `sensor.vdev_late_night_entertainment_shutdown_01_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_late_night_entertainment_shutdown_01_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_late_night_entertainment_shutdown_01_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_late_night_entertainment_shutdown_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Local API heavy case with AV integrations.
- BLE and cloud lanes remain present but smaller.
- Good target for cheap local lane packing.

### Main Optimization Focus
- Local AV and plug packing
- Cloud light and switch grouping
- Small BLE context reads

## Case 48. Overnight Quiet-Hours Snapshot

- `vdev_id`: `vdev_overnight_quiet_hours_snapshot_01`
- Group: Profile Coverage - Evening and Overnight Routines
- Scenario: At a fixed overnight time, the routine snapshots the family's quiet-hours state across environmental sensors, door or window sensors, Hue groups, thermostats, power strips, and Netatmo environment runtime.

### Composition
- BLE lane:
  - `A1`: `ble:airthings_ble:overnight_air_bedroom` -> `read_sensor` (`sensor`)
  - `A2`: `ble:ruuvitag_ble:overnight_environment_bedroom` -> `read_sensor` (`sensor`)
  - `A3`: `ble:ruuvitag_ble:overnight_environment_kids_room` -> `read_sensor` (`sensor`)
  - `A4`: `ble:switchbot:overnight_front_door` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:switchbot:overnight_bedroom_window` -> `read_sensor` (`binary_sensor`)
- Cloud lane:
  - `A6`: `ecobee:thermostat.overnight_1` -> `read_runtime` (`climate`)
  - `A7`: `ecobee:thermostat.overnight_2` -> `read_runtime` (`climate`)
  - `A8`: `tuya:switch.overnight_strip_1.status` -> `status` (`switch`)
  - `A9`: `tuya:switch.overnight_strip_2.status` -> `status` (`switch`)
  - `A10`: `netatmo:station.overnight_environment` -> `read_runtime` (`sensor`)
- Local lane:
  - `A11`: `hue:bridge_1:overnight_bedroom_group` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:overnight_hallway_group` -> `get_state` (`light`)
- Writeback:
  - `A13`: `sensor.vdev_overnight_quiet_hours_snapshot_01_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_overnight_quiet_hours_snapshot_01_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_overnight_quiet_hours_snapshot_01_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_overnight_quiet_hours_snapshot_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Read-heavy overnight monitoring case.
- Cloud lane mixes two Ecobee thermostats, Tuya switches, and Netatmo.
- BLE environment and safety sensors stay realistic.

### Main Optimization Focus
- Read-heavy cloud grouping
- BLE environmental sensor sweep
- Short overnight writeback tail

## Case 49. Weekend Whole-Home Snapshot Profile Coverage

- `vdev_id`: `vdev_weekend_whole_home_snapshot_profile_01`
- Group: Profile Coverage - Monitoring and Audit Routines
- Scenario: On a weekend, the routine builds a whole-home snapshot of lights, curtains, temperature, energy, air quality, local media, and climate state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:weekend_profile_curtain_living` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:weekend_profile_curtain_bedroom` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:weekend_profile_curtain_study` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:weekend_profile_temp_living` -> `read_sensor` (`sensor`)
  - `A5`: `ble:switchbot:weekend_profile_temp_bedroom` -> `read_sensor` (`sensor`)
  - `A6`: `ble:switchbot:weekend_profile_temp_kids` -> `read_sensor` (`sensor`)
  - `A7`: `ble:switchbot:weekend_profile_air_node` -> `connect` (`esphome`)
  - `A8`: `ble:switchbot:weekend_profile_relay_node` -> `subscribe` (`manager`)
- Cloud lane:
  - `A9`: `tuya:light.weekend_profile_light_1.status` -> `status` (`light`)
  - `A10`: `tuya:light.weekend_profile_light_2.status` -> `status` (`light`)
  - `A11`: `tuya:light.weekend_profile_light_3.status` -> `status` (`light`)
  - `A12`: `tuya:light.weekend_profile_light_4.status` -> `status` (`light`)
  - `A13`: `tuya:climate.weekend_profile_ac_1.status` -> `status` (`climate`)
  - `A14`: `tuya:climate.weekend_profile_ac_2.status` -> `status` (`climate`)
  - `A15`: `tuya:switch.weekend_profile_strip_1.status` -> `status` (`switch`)
  - `A16`: `tuya:switch.weekend_profile_strip_2.status` -> `status` (`switch`)
  - `A17`: `netatmo:station.weekend_environment` -> `read_runtime` (`sensor`)
- Local lane:
  - `A18`: `hue:bridge_1:weekend_living_group` -> `get_state` (`light`)
  - `A19`: `hue:bridge_1:weekend_dining_group` -> `get_state` (`light`)
  - `A20`: `hue:bridge_1:weekend_bedroom_group` -> `get_state` (`light`)
  - `A21`: `tplink:plug.weekend_kitchen` -> `get_state` (`switch`)
  - `A22`: `tplink:plug.weekend_study` -> `get_state` (`switch`)
  - `A23`: `nanoleaf:panel.weekend_family_room` -> `get_state` (`light`)
  - `A24`: `roku:media_player.weekend_family_room` -> `get_state` (`media_player`)
- Writeback:
  - `A25`: `sensor.vdev_weekend_whole_home_snapshot_profile_01_ble_lane` -> `publish` (`sensor`)
  - `A26`: `sensor.vdev_weekend_whole_home_snapshot_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A27`: `sensor.vdev_weekend_whole_home_snapshot_profile_01_local_lane` -> `publish` (`sensor`)
  - `A28`: `sensor.vdev_weekend_whole_home_snapshot_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Flagship whole-home mixed benchmark.
- Contains BLE connect-before-subscribe plus many ordinary BLE reads.
- Cloud and local frontiers are both large enough to show packing quality.

### Main Optimization Focus
- Large BLE lane with connect-before-subscribe
- Cloud burst grouping
- Cheap local frontier completeness
- Whole-home summary writeback

## Case 50. Whole-Home Energy and HVAC Audit Profile Coverage

- `vdev_id`: `vdev_whole_home_energy_hvac_audit_profile_01`
- Group: Profile Coverage - Monitoring and Audit Routines
- Scenario: At a fixed time, the routine audits lights, plug strips, climates, thermostats, local plugs, and local entertainment devices for energy and HVAC state.

### Composition
- Cloud lane:
  - `A1`: `tuya:light.energy_audit_light_1.status` -> `status` (`light`)
  - `A2`: `tuya:light.energy_audit_light_2.status` -> `status` (`light`)
  - `A3`: `tuya:light.energy_audit_light_3.status` -> `status` (`light`)
  - `A4`: `tuya:light.energy_audit_light_4.status` -> `status` (`light`)
  - `A5`: `tuya:switch.energy_audit_strip_1.status` -> `status` (`switch`)
  - `A6`: `tuya:switch.energy_audit_strip_2.status` -> `status` (`switch`)
  - `A7`: `tuya:switch.energy_audit_strip_3.status` -> `status` (`switch`)
  - `A8`: `tuya:switch.energy_audit_strip_4.status` -> `status` (`switch`)
  - `A9`: `tuya:climate.energy_audit_ac_1.status` -> `status` (`climate`)
  - `A10`: `tuya:climate.energy_audit_ac_2.status` -> `status` (`climate`)
  - `A11`: `ecobee:thermostat.energy_audit_1` -> `read_runtime` (`climate`)
  - `A12`: `ecobee:thermostat.energy_audit_2` -> `read_runtime` (`climate`)
  - `A13`: `smartthings:platform.energy_snapshot` -> `read_runtime` (`sensor`)
- Local lane:
  - `A14`: `tplink:plug.energy_audit_1` -> `get_state` (`switch`)
  - `A15`: `tplink:plug.energy_audit_2` -> `get_state` (`switch`)
  - `A16`: `tplink:plug.energy_audit_3` -> `get_state` (`switch`)
  - `A17`: `denonavr:media_player.energy_audit_avr` -> `get_state` (`media_player`)
  - `A18`: `webostv:media_player.energy_audit_tv` -> `get_state` (`media_player`)
- Writeback:
  - `A19`: `sensor.vdev_whole_home_energy_hvac_audit_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A20`: `sensor.vdev_whole_home_energy_hvac_audit_profile_01_local_lane` -> `publish` (`sensor`)
  - `A21`: `sensor.vdev_whole_home_energy_hvac_audit_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Cloud-heavy and local-heavy case without BLE.
- Useful to test cloud frontier completeness independently from BLE constraints.
- Local media state should not block cloud burst grouping.

### Main Optimization Focus
- Cloud heavy scheduling
- Local heavy packing
- Provider separation without BLE
- Energy audit writeback

## Case 51. Indoor Air and Climate Audit

- `vdev_id`: `vdev_indoor_air_climate_audit_01`
- Group: Profile Coverage - Monitoring and Audit Routines
- Scenario: The routine audits air quality and climate state across BLE environmental sensors, local ambience lights, Tuya climates, Ecobee thermostats, and Netatmo station runtime.

### Composition
- BLE lane:
  - `A1`: `ble:airthings_ble:climate_audit_airthings` -> `read_sensor` (`sensor`)
  - `A2`: `ble:sensorpush:climate_audit_sensorpush_1` -> `read_sensor` (`sensor`)
  - `A3`: `ble:sensorpush:climate_audit_sensorpush_2` -> `read_sensor` (`sensor`)
  - `A4`: `ble:qingping:climate_audit_qingping_1` -> `read_sensor` (`sensor`)
  - `A5`: `ble:qingping:climate_audit_qingping_2` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A6`: `tuya:climate.climate_audit_ac_1.status` -> `status` (`climate`)
  - `A7`: `tuya:climate.climate_audit_ac_2.status` -> `status` (`climate`)
  - `A8`: `tuya:climate.climate_audit_ac_3.status` -> `status` (`climate`)
  - `A9`: `ecobee:thermostat.climate_audit_1` -> `read_runtime` (`climate`)
  - `A10`: `ecobee:thermostat.climate_audit_2` -> `read_runtime` (`climate`)
  - `A11`: `netatmo:station.climate_audit` -> `read_runtime` (`sensor`)
- Local lane:
  - `A12`: `nanoleaf:panel.climate_audit` -> `get_state` (`light`)
- Writeback:
  - `A13`: `sensor.vdev_indoor_air_climate_audit_01_ble_lane` -> `publish` (`sensor`)
  - `A14`: `sensor.vdev_indoor_air_climate_audit_01_cloud_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_indoor_air_climate_audit_01_local_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_indoor_air_climate_audit_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Realistic environment and climate daily audit.
- BLE environmental families exercise the expanded profile coverage.
- Cloud climate grouping remains conservative.

### Main Optimization Focus
- BLE environmental sensor coverage
- Cloud climate grouping
- Local Nanoleaf cheap lane

## Case 52. Security and Presence Fabric Snapshot

- `vdev_id`: `vdev_security_presence_fabric_snapshot_01`
- Group: Profile Coverage - Monitoring and Audit Routines
- Scenario: At a fixed time, the routine checks whole-home presence, doors, motion, curtains, security platform state, and essential lights.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:presence_motion_entry` -> `read_sensor` (`binary_sensor`)
  - `A2`: `ble:switchbot:presence_motion_hallway` -> `read_sensor` (`binary_sensor`)
  - `A3`: `ble:switchbot:presence_front_door` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:switchbot:presence_back_door` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:switchbot:presence_kitchen_window` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:switchbot:presence_bedroom_window` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:switchbot:presence_curtain_living` -> `refresh_cover` (`cover`)
  - `A8`: `ble:switchbot:presence_curtain_bedroom` -> `refresh_cover` (`cover`)
- Cloud lane:
  - `A9`: `blink:security.presence_fabric` -> `read_runtime` (`sensor`)
  - `A10`: `smartthings:presence.fabric_snapshot` -> `read_runtime` (`sensor`)
  - `A11`: `tuya:light.presence_light_1.status` -> `status` (`light`)
  - `A12`: `tuya:light.presence_light_2.status` -> `status` (`light`)
- Local lane:
  - `A13`: `hue:bridge_1:security_entry_group` -> `get_state` (`light`)
- Writeback:
  - `A14`: `sensor.vdev_security_presence_fabric_snapshot_01_ble_lane` -> `publish` (`sensor`)
  - `A15`: `sensor.vdev_security_presence_fabric_snapshot_01_cloud_lane` -> `publish` (`sensor`)
  - `A16`: `sensor.vdev_security_presence_fabric_snapshot_01_local_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_security_presence_fabric_snapshot_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Security-focused benchmark that remains easy to explain.
- BLE safety sensors dominate but cloud security and presence aggregation also matter.
- Local lane is deliberately small and cheap.

### Main Optimization Focus
- BLE safety sensor sweep
- Cloud security and presence providers
- Minimal local packing
- Security summary writeback

## Case 53. Party Preparation Full Sweep

- `vdev_id`: `vdev_party_preparation_full_sweep_01`
- Group: Profile Coverage - Realistic Stress Routines
- Scenario: Before a party, the routine checks living-room and dining-room lighting, curtains, climate, entertainment devices, and air quality.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:party_full_curtain_living` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:party_full_curtain_dining` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:party_full_motion` -> `read_sensor` (`binary_sensor`)
  - `A4`: `ble:airthings_ble:party_full_air_quality` -> `read_sensor` (`sensor`)
- Cloud lane:
  - `A5`: `tuya:light.party_full_light_1.status` -> `status` (`light`)
  - `A6`: `tuya:light.party_full_light_2.status` -> `status` (`light`)
  - `A7`: `tuya:light.party_full_light_3.status` -> `status` (`light`)
  - `A8`: `tuya:switch.party_full_strip_1.status` -> `status` (`switch`)
  - `A9`: `tuya:switch.party_full_strip_2.status` -> `status` (`switch`)
  - `A10`: `tuya:climate.party_full_ac.status` -> `status` (`climate`)
- Local lane:
  - `A11`: `hue:bridge_1:party_light_1` -> `get_state` (`light`)
  - `A12`: `hue:bridge_1:party_light_2` -> `get_state` (`light`)
  - `A13`: `hue:bridge_1:party_light_3` -> `get_state` (`light`)
  - `A14`: `hue:bridge_1:party_light_4` -> `get_state` (`light`)
  - `A15`: `nanoleaf:panel.party_full` -> `get_state` (`light`)
  - `A16`: `denonavr:media_player.party_avr` -> `get_state` (`media_player`)
  - `A17`: `roku:media_player.party_roku` -> `get_state` (`media_player`)
  - `A18`: `webostv:media_player.party_tv` -> `get_state` (`media_player`)
- Writeback:
  - `A19`: `sensor.vdev_party_preparation_full_sweep_01_ble_lane` -> `publish` (`sensor`)
  - `A20`: `sensor.vdev_party_preparation_full_sweep_01_cloud_lane` -> `publish` (`sensor`)
  - `A21`: `sensor.vdev_party_preparation_full_sweep_01_local_lane` -> `publish` (`sensor`)
  - `A22`: `sensor.vdev_party_preparation_full_sweep_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large but realistic party preparation benchmark.
- Local lane includes Hue, Nanoleaf, Denon AVR, Roku, and webOS TV.
- Cloud and BLE lanes remain significant enough for mixed optimization.

### Main Optimization Focus
- Local API frontier packing
- Cloud light/switch/climate grouping
- BLE curtain and air-quality reads
- Party-readiness writeback

## Case 54. Holiday Vacation Mode Full Audit

- `vdev_id`: `vdev_holiday_vacation_mode_full_audit_01`
- Group: Profile Coverage - Realistic Stress Routines
- Scenario: Before a holiday trip, the routine performs the largest whole-home audit across curtains, doors, windows, environmental sensors, ESPHome transport, local lights, plugs, TVs, and cloud HVAC or security systems.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:holiday_curtain_1` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:holiday_curtain_2` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:holiday_curtain_3` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:holiday_curtain_4` -> `refresh_cover` (`cover`)
  - `A5`: `ble:switchbot:holiday_door_window_1` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:switchbot:holiday_door_window_2` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:switchbot:holiday_door_window_3` -> `read_sensor` (`binary_sensor`)
  - `A8`: `ble:switchbot:holiday_door_window_4` -> `read_sensor` (`binary_sensor`)
  - `A9`: `ble:switchbot:holiday_door_window_5` -> `read_sensor` (`binary_sensor`)
  - `A10`: `ble:qingping:holiday_temp_1` -> `read_sensor` (`sensor`)
  - `A11`: `ble:sensorpush:holiday_temp_2` -> `read_sensor` (`sensor`)
  - `A12`: `ble:sensorpush:holiday_temp_3` -> `read_sensor` (`sensor`)
  - `A13`: `ble:switchbot:holiday_esphome_connect` -> `connect` (`esphome`)
  - `A14`: `ble:switchbot:holiday_esphome_subscribe` -> `subscribe` (`manager`)
- Cloud lane:
  - `A15`: `tuya:light.holiday_light_1.status` -> `status` (`light`)
  - `A16`: `tuya:light.holiday_light_2.status` -> `status` (`light`)
  - `A17`: `tuya:light.holiday_light_3.status` -> `status` (`light`)
  - `A18`: `tuya:light.holiday_light_4.status` -> `status` (`light`)
  - `A19`: `tuya:switch.holiday_strip_1.status` -> `status` (`switch`)
  - `A20`: `tuya:switch.holiday_strip_2.status` -> `status` (`switch`)
  - `A21`: `tuya:switch.holiday_strip_3.status` -> `status` (`switch`)
  - `A22`: `tuya:switch.holiday_strip_4.status` -> `status` (`switch`)
  - `A23`: `tuya:climate.holiday_ac_1.status` -> `status` (`climate`)
  - `A24`: `tuya:climate.holiday_ac_2.status` -> `status` (`climate`)
  - `A25`: `ecobee:thermostat.holiday` -> `read_runtime` (`climate`)
  - `A26`: `blink:security.holiday` -> `read_runtime` (`sensor`)
- Local lane:
  - `A27`: `hue:bridge_1:holiday_light_group_1` -> `get_state` (`light`)
  - `A28`: `hue:bridge_1:holiday_light_group_2` -> `get_state` (`light`)
  - `A29`: `hue:bridge_1:holiday_light_group_3` -> `get_state` (`light`)
  - `A30`: `tplink:plug.holiday_1` -> `get_state` (`switch`)
  - `A31`: `tplink:plug.holiday_2` -> `get_state` (`switch`)
  - `A32`: `tplink:plug.holiday_3` -> `get_state` (`switch`)
  - `A33`: `webostv:media_player.holiday_tv` -> `get_state` (`media_player`)
  - `A34`: `roku:media_player.holiday_roku` -> `get_state` (`media_player`)
- Writeback:
  - `A35`: `sensor.vdev_holiday_vacation_mode_full_audit_01_ble_lane` -> `publish` (`sensor`)
  - `A36`: `sensor.vdev_holiday_vacation_mode_full_audit_01_cloud_lane` -> `publish` (`sensor`)
  - `A37`: `sensor.vdev_holiday_vacation_mode_full_audit_01_local_lane` -> `publish` (`sensor`)
  - `A38`: `sensor.vdev_holiday_vacation_mode_full_audit_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Large realistic stress benchmark with all three lanes.
- BLE connect-before-subscribe is embedded in a long BLE safety sweep.
- Cloud and local frontiers are both dense enough to reveal scheduler weaknesses.

### Main Optimization Focus
- Large BLE safety and environment sweep
- Cloud burst grouping with security state
- Local media and plug packing
- Holiday audit summary

## Case 55. BLE Safety Sweep Routine

- `vdev_id`: `vdev_ble_safety_sweep_routine_01`
- Group: Profile Coverage - Realistic Stress Routines
- Scenario: At a fixed time, the routine performs a whole-home BLE safety sweep over curtains, doors, windows, motion sensors, bedside lamps, environmental sensors, and ESPHome transport state.

### Composition
- BLE lane:
  - `A1`: `ble:switchbot:ble_safety_curtain_1` -> `refresh_cover` (`cover`)
  - `A2`: `ble:switchbot:ble_safety_curtain_2` -> `refresh_cover` (`cover`)
  - `A3`: `ble:switchbot:ble_safety_curtain_3` -> `refresh_cover` (`cover`)
  - `A4`: `ble:switchbot:ble_safety_door_window_1` -> `read_sensor` (`binary_sensor`)
  - `A5`: `ble:switchbot:ble_safety_door_window_2` -> `read_sensor` (`binary_sensor`)
  - `A6`: `ble:switchbot:ble_safety_door_window_3` -> `read_sensor` (`binary_sensor`)
  - `A7`: `ble:switchbot:ble_safety_door_window_4` -> `read_sensor` (`binary_sensor`)
  - `A8`: `ble:switchbot:ble_safety_motion_1` -> `read_sensor` (`binary_sensor`)
  - `A9`: `ble:switchbot:ble_safety_motion_2` -> `read_sensor` (`binary_sensor`)
  - `A10`: `ble:switchbot:ble_safety_lamp_1` -> `read_status` (`device`)
  - `A11`: `ble:switchbot:ble_safety_lamp_2` -> `read_status` (`device`)
  - `A12`: `ble:airthings_ble:ble_safety_airthings` -> `read_sensor` (`sensor`)
  - `A13`: `ble:ruuvitag_ble:ble_safety_ruuvitag` -> `read_sensor` (`sensor`)
  - `A14`: `ble:switchbot:ble_safety_esphome_connect` -> `connect` (`esphome`)
  - `A15`: `ble:switchbot:ble_safety_esphome_subscribe` -> `subscribe` (`manager`)
- Writeback:
  - `A16`: `sensor.vdev_ble_safety_sweep_routine_01_ble_lane` -> `publish` (`sensor`)
  - `A17`: `sensor.vdev_ble_safety_sweep_routine_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- BLE-heavy but still realistic safety scenario.
- Useful to test atomic BLE schedule behavior before any micro refinement.
- Only BLE lane and overall writeback keep the proof surface focused.

### Main Optimization Focus
- BLE-heavy atomic schedule
- Connect-before-subscribe constraint
- BLE lane publish plus overall publish

## Case 56. Cloud Burst Living Conditions Snapshot Profile Coverage

- `vdev_id`: `vdev_cloud_burst_living_conditions_snapshot_profile_01`
- Group: Profile Coverage - Realistic Stress Routines
- Scenario: During a weather change or scheduled snapshot, the routine performs a burst read over whole-home lights, plug strips, climates, thermostats, Netatmo runtime, SmartThings aggregation, and a small local plug lane.

### Composition
- Cloud lane:
  - `A1`: `tuya:light.cloud_burst_light_1.status` -> `status` (`light`)
  - `A2`: `tuya:light.cloud_burst_light_2.status` -> `status` (`light`)
  - `A3`: `tuya:light.cloud_burst_light_3.status` -> `status` (`light`)
  - `A4`: `tuya:light.cloud_burst_light_4.status` -> `status` (`light`)
  - `A5`: `tuya:light.cloud_burst_light_5.status` -> `status` (`light`)
  - `A6`: `tuya:switch.cloud_burst_strip_1.status` -> `status` (`switch`)
  - `A7`: `tuya:switch.cloud_burst_strip_2.status` -> `status` (`switch`)
  - `A8`: `tuya:switch.cloud_burst_strip_3.status` -> `status` (`switch`)
  - `A9`: `tuya:switch.cloud_burst_strip_4.status` -> `status` (`switch`)
  - `A10`: `tuya:switch.cloud_burst_strip_5.status` -> `status` (`switch`)
  - `A11`: `tuya:climate.cloud_burst_ac_1.status` -> `status` (`climate`)
  - `A12`: `tuya:climate.cloud_burst_ac_2.status` -> `status` (`climate`)
  - `A13`: `tuya:climate.cloud_burst_ac_3.status` -> `status` (`climate`)
  - `A14`: `ecobee:thermostat.cloud_burst_1` -> `read_runtime` (`climate`)
  - `A15`: `ecobee:thermostat.cloud_burst_2` -> `read_runtime` (`climate`)
  - `A16`: `netatmo:station.cloud_burst` -> `read_runtime` (`sensor`)
  - `A17`: `smartthings:platform.cloud_burst_snapshot` -> `read_runtime` (`sensor`)
- Local lane:
  - `A18`: `tplink:plug.cloud_burst_local_1` -> `get_state` (`switch`)
  - `A19`: `tplink:plug.cloud_burst_local_2` -> `get_state` (`switch`)
- Writeback:
  - `A20`: `sensor.vdev_cloud_burst_living_conditions_snapshot_profile_01_cloud_lane` -> `publish` (`sensor`)
  - `A21`: `sensor.vdev_cloud_burst_living_conditions_snapshot_profile_01_local_lane` -> `publish` (`sensor`)
  - `A22`: `sensor.vdev_cloud_burst_living_conditions_snapshot_profile_01_overall` -> `publish` (`sensor`)

### Why It Is Useful
- Cloud-heavy flagship benchmark.
- Provider separation and same-provider grouping are both visible.
- Small local TP-Link lane tests that cloud burst does not swallow cheap local work.

### Main Optimization Focus
- Cloud burst batching
- Provider separation
- Backoff-safe same-bucket grouping
- Small local lane packing

## Notes

- The generated `manifest.json` is the active source of truth for the current suite.
- The benchmark generator script is `scripts/run_vdev_benchmarks.py`.
- Targets are written under `data/targets/vdev_benchmarks`.
