from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Tuple

from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel, ResourceRule

from alignment_layer.ir.compatibility import block_observation_signature
from alignment_layer.search.search_alignment import ProvisionalAlignment
from alignment_layer.verify.obligations import ProofObligation
from alignment_layer.verify.violations import AlignmentViolation

CRITICAL_KINDS = {"ACT", "UPDATE", "CLEANUP"}
TRACE_EQ = "TRACE_EQ"
FINAL_STATE_EQ = "FINAL_STATE_EQ"
RESOURCE_PROTOCOL_PRESERVATION = "RESOURCE_PROTOCOL_PRESERVATION"


def _node_kind(program: IRProgram, node_id: str) -> str:
    return str(program.nodes[node_id].metadata.get("node_kind", "ACT"))


def _aligned_node_sets(provisional_alignment: ProvisionalAlignment) -> Tuple[set[str], set[str]]:
    baseline: set[str] = set()
    optimized: set[str] = set()
    for pair in provisional_alignment.aligned_pairs:
        baseline.add(pair.baseline_node_id)
        optimized.add(pair.optimized_node_id)
    for block in provisional_alignment.aligned_blocks:
        baseline.update(block.baseline_node_ids)
        optimized.update(block.optimized_node_ids)
    return baseline, optimized


def _resource_effect_counter(program: IRProgram) -> Counter[Tuple[str, str]]:
    counts: Counter[Tuple[str, str]] = Counter()
    for node_id in program.order:
        node = program.nodes[node_id]
        for effect in node.summary.resource_effects:
            counts[(str(effect.get("resource_kind", "generic")), str(effect.get("action", "")))] += 1
    return counts


def _cleanup_positions(program: IRProgram) -> List[int]:
    return [idx for idx, node_id in enumerate(program.order) if _node_kind(program, node_id) == "CLEANUP"]


def _critical_unmatched(program: IRProgram, node_ids: Iterable[str]) -> List[str]:
    return [node_id for node_id in node_ids if _node_kind(program, node_id) in CRITICAL_KINDS]


def _required_trace_nodes(program: IRProgram, schema: CounterexampleObservationSchema) -> List[str]:
    required_ops = set(schema.anchor_ops) | set(schema.semantic_ops)
    required_targets = set(schema.required_state_writes)
    result: List[str] = []
    for node_id in program.order:
        node = program.nodes[node_id]
        if not node.metadata.get("observation_boundary"):
            continue
        if node.summary.op in required_ops or node.summary.target in required_targets:
            result.append(node_id)
    return result


def _required_final_nodes(program: IRProgram, schema: CounterexampleObservationSchema) -> List[str]:
    required_targets = set(schema.required_state_writes) | {str(key) for key in schema.required_final_state}
    result: List[str] = []
    for node_id in program.order:
        node = program.nodes[node_id]
        if node.summary.semantic_updates:
            result.append(node_id)
            continue
        if node.summary.target in required_targets and _node_kind(program, node_id) in {"UPDATE", "ACT", "CHECK"}:
            result.append(node_id)
    return result


def _resource_rule_summary(program: IRProgram, rule: ResourceRule) -> Dict[str, int | bool]:
    open_count = 0
    max_open = 0
    acquire_count = 0
    release_count = 0
    required_before_violations = 0
    acquired = False
    for node_id in program.order:
        op = str(program.nodes[node_id].summary.op)
        if op in rule.acquire_ops:
            acquire_count += 1
            open_count += 1
            acquired = True
            max_open = max(max_open, open_count)
        if op in rule.required_before and not acquired:
            required_before_violations += 1
        if op in rule.release_ops:
            release_count += 1
            open_count = max(0, open_count - 1)
    missing_release = bool(rule.must_release and acquire_count != release_count)
    overlap_violation = bool(rule.forbid_overlap and max_open > 1)
    return {
        "acquire_count": acquire_count,
        "release_count": release_count,
        "required_before_violations": required_before_violations,
        "missing_release": missing_release,
        "overlap_violation": overlap_violation,
    }


def _append_violation(
    violations: List[AlignmentViolation],
    *,
    kind: str,
    baseline_scope: List[str],
    optimized_scope: List[str],
    note: str,
    severity: float = 1.0,
) -> None:
    violations.append(
        AlignmentViolation(
            violation_id=f"viol_{len(violations):03d}",
            kind=kind,
            baseline_scope=list(baseline_scope),
            optimized_scope=list(optimized_scope),
            note=note,
            severity=severity,
        )
    )


def check_relational_consistency(
    provisional_alignment: ProvisionalAlignment,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
) -> tuple[List[ProofObligation], List[AlignmentViolation], str]:
    obligations: List[ProofObligation] = []
    violations: List[AlignmentViolation] = []

    aligned_baseline, aligned_optimized = _aligned_node_sets(provisional_alignment)

    for block in provisional_alignment.aligned_blocks:
        left_sig = block_observation_signature(baseline_ir, block.baseline_node_ids)
        right_sig = block_observation_signature(optimized_ir, block.optimized_node_ids)
        if block.relation == "STUTTER":
            if left_sig or right_sig:
                _append_violation(
                    violations,
                    kind="TRACE_ANCHOR_CONFLICT",
                    baseline_scope=list(block.baseline_node_ids),
                    optimized_scope=list(block.optimized_node_ids),
                    note="stutter block crosses observation boundary",
                )
        elif left_sig != right_sig:
            _append_violation(
                violations,
                kind="TRACE_ANCHOR_CONFLICT",
                baseline_scope=list(block.baseline_node_ids),
                optimized_scope=list(block.optimized_node_ids),
                note="aligned block does not preserve observable anchor multiset",
            )

    for pair in provisional_alignment.aligned_pairs:
        if not pair.observation_compatibility.get("compatible", False):
            _append_violation(
                violations,
                kind="TRACE_ANCHOR_CONFLICT",
                baseline_scope=[pair.baseline_node_id],
                optimized_scope=[pair.optimized_node_id],
                note="pair crosses observation boundary or changes trace anchor",
            )
        if not pair.resource_compatibility.get("compatible", True):
            _append_violation(
                violations,
                kind="RESOURCE_PROTOCOL_CONFLICT",
                baseline_scope=[pair.baseline_node_id],
                optimized_scope=[pair.optimized_node_id],
                note="resource claims are not compatible",
            )

    baseline_cleanup = _cleanup_positions(baseline_ir)
    optimized_cleanup = _cleanup_positions(optimized_ir)
    if baseline_cleanup and optimized_cleanup and min(optimized_cleanup) < min(baseline_cleanup):
        _append_violation(
            violations,
            kind="RESOURCE_PROTOCOL_CONFLICT",
            baseline_scope=[baseline_ir.order[min(baseline_cleanup)]],
            optimized_scope=[optimized_ir.order[min(optimized_cleanup)]],
            note="cleanup appears earlier in optimized flow",
        )

    required_trace_baseline = _required_trace_nodes(baseline_ir, observation_schema)
    required_trace_optimized = _required_trace_nodes(optimized_ir, observation_schema)
    unmatched_trace_baseline = [node_id for node_id in required_trace_baseline if node_id not in aligned_baseline]
    unmatched_trace_optimized = [node_id for node_id in required_trace_optimized if node_id not in aligned_optimized]

    required_final_baseline = _required_final_nodes(baseline_ir, observation_schema)
    required_final_optimized = _required_final_nodes(optimized_ir, observation_schema)
    unmatched_final_baseline = [node_id for node_id in required_final_baseline if node_id not in aligned_baseline]
    unmatched_final_optimized = [node_id for node_id in required_final_optimized if node_id not in aligned_optimized]

    if _resource_effect_counter(baseline_ir) != _resource_effect_counter(optimized_ir):
        _append_violation(
            violations,
            kind="RESOURCE_PROTOCOL_CONFLICT",
            baseline_scope=list(baseline_ir.order),
            optimized_scope=list(optimized_ir.order),
            note="resource effect multiset differs between versions",
        )

    for resource_kind, rule in resource_model.rules.items():
        baseline_summary = _resource_rule_summary(baseline_ir, rule)
        optimized_summary = _resource_rule_summary(optimized_ir, rule)
        baseline_issue = bool(
            baseline_summary["missing_release"]
            or baseline_summary["overlap_violation"]
            or baseline_summary["required_before_violations"]
        )
        optimized_issue = bool(
            optimized_summary["missing_release"]
            or optimized_summary["overlap_violation"]
            or optimized_summary["required_before_violations"]
        )
        if baseline_summary != optimized_summary:
            _append_violation(
                violations,
                kind="RESOURCE_PROTOCOL_CONFLICT",
                baseline_scope=list(baseline_ir.order),
                optimized_scope=list(optimized_ir.order),
                note=f"resource protocol differs for {resource_kind}",
                severity=0.9,
            )
            continue
        if optimized_issue and not baseline_issue:
            _append_violation(
                violations,
                kind="RESOURCE_PROTOCOL_CONFLICT",
                baseline_scope=list(baseline_ir.order),
                optimized_scope=list(optimized_ir.order),
                note=f"optimized flow violates resource protocol for {resource_kind}",
                severity=0.95,
            )

    if observation_schema.required_state_writes:
        baseline_targets = Counter(
            baseline_ir.nodes[node_id].summary.target
            for node_id in baseline_ir.order
            if baseline_ir.nodes[node_id].summary.target in set(observation_schema.required_state_writes)
        )
        optimized_targets = Counter(
            optimized_ir.nodes[node_id].summary.target
            for node_id in optimized_ir.order
            if optimized_ir.nodes[node_id].summary.target in set(observation_schema.required_state_writes)
        )
        if baseline_targets != optimized_targets:
            _append_violation(
                violations,
                kind="FINAL_STATE_FLOW_CONFLICT",
                baseline_scope=list(required_final_baseline),
                optimized_scope=list(required_final_optimized),
                note="required final-state targets differ between versions",
                severity=0.9,
            )

    trace_failed = any(v.kind == "TRACE_ANCHOR_CONFLICT" for v in violations)
    final_failed = any(v.kind == "FINAL_STATE_FLOW_CONFLICT" for v in violations)
    resource_failed = any(v.kind == "RESOURCE_PROTOCOL_CONFLICT" for v in violations)

    obligations.append(
        ProofObligation(
            obligation_id="obl_trace_eq",
            kind=TRACE_EQ,
            baseline_scope=unmatched_trace_baseline or list(required_trace_baseline),
            optimized_scope=unmatched_trace_optimized or list(required_trace_optimized),
            status="FAILED" if trace_failed else ("PENDING" if unmatched_trace_baseline or unmatched_trace_optimized else "DISCHARGED"),
            note="required observation anchors remain unaligned" if unmatched_trace_baseline or unmatched_trace_optimized else None,
        )
    )
    obligations.append(
        ProofObligation(
            obligation_id="obl_final_state_eq",
            kind=FINAL_STATE_EQ,
            baseline_scope=unmatched_final_baseline,
            optimized_scope=unmatched_final_optimized,
            status="FAILED" if final_failed else ("PENDING" if unmatched_final_baseline or unmatched_final_optimized else "DISCHARGED"),
            note="required final-state flow remains unproved" if unmatched_final_baseline or unmatched_final_optimized else None,
        )
    )
    obligations.append(
        ProofObligation(
            obligation_id="obl_resource_protocol",
            kind=RESOURCE_PROTOCOL_PRESERVATION,
            baseline_scope=list(baseline_ir.order),
            optimized_scope=list(optimized_ir.order),
            status="FAILED" if resource_failed else ("PENDING" if _critical_unmatched(baseline_ir, provisional_alignment.unmatched_baseline_nodes) or _critical_unmatched(optimized_ir, provisional_alignment.unmatched_optimized_nodes) else "DISCHARGED"),
            note="resource protocol needs counterexample search" if not resource_failed and (_critical_unmatched(baseline_ir, provisional_alignment.unmatched_baseline_nodes) or _critical_unmatched(optimized_ir, provisional_alignment.unmatched_optimized_nodes)) else None,
        )
    )

    coverage = provisional_alignment.coverage
    high_risk_unmatched = bool(
        unmatched_trace_baseline
        or unmatched_trace_optimized
        or unmatched_final_baseline
        or unmatched_final_optimized
        or _critical_unmatched(baseline_ir, provisional_alignment.unmatched_baseline_nodes)
        or _critical_unmatched(optimized_ir, provisional_alignment.unmatched_optimized_nodes)
    )

    if violations:
        verdict = "VIOLATED"
    elif (
        coverage.get("observable_ratio", 0.0) >= 0.999
        and coverage.get("critical_ratio", 0.0) >= 0.999
        and not high_risk_unmatched
    ):
        verdict = "PROVED"
    elif coverage.get("critical_ratio", 0.0) >= 0.6 and not trace_failed and not resource_failed:
        verdict = "PARTIAL"
    else:
        verdict = "UNKNOWN"
    return obligations, violations, verdict
