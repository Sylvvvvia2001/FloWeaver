from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsl.contracts import (
    DEFAULT_LIFECYCLE_TEMPLATES,
    DEFAULT_MARKER_DETECTORS,
    HAPProfile,
    MarkerStrength,
    Phase,
    PROFILE_SCHEMA_VERSION,
    Rule,
    RuleStatus,
    ensure_profile,
    now_utc_iso,
)
from dsl.io import dump_json
from profile_builder.cluster import cluster_evidence
from profile_builder.evidence import EvidenceBank, build_evidence_bank
from profile_builder.evidence_policy import DEFAULT_SEMANTIC_POLICY, select_semantic_evidence_bank
from profile_builder.gate import GateDecision, run_deterministic_gate
from profile_builder.hardening import auto_harden_rules
from profile_builder.llm_discovery import (
    LLMDiscoveryAdapter,
    LLMDiscoveryResult,
    build_static_index,
    merge_llm_marker_detectors,
    run_llm_candidate_discovery,
)
from profile_builder.llm_norm import normalize_rules, synthesize_profile_heuristics
from profile_builder.validation_stats import load_validation_stats


@dataclass
class BuildArtifacts:
    evidence_bank: EvidenceBank
    rules_soft: List[Rule]
    gate: GateDecision
    hardening_decisions: Dict[str, Any]
    profile: HAPProfile
    llm_discovery: LLMDiscoveryResult | None = None
    raw_evidence_bank: EvidenceBank | None = None
    evidence_policy_report: Dict[str, Any] | None = None


PROTOCOL_DETECTOR_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "BLE_CONNECT": {
        "call_attrs": ["connect"],
        "module_hints": ["bleak", "bluetooth", "gatt"],
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    "BLE_DISCONNECT": {
        "call_attrs": ["disconnect", "close"],
        "module_hints": ["bleak", "bluetooth", "gatt"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    "BLE_GATT_OP": {
        "call_attrs": ["read_gatt_char", "write_gatt_char", "start_notify", "stop_notify", "notify"],
        "module_hints": ["bleak", "bluetooth", "gatt"],
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    "BLE_SCAN": {
        "call_attrs": ["scan", "discover", "discover_services"],
        "module_hints": ["bleak", "bluetooth", "gatt"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    "BLE_RETRY_OR_TIMEOUT": {
        "call_attrs": ["sleep", "wait_for", "retry", "timeout"],
        "module_hints": ["bleak", "bluetooth", "gatt"],
        "strength": MarkerStrength.WEAK.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_HTTP_CALL": {
        "call_attrs": ["request", "get", "post", "put", "patch", "delete"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3"],
        "strength": MarkerStrength.STRONG.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_TOKEN_REFRESH": {
        "call_attrs": ["login", "authenticate", "auth", "refresh", "refresh_token", "oauth"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_429_CHECK": {
        "call_attrs": ["raise_for_status", "request", "call_api"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3"],
        "strength": MarkerStrength.WEAK.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_BACKOFF_SLEEP": {
        "call_attrs": ["sleep"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3"],
        "strength": MarkerStrength.WEAK.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_SESSION_REUSE": {
        "call_attrs": ["send_commands", "update_device_cache", "refresh_mq", "query_scenes", "trigger_scene", "request", "call_api"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3", "manager"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    "CLOUD_BATCH_CALL": {
        "call_attrs": ["batch", "batch_call", "batch_request", "bulk", "send_commands", "update_devices"],
        "module_hints": ["aiohttp", "httpx", "requests", "urllib3"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
    "LOCAL_API_READ": {
        "call_attrs": ["request", "get", "async_get", "fetch", "async_fetch", "update", "async_update", "refresh", "async_refresh"],
        "module_hints": ["aiohttp", "httpx", "requests", "websocket"],
        "strength": MarkerStrength.MEDIUM.value,
        "phase": Phase.RUNTIME.value,
    },
}

TEST_TO_MARKER_HINT = {
    "TEST_429_RETRY": "CLOUD_429_CHECK",
    "TEST_BACKOFF_SLEEP": "CLOUD_BACKOFF_SLEEP",
    "TEST_BATCH_CALL": "CLOUD_BATCH_CALL",
    "TEST_BATCH_UPDATE": "CLOUD_BATCH_CALL",
    "TEST_RATE_LIMIT": "CLOUD_429_CHECK",
    "TEST_HTTP_ERROR_RECOVERY": "CLOUD_BACKOFF_SLEEP",
}

STRICT_PROTOCOL_THRESHOLD_MARKERS = {
    "CLOUD_429_CHECK",
    "CLOUD_BACKOFF_SLEEP",
    "CLOUD_BATCH_CALL",
    "CLOUD_SESSION_REUSE",
    "LOCAL_API_READ",
}

BASELINE_PROTOCOL_DETECTORS = {
    "BLE_CONNECT",
    "BLE_GATT_OP",
    "BLE_DISCONNECT",
    "CLOUD_HTTP_CALL",
}

MAX_EVIDENCE_PER_RULE = 40

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
        if strength not in {"MUST", "SHOULD"}:
            continue
        if specificity not in {"PROTOCOL", "FRAMEWORK"}:
            continue
        if typed_anchor == "CLOUD_429_CHECK" or "docs-data-update" in path:
            counts["CLOUD_429_CHECK"] = counts.get("CLOUD_429_CHECK", 0) + 1
        if typed_anchor in {"CLOUD_BACKOFF_SLEEP", "DOC_RETRY_BACKOFF_POLICY"} or "integration_fetching_data" in path:
            counts["CLOUD_BACKOFF_SLEEP"] = counts.get("CLOUD_BACKOFF_SLEEP", 0) + 1
        if typed_anchor in {"CLOUD_BATCH_CALL", "DOC_CLOUD_BATCH_POLICY"} or "diagnostics" in path:
            counts["CLOUD_BATCH_CALL"] = counts.get("CLOUD_BATCH_CALL", 0) + 1
    return counts


def _augment_marker_detectors(bank: EvidenceBank, rules: List[Rule]) -> tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
    detectors = [dict(item) for item in DEFAULT_MARKER_DETECTORS]
    existing_ids = {str(item.get("id", "")).strip() for item in detectors}
    existing_types = {str(item.get("type", "")).strip().upper() for item in detectors}

    support_counts: Dict[str, Dict[str, float]] = {}
    for item in bank.code:
        marker = str(getattr(item, "effective_typed_anchor", "") or getattr(item, "typed_anchor", "") or item.pattern).strip().upper()
        bucket = support_counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        weight = _CODE_SIGNAL_WEIGHT.get(str(getattr(item, "signal_strength", "AST_STRONG")).upper(), 1.0)
        bucket["code"] += float(item.frequency) * weight
        if str(getattr(item, "signal_strength", "AST_STRONG")).upper() != "TEXT_WEAK":
            bucket["code_strong"] += float(item.frequency)
    for item in bank.tests:
        marker = TEST_TO_MARKER_HINT.get(str(item.pattern).strip().upper())
        if not marker:
            continue
        bucket = support_counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        bucket["test"] += float(item.frequency)
    for marker, doc_count in _doc_marker_support(bank).items():
        bucket = support_counts.setdefault(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        bucket["doc"] = bucket.get("doc", 0.0) + float(doc_count)

    def _marker_supported(marker: str) -> bool:
        counts = support_counts.get(marker, {"code": 0.0, "test": 0.0, "doc": 0.0, "code_strong": 0.0})
        code_count = float(counts.get("code", 0.0))
        code_strong = float(counts.get("code_strong", 0.0))
        test_count = float(counts.get("test", 0.0))
        doc_count = float(counts.get("doc", 0.0))
        if marker == "CLOUD_SESSION_REUSE":
            store = support_counts.get("CLOUD_SESSION_STORE", {})
            use = support_counts.get("CLOUD_SESSION_USE", {})
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

    patterns_from_bank = {marker for marker in support_counts if _marker_supported(marker)}
    hints_from_rules = {
        str(hint).strip().upper()
        for rule in rules
        for hint in rule.marker_hints
        if str(hint).strip()
    }
    desired = {marker for marker in (patterns_from_bank | hints_from_rules) & set(PROTOCOL_DETECTOR_TEMPLATES) if _marker_supported(marker)}

    added = {"baseline": [], "provisional": []}
    for marker_type in sorted(desired):
        if marker_type in existing_types:
            continue
        spec = PROTOCOL_DETECTOR_TEMPLATES[marker_type]
        detector_id = f"call:protocol:{marker_type.lower()}"
        if detector_id in existing_ids:
            continue
        detector = {
            "id": detector_id,
            "type": marker_type,
            "match": {"call_attrs": [str(item).lower() for item in spec.get("call_attrs", [])]},
            "strength": spec.get("strength", MarkerStrength.MEDIUM.value),
            "phase": spec.get("phase", Phase.RUNTIME.value),
        }
        module_hints = [str(item).lower() for item in spec.get("module_hints", [])]
        if module_hints:
            detector["match"]["module_hints"] = module_hints
        if marker_type == "CLOUD_SESSION_REUSE":
            has_close = int(support_counts.get("CLOUD_SESSION_CLOSE", {}).get("code", 0)) >= 1
            detector["strength"] = MarkerStrength.STRONG.value if has_close else MarkerStrength.MEDIUM.value
        promotion_state = "BASELINE" if marker_type in BASELINE_PROTOCOL_DETECTORS else "PROVISIONAL"
        detector["promotion_state"] = promotion_state
        detectors.append(detector)
        existing_ids.add(detector_id)
        existing_types.add(marker_type)
        added["baseline" if promotion_state == "BASELINE" else "provisional"].append(marker_type)
    return detectors, added


def _rule_marker_hints(rules: List[Rule]) -> List[str]:
    hints = {str(hint).strip().upper() for rule in rules for hint in rule.marker_hints if str(hint).strip()}
    return sorted(hints)


def _augment_lifecycle_templates(rules: List[Rule]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    templates = [dict(item) for item in DEFAULT_LIFECYCLE_TEMPLATES]
    existing = set()
    def _params_key(value: Any) -> str:
        if not isinstance(value, dict):
            return "{}"
        return json.dumps(value, sort_keys=True, ensure_ascii=True)

    for item in templates:
        params_key = _params_key(item.get("params", {}))
        if isinstance(item.get("requires_order"), list) and len(item["requires_order"]) == 2:
            src = str(item["requires_order"][0]).strip().upper()
            dst = str(item["requires_order"][1]).strip().upper()
            existing.add((src, dst, str(item.get("edge_kind", "")).upper(), params_key))
        if isinstance(item.get("requires"), list) and len(item["requires"]) == 2:
            src = str(item["requires"][0]).strip().upper()
            dst = str(item["requires"][1]).strip().upper()
            existing.add((src, dst, str(item.get("edge_kind", "")).upper(), params_key))

    derived: List[Dict[str, Any]] = []
    for rule in rules:
        for idx, tpl in enumerate(rule.hard_edge_templates):
            src = str(tpl.get("src", "")).strip().upper()
            dst = str(tpl.get("dst", "")).strip().upper()
            if not src or not dst:
                continue
            edge_kind = str(tpl.get("kind", "HARD_LIFECYCLE")).strip().upper()
            params = dict(tpl.get("params", {})) if isinstance(tpl.get("params", {}), dict) else {}
            params_key = _params_key(params)
            key = (src, dst, edge_kind, params_key)
            if key in existing:
                continue
            template_row = {
                "template_id": f"rule:{rule.rule_id}:{idx}",
                "requires_order": [src, dst],
                "edge_kind": edge_kind,
            }
            if params:
                template_row["params"] = params
            templates.append(template_row)
            existing.add(key)
            derived.append(
                {
                    "rule_id": rule.rule_id,
                    "template_id": template_row["template_id"],
                    "src": src,
                    "dst": dst,
                    "edge_kind": edge_kind,
                    "params": params,
                }
            )

    return templates, derived


def lifecycle_bucket_key(rule: Rule) -> tuple[Any, ...]:
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


def protocol_bucket_key(rule: Rule) -> tuple[Any, ...]:
    template_kinds = tuple(sorted(str(t.get("kind", "")).strip().upper() for t in rule.soft_constraint_templates if isinstance(t, dict)))
    dominant_pattern = str(rule.match_pattern.get("dominant_pattern", "")).strip().upper()
    topic = str(rule.match_pattern.get("topic", "")).strip().lower()
    return (rule.category, topic, dominant_pattern, template_kinds)


def _cap_rule_by_evidence_limit(rule: Rule) -> List[Rule]:
    evidence_ids = list(dict.fromkeys(rule.evidence_ids))
    if len(evidence_ids) <= MAX_EVIDENCE_PER_RULE:
        return [
            Rule(
                **{
                    **rule.__dict__,
                    "evidence_ids": evidence_ids,
                }
            )
        ]

    kept = evidence_ids[:MAX_EVIDENCE_PER_RULE]
    return [
        Rule(
            **{
                **rule.__dict__,
                "evidence_ids": kept,
                "provenance": {
                    **dict(rule.provenance),
                    "evidence_cap_total": len(evidence_ids),
                    "evidence_cap_kept": len(kept),
                    "evidence_cap_policy": "representative_prefix_after_canonical_sort",
                },
                "normalization_flags": sorted(set(list(rule.normalization_flags) + ["evidence_cap_applied_v1"])),
            }
        )
    ]


def _refine_rule_granularity(rules: List[Rule]) -> List[Rule]:
    refined: List[Rule] = []
    for rule in rules:
        if rule.category == "lifecycle":
            rule.provenance = {**dict(rule.provenance), "bucket_key": lifecycle_bucket_key(rule)}
        elif rule.category == "protocol":
            rule.provenance = {**dict(rule.provenance), "bucket_key": protocol_bucket_key(rule)}
        refined.extend(_cap_rule_by_evidence_limit(rule))
    return refined


def _integration_from_snapshot_path(source_path: str) -> str | None:
    normalized = str(source_path)
    for marker in ("/repo_snapshot/", "/tests_snapshot/"):
        if marker in normalized:
            tail = normalized.split(marker, 1)[1]
            return tail.split("/", 1)[0] if tail else None
    for marker in ("data/repo_snapshot/", "data/tests_snapshot/"):
        if normalized.startswith(marker):
            tail = normalized[len(marker):]
            return tail.split("/", 1)[0] if tail else None
    return None


def _anchor_for_evidence_row(row: Any) -> str:
    return str(
        getattr(row, "effective_typed_anchor", None)
        or getattr(row, "protocol_hypothesis", None)
        or getattr(row, "typed_anchor", None)
        or getattr(row, "pattern", "")
        or "UNKNOWN"
    ).strip().upper()


def _protocol_family_for_anchor(anchor: str) -> str:
    normalized = str(anchor).strip().upper()
    if normalized.startswith("BLE_"):
        return "BLE"
    if normalized.startswith("CLOUD_"):
        return "CLOUD"
    if normalized.startswith("LOCAL_"):
        return "LOCAL_API"
    if normalized.startswith("TEST_"):
        return "TEST_BEHAVIOR"
    if normalized in {"ENTRY_SETUP", "ENTRY_UNLOAD", "STATE_WRITE", "COORD_REFRESH", "SUBSCRIBE", "UNSUBSCRIBE"}:
        return "HA_FRAMEWORK"
    return "OTHER"


def _manifest_iot_class_for_integration(repo_root: Path, integration: str) -> str | None:
    manifest_path = repo_root / integration / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    iot_class = payload.get("iot_class")
    return str(iot_class).strip() if isinstance(iot_class, str) and iot_class.strip() else None


def _profile_quality_summary(bank: EvidenceBank, repo_root: Path) -> Dict[str, Any]:
    totals_by_anchor: Counter[str] = Counter()
    totals_by_family: Counter[str] = Counter()
    per_integration: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "code": 0,
            "tests": 0,
            "protocol": 0,
            "anchors": Counter(),
            "families": Counter(),
            "files": set(),
        }
    )

    for modality, rows in (("code", bank.code), ("tests", bank.tests)):
        for row in rows:
            anchor = _anchor_for_evidence_row(row)
            family = _protocol_family_for_anchor(anchor)
            totals_by_anchor[anchor] += int(getattr(row, "frequency", 1))
            totals_by_family[family] += int(getattr(row, "frequency", 1))
            integration = _integration_from_snapshot_path(str(getattr(row, "source_path", "")))
            if not integration:
                continue
            summary = per_integration[integration]
            summary[modality] += 1
            summary["anchors"][anchor] += 1
            summary["families"][family] += 1
            summary["files"].add(str(getattr(row, "source_path", "")))
            if family in {"BLE", "CLOUD", "LOCAL_API"}:
                summary["protocol"] += 1

    integration_rows: List[Dict[str, Any]] = []
    weak_coverage: List[Dict[str, Any]] = []
    for integration, row in sorted(per_integration.items()):
        iot_class = _manifest_iot_class_for_integration(repo_root, integration)
        payload = {
            "integration": integration,
            "iot_class": iot_class,
            "code_evidence": row["code"],
            "test_evidence": row["tests"],
            "protocol_evidence": row["protocol"],
            "file_count": len(row["files"]),
            "top_anchors": row["anchors"].most_common(8),
            "family_counts": dict(sorted(row["families"].items())),
        }
        integration_rows.append(payload)
        if row["code"] == 0 or row["tests"] == 0 or (iot_class and row["protocol"] == 0):
            weak_coverage.append(
                {
                    "integration": integration,
                    "iot_class": iot_class,
                    "reason": (
                        "missing_code_or_test_evidence"
                        if row["code"] == 0 or row["tests"] == 0
                        else "no_protocol_level_code_or_test_evidence"
                    ),
                }
            )

    framework_noise = sum(totals_by_family.get(key, 0) for key in {"HA_FRAMEWORK", "TEST_BEHAVIOR"})
    protocol_signal = sum(totals_by_family.get(key, 0) for key in {"BLE", "CLOUD", "LOCAL_API"})
    return {
        "policy": "manifest_iot_class_plus_protocol_signal_v1",
        "integration_count": len(integration_rows),
        "totals_by_family": dict(sorted(totals_by_family.items())),
        "top_anchors": totals_by_anchor.most_common(16),
        "protocol_signal_count": protocol_signal,
        "framework_or_test_signal_count": framework_noise,
        "protocol_to_framework_signal_ratio": round(protocol_signal / max(framework_noise, 1), 3),
        "weak_coverage": weak_coverage[:32],
        "weak_coverage_count": len(weak_coverage),
        "per_integration": integration_rows[:96],
    }


def _dump_evidence_bank(path: str | Path, bank: EvidenceBank) -> None:
    dump_json(
        path,
        {
            "docs": [doc.__dict__ for doc in bank.docs],
            "code": [item.__dict__ for item in bank.code],
            "tests": [item.__dict__ for item in bank.tests],
        },
    )


def _dump_profile_facts(path: str | Path, repo_root: Path, tests_root: Path | None) -> None:
    index = build_static_index(repo_root, tests_root)
    dump_json(
        path,
        {
            "schema_version": "profile_builder_facts/v1",
            "repo_root": str(repo_root),
            "tests_root": str(tests_root) if tests_root else None,
            "file_count": len(index.files),
            "function_count": len(index.functions),
            "files": [item.to_payload() for item in sorted(index.files.values(), key=lambda row: (row.root_kind, row.integration, row.rel_path))],
            "functions": [item.to_payload() for item in sorted(index.functions, key=lambda row: (row.integration, row.rel_path, row.qualname))],
        },
    )


class HAPProfileBuilder:
    def __init__(
        self,
        docs_root: str | Path,
        repo_root: str | Path,
        out_dir: str | Path,
        tests_root: str | Path | None = None,
    ) -> None:
        self.docs_root = Path(docs_root)
        self.repo_root = Path(repo_root)
        self.tests_root = Path(tests_root) if tests_root else None
        self.out_dir = Path(out_dir)

    def run(
        self,
        profile_id: str = "ha_profile_default",
        validation_stats: Optional[Dict[str, Dict[str, float]]] = None,
        validation_stats_path: str | Path | None = None,
        enable_llm_discovery: bool = False,
        llm_discovery_adapter: LLMDiscoveryAdapter | None = None,
        llm_discovery_payload: Any = None,
        evidence_semantic_policy: str = DEFAULT_SEMANTIC_POLICY,
    ) -> BuildArtifacts:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        loaded_stats: Dict[str, Dict[str, Any]] = load_validation_stats(validation_stats_path)
        if validation_stats:
            loaded_stats.update(validation_stats)


        raw_bank = build_evidence_bank(
            docs_root=self.docs_root,
            repo_root=self.repo_root,
            tests_root=self.tests_root,
            output_path=self.out_dir / "evidence_bank_raw.json",
        )
        _dump_profile_facts(self.out_dir / "profile_facts.json", self.repo_root, self.tests_root)

        llm_discovery: LLMDiscoveryResult | None = None
        llm_discovery_error: str | None = None
        if enable_llm_discovery or llm_discovery_adapter is not None or llm_discovery_payload is not None:
            try:
                llm_discovery = run_llm_candidate_discovery(
                    repo_root=self.repo_root,
                    tests_root=self.tests_root,
                    bank=raw_bank,
                    adapter=llm_discovery_adapter,
                    candidate_payload=llm_discovery_payload,
                    out_dir=self.out_dir,
                )
                if llm_discovery.synthetic_evidence:
                    raw_bank.code.extend(llm_discovery.synthetic_evidence)
                    _dump_evidence_bank(self.out_dir / "evidence_bank_raw.json", raw_bank)
            except Exception as exc:
                dump_json(
                    self.out_dir / "llm_candidate_verification.json",
                    {
                        "schema_version": "profile_builder_llm_discovery/verification/v1",
                        "summary": {"candidate_count": 0, "verified_count": 0, "rejected_count": 0},
                        "error": str(exc),
                    },
                )
                llm_discovery_error = str(exc)
                llm_discovery = None

        evidence_policy = select_semantic_evidence_bank(raw_bank, policy=evidence_semantic_policy)
        bank = evidence_policy.semantic_bank
        _dump_evidence_bank(self.out_dir / "evidence_bank.json", bank)
        dump_json(self.out_dir / "evidence_policy_report.json", evidence_policy.report)


        packs = cluster_evidence(bank)
        raw_rules = normalize_rules(bank, packs)
        if llm_discovery is not None and llm_discovery.rule_candidates:
            raw_rules.extend(llm_discovery.rule_candidates)
        rules_soft = _refine_rule_granularity(raw_rules)
        dump_json(self.out_dir / "rules_soft.json", [rule.__dict__ for rule in rules_soft])


        gate = run_deterministic_gate(rules_soft, bank)
        dump_json(
            self.out_dir / "gate_result.json",
            {
                "enabled": [rule.__dict__ for rule in gate.enabled],
                "disabled": [rule.__dict__ for rule in gate.disabled],
                "reasons": gate.reasons,
            },
        )


        risk_warnings: List[str] = []
        hardened_rules, hardening_decisions = auto_harden_rules(gate.enabled, validation_stats=loaded_stats)
        if not loaded_stats:
            risk_warnings.append(
                "No validation_stats provided; all gate-enabled rules kept SOFT (conservative cold-start mode)."
            )
        if llm_discovery_error:
            risk_warnings.append(f"LLM discovery failed and deterministic profile path was used: {llm_discovery_error}")

        marker_hints = _rule_marker_hints(hardened_rules)
        lifecycle_templates, derived_lifecycle = _augment_lifecycle_templates(hardened_rules)
        marker_detectors, detector_additions = _augment_marker_detectors(bank, hardened_rules)
        marker_detectors = merge_llm_marker_detectors(marker_detectors, llm_discovery)
        profile_heuristics = synthesize_profile_heuristics(bank, hardened_rules)
        llm_summary = llm_discovery.summary if llm_discovery is not None else {
            "candidate_count": 0,
            "verified_count": 0,
            "rejected_count": 0,
            "synthetic_evidence_count": 0,
            "marker_detector_count": 0,
            "rule_candidate_count": 0,
            "grounding_profile_count": 0,
        }
        profile_enhancements = {
            "rule_marker_hints": marker_hints,
            "derived_lifecycle_templates": derived_lifecycle,
            "marker_detector_policy": "default_plus_protocol_from_profile_builder",
            "rule_evidence_policy": {
                "max_evidence_per_rule": MAX_EVIDENCE_PER_RULE,
                "overflow": "cap_representative_evidence_and_keep_full_evidence_bank",
                "semantic_policy": evidence_policy.policy,
            },
            "semantic_evidence_policy": evidence_policy.report,
            "baseline_protocol_detectors_added": detector_additions["baseline"],
            "baseline_protocol_detectors_added_count": len(detector_additions["baseline"]),
            "provisional_protocol_detectors_added": detector_additions["provisional"],
            "provisional_protocol_detectors_added_count": len(detector_additions["provisional"]),
            "protocol_detectors_added": detector_additions["baseline"] + detector_additions["provisional"],
            "protocol_detectors_added_count": len(detector_additions["baseline"]) + len(detector_additions["provisional"]),
            "llm_discovery": {
                **llm_summary,
                "enabled": bool(enable_llm_discovery or llm_discovery_adapter is not None or llm_discovery_payload is not None),
                "policy": "candidate_discovery_with_local_source_verification",
                "grounding_profile_paths": (
                    [
                        str((self.out_dir / "llm_grounding_profiles_auto" / f"{integration}.json").resolve())
                        for integration in sorted(llm_discovery.grounding_profiles)
                    ]
                    if llm_discovery is not None
                    else []
                ),
                "error": llm_discovery_error,
            },
        }
        profile_quality = _profile_quality_summary(bank, self.repo_root)
        raw_profile_quality = _profile_quality_summary(raw_bank, self.repo_root)

        profile = HAPProfile(
            profile_id=profile_id,
            schema_version=PROFILE_SCHEMA_VERSION,
            created_at=now_utc_iso(),
            provenance={
                "docs_root": str(self.docs_root),
                "repo_root": str(self.repo_root),
                "tests_root": str(self.tests_root) if self.tests_root else None,
                "validation_stats_path": str(validation_stats_path) if validation_stats_path else None,
                "validation_stats_count": len(loaded_stats),
                "evidence_count": {"docs": len(bank.docs), "code": len(bank.code), "tests": len(bank.tests)},
                "raw_evidence_count": {"docs": len(raw_bank.docs), "code": len(raw_bank.code), "tests": len(raw_bank.tests)},
                "semantic_evidence_policy": evidence_policy.policy,
                "llm_discovery_enabled": bool(enable_llm_discovery or llm_discovery_adapter is not None or llm_discovery_payload is not None),
                "gate_enabled": len(gate.enabled),
                "gate_disabled": len(gate.disabled),
                "risk_warnings": risk_warnings,
                "profile_enhancements": profile_enhancements,
                "profile_quality": profile_quality,
                "raw_profile_quality": raw_profile_quality,
            },
            marker_detectors=marker_detectors,
            lifecycle_templates=lifecycle_templates,
            rules=hardened_rules,
            profile_heuristics=profile_heuristics,
        )
        ensure_profile(profile)
        dump_json(self.out_dir / "ha_profile.json", profile)
        dump_json(
            self.out_dir / "hardening_decisions.json",
            {
                "decisions": hardening_decisions,
                "risk_warnings": risk_warnings,
            },
        )

        return BuildArtifacts(
            evidence_bank=bank,
            rules_soft=rules_soft,
            gate=gate,
            hardening_decisions=hardening_decisions,
            profile=profile,
            llm_discovery=llm_discovery,
            raw_evidence_bank=raw_bank,
            evidence_policy_report=evidence_policy.report,
        )
