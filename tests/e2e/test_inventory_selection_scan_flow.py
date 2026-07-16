from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.web.app import create_app


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _import(client: TestClient, root: Path) -> str:
    response = client.post(
        "/api/projects/import",
        json={"source_type": "local_path", "project_path": str(root)},
    )
    assert response.status_code == 200
    return str(response.json()["project_id"])


def _decision(proposal: dict[str, Any], action: str) -> dict[str, str]:
    return {
        "target_path": str(proposal["target"]["path"]),
        "fingerprint": str(proposal["target"]["fingerprint"]),
        "decision": action,
        "selection_scope": str(
            proposal["selection_context"]["selection_scope"]
        ),
    }


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_inventory_selection_scan_is_read_only_and_auditable(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    ignored = root / "ignored"
    ignored.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (root / ".gitignore").write_text(
        "ignored/\nmissing-*.py\n",
        encoding="utf-8",
    )
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (ignored / ".env").write_text("MODE=fixture\n", encoding="utf-8")
    (ignored / "safe.py").write_text("safe\n", encoding="utf-8")
    (ignored / "skip.py").write_text("skip\n", encoding="utf-8")
    (ignored / "blob.dat").write_bytes(b"prefix\x00binary")
    try:
        (ignored / "outside-link").symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    _git(root, "init")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "Fixture")
    _git(root, "add", ".gitignore", "app.py")
    _git(root, "commit", "-m", "fixture")
    before_status = _git(
        root, "status", "--porcelain=v1", "--untracked-files=all"
    )
    before_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    )
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import(client, root)

    preflight_response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["ignored", "ignored/skip.py"]},
    )
    assert preflight_response.status_code == 200
    assert str(root) not in preflight_response.text
    assert "MODE=fixture" not in preflight_response.text
    preflight = preflight_response.json()
    requested = {
        item["target_path"]: item["proposal"]
        for item in preflight["requested_target_results"]
    }
    scan_response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "outputs"),
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [
                _decision(requested["ignored"], "scan_this_run"),
                _decision(requested["ignored/skip.py"], "skip_this_run"),
            ],
        },
    )

    assert scan_response.status_code == 200
    scan = scan_response.json()
    assert scan["status"] == "completed"
    scope = scan["inventory_selection_summary"]["directory_scope_results"][0]
    assert scope["included_file_count"] == 2
    assert scope["post_decision_blocked_file_count"] == 1
    assert scope["hard_blocked_file_count"] == 1
    snapshot = LocalJsonStateProvider(state_dir).get_snapshot(
        project_id,
        scan["scan_id"],
    )
    assert snapshot is not None
    audit = {
        item.path: item for item in snapshot.scan_result.inventory_policy_audit
    }
    assert audit["ignored/.env"].effective_outcome == "included"
    assert audit["ignored/skip.py"].effective_outcome == "skipped"
    assert audit["ignored/blob.dat"].effective_outcome == "hard_blocked"
    assert audit["ignored/outside-link"].effective_outcome == "hard_blocked"
    audit_json = json.dumps(
        [item.model_dump(mode="json") for item in audit.values()],
        sort_keys=True,
    )
    assert str(root) not in audit_json
    assert "MODE=fixture" not in audit_json
    assert "masked_snippets" not in audit_json
    assert (
        _git(
            root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        )
        == before_status
    )
    after_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    )
    assert after_files == before_files


@pytest.mark.parametrize("mutation", ["add", "delete"])
def test_changed_directory_after_preflight_has_no_snapshot_or_build(
    tmp_path: Path,
    mutation: str,
) -> None:
    root = tmp_path / "project"
    ignored = root / "ignored"
    ignored.mkdir(parents=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (ignored / "one.py").write_text("one\n", encoding="utf-8")
    if mutation == "delete":
        (ignored / "two.py").write_text("two\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import(client, root)
    preflight = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["ignored"]},
    ).json()
    proposal = preflight["requested_target_results"][0]["proposal"]
    if mutation == "add":
        (ignored / "two.py").write_text("two\n", encoding="utf-8")
    else:
        (ignored / "two.py").unlink()

    response = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [_decision(proposal, "scan_this_run")],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == (
        "inventory_selection_target_changed"
    )
    repository = LocalJsonStateProvider(state_dir)
    assert repository.get_latest_pointer(project_id) is None
    assert repository.list_build_manifests(project_id) == ()


def test_rescan_recomputes_inventory_without_reusing_prior_decision(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (root / "app.py").write_text("app\n", encoding="utf-8")
    (root / "ignored.py").write_text("ignored\n", encoding="utf-8")
    state_dir = tmp_path / "state"
    client = TestClient(create_app(state_dir=state_dir))
    project_id = _import(client, root)
    preflight = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": ["ignored.py"]},
    ).json()
    proposal = preflight["requested_target_results"][0]["proposal"]

    selected = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "selected-output"),
            "preflight_request_id": preflight["preflight_request_id"],
            "boundary_decisions": [
                _decision(proposal, "scan_this_run"),
            ],
        },
    ).json()
    rescanned = client.post(
        "/api/scans",
        json={
            "project_id": project_id,
            "output": str(tmp_path / "rescan-output"),
        },
    ).json()

    assert selected["scan_id"] != rescanned["scan_id"]
    repository = LocalJsonStateProvider(state_dir)
    selected_snapshot = repository.get_snapshot(
        project_id,
        selected["scan_id"],
    )
    rescan_snapshot = repository.get_snapshot(
        project_id,
        rescanned["scan_id"],
    )
    assert selected_snapshot is not None
    assert rescan_snapshot is not None
    selected_audit = {
        item.path: item
        for item in selected_snapshot.scan_result.inventory_policy_audit
    }
    rescan_audit = {
        item.path: item
        for item in rescan_snapshot.scan_result.inventory_policy_audit
    }
    assert selected_audit["ignored.py"].effective_outcome == "included"
    assert selected_audit["ignored.py"].decision_origin == (
        "runtime_user_decision"
    )
    assert rescan_audit["ignored.py"].effective_outcome == "skipped"
    assert rescan_audit["ignored.py"].decision_origin == "default_policy"
