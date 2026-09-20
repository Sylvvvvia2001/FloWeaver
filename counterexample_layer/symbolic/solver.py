from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set, Tuple

from counterexample_layer.symbolic.sym_state import SymConfig


_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_./:-]*")


@dataclass(frozen=True)
class _Atom:
    kind: str
    key: str
    value: Any
    tokens: frozenset[str]
    cost: int

    @property
    def condition(self) -> str:
        if self.kind == "path":
            return str(self.value)
        if self.kind == "framework_event":
            return f"framework_event:{self.value}"
        if self.kind == "resource":
            return f"resource:{self.value}"
        return f"{self.kind}.{self.key}={self.value}"


def _tokens(value: Any) -> Set[str]:
    return {token for token in _TOKEN_RE.findall(str(value)) if token}


def _context_tokens(cfg: SymConfig) -> Set[str]:
    current = cfg.divergence_status.get("current_useg_node", {})
    tokens: Set[str] = set()
    tokens.update(_tokens(current))
    tokens.update(_tokens(cfg.semantic_state_b))
    tokens.update(_tokens(cfg.semantic_state_o))
    trace_tail = []
    if cfg.trace_b.events:
        trace_tail.append(cfg.trace_b.events[-1])
    if cfg.trace_o.events:
        trace_tail.append(cfg.trace_o.events[-1])
    tokens.update(_tokens(trace_tail))
    return tokens


def _candidate_atoms(cfg: SymConfig) -> List[_Atom]:
    env_state = cfg.env_state if isinstance(cfg.env_state, dict) else {}
    atoms: List[_Atom] = []
    for clause in cfg.path_condition.minimal_clauses():
        normalized = str(clause).strip()
        if not normalized:
            continue
        atoms.append(
            _Atom(
                kind="path",
                key=normalized,
                value=normalized,
                tokens=frozenset(_tokens(normalized)),
                cost=1,
            )
        )
    for kind, mapping_name in (
        ("request_params", "request_params"),
        ("symbolic_inputs", "inputs"),
        ("device_results", "device_results"),
        ("toggle_assumptions", "toggles"),
    ):
        mapping = dict(env_state.get(mapping_name, {}))
        for key, value in mapping.items():
            tokens = _tokens(key) | _tokens(value)
            atoms.append(
                _Atom(
                    kind=kind,
                    key=str(key),
                    value=value,
                    tokens=frozenset(tokens),
                    cost=1,
                )
            )
    for event in list(env_state.get("framework_events", [])):
        atoms.append(
            _Atom(
                kind="framework_event",
                key=str(event),
                value=str(event),
                tokens=frozenset(_tokens(event)),
                cost=1,
            )
        )
    for resource_key in sorted(
        set(cfg.semantic_state_b.get("resource_keys", [])) | set(cfg.semantic_state_o.get("resource_keys", []))
    ):
        atoms.append(
            _Atom(
                kind="resource",
                key=str(resource_key),
                value=str(resource_key),
                tokens=frozenset(_tokens(resource_key)),
                cost=1,
            )
        )
    return atoms


def _support_set(atoms: List[_Atom], context_tokens: Set[str]) -> List[_Atom]:
    if not atoms:
        return []
    target_tokens = set(context_tokens)
    explained = set().union(*(atom.tokens for atom in atoms))
    target_tokens.intersection_update(explained)
    if not target_tokens:

        ordered: List[_Atom] = []
        seen: set[Tuple[str, str, str]] = set()
        for atom in atoms:
            identity = (atom.kind, atom.key, str(atom.value))
            if identity in seen:
                continue
            seen.add(identity)
            ordered.append(atom)
        return ordered

    remaining = set(target_tokens)
    selected: List[_Atom] = []
    candidates = list(atoms)
    while remaining and candidates:
        ranked = sorted(
            candidates,
            key=lambda atom: (
                -len(atom.tokens.intersection(remaining)),
                atom.cost,
                len(atom.condition),
            ),
        )
        best = ranked[0]
        covered = best.tokens.intersection(remaining)
        if not covered:
            break
        selected.append(best)
        remaining -= covered
        candidates = [atom for atom in candidates if atom is not best]

    if not selected:
        selected = candidates[:1] if candidates else []


    changed = True
    while changed and len(selected) > 1:
        changed = False
        for atom in list(selected):
            reduced = [item for item in selected if item is not atom]
            covered = set().union(*(item.tokens for item in reduced))
            if target_tokens.issubset(covered):
                selected = reduced
                changed = True
                break
    return selected


def _group_atoms(atoms: Iterable[_Atom]) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    input_assumptions: Dict[str, Any] = {}
    environment_assumptions: Dict[str, Any] = {"path_assumptions": []}
    minimal_conditions: List[str] = []

    for atom in atoms:
        minimal_conditions.append(atom.condition)
        if atom.kind == "path":
            environment_assumptions.setdefault("path_assumptions", []).append(str(atom.value))
        elif atom.kind == "framework_event":
            environment_assumptions.setdefault("framework_events", []).append(str(atom.value))
        elif atom.kind == "resource":
            environment_assumptions.setdefault("resource_assumptions", []).append(str(atom.value))
        elif atom.kind == "request_params":
            input_assumptions.setdefault("request_params", {})[atom.key] = atom.value
        elif atom.kind == "symbolic_inputs":
            input_assumptions.setdefault("symbolic_inputs", {})[atom.key] = atom.value
        elif atom.kind == "device_results":
            environment_assumptions.setdefault("device_results", {})[atom.key] = atom.value
        elif atom.kind == "toggle_assumptions":
            environment_assumptions.setdefault("toggle_assumptions", {})[atom.key] = atom.value

    return input_assumptions, environment_assumptions, minimal_conditions


def minimal_assumptions(cfg: SymConfig) -> Tuple[Dict[str, Any], Dict[str, Any], List[str]]:
    atoms = _candidate_atoms(cfg)
    context_tokens = _context_tokens(cfg)
    support = _support_set(atoms, context_tokens)
    input_assumptions, environment_assumptions, minimal_conditions = _group_atoms(support)
    if not environment_assumptions.get("path_assumptions"):
        for atom in atoms:
            if atom.kind == "path":
                environment_assumptions["path_assumptions"] = [str(atom.value)]
                if atom.condition not in minimal_conditions:
                    minimal_conditions.insert(0, atom.condition)
                break
    current = cfg.divergence_status.get("current_useg_node", {})
    if current.get("suspicious_region_id"):
        environment_assumptions["suspicious_region_id"] = current.get("suspicious_region_id")
    return input_assumptions, environment_assumptions, minimal_conditions
