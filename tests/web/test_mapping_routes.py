from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.web_flows import scan_project

from systograph.web.app import create_app


def test_mapping_routes_create_and_list_confirmed_mapping() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_file": "src/reranker.py",
            "observed_kind": "dependency_candidate",
            "evidence_ids": ["evidence:reranker"],
            "target_slot": "retriever",
            "component_name": "cross-encoder reranker",
            "component_kind": "reranker",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "confirmed"
    assert payload["mapping_digest"].startswith("sha256:")
    assert payload["target_slot"] == "retriever"

    list_response = client.get("/api/mappings?project_id=project:demo")

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["project_id"] == "project:demo"
    assert list_payload["available_actions"] == [
        "confirm",
        "edit",
        "reject",
        "skip_for_now",
        "mark_not_applicable",
    ]
    assert [item["mapping_id"] for item in list_payload["mappings"]] == [
        payload["mapping_id"]
    ]


def test_mapping_route_rejects_invalid_slot() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_file": "src/reranker.py",
            "evidence_ids": ["evidence:reranker"],
            "target_slot": "invalid_slot",
            "component_name": "reranker",
        },
    )

    assert response.status_code == 422
    assert "Unknown target slot" in response.json()["detail"]


def test_mapping_route_does_not_mutate_current_map_payload() -> None:
    client = TestClient(create_app())
    before = client.get("/api/map").json()

    response = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_file": "src/reranker.py",
            "evidence_ids": ["evidence:reranker"],
            "target_slot": "retriever",
            "component_name": "reranker",
        },
    )
    after = client.get("/api/map").json()

    assert response.status_code == 200
    assert after == before


def test_mapping_route_patch_updates_audit_decision() -> None:
    client = TestClient(create_app())
    created = client.post(
        "/api/mappings",
        json={
            "project_id": "project:demo",
            "mapping_type": "existing_slot_mapping",
            "decision": "skip_for_now",
            "source_file": "src/reranker.py",
            "evidence_ids": ["evidence:reranker"],
            "reason": "Need more context.",
        },
    ).json()

    response = client.patch(
        f"/api/mappings/{created['mapping_id']}",
        json={
            "decision": "rejected",
            "reason": "User rejected this mapping.",
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "rejected"
    assert response.json()["reason"] == "User rejected this mapping."


def test_confirmed_mapping_takes_effect_on_next_scan(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "weak_chroma_project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]

    first_scan = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    first_map = first_scan["build_result"]["ai_system_map"]
    unmapped = first_map["unmapped_components"][0]

    client.post(
        "/api/mappings",
        json={
            "project_id": project_id,
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_unmapped_id": unmapped["unmapped_id"],
            "source_file": unmapped["source_file"],
            "observed_kind": unmapped["observed_kind"],
            "evidence_ids": unmapped["evidence_ids"],
            "target_slot": "vector_store",
            "component_name": "Chroma",
            "component_kind": "vector_db",
        },
    )

    second_scan = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    second_map = second_scan["build_result"]["ai_system_map"]

    vector_store = next(
        component
        for component in second_map["components"]
        if component["metadata"].get("legacy_slot") == "vector_store"
    )
    assert vector_store["status"] == "detected"
    assert vector_store["display_name"] == "Chroma"
    assert second_map["unmapped_components"] == []
