from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any, Dict, List, Set, Tuple

from dsl.contracts import Rule, RuleStatus
from profile_builder.evidence import EvidenceBank


ALLOWED_EFFECT_KINDS = {
    "ordering_or_constraint",
    "lifecycle_required",
    "retry_policy",
    "coalesce_state_write",
}

TEST_TO_MARKER_HINT = {
    "TEST_429_RETRY": "CLOUD_429_CHECK",
    "TEST_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
    "TEST_BATCH_CALL": "CLOUD_BATCH_CALL",
    "TEST_BATCH_UPDATE": "CLOUD_BATCH_CALL",
    "TEST_RATE_LIMIT": "CLOUD_429_CHECK",
    "TEST_HTTP_ERROR_RECOVERY": "CLOUD_BACKOFF_SLEEP",
}

_AGGREGATE_MARKERS = {"BLE_OP", "CLOUD_OP"}

STRICT_PROTOCOL_THRESHOLD_MARKERS = {
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_BATCH_CALL",
    "CLOUD_SESSION_REUSE",
}

_DOC_POLICY_MARKER_SUPPORT = {
    "DOC_ENTRY_SETUP_POLICY": {"ENTRY_SETUP"},
    "DOC_ENTRY_UNLOAD_POLICY": {"ENTRY_UNLOAD"},
    "DOC_COORD_REFRESH_POLICY": {"COORD_REFRESH"},
    "DOC_SUBSCRIBE_PAIRING_POLICY": {"SUBSCRIBE", "UNSUBSCRIBE"},
    "DOC_STATE_UPDATE_POLICY": {"STATE_WRITE"},
    "DOC_RETRY_BACKOFF_POLICY": {"CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP"},
    "DOC_CLOUD_BATCH_POLICY": {"CLOUD_BATCH_CALL"},
    "DOC_CLOUD_API_POLICY": {"CLOUD_HTTP_CALL"},
    "DOC_CLOUD_SESSION_POLICY": {"CLOUD_SESSION_REUSE"},
    "DOC_CLOUD_AUTH_POLICY": {"CLOUD_TOKEN_REFRESH"},
}

_CODE_SIGNAL_WEIGHT = {
    "AST_STRONG": 1.0,
    "CALL_CHAIN_STRONG": 0.8,
    "TEXT_WEAK": 0.35,
}


def _doc_marker_support(bank: EvidenceBank) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in bank.docs:
        path = str(row.source_path).lower()
        typed_anchor = str(getattr(row, "typed_anchor", "")).upper()
        for marker in _DOC_POLICY_MARKER_SUPPORT.get(typed_anchor, set()):
            counts[marker] = counts.get(marker, 0) + 1


        if "docs-data-update" in path:
            counts["CLOUD_429_CHECK"] = counts.get("CLOUD_429_CHECK", 0) + 1
        if "integration_fetching_data" in path:
            counts["CLOUD_BACKOFF_SLEEP"] = counts.get("CLOUD_BACKOFF_SLEEP", 0) + 1
        strength = str(getattr(row, "normative_strength", "INFO")).upper()
        specificity = str(getattr(row, "specificity", "GENERIC")).upper()
        if strength not in {"MUST", "SHOULD"} or specificity not in {"PROTOCOL", "FRAMEWORK"}:
            continue
        if typed_anchor == "CLOUD_429_CHECK" or "docs-data-update" in path:
            counts["CLOUD_429_CHECK"] = counts.get("CLOUD_429_CHECK", 0) + 1
        if typed_anchor in {"CLOUD_BACKOFF_SLEEP", "DOC_RETRY_BACKOFF_POLICY"} or "integration_fetching_data" in path:
            counts["CLOUD_BACKOFF_SLEEP"] = counts.get("CLOUD_BACKOFF_SLEEP", 0) + 1
        if typed_anchor in {"CLOUD_BATCH_CALL", "DOC_CLOUD_BATCH_POLICY"} or "diagnostics" in path:
            counts["CLOUD_BATCH_CALL"] = counts.get("CLOUD_BATCH_CALL", 0) + 1
    return counts


@dataclass
class GateDecision:
    enabled: List[Rule] = field(default_factory=list)
    disabled: List[Rule] = field(default_factory=list)
    reasons: Dict[str, List[str]] = field(default_factory=dict)


def _is_matchable(rule: Rule, bank: EvidenceBank) -> bool:
    return _matchability_reasons(rule, bank)[0]


def _aggregate_marker_available(marker: str, available_markers: Set[str]) -> bool:
    if marker == "BLE_OP":
        return any(pattern.startswith("BLE_") for pattern in available_markers)
    if marker == "CLOUD_OP":
        return any(pattern.startswith("CLOUD_") for pattern in available_markers)
    return marker in available_markers


def _support_counts(bank: EvidenceBank) -> Dict[str, Dict[str, float]]:
    counts: Dict[str, Dict[str, float]] = {}
    for item in bank.code:
        marker = str(getattr(item, "effective_typed_anchor", "") or getattr(item, "typed_anchor", "") or item.pattern).upper()
        bucket = counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        weight = _CODE_SIGNAL_WEIGHT.get(str(getattr(item, "signal_strength", "AST_STRONG")).upper(), 1.0)
        bucket["code"] += float(item.frequency) * weight
        if str(getattr(item, "signal_strength", "AST_STRONG")).upper() != "TEXT_WEAK":
            bucket["code_strong"] += float(item.frequency)
    for item in bank.tests:
        marker = str(getattr(item, "protocol_hypothesis", "") or TEST_TO_MARKER_HINT.get(item.pattern, "")).upper()
        if not marker:
            continue
        bucket = counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        bucket["test"] += float(item.frequency)
    for marker, doc_count in _doc_marker_support(bank).items():
        bucket = counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        bucket["doc"] += float(doc_count)
    return counts


def _evidence_threshold_met(marker: str, counts: Dict[str, Dict[str, float]]) -> bool:
    bucket = counts.get(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
    code_count = float(bucket.get("code", 0.0))
    code_strong = float(bucket.get("code_strong", 0.0))
    test_count = float(bucket.get("test", 0.0))
    doc_count = float(bucket.get("doc", 0.0))
    if marker == "CLOUD_SESSION_REUSE":
        store = counts.get("CLOUD_SESSION_STORE", {})
        use = counts.get("CLOUD_SESSION_USE", {})
        return float(store.get("code_strong", 0.0)) >= 1.0 and float(use.get("code_strong", 0.0)) >= 1.0
    if marker in STRICT_PROTOCOL_THRESHOLD_MARKERS:
        return (
            (code_strong >= 1 and test_count >= 1)
            or code_count >= 2.0
            or (code_strong >= 1 and doc_count >= 1)
            or (test_count >= 1 and doc_count >= 1)
            or doc_count >= 2
        )
    return code_strong >= 1 or code_count >= 1.0 or (code_strong >= 1 and test_count >= 1)


def _matchability_reasons(rule: Rule, bank: EvidenceBank) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    counts = _support_counts(bank)
    available_markers: Set[str] = {marker for marker, row in counts.items() if _evidence_threshold_met(marker, counts)}

    pattern = str(rule.match_pattern.get("dominant_pattern", "")).strip()
    if pattern and not _aggregate_marker_available(pattern, available_markers):
        reasons.append(f"missing_marker:{pattern}")
        reasons.append(f"missing_detector:{pattern}")
    elif pattern and not _evidence_threshold_met(pattern, counts):
        reasons.append(f"evidence_count_below_threshold:{pattern}")

    for marker in sorted({str(hint).strip().upper() for hint in rule.marker_hints if str(hint).strip()}):
        if not _aggregate_marker_available(marker, available_markers):
            reasons.append(f"missing_marker:{marker}")
            if marker not in {"BLE_OP", "CLOUD_OP"}:
                reasons.append(f"missing_detector:{marker}")
        elif marker not in {"BLE_OP", "CLOUD_OP"} and not _evidence_threshold_met(marker, counts):
            reasons.append(f"evidence_count_below_threshold:{marker}")

    if rule.rule_id == "rule_protocol_cloud_batch_reuse":
        if float(counts.get("CLOUD_SESSION_STORE", {}).get("code_strong", 0.0)) < 1.0:
            reasons.append("missing_supporting_evidence:CLOUD_SESSION_STORE")
        if float(counts.get("CLOUD_SESSION_USE", {}).get("code_strong", 0.0)) < 1.0:
            reasons.append("missing_supporting_evidence:CLOUD_SESSION_USE")

    if reasons:
        deduped = list(dict.fromkeys(["matchability:false", *reasons]))
        return False, deduped
    return True, []


def _rule_support_markers(rule: Rule) -> List[str]:
    ordered: List[str] = []
    seen: Set[str] = set()
    dominant_pattern = str(rule.match_pattern.get("dominant_pattern", "")).strip().upper()
    if dominant_pattern:
        seen.add(dominant_pattern)
        ordered.append(dominant_pattern)
    for marker in rule.marker_hints:
        normalized = str(marker).strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    concrete = [marker for marker in ordered if marker not in _AGGREGATE_MARKERS]
    return concrete or ordered


def _marker_modalities(marker: str, counts: Dict[str, Dict[str, float]]) -> Set[str]:
    modalities: Set[str] = set()
    normalized = str(marker).strip().upper()
    if normalized == "BLE_OP":
        prefixes = ("BLE_",)
    elif normalized == "CLOUD_OP":
        prefixes = ("CLOUD_",)
    else:
        prefixes = ()

    if prefixes:
        related_rows = [bucket for key, bucket in counts.items() if key.startswith(prefixes)]
    else:
        related_rows = [counts.get(normalized, {})]

    for bucket in related_rows:
        if float(bucket.get("code", 0.0)) > 0.0:
            modalities.add("code")
        if float(bucket.get("test", 0.0)) > 0.0:
            modalities.add("test")
        if float(bucket.get("doc", 0.0)) > 0.0:
            modalities.add("doc")
    return modalities


def _strong_code_only_protocol_support(
    rule: Rule,
    evidence_index: Dict[str, Dict[str, Any]],
    counts: Dict[str, Dict[str, float]],
) -> bool:
    code_rows = [
        evidence_index[evidence_id]
        for evidence_id in rule.evidence_ids
        if evidence_id in evidence_index and str(evidence_index[evidence_id].get("source_type", "")).strip().lower() == "code"
    ]
    code_frequency = sum(max(1, int(row.get("frequency", 1))) for row in code_rows)
    if code_frequency < 4:
        return False

    runtime_rows = sum(max(1, int(row.get("frequency", 1))) for row in code_rows if str(row.get("semantic_level", "")).strip().upper() == "RUNTIME")
    strong_rows = sum(max(1, int(row.get("frequency", 1))) for row in code_rows if str(row.get("signal_strength", "")).strip().upper() != "TEXT_WEAK")
    if runtime_rows < ceil(code_frequency * 0.75):
        return False
    if strong_rows < ceil(code_frequency * 0.6):
        return False

    support_markers = _rule_support_markers(rule)
    if not support_markers:
        return False

    strongly_supported = 0
    for marker in support_markers:
        bucket = counts.get(marker, {})
        if float(bucket.get("code_strong", 0.0)) >= 1.0 or float(bucket.get("code", 0.0)) >= 2.0:
            strongly_supported += 1

    required = min(2, len(support_markers))
    return strongly_supported >= required


def effect_specific_gate(rule: Rule, evidence_index: Dict[str, Dict[str, Any]]) -> List[str]:
    del evidence_index
    reasons: List[str] = []
    effect = rule.effect or {}
    effect_kind = str(effect.get("kind", "")).strip()
    hints = {str(hint).strip().upper() for hint in rule.marker_hints if str(hint).strip()}

    if effect_kind == "retry_policy":
        if not ({"CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP"} & hints):
            reasons.append("missing_retry_markers")

    if effect_kind == "coalesce_state_write":
        if "STATE_WRITE" not in hints:
            reasons.append("missing_state_write_marker")

    if rule.category == "lifecycle":
        clear_pairs = [
            {"ENTRY_SETUP", "COORD_REFRESH"},
            {"COORD_REFRESH", "STATE_WRITE"},
            {"SUBSCRIBE", "UNSUBSCRIBE"},
            {"UNSUBSCRIBE", "ENTRY_UNLOAD"},
            {"BLE_CONNECT", "BLE_GATT_OP"},
            {"BLE_GATT_OP", "BLE_DISCONNECT"},
        ]
        if not any(pair.issubset(hints) for pair in clear_pairs):
            reasons.append("lifecycle_rule_without_clear_anchor_pair")

    return reasons


def modality_gate(
    rule: Rule,
    evidence_index: Dict[str, Dict[str, Any]],
    counts: Dict[str, Dict[str, float]],
) -> List[str]:
    reasons: List[str] = []
    modalities: Set[str] = set()
    for evidence_id in rule.evidence_ids:
        row = evidence_index.get(evidence_id)
        if row:
            modalities.add(str(row.get("source_type", "")).strip().lower())

    for marker in _rule_support_markers(rule):
        modalities.update(_marker_modalities(marker, counts))

    if rule.category == "protocol":
        if "code" not in modalities:
            reasons.append("protocol_rule_without_code_support")
        if len(modalities) < 2 and not _strong_code_only_protocol_support(rule, evidence_index, counts):
            reasons.append("single_modality_support_only")

    return reasons


def semantic_level_gate(rule: Rule, evidence_index: Dict[str, Dict[str, Any]]) -> List[str]:
    reasons: List[str] = []
    total = 0
    runtime = 0
    hint = 0

    for evidence_id in rule.evidence_ids:
        row = evidence_index.get(evidence_id)
        if not row:
            continue
        total += 1
        level = str(row.get("semantic_level", "")).strip().upper()
        if level == "RUNTIME":
            runtime += 1
        if level == "HINT":
            hint += 1

    if rule.category == "protocol" and total > 0:
        if runtime / total < 0.4:
            reasons.append("insufficient_runtime_support")
        if hint / total > 0.5:
            reasons.append("hint_support_too_high")

    return reasons


def run_deterministic_gate(rules: List[Rule], bank: EvidenceBank) -> GateDecision:
    decision = GateDecision()
    evidence_index = bank.by_id()
    counts = _support_counts(bank)
    evidence_ids = set(evidence_index.keys())

    for rule in rules:
        rule_reasons: List[str] = []

        if not rule.rule_id or not rule.title:
            rule_reasons.append("schema:missing_identity")
        if not rule.evidence_ids:
            rule_reasons.append("schema:missing_evidence")
        if any(eid not in evidence_ids for eid in rule.evidence_ids):
            rule_reasons.append("evidence_binding:unknown_evidence")
        matchable, matchability_reasons = _matchability_reasons(rule, bank)
        if not matchable:
            rule_reasons.extend(matchability_reasons)
        effect_kind = rule.effect.get("kind")
        if effect_kind and effect_kind not in ALLOWED_EFFECT_KINDS:
            rule_reasons.append("effect:unsupported_primitive")
        rule_reasons.extend(effect_specific_gate(rule, evidence_index))
        rule_reasons.extend(modality_gate(rule, evidence_index, counts))
        rule_reasons.extend(semantic_level_gate(rule, evidence_index))

        if rule_reasons:
            disabled_rule = Rule(**{**rule.__dict__, "status": RuleStatus.DISABLED.value})
            decision.disabled.append(disabled_rule)
            decision.reasons[rule.rule_id] = rule_reasons
        else:
            enabled_rule = Rule(**{**rule.__dict__, "status": RuleStatus.SOFT.value})
            decision.enabled.append(enabled_rule)

    return decision
