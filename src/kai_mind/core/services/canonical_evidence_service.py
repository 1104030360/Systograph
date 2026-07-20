from __future__ import annotations

from kai_mind.core.models.ai_system_map_v2 import (
    AssessmentEvidenceKind,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
)
from kai_mind.core.models.system_map import Evidence


def canonical_evidence_from_scan(
    item: Evidence,
    *,
    no_snippets: bool,
) -> CanonicalEvidence:
    json_pointer = (
        item.path
        if item.path is not None and item.path.startswith("/")
        else None
    )
    config_key = (
        item.path
        if item.path is not None and not item.path.startswith("/")
        else None
    )
    evidence_kind: AssessmentEvidenceKind = (
        "direct"
        if item.file is not None
        and (item.line_start is not None or json_pointer is not None)
        else "indirect"
    )
    return CanonicalEvidence(
        evidence_id=item.id,
        artifact_type=item.kind,
        evidence_kind=evidence_kind,
        location=CanonicalEvidenceLocation(
            path=item.file,
            start_line=item.line_start,
            end_line=item.line_end,
            json_pointer=json_pointer,
            config_key=config_key,
        ),
        extract_summary=None if no_snippets else item.snippet or item.value,
        rule_id=item.rule_id,
    )
