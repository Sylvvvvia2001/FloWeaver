from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from alignment_layer.output.alignment_map import AlignedBlock, AlignedPair, AlignmentMap
from alignment_layer.output.suspicious_regions import SuspiciousRegion
from alignment_layer.verify.obligations import ProofObligation
from alignment_layer.verify.violations import AlignmentViolation


@dataclass
class AlignmentResult:
    verdict: str
    alignment_map: AlignmentMap
    aligned_pairs: List[AlignedPair] = field(default_factory=list)
    aligned_blocks: List[AlignedBlock] = field(default_factory=list)
    unaligned_baseline_nodes: List[str] = field(default_factory=list)
    unaligned_optimized_nodes: List[str] = field(default_factory=list)
    suspicious_regions: List[SuspiciousRegion] = field(default_factory=list)
    proof_obligations: List[ProofObligation] = field(default_factory=list)
    violations: List[AlignmentViolation] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "alignment_map": self.alignment_map.to_dict(),
            "aligned_pairs": [item.to_dict() for item in self.aligned_pairs],
            "aligned_blocks": [item.to_dict() for item in self.aligned_blocks],
            "unaligned_baseline_nodes": list(self.unaligned_baseline_nodes),
            "unaligned_optimized_nodes": list(self.unaligned_optimized_nodes),
            "suspicious_regions": [item.to_dict() for item in self.suspicious_regions],
            "proof_obligations": [item.to_dict() for item in self.proof_obligations],
            "violations": [item.to_dict() for item in self.violations],
            "summary": dict(self.summary),
        }
