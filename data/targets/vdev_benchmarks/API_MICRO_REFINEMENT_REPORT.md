# API Micro-Refinement Report

This report applies post-processing to benchmark M5 plans.
The policy permits bounded pre-request overlap under coordinator, shared-session, rate-limit, and backoff constraints.

## Policy

- `min_corridor_length` = `2`
- `min_corridor_latency_ms` = `700`
- `cloud_read_min_corridor_length` = `2`
- `cloud_read_min_corridor_latency_ms` = `700`
- `cloud_control_min_corridor_length` = `2`
- `cloud_control_min_corridor_latency_ms` = `760`
- `local_http_read_min_corridor_length` = `2`
- `local_http_read_min_corridor_latency_ms` = `180`
- `local_http_control_min_corridor_length` = `2`
- `local_http_control_min_corridor_latency_ms` = `220`
- `mqtt_read_min_corridor_length` = `3`
- `mqtt_read_min_corridor_latency_ms` = `220`
- `max_lookahead_steps` = `1`
- `require_coordinator_style_fetch` = `True`
- `disallow_entity_level_overlap` = `True`
- `preserve_refresh_cadence` = `True`
- `require_shared_web_session` = `True`
- `allow_local_prepare_overlap` = `True`
- `allow_cloud_prepare_overlap` = `True`
- `allow_cloud_auth_budget_overlap` = `True`
- `local_endpoint_concurrency_limit` = `1`
- `local_session_concurrency_limit` = `1`
- `cloud_host_concurrency_limit` = `1`
- `cloud_bucket_concurrency_limit` = `1`
- `keep_writeback_serialized` = `True`
- `disallow_parse_aggregate_cross_action_overlap` = `True`
- `disallow_backoff_bypass` = `True`
- `parse_async_safe_max_ms` = `220`
- `aggregate_async_safe_max_ms` = `180`
- `availability_must_precede_write` = `True`
- `require_known_session_key` = `True`
- `require_known_host_key` = `True`
- `require_known_endpoint_key` = `False`
- `require_known_bucket_key` = `False`
- `cloud_backoff_wait_ms` = `220`
- `treat_mqtt_as_non_overlap_lane` = `True`

## Overview

| Case | Corridors | Current Est. | Refined Est. | Added Saving | Added Saving % |
| --- | ---: | ---: | ---: | ---: | ---: |
| vdev_morning_wakeup_readiness_01 | 0 | 1510 ms | 1510 ms | 0 ms | 0.0% |
| vdev_leaving_home_safety_check_01 | 0 | 1520 ms | 1520 ms | 0 ms | 0.0% |
| vdev_arrival_comfort_preparation_01 | 1 | 2020 ms | 1916 ms | 104 ms | 5.1% |
| vdev_dinner_home_mode_01 | 2 | 1780 ms | 1672 ms | 108 ms | 6.1% |
| vdev_night_shutdown_01 | 2 | 1940 ms | 1832 ms | 108 ms | 5.6% |
| vdev_overnight_health_safety_monitoring_01 | 1 | 1880 ms | 1749 ms | 131 ms | 7.0% |
| vdev_weekend_whole_home_snapshot_01 | 1 | 2100 ms | 1991 ms | 109 ms | 5.2% |
| vdev_party_preparation_01 | 1 | 1620 ms | 1511 ms | 109 ms | 6.7% |
| vdev_party_scene_activation_01 | 1 | 3020 ms | 2900 ms | 120 ms | 4.0% |
| vdev_movie_night_blackout_01 | 1 | 3020 ms | 2900 ms | 120 ms | 4.0% |
| vdev_morning_wakeup_ramp_01 | 1 | 3020 ms | 2900 ms | 120 ms | 4.0% |
| vdev_workday_focus_mode_01 | 1 | 3930 ms | 3783 ms | 147 ms | 3.7% |
| vdev_guest_suite_welcome_01 | 1 | 4210 ms | 3997 ms | 213 ms | 5.1% |
| vdev_storm_lockdown_safety_01 | 1 | 3800 ms | 3560 ms | 240 ms | 6.3% |
| vdev_ble_safety_sweep_stress_01 | 0 | 1180 ms | 1180 ms | 0 ms | 0.0% |
| vdev_energy_hvac_audit_01 | 1 | 1610 ms | 1370 ms | 240 ms | 14.9% |

## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Group: Morning and Leaving Home Routines
- Current estimated latency: `1510 ms`
- Refined estimated latency: `1510 ms`
- Additional saving from API micro-refinement: `0 ms` (`0.0%`)
- Selected corridors: none

### Leaving Home Safety Check Routine (`vdev_leaving_home_safety_check_01`)

- Group: Morning and Leaving Home Routines
- Current estimated latency: `1520 ms`
- Refined estimated latency: `1520 ms`
- Additional saving from API micro-refinement: `0 ms` (`0.0%`)
- Selected corridors: none

### Coming Home Comfort Preparation Routine (`vdev_arrival_comfort_preparation_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `2020 ms`
- Refined estimated latency: `1916 ms`
- Additional saving from API micro-refinement: `104 ms` (`5.1%`)
- Corridor `corridor_00`: `batch_006 -> batch_007`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `920 ms` -> refined `816 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Dinner Time Home Mode Routine (`vdev_dinner_home_mode_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `1780 ms`
- Refined estimated latency: `1672 ms`
- Additional saving from API micro-refinement: `108 ms` (`6.1%`)
- Corridor `corridor_00`: `batch_004 -> batch_005`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `820 ms` -> refined `737 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`
- Corridor `corridor_01`: `batch_006 -> batch_007`; protocol `LOCAL` / kind `LOCAL_HTTP`; candidate pairs `1`; serial `200 ms` -> refined `175 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Night Shutdown Routine (`vdev_night_shutdown_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `1940 ms`
- Refined estimated latency: `1832 ms`
- Additional saving from API micro-refinement: `108 ms` (`5.6%`)
- Corridor `corridor_00`: `batch_006 -> batch_007`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `820 ms` -> refined `737 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`
- Corridor `corridor_01`: `batch_008 -> batch_009`; protocol `LOCAL` / kind `LOCAL_HTTP`; candidate pairs `1`; serial `200 ms` -> refined `175 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Overnight Health & Safety Monitoring Routine (`vdev_overnight_health_safety_monitoring_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `1880 ms`
- Refined estimated latency: `1749 ms`
- Additional saving from API micro-refinement: `131 ms` (`7.0%`)
- Corridor `corridor_00`: `batch_004 -> batch_005`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `1040 ms` -> refined `909 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `2100 ms`
- Refined estimated latency: `1991 ms`
- Additional saving from API micro-refinement: `109 ms` (`5.2%`)
- Corridor `corridor_00`: `batch_008 -> batch_009`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `940 ms` -> refined `831 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Party Preparation Routine (`vdev_party_preparation_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `1620 ms`
- Refined estimated latency: `1511 ms`
- Additional saving from API micro-refinement: `109 ms` (`6.7%`)
- Corridor `corridor_00`: `batch_004 -> batch_005`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `940 ms` -> refined `831 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `3020 ms`
- Refined estimated latency: `2900 ms`
- Additional saving from API micro-refinement: `120 ms` (`4.0%`)
- Corridor `corridor_00`: `batch_006 -> batch_007`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `1160 ms` -> refined `1040 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Movie Night Blackout Routine (`vdev_movie_night_blackout_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `3020 ms`
- Refined estimated latency: `2900 ms`
- Additional saving from API micro-refinement: `120 ms` (`4.0%`)
- Corridor `corridor_00`: `batch_006 -> batch_007`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `1160 ms` -> refined `1040 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Morning Wake-Up Ramp Routine (`vdev_morning_wakeup_ramp_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `3020 ms`
- Refined estimated latency: `2900 ms`
- Additional saving from API micro-refinement: `120 ms` (`4.0%`)
- Corridor `corridor_00`: `batch_006 -> batch_007`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `1160 ms` -> refined `1040 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Workday Focus Mode Routine (`vdev_workday_focus_mode_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `3930 ms`
- Refined estimated latency: `3783 ms`
- Additional saving from API micro-refinement: `147 ms` (`3.7%`)
- Corridor `corridor_00`: `batch_007 -> batch_008`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `1`; serial `1400 ms` -> refined `1253 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Guest Suite Welcome Routine (`vdev_guest_suite_welcome_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `4210 ms`
- Refined estimated latency: `3997 ms`
- Additional saving from API micro-refinement: `213 ms` (`5.1%`)
- Corridor `corridor_00`: `batch_007 -> batch_008 -> batch_009`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `2`; serial `1680 ms` -> refined `1467 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### Storm Lockdown Safety Routine (`vdev_storm_lockdown_safety_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `3800 ms`
- Refined estimated latency: `3560 ms`
- Additional saving from API micro-refinement: `240 ms` (`6.3%`)
- Corridor `corridor_00`: `batch_006 -> batch_007 -> batch_008`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `2`; serial `1800 ms` -> refined `1560 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

### BLE Congestion Routine Stress (`vdev_ble_safety_sweep_stress_01`)

- Group: Household Stress and Abnormality Routines
- Current estimated latency: `1180 ms`
- Refined estimated latency: `1180 ms`
- Additional saving from API micro-refinement: `0 ms` (`0.0%`)
- Selected corridors: none

### Cloud Burst Energy & HVAC Audit Routine (`vdev_energy_hvac_audit_01`)

- Group: Household Stress and Abnormality Routines
- Current estimated latency: `1610 ms`
- Refined estimated latency: `1370 ms`
- Additional saving from API micro-refinement: `240 ms` (`14.9%`)
- Corridor `corridor_00`: `batch_000 -> batch_001 -> batch_002`; protocol `CLOUD` / kind `CLOUD`; candidate pairs `2`; serial `1510 ms` -> refined `1270 ms`; validator `true`
  constraints: coordinator=`True`, parallel_updates=`True`, session=`True`, backoff=`True`, event_loop=`True`, availability=`True`

