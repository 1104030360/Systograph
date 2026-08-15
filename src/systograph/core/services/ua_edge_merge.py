from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence

from systograph.core.models.ai_system_map_v2 import CanonicalEdge
from systograph.core.services.ua_edge_derivation_models import (
    EdgeCandidate,
    EdgeMergeOutcome,
)


def merge_and_cap_edges(
    candidates: Sequence[EdgeCandidate],
    *,
    max_outgoing_edges: int,
    max_edges: int,
) -> EdgeMergeOutcome:
    grouped: dict[tuple[str, str, str], list[EdgeCandidate]] = defaultdict(
        list
    )
    for candidate in candidates:
        grouped[candidate.merge_key].append(candidate)
    merged: list[EdgeCandidate] = []
    discarded_lower_tier = 0
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: item.sort_key)
        winning_rank = group[0].rank
        winners = [item for item in group if item.rank == winning_rank]
        discarded_lower_tier += len(group) - len(winners)
        first = winners[0]
        merged.append(
            EdgeCandidate(
                source=first.source,
                target=first.target,
                relationship=first.relationship,
                tier=first.tier,
                rank=first.rank,
                status=first.status,
                evidence_ids=tuple(
                    sorted(
                        {
                            evidence_id
                            for winner in winners
                            for evidence_id in winner.evidence_ids
                        }
                    )
                ),
                undetermined_reason=first.undetermined_reason,
            )
        )
    ordered = sorted(merged, key=lambda item: item.sort_key)
    per_source: dict[str, int] = defaultdict(int)
    after_source_cap: list[EdgeCandidate] = []
    source_drops = {"L1": 0, "L2": 0}
    for candidate in ordered:
        if per_source[candidate.source] >= max_outgoing_edges:
            source_drops[candidate.tier] += 1
            continue
        per_source[candidate.source] += 1
        after_source_cap.append(candidate)
    kept = after_source_cap[:max_edges]
    global_drops = {"L1": 0, "L2": 0}
    for candidate in after_source_cap[max_edges:]:
        global_drops[candidate.tier] += 1
    return EdgeMergeOutcome(
        candidates=tuple(kept),
        discarded_lower_tier=discarded_lower_tier,
        source_cap_dropped_l1=source_drops["L1"],
        source_cap_dropped_l2=source_drops["L2"],
        global_cap_dropped_l1=global_drops["L1"],
        global_cap_dropped_l2=global_drops["L2"],
    )


def canonical_edges(
    candidates: Sequence[EdgeCandidate],
) -> tuple[CanonicalEdge, ...]:
    return tuple(
        CanonicalEdge(
            edge_id=_edge_id(candidate.merge_key),
            source=candidate.source,
            target=candidate.target,
            relationship=candidate.relationship,
            status=candidate.status,
            evidence_ids=list(candidate.evidence_ids),
            undetermined_reason=candidate.undetermined_reason,
        )
        for candidate in candidates
    )


def _edge_id(key: tuple[str, str, str]) -> str:
    payload = json.dumps(
        key,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:24]
    return f"edge:ua:{digest}"
