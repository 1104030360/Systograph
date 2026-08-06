"""Regressions that keep retired HTTP endpoints retired.

Each test pins a route that was deliberately removed from the local API. A
route coming back must fail here first, before it can reach a release.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from starlette.routing import Route

from systograph.web.app import create_app

RETIRED_VIEWER_LOAD_PATH = "/api/viewer/load"
RETIRED_MAP_BUILD_PATH = "/api/map/build"
LIVE_CONTROL_PATH = "/api/scans"


def assert_path_is_unregistered(retired_path: str) -> None:
    """Assert the app binds no method to `retired_path`.

    `LIVE_CONTROL_PATH` is a positive control: an app that assembled without
    any routes would otherwise satisfy the retirement assertion vacuously.
    """

    app = create_app()

    registered_paths = {
        route.path for route in app.routes if isinstance(route, Route)
    }

    assert LIVE_CONTROL_PATH in registered_paths
    assert retired_path not in registered_paths


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

    assert_path_is_unregistered(RETIRED_VIEWER_LOAD_PATH)


def test_post_api_map_build_returns_404_after_retirement() -> None:
    """Given the retired all-in-one demo build endpoint, when a client
    posts a project path, then the API answers 404 instead of scanning."""

    client = TestClient(create_app())

    response = client.post(
        RETIRED_MAP_BUILD_PATH,
        json={"project_path": "/abs/path/to/project", "output": "outputs"},
    )

    assert response.status_code == 404


def test_app_registers_no_route_for_retired_map_build_path() -> None:
    """Given the assembled app, when its routing table is inspected, then
    no method is bound to the retired map-build path."""

    assert_path_is_unregistered(RETIRED_MAP_BUILD_PATH)
