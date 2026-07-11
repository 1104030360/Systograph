from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import (
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalUnmappedComponent,
)
from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
    ManualMappingType,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.static_execution_artifact_service import (
    StaticExecutionArtifactService,
)


def mapping(
    decision: ManualMappingDecision,
    evidence_id: str,
) -> ManualMapping:
    return ManualMapping(
        project_id="project:test",
        mapping_type=ManualMappingType.EXISTING_SLOT,
        decision=decision,
        evidence_ids=[evidence_id],
        mapping_id=f"mapping:{decision.value}",
        mapping_digest=f"sha256:{decision.value}",
        created_at="2026-07-11T00:00:00Z",
        updated_at="2026-07-11T00:00:00Z",
    )


def test_evidence_review_state_tracks_durable_mapping_decisions() -> None:
    fixture = Path(
        "tests/fixtures/ai_system_map/v2/non_grounded_llm_app.v2.json"
    )
    system_map = (
        CanonicalMapLoader()
        .load(json.loads(fixture.read_text(encoding="utf-8")))
        .normalized
    )
    evidence_ids = (
        "evidence:confirmed",
        "evidence:rejected",
        "evidence:not-applicable",
        "evidence:skipped",
        "evidence:pending",
        "evidence:not-required",
    )
    evidence = [
        CanonicalEvidence(
            evidence_id=evidence_id,
            artifact_type="source_code",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(path=f"src/{index}.py"),
        )
        for index, evidence_id in enumerate(evidence_ids)
    ]
    unmapped = [
        CanonicalUnmappedComponent(
            unmapped_id=f"unmapped:{index}",
            observed_kind="ambiguous_component",
            status="needs_confirmation",
            reason="User review is required.",
            evidence_ids=[evidence_id],
        )
        for index, evidence_id in enumerate(
            ("evidence:skipped", "evidence:pending")
        )
    ]
    system_map = system_map.model_copy(
        update={"evidence": evidence, "unmapped_components": unmapped}
    )

    artifacts = StaticExecutionArtifactService().build(
        system_map,
        manual_mappings=(
            mapping(ManualMappingDecision.CONFIRMED, "evidence:confirmed"),
            mapping(ManualMappingDecision.REJECTED, "evidence:rejected"),
            mapping(
                ManualMappingDecision.NOT_APPLICABLE,
                "evidence:not-applicable",
            ),
            mapping(ManualMappingDecision.SKIP_FOR_NOW, "evidence:skipped"),
        ),
    )

    states = {
        row.evidence_id: row.review_state
        for row in artifacts.evidence_table.rows
    }
    assert states == {
        "evidence:confirmed": "confirmed",
        "evidence:rejected": "rejected",
        "evidence:not-applicable": "not_required",
        "evidence:skipped": "needs_confirmation",
        "evidence:pending": "needs_confirmation",
        "evidence:not-required": "not_required",
    }
