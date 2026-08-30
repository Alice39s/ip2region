from typer.testing import CliRunner

from ip2region_ci.cli import app

runner = CliRunner()


def test_validate_command() -> None:
    result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "validated" in result.stdout


def test_list_command_includes_cpp() -> None:
    result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "binding-cpp\tbinding" in result.stdout
