import pytest

from dsl.contracts import Batch, DependencyEdge, ExecutionPlan, MSSU, OptimizationTarget, SoftConstraint, TypedDAG
from optimizer.m5_scheduler import CrossProtocolScheduler, DerivedConstraintPolicy


def _target(actions: list[dict] | None = None, *, objectives: dict | None = None, validation: dict | None = None) -> OptimizationTarget:
    vdev_actions = actions or [
        {
            "action_id": "A1",
            "protocol": "BLE",
            "critical": True,
            "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
        },
        {
            "action_id": "A2",
            "protocol": "HA",
            "critical": True,
            "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
        },
    ]
    return OptimizationTarget(
        meta={"vdev_id": "sched_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=vdev_actions,
        target_anchors={},
        entrypoint={},
        objectives=objectives or {},
        constraints={},
        validation=validation or {},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[str(action["action_id"]) for action in vdev_actions if action.get("critical")],
    )


def test_scheduler_fails_fast_on_hard_action_cycle() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[
            DependencyEdge(src_mssu="m1", dst_mssu="m2", kind="HARD_CONTROL"),
            DependencyEdge(src_mssu="m2", dst_mssu="m1", kind="HARD_CONTROL"),
        ],
        soft_constraints=[],
        resources={},
    )

    with pytest.raises(ValueError, match="hard-edge cycle"):
        CrossProtocolScheduler().schedule(dag, optimization_target=_target())


def test_scheduler_aggregates_multiple_fallbacks_per_constraint_kind() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(kind="MIN_GAP", scope=["m1", "m2"], fallback="preserve_action_order"),
            SoftConstraint(kind="MIN_GAP", scope=["m1", "m2"], fallback="reduce_parallelism"),
        ],
        resources={},
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=_target())
    assert plan.ordered_batches
    fallback = plan.ordered_batches[0].fallback
    assert fallback
    assert {row["kind"] for row in fallback} == {"MIN_GAP"}
    assert sorted(row["action"] for row in fallback) == ["preserve_action_order", "reduce_parallelism"]


def test_scheduler_parses_protocol_guard_expressions_and_or() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="RATE_LIMIT",
                scope=["m1", "m2"],
                params={"max_qps": 2.0},
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="reduce_qps_and_parallelism",
            ),
            SoftConstraint(
                kind="NO_OVERLAP",
                scope=["m1", "m2"],
                params={"resource": "BLE_AIRTIME"},
                guard="ble_timeout_rate_high OR ble_overlap_risk_high",
                fallback="set_ble_parallelism_to_1",
            ),
        ],
        resources={},
    )

    target = OptimizationTarget(
        meta={"vdev_id": "sched_test_guard"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ],
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2"],
    )

    plan_low_429 = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=target,
        runtime_metrics={
            "latency_budget_allows_batching": True,
            "risk_indicators": {"recent_429_rate": 0.01, "ble_timeout_rate": 0.0, "ble_overlap_risk": 0.0},
        },
    )
    assert float(plan_low_429.meta["derived_policy"]["max_qps"]) <= 2.0
    assert plan_low_429.meta["derived_policy"]["triggered_fallbacks"] == []

    plan_high_429 = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=target,
        runtime_metrics={
            "latency_budget_allows_batching": True,
            "risk_indicators": {"recent_429_rate": 0.3, "ble_timeout_rate": 0.0, "ble_overlap_risk": 0.0},
        },
    )

    assert float(plan_high_429.meta["derived_policy"]["max_qps"]) < float(plan_low_429.meta["derived_policy"]["max_qps"])
    assert plan_high_429.meta["derived_policy"]["triggered_fallbacks"] == [
        {
            "kind": "RATE_LIMIT",
            "scope": ["A1", "A2"],
            "fallback": "reduce_qps_and_parallelism",
            "params": {"max_qps": 2.0},
        }
    ]


def test_scheduler_keeps_batch_rules_when_allow_guard_is_active() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m1", "m2"],
                params={"group_key": "endpoint", "max_batch_size": 4, "max_wait_ms": 80, "idempotent_only": True},
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="disable_batching_use_singleton_calls",
            ),
            SoftConstraint(
                kind="SAME_SESSION_GROUP",
                scope=["m1", "m2"],
                params={"group_key": "host", "reuse_window_ms": 10000},
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="disable_batching_use_singleton_calls",
            ),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.status"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.status"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ]
    )

    plan = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=target,
        runtime_metrics={
            "latency_budget_allows_batching": True,
            "risk_indicators": {"recent_429_rate": 0.01},
        },
    )

    assert len(plan.ordered_batches) == 1
    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"]]
    assert plan.meta["policy_snapshot"]["batch_policy"]["rules"] == [
        {"scope": ["A1", "A2"], "group_key": "endpoint", "max_batch_size": 4, "max_wait_ms": 80, "idempotent_only": True}
    ]
    assert plan.meta["derived_policy"]["triggered_fallbacks"] == []
    assert plan.meta["derived_policy"]["reuse_enabled"] is True


def test_scheduler_respects_soft_order_constraint() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(kind="SOFT_ORDER", scope=["m1", "m2"], fallback="preserve_action_order"),
        ],
        resources={},
    )

    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ]
    )
    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]
    assert flat == ["A1", "A2"]
    assert len(plan.ordered_batches) == 1
    assert plan.ordered_batches[0].parallel_groups == [["A1"], ["A2"]]


def test_scheduler_projects_pair_key_hard_edges_without_cartesian_blowup() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1", "A2"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["B1", "B2"]),
        },
        hard_edges=[
            DependencyEdge(
                src_mssu="m1",
                dst_mssu="m2",
                kind="HARD_LIFECYCLE",
                justification=["rule_template:ble_pair", "pair_key:device_id"],
            )
        ],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "BLE", "critical": True, "target": {"device_id": "dev-1"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "BLE", "critical": True, "target": {"device_id": "dev-2"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "B1", "protocol": "BLE", "critical": True, "target": {"device_id": "dev-1"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b1"}},
            {"action_id": "B2", "protocol": "BLE", "critical": True, "target": {"device_id": "dev-2"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b2"}},
        ]
    )

    out, _, _, _ = scheduler._project_hard_graph(dag, scheduler._action_index(target), target)

    assert out["A1"] == {"B1"}
    assert out["A2"] == {"B2"}


def test_scheduler_min_gap_forces_separate_batches_and_emits_gap() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(kind="MIN_GAP", scope=["m1", "m2"], params={"gap_ms": 250}, fallback="preserve_action_order"),
        ],
        resources={},
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=_target())

    assert len(plan.ordered_batches) == 2
    assert plan.ordered_batches[1].rate_policy["min_gap_before_ms"] == 250
    assert plan.ordered_batches[1].rate_policy["min_gap_rules"] == [{"before": "A1", "after": "A2", "gap_ms": 250}]


def test_scheduler_min_gap_is_directional() -> None:
    pairs = {("A1", "A2"): 250}
    assert CrossProtocolScheduler._min_gap_conflict("A2", ["A1"], pairs) is True
    assert CrossProtocolScheduler._min_gap_conflict("A1", ["A2"], pairs) is False


def test_scheduler_batches_only_idempotent_same_host_actions() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m1", "m2", "m3"],
                params={"group_key": "endpoint", "max_batch_size": 4, "max_wait_ms": 80, "idempotent_only": True},
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.control"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.control"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "no",
                "target": {"endpoint": "https://other.demo.local/device.control"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"},
            },
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)
    groups = plan.ordered_batches[0].parallel_groups

    assert ["A1", "A2"] in groups
    assert ["A3"] in groups


def test_scheduler_pair_key_nonunique_scope_uses_stable_zip_pairing() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1", "A2"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["B1", "B2"]),
        },
        hard_edges=[
            DependencyEdge(
                src_mssu="m1",
                dst_mssu="m2",
                kind="HARD_LIFECYCLE",
                justification=["rule_template:host_pair", "pair_key:host"],
            )
        ],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/a"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/b"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "B1", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/c"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b1"}},
            {"action_id": "B2", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/d"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b2"}},
        ]
    )

    out, _, _, _ = scheduler._project_hard_graph(dag, scheduler._action_index(target), target)

    assert out["A1"] == {"B1"}
    assert out["A2"] == {"B2"}


def test_scheduler_serializes_unknown_protocol_and_emits_policy_snapshot() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
        ],
        objectives={"metrics": {"e2e_latency_ms": {"p95": 1200}}},
        validation={"profile_version": "ha_profile/demo", "observation": {"canonicalization_version": "v2"}},
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert len(plan.ordered_batches) == 2
    assert plan.meta["unknown_protocol_actions"] == ["A1"]
    assert plan.meta["policy_snapshot"]["versions"] == {
        "profile_version": "ha_profile/demo",
        "canonicalization_version": "v2",
    }
    assert plan.meta["policy_snapshot"]["batch_policy"]["latency_budget_ms"] == 1200


def test_scheduler_recognizes_local_lane_and_local_writeback() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A2",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_local_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
            {
                "action_id": "A3",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert plan.meta["unknown_protocol_actions"] == []
    assert plan.meta["action_lanes"]["A1"] == "LOCAL"
    assert plan.meta["action_lanes"]["A2"] == "WRITEBACK_LOCAL"
    assert plan.meta["derived_policy"]["local_limit"] >= 1
    assert plan.meta["policy_snapshot"]["budgets"]["local"] >= 1
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]
    assert flat.index("A1") < flat.index("A2") < flat.index("A3")


def test_scheduler_emits_structured_guards_and_fallbacks() -> None:
    mssu_a = MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"])
    mssu_b = MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"])
    dag = TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="RATE_LIMIT",
                scope=["m1", "m2"],
                params={"max_qps": 2.0},
                guard="recent_429_rate_high",
                fallback="reduce_qps_and_parallelism",
            ),
        ],
        resources={},
    )

    plan = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=_target(
            [
                {"action_id": "A1", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
                {"action_id": "A2", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            ]
        ),
        runtime_metrics={"risk_indicators": {"recent_429_rate": 0.2}},
    )

    batch = plan.ordered_batches[0]
    assert batch.guards == [{"kind": "RATE_LIMIT", "scope": ["A1", "A2"], "expr": "recent_429_rate_high", "enforced": True}]
    assert batch.fallback == [
        {
            "kind": "RATE_LIMIT",
            "scope": ["A1"],
            "action": "reduce_qps_and_parallelism",
            "params": {"max_qps": 2.0},
        }
    ]
    assert batch.rate_policy["adaptive_controls"] == batch.fallback


def test_scheduler_keeps_inactive_constraints_in_policy_snapshot() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="RATE_LIMIT",
                scope=["m1", "m2"],
                params={"max_qps": 2.0},
                guard="recent_429_rate_high",
                fallback="reduce_qps_and_parallelism",
            ),
        ],
        resources={},
    )

    plan = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=_target(
            [
                {"action_id": "A1", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
                {"action_id": "A2", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            ]
        ),
        runtime_metrics={"risk_indicators": {"recent_429_rate": 0.0}},
    )

    rows = plan.meta["policy_snapshot"]["adaptive_controls"]["active_constraints"]
    assert rows == [
        {
            "kind": "RATE_LIMIT",
            "scope": ["A1", "A2"],
            "params": {"max_qps": 2.0},
            "guard": "recent_429_rate_high",
            "fallback": "reduce_qps_and_parallelism",
            "enforced": False,
        }
    ]


def test_scheduler_respects_scoped_budget_k_without_global_serialization() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BUDGET_K",
                scope=["m1", "m2"],
                params={"resource": "CLOUD", "limit": 1},
            )
        ],
        resources={},
    )

    target = _target(
        [
            {"action_id": "A1", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "A3", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"}},
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    first_batch = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]
    assert "A3" in first_batch
    assert len(set(first_batch) & {"A1", "A2"}) == 1
    assert plan.meta["derived_policy"]["budget_rules"] == [
        {"resource": "CLOUD", "scope": ["A1", "A2"], "limit": 1}
    ]


def test_scheduler_resets_budget_k_counts_per_batch() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BUDGET_K",
                scope=["m1", "m2"],
                params={"resource": "CLOUD", "limit": 1},
            )
        ],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "A3", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"}},
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert len(plan.ordered_batches) >= 2
    second_batch_actions = [action_id for group in plan.ordered_batches[1].parallel_groups for action_id in group]
    assert "A2" in second_batch_actions
    assert all(row["kind"] != "FORCED_PICK" for row in plan.ordered_batches[1].fallback)


def test_scheduler_resets_no_overlap_counts_per_batch() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="NO_OVERLAP",
                scope=["m1", "m2"],
                params={"resource": "BLE_AIRTIME"},
            )
        ],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "BLE", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "BLE", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "A3", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"}},
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert len(plan.ordered_batches) >= 2
    second_batch_actions = [action_id for group in plan.ordered_batches[1].parallel_groups for action_id in group]
    assert "A2" in second_batch_actions
    assert all(row["kind"] != "FORCED_PICK" for row in plan.ordered_batches[1].fallback)


def test_scheduler_forced_pick_records_blockers_and_prefers_lower_risk_violation() -> None:
    class ForcedPickScheduler(CrossProtocolScheduler):
        @staticmethod
        def _budget_conflict(
            candidate: str,
            budget_rule_ids_by_action: dict[str, list[int]],
            budget_counts: dict[int, int],
            budget_rules: list[dict],
        ) -> bool:
            del candidate, budget_rule_ids_by_action, budget_counts, budget_rules
            return True

        def _candidate_soft_blockers(
            self,
            candidate: str,
            selected: list[str],
            done: set[str],
            budget_rule_ids_by_action: dict[str, list[int]],
            budget_counts: dict[int, int],
            budget_rules: list[dict],
            no_overlap_scope_ids_by_action: dict[str, list[int]],
            no_overlap_scopes: list[set[str]],
            no_overlap_counts: dict[int, int],
            min_gap_pairs: dict[tuple[str, str], int],
            soft_order_pairs: set[tuple[str, str]],
        ) -> list[dict]:
            del selected, done, budget_rule_ids_by_action, budget_counts, budget_rules
            del no_overlap_scope_ids_by_action, no_overlap_scopes, no_overlap_counts, min_gap_pairs, soft_order_pairs
            if candidate == "A1":
                return [{"kind": "NO_OVERLAP", "scope": ["A1"], "params": {"scope_id": 0}}]
            return [{"kind": "SOFT_ORDER", "scope": ["A2"], "params": {"waiting_for": "upstream"}}]

    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
        ]
    )

    plan = ForcedPickScheduler().schedule(dag, optimization_target=target)

    first_batch = plan.ordered_batches[0]
    picked = [action_id for group in first_batch.parallel_groups for action_id in group]
    assert picked == ["A2"]
    assert first_batch.fallback == [
        {
            "kind": "FORCED_PICK",
            "scope": ["A2"],
            "action": "force_pick_despite_soft_conflicts",
            "params": {
                "picked": "A2",
                "blocked_by": [{"kind": "SOFT_ORDER", "scope": ["A2"], "params": {"waiting_for": "upstream"}}],
            },
        }
    ]
    assert "FORCED_PICK" in first_batch.constraints
    assert first_batch.rate_policy["forced_pick"] is True
    assert first_batch.rate_policy["forced_pick_target"] == ["A2"]
    assert first_batch.rate_policy["forced_pick_blocked_kinds"] == ["SOFT_ORDER"]
    assert first_batch.rate_policy["adaptive_controls"] == first_batch.fallback


def test_scheduler_forced_pick_prefers_non_safety_soft_even_if_weight_is_higher() -> None:
    class ForcedPickScheduler(CrossProtocolScheduler):
        @staticmethod
        def _budget_conflict(
            candidate: str,
            budget_rule_ids_by_action: dict[str, list[int]],
            budget_counts: dict[int, int],
            budget_rules: list[dict],
        ) -> bool:
            del candidate, budget_rule_ids_by_action, budget_counts, budget_rules
            return True

        def _candidate_soft_blockers(
            self,
            candidate: str,
            selected: list[str],
            done: set[str],
            budget_rule_ids_by_action: dict[str, list[int]],
            budget_counts: dict[int, int],
            budget_rules: list[dict],
            no_overlap_scope_ids_by_action: dict[str, list[int]],
            no_overlap_scopes: list[set[str]],
            no_overlap_counts: dict[int, int],
            min_gap_pairs: dict[tuple[str, str], int],
            soft_order_pairs: set[tuple[str, str]],
        ) -> list[dict]:
            del selected, done, budget_rule_ids_by_action, budget_counts, budget_rules
            del no_overlap_scope_ids_by_action, no_overlap_scopes, no_overlap_counts, min_gap_pairs, soft_order_pairs
            if candidate == "A1":
                return [{"kind": "NO_OVERLAP", "scope": ["A1"], "params": {"scope_id": 0}}]
            return [
                {"kind": "SOFT_ORDER", "scope": ["A2"], "params": {"waiting_for": "upstream"}},
                {"kind": "BUDGET_K", "scope": ["A2"], "params": {"resource": "CLOUD", "limit": 1}},
                {"kind": "BUDGET_K", "scope": ["A2"], "params": {"resource": "CLOUD", "limit": 1}},
            ]

    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "HA", "critical": True, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
        ]
    )

    plan = ForcedPickScheduler().schedule(dag, optimization_target=target)

    first_batch = plan.ordered_batches[0]
    picked = [action_id for group in first_batch.parallel_groups for action_id in group]
    assert picked == ["A2"]
    assert first_batch.rate_policy["forced_pick_blocked_kinds"] == ["BUDGET_K", "SOFT_ORDER"]


def test_scheduler_pair_key_nonunique_scope_extends_tail_stably() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1", "A2", "A3"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["B1", "B2"]),
        },
        hard_edges=[
            DependencyEdge(
                src_mssu="m1",
                dst_mssu="m2",
                kind="HARD_LIFECYCLE",
                justification=["rule_template:host_pair", "pair_key:host"],
            )
        ],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/a"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/b"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "A3", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/c"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"}},
            {"action_id": "B1", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/d"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b1"}},
            {"action_id": "B2", "protocol": "CLOUD", "critical": True, "target": {"endpoint": "https://api.demo.local/e"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "b2"}},
        ]
    )

    out, _, _, _ = scheduler._project_hard_graph(dag, scheduler._action_index(target), target)

    assert out["A1"] == {"B1"}
    assert out["A2"] == {"B2"}
    assert out["A3"] == {"B2"}


def test_scheduler_emits_batching_bucket_metadata() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m1", "m2", "m3"],
                params={"group_key": "endpoint", "max_batch_size": 2, "max_wait_ms": 80, "idempotent_only": True},
            )
        ],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A1", "protocol": "CLOUD", "critical": True, "idempotent": "yes", "target": {"endpoint": "https://api.demo.local/device.control"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True, "idempotent": "yes", "target": {"endpoint": "https://api.demo.local/device.control"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"}},
            {"action_id": "A3", "protocol": "CLOUD", "critical": True, "idempotent": "yes", "target": {"endpoint": "https://api.demo.local/device.control"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"}},
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].rate_policy["batching_buckets"] == [
        {
            "rule_kind": "BATCH_GROUP",
            "group_key": "endpoint",
            "bucket": "api.demo.local|api.demo.local|https://api.demo.local/device.control",
            "members": ["A1", "A2", "A3"],
            "size": 3,
            "chunks": 2,
            "max_batch_size": 2,
            "max_wait_ms": 80,
        }
    ]


def test_scheduler_materializes_batch_group_bucket_from_endpoint_group_key() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A4"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A5"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A6"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m1", "m2", "m3"],
                params={"group_key": "endpoint", "max_batch_size": 20, "max_wait_ms": 80, "idempotent_only": False},
            )
        ],
        resources={},
    )
    target = _target(
        [
            {"action_id": "A4", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"device_group": "cloud_lane", "endpoint": "tuya:light.living_room.status"}}},
            {"action_id": "A5", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"device_group": "cloud_lane", "endpoint": "tuya:climate.bedroom.status"}}},
            {"action_id": "A6", "protocol": "CLOUD", "critical": True, "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"device_group": "cloud_lane", "endpoint": "tuya:switch.energy_strip.status"}}},
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A4", "A5", "A6"]]
    assert plan.ordered_batches[0].rate_policy["batching_buckets"] == [
        {
            "rule_kind": "BATCH_GROUP",
            "group_key": "endpoint",
            "bucket": "tuya|cloud_lane",
            "members": ["A4", "A5", "A6"],
            "size": 3,
            "chunks": 1,
            "max_batch_size": 3,
            "max_wait_ms": 40,
        }
    ]


def test_scheduler_synthesizes_cloud_batch_rules_from_target_metadata() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A4"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A5"]),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A6"]),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "provider": "tuya",
                "target": {"endpoint": "tuya:light.living_room.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "light",
                    "service": "status",
                    "data_template": {
                        "endpoint": "tuya:light.living_room.status",
                        "endpoint_group_key": "cloud_lane",
                        "host_group_key": "tuya",
                    },
                },
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "provider": "tuya",
                "target": {"endpoint": "tuya:climate.bedroom.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "climate",
                    "service": "status",
                    "data_template": {
                        "endpoint": "tuya:climate.bedroom.status",
                        "endpoint_group_key": "cloud_lane",
                        "host_group_key": "tuya",
                    },
                },
            },
            {
                "action_id": "A6",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "provider": "tuya",
                "target": {"endpoint": "tuya:switch.energy_strip.status"},
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "switch",
                    "service": "status",
                    "data_template": {
                        "endpoint": "tuya:switch.energy_strip.status",
                        "endpoint_group_key": "cloud_lane",
                        "host_group_key": "tuya",
                    },
                },
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A4", "A5", "A6"]]
    assert plan.meta["policy_snapshot"]["batch_policy"]["rules"] == [
        {"scope": ["A4", "A5", "A6"], "group_key": "endpoint", "max_batch_size": 3, "max_wait_ms": 40, "idempotent_only": True}
    ]
    assert plan.ordered_batches[0].session_policy["session_groups"] == [
        {"scope": ["A4", "A5", "A6"], "group_key": "host"}
    ]
    assert plan.ordered_batches[0].rate_policy["batching_buckets"] == [
        {
            "rule_kind": "BATCH_GROUP",
            "group_key": "endpoint",
            "bucket": "tuya|cloud_lane",
            "members": ["A4", "A5", "A6"],
            "size": 3,
            "chunks": 1,
            "max_batch_size": 3,
            "max_wait_ms": 40,
        }
    ]


def test_scheduler_compress_plan_for_trust_dedupes_batch_metadata() -> None:
    scheduler = CrossProtocolScheduler()
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1", "A2"]],
                constraints=["SOFT_ORDER", "SOFT_ORDER", "MIN_GAP"],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 2.0},
                guards=[
                    {"kind": "BUDGET_K", "scope": ["A1", "A2"], "expr": "budget_ok", "enforced": True},
                    {"kind": "BUDGET_K", "scope": ["A2", "A1"], "expr": "budget_ok", "enforced": True},
                ],
                fallback=[
                    {"kind": "SOFT_ORDER", "scope": ["A1", "A2"], "action": "preserve_action_order", "params": {}},
                    {"kind": "SOFT_ORDER", "scope": ["A2", "A1"], "action": "preserve_action_order", "params": {}},
                ],
            )
        ],
        meta={
            "policy": {"max_parallel": 2},
            "node_kind": "action_id",
            "action_to_mssus": {"A1": ["m1", "m2"], "A2": ["m3"]},
        },
    )

    compressed = scheduler.compress_plan_for_trust(plan)

    batch = compressed.ordered_batches[0]
    assert batch.constraints == ["MIN_GAP", "SOFT_ORDER"]
    assert len(batch.guards) == 1
    assert len(batch.fallback) == 1
    assert compressed.meta["trust_compression"]["action_to_mssu_count"] == {"A1": 2, "A2": 1}


def test_scheduler_defaults_observable_priority_to_declared_target_order() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_cloud": MSSU(
                mssu_id="m_cloud",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=["n1"],
                action_refs=["A4"],
                primary_action_ref="A4",
                side_effect_sig={"cloud_http_call"},
            ),
            "m_ble": MSSU(
                mssu_id="m_ble",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=["n2"],
                action_refs=["A1"],
                primary_action_ref="A1",
                side_effect_sig={"ble_gatt_op"},
            ),
            "m_write": MSSU(
                mssu_id="m_write",
                mssu_type="UPDATE",
                phase="RUNTIME",
                node_ids=["n3"],
                action_refs=["A8"],
                primary_action_ref="A8",
                side_effect_sig={"state_write"},
            ),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A8",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_hybrid_transport_cloud_lane"},
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
            },
        ]
    )

    plan = scheduler.schedule(dag, optimization_target=target)
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]

    assert flat.index("A1") < flat.index("A4")
    assert flat.index("A1") < flat.index("A8")
    assert plan.meta["observable_anchor_priority"]["A1"] < plan.meta["observable_anchor_priority"]["A4"]
    assert plan.meta["observable_anchor_priority"]["A1"] < plan.meta["observable_anchor_priority"]["A8"]


def test_scheduler_soft_order_remains_preference_not_global_blocker() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"ble_gatt_op"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"ble_gatt_op"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(kind="SOFT_ORDER", scope=["m_a3", "m_a2"], fallback="preserve_action_order"),
            SoftConstraint(kind="MIN_GAP", scope=["m_a1", "m_a2"], params={"gap_ms": 200}, fallback="preserve_action_order"),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "ble:a1"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "ble:a2"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"kind": "cloud_endpoint", "id": "cloud:a3"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a3"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]

    assert flat.index("A1") < flat.index("A2") < flat.index("A3")


def test_scheduler_preserves_declared_order_inside_batch_bucket() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a9": MSSU(mssu_id="m_a9", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A9"], primary_action_ref="A9", side_effect_sig={"cloud_http_call"}),
            "m_a10": MSSU(mssu_id="m_a10", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A10"], primary_action_ref="A10", side_effect_sig={"cloud_http_call"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m_a9", "m_a10"],
                params={"group_key": "endpoint", "max_batch_size": 2, "max_wait_ms": 40, "idempotent_only": True},
            ),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A9",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/status", "id": "cloud:a9"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a9"},
            },
            {
                "action_id": "A10",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/status", "id": "cloud:a10"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a10"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A9", "A10"]]
    assert plan.ordered_batches[0].rate_policy["batching_buckets"][0]["members"] == ["A9", "A10"]


def test_scheduler_conservative_grouping_keeps_unaffinitized_ready_layer_serial_when_diff_testing_enabled() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"cloud_http_call"}),
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"ble_gatt_op"}),
            "m_a8": MSSU(mssu_id="m_a8", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A8"], primary_action_ref="A8", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"kind": "cloud_endpoint", "id": "tuya:climate.bedroom.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
            },
            {
                "action_id": "A8",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_hybrid_transport_cloud_lane"},
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert len(plan.ordered_batches) == 4
    assert [batch.parallel_groups for batch in plan.ordered_batches] == [
        [["A1"]],
        [["A4"]],
        [["A5"]],
        [["A8"]],
    ]


def test_scheduler_conservative_grouping_batches_affinitized_cloud_ready_layer() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"cloud_http_call"}),
            "m_a8": MSSU(mssu_id="m_a8", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n3"], action_refs=["A8"], primary_action_ref="A8", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SAME_SESSION_GROUP",
                scope=["m_a4", "m_a5"],
                params={"group_key": "host", "reuse_window_ms": 10000},
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="disable_batching_use_singleton_calls",
            ),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "https://api.demo.local/light.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "https://api.demo.local/climate.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status"},
            },
            {
                "action_id": "A8",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_hybrid_transport_cloud_lane"},
                "exec": {"kind": "ha_service_call", "domain": "homeassistant", "service": "update_entity"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(
        dag,
        optimization_target=target,
        runtime_metrics={
            "latency_budget_allows_batching": True,
            "risk_indicators": {"recent_429_rate": 0.01},
        },
    )

    assert len(plan.ordered_batches) == 2
    assert plan.ordered_batches[0].parallel_groups == [["A4", "A5"]]
    assert plan.ordered_batches[0].rate_policy["batching_buckets"] == [
        {
            "rule_kind": "SAME_SESSION_GROUP",
            "group_key": "host",
            "bucket": "api.demo.local",
            "members": ["A4", "A5"],
            "size": 2,
            "chunks": 1,
            "max_batch_size": 4,
            "max_wait_ms": 40,
        }
    ]
    assert plan.ordered_batches[1].parallel_groups == [["A8"]]


def test_scheduler_conservative_grouping_allows_local_read_parallelism() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"local_api_read"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"local_api_read"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"mqtt_subscribe"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A2",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "tplink:plug.coffee_machine", "provider": "tplink_local"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "get_state", "provider": "tplink_local"},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:power_meter_home_main", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A4",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_local_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2", "A3"]]
    assert plan.ordered_batches[1].parallel_groups == [["A4"]]


def test_scheduler_conservative_grouping_coalesces_independent_lane_writebacks() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"ble_gatt_op"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"state_write"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"state_write"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "ble:switchbot:curtain_lr"},
                "exec": {"kind": "ha_service_call", "domain": "switchbot", "service": "refresh_cover"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"kind": "cloud_endpoint", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A3",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_ble_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
            {
                "action_id": "A4",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_cloud_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert [batch.parallel_groups for batch in plan.ordered_batches] == [
        [["A1"]],
        [["A2"]],
        [["A3", "A4"]],
        [["A5"]],
    ]


def test_scheduler_conservative_grouping_allows_mixed_cloud_local_read_overlap() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"mqtt_subscribe"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.living_room.status", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.living_room.status", "endpoint_group_key": "cloud_lane", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.hallway.status", "id": "tuya:light.hallway.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.hallway.status", "endpoint_group_key": "cloud_lane", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_node_living_room", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"], ["A3", "A4"]]
    assert plan.ordered_batches[1].parallel_groups == [["A5"]]


def test_scheduler_conservative_grouping_keeps_cross_protocol_reads_separate_when_soft_order_exists() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"local_api_read"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["m_a1", "m_a2"],
                params={"reason": "candidate:DATA_DEP"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.living_room.status", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.living_room.status", "endpoint_group_key": "cloud_lane", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert [batch.parallel_groups for batch in plan.ordered_batches] == [
        [["A1"]],
        [["A2"]],
    ]


def test_scheduler_conservative_grouping_does_not_let_later_local_read_jump_frontier() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"local_api_read"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["m_a1", "m_a2"],
                params={"reason": "candidate:DATA_DEP"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.living_room.status", "id": "tuya:light.living_room.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.living_room.status", "endpoint_group_key": "cloud_lane", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_node_living_room", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1"]]
    assert plan.ordered_batches[1].parallel_groups == [["A2", "A3"]]


def test_scheduler_conservative_grouping_keeps_cloud_frontier_contiguous_before_local_overlap() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"cloud_http_call"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="ACT", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"local_api_read"}),
            "m_a7": MSSU(mssu_id="m_a7", mssu_type="ACT", phase="RUNTIME", node_ids=["n7"], action_refs=["A7"], primary_action_ref="A7", side_effect_sig={"local_api_read"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.living_room_1.status", "id": "tuya:light.living_room_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.living_room_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.living_room_2.status", "id": "tuya:light.living_room_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.living_room_2.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
                {
                    "action_id": "A3",
                    "protocol": "CLOUD",
                    "critical": True,
                    "idempotent": "yes",
                    "target": {"endpoint": "tuya:climate.bedroom.status", "id": "tuya:climate.bedroom.status"},
                    "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"endpoint": "tuya:climate.bedroom.status", "endpoint_group_key": "climate", "host_group_key": "tuya"}},
                },
                {
                    "action_id": "A4",
                    "protocol": "CLOUD",
                    "critical": True,
                    "idempotent": "yes",
                    "target": {"endpoint": "tuya:switch.energy_strip_tv.status", "id": "tuya:switch.energy_strip_tv.status"},
                    "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.energy_strip_tv.status", "endpoint_group_key": "energy", "host_group_key": "tuya"}},
                },
                {
                    "action_id": "A5",
                    "protocol": "CLOUD",
                    "critical": True,
                    "idempotent": "yes",
                    "target": {"endpoint": "tuya:switch.energy_strip_desk.status", "id": "tuya:switch.energy_strip_desk.status"},
                    "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.energy_strip_desk.status", "endpoint_group_key": "energy", "host_group_key": "tuya"}},
                },
                {
                    "action_id": "A6",
                    "protocol": "LOCAL",
                    "critical": True,
                    "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room_group", "provider": "hue_local"},
                    "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
                },
                {
                    "action_id": "A7",
                    "protocol": "LOCAL",
                    "critical": True,
                    "target": {"kind": "local_endpoint", "id": "hue:bridge_1:bedroom_group", "provider": "hue_local"},
                    "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
                },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    batch0_actions = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]
    batch1_actions = [action_id for group in plan.ordered_batches[1].parallel_groups for action_id in group]
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]

    assert "A5" in batch0_actions
    assert "A6" not in batch0_actions
    assert "A7" not in batch0_actions
    assert "A6" in batch1_actions
    assert "A7" in batch1_actions
    assert flat.index("A5") < flat.index("A6")
    assert flat.index("A5") < flat.index("A7")


def test_scheduler_conservative_grouping_keeps_snapshot_cloud_read_frontier_ahead_of_local_even_without_shared_bucket() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"cloud_http_call"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="ACT", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"local_api_read"}),
            "m_a7": MSSU(mssu_id="m_a7", mssu_type="ACT", phase="RUNTIME", node_ids=["n7"], action_refs=["A7"], primary_action_ref="A7", side_effect_sig={"local_api_read"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_1.status", "id": "tuya:light.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_2.status", "id": "tuya:light.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_2.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:climate.zone_1.status", "id": "tuya:climate.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"endpoint": "tuya:climate.zone_1.status", "endpoint_group_key": "climate", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:climate.zone_2.status", "id": "tuya:climate.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"endpoint": "tuya:climate.zone_2.status", "endpoint_group_key": "climate", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint": "ecobee:thermostat.home_1", "endpoint_group_key": "ecobee_runtime", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A6",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:group_living", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A7",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:group_hallway", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    batch0_actions = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]
    flat = [action_id for batch in plan.ordered_batches for group in batch.parallel_groups for action_id in group]

    assert "A6" not in batch0_actions
    assert "A7" not in batch0_actions
    assert flat.index("A5") < flat.index("A6")
    assert flat.index("A5") < flat.index("A7")


def test_scheduler_conservative_grouping_allows_read_only_cloud_singletons_to_share_a_batch() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_1.status", "id": "tuya:light.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_2.status", "id": "tuya:light.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_2.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:climate.zone_1.status", "id": "tuya:climate.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"endpoint": "tuya:climate.zone_1.status", "endpoint_group_key": "climate", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint": "ecobee:thermostat.home_1", "endpoint_group_key": "runtime_verify", "host_group_key": "ecobee"}},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    batch0_actions = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]

    assert batch0_actions == ["A1", "A2", "A3", "A4"]


def test_scheduler_corridor_optimizer_admission_requires_large_mixed_acquisition_corridor() -> None:
    scheduler = CrossProtocolScheduler()
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_1.status", "id": "tuya:light.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:living_room", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_living_room", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint": "ecobee:thermostat.home_1", "endpoint_group_key": "runtime", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:switch.strip_1.status", "id": "tuya:switch.strip_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.strip_1.status", "endpoint_group_key": "switches", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A6",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:bedroom", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )
    action_index = scheduler._action_index(target)
    action_phase_by_action = scheduler._action_phase_map(action_index)

    corridor = scheduler._extract_optimizable_corridor(
        list(action_index.keys()),
        set(),
        action_index,
        action_phase_by_action,
    )

    assert corridor == ["A1", "A2", "A3", "A4", "A5", "A6"]


def test_scheduler_frontier_window_optimizer_admits_smaller_mixed_frontier() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_a.status", "id": "tuya:light.room_a.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_a.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_b.status", "id": "tuya:light.room_b.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_b.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:room_a", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:room_a_air", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )
    action_index = scheduler._action_index(target)
    action_phase_by_action = scheduler._action_phase_map(action_index)
    action_ids = list(action_index.keys())

    assert scheduler._extract_optimizable_corridor(
        action_ids,
        set(),
        action_index,
        action_phase_by_action,
    ) == []
    assert scheduler._extract_frontier_window(
        action_ids,
        set(action_ids),
        set(),
        action_index,
        action_phase_by_action,
    ) == ["A1", "A2", "A3", "A4"]

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"], ["A3", "A4"]]
    assert plan.ordered_batches[1].parallel_groups == [["A5"]]
    assert plan.meta["optimizer_decisions"][0]["mode"] == "frontier_window"
    assert plan.meta["optimizer_decisions"][0]["window"] == ["A1", "A2", "A3", "A4"]


def test_scheduler_frontier_window_keeps_batch_bucket_when_earlier_cloud_is_incompatible() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            f"m_a{i}": MSSU(
                mssu_id=f"m_a{i}",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=[f"n{i}"],
                action_refs=[f"A{i}"],
                primary_action_ref=f"A{i}",
                side_effect_sig={"cloud_http_call"},
            )
            for i in range(1, 6)
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    actions = []
    for idx, (group, endpoint) in enumerate(
        [
            ("single", "tuya:plug.entry.status"),
            ("lights", "tuya:light.room_a.status"),
            ("lights", "tuya:light.room_b.status"),
            ("lights", "tuya:light.room_c.status"),
            ("climate", "tuya:climate.home.status"),
        ],
        1,
    ):
        actions.append(
            {
                "action_id": f"A{idx}",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": endpoint, "id": endpoint},
                "exec": {
                    "kind": "ha_service_call",
                    "domain": "light",
                    "service": "status",
                    "data_template": {
                        "endpoint": endpoint,
                        "endpoint_group_key": group,
                        "host_group_key": "tuya",
                    },
                },
            }
        )
    target = _target(actions, validation={"differential_tests": {"enabled": True}})

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1"], ["A2", "A3", "A4"], ["A5"]]
    assert plan.meta["optimizer_decisions"][0]["mode"] == "frontier_window"


def test_scheduler_frontier_window_optimizer_does_not_skip_ready_ble_barrier() -> None:
    scheduler = CrossProtocolScheduler()
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "xiaomi:motion.entry"},
                "exec": {"kind": "ha_service_call", "domain": "ble", "service": "read_sensor"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.entry.status", "id": "tuya:light.entry.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.entry.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:entry", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )
    action_index = scheduler._action_index(target)
    action_phase_by_action = scheduler._action_phase_map(action_index)
    action_ids = list(action_index.keys())

    assert scheduler._extract_frontier_window(
        action_ids,
        set(action_ids),
        set(),
        action_index,
        action_phase_by_action,
    ) == []


def test_scheduler_ble_api_frontier_packs_api_reads_with_single_ble_anchor() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"ble_gatt_op"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"ble_gatt_op"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"state_write"}),
        },
        hard_edges=[
            DependencyEdge(src_mssu=f"m_a{i}", dst_mssu="m_a6", kind="HARD_DATA")
            for i in range(1, 6)
        ],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "xiaomi:motion.entry"},
                "exec": {"kind": "ha_service_call", "domain": "ble", "service": "read_sensor"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.entry.status", "id": "tuya:light.entry.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.entry.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.hall.status", "id": "tuya:light.hall.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.hall.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:entry", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A5",
                "protocol": "BLE",
                "critical": True,
                "target": {"kind": "ble_device", "id": "xiaomi:door.entry"},
                "exec": {"kind": "ha_service_call", "domain": "ble", "service": "read_sensor"},
            },
            {
                "action_id": "A6",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )
    action_index = scheduler._action_index(target)
    action_phase_by_action = scheduler._action_phase_map(action_index)
    action_ids = list(action_index.keys())

    assert scheduler._extract_frontier_window(
        action_ids,
        {"A1", "A2", "A3", "A4", "A5"},
        set(),
        action_index,
        action_phase_by_action,
    ) == []
    assert scheduler._extract_ble_api_frontier_window(
        action_ids,
        {"A1", "A2", "A3", "A4", "A5"},
        set(),
        action_index,
        action_phase_by_action,
    ) == ["A1", "A2", "A3", "A4"]

    plan = scheduler.schedule(dag, optimization_target=target)

    first_batch_actions = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]
    assert first_batch_actions == ["A1", "A2", "A3", "A4"]
    assert "A5" not in first_batch_actions
    assert sum(1 for action_id in first_batch_actions if action_index[action_id]["protocol"] == "BLE") == 1
    assert plan.meta["optimizer_decisions"][0]["mode"] == "ble_api_frontier"
    assert plan.meta["optimizer_decisions"][0]["window"] == ["A1", "A2", "A3", "A4"]


def test_scheduler_corridor_optimizer_scores_pure_cloud_wave_better_than_mixed_wave() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"local_api_read"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="ACT", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"local_api_read"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_1.status", "id": "tuya:light.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_2.status", "id": "tuya:light.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_2.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:switch.strip_1.status", "id": "tuya:switch.strip_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.strip_1.status", "endpoint_group_key": "switches", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_room_1", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A5",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:room_2", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A6",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_room_2", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )
    action_index = scheduler._action_index(target)
    out, indegree, _, action_to_mssus = scheduler._project_hard_graph(dag, action_index, target)
    baseline_trace_hints = scheduler._baseline_trace_hints(target)
    action_rank = {action_id: idx for idx, action_id in enumerate(action_index.keys())}
    action_phase_by_action = scheduler._action_phase_map(action_index)
    soft_constraints = scheduler._project_soft_constraints(dag, action_index, target)
    derived = scheduler._derive_policy_from_constraints(scheduler.policy, soft_constraints, {}, target)
    cloud_request_slots = scheduler._prepare_cloud_request_slots(action_index, derived)
    affinity_tokens_by_action = scheduler._prepare_group_affinity(action_index, derived)
    action_ids = list(action_index.keys())
    critical_score = scheduler._critical_path_score(action_ids, out, dict(indegree), {})
    critical_boost = {action_id: (1 if bool(action_index[action_id].get("critical", False)) else 0) for action_id in action_ids}

    pure_cloud = scheduler._build_batch_from_order(
        ["A1", "A2", "A3", "A4", "A5", "A6"],
        True,
        set(action_ids),
        set(),
        action_index,
        derived,
        True,
        affinity_tokens_by_action,
        action_rank,
        action_phase_by_action,
        cloud_request_slots,
        scheduler._prepare_budget_index(derived.budget_rules),
        scheduler._prepare_overlap_index(derived.no_overlap_scopes),
        set(),
    )
    mixed = scheduler._build_batch_from_order(
        ["A1", "A2", "A3", "A4", "A5", "A6"],
        False,
        set(action_ids),
        set(),
        action_index,
        derived,
        True,
        affinity_tokens_by_action,
        action_rank,
        action_phase_by_action,
        cloud_request_slots,
        scheduler._prepare_budget_index(derived.budget_rules),
        scheduler._prepare_overlap_index(derived.no_overlap_scopes),
        set(),
    )

    pure_cloud_score = scheduler._corridor_batch_cost(
        pure_cloud,
        set(action_ids) - set(pure_cloud.selected),
        set(action_ids),
        (),
        action_index,
        action_rank,
    )
    mixed_score = scheduler._corridor_batch_cost(
        mixed,
        set(action_ids) - set(mixed.selected),
        set(action_ids),
        (),
        action_index,
        action_rank,
    )

    assert pure_cloud.selected == ["A1", "A2", "A3"]
    assert mixed.selected == ["A1", "A2", "A3", "A4", "A5", "A6"]
    assert pure_cloud_score < mixed_score


def test_scheduler_cloud_limit_counts_request_groups_not_logical_actions() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            f"m_a{i}": MSSU(mssu_id=f"m_a{i}", mssu_type="ACT", phase="RUNTIME", node_ids=[f"n{i}"], action_refs=[f"A{i}"], primary_action_ref=f"A{i}", side_effect_sig={"cloud_http_call"})
            for i in range(1, 7)
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_1.status", "id": "tuya:light.zone_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_1.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.zone_2.status", "id": "tuya:light.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.zone_2.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:switch.strip_1.status", "id": "tuya:switch.strip_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.strip_1.status", "endpoint_group_key": "switches", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:switch.strip_2.status", "id": "tuya:switch.strip_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "status", "data_template": {"endpoint": "tuya:switch.strip_2.status", "endpoint_group_key": "switches", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:climate.home_1.status", "id": "tuya:climate.home_1.status"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "status", "data_template": {"endpoint": "tuya:climate.home_1.status", "endpoint_group_key": "climate", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A6",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_2", "id": "ecobee:thermostat.home_2"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint": "ecobee:thermostat.home_2", "endpoint_group_key": "runtime_2", "host_group_key": "ecobee"}},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    batch0_actions = [action_id for group in plan.ordered_batches[0].parallel_groups for action_id in group]
    batch1_actions = [action_id for group in plan.ordered_batches[1].parallel_groups for action_id in group]

    assert batch0_actions == ["A1", "A2", "A3", "A4", "A5"]
    assert batch1_actions == ["A6"]


def test_scheduler_conservative_grouping_keeps_post_control_verification_frontier_contiguous() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "tuya:light.scene.turn_on", "id": "tuya:light.scene.turn_on"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "turn_on"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.scene.status", "id": "tuya:light.scene.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.scene.status", "endpoint_group_key": "scene_verify", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint": "ecobee:thermostat.home_1", "endpoint_group_key": "runtime_verify", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:scene_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert [batch.parallel_groups for batch in plan.ordered_batches] == [
        [["A1"]],
        [["A2"]],
        [["A3", "A4"]],
        [["A5"]],
    ]


def test_scheduler_defers_post_control_verification_until_all_control_actions_finish() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"cloud_http_call"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"cloud_http_call"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="ACT", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"cloud_http_call"}),
            "m_a7": MSSU(mssu_id="m_a7", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n7"], action_refs=["A7"], primary_action_ref="A7", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "tuya:light.scene.turn_on", "id": "tuya:light.scene.turn_on"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "turn_on", "data_template": {"endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "ecobee:thermostat.home_1.set_hvac_mode", "id": "ecobee:thermostat.home_1.set_hvac_mode"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "set_hvac_mode", "data_template": {"endpoint_group_key": "hvac", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "ecobee:thermostat.home_1.set_temperature", "id": "ecobee:thermostat.home_1.set_temperature"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "set_temperature", "data_template": {"endpoint_group_key": "hvac", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.scene.status", "id": "tuya:light.scene.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint_group_key": "scene_verify", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A5",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime", "data_template": {"endpoint_group_key": "runtime_verify", "host_group_key": "ecobee"}},
            },
            {
                "action_id": "A6",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:scene_group", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A7",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert [batch.parallel_groups for batch in plan.ordered_batches] == [
        [["A1"]],
        [["A2", "A3"]],
        [["A4"]],
        [["A5"], ["A6"]],
        [["A7"]],
    ]


def test_scheduler_conservative_grouping_compacts_local_verification_group_without_cloud_bucket() -> None:
    scheduler = CrossProtocolScheduler()
    action_index = {
        "A2": {
            "action_id": "A2",
            "protocol": "CLOUD",
            "critical": True,
            "idempotent": "yes",
            "target": {"endpoint": "ecobee:thermostat.home_1", "id": "ecobee:thermostat.home_1"},
            "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime"},
        },
        "A3": {
            "action_id": "A3",
            "protocol": "LOCAL",
            "critical": True,
            "target": {"kind": "local_endpoint", "id": "hue:bridge_1:scene_group", "provider": "hue_local"},
            "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
        },
        "A4": {
            "action_id": "A4",
            "protocol": "LOCAL",
            "critical": True,
            "target": {"kind": "local_endpoint", "id": "tplink:plug.scene_strip", "provider": "tplink_local"},
            "exec": {"kind": "ha_service_call", "domain": "switch", "service": "get_state", "provider": "tplink_local"},
        },
        "A5": {
            "action_id": "A5",
            "protocol": "LOCAL",
            "critical": True,
            "target": {"kind": "mqtt_topic", "id": "mqtt:air_quality_scene", "provider": "mqtt"},
            "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
        },
    }
    derived = DerivedConstraintPolicy(
        total_limit=10,
        ble_limit=1,
        cloud_limit=4,
        local_limit=6,
        unknown_limit=1,
        max_qps=5.0,
        rate_limit_burst=10,
        rate_limit_window_ms=1000,
        reuse_enabled=True,
        reuse_window_ms=20_000,
        latency_budget_ms=4_000,
        budget_rules=[],
        batch_rules=[
            {
                "scope": ["A9", "A10"],
                "scope_set": {"A9", "A10"},
                "group_key": "endpoint",
                "max_batch_size": 3,
                "max_wait_ms": 40,
                "idempotent_only": True,
            }
        ],
        session_rules=[],
        no_overlap_scopes=[],
        min_gap_pairs={},
        soft_order_pairs=set(),
        active_constraints=[],
        triggered_fallbacks=[],
    )

    groups, buckets = scheduler._group_selected_actions(["A2", "A3", "A4", "A5"], action_index, derived)

    assert buckets == []
    assert groups == [["A2"], ["A3", "A4", "A5"]]


def test_action_semantic_classification_does_not_treat_guest_suite_setters_as_reads() -> None:
    action = {
        "action_id": "A1",
        "protocol": "CLOUD",
        "critical": True,
        "target": {
            "id": "ecobee:thermostat.guest_suite.set_temperature",
            "kind": "cloud_endpoint",
            "endpoint": "ecobee:thermostat.guest_suite.set_temperature",
        },
        "exec": {
            "kind": "ha_service_call",
            "domain": "climate",
            "service": "set_temperature",
        },
    }

    assert CrossProtocolScheduler._action_is_read_like(action) is False
    assert CrossProtocolScheduler._action_is_control_like(action) is True


def test_action_phase_map_uses_last_control_boundary_for_intermediate_reads() -> None:
    action_index = {
        "A1": {
            "action_id": "A1",
            "protocol": "BLE",
            "target": {"id": "ble:switchbot:curtain"},
            "exec": {"kind": "ha_service_call", "service": "set_cover_position"},
        },
        "A2": {
            "action_id": "A2",
            "protocol": "BLE",
            "target": {"id": "ble:xiaomi_ble:motion"},
            "exec": {"kind": "ha_service_call", "service": "read_sensor"},
        },
        "A3": {
            "action_id": "A3",
            "protocol": "CLOUD",
            "target": {"id": "ecobee:thermostat.office.set_temperature"},
            "exec": {"kind": "ha_service_call", "service": "set_temperature"},
        },
        "A4": {
            "action_id": "A4",
            "protocol": "CLOUD",
            "idempotent": True,
            "target": {"id": "ecobee:thermostat.office"},
            "exec": {"kind": "ha_service_call", "service": "read_runtime"},
        },
    }

    assert CrossProtocolScheduler._action_phase_map(action_index) == {
        "A1": "control",
        "A2": "pre_control_acquisition",
        "A3": "control",
        "A4": "post_control_verification",
    }


def test_scheduler_compress_plan_for_trust_merges_lane_policy_rows() -> None:
    scheduler = CrossProtocolScheduler()
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A4"], ["A5"], ["A8"]],
                constraints=["SOFT_ORDER", "SOFT_ORDER", "NO_OVERLAP"],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 2.0},
                guards=[
                    {"kind": "RATE_LIMIT", "scope": ["A4", "A5"], "expr": "429_rate_low", "enforced": True},
                    {"kind": "RATE_LIMIT", "scope": ["A5", "A4"], "expr": "429_rate_low", "enforced": True},
                    {"kind": "WRITEBACK", "scope": ["A8"], "expr": "after_runtime", "enforced": True},
                ],
                fallback=[
                    {"kind": "SOFT_ORDER", "scope": ["A4", "A5"], "action": "preserve_action_order", "params": {}},
                    {"kind": "SOFT_ORDER", "scope": ["A5", "A4"], "action": "preserve_action_order", "params": {}},
                    {"kind": "WRITEBACK", "scope": ["A8"], "action": "delay_writeback", "params": {}},
                ],
            )
        ],
        meta={
            "policy": {"max_parallel": 2},
            "node_kind": "action_id",
            "action_lanes": {"A4": "CLOUD", "A5": "CLOUD", "A8": "WRITEBACK_CLOUD"},
            "action_to_mssus": {"A4": ["m1"] * 12, "A5": ["m2"] * 4, "A8": ["m3"]},
        },
    )

    compressed = scheduler.compress_plan_for_trust(plan)
    batch = compressed.ordered_batches[0]
    blocks = compressed.meta["trust_compression"]["policy_blocks"]

    assert len(batch.guards) == 2
    assert len(batch.fallback) == 2
    assert any(block["policy_block"] == "cloud_policy" and sorted(block["scope"]) == ["A4", "A5"] for block in blocks)
    assert any(block["policy_block"] == "writeback_cloud_policy" and block["scope"] == ["A8"] for block in blocks)
    assert compressed.meta["trust_compression"]["merged_constraints"]


def test_scheduler_dedupes_triggered_fallbacks_and_localizes_cloud_candidate_soft_order() -> None:
    dag = TypedDAG(
        nodes={
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"cloud_http_call"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["m_a4"],
                params={"reason": "candidate:DATA_DEP"},
                fallback="preserve_action_order",
            ),
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["m_a4"],
                params={"reason": "candidate:DATA_DEP"},
                fallback="preserve_action_order",
            ),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "https://api.demo.local/light.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            }
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    assert plan.meta["derived_policy"]["triggered_fallbacks"] == [
        {
            "fallback": "force_topological_local_order",
            "kind": "SOFT_ORDER",
            "params": {"reason": "candidate:DATA_DEP"},
            "scope": ["A4"],
        }
    ]
    assert plan.ordered_batches[0].fallback == [
        {
            "action": "force_topological_local_order",
            "kind": "SOFT_ORDER",
            "params": {"reason": "candidate:DATA_DEP"},
            "scope": ["A4"],
        }
    ]


def test_scheduler_keeps_local_api_serialize_fallback_lane_scoped() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(
                mssu_id="m1",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=["n1"],
                action_refs=["A1"],
                primary_action_ref="A1",
                side_effect_sig={"cloud_http_call"},
            ),
            "m2": MSSU(
                mssu_id="m2",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=["n2"],
                action_refs=["A2"],
                primary_action_ref="A2",
                side_effect_sig={"cloud_http_call"},
            ),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SAME_SESSION_GROUP",
                scope=["m1", "m2"],
                params={"group_key": "endpoint"},
                guard="local_endpoint_reachable",
                fallback="serialize_local_api_reads",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.a"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.b"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ]
    )

    plan = CrossProtocolScheduler().schedule(dag, optimization_target=target)

    derived_policy = plan.meta["derived_policy"]
    assert derived_policy["total_limit"] > 1
    assert derived_policy["cloud_limit"] > 1
    assert derived_policy["local_limit"] == 1
    assert derived_policy["triggered_fallbacks"] == [
        {
            "fallback": "serialize_local_api_reads",
            "kind": "SAME_SESSION_GROUP",
            "params": {"group_key": "endpoint"},
            "scope": ["A1", "A2"],
        }
    ]
    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"]]


def test_scheduler_shrinks_batch_before_disabling_when_429_is_not_high() -> None:
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="BATCH_GROUP",
                scope=["m1", "m2"],
                params={"group_key": "endpoint", "max_batch_size": 8, "max_wait_ms": 100, "idempotent_only": True},
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="disable_batching_use_singleton_calls",
            ),
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.status"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "https://api.demo.local/device.status"},
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
            },
        ],
        objectives={"metrics": {"e2e_latency_ms": {"p95": 120}}},
    )

    plan = CrossProtocolScheduler().schedule(
        dag,
        optimization_target=target,
        runtime_metrics={
            "latency_budget_allows_batching": True,
            "risk_indicators": {"recent_429_rate": 0.06},
        },
    )

    assert plan.meta["derived_policy"]["triggered_fallbacks"] == [
        {
            "fallback": "shrink_batch_not_disable",
            "kind": "BATCH_GROUP",
            "params": {"group_key": "endpoint", "max_batch_size": 4, "max_wait_ms": 40, "idempotent_only": True},
            "scope": ["A1", "A2"],
        }
    ]
    assert plan.meta["policy_snapshot"]["batch_policy"]["rules"] == [
        {
            "scope": ["A1", "A2"],
            "group_key": "endpoint",
            "max_batch_size": 4,
            "max_wait_ms": 30,
            "idempotent_only": True,
        }
    ]
    assert any(
        row["kind"] == "BATCH_GROUP"
        and row["fallback"] == "shrink_batch_not_disable"
        and row["params"] == {"group_key": "endpoint", "max_batch_size": 4, "max_wait_ms": 40, "idempotent_only": True}
        for row in plan.meta["policy_snapshot"]["adaptive_controls"]["active_constraints"]
    )
    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"]]


def test_scheduler_skips_shared_transport_min_gap_for_subscribe_like_action() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(nodes={}, hard_edges=[], soft_constraints=[], resources={})
    target = OptimizationTarget(
        meta={"vdev_id": "sched_subscribe_gap"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "active_op"},
            },
            {
                "action_id": "A3",
                "protocol": "BLE",
                "critical": True,
                "marker_hints": ["SUBSCRIBE"],
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "subscribe"},
            },
        ],
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[
            {"before": "A1", "after": "A3", "reason": "shared_radio_or_transport_budget"},
        ],
        critical_action_ids=["A1", "A3"],
    )

    projected = scheduler._project_soft_constraints(dag, scheduler._action_index(target), target)

    assert projected == []


def test_scheduler_skips_projected_shared_transport_min_gap_for_subscribe_like_action() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"]),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="PREPARE", phase="RUNTIME", node_ids=["n2"], action_refs=["A3"]),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="MIN_GAP",
                scope=["m_a1", "m_a3"],
                params={"reason": "shared_radio_or_transport_budget"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = OptimizationTarget(
        meta={"vdev_id": "sched_projected_subscribe_gap"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "critical": True,
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "active_op"},
            },
            {
                "action_id": "A3",
                "protocol": "BLE",
                "critical": True,
                "marker_hints": ["SUBSCRIBE"],
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "subscribe"},
            },
        ],
        target_anchors={},
        entrypoint={},
        objectives={},
        constraints={},
        validation={},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A3"],
    )

    projected = scheduler._project_soft_constraints(dag, scheduler._action_index(target), target)

    assert projected == []


def test_scheduler_mssu_to_actions_preserves_generalized_cluster_scope() -> None:
    dag = TypedDAG(
        nodes={
            "cluster_read": MSSU(
                mssu_id="cluster_read",
                mssu_type="ACT",
                phase="RUNTIME",
                node_ids=["n1"],
                primary_action_ref="A7",
                secondary_action_refs=["A8"],
                action_refs=["A7", "A8"],
            )
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )

    assert CrossProtocolScheduler._mssu_to_actions(dag) == {"cluster_read": {"A7", "A8"}}


def test_scheduler_projects_soft_order_scope_in_target_order() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["A10", "A2", "A9"],
                params={"reason": "candidate:DATA_DEP"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"endpoint": "tuya:light.zone_2.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A9",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:zone_9"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A10",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.zone_10"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
    )

    projected = scheduler._project_soft_constraints(dag, scheduler._action_index(target), target)

    assert projected == [
        {
            "kind": "SOFT_ORDER",
            "scope": ["A2", "A9", "A10"],
            "params": {"reason": "candidate:DATA_DEP"},
            "guard": "true",
            "fallback": "preserve_action_order",
        }
    ]


def test_scheduler_rewrites_local_control_dep_writeback_scope_to_pairwise_writeback_edges() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["A13", "A8", "A9"],
                params={"reason": "candidate:CONTROL_DEP"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A8",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:left"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A9",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:air:left"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            },
            {
                "action_id": "A13",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.local_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
    )

    projected = scheduler._project_soft_constraints(dag, scheduler._action_index(target), target)

    assert projected == [
        {
            "kind": "SOFT_ORDER",
            "scope": ["A8", "A13"],
            "params": {"reason": "candidate:CONTROL_DEP"},
            "guard": "true",
            "fallback": "preserve_action_order",
        },
        {
            "kind": "SOFT_ORDER",
            "scope": ["A9", "A13"],
            "params": {"reason": "candidate:CONTROL_DEP"},
            "guard": "true",
            "fallback": "preserve_action_order",
        },
    ]


def test_scheduler_keeps_local_frontier_packed_when_control_dep_soft_scope_only_targets_writeback() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="SOFT_ORDER",
                scope=["m_a5", "m_a3", "m_a4"],
                params={"reason": "candidate:CONTROL_DEP"},
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_a.status", "id": "tuya:light.room_a.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_a.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_b.status", "id": "tuya:light.room_b.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_b.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:room_a"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:room_a_air"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.local_lane"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"], ["A3", "A4"]]
    assert plan.ordered_batches[1].parallel_groups == [["A5"]]


def test_scheduler_groups_unbucketed_local_reads_after_cloud_bucket() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"mqtt_subscribe"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_a.status", "id": "tuya:light.room_a.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_a.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_b.status", "id": "tuya:light.room_b.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_b.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:room_a", "provider": "hue_local"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state", "provider": "hue_local"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:room_a_air", "provider": "mqtt"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message", "provider": "mqtt"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(dag, optimization_target=target)

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"], ["A3", "A4"]]
    assert plan.ordered_batches[1].parallel_groups == [["A5"]]


def test_scheduler_counts_cheap_local_frontier_by_group_occupancy() -> None:
    scheduler = CrossProtocolScheduler()
    dag = TypedDAG(
        nodes={
            "m_a1": MSSU(mssu_id="m_a1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1", side_effect_sig={"cloud_http_call"}),
            "m_a2": MSSU(mssu_id="m_a2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2", side_effect_sig={"cloud_http_call"}),
            "m_a3": MSSU(mssu_id="m_a3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3", side_effect_sig={"local_api_read"}),
            "m_a4": MSSU(mssu_id="m_a4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4", side_effect_sig={"local_api_read"}),
            "m_a5": MSSU(mssu_id="m_a5", mssu_type="ACT", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5", side_effect_sig={"local_api_read"}),
            "m_a6": MSSU(mssu_id="m_a6", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n6"], action_refs=["A6"], primary_action_ref="A6", side_effect_sig={"state_write"}),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    target = _target(
        [
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_a.status", "id": "tuya:light.room_a.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_a.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": "yes",
                "target": {"endpoint": "tuya:light.room_b.status", "id": "tuya:light.room_b.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status", "data_template": {"endpoint": "tuya:light.room_b.status", "endpoint_group_key": "lights", "host_group_key": "tuya"}},
            },
            {
                "action_id": "A3",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "hue:bridge_1:room_a"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "local_endpoint", "id": "tplink:plug.room_a"},
                "exec": {"kind": "ha_service_call", "domain": "switch", "service": "get_state"},
            },
            {
                "action_id": "A5",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"kind": "mqtt_topic", "id": "mqtt:room_a_air"},
                "exec": {"kind": "ha_service_call", "domain": "mqtt", "service": "read_last_message"},
            },
            {
                "action_id": "A6",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.vdev_overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        validation={"differential_tests": {"enabled": True}},
    )

    plan = scheduler.schedule(
        dag,
        optimization_target=target,
        runtime_metrics={"offline_policy_overrides": {"max_parallel": 3, "cloud_parallel": 3, "local_parallel": 6}},
    )

    assert plan.ordered_batches[0].parallel_groups == [["A1", "A2"], ["A3", "A4", "A5"]]
    assert plan.ordered_batches[1].parallel_groups == [["A6"]]
