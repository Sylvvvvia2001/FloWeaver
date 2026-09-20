from __future__ import annotations

from optimizer.api_micro_refinement import APIBatchStep, APIMicroEvent, APIMicroRefinementPolicy
from optimizer.ble_micro_refinement import BLEMicroEvent, BLEMicroRefinementPolicy
from optimizer.combined_micro_refinement import (
    CombinedCandidate,
    CombinedMicroRefinementPolicy,
    resolve_combined_candidates,
    validate_combined_candidates,
)
from dsl.contracts import Batch, ExecutionPlan, OptimizationTarget


def _target(actions: list[dict]) -> OptimizationTarget:
    return OptimizationTarget(
        meta={},
        source_scope={},
        vdev_actions=actions,
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[action["action_id"] for action in actions],
    )


def _plan(batch_ids: list[str], action_ids: list[str]) -> ExecutionPlan:
    return ExecutionPlan(
        ordered_batches=[
            Batch(batch_id=batch_id, parallel_groups=[[action_id]])
            for batch_id, action_id in zip(batch_ids, action_ids)
        ],
        meta={},
    )


def _ble_candidate(*, save_ms: int, overlap_xfer: bool = False) -> CombinedCandidate:
    if overlap_xfer:
        events = [
            BLEMicroEvent("A1", "PREPARE_ADV_SIDE", 0, 60),
            BLEMicroEvent("A1", "PREPARE_CONNECT_SIDE", 60, 120),
            BLEMicroEvent("A1", "BLE_XFER", 120, 520),
            BLEMicroEvent("A1", "BLE_SETTLE", 520, 620),
            BLEMicroEvent("A2", "PREPARE_ADV_SIDE", 220, 280),
            BLEMicroEvent("A2", "PREPARE_CONNECT_SIDE", 620, 680),
            BLEMicroEvent("A2", "BLE_XFER", 480, 860),
            BLEMicroEvent("A2", "BLE_SETTLE", 860, 980),
        ]
    else:
        events = [
            BLEMicroEvent("A1", "PREPARE_ADV_SIDE", 0, 60),
            BLEMicroEvent("A1", "PREPARE_CONNECT_SIDE", 60, 120),
            BLEMicroEvent("A1", "BLE_XFER", 120, 500),
            BLEMicroEvent("A1", "BLE_SETTLE", 500, 600),
            BLEMicroEvent("A2", "PREPARE_ADV_SIDE", 200, 260),
            BLEMicroEvent("A2", "PREPARE_CONNECT_SIDE", 600, 660),
            BLEMicroEvent("A2", "BLE_XFER", 660, 1040),
            BLEMicroEvent("A2", "BLE_SETTLE", 1040, 1200),
        ]
    return CombinedCandidate(
        source="BLE",
        corridor_id="corridor_ble",
        batch_ids=["batch_000", "batch_001"],
        action_ids=["A1", "A2"],
        latency_saved_ms=save_ms,
        validation_passed=True,
        payload={
            "original_latency_ms": 1500,
            "refined_latency_ms": 1200 if not overlap_xfer else 980,
            "events": events,
            "owner_ids": ["A1", "A2"],
        },
    )


def _api_candidate(*, save_ms: int, overlap_request: bool = False) -> CombinedCandidate:
    steps = [
        APIBatchStep(
            step_id="batch_002",
            batch_id="batch_002",
            protocol="CLOUD",
            phase_kind="CLOUD",
            capability_class="cloud_read",
            action_ids=["A3"],
            latency_ms=350,
            host_key="tuya",
            bucket_key="lights",
            session_key="tuya",
            endpoint_key="light.a",
            has_backoff_wait=False,
        ),
        APIBatchStep(
            step_id="batch_003",
            batch_id="batch_003",
            protocol="CLOUD",
            phase_kind="CLOUD",
            capability_class="cloud_read",
            action_ids=["A4"],
            latency_ms=350,
            host_key="tuya",
            bucket_key="lights",
            session_key="tuya",
            endpoint_key="light.b",
            has_backoff_wait=False,
        ),
    ]
    right_request_start = 180 if overlap_request else 260
    events = [
        APIMicroEvent("batch_002", "CLOUD_AUTH_CHECK", 0, 10),
        APIMicroEvent("batch_002", "CLOUD_RATE_BUDGET_CHECK", 10, 20),
        APIMicroEvent("batch_002", "API_PREPARE", 20, 50),
        APIMicroEvent("batch_002", "API_SESSION_READY", 50, 60),
        APIMicroEvent("batch_002", "CLOUD_REQUEST_SEND", 60, 100),
        APIMicroEvent("batch_002", "API_RESPONSE_RECV", 100, 140),
        APIMicroEvent("batch_002", "CLOUD_BACKOFF_WAIT", 140, 140),
        APIMicroEvent("batch_002", "API_PARSE_NORMALIZE", 140, 180),
        APIMicroEvent("batch_002", "API_AGGREGATE", 180, 200),
        APIMicroEvent("batch_002", "CLOUD_BATCH_GROUP_COMMIT", 200, 220),
        APIMicroEvent("batch_002", "HA_STATE_WRITE", 220, 250),
        APIMicroEvent("batch_003", "CLOUD_AUTH_CHECK", 90, 100),
        APIMicroEvent("batch_003", "CLOUD_RATE_BUDGET_CHECK", 100, 110),
        APIMicroEvent("batch_003", "API_PREPARE", 110, 140),
        APIMicroEvent("batch_003", "API_SESSION_READY", 250, 260),
        APIMicroEvent("batch_003", "CLOUD_REQUEST_SEND", right_request_start, right_request_start + 40),
        APIMicroEvent("batch_003", "API_RESPONSE_RECV", right_request_start + 40, right_request_start + 80),
        APIMicroEvent("batch_003", "CLOUD_BACKOFF_WAIT", right_request_start + 80, right_request_start + 80),
        APIMicroEvent("batch_003", "API_PARSE_NORMALIZE", right_request_start + 80, right_request_start + 120),
        APIMicroEvent("batch_003", "API_AGGREGATE", right_request_start + 120, right_request_start + 140),
        APIMicroEvent("batch_003", "CLOUD_BATCH_GROUP_COMMIT", right_request_start + 140, right_request_start + 160),
        APIMicroEvent("batch_003", "HA_STATE_WRITE", right_request_start + 160, right_request_start + 190),
    ]
    return CombinedCandidate(
        source="API",
        corridor_id="corridor_api",
        batch_ids=["batch_002", "batch_003"],
        action_ids=["A3", "A4"],
        latency_saved_ms=save_ms,
        validation_passed=True,
        payload={
            "original_latency_ms": 700,
            "refined_latency_ms": 450 if not overlap_request else right_request_start + 190,
            "events": events,
            "steps": steps,
            "owner_ids": ["batch_002", "batch_003"],
        },
    )


def test_combined_refiner_accepts_disjoint_ble_and_api_corridors() -> None:
    ble = _ble_candidate(save_ms=300)
    api = _api_candidate(save_ms=250)
    decision = resolve_combined_candidates([ble], [api], CombinedMicroRefinementPolicy())
    assert [row.corridor_id for row in decision.accepted] == ["corridor_api", "corridor_ble"]
    assert not decision.rejected
    assert not decision.conflicts


def test_combined_refiner_rejects_overlapping_corridor_by_higher_saving() -> None:
    ble = CombinedCandidate(
        source="BLE",
        corridor_id="corridor_ble",
        batch_ids=["batch_000", "batch_001"],
        action_ids=["A1", "A2"],
        latency_saved_ms=120,
        validation_passed=True,
        payload={},
    )
    api = CombinedCandidate(
        source="API",
        corridor_id="corridor_api",
        batch_ids=["batch_001", "batch_002"],
        action_ids=["A2", "A3"],
        latency_saved_ms=90,
        validation_passed=True,
        payload={},
    )
    decision = resolve_combined_candidates([ble], [api], CombinedMicroRefinementPolicy())
    assert [row.corridor_id for row in decision.accepted] == ["corridor_ble"]
    assert [row.corridor_id for row in decision.rejected] == ["corridor_api"]
    assert decision.conflicts[0]["reasons"] == ["batch_overlap", "action_overlap"]


def test_combined_refiner_rejects_adjacent_ble_corridor_with_same_session_domain() -> None:
    left = CombinedCandidate(
        source="BLE",
        corridor_id="corridor_left",
        batch_ids=["batch_000", "batch_001"],
        action_ids=["A1", "A2"],
        latency_saved_ms=120,
        validation_passed=True,
        payload={"resource_domains": {"session_groups": ["shared_session"], "device_ids": []}},
    )
    right = CombinedCandidate(
        source="BLE",
        corridor_id="corridor_right",
        batch_ids=["batch_003", "batch_004"],
        action_ids=["A3", "A4"],
        latency_saved_ms=100,
        validation_passed=True,
        payload={"resource_domains": {"session_groups": ["shared_session"], "device_ids": []}},
    )
    decision = resolve_combined_candidates([left, right], [], CombinedMicroRefinementPolicy())
    assert [row.corridor_id for row in decision.accepted] == ["corridor_left"]
    assert [row.corridor_id for row in decision.rejected] == ["corridor_right"]
    assert "ble_resource_domain_adjacent" in decision.conflicts[0]["reasons"]


def test_combined_validator_simulates_disjoint_corridors_and_preserves_projection() -> None:
    target = _target(
        [
            {"action_id": "A1", "protocol": "BLE", "action_kind": "read_sensor"},
            {"action_id": "A2", "protocol": "BLE", "action_kind": "read_sensor"},
            {"action_id": "A3", "protocol": "CLOUD", "action_kind": "status", "exec": {"kind": "ha_service_call"}},
            {"action_id": "A4", "protocol": "CLOUD", "action_kind": "status", "exec": {"kind": "ha_service_call"}},
        ]
    )
    plan = _plan(["batch_000", "batch_001", "batch_002", "batch_003"], ["A1", "A2", "A3", "A4"])
    validation, events, combined_saved_ms = validate_combined_candidates(
        plan=plan,
        target=target,
        accepted_candidates=[_ble_candidate(save_ms=300), _api_candidate(save_ms=250)],
        rejected_candidates=[],
        conflicts=[],
        ble_policy=BLEMicroRefinementPolicy(),
        api_policy=APIMicroRefinementPolicy(),
        combined_policy=CombinedMicroRefinementPolicy(),
    )
    assert validation.passed
    assert validation.simulated_total_ms == 1650
    assert combined_saved_ms == 550
    assert len(events) > 0


def test_combined_validator_catches_ble_xfer_overlap() -> None:
    target = _target(
        [
            {"action_id": "A1", "protocol": "BLE", "action_kind": "read_sensor"},
            {"action_id": "A2", "protocol": "BLE", "action_kind": "read_sensor"},
        ]
    )
    plan = _plan(["batch_000", "batch_001"], ["A1", "A2"])
    validation, _, _ = validate_combined_candidates(
        plan=plan,
        target=target,
        accepted_candidates=[_ble_candidate(save_ms=520, overlap_xfer=True)],
        rejected_candidates=[],
        conflicts=[],
        ble_policy=BLEMicroRefinementPolicy(),
        api_policy=APIMicroRefinementPolicy(),
        combined_policy=CombinedMicroRefinementPolicy(),
    )
    assert not validation.passed
    assert not validation.ble_constraints_ok
    assert "ble_xfer_global_limit_exceeded" in validation.reasons


def test_combined_validator_catches_api_request_overlap() -> None:
    target = _target(
        [
            {"action_id": "A3", "protocol": "CLOUD", "action_kind": "status", "exec": {"kind": "ha_service_call"}},
            {"action_id": "A4", "protocol": "CLOUD", "action_kind": "status", "exec": {"kind": "ha_service_call"}},
        ]
    )
    plan = _plan(["batch_002", "batch_003"], ["A3", "A4"])
    validation, _, _ = validate_combined_candidates(
        plan=plan,
        target=target,
        accepted_candidates=[_api_candidate(save_ms=330, overlap_request=True)],
        rejected_candidates=[],
        conflicts=[],
        ble_policy=BLEMicroRefinementPolicy(),
        api_policy=APIMicroRefinementPolicy(),
        combined_policy=CombinedMicroRefinementPolicy(),
    )
    assert not validation.passed
    assert not validation.api_constraints_ok
    assert "api_request_before_previous_write:batch_002->batch_003" in validation.reasons or any(
        reason.endswith(":cloud_request_send_overlap") for reason in validation.reasons
    )
