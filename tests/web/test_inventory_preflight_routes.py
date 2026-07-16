from __future__ import annotations

from pathlib import Path
from typing import IO, Any, cast

import pytest
from fastapi.testclient import TestClient

from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.web.app import create_app


def _import_project(client: TestClient, root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(root)},
    )
    assert response.status_code == 200
    return str(response.json()["project_id"])


def _decision(proposal: dict[str, Any], action: str) -> dict[str, str]:
    context = proposal["selection_context"]
    return {
        "target_path": str(proposal["target"]["path"]),
        "fingerprint": str(proposal["target"]["fingerprint"]),
        "decision": action,
        "selection_scope": str(context["selection_scope"]),
    }


def test_preflight_projects_bounded_directory_summary_without_entries(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / "ignored").mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / "ignored" / "extra.py").write_text(
        "extra\n",
        encoding="utf-8",
    )
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id = _import_project(client, root)

    response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["ignored"]},
    )

    assert response.status_code == 200
    payload = cast(dict[str, Any], response.json())
    assert payload["preflight_request_id"].startswith("preflight:")
    assert payload["summary"]["default_included_file_count"] == 2
    result = payload["requested_target_results"][0]
    assert result["target_path"] == "ignored"
    assert result["status"] == "reviewable"
    assert (
        result["proposal"]["selection_context"]["directory_summary"][
            "selectable_file_count"
        ]
        == 1
    )
    assert "entries" not in str(result)
    assert "scan_id" not in payload
    assert (
        LocalJsonStateProvider(tmp_path / "state").get_latest_pointer(
            project_id
        )
        is None
    )


def test_preflight_http_supports_root_file_missing_blocked_and_pagination(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / ".gitignore").write_text(
        "ignored-*.py\n",
        encoding="utf-8",
    )
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / "ignored-a.py").write_text("a\n", encoding="utf-8")
    (root / "ignored-b.py").write_text("b\n", encoding="utf-8")
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id = _import_project(client, root)

    first_response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={
            "requested_paths": [".", "app.py", "missing.py", ".git"],
            "reviewable_excluded_limit": 1,
        },
    )

    assert first_response.status_code == 200
    first = cast(dict[str, Any], first_response.json())
    page = first["reviewable_excluded_page"]
    assert page["total"] == 2
    assert len(page["items"]) == 1
    assert page["next_cursor"] is not None
    by_path = {
        item["target_path"]: item for item in first["requested_target_results"]
    }
    assert (
        by_path["."]["proposal"]["selection_context"]["selection_scope"]
        == "recursive_directory"
    )
    assert (
        by_path["app.py"]["proposal"]["selection_context"]["selection_scope"]
        == "exact_file"
    )
    assert by_path["missing.py"]["status"] == "missing"
    assert by_path[".git"]["status"] == "hard_blocked"
    assert "entries" not in str(first["requested_target_results"])

    second_response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={
            "reviewable_excluded_cursor": page["next_cursor"],
            "reviewable_excluded_limit": 1,
        },
    )

    assert second_response.status_code == 200
    second = cast(dict[str, Any], second_response.json())
    assert (
        second["reviewable_excluded_page"]["items"][0]["target"]["path"]
        != page["items"][0]["target"]["path"]
    )


def test_preflight_selection_scan_uses_final_inventory_and_returns_summary(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    (root / "ignored").mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / ".env").write_text("MODE=fixture\n", encoding="utf-8")
    (root / "ignored" / "extra.py").write_text(
        "extra\n",
        encoding="utf-8",
    )
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id = _import_project(client, root)
    preflight = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["ignored"]},
    ).json()
    proposals = {
        item["target"]["path"]: item
        for item in [
            *preflight["required_boundary_proposals"],
            *[
                row["proposal"]
                for row in preflight["requested_target_results"]
                if row["proposal"] is not None
            ],
        ]
    }

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [
                _decision(proposals[".env"], "skip_this_run"),
                _decision(proposals["ignored"], "scan_this_run"),
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["scan_id"].startswith("scan:")
    assert payload["preflight_request_id"] == preflight["preflight_request_id"]
    summary = payload["inventory_selection_summary"]
    assert summary["included_file_count"] == 3
    assert summary["directory_scope_results"] == [
        {
            "target_path": "ignored",
            "decision": "scan_this_run",
            "observed_file_count": 1,
            "included_file_count": 1,
            "hard_blocked_file_count": 0,
            "post_decision_blocked_file_count": 0,
        }
    ]
    snapshot = LocalJsonStateProvider(tmp_path / "state").get_snapshot(
        project_id,
        payload["scan_id"],
    )
    assert snapshot is not None
    assert snapshot.candidate_set_digest is not None
    assert snapshot.filesystem_safety_version == "inventory-safety/v1"
    assert snapshot.boundary_decision_digest is not None
    assert snapshot.final_inventory_digest is not None
    assert snapshot.inventory_selection_summary is not None
    audit = {
        item.path: item for item in snapshot.scan_result.inventory_policy_audit
    }
    assert audit["ignored/extra.py"].decision_target_path == "ignored"
    assert audit["ignored/extra.py"].decision_scope == "recursive_directory"
    assert audit[".env"].effective_outcome == "skipped"


def test_preflight_errors_use_typed_detail_and_do_not_create_scan(
    tmp_path: Path,
) -> None:
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    missing = client.post(
        "/api/projects/project:missing/scan-preflights",
        json={},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "project_not_found"

    root = tmp_path / "project"
    root.mkdir()
    project_id = _import_project(client, root)
    invalid = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["../outside"]},
    )

    assert invalid.status_code == 422
    assert invalid.json()["detail"] == {
        "code": "inventory_selection_path_invalid",
        "message": "Choose a project-relative path without glob syntax.",
        "retryable": False,
        "context": None,
    }


def test_stale_preflight_scan_returns_409_without_snapshot(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    app_path = root / "app.py"
    app_path.write_text("app\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import_project(client, root)
    preflight = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["app.py"]},
    ).json()
    proposal = preflight["requested_target_results"][0]["proposal"]
    app_path.write_text("app changed size\n", encoding="utf-8")

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [_decision(proposal, "skip_this_run")],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "inventory_preflight_stale"
    repository = LocalJsonStateProvider(state_dir)
    assert repository.get_latest_pointer(project_id) is None
    assert repository.list_build_manifests(project_id) == ()


@pytest.mark.parametrize(
    ("target_path", "selection_scope", "expected_status", "expected_code"),
    [
        (
            "app.py",
            "recursive_directory",
            422,
            "inventory_selection_scope_invalid",
        ),
        (
            "missing.py",
            "exact_file",
            409,
            "inventory_selection_target_missing",
        ),
        (
            ".git",
            "exact_file",
            422,
            "inventory_selection_override_not_allowed",
        ),
    ],
)
def test_scan_selection_errors_are_typed_and_create_no_snapshot(
    tmp_path: Path,
    target_path: str,
    selection_scope: str,
    expected_status: int,
    expected_code: str,
) -> None:
    root = tmp_path / "project"
    (root / ".git").mkdir(parents=True)
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import_project(client, root)
    preflight = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": [target_path]},
    ).json()
    result = preflight["requested_target_results"][0]
    fingerprint = (
        result["proposal"]["target"]["fingerprint"]
        if result["proposal"] is not None
        else "sha256:forged"
    )

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [
                {
                    "target_path": target_path,
                    "fingerprint": fingerprint,
                    "decision": "scan_this_run",
                    "selection_scope": selection_scope,
                }
            ],
        },
    )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    repository = LocalJsonStateProvider(state_dir)
    assert repository.get_latest_pointer(project_id) is None
    assert repository.list_build_manifests(project_id) == ()


def test_legacy_pending_flow_does_not_open_sensitive_candidate_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    env_path = root / ".env"
    env_path.write_text("TOKEN=must-not-open\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id = _import_project(client, root)
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == env_path:
            raise AssertionError("legacy pending flow opened .env")
        return cast(IO[Any], original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", guarded_open)

    response = client.post(
        "/api/scans",
        json={"project_id": project_id},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "requires_boundary_decision"
