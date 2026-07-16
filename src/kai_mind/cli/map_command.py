"""Thin CLI adapter for map builds."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from kai_mind.core.models.errors import (
    InventoryEnumerationError,
    ScanInventoryRulesError,
)
from kai_mind.core.models.map_build import MapBuildRequest
from kai_mind.core.services.map_build_service import MapBuildService


def register(app: typer.Typer) -> None:
    app.command("map")(map_command)


def map_command(
    project_path: Annotated[
        Path,
        typer.Argument(help="Project directory to scan."),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for map artifacts.",
        ),
    ] = Path("outputs"),
    redact_root_path: Annotated[
        bool,
        typer.Option(
            "--redact-root-path/--no-redact-root-path",
            help="Redact the project root path in the canonical map.",
        ),
    ] = True,
    no_snippets: Annotated[
        bool,
        typer.Option(
            "--no-snippets",
            help="Remove evidence snippets from the canonical map.",
        ),
    ] = False,
    system_map_schema_version: Annotated[
        Literal["ai-system-map/v1", "ai-system-map/v2"],
        typer.Option(
            "--system-map-schema-version",
            help=(
                "Requested map contract. Active artifact remains v1 until "
                "Plan 13 cutover; v2 is opt-in normalized view only."
            ),
        ),
    ] = "ai-system-map/v1",
) -> None:
    """Build a validated ai-system-map artifact (active output remains v1)."""

    try:
        result = MapBuildService().build(
            MapBuildRequest(
                project_path=project_path,
                output=output,
                redact_root_path=redact_root_path,
                no_snippets=no_snippets,
                system_map_schema_version=system_map_schema_version,
            )
        )
    except (InventoryEnumerationError, ScanInventoryRulesError) as exc:
        typer.echo(f"Map build failed: {exc.code.value}", err=True)
        raise typer.Exit(code=1) from exc
    if result.status == "error":
        if result.error is not None:
            typer.echo(
                f"Map build failed: {result.error.failure_reason.value}",
                err=True,
            )
        if result.map_error_path is not None:
            typer.echo(f"Error report: {result.map_error_path}", err=True)
        raise typer.Exit(code=1)

    if result.map_json_path is not None:
        typer.echo(str(result.map_json_path))
    if result.map_markdown_path is not None:
        typer.echo(str(result.map_markdown_path))
    if result.profile_signals_path is not None:
        typer.echo(str(result.profile_signals_path))
    typer.echo(f"active_schema_version={result.active_schema_version}")
    typer.echo(f"requested_schema_version={result.requested_schema_version}")
    for warning in result.migration_warnings:
        typer.echo(f"migration_warning={warning}")
