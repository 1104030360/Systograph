from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kai_mind.core.models.map_build import SystemMapSchemaSelection
from kai_mind.web.app import create_app


def prepare_apply(
    client: TestClient,
    tmp_path: Path,
    *,
    schema_version: SystemMapSchemaSelection = "ai-system-map/v1",
) -> tuple[str, str, str]:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "chromadb==0.5.0\n",
        encoding="utf-8",
    )
    imported = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()
    project_id = str(imported["project_id"])
    scan = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "output"),
            "system_map_schema_version": schema_version,
        },
    ).json()
    build_id = str(scan["build_result"]["lineage"]["build_id"])
    unmapped = scan["build_result"]["ai_system_map"]["unmapped_components"][0]
    mapping = client.post(
        "/api/mappings",
        json={
            "project_id": project_id,
            "mapping_type": "existing_slot_mapping",
            "decision": "confirmed",
            "source_unmapped_id": unmapped["id"],
            "source_file": unmapped["source_file"],
            "observed_kind": unmapped["observed_kind"],
            "evidence_ids": unmapped["evidence_ids"],
            "target_slot": "vector_store",
            "component_name": "Chroma",
            "component_kind": "vector_db",
        },
    ).json()
    return project_id, build_id, str(mapping["mapping_id"])


def apply(
    client: TestClient,
    build_id: str,
    mapping_id: str,
) -> Any:
    return client.post(
        f"/api/map-builds/{build_id}/apply",
        json={"mapping_ids": [mapping_id]},
    )


def test_apply_route_creates_build_and_read_routes(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, base_build_id, mapping_id = prepare_apply(client, tmp_path)

    response = apply(client, base_build_id, mapping_id)

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_id"].startswith("scan:")
    assert payload["build_id"] != base_build_id
    assert payload["based_on_build_id"] == base_build_id
    assert payload["build_reason"] == "apply_confirmations"
    assert payload["applied_mapping_ids"] == [mapping_id]
    assert payload["viewer_load_result"]["loaded"] is True
    assert payload["build_result"]["profile_signals_available"] is True
    profiles = payload["build_result"]["profile_inference_result"]
    assert profiles["schema_version"] == "profile-signals/v1"
    assert len(profiles["reference_capability_assessments"]) == 52
    assert len(profiles["profiles"]) == 15
    assert payload["build_result"]["readiness_report"]["schema_version"] == (
        "readiness-report/v1"
    )
    assert "output_run_dir" not in payload["build_result"]

    by_id = client.get(f"/api/map-builds/{payload['build_id']}")
    latest = client.get(f"/api/projects/{project_id}/map-builds/latest")
    history = client.get(f"/api/projects/{project_id}/map-builds")

    assert (
        by_id.status_code == latest.status_code == history.status_code == 200
    )
    assert by_id.json()["build_id"] == latest.json()["build_id"]
    assert [item["build_id"] for item in history.json()["builds"]] == [
        base_build_id,
        payload["build_id"],
    ]
    assert "output_dir" not in str(history.json())


def test_apply_preserves_parent_schema_selection(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    _, base_build_id, mapping_id = prepare_apply(
        client,
        tmp_path,
        schema_version="ai-system-map/v2",
    )

    response = apply(client, base_build_id, mapping_id)

    assert response.status_code == 200
    assert response.json()["build_result"]["requested_schema_version"] == (
        "ai-system-map/v2"
    )


def test_apply_route_is_idempotent_and_rejects_stale_base(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id, base_build_id, mapping_id = prepare_apply(client, tmp_path)
    first = apply(client, base_build_id, mapping_id)
    repeated = apply(client, base_build_id, mapping_id)

    assert first.status_code == repeated.status_code == 200
    assert first.json()["build_id"] == repeated.json()["build_id"]

    mapping_payload = client.get(
        f"/api/mappings?project_id={project_id}"
    ).json()["mappings"][0]
    mapping_payload.pop("mapping_id")
    mapping_payload.pop("mapping_digest")
    mapping_payload.pop("created_at")
    mapping_payload.pop("updated_at")
    mapping_payload["component_name"] = "Another Chroma"
    another = client.post("/api/mappings", json=mapping_payload).json()
    stale = apply(client, base_build_id, another["mapping_id"])

    assert stale.status_code == 409
    assert stale.json()["detail"] == "base_build_not_latest"


def test_apply_route_validates_request_and_unknown_ids(tmp_path: Path) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    _, base_build_id, mapping_id = prepare_apply(client, tmp_path)

    empty = client.post(
        f"/api/map-builds/{base_build_id}/apply",
        json={"mapping_ids": []},
    )
    duplicate = client.post(
        f"/api/map-builds/{base_build_id}/apply",
        json={"mapping_ids": [mapping_id, mapping_id]},
    )
    unknown_build = apply(client, "build:missing", mapping_id)
    unknown_mapping = apply(client, base_build_id, "mapping:missing")

    assert empty.status_code == duplicate.status_code == 422
    assert unknown_build.status_code == unknown_mapping.status_code == 404
    assert client.get("/api/map-builds/build:missing").status_code == 404


@pytest.mark.parametrize("sidecar_state", ["missing", "invalid"])
def test_build_read_degrades_when_profile_sidecar_is_unavailable(
    tmp_path: Path,
    sidecar_state: str,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    _, base_build_id, mapping_id = prepare_apply(client, tmp_path)
    applied = apply(client, base_build_id, mapping_id).json()
    build_id = str(applied["build_id"])
    profile_path = next(
        path
        for path in (tmp_path / "output").rglob("profile_signals.json")
        if json.loads(path.read_text(encoding="utf-8"))["build_id"] == build_id
    )
    if sidecar_state == "missing":
        profile_path.unlink()
    else:
        profile_path.write_text("{invalid", encoding="utf-8")

    response = client.get(f"/api/map-builds/{build_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["viewer_load_result"]["loaded"] is True
    assert payload["build_result"]["profile_signals_available"] is False
    assert payload["build_result"]["profile_inference_result"] is None
    assert (
        "profile_signals_missing_or_invalid"
        in payload["build_result"]["warnings"]
    )
