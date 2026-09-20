from __future__ import annotations

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget
from optimizer.ble_micro_refinement import (
    BLEMicroEvent,
    BLEMicroRefinementPolicy,
    BLE_MICRO_PHASES,
    ConservativeBLEMicroRefiner,
    estimate_plan_latency_ms,
    validate_refined_corridor,
)


def _target() -> OptimizationTarget:
    return OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={"files": ["/tmp/demo.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "refresh_cover",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:switchbot:curtain_1", "device_id": "ble:switchbot:curtain_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "refresh_cover"},
            },
            {
                "action_id": "A2",
                "type": "read_sensor",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:sensor_1", "device_id": "ble:xiaomi_ble:sensor_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
            {
                "action_id": "A3",
                "type": "read_status",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:sensor_2", "device_id": "ble:xiaomi_ble:sensor_2"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_status"},
            },
            {
                "action_id": "A4",
                "type": "status",
                "protocol": "CLOUD",
                "exec": {"kind": "ha_service_call"},
            },
            {
                "action_id": "A5",
                "type": "get_state",
                "protocol": "LOCAL",
                "exec": {"kind": "ha_service_call"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2", "A3", "A4", "A5"],
    )


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
            Batch(batch_id="batch_002", parallel_groups=[["A3"]]),
            Batch(batch_id="batch_003", parallel_groups=[["A4", "A5"]]),
        ],
        meta={},
    )


def test_ble_micro_refiner_selects_serial_ble_corridor() -> None:
    refiner = ConservativeBLEMicroRefiner(policy=BLEMicroRefinementPolicy(min_corridor_length=3, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())

    assert len(result.selected_corridors) == 1
    corridor = result.selected_corridors[0]
    assert corridor.corridor.action_ids == ["A1", "A2", "A3"]
    assert corridor.corridor.batch_ids == ["batch_000", "batch_001", "batch_002"]
    assert corridor.corridor.overlap_candidate_pairs == 2


def test_ble_micro_refiner_uses_uniform_four_phase_model_for_all_ble_actions() -> None:
    refiner = ConservativeBLEMicroRefiner(policy=BLEMicroRefinementPolicy(min_corridor_length=3, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())
    corridor = result.selected_corridors[0]

    phases_by_action = {}
    for event in corridor.refined_events:
        phases_by_action.setdefault(event.action_id, []).append(event.phase)

    for action_id in ["A1", "A2", "A3"]:
        assert phases_by_action[action_id] == list(BLE_MICRO_PHASES)


def test_ble_micro_refiner_overlaps_only_adv_prepare_and_reduces_latency() -> None:
    refiner = ConservativeBLEMicroRefiner(policy=BLEMicroRefinementPolicy(min_corridor_length=3, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())
    corridor = result.selected_corridors[0]

    assert corridor.validation.passed
    assert corridor.latency_saved_ms > 0

    by_action = {}
    for event in corridor.refined_events:
        by_action.setdefault(event.action_id, {})[event.phase] = event

    xfers = [by_action[action_id]["BLE_XFER"] for action_id in ["A1", "A2", "A3"]]
    for left, right in zip(xfers, xfers[1:]):
        assert left.end_ms <= right.start_ms

    assert by_action["A2"]["PREPARE_ADV_SIDE"].start_ms == by_action["A1"]["PREPARE_CONNECT_SIDE"].start_ms
    assert by_action["A2"]["PREPARE_ADV_SIDE"].start_ms < by_action["A1"]["BLE_XFER"].start_ms
    assert by_action["A2"]["PREPARE_CONNECT_SIDE"].start_ms >= by_action["A1"]["BLE_SETTLE"].end_ms


def test_ble_micro_validator_rejects_subscribe_like_adv_overlap_by_default() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "connect",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:switchbot:curtain_1", "device_id": "ble:switchbot:curtain_1"},
                "marker_hints": ["BLE_CONNECT"],
                "exec": {"kind": "ha_service_call", "service": "connect"},
            },
            {
                "action_id": "A2",
                "type": "subscribe",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:switchbot:curtain_2", "device_id": "ble:switchbot:curtain_2"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "service": "subscribe"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2"],
    )
    action_lookup = {action["action_id"]: action for action in target.vdev_actions}
    policy = BLEMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1)
    invalid = [
        BLEMicroEvent("A1", "PREPARE_ADV_SIDE", 0, 40),
        BLEMicroEvent("A1", "PREPARE_CONNECT_SIDE", 40, 120),
        BLEMicroEvent("A1", "BLE_XFER", 120, 420),
        BLEMicroEvent("A1", "BLE_SETTLE", 420, 500),
        BLEMicroEvent("A2", "PREPARE_ADV_SIDE", 120, 150),
        BLEMicroEvent("A2", "PREPARE_CONNECT_SIDE", 500, 620),
        BLEMicroEvent("A2", "BLE_XFER", 620, 760),
        BLEMicroEvent("A2", "BLE_SETTLE", 760, 820),
    ]
    verdict = validate_refined_corridor(["A1", "A2"], invalid, action_lookup, policy)
    assert not verdict.passed
    assert not verdict.type_constraints_ok


def test_ble_micro_validator_allows_whitelisted_esphome_connect_to_subscribe_adv_overlap() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "connect",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:air_node_1", "device_id": "ble:esphome:air_node_1"},
                "marker_hints": ["BLE_CONNECT"],
                "exec": {"kind": "ha_service_call", "service": "connect"},
            },
            {
                "action_id": "A2",
                "type": "subscribe",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:relay_node_1", "device_id": "ble:esphome:relay_node_1"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "service": "subscribe"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2"],
    )
    action_lookup = {action["action_id"]: action for action in target.vdev_actions}
    policy = BLEMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1)
    valid = [
        BLEMicroEvent("A1", "PREPARE_ADV_SIDE", 0, 40),
        BLEMicroEvent("A1", "PREPARE_CONNECT_SIDE", 40, 120),
        BLEMicroEvent("A1", "BLE_XFER", 120, 420),
        BLEMicroEvent("A1", "BLE_SETTLE", 420, 500),
        BLEMicroEvent("A2", "PREPARE_ADV_SIDE", 120, 150),
        BLEMicroEvent("A2", "PREPARE_CONNECT_SIDE", 500, 620),
        BLEMicroEvent("A2", "BLE_XFER", 620, 760),
        BLEMicroEvent("A2", "BLE_SETTLE", 760, 820),
    ]
    verdict = validate_refined_corridor(["A1", "A2"], valid, action_lookup, policy)
    assert verdict.passed


def test_ble_micro_refiner_skips_same_device_corridor_when_policy_blocks_overlap() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "read_status",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:shared_sensor", "device_id": "ble:xiaomi_ble:shared_sensor"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_status"},
            },
            {
                "action_id": "A2",
                "type": "read_sensor",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:shared_sensor", "device_id": "ble:xiaomi_ble:shared_sensor"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
            {
                "action_id": "A3",
                "type": "status",
                "protocol": "CLOUD",
                "exec": {"kind": "ha_service_call"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2", "A3"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
            Batch(batch_id="batch_002", parallel_groups=[["A3"]]),
        ],
        meta={},
    )
    refiner = ConservativeBLEMicroRefiner(policy=BLEMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=target, plan=plan)
    assert not result.selected_corridors


def test_ble_micro_refiner_does_not_pull_adv_prepare_to_connect_anchor_for_non_whitelisted_source() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "read_sensor",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:air_node_1", "device_id": "ble:esphome:air_node_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
            {
                "action_id": "A2",
                "type": "read_status",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:relay_node_1", "device_id": "ble:esphome:relay_node_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_status"},
            },
            {
                "action_id": "A3",
                "type": "read_sensor",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:sensor_1", "device_id": "ble:xiaomi_ble:sensor_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2", "A3"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
            Batch(batch_id="batch_002", parallel_groups=[["A3"]]),
        ],
        meta={},
    )
    refiner = ConservativeBLEMicroRefiner(policy=BLEMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=target, plan=plan)
    corridor = result.selected_corridors[0]
    by_action = {}
    for event in corridor.refined_events:
        by_action.setdefault(event.action_id, {})[event.phase] = event
    assert by_action["A2"]["PREPARE_ADV_SIDE"].start_ms == by_action["A1"]["BLE_XFER"].start_ms


def test_estimate_plan_latency_ms_handles_mixed_batches() -> None:
    latency = estimate_plan_latency_ms(_plan(), _target())
    assert latency > 0


def test_ble_micro_refiner_uses_profile_specific_thresholds_and_splits_session_chain() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "read_status",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:sensor_1", "device_id": "ble:xiaomi_ble:sensor_1"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_status"},
            },
            {
                "action_id": "A2",
                "type": "read_sensor",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:xiaomi_ble:sensor_2", "device_id": "ble:xiaomi_ble:sensor_2"},
                "marker_hints": ["BLE_OP", "BLE_GATT_OP"],
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
            {
                "action_id": "A3",
                "type": "connect",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:node_1", "device_id": "ble:esphome:node_1"},
                "marker_hints": ["BLE_CONNECT"],
                "exec": {"kind": "ha_service_call", "service": "connect"},
            },
            {
                "action_id": "A4",
                "type": "subscribe",
                "protocol": "BLE",
                "target_kind": "ble_device",
                "target": {"id": "ble:esphome:node_2", "device_id": "ble:esphome:node_2"},
                "marker_hints": ["BLE_OP"],
                "exec": {"kind": "ha_service_call", "service": "subscribe"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
            Batch(batch_id="batch_002", parallel_groups=[["A3"]]),
            Batch(batch_id="batch_003", parallel_groups=[["A4"]]),
        ],
        meta={},
    )
    refiner = ConservativeBLEMicroRefiner(
        policy=BLEMicroRefinementPolicy(
            min_corridor_length=99,
            min_corridor_latency_ms=99999,
            read_like_min_corridor_length=2,
            read_like_min_corridor_latency_ms=1,
            session_chain_min_corridor_length=2,
            session_chain_min_corridor_latency_ms=1,
        )
    )
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=target, plan=plan)
    assert len(result.selected_corridors) == 2
    assert sorted(row.corridor.profile_class for row in result.selected_corridors) == ["read_like", "session_chain"]
