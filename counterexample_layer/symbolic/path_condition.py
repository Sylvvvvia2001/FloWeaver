from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class PathCondition:
    clauses: List[str] = field(default_factory=list)

    def extend(self, clause: str) -> "PathCondition":
        normalized = str(clause).strip()
        if not normalized:
            return PathCondition(list(self.clauses))
        return PathCondition(self.clauses + [normalized])

    def minimal_clauses(self) -> List[str]:
        ordered: List[str] = []
        for clause in self.clauses:
            if clause not in ordered:
                ordered.append(clause)
        return ordered
