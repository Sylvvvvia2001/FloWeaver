from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple

from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel

from alignment_layer.graph.candidate_generation import CandidateBlock, CandidatePair
from alignment_layer.ir.compatibility import block_observation_signature


def candidate_baseline_ids(candidate: CandidatePair | CandidateBlock) -> List[str]:
    if isinstance(candidate, CandidatePair):
        return [candidate.baseline_node_id]
    return list(candidate.baseline_node_ids)


def candidate_optimized_ids(candidate: CandidatePair | CandidateBlock) -> List[str]:
    if isinstance(candidate, CandidatePair):
        return [candidate.optimized_node_id]
    return list(candidate.optimized_node_ids)


def candidate_supporting_rules(candidate: CandidatePair | CandidateBlock) -> List[str]:
    if isinstance(candidate, CandidatePair):
        return [candidate.supporting_rule] if candidate.supporting_rule else []
    return list(candidate.supporting_rules)


def candidate_relation(candidate: CandidatePair | CandidateBlock) -> str:
    return str(candidate.relation)


def candidate_id(candidate: CandidatePair | CandidateBlock) -> str:
    if isinstance(candidate, CandidatePair):
        return f"pair:{candidate.baseline_node_id}->{candidate.optimized_node_id}:{candidate.relation}"
    baseline = ",".join(candidate.baseline_node_ids)
    optimized = ",".join(candidate.optimized_node_ids)
    return f"block:{baseline}=>{optimized}:{candidate.relation}"


@dataclass
class AlignmentGraph:
    baseline_ir: IRProgram
    optimized_ir: IRProgram
    candidate_pairs: List[CandidatePair] = field(default_factory=list)
    candidate_blocks: List[CandidateBlock] = field(default_factory=list)
    candidates: Dict[str, CandidatePair | CandidateBlock] = field(default_factory=dict)
    incompatibility_edges: Dict[str, Set[str]] = field(default_factory=dict)
    ordering_consistency_edges: Dict[str, Set[str]] = field(default_factory=dict)
    rule_supported_edges: Dict[str, Tuple[str, ...]] = field(default_factory=dict)


def _span(program: IRProgram, node_ids: Iterable[str]) -> Tuple[int | None, int | None]:
    indices = [program.order.index(node_id) for node_id in node_ids if node_id in program.nodes]
    if not indices:
        return (None, None)
    return (min(indices), max(indices))


def _overlaps(left: Iterable[str], right: Iterable[str]) -> bool:
    return bool(set(left).intersection(right))


def _crosses(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    left: CandidatePair | CandidateBlock,
    right: CandidatePair | CandidateBlock,
) -> bool:
    left_b = _span(baseline_ir, candidate_baseline_ids(left))
    right_b = _span(baseline_ir, candidate_baseline_ids(right))
    left_o = _span(optimized_ir, candidate_optimized_ids(left))
    right_o = _span(optimized_ir, candidate_optimized_ids(right))
    if None in left_b or None in right_b or None in left_o or None in right_o:
        return False
    return (
        left_b[0] > right_b[1]
        and left_o[0] < right_o[0]
    ) or (
        left_b[1] < right_b[0]
        and left_o[1] > right_o[1]
    )


def _order_consistent(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    left: CandidatePair | CandidateBlock,
    right: CandidatePair | CandidateBlock,
) -> bool:
    left_b = _span(baseline_ir, candidate_baseline_ids(left))
    right_b = _span(baseline_ir, candidate_baseline_ids(right))
    left_o = _span(optimized_ir, candidate_optimized_ids(left))
    right_o = _span(optimized_ir, candidate_optimized_ids(right))
    if None in left_b or None in right_b or None in left_o or None in right_o:
        return False
    if left_b[1] < right_b[0] and left_o[1] < right_o[0]:
        return True
    if right_b[1] < left_b[0] and right_o[1] < left_o[0]:
        return True
    return False


def _is_required_anchor(program: IRProgram, node_id: str, observation_schema: CounterexampleObservationSchema) -> bool:
    node = program.nodes[node_id]
    return bool(
        node.metadata.get("observation_boundary")
        or node.summary.op in set(observation_schema.anchor_ops)
        or node.summary.op in set(observation_schema.semantic_ops)
        or node.summary.target in set(observation_schema.required_state_writes)
    )


def _resource_role_multiset(
    program: IRProgram,
    node_ids: Iterable[str],
    resource_model: ResourceModel,
) -> Counter[Tuple[str, str]]:
    counts: Counter[Tuple[str, str]] = Counter()
    for node_id in node_ids:
        if node_id not in program.nodes:
            continue
        op = str(program.nodes[node_id].summary.op)
        for resource_kind, rule in resource_model.rules.items():
            if op in rule.acquire_ops:
                counts[(resource_kind, "acquire")] += 1
            if op in rule.release_ops:
                counts[(resource_kind, "release")] += 1
            if op in rule.required_before:
                counts[(resource_kind, "required_before")] += 1
    return counts


def _self_incompatible(
    candidate: CandidatePair | CandidateBlock,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
) -> bool:
    baseline_ids = candidate_baseline_ids(candidate)
    optimized_ids = candidate_optimized_ids(candidate)
    relation = candidate_relation(candidate)

    if isinstance(candidate, CandidatePair):
        if not candidate.observation_compatibility.get("compatible", False):
            if any(_is_required_anchor(baseline_ir, node_id, observation_schema) for node_id in baseline_ids):
                return True
            if any(_is_required_anchor(optimized_ir, node_id, observation_schema) for node_id in optimized_ids):
                return True
        if not candidate.resource_compatibility.get("compatible", True) and relation not in {"REUSE_EQ", "BATCH_EQ"}:
            return True
        return False

    left_sig = block_observation_signature(baseline_ir, baseline_ids)
    right_sig = block_observation_signature(optimized_ir, optimized_ids)
    if relation == "STUTTER":
        return bool(left_sig or right_sig)
    if left_sig != right_sig:
        return True
    left_roles = _resource_role_multiset(baseline_ir, baseline_ids, resource_model)
    right_roles = _resource_role_multiset(optimized_ir, optimized_ids, resource_model)
    if relation not in {"REUSE_EQ", "BATCH_EQ"} and left_roles != right_roles:
        return True
    if relation not in {"EXACT", "SERIAL_EQ"} and not candidate_supporting_rules(candidate):
        return True
    return False


def build_alignment_graph(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    candidate_pairs: List[CandidatePair],
    candidate_blocks: List[CandidateBlock],
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
) -> AlignmentGraph:
    all_candidates: List[CandidatePair | CandidateBlock] = list(candidate_blocks) + list(candidate_pairs)
    candidates = {candidate_id(candidate): candidate for candidate in all_candidates}
    incompatibility_edges: Dict[str, Set[str]] = {key: set() for key in candidates}
    ordering_consistency_edges: Dict[str, Set[str]] = {key: set() for key in candidates}
    rule_supported_edges: Dict[str, Tuple[str, ...]] = {
        key: tuple(candidate_supporting_rules(candidate))
        for key, candidate in candidates.items()
    }

    for left_id, left in candidates.items():
        if _self_incompatible(left, baseline_ir, optimized_ir, observation_schema, resource_model):
            incompatibility_edges[left_id].add(left_id)
        for right_id, right in candidates.items():
            if left_id >= right_id:
                continue
            incompatible = (
                _overlaps(candidate_baseline_ids(left), candidate_baseline_ids(right))
                or _overlaps(candidate_optimized_ids(left), candidate_optimized_ids(right))
                or _crosses(baseline_ir, optimized_ir, left, right)
            )
            if incompatible:
                incompatibility_edges[left_id].add(right_id)
                incompatibility_edges[right_id].add(left_id)
                continue
            if _order_consistent(baseline_ir, optimized_ir, left, right):
                ordering_consistency_edges[left_id].add(right_id)
                ordering_consistency_edges[right_id].add(left_id)

    return AlignmentGraph(
        baseline_ir=baseline_ir,
        optimized_ir=optimized_ir,
        candidate_pairs=list(candidate_pairs),
        candidate_blocks=list(candidate_blocks),
        candidates=candidates,
        incompatibility_edges=incompatibility_edges,
        ordering_consistency_edges=ordering_consistency_edges,
        rule_supported_edges=rule_supported_edges,
    )
