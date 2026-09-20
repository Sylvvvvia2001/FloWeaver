from __future__ import annotations

from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget
from optimizer.api_micro_refinement import (
    CLOUD_MICRO_PHASES,
    LOCAL_HTTP_MICRO_PHASES,
    MQTT_MICRO_PHASES,
    APIMicroRefinementPolicy,
    ConservativeAPIMicroRefiner,
)


def _target() -> OptimizationTarget:
    return OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={"files": ["/tmp/demo.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:light.room_1.status", "endpoint": "tuya:light.room_1.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "status",
                    "provider": "tuya",
                    "data_template": {
                        "endpoint": "tuya:light.room_1.status",
                        "endpoint_group_key": "lights_status",
                        "host_group_key": "tuya",
                    },
                },
            },
            {
                "action_id": "A2",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:light.room_2.status", "endpoint": "tuya:light.room_2.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "status",
                    "provider": "tuya",
                    "data_template": {
                        "endpoint": "tuya:light.room_2.status",
                        "endpoint_group_key": "lights_status",
                        "host_group_key": "tuya",
                    },
                },
            },
            {
                "action_id": "A3",
                "type": "get_state",
                "protocol": "LOCAL",
                "target_kind": "local_endpoint",
                "target": {"id": "hue:bridge_1:room_1", "endpoint": "hue:bridge_1:room_1"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "get_state",
                    "provider": "hue_local",
                    "data_template": {
                        "endpoint": "hue:bridge_1:room_1",
                        "endpoint_group_key": "bridge_state",
                        "host_group_key": "hue_bridge_1",
                    },
                },
            },
            {
                "action_id": "A4",
                "type": "get_state",
                "protocol": "LOCAL",
                "target_kind": "local_endpoint",
                "target": {"id": "hue:bridge_1:room_2", "endpoint": "hue:bridge_1:room_2"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "get_state",
                    "provider": "hue_local",
                    "data_template": {
                        "endpoint": "hue:bridge_1:room_2",
                        "endpoint_group_key": "bridge_state",
                        "host_group_key": "hue_bridge_1",
                    },
                },
            },
            {
                "action_id": "A5",
                "type": "read_last_message",
                "protocol": "LOCAL",
                "target_kind": "mqtt_topic",
                "target": {"id": "mqtt:topic.a", "endpoint": "mqtt:topic.a"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "read_last_message",
                    "provider": "mqtt",
                    "data_template": {"endpoint": "mqtt:topic.a"},
                },
            },
            {
                "action_id": "A6",
                "type": "read_last_message",
                "protocol": "LOCAL",
                "target_kind": "mqtt_topic",
                "target": {"id": "mqtt:topic.b", "endpoint": "mqtt:topic.b"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "read_last_message",
                    "provider": "mqtt",
                    "data_template": {"endpoint": "mqtt:topic.b"},
                },
            },
            {
                "action_id": "A7",
                "type": "publish",
                "protocol": "HA",
                "target_kind": "state_write",
                "target": {"id": "sensor.demo"},
                "exec": {"kind": "ha_service_call", "service": "publish"},
            },
        ],
        target_anchors={},
        entrypoint={"kind": "function", "name": "demo"},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
    )


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
            Batch(batch_id="batch_002", parallel_groups=[["A3"]]),
            Batch(batch_id="batch_003", parallel_groups=[["A4"]]),
            Batch(batch_id="batch_004", parallel_groups=[["A5"]]),
            Batch(batch_id="batch_005", parallel_groups=[["A6"]]),
            Batch(batch_id="batch_006", parallel_groups=[["A7"]]),
        ],
        meta={},
    )


def test_api_micro_refiner_selects_cloud_and_local_http_corridors_only() -> None:
    refiner = ConservativeAPIMicroRefiner(policy=APIMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())

    assert len(result.selected_corridors) == 2
    assert result.selected_corridors[0].corridor.protocol == "CLOUD"
    assert result.selected_corridors[0].corridor.phase_kind == "CLOUD"
    assert result.selected_corridors[1].corridor.protocol == "LOCAL"
    assert result.selected_corridors[1].corridor.phase_kind == "LOCAL_HTTP"


def test_api_micro_refiner_uses_expected_cloud_and_local_phase_models() -> None:
    refiner = ConservativeAPIMicroRefiner(policy=APIMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())

    cloud = result.selected_corridors[0]
    local = result.selected_corridors[1]

    phases_by_step = {}
    for event in cloud.refined_events:
        phases_by_step.setdefault(event.step_id, []).append(event.phase)
    assert phases_by_step["batch_000"] == list(CLOUD_MICRO_PHASES)
    assert phases_by_step["batch_001"] == list(CLOUD_MICRO_PHASES)

    phases_by_step = {}
    for event in local.refined_events:
        phases_by_step.setdefault(event.step_id, []).append(event.phase)
    assert phases_by_step["batch_002"] == list(LOCAL_HTTP_MICRO_PHASES)
    assert phases_by_step["batch_003"] == list(LOCAL_HTTP_MICRO_PHASES)

    assert list(MQTT_MICRO_PHASES) == ["MQTT_LAST_MSG_READ", "MQTT_CACHE_PARSE", "HA_STATE_WRITE"]


def test_local_http_overlap_is_prepare_only_and_request_send_stays_serialized() -> None:
    refiner = ConservativeAPIMicroRefiner(policy=APIMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())
    local = result.selected_corridors[1]

    assert local.validation.passed

    by_step = {}
    for event in local.refined_events:
        by_step.setdefault(event.step_id, {})[event.phase] = event

    left = by_step["batch_002"]
    right = by_step["batch_003"]

    assert right["LOCAL_ENDPOINT_RESOLVE"].start_ms < left["HA_STATE_WRITE"].end_ms
    assert right["LOCAL_SESSION_READY"].end_ms <= left["LOCAL_RESPONSE_RECV"].end_ms
    assert right["LOCAL_REQUEST_SEND"].start_ms >= left["HA_STATE_WRITE"].end_ms


def test_cloud_overlap_is_auth_budget_prepare_only_and_request_send_stays_serialized() -> None:
    refiner = ConservativeAPIMicroRefiner(policy=APIMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())
    cloud = result.selected_corridors[0]

    assert cloud.validation.passed

    by_step = {}
    for event in cloud.refined_events:
        by_step.setdefault(event.step_id, {})[event.phase] = event

    left = by_step["batch_000"]
    right = by_step["batch_001"]

    assert right["CLOUD_AUTH_CHECK"].start_ms < left["HA_STATE_WRITE"].end_ms
    assert right["API_PREPARE"].end_ms <= left["API_RESPONSE_RECV"].end_ms
    assert right["API_SESSION_READY"].start_ms >= left["HA_STATE_WRITE"].end_ms
    assert right["CLOUD_REQUEST_SEND"].start_ms >= left["HA_STATE_WRITE"].end_ms


def test_cloud_backoff_barrier_blocks_corridor_selection() -> None:
    target = _target()
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="batch_000", parallel_groups=[["A1"]], constraints=["BACKOFF"]),
            Batch(batch_id="batch_001", parallel_groups=[["A2"]]),
        ],
        meta={},
    )
    refiner = ConservativeAPIMicroRefiner(policy=APIMicroRefinementPolicy(min_corridor_length=2, min_corridor_latency_ms=1))
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=target, plan=plan)
    assert not result.selected_corridors


def test_api_micro_refiner_uses_lane_specific_thresholds_for_local_http() -> None:
    refiner = ConservativeAPIMicroRefiner(
        policy=APIMicroRefinementPolicy(
            min_corridor_length=99,
            min_corridor_latency_ms=99999,
            cloud_read_min_corridor_length=99,
            cloud_read_min_corridor_latency_ms=99999,
            local_http_read_min_corridor_length=2,
            local_http_read_min_corridor_latency_ms=1,
        )
    )
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=_target(), plan=_plan())
    assert len(result.selected_corridors) == 1
    assert result.selected_corridors[0].corridor.capability_class == "local_http_read"


def test_api_micro_refiner_splits_cloud_read_and_cloud_control_capability_slices() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "demo"},
        source_scope={},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:light.room_1.status", "endpoint": "tuya:light.room_1.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "status",
                    "provider": "tuya",
                    "data_template": {"endpoint": "tuya:light.room_1.status", "host_group_key": "tuya"},
                },
            },
            {
                "action_id": "A2",
                "type": "status",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:light.room_2.status", "endpoint": "tuya:light.room_2.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "status",
                    "provider": "tuya",
                    "data_template": {"endpoint": "tuya:light.room_2.status", "host_group_key": "tuya"},
                },
            },
            {
                "action_id": "A3",
                "type": "set_temperature",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:climate.room_1", "endpoint": "tuya:climate.room_1"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "set_temperature",
                    "provider": "tuya",
                    "data_template": {"endpoint": "tuya:climate.room_1", "host_group_key": "tuya"},
                },
            },
            {
                "action_id": "A4",
                "type": "set_temperature",
                "protocol": "CLOUD",
                "target_kind": "cloud_endpoint",
                "target": {"id": "tuya:climate.room_2", "endpoint": "tuya:climate.room_2"},
                "exec": {
                    "kind": "ha_service_call",
                    "service": "set_temperature",
                    "provider": "tuya",
                    "data_template": {"endpoint": "tuya:climate.room_2", "host_group_key": "tuya"},
                },
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
    refiner = ConservativeAPIMicroRefiner(
        policy=APIMicroRefinementPolicy(
            min_corridor_length=99,
            min_corridor_latency_ms=99999,
            cloud_read_min_corridor_length=2,
            cloud_read_min_corridor_latency_ms=1,
            cloud_control_min_corridor_length=2,
            cloud_control_min_corridor_latency_ms=1,
        )
    )
    result = refiner.refine_case(vdev_id="demo", case_name="Demo", target=target, plan=plan)
    assert len(result.selected_corridors) == 2
    assert [row.corridor.capability_class for row in result.selected_corridors] == ["cloud_read", "cloud_control"]
