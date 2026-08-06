"""Regressions that keep retired HTTP endpoints retired.

Each test pins a route that was deliberately removed from the local API. A
route coming back must fail here first, before it can reach a release.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.routing import Route

from systograph.web.app import create_app

RETIRED_VIEWER_LOAD_PATH = "/api/viewer/load"


def test_post_api_viewer_load_returns_404_after_retirement() -> None:
    """Given the retired viewer-load adapter, when a client posts a
    map path, then the API answers 404 instead of reading the file."""

    client = TestClient(create_app())

    response = client.post(
        RETIRED_VIEWER_LOAD_PATH,
        json={"map_json_path": "outputs/run/ai_system_map.json"},
    )

    assert response.status_code == 404


def test_app_registers_no_route_for_retired_viewer_load_path() -> None:
    """Given the assembled app, when its routing table is inspected, then
    no method is bound to the retired viewer-load path."""

    app = create_app()

    registered_paths = {
        route.path for route in app.routes if isinstance(route, Route)
    }

    assert RETIRED_VIEWER_LOAD_PATH not in registered_paths
