from counterexample_layer.witness.witness import CounterexampleWitness, ViolatedProperty
from profile_builder import build_counterexample_cluster_packs
from profile_builder.clustering.conservative_merge import merge_bucket_to_clusters
from profile_builder.clustering.typed_grouping import bucket_evidence_by_type
from profile_builder.evidence import witness_to_evidence


def _witness(**overrides) -> CounterexampleWitness:
    base = CounterexampleWitness(
        verdict="DIFF_FOUND",
        violated_property=ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value,
        input_assumptions={"request_params": {"concurrency_level": 1, "bucket_size": 2}},
        environment_assumptions={"toggle_assumptions": {"timeout_enabled": True}},
        baseline_trace_prefix=[
            {"provider": "CLOUD", "op": "CLOUD_SESSION_REUSE", "target": "manager.cloud", "phase": "RUNTIME"},
            {"provider": "CLOUD", "op": "CLOUD_HTTP_CALL", "target": "/v1/device", "phase": "RUNTIME"},
        ],
        optimized_trace_prefix=[
            {"provider": "CLOUD", "op": "CLOUD_HTTP_CALL", "target": "/v1/device", "phase": "RUNTIME"},
            {"provider": "HA", "op": "ENTRY_UNLOAD", "target": "entry", "phase": "TEARDOWN"},
        ],
        divergence_point={"reason": "missing_release_or_unsubscribe", "details": {"resource_kind": "listener"}},
        baseline_state_at_divergence={"resource_keys": ["listener:cloud"]},
        optimized_state_at_divergence={"resource_keys": ["listener:cloud"]},
        minimal_conditions=["concurrency_level=1", "bucket_size=2", "retry_count=3"],
        phase_context="TEARDOWN",
        protocol_context="CLOUD",
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_witness_to_evidence_projects_typed_fields() -> None:
    evidence = witness_to_evidence(_witness())
    assert evidence.violated_property == ViolatedProperty.RESOURCE_PROTOCOL_VIOLATION.value
    assert evidence.trigger_pattern == "missing_unsubscribe"
    assert evidence.protocol_context == "CLOUD"
    assert evidence.phase_context == "TEARDOWN"
    assert evidence.resource_context == "CLOUD_LISTENER"
    assert evidence.suspected_rule_gap == "MISSING_LIFECYCLE_PAIRING_RULE"
    assert evidence.suggested_refinement == "add hard pairing between SUBSCRIBE and UNSUBSCRIBE"
    assert evidence.confidence == 0.9
    assert evidence.baseline_trace_signature
    assert evidence.optimized_trace_signature


def test_bucket_evidence_by_type_is_strict() -> None:
    first = witness_to_evidence(_witness())
    second = witness_to_evidence(_witness(phase_context="RUNTIME"))
    buckets = bucket_evidence_by_type([first, second])
    assert len(buckets) == 2
    assert all(len(values) == 1 for values in buckets.values())


def test_merge_bucket_to_clusters_respects_minimal_condition_conflicts() -> None:
    left = witness_to_evidence(_witness())
    right = witness_to_evidence(_witness(minimal_conditions=["concurrency_level=2", "bucket_size=2", "retry_count=3"]))
    clusters = merge_bucket_to_clusters([left, right])
    assert len(clusters) == 2


def test_build_counterexample_cluster_packs_runs_full_pipeline() -> None:
    packs = build_counterexample_cluster_packs([_witness(), _witness(suspicious_region_id="sr_2")])
    assert len(packs) == 1
    pack = packs[0]
    assert pack.semantic_tag == "CLOUD:TEARDOWN:missing_unsubscribe"
    assert len(pack.supporting_counterexample_ids) == 2
    assert pack.suspected_rule_gap == "MISSING_LIFECYCLE_PAIRING_RULE"


def test_unknown_trigger_projects_to_unknown_rule_gap() -> None:
    evidence = witness_to_evidence(
        _witness(
            violated_property=ViolatedProperty.TRACE_MISMATCH.value,
            baseline_trace_prefix=[{"provider": "HA", "op": "WAIT_STATE", "target": "sensor.demo", "phase": "RUNTIME"}],
            optimized_trace_prefix=[{"provider": "HA", "op": "WAIT_STATE", "target": "sensor.demo", "phase": "RUNTIME"}],
            divergence_point={"reason": "opaque_trace_difference", "details": {}},
            protocol_context=None,
            phase_context=None,
            trigger_pattern=None,
            suspected_rule_gap=None,
        )
    )
    assert evidence.trigger_pattern == "unknown_trigger"
    assert evidence.suspected_rule_gap == "UNKNOWN_RULE_GAP"
    assert evidence.suggested_refinement is None


def test_cluster_representative_conditions_do_not_embed_optimized_signature() -> None:
    evidence = witness_to_evidence(_witness())
    cluster = merge_bucket_to_clusters([evidence])[0]
    assert "_optimized_trace_signature" not in cluster.representative_minimal_conditions
