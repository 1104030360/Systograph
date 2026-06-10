from __future__ import annotations

import inspect

from kai_mind.core.services import map_build_service
from kai_mind.web.routes import map_routes


def test_static_map_paths_do_not_depend_on_query_trace_runtime_callers() -> (
    None
):
    map_build_source = inspect.getsource(map_build_service)
    map_route_source = inspect.getsource(map_routes)

    assert "EndpointCallProvider" not in map_build_source
    assert "QueryTraceService" not in map_build_source
    assert "EndpointCallProvider" not in map_route_source
    assert "QueryTraceService" not in map_route_source
