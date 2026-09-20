from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Tuple

from dsl.contracts import CANONICALIZATION_VERSION, DiffHunk, DiffResult, Event, Trace


COMMUTABLE_OPS = {
    "STATE_WRITE",
    "COORD_REFRESH",
}

VOLATILE_PARAM_KEYS = {"timestamp", "ts", "nonce", "request_id", "uuid"}


OP_ALIASES = {
    "BLE_OP": "BLE_GATT_OP",
    "CLOUD_OP": "CLOUD_HTTP_CALL",
    "CLOUD_CALL": "CLOUD_HTTP_CALL",
    "RETRY_BACKOFF": "CLOUD_BACKOFF_SLEEP",
}


def normalize_op_name(op: Any) -> str:
    token = str(op).strip().upper()
    if not token:
        return ""
    return OP_ALIASES.get(token, token)


def _compare_meta(config: TraceCompareConfig) -> Dict[str, Any]:
    normalized_rules: List[Dict[str, Any]] = []
    for rule in config.equivalence_rules:
        normalized_ops = set()
        for item in rule.get("ops", []):
            normalized = normalize_op_name(item)
            if normalized:
                normalized_ops.add(normalized)
        normalized_scope = sorted({str(item).strip() for item in rule.get("scope", []) if str(item).strip()})
        normalized_rules.append(
            {
                "policy": str(rule.get("policy", "commute")).strip().lower() or "commute",
                "ops": sorted(normalized_ops),
                "group_key": str(rule.get("group_key", "")).strip(),
                "scope": normalized_scope,
            }
        )
    normalized_rules.sort(
        key=lambda item: (
            item.get("policy", ""),
            ",".join(item.get("ops", [])),
            item.get("group_key", ""),
            ",".join(item.get("scope", [])),
        )
    )
    normalized_commutable = set()
    for op in config.commutable_ops:
        normalized = normalize_op_name(op)
        if normalized:
            normalized_commutable.add(normalized)

    payload = {
        "canonicalization_version": config.canonicalization_version,
        "commutable_ops": sorted(normalized_commutable),
        "equivalence_rules": normalized_rules,
        "parallel_action_scopes": sorted(
            [
                sorted({str(item).strip() for item in scope if str(item).strip()})
                for scope in config.parallel_action_scopes
                if isinstance(scope, list)
            ],
            key=lambda item: ",".join(item),
        ),
    }
    payload_raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["config_hash"] = hashlib.sha1(payload_raw).hexdigest()[:16]
    return payload


def trace_compare_meta(config: TraceCompareConfig) -> Dict[str, Any]:
    return _compare_meta(config)


@dataclass
class TraceCompareConfig:
    canonicalization_version: str = CANONICALIZATION_VERSION
    commutable_ops: set[str] = field(default_factory=lambda: set(COMMUTABLE_OPS))
    volatile_param_keys: set[str] = field(default_factory=lambda: set(VOLATILE_PARAM_KEYS))
    equivalence_rules: List[Dict[str, Any]] = field(default_factory=list)
    parallel_action_scopes: List[List[str]] = field(default_factory=list)

    @classmethod
    def from_observation(
        cls,
        canonicalization_version: str | None = None,
        equivalence_whitelist: List[Any] | None = None,
    ) -> "TraceCompareConfig":
        commutable = set(COMMUTABLE_OPS)
        equivalence_rules: List[Dict[str, Any]] = []

        for rule in equivalence_whitelist or []:
            if isinstance(rule, dict):
                policy = str(rule.get("policy", "commute")).strip().lower() or "commute"
                ops_raw = rule.get("ops", rule.get("op"))
                if isinstance(ops_raw, list):
                    ops = []
                    for item in ops_raw:
                        normalized = normalize_op_name(item)
                        if normalized:
                            ops.append(normalized)
                elif ops_raw is not None:
                    op_name = normalize_op_name(ops_raw)
                    ops = [op_name] if op_name else []
                else:
                    ops = []
                if policy == "commute":
                    commutable.update(ops)
                equivalence_rules.append(
                    {
                        "policy": policy,
                        "ops": ops,
                        "group_key": str(rule.get("group_key", "")).strip(),
                        "scope": [str(item).strip() for item in rule.get("scope", []) if str(item).strip()]
                        if isinstance(rule.get("scope", []), list)
                        else [],
                    }
                )
                continue

            token = normalize_op_name(rule)
            if token:
                commutable.add(token)
        return cls(
            canonicalization_version=canonicalization_version or CANONICALIZATION_VERSION,
            commutable_ops=commutable,
            equivalence_rules=equivalence_rules,
        )


def _stable_hash(value: Any) -> str:
    raw = repr(value).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def canonicalize_params(params: Dict[str, Any], config: TraceCompareConfig | None = None) -> Dict[str, Any]:
    config = config or TraceCompareConfig()
    result: Dict[str, Any] = {}
    for key, value in params.items():
        if key in config.volatile_param_keys:
            continue
        if key in {"payload", "body", "json"}:
            result[f"{key}_hash"] = _stable_hash(value)
            continue
        if key == "endpoint":
            result[key] = str(value).strip().lower()
            continue
        if key in {"ble_addr", "mac", "address"}:
            normalized = str(value).replace("-", ":").replace(" ", "").lower()
            result[key] = normalized
            continue
        result[key] = value
    return result


def canonicalize_event(event: Event, config: TraceCompareConfig | None = None) -> Event:
    config = config or TraceCompareConfig()
    return Event(
        ts=0.0,
        provider=event.provider,
        op=normalize_op_name(event.op),
        target=event.target,
        params_abst=canonicalize_params(event.params_abst, config=config),
        phase=event.phase,
        corr_id=None,
    )


def canonicalize_trace(trace: Trace, config: TraceCompareConfig | None = None) -> Trace:
    config = config or TraceCompareConfig()
    canonical_events = [canonicalize_event(event, config=config) for event in trace.events]
    meta = dict(trace.meta)
    meta["canonicalization_version"] = config.canonicalization_version
    return Trace(events=canonical_events, meta=meta)


def _event_key(event: Event) -> Tuple[Any, ...]:
    return (
        event.phase,
        event.provider,
        event.op,
        event.target,
        tuple(sorted(event.params_abst.items())),
    )


def _strict_equal(base: Iterable[Event], opt: Iterable[Event]) -> bool:
    return [_event_key(e) for e in base] == [_event_key(e) for e in opt]


def _event_group_value(event: Event, group_key: str) -> str:
    key = str(group_key).strip().lower()
    if not key:
        return ""
    if key == "target":
        return str(event.target)
    params = event.params_abst if isinstance(event.params_abst, dict) else {}
    if key in params:
        return str(params[key])

    if key in {"endpoint", "entity_id", "device_id", "characteristic", "host"}:
        return str(event.target)
    return ""


def _event_action_id(event: Event) -> str:
    params = event.params_abst if isinstance(event.params_abst, dict) else {}
    return str(params.get("action_id", "")).strip()


def _parallel_scope_lookup(config: TraceCompareConfig) -> Dict[str, frozenset[str]]:
    lookup: Dict[str, frozenset[str]] = {}
    for scope in config.parallel_action_scopes:
        if not isinstance(scope, list):
            continue
        normalized = frozenset(str(item).strip() for item in scope if str(item).strip())
        if len(normalized) < 2:
            continue
        for action_id in normalized:
            lookup[action_id] = normalized
    return lookup


def _parallel_scope_for_events(
    base_event: Event,
    opt_event: Event,
    parallel_scope_lookup: Dict[str, frozenset[str]],
) -> frozenset[str] | None:
    base_action = _event_action_id(base_event)
    opt_action = _event_action_id(opt_event)
    if not base_action or not opt_action:
        return None
    base_scope = parallel_scope_lookup.get(base_action)
    opt_scope = parallel_scope_lookup.get(opt_action)
    if base_scope is None or opt_scope is None or base_scope != opt_scope:
        return None
    return base_scope


def _parallel_scope_window(
    events: List[Event],
    start: int,
    scope: frozenset[str],
) -> Tuple[int, List[Tuple[Any, ...]]]:
    end = start
    window: List[Tuple[Any, ...]] = []
    while end < len(events):
        action_id = _event_action_id(events[end])
        if action_id not in scope:
            break
        window.append(_event_key(events[end]))
        end += 1
    return end, window


def _grouped_commutation_ok(
    base_window: List[Event],
    opt_window: List[Event],
    equivalence_rules: List[Dict[str, Any]],
) -> bool:
    for rule in equivalence_rules:
        if str(rule.get("policy", "commute")).strip().lower() != "commute":
            continue
        group_key = str(rule.get("group_key", "")).strip()
        if not group_key:
            continue
        ops = set()
        for item in rule.get("ops", []):
            normalized = normalize_op_name(item)
            if normalized:
                ops.add(normalized)
        if not ops:
            continue
        base_signature = [
            (event.op, _event_group_value(event, group_key))
            for event in base_window
            if event.op in ops
        ]
        opt_signature = [
            (event.op, _event_group_value(event, group_key))
            for event in opt_window
            if event.op in ops
        ]
        if base_signature != opt_signature:
            return False
    return True


def _tolerant_equal(
    base: List[Event],
    opt: List[Event],
    commutable_ops: set[str],
    equivalence_rules: List[Dict[str, Any]],
    parallel_action_scopes: List[List[str]] | None = None,
) -> bool:
    if len(base) != len(opt):
        return False

    parallel_lookup = _parallel_scope_lookup(
        TraceCompareConfig(parallel_action_scopes=list(parallel_action_scopes or []))
    )
    idx = 0
    while idx < len(base):
        b = base[idx]
        o = opt[idx]
        if _event_key(b) == _event_key(o):
            idx += 1
            continue

        if b.op in commutable_ops and o.op in commutable_ops and b.phase == o.phase:

            j = idx
            base_window: List[Tuple[Any, ...]] = []
            opt_window: List[Tuple[Any, ...]] = []
            while j < len(base) and base[j].op in commutable_ops:
                base_window.append(_event_key(base[j]))
                j += 1
            k = idx
            while k < len(opt) and opt[k].op in commutable_ops:
                opt_window.append(_event_key(opt[k]))
                k += 1
            if Counter(base_window) != Counter(opt_window):
                return False
            if not _grouped_commutation_ok(base[idx:j], opt[idx:k], equivalence_rules):
                return False
            idx = max(j, k)
            continue

        parallel_scope = _parallel_scope_for_events(b, o, parallel_lookup)
        if parallel_scope:
            j, base_window = _parallel_scope_window(base, idx, parallel_scope)
            k, opt_window = _parallel_scope_window(opt, idx, parallel_scope)
            if Counter(base_window) != Counter(opt_window):
                return False
            idx = max(j, k)
            continue

        return False

    return True


def _diff_signature(base: List[Event], opt: List[Event]) -> List[DiffHunk]:
    base_ops = [f"{e.phase}:{e.provider}:{e.op}:{e.target}" for e in base]
    opt_ops = [f"{e.phase}:{e.provider}:{e.op}:{e.target}" for e in opt]
    matcher = SequenceMatcher(a=base_ops, b=opt_ops)
    hunks: List[DiffHunk] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        baseline = base_ops[i1:i2]
        optimized = opt_ops[j1:j2]
        severity = "HIGH" if any("STATE_WRITE" in op for op in baseline + optimized) else "MEDIUM"
        anchor = baseline[0] if baseline else (optimized[0] if optimized else "UNKNOWN")
        hunks.append(
            DiffHunk(
                anchor=anchor,
                baseline_ops=baseline,
                optimized_ops=optimized,
                severity=severity,
            )
        )

    return hunks


def compare_traces(
    trace_base: Trace,
    trace_opt: Trace,
    config: TraceCompareConfig | None = None,
) -> DiffResult:
    config = config or TraceCompareConfig()
    base = canonicalize_trace(trace_base, config=config)
    opt = canonicalize_trace(trace_opt, config=config)

    strict = _strict_equal(base.events, opt.events)
    tolerant = strict or _tolerant_equal(
        base.events,
        opt.events,
        config.commutable_ops,
        config.equivalence_rules,
        config.parallel_action_scopes,
    )
    signature = [] if tolerant else _diff_signature(base.events, opt.events)
    meta = _compare_meta(config)
    return DiffResult(strict_equal=strict, tolerant_equal=tolerant, diff_signature=signature, meta=meta)


@dataclass
class EventAssertionResult:
    passed: bool
    failed_rules: List[str]


def assert_trace_contract(trace: Trace, required_ops: List[str]) -> EventAssertionResult:
    ops = {normalize_op_name(event.op) for event in trace.events}
    failed: List[str] = []
    for op in required_ops:
        normalized = normalize_op_name(op)
        if normalized and normalized not in ops:
            failed.append(normalized)
    return EventAssertionResult(passed=not failed, failed_rules=failed)
