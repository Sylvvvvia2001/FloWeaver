from dsl.contracts import Event, OptimizationTarget, Trace

from counterexample_layer.api.generate_counterexample import generate_counterexample, generate_counterexample_from_traces
from counterexample_layer.ir.alignment_map import AlignmentItem, AlignmentMap
from counterexample_layer.ir.ir_types import IRNode, IRProgram, IRSummary
from counterexample_layer.ir.summaries import trace_to_ir_program
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from counterexample_layer.witness.witness import CounterexampleVerdict, ViolatedProperty
from runtime.trace import TraceCompareConfig


def _target() -> OptimizationTarget:
    return OptimizationTarget(
        meta={"vdev_id": "cex_demo"},
        source_scope={"files": ["/tmp/fake.py"]},
        vdev_actions=[{"action_id": "A1", "exec": {"kind": "sleep"}}],
        target_anchors={"entities": ["sensor.vdev"], "required_state_writes": ["sensor.vdev"]},
        entrypoint={},
        objectives={},
        constraints={},
        validation={"observation": {"canonicalization_version": "v2"}},
        hard_dependencies=[],
        soft_dependencies=[],
        critical_action_ids=[],
    )


def test_counterexample_layer_finds_trace_mismatch() -> None:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="ENTRY_SETUP", target="entry", phase="SETUP"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="ENTRY_SETUP", target="entry", phase="SETUP"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/device", params_abst={"endpoint": "/v1/device"}, phase="RUNTIME"),
        ],
        meta={},
    )

    witness = generate_counterexample_from_traces(
        baseline_trace=baseline,
        optimized_trace=optimized,
        optimization_target=_target(),
        environment_model={"inputs": {"request_id": "demo"}, "assumptions": ["scenario:trace_mismatch"]},
    )

    assert witness.verdict == CounterexampleVerdict.DIFF_FOUND.value
    assert witness.violated_property == ViolatedProperty.TRACE_MISMATCH.value
    assert witness.divergence_point["step"] >= 1
    assert witness.refinement_hint == "check_observation_schema_or_alignment_rule"
    assert witness.environment_assumptions["path_assumptions"] == ["scenario:trace_mismatch"]


def test_counterexample_layer_finds_resource_protocol_violation() -> None:
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="SUBSCRIBE", target="listener.demo", phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="UNSUBSCRIBE", target="listener.demo", phase="TEARDOWN"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="SUBSCRIBE", target="listener.demo", phase="RUNTIME"),
        ],
        meta={},
    )

    witness = generate_counterexample_from_traces(
        baseline_trace=baseline,
        optimized_trace=optimized,
        optimization_target=_target(),
    )

    assert witness.verdict == CounterexampleVerdict.DIFF_FOUND.value
    assert witness.violated_property == ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value
    assert witness.refinement_hint == "upgrade_soft_constraint_or_add_guard"


def test_counterexample_layer_flags_unsupported_alignment() -> None:
    trace = Trace(
        events=[Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.vdev", params_abst={"state": "on"}, phase="RUNTIME")],
        meta={},
    )
    compare_config = TraceCompareConfig(canonicalization_version="v9")
    baseline_ir = trace_to_ir_program(trace, "baseline", compare_config)
    optimized_ir = trace_to_ir_program(trace, "optimized", compare_config)
    observation_schema = CounterexampleObservationSchema.from_optimization_target(_target())
    resource_model = ResourceModel.from_observation_schema(observation_schema)
    alignment_map = AlignmentMap(
        node_alignments=[],
        block_alignments=[],
        unmatched_baseline_nodes=list(baseline_ir.order),
        unmatched_optimized_nodes=list(optimized_ir.order),
    )

    witness = generate_counterexample(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=alignment_map,
        observation_schema=observation_schema,
        environment_model={"assumptions": ["manual_alignment_gap"]},
        resource_model=resource_model,
        suspicious_regions=[
            {
                "region_id": "sr_manual",
                "baseline_node_ids": [baseline_ir.order[0]],
                "optimized_node_ids": [optimized_ir.order[0]],
                "reason": "test_manual_alignment_gap",
                "unsupported_alignment": True,
            }
        ],
        max_steps=10,
        max_paths=20,
    )

    assert witness.verdict == CounterexampleVerdict.DIFF_FOUND.value
    assert witness.violated_property == ViolatedProperty.UNSUPPORTED_ALIGNMENT.value
    assert witness.suspicious_region_id == "sr_manual"


def test_counterexample_layer_environment_guards_drive_dynamic_split() -> None:
    observation_schema = CounterexampleObservationSchema.from_optimization_target(_target())
    resource_model = ResourceModel.from_observation_schema(observation_schema)

    baseline_node = IRNode(
        node_id="b0",
        summary=IRSummary(
            provider="HA",
            op="STATE_WRITE",
            target="sensor.vdev",
            phase="RUNTIME",
            params={"state": "on"},
            semantic_updates={"state_write": {"sensor.vdev": "on"}},
        ),
        metadata={"toggle_guards": {"ble_timeout": True}},
    )
    optimized_node = IRNode(
        node_id="o0",
        summary=IRSummary(
            provider="HA",
            op="STATE_WRITE",
            target="sensor.vdev",
            phase="RUNTIME",
            params={"state": "on"},
            semantic_updates={"state_write": {"sensor.vdev": "on"}},
        ),
        metadata={"toggle_guards": {"ble_timeout": False}},
    )
    baseline_ir = IRProgram(program_id="baseline", nodes={"b0": baseline_node}, entry_node="b0", exit_node="b0", order=["b0"])
    optimized_ir = IRProgram(program_id="optimized", nodes={"o0": optimized_node}, entry_node="o0", exit_node="o0", order=["o0"])
    alignment_map = AlignmentMap(
        node_alignments=[
            AlignmentItem(
                baseline_node_id="b0",
                optimized_node_id="o0",
                relation="EXACT",
                confidence=1.0,
                supporting_rule="unit_test",
            )
        ],
        block_alignments=[],
        unmatched_baseline_nodes=[],
        unmatched_optimized_nodes=[],
    )

    witness = generate_counterexample(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        alignment_map=alignment_map,
        observation_schema=observation_schema,
        environment_model={
            "toggles": {"ble_timeout": True},
            "request_params": {"noise": "ignore-me"},
            "assumptions": ["scenario:env_split"],
        },
        resource_model=resource_model,
        max_steps=10,
        max_paths=20,
    )

    assert witness.verdict == CounterexampleVerdict.DIFF_FOUND.value
    assert witness.violated_property == ViolatedProperty.TRACE_MISMATCH.value
    assert witness.metadata.get("mode") == "SPLIT"
    assert any("ble_timeout" in condition for condition in witness.minimal_conditions)
    assert "request_params.noise=ignore-me" not in witness.minimal_conditions
