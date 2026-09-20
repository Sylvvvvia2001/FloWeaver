from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IRSummary:
    provider: str
    op: str
    target: str
    phase: str
    params: Dict[str, Any] = field(default_factory=dict)
    emits_observation: bool = True
    resource_effects: List[Dict[str, Any]] = field(default_factory=list)
    semantic_updates: Dict[str, Any] = field(default_factory=dict)
    exception_category: str | None = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "IRSummary":
        return cls(
            provider=str(payload.get("provider", "")),
            op=str(payload.get("op", "")),
            target=str(payload.get("target", "")),
            phase=str(payload.get("phase", "")),
            params=dict(payload.get("params", {})),
            emits_observation=bool(payload.get("emits_observation", True)),
            resource_effects=[dict(item) for item in payload.get("resource_effects", [])],
            semantic_updates=dict(payload.get("semantic_updates", {})),
            exception_category=(
                str(payload.get("exception_category"))
                if payload.get("exception_category") is not None
                else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IRNode:
    node_id: str
    summary: IRSummary
    successors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "IRNode":
        return cls(
            node_id=str(payload.get("node_id", "")),
            summary=IRSummary.from_dict(dict(payload.get("summary", {}))),
            successors=[str(item) for item in payload.get("successors", [])],
            metadata=dict(payload.get("metadata", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "summary": self.summary.to_dict(),
            "successors": list(self.successors),
            "metadata": dict(self.metadata),
        }


@dataclass
class IRProgram:
    program_id: str
    nodes: Dict[str, IRNode]
    entry_node: str | None
    exit_node: str | None
    order: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "IRProgram":
        nodes_payload = payload.get("nodes", {})
        nodes = {
            str(node_id): IRNode.from_dict(dict(node_payload))
            for node_id, node_payload in dict(nodes_payload).items()
        }
        return cls(
            program_id=str(payload.get("program_id", "")),
            nodes=nodes,
            entry_node=str(payload.get("entry_node")) if payload.get("entry_node") is not None else None,
            exit_node=str(payload.get("exit_node")) if payload.get("exit_node") is not None else None,
            order=[str(item) for item in payload.get("order", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "entry_node": self.entry_node,
            "exit_node": self.exit_node,
            "order": list(self.order),
        }
