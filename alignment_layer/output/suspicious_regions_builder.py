from __future__ import annotations

from typing import Dict, List, Tuple

from counterexample_layer.ir.ir_types import IRProgram

from alignment_layer.output.alignment_map import AlignmentMap
from alignment_layer.output.suspicious_regions import SuspiciousRegion
from alignment_layer.verify.obligations import ProofObligation
from alignment_layer.verify.violations import AlignmentViolation


_REASON_FROM_VIOLATION = {
    "TRACE_ANCHOR_CONFLICT": "OBSERVATION_BOUNDARY_RISK",
    "RESOURCE_PROTOCOL_CONFLICT": "RESOURCE_MISMATCH",
    "FINAL_STATE_FLOW_CONFLICT": "UNSUPPORTED_PATTERN",
}


def _node_kind(program: IRProgram, node_id: str) -> str:
    return str(program.nodes[node_id].metadata.get("node_kind", "ACT"))


def infer_suspicious_regions(
    alignment_map: AlignmentMap,
    proof_obligations: List[ProofObligation],
    violations: List[AlignmentViolation],
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
) -> List[SuspiciousRegion]:
    regions: List[SuspiciousRegion] = []
    seen: set[Tuple[Tuple[str, ...], Tuple[str, ...], str]] = set()

    def add_region(baseline_node_ids: List[str], optimized_node_ids: List[str], reason: str, severity: float) -> None:
        key = (tuple(sorted(baseline_node_ids)), tuple(sorted(optimized_node_ids)), reason)
        if key in seen:
            return
        seen.add(key)
        regions.append(
            SuspiciousRegion(
                region_id=f"sr_{len(regions):03d}",
                baseline_node_ids=list(baseline_node_ids),
                optimized_node_ids=list(optimized_node_ids),
                reason=reason,
                severity=severity,
            )
        )

    for pair in alignment_map.node_alignments:
        if pair.confidence < 0.75:
            add_region([pair.baseline_node_id], [pair.optimized_node_id], "LOW_CONFIDENCE_ALIGNMENT", 1.0 - pair.confidence)

    for block in alignment_map.block_alignments:
        if block.confidence < 0.75:
            add_region(block.baseline_node_ids, block.optimized_node_ids, "LOW_CONFIDENCE_ALIGNMENT", 1.0 - block.confidence)

    for violation in violations:
        add_region(
            violation.baseline_scope,
            violation.optimized_scope,
            _REASON_FROM_VIOLATION.get(violation.kind, "UNSUPPORTED_PATTERN"),
            max(0.8, violation.severity),
        )

    for obligation in proof_obligations:
        if obligation.status != "PENDING":
            continue
        reason = "OBSERVATION_BOUNDARY_RISK" if obligation.kind == "TRACE_EQ" else "UNSUPPORTED_PATTERN"
        add_region(obligation.baseline_scope, obligation.optimized_scope, reason, 0.75)

    for node_id in alignment_map.unmatched_baseline_nodes:
        if _node_kind(baseline_ir, node_id) in {"ACT", "UPDATE", "CLEANUP"}:
            add_region([node_id], [], "UNSUPPORTED_PATTERN", 0.85)
    for node_id in alignment_map.unmatched_optimized_nodes:
        if _node_kind(optimized_ir, node_id) in {"ACT", "UPDATE", "CLEANUP"}:
            add_region([], [node_id], "UNSUPPORTED_PATTERN", 0.85)
    return regions
