from __future__ import annotations

from kai_mind.core.models.mapping import (
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
)
from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionService,
)
from kai_mind.core.services.manual_mapping_service import (
    InMemoryManualMappingRepository,
    ManualMappingService,
)
from kai_mind.core.services.rag_template_service import RagTemplateService


def ambiguous_vector_dependency() -> tuple[ScanFact, Evidence]:
    evidence = Evidence(
        id="evidence:chromadb_dependency",
        kind="dependency_candidate",
        file="requirements.txt",
        path="line[1]",
        value="chromadb",
        rule_id="dependency_vector_store_client_chromadb",
    )
    return (
        ScanFact(
            kind=evidence.kind,
            file=evidence.file or "",
            path=evidence.path or "",
            value=evidence.value,
            rule_id=evidence.rule_id,
        ),
        evidence,
    )


def reranker_extension_candidate() -> tuple[ScanFact, Evidence]:
    evidence = Evidence(
        id="evidence:reranker",
        kind="code_pattern",
        file="src/rerank.py",
        path="Reranker.rerank",
        value="rerank_documents",
        rule_id="code_pattern_reranker",
    )
    return (
        ScanFact(
            kind=evidence.kind,
            file=evidence.file or "",
            path=evidence.path or "",
            value=evidence.value,
            rule_id=evidence.rule_id,
        ),
        evidence,
    )


def test_confirmed_mapping_moves_unmapped_into_existing_slot() -> None:
    fact, evidence = ambiguous_vector_dependency()
    repository = InMemoryManualMappingRepository()
    manual_mapping_service = ManualMappingService(
        repository=repository,
        allowed_slots={"vector_store"},
        project_id="project:demo",
    )
    manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=ManualMappingDecision.CONFIRMED,
            source_file="requirements.txt",
            observed_kind="dependency_candidate",
            evidence_ids=[evidence.id],
            target_slot="vector_store",
            component_name="Chroma",
            component_kind="vector_db",
        )
    )

    result = ComponentDetectionService(
        manual_mapping_hook=manual_mapping_service,
    ).detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=[fact],
        evidence=[evidence],
    )

    vector_store = result.components_by_slot["vector_store"]
    assert vector_store.status == "detected"
    assert vector_store.instances[0].name == "Chroma"
    assert vector_store.instances[0].kind == "vector_db"
    assert vector_store.instances[0].evidence_ids == [evidence.id]
    assert result.unmapped_components == []


def test_rejected_mapping_keeps_unmapped_component_out_of_slots() -> None:
    fact, evidence = ambiguous_vector_dependency()
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        allowed_slots={"vector_store"},
        project_id="project:demo",
    )
    manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.EXISTING_SLOT,
            decision=ManualMappingDecision.REJECTED,
            source_file="requirements.txt",
            evidence_ids=[evidence.id],
            reason="User rejected this mapping.",
        )
    )

    result = ComponentDetectionService(
        manual_mapping_hook=manual_mapping_service,
    ).detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=[fact],
        evidence=[evidence],
    )

    assert result.components_by_slot["vector_store"].status == "missing"
    assert len(result.unmapped_components) == 1


def test_confirmed_extension_mapping_replays_live_candidate() -> None:
    fact, evidence = reranker_extension_candidate()
    manual_mapping_service = ManualMappingService(
        repository=InMemoryManualMappingRepository(),
        project_id="project:demo",
    )
    manual_mapping_service.create_mapping(
        ManualMappingCreate(
            project_id="project:demo",
            mapping_type=ManualMappingType.NEW_EXTENSION,
            decision=ManualMappingDecision.CONFIRMED,
            source_file="src/rerank.py",
            observed_kind="code_pattern",
            evidence_ids=[evidence.id],
            extension_id="extension:src_rerank_py:reranker",
            extension_name="Reranker",
            extension_kind="reranker",
        )
    )

    result = ComponentDetectionService(
        manual_mapping_hook=manual_mapping_service,
    ).detect(
        template=RagTemplateService.load("rag-core-v1"),
        facts=[fact],
        evidence=[evidence],
    )

    assert result.unmapped_components == []
    assert result.extensions[0].id == "extension:src_rerank_py:reranker"
    assert result.extensions[0].status == "confirmed"
    assert result.extensions[0].confirmed_by_user is True
