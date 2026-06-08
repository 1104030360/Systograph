from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from kai_mind.core.models.mapping import MappingEvidencePacket
from kai_mind.core.providers.llm_proposal_provider import (
    MappingProposalProviderUnavailableError,
)
from kai_mind.core.services.manual_mapping_service import ManualMappingService
from kai_mind.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalService,
)
from kai_mind.web.app import create_app


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
) -> tuple[str, str]:
    project_root = tmp_path / "weak_chroma_project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]
    scan_payload = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
        },
    ).json()
    unmapped_id = scan_payload["build_result"]["ai_system_map"][
        "unmapped_components"
    ][0]["id"]
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


def test_proposal_routes_create_and_list_pending_proposal(
    tmp_path: Path,
) -> None:
    client = create_deterministic_test_app()
    project_id, unmapped_id = import_and_scan_weak_project(client, tmp_path)
    before = client.get("/api/map").json()

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
            "user_description": "This may be the vector store client.",
        },
    )
    after = client.get("/api/map").json()

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
    assert payload["provider_error_reason"] == "timeout"
    assert payload["candidates"][0]["target_slot"] == "vector_store"


def test_proposal_route_requires_loaded_map() -> None:
    client = create_deterministic_test_app()

    response = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": "project:missing",
            "source_unmapped_id": "unmapped:missing",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "map_not_loaded"
