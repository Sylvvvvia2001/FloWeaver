from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel

from alignment_layer.ir.compatibility import (
    observation_compatibility,
    resource_compatibility,
    score_node_alignment,
    semantic_compatibility,
)
from alignment_layer.rules.alignment_rules import AlignmentConfig


@dataclass
class CandidatePair:
    baseline_node_id: str
    optimized_node_id: str
    relation: str
    score: float
    confidence: float
    supporting_rule: str | None = None
    semantic_compatibility: Dict[str, Any] = field(default_factory=dict)
    observation_compatibility: Dict[str, Any] = field(default_factory=dict)
    resource_compatibility: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateBlock:
    baseline_node_ids: List[str]
    optimized_node_ids: List[str]
    relation: str
    confidence: float
    supporting_rules: List[str] = field(default_factory=list)
    semantic_compatibility: Dict[str, Any] = field(default_factory=dict)
    observation_compatibility: Dict[str, Any] = field(default_factory=dict)
    resource_compatibility: Dict[str, Any] = field(default_factory=dict)


def _trace_anchor_score(b_node, o_node) -> float:
    return 0.05 if b_node.summary.target and b_node.summary.target == o_node.summary.target else 0.0


def _resource_roles(node, resource_model: ResourceModel) -> Dict[str, str]:
    roles: Dict[str, str] = {}
    op = str(node.summary.op)
    for resource_kind, rule in resource_model.rules.items():
        if op in rule.acquire_ops:
            roles[resource_kind] = "acquire"
        elif op in rule.release_ops:
            roles[resource_kind] = "release"
        elif op in rule.required_before:
            roles[resource_kind] = "required_before"
    return roles


def _resource_roles_compatible(b_node, o_node, resource_model: ResourceModel) -> bool:
    left = _resource_roles(b_node, resource_model)
    right = _resource_roles(o_node, resource_model)
    return left == right or (not left and not right)


def _is_required_anchor(node, schema: CounterexampleObservationSchema) -> bool:
    op = str(node.summary.op)
    target = str(node.summary.target)
    return (
        op in set(schema.anchor_ops)
        or op in set(schema.semantic_ops)
        or target in set(schema.required_state_writes)
        or bool(node.metadata.get("observation_boundary"))
    )


def generate_alignment_candidates(
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
    alignment_config: AlignmentConfig,
) -> Tuple[List[CandidatePair], List[CandidateBlock]]:
    candidates: List[CandidatePair] = []
    for baseline_node_id in baseline_ir.order:
        b_node = baseline_ir.nodes[baseline_node_id]
        local: List[CandidatePair] = []
        for optimized_node_id in optimized_ir.order:
            o_node = optimized_ir.nodes[optimized_node_id]
            semantic = semantic_compatibility(b_node, o_node)
            observation = observation_compatibility(b_node, o_node)
            resource = resource_compatibility(b_node, o_node)
            if not semantic.get("phase_compatible", False):
                continue
            if not _resource_roles_compatible(b_node, o_node, resource_model):
                continue
            if (
                b_node.metadata.get("observation_boundary")
                and o_node.metadata.get("observation_boundary")
                and not observation.get("compatible", False)
            ):
                continue
            if (_is_required_anchor(b_node, observation_schema) or _is_required_anchor(o_node, observation_schema)) and not observation.get("compatible", False):
                continue
            score = score_node_alignment(b_node, o_node)
            if score < alignment_config.confidence_threshold:
                continue
            score = round(score + _trace_anchor_score(b_node, o_node), 5)
            local.append(
                CandidatePair(
                    baseline_node_id=baseline_node_id,
                    optimized_node_id=optimized_node_id,
                    relation="EXACT",
                    score=score,
                    confidence=score,
                    supporting_rule=None,
                    semantic_compatibility=semantic,
                    observation_compatibility=observation,
                    resource_compatibility=resource,
                )
            )
        local.sort(key=lambda item: (item.score, item.observation_compatibility.get("compatible", False)), reverse=True)
        candidates.extend(local[: min(3, alignment_config.max_candidate_pairs)])

    candidates.sort(key=lambda item: (item.score, item.confidence), reverse=True)
    candidates = candidates[: alignment_config.max_candidate_pairs]

    candidate_blocks: List[CandidateBlock] = []
    contiguous: List[CandidatePair] = []
    for candidate in candidates:
        if candidate.confidence < alignment_config.high_confidence_threshold:
            continue
        contiguous.append(candidate)
    contiguous.sort(
        key=lambda item: (
            baseline_ir.order.index(item.baseline_node_id),
            optimized_ir.order.index(item.optimized_node_id),
        )
    )
    run: List[CandidatePair] = []
    for candidate in contiguous:
        if not run:
            run = [candidate]
            continue
        prev = run[-1]
        b_prev = baseline_ir.order.index(prev.baseline_node_id)
        o_prev = optimized_ir.order.index(prev.optimized_node_id)
        b_cur = baseline_ir.order.index(candidate.baseline_node_id)
        o_cur = optimized_ir.order.index(candidate.optimized_node_id)
        if b_cur == b_prev + 1 and o_cur == o_prev + 1:
            run.append(candidate)
            continue
        if len(run) >= 2:
            candidate_blocks.append(
                CandidateBlock(
                    baseline_node_ids=[item.baseline_node_id for item in run],
                    optimized_node_ids=[item.optimized_node_id for item in run],
                    relation="SERIAL_EQ",
                    confidence=sum(item.confidence for item in run) / len(run),
                )
            )
        run = [candidate]
    if len(run) >= 2:
        candidate_blocks.append(
            CandidateBlock(
                baseline_node_ids=[item.baseline_node_id for item in run],
                optimized_node_ids=[item.optimized_node_id for item in run],
                relation="SERIAL_EQ",
                confidence=sum(item.confidence for item in run) / len(run),
            )
        )
    return candidates, candidate_blocks
