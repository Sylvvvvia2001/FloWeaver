from __future__ import annotations

from pathlib import Path

from alignment_layer.api.run_alignment_verification import run_alignment_verification
from alignment_layer.rules.alignment_rules import AlignmentConfig, DEFAULT_ALIGNMENT_RULES
from dsl.contracts import (
    Batch,
    CounterExample,
    DiffHunk,
    ExecutionPlan,
    HAPProfile,
    MSSU,
    OptimizationTarget,
    PROFILE_SCHEMA_VERSION,
    Rule,
    RuleStatus,
    SoftConstraint,
    SoftConstraintKind,
    TypedDAG,
    now_utc_iso,
)
from counterexample_layer.ir.summaries import trace_to_ir_program
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from dsl.io import load_json, load_jsonl
from optimizer.m5_scheduler import CrossProtocolScheduler
from optimizer.m6_trust import LEVEL1_STRATEGIES, TrustLayer
from runtime.replay import ReplayResult
from dsl.contracts import Event, Trace
from runtime.trace import TraceCompareConfig, compare_traces


def _counterexample_runtime_artifacts(
    baseline: Trace,
    optimized: Trace,
    target: OptimizationTarget | None = None,
    suspicious_regions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    schema = CounterexampleObservationSchema.from_optimization_target(target)
    compare_config = TraceCompareConfig(canonicalization_version=schema.canonicalization_version)
    baseline_ir = trace_to_ir_program(baseline, "baseline", compare_config)
    optimized_ir = trace_to_ir_program(optimized, "optimized", compare_config)
    resource_model = ResourceModel.from_observation_schema(schema)
    alignment_result = run_alignment_verification(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        observation_schema=schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )
    return {
        "baseline_ir": baseline_ir.to_dict(),
        "optimized_ir": optimized_ir.to_dict(),
        "alignment_result": alignment_result.to_dict(),
        "alignment_map": alignment_result.alignment_map.to_dict(),
        "observation_schema": schema.to_dict(),
        "resource_model": resource_model.to_dict(),
        "environment_model": {
            "inputs": {"scenario_id": "fixture"},
            "request_params": {},
            "device_results": {},
            "toggles": {},
            "framework_events": [],
            "assumptions": ["fixture_assumption"],
            "branches": {},
        },
        "suspicious_regions": list(suspicious_regions or [item.to_dict() for item in alignment_result.suspicious_regions]),
        "alignment_status": "PARTIAL" if suspicious_regions else alignment_result.verdict,
    }


def _always_failing_replay(scenario_id: str = "s0") -> list[ReplayResult]:
    baseline = Trace(
        events=[Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", phase="RUNTIME")],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[Event(ts=1.0, provider="HA", op="CLOUD_OP", target="sensor.vdev", phase="RUNTIME")],
        meta={"variant": "optimized"},
    )
    return [
        ReplayResult(
            scenario_id=scenario_id,
            baseline_trace=baseline,
            optimized_trace=optimized,
            runtime_artifacts=_counterexample_runtime_artifacts(baseline, optimized, _target()),
        )
    ]


def _order_violation_replay(scenario_id: str = "s_order") -> list[ReplayResult]:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="BLE", op="BLE_GATT_OP", target="A1", phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", phase="RUNTIME"),
            Event(ts=2.0, provider="BLE", op="BLE_GATT_OP", target="A1", phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )
    return [
        ReplayResult(
            scenario_id=scenario_id,
            baseline_trace=baseline,
            optimized_trace=optimized,
            runtime_artifacts=_counterexample_runtime_artifacts(
                baseline,
                optimized,
                _target(),
                suspicious_regions=[{"region_id": "sr_order", "reason": "order_gap"}],
            ),
        )
    ]


def _unfocused_diff_replay(scenario_id: str = "s_unfocused") -> list[ReplayResult]:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/b", phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )
    return [
        ReplayResult(
            scenario_id=scenario_id,
            baseline_trace=baseline,
            optimized_trace=optimized,
            runtime_artifacts=_counterexample_runtime_artifacts(baseline, optimized, _target()),
        )
    ]


def _equal_trace_with_suspicious_regions(scenario_id: str = "s_equal_sr") -> list[ReplayResult]:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="BLE", op="BLE_GATT_OP", target="ble:demo", phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="BLE", op="BLE_GATT_OP", target="ble:demo", phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )
    return [
        ReplayResult(
            scenario_id=scenario_id,
            baseline_trace=baseline,
            optimized_trace=optimized,
            runtime_artifacts=_counterexample_runtime_artifacts(
                baseline,
                optimized,
                _target(),
                suspicious_regions=[{"region_id": "sr_equal", "reason": "alignment_gap"}],
            ),
        )
    ]


def _target() -> OptimizationTarget:
    return OptimizationTarget(
        meta={"spec_version": "0.1", "vdev_id": "rollback_test", "name": "Rollback Test"},
        source_scope={"files": ["/tmp/fake.py"], "domains": ["demo"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "type": "read",
                "protocol": "BLE",
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"},
                "critical": True,
                "marker_hints": ["BLE_OP"],
            },
            {
                "action_id": "A2",
                "type": "write",
                "protocol": "HA",
                "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a2"},
                "critical": True,
                "marker_hints": ["STATE_WRITE"],
            },
        ],
        target_anchors={"entities": ["sensor.vdev"]},
        entrypoint={"kind": "ha_service", "service": {"domain": "floweaver", "name": "run"}},
        objectives={"primary": "minimize_tail_latency"},
        constraints={"optimization_knobs": {"allow_concurrency": True, "max_concurrency": {"total": 3}}},
        validation={"differential_tests": {"enabled": True}, "observation": {"canonicalization_version": "v2"}},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=["A1", "A2"],
    )


def _dag() -> TypedDAG:
    mssu_a = MSSU(
        mssu_id="m1",
        mssu_type="ACT",
        phase="RUNTIME",
        node_ids=["n1"],
        side_effect_sig={"ble_op"},
        action_refs=["A1"],
        critical=True,
    )
    mssu_b = MSSU(
        mssu_id="m2",
        mssu_type="UPDATE",
        phase="RUNTIME",
        node_ids=["n2"],
        side_effect_sig={"state_write"},
        action_refs=["A2"],
        critical=True,
    )
    return TypedDAG(
        nodes={"m1": mssu_a, "m2": mssu_b},
        hard_edges=[],
        soft_constraints=[
            SoftConstraint(
                kind="MIN_GAP",
                scope=["m1", "m2"],
                params={"rule_id": "r1"},
                guard="true",
                fallback="preserve_action_order",
            )
        ],
        resources={},
    )


def _profile_rules() -> list[Rule]:
    profile = HAPProfile(
        profile_id="test_profile",
        schema_version=PROFILE_SCHEMA_VERSION,
        created_at=now_utc_iso(),
        provenance={},
        marker_detectors=[],
        lifecycle_templates=[],
        rules=[
            Rule(
                rule_id="r1",
                title="test rule",
                category="cleanup",
                status=RuleStatus.SOFT.value,
                marker_hints=["STATE_WRITE"],
                soft_constraint_templates=[{"kind": "MIN_GAP"}],
                evidence_ids=["DOC_1"],
            )
        ],
    )
    return profile.rules


def _guarded_profile_rules() -> list[Rule]:
    return [
        Rule(
            rule_id="r_guarded",
            title="guarded cleanup rule",
            category="cleanup",
            status=RuleStatus.SOFT.value,
            marker_hints=["STATE_WRITE"],
            soft_constraint_templates=[{"kind": "MIN_GAP"}],
            evidence_ids=["DOC_2"],
            guard="recent_429_rate_high",
        )
    ]


def test_m6_level2_keeps_cleanup_rule_soft_and_uses_compare_config(tmp_path: Path) -> None:
    target = _target()
    dag = _dag()
    rules = _profile_rules()

    initial_plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A2", "A1"]],
                constraints=[],
                session_policy={"reuse": True, "max_age_s": 20},
                rate_policy={"max_qps": 5.0, "batch_size": 2},
                guards=[],
                fallback={},
            )
        ],
        meta={"policy": {"max_parallel": 3, "ble_parallel": 2, "cloud_parallel": 2}},
    )

    scheduler = CrossProtocolScheduler()
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))

    def replay_with_plan(_plan: ExecutionPlan) -> list[ReplayResult]:
        return _always_failing_replay("scenario_x")

    def replan_with_dag(candidate_dag: TypedDAG) -> ExecutionPlan:
        return scheduler.schedule(candidate_dag, optimization_target=target)

    result = trust.evaluate(
        replay_results=_always_failing_replay("scenario_x"),
        dag=dag,
        rules=rules,
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=replay_with_plan,
        replan_with_dag=replan_with_dag,
    )

    assert result.rollback_log
    kinds = [str(item.get("kind")) for item in result.rollback_log]
    assert kinds[: len(LEVEL1_STRATEGIES)] == ["plan_patch"] * len(LEVEL1_STRATEGIES)
    assert any(item.get("kind") == "rule_patch" for item in result.rollback_log)
    assert not any(item.get("kind") == "constraint_patch" for item in result.rollback_log)

    strategies = [str(item.get("strategy")) for item in result.rollback_log if item.get("kind") == "plan_patch"]
    assert strategies == LEVEL1_STRATEGIES

    rule_patch = next(item for item in result.rollback_log if item.get("kind") == "rule_patch")
    assert "r1" not in rule_patch.get("disabled_rule_ids", [])
    assert "r1" in rule_patch.get("tightened_rule_ids", [])
    assert result.final_rules[0].status == RuleStatus.SOFT.value
    assert result.final_rules[0].guard == "rollback_safe_mode"
    assert result.certificate.canonicalization_version == "v2"
    assert result.certificate.plan_summary["batch_count"] >= 1
    assert "compare_meta" in result.certificate.differential_summary

    decisions = result.hardening_decisions
    assert "rollback" in decisions
    assert Path(tmp_path / "rule_hardening_decisions.json").exists()
    assert Path(tmp_path / "rollback_log.json").exists()


def test_m6_level3_only_triggers_on_order_counterexample(tmp_path: Path) -> None:
    target = _target()
    dag = _dag()
    rules = _profile_rules()
    scheduler = CrossProtocolScheduler()
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))

    initial_plan = scheduler.schedule(dag, optimization_target=target)

    def replay_with_plan(_plan: ExecutionPlan) -> list[ReplayResult]:
        return _order_violation_replay("scenario_order")

    def replan_with_dag(candidate_dag: TypedDAG) -> ExecutionPlan:
        return scheduler.schedule(candidate_dag, optimization_target=target)

    result = trust.evaluate(
        replay_results=_order_violation_replay("scenario_order"),
        dag=dag,
        rules=rules,
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=replay_with_plan,
        replan_with_dag=replan_with_dag,
    )

    assert any(item.get("kind") == "constraint_patch" for item in result.rollback_log)
    assert any(cex.diff_summary.get("kind") == "order_violation" for cex in result.counterexamples)
    assert any(cex.diff_summary.get("inferred_by") for cex in result.counterexamples)
    assert any(cex.diff_summary.get("violated_property") for cex in result.counterexamples)
    assert any(isinstance(cex.diff_summary.get("divergence_point"), dict) for cex in result.counterexamples)


def test_m6_level3_constraint_patch_uses_target_order_for_pure_snapshot_reads(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "snapshot_order_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "BLE", "critical": True, "target": {"kind": "ble_device", "id": "ble:a1"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a1"}},
            {"action_id": "A4", "protocol": "CLOUD", "critical": True, "target": {"kind": "cloud_endpoint", "id": "cloud:a4"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a4"}},
            {"action_id": "A8", "protocol": "HA", "critical": True, "target": {"kind": "ha_entity", "entity_id": "sensor.demo"}, "exec": {"kind": "ha_service_call", "domain": "demo", "service": "a8"}},
        ],
        critical_action_ids=["A1", "A4", "A8"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m4": MSSU(mssu_id="m4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4"),
            "m8": MSSU(mssu_id="m8", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n8"], action_refs=["A8"], primary_action_ref="A8"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A4"], ["A1"], ["A8"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex1",
            scenario_id="s1",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={"kind": "order_violation"},
        )
    ]

    patched_dag, patch = trust._apply_level3_constraint_patch(dag, plan, target, counterexamples)

    assert patch is not None
    hard_pairs = {(edge.src_mssu, edge.dst_mssu) for edge in patched_dag.hard_edges}
    assert hard_pairs == set()
    soft_rows = [
        (constraint.kind, list(constraint.scope), dict(constraint.params), constraint.fallback)
        for constraint in patched_dag.soft_constraints
    ]
    assert (
        SoftConstraintKind.SOFT_ORDER.value,
        ["A1", "A4"],
        {"reason": "m6_level3_action_order", "source": "m6", "ordered_scope": ["A1", "A4"]},
        "preserve_action_order",
    ) in soft_rows
    assert (
        SoftConstraintKind.SOFT_ORDER.value,
        ["A4", "A8"],
        {"reason": "m6_level3_action_order", "source": "m6", "ordered_scope": ["A4", "A8"]},
        "preserve_action_order",
    ) in soft_rows


def test_m6_level1_disable_batching_reuses_target_order_for_singleton_plan(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "disable_batching_order_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "CLOUD", "critical": True},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
        ],
        critical_action_ids=["A1", "A2", "A3"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="b0",
                parallel_groups=[["A2", "A3"], ["A1"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[],
            )
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_disable_batching",
            scenario_id="s_disable_batching",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={"kind": "order_violation"},
        )
    ]

    patched_plan, patch = trust._apply_level1_patch(plan, 2, target, counterexamples)

    assert patch is not None
    assert patch["strategy"] == "disable_batching"
    assert [batch.parallel_groups for batch in patched_plan.ordered_batches] == [
        [["A1"]],
        [["A2"]],
        [["A3"]],
    ]


def test_m6_level1_reduce_parallelism_preserves_group_boundaries(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "reduce_parallelism_group_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "CLOUD", "critical": True},
            {"action_id": "A2", "protocol": "CLOUD", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
            {"action_id": "A4", "protocol": "LOCAL", "critical": True},
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="b0",
                parallel_groups=[["A1", "A2"], ["A3", "A4"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[],
            )
        ],
        meta={"policy": {"max_parallel": 2, "cloud_parallel": 2, "local_parallel": 2}},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_reduce_parallelism",
            scenario_id="s_reduce_parallelism",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={"kind": "timeout"},
        )
    ]

    patched_plan, patch = trust._apply_level1_patch(plan, 0, target, counterexamples)

    assert patch is not None
    assert patch["strategy"] == "reduce_parallelism"
    assert patched_plan.ordered_batches[0].parallel_groups == [["A1"], ["A2"], ["A3"], ["A4"]]


def test_m6_level3_constraint_patch_skips_parallel_pairs_inside_same_group(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "parallel_scope_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "LOCAL", "critical": True},
            {"action_id": "A2", "protocol": "LOCAL", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
            {"action_id": "A4", "protocol": "HA", "critical": True, "target": {"kind": "ha_entity", "entity_id": "sensor.overall"}},
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2"),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3"),
            "m4": MSSU(mssu_id="m4", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A1", "A2", "A3"], ["A4"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_parallel",
            scenario_id="s_parallel",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={"kind": "order_violation"},
        )
    ]

    patched_dag, patch = trust._apply_level3_constraint_patch(dag, plan, target, counterexamples)

    assert patch is not None
    soft_rows = [
        (constraint.kind, tuple(sorted(constraint.scope)), dict(constraint.params), constraint.fallback)
        for constraint in patched_dag.soft_constraints
    ]
    assert not any(scope == ("A1", "A2") for _, scope, _, _ in soft_rows)
    assert not any(scope == ("A2", "A3") for _, scope, _, _ in soft_rows)
    assert any(scope == ("A3", "A4") for _, scope, _, _ in soft_rows)


def test_m6_level3_constraint_patch_keeps_parallel_to_serial_boundary_inside_group(
    tmp_path: Path,
) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "parallel_serial_boundary_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "LOCAL", "critical": True},
            {"action_id": "A2", "protocol": "LOCAL", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
        ],
        critical_action_ids=["A1", "A2", "A3"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2"),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="b0",
                parallel_groups=[["A1", "A2", "A3"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[
                    {
                        "kind": SoftConstraintKind.SOFT_ORDER.value,
                        "scope": ["A2"],
                        "action": "preserve_action_order",
                        "params": {"reason": "candidate:CONTROL_DEP"},
                    }
                ],
            ),
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_boundary",
            scenario_id="s_boundary",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={"kind": "order_violation"},
        )
    ]

    patched_dag, patch = trust._apply_level3_constraint_patch(dag, plan, target, counterexamples)

    assert patch is not None
    soft_rows = [
        (constraint.kind, tuple(sorted(constraint.scope)), dict(constraint.params), constraint.fallback)
        for constraint in patched_dag.soft_constraints
    ]
    assert not any(scope == ("A1", "A3") for _, scope, _, _ in soft_rows)
    assert any(scope == ("A2", "A3") for _, scope, _, _ in soft_rows)


def test_m6_evaluate_level3_uses_structured_reference_plan_not_last_level1_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "level3_reference_plan_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "LOCAL", "critical": True},
            {"action_id": "A2", "protocol": "LOCAL", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
            {"action_id": "A4", "protocol": "HA", "critical": True, "target": {"kind": "ha_entity", "entity_id": "sensor.overall"}},
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2"),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3"),
            "m4": MSSU(mssu_id="m4", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    structured_plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A1", "A2", "A3"], ["A4"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    degraded_plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A1"], ["A2"], ["A3"], ["A4"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    captured: dict[str, object] = {}

    def fake_apply_level1_patch(_plan, strategy_index, _target, _counterexamples):
        return degraded_plan, {
            "kind": "plan_patch",
            "level": "LEVEL_1",
            "strategy": LEVEL1_STRATEGIES[strategy_index],
            "changes": [],
            "reason": {},
        }

    def fake_apply_level2_rule_patch(current_rules, _counterexamples):
        return current_rules, None

    def fake_apply_level3_constraint_patch(current_dag, plan, _target, _counterexamples):
        captured["parallel_groups"] = [list(group) for group in plan.ordered_batches[0].parallel_groups]
        return current_dag, {
            "kind": "constraint_patch",
            "level": "LEVEL_3",
            "changes": [],
            "reason": {},
        }

    monkeypatch.setattr(trust, "_apply_level1_patch", fake_apply_level1_patch)
    monkeypatch.setattr(trust, "_apply_level2_rule_patch", fake_apply_level2_rule_patch)
    monkeypatch.setattr(trust, "_apply_level3_constraint_patch", fake_apply_level3_constraint_patch)

    result = trust.evaluate(
        replay_results=_order_violation_replay("scenario_level3_ref"),
        dag=dag,
        rules=[],
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=structured_plan,
        replay_with_plan=lambda _plan: _order_violation_replay("scenario_level3_ref"),
        replan_with_dag=lambda _dag: structured_plan,
    )

    assert captured["parallel_groups"] == [["A1", "A2", "A3"], ["A4"]]
    assert result.rollback_log


def test_m6_level3_constraint_patch_scopes_to_counterexample_action_neighborhood(
    tmp_path: Path,
) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "level3_implicated_scope_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "LOCAL", "critical": True, "target": {"id": "local:a1"}},
            {"action_id": "A2", "protocol": "LOCAL", "critical": True, "target": {"id": "local:a2"}},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True, "target": {"id": "local:a3"}},
            {"action_id": "A4", "protocol": "HA", "critical": True, "target": {"kind": "ha_entity", "entity_id": "sensor.overall"}},
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2"),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3"),
            "m4": MSSU(mssu_id="m4", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A1"], ["A2"], ["A3"], ["A4"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_implicated",
            scenario_id="s_implicated",
            violated_assertion="observable_semantic_equivalence",
            culprit_ids=["RUNTIME:LOCAL:LOCAL_API_READ:local:a3"],
            diff_summary={
                "kind": "order_violation",
                "hunks": [
                    {
                        "anchor": "RUNTIME:LOCAL:LOCAL_API_READ:local:a3",
                        "baseline_ops": ["RUNTIME:LOCAL:LOCAL_API_READ:local:a3"],
                        "optimized_ops": [],
                        "severity": "MEDIUM",
                    }
                ],
            },
        )
    ]

    patched_dag, patch = trust._apply_level3_constraint_patch(dag, plan, target, counterexamples)

    assert patch is not None
    soft_scopes = {tuple(sorted(constraint.scope)) for constraint in patched_dag.soft_constraints}
    assert ("A1", "A2") not in soft_scopes
    assert ("A2", "A3") in soft_scopes
    assert ("A3", "A4") in soft_scopes


def test_m6_level3_constraint_patch_uses_target_order_for_post_control_verification(
    tmp_path: Path,
) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "verification_phase_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "CLOUD",
                "critical": True,
                "target": {"id": "tuya:light.scene.turn_on"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "turn_on"},
            },
            {
                "action_id": "A2",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": True,
                "target": {"id": "tuya:light.scene.status"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "status"},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "critical": True,
                "idempotent": True,
                "target": {"id": "ecobee:thermostat.home_1"},
                "exec": {"kind": "ha_service_call", "domain": "climate", "service": "read_runtime"},
            },
            {
                "action_id": "A4",
                "protocol": "LOCAL",
                "critical": True,
                "target": {"id": "hue:bridge_1:scene_group"},
                "exec": {"kind": "ha_service_call", "domain": "light", "service": "get_state"},
            },
            {
                "action_id": "A5",
                "protocol": "HA",
                "critical": True,
                "target": {"kind": "ha_entity", "entity_id": "sensor.overall"},
                "exec": {"kind": "ha_service_call", "domain": "sensor", "service": "publish"},
            },
        ],
        critical_action_ids=["A1", "A2", "A3", "A4", "A5"],
    )
    dag = TypedDAG(
        nodes={
            "m1": MSSU(mssu_id="m1", mssu_type="ACT", phase="RUNTIME", node_ids=["n1"], action_refs=["A1"], primary_action_ref="A1"),
            "m2": MSSU(mssu_id="m2", mssu_type="ACT", phase="RUNTIME", node_ids=["n2"], action_refs=["A2"], primary_action_ref="A2"),
            "m3": MSSU(mssu_id="m3", mssu_type="ACT", phase="RUNTIME", node_ids=["n3"], action_refs=["A3"], primary_action_ref="A3"),
            "m4": MSSU(mssu_id="m4", mssu_type="ACT", phase="RUNTIME", node_ids=["n4"], action_refs=["A4"], primary_action_ref="A4"),
            "m5": MSSU(mssu_id="m5", mssu_type="UPDATE", phase="RUNTIME", node_ids=["n5"], action_refs=["A5"], primary_action_ref="A5"),
        },
        hard_edges=[],
        soft_constraints=[],
        resources={},
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(batch_id="b0", parallel_groups=[["A1"], ["A2"], ["A4"], ["A3"], ["A5"]], constraints=[], session_policy={}, rate_policy={}, guards=[], fallback=[]),
        ],
        meta={},
    )
    counterexamples = [
        CounterExample(
            counterexample_id="cex_verification",
            scenario_id="s_verification",
            violated_assertion="observable_semantic_equivalence",
            culprit_ids=["RUNTIME:CLOUD:CLOUD_STATUS_CALL:ecobee:thermostat.home_1"],
            diff_summary={
                "kind": "order_violation",
                "hunks": [
                    {
                        "anchor": "RUNTIME:CLOUD:CLOUD_STATUS_CALL:ecobee:thermostat.home_1",
                        "baseline_ops": ["RUNTIME:CLOUD:CLOUD_STATUS_CALL:ecobee:thermostat.home_1"],
                        "optimized_ops": [],
                        "severity": "MEDIUM",
                    }
                ],
            },
        )
    ]

    patched_dag, patch = trust._apply_level3_constraint_patch(dag, plan, target, counterexamples)

    assert patch is not None
    soft_rows = [
        (constraint.kind, tuple(sorted(constraint.scope)), dict(constraint.params), constraint.fallback)
        for constraint in patched_dag.soft_constraints
    ]
    assert (
        SoftConstraintKind.SOFT_ORDER.value,
        ("A2", "A3"),
        {"reason": "m6_level3_action_order", "source": "m6", "ordered_scope": ["A2", "A3"]},
        "preserve_action_order",
    ) in soft_rows
    assert (
        SoftConstraintKind.SOFT_ORDER.value,
        ("A3", "A4"),
        {"reason": "m6_level3_action_order", "source": "m6", "ordered_scope": ["A3", "A4"]},
        "preserve_action_order",
    ) in soft_rows
    assert not any(
        scope == ("A3", "A4") and params.get("ordered_scope") == ["A4", "A3"]
        for _, scope, params, _ in soft_rows
    )


def test_m6_action_phase_map_uses_last_control_boundary_for_intermediate_reads() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "phase_map_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {
                "action_id": "A1",
                "protocol": "BLE",
                "target": {"id": "ble:switchbot:curtain"},
                "exec": {"kind": "ha_service_call", "service": "set_cover_position"},
            },
            {
                "action_id": "A2",
                "protocol": "BLE",
                "target": {"id": "ble:xiaomi_ble:motion"},
                "exec": {"kind": "ha_service_call", "service": "read_sensor"},
            },
            {
                "action_id": "A3",
                "protocol": "CLOUD",
                "target": {"id": "ecobee:thermostat.office.set_temperature"},
                "exec": {"kind": "ha_service_call", "service": "set_temperature"},
            },
            {
                "action_id": "A4",
                "protocol": "CLOUD",
                "idempotent": True,
                "target": {"id": "ecobee:thermostat.office"},
                "exec": {"kind": "ha_service_call", "service": "read_runtime"},
            },
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )

    assert TrustLayer._action_phase_map(target) == {
        "A1": "control",
        "A2": "pre_control_acquisition",
        "A3": "control",
        "A4": "post_control_verification",
    }


def test_m6_plan_execution_order_and_parallel_scopes_follow_group_execution_semantics() -> None:
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1", "A2", "A3"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[
                    {
                        "kind": SoftConstraintKind.SOFT_ORDER.value,
                        "scope": ["A2"],
                        "action": "preserve_action_order",
                        "params": {"reason": "candidate:CONTROL_DEP"},
                    }
                ],
            )
        ],
        meta={},
    )

    assert TrustLayer._parallel_action_scopes(plan) == []
    assert TrustLayer._plan_execution_order(plan) == ["A1", "A2", "A3"]


def test_m6_level1_enforce_min_gap_no_overlap_scopes_transport_fallback_to_ble_only(
    tmp_path: Path,
) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "ble_scope_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "BLE", "critical": True},
            {"action_id": "A2", "protocol": "BLE", "critical": True},
            {"action_id": "A3", "protocol": "LOCAL", "critical": True},
            {"action_id": "A4", "protocol": "LOCAL", "critical": True},
        ],
        critical_action_ids=["A1", "A2", "A3", "A4"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1", "A2"], ["A3", "A4"]],
                constraints=[],
                session_policy={},
                rate_policy={"max_qps": 5.0, "batch_size": 2},
                guards=[],
                fallback=[],
            )
        ],
        meta={},
    )

    patched, patch = trust._apply_level1_patch(
        plan,
        LEVEL1_STRATEGIES.index("enforce_min_gap_no_overlap"),
        target,
        [],
    )

    assert patch is not None
    fallback_rows = patched.ordered_batches[0].fallback
    transport_rows = [
        row
        for row in fallback_rows
        if row["kind"] in {SoftConstraintKind.MIN_GAP.value, SoftConstraintKind.NO_OVERLAP.value}
    ]
    assert transport_rows
    assert all(row["scope"] == ["A1", "A2"] for row in transport_rows)
    assert TrustLayer._parallel_action_scopes(patched) == [["A3", "A4"]]
    assert TrustLayer._plan_execution_order(patched) == ["A1", "A2", "A3", "A4"]


def test_m6_trace_compare_tolerates_reorder_within_parallel_action_scope() -> None:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:group_a", params_abst={"action_id": "A1"}, phase="RUNTIME"),
            Event(ts=2.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:group_b", params_abst={"action_id": "A2"}, phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:group_b", params_abst={"action_id": "A2"}, phase="RUNTIME"),
            Event(ts=2.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:group_a", params_abst={"action_id": "A1"}, phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )
    config = TraceCompareConfig(parallel_action_scopes=[["A1", "A2"]])

    diff = compare_traces(baseline, optimized, config=config)

    assert diff.strict_equal is False
    assert diff.tolerant_equal is True


def test_m6_counterexample_signature_is_order_stable() -> None:
    hunks = [
        DiffHunk(
            anchor="RUNTIME:BLE:BLE_GATT_OP:A1",
            baseline_ops=["RUNTIME:BLE:BLE_GATT_OP:A1"],
            optimized_ops=["RUNTIME:HA:STATE_WRITE:sensor.vdev"],
            severity="MEDIUM",
        ),
        DiffHunk(
            anchor="RUNTIME:HA:STATE_WRITE:sensor.vdev",
            baseline_ops=["RUNTIME:HA:STATE_WRITE:sensor.vdev"],
            optimized_ops=["RUNTIME:BLE:BLE_GATT_OP:A1"],
            severity="HIGH",
        ),
    ]

    signature_a = TrustLayer._counterexample_signature(hunks)
    signature_b = TrustLayer._counterexample_signature(list(reversed(hunks)))
    assert signature_a == signature_b


def test_m6_order_type_fallback_infers_from_hunks_without_kind() -> None:
    cex = CounterExample(
        counterexample_id="cex_demo",
        scenario_id="s0",
        violated_assertion="observable_semantic_equivalence",
        diff_summary={
            "hunks": [
                {
                    "anchor": "RUNTIME:BLE:BLE_GATT_OP:A1",
                    "baseline_ops": [
                        "RUNTIME:BLE:BLE_GATT_OP:A1",
                        "RUNTIME:HA:STATE_WRITE:sensor.vdev",
                    ],
                    "optimized_ops": [
                        "RUNTIME:HA:STATE_WRITE:sensor.vdev",
                        "RUNTIME:BLE:BLE_GATT_OP:A1",
                    ],
                    "severity": "HIGH",
                }
            ]
        },
    )
    assert TrustLayer._is_order_type_counterexample(cex)


def test_m6_counterexample_layer_runs_even_without_focused_hunks(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    strict_pass, tolerant_pass, counterexamples, _ = trust._summarize_replay(
        _unfocused_diff_replay(),
        _target(),
        trust._trace_compare_config(_target()),
    )

    assert strict_pass == 0
    assert tolerant_pass == 0
    assert len(counterexamples) == 1
    assert counterexamples[0].diff_summary.get("violated_property") == "TRACE_MISMATCH"


def test_m6_summarize_replay_uses_plan_parallel_scopes_for_tolerant_equality(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = OptimizationTarget(
        meta={"vdev_id": "parallel_scope_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[
            {"action_id": "A1", "protocol": "LOCAL", "critical": True, "target": {"kind": "local_endpoint", "id": "hue:a1"}, "exec": {"kind": "ha_service_call", "service": "get_state"}},
            {"action_id": "A2", "protocol": "LOCAL", "critical": True, "target": {"kind": "local_endpoint", "id": "hue:a2"}, "exec": {"kind": "ha_service_call", "service": "get_state"}},
        ],
        critical_action_ids=["A1", "A2"],
    )
    plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1", "A2"]],
                constraints=[],
                session_policy={},
                rate_policy={},
                guards=[],
                fallback=[],
            )
        ],
        meta={},
    )
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:a1", params_abst={"action_id": "A1"}, phase="RUNTIME"),
            Event(ts=2.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:a2", params_abst={"action_id": "A2"}, phase="RUNTIME"),
        ],
        meta={"variant": "baseline"},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:a2", params_abst={"action_id": "A2"}, phase="RUNTIME"),
            Event(ts=2.0, provider="LOCAL", op="LOCAL_API_READ", target="hue:a1", params_abst={"action_id": "A1"}, phase="RUNTIME"),
        ],
        meta={"variant": "optimized"},
    )
    rows = [
        ReplayResult(
            scenario_id="s_parallel",
            baseline_trace=baseline,
            optimized_trace=optimized,
            runtime_artifacts=_counterexample_runtime_artifacts(baseline, optimized, target),
        )
    ]

    strict_pass, tolerant_pass, counterexamples, _ = trust._summarize_replay(
        rows,
        target,
        trust._trace_compare_config(target, plan),
    )

    assert strict_pass == 0
    assert tolerant_pass == 1
    assert counterexamples == []


def test_m6_level2_compounds_existing_guard_and_exports_runtime_policy_summary(tmp_path: Path) -> None:
    target = _target()
    dag = _dag()
    rules = _guarded_profile_rules()
    scheduler = CrossProtocolScheduler()
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))

    initial_plan = scheduler.schedule(dag, optimization_target=target)

    runtime_artifacts = {
        "runtime_policy_snapshot": [{"batch_id": "batch_000", "max_qps": 1.5}],
        "forced_fallbacks_applied": [{"batch_id": "batch_000", "fallbacks": [{"kind": "FORCED_PICK"}]}],
        "event_trace": [
            {"op": "RATE_DOWNGRADE"},
            {"op": "BATCH_COALESCE_WAIT"},
            {"op": "BATCH_COALESCE_WAIT"},
        ],
    }

    def replay_with_plan(_plan: ExecutionPlan) -> list[ReplayResult]:
        rows = _always_failing_replay("scenario_guarded")
        rows[0].runtime_artifacts.update(runtime_artifacts)
        return rows

    def replan_with_dag(candidate_dag: TypedDAG) -> ExecutionPlan:
        return scheduler.schedule(candidate_dag, optimization_target=target)

    seed_rows = _always_failing_replay("scenario_guarded")
    seed_rows[0].runtime_artifacts.update(runtime_artifacts)

    result = trust.evaluate(
        replay_results=seed_rows,
        dag=dag,
        rules=rules,
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=replay_with_plan,
        replan_with_dag=replan_with_dag,
    )

    assert result.final_rules[0].guard == "(recent_429_rate_high) AND rollback_safe_mode"
    summary_rows = result.certificate.differential_summary.get("runtime_policy_summary", [])
    assert summary_rows and summary_rows[0]["scenario_id"] == "scenario_guarded"
    assert summary_rows[0]["trace_counts"]["BATCH_COALESCE_WAIT"] == 2


def test_m6_fails_fast_when_counterexample_inputs_missing(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    rows = _always_failing_replay("scenario_missing")
    rows[0].runtime_artifacts = {}

    try:
        trust._summarize_replay(
            rows,
            _target(),
            trust._trace_compare_config(_target()),
        )
    except ValueError as exc:
        assert "missing counterexample inputs" in str(exc)
    else:
        raise AssertionError("expected counterexample input validation failure")


def test_m6_focused_hunks_use_structured_focus_instead_of_short_substring() -> None:
    target = OptimizationTarget(
        meta={"vdev_id": "focus_test"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[],
        target_anchors={"entities": ["id"], "anchor_ops": ["CLOUD_OP"]},
    )
    hunks = [
        DiffHunk(
            anchor="RUNTIME:CLOUD:CLOUD_HTTP_CALL:tuya:device.control",
            baseline_ops=["RUNTIME:CLOUD:CLOUD_HTTP_CALL:tuya:device.control"],
            optimized_ops=["RUNTIME:CLOUD:CLOUD_HTTP_CALL:tuya:device.control"],
            severity="MEDIUM",
        ),
        DiffHunk(
            anchor="RUNTIME:HA:STATE_WRITE:device",
            baseline_ops=["RUNTIME:HA:STATE_WRITE:device"],
            optimized_ops=["RUNTIME:HA:STATE_WRITE:device"],
            severity="HIGH",
        ),
    ]

    focused = TrustLayer._focused_hunks(hunks, target)
    assert len(focused) == 2
    cloud_only = [
        hunk
        for hunk in focused
        if "CLOUD_HTTP_CALL" in " ".join(hunk.baseline_ops + hunk.optimized_ops)
    ]
    assert cloud_only


def test_m6_level2_only_tightens_involved_rules(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    rules = [
        Rule(
            rule_id="r_hit",
            title="hit",
            category="cleanup",
            status=RuleStatus.SOFT.value,
            marker_hints=["STATE_WRITE"],
            evidence_ids=["DOC_1"],
            guard="true",
        ),
        Rule(
            rule_id="r_miss",
            title="miss",
            category="cleanup",
            status=RuleStatus.SOFT.value,
            marker_hints=["BLE_CONNECT"],
            evidence_ids=["DOC_2"],
            guard="true",
        ),
    ]
    counterexamples = [
        CounterExample(
            counterexample_id="cex1",
            scenario_id="s0",
            violated_assertion="observable_semantic_equivalence",
            diff_summary={
                "kind": "semantic_delta",
                "hunks": [
                    {
                        "anchor": "RUNTIME:HA:STATE_WRITE:sensor.vdev",
                        "baseline_ops": ["RUNTIME:HA:STATE_WRITE:sensor.vdev"],
                        "optimized_ops": ["RUNTIME:CLOUD:CLOUD_HTTP_CALL:tuya:device.control"],
                        "severity": "HIGH",
                    }
                ],
            },
        )
    ]

    patched_rules, patch = trust._apply_level2_rule_patch(rules, counterexamples)
    assert patch is not None
    assert next(rule for rule in patched_rules if rule.rule_id == "r_hit").guard == "rollback_safe_mode"
    assert next(rule for rule in patched_rules if rule.rule_id == "r_miss").guard == "true"


def test_m6_evaluate_writes_progress_and_streaming_outputs(tmp_path: Path, monkeypatch) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = _target()
    dag = _dag()
    initial_plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1"], ["A2"]],
                constraints=[],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 1.0},
                guards=[],
                fallback=[],
            )
        ],
        meta={"policy": {"max_parallel": 1}, "node_kind": "action_id"},
    )

    class _Witness:
        verdict = "DIFF_FOUND"
        violated_property = "TRACE_MISMATCH"
        divergence_point = {"anchor": "STATE_WRITE"}
        minimal_conditions = []
        suspicious_region_id = None
        refinement_hint = "fixture"
        baseline_trace_prefix = []
        optimized_trace_prefix = []
        baseline_state_at_divergence = {}
        optimized_state_at_divergence = {}
        environment_assumptions = {}
        input_assumptions = {}

    monkeypatch.setattr("optimizer.m6_trust.generate_counterexample", lambda **_: _Witness())

    seed_rows = _always_failing_replay("scenario_stream")
    result = trust.evaluate(
        replay_results=seed_rows,
        dag=dag,
        rules=_profile_rules(),
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=lambda _plan: seed_rows,
        replan_with_dag=lambda _dag: initial_plan,
        rollback_max_steps=1,
    )

    assert result.counterexamples
    progress = load_json(tmp_path / "m6_progress.json")
    partial = load_json(tmp_path / "execution_certificate.partial.json")
    trace_rows = load_jsonl(tmp_path / "m6_trace_compare.jsonl")
    partial_counterexamples = load_jsonl(tmp_path / "counterexamples.partial.jsonl")

    assert progress["phase"] == "finalize"
    assert partial["status"] == "COMPLETED"
    assert trace_rows
    assert partial_counterexamples
    assert "alignment_status" in trace_rows[0]
    assert "suspicious_region_count" in trace_rows[0]


def test_m6_evaluate_emits_validation_stats_json(tmp_path: Path, monkeypatch) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = _target()
    dag = _dag()
    initial_plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1"], ["A2"]],
                constraints=[],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 1.0},
                guards=[],
                fallback=[],
            )
        ],
        meta={"policy": {"max_parallel": 1}, "node_kind": "action_id"},
    )

    class _Witness:
        verdict = "DIFF_FOUND"
        violated_property = "TRACE_MISMATCH"
        divergence_point = {"anchor": "STATE_WRITE"}
        minimal_conditions = []
        suspicious_region_id = None
        refinement_hint = "fixture"
        baseline_trace_prefix = []
        optimized_trace_prefix = []
        baseline_state_at_divergence = {}
        optimized_state_at_divergence = {}
        environment_assumptions = {}
        input_assumptions = {}

    monkeypatch.setattr("optimizer.m6_trust.generate_counterexample", lambda **_: _Witness())

    trust.evaluate(
        replay_results=_always_failing_replay("scenario_validation_stats"),
        dag=dag,
        rules=_profile_rules(),
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=lambda _plan: _always_failing_replay("scenario_validation_stats"),
        replan_with_dag=lambda _dag: initial_plan,
        rollback_max_steps=1,
    )

    payload = load_json(tmp_path / "validation_stats.json")
    assert payload["schema_version"] == "validation_stats/v1"
    assert payload["producer"] == "optimizer.m6_trust"
    assert payload["source_contract"]["intended_upstream"] == "M6 trust aggregation"
    assert len(payload["rules"]) == len(_profile_rules())
    row = next(item for item in payload["rules"] if item["rule_id"] == "r1")
    assert row["n_matched"] >= 1
    assert row["n_applied"] >= 1
    assert row["n_counterexamples"] >= 1
    assert row["trace_preserved_rate"] is not None
    assert row["final_state_preserved_rate"] is not None
    assert row["resource_protocol_preserved_rate"] is not None
    assert row["last_updated_at"]
    assert row["m6_alignment"]["matched_scenarios"] == ["scenario_validation_stats"]


def test_m6_validation_stats_aligns_with_trace_compare_for_tolerant_equal_case(tmp_path: Path) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = _target()
    dag = _dag()
    initial_plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1"], ["A2"]],
                constraints=[],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 1.0},
                guards=[],
                fallback=[],
            )
        ],
        meta={"policy": {"max_parallel": 1}, "node_kind": "action_id"},
    )

    result = trust.evaluate(
        replay_results=_equal_trace_with_suspicious_regions("scenario_equal_stats"),
        dag=dag,
        rules=_profile_rules(),
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=lambda _plan: _equal_trace_with_suspicious_regions("scenario_equal_stats"),
        replan_with_dag=lambda _dag: initial_plan,
        rollback_max_steps=1,
    )

    assert result.summary["strict_pass"] == 1
    payload = load_json(tmp_path / "validation_stats.json")
    row = next(item for item in payload["rules"] if item["rule_id"] == "r1")
    assert row["trace_preserved_rate"] == 1.0
    assert row["final_state_preserved_rate"] == 1.0
    assert row["resource_protocol_preserved_rate"] == 1.0
    assert row["m6_alignment"]["alignment_status_counts"] == {"PROVED": 1}
    assert row["m6_alignment"]["resource_preserved_scenarios"] == ["scenario_equal_stats"]


def test_m6_does_not_emit_final_counterexample_for_tolerant_equal_case(tmp_path: Path, monkeypatch) -> None:
    trust = TrustLayer(integration="demo", out_dir=str(tmp_path))
    target = _target()
    dag = _dag()
    initial_plan = ExecutionPlan(
        ordered_batches=[
            Batch(
                batch_id="batch_000",
                parallel_groups=[["A1"], ["A2"]],
                constraints=[],
                session_policy={"reuse": True},
                rate_policy={"max_qps": 1.0},
                guards=[],
                fallback=[],
            )
        ],
        meta={"policy": {"max_parallel": 1}, "node_kind": "action_id"},
    )

    class _Witness:
        verdict = "DIFF_FOUND"
        violated_property = "TRACE_MISMATCH"
        divergence_point = {"anchor": "STATE_WRITE"}
        minimal_conditions = []
        suspicious_region_id = None
        refinement_hint = "fixture"
        baseline_trace_prefix = []
        optimized_trace_prefix = []
        baseline_state_at_divergence = {}
        optimized_state_at_divergence = {}
        environment_assumptions = {}
        input_assumptions = {}

    monkeypatch.setattr("optimizer.m6_trust.generate_counterexample", lambda **_: _Witness())

    result = trust.evaluate(
        replay_results=_equal_trace_with_suspicious_regions(),
        dag=dag,
        rules=_profile_rules(),
        profile_version="test_profile",
        optimization_target=target,
        execution_plan=initial_plan,
        replay_with_plan=lambda _plan: _equal_trace_with_suspicious_regions(),
        replan_with_dag=lambda _dag: initial_plan,
        rollback_max_steps=1,
    )

    assert result.counterexamples == []
    certificate = load_json(tmp_path / "execution_certificate.json")
    trace_rows = load_jsonl(tmp_path / "m6_trace_compare.jsonl")
    assert certificate["differential_summary"]["counterexample_count"] == 0
    assert len(trace_rows) == 1
    assert trace_rows[0]["alignment_status"] == "PROVED"
    assert trace_rows[0]["suspicious_region_count"] == 0
