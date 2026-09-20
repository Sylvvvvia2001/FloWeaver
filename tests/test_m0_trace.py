from dsl.contracts import Event, OptimizationTarget, Trace
from optimizer.m0_observation import ObservationEngine
from runtime.trace import compare_traces


def test_tolerant_equal_for_commutable_state_write_order() -> None:
    base = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.a", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.b", params_abst={}, phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    opt = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.b", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.a", params_abst={}, phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )

    diff = compare_traces(base, opt)
    assert diff.strict_equal is False
    assert diff.tolerant_equal is True


def test_observation_whitelist_enables_custom_commutation() -> None:
    target = OptimizationTarget(
        meta={},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"required_state_writes": []},
        entrypoint={},
        objectives={},
        constraints={},
        validation={
            "observation": {
                "canonicalization_version": "v2",
                "equivalence_whitelist": [{"op": "BLE_OP", "policy": "commute"}],
            }
        },
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )
    engine = ObservationEngine.from_optimization_target(target)

    base = Trace(
        events=[
            Event(ts=1.0, provider="BLE", op="BLE_OP", target="ble:dev1", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="BLE", op="BLE_OP", target="ble:dev2", params_abst={}, phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    opt = Trace(
        events=[
            Event(ts=1.0, provider="BLE", op="BLE_OP", target="ble:dev2", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="BLE", op="BLE_OP", target="ble:dev1", params_abst={}, phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )

    diff = engine.compare(base, opt)
    canonical = engine.canonicalize(base)
    assert diff.tolerant_equal is True
    assert diff.meta["canonicalization_version"] == "v2"
    assert isinstance(diff.meta.get("config_hash"), str) and len(diff.meta["config_hash"]) == 16
    assert canonical.meta["canonicalization_version"] == "v2"
    assert all(event.op == "BLE_GATT_OP" for event in canonical.events)


def test_structured_whitelist_group_key_blocks_cross_group_reorder() -> None:
    target = OptimizationTarget(
        meta={},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"required_state_writes": []},
        entrypoint={},
        objectives={},
        constraints={},
        validation={
            "observation": {
                "equivalence_whitelist": [{"op": "CLOUD_HTTP_CALL", "group_key": "endpoint", "policy": "commute"}],
            }
        },
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )
    engine = ObservationEngine.from_optimization_target(target)

    base = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/a", params_abst={"endpoint": "/a"}, phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/b", params_abst={"endpoint": "/b"}, phase="RUNTIME"),
        ],
        meta={},
    )
    opt = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/b", params_abst={"endpoint": "/b"}, phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/a", params_abst={"endpoint": "/a"}, phase="RUNTIME"),
        ],
        meta={},
    )
    diff = engine.compare(base, opt)
    assert diff.tolerant_equal is False


def test_required_state_writes_use_dedicated_anchor_only() -> None:
    target = OptimizationTarget(
        meta={},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"}}],
        target_anchors={
            "entities": ["sensor.read_only", "sensor.vdev"],
            "required_state_writes": ["sensor.vdev"],
        },
        entrypoint={},
        objectives={},
        constraints={},
        validation={"observation": {"semantic_ops": ["STATE_WRITE"]}},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )
    engine = ObservationEngine.from_optimization_target(target)
    trace = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    contract = engine.assert_contract(trace)
    assert contract["passed"] is True
    assert contract["missing_required_state_writes"] == []
    assert isinstance(contract["trace_compare_config_hash"], str)


def test_contract_supports_final_state_and_op_count_bounds_with_aliases() -> None:
    target = OptimizationTarget(
        meta={},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"}}],
        target_anchors={"required_state_writes": ["sensor.vdev"]},
        entrypoint={},
        objectives={},
        constraints={},
        validation={
            "observation": {
                "semantic_ops": ["STATE_WRITE", "CLOUD_HTTP_CALL"],
                "required_final_state": {"sensor.vdev": {"state": "on"}},
                "op_count_bounds": {"CLOUD_HTTP_CALL": {"max": 1}, "STATE_WRITE": {"min": 1}},
            }
        },
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )
    engine = ObservationEngine.from_optimization_target(target)

    bad_trace = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_CALL", target="/v1/a", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/b", params_abst={}, phase="RUNTIME"),
            Event(ts=3.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "off"}, phase="RUNTIME"),
        ],
        meta={},
    )
    bad_contract = engine.assert_contract(bad_trace)
    assert bad_contract["passed"] is False
    assert len(bad_contract["final_state_mismatches"]) == 1
    assert len(bad_contract["op_count_violations"]) == 1

    good_trace = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_CALL", target="/v1/a", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    good_contract = engine.assert_contract(good_trace)
    assert good_contract["passed"] is True
    assert good_contract["final_state_mismatches"] == []
    assert good_contract["op_count_violations"] == []


def test_contract_supports_factor_upper_bound_against_baseline() -> None:
    target = OptimizationTarget(
        meta={},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "ha_service_call", "domain": "demo", "service": "run"}}],
        target_anchors={"required_state_writes": ["sensor.vdev"], "anchor_ops": ["BLE_OP", "UNKNOWN_HINT"]},
        entrypoint={},
        objectives={},
        constraints={},
        validation={
            "observation": {
                "semantic_ops": ["STATE_WRITE", "CLOUD_HTTP_CALL"],
                "op_count_factor_upper": {"CLOUD_HTTP_CALL": 1.5},
            }
        },
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )
    engine = ObservationEngine.from_optimization_target(target)
    assert "UNKNOWN_HINT" in engine.schema.ignored_anchor_ops

    baseline = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", params_abst={}, phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/b", params_abst={}, phase="RUNTIME"),
            Event(ts=3.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    contract = engine.assert_contract(optimized, baseline_trace=baseline)
    assert contract["passed"] is False
    assert len(contract["op_count_factor_violations"]) == 1
