from __future__ import annotations

import inspect

from systograph.core.services import map_build_service
from systograph.web.routes import map_build_routes


def test_static_map_paths_do_not_depend_on_query_trace_runtime_callers() -> (
    None
):
    map_build_service_source = inspect.getsource(map_build_service)
    map_build_route_source = inspect.getsource(map_build_routes)

    assert "EndpointCallProvider" not in map_build_service_source
    assert "QueryTraceService" not in map_build_service_source
    assert "EndpointCallProvider" not in map_build_route_source
    assert "QueryTraceService" not in map_build_route_source
