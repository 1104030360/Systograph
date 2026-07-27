"""Thin CLI adapter for opt-in query traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from kai_mind.core.services.canonical_map_loader import (
    CanonicalMapLoader,
    CanonicalMapLoadError,
)
from kai_mind.core.services.query_trace_config_loader import (
    QueryTraceConfig,
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)
from kai_mind.core.services.query_trace_service import QueryTraceService


def register(app: typer.Typer) -> None:
    app.command("trace")(trace_command)


def trace_command(
    map_json_path: Annotated[
        Path,
        typer.Argument(help="Validated ai_system_map.json to trace against."),
    ],
    endpoint_id: Annotated[
        str,
        typer.Option(
            "--endpoint-id",
            help="Endpoint id from ai_system_map.endpoints[].",
        ),
    ],
    query: Annotated[
        str,
        typer.Option(
            "--query",
            help=(
                "Query to send. The raw value is not written to trace output."
            ),
        ),
    ],
    timeout_seconds: Annotated[
        float,
        typer.Option(
            "--timeout-seconds",
            help="Bounded endpoint timeout in seconds.",
        ),
    ] = 30.0,
    project_root: Annotated[
        Path | None,
        typer.Option(
            "--project-root",
            help=(
                "Optional scanned project root for "
                "[tool.systograph.trace] config "
                "(legacy: [tool.kai-mind.trace])."
            ),
        ),
    ] = None,
) -> None:
    """Run one explicit query trace against a map endpoint."""

    try:
        data = json.loads(map_json_path.read_text(encoding="utf-8"))
        system_map = CanonicalMapLoader().load(data).normalized
        trace_config = _load_trace_config(project_root)
    except (
        OSError,
        json.JSONDecodeError,
        QueryTraceConfigError,
        CanonicalMapLoadError,
    ) as exc:
        typer.echo(f"Trace failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    result = QueryTraceService().trace(
        system_map=system_map,
        endpoint_id=endpoint_id,
        query=query,
        timeout_seconds=timeout_seconds,
        retrieved_chunks_keys=trace_config.retrieved_chunks_keys,
    )
    typer.echo(result.model_dump_json(indent=2))


def _load_trace_config(project_root: Path | None) -> QueryTraceConfig:
    if project_root is None:
        return QueryTraceConfig()
    try:
        return QueryTraceConfigLoader().load_project_config(project_root)
    except QueryTraceConfigError as exc:
        raise QueryTraceConfigError(f"invalid_trace_config: {exc}") from exc
