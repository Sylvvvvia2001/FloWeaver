from __future__ import annotations

from typing import Any, Dict, List

from dsl.contracts import Event, Trace
from runtime.trace import canonicalize_trace, normalize_op_name, TraceCompareConfig

from counterexample_layer.ir.ir_types import IRNode, IRProgram, IRSummary


def _resource_effects(event: Event) -> List[Dict[str, Any]]:
    op = normalize_op_name(event.op)
    target = str(event.target)
    if op == "ENTRY_SETUP":
        return [{"resource_kind": "manager", "action": "acquire", "key": target or "entry"}]
    if op == "SUBSCRIBE":
        return [{"resource_kind": "listener", "action": "acquire", "key": target}]
    if op == "UNSUBSCRIBE":
        return [{"resource_kind": "listener", "action": "release", "key": target}]
    if op == "BLE_CONNECT":
        return [{"resource_kind": "connection", "action": "acquire", "key": target}]
    if op in {"BLE_DISCONNECT", "ENTRY_UNLOAD"}:
        effects = [{"resource_kind": "connection", "action": "release", "key": target}]
        if op == "ENTRY_UNLOAD":
            effects.append({"resource_kind": "manager", "action": "release", "key": target or "entry"})
            effects.append({"resource_kind": "session", "action": "release", "key": target or "entry"})
        return effects
    if op == "CLOUD_SESSION_REUSE":
        return [
            {"resource_kind": "cloud_session", "action": "acquire", "key": target},
            {"resource_kind": "session", "action": "acquire", "key": target},
        ]
    return []


def _semantic_updates(event: Event) -> Dict[str, Any]:
    op = normalize_op_name(event.op)
    params = dict(event.params_abst) if isinstance(event.params_abst, dict) else {}
    if op == "STATE_WRITE":
        value = None
        for key in ("state", "value", "payload_hash", "body_hash", "json_hash"):
            if key in params:
                value = params[key]
                break
        return {"state_write": {str(event.target): value if value is not None else params}}
    if op == "EXCEPTION":
        category = params.get("category") or params.get("exception") or "Exception"
        return {"exception": str(category)}
    return {}


def _exception_category(event: Event) -> str | None:
    if normalize_op_name(event.op) != "EXCEPTION":
        return None
    params = event.params_abst if isinstance(event.params_abst, dict) else {}
    category = params.get("category") or params.get("exception") or "Exception"
    return str(category)


def event_to_ir_node(event: Event, index: int, prefix: str) -> IRNode:
    node_id = f"{prefix}_{index:04d}"
    summary = IRSummary(
        provider=str(event.provider),
        op=normalize_op_name(event.op),
        target=str(event.target),
        phase=str(event.phase),
        params=dict(event.params_abst) if isinstance(event.params_abst, dict) else {},
        emits_observation=True,
        resource_effects=_resource_effects(event),
        semantic_updates=_semantic_updates(event),
        exception_category=_exception_category(event),
    )
    return IRNode(
        node_id=node_id,
        summary=summary,
        successors=[],
        metadata={"ts": event.ts, "corr_id": event.corr_id},
    )


def trace_to_ir_program(
    trace: Trace,
    program_id: str,
    compare_config: TraceCompareConfig | None = None,
) -> IRProgram:
    canonical = canonicalize_trace(trace, config=compare_config or TraceCompareConfig())
    nodes: Dict[str, IRNode] = {}
    order: List[str] = []
    previous_id: str | None = None
    for idx, event in enumerate(canonical.events):
        node = event_to_ir_node(event, idx, prefix=program_id)
        nodes[node.node_id] = node
        order.append(node.node_id)
        if previous_id is not None:
            nodes[previous_id].successors.append(node.node_id)
        previous_id = node.node_id
    entry = order[0] if order else None
    exit_node = order[-1] if order else None
    return IRProgram(program_id=program_id, nodes=nodes, entry_node=entry, exit_node=exit_node, order=order)
