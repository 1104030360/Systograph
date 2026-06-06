"""Thin CLI adapter for viewer map validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from kai_mind.core.services.viewer_session_service import ViewerSessionService


def register(app: typer.Typer) -> None:
    app.command("validate-map")(validate_map_command)


def validate_map_command(
    map_json_path: Annotated[
        Path,
        typer.Argument(help="Path to an ai_system_map.json file."),
    ],
) -> None:
    """Validate and project one ai-system-map/v1 artifact."""

    result = ViewerSessionService().load_map(map_json_path)
    graph = result.graph_view_model

    if result.loaded:
        typer.echo(
            f"loaded=true nodes={len(graph.nodes)} edges={len(graph.edges)}"
        )
        return

    typer.echo(f"loaded=false error_reason={result.error_reason}", err=True)
    raise typer.Exit(code=1)
