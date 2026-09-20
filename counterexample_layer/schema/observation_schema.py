from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

from dsl.contracts import OptimizationTarget
from optimizer.m0_observation import ObservationEngine, ObservationSchema as M0ObservationSchema
from runtime.trace import TraceCompareConfig


@dataclass
class CounterexampleObservationSchema:
    semantic_ops: List[str] = field(default_factory=list)
    canonicalization_version: str = "v1"
    required_state_writes: List[str] = field(default_factory=list)
    required_final_state: Dict[str, Any] = field(default_factory=dict)
    equivalence_whitelist: List[Any] = field(default_factory=list)
    anchor_ops: List[str] = field(default_factory=list)
    ignored_anchor_ops: List[str] = field(default_factory=list)
    trace_compare_config: TraceCompareConfig = field(default_factory=TraceCompareConfig)
    resource_protocol_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CounterexampleObservationSchema":
        canonicalization_version = str(payload.get("canonicalization_version", "v1"))
        equivalence_whitelist = list(payload.get("equivalence_whitelist", []))
        trace_compare_config = TraceCompareConfig.from_observation(
            canonicalization_version=canonicalization_version,
            equivalence_whitelist=equivalence_whitelist,
        )
        return cls(
            semantic_ops=[str(item) for item in payload.get("semantic_ops", [])],
            canonicalization_version=canonicalization_version,
            required_state_writes=[str(item) for item in payload.get("required_state_writes", [])],
            required_final_state=dict(payload.get("required_final_state", {})),
            equivalence_whitelist=equivalence_whitelist,
            anchor_ops=[str(item) for item in payload.get("anchor_ops", [])],
            ignored_anchor_ops=[str(item) for item in payload.get("ignored_anchor_ops", [])],
            trace_compare_config=trace_compare_config,
            resource_protocol_rules={
                str(resource_kind): dict(rule_payload)
                for resource_kind, rule_payload in dict(payload.get("resource_protocol_rules", {})).items()
            },
        )

    @classmethod
    def from_optimization_target(cls, target: OptimizationTarget | None) -> "CounterexampleObservationSchema":
        if target is None:
            base = M0ObservationSchema()
            return cls.from_m0_schema(base)
        engine = ObservationEngine.from_optimization_target(target)
        return cls.from_m0_schema(engine.schema)

    @classmethod
    def from_m0_schema(cls, schema: M0ObservationSchema) -> "CounterexampleObservationSchema":
        trace_compare_config = TraceCompareConfig.from_observation(
            canonicalization_version=schema.canonicalization_version,
            equivalence_whitelist=list(schema.equivalence_whitelist),
        )
        resource_protocol_rules = {
            "listener": {
                "acquire_ops": ["SUBSCRIBE"],
                "release_ops": ["UNSUBSCRIBE"],
                "forbid_overlap": True,
                "must_release": True,
            },
            "manager": {
                "acquire_ops": ["ENTRY_SETUP"],
                "release_ops": ["ENTRY_UNLOAD"],
                "forbid_overlap": False,
                "must_release": True,
            },
            "connection": {
                "acquire_ops": ["BLE_CONNECT"],
                "release_ops": ["BLE_DISCONNECT", "ENTRY_UNLOAD"],
                "forbid_overlap": True,
                "must_release": True,
            },
            "session": {
                "acquire_ops": ["CLOUD_SESSION_REUSE"],
                "release_ops": ["ENTRY_UNLOAD"],
                "forbid_overlap": False,
                "must_release": False,
                "required_before": ["CLOUD_HTTP_CALL"],
            },
            "cloud_session": {
                "acquire_ops": ["CLOUD_SESSION_REUSE"],
                "release_ops": ["ENTRY_UNLOAD"],
                "forbid_overlap": False,
                "must_release": False,
                "required_before": ["CLOUD_HTTP_CALL"],
            },
        }
        return cls(
            semantic_ops=list(schema.semantic_ops),
            canonicalization_version=schema.canonicalization_version,
            required_state_writes=list(schema.required_state_writes),
            required_final_state=dict(schema.required_final_state),
            equivalence_whitelist=list(schema.equivalence_whitelist),
            anchor_ops=list(schema.anchor_ops),
            ignored_anchor_ops=list(schema.ignored_anchor_ops),
            trace_compare_config=trace_compare_config,
            resource_protocol_rules=resource_protocol_rules,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["trace_compare_config"] = {
            "canonicalization_version": self.trace_compare_config.canonicalization_version,
            "equivalence_whitelist": list(self.equivalence_whitelist),
            "equivalence_rules": list(getattr(self.trace_compare_config, "equivalence_rules", [])),
            "commutable_ops": sorted(getattr(self.trace_compare_config, "commutable_ops", set())),
        }
        return payload
