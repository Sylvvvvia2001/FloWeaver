from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from dsl.contracts import Trace

from counterexample_layer.symbolic.path_condition import PathCondition


@dataclass
class SymConfig:
    useg_index: int
    pc_b: str | None
    pc_o: str | None
    path_condition: PathCondition
    split_offset_b: int = 0
    split_offset_o: int = 0
    env_state: Dict[str, Any] = field(default_factory=dict)
    resource_state_b: Dict[str, Any] = field(default_factory=dict)
    resource_state_o: Dict[str, Any] = field(default_factory=dict)
    semantic_state_b: Dict[str, Any] = field(default_factory=dict)
    semantic_state_o: Dict[str, Any] = field(default_factory=dict)
    trace_b: Trace = field(default_factory=Trace)
    trace_o: Trace = field(default_factory=Trace)
    mode: str = "UNIFIED"
    divergence_status: Dict[str, Any] = field(default_factory=dict)
    suspicious_region_id: str | None = None
    visited_useg_nodes: List[str] = field(default_factory=list)
    executed_steps: int = 0
