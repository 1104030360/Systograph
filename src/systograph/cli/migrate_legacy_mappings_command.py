from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from systograph.core.services.legacy_manual_mapping_migration_service import (
    LegacyManualMappingMigrationService,
)


def register(app: typer.Typer) -> None:
    app.command("migrate-legacy-mappings")(migrate_legacy_mappings_command)


def migrate_legacy_mappings_command(
    state_dir: Annotated[
        Path,
        typer.Option(
            "--state-dir",
            help="Systograph state directory containing persisted mappings.",
        ),
    ],
    apply: Annotated[
        bool,
        typer.Option(
            "--apply",
            help="Apply migration; omit for a zero-write dry run.",
        ),
    ] = False,
) -> None:
    report = LegacyManualMappingMigrationService(state_dir).migrate(
        apply=apply
    )
    typer.echo(report.model_dump_json(indent=2))
    if apply and report.cutover_blocked:
        raise typer.Exit(code=1)
