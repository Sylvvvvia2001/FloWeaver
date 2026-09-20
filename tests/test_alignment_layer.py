from alignment_layer.api.run_alignment_verification import materialize_alignment_map, run_alignment_verification
from alignment_layer.graph.alignment_graph import build_alignment_graph
from alignment_layer.graph.candidate_generation import CandidateBlock, generate_alignment_candidates
from alignment_layer.ir.normalize import normalize_ir
from alignment_layer.output.alignment_map import AlignedPair
from alignment_layer.rules.alignment_rules import AlignmentConfig, DEFAULT_ALIGNMENT_RULES
from alignment_layer.search.search_alignment import ProvisionalAlignment
from alignment_layer.verify.obligations import ProofObligation
from alignment_layer.verify.violations import AlignmentViolation
from counterexample_layer.ir.summaries import trace_to_ir_program
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from dsl.contracts import Event, Trace
from runtime.trace import TraceCompareConfig


def _schema() -> CounterexampleObservationSchema:
    return CounterexampleObservationSchema.from_optimization_target(None)


def _ir(trace: Trace, program_id: str):
    schema = _schema()
    return trace_to_ir_program(trace, program_id, TraceCompareConfig(canonicalization_version=schema.canonicalization_version))


def test_alignment_layer_proves_exact_alignment() -> None:
    schema = _schema()
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="ENTRY_SETUP", target="entry", phase="SETUP"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.demo", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    optimized = Trace(events=list(baseline.events), meta={})

    result = run_alignment_verification(
        baseline_ir=_ir(baseline, "baseline"),
        optimized_ir=_ir(optimized, "optimized"),
        observation_schema=schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )

    assert result.verdict == "PROVED"
    assert len(result.aligned_pairs) == 2
    assert not result.unaligned_baseline_nodes
    assert not result.violations


def test_alignment_layer_builds_reorder_equivalent_block() -> None:
    schema = _schema()
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/b", phase="RUNTIME"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/b", phase="RUNTIME"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", phase="RUNTIME"),
        ],
        meta={},
    )

    result = run_alignment_verification(
        baseline_ir=_ir(baseline, "baseline"),
        optimized_ir=_ir(optimized, "optimized"),
        observation_schema=schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )

    assert result.verdict in {"PROVED", "PARTIAL"}
    assert any(block.relation == "REORDER_EQ" for block in result.aligned_blocks)
    assert not result.violations


def test_alignment_graph_materializes_ordering_constraints() -> None:
    schema = _schema()
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="ENTRY_SETUP", target="entry", phase="SETUP"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.demo", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )
    baseline_ir = _ir(baseline, "baseline")
    optimized_ir = _ir(Trace(events=list(baseline.events), meta={}), "optimized")
    pairs, blocks = generate_alignment_candidates(
        baseline_ir,
        optimized_ir,
        schema,
        resource_model,
        AlignmentConfig(),
    )

    graph = build_alignment_graph(
        baseline_ir,
        optimized_ir,
        pairs,
        blocks,
        schema,
        resource_model,
    )

    assert graph.candidates
    assert any(graph.ordering_consistency_edges.values())
    assert all(isinstance(rules, tuple) for rules in graph.rule_supported_edges.values())


def test_alignment_layer_flags_final_state_flow_conflict() -> None:
    schema = _schema()
    schema.required_state_writes = ["sensor.demo", "sensor.extra"]
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.demo", params_abst={"state": "on"}, phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="STATE_WRITE", target="sensor.extra", params_abst={"state": "ready"}, phase="RUNTIME"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.demo", params_abst={"state": "on"}, phase="RUNTIME"),
        ],
        meta={},
    )

    result = run_alignment_verification(
        baseline_ir=_ir(baseline, "baseline"),
        optimized_ir=_ir(optimized, "optimized"),
        observation_schema=schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )

    assert result.verdict == "VIOLATED"
    assert any(violation.kind == "FINAL_STATE_FLOW_CONFLICT" for violation in result.violations)
    assert any(obligation.kind == "FINAL_STATE_EQ" and obligation.status == "FAILED" for obligation in result.proof_obligations)


def test_alignment_layer_rejects_cleanup_hoisting() -> None:
    schema = _schema()
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline = Trace(
        events=[
            Event(ts=1.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", phase="RUNTIME"),
            Event(ts=2.0, provider="HA", op="ENTRY_UNLOAD", target="entry", phase="TEARDOWN"),
        ],
        meta={},
    )
    optimized = Trace(
        events=[
            Event(ts=1.0, provider="HA", op="ENTRY_UNLOAD", target="entry", phase="TEARDOWN"),
            Event(ts=2.0, provider="CLOUD", op="CLOUD_HTTP_CALL", target="/v1/a", phase="RUNTIME"),
        ],
        meta={},
    )

    result = run_alignment_verification(
        baseline_ir=_ir(baseline, "baseline"),
        optimized_ir=_ir(optimized, "optimized"),
        observation_schema=schema,
        resource_model=resource_model,
        alignment_rules=DEFAULT_ALIGNMENT_RULES,
        alignment_config=AlignmentConfig(),
    )

    assert result.verdict == "VIOLATED"
    assert any(violation.kind == "RESOURCE_PROTOCOL_CONFLICT" for violation in result.violations)
    assert result.suspicious_regions


def test_alignment_graph_marks_observation_unsafe_stutter_incompatible() -> None:
    schema = _schema()
    resource_model = ResourceModel.from_observation_schema(schema)
    baseline_ir = normalize_ir(_ir(Trace(events=[], meta={}), "baseline"), schema)
    optimized_ir = normalize_ir(
        _ir(
        Trace(
            events=[
                Event(ts=1.0, provider="HA", op="STATE_WRITE", target="sensor.demo", params_abst={"state": "on"}, phase="RUNTIME")
            ],
            meta={},
        ),
        "optimized",
        ),
        schema,
    )
    stutter = CandidateBlock(
        baseline_node_ids=[],
        optimized_node_ids=[optimized_ir.order[0]],
        relation="STUTTER",
        confidence=0.8,
        supporting_rules=["SETUP_PREFIX_STUTTER"],
    )

    graph = build_alignment_graph(
        baseline_ir,
        optimized_ir,
        [],
        [stutter],
        schema,
        resource_model,
    )

    candidate_key = next(iter(graph.candidates))
    assert candidate_key in graph.incompatibility_edges[candidate_key]


def test_materialize_alignment_map_drops_trace_conflicted_pairs_and_promotes_failed_scope() -> None:
    provisional = ProvisionalAlignment(
        aligned_pairs=[
            AlignedPair(
                baseline_node_id="b1",
                optimized_node_id="o1",
                relation="EXACT",
                confidence=0.9,
                observation_compatibility={"compatible": False},
            )
        ],
        aligned_blocks=[],
        unmatched_baseline_nodes=[],
        unmatched_optimized_nodes=[],
        coverage={},
    )
    obligations = [
        ProofObligation(
            obligation_id="obl_trace_eq",
            kind="TRACE_EQ",
            baseline_scope=["b1"],
            optimized_scope=["o1"],
            status="FAILED",
            note="required observation anchors remain unaligned",
        )
    ]
    violations = [
        AlignmentViolation(
            violation_id="viol_000",
            kind="TRACE_ANCHOR_CONFLICT",
            baseline_scope=["b1"],
            optimized_scope=["o1"],
            note="pair crosses observation boundary",
            severity=1.0,
        )
    ]

    alignment_map = materialize_alignment_map(provisional, obligations, violations)

    assert not alignment_map.node_alignments
    assert alignment_map.unmatched_baseline_nodes == ["b1"]
    assert alignment_map.unmatched_optimized_nodes == ["o1"]
