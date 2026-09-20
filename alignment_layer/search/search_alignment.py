from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Set, Tuple

from alignment_layer.graph.alignment_graph import (
    AlignmentGraph,
    candidate_baseline_ids,
    candidate_id,
    candidate_optimized_ids,
    candidate_relation,
    candidate_supporting_rules,
)
from alignment_layer.graph.candidate_generation import CandidateBlock, CandidatePair
from alignment_layer.output.alignment_map import AlignedBlock, AlignedPair
from alignment_layer.rules.alignment_rules import AlignmentConfig

CRITICAL_KINDS = {"ACT", "UPDATE", "CLEANUP"}


@dataclass
class ProvisionalAlignment:
    aligned_pairs: List[AlignedPair] = field(default_factory=list)
    aligned_blocks: List[AlignedBlock] = field(default_factory=list)
    unmatched_baseline_nodes: List[str] = field(default_factory=list)
    unmatched_optimized_nodes: List[str] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


@dataclass
class _BeamState:
    aligned_pairs: List[AlignedPair] = field(default_factory=list)
    aligned_blocks: List[AlignedBlock] = field(default_factory=list)
    used_baseline: Set[str] = field(default_factory=set)
    used_optimized: Set[str] = field(default_factory=set)
    selected_candidate_ids: Set[str] = field(default_factory=set)
    objective: Tuple[float, float, float, float, float, float, float, float] = (0, 0, 0, 0, 0, 0, 0, 0)


def _node_kind(program, node_id: str) -> str:
    return str(program.nodes[node_id].metadata.get("node_kind", "ACT"))


def _observable_weight(program, node_ids: Iterable[str]) -> int:
    return sum(1 for node_id in node_ids if program.nodes[node_id].metadata.get("observation_boundary"))


def _critical_weight(program, node_ids: Iterable[str]) -> int:
    return sum(1 for node_id in node_ids if _node_kind(program, node_id) in CRITICAL_KINDS)


def _resource_weight(program, node_ids: Iterable[str]) -> int:
    return sum(1 for node_id in node_ids if program.nodes[node_id].metadata.get("resource_claims"))


def _unsupported_leap_penalty(candidate) -> float:
    relation = candidate_relation(candidate)
    if relation in {"EXACT", "SERIAL_EQ"}:
        return 0.0
    return 0.0 if candidate_supporting_rules(candidate) else 1.0


def _candidate_priority(graph: AlignmentGraph, candidate) -> Tuple[float, float, float, float, float]:
    baseline_ids = candidate_baseline_ids(candidate)
    optimized_ids = candidate_optimized_ids(candidate)
    confidence = float(getattr(candidate, "confidence", 0.0))
    observable = _observable_weight(graph.baseline_ir, baseline_ids) + _observable_weight(graph.optimized_ir, optimized_ids)
    resource = _resource_weight(graph.baseline_ir, baseline_ids) + _resource_weight(graph.optimized_ir, optimized_ids)
    critical = _critical_weight(graph.baseline_ir, baseline_ids) + _critical_weight(graph.optimized_ir, optimized_ids)
    low_conf_penalty = 1.0 if confidence < 0.75 else 0.0
    return (float(observable), float(resource), float(critical), confidence, -low_conf_penalty)


def _compatible(graph: AlignmentGraph, candidate, state: _BeamState) -> bool:
    candidate_key = candidate_id(candidate)
    baseline_ids = set(candidate_baseline_ids(candidate))
    optimized_ids = set(candidate_optimized_ids(candidate))
    if baseline_ids.intersection(state.used_baseline) or optimized_ids.intersection(state.used_optimized):
        return False
    if candidate_key in graph.incompatibility_edges.get(candidate_key, set()):
        return False
    incompatible_with_selected = graph.incompatibility_edges.get(candidate_key, set()).intersection(state.selected_candidate_ids)
    return not incompatible_with_selected


def _apply_candidate(graph: AlignmentGraph, candidate, state: _BeamState) -> _BeamState:
    next_state = _BeamState(
        aligned_pairs=list(state.aligned_pairs),
        aligned_blocks=list(state.aligned_blocks),
        used_baseline=set(state.used_baseline),
        used_optimized=set(state.used_optimized),
        selected_candidate_ids=set(state.selected_candidate_ids),
        objective=state.objective,
    )
    candidate_key = candidate_id(candidate)
    priority = _candidate_priority(graph, candidate)
    order_bonus = float(
        len(graph.ordering_consistency_edges.get(candidate_key, set()).intersection(state.selected_candidate_ids))
    )
    rule_bonus = 1.0 if graph.rule_supported_edges.get(candidate_key) else 0.0
    unsupported_penalty = _unsupported_leap_penalty(candidate)
    full_priority = priority + (order_bonus, rule_bonus, -unsupported_penalty)
    next_state.objective = tuple(left + right for left, right in zip(next_state.objective, full_priority))
    next_state.selected_candidate_ids.add(candidate_key)

    if isinstance(candidate, CandidatePair):
        next_state.aligned_pairs.append(
            AlignedPair(
                baseline_node_id=candidate.baseline_node_id,
                optimized_node_id=candidate.optimized_node_id,
                relation=candidate.relation,
                confidence=candidate.confidence,
                supporting_rule=candidate.supporting_rule,
                semantic_compatibility=dict(candidate.semantic_compatibility),
                observation_compatibility=dict(candidate.observation_compatibility),
                resource_compatibility=dict(candidate.resource_compatibility),
            )
        )
        next_state.used_baseline.add(candidate.baseline_node_id)
        next_state.used_optimized.add(candidate.optimized_node_id)
        return next_state

    next_state.aligned_blocks.append(
        AlignedBlock(
            baseline_node_ids=list(candidate.baseline_node_ids),
            optimized_node_ids=list(candidate.optimized_node_ids),
            relation=candidate.relation,
            confidence=candidate.confidence,
            supporting_rules=list(candidate.supporting_rules),
        )
    )
    next_state.used_baseline.update(candidate.baseline_node_ids)
    next_state.used_optimized.update(candidate.optimized_node_ids)
    return next_state


def _coverage(graph: AlignmentGraph, state: _BeamState) -> dict:
    total_critical = sum(1 for node_id in graph.baseline_ir.order if _node_kind(graph.baseline_ir, node_id) in CRITICAL_KINDS)
    total_critical += sum(1 for node_id in graph.optimized_ir.order if _node_kind(graph.optimized_ir, node_id) in CRITICAL_KINDS)
    matched_critical = _critical_weight(graph.baseline_ir, state.used_baseline) + _critical_weight(graph.optimized_ir, state.used_optimized)
    total_observable = _observable_weight(graph.baseline_ir, graph.baseline_ir.order) + _observable_weight(graph.optimized_ir, graph.optimized_ir.order)
    matched_observable = _observable_weight(graph.baseline_ir, state.used_baseline) + _observable_weight(graph.optimized_ir, state.used_optimized)
    return {
        "critical_total": total_critical,
        "critical_matched": matched_critical,
        "critical_ratio": (matched_critical / total_critical) if total_critical else 1.0,
        "observable_total": total_observable,
        "observable_matched": matched_observable,
        "observable_ratio": (matched_observable / total_observable) if total_observable else 1.0,
    }


def search_alignment(alignment_graph: AlignmentGraph, alignment_config: AlignmentConfig) -> ProvisionalAlignment:
    candidates: List[object] = list(alignment_graph.candidate_blocks) + list(alignment_graph.candidate_pairs)
    candidates.sort(key=lambda item: _candidate_priority(alignment_graph, item), reverse=True)

    beam: List[_BeamState] = [_BeamState()]
    for candidate in candidates:
        next_beam: List[_BeamState] = list(beam)
        for state in beam:
            if _compatible(alignment_graph, candidate, state):
                next_beam.append(_apply_candidate(alignment_graph, candidate, state))
        next_beam.sort(key=lambda state: state.objective, reverse=True)
        beam = next_beam[: max(1, alignment_config.beam_width)]

    best = max(beam, key=lambda state: state.objective)
    unmatched_baseline = [node_id for node_id in alignment_graph.baseline_ir.order if node_id not in best.used_baseline]
    unmatched_optimized = [node_id for node_id in alignment_graph.optimized_ir.order if node_id not in best.used_optimized]
    return ProvisionalAlignment(
        aligned_pairs=best.aligned_pairs,
        aligned_blocks=best.aligned_blocks,
        unmatched_baseline_nodes=unmatched_baseline,
        unmatched_optimized_nodes=unmatched_optimized,
        coverage=_coverage(alignment_graph, best),
    )
