from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.web_flows import scan_project

from systograph.core.models.mapping import (
    ManualMappingType,
    MappingCandidateType,
)
from systograph.core.services.manual_mapping_service import (
    ManualMappingService,
)
from systograph.core.services.mapping_proposal_service import (
    InMemoryMappingProposalRepository,
    MappingProposalService,
)
from systograph.web.app import create_app


def test_active_mapping_enums_do_not_contain_legacy_extension() -> None:
    assert "new_extension_component" not in {
        item.value for item in ManualMappingType
    }
    assert "new_extension_component" not in {
        item.value for item in MappingCandidateType
    }


def test_mapping_api_rejects_legacy_type_with_stable_code(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))

    response = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "new_extension_component",
            "decision": "confirmed",
            "source_unmapped_id": "unmapped:router",
            "source_file": "src/router.py",
            "observed_kind": "router_like_evidence",
            "evidence_ids": ["evidence:router"],
            "extension_id": "extension:router",
            "extension_name": "Router",
            "extension_kind": "routing",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "legacy_mapping_type_read_only"


def test_mapping_patch_rejects_legacy_type_with_stable_code(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    created = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "existing_slot_mapping",
            "decision": "skip_for_now",
            "source_file": "src/router.py",
            "evidence_ids": ["evidence:router"],
            "reason": "Need more context.",
        },
    ).json()

    response = client.patch(
        f"/api/mappings/{created['mapping_id']}",
        json={
            "mapping_type": "new_extension_component",
            "decision": "confirmed",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "legacy_mapping_type_read_only"


def test_proposal_decision_rejects_legacy_type_with_stable_code(
    tmp_path: Path,
) -> None:
    manual_mapping_service = ManualMappingService()
    proposal_service = MappingProposalService(
        repository=InMemoryMappingProposalRepository(),
        manual_mapping_service=manual_mapping_service,
    )
    client = TestClient(
        create_app(
            state_dir=tmp_path / "state",
            manual_mapping_service=manual_mapping_service,
            mapping_proposal_service=proposal_service,
        )
    )
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
    scan_payload = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    unmapped_id = scan_payload["build_result"]["ai_system_map"][
        "unmapped_components"
    ][0]["unmapped_id"]
    proposal = client.post(
        "/api/mapping-proposals",
        json={
            "project_id": project_id,
            "source_unmapped_id": unmapped_id,
        },
    ).json()

    response = client.post(
        f"/api/mapping-proposals/{proposal['proposal_id']}/decision",
        json={
            "decision": "edit",
            "edited_mapping": {
                "project_id": project_id,
                "mapping_type": "new_extension_component",
                "decision": "confirmed",
                "source_unmapped_id": unmapped_id,
                "source_file": "src/router.py",
                "observed_kind": "router_like_evidence",
                "evidence_ids": proposal["evidence_packet"]["evidence_ids"],
                "extension_id": "extension:router",
                "extension_name": "Router",
                "extension_kind": "routing",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "legacy_mapping_type_read_only"
