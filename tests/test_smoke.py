import importlib
import sys

from typer.testing import CliRunner


def test_package_can_be_imported() -> None:
    package = importlib.import_module("kai_mind")

    assert package.__version__


def test_cli_help_is_available() -> None:
    cli_main = importlib.import_module("kai_mind.cli.main")
    runner = CliRunner()

    result = runner.invoke(cli_main.app, ["--help"])

    assert result.exit_code == 0
    assert "KAI-Mind" in result.stdout


def test_core_import_does_not_load_fastapi_adapter() -> None:
    sys.modules.pop("fastapi", None)

    importlib.import_module("kai_mind.core")

    assert "fastapi" not in sys.modules
