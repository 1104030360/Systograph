"""CLI entry point for KAI-Mind."""

import typer

from kai_mind.cli.map_command import register as register_map_command
from kai_mind.cli.trace_command import register as register_trace_command
from kai_mind.cli.viewer_command import register as register_viewer_command

app = typer.Typer(
    help="KAI-Mind local AI health doctor backend tools.",
    no_args_is_help=True,
)
register_map_command(app)
register_trace_command(app)
register_viewer_command(app)


@app.callback()
def root() -> None:
    """KAI-Mind local AI health doctor backend tools."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
