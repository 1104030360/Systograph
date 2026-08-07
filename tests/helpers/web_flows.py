"""Explicit two-step scan helpers for web/e2e tests.

`POST /api/scans` always requires a `preflight_request_id`, so every test that
starts a scan has to open a preflight first. These helpers keep that two-step
flow in one place; they stay deliberately thin and return the raw response so
callers can still assert on the full payload.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast

import httpx
from fastapi.testclient import TestClient


def open_scan_preflight(
    client: TestClient,
    project_id: str,
    *,
    requested_paths: Iterable[str] = (),
) -> dict[str, Any]:
    """Open a metadata-only preflight and return its payload."""
    response = client.post(
        f"/api/projects/{project_id}/scan-preflights",
        json={"requested_paths": list(requested_paths)},
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def boundary_decision(
    proposal: Mapping[str, Any],
    decision: str,
    *,
    reason: str | None = None,
) -> dict[str, str]:
    """Build one delta decision from a preflight proposal."""
    context = proposal["selection_context"]
    item = {
        "target_path": str(proposal["target"]["path"]),
        "fingerprint": str(proposal["target"]["fingerprint"]),
        "decision": decision,
        "selection_scope": str(context["selection_scope"]),
    }
    if reason is not None:
        item["reason"] = reason
    return item


def create_scan_with_preflight(
    client: TestClient,
    project_id: str,
    *,
    boundary_decisions: Iterable[Mapping[str, str]] = (),
    requested_paths: Iterable[str] = (),
    **scan_fields: Any,
) -> httpx.Response:
    """Open a fresh preflight, then scan with that `preflight_request_id`.

    A rescan must never reuse a previous preflight, so this always opens a new
    one. Extra `scan_fields` are merged into the `POST /api/scans` body.
    """
    preflight = open_scan_preflight(
        client,
        project_id,
        requested_paths=requested_paths,
    )
    body: dict[str, Any] = {
        "project_id": project_id,
        "preflight_request_id": preflight["preflight_request_id"],
        "boundary_decisions": [dict(item) for item in boundary_decisions],
        **scan_fields,
    }
    return client.post("/api/scans", json=body)


def scan_project(
    client: TestClient,
    project_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run an explicit-preflight scan and return its successful payload."""
    response = create_scan_with_preflight(client, project_id, **kwargs)
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())
