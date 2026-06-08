from __future__ import annotations

from kai_mind.core.models.system_map import Evidence, UnmappedComponent
from kai_mind.core.services.mapping_evidence_packet_builder import (
    MappingEvidencePacketBuilder,
)


def test_builder_masks_evidence_and_keeps_traceable_metadata() -> None:
    packet = MappingEvidencePacketBuilder(max_value_chars=80).build(
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
        available_extensions=["extension:reranker"],
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
        "OPENAI_API_KEY=sk-l...7890 route_query"
    ]
    assert packet.masked_snippets == [
        "OPENAI_API_KEY=sk-l...7890\nclass QueryRouter: ..."
    ]
    assert packet.available_slots == ["retriever", "vector_store"]
    assert packet.available_extensions == ["extension:reranker"]
    assert packet.confirmed_component_ids == ["component:retriever:main"]
    assert packet.context_limits["source"] == "existing_evidence_array"


def test_builder_keeps_only_referenced_evidence() -> None:
    packet = MappingEvidencePacketBuilder().build(
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
    packet = MappingEvidencePacketBuilder().build(
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
