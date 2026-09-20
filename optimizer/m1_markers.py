from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from dsl.contracts import HAPProfile, Marker, MarkerStrength, OptimizationTarget, Phase
from optimizer.ast_utils import iter_function_nodes, parse_python_file
from optimizer.m1_grounding_profiles import (
    CompiledGroundingRule,
    load_compiled_grounding_profiles,
    rule_context_matches,
    rule_matches_call,
    rule_matches_file,
    rule_matches_function,
    rule_score,
)


MAC_RE = re.compile(r"^(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}$", re.IGNORECASE)
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
ENTITY_ID_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
BLE_DEVICE_RUNTIME_ATTRS = {
    "open",
    "close",
    "stop",
    "set_position",
    "turn_on",
    "turn_off",
    "press",
    "push",
    "update",
    "refresh",
}
BLE_DEVICE_RUNTIME_FN_HINTS = {
    "cover",
    "blind",
    "tilt",
    "shade",
    "garage",
    "fan",
    "relay",
    "switch",
    "curtain",
}
MIN_PRIMARY_BINDING_SCORE = 0.75
MIN_SECONDARY_BINDING_SCORE = 0.45
CLOUD_PROTOCOL_MODULE_HINTS = {
    "aiohttp",
    "httpx",
    "requests",
    "urllib3",
    "tuya_sharing",
    "device_wrapper",
}
BLE_PROTOCOL_MODULE_HINTS = {"bleak", "bluetooth", "gatt"}
CLOUD_PROTOCOL_CALL_HINTS = {
    "call_api",
    "async_call_api",
    "send_commands",
    "get_update_commands",
    "read_device_status",
    "async_send_commands",
    "device_manager",
    "tuya_sharing",
    "device_wrapper",
}
PROPERTY_GETTER_NAMES = {
    "available",
    "device_info",
    "extra_state_attributes",
    "icon",
    "is_on",
    "name",
    "native_unit_of_measurement",
    "native_value",
    "state",
    "supported_features",
    "unique_id",
    "value",
}
CONTROL_FUNCTION_PREFIXES = (
    "async_turn_",
    "turn_",
    "set_",
    "async_set_",
    "create_",
    "delete_",
    "open_",
    "close_",
    "async_open_",
    "async_close_",
    "send_",
    "async_send_",
    "write_",
    "publish_",
    "press_",
    "push_",
)
GENERIC_PROFILE_SUPPRESSIBLE_TYPES = {"CLOUD_OP", "BLE_OP"}


@dataclass
class MarkerSet:
    markers: List[Marker]
    index_by_function: Dict[str, List[str]]
    diagnostics: Dict[str, object]


@dataclass
class _AnchorContext:
    entities: Set[str]
    endpoints: Set[str]
    endpoint_prefixes: Set[str]
    device_ids: Set[str]
    device_macs_normalized: Set[str]
    characteristics: Set[str]
    characteristics_uuid_normalized: Set[str]


@dataclass
class _ActionMatcher:
    action_id: str
    action_type: str
    target_kind: str
    exec_domain: str
    exec_service: str
    action_kind_tokens: Set[str]
    marker_hints: Set[str]
    target_tokens: Set[str]
    service_tokens: Set[str]
    bound_file_paths: Set[str]
    bound_integrations: Set[str]
    bound_protocols: Set[str]
    primary_scope_token: str | None
    lane_tag: str | None


@dataclass
class _ActionBinding:
    primary_action_id: str | None
    secondary_action_ids: List[str]
    binding_reason: List[str]
    binding_score: Dict[str, float]


@dataclass
class _SourceBindingContext:
    file_path: str
    integrations: Set[str]
    protocols: Set[str]


def _is_shared_infra_marker_type(marker_type: str) -> bool:
    return str(marker_type).strip().upper() in {
        "SUBSCRIBE",
        "UNSUBSCRIBE",
        "BLE_CONNECT",
        "BLE_DISCONNECT",
        "CLOUD_BATCH_CALL",
        "CLOUD_SESSION_REUSE",
        "ENTRY_SETUP",
        "ENTRY_UNLOAD",
        "ENTRY_REMOVE",
        "COORD_REFRESH",
        "COORD_FIRST_REFRESH",
    }


def _marker_id(
    marker_type: str,
    file_path: str,
    fn: str,
    line: int,
    col_start: int,
    col_end: int,
    node_kind: str,
) -> str:
    payload = f"{marker_type}:{file_path}:{fn}:{line}:{col_start}:{col_end}:{node_kind}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"marker_{digest}"


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _attribute_chain(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        left = _attribute_chain(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _call_chain(call: ast.Call) -> str:
    return _attribute_chain(call.func)


def _normalize_mac(value: str) -> str:
    return value.strip().lower().replace("-", ":")


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    token = str(value).strip().lower()
    if not token:
        return ""
    if MAC_RE.match(token):
        return _normalize_mac(token)
    return token


def _collect_import_aliases(tree: ast.AST) -> Tuple[Dict[str, str], Dict[str, str], Set[str]]:
    module_aliases: Dict[str, str] = {}
    symbol_aliases: Dict[str, str] = {}
    imported_modules: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for row in node.names:
                module = str(row.name).strip()
                if not module:
                    continue
                imported_modules.add(module.split(".")[0].lower())
                if row.asname:
                    module_aliases[row.asname] = module.lower()
        elif isinstance(node, ast.ImportFrom):
            module = str(node.module or "").strip().lower()
            if module:
                imported_modules.add(module.split(".")[0].lower())
            for row in node.names:
                local_name = row.asname or row.name
                if not local_name:
                    continue
                symbol_aliases[local_name] = str(row.name).lower()
                if module:
                    symbol_aliases[f"{local_name}.__module__"] = module

    return module_aliases, symbol_aliases, imported_modules


def _expand_chain_alias(
    chain: str,
    module_aliases: Dict[str, str],
    symbol_aliases: Dict[str, str],
    local_aliases: Dict[str, str],
) -> Set[str]:
    chain_l = chain.lower()
    if not chain_l:
        return set()
    parts = chain_l.split(".")
    root = parts[0]
    tail = ".".join(parts[1:])
    variants = {chain_l}

    replacements: List[str] = []
    if root in local_aliases:
        replacements.append(local_aliases[root].lower())
    if root in symbol_aliases:
        replacements.append(symbol_aliases[root].lower())
    if root in module_aliases:
        replacements.append(module_aliases[root].lower())

    for replacement in replacements:
        if tail:
            variants.add(f"{replacement}.{tail}")
        else:
            variants.add(replacement)
    return variants


def _call_tokens(
    call: ast.Call,
    symbol_aliases: Dict[str, str],
    module_aliases: Dict[str, str],
    local_aliases: Dict[str, str],
) -> Set[str]:
    chain = _call_chain(call)
    name = _call_name(call)
    raw = {item.lower() for item in (chain, name) if item}
    if chain and "." in chain:
        suffix = ".".join(chain.lower().split(".")[-2:])
        raw.add(suffix)

    expanded: Set[str] = set()
    for token in raw:
        expanded.add(token)
        expanded |= _expand_chain_alias(token, module_aliases, symbol_aliases, local_aliases)


    if isinstance(call.func, ast.Name):
        alias = symbol_aliases.get(call.func.id)
        if alias:
            expanded.add(alias.lower().split(".")[-1])

    return {token for token in expanded if token}


def _token_matches_attr(token: str, attr: str) -> bool:
    token_l = token.lower()
    attr_l = attr.lower()
    if token_l == attr_l:
        return True
    if token_l.endswith(f".{attr_l}"):
        return True
    if "." in attr_l and token_l.endswith(attr_l):
        return True
    return False


def _call_matches_detector(call_tokens: Set[str], call_attrs: Set[str]) -> bool:
    for attr in call_attrs:
        if any(_token_matches_attr(token, attr) for token in call_tokens):
            return True
    return False


def _is_ble_device_runtime_call(
    call_tokens: Set[str],
    function_name: str,
    file_binding_context: _SourceBindingContext,
) -> bool:
    if "BLE" not in file_binding_context.protocols:
        return False
    if not any(
        any(_token_matches_attr(token, attr) for token in call_tokens)
        for attr in BLE_DEVICE_RUNTIME_ATTRS
    ):
        return False

    if any(
        token.startswith(("self._device", "_device", "self.device", "device", "self.coordinator.device", "coordinator.device"))
        or ".device." in token
        or token.startswith(("switchbot.", "bleak."))
        for token in call_tokens
    ):
        return True

    fn_name = function_name.strip().lower()
    return fn_name.startswith("async_") and any(hint in fn_name for hint in BLE_DEVICE_RUNTIME_FN_HINTS)


def _should_skip_protocol_detector(
    marker_type: str,
    call_tokens: Set[str],
    function_name: str,
    file_binding_context: _SourceBindingContext,
) -> bool:
    marker = str(marker_type).strip().upper()
    if marker != "BLE_DISCONNECT":
        return False
    if any(_token_matches_attr(token, "disconnect") for token in call_tokens):
        return False
    return _is_ble_device_runtime_call(call_tokens, function_name, file_binding_context)


def _resolve_alias_target(
    value: ast.AST,
    module_aliases: Dict[str, str],
    symbol_aliases: Dict[str, str],
    local_aliases: Dict[str, str],
) -> str | None:
    if isinstance(value, ast.Call):
        return _resolve_alias_target(value.func, module_aliases, symbol_aliases, local_aliases)
    chain = _attribute_chain(value)
    if chain:
        variants = _expand_chain_alias(chain, module_aliases, symbol_aliases, local_aliases)
        if variants:

            return max(variants, key=len)
    if isinstance(value, ast.Name):
        local = local_aliases.get(value.id)
        if local:
            return local
        if value.id in symbol_aliases:
            return symbol_aliases[value.id].lower()
        if value.id in module_aliases:
            return module_aliases[value.id].lower()
        return value.id.lower()
    return None


def _collect_local_aliases(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    known_attrs: Set[str],
    module_aliases: Dict[str, str],
    symbol_aliases: Dict[str, str],
) -> Dict[str, str]:
    aliases: Dict[str, str] = {}
    for node in ast.walk(fn):
        target_names: List[str] = []
        resolved: str | None = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    target_names.append(target.id)
            resolved = _resolve_alias_target(node.value, module_aliases, symbol_aliases, aliases)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                target_names.append(node.target.id)
            if node.value is not None:
                resolved = _resolve_alias_target(node.value, module_aliases, symbol_aliases, aliases)
        if not target_names or not resolved:
            continue

        if not any(_token_matches_attr(resolved, attr) for attr in known_attrs):
            continue
        for name in target_names:
            aliases[name] = resolved
    return aliases


def _module_context_ok(detector: Dict[str, Any], imported_modules: Set[str], call_tokens: Set[str]) -> bool:
    module_hints = detector.get("module_hints", [])
    if not module_hints:
        return True

    hints = {str(item).strip().lower() for item in module_hints if str(item).strip()}
    if not hints:
        return True

    if imported_modules & hints:
        return True

    for token in call_tokens:
        token_parts = set(token.split("."))
        if token_parts & hints:
            return True

    return False


def _protocol_context_ok(call_tokens: Set[str], imported_modules: Set[str], marker_type: str) -> bool:
    marker_u = str(marker_type).strip().upper()
    if marker_u.startswith("CLOUD_"):
        return bool(imported_modules & CLOUD_PROTOCOL_MODULE_HINTS) or any(
            any(hint in token for hint in (CLOUD_PROTOCOL_MODULE_HINTS | CLOUD_PROTOCOL_CALL_HINTS))
            for token in call_tokens
        )
    if marker_u.startswith("BLE_"):
        return bool(imported_modules & BLE_PROTOCOL_MODULE_HINTS) or any(
            any(hint in token for hint in BLE_PROTOCOL_MODULE_HINTS) for token in call_tokens
        )
    return True


def _is_cloud_runtime_call(
    call_tokens: Set[str],
    function_name: str,
    imported_modules: Set[str],
) -> bool:
    lowered_fn = function_name.strip().lower()
    if lowered_fn and any(hint in lowered_fn for hint in CLOUD_PROTOCOL_CALL_HINTS):
        return True
    if not _protocol_context_ok(call_tokens, imported_modules, "CLOUD_OP"):
        return False
    return any(hint in token for token in call_tokens for hint in CLOUD_PROTOCOL_CALL_HINTS)


def _is_protocol_marker(marker_type: str) -> bool:
    token = str(marker_type).strip().upper()
    return token.startswith("BLE_") or token.startswith("CLOUD_")


def _marker_protocols(marker_type: str, base_protocols: Set[str]) -> Set[str]:
    marker = str(marker_type).strip().upper()
    inferred = set(base_protocols)
    if marker.startswith("BLE_"):
        inferred.add("BLE")
    if marker.startswith("CLOUD_"):
        inferred.add("CLOUD")
    if marker in {"STATE_WRITE", "SUBSCRIBE", "UNSUBSCRIBE", "COORD_REFRESH", "COORD_FIRST_REFRESH"}:
        inferred.add("HA")
    if marker == "LOCAL_API_READ":
        inferred.add("LOCAL")
    if marker == "MQTT_SUBSCRIBE":
        inferred.add("MQTT")
    if marker == "POLL_UPDATE":
        inferred.add("CLOUD")
    return inferred


def _should_drop_unbound_runtime_marker(marker_type: str, phase: str, binding: _ActionBinding, has_target: bool) -> bool:
    if not has_target:
        return False
    if str(phase).strip().upper() != Phase.RUNTIME.value:
        return False
    if binding.primary_action_id is not None:
        return False
    return str(marker_type).strip().upper() in {"CLOUD_HTTP_CALL", "CLOUD_OP", "STATE_WRITE"}


def _downgrade_strength(strength: str) -> str:
    token = str(strength).strip().upper()
    if token == MarkerStrength.STRONG.value:
        return MarkerStrength.MEDIUM.value
    if token == MarkerStrength.MEDIUM.value:
        return MarkerStrength.WEAK.value
    return MarkerStrength.WEAK.value


def _strength_at_most(current: str, cap: str) -> str:
    order = {
        MarkerStrength.STRONG.value: 2,
        MarkerStrength.MEDIUM.value: 1,
        MarkerStrength.WEAK.value: 0,
    }
    current_u = str(current).strip().upper() or MarkerStrength.MEDIUM.value
    cap_u = str(cap).strip().upper() or MarkerStrength.MEDIUM.value
    if order.get(current_u, 1) <= order.get(cap_u, 1):
        return current_u
    return cap_u


def _has_phase_mismatch_evidence(evidence: List[str]) -> bool:
    return any(str(item).startswith("phase_mismatch:") for item in evidence)


def _context_weak_protocol_marker(
    marker_type: str,
    evidence: List[str],
    binding: _ActionBinding,
    strength: str,
) -> str:
    marker_u = str(marker_type).strip().upper()
    if binding.primary_action_id is None:
        return strength
    if "context_missing:module_hints" not in evidence:
        return strength
    if marker_u not in {"BLE_CONNECT", "BLE_DISCONNECT", "CLOUD_HTTP_CALL", "CLOUD_OP"}:
        return strength
    return _strength_at_most(strength, MarkerStrength.MEDIUM.value)


def _phase_mismatch_adjusted_protocol_strength(
    marker_type: str,
    phase: str,
    binding: _ActionBinding,
    evidence: List[str],
    strength: str,
) -> str:
    marker_u = str(marker_type).strip().upper()
    phase_u = str(phase).strip().upper()
    if marker_u == "BLE_CONNECT" and phase_u == Phase.TEARDOWN.value and binding.primary_action_id is not None:
        if "phase_mismatch:teardown_connect" not in evidence:
            evidence.append("phase_mismatch:teardown_connect")
        return _strength_at_most(strength, MarkerStrength.MEDIUM.value)
    return strength


def _collect_string_literals(call: ast.Call) -> Set[str]:
    values: Set[str] = set()
    for node in ast.walk(call):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(_normalize_token(node.value))
    return {value for value in values if value}


def _endpoint_match(literal: str, endpoint: str) -> bool:
    if not literal or not endpoint:
        return False
    if endpoint.startswith(("http://", "https://")):
        return literal.startswith(endpoint)
    if ":" in endpoint and "." in endpoint:
        return literal == endpoint or literal.startswith(f"{endpoint}/")
    if "/" in endpoint:
        return literal.startswith(endpoint)
    return literal == endpoint


def _anchor_context(target: OptimizationTarget | None) -> _AnchorContext:
    if target is None:
        return _AnchorContext(
            entities=set(),
            endpoints=set(),
            endpoint_prefixes=set(),
            device_ids=set(),
            device_macs_normalized=set(),
            characteristics=set(),
            characteristics_uuid_normalized=set(),
        )

    anchors = target.target_anchors if isinstance(target.target_anchors, dict) else {}
    entities = {
        _normalize_token(item)
        for item in anchors.get("entities", [])
        if ENTITY_ID_RE.match(_normalize_token(item))
    }

    endpoints: Set[str] = set()
    endpoint_prefixes: Set[str] = set()
    for item in anchors.get("endpoints", []):
        token = _normalize_token(item)
        if not token:
            continue
        if token.startswith(("http://", "https://")) or "/" in token:
            endpoint_prefixes.add(token)
        else:
            endpoints.add(token)

    device_ids = {_normalize_token(item) for item in anchors.get("device_ids", []) if _normalize_token(item)}
    characteristics = {_normalize_token(item) for item in anchors.get("characteristics", []) if _normalize_token(item)}
    device_macs_normalized = {_normalize_mac(item) for item in device_ids if MAC_RE.match(item)}
    characteristics_uuid_normalized = {item.lower() for item in characteristics if UUID_RE.match(item)}
    return _AnchorContext(
        entities=entities,
        endpoints=endpoints,
        endpoint_prefixes=endpoint_prefixes,
        device_ids=device_ids,
        device_macs_normalized=device_macs_normalized,
        characteristics=characteristics,
        characteristics_uuid_normalized=characteristics_uuid_normalized,
    )


def _call_matches_anchor(call_literals: Set[str], anchor_ctx: _AnchorContext) -> bool:
    if not call_literals:
        return False

    for literal in call_literals:
        if literal in anchor_ctx.entities:
            return True
        if literal in anchor_ctx.device_ids:
            return True
        if literal in anchor_ctx.characteristics:
            return True

        if MAC_RE.match(literal):
            if _normalize_mac(literal) in anchor_ctx.device_macs_normalized:
                return True
        if UUID_RE.match(literal) and literal.lower() in anchor_ctx.characteristics_uuid_normalized:
            return True

        for endpoint in anchor_ctx.endpoints:
            if _endpoint_match(literal, endpoint):
                return True
        for prefix in anchor_ctx.endpoint_prefixes:
            if literal.startswith(prefix):
                return True

    return False


def _anchor_ops(target: OptimizationTarget | None, allowed_ops: Set[str]) -> Set[str]:
    if target is None:
        return set()
    abstract_hints = {"BLE_OP", "CLOUD_OP"}
    anchor_ops: Set[str] = set()
    for item in target.target_anchors.get("anchor_ops", []):
        token = str(item).strip().upper()
        if not token or token in abstract_hints:
            continue
        if token in allowed_ops:
            anchor_ops.add(token)
    return anchor_ops


def _nearest_subscribe_related(
    subscribe_markers: Dict[str, List[Tuple[int, int, List[str]]]],
    fn_name: str,
    line: int,
    col: int,
) -> List[str]:
    rows = subscribe_markers.get(fn_name, [])
    if not rows:
        return []

    before = [item for item in rows if item[0] < line or (item[0] == line and item[1] <= col)]
    ordered = before if before else rows
    if before:
        ordered = sorted(ordered, key=lambda item: (item[0], item[1]), reverse=True)
    else:
        ordered = sorted(ordered, key=lambda item: (abs(item[0] - line), abs(item[1] - col)))

    for _, _, related in ordered:
        if related:
            return list(related)
    return []


def _collect_action_tokens(value: Any) -> Set[str]:
    tokens: Set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            tokens |= _collect_action_tokens(item)
        return tokens
    if isinstance(value, list):
        for item in value:
            tokens |= _collect_action_tokens(item)
        return tokens
    if isinstance(value, str):
        token = _normalize_token(value)
        if token:
            tokens.add(token)
    return tokens


def _scope_token_from_action(action: Dict[str, Any]) -> str | None:
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    for value in (
        target.get("device_id"),
        target.get("endpoint"),
        target.get("entity_id"),
        target.get("id"),
        exec_cfg.get("device_id"),
        exec_cfg.get("endpoint"),
        exec_cfg.get("entity_id"),
    ):
        token = _normalize_token(value)
        if token:
            return token
    return None


def _infer_lane_tag(action: Dict[str, Any]) -> str | None:
    protocol = _action_protocol(action)
    if protocol == "BLE":
        return "BLE_LOCAL"
    if protocol == "CLOUD":
        return "CLOUD"
    if protocol == "HA":
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        entity = _normalize_token(target.get("entity_id") or target.get("id") or "")
        if "overall" in entity:
            return "WRITEBACK_OVERALL"
        if "ble_lane" in entity:
            return "WRITEBACK_BLE"
        if "cloud_lane" in entity:
            return "WRITEBACK_CLOUD"
        return "WRITEBACK"
    return None


def _match_text_tokens(
    call_literals: Set[str],
    call_tokens: Set[str] | None,
    function_name: str,
    file_path: str,
) -> Set[str]:
    tokens = set(call_literals)
    tokens |= {str(item).strip().lower() for item in (call_tokens or set()) if str(item).strip()}
    fn = function_name.strip().lower()
    if fn:
        tokens.add(fn)
        tokens |= {part for part in re.split(r"[^a-z0-9_]+", fn) if part}
    file_stem = Path(file_path).stem.strip().lower()
    if file_stem:
        tokens.add(file_stem)
        tokens |= {part for part in re.split(r"[^a-z0-9_]+", file_stem) if part}
    return {token for token in tokens if token}


def _normalize_path(value: Any) -> str:
    text = str(value).strip()
    if not text:
        return ""
    return str(Path(text).expanduser().resolve())


def _normalize_protocols(values: Any) -> Set[str]:
    if not isinstance(values, list):
        return set()
    return {str(item).strip().upper() for item in values if str(item).strip()}


def _action_protocol(action: Dict[str, Any]) -> str:
    protocol = str(action.get("protocol", "")).strip().upper()
    if protocol:
        return protocol
    io_cfg = action.get("io", {})
    if isinstance(io_cfg, dict):
        return str(io_cfg.get("protocol", "")).strip().upper()
    return ""


def _binding_rows(target: OptimizationTarget | None) -> List[Dict[str, Any]]:
    if target is None:
        return []
    rows = target.source_scope.get("file_bindings", [])
    if not isinstance(rows, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        file_path = _normalize_path(row.get("file_path"))
        if not file_path:
            continue
        normalized.append(
            {
                "file_path": file_path,
                "integration": str(row.get("integration", "")).strip().lower(),
                "device_id": _normalize_token(row.get("device_id", "")),
                "protocols": _normalize_protocols(row.get("protocols", [])),
            }
        )
    return normalized


def _source_binding_context(target: OptimizationTarget | None, file_path: str) -> _SourceBindingContext:
    normalized_path = _normalize_path(file_path)
    integrations: Set[str] = set()
    protocols: Set[str] = set()
    for row in _binding_rows(target):
        if row["file_path"] != normalized_path:
            continue
        if row["integration"]:
            integrations.add(row["integration"])
        protocols |= set(row["protocols"])
    path_obj = Path(normalized_path)
    file_stem = path_obj.stem.strip().lower()
    parent_name = path_obj.parent.name.strip().lower()
    if file_stem:
        integrations.add(file_stem)
    if parent_name:
        integrations.add(parent_name)
    return _SourceBindingContext(file_path=normalized_path, integrations=integrations, protocols=protocols)


def _service_tokens(action: Dict[str, Any]) -> Set[str]:
    tokens: Set[str] = set()
    exec_cfg = action.get("exec", {})
    if isinstance(exec_cfg, dict):
        domain = _normalize_token(exec_cfg.get("domain", ""))
        service = _normalize_token(exec_cfg.get("service", ""))
        if domain:
            tokens.add(domain)
        if service:
            tokens.add(service)
        if domain and service:
            tokens.add(f"{domain}.{service}")
    target = action.get("target", {})
    if isinstance(target, dict):
        kind = _normalize_token(target.get("kind", ""))
        if kind:
            tokens.add(kind)
    target_kind = _normalize_token(action.get("target_kind", ""))
    if target_kind:
        tokens.add(target_kind)
    protocol = _action_protocol(action)
    if protocol:
        tokens.add(protocol.lower())
    return {token for token in tokens if token}


def _split_hint_tokens(*values: Any) -> Set[str]:
    tokens: Set[str] = set()
    for value in values:
        token = _normalize_token(value)
        if not token:
            continue
        tokens.add(token)
        tokens |= {part for part in re.split(r"[^a-z0-9_]+", token) if part}
    return tokens


def _action_kind_tokens(action: Dict[str, Any]) -> Set[str]:
    exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    return _split_hint_tokens(
        action.get("type", ""),
        action.get("target_kind", ""),
        target.get("kind", ""),
        exec_cfg.get("kind", ""),
        exec_cfg.get("domain", ""),
        exec_cfg.get("service", ""),
    )


def _tokens_overlap(left: Set[str], right: Set[str]) -> bool:
    if not left or not right:
        return False
    for left_token in left:
        for right_token in right:
            if left_token == right_token:
                return True
            if _token_matches_attr(left_token, right_token):
                return True
            if _token_matches_attr(right_token, left_token):
                return True
    return False


def _exact_tokens_overlap(left: Set[str], right: Set[str]) -> bool:
    if not left or not right:
        return False
    left_n = {_normalize_token(item) for item in left if _normalize_token(item)}
    right_n = {_normalize_token(item) for item in right if _normalize_token(item)}
    return bool(left_n & right_n)


def _action_matchers(target: OptimizationTarget | None) -> List[_ActionMatcher]:
    if target is None:
        return []

    bindings = _binding_rows(target)
    matchers: List[_ActionMatcher] = []
    for action in target.vdev_actions:
        action_id = str(action.get("action_id", "")).strip()
        if not action_id:
            continue
        action_type = _normalize_token(action.get("type", ""))
        marker_hints = {str(item).strip().upper() for item in action.get("marker_hints", []) if str(item).strip()}
        if not marker_hints:
            continue
        target_cfg = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        target_kind = _normalize_token(action.get("target_kind", "") or target_cfg.get("kind", ""))
        target_tokens = _collect_action_tokens(action.get("target", {}))
        target_tokens |= _collect_action_tokens(action.get("exec", {}))
        service_tokens = _service_tokens(action)
        target_tokens |= service_tokens
        primary_scope_token = _scope_token_from_action(action)

        action_protocol = _action_protocol(action)
        exec_domain = _normalize_token(exec_cfg.get("domain", ""))
        exec_service = _normalize_token(exec_cfg.get("service", ""))

        bound_file_paths: Set[str] = set()
        bound_integrations: Set[str] = set()
        bound_protocols: Set[str] = set()
        scope_tokens = {
            token
            for token in {
                primary_scope_token,
                _normalize_token(action.get("target_kind", "")),
                _normalize_token(action_id),
            }
            if token
        }
        for row in bindings:
            device_match = bool(scope_tokens and row["device_id"] and row["device_id"] in scope_tokens)
            integration_match = bool(exec_domain and exec_domain == row["integration"])
            protocol_match = bool(action_protocol and action_protocol in row["protocols"])
            if device_match:
                pass
            elif integration_match and protocol_match:
                pass
            else:
                continue
            bound_file_paths.add(row["file_path"])
            if row["integration"]:
                bound_integrations.add(row["integration"])
            bound_protocols |= set(row["protocols"])

        if action_protocol:
            bound_protocols.add(action_protocol)
        if exec_domain:
            bound_integrations.add(exec_domain)

        matchers.append(
            _ActionMatcher(
                action_id=action_id,
                action_type=action_type,
                target_kind=target_kind,
                exec_domain=exec_domain,
                exec_service=exec_service,
                action_kind_tokens=_action_kind_tokens(action),
                marker_hints=marker_hints,
                target_tokens=target_tokens,
                service_tokens=service_tokens,
                bound_file_paths=bound_file_paths,
                bound_integrations=bound_integrations,
                bound_protocols=bound_protocols,
                primary_scope_token=primary_scope_token,
                lane_tag=_infer_lane_tag(action),
            )
        )
    return matchers


def _related_actions(
    marker_type: str,
    call_literals: Set[str],
    action_matchers: List[_ActionMatcher],
    *,
    marker_file_path: str,
    marker_integrations: Set[str],
    marker_protocols: Set[str],
    call_tokens: Set[str] | None = None,
    function_name: str = "",
    preferred_action_kinds: Set[str] | None = None,
    boost_target_tokens: Set[str] | None = None,
    preferred_action_ids: Set[str] | None = None,
    allow_generalized_secondary_binding: bool = False,
) -> _ActionBinding:
    marker_type_u = marker_type.upper()
    preferred_action_kinds_n = {
        _normalize_token(item)
        for item in (preferred_action_kinds or set())
        if _normalize_token(item)
    }
    boost_target_tokens_n = {
        _normalize_token(item)
        for item in (boost_target_tokens or set())
        if _normalize_token(item)
    }
    preferred_action_ids_n = {
        str(item or "").strip()
        for item in (preferred_action_ids or set())
        if str(item or "").strip()
    }
    candidates: List[_ActionMatcher] = []
    for item in action_matchers:
        hints = item.marker_hints
        if marker_type_u in hints:
            candidates.append(item)
            continue
        if marker_type_u.startswith("BLE_") and "BLE_OP" in hints:
            candidates.append(item)
            continue
        if marker_type_u.startswith("CLOUD_") and "CLOUD_OP" in hints:
            candidates.append(item)
            continue
    if not candidates:
        return _ActionBinding(primary_action_id=None, secondary_action_ids=[], binding_reason=[], binding_score={})

    marker_file = _normalize_path(marker_file_path)
    marker_tokens = _match_text_tokens(call_literals, call_tokens, function_name, marker_file_path)

    scored: List[tuple[float, str, List[str], Dict[str, float]]] = []
    for item in candidates:
        score_parts: Dict[str, float] = {}
        reasons: List[str] = []
        file_binding_match = bool(item.bound_file_paths and marker_file in item.bound_file_paths)
        literal_match = bool(call_literals and item.target_tokens and (item.target_tokens & call_literals))
        service_match = bool(marker_tokens and item.service_tokens and _tokens_overlap(marker_tokens, item.service_tokens))
        target_token_match = bool(marker_tokens and item.target_tokens and _tokens_overlap(marker_tokens, item.target_tokens))
        scope_token_match = bool(item.primary_scope_token and item.primary_scope_token in marker_tokens)
        binding_hint_action_kind_match = bool(
            preferred_action_kinds_n
            and item.action_kind_tokens
            and _tokens_overlap(item.action_kind_tokens, preferred_action_kinds_n)
        )
        binding_hint_target_match = bool(
            boost_target_tokens_n
            and (item.target_tokens | item.service_tokens | item.action_kind_tokens)
            and _exact_tokens_overlap(item.target_tokens | item.service_tokens | item.action_kind_tokens, boost_target_tokens_n)
        )

        if item.bound_file_paths and not file_binding_match and not (
            literal_match
            or service_match
            or target_token_match
            or scope_token_match
            or binding_hint_action_kind_match
            or binding_hint_target_match
        ):
            continue

        if marker_type_u in item.marker_hints:
            score_parts["hint_score"] = 0.25
            reasons.append("hint_exact_match")
        elif marker_type_u.startswith("BLE_") and "BLE_OP" in item.marker_hints:
            score_parts["hint_score"] = 0.15
            reasons.append("hint_ble_generic")
        elif marker_type_u.startswith("CLOUD_") and "CLOUD_OP" in item.marker_hints:
            score_parts["hint_score"] = 0.15
            reasons.append("hint_cloud_generic")

        if literal_match:
            score_parts["literal_score"] = 0.35
            reasons.append("literal_overlap")
        if file_binding_match:
            score_parts["file_binding_score"] = 0.30
            reasons.append("file_binding_match")
        if marker_integrations and item.bound_integrations and (marker_integrations & item.bound_integrations):
            score_parts["integration_score"] = 0.15
            reasons.append("integration_binding_match")
        if marker_protocols and item.bound_protocols and (marker_protocols & item.bound_protocols):
            score_parts["protocol_score"] = 0.10
            reasons.append("protocol_binding_match")
        if service_match:
            score_parts["service_score"] = 0.25
            reasons.append("service_token_match")
        elif target_token_match:
            score_parts["target_token_score"] = 0.10
            reasons.append("target_token_match")
        if scope_token_match:
            score_parts["scope_token_score"] = 0.30
            reasons.append("scope_token_match")
        if binding_hint_action_kind_match:
            score_parts["binding_hint_action_kind_score"] = 0.20
            reasons.append("binding_hint_action_kind")
        if binding_hint_target_match:
            score_parts["binding_hint_target_token_score"] = 0.12
            reasons.append("binding_hint_target_token")
        if preferred_action_ids_n and item.action_id in preferred_action_ids_n:
            score_parts["binding_hint_action_id_score"] = 0.12
            reasons.append("binding_hint_action_id")

        total_score = round(sum(score_parts.values()), 4)
        scored.append((total_score, item.action_id, reasons, score_parts))

    scored.sort(key=lambda item: (-item[0], item[1]))
    if not scored:
        return _ActionBinding(primary_action_id=None, secondary_action_ids=[], binding_reason=[], binding_score={})
    max_score = scored[0][0]
    if max_score > 0:
        primary_score, primary_action_id, primary_reasons, primary_parts = scored[0]
        threshold = MIN_PRIMARY_BINDING_SCORE
        if _is_shared_infra_marker_type(marker_type_u) and "hint_exact_match" in primary_reasons:
            if {"literal_overlap", "service_token_match", "scope_token_match"} & set(primary_reasons):
                threshold = 0.60
            elif len(scored) == 1 and marker_type_u == "UNSUBSCRIBE":


                threshold = 0.25
        if (
            marker_type_u.startswith("CLOUD_")
            and "hint_exact_match" in primary_reasons
            and {"integration_binding_match", "protocol_binding_match"}.issubset(set(primary_reasons))
        ):
            threshold = min(threshold, 0.50)
        if primary_score < threshold:
            primary_action_id = None
            primary_reasons = []
            primary_parts = {}
        secondary_action_ids: List[str] = []
        if primary_action_id and (_is_shared_infra_marker_type(marker_type_u) or allow_generalized_secondary_binding):
            for score, action_id, _, _ in scored[1:]:
                if score < MIN_SECONDARY_BINDING_SCORE:
                    continue
                if preferred_action_ids_n and action_id not in preferred_action_ids_n:
                    continue
                if score >= max_score - 0.05:
                    secondary_action_ids.append(action_id)
        if _is_shared_infra_marker_type(marker_type_u):
            strong_reasons = {"file_binding_match", "hint_exact_match"}
            if not strong_reasons.intersection(primary_reasons):
                primary_action_id = None
                secondary_action_ids = []
                primary_reasons = []
                primary_parts = {}
        binding_reason = list(primary_reasons)
        if secondary_action_ids:
            binding_reason.append(
                "generalized_profile_secondary_binding"
                if allow_generalized_secondary_binding and not _is_shared_infra_marker_type(marker_type_u)
                else "shared_infra_secondary_binding"
            )
        binding_score = dict(primary_parts)
        binding_score["total"] = primary_score if primary_action_id else 0.0
        return _ActionBinding(
            primary_action_id=primary_action_id,
            secondary_action_ids=sorted(set(secondary_action_ids)),
            binding_reason=binding_reason,
            binding_score=binding_score,
        )

    return _ActionBinding(primary_action_id=None, secondary_action_ids=[], binding_reason=[], binding_score={})


def _infer_function_phases(tree: ast.AST) -> Dict[str, str]:
    local_functions = {fn.name for fn in iter_function_nodes(tree)}
    callers_of: Dict[str, Set[str]] = {name: set() for name in local_functions}

    for fn in iter_function_nodes(tree):
        for node in ast.walk(fn):
            if not isinstance(node, ast.Call):
                continue
            callee = ""
            if isinstance(node.func, ast.Name):
                callee = node.func.id
            elif isinstance(node.func, ast.Attribute):
                callee = node.func.attr
            if callee in local_functions:
                callers_of.setdefault(callee, set()).add(fn.name)

    phase_by_function: Dict[str, str] = {}
    for fn_name in local_functions:
        if fn_name == "async_setup_entry":
            phase_by_function[fn_name] = Phase.SETUP.value
        elif fn_name in {"async_unload_entry", "async_remove_entry"}:
            phase_by_function[fn_name] = Phase.TEARDOWN.value

    changed = True
    while changed:
        changed = False
        for fn_name in sorted(local_functions):
            if fn_name in phase_by_function:
                continue
            caller_phases = {phase_by_function[caller] for caller in callers_of.get(fn_name, set()) if caller in phase_by_function}
            if caller_phases == {Phase.SETUP.value}:
                phase_by_function[fn_name] = Phase.SETUP.value
                changed = True
            elif caller_phases == {Phase.TEARDOWN.value}:
                phase_by_function[fn_name] = Phase.TEARDOWN.value
                changed = True

    for fn_name in local_functions:
        phase_by_function.setdefault(fn_name, Phase.RUNTIME.value)
    return phase_by_function


def _emit(
    out: List[Marker],
    seen_keys: Set[Tuple[Any, ...]],
    marker_type: str,
    file_path: str,
    fn_name: str,
    line_start: int,
    line_end: int,
    col_start: int,
    col_end: int,
    node_kind: str,
    strength: str,
    phase: str,
    evidence: List[str],
    primary_action_id: str | None,
    secondary_action_ids: List[str],
    binding_reason: List[str],
    binding_score: float,
) -> bool:
    dedupe_key = (
        marker_type,
        file_path,
        fn_name,
        line_start,
        line_end,
        col_start,
        col_end,
        node_kind,
    )
    if dedupe_key in seen_keys:
        new_refs = {
            action_id
            for action_id in ([primary_action_id] + list(secondary_action_ids))
            if str(action_id or "").strip()
        }
        new_profile_rule = _profile_rule_id_from_evidence(evidence)
        if new_profile_rule and new_refs:
            for marker in out:
                if (
                    marker.marker_type == marker_type
                    and marker.file_path == file_path
                    and marker.function_name == fn_name
                    and marker.line_start == line_start
                    and marker.line_end == line_end
                    and _profile_rule_id_from_evidence(list(marker.evidence))
                ):
                    existing_refs = _marker_action_refs(marker)
                    merged_refs = sorted(existing_refs | new_refs)
                    primary = marker.primary_action_id or primary_action_id
                    marker.primary_action_id = primary
                    marker.secondary_action_ids = [
                        action_id
                        for action_id in merged_refs
                        if action_id != primary
                    ]
                    marker.related_action_ids = merged_refs
                    marker.evidence = list(dict.fromkeys([*marker.evidence, *evidence]))
                    marker.binding_reason = list(dict.fromkeys([*marker.binding_reason, *binding_reason]))
                    marker.binding_score = max(float(marker.binding_score or 0.0), float(binding_score or 0.0))
                    return True
        return False
    seen_keys.add(dedupe_key)
    out.append(
        Marker(
            marker_id=_marker_id(marker_type, file_path, fn_name, line_start, col_start, col_end, node_kind),
            marker_type=marker_type,
            file_path=file_path,
            function_name=fn_name,
            line_start=line_start,
            line_end=line_end,
            strength=strength,
            phase=phase,
            evidence=evidence,
            primary_action_id=primary_action_id,
            secondary_action_ids=sorted(set(secondary_action_ids)),
            related_action_ids=sorted(
                {
                    action_id
                    for action_id in ([primary_action_id] + list(secondary_action_ids))
                    if str(action_id or "").strip()
                }
            ),
            binding_reason=list(binding_reason),
            binding_score=float(binding_score),
        )
    )
    return True


def _profile_rule_id_from_evidence(evidence: List[str]) -> str:
    for item in evidence:
        token = str(item or "").strip()
        if token.startswith("grounding_profile_rule:"):
            return token.split(":", 1)[1].strip()
    return ""


def _marker_action_refs(marker: Marker) -> Set[str]:
    refs: Set[str] = set()
    for item in [marker.primary_action_id, *marker.secondary_action_ids, *marker.related_action_ids]:
        token = str(item or "").strip()
        if token:
            refs.add(token)
    return refs


def _rule_action_refs(rule: CompiledGroundingRule) -> Set[str]:
    refs: Set[str] = set()
    for item in [*rule.generalizes_actions, *rule.source_unresolved_action_ids]:
        token = str(item or "").strip()
        if token:
            refs.add(token)
    return refs


def _marker_location_key(marker: Marker) -> tuple[str, str, int, str]:
    return (
        str(marker.file_path or "").strip(),
        str(marker.function_name or "").strip(),
        int(getattr(marker, "line_start", 0) or 0),
        str(getattr(marker, "primary_action_id", "") or "").strip(),
    )


def _marker_binding_precedence(marker: Marker) -> int:
    if marker.marker_type in GENERIC_PROFILE_SUPPRESSIBLE_TYPES:
        return 2
    if _profile_rule_id_from_evidence(marker.evidence):
        return 0
    return 1


def _marker_inferred_role(marker: Marker) -> str:
    fn_name = str(marker.function_name or "").strip().lower()
    if fn_name == "__init__" or fn_name in {"async_setup_entry", "setup_entry"}:
        return "setup"
    if fn_name in PROPERTY_GETTER_NAMES:
        return "property_getter"
    if any(fn_name.startswith(prefix) for prefix in CONTROL_FUNCTION_PREFIXES):
        return "runtime_write"
    if any(token in fn_name for token in ("connect", "reconnect")):
        return "runtime_connect"
    if any(token in fn_name for token in ("subscribe", "listener", "notify", "message")):
        return "runtime_subscribe"
    if any(token in fn_name for token in ("update", "refresh", "read", "status", "poll", "fetch", "runtime")):
        return "runtime_read"
    return ""


def _marker_inferred_path_signals(marker: Marker) -> Set[str]:
    fn_name = str(marker.function_name or "").strip().lower()
    role = _marker_inferred_role(marker)
    signals: Set[str] = set()
    if role == "setup":
        signals.add(f"setup_function:{fn_name}")
    if role == "property_getter":
        signals.add(f"state_accessor_property:{fn_name}")
    if role == "runtime_write":
        signals.add(f"control_function:{fn_name}")
    if role == "runtime_read":
        signals.add(f"read_function:{fn_name}")
        if "update" in fn_name:
            signals.add(f"update_callback_function:{fn_name}")
        if "refresh" in fn_name:
            signals.add(f"refresh_call:{fn_name}")
    if role == "runtime_connect":
        signals.add(f"connect_function:{fn_name}")
    if role == "runtime_subscribe":
        signals.add(f"subscription_function:{fn_name}")
    return signals


def _rule_family_covers_marker(rule: CompiledGroundingRule, marker_type: str) -> bool:
    marker_type_u = str(marker_type or "").strip().upper()
    if marker_type_u == rule.family:
        return True
    if marker_type_u == "CLOUD_OP" and rule.family.startswith("CLOUD_"):
        return True
    if marker_type_u == "BLE_OP" and (rule.family.startswith("BLE_") or rule.family in {"SUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE"}):
        return True
    return False


def _profile_suppresses_baseline_marker(
    marker: Marker,
    *,
    matched_rules_same_file: List[CompiledGroundingRule],
    matched_profile_markers_same_function: List[tuple[Marker, CompiledGroundingRule]],
) -> bool:
    if _profile_rule_id_from_evidence(marker.evidence):
        return False

    marker_refs = _marker_action_refs(marker)
    for profile_marker, rule in matched_profile_markers_same_function:
        if not _rule_family_covers_marker(rule, marker.marker_type):
            continue
        if marker.marker_type not in GENERIC_PROFILE_SUPPRESSIBLE_TYPES:
            continue
        profile_refs = _marker_action_refs(profile_marker)
        if marker_refs and profile_refs and not (marker_refs & profile_refs):
            continue
        return True

    inferred_role = _marker_inferred_role(marker)
    inferred_signals = _marker_inferred_path_signals(marker)
    for rule in matched_rules_same_file:
        if not _rule_family_covers_marker(rule, marker.marker_type):
            continue
        rule_refs = _rule_action_refs(rule)
        if marker_refs and rule_refs and not (marker_refs & rule_refs):
            continue
        if any(pattern.match(marker.function_name) for pattern in rule.negative_function_patterns):
            return True
        if inferred_role and inferred_role in rule.forbidden_runtime_roles:
            return True
        if inferred_signals and rule.forbidden_path_signals & inferred_signals:
            return True
    return False


def _suppress_generic_markers_with_profile(
    markers: List[Marker],
    profile_hits: Dict[tuple[str, str, int, str], Marker],
) -> tuple[List[Marker], int]:
    if not profile_hits:
        return markers, 0
    filtered: List[Marker] = []
    suppressed = 0
    for marker in markers:
        if _profile_rule_id_from_evidence(marker.evidence):
            filtered.append(marker)
            continue
        if marker.marker_type not in GENERIC_PROFILE_SUPPRESSIBLE_TYPES:
            filtered.append(marker)
            continue
        key = _marker_location_key(marker)
        profile_marker = profile_hits.get(key)
        if profile_marker is None:
            filtered.append(marker)
            continue
        if _marker_action_refs(marker) and _marker_action_refs(profile_marker) and not (_marker_action_refs(marker) & _marker_action_refs(profile_marker)):
            filtered.append(marker)
            continue
        suppressed += 1
    return filtered, suppressed


def _apply_profile_driven_suppressor(
    markers: List[Marker],
    file_grounding_rules: List[CompiledGroundingRule],
) -> tuple[List[Marker], int]:
    if not markers or not file_grounding_rules:
        return markers, 0

    rules_by_id = {rule.rule_id: rule for rule in file_grounding_rules}
    matched_rules_same_file: Dict[str, List[CompiledGroundingRule]] = {}
    matched_profile_markers_same_function: Dict[tuple[str, str], List[tuple[Marker, CompiledGroundingRule]]] = {}
    matched_specific_markers_same_location: Dict[tuple[str, str, int, str], Marker] = {}
    for marker in markers:
        if marker.marker_type not in GENERIC_PROFILE_SUPPRESSIBLE_TYPES:
            current = matched_specific_markers_same_location.get(_marker_location_key(marker))
            if current is None or bool(_profile_rule_id_from_evidence(marker.evidence)):
                matched_specific_markers_same_location[_marker_location_key(marker)] = marker
        rule_id = _profile_rule_id_from_evidence(marker.evidence)
        if not rule_id:
            continue
        rule = rules_by_id.get(rule_id)
        if rule is None:
            continue
        matched_rules_same_file.setdefault(marker.file_path, []).append(rule)
        matched_profile_markers_same_function.setdefault((marker.file_path, marker.function_name), []).append((marker, rule))

    if not matched_rules_same_file and not matched_specific_markers_same_location:
        return markers, 0

    markers, generic_suppressed_count = _suppress_generic_markers_with_profile(
        markers,
        matched_specific_markers_same_location,
    )

    filtered: List[Marker] = []
    suppressed_count = generic_suppressed_count
    for marker in markers:
        rules_same_file = matched_rules_same_file.get(marker.file_path, [])
        if not rules_same_file:
            filtered.append(marker)
            continue
        same_function_profiles = matched_profile_markers_same_function.get((marker.file_path, marker.function_name), [])
        if _profile_suppresses_baseline_marker(
            marker,
            matched_rules_same_file=rules_same_file,
            matched_profile_markers_same_function=same_function_profiles,
        ):
            suppressed_count += 1
            continue
        filtered.append(marker)
    return filtered, suppressed_count


def detect_markers(path: str | Path, profile: HAPProfile, optimization_target: OptimizationTarget | None = None) -> MarkerSet:
    file_path = str(Path(path))
    tree = parse_python_file(path)
    if tree is None:
        return MarkerSet(markers=[], index_by_function={}, diagnostics={"parse_error": True})

    markers: List[Marker] = []
    seen_marker_keys: Set[Tuple[Any, ...]] = set()
    subscribe_callback_vars: Set[str] = set()
    subscribe_callback_related_actions: Dict[str, List[str]] = {}
    subscribe_markers_by_function: Dict[str, List[Tuple[int, int, List[str]]]] = {}
    anchor_ctx = _anchor_context(optimization_target)
    action_matchers = _action_matchers(optimization_target)
    file_binding_context = _source_binding_context(optimization_target, file_path)
    grounding_rules, grounding_profile_paths = load_compiled_grounding_profiles(optimization_target)
    file_grounding_rules = [
        rule
        for rule in grounding_rules
        if rule_matches_file(rule, file_path, file_binding_context.integrations)
    ]

    function_names_to_type: Dict[str, List[Dict[str, Any]]] = {}
    call_detector_rows: List[Dict[str, Any]] = []
    known_call_attrs: Set[str] = set()
    for detector in profile.marker_detectors:
        marker_type = str(detector.get("type", "")).strip().upper()
        if not marker_type:
            continue
        match = detector.get("match", {})
        strength = detector.get("strength", MarkerStrength.MEDIUM.value)
        phase = detector.get("phase", Phase.RUNTIME.value)
        module_hints = [str(item).lower() for item in match.get("module_hints", []) if str(item).strip()]
        call_attrs = {str(attr).strip().lower() for attr in match.get("call_attrs", []) if str(attr).strip()}

        for fn_name in match.get("function_names", []):
            key = str(fn_name).strip()
            if not key:
                continue
            function_names_to_type.setdefault(key, []).append(
                {
                    "marker_type": marker_type,
                    "strength": strength,
                    "phase": phase,
                    "evidence": [detector["id"]],
                    "module_hints": module_hints,
                }
            )
        if call_attrs:
            call_detector_rows.append(
                {
                    "marker_type": marker_type,
                    "strength": strength,
                    "phase": phase,
                    "evidence": [detector["id"]],
                    "module_hints": module_hints,
                    "call_attrs": call_attrs,
                }
            )
            known_call_attrs |= call_attrs

    function_marker_types = {
        det["marker_type"]
        for detector_rows in function_names_to_type.values()
        for det in detector_rows
    }
    anchor_ops = _anchor_ops(
        optimization_target,
        allowed_ops={det["marker_type"] for det in call_detector_rows} | function_marker_types,
    )

    module_aliases, symbol_aliases, imported_modules = _collect_import_aliases(tree)
    phase_by_function = _infer_function_phases(tree)
    direct_match_count = 0
    alias_match_count = 0
    dedup_dropped = 0
    protocol_context_downgraded = 0
    module_context_dropped = 0
    grounding_profile_match_count = 0

    for fn in iter_function_nodes(tree):
        fn_aliases = _collect_local_aliases(fn, known_call_attrs, module_aliases, symbol_aliases)
        fn_phase = phase_by_function.get(fn.name, Phase.RUNTIME.value)
        fn_range = (getattr(fn, "lineno", 0), getattr(fn, "end_lineno", getattr(fn, "lineno", 0)))
        fn_col_range = (getattr(fn, "col_offset", 0), getattr(fn, "end_col_offset", getattr(fn, "col_offset", 0)))

        if fn.name in function_names_to_type:
            for det in function_names_to_type[fn.name]:
                strength = det["strength"]
                if det["marker_type"] in anchor_ops:
                    strength = MarkerStrength.STRONG.value
                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type=det["marker_type"],
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=fn_range[0],
                    line_end=fn_range[1],
                    col_start=fn_col_range[0],
                    col_end=fn_col_range[1],
                    node_kind=fn.__class__.__name__,
                    strength=strength,
                    phase=det["phase"] if det["phase"] != Phase.RUNTIME.value else fn_phase,
                    evidence=det["evidence"],
                    primary_action_id=None,
                    secondary_action_ids=[],
                    binding_reason=[],
                    binding_score=0.0,
                )
                if not emitted:
                    dedup_dropped += 1

        for rule in file_grounding_rules:
            if rule.call_patterns:
                continue
            if not rule_matches_function(rule, fn.name):
                continue
            if not rule_context_matches(rule, fn.name, fn_phase, set()):
                continue

            score, evidence = rule_score(
                rule,
                imported_modules=imported_modules,
                fn_name=fn.name,
                call_tokens=set(),
            )
            if score < rule.emit_threshold:
                continue

            inferred_protocols = _marker_protocols(rule.family, file_binding_context.protocols)
            binding = _related_actions(
                rule.family,
                set(),
                action_matchers,
                marker_file_path=file_path,
                marker_integrations=file_binding_context.integrations,
                marker_protocols=inferred_protocols,
                call_tokens=set(),
                function_name=fn.name,
                preferred_action_kinds=set(rule.preferred_action_kinds),
                boost_target_tokens=set(rule.boost_target_tokens),
                preferred_action_ids=set(rule.generalizes_actions or rule.source_unresolved_action_ids),
                allow_generalized_secondary_binding=rule.generalization_scope in {"file_specific", "integration_specific"},
            )
            related_action_ids = [binding.primary_action_id] if binding.primary_action_id else []
            related_action_ids.extend(binding.secondary_action_ids)
            profile_evidence = list(evidence)
            profile_evidence.append(f"grounding_profile_rule:{rule.rule_id}")
            profile_evidence.append("grounding_profile:match=function")
            profile_evidence.append(f"grounding_profile:score:{score:.2f}")
            profile_evidence.extend(f"grounding_profile:runtime_path:{item}" for item in rule.runtime_path_evidence[:4])
            profile_evidence.extend(f"grounding_profile:negative:{item}" for item in rule.negative_evidence[:4])
            profile_evidence.extend(f"grounding_profile:why_not_setup:{item}" for item in rule.why_not_setup[:4])
            profile_evidence.append(f"grounding_profile:reviewer_status:{rule.reviewer_status}")
            if binding.primary_action_id:
                profile_evidence.append("related_actions:" + ",".join(related_action_ids))
                profile_evidence.extend("action_match:" + reason for reason in binding.binding_reason)

            effective_phase = rule.phase if rule.phase != Phase.RUNTIME.value else fn_phase
            if _should_drop_unbound_runtime_marker(
                rule.family,
                effective_phase,
                binding,
                optimization_target is not None,
            ):
                module_context_dropped += 1
                continue

            emitted = _emit(
                markers,
                seen_marker_keys,
                marker_type=rule.family,
                file_path=file_path,
                fn_name=fn.name,
                line_start=fn_range[0],
                line_end=fn_range[1],
                col_start=fn_col_range[0],
                col_end=fn_col_range[1],
                node_kind=fn.__class__.__name__,
                strength=rule.strength,
                phase=effective_phase,
                evidence=profile_evidence,
                primary_action_id=binding.primary_action_id,
                secondary_action_ids=binding.secondary_action_ids,
                binding_reason=binding.binding_reason,
                binding_score=float(binding.binding_score.get("total", score)),
            )
            if not emitted:
                dedup_dropped += 1
                continue
            grounding_profile_match_count += 1
            direct_match_count += 1

        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call_tokens = _call_tokens(node.value, symbol_aliases, module_aliases, fn_aliases)
                if any(_token_matches_attr(token, "dispatcher_connect") or _token_matches_attr(token, "add_listener") or _token_matches_attr(token, "async_track_state_change_event") for token in call_tokens):
                    binding = _related_actions(
                        "SUBSCRIBE",
                        _collect_string_literals(node.value),
                        action_matchers,
                        marker_file_path=file_path,
                        marker_integrations=file_binding_context.integrations,
                        marker_protocols=file_binding_context.protocols,
                        call_tokens=call_tokens,
                        function_name=fn.name,
                    )
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            subscribe_callback_vars.add(target.id)
                            subscribe_callback_related_actions[target.id] = sorted(
                                {
                                    action_id
                                    for action_id in ([binding.primary_action_id] + list(binding.secondary_action_ids))
                                    if str(action_id or "").strip()
                                }
                            )

            if not isinstance(node, ast.Call):
                continue

            call_tokens_raw = _call_tokens(node, symbol_aliases={}, module_aliases={}, local_aliases={})
            call_tokens = _call_tokens(node, symbol_aliases=symbol_aliases, module_aliases=module_aliases, local_aliases=fn_aliases)
            call_literals = _collect_string_literals(node)
            emitted_call_marker_types: Set[str] = set()

            for det in call_detector_rows:
                if _should_skip_protocol_detector(det["marker_type"], call_tokens, fn.name, file_binding_context):
                    continue
                if not _call_matches_detector(call_tokens, det["call_attrs"]):
                    continue
                if str(det["marker_type"]).strip().upper() in {"CLOUD_HTTP_CALL", "CLOUD_OP", "CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP"}:
                    if not _protocol_context_ok(call_tokens, imported_modules, det["marker_type"]):
                        module_context_dropped += 1
                        continue
                module_context_ok = _module_context_ok(det, imported_modules, call_tokens)
                context_missing = not module_context_ok and bool(det.get("module_hints"))
                if context_missing and not _is_protocol_marker(det["marker_type"]):
                    module_context_dropped += 1
                    continue

                matched_raw = _call_matches_detector(call_tokens_raw, det["call_attrs"])
                matched_alias = not matched_raw
                inferred_protocols = set(file_binding_context.protocols)
                if marker_type := str(det["marker_type"]).strip().upper():
                    if marker_type.startswith("BLE_"):
                        inferred_protocols.add("BLE")
                    elif marker_type.startswith("CLOUD_"):
                        inferred_protocols.add("CLOUD")
                    elif marker_type in {"STATE_WRITE", "SUBSCRIBE", "UNSUBSCRIBE", "COORD_REFRESH"}:
                        inferred_protocols.add("HA")

                binding = _related_actions(
                    det["marker_type"],
                    call_literals,
                    action_matchers,
                    marker_file_path=file_path,
                    marker_integrations=file_binding_context.integrations,
                    marker_protocols=inferred_protocols,
                    call_tokens=call_tokens,
                    function_name=fn.name,
                )
                related_action_ids = [binding.primary_action_id] if binding.primary_action_id else []
                related_action_ids.extend(binding.secondary_action_ids)
                anchor_literal_match = _call_matches_anchor(call_literals, anchor_ctx)
                anchor_op_match = det["marker_type"] in anchor_ops and bool(binding.primary_action_id)
                priority_seed = anchor_literal_match or anchor_op_match
                evidence = list(det["evidence"])
                if matched_alias:
                    evidence.append("alias_match:expanded_call_tokens")
                if priority_seed:
                    evidence.append("target_anchor_seed")
                elif det["marker_type"] in anchor_ops:
                    evidence.append("target_anchor_op_hint_only")
                if context_missing:
                    evidence.append("context_missing:module_hints")
                if binding.primary_action_id:
                    evidence.append("related_actions:" + ",".join(related_action_ids))
                    evidence.extend("action_match:" + reason for reason in binding.binding_reason)

                effective_phase = det["phase"] if det["phase"] != Phase.RUNTIME.value else fn_phase
                strength = MarkerStrength.STRONG.value if priority_seed else det["strength"]
                if context_missing:
                    strength = _downgrade_strength(strength)
                    protocol_context_downgraded += 1
                strength = _context_weak_protocol_marker(det["marker_type"], evidence, binding, strength)
                strength = _phase_mismatch_adjusted_protocol_strength(
                    det["marker_type"],
                    effective_phase,
                    binding,
                    evidence,
                    strength,
                )

                if _should_drop_unbound_runtime_marker(
                    det["marker_type"],
                    effective_phase,
                    binding,
                    optimization_target is not None,
                ):
                    module_context_dropped += 1
                    continue

                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type=det["marker_type"],
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=getattr(node, "lineno", fn_range[0]),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                    col_start=getattr(node, "col_offset", 0),
                    col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                    node_kind=node.__class__.__name__,
                    strength=strength,
                    phase=effective_phase,
                    evidence=evidence,
                    primary_action_id=binding.primary_action_id,
                    secondary_action_ids=binding.secondary_action_ids,
                    binding_reason=binding.binding_reason,
                    binding_score=float(binding.binding_score.get("total", 0.0)),
                )
                if not emitted:
                    dedup_dropped += 1
                    continue
                emitted_call_marker_types.add(str(det["marker_type"]).strip().upper())
                if matched_alias:
                    alias_match_count += 1
                else:
                    direct_match_count += 1
                if det["marker_type"] == "SUBSCRIBE":
                    subscribe_markers_by_function.setdefault(fn.name, []).append(
                        (
                            getattr(node, "lineno", fn_range[0]),
                            getattr(node, "col_offset", 0),
                            list(related_action_ids),
                        )
                    )

            for rule in file_grounding_rules:
                if rule.function_patterns and not rule_matches_function(rule, fn.name):
                    continue
                if not rule_matches_call(rule, call_tokens, fn.name):
                    continue
                if not rule_context_matches(rule, fn.name, fn_phase, call_tokens):
                    continue

                score, evidence = rule_score(
                    rule,
                    imported_modules=imported_modules,
                    fn_name=fn.name,
                    call_tokens=call_tokens,
                )
                if score < rule.emit_threshold:
                    continue

                inferred_protocols = _marker_protocols(rule.family, file_binding_context.protocols)
                binding = _related_actions(
                    rule.family,
                    call_literals,
                    action_matchers,
                    marker_file_path=file_path,
                    marker_integrations=file_binding_context.integrations,
                    marker_protocols=inferred_protocols,
                    call_tokens=call_tokens,
                    function_name=fn.name,
                    preferred_action_kinds=set(rule.preferred_action_kinds),
                    boost_target_tokens=set(rule.boost_target_tokens),
                    preferred_action_ids=set(rule.generalizes_actions or rule.source_unresolved_action_ids),
                    allow_generalized_secondary_binding=rule.generalization_scope in {"file_specific", "integration_specific"},
                )
                related_action_ids = [binding.primary_action_id] if binding.primary_action_id else []
                related_action_ids.extend(binding.secondary_action_ids)
                anchor_literal_match = _call_matches_anchor(call_literals, anchor_ctx)
                anchor_op_match = rule.family in anchor_ops and bool(binding.primary_action_id)
                priority_seed = anchor_literal_match or anchor_op_match
                profile_evidence = list(evidence)
                profile_evidence.append(f"grounding_profile_rule:{rule.rule_id}")
                profile_evidence.append("grounding_profile:match=call")
                profile_evidence.append(f"grounding_profile:score:{score:.2f}")
                profile_evidence.extend(f"grounding_profile:runtime_path:{item}" for item in rule.runtime_path_evidence[:4])
                profile_evidence.extend(f"grounding_profile:negative:{item}" for item in rule.negative_evidence[:4])
                profile_evidence.extend(f"grounding_profile:why_not_setup:{item}" for item in rule.why_not_setup[:4])
                profile_evidence.append(f"grounding_profile:reviewer_status:{rule.reviewer_status}")
                if priority_seed:
                    profile_evidence.append("target_anchor_seed")
                elif rule.family in anchor_ops:
                    profile_evidence.append("target_anchor_op_hint_only")
                if binding.primary_action_id:
                    profile_evidence.append("related_actions:" + ",".join(related_action_ids))
                    profile_evidence.extend("action_match:" + reason for reason in binding.binding_reason)

                effective_phase = rule.phase if rule.phase != Phase.RUNTIME.value else fn_phase
                strength = MarkerStrength.STRONG.value if priority_seed else rule.strength
                if _should_drop_unbound_runtime_marker(
                    rule.family,
                    effective_phase,
                    binding,
                    optimization_target is not None,
                ):
                    module_context_dropped += 1
                    continue

                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type=rule.family,
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=getattr(node, "lineno", fn_range[0]),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                    col_start=getattr(node, "col_offset", 0),
                    col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                    node_kind=node.__class__.__name__,
                    strength=strength,
                    phase=effective_phase,
                    evidence=profile_evidence,
                    primary_action_id=binding.primary_action_id,
                    secondary_action_ids=binding.secondary_action_ids,
                    binding_reason=binding.binding_reason,
                    binding_score=float(binding.binding_score.get("total", score)),
                )
                if not emitted:
                    dedup_dropped += 1
                    continue
                emitted_call_marker_types.add(rule.family)
                grounding_profile_match_count += 1
                direct_match_count += 1
                if rule.family == "SUBSCRIBE":
                    subscribe_markers_by_function.setdefault(fn.name, []).append(
                        (
                            getattr(node, "lineno", fn_range[0]),
                            getattr(node, "col_offset", 0),
                            list(related_action_ids),
                        )
                    )

            if (
                _is_ble_device_runtime_call(call_tokens, fn.name, file_binding_context)
                and "BLE_OP" not in emitted_call_marker_types
                and "BLE_GATT_OP" not in emitted_call_marker_types
            ):
                binding = _related_actions(
                    "BLE_OP",
                    call_literals,
                    action_matchers,
                    marker_file_path=file_path,
                    marker_integrations=file_binding_context.integrations,
                    marker_protocols=file_binding_context.protocols | {"BLE"},
                    call_tokens=call_tokens,
                    function_name=fn.name,
                )
                related_action_ids = [binding.primary_action_id] if binding.primary_action_id else []
                related_action_ids.extend(binding.secondary_action_ids)
                evidence = ["heuristic:ble_device_runtime_call"]
                if binding.primary_action_id:
                    evidence.append("related_actions:" + ",".join(related_action_ids))
                    evidence.extend("action_match:" + reason for reason in binding.binding_reason)
                if _should_drop_unbound_runtime_marker(
                    "BLE_OP",
                    fn_phase,
                    binding,
                    optimization_target is not None,
                ):
                    module_context_dropped += 1
                    continue
                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type="BLE_OP",
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=getattr(node, "lineno", fn_range[0]),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                    col_start=getattr(node, "col_offset", 0),
                    col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                    node_kind=node.__class__.__name__,
                    strength=MarkerStrength.STRONG.value if binding.primary_action_id else MarkerStrength.MEDIUM.value,
                    phase=fn_phase,
                    evidence=evidence,
                    primary_action_id=binding.primary_action_id,
                    secondary_action_ids=binding.secondary_action_ids,
                    binding_reason=binding.binding_reason,
                    binding_score=float(binding.binding_score.get("total", 0.0)),
                )
                if not emitted:
                    dedup_dropped += 1
                else:
                    direct_match_count += 1
                    emitted_call_marker_types.add("BLE_OP")

            if (
                _is_cloud_runtime_call(call_tokens, fn.name, imported_modules)
                and "CLOUD_OP" not in emitted_call_marker_types
                and "CLOUD_HTTP_CALL" not in emitted_call_marker_types
            ):
                binding = _related_actions(
                    "CLOUD_OP",
                    call_literals,
                    action_matchers,
                    marker_file_path=file_path,
                    marker_integrations=file_binding_context.integrations,
                    marker_protocols=file_binding_context.protocols | {"CLOUD"},
                    call_tokens=call_tokens,
                    function_name=fn.name,
                )
                related_action_ids = [binding.primary_action_id] if binding.primary_action_id else []
                related_action_ids.extend(binding.secondary_action_ids)
                evidence = ["heuristic:cloud_runtime_call"]
                if binding.primary_action_id:
                    evidence.append("related_actions:" + ",".join(related_action_ids))
                    evidence.extend("action_match:" + reason for reason in binding.binding_reason)
                if _should_drop_unbound_runtime_marker(
                    "CLOUD_OP",
                    fn_phase,
                    binding,
                    optimization_target is not None,
                ):
                    module_context_dropped += 1
                    continue
                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type="CLOUD_OP",
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=getattr(node, "lineno", fn_range[0]),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                    col_start=getattr(node, "col_offset", 0),
                    col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                    node_kind=node.__class__.__name__,
                    strength=MarkerStrength.STRONG.value if binding.primary_action_id else MarkerStrength.MEDIUM.value,
                    phase=fn_phase,
                    evidence=evidence,
                    primary_action_id=binding.primary_action_id,
                    secondary_action_ids=binding.secondary_action_ids,
                    binding_reason=binding.binding_reason,
                    binding_score=float(binding.binding_score.get("total", 0.0)),
                )
                if not emitted:
                    dedup_dropped += 1
                else:
                    direct_match_count += 1
                    emitted_call_marker_types.add("CLOUD_OP")


            if isinstance(node.func, ast.Name) and node.func.id in subscribe_callback_vars:
                related_actions = list(subscribe_callback_related_actions.get(node.func.id, []))
                if not related_actions:
                    related_actions = _nearest_subscribe_related(
                        subscribe_markers_by_function,
                        fn.name,
                        getattr(node, "lineno", fn_range[0]),
                        getattr(node, "col_offset", 0),
                    )
                if not related_actions:
                    binding = _related_actions(
                        "UNSUBSCRIBE",
                        call_literals,
                        action_matchers,
                        marker_file_path=file_path,
                        marker_integrations=file_binding_context.integrations,
                        marker_protocols=file_binding_context.protocols | {"HA"},
                        call_tokens=set(),
                        function_name=fn.name,
                    )
                    related_actions = [binding.primary_action_id] if binding.primary_action_id else []
                    related_actions.extend(binding.secondary_action_ids)

                evidence = ["pattern:unsubscribe_callback"]
                if related_actions:
                    evidence.append("related_actions:" + ",".join(sorted(set(related_actions))))
                emitted = _emit(
                    markers,
                    seen_marker_keys,
                    marker_type="UNSUBSCRIBE",
                    file_path=file_path,
                    fn_name=fn.name,
                    line_start=getattr(node, "lineno", fn_range[0]),
                    line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                    col_start=getattr(node, "col_offset", 0),
                    col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                    node_kind=node.__class__.__name__,
                    strength=MarkerStrength.STRONG.value,
                    phase=Phase.TEARDOWN.value if fn_phase == Phase.TEARDOWN.value else fn_phase,
                    evidence=evidence,
                    primary_action_id=related_actions[0] if related_actions else None,
                    secondary_action_ids=related_actions[1:] if len(related_actions) > 1 else [],
                    binding_reason=["unsubscribe_callback_reuse"] if related_actions else [],
                    binding_score=0.2 if related_actions else 0.0,
                )
                if not emitted:
                    dedup_dropped += 1


            if isinstance(node.func, ast.Subscript):
                key_name = None
                sub = node.func.slice
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    key_name = sub.value
                elif isinstance(sub, ast.Index) and isinstance(sub.value, ast.Constant) and isinstance(sub.value.value, str):
                    key_name = sub.value.value
                if key_name in {"unsub", "unsubscribe"}:
                    related_actions = _nearest_subscribe_related(
                        subscribe_markers_by_function,
                        fn.name,
                        getattr(node, "lineno", fn_range[0]),
                        getattr(node, "col_offset", 0),
                    )
                    if not related_actions:
                        binding = _related_actions(
                            "UNSUBSCRIBE",
                            set(),
                            action_matchers,
                            marker_file_path=file_path,
                            marker_integrations=file_binding_context.integrations,
                            marker_protocols=file_binding_context.protocols | {"HA"},
                            call_tokens=set(),
                            function_name=fn.name,
                        )
                        related_actions = [binding.primary_action_id] if binding.primary_action_id else []
                        related_actions.extend(binding.secondary_action_ids)
                    evidence = ["pattern:unsubscribe_subscript"]
                    if related_actions:
                        evidence.append("related_actions:" + ",".join(sorted(set(related_actions))))
                    emitted = _emit(
                        markers,
                        seen_marker_keys,
                        marker_type="UNSUBSCRIBE",
                        file_path=file_path,
                        fn_name=fn.name,
                        line_start=getattr(node, "lineno", fn_range[0]),
                        line_end=getattr(node, "end_lineno", getattr(node, "lineno", fn_range[0])),
                        col_start=getattr(node, "col_offset", 0),
                        col_end=getattr(node, "end_col_offset", getattr(node, "col_offset", 0)),
                        node_kind=node.__class__.__name__,
                        strength=MarkerStrength.STRONG.value,
                        phase=Phase.TEARDOWN.value if fn_phase == Phase.TEARDOWN.value else fn_phase,
                        evidence=evidence,
                        primary_action_id=related_actions[0] if related_actions else None,
                        secondary_action_ids=related_actions[1:] if len(related_actions) > 1 else [],
                        binding_reason=["unsubscribe_subscript_reuse"] if related_actions else [],
                        binding_score=0.2 if related_actions else 0.0,
                    )
                    if not emitted:
                        dedup_dropped += 1

    markers, profile_suppressed_baseline_count = _apply_profile_driven_suppressor(markers, file_grounding_rules)
    markers.sort(
        key=lambda m: (
            m.file_path,
            m.function_name,
            m.line_start,
            m.line_end,
            _marker_binding_precedence(m),
            m.marker_type,
            m.marker_id,
        )
    )

    index: Dict[str, List[str]] = {}
    for marker in markers:
        index.setdefault(marker.function_name, []).append(marker.marker_id)

    total_matches = direct_match_count + alias_match_count
    helper_phase_count = sum(
        1
        for fn_name, phase in phase_by_function.items()
        if fn_name not in {"async_setup_entry", "async_unload_entry", "async_remove_entry"} and phase != Phase.RUNTIME.value
    )
    related_marker_count = sum(1 for marker in markers if marker.related_action_ids)
    multi_bound_markers = [marker for marker in markers if marker.secondary_action_ids]
    markers_by_action_primary: Dict[str, int] = {}
    markers_by_action_secondary: Dict[str, int] = {}
    for marker in markers:
        if marker.primary_action_id:
            markers_by_action_primary[marker.primary_action_id] = markers_by_action_primary.get(marker.primary_action_id, 0) + 1
        for action_id in marker.secondary_action_ids:
            markers_by_action_secondary[action_id] = markers_by_action_secondary.get(action_id, 0) + 1
    diagnostics = {
        "match_counts": {
            "direct": direct_match_count,
            "alias": alias_match_count,
            "total": total_matches,
        },
        "alias_precision_estimate": 0.9 if alias_match_count else 1.0,
        "dedup_dropped": dedup_dropped,
        "helper_phase_inferred_count": helper_phase_count,
        "related_action_marker_count": related_marker_count,
        "multi_bound_marker_count": len(multi_bound_markers),
        "markers_with_secondary_actions": [marker.marker_id for marker in multi_bound_markers],
        "markers_by_action_primary": dict(sorted(markers_by_action_primary.items())),
        "markers_by_action_secondary": dict(sorted(markers_by_action_secondary.items())),
        "protocol_context_downgraded": protocol_context_downgraded,
        "module_context_dropped": module_context_dropped,
        "grounding_profile_loaded_paths": sorted(set(grounding_profile_paths)),
        "grounding_profile_rule_count": len(grounding_rules),
        "grounding_profile_file_rule_count": len(file_grounding_rules),
        "grounding_profile_match_count": grounding_profile_match_count,
        "grounding_profile_suppressed_baseline_count": profile_suppressed_baseline_count,
    }

    return MarkerSet(markers=markers, index_by_function=index, diagnostics=diagnostics)
