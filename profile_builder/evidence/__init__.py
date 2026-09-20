from __future__ import annotations

import ast
import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

from dsl.contracts import CodeEvidence, DocEvidence, TestEvidence
from dsl.io import dump_json


_DOC_MODALITY_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("MUST", re.compile(r"\bmust\b|\brequired\b|\bshall\b", re.IGNORECASE)),
    ("SHOULD", re.compile(r"\bshould\b|\brecommended\b", re.IGNORECASE)),
    ("MAY", re.compile(r"\bmay\b", re.IGNORECASE)),
]

_DOC_ANCHOR_PATTERNS = {
    "integration",
    "entity",
    "config entry",
    "config_entry",
    "subscribe",
    "unsubscribe",
    "unload",
    "remove",
    "setup",
    "update",
    "coordinator",
    "refresh",
    "state",
    "listener",
}
_DOC_LIFECYCLE_HINTS = {
    "setup",
    "unload",
    "remove",
    "subscribe",
    "unsubscribe",
    "coordinator",
    "refresh",
    "update",
}
_DOC_RULE_KINDS = {"NORMATIVE_SENTENCE", "LIFECYCLE_SENTENCE"}
_DOC_STRONG_SECTION_HINTS = {"requirement", "quality rule", "quality rules", "lifecycle", "requirements"}
_DOC_SOURCE_BOOSTS = {
    "bluetooth": 0.2,
    "integration_fetching_data": 0.15,
    "entity.md": 0.1,
    "reauthentication": 0.15,
    "diagnostics": 0.1,
    "system_health": 0.1,
}
_DOC_BLE_HINTS = {
    "bluetooth",
    "ble",
    "bleak",
    "gatt",
    "characteristic",
    "scanner",
    "adapter",
    "advertisement",
    "bledevice",
    "connectable",
    "disconnect",
    "connect",
    "notify",
}
_DOC_CLOUD_HINTS = {
    "cloud",
    "http",
    "request",
    "response",
    "status_code",
    "token",
    "oauth",
    "session",
    "client",
    "retry_after",
    "backoff",
    "rate limit",
    "ratelimit",
    "too many requests",
    "429",
    "batch",
    "bulk",
    "grouped",
    "fetch_all",
}
_DOC_CLOUD_PATH_HINTS = {
    "diagnostics",
    "system_health",
    "docs-data-update",
    "reauthentication",
    "reconfiguration",
}
_DOC_PROTOCOL_ANCHOR_FORBIDDEN_PATHS = {
    "creating_integration_manifest.md",
}
_DOC_PROTOCOL_ANCHOR_FORBIDDEN_SECTION_HINTS = {
    "brands",
    "branding",
    "logo",
    "manifest",
    "requirements",
    "owners",
    "dependencies",
    "documentation",
    "website",
}
_DOC_PROTOCOL_RUNTIME_ANCHORS = {
    "CLOUD_HTTP_CALL",
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_BATCH_CALL",
    "CLOUD_SESSION_REUSE",
    "CLOUD_TOKEN_REFRESH",
    "BLE_CONNECT",
    "BLE_GATT_OP",
    "BLE_DISCONNECT",
}
_DOC_RUNTIME_TO_POLICY = {
    "ENTRY_SETUP": "DOC_ENTRY_SETUP_POLICY",
    "ENTRY_UNLOAD": "DOC_ENTRY_UNLOAD_POLICY",
    "COORD_REFRESH": "DOC_COORD_REFRESH_POLICY",
    "STATE_WRITE": "DOC_STATE_UPDATE_POLICY",
    "SUBSCRIBE_PAIRING": "DOC_SUBSCRIBE_PAIRING_POLICY",
    "BLE_CONNECT": "DOC_BLE_CONNECTION_POLICY",
    "BLE_GATT_OP": "DOC_BLE_GATT_POLICY",
    "BLE_DISCONNECT": "DOC_BLE_DISCONNECT_POLICY",
    "CLOUD_HTTP_CALL": "DOC_CLOUD_API_POLICY",
    "CLOUD_BACKOFF_SLEEP": "DOC_RETRY_BACKOFF_POLICY",
    "CLOUD_BATCH_CALL": "DOC_CLOUD_BATCH_POLICY",
}
_DOC_POLICY_TO_RUNTIME = {value: key for key, value in _DOC_RUNTIME_TO_POLICY.items()}
_DOC_CLOUD_ACTION_HINTS = {
    "call",
    "request",
    "fetch",
    "post",
    "get",
    "put",
    "patch",
    "delete",
    "send",
}
_DOC_BLE_CONNECT_ACTION_HINTS = {"connect", "reconnect", "establish connection", "established", "establish"}
_DOC_BLE_DISCONNECT_ACTION_HINTS = {"disconnect", "close connection"}
_DOC_BLE_GATT_ACTION_HINTS = {
    "gatt",
    "notify",
    "read_gatt_char",
    "write_gatt_char",
    "characteristic",
    "read characteristic",
    "write characteristic",
}
_DOC_ACTION_LEXICON: Dict[str, set[str]] = {
    "CLOUD_HTTP_CALL": _DOC_CLOUD_ACTION_HINTS | {"api", "http"},
    "CLOUD_BACKOFF_SLEEP": {"backoff", "back off", "retry", "retry_after", "delay", "sleep", "cooldown", "jitter"},
    "CLOUD_BATCH_CALL": {"batch", "bulk", "grouped", "multiple", "fetch_all"},
    "BLE_CONNECT": {"connect", "reconnect", "establish", "established"},
    "BLE_GATT_OP": {"gatt", "characteristic", "notify", "read", "write"},
    "BLE_DISCONNECT": {"disconnect", "close"},
}

_CODE_PATTERNS: Dict[str, set[str]] = {
    "ENTRY_SETUP": {"async_setup_entry"},
    "ENTRY_UNLOAD": {"async_unload_entry", "async_remove_entry"},
    "STATE_WRITE": {"async_write_ha_state", "schedule_update_ha_state"},
    "COORD_REFRESH": {"async_config_entry_first_refresh", "_async_update_data", "_async_setup"},
    "SUBSCRIBE": {"dispatcher_connect", "async_track_state_change_event", "add_listener"},
    "UNSUBSCRIBE": {"unsubscribe", "unsub"},
}

_BLE_CONNECT_NAMES = {"connect", "establish_connection"}
_BLE_DISCONNECT_NAMES = {"disconnect", "close"}
_BLE_GATT_NAMES = {
    "read_gatt_char",
    "write_gatt_char",
    "start_notify",
    "stop_notify",
    "notify",
    "subscribe",
    "unsubscribe",
}
_BLE_DEVICE_ACTION_NAMES = {"update", "turn_on", "turn_off"}
_BLE_SCAN_NAMES = {"scan", "discover", "discover_services"}
_BLE_TIMEOUT_OR_RETRY_NAMES = {"sleep", "wait_for", "retry", "timeout"}
_BLE_GATT_HINT_SUBSTRINGS = {"gatt", "characteristic"}
_BLE_RUNTIME_PATTERNS = {"BLE_CONNECT", "BLE_DISCONNECT", "BLE_GATT_OP", "BLE_SCAN", "BLE_RETRY_OR_TIMEOUT"}

_CLOUD_HTTP_NAMES = {"request", "get", "post", "put", "patch", "delete"}
_CLOUD_TOKEN_NAMES = {"login", "authenticate", "auth", "token", "refresh", "refresh_token", "oauth"}
_CLOUD_SESSION_NAMES = {"clientsession", "session"}
_CLOUD_BATCH_NAMES = {"batch", "bulk", "batch_call", "batch_request", "grouped", "fetch_all", "update_devices", "send_commands"}
_CLOUD_BACKOFF_NAMES = {"backoff", "retry_after", "delay", "cooldown", "jitter"}
_CLOUD_STATUS_HINTS = {"status", "status_code", "httpstatus", "response.status", "response.status_code"}
_CLOUD_BATCH_ARG_HINTS = {"commands", "device_ids", "entity_ids", "ids", "devices"}
_CLOUD_SESSION_CREATE_NAMES = {"clientsession", "manager", "logincontrol"}
_CLOUD_SESSION_STORE_HINTS = {"runtime_data", "self.session", "self.client", "self.manager", "device_manager", "manager", "listener"}
_CLOUD_SESSION_CLOSE_HINTS = {"close", "unload", "stop", "remove_device_listener"}
_CLOUD_STRONG_CONTEXT_HINTS = {
    "aiohttp",
    "httpx",
    "requests",
    "oauth",
    "access_token",
    "refresh_token",
    "retry_after",
    "status_code",
    "http request",
    "http response",
    "api request",
    "cloud api",
    "clientsession",
    "rest api",
}

_RATE_LIMIT_EXCEPTION_HINTS = {"toomanyrequests", "ratelimit", "rate_limit", "429"}
_CLOUD_MODULE_HINTS = {"aiohttp", "httpx", "requests", "urllib3"}
_BLE_MODULE_HINTS = {"bleak", "bluetooth", "gatt", "switchbot"}
_LOCAL_API_READ_NAMES = {"request", "get", "async_get", "fetch", "async_fetch", "update", "async_update", "refresh", "async_refresh"}
_LOCAL_READ_CONTEXT_HINTS = {"read", "get", "fetch", "poll", "refresh", "update", "status", "state", "snapshot", "data"}
_LOCAL_CONTROL_CONTEXT_HINTS = {"set", "send", "command", "turn_on", "turn_off", "delete", "create", "remove", "write"}
_LOCAL_TRANSPORT_CONTEXT_HINTS = {"api", "client", "session", "http", "request", "websocket", "ws", "endpoint", "host", "url"}

_TEST_SETUP_CALLS = {
    "async_setup_entry",
    "async_setup",
}
_TEST_UNLOAD_CALLS = {
    "async_unload_entry",
    "async_unload",
    "async_remove_entry",
    "async_remove",
}
_TEST_RAISES_NAMES = {"raises"}
_TEST_ASSERT_METHODS = {"assert_called_once", "assert_called_once_with", "assert_not_called"}
_TEST_CLOUD_PATTERN_MAP = {
    "TEST_429_RETRY": "CLOUD_429_CHECK",
    "TEST_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
    "TEST_BATCH_CALL": "CLOUD_BATCH_CALL",
    "TEST_BATCH_UPDATE": "CLOUD_BATCH_CALL",
    "TEST_CLIENT_CALL_CONSTRAINT": "CLIENT_CALL_CONSTRAINT",
    "TEST_RATE_LIMIT": "CLOUD_429_CHECK",
    "TEST_HTTP_ERROR_RECOVERY": "CLOUD_BACKOFF_SLEEP",
}
_PROTOCOL_HINT_MAP = {
    "CLOUD_SESSION_STORE": "CLOUD_SESSION_HINT",
    "CLOUD_SESSION_CLOSE": "CLOUD_SESSION_HINT",
    "CLOUD_SESSION_USE": "CLOUD_SESSION_HINT",
    "CLOUD_BATCH_CALL": "CLOUD_BATCH_HINT",
    "CLOUD_BACKOFF_SLEEP": "CLOUD_BACKOFF_HINT",
    "CLOUD_HTTP_CALL": "CLOUD_API_HINT",
    "BLE_CONNECT": "BLE_CONNECTION_HINT",
    "BLE_GATT_OP": "BLE_GATT_HINT",
    "BLE_DISCONNECT": "BLE_CONNECTION_HINT",
}

_TYPED_ANCHOR_MAP = {
    "DOC_CONFIG_ENTRY_SETUP": "DOC_ENTRY_SETUP_POLICY",
    "DOC_CONFIG_ENTRY_UNLOAD": "DOC_ENTRY_UNLOAD_POLICY",
    "DOC_STATE_WRITE": "DOC_STATE_UPDATE_POLICY",
    "DOC_STATE_UPDATE_POLICY": "DOC_STATE_UPDATE_POLICY",
    "DOC_SUBSCRIBE_PAIR": "DOC_SUBSCRIBE_PAIRING_POLICY",
    "DOC_SUBSCRIPTION_POLICY": "DOC_SUBSCRIPTION_POLICY",
    "DOC_COORD_REFRESH": "DOC_COORD_REFRESH_POLICY",
    "DOC_ENTRY_SETUP_POLICY": "DOC_ENTRY_SETUP_POLICY",
    "DOC_ENTRY_UNLOAD_POLICY": "DOC_ENTRY_UNLOAD_POLICY",
    "DOC_COORD_REFRESH_POLICY": "DOC_COORD_REFRESH_POLICY",
    "DOC_SUBSCRIBE_PAIRING_POLICY": "DOC_SUBSCRIBE_PAIRING_POLICY",
    "DOC_BLE_CONNECT": "DOC_BLE_CONNECTION_POLICY",
    "DOC_BLE_GATT_OP": "DOC_BLE_GATT_POLICY",
    "DOC_BLE_DISCONNECT": "DOC_BLE_DISCONNECT_POLICY",
    "DOC_CLOUD_HTTP_CALL": "DOC_CLOUD_API_POLICY",
    "DOC_CLOUD_429_CHECK": "DOC_RETRY_BACKOFF_POLICY",
    "DOC_CLOUD_BACKOFF_SLEEP": "DOC_RETRY_BACKOFF_POLICY",
    "DOC_CLOUD_BATCH_CALL": "DOC_CLOUD_BATCH_POLICY",
    "DOC_CLOUD_SESSION_REUSE": "DOC_CLOUD_SESSION_POLICY",
    "DOC_CLOUD_TOKEN_REFRESH": "DOC_CLOUD_AUTH_POLICY",
    "ENTRY_SETUP": "ENTRY_SETUP",
    "ENTRY_UNLOAD": "ENTRY_UNLOAD",
    "STATE_WRITE": "STATE_WRITE",
    "COORD_REFRESH": "COORD_REFRESH",
    "SUBSCRIBE": "SUBSCRIBE",
    "UNSUBSCRIBE": "UNSUBSCRIBE",
    "BLE_CONNECT": "BLE_CONNECT",
    "BLE_GATT_OP": "BLE_GATT_OP",
    "BLE_DISCONNECT": "BLE_DISCONNECT",
    "BLE_SCAN": "BLE_SCAN",
    "BLE_RETRY_OR_TIMEOUT": "BLE_RETRY_OR_TIMEOUT",
    "BLE_REUSE_CONTEXT": "BLE_REUSE_CONTEXT",
    "BLE_OP": "BLE_OP",
    "LOCAL_API_READ": "LOCAL_API_READ",
    "CLOUD_HTTP_CALL": "CLOUD_HTTP_CALL",
    "CLOUD_TOKEN_REFRESH": "CLOUD_TOKEN_REFRESH",
    "CLOUD_429_CHECK": "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
    "CLOUD_BATCH_CALL": "CLOUD_BATCH_CALL",
    "CLOUD_SESSION_CREATE": "CLOUD_SESSION_CREATE",
    "CLOUD_SESSION_STORE": "CLOUD_SESSION_STORE",
    "CLOUD_SESSION_USE": "CLOUD_SESSION_USE",
    "CLOUD_SESSION_CLOSE": "CLOUD_SESSION_CLOSE",
    "CLOUD_SESSION_REUSE": "CLOUD_SESSION_REUSE",
    "TEST_ENTRY_SETUP": "TEST_ENTRY_SETUP",
    "TEST_ENTRY_UNLOAD": "TEST_ENTRY_UNLOAD",
    "TEST_CONFIG_ENTRY_NOT_READY": "TEST_ENTRY_SETUP",
    "TEST_AUTH_FAILED": "TEST_ENTRY_SETUP",
    "TEST_SUBSCRIBE_CLEANUP": "TEST_SUBSCRIBE_CLEANUP",
    "TEST_STATE_WRITE": "TEST_STATE_WRITE",
    "TEST_MANAGER_STOP": "TEST_ENTRY_UNLOAD",
    "TEST_429_RETRY": "TEST_RETRY_CALL",
    "TEST_BACKOFF_SLEEP": "TEST_BACKOFF_CALL",
    "TEST_BATCH_CALL": "TEST_BATCH_CALL",
    "TEST_BATCH_UPDATE": "TEST_BATCH_CALL",
    "TEST_NO_REDUNDANT_CALL": "TEST_NO_REDUNDANT_CALL",
    "TEST_EXPECTED_SINGLE_CALL": "TEST_EXPECTED_SINGLE_CALL",
    "TEST_EXPECTED_CLIENT_IDLE": "TEST_EXPECTED_CLIENT_IDLE",
    "TEST_CLIENT_CONNECT": "TEST_EXPECTED_SINGLE_CALL",
    "TEST_CLIENT_DISCONNECT": "TEST_EXPECTED_SINGLE_CALL",
    "TEST_CLIENT_CONFIG_UPDATE": "TEST_EXPECTED_SINGLE_CALL",
    "TEST_CLIENT_EMIT": "TEST_EXPECTED_SINGLE_CALL",
    "TEST_CALL_SUPPRESSION": "TEST_CALL_SUPPRESSION",
    "TEST_CLIENT_CALL_CONSTRAINT": "TEST_CLIENT_CALL_CONSTRAINT",
    "TEST_RATE_LIMIT": "TEST_RETRY_CALL",
    "TEST_HTTP_ERROR_RECOVERY": "TEST_BACKOFF_CALL",
}

_NORMATIVE_STRENGTH_SCORE = {"INFO": 0, "MAY": 1, "SHOULD": 2, "MUST": 3}
_SPECIFICITY_SCORE = {"GENERIC": 0, "FRAMEWORK": 1, "PROTOCOL": 2}
_SIGNAL_STRENGTH_SCORE = {"UNKNOWN": 0, "TEXT_WEAK": 1, "CALL_CHAIN_STRONG": 2, "AST_STRONG": 3}


def _stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


@dataclass
class EvidenceBank:
    docs: List[DocEvidence] = field(default_factory=list)
    code: List[CodeEvidence] = field(default_factory=list)
    tests: List[TestEvidence] = field(default_factory=list)

    def by_id(self) -> Dict[str, dict]:
        result: Dict[str, dict] = {}
        for doc in self.docs:
            result[doc.evidence_id] = {
                "kind": "doc",
                "source_path": doc.source_path,
                "line_no": doc.line_no,
                "modality": doc.modality,
                "text": doc.text,
                "typed_anchor": getattr(doc, "typed_anchor", "UNKNOWN"),
                "semantic_anchor": getattr(doc, "semantic_anchor", getattr(doc, "typed_anchor", "UNKNOWN")),
                "semantic_level": getattr(doc, "semantic_level", None),
                "section_title": doc.section_title,
                "is_code_block": doc.is_code_block,
                "is_table_row": doc.is_table_row,
                "doc_kind": doc.doc_kind,
                "normative_strength": doc.normative_strength,
                "specificity": doc.specificity,
                "source_type": doc.source_type,
                "source_commit": doc.source_commit,
                "extractor_version": doc.extractor_version,
                "normalization_flags": list(doc.normalization_flags),
                "confidence": doc.confidence,
            }
        for code in self.code:
            result[code.evidence_id] = {
                "kind": "code",
                "source_path": code.source_path,
                "line_no": code.line_no,
                "pattern": code.pattern,
                "typed_anchor": getattr(code, "typed_anchor", "UNKNOWN"),
                "effective_typed_anchor": getattr(code, "effective_typed_anchor", None),
                "semantic_anchor": getattr(code, "semantic_anchor", getattr(code, "effective_typed_anchor", None) or getattr(code, "typed_anchor", "UNKNOWN")),
                "semantic_level": getattr(code, "semantic_level", None),
                "frequency": code.frequency,
                "signal_strength": getattr(code, "signal_strength", "UNKNOWN"),
                "specificity": code.specificity,
                "source_type": code.source_type,
                "source_commit": code.source_commit,
                "extractor_version": code.extractor_version,
                "normalization_flags": list(code.normalization_flags),
                "confidence": code.confidence,
            }
        for test in self.tests:
            result[test.evidence_id] = {
                "kind": "test",
                "source_path": test.source_path,
                "line_no": test.line_no,
                "pattern": test.pattern,
                "typed_anchor": getattr(test, "typed_anchor", "UNKNOWN"),
                "protocol_hypothesis": getattr(test, "protocol_hypothesis", None),
                "semantic_anchor": getattr(test, "semantic_anchor", getattr(test, "typed_anchor", "UNKNOWN")),
                "semantic_level": getattr(test, "semantic_level", None),
                "behavior_category": getattr(test, "behavior_category", None),
                "frequency": test.frequency,
                "test_name": test.test_name,
                "assertion_kind": test.assertion_kind,
                "target_symbol": test.target_symbol,
                "specificity": test.specificity,
                "source_type": test.source_type,
                "source_commit": test.source_commit,
                "extractor_version": test.extractor_version,
                "normalization_flags": list(test.normalization_flags),
                "confidence": test.confidence,
            }
        return result


@dataclass
class EvidenceCandidate:
    modality: str
    source_path: str
    line_no: int
    typed_anchor: str
    pattern_id: str
    raw_text: str = ""
    symbol: str | None = None
    protocol_scope: str = "UNKNOWN"
    lifecycle_scope: str = "UNKNOWN"
    resource_scope: str = "UNKNOWN"
    confidence_prior: float = 0.5
    specificity: str = "GENERIC"
    normative_strength: str = "INFO"
    metadata: Dict[str, Any] = field(default_factory=dict)
    normalization_flags: List[str] = field(default_factory=list)
    frequency_hint: int = 1
    signal_strength: str = "UNKNOWN"
    effective_typed_anchor: str | None = None
    semantic_level: str | None = None


def iter_files(root: Path, suffixes: Iterable[str]) -> Iterable[Path]:
    if not root.exists():
        return []
    suffix_set = set(suffixes)
    return (path for path in root.rglob("*") if path.is_file() and path.suffix in suffix_set)


def _strip_markdown_prefix(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^[-*+]\s+", "", stripped)
    stripped = re.sub(r"^\d+\.\s+", "", stripped)
    return stripped.strip()


def _semantic_doc_text(text: str) -> str:
    normalized = _strip_markdown_prefix(text)
    normalized = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", normalized)
    normalized = re.sub(r"https?://\S+", "", normalized)
    normalized = normalized.replace("`", "")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def _is_markdown_table_row(text: str) -> bool:
    stripped = text.strip()
    if stripped.count("|") < 2:
        return False
    compact = stripped.replace(" ", "")
    if re.fullmatch(r"\|?[:\-|]+\|?", compact):
        return True
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return len(cells) >= 2 and any(cells)


def _looks_like_code_comment(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("#")


def _looks_like_prose_sentence(text: str) -> bool:
    candidate = _strip_markdown_prefix(text)
    if not candidate:
        return False
    if candidate.startswith("`") and candidate.endswith("`"):
        return False
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", candidate):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", candidate)
    if len(words) < 5:
        return False
    alpha_ratio = sum(ch.isalpha() for ch in candidate) / max(1, len(candidate))
    return alpha_ratio >= 0.45


def _contains_doc_anchor(text: str) -> bool:
    lowered = _semantic_doc_text(text)
    return any(anchor in lowered for anchor in _DOC_ANCHOR_PATTERNS)


def _classify_doc_kind(text: str) -> str:
    lowered = _semantic_doc_text(text)
    if "example" in lowered or "for example" in lowered:
        return "EXAMPLE_SENTENCE"
    if any(hint in lowered for hint in _DOC_LIFECYCLE_HINTS):
        return "LIFECYCLE_SENTENCE"
    return "NORMATIVE_SENTENCE"


def _doc_normative_strength(modality: str, path: Path, section_title: str | None) -> str:
    section = (section_title or "").lower()
    if modality == "MUST":
        strength = "MUST"
    elif modality == "SHOULD":
        strength = "SHOULD"
    elif modality == "MAY":
        strength = "MAY"
    else:
        strength = "INFO"
    if strength != "MUST" and any(hint in section for hint in _DOC_STRONG_SECTION_HINTS):
        strength = "MUST" if strength == "SHOULD" else strength
    if strength != "MUST" and "quality" in str(path).lower() and "rule" in str(path).lower():
        strength = "MUST" if strength == "SHOULD" else strength
    return strength


def _semantic_anchor_for_candidate(candidate: EvidenceCandidate) -> str:
    return str(candidate.effective_typed_anchor or candidate.typed_anchor or "UNKNOWN")


def _doc_specificity_for_anchor(typed_anchor: str, text: str, path: Path, section_title: str | None) -> str:
    lowered = _semantic_doc_text(text)
    path_lower = str(path).lower()
    section_lower = str(section_title or "").lower()
    anchor = str(typed_anchor or "").upper()
    protocol_terms = {
        "ble",
        "bluetooth",
        "gatt",
        "api",
        "http",
        "session",
        "batch",
        "retry_after",
        "backoff",
        "connect",
        "disconnect",
        "mqtt",
        "zeroconf",
        "ssdp",
        "dhcp",
        "oauth",
        "token",
        "429",
    }
    if anchor in {
        "DOC_CLOUD_API_POLICY",
        "DOC_BLE_CONNECTION_POLICY",
        "DOC_BLE_GATT_POLICY",
        "DOC_BLE_DISCONNECT_POLICY",
        "DOC_CLOUD_BATCH_POLICY",
        "DOC_RETRY_BACKOFF_POLICY",
        "DOC_CLOUD_SESSION_POLICY",
        "DOC_CLOUD_AUTH_POLICY",
        "DOC_SUBSCRIPTION_POLICY",
    } and any(term in lowered for term in protocol_terms):
        return "PROTOCOL"
    if anchor in {
        "DOC_ENTRY_SETUP_POLICY",
        "DOC_ENTRY_UNLOAD_POLICY",
        "DOC_COORD_REFRESH_POLICY",
        "DOC_SUBSCRIBE_PAIRING_POLICY",
        "DOC_STATE_UPDATE_POLICY",
        "DOC_ENTITY_PROPERTY_POLICY",
        "DOC_ENTITY_NAMING_POLICY",
        "DOC_AVAILABILITY_POLICY",
        "DOC_DIAGNOSTICS_POLICY",
        "DOC_CONFIG_ENTRY_MUTATION",
        "DOC_REAUTH_FLOW",
        "DOC_RECONFIGURE_FLOW",
        "DOC_MIGRATION",
        "DOC_DISCOVERY_POLICY",
        "DOC_SHARED_RESOURCE",
        "DOC_UNIQUE_ID_POLICY",
    }:
        return "FRAMEWORK"
    if any(token in section_lower for token in {"entity", "system health", "diagnostics", "config entry", "migration", "reauth"}):
        return "FRAMEWORK"
    if any(token in lowered for token in {"async_write_ha_state", "schedule_update_ha_state", "config entry", "config_entry"}):
        return "FRAMEWORK"
    if any(token in path_lower for token in {"entity.md", "config_entries", "runtime-data", "docs-data-update", "integration_fetching_data"}):
        return "FRAMEWORK"
    return "GENERIC"


def _code_specificity(pattern: str) -> str:
    if pattern.startswith("BLE_") or pattern.startswith("CLOUD_") or pattern.startswith("LOCAL_"):
        return "PROTOCOL"
    if pattern in {"STATE_WRITE", "ENTRY_SETUP", "ENTRY_UNLOAD", "SUBSCRIBE", "UNSUBSCRIBE", "COORD_REFRESH"}:
        return "FRAMEWORK"
    return "GENERIC"


def _test_specificity(pattern: str) -> str:
    if pattern in _TEST_CLOUD_PATTERN_MAP:
        return "PROTOCOL"
    if pattern in {"TEST_ENTRY_SETUP", "TEST_ENTRY_UNLOAD", "TEST_SUBSCRIBE_CLEANUP", "TEST_STATE_WRITE", "TEST_MANAGER_STOP"}:
        return "FRAMEWORK"
    return "GENERIC"


def _test_behavior_category(pattern: str) -> str | None:
    normalized = str(pattern).strip().upper()
    mapping = {
        "TEST_ENTRY_SETUP": "LIFECYCLE_SETUP",
        "TEST_ENTRY_UNLOAD": "LIFECYCLE_UNLOAD",
        "TEST_CONFIG_ENTRY_NOT_READY": "SETUP_RETRY",
        "TEST_AUTH_FAILED": "AUTH_FAILURE",
        "TEST_STATE_WRITE": "STATE_OBSERVATION",
        "TEST_SUBSCRIBE_CLEANUP": "SUBSCRIPTION_CLEANUP",
        "TEST_MANAGER_STOP": "MANAGER_STOP",
        "TEST_RETRY_CALL": "RETRY_BEHAVIOR",
        "TEST_BACKOFF_SLEEP": "RETRY_BEHAVIOR",
        "TEST_BACKOFF_CALL": "RETRY_BEHAVIOR",
        "TEST_BATCH_CALL": "BATCH_BEHAVIOR",
        "TEST_CLIENT_CONNECT": "CLIENT_CONNECT",
        "TEST_CLIENT_DISCONNECT": "CLIENT_DISCONNECT",
        "TEST_CLIENT_CONFIG_UPDATE": "CLIENT_CONFIG_UPDATE",
        "TEST_CLIENT_EMIT": "CLIENT_EMIT",
        "TEST_EXPECTED_SINGLE_CALL": "CALL_COUNT_EXPECTATION",
        "TEST_EXPECTED_CLIENT_IDLE": "CLIENT_IDLE",
        "TEST_CALL_SUPPRESSION": "CALL_SUPPRESSION",
        "TEST_NO_REDUNDANT_CALL": "NO_REDUNDANT_CALL",
        "TEST_CLIENT_CALL_CONSTRAINT": "CLIENT_CONSTRAINT",
        "TEST_RATE_LIMIT": "RETRY_BEHAVIOR",
        "TEST_HTTP_ERROR_RECOVERY": "ERROR_RECOVERY",
    }
    return mapping.get(normalized)


def _typed_anchor_for_pattern(pattern_id: str) -> str:
    normalized = str(pattern_id).strip().upper()
    return _TYPED_ANCHOR_MAP.get(normalized, normalized)


def _infer_protocol_scope(typed_anchor: str) -> str:
    if typed_anchor.startswith("BLE_"):
        return "BLE"
    if typed_anchor.startswith("CLOUD_"):
        return "CLOUD"
    if typed_anchor.startswith("LOCAL_"):
        return "LOCAL_API"
    if typed_anchor in {"DOC_BLE_CONNECTION_POLICY", "DOC_BLE_GATT_POLICY", "DOC_BLE_DISCONNECT_POLICY"}:
        return "BLE"
    if typed_anchor in {
        "DOC_CLOUD_API_POLICY",
        "DOC_CLOUD_BATCH_POLICY",
        "DOC_RETRY_BACKOFF_POLICY",
        "DOC_CLOUD_SESSION_POLICY",
        "DOC_CLOUD_AUTH_POLICY",
    }:
        return "CLOUD"
    if typed_anchor in {
        "DOC_ENTRY_SETUP_POLICY",
        "DOC_ENTRY_UNLOAD_POLICY",
        "DOC_COORD_REFRESH_POLICY",
        "DOC_SUBSCRIBE_PAIRING_POLICY",
        "DOC_STATE_UPDATE_POLICY",
    }:
        return "HA"
    if typed_anchor in {"ENTRY_SETUP", "ENTRY_UNLOAD", "STATE_WRITE", "COORD_REFRESH", "SUBSCRIBE", "UNSUBSCRIBE", "SUBSCRIBE_PAIRING"}:
        return "HA"
    return "UNKNOWN"


def _infer_lifecycle_scope(typed_anchor: str) -> str:
    if typed_anchor in {"ENTRY_SETUP"}:
        return "SETUP"
    if typed_anchor in {"TEST_ENTRY_SETUP"}:
        return "SETUP"
    if typed_anchor in {"ENTRY_UNLOAD"}:
        return "TEARDOWN"
    if typed_anchor in {"TEST_ENTRY_UNLOAD"}:
        return "TEARDOWN"
    if typed_anchor in {"STATE_WRITE", "COORD_REFRESH", "SUBSCRIBE", "UNSUBSCRIBE", "SUBSCRIBE_PAIRING"}:
        return "RUNTIME"
    if typed_anchor in {"TEST_STATE_WRITE", "TEST_SUBSCRIBE_CLEANUP", "TEST_RETRY_CALL", "TEST_BACKOFF_CALL", "TEST_BATCH_CALL"}:
        return "RUNTIME"
    if typed_anchor.startswith("BLE_") or typed_anchor.startswith("CLOUD_") or typed_anchor.startswith("LOCAL_"):
        return "RUNTIME"
    if typed_anchor.startswith("DOC_"):
        return "POLICY"
    return "UNKNOWN"


def _infer_resource_scope(typed_anchor: str, symbol: str | None = None, raw_text: str = "") -> str:
    symbol_text = str(symbol or "").lower()
    raw_lower = str(raw_text).lower()
    if typed_anchor in {"ENTRY_SETUP", "ENTRY_UNLOAD"}:
        return "manager"
    if typed_anchor in {"DOC_ENTRY_SETUP_POLICY", "DOC_ENTRY_UNLOAD_POLICY"}:
        return "manager_policy"
    if typed_anchor in {"SUBSCRIBE", "UNSUBSCRIBE", "SUBSCRIBE_PAIRING"}:
        return "listener"
    if typed_anchor in {"DOC_SUBSCRIBE_PAIRING_POLICY", "DOC_SUBSCRIPTION_POLICY"}:
        return "listener_policy"
    if typed_anchor == "STATE_WRITE":
        return "entity_state"
    if typed_anchor == "DOC_STATE_UPDATE_POLICY":
        return "entity_state_policy"
    if typed_anchor in {"COORD_REFRESH"}:
        return "coordinator"
    if typed_anchor == "DOC_COORD_REFRESH_POLICY":
        return "coordinator_policy"
    if typed_anchor in {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_REUSE_CONTEXT", "BLE_SCAN", "BLE_RETRY_OR_TIMEOUT", "BLE_OP"}:
        return "connection"
    if typed_anchor in {"DOC_BLE_CONNECTION_POLICY", "DOC_BLE_GATT_POLICY", "DOC_BLE_DISCONNECT_POLICY"}:
        return "connection_policy"
    if typed_anchor == "LOCAL_API_READ":
        return "local_request"
    if typed_anchor in {"CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP"}:
        return "cloud_rate_limit"
    if typed_anchor == "DOC_RETRY_BACKOFF_POLICY":
        return "cloud_rate_limit_policy"
    if typed_anchor in {"CLOUD_SESSION_CREATE", "CLOUD_SESSION_STORE", "CLOUD_SESSION_USE", "CLOUD_SESSION_CLOSE", "CLOUD_SESSION_REUSE"}:
        return "cloud_session"
    if typed_anchor in {"DOC_CLOUD_SESSION_POLICY", "DOC_CLOUD_AUTH_POLICY"}:
        return "cloud_session_policy"
    if typed_anchor in {"CLOUD_BATCH_CALL"}:
        return "cloud_batch"
    if typed_anchor == "DOC_CLOUD_BATCH_POLICY":
        return "cloud_batch_policy"
    if typed_anchor in {"CLOUD_HTTP_CALL", "CLOUD_TOKEN_REFRESH"}:
        return "cloud_request"
    if typed_anchor == "DOC_CLOUD_API_POLICY":
        return "cloud_request_policy"
    if typed_anchor in {
        "TEST_EXPECTED_SINGLE_CALL",
        "TEST_CALL_SUPPRESSION",
        "TEST_EXPECTED_CLIENT_IDLE",
        "TEST_NO_REDUNDANT_CALL",
        "TEST_ENTRY_SETUP",
        "TEST_ENTRY_UNLOAD",
        "TEST_STATE_WRITE",
        "TEST_CLIENT_CALL_CONSTRAINT",
        "TEST_SUBSCRIBE_CLEANUP",
        "TEST_RETRY_CALL",
        "TEST_BACKOFF_CALL",
        "TEST_BATCH_CALL",
    }:
        return "test_observation"
    if typed_anchor in {"CLOUD_SESSION_HINT", "CLOUD_BATCH_HINT", "CLOUD_BACKOFF_HINT", "CLOUD_API_HINT"}:
        return "cloud_hint"
    if typed_anchor in {"BLE_CONNECTION_HINT", "BLE_GATT_HINT"}:
        return "connection_hint"
    if "listener" in symbol_text or "listener" in raw_lower:
        return "listener"
    if "session" in symbol_text or "client" in symbol_text or "session" in raw_lower:
        return "cloud_session"
    if "gatt" in symbol_text or "ble" in symbol_text:
        return "connection"
    return "generic"


def _candidate_score(candidate: EvidenceCandidate) -> tuple[int, int, float, int]:
    return (
        _SIGNAL_STRENGTH_SCORE.get(str(candidate.signal_strength).upper(), 0),
        _NORMATIVE_STRENGTH_SCORE.get(str(candidate.normative_strength).upper(), 0),
        _SPECIFICITY_SCORE.get(str(candidate.specificity).upper(), 0),
        float(candidate.confidence_prior),
        -int(candidate.line_no),
    )


def _merge_candidate_metadata(group: List[EvidenceCandidate]) -> Dict[str, Any]:
    representative = max(group, key=_candidate_score)
    merged = dict(representative.metadata)
    pattern_ids = sorted({str(item.pattern_id) for item in group if str(item.pattern_id).strip()})
    support_lines = sorted({int(item.line_no) for item in group})
    support_symbols = sorted({str(item.symbol) for item in group if item.symbol})
    merged["candidate_count"] = len(group)
    merged["pattern_ids"] = pattern_ids
    merged["support_lines"] = support_lines
    if support_symbols:
        merged["support_symbols"] = support_symbols
    signal_strengths = sorted({str(item.signal_strength).upper() for item in group if str(item.signal_strength).strip()})
    if signal_strengths:
        merged["support_signal_strengths"] = signal_strengths
    return merged


def _merge_candidate_flags(group: List[EvidenceCandidate], typed_anchor: str) -> List[str]:
    flags = {
        flag
        for item in group
        for flag in item.normalization_flags
        if str(flag).strip()
    }
    flags.add(f"typed_anchor:{typed_anchor}")
    flags.add(f"candidate_fused:{len(group)}")
    return sorted(flags)


def _fuse_candidate_group(group: List[EvidenceCandidate]) -> EvidenceCandidate:
    representative = max(group, key=_candidate_score)
    total_frequency = sum(max(1, int(item.frequency_hint)) for item in group)
    fused_confidence = min(
        0.99,
        max(float(item.confidence_prior) for item in group) + min(0.1, 0.02 * max(0, len(group) - 1)),
    )
    metadata = _merge_candidate_metadata(group)
    flags = _merge_candidate_flags(group, representative.typed_anchor)
    effective_typed_anchor = representative.effective_typed_anchor
    if representative.modality == "CODE" and representative.typed_anchor in _PROTOCOL_HINT_MAP:
        group_flags = {
            flag
            for item in group
            for flag in item.normalization_flags
            if str(flag).strip()
        }
        strengths = {str(item.signal_strength).upper() for item in group if str(item.signal_strength).strip()}
        hint_anchor = _PROTOCOL_HINT_MAP[representative.typed_anchor]
        if strengths <= {"TEXT_WEAK"}:
            fused_confidence = min(fused_confidence, 0.55)
            flags.append("protocol_anchor_downgraded:text_only")
            flags.append("typed_anchor_downgraded:hint")
            effective_typed_anchor = hint_anchor
        elif "TEXT_WEAK" in strengths and "assignment_match_v1" in group_flags and "CALL_CHAIN_STRONG" not in strengths:
            fused_confidence = min(fused_confidence, 0.62)
            flags.append("protocol_anchor_downgraded:assignment_plus_text")
            flags.append("typed_anchor_downgraded:hint")
            effective_typed_anchor = hint_anchor
        metadata["strongest_signal_strength"] = max(
            strengths or {"UNKNOWN"},
            key=lambda item: _SIGNAL_STRENGTH_SCORE.get(item, 0),
        )
        if effective_typed_anchor:
            metadata["semantic_class"] = "HINT"
    flags.append(f"semantic_anchor:{effective_typed_anchor or representative.typed_anchor}")
    return replace(
        representative,
        line_no=min(item.line_no for item in group),
        confidence_prior=fused_confidence,
        metadata=metadata,
        normalization_flags=sorted(set(flags)),
        frequency_hint=total_frequency,
        effective_typed_anchor=effective_typed_anchor,
    )


def _candidate_key_doc(candidate: EvidenceCandidate) -> tuple[str, str, str]:
    section_title = str(candidate.metadata.get("section_title", "") or "")
    return (candidate.source_path, section_title, candidate.typed_anchor)


def _candidate_key_code(candidate: EvidenceCandidate) -> tuple[str, str, str, str]:
    symbol = str(candidate.metadata.get("function_name") or candidate.symbol or "").strip() or f"line:{candidate.line_no}"
    return (candidate.source_path, candidate.typed_anchor, symbol, candidate.resource_scope)


def _candidate_key_test(candidate: EvidenceCandidate) -> tuple[str, str, str, str]:
    test_name = str(candidate.metadata.get("test_name", "") or "")
    symbol = str(candidate.symbol or "").strip() or f"line:{candidate.line_no}"
    return (candidate.source_path, test_name, candidate.typed_anchor, symbol)


def _semantic_level_for_candidate(candidate: EvidenceCandidate) -> str:
    if candidate.semantic_level:
        return str(candidate.semantic_level)
    if candidate.modality == "DOC":
        return "POLICY"
    if candidate.modality == "TEST":
        return "BEHAVIOR"
    effective_anchor = str(candidate.effective_typed_anchor or candidate.typed_anchor or "UNKNOWN")
    if effective_anchor.endswith("_HINT") or candidate.metadata.get("semantic_class") == "HINT":
        return "HINT"
    return "RUNTIME"


def _candidate_to_doc_evidence(candidate: EvidenceCandidate) -> DocEvidence:
    section_title = candidate.metadata.get("section_title")
    doc_kind = str(candidate.metadata.get("doc_kind", "NORMATIVE_SENTENCE"))
    modality = str(candidate.metadata.get("modality", "INFO"))
    evidence_id = _stable_id("DOC", f"{candidate.source_path}:{candidate.line_no}:{section_title or ''}:{candidate.typed_anchor}")
    return DocEvidence(
        evidence_id=evidence_id,
        source_path=candidate.source_path,
        line_no=candidate.line_no,
        modality=modality,
        text=candidate.raw_text,
        typed_anchor=candidate.typed_anchor,
        section_title=str(section_title) if section_title else None,
        is_code_block=False,
        is_table_row=False,
        doc_kind=doc_kind,
        normative_strength=candidate.normative_strength,
        specificity=candidate.specificity,
        normalization_flags=list(candidate.normalization_flags),
        confidence=candidate.confidence_prior,
        semantic_level=_semantic_level_for_candidate(candidate),
        semantic_anchor=_semantic_anchor_for_candidate(candidate),
    )


def _candidate_to_code_evidence(candidate: EvidenceCandidate) -> CodeEvidence:
    evidence_id = _stable_id(
        "CODE",
        f"{candidate.source_path}:{candidate.line_no}:{candidate.typed_anchor}:{candidate.symbol or ''}:{candidate.resource_scope}",
    )
    return CodeEvidence(
        evidence_id=evidence_id,
        source_path=candidate.source_path,
        pattern=candidate.pattern_id,
        line_no=candidate.line_no,
        typed_anchor=candidate.typed_anchor,
        frequency=max(1, int(candidate.frequency_hint)),
        specificity=candidate.specificity,
        normalization_flags=list(candidate.normalization_flags),
        confidence=candidate.confidence_prior,
        signal_strength=str(candidate.signal_strength).upper() or "UNKNOWN",
        effective_typed_anchor=str(candidate.effective_typed_anchor) if candidate.effective_typed_anchor else None,
        semantic_level=_semantic_level_for_candidate(candidate),
        semantic_anchor=_semantic_anchor_for_candidate(candidate),
    )


def _candidate_to_test_evidence(candidate: EvidenceCandidate) -> TestEvidence:
    test_name = candidate.metadata.get("test_name")
    assertion_kind = str(candidate.metadata.get("assertion_kind", "call"))
    target_symbol = candidate.symbol or candidate.metadata.get("target_symbol")
    protocol_hypothesis = candidate.metadata.get("protocol_hypothesis")
    evidence_id = _stable_id(
        "TEST",
        f"{candidate.source_path}:{candidate.line_no}:{test_name or ''}:{candidate.typed_anchor}:{target_symbol or ''}",
    )
    return TestEvidence(
        evidence_id=evidence_id,
        source_path=candidate.source_path,
        pattern=candidate.pattern_id,
        test_name=str(test_name) if test_name else None,
        line_no=candidate.line_no,
        assertion_kind=assertion_kind,
        target_symbol=str(target_symbol) if target_symbol else None,
        typed_anchor=candidate.typed_anchor,
        frequency=max(1, int(candidate.frequency_hint)),
        specificity=candidate.specificity,
        normalization_flags=list(candidate.normalization_flags),
        confidence=candidate.confidence_prior,
        protocol_hypothesis=str(protocol_hypothesis) if protocol_hypothesis else None,
        semantic_level=_semantic_level_for_candidate(candidate),
        semantic_anchor=_semantic_anchor_for_candidate(candidate),
        behavior_category=str(candidate.metadata.get("behavior_category")) if candidate.metadata.get("behavior_category") else None,
    )


def _fuse_candidates(
    candidates: List[EvidenceCandidate],
    key_fn,
) -> List[EvidenceCandidate]:
    buckets: Dict[tuple, List[EvidenceCandidate]] = {}
    for candidate in candidates:
        buckets.setdefault(key_fn(candidate), []).append(candidate)
    fused = [_fuse_candidate_group(group) for group in buckets.values()]
    fused.sort(key=lambda item: (item.source_path, item.line_no, item.pattern_id, item.symbol or ""))
    return fused


def _contains_any_phrase(text: str, phrases: Set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _contains_term(text: str, term: str) -> bool:
    pattern = r"\b" + re.escape(term).replace(r"\ ", r"\s+") + r"\b"
    return re.search(pattern, text) is not None


def _contains_any_term(text: str, terms: Set[str]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _has_action_lexicon(text: str, anchor: str) -> bool:
    return _contains_any_term(text, _DOC_ACTION_LEXICON.get(anchor, set()))


def _doc_protocol_anchor_forbidden(source_path: str | Path | None, section_title: str | None) -> bool:
    path_lower = str(source_path or "").lower()
    filename = Path(str(source_path or "")).name.lower() if source_path else ""
    section_lower = str(section_title or "").lower()
    if filename in _DOC_PROTOCOL_ANCHOR_FORBIDDEN_PATHS:
        return True
    if "integration_quality_scale" in path_lower and any(hint in section_lower for hint in _DOC_PROTOCOL_ANCHOR_FORBIDDEN_SECTION_HINTS):
        return True
    return False


def _protocol_anchor_allowed(
    anchor: str,
    text: str,
    source_path: str | Path | None,
    section_title: str | None,
    *,
    ble_context: bool,
    cloud_context: bool,
) -> bool:
    if anchor in _DOC_PROTOCOL_RUNTIME_ANCHORS and _doc_protocol_anchor_forbidden(source_path, section_title):
        return False
    if anchor.startswith("BLE_"):
        return ble_context and _has_action_lexicon(text, anchor)
    if anchor in {"CLOUD_HTTP_CALL", "CLOUD_BACKOFF_SLEEP", "CLOUD_BATCH_CALL"}:
        return cloud_context and _has_action_lexicon(text, anchor)
    if anchor == "CLOUD_429_CHECK":
        return (
            cloud_context
            and _contains_any_term(text, {"429", "too many requests", "rate limit", "ratelimit"})
            and _has_action_lexicon(text, "CLOUD_BACKOFF_SLEEP")
        )
    if anchor == "CLOUD_TOKEN_REFRESH":
        return cloud_context and _contains_any_term(text, {"token", "oauth", "authenticate", "refresh token", "refresh_token"})
    if anchor == "CLOUD_SESSION_REUSE":
        return cloud_context and any(token in text for token in {"session", "client"}) and any(
            token in text for token in {"reuse", "reused", "persistent", "share", "shared"}
        )
    return True


def _doc_pattern_id_for_anchor(typed_anchor: str) -> str:
    mapping = {
        "ENTRY_SETUP": "DOC_CONFIG_ENTRY_SETUP",
        "ENTRY_UNLOAD": "DOC_CONFIG_ENTRY_UNLOAD",
        "DOC_ENTRY_SETUP_POLICY": "DOC_CONFIG_ENTRY_SETUP",
        "DOC_ENTRY_UNLOAD_POLICY": "DOC_CONFIG_ENTRY_UNLOAD",
        "STATE_WRITE": "DOC_STATE_WRITE",
        "DOC_STATE_UPDATE_POLICY": "DOC_STATE_UPDATE_POLICY",
        "SUBSCRIBE_PAIRING": "DOC_SUBSCRIBE_PAIR",
        "DOC_SUBSCRIBE_PAIRING_POLICY": "DOC_SUBSCRIBE_PAIR",
        "COORD_REFRESH": "DOC_COORD_REFRESH",
        "DOC_COORD_REFRESH_POLICY": "DOC_COORD_REFRESH",
        "DOC_BLE_CONNECTION_POLICY": "DOC_BLE_CONNECT",
        "DOC_BLE_GATT_POLICY": "DOC_BLE_GATT_OP",
        "DOC_BLE_DISCONNECT_POLICY": "DOC_BLE_DISCONNECT",
        "DOC_CLOUD_API_POLICY": "DOC_CLOUD_HTTP_CALL",
        "DOC_CLOUD_AUTH_POLICY": "DOC_CLOUD_TOKEN_REFRESH",
        "DOC_RETRY_BACKOFF_POLICY": "DOC_CLOUD_BACKOFF_SLEEP",
        "DOC_CLOUD_BATCH_POLICY": "DOC_CLOUD_BATCH_CALL",
        "DOC_CLOUD_SESSION_POLICY": "DOC_CLOUD_SESSION_REUSE",
        "DOC_UNIQUE_ID_POLICY": "DOC_UNIQUE_ID_POLICY",
        "DOC_DISCOVERY_POLICY": "DOC_DISCOVERY_POLICY",
        "DOC_SHARED_RESOURCE": "DOC_SHARED_RESOURCE",
        "DOC_SUBSCRIPTION_POLICY": "DOC_SUBSCRIPTION_POLICY",
        "DOC_CONFIG_ENTRY_MUTATION": "DOC_CONFIG_ENTRY_MUTATION",
        "DOC_RETRY_POLICY": "DOC_RETRY_POLICY",
        "DOC_AVAILABILITY_POLICY": "DOC_AVAILABILITY_POLICY",
        "DOC_ENTITY_PROPERTY_POLICY": "DOC_ENTITY_PROPERTY_POLICY",
        "DOC_ENTITY_NAMING_POLICY": "DOC_ENTITY_NAMING_POLICY",
        "DOC_TRANSLATION_POLICY": "DOC_TRANSLATION_POLICY",
        "DOC_DIAGNOSTICS_POLICY": "DOC_DIAGNOSTICS_POLICY",
        "DOC_REAUTH_FLOW": "DOC_REAUTH_FLOW",
        "DOC_RECONFIGURE_FLOW": "DOC_RECONFIGURE_FLOW",
        "DOC_MIGRATION": "DOC_MIGRATION",
        "DOC_MANIFEST_META": "DOC_MANIFEST_META",
        "DOC_NORMATIVE": "DOC_NORMATIVE",
    }
    if typed_anchor in mapping:
        return mapping[typed_anchor]
    if typed_anchor.startswith("DOC_"):
        return typed_anchor
    return f"DOC_{typed_anchor}"


def _infer_doc_typed_anchor(text: str, source_path: str | Path | None = None, section_title: str | None = None) -> str:
    lowered = _semantic_doc_text(text)
    path_lower = str(source_path or "").lower()
    section_lower = str(section_title or "").lower()
    ble_context = _contains_any_phrase(lowered, _DOC_BLE_HINTS) or any(hint in path_lower for hint in {"bluetooth", "ble"})
    cloud_context = _contains_any_phrase(lowered, _DOC_CLOUD_HINTS) or any(hint in path_lower for hint in _DOC_CLOUD_PATH_HINTS)

    if any(token in lowered for token in {"brand", "branding", "logo", "brands repository", "virtual integration", "manifest file"}):
        return "DOC_MANIFEST_META"
    if _doc_protocol_anchor_forbidden(source_path, section_title) and any(
        token in lowered for token in {"website", "documentation", "api", "requirements", "dependency", "owner", "owners"}
    ):
        return "DOC_MANIFEST_META"
    if any(token in lowered for token in {"reauth", "reauthentication"}):
        return "DOC_REAUTH_FLOW"
    if any(token in lowered for token in {"reconfigure", "reconfiguration"}):
        return "DOC_RECONFIGURE_FLOW"
    if any(token in lowered for token in {"migrate", "migration"}):
        return "DOC_MIGRATION"
    if "unique id" in lowered:
        return "DOC_UNIQUE_ID_POLICY"
    if any(token in lowered for token in {"discovery step", "discovered", "discoveries", "discover"}):
        return "DOC_DISCOVERY_POLICY"
    if ble_context and any(token in lowered for token in {"scanner", "bledevice", "address"}) and any(
        token in lowered for token in {"share", "shared", "wrapper", "avoid the overhead", "additional scanner", "nearest configured"}
    ):
        return "DOC_SHARED_RESOURCE"
    if "async_update_entry" in lowered or ("config entry" in lowered and any(token in lowered for token in {"mutated directly", "modified directly", "update entry"})):
        return "DOC_CONFIG_ENTRY_MUTATION"
    if "retry" in lowered and any(
        token in lowered for token in {"configentrynotready", "avoid spamming", "should not log", "rely on the logic", "non-debug messages"}
    ):
        return "DOC_RETRY_POLICY"
    if any(token in path_lower for token in {"system_health", "diagnostics"}) and any(
        token in lowered for token in {"diagnostic", "diagnostics", "system health", "repair issue", "troubleshoot", "troubleshooting"}
    ):
        return "DOC_DIAGNOSTICS_POLICY"
    if any(token in lowered for token in {"unavailable", "standby", "unresponsive", "cannot be controlled"}):
        return "DOC_AVAILABILITY_POLICY"
    if any(token in section_lower for token in {"generic properties", "advanced properties", "system properties", "entity class or instance attributes", "entity description", "excluding state attributes"}):
        return "DOC_ENTITY_PROPERTY_POLICY"
    if any(token in lowered for token in {"capability_attributes", "supported_features", "device_class", "_entity_component_unrecorded_attributes", "_unrecorded_attributes"}):
        return "DOC_ENTITY_PROPERTY_POLICY"
    if any(token in section_lower for token in {"has_entity_name", "name property"}):
        return "DOC_ENTITY_NAMING_POLICY"
    if "entity" in lowered and "name" in lowered and any(token in lowered for token in {"capital letter", "proper noun", "combination of the device name"}):
        return "DOC_ENTITY_NAMING_POLICY"
    if any(token in lowered for token in {"translated states", "translation keys"}) or "icon translations" in section_lower:
        return "DOC_TRANSLATION_POLICY"

    if "subscribe" in lowered and "unsubscribe" in lowered:
        return "SUBSCRIBE_PAIRING"
    if any(token in lowered for token in {"config entry", "config_entry"}) and "setup" in lowered:
        return "ENTRY_SETUP"
    if any(token in lowered for token in {"unload", "teardown", "remove"}):
        return "ENTRY_UNLOAD"
    if "coordinator" in lowered and any(token in lowered for token in {"refresh", "update"}):
        return "COORD_REFRESH"
    if any(token in lowered for token in {"async_write_ha_state", "schedule_update_ha_state"}):
        return "STATE_WRITE"
    if "async_update" in lowered or "async update" in lowered:
        return "STATE_WRITE"
    if (
        any(token in lowered for token in {"poll", "polling", "update interval"})
        and any(token in lowered for token in {"entity", "state", "property", "properties"})
    ):
        return "STATE_WRITE"
    if (
        "property" in lowered
        and "memory" in lowered
        and any(token in lowered for token in {"return", "returns", "handled inside async_update", "handled in async_update"})
    ):
        return "STATE_WRITE"
    if "state" in lowered and any(token in lowered for token in {"write", "update", "entity"}):
        return "STATE_WRITE"
    if _protocol_anchor_allowed("BLE_GATT_OP", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context) and _contains_any_term(lowered, _DOC_BLE_GATT_ACTION_HINTS):
        return "DOC_BLE_GATT_POLICY"
    if _protocol_anchor_allowed("BLE_DISCONNECT", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context) and _contains_any_term(lowered, _DOC_BLE_DISCONNECT_ACTION_HINTS):
        return "DOC_BLE_DISCONNECT_POLICY"
    if _protocol_anchor_allowed("BLE_CONNECT", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context) and _contains_any_term(lowered, _DOC_BLE_CONNECT_ACTION_HINTS):
        return "DOC_BLE_CONNECTION_POLICY"
    if _protocol_anchor_allowed("CLOUD_429_CHECK", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context):
        return "DOC_RETRY_BACKOFF_POLICY"
    if _protocol_anchor_allowed("CLOUD_BACKOFF_SLEEP", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context) and any(token in lowered for token in {"backoff", "retry_after", "cooldown", "delay", "jitter", "back off"}):
        return "DOC_RETRY_BACKOFF_POLICY"
    if _protocol_anchor_allowed("CLOUD_BATCH_CALL", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context) and any(token in lowered for token in {"batch", "bulk", "grouped", "fetch_all"}):
        return "DOC_CLOUD_BATCH_POLICY"
    if _protocol_anchor_allowed("CLOUD_SESSION_REUSE", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context):
        return "DOC_CLOUD_SESSION_POLICY"
    if _protocol_anchor_allowed("CLOUD_TOKEN_REFRESH", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context):
        return "DOC_CLOUD_AUTH_POLICY"
    if _protocol_anchor_allowed("CLOUD_HTTP_CALL", lowered, source_path, section_title, ble_context=ble_context, cloud_context=cloud_context):
        return "DOC_CLOUD_API_POLICY"
    if "subscribe" in lowered:
        return "DOC_SUBSCRIPTION_POLICY"
    if "unsubscribe" in lowered:
        return "DOC_SUBSCRIPTION_POLICY"
    if "setup" in lowered:
        return "ENTRY_SETUP"
    if "refresh" in lowered:
        return "COORD_REFRESH"
    if "lifecycle" in section_lower or "requirement" in section_lower:
        return "DOC_NORMATIVE"
    if ble_context or cloud_context:
        return "DOC_NORMATIVE"
    return "DOC_NORMATIVE"


def collect_doc_candidates(docs_root: str | Path) -> List[EvidenceCandidate]:
    candidates: List[EvidenceCandidate] = []
    root = Path(docs_root)

    for path in iter_files(root, {".md", ".txt", ".rst"}):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_code_block = False
        current_section: str | None = None
        for line_no, line in enumerate(lines, start=1):
            text = line.strip()
            if not text:
                continue
            if re.match(r"^(```|~~~)", text):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            if re.match(r"^#{1,6}\s+\S", text):
                current_section = text.lstrip("#").strip() or current_section
                continue
            is_table_row = _is_markdown_table_row(text)
            if is_table_row or _looks_like_code_comment(text):
                continue
            if not _looks_like_prose_sentence(text):
                continue
            modality = None
            for name, pattern in _DOC_MODALITY_PATTERNS:
                if pattern.search(text):
                    modality = name
                    break
            if not modality:
                continue
            if not _contains_doc_anchor(text):
                continue
            doc_kind = _classify_doc_kind(text)
            if doc_kind not in _DOC_RULE_KINDS:
                continue
            typed_anchor = _infer_doc_typed_anchor(text, path, current_section)
            runtime_hypothesis = typed_anchor if typed_anchor in _DOC_RUNTIME_TO_POLICY else None
            if runtime_hypothesis:
                typed_anchor = _DOC_RUNTIME_TO_POLICY[runtime_hypothesis]
            runtime_hypothesis = runtime_hypothesis or _DOC_POLICY_TO_RUNTIME.get(typed_anchor)
            pattern_id = _doc_pattern_id_for_anchor(typed_anchor)
            normalized_anchor = _typed_anchor_for_pattern(pattern_id)
            candidates.append(
                EvidenceCandidate(
                    modality="DOC",
                    source_path=str(path),
                    line_no=line_no,
                    typed_anchor=normalized_anchor,
                    pattern_id=pattern_id,
                    raw_text=text,
                    protocol_scope=_infer_protocol_scope(normalized_anchor),
                    lifecycle_scope=_infer_lifecycle_scope(normalized_anchor),
                    resource_scope=_infer_resource_scope(normalized_anchor, raw_text=text),
                    confidence_prior=0.9 if doc_kind == "LIFECYCLE_SENTENCE" else 0.85,
                    specificity=_doc_specificity_for_anchor(normalized_anchor, text, path, current_section),
                    normative_strength=_doc_normative_strength(modality, path, current_section),
                    metadata={
                        "section_title": current_section,
                        "doc_kind": doc_kind,
                        "modality": modality,
                        "runtime_hypothesis": runtime_hypothesis,
                    },
                    normalization_flags=[
                        "doc_candidate_v1",
                        "doc_prose_filter_v1",
                        *([f"runtime_hypothesis:{runtime_hypothesis}"] if runtime_hypothesis else []),
                    ],
                )
            )

    return candidates


def fuse_doc_candidates(candidates: List[EvidenceCandidate]) -> List[DocEvidence]:
    fused = _fuse_candidates(candidates, _candidate_key_doc)
    return [_candidate_to_doc_evidence(candidate) for candidate in fused]


def extract_doc_evidence(docs_root: str | Path) -> List[DocEvidence]:
    return fuse_doc_candidates(collect_doc_candidates(docs_root))


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Attribute):
        return fn.attr
    if isinstance(fn, ast.Name):
        return fn.id
    return ""


def _expr_chain(expr: ast.AST) -> str:
    if isinstance(expr, ast.Attribute):
        left = _expr_chain(expr.value)
        return f"{left}.{expr.attr}" if left else expr.attr
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Call):
        return _expr_chain(expr.func)
    if isinstance(expr, ast.Await):
        return _expr_chain(expr.value)
    return ""


def _call_chain(node: ast.Call) -> str:
    return _expr_chain(node.func)


def _collect_import_aliases(tree: ast.AST) -> tuple[Dict[str, str], Dict[str, str], Set[str]]:
    module_aliases: Dict[str, str] = {}
    symbol_aliases: Dict[str, str] = {}
    imported_modules: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                imported_modules.add(module)
                if alias.asname:
                    module_aliases[alias.asname] = module
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                imported_modules.add(module)
            for alias in node.names:
                local_name = alias.asname or alias.name
                symbol_aliases[local_name] = alias.name
                if module:
                    symbol_aliases[f"{local_name}.__module__"] = module

    return module_aliases, symbol_aliases, imported_modules


def _has_ancestor(node: ast.AST, parent_map: Dict[int, ast.AST], kinds: tuple[type[ast.AST], ...]) -> bool:
    cursor = parent_map.get(id(node))
    while cursor is not None:
        if isinstance(cursor, kinds):
            return True
        cursor = parent_map.get(id(cursor))
    return False


def _enclosing_function_name(node: ast.AST, parent_map: Dict[int, ast.AST]) -> str | None:
    cursor = node
    while cursor is not None:
        if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cursor.name
        cursor = parent_map.get(id(cursor))
    return None


def _function_ranges(tree: ast.AST) -> List[Tuple[int, int, str]]:
    ranges: List[Tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = int(getattr(node, "lineno", 0))
            end = int(getattr(node, "end_lineno", start))
            ranges.append((start, end, node.name))
    ranges.sort(key=lambda item: (item[1] - item[0], item[0]))
    return ranges


def _function_name_for_line(line_no: int, ranges: List[Tuple[int, int, str]]) -> str | None:
    for start, end, name in ranges:
        if start <= line_no <= end:
            return name
    return None


def _name_tokens(call: ast.Call, symbol_aliases: Dict[str, str], module_aliases: Dict[str, str]) -> Set[str]:
    chain = _call_chain(call)
    root = chain.split(".")[0] if chain else ""
    callee = _call_name(call)
    tokens = {callee.lower(), chain.lower()}
    if root in symbol_aliases:
        tokens.add(str(symbol_aliases[root]).lower())
    if root in module_aliases:
        tokens.add(str(module_aliases[root]).lower())
    return {token for token in tokens if token}


def _token_substr_hit(tokens: Set[str], hints: Set[str]) -> bool:
    for token in tokens:
        for hint in hints:
            if hint and hint in token:
                return True
    return False


def _local_text_window(lines: List[str], line_no: int, radius: int = 3) -> str:
    start = max(0, line_no - 1 - radius)
    end = min(len(lines), line_no + radius)
    return "\n".join(lines[start:end]).lower()


def _match_protocol_call_patterns(
    call: ast.Call,
    symbol_aliases: Dict[str, str],
    module_aliases: Dict[str, str],
    imported_modules: Set[str],
    parent_map: Dict[int, ast.AST],
    api_scope: str = "unknown",
) -> Set[str]:
    tokens = _name_tokens(call, symbol_aliases, module_aliases)
    module_tokens = {token.lower() for module in imported_modules for token in module.split(".") if token}
    enclosing_fn = (_enclosing_function_name(call, parent_map) or "").lower()
    matches: Set[str] = set()

    ble_module_context = any(module in _BLE_MODULE_HINTS for module in module_tokens)
    cloud_module_context = api_scope != "local" and any(module in _CLOUD_MODULE_HINTS for module in module_tokens)
    ble_chain_context = _token_substr_hit(tokens, {"ble", "gatt", "bluetooth", "characteristic"})
    cloud_chain_context = _token_substr_hit(tokens, {"http", "api", "oauth", "token", "clientsession"})
    local_scope_context = api_scope == "local"
    ble_context = ble_module_context or ble_chain_context
    cloud_context = api_scope == "cloud" or cloud_module_context or (api_scope != "local" and cloud_chain_context)
    read_context = any(hint in enclosing_fn for hint in _LOCAL_READ_CONTEXT_HINTS) or _token_substr_hit(tokens, _LOCAL_READ_CONTEXT_HINTS)
    control_context = any(hint in enclosing_fn for hint in _LOCAL_CONTROL_CONTEXT_HINTS) or _token_substr_hit(tokens, _LOCAL_CONTROL_CONTEXT_HINTS)
    local_transport_context = (
        any(module in _CLOUD_MODULE_HINTS for module in module_tokens)
        or _token_substr_hit(tokens, _LOCAL_TRANSPORT_CONTEXT_HINTS)
    )

    if any(token in _BLE_CONNECT_NAMES for token in tokens) and ble_context:
        matches.add("BLE_CONNECT")
    if any(token in _BLE_DISCONNECT_NAMES for token in tokens) and ble_context:
        matches.add("BLE_DISCONNECT")
    if (
        any(token in _BLE_GATT_NAMES for token in tokens)
        or (
            ble_context
            and any(any(hint in token for hint in _BLE_GATT_HINT_SUBSTRINGS) for token in tokens)
            and any(any(action in token for action in {"read", "write", "notify"}) for token in tokens)
        )
        or (
            ble_context
            and any(token in _BLE_DEVICE_ACTION_NAMES for token in tokens)
            and ("switchbot" in module_tokens or _token_substr_hit(tokens, {"switchbot", "device"}))
        )
    ) and ble_context:
        matches.add("BLE_GATT_OP")
    if any(token in _BLE_SCAN_NAMES for token in tokens):
        matches.add("BLE_SCAN")
    if any(token in _BLE_TIMEOUT_OR_RETRY_NAMES for token in tokens) and ble_context:
        if _has_ancestor(call, parent_map, (ast.Try, ast.For, ast.While, ast.ExceptHandler)):
            matches.add("BLE_RETRY_OR_TIMEOUT")

    if local_scope_context and local_transport_context and any(token in _LOCAL_API_READ_NAMES or token in _CLOUD_HTTP_NAMES for token in tokens):
        if read_context or not control_context:
            matches.add("LOCAL_API_READ")

    if any(token in _CLOUD_HTTP_NAMES for token in tokens) and cloud_context:
        matches.add("CLOUD_HTTP_CALL")
    if any(token in _CLOUD_TOKEN_NAMES for token in tokens) and cloud_context:
        matches.add("CLOUD_TOKEN_REFRESH")
    if (
        any(token in _CLOUD_BATCH_NAMES for token in tokens)
        or any(any(hint in token for hint in _CLOUD_BATCH_NAMES) for token in tokens)
        or any(token.startswith("multi_") for token in tokens)
        or (
            cloud_context
            and any(isinstance(arg, (ast.List, ast.Tuple, ast.Set)) and len(arg.elts) > 1 for arg in call.args)
        )
        or (
            any(isinstance(arg, ast.Name) and arg.id.lower() in _CLOUD_BATCH_ARG_HINTS for arg in call.args)
        )
    ) and cloud_context:
        matches.add("CLOUD_BATCH_CALL")
    call_chain = _call_chain(call).lower()
    if any(token in _CLOUD_SESSION_CREATE_NAMES for token in tokens) and (cloud_context or "manager" in call_chain):
        matches.add("CLOUD_SESSION_CREATE")
    if any(hint in call_chain for hint in {"self.session", "self.client", "runtime_data", "device_manager", "manager.", "listener"}) and (
        cloud_context or any(token in call_chain for token in {"send_commands", "refresh_mq", "update_device_cache", "query_scenes", "trigger_scene"})
    ):
        matches.add("CLOUD_SESSION_USE")
    if any(token in _CLOUD_SESSION_CLOSE_HINTS for token in tokens) and any(
        hint in call_chain for hint in {"session", "client", "manager", "listener", "mq"}
    ):
        matches.add("CLOUD_SESSION_CLOSE")

    if any(token.endswith("sleep") or token == "sleep" or token in _CLOUD_BACKOFF_NAMES for token in tokens):
        if _has_ancestor(call, parent_map, (ast.Try, ast.For, ast.While, ast.ExceptHandler, ast.If)):
            if cloud_context:
                matches.add("CLOUD_BACKOFF_SLEEP")
            if ble_context:
                matches.add("BLE_RETRY_OR_TIMEOUT")
    if cloud_context and any(any(hint in token for hint in _CLOUD_BACKOFF_NAMES) for token in tokens):
        matches.add("CLOUD_BACKOFF_SLEEP")


    if cloud_module_context and any(token in _CLOUD_HTTP_NAMES for token in tokens):
        matches.add("CLOUD_HTTP_CALL")
    if ble_module_context and any(token in _BLE_GATT_NAMES | _BLE_CONNECT_NAMES for token in tokens):
        matches.add("BLE_GATT_OP")

    if matches & _BLE_RUNTIME_PATTERNS:
        matches.add("BLE_OP")

    return matches


def _match_control_flow_patterns(node: ast.AST, source_lines: List[str]) -> Set[str]:
    matches: Set[str] = set()
    source_segment = _local_text_window(source_lines, getattr(node, "lineno", 1), radius=1)
    if isinstance(node, ast.Compare):
        values: List[str] = []
        if isinstance(node.left, ast.Constant):
            values.append(str(node.left.value))
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant):
                values.append(str(comparator.value))
        left_text = _expr_chain(node.left).lower()
        if any(value == "429" for value in values) and any(hint in left_text or hint in source_segment for hint in _CLOUD_STATUS_HINTS):
            matches.add("CLOUD_429_CHECK")
        elif "httpstatus.too_many_requests" in source_segment or "too_many_requests" in source_segment:
            matches.add("CLOUD_429_CHECK")

    if isinstance(node, ast.Raise):
        exc = node.exc
        exc_name = ""
        if isinstance(exc, ast.Call):
            exc_name = _call_name(exc)
        elif isinstance(exc, ast.Name):
            exc_name = exc.id
        elif isinstance(exc, ast.Attribute):
            exc_name = exc.attr
        lowered = exc_name.lower()
        if (lowered and any(hint in lowered for hint in _RATE_LIMIT_EXCEPTION_HINTS)) or any(hint in source_segment for hint in _RATE_LIMIT_EXCEPTION_HINTS):
            matches.add("CLOUD_429_CHECK")
    if isinstance(node, ast.If) and any(hint in source_segment for hint in {"429", "too_many_requests", "retry_after", "backoff"}):
        matches.add("CLOUD_429_CHECK")
    return matches


def _match_assignment_patterns(
    node: ast.AST,
    source_lines: List[str],
    *,
    cloud_file_context: bool,
) -> Set[str]:
    matches: Set[str] = set()
    if not isinstance(node, (ast.Assign, ast.AnnAssign)):
        return matches
    targets: List[ast.AST] = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
    target_chains = [_expr_chain(target).lower() for target in targets]
    value = node.value if isinstance(node, ast.Assign) else node.value
    value_chain = _expr_chain(value).lower() if value is not None else ""
    source_segment = _local_text_window(source_lines, getattr(node, "lineno", 1), radius=1)
    target_joined = " ".join(target_chains)
    if not cloud_file_context:
        return matches
    if any(
        hint in target_joined
        for hint in {"self.session", "self.client", "runtime_data.session", "runtime_data.client", "manager.session", "manager.client"}
    ):
        if any(hint in value_chain or hint in source_segment for hint in {"clientsession", "session", "client"}):
            matches.add("CLOUD_SESSION_STORE")
    if any(hint in target_joined for hint in {"runtime_data", "self.manager", "device_manager", "listener"}) and any(
        hint in value_chain or hint in source_segment for hint in {"manager", "listener", "clientsession", "session"}
    ):
        matches.add("CLOUD_SESSION_STORE")
    return matches


def _scan_cloud_text_patterns(source_text: str, *, cloud_file_context: bool) -> List[tuple[str, int]]:
    matches: List[tuple[str, int]] = []
    if not cloud_file_context:
        return matches
    lines = source_text.splitlines()
    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()
        if "429" in lowered and any(hint in lowered for hint in _CLOUD_STATUS_HINTS | {"too_many_requests"}):
            matches.append(("CLOUD_429_CHECK", idx))
        if any(token in lowered for token in {"backoff", "back off", "retry_after", "cooldown", "jitter"}) and "sleep_mode" not in lowered:
            matches.append(("CLOUD_BACKOFF_SLEEP", idx))
        if any(token in lowered for token in {"send_commands", "batch", "bulk", "fetch_all", "grouped", "update_devices"}):
            matches.append(("CLOUD_BATCH_CALL", idx))
        if any(token in lowered for token in {"entry.runtime_data", "runtime_data.manager", "self.device_manager", "manager =", "self.manager"}) and any(
            token in lowered for token in {"manager", "listener", "session", "client"}
        ):
            matches.append(("CLOUD_SESSION_STORE", idx))
        if any(token in lowered for token in {"manager.unload", "mq.stop", "remove_device_listener", ".close("}):
            matches.append(("CLOUD_SESSION_CLOSE", idx))
    return matches


def _code_confidence(pattern: str) -> float:
    if pattern == "BLE_REUSE_CONTEXT":
        return 0.7
    if pattern == "CLOUD_SESSION_REUSE":
        return 0.8
    if pattern in {"CLOUD_SESSION_CREATE", "CLOUD_SESSION_STORE", "CLOUD_SESSION_USE", "CLOUD_SESSION_CLOSE"}:
        return 0.75
    if pattern in {"BLE_OP", "CLOUD_HTTP_CALL", "LOCAL_API_READ", "BLE_GATT_OP", "BLE_CONNECT", "ENTRY_SETUP", "ENTRY_UNLOAD", "STATE_WRITE", "SUBSCRIBE"}:
        return 0.9
    return 0.8


def _code_signal_strength(normalization_flags: List[str] | None) -> str:
    flags = {str(flag).strip().lower() for flag in (normalization_flags or [])}
    if "text_pattern_match_v1" in flags:
        return "TEXT_WEAK"
    if "call_name_match_v1" in flags or "protocol_call_match_v1" in flags or "session_chain_match_v1" in flags:
        return "CALL_CHAIN_STRONG"
    return "AST_STRONG"


def _has_cloud_runtime_context(text: str) -> bool:
    lowered = str(text or "").lower()
    return _contains_any_term(lowered, _CLOUD_STRONG_CONTEXT_HINTS) or any(module in lowered for module in _CLOUD_MODULE_HINTS)


def _integration_root_for_path(source_path: Path, repo_root: Path) -> Path | None:
    try:
        rel = source_path.relative_to(repo_root)
    except ValueError:
        return None
    if not rel.parts:
        return None
    return repo_root / rel.parts[0]


def _manifest_iot_class_for_path(source_path: Path, repo_root: Path, cache: Dict[str, str | None]) -> str | None:
    integration_root = _integration_root_for_path(source_path, repo_root)
    if integration_root is None:
        return None
    cache_key = str(integration_root)
    if cache_key in cache:
        return cache[cache_key]
    manifest_path = integration_root / "manifest.json"
    iot_class: str | None = None
    if manifest_path.exists():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw_iot_class = payload.get("iot_class")
            if isinstance(raw_iot_class, str):
                iot_class = raw_iot_class.strip().lower() or None
        except (OSError, json.JSONDecodeError):
            iot_class = None
    cache[cache_key] = iot_class
    return iot_class


def _api_scope_for_path(source_path: Path, repo_root: Path, imported_modules: Set[str], source_text: str, cache: Dict[str, str | None]) -> str:
    iot_class = _manifest_iot_class_for_path(source_path, repo_root, cache)
    if iot_class and iot_class.startswith("local"):
        return "local"
    if iot_class and iot_class.startswith("cloud"):
        return "cloud"
    if _has_cloud_runtime_context(source_text):
        return "cloud"
    module_tokens = {token.lower() for module in imported_modules for token in module.split(".") if token}
    if any(module in _CLOUD_MODULE_HINTS for module in module_tokens):
        return "unknown"
    return "unknown"


def _has_cloud_file_context(source_path: str | Path, imported_modules: Set[str], source_text: str, api_scope: str = "unknown") -> bool:
    if api_scope == "local":
        return False
    if api_scope == "cloud":
        return True
    path_lower = str(source_path).lower()
    module_tokens = {token.lower() for module in imported_modules for token in module.split(".") if token}
    if any(module in _CLOUD_MODULE_HINTS for module in module_tokens):
        return True
    if _has_cloud_runtime_context(source_text):
        return True
    return any(hint in path_lower for hint in {"oauth", "rest", "cloud_api"})


def _append_code_candidate(
    candidates: List[EvidenceCandidate],
    source_path: str,
    pattern: str,
    line_no: int,
    symbol: str | None = None,
    raw_text: str = "",
    normalization_flags: List[str] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> None:
    typed_anchor = _typed_anchor_for_pattern(pattern)
    candidates.append(
        EvidenceCandidate(
            modality="CODE",
            source_path=source_path,
            line_no=line_no,
            typed_anchor=typed_anchor,
            pattern_id=str(pattern).upper(),
            raw_text=raw_text,
            symbol=(symbol or "").strip() or None,
            protocol_scope=_infer_protocol_scope(typed_anchor),
            lifecycle_scope=_infer_lifecycle_scope(typed_anchor),
            resource_scope=_infer_resource_scope(typed_anchor, symbol=symbol, raw_text=raw_text),
            confidence_prior=_code_confidence(str(pattern).upper()),
            specificity=_code_specificity(str(pattern).upper()),
            metadata=dict(metadata or {}),
            normalization_flags=list(normalization_flags or ["ast_pattern_match_v2"]),
            signal_strength=_code_signal_strength(normalization_flags),
        )
    )


def collect_code_candidates(repo_root: str | Path) -> List[EvidenceCandidate]:
    root = Path(repo_root)
    candidates: List[EvidenceCandidate] = []
    manifest_cache: Dict[str, str | None] = {}

    for path in iter_files(root, {".py"}):
        source = path.read_text(encoding="utf-8", errors="ignore")
        source_lines = source.splitlines()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        module_aliases, symbol_aliases, imported_modules = _collect_import_aliases(tree)
        api_scope = _api_scope_for_path(path, root, imported_modules, source, manifest_cache)
        cloud_file_context = _has_cloud_file_context(path, imported_modules, source, api_scope=api_scope)
        function_ranges = _function_ranges(tree)
        parent_map: Dict[int, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parent_map[id(child)] = parent

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for pattern, names in _CODE_PATTERNS.items():
                    if node.name in names:
                        _append_code_candidate(
                            candidates,
                            str(path),
                            pattern,
                            node.lineno,
                            symbol=node.name,
                            normalization_flags=["ast_pattern_match_v2", "function_name_match_v1"],
                            metadata={"function_name": node.name},
                        )

                local_patterns: List[str] = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        for pattern in _match_protocol_call_patterns(
                            child,
                            symbol_aliases=symbol_aliases,
                            module_aliases=module_aliases,
                            imported_modules=imported_modules,
                            parent_map=parent_map,
                            api_scope=api_scope,
                        ):
                            local_patterns.append(pattern)
                if (
                    "BLE_CONNECT" in local_patterns
                    and "BLE_GATT_OP" in local_patterns
                    and "BLE_DISCONNECT" in local_patterns
                    and local_patterns.count("BLE_GATT_OP") >= 1
                ):
                    _append_code_candidate(
                        candidates,
                        str(path),
                        "BLE_REUSE_CONTEXT",
                        node.lineno,
                        symbol=node.name,
                        normalization_flags=["ast_pattern_match_v2", "function_block_match_v1"],
                        metadata={"function_name": node.name},
                    )

            if isinstance(node, ast.Call):
                callee = _call_name(node)
                call_chain = _call_chain(node)
                if callee:
                    for pattern, names in _CODE_PATTERNS.items():
                        if callee in names:
                            _append_code_candidate(
                                candidates,
                                str(path),
                                pattern,
                                getattr(node, "lineno", 0),
                                symbol=call_chain or callee,
                                normalization_flags=["ast_pattern_match_v2", "call_name_match_v1"],
                                metadata={"function_name": _enclosing_function_name(node, parent_map)},
                            )

                for pattern in _match_protocol_call_patterns(
                    node,
                    symbol_aliases=symbol_aliases,
                    module_aliases=module_aliases,
                    imported_modules=imported_modules,
                    parent_map=parent_map,
                    api_scope=api_scope,
                ):
                    _append_code_candidate(
                        candidates,
                        str(path),
                        pattern,
                        getattr(node, "lineno", 0),
                        symbol=call_chain or callee,
                        normalization_flags=["ast_pattern_match_v2", "protocol_call_match_v1"],
                        metadata={"function_name": _enclosing_function_name(node, parent_map)},
                    )

            if isinstance(node, (ast.Compare, ast.Raise, ast.If)):
                for pattern in _match_control_flow_patterns(node, source_lines):
                    _append_code_candidate(
                        candidates,
                        str(path),
                        pattern,
                        getattr(node, "lineno", 0),
                        symbol=_enclosing_function_name(node, parent_map),
                        raw_text=_local_text_window(source_lines, getattr(node, "lineno", 1), radius=1),
                        normalization_flags=["ast_pattern_match_v2", "control_flow_match_v1"],
                        metadata={"function_name": _enclosing_function_name(node, parent_map)},
                    )

            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                for pattern in _match_assignment_patterns(node, source_lines, cloud_file_context=cloud_file_context):
                    targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
                    target_symbol = next((_expr_chain(target) for target in targets if _expr_chain(target)), None)
                    _append_code_candidate(
                        candidates,
                        str(path),
                        pattern,
                        getattr(node, "lineno", 0),
                        symbol=target_symbol or _enclosing_function_name(node, parent_map),
                        raw_text=_local_text_window(source_lines, getattr(node, "lineno", 1), radius=1),
                        normalization_flags=["ast_pattern_match_v2", "assignment_match_v1"],
                        metadata={"function_name": _enclosing_function_name(node, parent_map)},
                    )

        for pattern, line_no in _scan_cloud_text_patterns(source, cloud_file_context=cloud_file_context):
            function_name = _function_name_for_line(line_no, function_ranges)
            _append_code_candidate(
                candidates,
                str(path),
                pattern,
                line_no,
                symbol=function_name or f"line:{line_no}",
                raw_text=_local_text_window(source_lines, line_no, radius=0),
                normalization_flags=["text_pattern_match_v1"],
                metadata={"function_name": function_name},
            )

        file_candidates = [item for item in candidates if item.source_path == str(path)]
        if any(item.pattern_id == "CLOUD_SESSION_STORE" for item in file_candidates) and any(
            item.pattern_id == "CLOUD_SESSION_USE" for item in file_candidates
        ):
            first_store = min(
                (item.line_no for item in file_candidates if item.pattern_id == "CLOUD_SESSION_STORE"),
                default=1,
            )
            _append_code_candidate(
                candidates,
                str(path),
                "CLOUD_SESSION_REUSE",
                first_store,
                symbol="cloud_session_chain",
                normalization_flags=["derived_pattern_v1", "session_chain_match_v1"],
                metadata={"derived_from": ["CLOUD_SESSION_STORE", "CLOUD_SESSION_USE"]},
            )

    return candidates


def fuse_code_candidates(candidates: List[EvidenceCandidate]) -> List[CodeEvidence]:
    fused = _fuse_candidates(candidates, _candidate_key_code)
    return [_candidate_to_code_evidence(candidate) for candidate in fused]


def extract_code_evidence(repo_root: str | Path) -> List[CodeEvidence]:
    return fuse_code_candidates(collect_code_candidates(repo_root))


def _call_name_or_chain(expr: ast.AST) -> str:
    if isinstance(expr, ast.Call):
        return _call_chain(expr)
    return _expr_chain(expr)


def _extract_raises_patterns(node: ast.AST) -> List[tuple[str, str | None]]:
    patterns: List[tuple[str, str | None]] = []
    if not isinstance(node, (ast.With, ast.AsyncWith)):
        return patterns

    for item in node.items:
        context_expr = item.context_expr
        if not isinstance(context_expr, ast.Call):
            continue
        if _call_name(context_expr) not in _TEST_RAISES_NAMES:
            continue
        if not context_expr.args:
            continue
        exc_name = _expr_chain(context_expr.args[0]).split(".")[-1]
        if exc_name == "ConfigEntryNotReady":
            patterns.append(("TEST_CONFIG_ENTRY_NOT_READY", exc_name))
        elif exc_name == "ConfigEntryAuthFailed":
            patterns.append(("TEST_AUTH_FAILED", exc_name))
    return patterns


def _extract_setup_unload_pattern(node: ast.AST) -> tuple[str, str | None] | None:
    call: ast.Call | None = None
    assertion_kind = "call"

    if isinstance(node, ast.Assert):
        value = node.test
        assertion_kind = "assert"
        if isinstance(value, ast.Await):
            value = value.value
        if isinstance(value, ast.Call):
            call = value
    elif isinstance(node, ast.Expr):
        value = node.value
        if isinstance(value, ast.Await):
            value = value.value
        if isinstance(value, ast.Call):
            call = value

    if call is None:
        return None

    callee = _call_name(call)
    chain = _call_chain(call)
    if callee in _TEST_SETUP_CALLS or chain.endswith(".async_setup"):
        return ("TEST_ENTRY_SETUP", assertion_kind)
    if callee in _TEST_UNLOAD_CALLS or chain.endswith(".async_remove") or chain.endswith(".async_unload"):
        return ("TEST_ENTRY_UNLOAD", assertion_kind)
    return None


def _extract_mock_assertion_pattern(node: ast.AST) -> tuple[str, str, str | None] | None:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return None
    call = node.value
    method = _call_name(call)
    if method not in _TEST_ASSERT_METHODS:
        return None

    target = _expr_chain(call.func.value) if isinstance(call.func, ast.Attribute) else ""
    lowered = target.lower()
    if any(token in lowered for token in {"unsubscribe", "listener", "cleanup", "remove"}):
        return ("TEST_SUBSCRIBE_CLEANUP", method, target or None)
    if any(token in lowered for token in {"disconnect", "stop", "close"}):
        return ("TEST_MANAGER_STOP", method, target or None)
    if any(token in lowered for token in {"async_write_ha_state", "schedule_update_ha_state", "state_write", "update"}):
        return ("TEST_STATE_WRITE", method, target or None)
    return None


def _extract_state_write_pattern(node: ast.AST) -> tuple[str, str, str | None] | None:
    call: ast.Call | None = None
    if isinstance(node, ast.Expr):
        value = node.value
        if isinstance(value, ast.Await):
            value = value.value
        if isinstance(value, ast.Call):
            call = value
    elif isinstance(node, ast.Assert):
        value = node.test
        if isinstance(value, ast.Await):
            value = value.value
        if isinstance(value, ast.Call):
            call = value
    if call is None:
        return None

    chain = _call_chain(call).lower()
    callee = _call_name(call).lower()
    if any(token in chain or token == callee for token in {"async_write_ha_state", "schedule_update_ha_state"}):
        return ("TEST_STATE_WRITE", "call", _call_chain(call) or None)
    return None


def _extract_test_cloud_pattern(node: ast.AST, source_lines: List[str]) -> tuple[str, str, str | None] | None:
    line_no = getattr(node, "lineno", 1)
    segment = _local_text_window(source_lines, line_no, radius=0)
    window = _local_text_window(source_lines, line_no, radius=3)

    if isinstance(node, (ast.With, ast.AsyncWith)):
        for pattern, target in _extract_raises_patterns(node):
            if pattern == "TEST_CONFIG_ENTRY_NOT_READY" and "429" in segment:
                return ("TEST_429_RETRY", "raises", target)
            if pattern == "TEST_AUTH_FAILED":
                return ("TEST_HTTP_ERROR_RECOVERY", "raises", target)

    if isinstance(node, ast.Call):
        chain = _call_chain(node).lower()
        callee = _call_name(node).lower()
        if any(token in chain for token in {"send_commands", "batch", "bulk", "fetch_all", "grouped", "update_devices"}) or callee.startswith("multi_"):
            return ("TEST_BATCH_CALL", "call", _call_chain(node) or None)
        if "sleep" in callee or "sleep" in chain:
            if any(token in window for token in {"429", "backoff", "retry_after", "retry", "rate_limit", "too_many_requests"}):
                return ("TEST_BACKOFF_SLEEP", "call", _call_chain(node) or None)
        if any(token in chain for token in {"session", "clientsession", "client", "manager"}) and any(
            token in segment for token in {"assert_called_once", "assert_called_once_with", "assert_not_called"}
        ):
            root_obj = chain.split(".")[0]
            chain_parts = [part for part in chain.split(".") if part]
            assertion_name = chain_parts[-1] if chain_parts else callee
            target_name = chain_parts[-2] if len(chain_parts) >= 2 else callee
            explicit_session_reuse = any(token in chain for token in {
                "clientsession",
                "client_session",
                "self.session",
                "runtime_data.session",
                "session.request",
                "session.get",
                "session.post",
                "session.put",
                "session.patch",
                "session.delete",
                "send_commands",
                "refresh_mq",
                "query_scenes",
                "trigger_scene",
                "update_device_cache",
                "batch_update",
            })
            if root_obj in {"session", "clientsession", "client_session"}:
                explicit_session_reuse = True
            if explicit_session_reuse:
                if assertion_name == "assert_not_called":
                    return ("TEST_EXPECTED_CLIENT_IDLE", "assert", _call_chain(node) or None)
                return ("TEST_NO_REDUNDANT_CALL", "assert", _call_chain(node) or None)
            if assertion_name == "assert_not_called":
                return ("TEST_CALL_SUPPRESSION", "assert", _call_chain(node) or None)
            if target_name in {"connect", "async_connect"}:
                return ("TEST_CLIENT_CONNECT", "assert", _call_chain(node) or None)
            if target_name in {"disconnect", "close", "async_disconnect"}:
                return ("TEST_CLIENT_DISCONNECT", "assert", _call_chain(node) or None)
            if target_name.startswith("set_") or any(token in target_name for token in {"configuration", "config", "encryption", "key"}):
                return ("TEST_CLIENT_CONFIG_UPDATE", "assert", _call_chain(node) or None)
            if target_name.startswith("send_") or any(token in target_name for token in {"event", "audio", "response", "timer"}):
                return ("TEST_CLIENT_EMIT", "assert", _call_chain(node) or None)
            return ("TEST_CLIENT_CALL_CONSTRAINT", "assert", _call_chain(node) or None)
        if "429" in segment or "too_many_requests" in segment or "ratelimit" in segment:
            return ("TEST_RATE_LIMIT", "call", _call_chain(node) or None)
        if any(token in segment for token in {"configentryauthfailed", "auth failed", "http error"}):
            return ("TEST_HTTP_ERROR_RECOVERY", "call", _call_chain(node) or None)

    if isinstance(node, ast.Assert):
        test_expr = node.test
        if isinstance(test_expr, ast.Compare):
            compare_segment = _local_text_window(source_lines, getattr(test_expr, "lineno", line_no), radius=0)
            if "429" in compare_segment or "too_many_requests" in compare_segment:
                return ("TEST_RATE_LIMIT", "assert", None)
    return None


def _append_test_candidate(
    candidates: List[EvidenceCandidate],
    source_path: str,
    test_name: str,
    pattern: str,
    line_no: int,
    assertion_kind: str,
    target_symbol: str | None,
    confidence: float,
    protocol_hypothesis: str | None = None,
) -> None:
    typed_anchor = _typed_anchor_for_pattern(pattern)
    candidates.append(
        EvidenceCandidate(
            modality="TEST",
            source_path=source_path,
            line_no=line_no,
            typed_anchor=typed_anchor,
            pattern_id=str(pattern).upper(),
            raw_text="",
            symbol=(target_symbol or "").strip() or None,
            protocol_scope=_infer_protocol_scope(typed_anchor),
            lifecycle_scope=_infer_lifecycle_scope(typed_anchor),
            resource_scope=_infer_resource_scope(typed_anchor, symbol=target_symbol),
            confidence_prior=confidence,
            specificity=_test_specificity(str(pattern).upper()),
            metadata={
                "test_name": test_name,
                "assertion_kind": assertion_kind,
                "target_symbol": target_symbol,
                "protocol_hypothesis": protocol_hypothesis,
                "behavior_category": _test_behavior_category(pattern),
            },
            normalization_flags=[
                "test_candidate_v1",
                "test_assertion_pattern_v2",
                *([f"protocol_hypothesis:{protocol_hypothesis}"] if protocol_hypothesis else []),
            ],
        )
    )


def collect_test_candidates(tests_root: str | Path) -> List[EvidenceCandidate]:
    root = Path(tests_root)
    candidates: List[EvidenceCandidate] = []
    seen: Set[Tuple[str, str, int, str, str | None]] = set()

    for path in iter_files(root, {".py"}):
        source = path.read_text(encoding="utf-8", errors="ignore")
        source_lines = source.splitlines()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                continue
            test_name = node.name

            def _emit(pattern: str, line_no: int, assertion_kind: str, target_symbol: str | None, confidence: float = 0.85) -> None:
                key = (str(path), pattern, line_no, assertion_kind, target_symbol)
                if key in seen:
                    return
                seen.add(key)
                protocol_hypothesis = {
                    "TEST_429_RETRY": "CLOUD_429_CHECK",
                    "TEST_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
                    "TEST_BATCH_CALL": "CLOUD_BATCH_CALL",
                    "TEST_BATCH_UPDATE": "CLOUD_BATCH_CALL",
                    "TEST_SUBSCRIBE_CLEANUP": "SUBSCRIBE_PAIRING",
                }.get(pattern)
                if pattern in {"TEST_NO_REDUNDANT_CALL", "TEST_EXPECTED_CLIENT_IDLE"} and target_symbol:
                    target_lower = target_symbol.lower()
                    if any(token in target_lower for token in {
                        "clientsession",
                        "client_session",
                        "self.session",
                        "runtime_data.session",
                        "session.request",
                        "session.get",
                        "session.post",
                        "session.put",
                        "session.patch",
                        "session.delete",
                        "send_commands",
                        "refresh_mq",
                        "query_scenes",
                        "trigger_scene",
                        "update_device_cache",
                        "batch_update",
                    }):
                        protocol_hypothesis = "CLOUD_SESSION_REUSE"
                _append_test_candidate(
                    candidates,
                    str(path),
                    test_name,
                    pattern,
                    line_no,
                    assertion_kind,
                    target_symbol,
                    confidence,
                    protocol_hypothesis=protocol_hypothesis,
                )

            for child in ast.walk(node):
                for pattern, target_symbol in _extract_raises_patterns(child):
                    _emit(pattern, getattr(child, "lineno", node.lineno), "raises", target_symbol, 0.9)

                setup_or_unload = _extract_setup_unload_pattern(child)
                if setup_or_unload is not None:
                    pattern, assertion_kind = setup_or_unload
                    call_node = child.test if isinstance(child, ast.Assert) else child.value
                    if isinstance(call_node, ast.Await):
                        call_node = call_node.value
                    target_symbol = _call_chain(call_node) if isinstance(call_node, ast.Call) else None
                    _emit(pattern, getattr(child, "lineno", node.lineno), assertion_kind, target_symbol, 0.9)

                mock_pattern = _extract_mock_assertion_pattern(child)
                if mock_pattern is not None:
                    pattern, assertion_kind, target_symbol = mock_pattern
                    confidence = 0.9 if pattern in {"TEST_SUBSCRIBE_CLEANUP", "TEST_MANAGER_STOP"} else 0.85
                    _emit(pattern, getattr(child, "lineno", node.lineno), assertion_kind, target_symbol, confidence)

                state_write_pattern = _extract_state_write_pattern(child)
                if state_write_pattern is not None:
                    pattern, assertion_kind, target_symbol = state_write_pattern
                    _emit(pattern, getattr(child, "lineno", node.lineno), assertion_kind, target_symbol, 0.85)

                if isinstance(child, (ast.With, ast.AsyncWith, ast.Call, ast.Assert)):
                    cloud_pattern = _extract_test_cloud_pattern(child, source_lines)
                    if cloud_pattern is not None:
                        pattern, assertion_kind, target_symbol = cloud_pattern
                        _emit(pattern, getattr(child, "lineno", node.lineno), assertion_kind, target_symbol, 0.85)

    return candidates


def fuse_test_candidates(candidates: List[EvidenceCandidate]) -> List[TestEvidence]:
    fused = _fuse_candidates(candidates, _candidate_key_test)
    evidence = [_candidate_to_test_evidence(candidate) for candidate in fused]
    evidence.sort(key=lambda item: (item.source_path, item.line_no, item.pattern, item.test_name or ""))
    return evidence


def extract_test_evidence(tests_root: str | Path) -> List[TestEvidence]:
    return fuse_test_candidates(collect_test_candidates(tests_root))


def build_evidence_bank(
    docs_root: str | Path,
    repo_root: str | Path,
    tests_root: str | Path | None = None,
    output_path: str | Path | None = None,
) -> EvidenceBank:
    bank = EvidenceBank(
        docs=extract_doc_evidence(docs_root),
        code=extract_code_evidence(repo_root),
        tests=extract_test_evidence(tests_root) if tests_root else [],
    )

    if output_path:
        dump_json(
            output_path,
            {
                "docs": [doc.__dict__ for doc in bank.docs],
                "code": [item.__dict__ for item in bank.code],
                "tests": [item.__dict__ for item in bank.tests],
            },
        )

    return bank


from profile_builder.evidence.counterexample_projection import (
    infer_context,
    project_witnesses_to_evidence,
    witness_to_evidence,
)
from profile_builder.evidence.evidence_types import (
    ClusterPack as CounterexampleClusterPack,
    CounterexampleCluster,
    CounterexampleEvidence,
)
from profile_builder.evidence.normalization import make_trace_signature, normalize_witness
from profile_builder.evidence.trigger_patterns import (
    infer_rule_gap_and_refinement,
    infer_trigger_pattern,
)

__all__ = [
    "EvidenceBank",
    "build_evidence_bank",
    "extract_code_evidence",
    "extract_doc_evidence",
    "extract_test_evidence",
    "TestEvidence",
    "CounterexampleEvidence",
    "CounterexampleCluster",
    "CounterexampleClusterPack",
    "infer_context",
    "infer_rule_gap_and_refinement",
    "infer_trigger_pattern",
    "make_trace_signature",
    "normalize_witness",
    "project_witnesses_to_evidence",
    "witness_to_evidence",
]
