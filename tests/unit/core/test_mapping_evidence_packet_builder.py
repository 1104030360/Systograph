from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalProject,
    CanonicalUnmappedComponent,
)
from kai_mind.core.models.mapping import MappingEvidencePacket
from kai_mind.core.models.system_map import (
    Evidence,
    RagSystemMap,
    UnmappedComponent,
)
from kai_mind.core.services.mapping_evidence_packet_builder import (
    MappingEvidencePacketBuilder,
)
from kai_mind.core.services.system_map_index import SystemMapIndex
from kai_mind.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)

RICH_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "valid_rich_frontend_sample.v1.json"
)


def _build_packet(
    builder: MappingEvidencePacketBuilder,
    *,
    project_id: str,
    unmapped_component: UnmappedComponent,
    evidence: list[Evidence],
    available_slots: list[str],
    confirmed_component_ids: list[str] | None = None,
    user_description: str | None = None,
) -> MappingEvidencePacket:
    canonical_evidence = [
        CanonicalEvidence(
            evidence_id=item.id,
            artifact_type=item.kind,
            evidence_kind="direct" if item.file else "indirect",
            location=CanonicalEvidenceLocation(
                path=item.file,
                start_line=item.line_start,
                end_line=item.line_end,
                json_pointer=(
                    item.path
                    if item.path and item.path.startswith("/")
                    else None
                ),
                config_key=(
                    item.path
                    if item.path and not item.path.startswith("/")
                    else None
                ),
            ),
            # Keep helper aligned with production adapter:
            # extract_summary = snippet or value.
            extract_summary=item.snippet or item.value,
            rule_id=item.rule_id,
        )
        for item in evidence
    ]
    canonical = AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        project=CanonicalProject(name="packet-test"),
        evidence=canonical_evidence,
        unmapped_components=[
            CanonicalUnmappedComponent(
                unmapped_id=unmapped_component.id,
                observed_kind=unmapped_component.observed_kind,
                status=unmapped_component.status,
                reason=unmapped_component.reason,
                source_file=unmapped_component.source_file,
                evidence_ids=list(unmapped_component.evidence_ids),
                suggested_actions=list(unmapped_component.suggested_actions),
            )
        ],
    )
    return builder.build(
        project_id=project_id,
        index=SystemMapIndex.from_map(canonical),
        unmapped_id=unmapped_component.id,
        available_slots=available_slots,
        confirmed_component_ids=confirmed_component_ids,
        user_description=user_description,
    )


def test_builder_consumes_normalized_index_facts_without_mutation() -> None:
    legacy = RagSystemMap.model_validate_json(
        RICH_MAP.read_text(encoding="utf-8")
    )
    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(legacy)
    original = canonical.model_copy(deep=True)
    index = SystemMapIndex.from_map(canonical)
    unmapped = canonical.unmapped_components[0]

    packet = MappingEvidencePacketBuilder().build(
        project_id="project:demo",
        index=index,
        unmapped_id=unmapped.unmapped_id,
        available_slots=["retriever"],
        confirmed_component_ids=[],
    )

    assert packet.source_unmapped_id == unmapped.unmapped_id
    assert packet.evidence_ids == unmapped.evidence_ids
    assert canonical == original


def test_builder_masks_evidence_and_keeps_traceable_metadata() -> None:
    packet = _build_packet(
        MappingEvidencePacketBuilder(max_value_chars=80),
        project_id="project:demo",
        unmapped_component=UnmappedComponent(
            id="unmapped:src_router_py:route:code_pattern_custom_router",
            source_file="src/router.py",
            observed_kind="code_pattern",
            status="needs_confirmation",
            reason="Detected router-like code pending confirmation.",
            evidence_ids=["evidence:router"],
            suggested_actions=["confirm_mapping"],
        ),
        evidence=[
            Evidence(
                id="evidence:router",
                kind="code_pattern",
                file="src/router.py",
                path="QueryRouter.route",
                value="OPENAI_API_KEY=sk-live-1234567890 route_query",
                rule_id="code_pattern_custom_router",
                line_start=7,
                line_end=9,
                snippet=(
                    "OPENAI_API_KEY=sk-live-1234567890\nclass QueryRouter: ..."
                ),
            )
        ],
        available_slots=["retriever", "vector_store"],
        confirmed_component_ids=["component:retriever:main"],
    )

    serialized = str(packet.model_dump(mode="json"))
    assert "sk-live-1234567890" not in serialized
    assert packet.project_id == "project:demo"
    assert packet.source_unmapped_id == (
        "unmapped:src_router_py:route:code_pattern_custom_router"
    )
    assert packet.source_file == "src/router.py"
    assert packet.evidence_ids == ["evidence:router"]
    assert packet.rule_ids == ["code_pattern_custom_router"]
    assert packet.line_ranges == ["src/router.py:7-9"]
    assert packet.masked_evidence_values == [
        "OPENAI_API_KEY=sk-l...7890\nclass QueryRouter: ..."
    ]
    assert packet.masked_snippets == [
        "OPENAI_API_KEY=sk-l...7890\nclass QueryRouter: ..."
    ]
    assert packet.available_slots == ["retriever", "vector_store"]
    assert packet.confirmed_component_ids == ["component:retriever:main"]
    assert packet.context_limits["source"] == "system_map_index"


def test_builder_keeps_only_referenced_evidence() -> None:
    packet = _build_packet(
        MappingEvidencePacketBuilder(),
        project_id="project:demo",
        unmapped_component=UnmappedComponent(
            id="unmapped:requirements_txt:line_1:dependency",
            source_file="requirements.txt",
            observed_kind="dependency_candidate",
            status="needs_confirmation",
            reason="Weak dependency signal.",
            evidence_ids=["evidence:used"],
        ),
        evidence=[
            Evidence(
                id="evidence:used",
                kind="dependency_candidate",
                file="requirements.txt",
                path="line[1]",
                value="chromadb",
                rule_id="dependency_vector_store_client_chromadb",
            ),
            Evidence(
                id="evidence:unused",
                kind="dependency_candidate",
                file="requirements.txt",
                path="line[2]",
                value="pytest",
                rule_id="dependency_test_pytest",
            ),
        ],
        available_slots=["vector_store"],
    )

    assert packet.evidence_ids == ["evidence:used"]
    assert packet.masked_evidence_values == ["chromadb"]
    assert packet.dependency_signals == ["chromadb"]


def test_builder_masks_and_truncates_user_description() -> None:
    packet = _build_packet(
        MappingEvidencePacketBuilder(),
        project_id="project:demo",
        unmapped_component=UnmappedComponent(
            id="unmapped:requirements_txt:line_1:dependency",
            source_file="requirements.txt",
            observed_kind="dependency_candidate",
            status="needs_confirmation",
            reason="Weak dependency signal.",
            evidence_ids=["evidence:used"],
        ),
        evidence=[
            Evidence(
                id="evidence:used",
                kind="dependency_candidate",
                file="requirements.txt",
                value="chromadb",
                rule_id="dependency_vector_store_client_chromadb",
            )
        ],
        available_slots=["vector_store"],
        user_description=(
            "This may use sk-live-1234567890 as the vector store key. "
            + "x" * 1200
        ),
    )

    assert packet.user_description is not None
    assert "sk-live-1234567890" not in packet.user_description
    assert len(packet.user_description) <= 1014
    assert packet.user_description.endswith("...[truncated]")


def test_builder_consumes_detail_scan_evidence_from_existing_index() -> None:
    packet = _build_packet(
        MappingEvidencePacketBuilder(max_value_chars=120),
        project_id="project:demo",
        unmapped_component=UnmappedComponent(
            id="unmapped:router",
            source_file="src/router.py",
            observed_kind="router_like_evidence",
            status="needs_confirmation",
            reason="Custom router needs confirmation.",
            evidence_ids=[
                "evidence:l1-router",
                "evidence:detail-scan:unmapped-router:src-router-py:11:call",
            ],
        ),
        evidence=[
            Evidence(
                id="evidence:l1-router",
                kind="code_pattern",
                file="src/router.py",
                path="line[10]",
                value="custom router",
                rule_id="code_pattern_custom_router",
            ),
            Evidence(
                id="evidence:detail-scan:unmapped-router:src-router-py:11:call",
                kind="detail_scan_call_like",
                file="src/router.py",
                path="Router.build_chain",
                value="Router.build_chain(question)",
                rule_id="detail_scan.python_call_like",
                line_start=11,
                line_end=11,
                snippet="route = Router.build_chain(question)",
            ),
        ],
        available_slots=["retriever"],
    )

    assert packet.evidence_ids == [
        "evidence:l1-router",
        "evidence:detail-scan:unmapped-router:src-router-py:11:call",
    ]
    assert packet.call_like_signals == ["Router.build_chain"]
    assert packet.line_ranges == ["src/router.py:11-11"]


def test_builder_masks_url_credentials_in_evidence_packet() -> None:
    raw_url = "postgresql://demo:synthetic-pass-138@db.example:5432/app"
    packet = _build_packet(
        MappingEvidencePacketBuilder(),
        project_id="project:demo",
        unmapped_component=UnmappedComponent(
            id="unmapped:database",
            source_file="config.yaml",
            observed_kind="database",
            status="needs_confirmation",
            reason="Database candidate.",
            evidence_ids=["evidence:database"],
        ),
        evidence=[
            Evidence(
                id="evidence:database",
                kind="config_value",
                file="config.yaml",
                path="database.url",
                value=raw_url,
                snippet=f"DATABASE_URL={raw_url}",
                rule_id="config_yaml_value_detected",
            )
        ],
        available_slots=["vector_store"],
    )

    serialized = str(packet.model_dump(mode="json"))
    assert raw_url not in serialized
    assert "synthetic-pass-138" not in serialized
    assert "[MASKED]" in serialized


def test_production_adapter_preserves_value_only_evidence_in_packet() -> None:
    # Given: real adapter path (not helper bypass) with null snippets
    legacy = RagSystemMap.model_validate_json(
        RICH_MAP.read_text(encoding="utf-8")
    )
    config_evidence = Evidence(
        id="evidence:config-custom-router",
        kind="config_value",
        file="config.yaml",
        path="routing.custom_query_router",
        value="custom_query_router",
        snippet=None,
        rule_id="config_yaml_value_detected",
    )
    dependency_evidence = Evidence(
        id="evidence:dependency-langchain-core",
        kind="dependency_candidate",
        file="requirements.txt",
        path="line[3]",
        value="langchain-core",
        snippet=None,
        rule_id="dependency_framework_langchain",
    )
    unmapped = UnmappedComponent(
        id="unmapped:custom-router-value-only",
        source_file="config.yaml",
        observed_kind="custom_router",
        status="needs_confirmation",
        reason="Custom router candidate from config/dependency signals.",
        evidence_ids=[
            config_evidence.id,
            dependency_evidence.id,
        ],
        suggested_actions=["confirm_mapping"],
    )
    extended = legacy.model_copy(
        update={
            "evidence": [
                *legacy.evidence,
                config_evidence,
                dependency_evidence,
            ],
            "unmapped_components": [
                *legacy.unmapped_components,
                unmapped,
            ],
        }
    )
    canonical = SystemMapV1ToV2Adapter().adapt_to_canonical(extended)

    # When
    packet = MappingEvidencePacketBuilder().build(
        project_id="project:demo",
        index=SystemMapIndex.from_map(canonical),
        unmapped_id=unmapped.id,
        available_slots=["retriever"],
    )

    # Then
    assert packet.masked_evidence_values == [
        "custom_query_router",
        "langchain-core",
    ]
    assert packet.dependency_signals == ["langchain-core"]
