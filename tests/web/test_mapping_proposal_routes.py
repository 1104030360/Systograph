from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.web_flows import scan_project

from systograph.core.models.mapping import (
    MappingEvidencePacket,
    MappingProposal,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalProviderUnavailableError,
    MappingProposalService,
)
from systograph.web.app import create_app


class UnavailableProvider:
    name = "unavailable-provider"

    def generate(
        self,
        *,
        packet: MappingEvidencePacket,
        output_schema: dict[str, object],
        validation_error: str | None = None,
    ) -> str:
        raise MappingProposalProviderUnavailableError("timeout")


def import_and_scan_weak_project(
    client: TestClient,
    tmp_path: Path,
    *,
    name: str = "weak_chroma_project",
    dependency: str = "chromadb==0.5.0",
) -> tuple[str, str]:
    project_root = tmp_path / name
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        f"{dependency}\n",
        encoding="utf-8",
    )
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]
    scan_payload = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    unmapped_id = scan_payload["build_result"]["ai_system_map"][
        "unmapped_components"
    ][0]["unmapped_id"]
    return project_id, unmapped_id


def create_deterministic_test_app() -> TestClient:
    manual_mapping_service = ManualMappingService()
    proposal_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        manual_mapping_service=manual_mapping_service,
    )
    return TestClient(
        create_app(
            manual_mapping_service=manual_mapping_service,
            mapping_proposal_service=proposal_service,
        )
    )


def create_nonbaseline_decision_test_app() -> tuple[
    TestClient,
    MappingProposal,
]:
    manual_mapping_service = ManualMappingService()
    proposal_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        manual_mapping_service=manual_mapping_service,
    )
    proposal = proposal_service.create_proposal(
        MappingEvidencePacket(
            project_id="project:demo",
            source_unmapped_id="unmapped:src_router_py:route",
            source_file="src/router.py",
            observed_kind="code_pattern",
            reason="Router-like code needs confirmation.",
            evidence_ids=["evidence:router"],
            rule_ids=["code_pattern_custom_router"],
            masked_evidence_values=["route_query"],
            call_like_signals=["QueryRouter.route"],
            available_slots=["app_api_or_orchestrator", "retriever"],
            confirmed_component_ids=["component:retriever:retriever"],
        )
    )
    client = TestClient(
        create_app(
            manual_mapping_service=manual_mapping_service,
            mapping_proposal_service=proposal_service,
        )
    )
    return client, proposal


def test_proposal_routes_create_and_list_pending_proposal(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    latest_url = f"/api/projects/{project_id}/map-builds/latest"
    before = client.get(latest_url).json()
    # Pin the baseline as a real projection: without this, a latest that
    # degraded to 404 would make both sides equal error bodies and pass.
    assert before["viewer_load_result"]["loaded"] is True
    assert before["viewer_load_result"]["graph_view_model"]["nodes"]

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
            "user_description": "This may be the vector store client.",
        },
    )
    after = client.get(latest_url).json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending_user_confirmation"
    assert payload["source_unmapped_id"] == unmapped_id
    assert payload["provider_name"] == "deterministic"
    assert payload["candidates"][0]["target_slot"] == "vector_store"
    assert "confidence" not in str(payload)
    assert after == before

    list_response = client.get(
        f"/api/mapping-proposals?project_id={project_id}"
    )

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["project_id"] == project_id
    assert [item["proposal_id"] for item in list_payload["proposals"]] == [
        payload["proposal_id"]
    ]


def test_proposal_create_uses_requested_project_build_result(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_b_id, _project_b_unmapped_id = import_and_scan_weak_project(
        client,
        tmp_path,
        name="weak_chroma_project",
        dependency="chromadb==0.5.0",
    )
    _project_a_id, project_a_unmapped_id = import_and_scan_weak_project(
        client,
        tmp_path,
        name="weak_qdrant_project",
        dependency="qdrant-client==1.7.0",
    )

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_b_id,
            "source_unmapped_id": project_a_unmapped_id,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "unmapped_not_found"


def test_proposal_decision_accept_creates_manual_mapping(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    ).json()
    candidate_id = proposal["candidates"][0]["candidate_id"]

    decision_response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "accept",
            "candidate_id": candidate_id,
        },
    )

    assert decision_response.status_code == 200
    decision_payload = decision_response.json()
    assert decision_payload["proposal"]["status"] == "accepted"
    assert (
        decision_payload["manual_mapping"]["proposal_id"]
        == (proposal["proposal_id"])
    )
    assert decision_payload["manual_mapping"]["target_slot"] == "vector_store"

    mappings = client.get(f"/api/mappings?project_id={project_id}").json()
    assert [item["mapping_id"] for item in mappings["mappings"]] == [
        decision_payload["manual_mapping"]["mapping_id"]
    ]


def test_proposal_decision_edit_creates_manual_mapping(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    ).json()

    decision_response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "edit",
            "edited_mapping": {
                "project_id": project_id,
                "mapping_type": "existing_slot_mapping",
                "decision": "confirmed",
                "source_unmapped_id": unmapped_id,
                "evidence_ids": proposal["evidence_packet"]["evidence_ids"],
                "target_slot": "vector_store",
                "component_name": "Edited Chroma",
                "component_kind": "vector_db",
            },
        },
    )

    assert decision_response.status_code == 200
    payload = decision_response.json()
    assert payload["proposal"]["status"] == "edited"
    assert payload["manual_mapping"]["decision_source"] == "proposal_edit"
    assert payload["manual_mapping"]["component_name"] == "Edited Chroma"


def test_proposal_decision_skip_for_now_returns_durable_mapping(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    ).json()

    response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={"decision": "skip_for_now", "reason": "Later."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal"]["status"] == "skipped"
    assert payload["manual_mapping"]["decision"] == "skip_for_now"
    assert payload["manual_mapping"]["audit_metadata"]["actor_surface"] == (
        "mapping_proposal"
    )


def test_nonbaseline_proposal_skip_for_now_persists_audit_shape() -> None:
    client, proposal = create_nonbaseline_decision_test_app()

    response = client.post(
        f"/api/mapping-proposals/{proposal.proposal_id}/decision",
        json={"decision": "skip_for_now", "reason": "Decide later."},
    )

    assert response.status_code == 200
    payload = response.json()
    audit = payload["manual_mapping"]
    assert payload["proposal"]["status"] == "skipped"
    assert audit["decision"] == "skip_for_now"
    assert audit["proposal_id"] == proposal.proposal_id
    assert audit["source_unmapped_id"] == "unmapped:src_router_py:route"
    assert audit["observed_kind"] == "code_pattern"
    assert audit["capability_candidate_id"] == (
        "capability-candidate:query_router"
    )
    assert audit["capability_candidate_name"] == "Query Router"
    assert audit["capability_candidate_kind"] == "routing_orchestration"
    assert audit["decision_source"] == "proposal_skip_for_now"
    assert audit["audit_metadata"]["actor_surface"] == "mapping_proposal"

    mappings_response = client.get("/api/mappings?project_id=project:demo")
    assert mappings_response.status_code == 200
    persisted = mappings_response.json()["mappings"]
    assert len(persisted) == 1
    assert persisted[0]["mapping_id"] == audit["mapping_id"]
    assert persisted[0]["capability_candidate_id"] == (
        "capability-candidate:query_router"
    )
    assert persisted[0]["capability_candidate_name"] == "Query Router"
    assert persisted[0]["capability_candidate_kind"] == (
        "routing_orchestration"
    )


def test_nonbaseline_proposal_reject_persists_audit_shape() -> None:
    client, proposal = create_nonbaseline_decision_test_app()

    response = client.post(
        f"/api/mapping-proposals/{proposal.proposal_id}/decision",
        json={"decision": "reject", "reason": "Not part of the RAG path."},
    )

    assert response.status_code == 200
    payload = response.json()
    audit = payload["manual_mapping"]
    assert payload["proposal"]["status"] == "rejected"
    assert audit["decision"] == "rejected"
    assert audit["proposal_id"] == proposal.proposal_id
    assert audit["source_unmapped_id"] == "unmapped:src_router_py:route"
    assert audit["observed_kind"] == "code_pattern"
    assert audit["capability_candidate_id"] == (
        "capability-candidate:query_router"
    )
    assert audit["capability_candidate_name"] == "Query Router"
    assert audit["capability_candidate_kind"] == "routing_orchestration"
    assert audit["decision_source"] == "proposal_reject"
    assert audit["audit_metadata"]["actor_surface"] == "mapping_proposal"

    mappings_response = client.get("/api/mappings?project_id=project:demo")
    assert mappings_response.status_code == 200
    persisted = mappings_response.json()["mappings"]
    assert len(persisted) == 1
    assert persisted[0]["mapping_id"] == audit["mapping_id"]
    assert persisted[0]["capability_candidate_id"] == (
        "capability-candidate:query_router"
    )
    assert persisted[0]["capability_candidate_name"] == "Query Router"
    assert persisted[0]["capability_candidate_kind"] == (
        "routing_orchestration"
    )


def test_proposal_decision_missing_proposal_returns_404() -> None:
    client = create_deterministic_test_app()

    response = client.post(
        "/api/mapping-proposals/proposal:missing/decision",
        json={"decision": "reject", "reason": "No proposal."},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "proposal_not_found"


def test_proposal_decision_second_request_returns_422(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    ).json()
    candidate_id = proposal["candidates"][0]["candidate_id"]
    first_response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "accept",
            "candidate_id": candidate_id,
        },
    )

    second_response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={"decision": "reject", "reason": "late retry"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 422
    assert "Proposal is not pending" in second_response.json()["detail"]


def test_proposal_route_falls_back_when_provider_is_unavailable(
    tmp_path: Path,
) -> None:
    proposal_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        provider=UnavailableProvider(),
    )
    client = TestClient(
        create_app(mapping_proposal_service=proposal_service),
    )
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_name"] == "deterministic"
    assert payload["provider_error_reason"] == "provider_unavailable"
    assert payload["candidates"][0]["target_slot"] == "vector_store"


def test_proposal_route_requires_existing_project() -> None:
    client = create_deterministic_test_app()

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": "project:missing",
            "source_unmapped_id": "unmapped:missing",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "project_not_found"


def test_proposal_route_requires_loaded_map(tmp_path: Path) -> None:
    client = create_deterministic_test_app()
    project_root = tmp_path / "unscanned_project"
    project_root.mkdir()
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": "unmapped:missing",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "map_not_loaded"
