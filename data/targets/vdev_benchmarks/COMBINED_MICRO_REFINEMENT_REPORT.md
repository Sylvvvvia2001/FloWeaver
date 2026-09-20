# Combined BLE + API Micro-Refinement Report

This report combines BLE and API micro-refinement over the M5 plan.
The combined layer checks conflicts and validates the merged schedule.

## Combined Policy

- `conflict_policy` = `highest_saving_wins`
- `forbid_batch_overlap` = `True`
- `forbid_action_overlap` = `True`
- `require_component_validation` = `True`
- `require_contiguous_corridor_batches` = `True`
- `require_segment_local_refinement` = `True`
- `enforce_batch_order_projection` = `True`
- `ble_global_xfer_limit` = `1`
- `ble_global_connect_prepare_limit` = `1`
- `cloud_host_request_limit` = `1`
- `cloud_bucket_request_limit` = `1`
- `local_endpoint_request_limit` = `1`
- `local_session_request_limit` = `1`
- `max_global_parse_overlap` = `1`
- `adjacent_batch_gap_threshold` = `1`
- `forbid_adjacent_same_ble_session_domain` = `True`
- `forbid_adjacent_same_api_host_domain` = `False`
- `forbid_adjacent_same_api_endpoint_domain` = `False`

## Overview

| Case | BLE Save | API Save | Combined Save | Combined % | Conflicts | Validator |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| vdev_homecoming_security_ambience_merge_01 | 0 ms | 25 ms | 25 ms | 1.3% | 0 | pass |

## Case Details

### Homecoming Security and Ambience Merge (`vdev_homecoming_security_ambience_merge_01`)

- Group: Scene Activation and Comfort Control Routines
- Original estimated latency: `1900 ms`
- BLE additional saving: `0 ms`
- API additional saving: `25 ms`
- Combined additional saving: `25 ms` (`1.3%`)
- Combined refined estimated latency: `1875 ms`
- Conflict count: `0`
- Validator passed: `True`
- Simulated event count: `18`
- Projection / order / resource checks:
  - `component_validations_ok = True`
  - `conflict_free = True`
  - `contiguous_coverage_ok = True`
  - `savings_consistency_ok = True`
  - `batch_order_preserved = True`
  - `projection_ok = True`
  - `ble_constraints_ok = True`
  - `api_constraints_ok = True`
  - `event_loop_constraints_ok = True`
- Accepted corridors:
  - `API:corridor_00` batches=`['batch_002', 'batch_003']` actions=`['A8', 'A9']` save=`25 ms`

## Component Policies

### BLE

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

### API

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
