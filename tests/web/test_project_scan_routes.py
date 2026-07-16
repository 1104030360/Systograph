from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from tests.helpers.fixtures import rag_project_fixture_path

from kai_mind.core.models.errors import (
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)
from kai_mind.core.models.inventory_policy import ScanInventoryPolicyCatalog
from kai_mind.core.providers.filesystem_provider import FilesystemProvider
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.project_scan_service import ProjectScanService
from kai_mind.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
)
from kai_mind.core.services.scan_snapshot_service import ScanSnapshotService
from kai_mind.web.app import create_app


class MissingInventoryRuleLoader(ScanInventoryRuleLoader):
    def load_default(self) -> ScanInventoryPolicyCatalog:
        raise ScanInventoryRulesError(ScanInventoryRulesErrorCode.UNAVAILABLE)


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

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "scan_depth": "system",
            "output": str(tmp_path / "outputs"),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_id"].startswith("scan:")
    assert payload["project_id"] == project_id
    assert payload["status"] == "completed"
    assert payload["build_result"]["status"] == "ok"


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


def test_scan_create_fails_closed_when_inventory_catalog_is_missing(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"
    scanner = ProjectScanService(
        filesystem_provider=FilesystemProvider(
            inventory_rule_loader=MissingInventoryRuleLoader()
        )
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
    imported = client.post(
        "/api/projects/import",
        json={
            "source_type": "local_path",
            "project_path": str(project_root),
        },
    )

    response = client.post(
        "/api/scans",
        json={
            "project_id": imported.json()["project_id"],
            "scan_depth": "system",
            "output": str(tmp_path / "outputs"),
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
