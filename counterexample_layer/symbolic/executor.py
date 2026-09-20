from __future__ import annotations

import copy
import heapq
from itertools import product
from typing import Any, Dict, List, Tuple

from dsl.contracts import Event, Trace

from counterexample_layer.ir.ir_types import IRNode, IRProgram
from counterexample_layer.ir.useg import USEG, USEGNode
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from counterexample_layer.symbolic.path_condition import PathCondition
from counterexample_layer.symbolic.sym_state import SymConfig


def _initial_env_state(environment_model: Dict[str, Any] | None) -> Dict[str, Any]:
    environment_model = environment_model or {}
    return {
        "inputs": dict(environment_model.get("inputs", {})),
        "request_params": dict(environment_model.get("request_params", {})),
        "device_results": dict(environment_model.get("device_results", {})),
        "toggles": dict(environment_model.get("toggles", {})),
        "framework_events": list(environment_model.get("framework_events", [])),
        "assumptions": list(environment_model.get("assumptions", [])),
        "branches": dict(environment_model.get("branches", {})),
    }


def _current_useg_status(useg: USEG, useg_index: int) -> Dict[str, Any]:
    if not useg.nodes or useg_index >= len(useg.nodes):
        return {}
    node = useg.nodes[useg_index]
    return {
        "useg_node_id": node.useg_node_id,
        "kind": node.kind,
        "suspicious_region_id": node.suspicious_region_id,
        "unsupported_alignment": node.unsupported_alignment,
        "crosses_observation_boundary": node.crosses_observation_boundary,
    }


def init_symbolic_config(
    useg: USEG,
    environment_model: Dict[str, Any] | None,
    resource_model: ResourceModel,
    observation_schema: CounterexampleObservationSchema,
) -> SymConfig:
    del resource_model, observation_schema
    env_state = _initial_env_state(environment_model)
    return SymConfig(
        useg_index=0,
        pc_b=None,
        pc_o=None,
        path_condition=PathCondition([str(item) for item in env_state.get("assumptions", [])]),
        split_offset_b=0,
        split_offset_o=0,
        env_state=env_state,
        resource_state_b={},
        resource_state_o={},
        semantic_state_b={"state_writes": {}, "exception_category": None, "resource_keys": []},
        semantic_state_o={"state_writes": {}, "exception_category": None, "resource_keys": []},
        trace_b=Trace(events=[], meta={"variant": "baseline"}),
        trace_o=Trace(events=[], meta={"variant": "optimized"}),
        mode="UNIFIED",
        divergence_status={
            "current_useg_node": _current_useg_status(useg, 0),
            "at_terminal": not bool(useg.nodes),
        },
        suspicious_region_id=None,
        visited_useg_nodes=[],
        executed_steps=0,
    )


def _event_from_node(node: IRNode) -> Event:
    summary = node.summary
    return Event(
        ts=float(node.metadata.get("ts", 0.0) or 0.0),
        provider=summary.provider,
        op=summary.op,
        target=summary.target,
        params_abst=dict(summary.params),
        phase=summary.phase,
        corr_id=str(node.metadata.get("corr_id")) if node.metadata.get("corr_id") else None,
    )


def _apply_semantic_updates(state: Dict[str, Any], node: IRNode) -> None:
    updates = node.summary.semantic_updates
    if "state_write" in updates:
        writes = state.setdefault("state_writes", {})
        writes.update(dict(updates["state_write"]))
    if "exception" in updates:
        state["exception_category"] = str(updates["exception"])


def _apply_resource_effects(resource_state: Dict[str, Any], node: IRNode) -> None:
    for effect in node.summary.resource_effects:
        resource_kind = str(effect.get("resource_kind", "generic"))
        action = str(effect.get("action", ""))
        key = str(effect.get("key", node.summary.target))
        resources = resource_state.setdefault(resource_kind, {})
        payload = resources.setdefault(key, {"count": 0, "history": []})
        payload["history"].append(action)
        if action == "acquire":
            payload["count"] = int(payload.get("count", 0)) + 1
        elif action == "release":
            if int(payload.get("count", 0)) <= 0:
                payload["premature_release"] = True
            else:
                payload["count"] = int(payload.get("count", 0)) - 1


def _apply_nodes(
    trace: Trace,
    semantic_state: Dict[str, Any],
    resource_state: Dict[str, Any],
    program: IRProgram,
    node_ids: List[str],
) -> None:
    for node_id in node_ids:
        node = program.nodes[node_id]
        if node.summary.emits_observation or node.metadata.get("observation_boundary"):
            trace.events.append(_event_from_node(node))
        _apply_semantic_updates(semantic_state, node)
        _apply_resource_effects(resource_state, node)
    semantic_state["resource_keys"] = sorted(
        f"{resource_kind}:{key}"
        for resource_kind, resources in resource_state.items()
        for key, payload in resources.items()
        if isinstance(payload, dict) and int(payload.get("count", 0))
    )


def _branch_clauses(env_state: Dict[str, Any], useg_node: USEGNode) -> List[List[str]]:
    branches = env_state.get("branches", {}) if isinstance(env_state, dict) else {}
    node_branches = branches.get(useg_node.useg_node_id, [])
    if not isinstance(node_branches, list) or not node_branches:
        return [[]]
    normalized = [str(item).strip() for item in node_branches if str(item).strip()]
    return [[item] for item in normalized] or [[]]


def _extend_condition(path_condition: PathCondition, clauses: List[str]) -> PathCondition:
    current = path_condition
    for clause in clauses:
        current = current.extend(clause)
    return current


def _guard_clauses(prefix: str, key: str, expected: Any) -> Tuple[str, str]:
    normalized_key = str(key)
    normalized_value = repr(expected)
    positive = f"{prefix}.{normalized_key} == {normalized_value}"
    negative = f"NOT({positive})"
    return positive, negative


def _mapping_guard_options(prefix: str, values: Dict[str, Any], guards: Dict[str, Any]) -> List[Tuple[bool, List[str]]]:
    options: List[Tuple[bool, List[str]]] = [(True, [])]
    for key, expected in guards.items():
        positive, negative = _guard_clauses(prefix, key, expected)
        if key in values:
            applies = values.get(key) == expected
            options = [(prev and applies, clauses + [positive if applies else negative]) for prev, clauses in options]
            continue
        expanded: List[Tuple[bool, List[str]]] = []
        for prev, clauses in options:
            expanded.append((prev, clauses + [positive]))
            expanded.append((False, clauses + [negative]))
        options = expanded
    return options


def _framework_guard_options(framework_events: List[Any], guards: Any) -> List[Tuple[bool, List[str]]]:
    if not guards:
        return [(True, [])]
    required_events = []
    if isinstance(guards, dict):
        required_events = [str(key) for key, enabled in guards.items() if bool(enabled)]
    elif isinstance(guards, list):
        required_events = [str(item) for item in guards]
    elif isinstance(guards, str):
        required_events = [guards]
    options: List[Tuple[bool, List[str]]] = [(True, [])]
    known_events = {str(item) for item in framework_events}
    for event_name in required_events:
        positive = f"framework_event:{event_name}"
        negative = f"NOT({positive})"
        if known_events:
            applies = event_name in known_events
            options = [(prev and applies, clauses + [positive if applies else negative]) for prev, clauses in options]
            continue
        expanded: List[Tuple[bool, List[str]]] = []
        for prev, clauses in options:
            expanded.append((prev, clauses + [positive]))
            expanded.append((False, clauses + [negative]))
        options = expanded
    return options


def _node_guard_options(node: IRNode, env_state: Dict[str, Any]) -> List[Tuple[bool, List[str]]]:
    metadata = node.metadata if isinstance(node.metadata, dict) else {}
    option_sets: List[List[Tuple[bool, List[str]]]] = [
        _mapping_guard_options(
            "request_params",
            dict(env_state.get("request_params", {})),
            dict(metadata.get("request_param_guards", {})),
        ),
        _mapping_guard_options(
            "device_results",
            dict(env_state.get("device_results", {})),
            dict(metadata.get("device_result_guards", {})),
        ),
        _mapping_guard_options(
            "toggles",
            dict(env_state.get("toggles", {})),
            dict(metadata.get("toggle_guards", {})),
        ),
        _framework_guard_options(
            list(env_state.get("framework_events", [])),
            metadata.get("framework_event_guards"),
        ),
    ]
    combined: List[Tuple[bool, List[str]]] = []
    for choice_tuple in product(*option_sets):
        applies = all(item[0] for item in choice_tuple)
        clauses: List[str] = []
        for _, extra_clauses in choice_tuple:
            clauses.extend(extra_clauses)
        combined.append((applies, clauses))
    deduped: List[Tuple[bool, List[str]]] = []
    seen: set[Tuple[bool, Tuple[str, ...]]] = set()
    for applies, clauses in combined or [(True, [])]:
        key = (applies, tuple(clauses))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((applies, clauses))
    return deduped or [(True, [])]


def _execution_options(program: IRProgram, node_ids: List[str], env_state: Dict[str, Any]) -> List[Tuple[List[str], List[str]]]:
    options: List[Tuple[List[str], List[str]]] = [([], [])]
    for node_id in node_ids:
        node = program.nodes[node_id]
        node_options = _node_guard_options(node, env_state)
        expanded: List[Tuple[List[str], List[str]]] = []
        for selected_ids, clauses in options:
            for applies, guard_clauses in node_options:
                next_ids = list(selected_ids)
                if applies:
                    next_ids.append(node_id)
                expanded.append((next_ids, clauses + guard_clauses))
        options = expanded
    deduped: List[Tuple[List[str], List[str]]] = []
    seen: set[Tuple[Tuple[str, ...], Tuple[str, ...]]] = set()
    for selected_ids, clauses in options:
        key = (tuple(selected_ids), tuple(clauses))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((selected_ids, clauses))
    return deduped


def _advance_unified_node(
    cfg: SymConfig,
    useg_node: USEGNode,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    clauses: List[str],
    baseline_node_ids: List[str] | None = None,
    optimized_node_ids: List[str] | None = None,
) -> SymConfig:
    next_cfg = copy.deepcopy(cfg)
    next_cfg.useg_index += 1
    next_cfg.split_offset_b = 0
    next_cfg.split_offset_o = 0
    next_cfg.mode = "UNIFIED"
    next_cfg.pc_b = useg_node.baseline_node_ids[-1] if useg_node.baseline_node_ids else next_cfg.pc_b
    next_cfg.pc_o = useg_node.optimized_node_ids[-1] if useg_node.optimized_node_ids else next_cfg.pc_o
    next_cfg.suspicious_region_id = useg_node.suspicious_region_id
    next_cfg.visited_useg_nodes = list(next_cfg.visited_useg_nodes) + [useg_node.useg_node_id]
    if clauses:
        next_cfg.path_condition = _extend_condition(next_cfg.path_condition, clauses)
    active_baseline = baseline_node_ids if baseline_node_ids is not None else useg_node.baseline_node_ids
    active_optimized = optimized_node_ids if optimized_node_ids is not None else useg_node.optimized_node_ids
    if active_baseline:
        next_cfg.pc_b = active_baseline[-1]
    if active_optimized:
        next_cfg.pc_o = active_optimized[-1]
    _apply_nodes(next_cfg.trace_b, next_cfg.semantic_state_b, next_cfg.resource_state_b, baseline_ir, active_baseline)
    _apply_nodes(next_cfg.trace_o, next_cfg.semantic_state_o, next_cfg.resource_state_o, optimized_ir, active_optimized)
    next_cfg.executed_steps += max(len(active_baseline), len(active_optimized), 1 if clauses else 0)
    return next_cfg


def _finish_status(next_cfg: SymConfig, useg: USEG, useg_node: USEGNode) -> None:
    next_cfg.divergence_status = {
        "current_useg_node": {
            "useg_node_id": useg_node.useg_node_id,
            "kind": useg_node.kind,
            "suspicious_region_id": useg_node.suspicious_region_id,
            "unsupported_alignment": useg_node.unsupported_alignment,
            "crosses_observation_boundary": useg_node.crosses_observation_boundary,
        },
        "at_terminal": next_cfg.useg_index >= len(useg.nodes),
    }


def _advance_split_branch(
    cfg: SymConfig,
    useg: USEG,
    useg_node: USEGNode,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    clauses: List[str],
    side: str,
    apply_node: bool = True,
) -> SymConfig:
    next_cfg = copy.deepcopy(cfg)
    next_cfg.mode = "SPLIT"
    next_cfg.suspicious_region_id = useg_node.suspicious_region_id
    if clauses:
        next_cfg.path_condition = _extend_condition(next_cfg.path_condition, clauses)
    next_cfg.visited_useg_nodes = list(next_cfg.visited_useg_nodes) + [useg_node.useg_node_id]

    if side == "baseline" and next_cfg.split_offset_b < len(useg_node.baseline_node_ids):
        node_id = useg_node.baseline_node_ids[next_cfg.split_offset_b]
        if apply_node:
            _apply_nodes(next_cfg.trace_b, next_cfg.semantic_state_b, next_cfg.resource_state_b, baseline_ir, [node_id])
            next_cfg.pc_b = node_id
        next_cfg.split_offset_b += 1
        next_cfg.executed_steps += 1
    elif side == "optimized" and next_cfg.split_offset_o < len(useg_node.optimized_node_ids):
        node_id = useg_node.optimized_node_ids[next_cfg.split_offset_o]
        if apply_node:
            _apply_nodes(next_cfg.trace_o, next_cfg.semantic_state_o, next_cfg.resource_state_o, optimized_ir, [node_id])
            next_cfg.pc_o = node_id
        next_cfg.split_offset_o += 1
        next_cfg.executed_steps += 1

    if (
        next_cfg.split_offset_b >= len(useg_node.baseline_node_ids)
        and next_cfg.split_offset_o >= len(useg_node.optimized_node_ids)
    ):
        next_cfg.useg_index += 1
        next_cfg.split_offset_b = 0
        next_cfg.split_offset_o = 0
    _finish_status(next_cfg, useg, useg_node)
    return next_cfg


def _merge_compatible(cfg: SymConfig) -> bool:
    if cfg.semantic_state_b.get("exception_category") != cfg.semantic_state_o.get("exception_category"):
        return False
    if set(cfg.semantic_state_b.get("resource_keys", [])) != set(cfg.semantic_state_o.get("resource_keys", [])):
        return False
    baseline_writes = cfg.semantic_state_b.get("state_writes", {})
    optimized_writes = cfg.semantic_state_o.get("state_writes", {})
    shared_keys = set(baseline_writes) & set(optimized_writes)
    for key in shared_keys:
        if baseline_writes.get(key) != optimized_writes.get(key):
            return False
    return True


def step_useg(
    cfg: SymConfig,
    useg: USEG,
    baseline_ir: IRProgram,
    optimized_ir: IRProgram,
    observation_schema: CounterexampleObservationSchema,
    resource_model: ResourceModel,
) -> List[SymConfig]:
    del observation_schema, resource_model
    if cfg.useg_index >= len(useg.nodes):
        return []

    useg_node = useg.nodes[cfg.useg_index]
    successors: List[SymConfig] = []
    for base_clauses in _branch_clauses(cfg.env_state, useg_node):
        if useg_node.kind == "UNIFIED":
            baseline_options = _execution_options(baseline_ir, useg_node.baseline_node_ids, cfg.env_state)
            optimized_options = _execution_options(optimized_ir, useg_node.optimized_node_ids, cfg.env_state)
            for baseline_ids, baseline_clauses in baseline_options:
                for optimized_ids, optimized_clauses in optimized_options:
                    clauses = base_clauses + baseline_clauses + optimized_clauses
                    if baseline_ids == useg_node.baseline_node_ids and optimized_ids == useg_node.optimized_node_ids:
                        next_cfg = _advance_unified_node(
                            cfg,
                            useg_node,
                            baseline_ir,
                            optimized_ir,
                            clauses,
                            baseline_node_ids=baseline_ids,
                            optimized_node_ids=optimized_ids,
                        )
                    elif not baseline_ids and not optimized_ids:
                        next_cfg = _advance_unified_node(
                            cfg,
                            useg_node,
                            baseline_ir,
                            optimized_ir,
                            clauses,
                            baseline_node_ids=[],
                            optimized_node_ids=[],
                        )
                    else:
                        next_cfg = _advance_unified_node(
                            cfg,
                            useg_node,
                            baseline_ir,
                            optimized_ir,
                            clauses,
                            baseline_node_ids=baseline_ids,
                            optimized_node_ids=optimized_ids,
                        )
                        next_cfg.mode = "SPLIT"
                    _finish_status(next_cfg, useg, useg_node)
                    successors.append(next_cfg)
            continue

        if useg_node.kind == "MERGE":
            baseline_options = _execution_options(baseline_ir, useg_node.baseline_node_ids, cfg.env_state)
            optimized_options = _execution_options(optimized_ir, useg_node.optimized_node_ids, cfg.env_state)
            if _merge_compatible(cfg):
                for baseline_ids, baseline_clauses in baseline_options:
                    for optimized_ids, optimized_clauses in optimized_options:
                        clauses = base_clauses + baseline_clauses + optimized_clauses
                        if baseline_ids == useg_node.baseline_node_ids and optimized_ids == useg_node.optimized_node_ids:
                            next_cfg = _advance_unified_node(
                                cfg,
                                useg_node,
                                baseline_ir,
                                optimized_ir,
                                clauses,
                                baseline_node_ids=baseline_ids,
                                optimized_node_ids=optimized_ids,
                            )
                        elif not baseline_ids and not optimized_ids:
                            next_cfg = _advance_unified_node(
                                cfg,
                                useg_node,
                                baseline_ir,
                                optimized_ir,
                                clauses,
                                baseline_node_ids=[],
                                optimized_node_ids=[],
                            )
                        else:
                            next_cfg = _advance_unified_node(
                                cfg,
                                useg_node,
                                baseline_ir,
                                optimized_ir,
                                clauses,
                                baseline_node_ids=baseline_ids,
                                optimized_node_ids=optimized_ids,
                            )
                            next_cfg.mode = "SPLIT"
                        _finish_status(next_cfg, useg, useg_node)
                        successors.append(next_cfg)
                continue

            split_like = copy.deepcopy(useg_node)
            split_like.kind = "SPLIT"
            if cfg.split_offset_b < len(split_like.baseline_node_ids):
                node = baseline_ir.nodes[split_like.baseline_node_ids[cfg.split_offset_b]]
                for applies, guard_clauses in _node_guard_options(node, cfg.env_state):
                    successors.append(
                        _advance_split_branch(
                            cfg,
                            useg,
                            split_like,
                            baseline_ir,
                            optimized_ir,
                            base_clauses + guard_clauses,
                            side="baseline",
                            apply_node=applies,
                        )
                    )
            if cfg.split_offset_o < len(split_like.optimized_node_ids):
                node = optimized_ir.nodes[split_like.optimized_node_ids[cfg.split_offset_o]]
                for applies, guard_clauses in _node_guard_options(node, cfg.env_state):
                    successors.append(
                        _advance_split_branch(
                            cfg,
                            useg,
                            split_like,
                            baseline_ir,
                            optimized_ir,
                            base_clauses + guard_clauses,
                            side="optimized",
                            apply_node=applies,
                        )
                    )
            continue

        if useg_node.kind == "SPLIT":
            if cfg.split_offset_b < len(useg_node.baseline_node_ids):
                node = baseline_ir.nodes[useg_node.baseline_node_ids[cfg.split_offset_b]]
                for applies, guard_clauses in _node_guard_options(node, cfg.env_state):
                    successors.append(
                        _advance_split_branch(
                            cfg,
                            useg,
                            useg_node,
                            baseline_ir,
                            optimized_ir,
                            base_clauses + guard_clauses,
                            side="baseline",
                            apply_node=applies,
                        )
                    )
            if cfg.split_offset_o < len(useg_node.optimized_node_ids):
                node = optimized_ir.nodes[useg_node.optimized_node_ids[cfg.split_offset_o]]
                for applies, guard_clauses in _node_guard_options(node, cfg.env_state):
                    successors.append(
                        _advance_split_branch(
                            cfg,
                            useg,
                            useg_node,
                            baseline_ir,
                            optimized_ir,
                            base_clauses + guard_clauses,
                            side="optimized",
                            apply_node=applies,
                        )
                    )
            if not useg_node.baseline_node_ids and not useg_node.optimized_node_ids:
                next_cfg = copy.deepcopy(cfg)
                next_cfg.useg_index += 1
                _finish_status(next_cfg, useg, useg_node)
                successors.append(next_cfg)
    return successors


def step_bound_exceeded(cfg: SymConfig, max_steps: int) -> bool:
    return cfg.executed_steps >= max_steps


def rank_config(cfg: SymConfig, suspicious_regions: List[Dict[str, Any]] | None = None) -> Tuple[int, int, int, int, int]:
    suspicious_ids = {
        str(item.get("region_id", ""))
        for item in suspicious_regions or []
        if str(item.get("region_id", ""))
    }
    current = cfg.divergence_status.get("current_useg_node", {})
    suspicious_penalty = 0 if cfg.suspicious_region_id and cfg.suspicious_region_id in suspicious_ids else 1
    observation_penalty = 0 if current.get("crosses_observation_boundary") else 1
    resource_penalty = 0 if cfg.semantic_state_b.get("resource_keys") or cfg.semantic_state_o.get("resource_keys") else 1
    weak_signal_penalty = 0 if (
        cfg.mode == "SPLIT"
        or len(cfg.trace_b.events) != len(cfg.trace_o.events)
        or (
            cfg.trace_b.events
            and cfg.trace_o.events
            and (
                cfg.trace_b.events[-1].op != cfg.trace_o.events[-1].op
                or cfg.trace_b.events[-1].target != cfg.trace_o.events[-1].target
            )
        )
    ) else 1
    return (
        suspicious_penalty,
        observation_penalty,
        resource_penalty,
        weak_signal_penalty,
        cfg.executed_steps,
    )


def push_config(queue: List[Tuple[Tuple[int, int, int, int, int], int, SymConfig]], priority: Tuple[int, int, int, int, int], order: int, cfg: SymConfig) -> None:
    heapq.heappush(queue, (priority, order, cfg))


def pop_config(queue: List[Tuple[Tuple[int, int, int, int, int], int, SymConfig]]) -> SymConfig:
    _, _, cfg = heapq.heappop(queue)
    return cfg
