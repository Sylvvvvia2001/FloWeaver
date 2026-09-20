from __future__ import annotations

from typing import Any, Dict, List, Tuple


CERTIFICATE_REQUIRED_FIELDS = [
    "certificate_id",
    "schema_version",
    "generated_at",
    "integration",
    "profile_version",
    "canonicalization_version",
    "mssu_signatures",
    "hard_edge_proof",
    "soft_constraints",
    "differential_summary",
]


def validate_certificate_dict(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    for key in CERTIFICATE_REQUIRED_FIELDS:
        if key not in payload:
            errors.append(f"missing:{key}")
    if "mssu_signatures" in payload and not isinstance(payload["mssu_signatures"], list):
        errors.append("invalid:mssu_signatures")
    if "hard_edge_proof" in payload and not isinstance(payload["hard_edge_proof"], dict):
        errors.append("invalid:hard_edge_proof")
    return (not errors), errors
