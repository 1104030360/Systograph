from __future__ import annotations

import pytest

from kai_mind.core.models.mapping import (
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
)
from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)


def service() -> ManualMappingService:
    return ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"retriever", "vector_store"},
    )


def test_confirmed_existing_slot_mapping_is_persisted_by_project() -> None:
    mapping = service().create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=ManualMappingDecision.CONFIRMED,
            source_unmapped_id="unmapped:reranker",
            source_file="src/reranker.py",
            observed_kind="dependency_candidate",
            evidence_ids=["evidence:reranker"],
            target_slot="retriever",
            component_name="cross-encoder reranker",
            component_kind="reranker",
        )
    )

    assert mapping.mapping_id.startswith("mapping:")
    assert mapping.mapping_digest.startswith("sha256:")
    assert mapping.project_id == "project:demo"
    assert mapping.decision == ManualMappingDecision.CONFIRMED
    assert mapping.target_slot == "retriever"
    assert mapping.component_name == "cross-encoder reranker"


def test_invalid_slot_mapping_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown target slot"):
        service().create_mapping(
            ManualMappingCreate(
                project_id="project:demo",
                mapping_type=ManualMappingType.EXISTING_SLOT,
                decision=ManualMappingDecision.CONFIRMED,
                source_file="src/reranker.py",
                evidence_ids=["evidence:reranker"],
                target_slot="invalid_slot",
                component_name="reranker",
            )
        )


@pytest.mark.parametrize(
    "decision",
    [
        ManualMappingDecision.REJECTED,
        ManualMappingDecision.SKIP_FOR_NOW,
        ManualMappingDecision.NOT_APPLICABLE,
    ],
)
def test_non_confirmed_decisions_are_audit_only(
    decision: ManualMappingDecision,
) -> None:
    mapping = service().create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=decision,
            source_unmapped_id="unmapped:reranker",
            source_file="src/reranker.py",
            observed_kind="dependency_candidate",
            evidence_ids=["evidence:reranker"],
            reason="User decided this is not part of the RAG path.",
        )
    )

    assert mapping.decision == decision
    assert mapping.target_slot is None
    assert mapping.component_name is None


def test_unmasked_secret_like_payload_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not contain unmasked secrets"):
        service().create_mapping(
            ManualMappingCreate(
                project_id="project:demo",
                mapping_type=ManualMappingType.EXISTING_SLOT,
                decision=ManualMappingDecision.CONFIRMED,
                source_file="src/reranker.py",
                evidence_ids=["evidence:reranker"],
                target_slot="retriever",
                component_name="reranker",
                audit_metadata={"raw_value": "sk-live-1234567890"},
            )
        )


def test_extension_edge_with_unknown_endpoint_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown endpoint"):
        service().create_mapping(
            ManualMappingCreate(
                project_id="project:demo",
                mapping_type=ManualMappingType.NEW_EXTENSION,
                decision=ManualMappingDecision.CONFIRMED,
                source_file="src/router.py",
                evidence_ids=["evidence:router"],
                extension_id="extension:query_router",
                extension_name="Query Router",
                extension_kind="routing_orchestration",
                extension_edges=[
                    {
                        "from": "app_api_or_orchestrator",
                        "to": "missing_extension",
                        "relationship": "routes_query",
                    }
                ],
            )
        )


def test_list_for_project_does_not_leak_other_projects() -> None:
    manual_mapping_service = service()
    mapping = manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:a",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=ManualMappingDecision.CONFIRMED,
            source_file="src/reranker.py",
            evidence_ids=["evidence:reranker"],
            target_slot="retriever",
            component_name="reranker",
        )
    )
    manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:b",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=ManualMappingDecision.CONFIRMED,
            source_file="src/vector.py",
            evidence_ids=["evidence:vector"],
            target_slot="vector_store",
            component_name="vector store",
        )
    )

    assert manual_mapping_service.list_for_project("project:a") == [mapping]
