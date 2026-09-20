from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, Iterable, List, Set
from urllib import error, request

from dsl.contracts import Marker, OptimizationTarget, now_utc_iso
from optimizer.ast_utils import iter_function_nodes, parse_python_file


UNRESOLVED_REPORT_SCHEMA_VERSION = "m1_unresolved_grounding_report/v3"
DETECTOR_DRAFT_SCHEMA_VERSION = "m1_detector_draft/v3"
GROUNDING_PROFILE_SCHEMA_VERSION = "m1_grounding_profile/v3"
BUILDER_VERSION = "m1_detector_builder/v3"
PROMPT_VERSION = "m1_detector_builder_prompt/v3"
DEFAULT_LLM_TIMEOUT_S = 120
DEFAULT_LLM_MAX_ATTEMPTS = 0
DEFAULT_LLM_RETRY_BACKOFF_S = 0.75
HEURISTIC_PROMOTION_THRESHOLD = 5
LLM_REFINE_THRESHOLD = 2
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL | re.IGNORECASE)
_PROPERTY_GETTER_NAMES = {
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
_GENERIC_CALL_TOKENS = {
    "all",
    "any",
    "append",
    "bool",
    "coerce",
    "debug",
    "error",
    "float",
    "get",
    "inclusive",
    "insert",
    "int",
    "isinstance",
    "items",
    "join",
    "len",
    "list",
    "lower",
    "next",
    "optional",
    "range",
    "required",
    "schema",
    "set",
    "sorted",
    "split",
    "str",
    "update",
    "values",
    "warning",
}
_SHARED_INFRA_MARKER_TYPES = {
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
_CONTROL_FUNCTION_PREFIXES = (
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
_CONTROL_CALL_PREFIXES = (
    "turn_",
    "async_turn_",
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
_CONTROL_EXACT_TOKENS = {
    "_async_send_commands",
    "_async_send_wrapper_updates",
    "create_vacation",
    "create_vacation_service",
    "delete_vacation",
    "delete_vacation_service",
    "resume_program",
    "resume_program_set_service",
    "schedule_update_ha_state",
    "set_fan_min_on_time",
}
_STRONG_READ_HINT_TOKENS = {
    "async_update",
    "coordinator_refresh",
    "fetch_status",
    "get_last_message",
    "get_remote_sensors",
    "get_state",
    "get_status",
    "get_thermostat",
    "poll_state",
    "read_last_message",
    "read_runtime",
    "read_sensor",
    "read_status",
    "refresh_status",
}
_STATE_WRITE_HINT_TOKENS = (
    "async_write_ha_state",
    "schedule_update_ha_state",
    "write_ha_state",
    "_handle_coordinator_update",
    "handle_coordinator_update",
    "_async_call_update_attrs",
)
_READ_SEMANTIC_SERVICES = {
    "get_state",
    "poll_update",
    "read_last_message",
    "read_runtime",
    "read_sensor",
    "read_status",
    "status",
}
_CONTROL_SEMANTIC_SERVICES = {
    "turn_on",
    "turn_off",
    "set_cover_position",
    "set_fan_mode",
    "set_hvac_mode",
    "set_percentage",
    "set_preset_mode",
    "set_swing_mode",
    "set_temperature",
    "set_volume_level",
    "play_media",
    "media_play",
    "media_pause",
    "media_stop",
    "open_cover",
    "close_cover",
    "stop_cover",
}
_SETUP_CALL_HINTS = {
    "async_add_entities",
    "async_dispatcher_connect",
    "async_get_current_platform",
    "async_on_unload",
    "async_register",
    "async_register_entity_service",
}
_REFRESH_PATH_HINTS = (
    "async_request_refresh",
    "data.update",
    "manager.update",
    "request_refresh",
)
_UPDATE_CALLBACK_NAME_HINTS = (
    "handle_update",
    "coordinator_update",
    "process_device_update",
    "update_callback",
    "status_updated",
    "device_update",
    "on_update",
    "handle_event",
)
_SUPPORTED_CONTEXT_FLAGS = {
    "runtime_path",
    "runtime_update_path",
    "runtime_connect_path",
    "subscription_path",
    "setup_function",
    "teardown_function",
    "dunder_init",
    "entity_property_getter",
    "helper_wrapper",
}
_PROTOTYPE_ROLE_PRIORITY = {
    "runtime_read": 4,
    "runtime_connect": 3,
    "runtime_subscribe": 3,
    "runtime_write": -3,
    "setup": -4,
    "property_getter": -4,
    "helper": -2,
    "teardown": -2,
}
_WRAPPER_LIKE_FUNCTION_TOKENS = (
    "wrap",
    "wrapper",
    "decorator",
    "refresh_after",
    "schema",
    "description",
)
_WRAPPER_LIKE_CALL_TOKENS = {
    "func",
    "wrapped",
    "wrapper",
    "callback",
}
_CALLBACK_READ_HINT_TOKENS = (
    "update_state",
    "message_received",
    "state_message_received",
    "handle_message",
    "process_message",
    "process_event",
    "handle_event",
)


def _semantic_token_variants(token: str) -> List[str]:
    normalized = str(token or "").strip().lower()
    if not normalized:
        return []
    parts = [part for part in re.split(r"[.:]", normalized) if part]
    out: List[str] = []
    for item in (normalized, *parts[-2:], parts[-1] if parts else ""):
        item = str(item or "").strip().lower()
        if item and item not in out:
            out.append(item)
    return out


class DetectorBuilderLLMError(RuntimeError):
    pass


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _source_bindings(optimization_target: OptimizationTarget) -> List[Dict[str, Any]]:
    source_scope = optimization_target.source_scope if isinstance(optimization_target.source_scope, dict) else {}
    rows = source_scope.get("file_bindings", [])
    return [row for row in rows if isinstance(row, dict)]


def _action_catalog_row(action: Dict[str, Any], bindings: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    action_id = str(action.get("action_id", "")).strip()
    action_bindings = _action_bindings(action, bindings)
    bound_files = [str(row.get("file_path", "")).strip() for row in action_bindings if str(row.get("file_path", "")).strip()]
    integrations = sorted({str(row.get("integration", "")).strip().lower() for row in action_bindings if str(row.get("integration", "")).strip()})
    preferred_family = _preferred_family(action)
    return {
        "action_id": action_id,
        "protocol": str(action.get("protocol", "")).strip().upper(),
        "action_type": str(action.get("type", "")).strip().lower(),
        "target_tokens": sorted(
            _normalized_hint_tokens(action.get("target", {}))
            | _normalized_hint_tokens(action.get("exec", {}))
        )[:24],
        "target_identity_tokens": sorted(_normalized_hint_tokens(action.get("target", {})))[:24],
        "marker_hints": [str(item).strip().upper() for item in action.get("marker_hints", []) if str(item).strip()],
        "target_kind": str(action.get("target_kind", "")).strip(),
        "exec_kind": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("kind", "")).strip(),
        "exec_domain": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("domain", "")).strip(),
        "exec_service": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("service", "")).strip(),
        "bound_files": bound_files,
        "integrations": integrations,
        "preferred_runtime_roles": _preferred_runtime_roles(action, preferred_family),
        "forbidden_runtime_roles": _forbidden_runtime_roles(action, preferred_family),
        "runtime_archetypes": _runtime_archetypes_for_action(action, preferred_family),
    }


def _action_index(optimization_target: OptimizationTarget) -> Dict[str, Dict[str, Any]]:
    return {
        str(action.get("action_id", "")).strip(): action
        for action in optimization_target.vdev_actions
        if isinstance(action, dict) and str(action.get("action_id", "")).strip()
    }


def _action_bindings(action: Dict[str, Any], bindings: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    action_id = str(action.get("action_id", "")).strip()
    target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
    target_ids = {
        str(action_id),
        str(target.get("id", "")).strip(),
        str(target.get("endpoint", "")).strip(),
        str(target.get("device_id", "")).strip(),
        str(target.get("entity_id", "")).strip(),
    }
    out: List[Dict[str, Any]] = []
    for row in bindings:
        device_id = str(row.get("device_id", "")).strip()
        if device_id and device_id in target_ids:
            out.append(row)
    return out


def _normalized_hint_tokens(value: Any) -> Set[str]:
    tokens: Set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            tokens |= _normalized_hint_tokens(item)
        return tokens
    if isinstance(value, list):
        for item in value:
            tokens |= _normalized_hint_tokens(item)
        return tokens
    token = str(value or "").strip().lower()
    if not token:
        return tokens
    tokens.add(token)
    tokens |= {part for part in re.split(r"[^a-z0-9_]+", token) if part}
    return tokens


def _call_tokens(tree: ast.AST) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        token = ""
        if isinstance(node.func, ast.Attribute):
            token = node.func.attr
        elif isinstance(node.func, ast.Name):
            token = node.func.id
        token = str(token or "").strip().lower()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _imports(tree: ast.AST) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for row in node.names:
                token = str(row.name or "").strip().lower().split(".")[0]
                if token and token not in seen:
                    seen.add(token)
                    out.append(token)
        elif isinstance(node, ast.ImportFrom):
            token = str(node.module or "").strip().lower().split(".")[0]
            if token and token not in seen:
                seen.add(token)
                out.append(token)
    return out


def _function_names(tree: ast.AST) -> List[str]:
    return sorted({str(fn.name).strip() for fn in iter_function_nodes(tree) if str(fn.name).strip()})


def _call_tokens_for_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    return _call_tokens(fn)


def _decorator_names_for_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for node in getattr(fn, "decorator_list", []):
        token = _attribute_chain(node).strip().lower()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _attribute_chain(node: ast.AST) -> str:
    if isinstance(node, ast.Attribute):
        left = _attribute_chain(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return ""


def _call_chains_for_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        token = _attribute_chain(node.func).strip().lower()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _awaited_call_chains_for_function(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Await):
            continue
        value = getattr(node, "value", None)
        if not isinstance(value, ast.Call):
            continue
        token = _attribute_chain(value.func).strip().lower()
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def _read_source_lines(file_path: str) -> List[str]:
    return Path(file_path).read_text(encoding="utf-8", errors="ignore").splitlines()


def _snippet(file_path: str, line_start: int, line_end: int, *, context_before: int = 1, context_after: int = 2, max_lines: int = 14) -> str:
    lines = _read_source_lines(file_path)
    if not lines:
        return ""
    start = max(1, int(line_start or 1) - context_before)
    end = min(len(lines), int(line_end or line_start or 1) + context_after)
    snippet_lines = lines[start - 1 : end]
    if len(snippet_lines) > max_lines:
        snippet_lines = snippet_lines[:max_lines]
    rendered = []
    for idx, line in enumerate(snippet_lines, start=start):
        rendered.append(f"{idx}: {line}")
    return "\n".join(rendered)


def _function_role_hint(fn_name: str, call_tokens: List[str], decorator_names: List[str]) -> str:
    name = str(fn_name or "").strip().lower()
    token_text = " ".join(call_tokens)
    if name == "__init__":
        return "setup"
    if any(token in {"property", "cached_property"} or token.endswith(".property") for token in decorator_names):
        return "property_getter"
    if name in _PROPERTY_GETTER_NAMES:
        return "property_getter"
    if any(token in name for token in ("setup", "config_entry", "async_setup_entry", "initialize", "initialise")):
        return "setup"
    if any(token in name for token in ("unload", "remove", "teardown", "cleanup")):
        return "teardown"
    if any(_token_is_state_write_like(token) for token in [name, *call_tokens]):
        return "runtime_write"
    if any(_token_is_control_like(token) for token in [name, *call_tokens]):
        return "runtime_write"
    if any(token in f"{name} {token_text}" for token in ("connect", "session", "handshake")):
        return "runtime_connect"
    if any(token in f"{name} {token_text}" for token in ("subscribe", "notify", "listener", "message")):
        return "runtime_subscribe"
    if any(
        token in f"{name} {token_text}"
        for token in ("update", "refresh", "poll", "status", "runtime", "fetch", "read", "get_thermostat", "get_remote_sensors")
    ):
        return "runtime_read"
    if name.startswith("_"):
        return "helper"
    return "helper"


def _fallback_allowed_for_family(action_row: Dict[str, Any], family: str) -> bool:
    return not _action_requires_read_semantics(action_row, family)


def _path_kind_for_role(role_hint: str) -> str:
    normalized = str(role_hint or "").strip().lower()
    mapping = {
        "runtime_read": "read_path",
        "runtime_write": "control_path",
        "runtime_connect": "connect_path",
        "runtime_subscribe": "subscription_path",
        "setup": "setup_path",
        "property_getter": "property_path",
        "helper": "helper_path",
        "teardown": "teardown_path",
    }
    return mapping.get(normalized, "helper_path")


def _path_signals_for_function(
    fn_name: str,
    call_tokens: List[str],
    call_chains: List[str],
    awaited_call_chains: List[str],
    decorator_names: List[str],
) -> List[str]:
    name = str(fn_name or "").strip().lower()
    signals: List[str] = []

    def _push(prefix: str, value: str) -> None:
        token = str(value or "").strip().lower()
        if not token:
            return
        item = f"{prefix}:{token}"
        if item not in signals:
            signals.append(item)

    combined = [name, *call_tokens, *call_chains, *awaited_call_chains]
    if any(token in {"property", "cached_property"} or token.endswith(".property") for token in decorator_names):
        _push("property_function", name)
        if any(token in " ".join(combined) for token in ("_read_wrapper", "read_device_status", ".status", "status(")):
            _push("state_accessor_property", name)
    if any(token in name for token in ("setup", "config_entry", "async_setup_entry")):
        _push("setup_function", name)
    if any(token in name for token in _UPDATE_CALLBACK_NAME_HINTS):
        _push("update_callback_function", name)
    if any(token in name for token in ("connect", "reconnect", "handshake")):
        _push("connect_function", name)
    if any(token in name for token in ("subscribe", "listener", "notify", "message")):
        _push("subscription_function", name)
    if any(_token_is_state_write_like(token) for token in combined):
        _push("state_write_function", name)
    if any(_token_is_control_like(token) for token in combined):
        _push("control_function", name)
    if any(_token_has_strong_read_signal(token) for token in combined):
        _push("read_function", name)

    for chain in call_chains:
        if chain in _SETUP_CALL_HINTS:
            _push("setup_call", chain)
        if any(hint in chain for hint in _REFRESH_PATH_HINTS):
            _push("refresh_call", chain)
        if _token_has_strong_read_signal(chain):
            _push("read_call", chain)
        if _token_is_control_like(chain):
            _push("control_call", chain)
        if _token_is_state_write_like(chain):
            _push("state_write_call", chain)
        if any(token in chain for token in ("_read_wrapper", "read_device_status")) or chain.endswith(".status"):
            _push("state_accessor_call", chain)
        if any(token in chain for token in ("connect", "reconnect", "handshake")):
            _push("connect_call", chain)
        if any(token in chain for token in ("subscribe", "listener", "notify", "message", "track_state")):
            _push("subscription_call", chain)
        if "register" in chain:
            _push("service_registration_call", chain)

    for chain in awaited_call_chains:
        if any(hint in chain for hint in _REFRESH_PATH_HINTS):
            _push("awaited_refresh_call", chain)
        if _token_has_strong_read_signal(chain):
            _push("awaited_read_call", chain)
        if _token_is_control_like(chain):
            _push("awaited_control_call", chain)
        if _token_is_state_write_like(chain):
            _push("awaited_state_write_call", chain)

    return signals


def _function_record(file_path: str, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> Dict[str, Any]:
    call_patterns = _call_tokens_for_function(fn)
    call_chains = _call_chains_for_function(fn)
    awaited_call_chains = _awaited_call_chains_for_function(fn)
    decorator_names = _decorator_names_for_function(fn)
    role_hint = _function_role_hint(fn.name, call_patterns, decorator_names)
    line_start = getattr(fn, "lineno", 0)
    line_end = getattr(fn, "end_lineno", line_start)
    path_signals = _path_signals_for_function(
        str(fn.name).strip(),
        call_patterns,
        call_chains,
        awaited_call_chains,
        decorator_names,
    )
    return {
        "function_name": str(fn.name).strip(),
        "role_hint": role_hint,
        "decorator_names": decorator_names,
        "line_start": line_start,
        "line_end": line_end,
        "call_patterns": call_patterns,
        "call_chains": call_chains,
        "awaited_call_chains": awaited_call_chains,
        "path_signals": path_signals,
        "path_kind": _path_kind_for_role(role_hint),
        "snippet": _snippet(file_path, line_start, line_end),
    }


def _role_signal_score(row: Dict[str, Any]) -> tuple[int, int, int, int]:
    role_hint = str(row.get("role_hint", "")).strip().lower()
    fn_name = str(row.get("function_name", "")).strip().lower()
    signals = [str(item).strip().lower() for item in row.get("path_signals", []) if str(item).strip()]

    def _count(prefix: str) -> int:
        return sum(1 for item in signals if item.startswith(prefix))

    preferred = 0
    if role_hint == "runtime_read":
        preferred = (
            _count("awaited_refresh_call:") * 6
            + _count("awaited_read_call:") * 5
            + _count("refresh_call:") * 4
            + _count("read_call:") * 3
            + _count("read_function:") * 2
            + _count("update_callback_function:") * 4
        )
        if any(token in fn_name for token in ("update", "refresh", "poll", "fetch", "read")):
            preferred += 3
    elif role_hint == "runtime_write":
        preferred = (
            _count("awaited_state_write_call:") * 7
            + _count("state_write_call:") * 6
            + _count("state_write_function:") * 5
            + _count("awaited_control_call:") * 6
            + _count("control_call:") * 4
            + _count("control_function:") * 3
        )
        if any(token in fn_name for token in ("coordinator_update", "write_ha_state", "update_attrs")):
            preferred += 3
    elif role_hint == "runtime_connect":
        preferred = _count("connect_call:") * 4 + _count("connect_function:") * 3
    elif role_hint == "runtime_subscribe":
        preferred = _count("subscription_call:") * 4 + _count("subscription_function:") * 3
    elif role_hint == "setup":
        preferred = _count("setup_call:") * 4 + _count("setup_function:") * 3
    elif role_hint == "property_getter":
        preferred = _count("property_function:") * 4 + _count("state_accessor_property:") * 5 + _count("state_accessor_call:") * 4

    penalty = 0
    if role_hint == "runtime_read":
        penalty += _count("control_call:") * 5 + _count("awaited_control_call:") * 6 + _count("property_function:") * 4
        if fn_name.startswith("_"):
            penalty += 1
    if role_hint == "runtime_write" and fn_name.startswith("_"):
        penalty += 1

    signal_count = len(signals)
    lexical = -len(fn_name)
    return (preferred - penalty, signal_count, lexical, -int(row.get("line_start", 0) or 0))


def _sorted_role_rows(function_records: List[Dict[str, Any]], role_hint: str) -> List[Dict[str, Any]]:
    rows = [row for row in function_records if row.get("role_hint") == role_hint]
    return sorted(rows, key=_role_signal_score, reverse=True)


def _representative_functions(function_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    runtime_read = _sorted_role_rows(function_records, "runtime_read")[:2]
    runtime_connect = _sorted_role_rows(function_records, "runtime_connect")[:1]
    runtime_subscribe = _sorted_role_rows(function_records, "runtime_subscribe")[:1]
    runtime_write = _sorted_role_rows(function_records, "runtime_write")[:16]
    runtime_write_callbacks = [
        row
        for row in _sorted_role_rows(function_records, "runtime_write")
        if any(str(signal).startswith("update_callback_function:") for signal in row.get("path_signals", []))
    ][:1]
    setup = _sorted_role_rows(function_records, "setup")[:1]
    helper = _sorted_role_rows(function_records, "helper")[:1] + _sorted_role_rows(function_records, "property_getter")[:1]
    chosen = runtime_read + runtime_connect + runtime_subscribe + runtime_write + runtime_write_callbacks + setup + helper
    seen: Set[str] = set()
    out: List[Dict[str, Any]] = []
    for row in chosen:
        fn_name = row["function_name"]
        if fn_name in seen:
            continue
        seen.add(fn_name)
        out.append(row)
    return out


def _compact_function_example(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "function_name": row["function_name"],
        "role_hint": row["role_hint"],
        "path_kind": row.get("path_kind", _path_kind_for_role(row["role_hint"])),
        "path_signals": [str(item).strip() for item in row.get("path_signals", []) if str(item).strip()][:8],
        "snippet": row.get("snippet", ""),
    }


def _path_signal_summary(function_records: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for row in function_records:
        for item in row.get("path_signals", []):
            token = str(item).strip()
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
    return out[:24]


def _path_contrast_examples(function_records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    buckets = {
        "read_path_examples": [_compact_function_example(row) for row in function_records if row.get("path_kind") == "read_path"][:2],
        "control_path_examples": [_compact_function_example(row) for row in function_records if row.get("path_kind") == "control_path"][:16],
        "connect_path_examples": [_compact_function_example(row) for row in function_records if row.get("path_kind") == "connect_path"][:1],
        "subscription_path_examples": [_compact_function_example(row) for row in function_records if row.get("path_kind") == "subscription_path"][:1],
        "setup_path_examples": [_compact_function_example(row) for row in function_records if row.get("path_kind") == "setup_path"][:1],
        "property_path_examples": [
            _compact_function_example(row)
            for row in _sorted_role_rows(function_records, "property_getter")
        ][:2],
    }
    return buckets


def _shared_accessor_signals(function_records: List[Dict[str, Any]]) -> List[str]:
    accessor_counts: Dict[str, int] = {}
    special_tokens: List[str] = []
    seen_special: Set[str] = set()
    for row in function_records:
        for signal in row.get("path_signals", []):
            token = str(signal).strip()
            if token.startswith("state_accessor_call:"):
                accessor_counts[token] = accessor_counts.get(token, 0) + 1
        for chain in [
            *[str(item).strip().lower() for item in row.get("call_chains", []) if str(item).strip()],
            *[str(item).strip().lower() for item in row.get("awaited_call_chains", []) if str(item).strip()],
        ]:
            for needle in ("_read_wrapper", "read_device_status", "skip_update"):
                if needle in chain and needle not in seen_special:
                    seen_special.add(needle)
                    special_tokens.append(needle)
    repeated_accessor_signals = sorted(
        signal
        for signal, count in accessor_counts.items()
        if int(count) >= 2
    )
    return [*special_tokens, *repeated_accessor_signals][:12]


def _source_file_summary(file_path: str, integration: str) -> Dict[str, Any]:
    tree = parse_python_file(file_path)
    if tree is None:
        return {
            "file_path": file_path,
            "integration": integration,
            "parse_error": True,
            "imports": [],
            "function_names": [],
            "call_patterns": [],
            "runtime_candidate_functions": [],
            "runtime_read_candidate_functions": [],
            "runtime_write_candidate_functions": [],
            "runtime_connect_candidate_functions": [],
            "runtime_subscribe_candidate_functions": [],
            "setup_candidate_functions": [],
            "helper_candidate_functions": [],
            "shared_accessor_signals": [],
            "path_signal_summary": [],
            "path_contrast_examples": {},
            "representative_functions": [],
        }

    function_records = [_function_record(file_path, fn) for fn in iter_function_nodes(tree)]
    ranked_runtime_read = _sorted_role_rows(function_records, "runtime_read")
    ranked_runtime_write = _sorted_role_rows(function_records, "runtime_write")
    ranked_runtime_connect = _sorted_role_rows(function_records, "runtime_connect")
    ranked_runtime_subscribe = _sorted_role_rows(function_records, "runtime_subscribe")
    ranked_setup = _sorted_role_rows(function_records, "setup")
    ranked_helpers = _sorted_role_rows(function_records, "helper") + _sorted_role_rows(function_records, "property_getter")
    runtime_candidate_functions = [
        row["function_name"]
        for row in [*ranked_runtime_read, *ranked_runtime_write, *ranked_runtime_connect, *ranked_runtime_subscribe]
    ]
    runtime_read_candidate_functions = [row["function_name"] for row in ranked_runtime_read]
    runtime_write_candidate_functions = [row["function_name"] for row in ranked_runtime_write]
    runtime_connect_candidate_functions = [row["function_name"] for row in ranked_runtime_connect]
    runtime_subscribe_candidate_functions = [row["function_name"] for row in ranked_runtime_subscribe]
    setup_candidate_functions = [row["function_name"] for row in ranked_setup]
    helper_candidate_functions = [row["function_name"] for row in ranked_helpers] + [
        row["function_name"] for row in function_records if row["role_hint"] == "teardown"
    ]
    call_patterns = []
    seen_calls: Set[str] = set()
    for row in function_records:
        for token in row["call_patterns"]:
            if token in seen_calls:
                continue
            seen_calls.add(token)
            call_patterns.append(token)

    return {
        "file_path": file_path,
        "integration": integration,
        "parse_error": False,
        "imports": _imports(tree),
        "function_names": _function_names(tree),
        "call_patterns": call_patterns,
        "runtime_candidate_functions": runtime_candidate_functions,
        "runtime_read_candidate_functions": runtime_read_candidate_functions,
        "runtime_write_candidate_functions": runtime_write_candidate_functions,
        "runtime_connect_candidate_functions": runtime_connect_candidate_functions,
        "runtime_subscribe_candidate_functions": runtime_subscribe_candidate_functions,
        "setup_candidate_functions": setup_candidate_functions,
        "helper_candidate_functions": helper_candidate_functions,
        "shared_accessor_signals": _shared_accessor_signals(function_records),
        "path_signal_summary": _path_signal_summary(function_records),
        "path_contrast_examples": _path_contrast_examples(function_records),
        "representative_functions": _representative_functions(function_records),
    }


def _preferred_family(action: Dict[str, Any]) -> str:
    hints = [str(item).strip().upper() for item in action.get("marker_hints", []) if str(item).strip()]
    hint_set = set(hints)
    if "STATE_WRITE" in hint_set:
        return "STATE_WRITE"
    if "CLOUD_STATUS_CALL" in hint_set and _action_requires_read_semantics(action, "CLOUD_STATUS_CALL"):
        return "CLOUD_STATUS_CALL"
    if "LOCAL_API_READ" in hint_set and _action_requires_read_semantics(action, "LOCAL_API_READ"):
        return "LOCAL_API_READ"
    if "MQTT_SUBSCRIBE" in hint_set and _action_requires_read_semantics(action, "MQTT_SUBSCRIBE"):
        return "MQTT_SUBSCRIBE"
    if "POLL_UPDATE" in hint_set and _action_requires_read_semantics(action, "POLL_UPDATE"):
        return "POLL_UPDATE"
    if "CLOUD_OP" in hint_set and _action_prefers_control_semantics(action, "CLOUD_OP"):
        return "CLOUD_OP"
    if "BLE_OP" in hint_set and _action_prefers_control_semantics(action, "BLE_OP"):
        return "BLE_OP"
    precedence = [
        "BLE_CONNECT",
        "BLE_DISCONNECT",
        "BLE_NOTIFY_SUBSCRIBE",
        "SUBSCRIBE",
        "UNSUBSCRIBE",
        "CLOUD_STATUS_CALL",
        "CLOUD_HTTP_CALL",
        "LOCAL_API_READ",
        "MQTT_SUBSCRIBE",
        "POLL_UPDATE",
        "STATE_WRITE",
        "BLE_OP",
        "CLOUD_OP",
    ]
    for family in precedence:
        if family in hints:
            return family
    return hints[0] if hints else "RUNTIME_OP"


def _marker_refs_for_action(action_id: str, markers: Iterable[Marker]) -> List[Marker]:
    out: List[Marker] = []
    for marker in markers:
        refs = {
            str(getattr(marker, "primary_action_id", "") or "").strip(),
            *[
                str(item).strip()
                for item in getattr(marker, "secondary_action_ids", [])
                if str(item).strip()
            ],
            *[
                str(item).strip()
                for item in getattr(marker, "related_action_ids", [])
                if str(item).strip()
            ],
        }
        refs.discard("")
        if action_id in refs:
            out.append(marker)
    return out


def _marker_example(marker: Marker) -> Dict[str, Any]:
    return {
        "marker_id": marker.marker_id,
        "marker_type": marker.marker_type,
        "phase": marker.phase,
        "file_path": marker.file_path,
        "function_name": marker.function_name,
        "line_start": marker.line_start,
        "binding_score": float(getattr(marker, "binding_score", 0.0) or 0.0),
        "primary_action_id": str(getattr(marker, "primary_action_id", "") or "").strip() or None,
        "evidence": [str(item).strip() for item in getattr(marker, "evidence", []) if str(item).strip()][:8],
    }


def _miss_reason_summary(action_markers: List[Marker]) -> List[str]:
    if not action_markers:
        return ["no_runtime_family_detected"]

    reasons: List[str] = []
    runtime_markers = [marker for marker in action_markers if str(marker.phase).strip().upper() == "RUNTIME"]
    marker_types = {str(marker.marker_type).strip().upper() for marker in action_markers if str(marker.marker_type).strip()}
    evidence = {
        str(item).strip()
        for marker in action_markers
        for item in getattr(marker, "evidence", [])
        if str(item).strip()
    }

    if marker_types and marker_types <= {"STATE_WRITE"}:
        reasons.append("only_state_write_detected")
    if not runtime_markers and action_markers:
        reasons.append("setup_only_matches")
    if "context_missing:module_hints" in evidence:
        reasons.append("context_missing_module_hints")
    if any(float(getattr(marker, "binding_score", 0.0) or 0.0) < 0.75 for marker in action_markers):
        reasons.append("binding_score_below_threshold")
    if action_markers and all(
        (
            not str(getattr(marker, "primary_action_id", "") or "").strip()
            and str(getattr(marker, "marker_type", "")).strip().upper() in _SHARED_INFRA_MARKER_TYPES
        )
        for marker in action_markers
    ):
        reasons.append("shared_infra_only_matches")
    if not reasons:
        reasons.append("runtime_family_present_but_binding_failed")
    return reasons


def _weak_marker_examples(action_markers: List[Marker]) -> List[Dict[str, Any]]:
    weak = [
        marker
        for marker in action_markers
        if float(getattr(marker, "binding_score", 0.0) or 0.0) < 0.75
        or "context_missing:module_hints" in getattr(marker, "evidence", [])
        or any(str(item).startswith("phase_mismatch:") for item in getattr(marker, "evidence", []))
    ]
    weak.sort(key=lambda marker: (float(getattr(marker, "binding_score", 0.0) or 0.0), marker.file_path, marker.line_start))
    return [_marker_example(marker) for marker in weak[:4]]


def _binding_fail_markers(action_markers: List[Marker]) -> List[Dict[str, Any]]:
    rows = [
        _marker_example(marker)
        for marker in action_markers
        if not str(getattr(marker, "primary_action_id", "") or "").strip()
        or float(getattr(marker, "binding_score", 0.0) or 0.0) < 0.75
    ]
    return rows[:6]


def _informative_tokens(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        token = str(value or "").strip().lower()
        if not token or token in seen or token in _GENERIC_CALL_TOKENS:
            continue
        if len(token) <= 2:
            continue
        seen.add(token)
        out.append(token)
    return out


def _unique_tokens(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _token_is_control_like(token: str) -> bool:
    variants = _semantic_token_variants(token)
    return any(
        candidate in _CONTROL_EXACT_TOKENS
        or any(candidate.startswith(prefix) for prefix in (*_CONTROL_FUNCTION_PREFIXES, *_CONTROL_CALL_PREFIXES))
        for candidate in variants
    )


def _token_is_state_write_like(token: str) -> bool:
    variants = _semantic_token_variants(token)
    return any(
        candidate in _STATE_WRITE_HINT_TOKENS
        or any(hint in candidate for hint in ("write_ha_state", "coordinator_update", "update_attrs"))
        for candidate in variants
    )


def _token_has_strong_read_signal(token: str) -> bool:
    variants = _semantic_token_variants(token)
    return any(
        candidate in _STRONG_READ_HINT_TOKENS
        or any(candidate.startswith(prefix) for prefix in ("get_", "read_", "fetch_", "poll_", "refresh_"))
        or any(hint in candidate for hint in _CALLBACK_READ_HINT_TOKENS)
        for candidate in variants
    )


def _action_requires_read_semantics(action_row: Dict[str, Any], family: str) -> bool:
    family_n = str(family or "").strip().upper()
    exec_cfg = action_row.get("exec", {}) if isinstance(action_row.get("exec", {}), dict) else {}
    service = str(action_row.get("exec_service", "") or exec_cfg.get("service", "")).strip().lower()
    action_type = str(action_row.get("action_type", "") or action_row.get("type", "")).strip().lower()
    marker_hints = " ".join(str(item).strip().lower() for item in action_row.get("marker_hints", []) if str(item).strip())
    if family_n in {"LOCAL_API_READ", "POLL_UPDATE"}:
        return True
    if family_n == "CLOUD_STATUS_CALL":
        return True
    text = f"{service} {action_type} {marker_hints}"
    if service.startswith("refresh_") or action_type.startswith("refresh_"):
        return True
    return any(token in text for token in _READ_SEMANTIC_SERVICES)


def _action_prefers_control_semantics(action_row: Dict[str, Any], family: str) -> bool:
    family_n = str(family or "").strip().upper()
    if family_n == "STATE_WRITE":
        return False
    if _action_requires_read_semantics(action_row, family_n):
        return False
    exec_cfg = action_row.get("exec", {}) if isinstance(action_row.get("exec", {}), dict) else {}
    service = str(action_row.get("exec_service", "") or exec_cfg.get("service", "")).strip().lower()
    action_type = str(action_row.get("action_type", "") or action_row.get("type", "")).strip().lower()
    marker_hints = {
        str(item).strip().upper()
        for item in action_row.get("marker_hints", [])
        if str(item).strip()
    }
    if family_n in {"CLOUD_OP", "BLE_OP"}:
        return True
    if marker_hints & {"CLOUD_OP", "BLE_OP"} and any(
        _token_is_control_like(token) for token in (service, action_type)
    ):
        return True
    combined = f"{service} {action_type}"
    return any(token in combined for token in _CONTROL_SEMANTIC_SERVICES)


def _preferred_runtime_roles(action_row: Dict[str, Any], family: str) -> List[str]:
    family_n = str(family or "").strip().upper()
    if _action_requires_read_semantics(action_row, family_n):
        if family_n in {"SUBSCRIBE", "MQTT_SUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE"}:
            return ["runtime_read", "runtime_subscribe"]
        return ["runtime_read"]
    if family_n == "BLE_CONNECT":
        return ["runtime_connect"]
    if family_n in {"SUBSCRIBE", "UNSUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE", "MQTT_SUBSCRIBE"}:
        return ["runtime_subscribe"]
    if family_n == "STATE_WRITE":
        return ["runtime_write"]
    if _action_prefers_control_semantics(action_row, family_n):
        return ["runtime_write"]
    return ["runtime_read", "runtime_connect", "runtime_subscribe"]


def _forbidden_runtime_roles(action_row: Dict[str, Any], family: str) -> List[str]:
    family_n = str(family or "").strip().upper()
    if _action_requires_read_semantics(action_row, family_n):
        return ["runtime_write", "setup", "property_getter", "helper"]
    if family_n == "BLE_CONNECT":
        return ["runtime_write", "setup", "property_getter"]
    if family_n in {"SUBSCRIBE", "UNSUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE", "MQTT_SUBSCRIBE"}:
        return ["runtime_write", "setup", "property_getter"]
    if family_n == "STATE_WRITE":
        return ["setup", "property_getter"]
    if _action_prefers_control_semantics(action_row, family_n):
        return ["setup", "property_getter", "helper"]
    return ["setup", "property_getter"]


def _runtime_archetypes_for_action(action_row: Dict[str, Any], family: str) -> List[str]:
    family_n = str(family or "").strip().upper()
    protocol = str(action_row.get("protocol", "")).strip().upper()
    if family_n == "BLE_CONNECT":
        return ["ble_transport_connect"]
    if family_n in {"SUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE"}:
        if _action_requires_read_semantics(action_row, family_n):
            return ["subscription_listener", "runtime_read"]
        return ["subscription_listener"]
    if family_n == "MQTT_SUBSCRIBE":
        return ["mqtt_message_read", "subscription_listener"]
    if family_n == "LOCAL_API_READ":
        return ["local_bridge_getter", "runtime_read"]
    if family_n in {"CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "POLL_UPDATE"}:
        return ["cloud_runtime_read", "entity_wrapper_read", "coordinator_update_path"]
    if family_n == "STATE_WRITE":
        return ["state_writeback"]
    if family_n == "CLOUD_OP" or (family_n == "CLOUD_HTTP_CALL" and _action_prefers_control_semantics(action_row, family_n)):
        return ["cloud_runtime_control", "entity_control_path"]
    if family_n == "BLE_OP" and _action_prefers_control_semantics(action_row, family_n):
        return ["ble_runtime_control", "device_control_path"]
    if protocol == "BLE":
        return ["ble_runtime_read"]
    return ["runtime_read"]


def _summary_role_function_names(summary: Dict[str, Any], role_hint: str) -> List[str]:
    mapping = {
        "runtime_read": "runtime_read_candidate_functions",
        "runtime_write": "runtime_write_candidate_functions",
        "runtime_connect": "runtime_connect_candidate_functions",
        "runtime_subscribe": "runtime_subscribe_candidate_functions",
        "setup": "setup_candidate_functions",
        "helper": "helper_candidate_functions",
        "property_getter": "helper_candidate_functions",
    }
    key = mapping.get(role_hint, "")
    if not key:
        return []
    return [str(item).strip() for item in summary.get(key, []) if str(item).strip()]


def _contrast_bucket_key_for_role(role_hint: str) -> str:
    normalized = str(role_hint or "").strip().lower()
    mapping = {
        "runtime_read": "read_path_examples",
        "runtime_write": "control_path_examples",
        "runtime_connect": "connect_path_examples",
        "runtime_subscribe": "subscription_path_examples",
        "setup": "setup_path_examples",
    }
    return mapping.get(normalized, "")


def _action_path_contrast_examples(
    bound_files: List[str],
    file_summaries: Dict[str, Dict[str, Any]],
    preferred_roles: List[str],
    forbidden_roles: List[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    preferred_roles_n = {str(item).strip().lower() for item in preferred_roles if str(item).strip()}
    preferred_example_limit = 16 if "runtime_write" in preferred_roles_n else 2
    for file_path in bound_files:
        summary = file_summaries.get(file_path)
        if not summary:
            continue
        contrast = summary.get("path_contrast_examples", {}) if isinstance(summary.get("path_contrast_examples", {}), dict) else {}
        preferred_examples: List[Dict[str, Any]] = []
        forbidden_examples: List[Dict[str, Any]] = []
        for role_hint in preferred_roles:
            bucket_key = _contrast_bucket_key_for_role(role_hint)
            preferred_examples.extend(contrast.get(bucket_key, []) if isinstance(contrast.get(bucket_key, []), list) else [])
        for role_hint in forbidden_roles:
            bucket_key = _contrast_bucket_key_for_role(role_hint)
            forbidden_examples.extend(contrast.get(bucket_key, []) if isinstance(contrast.get(bucket_key, []), list) else [])
        setup_examples = contrast.get("setup_path_examples", []) if isinstance(contrast.get("setup_path_examples", []), list) else []
        supporting_examples = []
        if "runtime_read" in {str(item).strip().lower() for item in preferred_roles}:
            supporting_examples = contrast.get("property_path_examples", []) if isinstance(contrast.get("property_path_examples", []), list) else []
        rows.append(
            {
                "file_path": file_path,
                "preferred_examples": preferred_examples[:preferred_example_limit],
                "forbidden_examples": forbidden_examples[:2],
                "setup_examples": setup_examples[:1],
                "supporting_examples": supporting_examples[:1],
            }
        )
    return rows


def _action_path_signal_focus(
    bound_files: List[str],
    file_summaries: Dict[str, Dict[str, Any]],
    preferred_roles: List[str],
    forbidden_roles: List[str],
) -> Dict[str, List[str]]:
    preferred_signals: List[str] = []
    forbidden_signals: List[str] = []
    seen_preferred: Set[str] = set()
    seen_forbidden: Set[str] = set()
    for row in _action_path_contrast_examples(bound_files, file_summaries, preferred_roles, forbidden_roles):
        for example in row.get("preferred_examples", []):
            for item in example.get("path_signals", []):
                token = str(item).strip()
                if token and token not in seen_preferred:
                    seen_preferred.add(token)
                    preferred_signals.append(token)
        for example in row.get("forbidden_examples", []):
            for item in example.get("path_signals", []):
                token = str(item).strip()
                if token and token not in seen_forbidden:
                    seen_forbidden.add(token)
                    forbidden_signals.append(token)
    return {
        "preferred_signals": preferred_signals[:12],
        "forbidden_signals": forbidden_signals[:12],
    }


def _positive_selector_missing_reason(
    bound_files: List[str],
    file_summaries: Dict[str, Dict[str, Any]],
    preferred_roles: List[str],
) -> str:
    preferred = {str(item).strip().lower() for item in preferred_roles if str(item).strip()}
    if "runtime_write" in preferred:
        runtime_write_candidates = any(
            file_summaries.get(file_path, {}).get("runtime_write_candidate_functions")
            for file_path in bound_files
        )
        control_path_detected = any(
            any(
                str(signal).startswith("control_function:")
                or str(signal).startswith("control_call:")
                or str(signal).startswith("awaited_control_call:")
                for signal in file_summaries.get(file_path, {}).get("path_signal_summary", [])
            )
            for file_path in bound_files
        )
        if runtime_write_candidates or control_path_detected:
            return ""
        return "no_runtime_write_or_control_handler_detected"
    if "runtime_read" not in preferred:
        return ""
    runtime_read_candidates = any(
        file_summaries.get(file_path, {}).get("runtime_read_candidate_functions")
        for file_path in bound_files
    )
    update_callback_detected = any(
        any(
            str(signal).startswith("update_callback_function:")
            for signal in file_summaries.get(file_path, {}).get("path_signal_summary", [])
        )
        for file_path in bound_files
    )
    if runtime_read_candidates or update_callback_detected:
        return ""
    return "no_runtime_read_or_update_callback_detected"


def _cluster_action_kind(action_row: Dict[str, Any]) -> str:
    action_type = str(action_row.get("action_type", "")).strip().lower()
    exec_service = str(action_row.get("exec_service", "")).strip().lower()
    return action_type or exec_service or "runtime_op"


def _cluster_key(action_row: Dict[str, Any]) -> tuple[str, tuple[str, ...], str, str, str]:
    integration = str((action_row.get("integrations") or ["unknown"])[0]).strip().lower() or "unknown"
    bound_files = tuple(sorted(str(item).strip() for item in action_row.get("bound_files", []) if str(item).strip()))
    family = _preferred_family(action_row)
    action_kind = _cluster_action_kind(action_row)
    protocol = str(action_row.get("protocol", "")).strip().upper()
    return (integration, bound_files, family, action_kind, protocol)


def _cluster_id(
    integration: str,
    bound_files: Iterable[str],
    family: str,
    action_kind: str,
    protocol: str,
) -> str:
    stems = [Path(file_path).stem.strip().lower() for file_path in bound_files if str(file_path).strip()]
    scope = "_".join(dict.fromkeys(stems)) if stems else "unknown_file"
    token = "__".join(
        [
            integration or "unknown",
            scope or "unknown_file",
            str(family or "").strip().lower(),
            str(action_kind or "").strip().lower(),
            str(protocol or "").strip().lower(),
        ]
    )
    return re.sub(r"[^a-z0-9_]+", "_", token).strip("_")


def _merge_unique_lists(values: Iterable[Iterable[str]]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for rows in values:
        for item in rows:
            token = str(item).strip()
            if not token or token in seen:
                continue
            seen.add(token)
            out.append(token)
    return out


def _prototype_signal_score(row: Dict[str, Any], preferred_roles: Set[str], forbidden_roles: Set[str]) -> int:
    role_hint = str(row.get("role_hint", "")).strip().lower()
    fn_name = str(row.get("function_name", "")).strip().lower()
    path_signals = [str(item).strip().lower() for item in row.get("path_signals", []) if str(item).strip()]
    call_patterns = [str(item).strip().lower() for item in row.get("call_patterns", []) if str(item).strip()]
    call_chains = [str(item).strip().lower() for item in row.get("call_chains", []) if str(item).strip()]
    score = 0
    score += _PROTOTYPE_ROLE_PRIORITY.get(role_hint, 0)
    if role_hint in preferred_roles:
        score += 2
    if role_hint == "runtime_write" and "runtime_write" in preferred_roles:
        score += 4
    if role_hint in forbidden_roles:
        score -= 2
    if any(item.startswith("read_function:") for item in path_signals):
        score += 2
    if any(item.startswith("refresh_call:") or item.startswith("update_callback_function:") for item in path_signals):
        score += 2
    if any(item.startswith("awaited_refresh_call:") for item in path_signals):
        score += 2
    if any(item.startswith("connect_call:") or item.startswith("connect_function:") for item in path_signals):
        score += 2
    if any(item.startswith("subscription_call:") or item.startswith("subscription_function:") for item in path_signals):
        score += 2
    if any(
        item.startswith("state_write_function:")
        or item.startswith("state_write_call:")
        or item.startswith("awaited_state_write_call:")
        for item in path_signals
    ):
        score += 4
    if any(item.startswith("control_function:") for item in path_signals):
        if "runtime_write" in preferred_roles:
            score += 4
        else:
            score -= 3
    if any(item.startswith("control_call:") or item.startswith("awaited_control_call:") for item in path_signals):
        if "runtime_write" in preferred_roles:
            score += 4
        elif "runtime_read" in preferred_roles:
            score -= 4
    if any(item.startswith("setup_function:") for item in path_signals):
        score -= 4
    if any(item.startswith("property_function:") or item.startswith("state_accessor_property:") for item in path_signals):
        score -= 4
    if "runtime_read" in preferred_roles:
        registry_or_migration_calls = {
            "async_entries_for_device",
            "async_get",
            "async_get_device",
            "async_get_entity_id",
            "async_update_entity",
        }
        if fn_name == "async_migrate" or any(token in registry_or_migration_calls for token in call_patterns):
            score -= 10
        media_control_names = {
            "async_get_browse_image",
            "async_media_next_track",
            "async_media_pause",
            "async_media_play",
            "async_media_play_pause",
            "async_media_previous_track",
            "async_mute_volume",
            "async_play_media",
            "async_select_source",
        }
        if fn_name in media_control_names:
            score -= 8
        elif fn_name.startswith("async_media_"):
            score -= 6
    update_snapshot_read = (
        "runtime_read" in preferred_roles
        and any(item.startswith("update_callback_function:") for item in path_signals)
        and any(
            item.startswith("state_write_function:")
            or item.startswith("state_write_call:")
            or item.startswith("awaited_state_write_call:")
            for item in path_signals
        )
        and not any(
            item.startswith("control_function:")
            or item.startswith("control_call:")
            or item.startswith("awaited_control_call:")
            for item in path_signals
        )
    )
    if update_snapshot_read:
        score += 8
        if role_hint == "runtime_write":
            score += 5
    wrapper_like = (
        "runtime_read" in preferred_roles
        and any(token in fn_name for token in _WRAPPER_LIKE_FUNCTION_TOKENS)
        and any(token in _WRAPPER_LIKE_CALL_TOKENS for token in call_patterns)
        and not update_snapshot_read
    )
    if wrapper_like:
        score -= 6
    if (
        "runtime_read" in preferred_roles
        and not path_signals
        and (fn_name.startswith("_get_") or "description" in fn_name)
        and not any(chain.startswith("self.") or chain.startswith("coordinator.") for chain in call_chains)
    ):
        score -= 4
    return score


def _control_selector_tokens(cluster: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    action_kind = str(cluster.get("action_kind", "")).strip().lower()
    if action_kind:
        values.append(action_kind)
    for row in cluster.get("rows", []):
        if not isinstance(row, dict):
            continue
        values.extend(
            [
                str(row.get("action_type", "")).strip().lower(),
                str(row.get("exec_service", "")).strip().lower(),
            ]
        )
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        for token in _semantic_token_variants(value):
            token_n = str(token).strip().lower()
            if not token_n or token_n in seen or token_n in _GENERIC_CALL_TOKENS or len(token_n) <= 2:
                continue
            seen.add(token_n)
            out.append(token_n)
    return out


def _required_service_tokens(cluster: Dict[str, Any]) -> List[str]:
    preferred_roles = {
        str(item).strip().lower()
        for item in cluster.get("preferred_runtime_roles", [])
        if str(item).strip()
    }
    family = str(cluster.get("family", "")).strip().upper()
    if "runtime_write" not in preferred_roles or family not in {"CLOUD_OP", "BLE_OP"}:
        return []
    return _control_selector_tokens(cluster)[:4]


def _selector_alignment_strength(token: str, selector: str) -> int:
    token_n = str(token or "").strip().lower()
    selector_n = str(selector or "").strip().lower()
    if not token_n or not selector_n:
        return 0
    if token_n == selector_n:
        return 4
    if token_n.endswith(f"_{selector_n}") or selector_n.endswith(f"_{token_n}"):
        return 3
    if selector_n in token_n or token_n in selector_n:
        return 2
    return 0


def _control_selector_alignment_score(row: Dict[str, Any], selector_tokens: Sequence[str]) -> int:
    if not selector_tokens:
        return 0
    function_name = str(row.get("function_name", "")).strip().lower()
    call_patterns = [str(item).strip().lower() for item in row.get("call_patterns", []) if str(item).strip()]
    call_chains = [str(item).strip().lower() for item in row.get("call_chains", []) if str(item).strip()]
    score = 0
    for selector in selector_tokens:
        score = max(score, 3 * _selector_alignment_strength(function_name, selector))
        for token in [*call_patterns, *call_chains]:
            score = max(score, 2 * _selector_alignment_strength(token, selector))
    if score == 0 and function_name.endswith("_service"):
        score -= 4
    return score


def _filter_control_aligned_selectors(
    cluster: Dict[str, Any],
    positive_function_patterns: List[str],
    positive_call_patterns: List[str],
) -> tuple[List[str], List[str], List[str], List[str]]:
    preferred_roles = {
        str(item).strip().lower()
        for item in cluster.get("preferred_runtime_roles", [])
        if str(item).strip()
    }
    family = str(cluster.get("family", "")).strip().upper()
    if "runtime_write" not in preferred_roles or family not in {"CLOUD_OP", "BLE_OP"}:
        return positive_function_patterns, positive_call_patterns, [], []

    selector_tokens = _control_selector_tokens(cluster)
    if not selector_tokens:
        return positive_function_patterns, positive_call_patterns, [], []

    aligned_functions = [
        token
        for token in positive_function_patterns
        if any(_selector_alignment_strength(token, selector) > 0 for selector in selector_tokens)
    ]
    aligned_calls = [
        token
        for token in positive_call_patterns
        if any(_selector_alignment_strength(token, selector) > 0 for selector in selector_tokens)
    ]
    if not aligned_functions and not aligned_calls:
        return positive_function_patterns, positive_call_patterns, [], []

    removed_functions = [token for token in positive_function_patterns if token not in aligned_functions]
    removed_calls = [token for token in positive_call_patterns if token not in aligned_calls]
    return aligned_functions or positive_function_patterns, aligned_calls or positive_call_patterns, removed_functions, removed_calls


def _cluster_examples(
    cluster: Dict[str, Any],
    file_summaries: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    examples: List[Dict[str, Any]] = []
    seen: Set[tuple[str, str]] = set()
    for file_path in cluster["bound_files"]:
        summary = file_summaries.get(file_path)
        if not summary:
            continue
        rows: List[Dict[str, Any]] = []
        rows.extend(summary.get("representative_functions", []) if isinstance(summary.get("representative_functions", []), list) else [])
        contrast = summary.get("path_contrast_examples", {}) if isinstance(summary.get("path_contrast_examples", {}), dict) else {}
        for bucket in contrast.values():
            if isinstance(bucket, list):
                rows.extend(bucket)
        for row in rows:
            if not isinstance(row, dict):
                continue
            function_name = str(row.get("function_name", "")).strip()
            if not function_name:
                continue
            key = (file_path, function_name)
            if key in seen:
                continue
            seen.add(key)
            merged = dict(row)
            merged["file_path"] = file_path
            merged["prototype_score"] = _prototype_signal_score(
                merged,
                set(cluster["preferred_runtime_roles"]),
                set(cluster["forbidden_runtime_roles"]),
            )
            examples.append(merged)
    return examples


def _prototype_bucket(row: Dict[str, Any], preferred_roles: Set[str]) -> str:
    role_hint = str(row.get("role_hint", "")).strip().lower()
    path_signals = [str(item).strip().lower() for item in row.get("path_signals", []) if str(item).strip()]
    if (
        "runtime_read" in preferred_roles
        and any(item.startswith("update_callback_function:") for item in path_signals)
        and any(item.startswith("state_write_function:") or item.startswith("state_write_call:") for item in path_signals)
        and not any(
            item.startswith("control_function:")
            or item.startswith("control_call:")
            or item.startswith("awaited_control_call:")
            for item in path_signals
        )
    ):
        return "positive"
    if role_hint in preferred_roles:
        return "positive"
    if role_hint == "runtime_write":
        return "negative_control"
    if role_hint == "setup":
        return "negative_setup"
    if role_hint in {"property_getter", "helper", "runtime_read", "runtime_connect", "runtime_subscribe"}:
        return "negative_helper"
    return "negative_helper"


def _compact_prototype(row: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    return {
        "prototype_kind": kind,
        "file_path": str(row.get("file_path", "")).strip(),
        "function_name": str(row.get("function_name", "")).strip(),
        "role_hint": str(row.get("role_hint", "")).strip().lower(),
        "path_kind": str(row.get("path_kind", "")).strip().lower(),
        "path_signals": [str(item).strip() for item in row.get("path_signals", []) if str(item).strip()][:10],
        "call_patterns": [str(item).strip() for item in row.get("call_patterns", []) if str(item).strip()][:8],
        "call_chains": [str(item).strip() for item in row.get("call_chains", []) if str(item).strip()][:8],
        "score": int(row.get("prototype_score", 0) or 0),
        "snippet": str(row.get("snippet", "")).strip(),
    }


def _prototype_path_constraints(
    positive_prototypes: List[Dict[str, Any]],
    negative_prototypes: List[Dict[str, Any]],
) -> tuple[List[str], List[str]]:
    required_path_signals = _merge_unique_lists(
        [
            [
                signal
                for signal in proto.get("path_signals", [])
                if any(
                    signal.startswith(prefix)
                    for prefix in (
                        "read_function:",
                        "read_call:",
                        "awaited_read_call:",
                        "refresh_call:",
                        "awaited_refresh_call:",
                        "update_callback_function:",
                        "connect_function:",
                        "connect_call:",
                        "subscription_function:",
                        "subscription_call:",
                        "state_accessor_call:",
                        "state_accessor_property:",
                        "property_function:",
                        "control_function:",
                        "control_call:",
                        "awaited_control_call:",
                        "state_write_function:",
                        "state_write_call:",
                        "awaited_state_write_call:",
                    )
                )
            ]
            for proto in positive_prototypes
        ]
    )[:8]
    forbidden_path_signals = _merge_unique_lists(
        [
            [
                signal
                for signal in proto.get("path_signals", [])
                if any(
                    signal.startswith(prefix)
                    for prefix in (
                        "control_function:",
                        "control_call:",
                        "awaited_control_call:",
                        "setup_function:",
                        "setup_call:",
                        "property_function:",
                        "state_accessor_property:",
                    )
                )
            ]
            for proto in negative_prototypes
        ]
    )[:8]
    return required_path_signals, forbidden_path_signals


def _synthesize_cluster_prototypes(
    cluster: Dict[str, Any],
    file_summaries: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    examples = _cluster_examples(cluster, file_summaries)
    preferred_roles = {
        str(item).strip().lower()
        for item in cluster.get("preferred_runtime_roles", [])
        if str(item).strip()
    }
    positive_rows = [
        row
        for row in examples
        if _prototype_bucket(row, preferred_roles) == "positive"
        and int(row.get("prototype_score", 0) or 0) > 0
    ]
    control_selector_tokens = _control_selector_tokens(cluster)
    if control_selector_tokens and "runtime_write" in preferred_roles:
        aligned_rows = [
            row
            for row in positive_rows
            if _control_selector_alignment_score(row, control_selector_tokens) > 0
        ]
        if aligned_rows:
            positive_rows = aligned_rows
    positives = sorted(
        positive_rows,
        key=lambda row: (
            _control_selector_alignment_score(row, control_selector_tokens),
            int(row.get("prototype_score", 0) or 0),
            len(row.get("path_signals", [])),
            -int(row.get("line_start", 0) or 0),
        ),
        reverse=True,
    )[:3]
    negative_setup = sorted(
        [row for row in examples if _prototype_bucket(row, preferred_roles) == "negative_setup"],
        key=lambda row: int(row.get("prototype_score", 0) or 0),
    )[:1]
    negative_control = sorted(
        [row for row in examples if _prototype_bucket(row, preferred_roles) == "negative_control"],
        key=lambda row: int(row.get("prototype_score", 0) or 0),
    )[:2]
    negative_helper = sorted(
        [row for row in examples if _prototype_bucket(row, preferred_roles) == "negative_helper"],
        key=lambda row: int(row.get("prototype_score", 0) or 0),
    )[:2]

    positive_prototypes = [_compact_prototype(row, kind="positive") for row in positives]
    negative_prototypes = [
        *[_compact_prototype(row, kind="negative_setup") for row in negative_setup],
        *[_compact_prototype(row, kind="negative_control") for row in negative_control],
        *[_compact_prototype(row, kind="negative_helper") for row in negative_helper],
    ]

    required_path_signals, forbidden_path_signals = _prototype_path_constraints(
        positive_prototypes,
        negative_prototypes,
    )
    return {
        "positive_prototypes": positive_prototypes,
        "negative_prototypes": negative_prototypes,
        "required_path_signals": required_path_signals,
        "forbidden_path_signals": forbidden_path_signals,
    }


def _candidate_generalization_scope(cluster: Dict[str, Any], prototypes: Dict[str, Any]) -> tuple[str, str]:
    action_ids = cluster["action_ids"]
    bound_files = cluster["bound_files"]
    positive = prototypes.get("positive_prototypes", [])
    positive_names = {
        str(item.get("function_name", "")).strip()
        for item in positive
        if str(item.get("function_name", "")).strip()
    }
    if not positive:
        return "action_specific", "prototype evidence is too weak to generalize safely"
    if len(bound_files) == 1:
        if len(action_ids) <= 1:
            return "file_specific", "single unresolved action still exposes a reusable file-local runtime idiom"
        return "file_specific", "same runtime idiom appears in one file across multiple unresolved actions"
    if len(positive_names) == 1 and positive_names:
        return "integration_specific", "multiple files share the same primary runtime function idiom"
    if len(action_ids) <= 1:
        return "file_specific", "single unresolved action has reusable file-scoped prototypes but not integration-wide evidence"
    return "file_specific", "runtime idioms differ across files, so keep the rule at file scope"


def _filter_wrapper_like_positive_selectors(
    positive_function_patterns: List[str],
    positive_call_patterns: List[str],
    positive_prototypes: List[Dict[str, Any]],
    preferred_roles: List[str],
) -> tuple[List[str], List[str], List[str], List[str]]:
    preferred_roles_n = {str(item).strip().lower() for item in preferred_roles if str(item).strip()}
    if "runtime_read" not in preferred_roles_n:
        return positive_function_patterns, positive_call_patterns, [], []
    has_strong_snapshot_carrier = any(
        str(proto.get("prototype_kind", "")).strip().lower() in {"synthetic_update_snapshot_positive", "synthetic_accessor_positive"}
        or str(proto.get("role_hint", "")).strip().lower() == "runtime_read_snapshot"
        or any(
            str(signal).strip().lower().startswith("update_callback_function:")
            for signal in proto.get("path_signals", [])
            if str(signal).strip()
        )
        for proto in positive_prototypes
        if isinstance(proto, dict)
    )
    if not has_strong_snapshot_carrier:
        return positive_function_patterns, positive_call_patterns, [], []

    removed_functions = [
        token
        for token in positive_function_patterns
        if any(marker in str(token).strip().lower() for marker in _WRAPPER_LIKE_FUNCTION_TOKENS)
    ]
    removed_calls = [
        token
        for token in positive_call_patterns
        if any(marker in str(token).strip().lower() for marker in _WRAPPER_LIKE_CALL_TOKENS)
    ]
    filtered_functions = [token for token in positive_function_patterns if token not in removed_functions]
    filtered_calls = [token for token in positive_call_patterns if token not in removed_calls]
    return filtered_functions, filtered_calls, removed_functions, removed_calls


def _positive_private_update_carrier_selected(positive_prototypes: List[Dict[str, Any]], preferred_roles: List[str]) -> bool:
    preferred_roles_n = {str(item).strip().lower() for item in preferred_roles if str(item).strip()}
    if "runtime_read" not in preferred_roles_n:
        return False
    for proto in positive_prototypes:
        if not isinstance(proto, dict):
            continue
        function_name = str(proto.get("function_name", "")).strip().lower()
        if function_name in {"_async_update_data", "_async_update", "_async_update_status"}:
            return True
        if function_name.startswith("_async_update_"):
            return True
    return False


def _should_try_update_snapshot_fallback(
    cluster: Dict[str, Any],
    summary: Dict[str, Any],
) -> bool:
    preferred_roles = {
        str(item).strip().lower()
        for item in cluster.get("preferred_runtime_roles", [])
        if str(item).strip()
    }
    if "runtime_read" not in preferred_roles:
        return False
    if summary.get("runtime_read_candidate_functions"):
        return False
    representative_functions = summary.get("representative_functions", []) if isinstance(summary.get("representative_functions", []), list) else []
    for row in representative_functions:
        if not isinstance(row, dict):
            continue
        path_signals = [str(item).strip().lower() for item in row.get("path_signals", []) if str(item).strip()]
        if not any(item.startswith("update_callback_function:") for item in path_signals):
            continue
        if not any(item.startswith("state_write_function:") or item.startswith("state_write_call:") for item in path_signals):
            continue
        if any(
            item.startswith("control_function:")
            or item.startswith("control_call:")
            or item.startswith("awaited_control_call:")
            for item in path_signals
        ):
            continue
        return True
    return False


def fallback_positive_synthesis(
    cluster: Dict[str, Any],
    file_summaries: Dict[str, Dict[str, Any]],
    negative_prototypes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    family = str(cluster.get("family", "")).strip().upper()
    action_kind = str(cluster.get("action_kind", "")).strip().lower()
    is_accessor_read = (
        (family == "CLOUD_STATUS_CALL" and action_kind == "status")
        or (family == "LOCAL_API_READ" and action_kind == "get_state")
    )
    if negative_prototypes == []:
        return []
    is_refresh_snapshot = family == "BLE_OP" and action_kind.startswith("refresh_")
    update_snapshot_read = False
    if not (is_accessor_read or is_refresh_snapshot):
        for file_path in cluster.get("bound_files", []):
            summary = file_summaries.get(str(file_path).strip(), {})
            if summary and _should_try_update_snapshot_fallback(cluster, summary):
                update_snapshot_read = True
                break
    if not (is_accessor_read or is_refresh_snapshot or update_snapshot_read):
        return []
    for file_path in cluster.get("bound_files", []):
        summary = file_summaries.get(str(file_path).strip(), {})
        if not summary:
            continue
        if summary.get("runtime_read_candidate_functions"):
            continue
        if is_accessor_read and any(
            str(signal).startswith("update_callback_function:")
            for signal in summary.get("path_signal_summary", [])
        ):
            continue
        contrast = summary.get("path_contrast_examples", {}) if isinstance(summary.get("path_contrast_examples", {}), dict) else {}
        property_examples = contrast.get("property_path_examples", []) if isinstance(contrast.get("property_path_examples", []), list) else []
        repeated_accessor_signals = [
            str(item).strip()
            for item in summary.get("shared_accessor_signals", [])
            if str(item).strip().startswith("state_accessor_call:")
        ]
        if is_accessor_read and property_examples:
            lead_example = property_examples[0] if isinstance(property_examples[0], dict) else {}
            call_chains = [signal.split(":", 1)[1] for signal in repeated_accessor_signals if ":" in signal]
            call_patterns = _informative_tokens(chain.rsplit(".", 1)[-1] for chain in call_chains if str(chain).strip())
            path_signals = _unique_tokens(
                [
                    *[str(item).strip() for item in lead_example.get("path_signals", []) if str(item).strip()],
                    *repeated_accessor_signals,
                    *[
                        str(item).strip()
                        for item in summary.get("shared_accessor_signals", [])
                        if str(item).strip() and not str(item).strip().startswith("state_accessor_call:")
                    ],
                ]
            )[:10]
            function_name = str(lead_example.get("function_name", "")).strip()
            if function_name:
                return [
                    {
                        "prototype_kind": "synthetic_accessor_positive",
                        "file_path": str(file_path).strip(),
                        "function_name": function_name,
                        "role_hint": "runtime_read_snapshot",
                        "path_kind": "read_path",
                        "path_signals": path_signals,
                        "call_patterns": call_patterns[:6],
                        "call_chains": call_chains[:6],
                        "score": 3,
                        "snippet": str(lead_example.get("snippet", "")).strip(),
                    }
                ]
        representative_functions = summary.get("representative_functions", []) if isinstance(summary.get("representative_functions", []), list) else []
        callback_candidates = []
        for row in representative_functions:
            if not isinstance(row, dict):
                continue
            path_signals = [str(item).strip() for item in row.get("path_signals", []) if str(item).strip()]
            path_signals_n = [str(item).strip().lower() for item in row.get("path_signals", []) if str(item).strip()]
            if not any(item.startswith("update_callback_function:") for item in path_signals_n):
                continue
            if not any(item.startswith("state_write_function:") or item.startswith("state_write_call:") for item in path_signals_n):
                continue
            if any(
                item.startswith("control_function:")
                or item.startswith("control_call:")
                or item.startswith("awaited_control_call:")
                for item in path_signals_n
            ):
                continue
            callback_candidates.append(row)
        if not callback_candidates:
            continue
        lead = callback_candidates[0]
        return [
            {
                "prototype_kind": "synthetic_update_snapshot_positive",
                "file_path": str(file_path).strip(),
                "function_name": str(lead.get("function_name", "")).strip(),
                "role_hint": "runtime_read_snapshot",
                "path_kind": "read_path",
                "path_signals": [str(item).strip() for item in lead.get("path_signals", []) if str(item).strip()][:10],
                "call_patterns": [],
                "call_chains": [],
                "score": 4,
                "snippet": str(lead.get("snippet", "")).strip(),
            }
        ]
    return []


def score_cluster_promotability(cluster: Dict[str, Any]) -> int:
    score = 0
    score += 3 * len(cluster.get("positive_prototypes", []))
    score += 1 * len(cluster.get("negative_prototypes", []))
    if str(cluster.get("generalization_scope", "")).strip().lower() in {"file_specific", "integration_specific"}:
        score += 2
    if cluster.get("required_path_signals"):
        score += 2
    if bool(cluster.get("skipped")):
        score -= 4
    return int(score)


def _cluster_rule_id(cluster: Dict[str, Any], generalization_scope: str) -> str:
    integration = cluster["integration"]
    stems = [Path(file_path).stem.strip().lower() for file_path in cluster["bound_files"] if str(file_path).strip()]
    if generalization_scope == "integration_specific":
        scope_token = integration
    else:
        scope_token = "_".join(dict.fromkeys(stems)) or "runtime"
    action_kind = str(cluster["action_kind"]).strip().lower()
    if cluster["family"] in {"CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "POLL_UPDATE"}:
        semantic_kind = "status"
        if any(token in action_kind for token in ("poll", "refresh", "update")):
            semantic_kind = "poll"
        semantic = f"{scope_token}_runtime_{semantic_kind}_read"
    elif cluster["family"] in {"CLOUD_OP", "BLE_OP"}:
        action_token = re.sub(r"[^a-z0-9]+", "_", action_kind).strip("_") or "control"
        semantic = f"{scope_token}_runtime_{action_token}_control"
    elif cluster["family"] == "BLE_CONNECT":
        semantic = f"{scope_token}_runtime_connect"
    elif cluster["family"] in {"SUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE", "MQTT_SUBSCRIBE"}:
        semantic = f"{scope_token}_runtime_subscribe"
    elif cluster["family"] == "STATE_WRITE":
        semantic = f"{scope_token}_runtime_writeback"
    else:
        semantic = f"{scope_token}_{cluster['family'].lower()}"
    return f"{integration}:{semantic}"


def _split_grouped_rows_by_file(
    integration: str,
    bound_files: tuple[str, ...],
    family: str,
    action_kind: str,
    protocol: str,
    rows: List[Dict[str, Any]],
    action_catalog: List[Dict[str, Any]],
) -> List[tuple[str, tuple[str, ...], str, str, str, List[Dict[str, Any]], List[Dict[str, Any]]]]:
    if len(bound_files) <= 1:
        catalog_rows = [
            row
            for row in action_catalog
            if _cluster_key(row) == (integration, bound_files, family, action_kind, protocol)
        ]
        return [
            (
                integration,
                bound_files,
                family,
                action_kind,
                protocol,
                rows,
                catalog_rows or rows,
            )
        ]

    split_rows: List[tuple[str, tuple[str, ...], str, str, str, List[Dict[str, Any]], List[Dict[str, Any]]]] = []
    for file_path in bound_files:
        file_rows: List[Dict[str, Any]] = []
        file_catalog_rows: List[Dict[str, Any]] = []
        for row in rows:
            row_files = {str(item).strip() for item in row.get("bound_files", []) if str(item).strip()}
            if str(file_path).strip() not in row_files:
                continue
            cloned = dict(row)
            cloned["bound_files"] = [str(file_path).strip()]
            file_rows.append(cloned)
        for row in action_catalog:
            if _cluster_key(row) != (integration, bound_files, family, action_kind, protocol):
                continue
            row_files = {str(item).strip() for item in row.get("bound_files", []) if str(item).strip()}
            if str(file_path).strip() not in row_files:
                continue
            cloned = dict(row)
            cloned["bound_files"] = [str(file_path).strip()]
            file_catalog_rows.append(cloned)
        if not file_rows:
            continue
        split_rows.append(
            (
                integration,
                (str(file_path).strip(),),
                family,
                action_kind,
                protocol,
                file_rows,
                file_catalog_rows or file_rows,
            )
        )
    return split_rows


def _build_unresolved_clusters(unresolved_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, tuple[str, ...], str, str, str], List[Dict[str, Any]]] = {}
    action_catalog = [
        row
        for row in unresolved_report.get("action_catalog", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    ]
    for row in unresolved_report.get("unresolved_actions", []):
        if not isinstance(row, dict):
            continue
        grouped.setdefault(_cluster_key(row), []).append(row)

    clusters: List[Dict[str, Any]] = []
    for (integration, bound_files, family, action_kind, protocol), rows in grouped.items():
        split_groups = _split_grouped_rows_by_file(
            integration,
            bound_files,
            family,
            action_kind,
            protocol,
            rows,
            action_catalog,
        )
        for (
            cluster_integration,
            cluster_bound_files,
            cluster_family,
            cluster_action_kind,
            cluster_protocol,
            cluster_rows,
            generalization_rows,
        ) in split_groups:
            merged_preferred_roles = _merge_unique_lists(row.get("preferred_runtime_roles", []) for row in cluster_rows)
            merged_forbidden_roles = _merge_unique_lists(row.get("forbidden_runtime_roles", []) for row in cluster_rows)
            merged_archetypes = _merge_unique_lists(row.get("runtime_archetypes", []) for row in cluster_rows)
            cluster_id = _cluster_id(cluster_integration, cluster_bound_files, cluster_family, cluster_action_kind, cluster_protocol)
            clusters.append(
                {
                    "cluster_id": cluster_id,
                    "integration": cluster_integration,
                    "bound_files": list(cluster_bound_files),
                    "family": cluster_family,
                    "action_kind": cluster_action_kind,
                    "protocol": cluster_protocol,
                    "action_ids": [str(row.get("action_id", "")).strip() for row in cluster_rows if str(row.get("action_id", "")).strip()],
                    "generalizes_action_ids": [
                        str(row.get("action_id", "")).strip()
                        for row in (generalization_rows or cluster_rows)
                        if str(row.get("action_id", "")).strip()
                    ],
                    "rows": cluster_rows,
                    "generalization_rows": generalization_rows or cluster_rows,
                    "preferred_runtime_roles": merged_preferred_roles,
                    "forbidden_runtime_roles": merged_forbidden_roles,
                    "runtime_archetypes": merged_archetypes,
                    "miss_reason_summary": _merge_unique_lists(row.get("miss_reason_summary", []) for row in cluster_rows),
                    "positive_selector_missing_reason": _merge_unique_lists(
                        [[str(row.get("positive_selector_missing_reason", "")).strip()] for row in cluster_rows]
                    ),
                    "shared_accessor_signals": _merge_unique_lists(row.get("shared_accessor_signals", []) for row in cluster_rows),
                    "path_signal_focus": {
                        "preferred_signals": _merge_unique_lists(
                            (
                                row.get("path_signal_focus", {}).get("preferred_signals", [])
                                if isinstance(row.get("path_signal_focus", {}), dict)
                                else []
                            )
                            for row in cluster_rows
                        )[:12],
                        "forbidden_signals": _merge_unique_lists(
                            (
                                row.get("path_signal_focus", {}).get("forbidden_signals", [])
                                if isinstance(row.get("path_signal_focus", {}), dict)
                                else []
                            )
                            for row in cluster_rows
                        )[:12],
                    },
                    "target_identity_tokens": _merge_unique_lists(row.get("target_identity_tokens", []) for row in cluster_rows),
                    "target_tokens": _merge_unique_lists(row.get("target_tokens", []) for row in cluster_rows),
                }
            )
    clusters.sort(key=lambda row: (row["integration"], tuple(row["bound_files"]), row["family"], row["action_kind"], row["cluster_id"]))
    return clusters


def _family_specific_negative_patterns(action_row: Dict[str, Any], family: str) -> tuple[List[str], List[str], List[str], List[str]]:
    if not _action_requires_read_semantics(action_row, family):
        return [], [], [], []
    negative_functions = [
        "async_turn_on",
        "async_turn_off",
        "async_set_*",
        "async_open_*",
        "async_close_*",
        "async_stop_*",
        "async_set_cover_position",
        "turn_on",
        "turn_off",
        "open_*",
        "close_*",
        "stop_*",
        "set_position",
        "set_*",
        "create_*",
        "delete_*",
    ]
    negative_calls = [
        "_async_send_commands",
        "_async_send_wrapper_updates",
        "async_turn_on",
        "async_turn_off",
        "async_open_*",
        "async_close_*",
        "async_stop_*",
        "async_set_cover_position",
        "create_*",
        "delete_*",
        "open_*",
        "close_*",
        "stop_*",
        "set_position",
        "set_*",
        "turn_on",
        "turn_off",
    ]
    negative_evidence = [
        "negative_family_constraint:exclude_control_path_for_read_semantics",
    ]
    why_not_setup = [
        "exclude_control_path_for_read_like_action",
    ]
    return negative_functions, negative_calls, negative_evidence, why_not_setup


def _family_specific_negative_path_signals(action_row: Dict[str, Any], family: str) -> List[str]:
    if not _action_requires_read_semantics(action_row, family):
        return []
    return [
        "control_function:async_turn_on",
        "control_function:async_turn_off",
        "control_function:async_open_cover",
        "control_function:async_close_cover",
        "control_function:async_set_cover_position",
        "control_function:set_state",
        "setup_function:async_setup_entry",
        "state_accessor_property:state",
    ]


def _prune_conflicting_selectors(
    positive_function_patterns: List[str],
    positive_call_patterns: List[str],
    negative_function_patterns: List[str],
    negative_call_patterns: List[str],
) -> tuple[List[str], List[str]]:
    positive_functions = {str(item).strip().lower() for item in positive_function_patterns if str(item).strip()}
    positive_calls = {str(item).strip().lower() for item in positive_call_patterns if str(item).strip()}
    pruned_negative_functions = [
        token for token in negative_function_patterns
        if str(token).strip().lower() not in positive_functions
    ]
    pruned_negative_calls = [
        token for token in negative_call_patterns
        if str(token).strip().lower() not in positive_calls
    ]
    return pruned_negative_functions, pruned_negative_calls


def _required_and_forbidden_context_for_family(
    family: str,
    *,
    preferred_roles: Sequence[str] | None = None,
) -> tuple[List[str], List[str]]:
    family_n = str(family or "").strip().upper()
    preferred = {str(item).strip().lower() for item in (preferred_roles or []) if str(item).strip()}
    if family_n in {"CLOUD_HTTP_CALL", "CLOUD_STATUS_CALL", "POLL_UPDATE"}:
        return ["runtime_update_path"], ["setup_function", "dunder_init", "entity_property_getter"]
    if family_n == "CLOUD_OP":
        return ["runtime_path"], ["setup_function", "dunder_init", "entity_property_getter"]
    if family_n in {"SUBSCRIBE", "UNSUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE", "MQTT_SUBSCRIBE"}:
        if "runtime_read" in preferred and "runtime_subscribe" in preferred:
            return ["runtime_path", "subscription_path"], ["setup_function", "dunder_init"]
        if "runtime_read" in preferred:
            return ["runtime_path"], ["setup_function", "dunder_init"]
        return ["subscription_path"], ["setup_function", "dunder_init"]
    if family_n == "BLE_CONNECT":
        return ["runtime_connect_path"], ["dunder_init"]
    return ["runtime_path"], ["dunder_init"]


def _select_positive_call_patterns(
    *,
    family: str,
    positive_function_patterns: List[str],
    positive_call_patterns: List[str],
    preferred_roles: Sequence[str],
) -> List[str]:
    preferred = {str(item).strip().lower() for item in preferred_roles if str(item).strip()}
    if not positive_call_patterns:
        return []
    if not positive_function_patterns:
        return positive_call_patterns[:6]
    semantic_call_patterns = [
        token
        for token in positive_call_patterns
        if _token_has_strong_read_signal(token)
        or _token_is_control_like(token)
        or token.startswith("subscribe")
        or token.startswith("track_")
        or token.startswith("connect")
        or token.startswith("refresh")
        or token.startswith("poll")
        or token.startswith("fetch")
    ]
    if semantic_call_patterns:
        if "runtime_write" in preferred:
            return semantic_call_patterns[:6]
        read_like_patterns = [token for token in semantic_call_patterns if not _token_is_control_like(token)]
        return read_like_patterns[:6]
    if "runtime_read" in preferred or str(family or "").strip().upper() in {"SUBSCRIBE", "MQTT_SUBSCRIBE", "LOCAL_API_READ", "CLOUD_STATUS_CALL"}:
        return []
    return positive_call_patterns[:6]


def _resolve_related_unresolved_actions(row: Dict[str, Any], unresolved_action_index: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids: List[str] = []
    origin_action_id = str(row.get("origin_action_id", "")).strip()
    if origin_action_id:
        ids.append(origin_action_id)
    ids.extend(
        str(item).strip()
        for item in row.get("source_unresolved_action_ids", [])
        if str(item).strip()
    )
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for action_id in ids:
        if action_id in seen:
            continue
        seen.add(action_id)
        action = unresolved_action_index.get(action_id)
        if action is not None:
            out.append(action)
    return out


def _candidate_functions_for_roles(
    related_actions: List[Dict[str, Any]],
    file_summary_index: Dict[str, Dict[str, Any]],
    roles: Iterable[str],
) -> Set[str]:
    out: Set[str] = set()
    role_list = [str(item).strip().lower() for item in roles if str(item).strip()]
    for action in related_actions:
        for file_path in action.get("bound_files", []) if isinstance(action.get("bound_files", []), list) else []:
            summary = file_summary_index.get(str(file_path).strip())
            if not summary:
                continue
            for role_hint in role_list:
                out.update(_summary_role_function_names(summary, role_hint))
    return {item for item in out if item}


def _expected_roles_for_actions(related_actions: List[Dict[str, Any]], family: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for action in related_actions:
        for role_hint in _preferred_runtime_roles(action, family):
            token = str(role_hint).strip().lower()
            if token and token not in seen:
                seen.add(token)
                out.append(token)
    return out


def _expected_forbidden_roles_for_actions(related_actions: List[Dict[str, Any]], family: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for action in related_actions:
        for role_hint in _forbidden_runtime_roles(action, family):
            token = str(role_hint).strip().lower()
            if token and token not in seen:
                seen.add(token)
                out.append(token)
    return out


def _expected_archetypes_for_actions(related_actions: List[Dict[str, Any]], family: str) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for action in related_actions:
        for item in _runtime_archetypes_for_action(action, family):
            token = str(item).strip()
            if token and token not in seen:
                seen.add(token)
                out.append(token)
    return out


def _refine_llm_runtime_family(
    row: Dict[str, Any],
    unresolved_action_index: Dict[str, Dict[str, Any]],
    file_summary_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any] | None:
    related_actions = _resolve_related_unresolved_actions(row, unresolved_action_index)
    if not related_actions:
        return row
    family = str(row.get("family", "")).strip().upper()
    expected_preferred_roles = _expected_roles_for_actions(related_actions, family)
    expected_forbidden_roles = _expected_forbidden_roles_for_actions(related_actions, family)
    expected_archetypes = _expected_archetypes_for_actions(related_actions, family)
    if not any(_action_requires_read_semantics(action_row, family) for action_row in related_actions):
        return row
    preferred_roles = expected_preferred_roles
    forbidden_roles = expected_forbidden_roles

    positive_functions = [str(item).strip() for item in row.get("function_name_patterns", []) if str(item).strip()]
    positive_calls = [str(item).strip() for item in row.get("call_patterns", []) if str(item).strip()]
    negative_functions = [str(item).strip() for item in row.get("negative_function_patterns", []) if str(item).strip()]
    negative_calls = [str(item).strip() for item in row.get("negative_call_patterns", []) if str(item).strip()]
    negative_evidence = [str(item).strip() for item in row.get("negative_evidence", []) if str(item).strip()]

    removed_functions = [token for token in positive_functions if _token_is_control_like(token)]
    removed_calls = [token for token in positive_calls if _token_is_control_like(token)]
    if removed_functions or removed_calls:
        negative_evidence.append("negative_family_constraint:llm_removed_control_like_positive")
    negative_functions = _unique_tokens([*negative_functions, *removed_functions])
    negative_calls = _unique_tokens([*negative_calls, *removed_calls])
    positive_functions = [token for token in positive_functions if token not in removed_functions]
    positive_calls = [token for token in positive_calls if token not in removed_calls]

    preferred_candidates = _candidate_functions_for_roles(related_actions, file_summary_index, preferred_roles)
    forbidden_candidates = _candidate_functions_for_roles(related_actions, file_summary_index, forbidden_roles)
    if positive_functions and preferred_candidates:
        positive_functions = [token for token in positive_functions if token in preferred_candidates]
    if any(token in forbidden_candidates for token in positive_functions):
        return None

    read_evidence_tokens = [
        *positive_functions,
        *positive_calls,
        *[str(item).split(":", 1)[-1] for item in row.get("runtime_path_evidence", []) if str(item).strip()],
    ]
    has_strong_read_signal = any(_token_has_strong_read_signal(token) for token in read_evidence_tokens)
    if not has_strong_read_signal:
        return None

    normalized = dict(row)
    normalized["function_name_patterns"] = positive_functions
    normalized["call_patterns"] = positive_calls
    normalized["negative_function_patterns"] = negative_functions
    normalized["negative_call_patterns"] = negative_calls
    normalized["negative_evidence"] = _unique_tokens(negative_evidence)
    normalized["preferred_runtime_roles"] = preferred_roles
    normalized["forbidden_runtime_roles"] = forbidden_roles
    normalized["runtime_archetypes"] = expected_archetypes
    return normalized


def _preferred_action_kinds(action_row: Dict[str, Any], family: str) -> List[str]:
    action_type = str(action_row.get("action_type", "") or action_row.get("exec_service", "")).strip().lower()
    service = str(action_row.get("exec_service", "")).strip().lower()
    out: List[str] = []
    if family in {"CLOUD_STATUS_CALL", "CLOUD_HTTP_CALL", "POLL_UPDATE"}:
        if any(token in f"{action_type} {service}" for token in ("status", "read_runtime", "poll", "refresh", "update")):
            out.extend(["status", "poll_update"])
        else:
            out.append("call_api")
    elif family == "BLE_CONNECT":
        out.append("connect")
    elif family in {"SUBSCRIBE", "BLE_NOTIFY_SUBSCRIBE", "MQTT_SUBSCRIBE"}:
        if _action_requires_read_semantics(action_row, family):
            out.extend(["subscribe", "read", action_type or service])
        else:
            out.append("subscribe")
    elif family == "LOCAL_API_READ":
        out.extend(["read", "local_api_read"])
    elif family in {"CLOUD_OP", "BLE_OP"}:
        out.extend(["control", action_type or service])
    elif family == "STATE_WRITE":
        out.extend(["publish", "write"])
    else:
        if action_type:
            out.append(action_type)
    return _informative_tokens(out)


def _boost_target_tokens(action_row: Dict[str, Any]) -> List[str]:
    target_kind = str(action_row.get("target_kind", "")).strip().lower()
    action_type = str(action_row.get("action_type", "")).strip().lower()
    protocol = str(action_row.get("protocol", "")).strip().lower()
    service = str(action_row.get("exec_service", "")).strip().lower()
    domain = str(action_row.get("exec_domain", "")).strip().lower()
    integrations = [str(item).strip().lower() for item in action_row.get("integrations", []) if str(item).strip()]
    marker_hints = [str(item).strip().lower() for item in action_row.get("marker_hints", []) if str(item).strip()]
    target_tokens = [str(item).strip().lower() for item in action_row.get("target_tokens", []) if str(item).strip()]
    target_identity_tokens = [
        str(item).strip().lower()
        for item in action_row.get("target_identity_tokens", [])
        if str(item).strip()
    ]
    preferred_roles = [str(item).strip().lower() for item in action_row.get("preferred_runtime_roles", []) if str(item).strip()]
    runtime_archetypes = [str(item).strip().lower() for item in action_row.get("runtime_archetypes", []) if str(item).strip()]
    generic_tokens = set(
        _informative_tokens(
            [
                target_kind,
                action_type,
                protocol,
                service,
                domain,
                *integrations,
                *marker_hints,
                *preferred_roles,
                *runtime_archetypes,
                "true",
                "false",
                "none",
            ]
        )
    )
    source_tokens = target_identity_tokens or target_tokens
    discriminative_tokens = [token for token in source_tokens if token and token not in generic_tokens]
    prioritized_tokens = [
        token
        for token in discriminative_tokens
        if any(ch.isdigit() for ch in token) or ":" in token or "." in token or "_" in token
    ]
    if prioritized_tokens:
        return _informative_tokens([*prioritized_tokens, *discriminative_tokens])
    if discriminative_tokens:
        return _informative_tokens(discriminative_tokens)
    return _informative_tokens([*source_tokens, target_kind, action_type, protocol, service, domain, *marker_hints])


def _cluster_boost_target_tokens(cluster: Dict[str, Any]) -> List[str]:
    return _informative_tokens(
        token
        for row in cluster.get("generalization_rows", cluster.get("rows", []))
        for token in _boost_target_tokens(row)
    )


def build_unresolved_grounding_report(
    optimization_target: OptimizationTarget,
    marker_grounding: Dict[str, Any],
    marker_set: Iterable[Marker] | None = None,
) -> Dict[str, Any]:
    markers = list(marker_set or [])
    missing = [str(item).strip() for item in marker_grounding.get("missing_critical_action_ids", []) if str(item).strip()]
    actions = _action_index(optimization_target)
    bindings = _source_bindings(optimization_target)
    unresolved_actions: List[Dict[str, Any]] = []
    file_summaries: Dict[str, Dict[str, Any]] = {}

    for row in bindings:
        file_path = str(row.get("file_path", "")).strip()
        integration = str(row.get("integration", "")).strip().lower()
        if file_path and file_path not in file_summaries:
            file_summaries[file_path] = _source_file_summary(file_path, integration)

    for action_id in missing:
        action = actions.get(action_id, {})
        action_markers = _marker_refs_for_action(action_id, markers)
        action_bindings = _action_bindings(action, bindings)
        bound_files = [str(row.get("file_path", "")).strip() for row in action_bindings if str(row.get("file_path", "")).strip()]
        integrations = sorted({str(row.get("integration", "")).strip().lower() for row in action_bindings if str(row.get("integration", "")).strip()})
        current_detected_marker_types = sorted(
            {
                str(marker.marker_type).strip().upper()
                for marker in action_markers
                if str(marker.marker_type).strip()
            }
        )
        preferred_roles = _preferred_runtime_roles(action, _preferred_family(action))
        forbidden_roles = _forbidden_runtime_roles(action, _preferred_family(action))
        runtime_archetypes = _runtime_archetypes_for_action(action, _preferred_family(action))
        path_contrast_examples = _action_path_contrast_examples(bound_files, file_summaries, preferred_roles, forbidden_roles)
        path_signal_focus = _action_path_signal_focus(bound_files, file_summaries, preferred_roles, forbidden_roles)
        positive_selector_missing_reason = _positive_selector_missing_reason(
            bound_files,
            file_summaries,
            preferred_roles,
        )
        shared_accessor_signals = _merge_unique_lists(
            [
                file_summaries.get(file_path, {}).get("shared_accessor_signals", [])
                for file_path in bound_files
                if file_summaries.get(file_path)
            ]
        )

        unresolved_actions.append(
            {
                "action_id": action_id,
                "protocol": str(action.get("protocol", "")).strip().upper(),
                "action_type": str(action.get("type", "")).strip().lower(),
                "target_tokens": sorted(
                    _normalized_hint_tokens(action.get("target", {}))
                    | _normalized_hint_tokens(action.get("exec", {}))
                )[:24],
                "target_identity_tokens": sorted(_normalized_hint_tokens(action.get("target", {})))[:24],
                "marker_hints": [str(item).strip().upper() for item in action.get("marker_hints", []) if str(item).strip()],
                "target_kind": str(action.get("target_kind", "")).strip(),
                "exec_kind": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("kind", "")).strip(),
                "exec_domain": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("domain", "")).strip(),
                "exec_service": str((action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}).get("service", "")).strip(),
                "bound_files": bound_files,
                "integrations": integrations,
                "unresolved_reason": "missing_runtime_grounding_in_m1",
                "miss_reason_summary": _miss_reason_summary(action_markers),
                "current_detected_marker_types": current_detected_marker_types,
                "weak_marker_examples": _weak_marker_examples(action_markers),
                "binding_fail_markers": _binding_fail_markers(action_markers),
                "preferred_runtime_roles": preferred_roles,
                "forbidden_runtime_roles": forbidden_roles,
                "runtime_archetypes": runtime_archetypes,
                "positive_selector_missing_reason": positive_selector_missing_reason,
                "shared_accessor_signals": shared_accessor_signals,
                "path_contrast_examples": path_contrast_examples,
                "path_signal_focus": path_signal_focus,
            }
        )

    report = {
        "schema_version": UNRESOLVED_REPORT_SCHEMA_VERSION,
        "generated_at": now_utc_iso(),
        "builder_version": BUILDER_VERSION,
        "target_meta": {
            "vdev_id": str(optimization_target.meta.get("vdev_id", "")).strip(),
            "name": str(optimization_target.meta.get("name", "")).strip(),
        },
        "missing_critical_action_ids": missing,
        "resolved_action_ids": [str(item).strip() for item in marker_grounding.get("resolved_action_ids", []) if str(item).strip()],
        "action_catalog": [_action_catalog_row(action, bindings) for action in actions.values() if isinstance(action, dict)],
        "unresolved_actions": unresolved_actions,
        "source_file_summaries": list(file_summaries.values()),
    }
    report["source_report_sha256"] = _sha256_json(report)
    return report


def _build_heuristic_rule_from_cluster(
    cluster: Dict[str, Any],
    file_summaries: Dict[str, Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any] | None]:
    integration = cluster["integration"]
    family = cluster["family"]
    lead_row = cluster["rows"][0]
    preferred_roles = [str(item).strip().lower() for item in cluster.get("preferred_runtime_roles", []) if str(item).strip()]
    forbidden_roles = [str(item).strip().lower() for item in cluster.get("forbidden_runtime_roles", []) if str(item).strip()]
    runtime_archetypes = [str(item).strip() for item in cluster.get("runtime_archetypes", []) if str(item).strip()]

    prototypes = _synthesize_cluster_prototypes(cluster, file_summaries)
    positive_prototypes = list(prototypes["positive_prototypes"])
    negative_prototypes = list(prototypes["negative_prototypes"])
    allow_accessor_fallback = False
    if not positive_prototypes:
        synthetic_positive = fallback_positive_synthesis(cluster, file_summaries, negative_prototypes)
        if synthetic_positive:
            positive_prototypes.extend(synthetic_positive)
            allow_accessor_fallback = True
    required_path_signals, forbidden_path_signals = _prototype_path_constraints(
        positive_prototypes,
        negative_prototypes,
    )
    positive_selector_missing_reason = _merge_unique_lists(
        [
            cluster.get("positive_selector_missing_reason", []),
            ["synthetic_accessor_positive_selected"] if allow_accessor_fallback else [],
        ]
    )
    generalization_scope, why_not_more_general = _candidate_generalization_scope(
        cluster,
        {
            "positive_prototypes": positive_prototypes,
            "negative_prototypes": negative_prototypes,
            "required_path_signals": required_path_signals,
            "forbidden_path_signals": forbidden_path_signals,
        },
    )

    skipped = False
    skip_reason = ""
    if not positive_prototypes:
        skipped = True
        skip_reason = "no_positive_selector_after_prototype_synthesis"
    effective_forbidden_roles = list(forbidden_roles)
    if _positive_private_update_carrier_selected(positive_prototypes, preferred_roles):
        effective_forbidden_roles = [role for role in effective_forbidden_roles if role != "helper"]

    positive_function_patterns = _informative_tokens(
        proto.get("function_name", "")
        for proto in positive_prototypes
        if str(proto.get("function_name", "")).strip()
    )
    positive_call_patterns = _informative_tokens(
        token
        for proto in positive_prototypes
        for token in [*proto.get("call_patterns", []), *proto.get("call_chains", [])]
    )
    (
        positive_function_patterns,
        positive_call_patterns,
        wrapper_removed_functions,
        wrapper_removed_calls,
    ) = _filter_wrapper_like_positive_selectors(
        positive_function_patterns,
        positive_call_patterns,
        positive_prototypes,
        preferred_roles,
    )
    (
        positive_function_patterns,
        positive_call_patterns,
        control_removed_functions,
        control_removed_calls,
    ) = _filter_control_aligned_selectors(
        cluster,
        positive_function_patterns,
        positive_call_patterns,
    )
    positive_call_patterns = _select_positive_call_patterns(
        family=family,
        positive_function_patterns=positive_function_patterns,
        positive_call_patterns=positive_call_patterns,
        preferred_roles=preferred_roles,
    )
    negative_function_patterns = _informative_tokens(
        proto.get("function_name", "")
        for proto in negative_prototypes
        if str(proto.get("function_name", "")).strip()
    )
    negative_call_patterns = _informative_tokens(
        token
        for proto in negative_prototypes
        for token in [*proto.get("call_patterns", []), *proto.get("call_chains", [])]
    )
    runtime_path_evidence = _merge_unique_lists(
        [
            [f"runtime_function:{proto['function_name']}" for proto in positive_prototypes if proto.get("function_name")],
            [
                f"runtime_call:{token}"
                for proto in positive_prototypes
                for token in [*proto.get("call_patterns", []), *proto.get("call_chains", [])]
            ],
            [f"path_signal:{token}" for token in required_path_signals],
            [f"path_signal:{token}" for token in cluster.get("path_signal_focus", {}).get("preferred_signals", [])],
        ]
    )
    negative_evidence = _merge_unique_lists(
        [
            [f"negative_function:{proto['function_name']}" for proto in negative_prototypes if proto.get("function_name")],
            [
                f"negative_call:{token}"
                for proto in negative_prototypes
                for token in [*proto.get("call_patterns", []), *proto.get("call_chains", [])]
            ],
            [f"negative_path_signal:{token}" for token in forbidden_path_signals],
            [f"negative_path_signal:{token}" for token in cluster.get("path_signal_focus", {}).get("forbidden_signals", [])],
        ]
    )
    why_not_setup = _merge_unique_lists(
        [
            [
                f"exclude_role:{proto.get('role_hint')}:{proto.get('function_name')}"
                for proto in negative_prototypes
                if proto.get("role_hint") in set(effective_forbidden_roles) and proto.get("function_name")
            ],
            [f"exclude_path_signal:{token}" for token in forbidden_path_signals],
        ]
    )
    family_negative_functions, family_negative_calls, family_negative_evidence, family_why_not_setup = (
        _family_specific_negative_patterns(lead_row, family)
    )
    family_negative_path_signals = _family_specific_negative_path_signals(lead_row, family)
    negative_function_patterns = _unique_tokens(
        [
            *negative_function_patterns,
            *wrapper_removed_functions,
            *[token for token in family_negative_functions if token not in set(positive_function_patterns)],
        ]
    )
    negative_call_patterns = _unique_tokens(
        [
            *negative_call_patterns,
            *wrapper_removed_calls,
            *[token for token in family_negative_calls if token not in set(positive_call_patterns)],
        ]
    )
    negative_function_patterns, negative_call_patterns = _prune_conflicting_selectors(
        positive_function_patterns,
        positive_call_patterns,
        negative_function_patterns,
        negative_call_patterns,
    )
    forbidden_path_signals = _unique_tokens([*forbidden_path_signals, *family_negative_path_signals])
    negative_evidence = _unique_tokens([*negative_evidence, *family_negative_evidence])
    if wrapper_removed_functions or wrapper_removed_calls:
        negative_evidence = _unique_tokens(
            [*negative_evidence, "negative_family_constraint:wrapper_like_positive_removed"]
        )
    if control_removed_functions or control_removed_calls:
        negative_evidence = _unique_tokens(
            [*negative_evidence, "negative_family_constraint:control_selector_misaligned_positive_removed"]
        )
    why_not_setup = _unique_tokens([*why_not_setup, *family_why_not_setup])
    required_context, forbidden_context = _required_and_forbidden_context_for_family(
        family,
        preferred_roles=preferred_roles,
    )
    if allow_accessor_fallback:
        forbidden_context = [token for token in forbidden_context if token != "entity_property_getter"]

    imports = sorted(
        {
            str(item).strip().lower()
            for file_path in cluster["bound_files"]
            for item in file_summaries.get(file_path, {}).get("imports", [])
            if str(item).strip()
        }
    )
    proposal = None
    if not skipped:
        proposal = {
            "rule_id": _cluster_rule_id(cluster, generalization_scope),
            "integration": integration,
            "family": family,
            "action_kind": cluster["action_kind"],
            "generalization_scope": generalization_scope,
            "generalizes_actions": list(cluster.get("generalizes_action_ids", cluster["action_ids"])),
            "origin_cluster_id": cluster["cluster_id"],
            "file_globs": ["/".join(Path(file_path).parts[-2:]) for file_path in cluster["bound_files"]] or [f"{integration}/*.py"],
            "call_patterns": positive_call_patterns[:6],
            "function_name_patterns": positive_function_patterns[:4],
            "negative_call_patterns": negative_call_patterns[:6],
            "negative_function_patterns": negative_function_patterns[:6],
            "required_context": required_context,
            "forbidden_context": forbidden_context,
            "required_path_signals": required_path_signals[:8],
            "forbidden_path_signals": forbidden_path_signals[:8],
            "required_runtime_roles": preferred_roles,
            "forbidden_runtime_roles": effective_forbidden_roles,
            "allow_accessor_fallback": allow_accessor_fallback,
            "binding_hints": {
                "preferred_action_kinds": _preferred_action_kinds(lead_row, family),
                "boost_target_tokens": _cluster_boost_target_tokens(cluster),
                "required_service_tokens": _required_service_tokens(cluster),
                "phase": "RUNTIME",
            },
            "preferred_runtime_roles": preferred_roles,
            "forbidden_runtime_roles": effective_forbidden_roles,
            "runtime_archetypes": runtime_archetypes,
            "positive_prototypes": positive_prototypes,
            "negative_prototypes": negative_prototypes,
            "runtime_path_evidence": runtime_path_evidence[:10],
            "negative_evidence": negative_evidence[:10],
            "why_not_setup": why_not_setup[:8],
            "why_not_more_general": why_not_more_general,
            "phase": "RUNTIME",
            "strength": "MEDIUM",
            "confidence": {
                "base": 0.7,
                "emit_threshold": 0.7,
                "boost_if_imports": imports[:6],
                "boost_if_names": _informative_tokens([cluster["action_kind"], *positive_function_patterns, *positive_call_patterns])[:6],
            },
            "origin_action_id": cluster["action_ids"][0] if len(cluster["action_ids"]) == 1 else None,
            "source_file_paths": list(cluster["bound_files"]),
            "source_unresolved_action_ids": list(cluster["action_ids"]),
            "reviewer_status": "draft",
        }

    cluster_summary = {
        "cluster_id": cluster["cluster_id"],
        "integration": integration,
        "bound_files": cluster["bound_files"],
        "family": family,
        "action_kind": cluster["action_kind"],
        "protocol": cluster["protocol"],
        "action_ids": cluster["action_ids"],
        "generalizes_actions": cluster.get("generalizes_action_ids", cluster["action_ids"]),
        "generalization_scope": generalization_scope,
        "positive_prototypes": positive_prototypes,
        "negative_prototypes": negative_prototypes,
        "required_path_signals": required_path_signals[:8],
        "forbidden_path_signals": forbidden_path_signals[:8],
        "positive_selector_missing_reason": positive_selector_missing_reason,
        "shared_accessor_signals": list(cluster.get("shared_accessor_signals", [])),
        "allow_accessor_fallback": allow_accessor_fallback,
        "skipped": skipped,
        "skip_reason": skip_reason,
        "heuristic_rule": proposal,
    }
    cluster_summary["promotability_score"] = score_cluster_promotability(cluster_summary)
    if proposal is None or cluster_summary["promotability_score"] < LLM_REFINE_THRESHOLD:
        cluster_summary["promotion_decision"] = "report_only"
    elif cluster_summary["promotability_score"] >= HEURISTIC_PROMOTION_THRESHOLD:
        cluster_summary["promotion_decision"] = "promote"
    else:
        cluster_summary["promotion_decision"] = "llm_refine"
    return cluster_summary, proposal


def build_heuristic_profile_from_clusters(unresolved_report: Dict[str, Any], *, mode: str = "repair") -> Dict[str, Any]:
    file_summaries = {
        str(row.get("file_path", "")).strip(): row
        for row in unresolved_report.get("source_file_summaries", [])
        if isinstance(row, dict) and str(row.get("file_path", "")).strip()
    }
    drafts_by_integration: Dict[str, Dict[str, Any]] = {}
    proposal_items: List[Dict[str, Any]] = []
    source_report_sha256 = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
    clusters = _build_unresolved_clusters(unresolved_report)
    cluster_summaries: List[Dict[str, Any]] = []

    for cluster in clusters:
        cluster_summary, proposal = _build_heuristic_rule_from_cluster(cluster, file_summaries)
        cluster_summaries.append(cluster_summary)
        if proposal is None:
            continue
        if cluster_summary.get("promotion_decision") != "promote":
            continue
        integration = cluster_summary["integration"]
        draft = drafts_by_integration.setdefault(
            integration,
            {
                "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                "integration": integration,
                "version": "draft_v3",
                "runtime_families": [],
            },
        )
        draft["runtime_families"].append(proposal)
        proposal_items.append(
            {
                "integration": integration,
                "cluster_id": cluster_summary["cluster_id"],
                "action_ids": cluster_summary["action_ids"],
                "generalizes_actions": cluster_summary.get("generalizes_actions", cluster_summary["action_ids"]),
                "family": cluster_summary["family"],
                "action_kind": cluster_summary["action_kind"],
                "bound_files": cluster_summary["bound_files"],
                "generalization_scope": cluster_summary["generalization_scope"],
                "proposal_rule_id": proposal["rule_id"],
                "miss_reason_summary": cluster.get("miss_reason_summary", []),
                "promotability_score": cluster_summary.get("promotability_score", 0),
            }
        )

    detector_profile_drafts = [draft for draft in drafts_by_integration.values() if draft.get("runtime_families")]

    return {
        "schema_version": DETECTOR_DRAFT_SCHEMA_VERSION,
        "generated_at": now_utc_iso(),
        "builder_version": BUILDER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "mode": str(mode or "repair").strip().lower() or "repair",
        "source_report_version": str(unresolved_report.get("schema_version", "")),
        "source_report_sha256": source_report_sha256,
        "cluster_count": len(cluster_summaries),
        "cluster_summaries": cluster_summaries,
        "proposal_count": len(proposal_items),
        "proposal_items": proposal_items,
        "detector_profile_drafts": detector_profile_drafts,
        "workflow": {
            "mode": "offline_llm_assisted_then_deterministic_execute",
            "next_step": "Review detector_profile_drafts, refine with LLM offline, then pass resulting JSON via validation.grounding_profile_paths.",
        },
    }


def build_detector_profile_draft(unresolved_report: Dict[str, Any], *, mode: str = "repair") -> Dict[str, Any]:
    return build_heuristic_profile_from_clusters(unresolved_report, mode=mode)


def build_llm_fallback_from_heuristic_draft(
    heuristic_draft: Dict[str, Any],
    *,
    reason: str,
    request_sha256: str = "",
) -> Dict[str, Any]:
    detector_profile_drafts = [
        draft
        for draft in heuristic_draft.get("detector_profile_drafts", [])
        if isinstance(draft, dict) and isinstance(draft.get("runtime_families", []), list) and draft.get("runtime_families")
    ]
    proposal_items = [
        item
        for item in heuristic_draft.get("proposal_items", [])
        if isinstance(item, dict)
    ]
    cluster_decisions: List[Dict[str, Any]] = []
    for cluster in heuristic_draft.get("cluster_summaries", []):
        if not isinstance(cluster, dict):
            continue
        decision = "report_only"
        if str(cluster.get("promotion_decision", "")).strip().lower() in {"promote", "llm_refine"} and isinstance(cluster.get("heuristic_rule"), dict):
            decision = "heuristic_fallback"
        cluster_decisions.append(
            {
                "cluster_id": cluster.get("cluster_id"),
                "decision": decision,
                "reason": reason,
                "promotability_score": int(cluster.get("promotability_score", 0) or 0),
                "heuristic_rule_id": (cluster.get("heuristic_rule", {}) if isinstance(cluster.get("heuristic_rule", {}), dict) else {}).get("rule_id"),
            }
        )
    return {
        "schema_version": DETECTOR_DRAFT_SCHEMA_VERSION,
        "generated_at": now_utc_iso(),
        "builder_version": BUILDER_VERSION,
        "prompt_version": heuristic_draft.get("prompt_version", PROMPT_VERSION),
        "request_sha256": str(request_sha256 or "").strip(),
        "source_report_version": heuristic_draft.get("source_report_version", ""),
        "source_report_sha256": heuristic_draft.get("source_report_sha256", ""),
        "proposal_count": len(proposal_items),
        "proposal_items": proposal_items,
        "cluster_count": int(heuristic_draft.get("cluster_count", 0) or 0),
        "cluster_decisions": cluster_decisions,
        "detector_profile_drafts": detector_profile_drafts,
        "workflow": {
            "mode": "offline_llm_assisted_then_deterministic_execute",
            "next_step": "LLM refinement failed; using promotable heuristic cluster rules as deterministic fallback.",
        },
        "heuristic_baseline_proposal_count": int(heuristic_draft.get("proposal_count", 0) or 0),
        "llm_fallback_reason": str(reason or "").strip(),
    }


def _json_text_from_llm_content(content: str) -> str:
    text = str(content or "").strip()
    if not text:
        raise DetectorBuilderLLMError("LLM response content is empty")
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    start = min((idx for idx in (text.find("{"), text.find("[")) if idx >= 0), default=-1)
    if start >= 0:
        return text[start:].strip()
    return text


def _content_from_chat_response(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise DetectorBuilderLLMError("LLM response missing choices[0]")
    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out: List[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("text"), str):
                out.append(item["text"])
            elif item.get("type") == "output_text" and isinstance(item.get("text"), str):
                out.append(item["text"])
        return "\n".join(part for part in out if part.strip())
    raise DetectorBuilderLLMError("LLM response content has unsupported shape")


def _normalized_file_globs(values: Any, integration: str) -> List[str]:
    out: List[str] = []
    if isinstance(values, list):
        for item in values:
            token = str(item or "").strip()
            if token and token not in out:
                out.append(token)
    if out:
        return out
    return [f"{integration}/*.py"] if integration else ["*.py"]


def _normalize_context_tokens(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    synonyms = {
        "cloud_runtime_read": "runtime_update_path",
        "cloud_runtime_control": "runtime_path",
        "coordinator_update_path": "runtime_update_path",
        "entity_wrapper_read": "runtime_path",
        "entity_control_path": "runtime_path",
        "local_bridge_getter": "runtime_path",
        "mqtt_message_read": "subscription_path",
        "ble_transport_connect": "runtime_connect_path",
        "ble_runtime_control": "runtime_path",
        "device_control_path": "runtime_path",
        "subscription_listener": "subscription_path",
        "setup_path": "setup_function",
        "teardown_path": "teardown_function",
        "property_path": "entity_property_getter",
        "helper_path": "helper_wrapper",
        "read_path": "runtime_update_path",
        "control_path": "runtime_path",
        "connect_path": "runtime_connect_path",
    }
    out: List[str] = []
    seen: Set[str] = set()
    for item in values:
        token = str(item or "").strip().lower()
        if not token:
            continue
        normalized = synonyms.get(token, token)
        if normalized not in _SUPPORTED_CONTEXT_FLAGS or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _normalize_runtime_family(row: Dict[str, Any], integration: str, index: int) -> Dict[str, Any]:
    family = str(row.get("family", "") or row.get("marker_type", "")).strip().upper()
    if not family:
        raise DetectorBuilderLLMError(f"LLM detector profile missing family at index {index}")
    confidence = row.get("confidence", {}) if isinstance(row.get("confidence", {}), dict) else {}
    binding_hints = row.get("binding_hints", {}) if isinstance(row.get("binding_hints", {}), dict) else {}
    call_patterns = row.get("call_patterns", [])
    function_patterns = row.get("function_name_patterns", row.get("function_patterns", []))
    return {
        "rule_id": str(row.get("rule_id", "") or f"{integration}:{family.lower()}:{index}").strip(),
        "integration": integration,
        "family": family,
        "action_kind": str(row.get("action_kind", "")).strip().lower(),
        "generalization_scope": str(row.get("generalization_scope", "action_specific") or "action_specific").strip().lower(),
        "generalizes_actions": [str(item).strip() for item in row.get("generalizes_actions", []) if str(item).strip()],
        "origin_cluster_id": str(row.get("origin_cluster_id", "")).strip() or None,
        "file_globs": _normalized_file_globs(row.get("file_globs", []), integration),
        "call_patterns": [str(item).strip() for item in call_patterns if str(item).strip()],
        "function_name_patterns": [str(item).strip() for item in function_patterns if str(item).strip()],
        "negative_call_patterns": [str(item).strip() for item in row.get("negative_call_patterns", []) if str(item).strip()],
        "negative_function_patterns": [str(item).strip() for item in row.get("negative_function_patterns", []) if str(item).strip()],
        "required_context": _normalize_context_tokens(row.get("required_context", [])),
        "forbidden_context": _normalize_context_tokens(row.get("forbidden_context", [])),
        "required_path_signals": [str(item).strip() for item in row.get("required_path_signals", []) if str(item).strip()],
        "forbidden_path_signals": [str(item).strip() for item in row.get("forbidden_path_signals", []) if str(item).strip()],
        "required_runtime_roles": [str(item).strip().lower() for item in row.get("required_runtime_roles", []) if str(item).strip()],
        "forbidden_runtime_roles": [str(item).strip().lower() for item in row.get("forbidden_runtime_roles", []) if str(item).strip()],
        "allow_accessor_fallback": bool(row.get("allow_accessor_fallback", False)),
        "binding_hints": {
            "preferred_action_kinds": [str(item).strip() for item in binding_hints.get("preferred_action_kinds", []) if str(item).strip()],
            "boost_target_tokens": [str(item).strip() for item in binding_hints.get("boost_target_tokens", []) if str(item).strip()],
            "required_service_tokens": [str(item).strip() for item in binding_hints.get("required_service_tokens", []) if str(item).strip()],
            "phase": str(binding_hints.get("phase", row.get("phase", "RUNTIME")) or "RUNTIME").strip().upper(),
        },
        "preferred_runtime_roles": [str(item).strip().lower() for item in row.get("preferred_runtime_roles", []) if str(item).strip()],
        "forbidden_runtime_roles": [str(item).strip().lower() for item in row.get("forbidden_runtime_roles", []) if str(item).strip()],
        "runtime_archetypes": [str(item).strip() for item in row.get("runtime_archetypes", []) if str(item).strip()],
        "positive_prototypes": [item for item in row.get("positive_prototypes", []) if isinstance(item, dict)],
        "negative_prototypes": [item for item in row.get("negative_prototypes", []) if isinstance(item, dict)],
        "runtime_path_evidence": [str(item).strip() for item in row.get("runtime_path_evidence", []) if str(item).strip()],
        "negative_evidence": [str(item).strip() for item in row.get("negative_evidence", []) if str(item).strip()],
        "why_not_setup": [str(item).strip() for item in row.get("why_not_setup", []) if str(item).strip()],
        "why_not_more_general": str(row.get("why_not_more_general", "")).strip(),
        "phase": str(row.get("phase", "RUNTIME") or "RUNTIME").strip().upper(),
        "strength": str(row.get("strength", "MEDIUM") or "MEDIUM").strip().upper(),
        "confidence": {
            "base": float(confidence.get("base", row.get("base_confidence", 0.7)) or 0.7),
            "emit_threshold": float(confidence.get("emit_threshold", row.get("emit_threshold", 0.7)) or 0.7),
            "boost_if_imports": [str(item).strip() for item in confidence.get("boost_if_imports", []) if str(item).strip()],
            "boost_if_names": [str(item).strip() for item in confidence.get("boost_if_names", []) if str(item).strip()],
        },
        "origin_action_id": str(row.get("origin_action_id", "")).strip() or None,
        "source_file_paths": [str(item).strip() for item in row.get("source_file_paths", []) if str(item).strip()],
        "source_unresolved_action_ids": [str(item).strip() for item in row.get("source_unresolved_action_ids", []) if str(item).strip()],
        "reviewer_status": str(row.get("reviewer_status", "draft") or "draft").strip().lower(),
    }


def _merge_generalization_scope(current: str, new: str) -> str:
    rank = {"action_specific": 0, "file_specific": 1, "integration_specific": 2}
    current_n = str(current or "action_specific").strip().lower()
    new_n = str(new or "action_specific").strip().lower()
    return new_n if rank.get(new_n, 0) > rank.get(current_n, 0) else current_n


def _merge_runtime_families(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[Any, ...], Dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("integration", "")).strip().lower(),
            str(row.get("family", "")).strip().upper(),
            tuple(row.get("file_globs", [])),
            tuple(row.get("function_name_patterns", [])),
            tuple(row.get("call_patterns", [])),
            tuple(row.get("negative_function_patterns", [])),
            tuple(row.get("negative_call_patterns", [])),
            tuple(row.get("required_context", [])),
            tuple(row.get("forbidden_context", [])),
            str(row.get("origin_cluster_id", "") or ""),
        )
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = dict(row)
            continue
        existing["generalization_scope"] = _merge_generalization_scope(existing.get("generalization_scope", ""), row.get("generalization_scope", ""))
        if not existing.get("action_kind") and row.get("action_kind"):
            existing["action_kind"] = row.get("action_kind")
        existing["generalizes_actions"] = _merge_unique_lists([existing.get("generalizes_actions", []), row.get("generalizes_actions", [])])
        existing["source_unresolved_action_ids"] = _merge_unique_lists(
            [existing.get("source_unresolved_action_ids", []), row.get("source_unresolved_action_ids", [])]
        )
        existing["source_file_paths"] = _merge_unique_lists([existing.get("source_file_paths", []), row.get("source_file_paths", [])])
        existing["positive_prototypes"] = [*existing.get("positive_prototypes", []), *[item for item in row.get("positive_prototypes", []) if item not in existing.get("positive_prototypes", [])]]
        existing["negative_prototypes"] = [*existing.get("negative_prototypes", []), *[item for item in row.get("negative_prototypes", []) if item not in existing.get("negative_prototypes", [])]]
        existing["required_path_signals"] = _merge_unique_lists([existing.get("required_path_signals", []), row.get("required_path_signals", [])])
        existing["forbidden_path_signals"] = _merge_unique_lists([existing.get("forbidden_path_signals", []), row.get("forbidden_path_signals", [])])
        existing["allow_accessor_fallback"] = bool(existing.get("allow_accessor_fallback")) or bool(row.get("allow_accessor_fallback"))
        if not existing.get("origin_cluster_id") and row.get("origin_cluster_id"):
            existing["origin_cluster_id"] = row.get("origin_cluster_id")
        if not existing.get("origin_action_id") and row.get("origin_action_id"):
            existing["origin_action_id"] = row.get("origin_action_id")
    return list(grouped.values())


def _normalize_llm_detector_draft(
    payload: Dict[str, Any],
    unresolved_report: Dict[str, Any],
    *,
    prompt_version: str,
    request_sha256: str,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise DetectorBuilderLLMError("LLM detector draft payload must be a JSON object")

    raw_drafts = payload.get("detector_profile_drafts")
    if isinstance(raw_drafts, list) and not raw_drafts:
        raw_drafts = []
    elif not isinstance(raw_drafts, list) or not raw_drafts:
        if isinstance(payload.get("runtime_families"), list):
            integration = str(payload.get("integration", "")).strip().lower() or "unknown"
            raw_drafts = [
                {
                    "integration": integration,
                    "version": str(payload.get("version", "draft_llm") or "draft_llm"),
                    "runtime_families": payload.get("runtime_families", []),
                }
            ]
        else:
            raise DetectorBuilderLLMError("LLM payload missing detector_profile_drafts/runtime_families")

    detector_profile_drafts: List[Dict[str, Any]] = []
    proposal_items: List[Dict[str, Any]] = []
    proposal_count = 0
    unresolved_action_index = {
        str(row.get("action_id", "")).strip(): row
        for row in unresolved_report.get("unresolved_actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    file_summary_index = {
        str(row.get("file_path", "")).strip(): row
        for row in unresolved_report.get("source_file_summaries", [])
        if isinstance(row, dict) and str(row.get("file_path", "")).strip()
    }

    for draft_index, draft in enumerate(raw_drafts):
        if not isinstance(draft, dict):
            continue
        integration = str(draft.get("integration", "")).strip().lower() or f"unknown_{draft_index}"
        runtime_families_raw = draft.get("runtime_families", [])
        if not isinstance(runtime_families_raw, list):
            continue
        runtime_families: List[Dict[str, Any]] = []
        for idx, row in enumerate(runtime_families_raw):
            if not isinstance(row, dict):
                continue
            normalized_row = _normalize_runtime_family(row, integration, idx)
            refined_row = _refine_llm_runtime_family(normalized_row, unresolved_action_index, file_summary_index)
            if refined_row is None:
                continue
            runtime_families.append(refined_row)
        runtime_families = _merge_runtime_families(runtime_families)
        if not runtime_families:
            continue
        detector_profile_drafts.append(
            {
                "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                "integration": integration,
                "version": str(draft.get("version", "draft_llm_v3") or "draft_llm_v3"),
                "runtime_families": runtime_families,
            }
        )
        for row in runtime_families:
            proposal_count += 1
            proposal_items.append(
                {
                    "integration": integration,
                    "family": row["family"],
                    "generalization_scope": row.get("generalization_scope"),
                    "generalizes_actions": row.get("generalizes_actions", []),
                    "origin_cluster_id": row.get("origin_cluster_id"),
                    "proposal_rule_id": row["rule_id"],
                    "origin_action_id": row.get("origin_action_id"),
                }
            )

    source_report_sha256 = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
    normalized = {
        "schema_version": DETECTOR_DRAFT_SCHEMA_VERSION,
        "generated_at": now_utc_iso(),
        "builder_version": BUILDER_VERSION,
        "prompt_version": prompt_version,
        "request_sha256": request_sha256,
        "source_report_version": str(unresolved_report.get("schema_version", "")),
        "source_report_sha256": source_report_sha256,
        "proposal_count": proposal_count,
        "proposal_items": proposal_items,
        "cluster_count": len(
            {
                str(item.get("origin_cluster_id", "")).strip()
                for item in proposal_items
                if str(item.get("origin_cluster_id", "")).strip()
            }
        ),
        "detector_profile_drafts": detector_profile_drafts,
        "workflow": {
            "mode": "offline_llm_assisted_then_deterministic_execute",
            "next_step": "Review detector_profile_drafts, then pass resulting JSON via validation.grounding_profile_paths.",
        },
    }
    if not detector_profile_drafts:
        normalized["llm_abstained"] = True
        normalized["workflow"]["next_step"] = (
            "LLM returned no reusable detector rules for this report. Review cluster_summaries/heuristic baseline "
            "or refine the unresolved report before promoting any profile."
        )
    return normalized


def _llm_messages_for_cluster(
    cluster: Dict[str, Any],
    heuristic_rule: Dict[str, Any],
    *,
    attempt: int = 1,
    last_error: str = "",
) -> List[Dict[str, str]]:
    system = (
        "You are refining deterministic runtime-grounding rules for one integration/file cluster.\n\n"
        "Goal:\n"
        "Produce the smallest reusable runtime-grounding rule for this cluster.\n"
        "Prefer file-specific or integration-specific rules over action-specific patches.\n"
        "If the provided heuristic rule is already precise enough, return decision=accept.\n"
        "If you can improve it conservatively, return decision=refine.\n"
        "If evidence is insufficient, return decision=abstain.\n\n"
        "Do not output global drafts. Only return one cluster decision.\n"
        "Do not emit two rules that differ only by origin_action_id if the same rule can be generalized to a file-specific or integration-specific runtime idiom.\n"
        "For read-like actions, do not use turn_on/turn_off/set_*/create_*/delete_* or other control handlers as runtime read detectors.\n"
        "Return JSON only."
    )
    user = {
        "task": "Refine one cluster rule into the minimum reusable deterministic runtime-grounding rule.",
        "prompt_version": PROMPT_VERSION,
        "cluster_summary": cluster,
        "heuristic_rule": heuristic_rule,
        "positive_prototypes": cluster.get("positive_prototypes", []),
        "negative_prototypes": cluster.get("negative_prototypes", []),
        "attempt": int(attempt),
        "validation_feedback": str(last_error or "").strip(),
        "requirements": [
            "Return a JSON object with decision and optional runtime_family.",
            "decision must be one of accept, refine, abstain.",
            "If decision=accept, runtime_family may be omitted and the heuristic rule will be used.",
            "If decision=refine, runtime_family must use schema_version m1_grounding_profile/v3 semantics.",
            "Prefer file-specific or integration-specific rules over action-specific patches.",
            "If evidence is insufficient, return decision=abstain.",
            "Use positive_prototypes and negative_prototypes as hard constraints, not as loose inspiration.",
            "If the heuristic rule can already generalize safely, prefer decision=accept over emitting a near-duplicate patch.",
            "why_not_more_general should explain why the rule is not widened further.",
            "If validation_feedback is non-empty, fix that exact issue and return a complete valid payload.",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, sort_keys=True)},
    ]


def _merge_runtime_family_with_heuristic_defaults(
    runtime_family: Dict[str, Any],
    heuristic_rule: Dict[str, Any],
) -> Dict[str, Any]:
    merged = dict(heuristic_rule)
    for key, value in runtime_family.items():
        if key == "binding_hints" and isinstance(value, dict):
            binding_hints = dict(heuristic_rule.get("binding_hints", {}))
            for hint_key, hint_value in value.items():
                if isinstance(hint_value, list):
                    if hint_value:
                        binding_hints[hint_key] = hint_value
                    continue
                if hint_value not in (None, "", {}):
                    binding_hints[hint_key] = hint_value
            merged["binding_hints"] = binding_hints
        elif isinstance(value, list):
            if value:
                merged[key] = value
        elif isinstance(value, dict):
            if value:
                merged[key] = value
        elif value not in (None, ""):
            merged[key] = value
    merged["schema_version"] = GROUNDING_PROFILE_SCHEMA_VERSION
    return merged


def _validate_runtime_family_against_cluster(
    runtime_family: Dict[str, Any],
    *,
    cluster: Dict[str, Any],
    heuristic_rule: Dict[str, Any],
) -> None:
    expected_integration = str(cluster.get("integration", "")).strip().lower()
    actual_integration = str(runtime_family.get("integration", "") or expected_integration).strip().lower()
    if expected_integration and actual_integration and actual_integration != expected_integration:
        raise DetectorBuilderLLMError(
            f"LLM cluster rule integration drifted from {expected_integration} to {actual_integration}"
        )

    expected_family = str(cluster.get("family", "")).strip().upper()
    actual_family = str(runtime_family.get("family", "")).strip().upper()
    if expected_family and actual_family and actual_family != expected_family:
        raise DetectorBuilderLLMError(
            f"LLM cluster rule family drifted from {expected_family} to {actual_family}"
        )

    expected_action_kind = str(cluster.get("action_kind", "")).strip().lower()
    actual_action_kind = str(runtime_family.get("action_kind", "") or expected_action_kind).strip().lower()
    if expected_action_kind and actual_action_kind and actual_action_kind != expected_action_kind:
        raise DetectorBuilderLLMError(
            f"LLM cluster rule action_kind drifted from {expected_action_kind} to {actual_action_kind}"
        )

    cluster_files = {str(item).strip() for item in cluster.get("bound_files", []) if str(item).strip()}
    cluster_file_basenames = {Path(item).name for item in cluster_files}
    rule_globs = [str(item).strip() for item in runtime_family.get("file_globs", []) if str(item).strip()]
    if cluster_file_basenames and rule_globs:
        def _glob_matches_cluster(glob: str) -> bool:
            if "*" in glob or "?" in glob:
                return expected_integration in {part.strip().lower() for part in Path(glob).parts if str(part).strip()}
            return Path(glob).name in cluster_file_basenames

        if not any(_glob_matches_cluster(glob) for glob in rule_globs):
            raise DetectorBuilderLLMError("LLM cluster rule file_globs do not match the cluster file family")

    cluster_actions = {str(item).strip() for item in cluster.get("generalizes_actions", cluster.get("action_ids", [])) if str(item).strip()}
    rule_actions = {str(item).strip() for item in runtime_family.get("generalizes_actions", []) if str(item).strip()}
    if rule_actions and cluster_actions and not rule_actions.issubset(cluster_actions):
        raise DetectorBuilderLLMError("LLM cluster rule references actions outside the current cluster")

    heuristic_required_signals = {
        str(item).strip()
        for item in heuristic_rule.get("required_path_signals", [])
        if str(item).strip()
    }
    rule_required_signals = {
        str(item).strip()
        for item in runtime_family.get("required_path_signals", [])
        if str(item).strip()
    }
    if heuristic_required_signals and rule_required_signals and not (rule_required_signals & heuristic_required_signals):
        raise DetectorBuilderLLMError("LLM cluster rule dropped the cluster's required path-signal family")
    if not any(str(item).strip() for item in runtime_family.get("function_name_patterns", []) if str(item).strip()) and not any(
        str(item).strip() for item in runtime_family.get("call_patterns", []) if str(item).strip()
    ):
        raise DetectorBuilderLLMError("LLM cluster rule is missing a positive selector")
    heuristic_required_context = {
        str(item).strip().lower()
        for item in heuristic_rule.get("required_context", [])
        if str(item).strip()
    }
    rule_required_context = {
        str(item).strip().lower()
        for item in runtime_family.get("required_context", [])
        if str(item).strip()
    }
    if {"runtime_path", "subscription_path"}.issubset(heuristic_required_context) and not {"runtime_path", "subscription_path"}.issubset(rule_required_context):
        raise DetectorBuilderLLMError("LLM cluster rule weakened a hybrid runtime/subscription context into a single-path context")

    heuristic_signal_prefixes = {
        str(item).split(":", 1)[0].strip().lower()
        for item in heuristic_rule.get("required_path_signals", [])
        if str(item).strip()
    }
    rule_signal_prefixes = {
        str(item).split(":", 1)[0].strip().lower()
        for item in runtime_family.get("required_path_signals", [])
        if str(item).strip()
    }
    if "update_callback_function" in heuristic_signal_prefixes and "update_callback_function" not in rule_signal_prefixes:
        raise DetectorBuilderLLMError("LLM cluster rule dropped the heuristic update-callback carrier")

    heuristic_functions = [
        str(item).strip().lower()
        for item in heuristic_rule.get("function_name_patterns", [])
        if str(item).strip()
    ]
    rule_functions = [
        str(item).strip().lower()
        for item in runtime_family.get("function_name_patterns", [])
        if str(item).strip()
    ]
    heuristic_has_non_wrapper = any(
        not any(marker in token for marker in _WRAPPER_LIKE_FUNCTION_TOKENS)
        for token in heuristic_functions
    )
    rule_all_wrapper = bool(rule_functions) and all(
        any(marker in token for marker in _WRAPPER_LIKE_FUNCTION_TOKENS)
        for token in rule_functions
    )
    if heuristic_has_non_wrapper and rule_all_wrapper:
        raise DetectorBuilderLLMError("LLM cluster rule regressed to wrapper-only positive selectors")


def _normalize_llm_cluster_decision(
    payload: Dict[str, Any],
    *,
    cluster: Dict[str, Any],
    heuristic_rule: Dict[str, Any],
    unresolved_report: Dict[str, Any],
) -> tuple[str, Dict[str, Any] | None]:
    if not isinstance(payload, dict):
        raise DetectorBuilderLLMError("LLM cluster payload must be a JSON object")
    decision = str(payload.get("decision", "") or "").strip().lower()
    if not decision and isinstance(payload.get("runtime_family"), dict):
        decision = "refine"
    if decision not in {"accept", "refine", "abstain"}:
        raise DetectorBuilderLLMError("LLM cluster payload must contain decision=accept|refine|abstain")
    if decision == "accept":
        return decision, dict(heuristic_rule)
    if decision == "abstain":
        return decision, None

    runtime_family = payload.get("runtime_family")
    if not isinstance(runtime_family, dict):
        raise DetectorBuilderLLMError("LLM cluster refine payload missing runtime_family")
    runtime_family = dict(runtime_family)
    for key in (
        "action_kind",
        "generalization_scope",
        "generalizes_actions",
        "origin_cluster_id",
        "file_globs",
        "required_runtime_roles",
        "forbidden_runtime_roles",
        "allow_accessor_fallback",
    ):
        if key not in runtime_family and key in heuristic_rule:
            runtime_family[key] = heuristic_rule.get(key)
    unresolved_action_index = {
        str(row.get("action_id", "")).strip(): row
        for row in unresolved_report.get("unresolved_actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    file_summary_index = {
        str(row.get("file_path", "")).strip(): row
        for row in unresolved_report.get("source_file_summaries", [])
        if isinstance(row, dict) and str(row.get("file_path", "")).strip()
    }
    normalized = _normalize_runtime_family(runtime_family, str(cluster.get("integration", "")).strip().lower(), 0)
    normalized = _merge_runtime_family_with_heuristic_defaults(normalized, heuristic_rule)
    _validate_runtime_family_against_cluster(normalized, cluster=cluster, heuristic_rule=heuristic_rule)
    refined = _refine_llm_runtime_family(normalized, unresolved_action_index, file_summary_index)
    if refined is None:
        return "abstain", None
    return "refine", refined


def _sleep_before_retry(attempt: int, retry_backoff_s: float) -> None:
    if retry_backoff_s <= 0:
        return
    delay = min(float(retry_backoff_s) * max(1, attempt), 5.0)
    time.sleep(delay)


def _request_cluster_decision_once(
    *,
    cluster: Dict[str, Any],
    heuristic_rule: Dict[str, Any],
    unresolved_report: Dict[str, Any],
    api_base_url: str,
    api_key: str,
    model: str,
    timeout_s: int,
    attempt: int,
    last_error: str,
) -> tuple[str, Dict[str, Any] | None, str]:
    messages = _llm_messages_for_cluster(cluster, heuristic_rule, attempt=attempt, last_error=last_error)
    request_payload = {
        "model": model,
        "temperature": 0.0,
        "messages": messages,
    }
    request_sha256 = _sha256_json(request_payload)
    req = request.Request(
        api_base_url,
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=int(timeout_s)) as resp:
            raw_response = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise DetectorBuilderLLMError(f"LLM HTTP error {exc.code}: {body[:500]}") from exc
    except error.URLError as exc:
        raise DetectorBuilderLLMError(f"LLM request failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise DetectorBuilderLLMError("LLM request failed: timeout") from exc
    except OSError as exc:
        raise DetectorBuilderLLMError(f"LLM request failed: {exc}") from exc

    try:
        response_payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise DetectorBuilderLLMError("LLM endpoint did not return JSON") from exc

    content = _content_from_chat_response(response_payload)
    decision, final_rule = _normalize_llm_cluster_decision(
        json.loads(_json_text_from_llm_content(content)),
        cluster=cluster,
        heuristic_rule=heuristic_rule,
        unresolved_report=unresolved_report,
    )
    return decision, final_rule, request_sha256


def generate_detector_profile_draft_with_llm(
    unresolved_report: Dict[str, Any],
    *,
    api_base_url: str,
    api_key: str,
    model: str = "gpt-5",
    timeout_s: int = DEFAULT_LLM_TIMEOUT_S,
    max_attempts: int = DEFAULT_LLM_MAX_ATTEMPTS,
    retry_backoff_s: float = DEFAULT_LLM_RETRY_BACKOFF_S,
) -> Dict[str, Any]:
    base_url = str(api_base_url or "").strip()
    key = str(api_key or "").strip()
    if not base_url:
        raise DetectorBuilderLLMError("api_base_url is required")
    if not key:
        raise DetectorBuilderLLMError("api_key is required")

    heuristic_draft = build_detector_profile_draft(unresolved_report)
    cluster_summaries = [
        row for row in heuristic_draft.get("cluster_summaries", [])
        if isinstance(row, dict)
    ]
    drafts_by_integration: Dict[str, Dict[str, Any]] = {}
    proposal_items: List[Dict[str, Any]] = []
    cluster_decisions: List[Dict[str, Any]] = []
    llm_abstained = True
    request_hashes: List[str] = []

    for cluster in cluster_summaries:
        heuristic_rule = cluster.get("heuristic_rule")
        if not isinstance(heuristic_rule, dict):
            cluster_decisions.append(
                {
                    "cluster_id": cluster.get("cluster_id"),
                    "decision": "report_only",
                    "reason": "no_heuristic_rule",
                }
            )
            continue
        promotability_score = int(cluster.get("promotability_score", 0) or 0)
        promotion_decision = str(cluster.get("promotion_decision", "")).strip().lower()
        if promotion_decision == "report_only":
            cluster_decisions.append(
                {
                    "cluster_id": cluster.get("cluster_id"),
                    "decision": "report_only",
                    "reason": "promotability_below_threshold",
                }
            )
            continue
        if promotion_decision == "promote":
            decision = "heuristic_accept"
            final_rule = dict(heuristic_rule)
            cluster_decisions.append(
                {
                    "cluster_id": cluster.get("cluster_id"),
                    "decision": decision,
                    "promotability_score": promotability_score,
                    "heuristic_rule_id": heuristic_rule.get("rule_id"),
                    "final_rule_id": final_rule.get("rule_id"),
                    "attempts": 0,
                    "llm_error": None,
                }
            )
            llm_abstained = False
            integration = str(final_rule.get("integration", "")).strip().lower() or str(cluster.get("integration", "")).strip().lower()
            draft = drafts_by_integration.setdefault(
                integration,
                {
                    "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                    "integration": integration,
                    "version": "draft_llm_v3",
                    "runtime_families": [],
                },
            )
            draft["runtime_families"].append(final_rule)
            proposal_items.append(
                {
                    "integration": integration,
                    "family": final_rule.get("family"),
                    "generalization_scope": final_rule.get("generalization_scope"),
                    "generalizes_actions": final_rule.get("generalizes_actions", []),
                    "origin_cluster_id": final_rule.get("origin_cluster_id"),
                    "proposal_rule_id": final_rule.get("rule_id"),
                    "origin_action_id": final_rule.get("origin_action_id"),
                    "llm_decision": decision,
                }
            )
            continue

        attempt = 1
        last_error = ""
        decision = "abstain"
        final_rule: Dict[str, Any] | None = None
        request_sha256 = ""
        while True:
            try:
                decision, final_rule, request_sha256 = _request_cluster_decision_once(
                    cluster=cluster,
                    heuristic_rule=heuristic_rule,
                    unresolved_report=unresolved_report,
                    api_base_url=base_url,
                    api_key=key,
                    model=model,
                    timeout_s=int(timeout_s),
                    attempt=attempt,
                    last_error=last_error,
                )
                request_hashes.append(request_sha256)
                break
            except DetectorBuilderLLMError as exc:
                last_error = str(exc)
                if max_attempts > 0 and attempt >= int(max_attempts):
                    if promotability_score >= HEURISTIC_PROMOTION_THRESHOLD:
                        decision = "heuristic_fallback"
                        final_rule = dict(heuristic_rule)
                    else:
                        decision = "abstain"
                        final_rule = None
                    cluster_decisions.append(
                        {
                            "cluster_id": cluster.get("cluster_id"),
                            "decision": decision,
                            "promotability_score": promotability_score,
                            "heuristic_rule_id": heuristic_rule.get("rule_id"),
                            "final_rule_id": final_rule.get("rule_id") if isinstance(final_rule, dict) else None,
                            "attempts": attempt,
                            "llm_error": last_error,
                        }
                    )
                    break
                _sleep_before_retry(attempt, float(retry_backoff_s))
                attempt += 1
                continue
        if cluster_decisions and cluster_decisions[-1].get("cluster_id") == cluster.get("cluster_id"):

            if not isinstance(final_rule, dict):
                continue
            llm_abstained = False
            integration = str(final_rule.get("integration", "")).strip().lower() or str(cluster.get("integration", "")).strip().lower()
            draft = drafts_by_integration.setdefault(
                integration,
                {
                    "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                    "integration": integration,
                    "version": "draft_llm_v3",
                    "runtime_families": [],
                },
            )
            draft["runtime_families"].append(final_rule)
            proposal_items.append(
                {
                    "integration": integration,
                    "family": final_rule.get("family"),
                    "generalization_scope": final_rule.get("generalization_scope"),
                    "generalizes_actions": final_rule.get("generalizes_actions", []),
                    "origin_cluster_id": final_rule.get("origin_cluster_id"),
                    "proposal_rule_id": final_rule.get("rule_id"),
                    "origin_action_id": final_rule.get("origin_action_id"),
                    "llm_decision": decision,
                }
            )
            continue
        if decision == "abstain" and promotability_score >= HEURISTIC_PROMOTION_THRESHOLD:
            decision = "heuristic_fallback"
            final_rule = dict(heuristic_rule)
        cluster_decisions.append(
            {
                "cluster_id": cluster.get("cluster_id"),
                "decision": decision,
                "promotability_score": promotability_score,
                "heuristic_rule_id": heuristic_rule.get("rule_id"),
                "final_rule_id": final_rule.get("rule_id") if isinstance(final_rule, dict) else None,
                "attempts": attempt,
                "llm_error": last_error or None,
            }
        )
        if not isinstance(final_rule, dict):
            continue
        llm_abstained = False
        integration = str(final_rule.get("integration", "")).strip().lower() or str(cluster.get("integration", "")).strip().lower()
        draft = drafts_by_integration.setdefault(
            integration,
            {
                "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                "integration": integration,
                "version": "draft_llm_v3",
                "runtime_families": [],
            },
        )
        draft["runtime_families"].append(final_rule)
        proposal_items.append(
            {
                "integration": integration,
                "family": final_rule.get("family"),
                "generalization_scope": final_rule.get("generalization_scope"),
                "generalizes_actions": final_rule.get("generalizes_actions", []),
                "origin_cluster_id": final_rule.get("origin_cluster_id"),
                "proposal_rule_id": final_rule.get("rule_id"),
                "origin_action_id": final_rule.get("origin_action_id"),
                "llm_decision": decision,
            }
        )

    detector_profile_drafts: List[Dict[str, Any]] = []
    for integration, draft in drafts_by_integration.items():
        runtime_families = _merge_runtime_families(
            [row for row in draft.get("runtime_families", []) if isinstance(row, dict)]
        )
        if not runtime_families:
            continue
        detector_profile_drafts.append(
            {
                "schema_version": GROUNDING_PROFILE_SCHEMA_VERSION,
                "integration": integration,
                "version": draft.get("version", "draft_llm_v3"),
                "runtime_families": runtime_families,
            }
        )

    source_report_sha256 = str(unresolved_report.get("source_report_sha256", "")).strip() or _sha256_json(unresolved_report)
    normalized = {
        "schema_version": DETECTOR_DRAFT_SCHEMA_VERSION,
        "generated_at": now_utc_iso(),
        "builder_version": BUILDER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "request_sha256": _sha256_json(sorted(request_hashes)),
        "source_report_version": str(unresolved_report.get("schema_version", "")),
        "source_report_sha256": source_report_sha256,
        "proposal_count": len(proposal_items),
        "proposal_items": proposal_items,
        "cluster_count": len(
            {
                str(item.get("origin_cluster_id", "")).strip()
                for item in proposal_items
                if str(item.get("origin_cluster_id", "")).strip()
            }
        ),
        "cluster_decisions": cluster_decisions,
        "detector_profile_drafts": detector_profile_drafts,
        "workflow": {
            "mode": "offline_llm_assisted_then_deterministic_execute",
            "next_step": "Review detector_profile_drafts, then pass resulting JSON via validation.grounding_profile_paths.",
        },
        "llm_request": {
            "base_url": "${FLOWEAVER_LLM_API_BASE_URL}",
            "model": model,
            "timeout_s": int(timeout_s),
            "max_attempts": int(max_attempts),
            "retry_backoff_s": float(retry_backoff_s),
            "mode": "per_cluster_refine",
        },
        "heuristic_baseline_proposal_count": int(heuristic_draft.get("proposal_count", 0) or 0),
    }
    if llm_abstained:
        normalized["llm_abstained"] = True
        normalized["workflow"]["next_step"] = (
            "LLM returned no promoted cluster rules. Review cluster_decisions, cluster_summaries, and heuristic rules "
            "before promoting any profile."
        )
    return normalized
