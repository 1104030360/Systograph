"""CLI entry point for Systograph."""

import typer

from systograph.cli.map_command import register as register_map_command
from systograph.cli.migrate_legacy_mappings_command import (
    register as register_migrate_legacy_mappings_command,
)
from systograph.cli.trace_command import register as register_trace_command
from systograph.cli.viewer_command import register as register_viewer_command

app = typer.Typer(
    help="Systograph AI system release-readiness tools.",
    no_args_is_help=True,
)
register_map_command(app)
register_migrate_legacy_mappings_command(app)
register_trace_command(app)
register_viewer_command(app)


@app.callback()
def root() -> None:
    """Systograph AI system release-readiness tools."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
