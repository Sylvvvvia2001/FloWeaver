# BLE Micro-Refinement Report

This report applies post-processing to benchmark M5 plans.
The policy accounts for shared scanners, connectable controllers, connection slots, device and session identity, and subscriptions.

## Policy

- `min_corridor_length` = `3`
- `min_corridor_latency_ms` = `1800`
- `read_like_min_corridor_length` = `2`
- `read_like_min_corridor_latency_ms` = `1200`
- `control_like_min_corridor_length` = `3`
- `control_like_min_corridor_latency_ms` = `1800`
- `session_chain_min_corridor_length` = `2`
- `session_chain_min_corridor_latency_ms` = `1400`
- `generic_min_corridor_length` = `3`
- `generic_min_corridor_latency_ms` = `1800`
- `max_lookahead_actions` = `1`
- `require_shared_scanner` = `True`
- `assume_shared_scanner_available` = `True`
- `require_source_resolution_for_adv_overlap` = `True`
- `allow_unknown_source_adv_overlap` = `False`
- `require_connectable_controller_for_connect_prep` = `True`
- `assume_connectable_controller_available` = `True`
- `enforce_connection_slot_guard` = `True`
- `connectable_slot_limit` = `1`
- `current_xfer_slot_cost` = `1`
- `next_connect_prepare_slot_cost` = `1`
- `allow_adv_prepare_overlap` = `True`
- `allow_connect_prepare_overlap` = `False`
- `allow_subscribe_like_adv_overlap` = `False`
- `allow_same_device_adv_overlap` = `False`
- `allow_same_session_adv_overlap` = `False`
- `source_capability_overrides` = `{'switchbot': ['adv_anchor_safe'], 'xiaomi_ble': ['adv_anchor_safe'], 'esphome': ['subscribe_adv_overlap_safe']}`
- `kind_capability_overrides` = `{'refresh_cover': ['read_like_ble_op'], 'read_sensor': ['read_like_ble_op'], 'read_status': ['read_like_ble_op'], 'connect': ['session_chain_ble_op'], 'subscribe': ['session_chain_ble_op'], 'set_cover_position': ['control_like_ble_op'], 'set_percentage': ['control_like_ble_op'], 'turn_on': ['control_like_ble_op'], 'turn_off': ['control_like_ble_op']}`
- `allow_adv_prepare_during_connect_capabilities` = `['adv_anchor_safe']`
- `allow_subscribe_like_adv_overlap_capabilities` = `['subscribe_adv_overlap_safe']`
- `allow_adv_prepare_during_connect_for_sources` = `['switchbot', 'xiaomi_ble']`
- `allow_subscribe_like_adv_overlap_sources` = `['esphome']`
- `prepare_adv_timeout_ms` = `120`
- `prepare_connect_timeout_ms` = `180`
- `prepare_must_be_side_effect_free` = `True`

## Overview

| Case | Corridors | Current Est. | Refined Est. | Added Saving | Added Saving % |
| --- | ---: | ---: | ---: | ---: | ---: |
| vdev_morning_wakeup_readiness_01 | 2 | 6070 ms | 5686 ms | 384 ms | 6.3% |
| vdev_leaving_home_safety_check_01 | 1 | 4770 ms | 4410 ms | 360 ms | 7.5% |
| vdev_arrival_comfort_preparation_01 | 2 | 6150 ms | 5820 ms | 330 ms | 5.4% |
| vdev_dinner_home_mode_01 | 1 | 4500 ms | 4218 ms | 282 ms | 6.3% |
| vdev_night_shutdown_01 | 1 | 5720 ms | 5282 ms | 438 ms | 7.7% |
| vdev_overnight_health_safety_monitoring_01 | 1 | 4400 ms | 4130 ms | 270 ms | 6.1% |
| vdev_weekend_whole_home_snapshot_01 | 2 | 7590 ms | 7080 ms | 510 ms | 6.7% |
| vdev_party_preparation_01 | 1 | 4340 ms | 4058 ms | 282 ms | 6.5% |
| vdev_party_scene_activation_01 | 2 | 7600 ms | 7168 ms | 432 ms | 5.7% |
| vdev_movie_night_blackout_01 | 2 | 7600 ms | 7168 ms | 432 ms | 5.7% |
| vdev_morning_wakeup_ramp_01 | 2 | 7600 ms | 7168 ms | 432 ms | 5.7% |
| vdev_workday_focus_mode_01 | 2 | 8590 ms | 8068 ms | 522 ms | 6.1% |
| vdev_guest_suite_welcome_01 | 2 | 8870 ms | 8348 ms | 522 ms | 5.9% |
| vdev_storm_lockdown_safety_01 | 2 | 7970 ms | 7556 ms | 414 ms | 5.2% |
| vdev_ble_safety_sweep_stress_01 | 2 | 7300 ms | 6700 ms | 600 ms | 8.2% |
| vdev_energy_hvac_audit_01 | 0 | 1610 ms | 1610 ms | 0 ms | 0.0% |

## Case Details

### Morning Wake-Up Readiness Routine (`vdev_morning_wakeup_readiness_01`)

- Group: Morning and Leaving Home Routines
- Current estimated latency: `6070 ms`
- Refined estimated latency: `5686 ms`
- Additional saving from BLE micro-refinement: `384 ms` (`6.3%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5`; candidate pairs `4`; serial `3750 ms` -> refined `3402 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A6 -> A7`; candidate pairs `1`; serial `1650 ms` -> refined `1614 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Leaving Home Safety Check Routine (`vdev_leaving_home_safety_check_01`)

- Group: Morning and Leaving Home Routines
- Current estimated latency: `4770 ms`
- Refined estimated latency: `4410 ms`
- Additional saving from BLE micro-refinement: `360 ms` (`7.5%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5`; candidate pairs `4`; serial `3850 ms` -> refined `3490 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Coming Home Comfort Preparation Routine (`vdev_arrival_comfort_preparation_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `6150 ms`
- Refined estimated latency: `5820 ms`
- Additional saving from BLE micro-refinement: `330 ms` (`5.4%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3200 ms` -> refined `2906 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A5 -> A6`; candidate pairs `1`; serial `1650 ms` -> refined `1614 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Dinner Time Home Mode Routine (`vdev_dinner_home_mode_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `4500 ms`
- Refined estimated latency: `4218 ms`
- Additional saving from BLE micro-refinement: `282 ms` (`6.3%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3200 ms` -> refined `2918 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Night Shutdown Routine (`vdev_night_shutdown_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `5720 ms`
- Refined estimated latency: `5282 ms`
- Additional saving from BLE micro-refinement: `438 ms` (`7.7%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5 -> A6`; candidate pairs `5`; serial `4500 ms` -> refined `4062 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Overnight Health & Safety Monitoring Routine (`vdev_overnight_health_safety_monitoring_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `4400 ms`
- Refined estimated latency: `4130 ms`
- Additional saving from BLE micro-refinement: `270 ms` (`6.1%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3000 ms` -> refined `2730 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Weekend Whole-Home Snapshot Routine (`vdev_weekend_whole_home_snapshot_01`)

- Group: Night and Energy Monitoring Routines
- Current estimated latency: `7590 ms`
- Refined estimated latency: `7080 ms`
- Additional saving from BLE micro-refinement: `510 ms` (`6.7%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5 -> A6`; candidate pairs `5`; serial `4800 ms` -> refined `4326 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A7 -> A8`; candidate pairs `1`; serial `1650 ms` -> refined `1614 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Party Preparation Routine (`vdev_party_preparation_01`)

- Group: Coming Home and Evening Comfort Routines
- Current estimated latency: `4340 ms`
- Refined estimated latency: `4058 ms`
- Additional saving from BLE micro-refinement: `282 ms` (`6.5%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3200 ms` -> refined `2918 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Party Scene Activation Routine (`vdev_party_scene_activation_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `7600 ms`
- Refined estimated latency: `7168 ms`
- Additional saving from BLE micro-refinement: `432 ms` (`5.7%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3800 ms` -> refined `3458 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A5 -> A6`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Movie Night Blackout Routine (`vdev_movie_night_blackout_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `7600 ms`
- Refined estimated latency: `7168 ms`
- Additional saving from BLE micro-refinement: `432 ms` (`5.7%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3800 ms` -> refined `3458 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A5 -> A6`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Morning Wake-Up Ramp Routine (`vdev_morning_wakeup_ramp_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `7600 ms`
- Refined estimated latency: `7168 ms`
- Additional saving from BLE micro-refinement: `432 ms` (`5.7%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3800 ms` -> refined `3458 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A5 -> A6`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Workday Focus Mode Routine (`vdev_workday_focus_mode_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `8590 ms`
- Refined estimated latency: `8068 ms`
- Additional saving from BLE micro-refinement: `522 ms` (`6.1%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5`; candidate pairs `4`; serial `4550 ms` -> refined `4118 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A6 -> A7`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Guest Suite Welcome Routine (`vdev_guest_suite_welcome_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `8870 ms`
- Refined estimated latency: `8348 ms`
- Additional saving from BLE micro-refinement: `522 ms` (`5.9%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5`; candidate pairs `4`; serial `4550 ms` -> refined `4118 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A6 -> A7`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Storm Lockdown Safety Routine (`vdev_storm_lockdown_safety_01`)

- Group: Scene Activation and Comfort Control Routines
- Current estimated latency: `7970 ms`
- Refined estimated latency: `7556 ms`
- Additional saving from BLE micro-refinement: `414 ms` (`5.2%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4`; candidate pairs `3`; serial `3650 ms` -> refined `3326 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A5 -> A6`; candidate pairs `1`; serial `1500 ms` -> refined `1410 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### BLE Congestion Routine Stress (`vdev_ble_safety_sweep_stress_01`)

- Group: Household Stress and Abnormality Routines
- Current estimated latency: `7300 ms`
- Refined estimated latency: `6700 ms`
- Additional saving from BLE micro-refinement: `600 ms` (`8.2%`)
- Corridor `corridor_00`: `A1 -> A2 -> A3 -> A4 -> A5 -> A6 -> A7`; candidate pairs `6`; serial `5550 ms` -> refined `4986 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`
- Corridor `corridor_01`: `A8 -> A9`; candidate pairs `1`; serial `1650 ms` -> refined `1614 ms`; validator `true`
  constraints: scanner=`True`, connectable=`True`, slots=`True`, types=`True`, rollback=`True`

### Cloud Burst Energy & HVAC Audit Routine (`vdev_energy_hvac_audit_01`)

- Group: Household Stress and Abnormality Routines
- Current estimated latency: `1610 ms`
- Refined estimated latency: `1610 ms`
- Additional saving from BLE micro-refinement: `0 ms` (`0.0%`)
- Selected corridors: none

