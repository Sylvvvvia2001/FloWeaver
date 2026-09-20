from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple

from counterexample_layer.ir.ir_types import IRNode

ALLOWED_KIND_ALIGNMENTS = {
    ("INIT", "PREPARE"),
    ("PREPARE", "INIT"),
    ("ACT", "UPDATE"),
    ("UPDATE", "ACT"),
}


def _metadata_list(node: IRNode, key: str) -> List[str]:
    value = node.metadata.get(key, []) if isinstance(node.metadata, dict) else []
    return [str(item) for item in value]


def compatible_kinds(b_node: IRNode, o_node: IRNode) -> bool:
    left = str(b_node.metadata.get("node_kind", ""))
    right = str(o_node.metadata.get("node_kind", ""))
    return left == right or (left, right) in ALLOWED_KIND_ALIGNMENTS


def compatible_effects(left: Iterable[str], right: Iterable[str]) -> bool:
    left_set = Counter(str(item) for item in left)
    right_set = Counter(str(item) for item in right)
    return left_set == right_set


def compatible_resources(left: Iterable[str], right: Iterable[str]) -> bool:
    left_claims = {tuple(str(item).split(":", 2)[0:2]) for item in left}
    right_claims = {tuple(str(item).split(":", 2)[0:2]) for item in right}
    return left_claims == right_claims


def trace_anchor_compatible(b_node: IRNode, o_node: IRNode) -> bool:
    left = str(b_node.metadata.get("trace_anchor", ""))
    right = str(o_node.metadata.get("trace_anchor", ""))
    if left == right:
        return True
    return b_node.summary.op == o_node.summary.op and b_node.summary.target == o_node.summary.target


def semantic_compatibility(b_node: IRNode, o_node: IRNode) -> Dict[str, Any]:
    kind_compatible = compatible_kinds(b_node, o_node)
    phase_compatible = b_node.summary.phase == o_node.summary.phase
    effects_compatible = compatible_effects(
        _metadata_list(b_node, "external_effects"),
        _metadata_list(o_node, "external_effects"),
    )
    return {
        "kind_compatible": kind_compatible,
        "phase_compatible": phase_compatible,
        "effects_compatible": effects_compatible,
        "compatible": kind_compatible and phase_compatible and effects_compatible,
    }


def observation_compatibility(b_node: IRNode, o_node: IRNode) -> Dict[str, Any]:
    same_boundary = bool(b_node.metadata.get("observation_boundary")) == bool(o_node.metadata.get("observation_boundary"))
    same_anchor = trace_anchor_compatible(b_node, o_node)
    return {
        "same_boundary": same_boundary,
        "same_anchor": same_anchor,
        "compatible": same_boundary and same_anchor,
    }


def resource_compatibility(b_node: IRNode, o_node: IRNode) -> Dict[str, Any]:
    left_claims = _metadata_list(b_node, "resource_claims")
    right_claims = _metadata_list(o_node, "resource_claims")
    compatible = compatible_resources(left_claims, right_claims)
    return {
        "baseline_claims": left_claims,
        "optimized_claims": right_claims,
        "compatible": compatible,
    }


def score_node_alignment(b_node: IRNode, o_node: IRNode) -> float:
    score = 0.0
    if compatible_kinds(b_node, o_node):
        score += 0.30
    if b_node.summary.phase == o_node.summary.phase:
        score += 0.15
    if compatible_effects(_metadata_list(b_node, "external_effects"), _metadata_list(o_node, "external_effects")):
        score += 0.25
    if compatible_resources(_metadata_list(b_node, "resource_claims"), _metadata_list(o_node, "resource_claims")):
        score += 0.15
    if bool(b_node.metadata.get("observation_boundary")) == bool(o_node.metadata.get("observation_boundary")):
        score += 0.10
    if trace_anchor_compatible(b_node, o_node):
        score += 0.05
    return round(score, 5)


def block_observation_signature(program, node_ids: List[str]) -> Counter[Tuple[str, str]]:
    signature: Counter[Tuple[str, str]] = Counter()
    for node_id in node_ids:
        node = program.nodes[node_id]
        if not node.metadata.get("observation_boundary"):
            continue
        signature[(node.summary.op, node.summary.target)] += 1
    return signature
