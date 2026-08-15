"""Thin CLI adapter for map builds."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from systograph.cli.map_workflow import CliMapWorkflow
from systograph.core.models.errors import (
    InventoryEnumerationError,
    InventorySelectionError,
    InventorySelectionErrorCode,
    ScanInventoryRulesError,
)
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.services.canonical_output_configuration import (
    CanonicalOutputConfigurationError,
)
from systograph.core.services.noninteractive_inventory_gate import (
    NonInteractiveInventoryGate,
)
from systograph.core.services.state_directory_service import default_state_dir
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError


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
            help=("Canonical map contract. v1 is not publicly selectable."),
        ),
    ] = "ai-system-map/v2",
    state_dir: Annotated[
        Path | None,
        typer.Option(
            "--state-dir",
            help="Durable state directory for scan snapshots.",
        ),
    ] = None,
    approve_boundary_review: Annotated[
        bool,
        typer.Option(
            "--approve-boundary-review",
            help=(
                "Take the reviewable boundary decisions here instead of "
                "in the Web flow: every reviewable path is scanned for "
                "this run and recorded as a runtime user decision. "
                "Blocked paths stay blocked."
            ),
        ),
    ] = False,
) -> None:
    """Build v2 through the default non-interactive inventory gate.

    Boundary decisions that need review are blocked and must be resolved in
    the Web review flow, or approved for one run with
    --approve-boundary-review.
    """

    try:
        workflow_result = CliMapWorkflow(
            state_dir=state_dir or default_state_dir(),
            inventory_gate=NonInteractiveInventoryGate(
                approve_boundary_review=approve_boundary_review
            ),
        ).build(
            MapBuildRequest(
                project_path=project_path,
                output=output,
                redact_root_path=redact_root_path,
                no_snippets=no_snippets,
                system_map_schema_version=system_map_schema_version,
            )
        )
        result = workflow_result.build
    except (
        CanonicalOutputConfigurationError,
        InventoryEnumerationError,
        InventorySelectionError,
        ScanInventoryRulesError,
        UaAnalysisError,
    ) as exc:
        code = exc.code if isinstance(exc.code, str) else exc.code.value
        typer.echo(f"Map build failed: {code}", err=True)
        if (
            isinstance(exc, InventorySelectionError)
            and exc.code
            == InventorySelectionErrorCode.NON_INTERACTIVE_REVIEW_REQUIRED
        ):
            typer.echo(
                "Resolve the boundary decision in the Web review flow.",
                err=True,
            )
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
    if workflow_result.snapshot is not None:
        typer.echo(f"scan_id={workflow_result.snapshot.scan_id}")
