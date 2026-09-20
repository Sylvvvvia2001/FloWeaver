from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

from alignment_layer.output.suspicious_regions import SuspiciousRegion


@dataclass
class AlignedPair:
    baseline_node_id: str
    optimized_node_id: str
    relation: str
    confidence: float
    supporting_rule: str | None = None
    semantic_compatibility: Dict[str, Any] = field(default_factory=dict)
    observation_compatibility: Dict[str, Any] = field(default_factory=dict)
    resource_compatibility: Dict[str, Any] = field(default_factory=dict)

    @property
    def source_rule(self) -> str:
        return self.supporting_rule or ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AlignedPair":
        return cls(
            baseline_node_id=str(payload.get("baseline_node_id", "")),
            optimized_node_id=str(payload.get("optimized_node_id", "")),
            relation=str(payload.get("relation", payload.get("source_rule", "EXACT")) or "EXACT"),
            confidence=float(payload.get("confidence", 0.0)),
            supporting_rule=(
                str(payload.get("supporting_rule"))
                if payload.get("supporting_rule") is not None
                else (str(payload.get("source_rule")) if payload.get("source_rule") is not None else None)
            ),
            semantic_compatibility=dict(payload.get("semantic_compatibility", {})),
            observation_compatibility=dict(payload.get("observation_compatibility", {})),
            resource_compatibility=dict(payload.get("resource_compatibility", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlignedBlock:
    baseline_node_ids: List[str]
    optimized_node_ids: List[str]
    relation: str
    confidence: float
    supporting_rules: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AlignedBlock":
        return cls(
            baseline_node_ids=[str(item) for item in payload.get("baseline_node_ids", [])],
            optimized_node_ids=[str(item) for item in payload.get("optimized_node_ids", [])],
            relation=str(payload.get("relation", "SERIAL_EQ")),
            confidence=float(payload.get("confidence", 0.0)),
            supporting_rules=[str(item) for item in payload.get("supporting_rules", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlignmentMap:
    node_alignments: List[AlignedPair] = field(default_factory=list)
    block_alignments: List[AlignedBlock] = field(default_factory=list)
    unmatched_baseline_nodes: List[str] = field(default_factory=list)
    unmatched_optimized_nodes: List[str] = field(default_factory=list)
    suspicious_regions: List[SuspiciousRegion] = field(default_factory=list)

    @property
    def node_pairs(self) -> List[AlignedPair]:
        return self.node_alignments

    @property
    def block_pairs(self) -> List[Tuple[List[str], List[str]]]:
        return [
            (list(block.baseline_node_ids), list(block.optimized_node_ids))
            for block in self.block_alignments
        ]

    @property
    def unmatched_baseline(self) -> List[str]:
        return self.unmatched_baseline_nodes

    @property
    def unmatched_optimized(self) -> List[str]:
        return self.unmatched_optimized_nodes

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AlignmentMap":
        if "node_alignments" in payload or "block_alignments" in payload:
            return cls(
                node_alignments=[AlignedPair.from_dict(dict(item)) for item in payload.get("node_alignments", [])],
                block_alignments=[AlignedBlock.from_dict(dict(item)) for item in payload.get("block_alignments", [])],
                unmatched_baseline_nodes=[str(item) for item in payload.get("unmatched_baseline_nodes", [])],
                unmatched_optimized_nodes=[str(item) for item in payload.get("unmatched_optimized_nodes", [])],
                suspicious_regions=[SuspiciousRegion.from_dict(dict(item)) for item in payload.get("suspicious_regions", [])],
            )
        return cls(
            node_alignments=[AlignedPair.from_dict(dict(item)) for item in payload.get("node_pairs", [])],
            block_alignments=[
                AlignedBlock(
                    baseline_node_ids=[str(node_id) for node_id in left],
                    optimized_node_ids=[str(node_id) for node_id in right],
                    relation="SERIAL_EQ",
                    confidence=0.75,
                    supporting_rules=[],
                )
                for left, right in payload.get("block_pairs", [])
            ],
            unmatched_baseline_nodes=[str(item) for item in payload.get("unmatched_baseline", [])],
            unmatched_optimized_nodes=[str(item) for item in payload.get("unmatched_optimized", [])],
            suspicious_regions=[SuspiciousRegion.from_dict(dict(item)) for item in payload.get("suspicious_regions", [])],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_alignments": [item.to_dict() for item in self.node_alignments],
            "block_alignments": [item.to_dict() for item in self.block_alignments],
            "unmatched_baseline_nodes": list(self.unmatched_baseline_nodes),
            "unmatched_optimized_nodes": list(self.unmatched_optimized_nodes),
            "suspicious_regions": [item.to_dict() for item in self.suspicious_regions],
        }
