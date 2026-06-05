"""Thin CLI adapter for map builds."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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
) -> None:
    """Build a validated ai-system-map/v1 artifact."""

    result = MapBuildService().build(
        MapBuildRequest(
            project_path=project_path,
            output=output,
            redact_root_path=redact_root_path,
            no_snippets=no_snippets,
        )
    )
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
