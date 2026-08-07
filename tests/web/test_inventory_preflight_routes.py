from __future__ import annotations

from pathlib import Path
from typing import IO, Any, cast

import pytest
from fastapi.testclient import TestClient
from tests.helpers.web_flows import boundary_decision, open_scan_preflight

from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.web.app import create_app


def _import_project(client: TestClient, root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(root)},
    )
    assert response.status_code == 200
    return str(response.json()["project_id"])


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
    (root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
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
                boundary_decision(proposals[".env"], "skip_this_run"),
                boundary_decision(proposals["ignored"], "scan_this_run"),
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["scan_id"].startswith("scan:")
    assert payload["preflight_request_id"] == preflight["preflight_request_id"]
    # A skipped .env must leave no trace at all: neither the secret value nor
    # the key name it was stored under.
    assert "sk-live-secret-value" not in str(payload)
    assert "OPENAI_API_KEY" not in str(payload)
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


def test_scan_this_run_completed_response_masks_value_but_keeps_key_name(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".env").write_text(
        "OPENAI_API_KEY=sk-live-secret-value\n",
        encoding="utf-8",
    )
    (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    client = TestClient(create_app(state_dir=tmp_path / "state"))
    project_id = _import_project(client, root)
    preflight = open_scan_preflight(client, project_id)
    proposal = preflight["required_boundary_proposals"][0]
    assert proposal["target"]["path"] == ".env"

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [
                boundary_decision(proposal, "scan_this_run"),
            ],
        },
    )

    assert response.status_code == 200
    completed = response.json()
    assert completed["status"] == "completed"
    assert completed["boundary_proposals"] == []
    assert completed["inventory_selection_summary"]["included_file_count"] == 2
    # An explicitly scanned .env is reported, but only ever masked: the key
    # name survives so the finding is actionable, the value never does.
    assert "sk-live-secret-value" not in str(completed)
    assert "OPENAI_API_KEY" in str(completed)


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
            "boundary_decisions": [
                boundary_decision(proposal, "skip_this_run"),
            ],
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


def test_unanswered_required_decision_returns_pending_without_opening_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    env_path = root / ".env"
    env_path.write_text("TOKEN=must-not-open\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import_project(client, root)
    preflight = open_scan_preflight(client, project_id)
    assert [
        item["target"]["path"]
        for item in preflight["required_boundary_proposals"]
    ] == [".env"]
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> IO[Any]:
        if path == env_path:
            raise AssertionError("pending selection opened .env")
        return cast(IO[Any], original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", guarded_open)

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
            "preflight_request_id": preflight["preflight_request_id"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "requires_boundary_decision"
    assert payload["build_result"] is None
    assert "scan_id" not in payload
    assert payload["preflight_request_id"] == preflight["preflight_request_id"]
    assert [
        item["target"]["path"] for item in payload["boundary_proposals"]
    ] == [".env"]
    assert payload["available_boundary_actions"] == [
        "scan_this_run",
        "skip_this_run",
    ]
    assert "must-not-open" not in response.text
    repository = LocalJsonStateProvider(state_dir)
    assert repository.get_latest_pointer(project_id) is None
    assert repository.list_build_manifests(project_id) == ()
