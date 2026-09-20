from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from profile_builder.evidence.evidence_types import CounterexampleEvidence

BucketKey = Tuple[str, str, str, str]


def bucket_evidence_by_type(
    evidence_list: list[CounterexampleEvidence],
) -> dict[tuple, list[CounterexampleEvidence]]:
    buckets: Dict[BucketKey, List[CounterexampleEvidence]] = defaultdict(list)
    for evidence in evidence_list:
        key = (
            str(evidence.violated_property),
            str(evidence.protocol_context),
            str(evidence.phase_context),
            str(evidence.trigger_pattern),
        )
        buckets[key].append(evidence)
    return {key: sorted(values, key=lambda item: item.evidence_id) for key, values in buckets.items()}
