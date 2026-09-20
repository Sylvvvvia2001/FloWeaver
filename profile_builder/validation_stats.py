from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable


def _iter_rows(payload: Any) -> Iterable[tuple[str, Dict[str, Any]]]:
    if isinstance(payload, dict):
        if "rules" in payload and isinstance(payload["rules"], list):
            for row in payload["rules"]:
                if isinstance(row, dict) and row.get("rule_id"):
                    yield str(row["rule_id"]), row
            return
        for rule_id, row in payload.items():
            if isinstance(row, dict):
                yield str(rule_id), row
        return
    if isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict) and row.get("rule_id"):
                yield str(row["rule_id"]), row


def zero_validation_summary() -> Dict[str, Any]:
    return {
        "stats_state": "MISSING",
        "n_matched": 0,
        "n_applied": 0,
        "n_success": 0,
        "n_counterexamples": 0,
        "trace_preserved_rate": None,
        "resource_protocol_preserved_rate": None,
        "final_state_preserved_rate": None,
        "avg_latency_delta_ms": None,
        "p95_latency_delta_ms": None,
        "last_updated_at": None,
    }


def make_validation_summary(stats: Dict[str, Any] | None) -> Dict[str, Any]:
    if stats is None:
        return zero_validation_summary()

    return {
        "stats_state": "PRESENT",
        "n_matched": int(stats.get("n_matched", 0)),
        "n_applied": int(stats.get("n_applied", 0)),
        "n_success": int(stats.get("n_success", 0)),
        "n_counterexamples": int(stats.get("n_counterexamples", 0)),
        "trace_preserved_rate": stats.get("trace_preserved_rate"),
        "resource_protocol_preserved_rate": stats.get("resource_protocol_preserved_rate"),
        "final_state_preserved_rate": stats.get("final_state_preserved_rate"),
        "avg_latency_delta_ms": stats.get("avg_latency_delta_ms"),
        "p95_latency_delta_ms": stats.get("p95_latency_delta_ms"),
        "last_updated_at": stats.get("last_updated_at"),
    }


def load_validation_stats(path: str | Path | None) -> Dict[str, Dict[str, Any]]:


    if not path or not os.path.exists(path):
        return {}

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    stats: Dict[str, Dict[str, Any]] = {}
    for rule_id, row in _iter_rows(payload):
        stats[rule_id] = make_validation_summary(row)
    return stats
