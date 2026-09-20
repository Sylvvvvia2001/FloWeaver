from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Set, Tuple

from dsl.contracts import OptimizationTarget, Phase
from dsl.io import load_json


GROUNDING_PROFILE_SCHEMA_VERSION = "m1_grounding_profile/v3"
GROUNDING_PROFILE_SCHEMA_VERSION_V1 = "m1_grounding_profile/v1"
GROUNDING_PROFILE_SCHEMA_VERSION_V2 = "m1_grounding_profile/v2"
GROUNDING_PROFILE_SCHEMA_VERSION_V3 = GROUNDING_PROFILE_SCHEMA_VERSION
SUPPORTED_GROUNDING_PROFILE_SCHEMA_VERSIONS = {
    GROUNDING_PROFILE_SCHEMA_VERSION_V1,
    GROUNDING_PROFILE_SCHEMA_VERSION_V2,
    GROUNDING_PROFILE_SCHEMA_VERSION_V3,
}
_DEFAULT_GROUNDING_PROFILE_ROOT = Path(__file__).resolve().parent.parent / "data" / "grounding_profiles"
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
_READ_CONTEXT_TOKENS = (
    "update",
    "refresh",
    "status",
    "poll",
    "fetch",
    "runtime",
    "read",
    "get",
)
_CONTROL_CONTEXT_TOKENS = (
    "turn_on",
    "turn_off",
    "set_",
    "write",
    "command",
    "send",
    "create_",
    "delete_",
)
_CONNECT_CONTEXT_TOKENS = ("connect", "reconnect")
_SUBSCRIPTION_CONTEXT_TOKENS = ("subscribe", "listener", "notify", "message", "track_state")
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
_STATE_ACCESSOR_HINT_TOKENS = ("_read_wrapper", "read_device_status", "current_state", "device_status", "state", "status", "value")
_STATE_WRITE_HINT_TOKENS = (
    "async_write_ha_state",
    "schedule_update_ha_state",
    "write_ha_state",
    "_handle_coordinator_update",
    "handle_coordinator_update",
    "_async_call_update_attrs",
)


@dataclass(frozen=True)
class CompiledGroundingRule:
    rule_id: str
    integration: str
    family: str
    action_kind: str
    generalization_scope: str
    specificity_rank: int
    generalizes_actions: Tuple[str, ...]
    origin_cluster_id: str | None
    file_globs: Tuple[str, ...]
    phase: str
    strength: str
    base_confidence: float
    emit_threshold: float
    required_context: frozenset[str]
    forbidden_context: frozenset[str]
    required_path_signals: frozenset[str]
    forbidden_path_signals: frozenset[str]
    required_runtime_roles: frozenset[str]
    forbidden_runtime_roles: frozenset[str]
    boost_imports: frozenset[str]
    boost_names: frozenset[str]
    call_patterns: Tuple[re.Pattern[str], ...]
    function_patterns: Tuple[re.Pattern[str], ...]
    negative_call_patterns: Tuple[re.Pattern[str], ...]
    negative_function_patterns: Tuple[re.Pattern[str], ...]
    preferred_action_kinds: frozenset[str]
    boost_target_tokens: frozenset[str]
    required_service_tokens: frozenset[str]
    allow_accessor_fallback: bool
    positive_prototypes: Tuple[dict[str, Any], ...]
    negative_prototypes: Tuple[dict[str, Any], ...]
    runtime_path_evidence: Tuple[str, ...]
    negative_evidence: Tuple[str, ...]
    why_not_setup: Tuple[str, ...]
    why_not_more_general: str
    source_file_paths: Tuple[str, ...]
    source_unresolved_action_ids: Tuple[str, ...]
    reviewer_status: str
    source_schema_version: str


def _specificity_rank(row: dict[str, Any], preferred_action_kinds: Set[str]) -> int:
    scope = str(row.get("generalization_scope", "action_specific") or "action_specific").strip().lower()
    rank = {
        "integration_specific": 3,
        "file_specific": 2,
        "action_specific": 1,
    }.get(scope, 1)
    if any(str(item).strip() for item in row.get("required_path_signals", []) if str(item).strip()):
        rank += 1
    if any(str(item).strip() for item in row.get("forbidden_runtime_roles", []) if str(item).strip()):
        rank += 1
    return rank


def _repo_relative_candidates(file_path: str) -> List[str]:
    path = Path(file_path).resolve()
    parts = list(path.parts)
    candidates = {path.as_posix().lower(), path.name.lower()}
    for width in (2, 3, 4):
        if len(parts) >= width:
            candidates.add("/".join(parts[-width:]).lower())
    return sorted(candidates)


def _compile_name_pattern(pattern: str) -> re.Pattern[str]:
    token = str(pattern or "").strip()
    if not token:
        return re.compile(r"^$")
    if "*" in token or "?" in token:
        return re.compile(fnmatch.translate(token), re.IGNORECASE)
    return re.compile(rf"^{re.escape(token)}$", re.IGNORECASE)


def _normalize_file_globs(raw: Sequence[Any], integration: str) -> Tuple[str, ...]:
    normalized: List[str] = []
    for item in raw:
        token = str(item or "").strip()
        if token:
            normalized.append(token)
    if normalized:
        return tuple(normalized)
    if integration:
        return (f"{integration}/*.py",)
    return ("*.py",)


def _normalize_string_list(values: Any) -> Tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    out: List[str] = []
    seen: Set[str] = set()
    for item in values:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return tuple(out)


def _infer_integrations(optimization_target: OptimizationTarget | None) -> Set[str]:
    integrations: Set[str] = set()
    if optimization_target is None:
        return integrations
    source_scope = optimization_target.source_scope if isinstance(optimization_target.source_scope, dict) else {}
    for item in source_scope.get("domains", []) if isinstance(source_scope.get("domains", []), list) else []:
        token = str(item or "").strip().lower()
        if token:
            integrations.add(token)
    for row in source_scope.get("file_bindings", []) if isinstance(source_scope.get("file_bindings", []), list) else []:
        if not isinstance(row, dict):
            continue
        token = str(row.get("integration", "") or "").strip().lower()
        if token:
            integrations.add(token)
    return integrations


def _explicit_profile_paths(optimization_target: OptimizationTarget | None) -> List[Path]:
    if optimization_target is None:
        return []
    validation = optimization_target.validation if isinstance(optimization_target.validation, dict) else {}
    constraints = optimization_target.constraints if isinstance(optimization_target.constraints, dict) else {}
    values = []
    for key in ("grounding_profile_paths", "detector_profile_paths"):
        for source in (validation, constraints):
            raw = source.get(key, [])
            if isinstance(raw, list):
                values.extend(str(item) for item in raw if str(item or "").strip())
            elif isinstance(raw, str) and raw.strip():
                values.append(raw)
    seen: Set[str] = set()
    out: List[Path] = []
    for item in values:
        resolved = str(Path(item).expanduser().resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        out.append(Path(resolved))
    return out


def _grounding_profile_root(optimization_target: OptimizationTarget | None) -> Path:
    if optimization_target is not None:
        validation = optimization_target.validation if isinstance(optimization_target.validation, dict) else {}
        constraints = optimization_target.constraints if isinstance(optimization_target.constraints, dict) else {}
        for source in (validation, constraints):
            raw = str(source.get("grounding_profile_root", "") or "").strip()
            if raw:
                return Path(raw).expanduser().resolve()
    return _DEFAULT_GROUNDING_PROFILE_ROOT


def discover_grounding_profile_paths(optimization_target: OptimizationTarget | None) -> List[Path]:
    paths = list(_explicit_profile_paths(optimization_target))
    root = _grounding_profile_root(optimization_target)
    integrations = _infer_integrations(optimization_target)
    seen = {str(path) for path in paths}
    for integration in sorted(integrations):
        candidate = root / f"{integration}.json"
        resolved = str(candidate.resolve())
        if candidate.exists() and resolved not in seen:
            seen.add(resolved)
            paths.append(candidate.resolve())
    return paths


def _iter_profile_rows(raw: Any) -> Iterable[dict[str, Any]]:
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(raw, dict):
        return
    families = raw.get("runtime_families", [])
    if isinstance(families, list):
        for item in families:
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("integration", raw.get("integration"))
                row.setdefault("version", raw.get("version"))
                row.setdefault("schema_version", raw.get("schema_version"))
                yield row


def _compile_rule(row: dict[str, Any], *, fallback_integration: str = "", schema_version: str = "") -> CompiledGroundingRule | None:
    family = str(row.get("family", "") or row.get("marker_type", "")).strip().upper()
    integration = str(row.get("integration", "") or fallback_integration).strip().lower()
    if not family:
        return None
    confidence = row.get("confidence", {}) if isinstance(row.get("confidence", {}), dict) else {}
    binding_hints = row.get("binding_hints", {}) if isinstance(row.get("binding_hints", {}), dict) else {}
    preferred_action_kinds = {
        str(item).strip().lower()
        for item in binding_hints.get("preferred_action_kinds", [])
        if str(item).strip()
    }
    reviewer_status = str(row.get("reviewer_status", "draft") or "draft").strip().lower()
    if reviewer_status in {"rejected", "disabled"}:
        return None
    rule_id = str(row.get("rule_id", "") or f"{integration}:{family}:{len(str(row))}").strip()
    action_kind = str(row.get("action_kind", "") or "").strip().lower()
    allow_accessor_fallback = bool(row.get("allow_accessor_fallback", False))
    generalization_scope = str(row.get("generalization_scope", "action_specific") or "action_specific").strip().lower()
    accessor_allowed_for_family = (
        (family == "CLOUD_STATUS_CALL" and (action_kind == "status" or "status" in preferred_action_kinds))
        or (family == "LOCAL_API_READ" and (action_kind == "get_state" or "get_state" in preferred_action_kinds))
    )
    if not (
        allow_accessor_fallback
        and generalization_scope == "file_specific"
        and accessor_allowed_for_family
    ):
        allow_accessor_fallback = False
    return CompiledGroundingRule(
        rule_id=rule_id,
        integration=integration,
        family=family,
        action_kind=action_kind,
        generalization_scope=generalization_scope,
        specificity_rank=_specificity_rank(row, preferred_action_kinds),
        generalizes_actions=_normalize_string_list(row.get("generalizes_actions", [])),
        origin_cluster_id=str(row.get("origin_cluster_id", "") or "").strip() or None,
        file_globs=_normalize_file_globs(row.get("file_globs", []), integration),
        phase=str(binding_hints.get("phase", row.get("phase", Phase.RUNTIME.value)) or Phase.RUNTIME.value).strip().upper(),
        strength=str(row.get("strength", "MEDIUM") or "MEDIUM").strip().upper(),
        base_confidence=float(confidence.get("base", row.get("base_confidence", 0.7)) or 0.7),
        emit_threshold=float(confidence.get("emit_threshold", row.get("emit_threshold", 0.7)) or 0.7),
        required_context=frozenset(str(item).strip().lower() for item in row.get("required_context", []) if str(item).strip()),
        forbidden_context=frozenset(str(item).strip().lower() for item in row.get("forbidden_context", []) if str(item).strip()),
        required_path_signals=frozenset(str(item).strip().lower() for item in row.get("required_path_signals", []) if str(item).strip()),
        forbidden_path_signals=frozenset(str(item).strip().lower() for item in row.get("forbidden_path_signals", []) if str(item).strip()),
        required_runtime_roles=frozenset(str(item).strip().lower() for item in row.get("required_runtime_roles", []) if str(item).strip()),
        forbidden_runtime_roles=frozenset(str(item).strip().lower() for item in row.get("forbidden_runtime_roles", []) if str(item).strip()),
        boost_imports=frozenset(str(item).strip().lower() for item in confidence.get("boost_if_imports", []) if str(item).strip()),
        boost_names=frozenset(str(item).strip().lower() for item in confidence.get("boost_if_names", []) if str(item).strip()),
        call_patterns=tuple(_compile_name_pattern(str(item)) for item in row.get("call_patterns", []) if str(item).strip()),
        function_patterns=tuple(_compile_name_pattern(str(item)) for item in row.get("function_name_patterns", row.get("function_patterns", [])) if str(item).strip()),
        negative_call_patterns=tuple(_compile_name_pattern(str(item)) for item in row.get("negative_call_patterns", []) if str(item).strip()),
        negative_function_patterns=tuple(_compile_name_pattern(str(item)) for item in row.get("negative_function_patterns", []) if str(item).strip()),
        preferred_action_kinds=frozenset(preferred_action_kinds),
        boost_target_tokens=frozenset(str(item).strip().lower() for item in binding_hints.get("boost_target_tokens", []) if str(item).strip()),
        required_service_tokens=frozenset(str(item).strip().lower() for item in binding_hints.get("required_service_tokens", []) if str(item).strip()),
        allow_accessor_fallback=allow_accessor_fallback,
        positive_prototypes=tuple(item for item in row.get("positive_prototypes", []) if isinstance(item, dict)),
        negative_prototypes=tuple(item for item in row.get("negative_prototypes", []) if isinstance(item, dict)),
        runtime_path_evidence=_normalize_string_list(row.get("runtime_path_evidence", [])),
        negative_evidence=_normalize_string_list(row.get("negative_evidence", [])),
        why_not_setup=_normalize_string_list(row.get("why_not_setup", [])),
        why_not_more_general=str(row.get("why_not_more_general", "") or "").strip(),
        source_file_paths=_normalize_string_list(row.get("source_file_paths", [])),
        source_unresolved_action_ids=_normalize_string_list(row.get("source_unresolved_action_ids", [])),
        reviewer_status=reviewer_status,
        source_schema_version=str(row.get("schema_version", "") or schema_version or GROUNDING_PROFILE_SCHEMA_VERSION_V1).strip(),
    )


def get_grounding_profile_root(optimization_target: OptimizationTarget | None = None) -> Path:

    return _grounding_profile_root(optimization_target)


def load_compiled_grounding_profiles(optimization_target: OptimizationTarget | None) -> tuple[List[CompiledGroundingRule], List[str]]:
    rules: List[CompiledGroundingRule] = []
    loaded_paths: List[str] = []
    for path in discover_grounding_profile_paths(optimization_target):
        if not path.exists():
            continue
        raw = load_json(path)
        if isinstance(raw, dict):
            schema = str(raw.get("schema_version", "") or "").strip()
            if schema and schema not in SUPPORTED_GROUNDING_PROFILE_SCHEMA_VERSIONS:
                continue
            integration = str(raw.get("integration", "") or "").strip().lower()
        else:
            schema = ""
            integration = ""
        rows = list(_iter_profile_rows(raw))
        compiled_any = False
        for row in rows:
            rule = _compile_rule(row, fallback_integration=integration, schema_version=schema)
            if rule is None:
                continue
            rules.append(rule)
            compiled_any = True
        if compiled_any:
            loaded_paths.append(str(path))
    rules.sort(key=lambda rule: (-int(rule.specificity_rank), rule.integration, rule.rule_id))
    return rules, loaded_paths


def rule_matches_file(rule: CompiledGroundingRule, file_path: str, file_integrations: Set[str]) -> bool:
    if rule.integration and file_integrations and rule.integration not in {item.lower() for item in file_integrations}:
        return False
    path_candidates = _repo_relative_candidates(file_path)
    for glob in rule.file_globs:
        token = str(glob).strip().lower()
        if not token:
            continue
        if any(fnmatch.fnmatch(candidate, token) for candidate in path_candidates):
            return True
    return False


def context_flags(fn_name: str, phase: str, call_tokens: Set[str]) -> Set[str]:
    fn_token = str(fn_name or "").strip().lower()
    phase_token = str(phase or Phase.RUNTIME.value).strip().upper()
    token_text = " ".join(sorted(str(item).strip().lower() for item in call_tokens if str(item).strip()))
    flags: Set[str] = set()
    if phase_token == Phase.RUNTIME.value:
        flags.add("runtime_path")
    if phase_token == Phase.SETUP.value:
        flags.add("setup_function")
    if phase_token == Phase.TEARDOWN.value:
        flags.add("teardown_function")
    if fn_token == "__init__":
        flags.add("dunder_init")
    if fn_token in _PROPERTY_GETTER_NAMES:
        flags.add("entity_property_getter")
    if phase_token == Phase.RUNTIME.value and any(token in f"{fn_token} {token_text}" for token in ("update", "refresh", "status", "poll", "fetch", "runtime", "read")):
        flags.add("runtime_update_path")
    if phase_token == Phase.RUNTIME.value and any(token in f"{fn_token} {token_text}" for token in ("connect", "reconnect")):
        flags.add("runtime_connect_path")
    if any(token in f"{fn_token} {token_text}" for token in ("subscribe", "listener", "notify", "message", "track_state")):
        flags.add("subscription_path")
    if fn_token.startswith("_"):
        flags.add("helper_wrapper")
    return flags


def _combined_signal_text(fn_name: str, call_tokens: Set[str]) -> str:
    fn_token = str(fn_name or "").strip().lower()
    token_text = " ".join(sorted(str(item).strip().lower() for item in call_tokens if str(item).strip()))
    return f"{fn_token} {token_text}".strip()


def _token_is_control_like(token: str) -> bool:
    value = str(token or "").strip().lower()
    if not value:
        return False
    if _token_is_state_write_like(value):
        return False
    return any(
        needle in value or value.startswith(needle)
        for needle in _CONTROL_CONTEXT_TOKENS
    )


def _token_is_state_write_like(token: str) -> bool:
    value = str(token or "").strip().lower()
    if not value:
        return False
    return any(
        value == hint or hint in value
        for hint in _STATE_WRITE_HINT_TOKENS
    )


def _token_is_read_like(token: str) -> bool:
    value = str(token or "").strip().lower()
    if not value or _token_is_control_like(value):
        return False
    return any(
        needle in value or value.startswith(f"{needle}_") or f".{needle}_" in value
        for needle in _READ_CONTEXT_TOKENS
    )


def _token_is_connect_like(token: str) -> bool:
    value = str(token or "").strip().lower()
    if not value:
        return False
    return any(needle in value for needle in _CONNECT_CONTEXT_TOKENS)


def _token_is_subscription_like(token: str) -> bool:
    value = str(token or "").strip().lower()
    if not value:
        return False
    return any(needle in value for needle in _SUBSCRIPTION_CONTEXT_TOKENS)


def infer_runtime_roles(fn_name: str, phase: str, call_tokens: Set[str]) -> Set[str]:
    fn_token = str(fn_name or "").strip().lower()
    phase_token = str(phase or Phase.RUNTIME.value).strip().upper()
    signal_text = _combined_signal_text(fn_name, call_tokens)
    roles: Set[str] = set()
    if phase_token == Phase.SETUP.value:
        roles.add("setup")
    if phase_token == Phase.TEARDOWN.value:
        roles.add("teardown")
    if fn_token in _PROPERTY_GETTER_NAMES:
        roles.add("property_getter")
    if any(token in fn_token for token in _UPDATE_CALLBACK_NAME_HINTS) and not _token_is_control_like(signal_text):
        roles.add("runtime_read")
    if _token_is_state_write_like(signal_text):
        roles.add("runtime_write")
    if _token_is_control_like(signal_text):
        roles.add("runtime_write")
    if _token_is_connect_like(signal_text):
        roles.add("runtime_connect")
    if _token_is_subscription_like(signal_text):
        roles.add("runtime_subscribe")
    if _token_is_read_like(signal_text):
        roles.add("runtime_read")
    if fn_token.startswith("_"):
        roles.add("helper")
    return roles


def infer_path_signals(fn_name: str, phase: str, call_tokens: Set[str]) -> Set[str]:
    fn_token = str(fn_name or "").strip().lower()
    phase_token = str(phase or Phase.RUNTIME.value).strip().upper()
    roles = infer_runtime_roles(fn_name, phase, call_tokens)
    signals: Set[str] = set()

    if phase_token == Phase.SETUP.value:
        signals.add(f"setup_function:{fn_token}")
    if phase_token == Phase.TEARDOWN.value:
        signals.add(f"teardown_function:{fn_token}")
    if "property_getter" in roles:
        signals.add(f"property_function:{fn_token}")
        signals.add(f"state_accessor_property:{fn_token}")
    if "runtime_write" in roles and _token_is_state_write_like(_combined_signal_text(fn_name, call_tokens)):
        signals.add(f"state_write_function:{fn_token}")
    if "runtime_write" in roles:
        signals.add(f"control_function:{fn_token}")
    if "runtime_read" in roles:
        signals.add(f"read_function:{fn_token}")
        if any(token in _combined_signal_text(fn_name, call_tokens) for token in ("update", "refresh", "poll", "fetch")) or any(
            token in fn_token for token in _UPDATE_CALLBACK_NAME_HINTS
        ):
            signals.add(f"update_callback_function:{fn_token}")
    if "runtime_connect" in roles:
        signals.add(f"connect_function:{fn_token}")
    if "runtime_subscribe" in roles:
        signals.add(f"subscription_function:{fn_token}")

    for token in {str(item).strip().lower() for item in call_tokens if str(item).strip()}:
        if _token_is_control_like(token):
            signals.add(f"control_call:{token}")
        if _token_is_state_write_like(token):
            signals.add(f"state_write_call:{token}")
        if _token_is_read_like(token):
            signals.add(f"read_call:{token}")
            if any(hint in token for hint in _STATE_ACCESSOR_HINT_TOKENS):
                signals.add(f"state_accessor_call:{token}")
            if any(hint in token for hint in ("update", "refresh", "poll", "fetch")):
                signals.add(f"refresh_call:{token}")
        if _token_is_connect_like(token):
            signals.add(f"connect_call:{token}")
        if _token_is_subscription_like(token):
            signals.add(f"subscription_call:{token}")
    return signals


def _required_path_signals_match(rule: CompiledGroundingRule, inferred_signals: Set[str]) -> bool:
    if not rule.required_path_signals:
        return True
    return bool(rule.required_path_signals & inferred_signals)


def _service_alignment_context_tokens(fn_name: str, call_tokens: Set[str]) -> Set[str]:
    values = {str(fn_name or "").strip().lower(), *{str(item).strip().lower() for item in call_tokens if str(item).strip()}}
    tokens: Set[str] = set()
    for value in values:
        if not value:
            continue
        tokens.add(value)
        for item in re.split(r"[.:]", value):
            item_n = str(item).strip().lower()
            if item_n:
                tokens.add(item_n)
        underscore_parts = [part for part in value.split("_") if part]
        for idx in range(len(underscore_parts)):
            suffix = "_".join(underscore_parts[idx:])
            if suffix:
                tokens.add(suffix)
    return tokens


def _required_service_tokens_match(
    rule: CompiledGroundingRule,
    fn_name: str,
    call_tokens: Set[str],
) -> bool:
    if not rule.required_service_tokens:
        return True
    return bool(rule.required_service_tokens & _service_alignment_context_tokens(fn_name, call_tokens))


def _semantic_runtime_read_fallback_allowed(
    rule: CompiledGroundingRule,
    flags: Set[str],
    inferred_roles: Set[str],
    inferred_signals: Set[str],
) -> bool:
    if "runtime_read" not in rule.required_runtime_roles:
        return False
    if not rule.required_path_signals:
        return False
    if not (rule.required_path_signals & inferred_signals):
        return False
    if "runtime_read" not in inferred_roles:
        return False
    if rule.forbidden_path_signals & inferred_signals:
        return False
    if not (flags & {"setup_function", "entity_property_getter", "helper_wrapper"}):
        return False
    return True


def _update_snapshot_runtime_read_fallback(
    rule: CompiledGroundingRule,
    inferred_signals: Set[str],
) -> bool:
    if "runtime_read" not in rule.required_runtime_roles:
        return False
    if not any(item.startswith("update_callback_function:") for item in inferred_signals):
        return False
    if not any(
        item.startswith("state_write_function:") or item.startswith("state_write_call:")
        for item in inferred_signals
    ):
        return False
    if any(
        item.startswith("control_call:") or item.startswith("awaited_control_call:")
        for item in inferred_signals
    ):
        return False
    return True


def rule_context_matches(rule: CompiledGroundingRule, fn_name: str, phase: str, call_tokens: Set[str]) -> bool:
    flags = context_flags(fn_name, phase, call_tokens)
    inferred_roles = infer_runtime_roles(fn_name, phase, call_tokens)
    inferred_signals = infer_path_signals(fn_name, phase, call_tokens)
    semantic_runtime_fallback = _semantic_runtime_read_fallback_allowed(
        rule,
        flags,
        inferred_roles,
        inferred_signals,
    )
    update_snapshot_fallback = _update_snapshot_runtime_read_fallback(rule, inferred_signals)

    effective_roles = set(inferred_roles)
    if semantic_runtime_fallback:
        effective_roles.discard("setup")
        effective_roles.discard("helper")
    if update_snapshot_fallback:
        effective_roles.discard("runtime_write")
        effective_roles.discard("helper")
    if rule.allow_accessor_fallback and "runtime_read" in rule.required_runtime_roles:
        effective_roles.discard("property_getter")
        effective_roles.discard("helper")
        if any(
            item.startswith("property_function:")
            or item.startswith("state_accessor_property:")
            or item.startswith("state_accessor_call:")
            for item in inferred_signals
        ):
            effective_roles.add("runtime_read")

    if rule.required_runtime_roles and not (rule.required_runtime_roles & effective_roles):
        return False
    if not _required_service_tokens_match(rule, fn_name, call_tokens):
        return False
    if not _required_path_signals_match(rule, inferred_signals):
        return False
    if rule.required_context:
        hybrid_runtime_subscription = {"runtime_path", "subscription_path"}.issubset(rule.required_context)
        if hybrid_runtime_subscription:
            remaining_required = set(rule.required_context) - {"runtime_path", "subscription_path"}
            if not (flags & {"runtime_path", "subscription_path"}):
                return False
            if remaining_required and not remaining_required.issubset(flags):
                return False
        elif not rule.required_context.issubset(flags):
            if not (
                rule.allow_accessor_fallback
                and flags & {"entity_property_getter", "runtime_path"}
                and "runtime_update_path" in rule.required_context
            ) and not (
                semantic_runtime_fallback
                and "runtime_update_path" in rule.required_context
            ):
                return False
    forbidden_flags = set(rule.forbidden_context)
    if rule.allow_accessor_fallback:
        forbidden_flags.discard("entity_property_getter")
    if semantic_runtime_fallback:
        forbidden_flags.discard("setup_function")
    if forbidden_flags and forbidden_flags & flags:
        return False
    effective_forbidden_signals = set(rule.forbidden_path_signals)
    if rule.allow_accessor_fallback:
        effective_forbidden_signals = {
            item
            for item in effective_forbidden_signals
            if not (item.startswith("state_accessor_property:") or item.startswith("property_function:"))
        }
    if rule.forbidden_runtime_roles and rule.forbidden_runtime_roles & effective_roles:
        return False
    if effective_forbidden_signals and effective_forbidden_signals & inferred_signals:
        return False
    return True


def rule_matches_function(rule: CompiledGroundingRule, fn_name: str) -> bool:
    token = str(fn_name or "").strip()
    if any(pattern.match(token) for pattern in rule.negative_function_patterns):
        return False
    if not rule.function_patterns:
        return False
    return any(pattern.match(token) for pattern in rule.function_patterns)


def rule_matches_call(rule: CompiledGroundingRule, call_tokens: Set[str], fn_name: str = "") -> bool:
    fn_token = str(fn_name or "").strip()
    if any(pattern.match(fn_token) for pattern in rule.negative_function_patterns):
        return False
    if rule.negative_call_patterns and any(
        pattern.match(token)
        for token in call_tokens
        for pattern in rule.negative_call_patterns
    ):
        return False
    if not rule.call_patterns:
        return False
    return any(pattern.match(token) for token in call_tokens for pattern in rule.call_patterns)


def rule_score(
    rule: CompiledGroundingRule,
    *,
    imported_modules: Set[str],
    fn_name: str,
    call_tokens: Set[str],
) -> tuple[float, List[str]]:
    score = float(rule.base_confidence)
    evidence: List[str] = [f"grounding_profile:{rule.integration or 'global'}:{rule.family}"]
    if rule.boost_imports and rule.boost_imports & {item.lower() for item in imported_modules}:
        score += 0.15
        evidence.append("grounding_profile:boost_imports")
    combined = {str(item).strip().lower() for item in call_tokens if str(item).strip()}
    fn_token = str(fn_name or "").strip().lower()
    combined.add(fn_token)
    if rule.boost_names and any(
        boost in token
        for boost in rule.boost_names
        for token in combined
    ):
        score += 0.10
        evidence.append("grounding_profile:boost_names")
    if rule.boost_target_tokens and any(
        boost in token
        for boost in rule.boost_target_tokens
        for token in combined
    ):
        score += 0.05
        evidence.append("grounding_profile:boost_target_tokens")
    return round(score, 4), evidence
