"""CLI entry point for KAI-Mind."""

import typer

app = typer.Typer(
    help="KAI-Mind local AI health doctor backend tools.",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """KAI-Mind local AI health doctor backend tools."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
