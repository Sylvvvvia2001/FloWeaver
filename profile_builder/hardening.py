from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from dsl.contracts import Rule, RuleStatus
from profile_builder.validation_stats import make_validation_summary, zero_validation_summary


MIN_MATCH_COUNT = 3
MIN_APPLIED_COUNT = 3

MIN_PASS_RATE_CANDIDATE = 0.80
MIN_PASS_RATE_HARD = 0.95

MIN_TRACE_RATE_HARD = 0.95
MIN_RESOURCE_RATE_HARD = 0.95
MIN_FINAL_STATE_RATE_HARD = 0.95

MAX_COUNTEREXAMPLES_HARD = 0


@dataclass
class HardeningThreshold:
    min_pass_rate: float = MIN_PASS_RATE_HARD
    min_coverage: float = MIN_PASS_RATE_CANDIDATE


def decide_hardening_state(stats: Dict[str, Any]) -> tuple[str, str]:
    n_matched = int(stats.get("n_matched", 0))
    n_applied = int(stats.get("n_applied", 0))
    n_success = int(stats.get("n_success", 0))
    n_counterexamples = int(stats.get("n_counterexamples", 0))

    trace_rate = stats.get("trace_preserved_rate")
    resource_rate = stats.get("resource_protocol_preserved_rate")
    final_state_rate = stats.get("final_state_preserved_rate")

    if n_matched < MIN_MATCH_COUNT or n_applied < MIN_APPLIED_COUNT:
        return "SOFT", "insufficient_coverage"

    if n_counterexamples > MAX_COUNTEREXAMPLES_HARD:
        return "SOFT", "counterexample_seen"

    pass_rate = n_success / max(n_applied, 1)

    if (
        pass_rate >= MIN_PASS_RATE_HARD
        and (trace_rate is not None and trace_rate >= MIN_TRACE_RATE_HARD)
        and (resource_rate is not None and resource_rate >= MIN_RESOURCE_RATE_HARD)
        and (final_state_rate is not None and final_state_rate >= MIN_FINAL_STATE_RATE_HARD)
    ):
        return "HARD", "promoted_by_validation"

    if pass_rate >= MIN_PASS_RATE_CANDIDATE:
        return "HARD_CANDIDATE", "promoted_candidate_by_validation"

    return "SOFT", "validation_below_threshold"


def auto_harden_rules(
    rules: List[Rule],
    validation_stats: Dict[str, Dict[str, Any]] | None,
    threshold: HardeningThreshold | None = None,
) -> Tuple[List[Rule], Dict[str, Dict[str, Any]]]:
    del threshold
    hardened: List[Rule] = []
    decisions: Dict[str, Dict[str, Any]] = {}

    stats_by_rule = validation_stats or {}

    for rule in rules:
        raw_stats = stats_by_rule.get(rule.rule_id)
        if raw_stats is None:
            summary = zero_validation_summary()
            hardened_rule = Rule(
                **{
                    **rule.__dict__,
                    "status": RuleStatus.SOFT.value,
                    "hardening_state": "SOFT",
                    "hardening_reason": "cold_start_no_validation_stats",
                    "validation_summary": summary,
                }
            )
            hardened.append(hardened_rule)
            decisions[rule.rule_id] = {
                "hardening_state": "SOFT",
                "hardening_reason": "cold_start_no_validation_stats",
            }
            continue

        summary = make_validation_summary(raw_stats)
        state, reason = decide_hardening_state(summary)
        status = RuleStatus.HARD.value if state == "HARD" else RuleStatus.SOFT.value

        hardened_rule = Rule(
            **{
                **rule.__dict__,
                "status": status,
                "hardening_state": state,
                "hardening_reason": reason,
                "validation_summary": summary,
            }
        )
        hardened.append(hardened_rule)
        decisions[rule.rule_id] = {
            "hardening_state": state,
            "hardening_reason": reason,
        }

    return hardened, decisions
