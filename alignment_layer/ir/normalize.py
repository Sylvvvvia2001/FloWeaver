from __future__ import annotations

from typing import Dict, Iterable, List

from runtime.trace import normalize_op_name

from counterexample_layer.ir.ir_types import IRNode, IRProgram, IRSummary
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema

WRAPPER_OPS = {"NOOP", "WRAPPER", "PASS"}
PREPARE_OPS = {"ENTRY_SETUP", "BLE_CONNECT", "CLOUD_SESSION_REUSE", "SUBSCRIBE"}
CLEANUP_OPS = {"UNSUBSCRIBE", "BLE_DISCONNECT", "ENTRY_UNLOAD"}
UPDATE_OPS = {"STATE_WRITE"}
ACT_OPS = {"BLE_GATT_OP", "CLOUD_HTTP_CALL"}


def _classify_node(op: str) -> str:
    if op in {"ENTRY_SETUP"}:
        return "INIT"
    if op in PREPARE_OPS:
        return "PREPARE"
    if op in CLEANUP_OPS:
        return "CLEANUP"
    if op in UPDATE_OPS:
        return "UPDATE"
    if op in ACT_OPS:
        return "ACT"
    if op in {"EXCEPTION", "WAIT_STATE"}:
        return "CHECK"
    return "ACT"


def _resource_claims(summary: IRSummary) -> List[str]:
    claims = []
    for effect in summary.resource_effects:
        claims.append(
            ":".join(
                [
                    str(effect.get("resource_kind", "generic")),
                    str(effect.get("action", "")),
                    str(effect.get("key", summary.target)),
                ]
            )
        )
    return sorted(claims)


def _external_effects(summary: IRSummary, observation_boundary: bool) -> List[str]:
    effects: List[str] = []
    if observation_boundary:
        effects.append(f"{summary.provider}:{summary.op}:{summary.target}")
    if summary.semantic_updates:
        effects.append(f"semantic:{summary.op}:{summary.target}")
    return sorted(set(effects))


def _is_trivial_wrapper(summary: IRSummary) -> bool:
    return (
        summary.op in WRAPPER_OPS
        and not summary.params
        and not summary.resource_effects
        and not summary.semantic_updates
        and not summary.emits_observation
    )


def _normalized_phase(phase: str) -> str:
    token = str(phase or "RUNTIME").strip().upper() or "RUNTIME"
    if token not in {"SETUP", "RUNTIME", "TEARDOWN"}:
        return "RUNTIME"
    return token


def _normalize_summary(summary: IRSummary, schema: CounterexampleObservationSchema) -> IRSummary:
    normalized_op = normalize_op_name(summary.op)
    phase = _normalized_phase(summary.phase)
    emits_observation = bool(summary.emits_observation or normalized_op in set(schema.semantic_ops))
    return IRSummary(
        provider=str(summary.provider).upper(),
        op=normalized_op,
        target=str(summary.target).strip(),
        phase=phase,
        params=dict(summary.params),
        emits_observation=emits_observation,
        resource_effects=[dict(item) for item in summary.resource_effects],
        semantic_updates=dict(summary.semantic_updates),
        exception_category=summary.exception_category,
    )


def _normalize_node(node: IRNode, schema: CounterexampleObservationSchema) -> IRNode:
    summary = _normalize_summary(node.summary, schema)
    observation_boundary = bool(summary.emits_observation or summary.target in set(schema.required_state_writes))
    metadata = dict(node.metadata)
    metadata.update(
        {
            "phase": summary.phase,
            "node_kind": _classify_node(summary.op),
            "observation_boundary": observation_boundary,
            "trace_anchor": f"{summary.provider}:{summary.op}:{summary.target}",
            "resource_claims": _resource_claims(summary),
            "external_effects": _external_effects(summary, observation_boundary),
            "critical_alignment_role": _classify_node(summary.op) in {"ACT", "UPDATE", "CLEANUP"},
        }
    )
    return IRNode(node_id=node.node_id, summary=summary, successors=[], metadata=metadata)


def _materialize_successors(nodes: Dict[str, IRNode], order: Iterable[str]) -> None:
    ordered = list(order)
    for idx, node_id in enumerate(ordered):
        nodes[node_id].successors = [ordered[idx + 1]] if idx + 1 < len(ordered) else []


def normalize_ir(program: IRProgram, observation_schema: CounterexampleObservationSchema) -> IRProgram:
    normalized_nodes: Dict[str, IRNode] = {}
    normalized_order: List[str] = []
    for node_id in program.order:
        raw_node = program.nodes[node_id]
        normalized = _normalize_node(raw_node, observation_schema)
        if _is_trivial_wrapper(normalized.summary):
            continue
        normalized_nodes[node_id] = normalized
        normalized_order.append(node_id)

    _materialize_successors(normalized_nodes, normalized_order)
    entry_node = normalized_order[0] if normalized_order else None
    exit_node = normalized_order[-1] if normalized_order else None
    return IRProgram(
        program_id=program.program_id,
        nodes=normalized_nodes,
        entry_node=entry_node,
        exit_node=exit_node,
        order=normalized_order,
    )
