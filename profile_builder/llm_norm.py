from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set

from dsl.contracts import Rule, RuleStatus
from profile_builder.cluster import ClusterPack
from profile_builder.evidence import EvidenceBank

_STATE_WRITE_GUARD = "crosses_observation_boundary OR affects_entity_state"

_RULE_TEMPLATE_BY_PATTERN: Dict[str, Dict[str, object]] = {
    "ENTRY_SETUP": {
        "title": "Entry setup precedes first refresh",
        "category": "lifecycle",
        "marker_hints": ["ENTRY_SETUP", "COORD_REFRESH"],
        "hard_edge_templates": [
            {
                "src": "ENTRY_SETUP",
                "dst": "COORD_REFRESH",
                "kind": "HARD_LIFECYCLE",
            }
        ],
    },
    "ENTRY_UNLOAD": {
        "title": "Unsubscribe before entry unload",
        "category": "lifecycle",
        "marker_hints": ["ENTRY_UNLOAD", "UNSUBSCRIBE"],
        "hard_edge_templates": [
            {
                "src": "UNSUBSCRIBE",
                "dst": "ENTRY_UNLOAD",
                "kind": "HARD_LIFECYCLE",
            }
        ],
    },
    "STATE_WRITE": {
        "title": "State write is observable",
        "category": "observable",
        "marker_hints": ["STATE_WRITE"],
        "guard": _STATE_WRITE_GUARD,
    },
    "COORD_REFRESH": {
        "title": "Coordinator refresh precedes state write",
        "category": "lifecycle",
        "marker_hints": ["COORD_REFRESH", "STATE_WRITE"],
        "hard_edge_templates": [
            {
                "src": "COORD_REFRESH",
                "dst": "STATE_WRITE",
                "kind": "HARD_LIFECYCLE",
            }
        ],
    },
    "SUBSCRIBE": {
        "title": "Subscription cleanup pairing",
        "category": "cleanup",
        "marker_hints": ["SUBSCRIBE", "UNSUBSCRIBE"],
        "hard_edge_templates": [
            {
                "src": "SUBSCRIBE",
                "dst": "UNSUBSCRIBE",
                "kind": "HARD_LIFECYCLE",
            }
        ],
    },
    "BLE_CONNECT": {"title": "BLE connect precedes GATT operations", "category": "protocol", "marker_hints": ["BLE_CONNECT", "BLE_OP"]},
    "BLE_DISCONNECT": {"title": "BLE disconnect closes active session", "category": "protocol", "marker_hints": ["BLE_DISCONNECT", "BLE_OP"]},
    "BLE_GATT_OP": {"title": "BLE GATT operation is sequencing-sensitive", "category": "protocol", "marker_hints": ["BLE_GATT_OP", "BLE_OP"]},
    "BLE_SCAN": {"title": "BLE scan operation", "category": "protocol", "marker_hints": ["BLE_SCAN", "BLE_OP"]},
    "BLE_RETRY_OR_TIMEOUT": {"title": "BLE retry and timeout handling", "category": "protocol", "marker_hints": ["BLE_RETRY_OR_TIMEOUT", "BLE_OP"]},
    "LOCAL_API_READ": {"title": "Local API read", "category": "protocol", "marker_hints": ["LOCAL_API_READ"]},
    "CLOUD_HTTP_CALL": {"title": "Cloud HTTP call", "category": "protocol", "marker_hints": ["CLOUD_HTTP_CALL", "CLOUD_OP"]},
    "CLOUD_TOKEN_REFRESH": {"title": "Cloud token refresh", "category": "protocol", "marker_hints": ["CLOUD_TOKEN_REFRESH", "CLOUD_OP"]},
    "CLOUD_429_CHECK": {"title": "Cloud rate-limit check", "category": "protocol", "marker_hints": ["CLOUD_429_CHECK", "CLOUD_OP"]},
    "CLOUD_BACKOFF_SLEEP": {"title": "Cloud backoff sleep", "category": "protocol", "marker_hints": ["CLOUD_BACKOFF_SLEEP", "CLOUD_OP"]},
    "CLOUD_SESSION_REUSE": {"title": "Cloud session reuse", "category": "protocol", "marker_hints": ["CLOUD_SESSION_REUSE", "CLOUD_OP"]},
    "CLOUD_BATCH_CALL": {"title": "Cloud batch call", "category": "protocol", "marker_hints": ["CLOUD_BATCH_CALL", "CLOUD_OP"]},
}

_PROTOCOL_PATTERNS: Set[str] = {
    "BLE_OP",
    "BLE_CONNECT",
    "BLE_DISCONNECT",
    "BLE_GATT_OP",
    "BLE_SCAN",
    "BLE_RETRY_OR_TIMEOUT",
    "BLE_REUSE_CONTEXT",
    "LOCAL_API_READ",
    "CLOUD_HTTP_CALL",
    "CLOUD_TOKEN_REFRESH",
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_SESSION_REUSE",
    "CLOUD_BATCH_CALL",
}

_TEST_PATTERN_TO_DOMINANT: Dict[str, str] = {
    "TEST_ENTRY_SETUP": "ENTRY_SETUP",
    "TEST_ENTRY_UNLOAD": "ENTRY_UNLOAD",
    "TEST_CONFIG_ENTRY_NOT_READY": "ENTRY_SETUP",
    "TEST_AUTH_FAILED": "ENTRY_SETUP",
    "TEST_SUBSCRIBE_CLEANUP": "SUBSCRIBE",
    "TEST_STATE_WRITE": "STATE_WRITE",
    "TEST_MANAGER_STOP": "ENTRY_UNLOAD",
    "TEST_429_RETRY": "CLOUD_429_CHECK",
    "TEST_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
    "TEST_BATCH_CALL": "CLOUD_BATCH_CALL",
    "TEST_BATCH_UPDATE": "CLOUD_BATCH_CALL",
    "TEST_RATE_LIMIT": "CLOUD_429_CHECK",
    "TEST_HTTP_ERROR_RECOVERY": "CLOUD_BACKOFF_SLEEP",
}

_NON_PROTOCOL_TEST_ANCHORS: Set[str] = {
    "TEST_ENTRY_SETUP",
    "TEST_ENTRY_UNLOAD",
    "TEST_STATE_WRITE",
    "TEST_CLIENT_CALL_CONSTRAINT",
    "TEST_CALL_SUPPRESSION",
    "TEST_EXPECTED_CLIENT_IDLE",
    "TEST_EXPECTED_SINGLE_CALL",
    "TEST_NO_REDUNDANT_CALL",
    "TEST_SUBSCRIBE_CLEANUP",
    "TEST_RETRY_CALL",
    "TEST_BACKOFF_CALL",
    "TEST_BATCH_CALL",
}

_CODE_SIGNAL_WEIGHT: Dict[str, float] = {
    "AST_STRONG": 1.0,
    "CALL_CHAIN_STRONG": 0.8,
    "TEXT_WEAK": 0.35,
}

_CANONICAL_TOPIC_BY_PATTERN: Dict[str, str] = {
    "ENTRY_SETUP": "lifecycle",
    "COORD_REFRESH": "lifecycle",
    "ENTRY_UNLOAD": "cleanup",
    "SUBSCRIBE": "cleanup",
    "STATE_WRITE": "state_write",
}

_CANONICAL_PATTERN_ALIAS: Dict[str, str] = {
    "UNSUBSCRIBE": "ENTRY_UNLOAD",
}

_DOMINANT_PATTERN_PRIORITY: Dict[str, int] = {
    "ENTRY_SETUP": 100,
    "ENTRY_UNLOAD": 95,
    "SUBSCRIBE": 90,
    "COORD_REFRESH": 85,
    "STATE_WRITE": 80,
    "BLE_CONNECT": 70,
    "BLE_GATT_OP": 69,
    "BLE_DISCONNECT": 68,
    "BLE_OP": 67,
    "LOCAL_API_READ": 63,
    "CLOUD_HTTP_CALL": 60,
    "CLOUD_TOKEN_REFRESH": 59,
}

_DOC_NORMATIVE_WEIGHTS: Dict[str, float] = {
    "MUST": 1.0,
    "SHOULD": 0.7,
    "MAY": 0.3,
    "INFO": 0.1,
}
_DOC_KIND_WHITELIST: Set[str] = {"NORMATIVE_SENTENCE", "LIFECYCLE_SENTENCE"}
_DOC_TOPIC_MIN_WEIGHT: Dict[str, float] = {
    "protocol_ble": 0.9,
    "protocol_cloud": 0.9,
    "protocol_local": 0.9,
    "state_write": 0.55,
    "lifecycle": 0.5,
    "cleanup": 0.5,
}


def _rule_id(topic: str, evidence_ids: List[str]) -> str:
    digest = hashlib.sha1((topic + "::" + ",".join(sorted(evidence_ids))).encode("utf-8")).hexdigest()[:10]
    return f"rule_{topic}_{digest}"


def _normalized_typed_anchor(value: Any) -> str:
    return str(value or "").strip().upper()


def _doc_dominant_pattern_from_row(row: Dict[str, Any]) -> str:
    anchor = _normalized_typed_anchor(row.get("typed_anchor"))
    if not anchor or anchor in {"UNKNOWN", "DOC_NORMATIVE"}:
        return ""
    if anchor.startswith("DOC_"):
        return ""
    return anchor


def _effective_code_anchor(item: Any) -> str:
    effective = _normalized_typed_anchor(getattr(item, "effective_typed_anchor", ""))
    if effective and effective != "UNKNOWN":
        return effective
    return _normalized_typed_anchor(getattr(item, "typed_anchor", ""))


def _code_dominant_pattern(item: Any) -> str:
    anchor = _effective_code_anchor(item)
    if anchor and anchor != "UNKNOWN":
        return anchor
    return str(getattr(item, "pattern", "")).strip().upper()


def _test_dominant_pattern(item: Any) -> str:
    anchor = _normalized_typed_anchor(getattr(item, "typed_anchor", ""))
    protocol_hypothesis = _normalized_typed_anchor(getattr(item, "protocol_hypothesis", ""))
    if protocol_hypothesis:
        return protocol_hypothesis
    if anchor and anchor not in {"UNKNOWN", *_NON_PROTOCOL_TEST_ANCHORS}:
        return anchor
    return _TEST_PATTERN_TO_DOMINANT.get(str(getattr(item, "pattern", "")).strip().upper(), "")


def _row_code_pattern(row: Dict[str, Any]) -> str:
    anchor = _normalized_typed_anchor(row.get("effective_typed_anchor")) or _normalized_typed_anchor(row.get("typed_anchor"))
    if anchor and anchor != "UNKNOWN":
        return anchor
    return str(row.get("pattern", "")).strip().upper()


def _row_test_pattern(row: Dict[str, Any]) -> str:
    anchor = _normalized_typed_anchor(row.get("typed_anchor"))
    protocol_hypothesis = _normalized_typed_anchor(row.get("protocol_hypothesis"))
    if protocol_hypothesis:
        return protocol_hypothesis
    if anchor and anchor not in {"UNKNOWN", *_NON_PROTOCOL_TEST_ANCHORS}:
        return anchor
    return _TEST_PATTERN_TO_DOMINANT.get(str(row.get("pattern", "")).strip().upper(), "")


def _code_signal_weight(item: Any) -> float:
    strength = str(getattr(item, "signal_strength", "AST_STRONG")).strip().upper()
    return _CODE_SIGNAL_WEIGHT.get(strength, 1.0)


def _rule_semantic_tag(rule: Rule) -> str:
    effect_scope = str(rule.effect.get("scope", "general"))
    dominant = str(rule.match_pattern.get("dominant_pattern", "unknown")).lower()
    return f"{rule.category}:{effect_scope}:{dominant}"


def _canonical_title_for_rule(rule: Rule) -> str:
    by_id = {
        "rule_protocol_ble_budget_overlap": "BLE overlap control",
        "rule_protocol_ble_reuse_gap": "BLE session reuse cooldown",
        "rule_protocol_ble_connect_op_disconnect": "BLE connect precedes GATT operations",
        "rule_protocol_local_api_budget": "Local API read budget",
        "rule_protocol_cloud_budget_rate": "Cloud parallel budget and rate limit",
        "rule_protocol_cloud_backoff": "Cloud 429 backoff window",
        "rule_protocol_cloud_batch_reuse": "Cloud batching and session reuse",
        "rule_protocol_cloud_refresh_before_call": "Cloud token refresh precedence",
    }
    if rule.rule_id in by_id:
        return by_id[rule.rule_id]

    hints = {str(hint).upper() for hint in rule.marker_hints}
    hard_pairs = {
        (str(tpl.get("src", "")).upper(), str(tpl.get("dst", "")).upper())
        for tpl in rule.hard_edge_templates
        if isinstance(tpl, dict)
    }
    if ("ENTRY_SETUP", "COORD_REFRESH") in hard_pairs:
        return "Entry setup precedes first refresh"
    if ("UNSUBSCRIBE", "ENTRY_UNLOAD") in hard_pairs:
        return "Unsubscribe before entry unload"
    if ("SUBSCRIBE", "UNSUBSCRIBE") in hard_pairs:
        return "Subscription cleanup pairing"
    if ("COORD_REFRESH", "STATE_WRITE") in hard_pairs:
        return "Coordinator refresh precedes state write"
    if hints == {"STATE_WRITE"} or "STATE_WRITE" in hints:
        return "State write is observable"
    return rule.title


def _evidence_pattern(bank: EvidenceBank, evidence_id: str) -> str:
    row = bank.by_id().get(evidence_id, {})
    kind = str(row.get("kind", ""))
    if kind == "code":
        return _row_code_pattern(row)
    if kind == "test":
        return _row_test_pattern(row)
    if kind == "doc":
        return _doc_dominant_pattern_from_row(row)
    return ""


def _pattern_frequency(bank: EvidenceBank, pattern: str) -> float:
    total = 0.0
    for row in bank.code:
        if _code_dominant_pattern(row) == pattern:
            total += float(row.frequency) * _code_signal_weight(row)
    for row in bank.tests:
        if _test_dominant_pattern(row) == pattern:
            total += int(row.frequency)
    return total


def _pattern_support_counts(bank: EvidenceBank) -> Dict[str, Dict[str, float]]:
    counts: Dict[str, Dict[str, float]] = defaultdict(lambda: {"code": 0.0, "test": 0.0, "total": 0.0, "code_strong": 0.0})
    for row in bank.code:
        bucket = counts[_code_dominant_pattern(row)]
        weighted = float(row.frequency) * _code_signal_weight(row)
        bucket["code"] += weighted
        bucket["total"] += weighted
        if str(getattr(row, "signal_strength", "AST_STRONG")).strip().upper() != "TEXT_WEAK":
            bucket["code_strong"] += int(row.frequency)
    for row in bank.tests:
        dominant = _test_dominant_pattern(row)
        if not dominant:
            continue
        bucket = counts[dominant]
        bucket["test"] += float(row.frequency)
        bucket["total"] += float(row.frequency)
    return counts


def _doc_supports_topic(row: Dict[str, Any], topic: str) -> bool:
    path = str(row.get("source_path", "")).lower()
    text = str(row.get("text", "")).lower()
    typed_anchor = _normalized_typed_anchor(row.get("typed_anchor"))
    doc_kind = str(row.get("doc_kind", "NORMATIVE_SENTENCE")).upper()
    if doc_kind not in _DOC_KIND_WHITELIST:
        return False
    if topic == "protocol_ble":
        if typed_anchor.startswith("BLE_") or typed_anchor in {"DOC_BLE_CONNECTION_POLICY", "DOC_BLE_GATT_POLICY", "DOC_BLE_DISCONNECT_POLICY"}:
            return True
        return any(token in path or token in text for token in {"bluetooth", "ble", "gatt"})
    if topic == "protocol_cloud":
        if typed_anchor.startswith("CLOUD_") or typed_anchor in {
            "DOC_CLOUD_API_POLICY",
            "DOC_CLOUD_BATCH_POLICY",
            "DOC_RETRY_BACKOFF_POLICY",
            "DOC_CLOUD_SESSION_POLICY",
            "DOC_CLOUD_AUTH_POLICY",
        }:
            return True
        return any(
            token in path or token in text
            for token in {"cloud", "api", "http", "reauth", "diagnostics", "system_health", "data update", "429", "backoff", "retry_after"}
        )
    if topic == "protocol_local":
        if typed_anchor.startswith("LOCAL_"):
            return True
        return any(token in path or token in text for token in {"local", "lan", "http", "websocket", "api", "polling", "local push"})
    if topic == "state_write":
        if typed_anchor in {"STATE_WRITE", "DOC_STATE_UPDATE_POLICY"}:
            return True
        return any(token in path or token in text for token in {"entity", "state", "async_write_ha_state", "schedule_update_ha_state", "fetching_data"})
    if topic in {"lifecycle", "cleanup"}:
        if typed_anchor in {
            "ENTRY_SETUP",
            "ENTRY_UNLOAD",
            "SUBSCRIBE",
            "UNSUBSCRIBE",
            "SUBSCRIBE_PAIRING",
            "COORD_REFRESH",
            "DOC_ENTRY_SETUP_POLICY",
            "DOC_ENTRY_UNLOAD_POLICY",
            "DOC_COORD_REFRESH_POLICY",
            "DOC_SUBSCRIBE_PAIRING_POLICY",
        }:
            return True
        return any(token in text for token in {"setup", "unload", "unsubscribe", "cleanup", "refresh"})
    return True


def compute_doc_weight(row: Dict[str, Any], topic: str) -> float:
    strength = str(row.get("normative_strength", "INFO")).upper()
    if strength == "INFO":
        strength = str(row.get("modality", "INFO")).upper()
    score = _DOC_NORMATIVE_WEIGHTS.get(strength, 0.1)
    path = str(row.get("source_path", "")).lower()
    section = str(row.get("section_title", "")).lower()
    specificity = str(row.get("specificity", "GENERIC")).upper()
    if "rules/" in path or "quality" in path and "rule" in path:
        score += 0.2
    if specificity == "PROTOCOL":
        score += 0.25
    elif specificity == "FRAMEWORK":
        score += 0.15

    if topic == "protocol_ble":
        if "bluetooth" in path:
            score += 0.3
        elif "integration_fetching_data" in path:
            score += 0.1
        elif "entity.md" in path:
            score += 0.05
    elif topic == "protocol_cloud":
        if any(token in path for token in {"diagnostics", "integration_diagnostics", "system_health", "integration_system_health", "reauth", "docs-data-update"}):
            score += 0.2
        elif "integration_fetching_data" in path:
            score += 0.1
    elif topic == "protocol_local":
        if "integration_fetching_data" in path:
            score += 0.1
        if any(token in path for token in {"local", "polling", "websocket"}):
            score += 0.1
    elif topic == "state_write":
        if "entity.md" in path:
            score += 0.25
        elif "integration_fetching_data" in path:
            score += 0.15
        elif any(token in path for token in {"runtime-data", "docs-data-update"}):
            score += 0.05

    if any(token in section for token in {"requirements", "quality rule", "lifecycle"}):
        score += 0.1
    if specificity == "PROTOCOL" and topic.startswith("protocol_"):
        score += 0.1
    if specificity == "FRAMEWORK" and topic == "state_write":
        score += 0.1
    return score


def _select_doc_evidence(bank: EvidenceBank, topic: str, limit: int = 4) -> List[str]:
    evidence_lookup = bank.by_id()
    scored: List[tuple[float, str]] = []
    min_weight = _DOC_TOPIC_MIN_WEIGHT.get(topic, 0.4)
    for doc in bank.docs:
        row = evidence_lookup.get(doc.evidence_id, {})
        if not _doc_supports_topic(row, topic):
            continue
        weight = compute_doc_weight(row, topic)
        if weight < min_weight:
            continue
        scored.append((weight, doc.evidence_id))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [evidence_id for _, evidence_id in scored[:limit]]


def _topic_support_score(bank: EvidenceBank, topic: str, patterns: Set[str]) -> Dict[str, float]:
    evidence_lookup = bank.by_id()
    doc_score = 0.0
    for doc in bank.docs:
        row = evidence_lookup.get(doc.evidence_id, {})
        if _doc_supports_topic(row, topic):
            doc_score += compute_doc_weight(row, topic)

    code_score = 0.0
    for row in bank.code:
        if _code_dominant_pattern(row) in patterns:
            code_score += 1.0 * float(row.frequency) * _code_signal_weight(row)

    test_score = 0.0
    for row in bank.tests:
        dominant = _test_dominant_pattern(row)
        if dominant in patterns:
            test_score += 1.2 * int(row.frequency)

    return {
        "doc_score": round(doc_score, 3),
        "code_score": round(code_score, 3),
        "test_score": round(test_score, 3),
        "total_score": round(doc_score + code_score + test_score, 3),
    }


def _select_test_evidence(bank: EvidenceBank, patterns: Set[str], limit: int = 4) -> List[str]:
    rows = [row for row in bank.tests if _test_dominant_pattern(row) in patterns]
    rows.sort(
        key=lambda row: (
            -int(row.frequency),
            str(row.source_path),
            int(row.line_no),
            str(row.pattern),
            str(row.evidence_id),
        )
    )
    return [row.evidence_id for row in rows[:limit]]


def _select_state_write_evidence(bank: EvidenceBank, pack: ClusterPack) -> List[str]:
    evidence_lookup = bank.by_id()
    selected: List[str] = []
    for evidence_id in pack.evidence_ids:
        row = evidence_lookup.get(evidence_id, {})
        kind = str(row.get("kind", ""))
        pattern = str(row.get("pattern", ""))
        typed_anchor = _normalized_typed_anchor(row.get("typed_anchor"))
        specificity = str(row.get("specificity", "GENERIC")).upper()
        if kind == "code" and typed_anchor == "STATE_WRITE":
            selected.append(evidence_id)
        elif kind == "test" and typed_anchor == "STATE_WRITE":
            selected.append(evidence_id)
        elif kind == "doc" and typed_anchor == "STATE_WRITE" and specificity in {"FRAMEWORK", "PROTOCOL"}:
            selected.append(evidence_id)
    if selected:
        return sorted(set(selected))
    return sorted(set(pack.evidence_ids[:6]))


def _select_deterministic_rule_evidence(
    bank: EvidenceBank,
    pack: ClusterPack,
    dominant: str,
    canonical_topic: str,
    limit: int = 8,
) -> List[str]:
    if dominant == "STATE_WRITE":
        return _select_state_write_evidence(bank, pack)

    evidence_lookup = bank.by_id()
    selected: List[str] = []
    selected_set: Set[str] = set()
    for evidence_id in pack.evidence_ids:
        row = evidence_lookup.get(evidence_id, {})
        kind = str(row.get("kind", ""))
        if kind == "code" and str(row.get("pattern", "")) in {dominant, "STATE_WRITE", "COORD_REFRESH", "ENTRY_SETUP", "ENTRY_UNLOAD", "SUBSCRIBE", "UNSUBSCRIBE"}:
            selected.append(evidence_id)
            selected_set.add(evidence_id)
        elif kind == "test" and _TEST_PATTERN_TO_DOMINANT.get(str(row.get("pattern", ""))) == dominant:
            selected.append(evidence_id)
            selected_set.add(evidence_id)

    for evidence_id in _select_doc_evidence(bank, canonical_topic, limit=limit):
        if evidence_id in selected_set:
            continue
        selected.append(evidence_id)
        selected_set.add(evidence_id)
        if len(selected) >= limit:
            break

    if not selected:
        return sorted(set(pack.evidence_ids[:limit]))
    return selected[:limit]


def _dominant_pattern(patterns: List[str]) -> str:
    counts: Dict[str, int] = defaultdict(int)
    for pattern in patterns:
        counts[pattern] += 1
    return max(
        counts,
        key=lambda pattern: (
            counts[pattern],
            _DOMINANT_PATTERN_PRIORITY.get(pattern, 0),
            pattern,
        ),
    )


def _canonicalize_rules(rules: List[Rule]) -> List[Rule]:
    merged: Dict[str, Rule] = {}

    def _json_key(value: Any) -> str:
        return json.dumps(value, sort_keys=True, ensure_ascii=True)

    def _lifecycle_bucket_key(rule: Rule) -> tuple[Any, ...]:
        edge_templates = rule.hard_edge_templates or []
        if edge_templates:
            first = edge_templates[0]
            return (
                rule.category,
                str(first.get("src", "")).strip().upper(),
                str(first.get("dst", "")).strip().upper(),
                str(first.get("kind", "")).strip().upper(),
            )
        return (rule.category, tuple(sorted(str(h).strip().upper() for h in rule.marker_hints if str(h).strip())))

    def _protocol_bucket_key(rule: Rule) -> tuple[Any, ...]:
        template_kinds = tuple(sorted(str(t.get("kind", "")).strip().upper() for t in rule.soft_constraint_templates if isinstance(t, dict)))
        dominant_pattern = str(rule.match_pattern.get("dominant_pattern", "")).strip().upper()
        topic = str(rule.match_pattern.get("topic", "")).strip().lower()
        return (rule.category, topic, dominant_pattern, template_kinds)

    for rule in rules:
        if rule.category == "lifecycle":
            bucket_key = _lifecycle_bucket_key(rule)
        elif rule.category == "protocol":
            bucket_key = _protocol_bucket_key(rule)
        else:
            bucket_key = None
        key = _json_key(
            {
                "bucket_key": bucket_key,
                "category": rule.category,
                "effect_kind": rule.effect.get("kind"),
                "effect_scope": rule.effect.get("scope"),
                "hard_edge_templates": rule.hard_edge_templates,
                "soft_constraint_templates": rule.soft_constraint_templates,
                "marker_hints": sorted(rule.marker_hints),
                "dominant_pattern": rule.match_pattern.get("dominant_pattern"),
                "topic": rule.match_pattern.get("topic"),
            }
        )
        canonical_title = _canonical_title_for_rule(rule)
        semantic_tag = _rule_semantic_tag(rule)
        if key not in merged:
            merged_rule = Rule(
                **{
                    **rule.__dict__,
                    "title": canonical_title,
                    "semantic_tag": semantic_tag,
                    "evidence_ids": sorted(set(rule.evidence_ids)),
                    "provenance": {
                        **dict(rule.provenance),
                        "merged_from_rule_ids": [rule.rule_id],
                        "merged_titles": [rule.title],
                    },
                    "normalization_flags": sorted(set(list(rule.normalization_flags) + ["canonicalized_rule_v1"])),
                }
            )
            merged[key] = merged_rule
            continue

        existing = merged[key]
        existing.evidence_ids = sorted(set(existing.evidence_ids) | set(rule.evidence_ids))
        existing.provenance.setdefault("merged_from_rule_ids", []).append(rule.rule_id)
        existing.provenance.setdefault("merged_titles", []).append(rule.title)
        existing.normalization_flags = sorted(set(list(existing.normalization_flags) + list(rule.normalization_flags) + ["canonicalized_rule_v1"]))
        existing.confidence = max(existing.confidence, rule.confidence)

    return list(merged.values())


def _required_marker_coverage_for_pattern(bank: EvidenceBank, dominant: str) -> bool:
    requirements: Dict[str, Set[str]] = {
        "ENTRY_SETUP": {"COORD_REFRESH"},
        "ENTRY_UNLOAD": {"UNSUBSCRIBE"},
        "SUBSCRIBE": {"UNSUBSCRIBE"},
        "COORD_REFRESH": {"STATE_WRITE"},
    }
    required = requirements.get(dominant)
    if not required:
        return True
    return all(_pattern_frequency(bank, marker) > 0 for marker in required)


def _deterministic_rules(bank: EvidenceBank, packs: List[ClusterPack]) -> List[Rule]:
    rules: List[Rule] = []

    for pack in packs:
        patterns = [pattern for evidence_id in pack.evidence_ids if (pattern := _evidence_pattern(bank, evidence_id))]
        if patterns:
            dominant = _dominant_pattern(patterns)
        else:
            if "policy" in pack.topic:
                continue
            dominant = "STATE_WRITE" if "state" in pack.topic else "ENTRY_SETUP"
        dominant = _CANONICAL_PATTERN_ALIAS.get(dominant, dominant)

        if dominant in _PROTOCOL_PATTERNS:

            continue
        if not _required_marker_coverage_for_pattern(bank, dominant):
            continue

        tpl = _RULE_TEMPLATE_BY_PATTERN.get(dominant)
        if tpl is None:
            continue
        canonical_topic = _CANONICAL_TOPIC_BY_PATTERN.get(dominant, pack.topic)
        rid = _rule_id(pack.topic, pack.evidence_ids)
        evidence_ids = _select_deterministic_rule_evidence(bank, pack, dominant, canonical_topic)
        rules.append(
            Rule(
                rule_id=rid,
                title=str(tpl["title"]),
                category=str(tpl["category"]),
                status=RuleStatus.SOFT.value,
                semantic_tag=f"{str(tpl['category'])}:{canonical_topic}:{dominant.lower()}",
                marker_hints=list(tpl.get("marker_hints", [])),
                hard_edge_templates=list(tpl.get("hard_edge_templates", [])),
                soft_constraint_templates=list(tpl.get("soft_constraint_templates", [])),
                guard=str(tpl.get("guard", "runtime_metrics_available")),
                fallback="disable_optimization_for_scope",
                evidence_ids=evidence_ids,
                match_pattern={"topic": canonical_topic, "dominant_pattern": dominant},
                effect={"kind": "ordering_or_constraint", "scope": canonical_topic},
                provenance={"cluster_id": pack.cluster_id, "source_rule_kind": "deterministic"},
                normalization_flags=["deterministic_rule_v1"],
                confidence=0.8,
            )
        )

    return rules


def _top_evidence_for_patterns(bank: EvidenceBank, patterns: Set[str], topic: str, limit: int = 8) -> List[str]:
    rows = [row for row in bank.code if _code_dominant_pattern(row) in patterns]
    rows.sort(
        key=lambda row: (
            -_code_signal_weight(row),
            -int(row.frequency),
            str(row.source_path),
            int(row.line_no),
            _code_dominant_pattern(row),
            str(row.evidence_id),
        )
    )

    selected: List[str] = []
    selected_set: Set[str] = set()
    by_pattern: Dict[str, List[object]] = defaultdict(list)
    for row in rows:
        by_pattern[_code_dominant_pattern(row)].append(row)


    for pattern in sorted(by_pattern):
        row = by_pattern[pattern][0]
        if row.evidence_id not in selected_set:
            selected.append(row.evidence_id)
            selected_set.add(row.evidence_id)
        if len(selected) >= limit:
            return selected[:limit]


    for row in rows:
        if row.evidence_id in selected_set:
            continue
        selected.append(row.evidence_id)
        selected_set.add(row.evidence_id)
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for evidence_id in _select_test_evidence(bank, patterns, limit=limit):
            if evidence_id in selected_set:
                continue
            selected.append(evidence_id)
            selected_set.add(evidence_id)
            if len(selected) >= limit:
                break

    if len(selected) < limit:
        for evidence_id in _select_doc_evidence(bank, topic, limit=limit):
            if evidence_id in selected_set:
                continue
            selected.append(evidence_id)
            selected_set.add(evidence_id)
            if len(selected) >= limit:
                break
    return selected


def _protocol_pattern_presence(bank: EvidenceBank) -> Dict[str, float]:
    counts: Dict[str, float] = defaultdict(float)
    support = _pattern_support_counts(bank)
    for pattern in _PROTOCOL_PATTERNS:
        counts[pattern] = float(support.get(pattern, {}).get("total", 0.0))
    return counts


def _protocol_synthesis_rules(bank: EvidenceBank) -> List[Rule]:
    counts = _protocol_pattern_presence(bank)
    rules: List[Rule] = []
    def dominant(*patterns: str) -> str:
        for pattern in patterns:
            if counts.get(pattern, 0) > 0:
                return pattern
        return patterns[0]

    ble_patterns = {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_RETRY_OR_TIMEOUT", "BLE_REUSE_CONTEXT"}
    local_patterns = {"LOCAL_API_READ"}
    cloud_patterns = {"CLOUD_HTTP_CALL", "CLOUD_TOKEN_REFRESH", "CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP", "CLOUD_SESSION_REUSE", "CLOUD_BATCH_CALL"}
    ble_scores = _topic_support_score(bank, "protocol_ble", ble_patterns)
    local_scores = _topic_support_score(bank, "protocol_local", local_patterns)
    cloud_scores = _topic_support_score(bank, "protocol_cloud", cloud_patterns)

    ble_present = any(counts.get(pattern, 0) > 0 for pattern in {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT"}) or ble_scores["total_score"] >= 2.5
    local_present = counts.get("LOCAL_API_READ", 0) > 0 or local_scores["total_score"] >= 2.5
    cloud_present = any(counts.get(pattern, 0) > 0 for pattern in {"CLOUD_HTTP_CALL", "CLOUD_429_CHECK", "CLOUD_TOKEN_REFRESH"}) or cloud_scores["total_score"] >= 2.5

    if ble_present:
        ble_evidence = _top_evidence_for_patterns(
            bank,
            ble_patterns,
            topic="protocol_ble",
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_ble_budget_overlap",
                title="BLE overlap control",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_ble:ble_gatt_op",
                marker_hints=["BLE_CONNECT", "BLE_GATT_OP", "BLE_OP"],
                soft_constraint_templates=[
                    {
                        "kind": "BUDGET_K",
                        "scope": ["BLE_CONNECT", "BLE_GATT_OP", "BLE_OP"],
                        "params": {"resource": "BLE", "limit": 1, "mode": "soft_cap"},
                    },
                    {
                        "kind": "NO_OVERLAP",
                        "scope": ["BLE_CONNECT", "BLE_GATT_OP", "BLE_OP"],
                        "params": {"resource": "BLE_AIRTIME", "max_parallel": 1, "risk_feature": "conn_event_overlap"},
                    },
                ],
                guard="ble_timeout_rate_high OR ble_overlap_risk_high",
                fallback="serialize_ble_ops_and_disable_reuse",
                evidence_ids=ble_evidence,
                match_pattern={"topic": "protocol_ble", "dominant_pattern": dominant("BLE_GATT_OP", "BLE_CONNECT")},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_ble"},
                provenance={"source_rule_kind": "protocol_synthesis", **ble_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.7 + min(ble_scores["total_score"], 10.0) / 40.0),
            )
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_ble_reuse_gap",
                title="BLE session reuse cooldown",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_ble:ble_connect",
                marker_hints=["BLE_GATT_OP", "BLE_DISCONNECT", "BLE_CONNECT", "BLE_OP"],
                soft_constraint_templates=[
                    {
                        "kind": "SAME_SESSION_GROUP",
                        "scope": ["BLE_GATT_OP", "BLE_OP"],
                        "params": {"group_key": "device_id", "reuse_window_ms": 3000},
                    },
                    {
                        "kind": "MIN_GAP",
                        "scope": ["BLE_DISCONNECT", "BLE_CONNECT", "BLE_OP"],
                        "params": {"gap_ms": 100, "reason": "cooldown"},
                    },
                ],
                guard="ble_conn_success_rate_ok",
                fallback="disable_ble_reuse_and_insert_gap",
                evidence_ids=ble_evidence,
                match_pattern={"topic": "protocol_ble", "dominant_pattern": dominant("BLE_CONNECT", "BLE_GATT_OP")},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_ble"},
                provenance={"source_rule_kind": "protocol_synthesis", **ble_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.68 + min(ble_scores["total_score"], 10.0) / 40.0),
            )
        )

    if local_present:
        local_evidence = _top_evidence_for_patterns(
            bank,
            local_patterns,
            topic="protocol_local",
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_local_api_budget",
                title="Local API read budget",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_local:local_api_read",
                marker_hints=["LOCAL_API_READ"],
                soft_constraint_templates=[
                    {
                        "kind": "BUDGET_K",
                        "scope": ["LOCAL_API_READ"],
                        "params": {"resource": "LOCAL_PARALLEL", "limit": 4},
                    },
                    {
                        "kind": "SAME_SESSION_GROUP",
                        "scope": ["LOCAL_API_READ"],
                        "params": {"group_key": "endpoint", "reuse_window_ms": 5000},
                    },
                ],
                guard="local_endpoint_reachable",
                fallback="serialize_local_api_reads",
                evidence_ids=local_evidence,
                match_pattern={"topic": "protocol_local", "dominant_pattern": "LOCAL_API_READ"},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_local"},
                provenance={"source_rule_kind": "protocol_synthesis", **local_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.68 + min(local_scores["total_score"], 10.0) / 40.0),
            )
        )

    if cloud_present:
        cloud_evidence = _top_evidence_for_patterns(
            bank,
            cloud_patterns,
            topic="protocol_cloud",
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_cloud_budget_rate",
                title="Cloud parallel budget and rate limit",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_cloud:cloud_http_call",
                marker_hints=["CLOUD_HTTP_CALL", "CLOUD_OP"],
                soft_constraint_templates=[
                    {
                        "kind": "BUDGET_K",
                        "scope": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                        "params": {"resource": "CLOUD_PARALLEL", "limit": 4},
                    },
                    {
                        "kind": "RATE_LIMIT",
                        "scope": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                        "params": {"max_qps": 5.0, "burst": 8, "window_ms": 1000},
                    },
                ],
                guard="recent_429_rate_high",
                fallback="reduce_qps_and_parallelism",
                evidence_ids=cloud_evidence,
                match_pattern={"topic": "protocol_cloud", "dominant_pattern": dominant("CLOUD_HTTP_CALL")},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_cloud"},
                provenance={"source_rule_kind": "protocol_synthesis", **cloud_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.7 + min(cloud_scores["total_score"], 10.0) / 40.0),
            )
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_cloud_backoff",
                title="Cloud 429 backoff window",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_cloud:cloud_429_check",
                marker_hints=["CLOUD_HTTP_CALL", "CLOUD_429_CHECK", "CLOUD_BACKOFF_SLEEP", "CLOUD_OP"],
                soft_constraint_templates=[
                    {
                        "kind": "BACKOFF_WINDOW",
                        "scope": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                        "params": {"base_ms": 200, "factor": 2.0, "max_ms": 2000},
                    }
                ],
                guard="recent_429_rate_high",
                fallback="backoff_then_shrink_batch",
                evidence_ids=cloud_evidence,
                match_pattern={"topic": "protocol_cloud", "dominant_pattern": dominant("CLOUD_429_CHECK", "CLOUD_HTTP_CALL")},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_cloud"},
                provenance={"source_rule_kind": "protocol_synthesis", **cloud_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.68 + min(cloud_scores["total_score"], 10.0) / 40.0),
            )
        )
        rules.append(
            Rule(
                rule_id="rule_protocol_cloud_batch_reuse",
                title="Cloud batching and session reuse",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_cloud:cloud_batch_call",
                marker_hints=["CLOUD_HTTP_CALL", "CLOUD_BATCH_CALL", "CLOUD_SESSION_REUSE", "CLOUD_OP"],
                soft_constraint_templates=[
                    {
                        "kind": "BATCH_GROUP",
                        "scope": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                        "params": {"group_key": "endpoint", "max_batch_size": 20, "max_wait_ms": 80, "idempotent_only": True},
                    },
                    {
                        "kind": "SAME_SESSION_GROUP",
                        "scope": ["CLOUD_HTTP_CALL", "CLOUD_OP"],
                        "params": {"group_key": "host", "reuse_window_ms": 10000},
                    },
                ],
                guard="latency_budget_allows_batching AND 429_rate_low",
                fallback="disable_batching_use_singleton_calls",
                evidence_ids=cloud_evidence,
                match_pattern={"topic": "protocol_cloud", "dominant_pattern": dominant("CLOUD_BATCH_CALL", "CLOUD_HTTP_CALL")},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_cloud"},
                provenance={"source_rule_kind": "protocol_synthesis", **cloud_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.66 + min(cloud_scores["total_score"], 10.0) / 40.0),
            )
        )

        if counts.get("CLOUD_TOKEN_REFRESH", 0) > 0 and counts.get("CLOUD_HTTP_CALL", 0) > 0:
            rules.append(
                Rule(
                    rule_id="rule_protocol_cloud_refresh_before_call",
                    title="Cloud token refresh precedence",
                    category="protocol",
                    status=RuleStatus.SOFT.value,
                    semantic_tag="protocol:protocol_cloud:cloud_token_refresh",
                    marker_hints=["CLOUD_TOKEN_REFRESH", "CLOUD_HTTP_CALL", "CLOUD_OP"],
                    hard_edge_templates=[
                        {"src": "CLOUD_TOKEN_REFRESH", "dst": "CLOUD_HTTP_CALL", "kind": "HARD_LIFECYCLE", "params": {"pair_key": "host"}}
                    ],
                    guard="runtime_metrics_available",
                    fallback="disable_optimization_for_scope",
                    evidence_ids=cloud_evidence,
                    match_pattern={"topic": "protocol_cloud", "dominant_pattern": "CLOUD_TOKEN_REFRESH"},
                    effect={"kind": "ordering_or_constraint", "scope": "protocol_cloud"},
                    provenance={"source_rule_kind": "protocol_synthesis", **cloud_scores},
                    normalization_flags=["protocol_rule_v1"],
                    confidence=min(0.95, 0.72 + min(cloud_scores["total_score"], 10.0) / 40.0),
                )
            )

    if ble_present and counts.get("BLE_CONNECT", 0) > 0 and counts.get("BLE_GATT_OP", 0) > 0 and counts.get("BLE_DISCONNECT", 0) > 0:
        ble_evidence = _top_evidence_for_patterns(bank, {"BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT"}, topic="protocol_ble")
        rules.append(
            Rule(
                rule_id="rule_protocol_ble_connect_op_disconnect",
                title="BLE connect/op/disconnect sequence",
                category="protocol",
                status=RuleStatus.SOFT.value,
                semantic_tag="protocol:protocol_ble:ble_connect",
                marker_hints=["BLE_CONNECT", "BLE_GATT_OP", "BLE_DISCONNECT", "BLE_OP"],
                hard_edge_templates=[
                    {"src": "BLE_CONNECT", "dst": "BLE_GATT_OP", "kind": "HARD_LIFECYCLE", "params": {"pair_key": "device_id"}},
                    {"src": "BLE_GATT_OP", "dst": "BLE_DISCONNECT", "kind": "HARD_LIFECYCLE", "params": {"pair_key": "device_id"}},
                ],
                guard="runtime_metrics_available",
                fallback="disable_optimization_for_scope",
                evidence_ids=ble_evidence,
                match_pattern={"topic": "protocol_ble", "dominant_pattern": "BLE_GATT_OP"},
                effect={"kind": "ordering_or_constraint", "scope": "protocol_ble"},
                provenance={"source_rule_kind": "protocol_synthesis", **ble_scores},
                normalization_flags=["protocol_rule_v1"],
                confidence=min(0.95, 0.72 + min(ble_scores["total_score"], 10.0) / 40.0),
            )
        )

    return rules


def _text_snippet(text: str, limit: int = 180) -> str:
    compact = " ".join(str(text).split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)] + "..."


def _evidence_summary_row(evidence_id: str, row: Dict[str, Any]) -> Dict[str, Any]:
    kind = str(row.get("kind", ""))
    if kind == "doc":
        return {
            "evidence_id": evidence_id,
            "kind": "doc",
            "typed_anchor": row.get("typed_anchor", ""),
            "modality": row.get("modality", ""),
            "normative_strength": row.get("normative_strength", ""),
            "specificity": row.get("specificity", ""),
            "source_path": row.get("source_path", ""),
            "line_no": int(row.get("line_no", 0)),
            "text_snippet": _text_snippet(str(row.get("text", ""))),
        }
    if kind == "test":
        return {
            "evidence_id": evidence_id,
            "kind": "test",
            "pattern": row.get("pattern", ""),
            "typed_anchor": row.get("typed_anchor", ""),
            "protocol_hypothesis": row.get("protocol_hypothesis", ""),
            "test_name": row.get("test_name", ""),
            "assertion_kind": row.get("assertion_kind", ""),
            "target_symbol": row.get("target_symbol", ""),
            "specificity": row.get("specificity", ""),
            "source_path": row.get("source_path", ""),
            "line_no": int(row.get("line_no", 0)),
            "frequency": int(row.get("frequency", 1)),
        }
    return {
        "evidence_id": evidence_id,
        "kind": "code",
        "pattern": row.get("pattern", ""),
        "typed_anchor": row.get("typed_anchor", ""),
        "effective_typed_anchor": row.get("effective_typed_anchor", ""),
        "signal_strength": row.get("signal_strength", ""),
        "specificity": row.get("specificity", ""),
        "source_path": row.get("source_path", ""),
        "line_no": int(row.get("line_no", 0)),
        "frequency": int(row.get("frequency", 1)),
    }


def _cluster_pattern_stats(pack: ClusterPack, evidence_lookup: Dict[str, Dict[str, Any]]) -> tuple[Dict[str, int], str]:
    pattern_counts: Dict[str, int] = {}
    for evidence_id in pack.evidence_ids:
        row = evidence_lookup.get(evidence_id, {})
        kind = str(row.get("kind", ""))
        if kind == "code":
            pattern = _row_code_pattern(row)
        elif kind == "test":
            pattern = _row_test_pattern(row)
        elif kind == "doc":
            pattern = _doc_dominant_pattern_from_row(row)
        else:
            pattern = ""
        if not pattern:
            continue
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + int(row.get("frequency", 1))

    dominant_pattern = ""
    if pattern_counts:
        dominant_pattern = max(pattern_counts.items(), key=lambda item: (item[1], item[0]))[0]
    return pattern_counts, dominant_pattern


def _build_llm_payload(bank: EvidenceBank, packs: List[ClusterPack], max_pack_evidence: int = 8) -> Dict[str, object]:
    evidence_lookup = bank.by_id()
    pack_rows: List[Dict[str, Any]] = []
    evidence_index: Dict[str, Dict[str, Any]] = {}

    for pack in packs:
        pattern_stats, dominant_pattern = _cluster_pattern_stats(pack, evidence_lookup)
        selected_ids = list(pack.evidence_ids[:max_pack_evidence])
        cluster_evidence: List[Dict[str, Any]] = []
        for evidence_id in selected_ids:
            row = evidence_lookup.get(evidence_id)
            if row is None:
                continue
            summary_row = _evidence_summary_row(evidence_id, row)
            cluster_evidence.append(summary_row)
            evidence_index[evidence_id] = summary_row

        pack_rows.append(
            {
                "cluster_id": pack.cluster_id,
                "topic": pack.topic,
                "evidence_ids": list(pack.evidence_ids),
                "dominant_pattern_candidate": dominant_pattern,
                "pattern_stats": pattern_stats,
                "evidence": cluster_evidence,
            }
        )

    code_pattern_summary: Dict[str, int] = {}
    for row in bank.code:
        pattern = _code_dominant_pattern(row)
        code_pattern_summary[pattern] = code_pattern_summary.get(pattern, 0) + int(row.frequency)
    top_code_patterns = [
        {"pattern": pattern, "frequency": freq}
        for pattern, freq in sorted(code_pattern_summary.items(), key=lambda item: (-item[1], item[0]))[:20]
    ]

    return {
        "clusters": pack_rows,
        "evidence_index": evidence_index,
        "summary": {
            "doc_count": len(bank.docs),
            "code_count": len(bank.code),
            "test_count": len(bank.tests),
            "cluster_count": len(packs),
            "top_code_patterns": top_code_patterns,
        },
    }


def synthesize_profile_heuristics(bank: EvidenceBank, rules: List[Rule]) -> List[Dict[str, Any]]:
    heuristics: List[Dict[str, Any]] = []
    state_write_count = _pattern_frequency(bank, "STATE_WRITE")
    if state_write_count >= 10 and any(rule.match_pattern.get("dominant_pattern") == "STATE_WRITE" for rule in rules):
        heuristics.append(
            {
                "heuristic_kind": "STATE_WRITE_COALESCE_WINDOW",
                "params": {"window_ms": 120},
                "source": "cold_start_default",
                "guard": _STATE_WRITE_GUARD,
            }
        )
    return heuristics


def normalize_rules(
    bank: EvidenceBank,
    packs: List[ClusterPack],
    llm_adapter: Optional[Callable[[Dict[str, object]], List[Dict[str, object]]]] = None,
) -> List[Rule]:


    if llm_adapter is None:
        deterministic = _deterministic_rules(bank, packs)
        protocol_rules = _protocol_synthesis_rules(bank)
        dedup = {rule.rule_id: rule for rule in deterministic}
        for rule in protocol_rules:
            dedup[rule.rule_id] = rule
        return _canonicalize_rules(list(dedup.values()))

    payload = _build_llm_payload(bank, packs)

    try:
        rows = llm_adapter(payload)
        rules: List[Rule] = []
        for row in rows:
            rules.append(
                Rule(
                    rule_id=row["rule_id"],
                    title=row["title"],
                    category=row.get("category", "general"),
                    status=RuleStatus.SOFT.value,
                    marker_hints=row.get("marker_hints", []),
                    hard_edge_templates=row.get("hard_edge_templates", []),
                    soft_constraint_templates=row.get("soft_constraint_templates", []),
                    guard=row.get("guard", "runtime_metrics_available"),
                    fallback=row.get("fallback", "disable_optimization_for_scope"),
                    evidence_ids=row["evidence_ids"],
                    match_pattern=row.get("match_pattern", {}),
                    effect=row.get("effect", {}),
                )
            )
        dedup = {rule.rule_id: rule for rule in rules}
        for rule in _protocol_synthesis_rules(bank):
            dedup[rule.rule_id] = rule
        return _canonicalize_rules(list(dedup.values()))
    except Exception:
        deterministic = _deterministic_rules(bank, packs)
        protocol_rules = _protocol_synthesis_rules(bank)
        dedup = {rule.rule_id: rule for rule in deterministic}
        for rule in protocol_rules:
            dedup[rule.rule_id] = rule
        return _canonicalize_rules(list(dedup.values()))
