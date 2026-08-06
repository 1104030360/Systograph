from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from tests.helpers.fixtures import rag_project_fixture_path
from tests.helpers.web_flows import (
    create_scan_with_preflight,
    open_scan_preflight,
    scan_project,
)

from systograph.core.models.errors import (
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)
from systograph.core.models.inventory_policy import ScanInventoryPolicyCatalog
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.web.app import create_app


class MissingInventoryRuleLoader(ScanInventoryRuleLoader):
    def load_default(self) -> ScanInventoryPolicyCatalog:
        raise ScanInventoryRulesError(ScanInventoryRulesErrorCode.UNAVAILABLE)


class RevocableInventoryRuleLoader(ScanInventoryRuleLoader):
    """Real catalog until `available` is cleared, then fails like a removal."""

    def __init__(self) -> None:
        self.available = True

    def load_default(self) -> ScanInventoryPolicyCatalog:
        if not self.available:
            raise ScanInventoryRulesError(
                ScanInventoryRulesErrorCode.UNAVAILABLE
            )
        return super().load_default()


def test_project_import_accepts_only_local_path_source() -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")

    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"].startswith("project:")
    assert payload["source_type"] == "local_path"
    assert payload["project_name"] == "basic_qdrant_ollama_rag"


def test_project_import_rejects_upload_source_type() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/projects/import",
        json={
            "source_type": "upload",
            "project_path": "/tmp/example.zip",
        },
    )

    assert response.status_code == 422


def test_scan_create_builds_imported_project(tmp_path: Path) -> None:
    client = TestClient(create_app())
    project_root = rag_project_fixture_path("basic_qdrant_ollama_rag")
    import_response = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    project_id = import_response.json()["project_id"]

    response = create_scan_with_preflight(
        client,
        project_id,
        scan_depth="system",
        output=str(tmp_path / "outputs"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_id"].startswith("scan:")
    assert payload["project_id"] == project_id
    assert payload["status"] == "completed"
    assert payload["build_result"]["status"] == "ok"


def _state_dir_entries(state_dir: Path) -> set[str]:
    return {
        path.relative_to(state_dir).as_posix() for path in state_dir.rglob("*")
    }


def test_create_scan_without_preflight_request_id_returns_422_stable_code(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "outputs"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(
                rag_project_fixture_path("basic_qdrant_ollama_rag")
            ),
        },
    ).json()["project_id"]
    before = _state_dir_entries(state_dir)

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "scan_depth": "system",
            "output": str(output_dir),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "preflight_request_id_required",
        "message": "Open a scan preflight and send its preflight_request_id.",
        "retryable": False,
        "context": None,
    }
    assert _state_dir_entries(state_dir) == before
    assert not output_dir.exists()


def test_create_scan_without_preflight_request_id_is_rejected_for_sensitive_project(  # noqa: E501
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (project_root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "preflight_request_id_required"
    assert "boundary_proposals" not in response.json()


def test_scan_create_rejects_public_v1_selection_before_scanning(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    output_dir = tmp_path / "outputs"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(
                rag_project_fixture_path("basic_qdrant_ollama_rag")
            ),
        },
    ).json()["project_id"]
    before = _state_dir_entries(state_dir)

    response = create_scan_with_preflight(
        client,
        project_id,
        scan_depth="system",
        output=str(output_dir),
        system_map_schema_version="ai-system-map/v1",
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "legacy_output_not_selectable"
    assert _state_dir_entries(state_dir) == before
    assert not any(state_dir.rglob("snapshot.json"))
    assert not output_dir.exists()


def test_scan_create_with_explicit_v2_selection_persists_snapshot(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(
                rag_project_fixture_path("basic_qdrant_ollama_rag")
            ),
        },
    ).json()["project_id"]
    before = _state_dir_entries(state_dir)

    response = create_scan_with_preflight(
        client,
        project_id,
        scan_depth="system",
        output=str(tmp_path / "outputs"),
        system_map_schema_version="ai-system-map/v2",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert _state_dir_entries(state_dir) != before
    assert any(state_dir.rglob("snapshot.json"))


def test_committed_scan_survives_session_projection_failure(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    app = create_app(state_dir=tmp_path / "state")
    client = TestClient(app)
    project_id = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(project_root)},
    ).json()["project_id"]

    def fail_save(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("injected session projection failure")

    monkeypatch.setattr(
        app.state.session_store,
        "save_build_result",
        fail_save,
    )

    completed = scan_project(
        client,
        project_id,
        output=str(tmp_path / "outputs"),
    )
    build_id = completed["build_result"]["lineage"]["build_id"]

    assert completed["status"] == "completed"
    assert (
        "session_projection_save_failed"
        in completed["build_result"]["warnings"]
    )
    assert client.get(f"/api/map-builds/{build_id}").status_code == 200


def test_scan_create_rejects_unknown_project() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/scans",
        json={
            "project_id": "project:missing",
            "scan_depth": "system",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "project_not_found",
        "message": "Project not found.",
        "retryable": False,
        "context": None,
    }


def test_scan_create_fails_closed_when_catalog_is_lost_after_preflight(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    loader = RevocableInventoryRuleLoader()
    scanner = ProjectScanService(
        filesystem_provider=FilesystemProvider(inventory_rule_loader=loader)
    )
    snapshot_service = ScanSnapshotService(
        project_scan_service=scanner,
        repository=LocalJsonStateProvider(state_dir),
    )
    client = TestClient(
        create_app(
            state_dir=state_dir,
            scan_snapshot_service=snapshot_service,
        )
    )
    project_id = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    ).json()["project_id"]
    preflight = open_scan_preflight(client, project_id)
    loader.available = False

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "scan_depth": "system",
            "output": str(tmp_path / "outputs"),
            "preflight_request_id": preflight["preflight_request_id"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "inventory_rules_unavailable",
        "message": "Inventory policy could not be loaded safely.",
        "retryable": False,
        "context": None,
    }
    assert not list(state_dir.rglob("snapshot.json"))
    assert not (tmp_path / "outputs").exists()


def test_preflight_cannot_bypass_missing_catalog_with_exact_target(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("app\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    scanner = ProjectScanService(
        filesystem_provider=FilesystemProvider(
            inventory_rule_loader=MissingInventoryRuleLoader()
        )
    )
    client = TestClient(
        create_app(
            state_dir=state_dir,
            scan_snapshot_service=ScanSnapshotService(
                project_scan_service=scanner,
                repository=LocalJsonStateProvider(state_dir),
            ),
        )
    )
    imported = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )
    project_id = imported.json()["project_id"]

    response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["app.py"]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "inventory_rules_unavailable",
        "message": "Inventory policy could not be loaded safely.",
        "retryable": False,
        "context": None,
    }
    assert not list(state_dir.rglob("snapshot.json"))
