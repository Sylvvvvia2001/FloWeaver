from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from profile_builder.evidence import EvidenceBank


EVIDENCE_POLICY_VERSION = "profile_builder_evidence_policy/v1"
DEFAULT_SEMANTIC_POLICY = "core_plus_verified"

_CORE_FRAMEWORK_ANCHORS = {
    "ENTRY_SETUP",
    "ENTRY_UNLOAD",
    "STATE_WRITE",
    "COORD_REFRESH",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "SUBSCRIBE_PAIRING",
}

_CORE_DOC_POLICY_ANCHORS = {
    "DOC_ENTRY_SETUP_POLICY",
    "DOC_ENTRY_UNLOAD_POLICY",
    "DOC_COORD_REFRESH_POLICY",
    "DOC_SUBSCRIBE_PAIRING_POLICY",
    "DOC_STATE_UPDATE_POLICY",
    "DOC_BLE_CONNECTION_POLICY",
    "DOC_BLE_GATT_POLICY",
    "DOC_BLE_DISCONNECT_POLICY",
    "DOC_RETRY_BACKOFF_POLICY",
    "DOC_CLOUD_BATCH_POLICY",
    "DOC_CLOUD_API_POLICY",
    "DOC_CLOUD_SESSION_POLICY",
    "DOC_CLOUD_AUTH_POLICY",
}

_CORE_PROTOCOL_ANCHORS = {
    "BLE_CONNECT",
    "BLE_GATT_OP",
    "BLE_DISCONNECT",
    "BLE_SCAN",
    "BLE_RETRY_OR_TIMEOUT",
    "BLE_REUSE_CONTEXT",
    "BLE_OP",
    "CLOUD_HTTP_CALL",
    "CLOUD_TOKEN_REFRESH",
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_BATCH_CALL",
    "CLOUD_SESSION_CREATE",
    "CLOUD_SESSION_STORE",
    "CLOUD_SESSION_USE",
    "CLOUD_SESSION_CLOSE",
    "CLOUD_SESSION_REUSE",
    "LOCAL_API_READ",
}

_CORE_TEST_ANCHORS = {
    "TEST_ENTRY_SETUP",
    "TEST_ENTRY_UNLOAD",
    "TEST_CONFIG_ENTRY_NOT_READY",
    "TEST_AUTH_FAILED",
    "TEST_STATE_WRITE",
    "TEST_SUBSCRIBE_CLEANUP",
    "TEST_CLIENT_CALL_CONSTRAINT",
    "TEST_CALL_SUPPRESSION",
    "TEST_EXPECTED_CLIENT_IDLE",
    "TEST_EXPECTED_SINGLE_CALL",
    "TEST_NO_REDUNDANT_CALL",
    "TEST_RETRY_CALL",
    "TEST_BACKOFF_CALL",
    "TEST_BATCH_CALL",
    "TEST_RATE_LIMIT",
    "TEST_HTTP_ERROR_RECOVERY",
}

CORE_SEMANTIC_ANCHORS = (
    _CORE_FRAMEWORK_ANCHORS
    | _CORE_DOC_POLICY_ANCHORS
    | _CORE_PROTOCOL_ANCHORS
    | _CORE_TEST_ANCHORS
)

_EXTENDED_HINT_SUFFIXES = ("_HINT",)
_EXTENDED_HINT_ANCHORS = {
    "CLOUD_SESSION_HINT",
    "CLOUD_BATCH_HINT",
    "CLOUD_BACKOFF_HINT",
    "CLOUD_API_HINT",
    "BLE_CONNECTION_HINT",
    "BLE_GATT_HINT",
}


@dataclass
class EvidencePolicyResult:
    policy: str
    semantic_bank: EvidenceBank
    report: Dict[str, Any]


def _anchor(row: Any) -> str:
    return str(
        getattr(row, "effective_typed_anchor", None)
        or getattr(row, "protocol_hypothesis", None)
        or getattr(row, "typed_anchor", None)
        or getattr(row, "pattern", "")
        or "UNKNOWN"
    ).strip().upper()


def _row_kind(row: Any) -> str:
    source_type = str(getattr(row, "source_type", "") or "").strip().lower()
    if source_type in {"doc", "code", "test"}:
        return source_type
    if hasattr(row, "assertion_kind"):
        return "test"
    if hasattr(row, "modality"):
        return "doc"
    return "code"


def _evidence_id(row: Any) -> str:
    return str(getattr(row, "evidence_id", "") or "")


def _is_llm_verified(row: Any) -> bool:
    extractor = str(getattr(row, "extractor_version", "") or "")
    flags = {str(item) for item in getattr(row, "normalization_flags", [])}
    return extractor == "profile_builder_llm_discovery/v1" or any(
        flag.startswith("llm_candidate_verified") for flag in flags
    )


def _is_hint_anchor(anchor: str) -> bool:
    return anchor in _EXTENDED_HINT_ANCHORS or any(anchor.endswith(suffix) for suffix in _EXTENDED_HINT_SUFFIXES)


def classify_evidence(row: Any) -> Tuple[str, str]:


    kind = _row_kind(row)
    anchor = _anchor(row)
    if _is_llm_verified(row):
        return "llm_verified_semantic", "accepted:llm_verified"
    if kind == "doc":
        doc_kind = str(getattr(row, "doc_kind", "") or "").strip().upper()
        if anchor in CORE_SEMANTIC_ANCHORS or doc_kind in {"NORMATIVE_SENTENCE", "LIFECYCLE_SENTENCE"}:
            return "deterministic_core_semantic", "accepted:doc_normative_or_core_anchor"
        return "deterministic_extended_semantic", "rejected:doc_not_core_normative"
    if kind == "test":
        return "deterministic_core_semantic", "accepted:test_behavior_fact"
    if anchor in CORE_SEMANTIC_ANCHORS:
        strength = str(getattr(row, "signal_strength", "") or "").strip().upper()
        if strength == "TEXT_WEAK":
            return "deterministic_extended_semantic", "rejected:text_weak_core_anchor"
        return "deterministic_core_semantic", "accepted:core_runtime_anchor"
    if _is_hint_anchor(anchor):
        return "deterministic_extended_semantic", "rejected:hint_anchor_requires_llm_or_stronger_support"
    return "deterministic_extended_semantic", "rejected:not_core_semantic_anchor"


def _counts() -> Dict[str, int]:
    return {
        "deterministic_core_semantic": 0,
        "deterministic_extended_semantic": 0,
        "llm_verified_semantic": 0,
    }


def select_semantic_evidence_bank(bank: EvidenceBank, *, policy: str = DEFAULT_SEMANTIC_POLICY) -> EvidencePolicyResult:


    normalized_policy = str(policy or DEFAULT_SEMANTIC_POLICY).strip().lower()
    if normalized_policy not in {"legacy", "core_plus_verified"}:
        raise ValueError(f"Unsupported evidence semantic policy: {policy}")
    if normalized_policy == "legacy":
        total = len(bank.docs) + len(bank.code) + len(bank.tests)
        return EvidencePolicyResult(
            policy=normalized_policy,
            semantic_bank=bank,
            report={
                "schema_version": EVIDENCE_POLICY_VERSION,
                "policy": normalized_policy,
                "raw_count": {"docs": len(bank.docs), "code": len(bank.code), "tests": len(bank.tests), "total": total},
                "semantic_count": {"docs": len(bank.docs), "code": len(bank.code), "tests": len(bank.tests), "total": total},
                "class_counts": {"legacy_passthrough": total},
                "dropped_count": 0,
                "dropped_examples": [],
            },
        )

    semantic = EvidenceBank()
    class_counts = _counts()
    dropped_examples: List[Dict[str, Any]] = []

    for attr in ("docs", "code", "tests"):
        rows = list(getattr(bank, attr))
        for row in rows:
            evidence_class, reason = classify_evidence(row)
            class_counts[evidence_class] = class_counts.get(evidence_class, 0) + 1
            if evidence_class in {"deterministic_core_semantic", "llm_verified_semantic"}:
                getattr(semantic, attr).append(row)
                continue
            if len(dropped_examples) < 32:
                dropped_examples.append(
                    {
                        "evidence_id": _evidence_id(row),
                        "kind": attr[:-1] if attr.endswith("s") else attr,
                        "anchor": _anchor(row),
                        "source_path": str(getattr(row, "source_path", "") or ""),
                        "line_no": getattr(row, "line_no", None),
                        "reason": reason,
                    }
                )

    raw_total = len(bank.docs) + len(bank.code) + len(bank.tests)
    semantic_total = len(semantic.docs) + len(semantic.code) + len(semantic.tests)
    return EvidencePolicyResult(
        policy=normalized_policy,
        semantic_bank=semantic,
        report={
            "schema_version": EVIDENCE_POLICY_VERSION,
            "policy": normalized_policy,
            "raw_count": {"docs": len(bank.docs), "code": len(bank.code), "tests": len(bank.tests), "total": raw_total},
            "semantic_count": {
                "docs": len(semantic.docs),
                "code": len(semantic.code),
                "tests": len(semantic.tests),
                "total": semantic_total,
            },
            "class_counts": class_counts,
            "dropped_count": raw_total - semantic_total,
            "dropped_examples": dropped_examples,
        },
    )

