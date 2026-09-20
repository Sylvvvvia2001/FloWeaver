from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence, Tuple

from counterexample_layer.api.generate_counterexample import generate_counterexample
from counterexample_layer.ir.alignment_map import AlignmentMap
from counterexample_layer.ir.ir_types import IRProgram
from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema
from counterexample_layer.schema.resource_model import ResourceModel
from dsl.contracts import (
    CANONICALIZATION_VERSION,
    CERT_SCHEMA_VERSION,
    Batch,
    CounterExample,
    DependencyEdge,
    EdgeKind,
    ExecutionCertificate,
    ExecutionPlan,
    OptimizationTarget,
    Rule,
    RuleStatus,
    SoftConstraint,
    SoftConstraintKind,
    TypedDAG,
    now_utc_iso,
)
from dsl.io import dump_json, dump_jsonl
from profile_builder.hardening import HardeningThreshold, auto_harden_rules
from runtime.replay import ReplayResult
from runtime.trace import TraceCompareConfig, compare_traces, normalize_op_name, trace_compare_meta


ANCHOR_OPS = {
    "ENTRY_SETUP",
    "COORD_REFRESH",
    "STATE_WRITE",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
    "ENTRY_UNLOAD",
}

RollbackReplayFn = Callable[[ExecutionPlan], List[ReplayResult]]
ReplanFn = Callable[[TypedDAG], ExecutionPlan]

LEVEL1_STRATEGIES = [
    "reduce_parallelism",
    "disable_session_reuse",
    "disable_batching",
    "enforce_min_gap_no_overlap",
]


@dataclass
class TrustResult:
    certificate: ExecutionCertificate
    counterexamples: List[CounterExample]
    hardened_rules: List[Rule]
    hardening_decisions: Dict[str, Any]
    summary: Dict[str, object] = field(default_factory=dict)
    final_plan: ExecutionPlan | None = None
    final_dag: TypedDAG | None = None
    final_rules: List[Rule] = field(default_factory=list)
    replay_results: List[ReplayResult] = field(default_factory=list)
    rollback_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ReplayCaseSummary:
    replay: ReplayResult
    row: Dict[str, Any]
    candidate_hunks: List[object]
    hunk_payloads: List[Dict[str, Any]]
    counterexample_payload: Dict[str, Any]


class EquivalenceValidator:
    def __init__(self, integration: str, out_dir: str) -> None:
        self.integration = integration
        self.out_dir = out_dir

    @property
    def _progress_path(self) -> Path:
        return Path(self.out_dir) / "m6_progress.json"

    @property
    def _partial_certificate_path(self) -> Path:
        return Path(self.out_dir) / "execution_certificate.partial.json"

    @property
    def _trace_compare_path(self) -> Path:
        return Path(self.out_dir) / "m6_trace_compare.jsonl"

    @property
    def _counterexample_partial_path(self) -> Path:
        return Path(self.out_dir) / "counterexamples.partial.jsonl"

    @property
    def _validation_stats_path(self) -> Path:
        return Path(self.out_dir) / "validation_stats.json"

    @staticmethod
    def _trust_budget(target: OptimizationTarget | None) -> Dict[str, Any]:
        validation = target.validation if target and isinstance(target.validation, dict) else {}
        trust = validation.get("trust", {}) if isinstance(validation.get("trust", {}), dict) else {}
        return {
            "max_counterexample_cases": max(1, int(trust.get("max_counterexample_cases", 2))),
            "max_counterexample_hunks": max(1, int(trust.get("max_counterexample_hunks", 12))),
            "counterexample_budget_seconds": max(1.0, float(trust.get("counterexample_budget_seconds", 20.0))),
        }

    def _write_progress(self, phase: str, **extra: object) -> None:
        payload = {
            "phase": phase,
            "updated_at": now_utc_iso(),
            **extra,
        }
        dump_json(self._progress_path, payload)

    def _write_partial_certificate(
        self,
        status: str,
        plan: ExecutionPlan | None,
        replay_summary: Dict[str, Any] | None = None,
        counterexample_summary: Dict[str, Any] | None = None,
        **extra: object,
    ) -> None:
        payload = {
            "schema_version": CERT_SCHEMA_VERSION,
            "created_at": now_utc_iso(),
            "integration": self.integration,
            "status": status,
            "plan_summary": self._plan_summary(plan),
            "replay_summary": replay_summary,
            "counterexample_summary": counterexample_summary,
            **extra,
        }
        dump_json(self._partial_certificate_path, payload)

    @staticmethod
    def _plan_hash(plan: ExecutionPlan | None) -> str | None:
        if plan is None:
            return None
        encoded = json.dumps(plan, default=lambda value: value.__dict__, sort_keys=True).encode("utf-8")
        return hashlib.sha1(encoded).hexdigest()[:12]

    @staticmethod
    def _counterexample_id(scenario_id: str, signature: str) -> str:
        digest = hashlib.sha1(f"{scenario_id}:{signature}".encode("utf-8")).hexdigest()[:10]
        return f"cex_{digest}"

    @staticmethod
    def _event_repr_op(token: Any) -> str:
        text = str(token).strip()
        parts = text.split(":", 3)
        if len(parts) >= 3:
            return normalize_op_name(parts[2])
        return normalize_op_name(text)

    @staticmethod
    def _event_repr_target(token: Any) -> str:
        text = str(token).strip()
        parts = text.split(":", 3)
        if len(parts) >= 4:
            text = parts[3]
        normalized = text.strip().lower()
        if normalized.startswith("http://") or normalized.startswith("https://"):
            normalized = normalized.rstrip("/")
        return normalized.replace("-", ":").replace(" ", "")

    @classmethod
    def _normalized_hunk_payload(cls, hunk: object) -> Dict[str, Any]:
        return {
            "anchor": str(getattr(hunk, "anchor", "UNKNOWN")),
            "baseline_ops": [str(item) for item in getattr(hunk, "baseline_ops", [])],
            "optimized_ops": [str(item) for item in getattr(hunk, "optimized_ops", [])],
            "severity": str(getattr(hunk, "severity", "")),
        }

    @classmethod
    def _normalized_hunk_payload_from_dict(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "anchor": str(payload.get("anchor", "UNKNOWN")),
            "baseline_ops": [str(item) for item in payload.get("baseline_ops", [])],
            "optimized_ops": [str(item) for item in payload.get("optimized_ops", [])],
            "severity": str(payload.get("severity", "")),
        }

    @classmethod
    def _stable_hunk_signature(cls, hunk: object) -> str:
        return json.dumps(cls._normalized_hunk_payload(hunk), sort_keys=True, separators=(",", ":"))

    @classmethod
    def _counterexample_signature(cls, hunks: Sequence[object]) -> str:
        stable_hunks = sorted((cls._stable_hunk_signature(hunk) for hunk in hunks), key=str)
        return "|".join(stable_hunks)

    @classmethod
    def _hunk_targets_from_payload(cls, payload: Dict[str, Any]) -> set[str]:
        targets = {cls._event_repr_target(payload.get("anchor", ""))}
        for token in payload.get("baseline_ops", []) + payload.get("optimized_ops", []):
            normalized = cls._event_repr_target(token)
            if normalized:
                targets.add(normalized)
        return {item for item in targets if item}

    @classmethod
    def _sequence_ops_from_payloads(cls, payloads: Sequence[Dict[str, Any]], side: str) -> List[str]:
        sequence: List[str] = []
        key = "baseline_ops" if side == "baseline" else "optimized_ops"
        for payload in payloads:
            for token in payload.get(key, []):
                normalized = cls._event_repr_op(token)
                if normalized:
                    sequence.append(normalized)
        return sequence

    @classmethod
    def _has_sequence_inversion(cls, payloads: Sequence[Dict[str, Any]]) -> bool:
        baseline_seq = cls._sequence_ops_from_payloads(payloads, "baseline")
        optimized_seq = cls._sequence_ops_from_payloads(payloads, "optimized")
        baseline_unique = list(dict.fromkeys(baseline_seq))
        optimized_unique = list(dict.fromkeys(optimized_seq))
        common = [item for item in baseline_unique if item in set(optimized_unique)]
        if len(common) < 2:
            return False
        base_rank = {item: idx for idx, item in enumerate(baseline_unique)}
        opt_rank = {item: idx for idx, item in enumerate(optimized_unique)}
        for idx in range(len(common)):
            for jdx in range(idx + 1, len(common)):
                left = common[idx]
                right = common[jdx]
                if base_rank[left] < base_rank[right] and opt_rank[left] > opt_rank[right]:
                    return True
        return False

    @classmethod
    def _hunk_ops(cls, hunk: object) -> set[str]:
        payload = cls._normalized_hunk_payload(hunk)
        return cls._hunk_ops_from_payload(payload)

    @classmethod
    def _hunk_ops_from_payload(cls, payload: Dict[str, Any]) -> set[str]:
        ops = {cls._event_repr_op(payload["anchor"])}
        for token in payload["baseline_ops"] + payload["optimized_ops"]:
            normalized = cls._event_repr_op(token)
            if normalized:
                ops.add(normalized)
        return {item for item in ops if item}

    @classmethod
    def _counterexample_kind_from_hunks(cls, hunks: Sequence[object]) -> str:
        payloads = [cls._normalized_hunk_payload(hunk) for hunk in hunks]
        return cls._counterexample_inference_from_payloads(payloads)["kind"]

    @classmethod
    def _counterexample_kind_from_payloads(cls, payloads: Sequence[Dict[str, Any]]) -> str:
        return cls._counterexample_inference_from_payloads(payloads)["kind"]

    @classmethod
    def _counterexample_inference_from_payloads(cls, payloads: Sequence[Dict[str, Any]]) -> Dict[str, str]:
        baseline_counter: Counter[str] = Counter()
        optimized_counter: Counter[str] = Counter()
        for payload in payloads:
            baseline_ops = [cls._event_repr_op(token) for token in payload["baseline_ops"]]
            optimized_ops = [cls._event_repr_op(token) for token in payload["optimized_ops"]]
            baseline_counter.update(item for item in baseline_ops if item)
            optimized_counter.update(item for item in optimized_ops if item)
        if baseline_counter and baseline_counter == optimized_counter:
            return {"kind": "order_violation", "inferred_by": "multiset_equal_but_order_diff"}
        if cls._has_sequence_inversion(payloads):
            return {"kind": "order_violation", "inferred_by": "sequence_inversion"}
        if baseline_counter and not optimized_counter:
            return {"kind": "missing_prerequisite", "inferred_by": "optimized_ops_missing"}
        if baseline_counter and optimized_counter:
            baseline_ops = set(baseline_counter)
            optimized_ops = set(optimized_counter)
            if optimized_ops.issubset(baseline_ops) and baseline_ops != optimized_ops:
                return {"kind": "missing_prerequisite", "inferred_by": "optimized_subset_of_baseline"}
        if baseline_counter and sum((baseline_counter - optimized_counter).values()) > 0 and not (
            set(optimized_counter).difference(set(baseline_counter))
        ):
            return {"kind": "missing_prerequisite", "inferred_by": "baseline_ops_missing_in_optimized"}
        return {"kind": "semantic_delta", "inferred_by": "op_set_delta"}

    @classmethod
    def _rollback_touched_rule_ids(cls, rollback_log: List[Dict[str, Any]]) -> set[str]:
        touched: set[str] = set()
        for row in rollback_log:
            if not isinstance(row, dict):
                continue
            for key in ("disabled_rule_ids", "tightened_rule_ids"):
                values = row.get(key, [])
                if not isinstance(values, list):
                    continue
                for rule_id in values:
                    token = str(rule_id).strip()
                    if token:
                        touched.add(token)
            changes = row.get("changes", [])
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                token = str(change.get("rule_id", "")).strip()
                if token:
                    touched.add(token)
        return touched

    @classmethod
    def _rule_signal_hints(cls, rule: Rule) -> Tuple[set[str], set[str]]:
        hints = {
            normalize_op_name(item)
            for item in rule.marker_hints
            if normalize_op_name(item)
        }
        text_hints = {
            str(item).upper()
            for item in rule.marker_hints
            if str(item).strip() and len(str(item).strip()) >= 4
        }
        return hints, text_hints

    @classmethod
    def _rule_involved_in_replay_row(
        cls,
        rule: Rule,
        scenario_ops: set[str],
        scenario_text: str,
        hunk_ops: List[set[str]],
        hunk_text: List[str],
    ) -> bool:
        hints, text_hints = cls._rule_signal_hints(rule)
        if not hints and not text_hints:
            return True
        if hints:
            if hints.intersection(scenario_ops):
                return True
            if any(bool(hints.intersection(row)) for row in hunk_ops):
                return True
        if text_hints:
            if any(hint in scenario_text for hint in text_hints):
                return True
            if any(any(hint in row for hint in text_hints) for row in hunk_text):
                return True
        return False

    @staticmethod
    def _replay_alignment_status(replay: ReplayResult, tolerant_equal: bool) -> Tuple[str, int]:
        artifacts = replay.runtime_artifacts if isinstance(replay.runtime_artifacts, dict) else {}
        alignment_status = str(artifacts.get("alignment_status", "")).strip().upper()
        if not alignment_status and isinstance(artifacts.get("alignment_result"), dict):
            alignment_status = str(artifacts["alignment_result"].get("verdict", "")).strip().upper()
        suspicious_regions = artifacts.get("suspicious_regions", [])
        if not suspicious_regions and isinstance(artifacts.get("alignment_result"), dict):
            suspicious_regions = artifacts["alignment_result"].get("suspicious_regions", [])
        suspicious_count = len(suspicious_regions) if isinstance(suspicious_regions, list) else 0


        if tolerant_equal:
            alignment_status = "PROVED"
            suspicious_count = 0
        return alignment_status, suspicious_count

    @staticmethod
    def _latency_summary_for_rule(
        rule: Rule,
        replay_results: List[ReplayResult],
    ) -> Tuple[float | None, float | None]:
        del rule, replay_results
        return None, None

    @classmethod
    def _rule_validation_stats(
        cls,
        rules: List[Rule],
        replay_results: List[ReplayResult],
        compare_config: TraceCompareConfig,
        counterexamples: List[CounterExample] | None = None,
        rollback_log: List[Dict[str, Any]] | None = None,
        generated_at: str | None = None,
    ) -> Dict[str, Dict[str, Any]]:
        replay_cache: List[Dict[str, Any]] = []
        for replay in replay_results:
            diff = compare_traces(replay.baseline_trace, replay.optimized_trace, config=compare_config)
            alignment_status, suspicious_count = cls._replay_alignment_status(replay, diff.tolerant_equal)
            scenario_ops = {
                normalize_op_name(event.op)
                for event in list(replay.baseline_trace.events) + list(replay.optimized_trace.events)
                if normalize_op_name(event.op)
            }
            scenario_text = " ".join(
                f"{event.provider}:{event.op}:{event.target}"
                for event in list(replay.baseline_trace.events) + list(replay.optimized_trace.events)
            ).upper()
            replay_cache.append(
                {
                    "scenario_id": replay.scenario_id,
                    "strict_equal": diff.strict_equal,
                    "tolerant_equal": diff.tolerant_equal,
                    "alignment_status": alignment_status,
                    "suspicious_region_count": suspicious_count,
                    "scenario_ops": scenario_ops,
                    "scenario_text": scenario_text,
                    "hunk_ops": [cls._hunk_ops(hunk) for hunk in diff.diff_signature],
                    "hunk_text": [
                        " ".join(
                            cls._normalized_hunk_payload(hunk)["baseline_ops"]
                            + cls._normalized_hunk_payload(hunk)["optimized_ops"]
                        ).upper()
                        for hunk in diff.diff_signature
                    ],
                }
            )

        final_counterexamples = counterexamples or []
        rollback_touched = cls._rollback_touched_rule_ids(rollback_log or [])
        emitted_at = generated_at or now_utc_iso()
        stats: Dict[str, Dict[str, Any]] = {}
        for rule in rules:
            matched_scenarios: List[str] = []
            strict_scenarios: List[str] = []
            success_scenarios: List[str] = []
            resource_preserved_scenarios: List[str] = []
            alignment_status_counter: Counter[str] = Counter()

            for replay_row in replay_cache:
                involved_in_case = cls._rule_involved_in_replay_row(
                    rule,
                    replay_row["scenario_ops"],
                    replay_row["scenario_text"],
                    replay_row["hunk_ops"],
                    replay_row["hunk_text"],
                )
                if not involved_in_case:
                    continue

                scenario_id = str(replay_row["scenario_id"])
                matched_scenarios.append(scenario_id)
                alignment_status = str(replay_row.get("alignment_status", "")).strip().upper()
                if alignment_status:
                    alignment_status_counter[alignment_status] += 1
                if replay_row["strict_equal"]:
                    strict_scenarios.append(scenario_id)
                if replay_row["tolerant_equal"]:
                    success_scenarios.append(scenario_id)
                if alignment_status == "PROVED" and int(replay_row.get("suspicious_region_count", 0) or 0) == 0:
                    resource_preserved_scenarios.append(scenario_id)

            applied_count = len(matched_scenarios)
            final_counterexample_scenarios = sorted(
                {
                    cex.scenario_id
                    for cex in final_counterexamples
                    if cls._rule_involved_in_counterexamples(rule, [cex])
                }
            )
            n_counterexamples = len(final_counterexample_scenarios)
            rollback_touched_rule = rule.rule_id in rollback_touched
            if rollback_touched_rule and n_counterexamples == 0 and matched_scenarios:
                n_counterexamples = 1

            avg_latency_delta_ms, p95_latency_delta_ms = cls._latency_summary_for_rule(rule, replay_results)
            stats[rule.rule_id] = {
                "rule_id": rule.rule_id,
                "n_matched": len(matched_scenarios),
                "n_applied": applied_count,
                "n_success": len(success_scenarios),
                "n_counterexamples": n_counterexamples,
                "trace_preserved_rate": (len(strict_scenarios) / applied_count) if applied_count else None,
                "resource_protocol_preserved_rate": (
                    len(resource_preserved_scenarios) / applied_count
                ) if applied_count else None,
                "final_state_preserved_rate": (len(success_scenarios) / applied_count) if applied_count else None,
                "avg_latency_delta_ms": avg_latency_delta_ms,
                "p95_latency_delta_ms": p95_latency_delta_ms,
                "last_updated_at": emitted_at,
                "m6_alignment": {
                    "matched_scenarios": matched_scenarios,
                    "strict_pass_scenarios": strict_scenarios,
                    "tolerant_pass_scenarios": success_scenarios,
                    "resource_preserved_scenarios": resource_preserved_scenarios,
                    "final_counterexample_scenarios": final_counterexample_scenarios,
                    "rollback_touched": rollback_touched_rule,
                    "alignment_status_counts": dict(alignment_status_counter),
                },
            }
        return stats

    @staticmethod
    def _validation_stats_payload(
        validation_stats: Dict[str, Dict[str, Any]],
        generated_at: str,
    ) -> Dict[str, Any]:
        return {
            "schema_version": "validation_stats/v1",
            "generated_at": generated_at,
            "producer": "optimizer.m6_trust",
            "source_contract": {
                "intended_upstream": "M6 trust aggregation",
                "m6_output_files": [
                    "m6_trace_compare.jsonl",
                    "execution_certificate.json",
                    "counterexamples.json",
                    "rollback_log.json",
                    "rule_hardening_decisions.json",
                ],
                "field_alignment": {
                    "n_matched": {
                        "m6_source": ["m6_trace_compare.jsonl:scenario_id", "m6_trace_compare.jsonl:diff_signature"],
                        "derivation": "Count of scenarios whose trace or diff signature intersects the rule marker hints.",
                    },
                    "n_applied": {
                        "m6_source": ["m6_trace_compare.jsonl:scenario_id", "m6_trace_compare.jsonl:iteration"],
                        "derivation": "Count of matched scenarios evaluated under trust for this rule.",
                    },
                    "n_success": {
                        "m6_source": ["m6_trace_compare.jsonl:tolerant_equal"],
                        "derivation": "Count of matched scenarios that preserve final observable behavior.",
                    },
                    "n_counterexamples": {
                        "m6_source": ["counterexamples.json[*].scenario_id", "rollback_log.json"],
                        "derivation": "Count of final or rollback-attributed counterexamples mapped to the rule.",
                    },
                    "trace_preserved_rate": {
                        "m6_source": ["m6_trace_compare.jsonl:strict_equal"],
                        "derivation": "Fraction of matched scenarios with strict trace preservation.",
                    },
                    "resource_protocol_preserved_rate": {
                        "m6_source": [
                            "m6_trace_compare.jsonl:alignment_status",
                            "m6_trace_compare.jsonl:suspicious_region_count",
                        ],
                        "derivation": "Fraction of matched scenarios whose alignment verdict is PROVED with no suspicious regions.",
                    },
                    "final_state_preserved_rate": {
                        "m6_source": ["m6_trace_compare.jsonl:tolerant_equal"],
                        "derivation": "Fraction of matched scenarios with tolerant semantic equivalence.",
                    },
                    "avg_latency_delta_ms": {
                        "m6_source": ["execution_certificate.json:differential_summary.runtime_policy_summary"],
                        "derivation": "Optional per-rule latency delta; null when replay does not emit stable latency signals.",
                    },
                    "p95_latency_delta_ms": {
                        "m6_source": ["execution_certificate.json:differential_summary.runtime_policy_summary"],
                        "derivation": "Optional per-rule p95 latency delta; null when replay does not emit stable latency signals.",
                    },
                    "last_updated_at": {
                        "m6_source": ["execution_certificate.json:generated_at"],
                        "derivation": "Timestamp of the trust aggregation pass.",
                    },
                },
            },
            "rules": list(validation_stats.values()),
        }

    @classmethod
    def _trace_compare_config(
        cls,
        target: OptimizationTarget | None,
        plan: ExecutionPlan | None = None,
    ) -> TraceCompareConfig:
        if target is None:
            return TraceCompareConfig(parallel_action_scopes=cls._parallel_action_scopes(plan))
        observation = target.validation.get("observation", {}) if isinstance(target.validation, dict) else {}
        whitelist = observation.get("equivalence_whitelist", [])
        if not isinstance(whitelist, list):
            whitelist = []
        config = TraceCompareConfig.from_observation(
            canonicalization_version=str(observation.get("canonicalization_version", CANONICALIZATION_VERSION)),
            equivalence_whitelist=whitelist,
        )
        config.parallel_action_scopes = cls._parallel_action_scopes(plan)
        return config

    @staticmethod
    def _focus_terms(target: OptimizationTarget | None) -> List[str]:
        if target is None:
            return []
        terms: List[str] = []
        for values in target.target_anchors.values():
            for value in values:
                token = str(value).strip()
                if token:
                    terms.append(token)
        return terms

    @classmethod
    def _focus_context(cls, target: OptimizationTarget | None) -> Dict[str, Any]:
        if target is None:
            return {"ops": set(), "targets": set(), "fuzzy_terms": []}

        anchors = target.target_anchors if isinstance(target.target_anchors, dict) else {}
        op_terms = {
            normalize_op_name(item)
            for item in anchors.get("anchor_ops", [])
            if normalize_op_name(item)
        }
        target_terms: set[str] = set()
        fuzzy_terms: set[str] = set()
        for key, values in anchors.items():
            if key == "anchor_ops" or not isinstance(values, list):
                continue
            for value in values:
                token = str(value).strip()
                if not token:
                    continue
                normalized = cls._event_repr_target(token)
                if not normalized:
                    continue
                target_terms.add(normalized)
                if len(normalized) >= 4:
                    fuzzy_terms.add(normalized)
        return {
            "ops": op_terms,
            "targets": target_terms,
            "fuzzy_terms": sorted(fuzzy_terms),
        }

    @classmethod
    def _action_target_tokens(cls, action: Dict[str, Any] | None) -> set[str]:
        if not isinstance(action, dict):
            return set()
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        tokens: set[str] = set()
        for value in (
            target.get("id"),
            target.get("entity_id"),
            target.get("device_id"),
            target.get("host"),
        ):
            normalized = cls._event_repr_target(value)
            if normalized:
                tokens.add(normalized)
        return tokens

    @classmethod
    def _counterexample_target_tokens(cls, counterexamples: List[CounterExample]) -> set[str]:
        tokens: set[str] = set()
        for counterexample in counterexamples:
            for culprit in counterexample.culprit_ids:
                normalized = cls._event_repr_target(culprit)
                if normalized:
                    tokens.add(normalized)
            diff_summary = counterexample.diff_summary if isinstance(counterexample.diff_summary, dict) else {}
            hunks = diff_summary.get("hunks", [])
            if isinstance(hunks, list):
                for hunk in hunks:
                    if not isinstance(hunk, dict):
                        continue
                    normalized = cls._event_repr_target(hunk.get("anchor", ""))
                    if normalized:
                        tokens.add(normalized)
        return tokens

    @classmethod
    def _counterexample_action_ids(cls, counterexamples: List[CounterExample]) -> set[str]:
        action_ids: set[str] = set()
        for counterexample in counterexamples:
            diff_summary = counterexample.diff_summary if isinstance(counterexample.diff_summary, dict) else {}
            for key in ("baseline_trace_prefix", "optimized_trace_prefix"):
                events = diff_summary.get(key, [])
                if not isinstance(events, list):
                    continue
                for event in events:
                    if not isinstance(event, dict):
                        continue
                    params = event.get("params_abst", {}) if isinstance(event.get("params_abst", {}), dict) else {}
                    action_id = str(params.get("action_id", "")).strip()
                    if action_id:
                        action_ids.add(action_id)
        return action_ids

    @classmethod
    def _implicated_action_ids(
        cls,
        target: OptimizationTarget | None,
        counterexamples: List[CounterExample],
    ) -> set[str]:
        action_ids = cls._counterexample_action_ids(counterexamples)
        target_tokens = cls._counterexample_target_tokens(counterexamples)
        if not target_tokens or target is None:
            return action_ids
        for action in target.vdev_actions:
            if not isinstance(action, dict):
                continue
            action_id = str(action.get("action_id", "")).strip()
            if not action_id:
                continue
            if cls._action_target_tokens(action).intersection(target_tokens):
                action_ids.add(action_id)
        return action_ids

    @classmethod
    def _focused_hunks(cls, diff_signature: Sequence[object], target: OptimizationTarget | None) -> List[object]:
        focus = cls._focus_context(target)
        lifecycle_ops = {normalize_op_name(op) for op in ANCHOR_OPS if normalize_op_name(op)}
        no_focus = not focus["ops"] and not focus["targets"] and not focus["fuzzy_terms"]
        focused = []
        for hunk in diff_signature:
            payload = cls._normalized_hunk_payload(hunk)
            text = " ".join(payload["baseline_ops"] + payload["optimized_ops"]).lower()
            hunk_ops = cls._hunk_ops_from_payload(payload)
            hunk_targets = cls._hunk_targets_from_payload(payload)
            lifecycle_hit = bool(hunk_ops.intersection(lifecycle_ops))
            op_hit = bool(hunk_ops.intersection(focus["ops"]))
            target_hit = no_focus or bool(hunk_targets.intersection(focus["targets"]))
            fuzzy_hit = any(term in text for term in focus["fuzzy_terms"])
            if lifecycle_hit or op_hit or target_hit or fuzzy_hit:
                focused.append(hunk)
        return focused

    @staticmethod
    def _coerce_ir_program(payload: Any) -> IRProgram | None:
        if isinstance(payload, IRProgram):
            return payload
        if isinstance(payload, dict):
            return IRProgram.from_dict(payload)
        return None

    @staticmethod
    def _coerce_alignment_map(payload: Any) -> AlignmentMap | None:
        if isinstance(payload, AlignmentMap):
            return payload
        if isinstance(payload, dict):
            return AlignmentMap.from_dict(payload)
        return None

    @staticmethod
    def _coerce_observation_schema(
        payload: Any,
        target: OptimizationTarget | None,
    ) -> CounterexampleObservationSchema:
        if isinstance(payload, CounterexampleObservationSchema):
            return payload
        if isinstance(payload, dict):
            return CounterexampleObservationSchema.from_dict(payload)
        return CounterexampleObservationSchema.from_optimization_target(target)

    @staticmethod
    def _coerce_resource_model(
        payload: Any,
        observation_schema: CounterexampleObservationSchema,
    ) -> ResourceModel:
        if isinstance(payload, ResourceModel):
            return payload
        if isinstance(payload, dict):
            return ResourceModel.from_dict(payload)
        return ResourceModel.from_observation_schema(observation_schema)

    @classmethod
    def _counterexample_payload(
        cls,
        replay: ReplayResult,
        optimization_target: OptimizationTarget | None,
        compare_config: TraceCompareConfig,
    ) -> Dict[str, Any]:
        artifacts = replay.runtime_artifacts if isinstance(replay.runtime_artifacts, dict) else {}
        baseline_ir = cls._coerce_ir_program(artifacts.get("baseline_ir"))
        optimized_ir = cls._coerce_ir_program(artifacts.get("optimized_ir"))
        alignment_map = cls._coerce_alignment_map(artifacts.get("alignment_map"))
        observation_schema = cls._coerce_observation_schema(artifacts.get("observation_schema"), optimization_target)
        resource_model = cls._coerce_resource_model(artifacts.get("resource_model"), observation_schema)
        environment_model = dict(artifacts.get("environment_model", {}))
        if not environment_model:
            environment_model = {
                "inputs": {"scenario_id": replay.scenario_id},
                "request_params": {},
                "device_results": {},
                "toggles": {},
                "framework_events": [],
                "assumptions": [f"scenario:{replay.scenario_id}"],
                "branches": {},
            }
        suspicious_regions = [dict(item) for item in artifacts.get("suspicious_regions", [])]
        alignment_status = str(artifacts.get("alignment_status", "")).strip().upper()
        if not alignment_status and isinstance(artifacts.get("alignment_result"), dict):
            alignment_status = str(artifacts["alignment_result"].get("verdict", "")).strip().upper()
        if not suspicious_regions and isinstance(artifacts.get("alignment_result"), dict):
            suspicious_regions = [
                dict(item)
                for item in artifacts["alignment_result"].get("suspicious_regions", [])
            ]
        should_run = (
            bool(artifacts.get("run_counterexample_search"))
            or alignment_status in {"PARTIAL", "UNKNOWN", "VIOLATED"}
            or bool(suspicious_regions)
        )
        return {
            "baseline_ir": baseline_ir,
            "optimized_ir": optimized_ir,
            "alignment_map": alignment_map,
            "observation_schema": observation_schema,
            "resource_model": resource_model,
            "environment_model": environment_model,
            "suspicious_regions": suspicious_regions,
            "alignment_status": alignment_status,
            "suspicious_region_count": len(suspicious_regions),
            "should_run": should_run,
            "compare_config": compare_config,
        }

    @staticmethod
    def _counterexample_search_required(
        diff_tolerant_equal: bool,
        payload: Dict[str, Any],
    ) -> bool:
        alignment_status = str(payload.get("alignment_status", "")).strip().upper()
        suspicious_regions = payload.get("suspicious_regions", [])
        return ((not diff_tolerant_equal) and alignment_status != "PROVED") or bool(suspicious_regions)

    @staticmethod
    def _synthetic_witness_summary(case: ReplayCaseSummary) -> Dict[str, Any]:
        return {
            "counterexample_verdict": "TRACE_ONLY",
            "violated_property": "TRACE_MISMATCH" if not case.row["tolerant_equal"] else "UNSUPPORTED_ALIGNMENT",
            "divergence_point": {"scenario_id": case.replay.scenario_id},
            "minimal_conditions": [],
            "suspicious_region_id": None,
            "refinement_hint": "trace_compare_only",
            "baseline_trace_prefix": [],
            "optimized_trace_prefix": [],
            "baseline_state_at_divergence": {},
            "optimized_state_at_divergence": {},
            "environment_assumptions": {},
            "input_assumptions": {},
        }

    @classmethod
    def _materialize_counterexample(
        cls,
        case: ReplayCaseSummary,
        witness: Any | None = None,
    ) -> CounterExample:
        inference = cls._counterexample_inference_from_payloads(case.hunk_payloads)
        signature = cls._counterexample_signature(case.candidate_hunks)
        witness_summary = cls._synthetic_witness_summary(case) if witness is None else {
            "counterexample_verdict": witness.verdict,
            "violated_property": witness.violated_property,
            "divergence_point": dict(witness.divergence_point),
            "minimal_conditions": list(witness.minimal_conditions),
            "suspicious_region_id": witness.suspicious_region_id,
            "refinement_hint": witness.refinement_hint,
            "baseline_trace_prefix": list(witness.baseline_trace_prefix),
            "optimized_trace_prefix": list(witness.optimized_trace_prefix),
            "baseline_state_at_divergence": dict(witness.baseline_state_at_divergence),
            "optimized_state_at_divergence": dict(witness.optimized_state_at_divergence),
            "environment_assumptions": dict(witness.environment_assumptions),
            "input_assumptions": dict(witness.input_assumptions),
        }
        diff_summary = {
            "kind": str(inference.get("kind", "semantic_delta")).strip().lower() or "semantic_delta",
            "inferred_by": (
                witness.refinement_hint
                if witness is not None and getattr(witness, "refinement_hint", None)
                else str(inference.get("inferred_by", "")) or "trace_compare_only"
            ),
            "hunks": case.hunk_payloads,
            **witness_summary,
        }
        return CounterExample(
            counterexample_id=cls._counterexample_id(case.replay.scenario_id, signature),
            scenario_id=case.replay.scenario_id,
            violated_assertion="observable_semantic_equivalence",
            culprit_ids=sorted({str(item["anchor"]) for item in case.hunk_payloads}),
            diff_summary=diff_summary,
            alignment_status=str(case.counterexample_payload.get("alignment_status", "") or "").strip().upper() or None,
            suspicious_region_count=int(case.counterexample_payload.get("suspicious_region_count", 0) or 0),
        )

    @staticmethod
    def _select_counterexample_cases(
        cases: List[ReplayCaseSummary],
        max_cases: int,
    ) -> List[ReplayCaseSummary]:
        ranked = sorted(
            cases,
            key=lambda case: (
                0 if not case.row.get("strict_equal", False) else 1,
                0 if case.counterexample_payload.get("suspicious_regions") else 1,
                len(case.candidate_hunks),
                str(case.replay.scenario_id),
            ),
        )
        return ranked[:max_cases]

    @staticmethod
    def _flatten_plan_actions(plan: ExecutionPlan) -> List[str]:
        return TrustLayer._plan_execution_order(plan)

    @staticmethod
    def _chunked(items: List[str], size: int) -> List[List[str]]:
        size = max(1, size)
        return [items[idx : idx + size] for idx in range(0, len(items), size)]

    @staticmethod
    def _append_fallback(
        batch: Batch,
        kind: str,
        mode: str,
        scope: List[str] | None = None,
        params: Dict[str, Any] | None = None,
    ) -> None:
        if not isinstance(batch.fallback, list):
            legacy = batch.fallback if isinstance(batch.fallback, dict) else {}
            converted: List[Dict[str, Any]] = []
            for key, value in legacy.items():
                values = value if isinstance(value, list) else [value]
                for entry in values:
                    converted.append({"kind": str(key), "scope": [], "action": str(entry), "params": {}})
            batch.fallback = converted

        row = {
            "kind": str(kind),
            "scope": [str(token) for token in (scope or []) if str(token).strip()],
            "action": str(mode),
            "params": dict(params or {}),
        }
        if row not in batch.fallback:
            batch.fallback.append(row)

    @staticmethod
    def _append_guard(batch: Batch, kind: str, expr: str, scope: List[str] | None = None) -> None:
        if not isinstance(batch.guards, list):
            batch.guards = []
        normalized: List[Dict[str, Any]] = []
        for item in batch.guards:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "kind": str(item.get("kind", "")),
                        "scope": [str(token) for token in item.get("scope", [])],
                        "expr": str(item.get("expr", "true")),
                        "enforced": bool(item.get("enforced", True)),
                    }
                )
            else:
                normalized.append({"kind": "", "scope": [], "expr": str(item), "enforced": True})
        batch.guards = normalized

        row = {
            "kind": str(kind),
            "scope": [str(token) for token in (scope or [])],
            "expr": str(expr),
            "enforced": True,
        }
        if row not in batch.guards:
            batch.guards.append(row)

    @staticmethod
    def _rows_for_group(action_ids: List[str], rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        action_set = {str(action_id) for action_id in action_ids}
        relevant: List[Dict[str, Any]] = []
        for row in rows:
            scope = [str(token) for token in row.get("scope", [])]
            if not scope or action_set.intersection(scope):
                relevant.append(row)
        return relevant

    @staticmethod
    def _serialize_targets_for_group(
        action_ids: List[str],
        fallback_rows: List[Dict[str, Any]],
    ) -> List[str]:
        action_set = {str(action_id) for action_id in action_ids}
        serialize_targets: set[str] = set()
        for row in fallback_rows:
            mode = str(row.get("action", ""))
            scope = [str(token) for token in row.get("scope", []) if str(token) in action_set]
            scope_targets = set(scope) if scope else set(action_ids)
            if mode in {"preserve_action_order", "force_pick_despite_soft_conflicts"}:
                serialize_targets.update(scope_targets)
        return [action_id for action_id in action_ids if action_id in serialize_targets]

    @staticmethod
    def _group_requires_order_preservation(
        action_ids: List[str],
        fallback_rows: List[Dict[str, Any]],
    ) -> bool:
        action_set = {str(action_id) for action_id in action_ids}
        for row in fallback_rows:
            mode = str(row.get("action", ""))
            if mode not in {"preserve_action_order", "force_topological_local_order"}:
                continue
            scope = [str(token) for token in row.get("scope", []) if str(token) in action_set]
            if scope or not row.get("scope"):
                return True
        return False

    @classmethod
    def _group_execution_layout(cls, batch: Batch, group: List[str]) -> Tuple[List[str], List[str]]:
        fallback_rows = cls._rows_for_group(group, batch.fallback if isinstance(batch.fallback, list) else [])
        if cls._group_requires_order_preservation(group, fallback_rows):
            return [], list(group)
        serial_ids = cls._serialize_targets_for_group(group, fallback_rows)
        parallel_ids = [action_id for action_id in group if action_id not in set(serial_ids)]
        return parallel_ids, serial_ids

    @classmethod
    def _parallel_action_scopes(cls, plan: ExecutionPlan | None) -> List[List[str]]:
        if plan is None:
            return []
        scopes: List[List[str]] = []
        for batch in plan.ordered_batches:
            for group in batch.parallel_groups:
                ordered_group = [str(action_id).strip() for action_id in group if str(action_id).strip()]
                if len(ordered_group) < 2:
                    continue
                parallel_ids, _ = cls._group_execution_layout(batch, ordered_group)
                if len(parallel_ids) > 1:
                    scopes.append(list(parallel_ids))
        return scopes

    @classmethod
    def _plan_execution_order(cls, plan: ExecutionPlan | None) -> List[str]:
        ordered: List[str] = []
        if plan is None:
            return ordered
        for batch in plan.ordered_batches:
            for group in batch.parallel_groups:
                ordered_group = [str(action_id).strip() for action_id in group if str(action_id).strip()]
                if not ordered_group:
                    continue
                parallel_ids, serial_ids = cls._group_execution_layout(batch, ordered_group)
                ordered.extend(parallel_ids)
                ordered.extend(serial_ids)
        return ordered

    @classmethod
    def _plan_action_execution_contexts(
        cls,
        plan: ExecutionPlan | None,
    ) -> Dict[str, Dict[str, Any]]:
        contexts: Dict[str, Dict[str, Any]] = {}
        if plan is None:
            return contexts
        for batch_idx, batch in enumerate(plan.ordered_batches):
            for group_idx, group in enumerate(batch.parallel_groups):
                ordered_group = [str(action_id).strip() for action_id in group if str(action_id).strip()]
                if not ordered_group:
                    continue
                parallel_ids, serial_ids = cls._group_execution_layout(batch, ordered_group)
                for order_idx, action_id in enumerate(parallel_ids):
                    contexts[action_id] = {
                        "batch_idx": batch_idx,
                        "group_idx": group_idx,
                        "phase": "parallel",
                        "order_idx": order_idx,
                    }
                offset = len(parallel_ids)
                for order_idx, action_id in enumerate(serial_ids, start=offset):
                    contexts[action_id] = {
                        "batch_idx": batch_idx,
                        "group_idx": group_idx,
                        "phase": "serial",
                        "order_idx": order_idx,
                    }
        return contexts

    @staticmethod
    def _action_rank(target: OptimizationTarget | None) -> Dict[str, int]:
        if target is None:
            return {}
        rank: Dict[str, int] = {}
        for idx, action in enumerate(target.vdev_actions):
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                rank[action_id] = idx
        return rank

    @staticmethod
    def _action_index(target: OptimizationTarget | None) -> Dict[str, Dict[str, Any]]:
        if target is None:
            return {}
        index: Dict[str, Dict[str, Any]] = {}
        for action in target.vdev_actions:
            if not isinstance(action, dict):
                continue
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                index[action_id] = action
        return index

    @staticmethod
    def _normalized_action_protocol(action: Dict[str, Any] | None) -> str:
        if not isinstance(action, dict):
            return "UNKNOWN"
        protocol = str(action.get("protocol", "")).strip().upper()
        if protocol == "MQTT":
            protocol = "LOCAL"
        return protocol or "UNKNOWN"

    @staticmethod
    def _action_is_writeback(action: Dict[str, Any] | None) -> bool:
        if not isinstance(action, dict):
            return False
        protocol = str(action.get("protocol", "")).strip().upper()
        if protocol == "HA":
            return True
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        return str(target.get("kind", "")).strip().lower() == "ha_entity"

    @classmethod
    def _action_is_read_like(cls, action: Dict[str, Any] | None) -> bool:
        if not isinstance(action, dict) or cls._action_is_writeback(action):
            return False
        strings = cls._action_semantic_strings(action)
        tokens = cls._action_semantic_tokens(strings)
        read_markers = {
            "status",
            "get",
            "get_state",
            "read",
            "read_runtime",
            "read_sensor",
            "read_status",
            "read_last_message",
            "fetch",
            "list",
            "refresh",
            "refresh_cover",
        }
        if any(value in read_markers for value in strings):
            return True
        if any(value.endswith(".status") for value in strings):
            return True
        return bool(tokens & read_markers)

    @staticmethod
    def _action_semantic_strings(action: Dict[str, Any] | None) -> List[str]:
        if not isinstance(action, dict):
            return []
        target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
        exec_cfg = action.get("exec", {}) if isinstance(action.get("exec", {}), dict) else {}
        fields = [
            action.get("type"),
            action.get("action_kind"),
            action.get("kind"),
            exec_cfg.get("service"),
            exec_cfg.get("kind"),
            target.get("kind"),
            target.get("id"),
            target.get("entity_id"),
            target.get("endpoint"),
        ]
        values: List[str] = []
        for field in fields:
            token = str(field).strip().lower()
            if token:
                values.append(token)
        return values

    @staticmethod
    def _action_semantic_tokens(strings: List[str]) -> set[str]:
        tokens: set[str] = set(strings)
        for value in strings:
            for token in re.split(r"[^a-z0-9]+", value):
                normalized = str(token).strip().lower()
                if normalized:
                    tokens.add(normalized)
        return tokens

    @classmethod
    def _action_is_control_like(cls, action: Dict[str, Any] | None) -> bool:
        if not isinstance(action, dict) or cls._action_is_writeback(action) or cls._action_is_read_like(action):
            return False
        strings = cls._action_semantic_strings(action)
        control_tokens = (
            "turn_on",
            "turn_off",
            "toggle",
            "set_",
            "open",
            "close",
            "play_media",
            "media_play",
            "media_pause",
            "volume",
            "brightness",
            "color_temp",
            "hs_color",
            "rgb_color",
            "cover_position",
            "cover_tilt",
            "hvac_mode",
            "temperature",
            "fan_mode",
            "percentage",
            "preset_mode",
            "swing_mode",
            "source",
        )
        return any(token in value for value in strings for token in control_tokens)

    @classmethod
    def _action_phase_map(cls, target: OptimizationTarget | None) -> Dict[str, str]:
        phases: Dict[str, str] = {}
        if target is None:
            return phases
        ordered_actions: List[Tuple[str, Dict[str, Any]]] = []
        for action in target.vdev_actions:
            if not isinstance(action, dict):
                continue
            action_id = str(action.get("action_id", "")).strip()
            if action_id:
                ordered_actions.append((action_id, action))

        last_control_idx = -1
        for idx, (_, action) in enumerate(ordered_actions):
            if cls._action_is_writeback(action):
                continue
            if cls._action_is_control_like(action):
                last_control_idx = idx

        for idx, (action_id, action) in enumerate(ordered_actions):
            if not isinstance(action, dict):
                continue
            if cls._action_is_writeback(action):
                phases[action_id] = "writeback"
                continue
            if cls._action_is_control_like(action):
                phases[action_id] = "control"
                continue
            if last_control_idx >= 0 and idx > last_control_idx:
                phases[action_id] = "post_control_verification"
                continue
            phases[action_id] = "pre_control_acquisition"
        return phases

    @classmethod
    def _level3_patch_action_order(
        cls,
        plan: ExecutionPlan,
        optimization_target: OptimizationTarget | None,
    ) -> List[str]:
        action_order: List[str] = cls._flatten_plan_actions(plan)
        action_order = list(dict.fromkeys(item for item in action_order if item))
        if optimization_target is None:
            return action_order

        target_order = [str(action.get("action_id", "")).strip() for action in optimization_target.vdev_actions]
        target_order = [item for item in target_order if item]
        for action_id in target_order:
            if action_id not in action_order:
                action_order.append(action_id)

        action_phase = cls._action_phase_map(optimization_target)
        verification_actions = [
            action_id
            for action_id in target_order
            if action_phase.get(action_id) == "post_control_verification" and action_id in action_order
        ]
        has_control = any(phase == "control" for phase in action_phase.values())
        if not verification_actions and not has_control:
            return target_order
        if not verification_actions:
            return action_order

        verification_set = set(verification_actions)
        reordered: List[str] = []
        injected_verification = False
        for action_id in action_order:
            if action_id in verification_set:
                if not injected_verification:
                    reordered.extend(verification_actions)
                    injected_verification = True
                continue
            reordered.append(action_id)
        if not injected_verification:
            reordered.extend(verification_actions)
        return reordered

    @classmethod
    def _batch_protocol_scopes(
        cls,
        batch: Batch,
        action_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        scopes: Dict[str, List[str]] = {}
        ordered: List[str] = []
        for group in batch.parallel_groups:
            for action_id in group:
                action_token = str(action_id).strip()
                if action_token:
                    ordered.append(action_token)
        for action_id in ordered:
            protocol = cls._normalized_action_protocol(action_index.get(action_id))
            scopes.setdefault(protocol, [])
            if action_id not in scopes[protocol]:
                scopes[protocol].append(action_id)
        return scopes

    @staticmethod
    def _roll_reason(counterexamples: List[CounterExample]) -> Dict[str, Any]:
        anchors: List[str] = []
        for cex in counterexamples:
            anchors.extend(str(item) for item in cex.culprit_ids)
        return {
            "counterexample_ids": [cex.counterexample_id for cex in counterexamples],
            "scenario_ids": [cex.scenario_id for cex in counterexamples],
            "culprit_anchors": sorted(set(anchors)),
        }

    def _run_trace_compare(
        self,
        replay_results: List[ReplayResult],
        optimization_target: OptimizationTarget | None,
        compare_config: TraceCompareConfig,
        trace_compare_jsonl_path: str | None = None,
        iteration: int = 0,
    ) -> Tuple[int, int, List[ReplayCaseSummary], List[Dict[str, Any]]]:
        strict_pass = 0
        tolerant_pass = 0
        replay_rows: List[Dict[str, Any]] = []
        failing_cases: List[ReplayCaseSummary] = []

        self._write_progress(
            "trace_compare_start",
            iteration=iteration,
            replay_count=len(replay_results),
        )

        for idx, replay in enumerate(replay_results):
            diff = compare_traces(replay.baseline_trace, replay.optimized_trace, config=compare_config)
            counterexample_payload = self._counterexample_payload(replay, optimization_target, compare_config)
            if diff.tolerant_equal:
                counterexample_payload["alignment_status"] = "PROVED"
                counterexample_payload["suspicious_regions"] = []
                counterexample_payload["suspicious_region_count"] = 0
                counterexample_payload["should_run"] = False
            row = {
                "iteration": iteration,
                "scenario_id": replay.scenario_id,
                "strict_equal": diff.strict_equal,
                "tolerant_equal": diff.tolerant_equal,
                "compare_meta": dict(diff.meta),
                "diff_signature": [hunk.__dict__ for hunk in diff.diff_signature],
                "alignment_status": str(counterexample_payload.get("alignment_status", "")),
                "suspicious_region_count": int(counterexample_payload.get("suspicious_region_count", 0) or 0),
            }
            replay_rows.append(row)
            if trace_compare_jsonl_path:
                dump_jsonl(trace_compare_jsonl_path, [row], append=True)

            if diff.strict_equal:
                strict_pass += 1
            if diff.tolerant_equal:
                tolerant_pass += 1

            focused_hunks = self._focused_hunks(diff.diff_signature, optimization_target)
            candidate_hunks = list(focused_hunks) if focused_hunks else list(diff.diff_signature)
            hunk_payloads = [
                self._normalized_hunk_payload(hunk)
                for hunk in sorted(candidate_hunks, key=self._stable_hunk_signature)
            ]
            if (not diff.tolerant_equal) or self._counterexample_search_required(diff.tolerant_equal, counterexample_payload):
                failing_cases.append(
                    ReplayCaseSummary(
                        replay=replay,
                        row=row,
                        candidate_hunks=list(candidate_hunks),
                        hunk_payloads=hunk_payloads,
                        counterexample_payload=counterexample_payload,
                    )
                )
            self._write_progress(
                "trace_compare_case_done",
                iteration=iteration,
                case_idx=idx,
                scenario_id=replay.scenario_id,
                strict_equal=diff.strict_equal,
                tolerant_equal=diff.tolerant_equal,
            )

        return strict_pass, tolerant_pass, failing_cases, replay_rows

    def _materialize_counterexamples(
        self,
        cases: List[ReplayCaseSummary],
        optimization_target: OptimizationTarget | None,
        counterexample_jsonl_path: str | None = None,
        iteration: int = 0,
    ) -> List[CounterExample]:
        budget = self._trust_budget(optimization_target)
        selected_cases = self._select_counterexample_cases(
            [
                case
                for case in cases
                if self._counterexample_search_required(case.row["tolerant_equal"], case.counterexample_payload)
                and len(case.candidate_hunks) <= budget["max_counterexample_hunks"]
            ],
            max_cases=budget["max_counterexample_cases"],
        )
        selected_ids = {id(case) for case in selected_cases}
        counterexamples: List[CounterExample] = []
        started_at = time.monotonic()

        for idx, case in enumerate(cases):
            if case.row["tolerant_equal"]:
                self._write_progress(
                    "counterexample_skipped",
                    iteration=iteration,
                    case_idx=idx,
                    scenario_id=case.replay.scenario_id,
                    reason="tolerant_equal",
                    candidate_hunk_count=len(case.candidate_hunks),
                )
                continue
            run_search = False
            skip_reason = ""
            if id(case) in selected_ids:
                if (time.monotonic() - started_at) >= float(budget["counterexample_budget_seconds"]):
                    skip_reason = "budget_exhausted"
                else:
                    run_search = True
            elif self._counterexample_search_required(case.row["tolerant_equal"], case.counterexample_payload):
                skip_reason = "deferred_by_case_budget"

            witness = None
            if run_search:
                self._write_progress(
                    "counterexample_start",
                    iteration=iteration,
                    case_idx=idx,
                    scenario_id=case.replay.scenario_id,
                    candidate_hunk_count=len(case.candidate_hunks),
                )
                missing_inputs = [
                    name
                    for name in ("baseline_ir", "optimized_ir", "alignment_map")
                    if case.counterexample_payload.get(name) is None
                ]
                if missing_inputs:
                    raise ValueError(
                        "ReplayResult.runtime_artifacts is missing counterexample inputs: "
                        + ", ".join(missing_inputs)
                    )
                witness = generate_counterexample(
                    baseline_ir=case.counterexample_payload["baseline_ir"],
                    optimized_ir=case.counterexample_payload["optimized_ir"],
                    alignment_map=case.counterexample_payload["alignment_map"],
                    observation_schema=case.counterexample_payload["observation_schema"],
                    environment_model=case.counterexample_payload["environment_model"],
                    resource_model=case.counterexample_payload["resource_model"],
                    suspicious_regions=case.counterexample_payload["suspicious_regions"],
                )
                self._write_progress(
                    "counterexample_done",
                    iteration=iteration,
                    case_idx=idx,
                    scenario_id=case.replay.scenario_id,
                    verdict=getattr(witness, "verdict", None),
                )
            elif skip_reason:
                self._write_progress(
                    "counterexample_skipped",
                    iteration=iteration,
                    case_idx=idx,
                    scenario_id=case.replay.scenario_id,
                    reason=skip_reason,
                    candidate_hunk_count=len(case.candidate_hunks),
                )

            counterexample = self._materialize_counterexample(case, witness)
            counterexamples.append(counterexample)
            if counterexample_jsonl_path:
                dump_jsonl(counterexample_jsonl_path, [counterexample.__dict__], append=True)

        return counterexamples

    def _summarize_replay(
        self,
        replay_results: List[ReplayResult],
        optimization_target: OptimizationTarget | None,
        compare_config: TraceCompareConfig,
        trace_compare_jsonl_path: str | None = None,
        counterexample_jsonl_path: str | None = None,
        iteration: int = 0,
    ) -> Tuple[int, int, List[CounterExample], List[Dict[str, Any]]]:
        strict_pass, tolerant_pass, cases, replay_rows = self._run_trace_compare(
            replay_results,
            optimization_target,
            compare_config,
            trace_compare_jsonl_path=trace_compare_jsonl_path,
            iteration=iteration,
        )
        counterexamples = self._materialize_counterexamples(
            cases,
            optimization_target,
            counterexample_jsonl_path=counterexample_jsonl_path,
            iteration=iteration,
        )

        return strict_pass, tolerant_pass, counterexamples, replay_rows

    def _apply_level1_patch(
        self,
        plan: ExecutionPlan,
        strategy_index: int,
        optimization_target: OptimizationTarget | None,
        counterexamples: List[CounterExample],
    ) -> Tuple[ExecutionPlan, Dict[str, Any] | None]:
        if strategy_index < 0 or strategy_index >= len(LEVEL1_STRATEGIES):
            return plan, None

        strategy = LEVEL1_STRATEGIES[strategy_index]
        patched = copy.deepcopy(plan)
        changes: List[Dict[str, Any]] = []
        rank = self._action_rank(optimization_target)
        action_index = self._action_index(optimization_target)

        if strategy == "reduce_parallelism":
            policy = patched.meta.setdefault("policy", {})
            old_total = int(policy.get("max_parallel", 1))
            new_total = max(1, old_total - 1) if old_total > 1 else 1
            if new_total != old_total:
                policy["max_parallel"] = new_total
                changes.append(
                    {"path": "meta.policy.max_parallel", "from": old_total, "to": new_total}
                )
            for key in ("ble_parallel", "cloud_parallel"):
                old_value = int(policy.get(key, 1))
                new_value = max(1, old_value - 1) if old_value > 1 else 1
                if new_value != old_value:
                    policy[key] = new_value
                    changes.append({"path": f"meta.policy.{key}", "from": old_value, "to": new_value})

            max_group = max(1, int(policy.get("max_parallel", 1)))
            for batch in patched.ordered_batches:
                regrouped: List[List[str]] = []
                for group in batch.parallel_groups:
                    ordered_group = [str(item) for item in group if str(item).strip()]
                    if not ordered_group:
                        continue
                    if len(ordered_group) <= max_group:
                        regrouped.append(list(ordered_group))
                        continue
                    ordered = sorted(ordered_group, key=lambda action_id: (rank.get(action_id, 10_000), action_id))
                    regrouped.extend(self._chunked(ordered, max_group))
                if not regrouped:
                    continue
                if regrouped != batch.parallel_groups:
                    changes.append(
                        {
                            "path": f"batch:{batch.batch_id}.parallel_groups",
                            "from": batch.parallel_groups,
                            "to": regrouped,
                        }
                    )
                    batch.parallel_groups = regrouped

        elif strategy == "disable_session_reuse":
            for batch in patched.ordered_batches:
                before = dict(batch.session_policy)
                batch.session_policy["reuse"] = False
                batch.session_policy["max_age_s"] = 0
                if before != batch.session_policy:
                    changes.append(
                        {
                            "path": f"batch:{batch.batch_id}.session_policy",
                            "from": before,
                            "to": dict(batch.session_policy),
                        }
                    )

        elif strategy == "disable_batching":
            ordered_actions = self._flatten_plan_actions(patched)
            if len(ordered_actions) > 1:
                original_order = {action_id: idx for idx, action_id in enumerate(ordered_actions)}
                ordered_actions = sorted(
                    ordered_actions,
                    key=lambda action_id: (
                        rank.get(action_id, 10_000),
                        original_order.get(action_id, 10_000),
                    ),
                )
                new_batches: List[Batch] = []
                for idx, action_id in enumerate(ordered_actions):
                    new_batches.append(
                        Batch(
                            batch_id=f"batch_{idx:03d}",
                            parallel_groups=[[action_id]],
                            constraints=[],
                            session_policy={"reuse": False, "max_age_s": 0},
                            rate_policy={"max_qps": 1.0, "batch_size": 1},
                            guards=[],
                            fallback=[
                                {
                                    "kind": SoftConstraintKind.MIN_GAP.value,
                                    "scope": [],
                                    "action": "preserve_action_order",
                                    "params": {},
                                },
                                {
                                    "kind": SoftConstraintKind.NO_OVERLAP.value,
                                    "scope": [],
                                    "action": "set_ble_parallelism_to_1",
                                    "params": {},
                                },
                            ],
                        )
                    )
                changes.append(
                    {
                        "path": "ordered_batches",
                        "from_batch_count": len(patched.ordered_batches),
                        "to_batch_count": len(new_batches),
                    }
                )
                patched.ordered_batches = new_batches

        elif strategy == "enforce_min_gap_no_overlap":
            for batch in patched.ordered_batches:
                before_fallback = list(batch.fallback) if isinstance(batch.fallback, list) else dict(batch.fallback)
                before_rate = dict(batch.rate_policy)
                before_guards = list(batch.guards)
                protocol_scopes = self._batch_protocol_scopes(batch, action_index)
                ble_scope = protocol_scopes.get("BLE", [])
                self._append_guard(batch, "BUDGET_K", "resource_constrained")
                if len(ble_scope) >= 2:
                    self._append_fallback(
                        batch,
                        SoftConstraintKind.MIN_GAP.value,
                        "preserve_action_order",
                        scope=list(ble_scope),
                        params={"reason": "m6_level1_ble_transport_serial"},
                    )
                    self._append_fallback(
                        batch,
                        SoftConstraintKind.NO_OVERLAP.value,
                        "set_ble_parallelism_to_1",
                        scope=list(ble_scope),
                        params={"reason": "m6_level1_ble_transport_serial"},
                    )
                batch.rate_policy["max_qps"] = min(float(batch.rate_policy.get("max_qps", 5.0)), 1.0)

                if before_guards != batch.guards:
                    changes.append(
                        {
                            "path": f"batch:{batch.batch_id}.guards",
                            "from": before_guards,
                            "to": list(batch.guards),
                        }
                    )
                if before_fallback != batch.fallback:
                    changes.append(
                        {
                            "path": f"batch:{batch.batch_id}.fallback",
                            "from": before_fallback,
                            "to": list(batch.fallback),
                        }
                    )
                if before_rate != batch.rate_policy:
                    changes.append(
                        {
                            "path": f"batch:{batch.batch_id}.rate_policy",
                            "from": before_rate,
                            "to": dict(batch.rate_policy),
                        }
                    )

        if not changes:
            return plan, None

        patch = {
            "kind": "plan_patch",
            "level": "LEVEL_1",
            "strategy": strategy,
            "reason": self._roll_reason(counterexamples),
            "changes": changes,
        }
        return patched, patch

    @classmethod
    def _counterexample_text(cls, counterexamples: List[CounterExample]) -> str:
        tokens: set[str] = set()
        for cex in counterexamples:
            hunks = cex.diff_summary.get("hunks", [])
            for hunk in hunks:
                if not isinstance(hunk, dict):
                    continue
                payload = cls._normalized_hunk_payload_from_dict(hunk)
                tokens.update(cls._hunk_ops_from_payload(payload))
        return " ".join(sorted(tokens))

    @classmethod
    def _rule_involved_in_counterexamples(cls, rule: Rule, counterexamples: List[CounterExample]) -> bool:
        hints = {
            normalize_op_name(item)
            for item in rule.marker_hints
            if normalize_op_name(item)
        }
        text_hints = {
            str(item).upper()
            for item in rule.marker_hints
            if str(item).strip() and len(str(item).strip()) >= 4
        }
        for cex in counterexamples:
            hunks = cex.diff_summary.get("hunks", [])
            for hunk in hunks:
                if not isinstance(hunk, dict):
                    continue
                payload = cls._normalized_hunk_payload_from_dict(hunk)
                if hints and hints.intersection(cls._hunk_ops_from_payload(payload)):
                    return True
                if text_hints:
                    text = " ".join(payload["baseline_ops"] + payload["optimized_ops"]).upper()
                    if any(hint in text for hint in text_hints):
                        return True
        return False

    @staticmethod
    def _is_order_type_counterexample(counterexample: CounterExample) -> bool:
        kind = str(counterexample.diff_summary.get("kind", "")).strip().lower()
        if kind in {"order_violation", "missing_prerequisite"}:
            return True
        hunks = counterexample.diff_summary.get("hunks", [])
        normalized_payloads = [
            TrustLayer._normalized_hunk_payload_from_dict(hunk)
            for hunk in hunks
            if isinstance(hunk, dict)
        ]
        if not normalized_payloads:
            return False
        inferred = TrustLayer._counterexample_kind_from_payloads(normalized_payloads)
        return inferred in {"order_violation", "missing_prerequisite"}

    @staticmethod
    def _level1_strategy_chain(counterexamples: List[CounterExample]) -> List[str]:
        base = list(LEVEL1_STRATEGIES)
        if any(TrustLayer._is_order_type_counterexample(cex) for cex in counterexamples):
            preferred = ["enforce_min_gap_no_overlap"]
        else:
            signal_text = TrustLayer._counterexample_text(counterexamples)
            if any(token in signal_text for token in {"CLOUD_BACKOFF_SLEEP", "BLE_RETRY_OR_TIMEOUT", "TIMEOUT"}):
                preferred = ["reduce_parallelism", "disable_batching", "disable_session_reuse"]
            else:
                preferred = []
        ordered: List[str] = []
        for item in preferred + base:
            if item not in ordered:
                ordered.append(item)
        return ordered

    @staticmethod
    def _plan_summary(plan: ExecutionPlan | None) -> Dict[str, Any]:
        if plan is None:
            return {}

        batch_rows: List[Dict[str, Any]] = []
        total_groups = 0
        total_actions = 0
        max_group_size = 0
        forced_pick_batches = 0
        for batch in plan.ordered_batches:
            group_sizes = [len(group) for group in batch.parallel_groups]
            total_groups += len(batch.parallel_groups)
            total_actions += sum(group_sizes)
            max_group_size = max(max_group_size, max(group_sizes, default=0))

            fallback_rows = batch.fallback if isinstance(batch.fallback, list) else []
            forced_pick = any(
                str(row.get("kind", "")).upper() == "FORCED_PICK"
                or str(row.get("action", "")) == "force_pick_despite_soft_conflicts"
                for row in fallback_rows
                if isinstance(row, dict)
            )
            if forced_pick:
                forced_pick_batches += 1

            rate_policy = batch.rate_policy if isinstance(batch.rate_policy, dict) else {}
            batch_rows.append(
                {
                    "batch_id": batch.batch_id,
                    "group_count": len(batch.parallel_groups),
                    "group_sizes": group_sizes,
                    "max_group_size": max(group_sizes, default=0),
                    "guard_count": len(batch.guards),
                    "fallback_count": len(fallback_rows),
                    "constraint_kinds": sorted({str(item) for item in batch.constraints}),
                    "rate_policy": {
                        "max_qps": rate_policy.get("max_qps"),
                        "burst": rate_policy.get("burst"),
                        "window_ms": rate_policy.get("window_ms"),
                        "batch_rule_count": len(rate_policy.get("batch_rules", []))
                        if isinstance(rate_policy.get("batch_rules", []), list)
                        else 0,
                        "adaptive_control_count": len(rate_policy.get("adaptive_controls", []))
                        if isinstance(rate_policy.get("adaptive_controls", []), list)
                        else 0,
                    },
                    "session_policy": dict(batch.session_policy),
                }
            )

        return {
            "batch_count": len(plan.ordered_batches),
            "group_count": total_groups,
            "action_count": total_actions,
            "max_group_size": max_group_size,
            "forced_pick_batch_count": forced_pick_batches,
            "policy": dict(plan.meta.get("policy", {})) if isinstance(plan.meta.get("policy", {}), dict) else {},
            "policy_snapshot": dict(plan.meta.get("policy_snapshot", {}))
            if isinstance(plan.meta.get("policy_snapshot", {}), dict)
            else {},
            "batches": batch_rows,
        }

    @staticmethod
    def _earliest_violation_summary(counterexamples: List[CounterExample]) -> Dict[str, Any]:
        anchor_counter: Counter[str] = Counter()
        target_counter: Counter[str] = Counter()
        for counterexample in counterexamples:
            hunks = counterexample.diff_summary.get("hunks", []) if isinstance(counterexample.diff_summary, dict) else []
            if not hunks:
                continue
            first = hunks[0]
            anchor = str(first.get("anchor", "")).strip()
            if anchor:
                anchor_counter[anchor] += 1
                target = TrustLayer._event_repr_target(anchor)
                if target:
                    target_counter[target] += 1
        return {
            "top_anchors": anchor_counter.most_common(5),
            "top_targets": target_counter.most_common(5),
            "dominant_target": target_counter.most_common(1)[0][0] if target_counter else None,
        }

    @staticmethod
    def _runtime_policy_summary(replay_results: List[ReplayResult]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for replay in replay_results:
            artifacts = replay.runtime_artifacts if isinstance(replay.runtime_artifacts, dict) else {}
            if not artifacts:
                continue
            row = {"scenario_id": replay.scenario_id}
            if isinstance(artifacts.get("runtime_policy_snapshot"), list):
                row["runtime_policy_snapshot"] = list(artifacts.get("runtime_policy_snapshot", []))
            if isinstance(artifacts.get("forced_fallbacks_applied"), list):
                row["forced_fallbacks_applied"] = list(artifacts.get("forced_fallbacks_applied", []))
            event_trace = artifacts.get("event_trace", [])
            if isinstance(event_trace, list):
                counts = Counter(
                    str(item.get("op", ""))
                    for item in event_trace
                    if isinstance(item, dict) and str(item.get("op", ""))
                )
                if counts:
                    row["trace_counts"] = {
                        key: counts[key]
                        for key in ("RATE_DOWNGRADE", "BATCH_COALESCE_WAIT", "RATE_WAIT", "TRACE_EXPORTED")
                        if counts.get(key)
                    }
            if len(row) > 1:
                rows.append(row)
        return rows

    def _apply_level2_rule_patch(
        self,
        rules: List[Rule],
        counterexamples: List[CounterExample],
    ) -> Tuple[List[Rule], Dict[str, Any] | None]:
        patched_rules = [Rule(**{**rule.__dict__}) for rule in rules]
        changes: List[Dict[str, Any]] = []
        disabled_rule_ids: List[str] = []
        tightened_rule_ids: List[str] = []

        for rule in patched_rules:
            if rule.status != RuleStatus.SOFT.value:
                continue

            involved = self._rule_involved_in_counterexamples(rule, counterexamples)
            if involved:
                if str(rule.category).strip().lower() == "protocol":
                    old_status = rule.status
                    rule.status = RuleStatus.DISABLED.value
                    disabled_rule_ids.append(rule.rule_id)
                    changes.append(
                        {
                            "rule_id": rule.rule_id,
                            "op": "set_status",
                            "from": old_status,
                            "to": rule.status,
                            "reason": "counterexample_marker_match_protocol",
                        }
                    )
                elif rule.guard == "true":
                    old_guard = rule.guard
                    rule.guard = "rollback_safe_mode"
                    tightened_rule_ids.append(rule.rule_id)
                    changes.append(
                        {
                            "rule_id": rule.rule_id,
                            "op": "tighten_guard",
                            "from": old_guard,
                            "to": rule.guard,
                            "reason": "counterexample_marker_match_semantic_rule",
                        }
                    )
                else:
                    old_guard = rule.guard
                    if "ROLLBACK_SAFE_MODE" not in old_guard.upper():
                        rule.guard = f"({old_guard}) AND rollback_safe_mode"
                        tightened_rule_ids.append(rule.rule_id)
                        changes.append(
                            {
                                "rule_id": rule.rule_id,
                                "op": "tighten_guard",
                                "from": old_guard,
                                "to": rule.guard,
                                "reason": "counterexample_marker_match_semantic_rule",
                            }
                        )
                        continue
                    changes.append(
                        {
                            "rule_id": rule.rule_id,
                            "op": "keep_soft_with_risk_warning",
                            "status": rule.status,
                            "guard": rule.guard,
                            "reason": "counterexample_marker_match_semantic_rule",
                        }
                    )
                continue

        if not changes:
            return rules, None

        patch = {
            "kind": "rule_patch",
            "level": "LEVEL_2",
            "reason": self._roll_reason(counterexamples),
            "changes": changes,
            "disabled_rule_ids": disabled_rule_ids,
            "tightened_rule_ids": tightened_rule_ids,
        }
        return patched_rules, patch

    @staticmethod
    def _apply_rule_overlay_to_dag(
        dag: TypedDAG,
        rule_patch: Dict[str, Any],
    ) -> Tuple[TypedDAG, List[Dict[str, Any]]]:
        patched = copy.deepcopy(dag)
        disabled = {str(item) for item in rule_patch.get("disabled_rule_ids", [])}
        tightened = {str(item) for item in rule_patch.get("tightened_rule_ids", [])}
        changes: List[Dict[str, Any]] = []

        kept_constraints: List[SoftConstraint] = []
        for constraint in patched.soft_constraints:
            rule_id = str(constraint.params.get("rule_id", ""))
            if rule_id and rule_id in disabled:
                changes.append(
                    {
                        "op": "drop_soft_constraint",
                        "rule_id": rule_id,
                        "kind": constraint.kind,
                        "scope": list(constraint.scope),
                    }
                )
                continue
            if rule_id and rule_id in tightened:
                old_guard = constraint.guard
                if "ROLLBACK_SAFE_MODE" not in old_guard.upper():
                    new_guard = "rollback_safe_mode" if old_guard == "true" else f"({old_guard}) AND rollback_safe_mode"
                else:
                    new_guard = old_guard
            else:
                new_guard = constraint.guard
            if rule_id and rule_id in tightened and new_guard != constraint.guard:
                changes.append(
                    {
                        "op": "tighten_soft_constraint_guard",
                        "rule_id": rule_id,
                        "kind": constraint.kind,
                        "from": constraint.guard,
                        "to": new_guard,
                    }
                )
                constraint.guard = new_guard
            kept_constraints.append(constraint)
        patched.soft_constraints = kept_constraints
        return patched, changes

    @staticmethod
    def _dag_has_path(edges: List[DependencyEdge], src: str, dst: str) -> bool:
        out: Dict[str, List[str]] = {}
        for edge in edges:
            out.setdefault(edge.src_mssu, []).append(edge.dst_mssu)
        queue = [src]
        seen = set()
        while queue:
            node = queue.pop(0)
            if node == dst:
                return True
            if node in seen:
                continue
            seen.add(node)
            queue.extend(out.get(node, []))
        return False

    @staticmethod
    def _dag_acyclic(dag: TypedDAG) -> bool:
        indegree: Dict[str, int] = {node_id: 0 for node_id in dag.nodes}
        out: Dict[str, List[str]] = {node_id: [] for node_id in dag.nodes}
        for edge in dag.hard_edges:
            indegree[edge.dst_mssu] = indegree.get(edge.dst_mssu, 0) + 1
            out.setdefault(edge.src_mssu, []).append(edge.dst_mssu)
        queue = [node_id for node_id, degree in indegree.items() if degree == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for nxt in out.get(node, []):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        return visited == len(indegree)

    def _apply_level3_constraint_patch(
        self,
        dag: TypedDAG,
        plan: ExecutionPlan,
        optimization_target: OptimizationTarget | None,
        counterexamples: List[CounterExample],
    ) -> Tuple[TypedDAG, Dict[str, Any] | None]:
        patched = copy.deepcopy(dag)
        changes: List[Dict[str, Any]] = []

        action_order: List[str] = self._level3_patch_action_order(plan, optimization_target)
        action_contexts = self._plan_action_execution_contexts(plan)
        implicated_actions = self._implicated_action_ids(optimization_target, counterexamples)

        action_index: Dict[str, Dict[str, Any]] = {}
        if optimization_target is not None:
            for action in optimization_target.vdev_actions:
                action_id = str(action.get("action_id", "")).strip()
                if action_id:
                    action_index[action_id] = action

        def mssu_primary_action(mssu: MSSU) -> str:
            primary = str(getattr(mssu, "primary_action_ref", "") or "").strip()
            if primary:
                return primary
            refs = [str(action_id).strip() for action_id in getattr(mssu, "action_refs", []) if str(action_id).strip()]
            return refs[0] if len(refs) == 1 else ""

        def action_is_writeback(action: Dict[str, Any] | None) -> bool:
            if not isinstance(action, dict):
                return False
            protocol = str(action.get("protocol", "")).strip().upper()
            target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
            return protocol == "HA" or str(target.get("kind", "")).strip().lower() == "ha_entity"

        def action_is_aggregate_sink(action: Dict[str, Any] | None) -> bool:
            if not isinstance(action, dict):
                return False
            target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
            entity = str(target.get("entity_id") or target.get("id") or "").lower()
            return "overall" in entity or "aggregate" in entity

        def action_lane(action: Dict[str, Any] | None) -> str:
            if not isinstance(action, dict):
                return "UNKNOWN"
            protocol = str(action.get("protocol", "")).strip().upper()
            if protocol == "MQTT":
                protocol = "LOCAL"
            target = action.get("target", {}) if isinstance(action.get("target", {}), dict) else {}
            entity = str(target.get("entity_id") or target.get("id") or "").lower()
            if protocol == "BLE":
                return "BLE_LOCAL"
            if protocol == "CLOUD":
                return "CLOUD"
            if protocol == "LOCAL":
                return "LOCAL"
            if protocol == "HA" or str(target.get("kind", "")).strip().lower() == "ha_entity":
                if "overall" in entity or "aggregate" in entity:
                    return "WRITEBACK_OVERALL"
                if "ble_lane" in entity:
                    return "WRITEBACK_BLE"
                if "cloud_lane" in entity:
                    return "WRITEBACK_CLOUD"
                if "local_lane" in entity or "mqtt_lane" in entity:
                    return "WRITEBACK_LOCAL"
                return "WRITEBACK"
            return "UNKNOWN"

        def mssu_priority(mssu: MSSU) -> int:
            return {
                "ACT": 0,
                "UPDATE": 1,
                "CONFIRM": 2,
                "SYNC": 3,
                "PREPARE": 4,
                "CHECK": 5,
                "CLEANUP": 6,
                "FALLBACK": 7,
            }.get(str(mssu.mssu_type).strip().upper(), 99)

        def representative_mssus_for_action(action_id: str) -> List[str]:
            primary_nodes = [
                mssu
                for mssu in patched.nodes.values()
                if mssu_primary_action(mssu) == str(action_id).strip()
            ]
            if not primary_nodes:
                return []
            action = action_index.get(str(action_id).strip())
            if action_is_aggregate_sink(action):
                aggregate_nodes = [mssu for mssu in primary_nodes if bool(getattr(mssu, "is_aggregate_sink", False))]
                if aggregate_nodes:
                    chosen = min(aggregate_nodes, key=lambda mssu: (mssu_priority(mssu), mssu.mssu_id))
                    return [chosen.mssu_id]
            if action_is_writeback(action):
                update_nodes = [mssu for mssu in primary_nodes if str(mssu.mssu_type).strip().upper() == "UPDATE"]
                if update_nodes:
                    chosen = min(update_nodes, key=lambda mssu: (mssu_priority(mssu), mssu.mssu_id))
                    return [chosen.mssu_id]
            chosen = min(primary_nodes, key=lambda mssu: (mssu_priority(mssu), mssu.mssu_id))
            return [chosen.mssu_id]

        action_to_mssu: Dict[str, List[str]] = {
            action_id: representative_mssus_for_action(action_id)
            for action_id in action_order
        }

        existing_soft = {
            (
                str(constraint.kind),
                tuple(sorted(str(item) for item in constraint.scope)),
                str(constraint.guard or ""),
                str(constraint.fallback or ""),
            )
            for constraint in patched.soft_constraints
        }
        for idx in range(len(action_order) - 1):
            src_action = action_order[idx]
            dst_action = action_order[idx + 1]
            if implicated_actions and src_action not in implicated_actions and dst_action not in implicated_actions:
                continue
            src_ctx = action_contexts.get(src_action)
            dst_ctx = action_contexts.get(dst_action)
            if (
                isinstance(src_ctx, dict)
                and isinstance(dst_ctx, dict)
                and src_ctx.get("batch_idx") == dst_ctx.get("batch_idx")
                and src_ctx.get("group_idx") == dst_ctx.get("group_idx")
                and str(src_ctx.get("phase", "")) == "parallel"
                and str(dst_ctx.get("phase", "")) == "parallel"
            ):
                continue
            scope = tuple(sorted({src_action, dst_action}))
            key = (
                SoftConstraintKind.SOFT_ORDER.value,
                scope,
                "true",
                "preserve_action_order",
            )
            if key in existing_soft:
                continue
            patched.soft_constraints.append(
                SoftConstraint(
                    kind=SoftConstraintKind.SOFT_ORDER.value,
                    scope=list(scope),
                    params={
                        "reason": "m6_level3_action_order",
                        "source": "m6",
                        "ordered_scope": [src_action, dst_action],
                    },
                    guard="true",
                    fallback="preserve_action_order",
                )
            )
            existing_soft.add(key)
            changes.append(
                {
                    "op": "add_soft_constraint",
                    "kind": SoftConstraintKind.SOFT_ORDER.value,
                    "scope": [src_action, dst_action],
                }
            )

        ble_scope = [
            action_id
            for action_id in action_order
            if action_lane(action_index.get(action_id)) == "BLE_LOCAL"
        ]
        if len(ble_scope) >= 2:
            ble_key = (
                SoftConstraintKind.NO_OVERLAP.value,
                tuple(sorted(ble_scope)),
                "true",
                "set_ble_parallelism_to_1",
            )
            if ble_key not in existing_soft:
                patched.soft_constraints.append(
                    SoftConstraint(
                        kind=SoftConstraintKind.NO_OVERLAP.value,
                        scope=list(ble_scope),
                        params={"reason": "m6_level3_ble_serial", "source": "m6"},
                        guard="true",
                        fallback="set_ble_parallelism_to_1",
                    )
                )
                existing_soft.add(ble_key)
                changes.append(
                    {
                        "op": "add_soft_constraint",
                        "kind": SoftConstraintKind.NO_OVERLAP.value,
                        "scope": list(ble_scope),
                    }
                )

        if not changes:
            return dag, None

        patch = {
            "kind": "constraint_patch",
            "level": "LEVEL_3",
            "reason": self._roll_reason(counterexamples),
            "changes": changes,
        }
        return patched, patch

    def evaluate(
        self,
        replay_results: List[ReplayResult],
        dag: TypedDAG,
        rules: List[Rule],
        profile_version: str,
        optimization_target: OptimizationTarget | None = None,
        execution_plan: ExecutionPlan | None = None,
        replay_with_plan: RollbackReplayFn | None = None,
        replan_with_dag: ReplanFn | None = None,
        rollback_max_steps: int = 6,
        hardening_min_pass_rate: float = 0.98,
        hardening_min_coverage: float = 0.85,
    ) -> TrustResult:
        current_dag = copy.deepcopy(dag)
        current_plan = copy.deepcopy(execution_plan)
        level3_reference_plan = copy.deepcopy(execution_plan)
        current_rules = [Rule(**{**rule.__dict__}) for rule in rules]
        current_replay_results = list(replay_results)
        rollback_log: List[Dict[str, Any]] = []
        applied_steps = 0
        max_steps = max(1, int(rollback_max_steps))
        last_summary: Tuple[int, int, List[CounterExample], List[Dict[str, Any]]] | None = None
        summary_is_current = False

        tried_level1: List[str] = []
        level2_applied = False
        level3_applied = False
        dump_jsonl(self._trace_compare_path, [])
        dump_jsonl(self._counterexample_partial_path, [])
        self._write_progress(
            "init",
            replay_count=len(replay_results),
            has_alignment=bool(
                any(
                    isinstance(replay.runtime_artifacts, dict) and replay.runtime_artifacts.get("alignment_map")
                    for replay in replay_results
                )
            ),
            has_counterexample_inputs=bool(
                any(
                    isinstance(replay.runtime_artifacts, dict) and replay.runtime_artifacts.get("baseline_ir")
                    for replay in replay_results
                )
            ),
        )
        self._write_partial_certificate(
            status="RUNNING",
            plan=current_plan,
            replay_summary={"phase": "init", "total_cases": len(replay_results)},
            counterexample_summary={"count": 0},
        )

        while applied_steps < max_steps:
            compare_config = self._trace_compare_config(optimization_target, current_plan)
            strict_pass, tolerant_pass, counterexamples, _ = self._summarize_replay(
                current_replay_results,
                optimization_target,
                compare_config,
                trace_compare_jsonl_path=str(self._trace_compare_path),
                counterexample_jsonl_path=str(self._counterexample_partial_path),
                iteration=applied_steps,
            )
            last_summary = (strict_pass, tolerant_pass, counterexamples, _)
            summary_is_current = True
            self._write_partial_certificate(
                status="RUNNING",
                plan=current_plan,
                replay_summary={
                    "phase": "trace_compare_complete",
                    "iteration": applied_steps,
                    "strict_pass": strict_pass,
                    "tolerant_pass": tolerant_pass,
                    "total": len(current_replay_results),
                },
                counterexample_summary={"count": len(counterexamples)},
            )
            if not counterexamples:
                break

            if current_plan is None or replay_with_plan is None:
                break

            patch_applied = False

            level1_chain = self._level1_strategy_chain(counterexamples)
            next_level1 = next((item for item in level1_chain if item not in tried_level1), None)
            if next_level1 is not None:
                strategy_index = LEVEL1_STRATEGIES.index(next_level1)
                patched_plan, plan_patch = self._apply_level1_patch(
                    current_plan,
                    strategy_index,
                    optimization_target,
                    counterexamples,
                )
                tried_level1.append(next_level1)
                if plan_patch is not None:
                    rollback_log.append(plan_patch)
                    current_plan = patched_plan
                    self._write_progress(
                        "rollback_patch_applied",
                        iteration=applied_steps,
                        patch_kind=str(plan_patch.get("kind", "")),
                        level=str(plan_patch.get("level", "")),
                    )
                    current_replay_results = replay_with_plan(current_plan)
                    patch_applied = True
                    summary_is_current = False
                    applied_steps += 1
                    continue

            if not level2_applied:
                patched_rules, rule_patch = self._apply_level2_rule_patch(current_rules, counterexamples)
                level2_applied = True
                if rule_patch is not None:
                    current_rules = patched_rules
                    patched_dag, dag_changes = self._apply_rule_overlay_to_dag(current_dag, rule_patch)
                    if dag_changes:
                        rule_patch["dag_effects"] = dag_changes
                        current_dag = patched_dag
                    rollback_log.append(rule_patch)
                    self._write_progress(
                        "rollback_patch_applied",
                        iteration=applied_steps,
                        patch_kind=str(rule_patch.get("kind", "")),
                        level=str(rule_patch.get("level", "")),
                    )

                    if replan_with_dag is not None:
                        current_plan = replan_with_dag(current_dag)
                        level3_reference_plan = copy.deepcopy(current_plan)
                    current_replay_results = replay_with_plan(current_plan)
                    patch_applied = True
                    summary_is_current = False
                    applied_steps += 1
                    continue

            if (
                not level3_applied
                and replan_with_dag is not None
                and any(self._is_order_type_counterexample(cex) for cex in counterexamples)
            ):
                patched_dag, constraint_patch = self._apply_level3_constraint_patch(
                    current_dag,
                    level3_reference_plan if level3_reference_plan is not None else current_plan,
                    optimization_target,
                    counterexamples,
                )
                level3_applied = True
                if constraint_patch is not None:
                    rollback_log.append(constraint_patch)
                    self._write_progress(
                        "rollback_patch_applied",
                        iteration=applied_steps,
                        patch_kind=str(constraint_patch.get("kind", "")),
                        level=str(constraint_patch.get("level", "")),
                    )
                    current_dag = patched_dag
                    current_plan = replan_with_dag(current_dag)
                    current_replay_results = replay_with_plan(current_plan)
                    patch_applied = True
                    summary_is_current = False
                    applied_steps += 1
                    continue

            if not patch_applied:
                break

        if not summary_is_current or last_summary is None:
            strict_pass, tolerant_pass, counterexamples, replay_rows = self._summarize_replay(
                current_replay_results,
                optimization_target,
                compare_config,
                trace_compare_jsonl_path=str(self._trace_compare_path),
                counterexample_jsonl_path=str(self._counterexample_partial_path),
                iteration=applied_steps,
            )
        else:
            strict_pass, tolerant_pass, counterexamples, replay_rows = last_summary
        self._write_progress(
            "finalize",
            strict_pass=strict_pass,
            tolerant_pass=tolerant_pass,
            counterexample_count=len(counterexamples),
            rollback_iterations=len(rollback_log),
        )

        trust_plan_hash = self._plan_hash(current_plan)
        execution_plan_hash = self._plan_hash(execution_plan)
        for counterexample in counterexamples:
            counterexample.trust_plan_hash = trust_plan_hash
            counterexample.execution_plan_hash = execution_plan_hash

        generated_at = now_utc_iso()
        validation_stats = self._rule_validation_stats(
            current_rules,
            current_replay_results,
            compare_config,
            counterexamples=counterexamples,
            rollback_log=rollback_log,
            generated_at=generated_at,
        )
        validation_stats_payload = self._validation_stats_payload(validation_stats, generated_at)
        threshold = HardeningThreshold(
            min_pass_rate=float(hardening_min_pass_rate),
            min_coverage=float(hardening_min_coverage),
        )
        hardened_rules, auto_decisions = auto_harden_rules(
            current_rules,
            validation_stats,
            threshold=threshold,
        )

        hardening_payload: Dict[str, Any] = {
            "auto_hardening": auto_decisions,
            "rollback": {
                "priority_chain": LEVEL1_STRATEGIES + ["rule_patch", "constraint_patch"],
                "iterations": len(rollback_log),
                "max_steps": max_steps,
                "log": rollback_log,
                "final_counterexample_count": len(counterexamples),
            },
            "thresholds": {
                "hardening_min_pass_rate": float(hardening_min_pass_rate),
                "hardening_min_coverage": float(hardening_min_coverage),
            },
            "validation_stats_path": str(self._validation_stats_path),
        }

        cert = ExecutionCertificate(
            certificate_id=f"cert_{hashlib.sha1((self.integration + generated_at).encode('utf-8')).hexdigest()[:12]}",
            schema_version=CERT_SCHEMA_VERSION,
            generated_at=generated_at,
            integration=self.integration,
            profile_version=profile_version,
            canonicalization_version=compare_config.canonicalization_version,
            mssu_signatures=[
                {
                    "mssu_id": mssu_id,
                    "phase": mssu.phase,
                    "type": mssu.mssu_type,
                    "side_effect_sig": sorted(mssu.side_effect_sig),
                }
                for mssu_id, mssu in current_dag.nodes.items()
            ],
            hard_edge_proof={
                "edge_count": len(current_dag.hard_edges),
                "edges": [edge.__dict__ for edge in current_dag.hard_edges],
                "acyclic": self._dag_acyclic(current_dag),
            },
            soft_constraints=[constraint.__dict__ for constraint in current_dag.soft_constraints],
            plan_summary=self._plan_summary(current_plan),
            differential_summary={
                "scenario_total": len(current_replay_results),
                "strict_pass": strict_pass,
                "tolerant_pass": tolerant_pass,
                "counterexample_count": len(counterexamples),
                "earliest_violation_summary": self._earliest_violation_summary(counterexamples),
                "focus_terms": self._focus_terms(optimization_target),
                "rule_stats": validation_stats,
                "compare_meta": trace_compare_meta(compare_config),
                "runtime_policy_summary": self._runtime_policy_summary(current_replay_results),
                "rollback_iterations": len(rollback_log),
                "rollback_max_steps": max_steps,
                "rollback_applied_kinds": [str(item.get("kind", "")) for item in rollback_log],
                "hardening_threshold": {
                    "min_pass_rate": threshold.min_pass_rate,
                    "min_coverage": threshold.min_coverage,
                },
            },
            counterexamples=[cex.__dict__ for cex in counterexamples],
        )

        dump_json(f"{self.out_dir}/execution_certificate.json", cert)
        dump_json(f"{self.out_dir}/counterexamples.json", [cex.__dict__ for cex in counterexamples])
        dump_json(f"{self.out_dir}/rule_hardening_decisions.json", hardening_payload)
        dump_json(f"{self.out_dir}/rollback_log.json", rollback_log)
        dump_json(self._validation_stats_path, validation_stats_payload)
        self._write_partial_certificate(
            status="COMPLETED",
            plan=current_plan,
            replay_summary={
                "phase": "finalize",
                "strict_pass": strict_pass,
                "tolerant_pass": tolerant_pass,
                "total": len(current_replay_results),
            },
            counterexample_summary={"count": len(counterexamples)},
            rollback_iterations=len(rollback_log),
        )

        return TrustResult(
            certificate=cert,
            counterexamples=counterexamples,
            hardened_rules=hardened_rules,
            hardening_decisions=hardening_payload,
            summary={
                "strict_pass": strict_pass,
                "tolerant_pass": tolerant_pass,
                "total": len(current_replay_results),
                "rollback_iterations": len(rollback_log),
                "rollback_max_steps": max_steps,
                "hardening_min_pass_rate": threshold.min_pass_rate,
                "hardening_min_coverage": threshold.min_coverage,
            },
            final_plan=current_plan,
            final_dag=current_dag,
            final_rules=current_rules,
            replay_results=current_replay_results,
            rollback_log=rollback_log,
        )


def rollback_rules_on_counterexample(rules: List[Rule], counterexamples: List[CounterExample]) -> List[Rule]:
    if not counterexamples:
        return rules

    rolled: List[Rule] = []
    for rule in rules:
        if rule.status == RuleStatus.HARD.value:
            rolled.append(Rule(**{**rule.__dict__, "status": RuleStatus.SOFT.value}))
        else:
            rolled.append(rule)
    return rolled


TrustLayer = EquivalenceValidator
