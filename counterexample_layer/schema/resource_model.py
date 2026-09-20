from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

from counterexample_layer.schema.observation_schema import CounterexampleObservationSchema


@dataclass
class ResourceRule:
    resource_kind: str
    acquire_ops: List[str] = field(default_factory=list)
    release_ops: List[str] = field(default_factory=list)
    forbid_overlap: bool = False
    must_release: bool = False
    required_before: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ResourceRule":
        return cls(
            resource_kind=str(payload.get("resource_kind", "")),
            acquire_ops=[str(item) for item in payload.get("acquire_ops", [])],
            release_ops=[str(item) for item in payload.get("release_ops", [])],
            forbid_overlap=bool(payload.get("forbid_overlap", False)),
            must_release=bool(payload.get("must_release", False)),
            required_before=[str(item) for item in payload.get("required_before", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceModel:
    rules: Dict[str, ResourceRule] = field(default_factory=dict)
    lifecycle_boundaries: Dict[str, List[str]] = field(default_factory=dict)
    overlap_constraints: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ResourceModel":
        return cls(
            rules={
                str(resource_kind): ResourceRule.from_dict(dict(rule_payload))
                for resource_kind, rule_payload in dict(payload.get("rules", {})).items()
            },
            lifecycle_boundaries={
                str(key): [str(item) for item in values]
                for key, values in dict(payload.get("lifecycle_boundaries", {})).items()
            },
            overlap_constraints={
                str(key): dict(values)
                for key, values in dict(payload.get("overlap_constraints", {})).items()
            },
        )

    @classmethod
    def from_observation_schema(cls, schema: CounterexampleObservationSchema) -> "ResourceModel":
        rules: Dict[str, ResourceRule] = {}
        for resource_kind, payload in schema.resource_protocol_rules.items():
            rules[str(resource_kind)] = ResourceRule(
                resource_kind=str(resource_kind),
                acquire_ops=[str(item) for item in payload.get("acquire_ops", [])],
                release_ops=[str(item) for item in payload.get("release_ops", [])],
                forbid_overlap=bool(payload.get("forbid_overlap", False)),
                must_release=bool(payload.get("must_release", False)),
                required_before=[str(item) for item in payload.get("required_before", [])],
            )
        return cls(
            rules=rules,
            lifecycle_boundaries={
                "setup_ops": ["ENTRY_SETUP"],
                "teardown_ops": ["ENTRY_UNLOAD"],
                "cleanup_ops": ["UNSUBSCRIBE", "BLE_DISCONNECT", "ENTRY_UNLOAD"],
            },
            overlap_constraints={
                resource_kind: {
                    "forbid_overlap": rule.forbid_overlap,
                    "must_release": rule.must_release,
                }
                for resource_kind, rule in rules.items()
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rules": {resource_kind: rule.to_dict() for resource_kind, rule in self.rules.items()},
            "lifecycle_boundaries": {
                key: list(values)
                for key, values in self.lifecycle_boundaries.items()
            },
            "overlap_constraints": {
                key: dict(values)
                for key, values in self.overlap_constraints.items()
            },
        }
