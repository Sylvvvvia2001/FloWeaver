from __future__ import annotations

from typing import Any, Dict, List, Tuple


RULE_DSL_SCHEMA: Dict[str, Any] = {
    "required": ["rule_id", "title", "category", "status", "evidence_ids"],
    "status_enum": ["SOFT", "HARD", "DISABLED"],
}


SOFT_CONSTRAINT_SCHEMA: Dict[str, Any] = {
    "required": ["kind", "scope", "guard", "fallback"],
    "kind_enum": [
        "MIN_GAP",
        "NO_OVERLAP",
        "SAME_SESSION_GROUP",
        "BUDGET_K",
        "COALESCE_STATE_WRITE",
        "BACKOFF_WINDOW",
    ],
}


def validate_rule_dsl(rule: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in RULE_DSL_SCHEMA["required"]:
        if key not in rule:
            errors.append(f"missing:{key}")
    if "status" in rule and rule["status"] not in RULE_DSL_SCHEMA["status_enum"]:
        errors.append("invalid:status")
    if "evidence_ids" in rule and not isinstance(rule["evidence_ids"], list):
        errors.append("invalid:evidence_ids")
    return (not errors), errors


def validate_soft_constraint(constraint: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in SOFT_CONSTRAINT_SCHEMA["required"]:
        if key not in constraint:
            errors.append(f"missing:{key}")
    if "kind" in constraint and constraint["kind"] not in SOFT_CONSTRAINT_SCHEMA["kind_enum"]:
        errors.append("invalid:kind")
    if "scope" in constraint and not isinstance(constraint["scope"], list):
        errors.append("invalid:scope")
    return (not errors), errors
