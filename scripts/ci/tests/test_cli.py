from typer.testing import CliRunner

from ip2region_ci.cli import app

runner = CliRunner()


def test_validate() -> None:
    result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0, result.output
    assert "components are valid" in result.stdout


def test_plan_only() -> None:
    result = runner.invoke(app, ["plan", "--only", "binding/golang"])

    assert result.exit_code == 0, result.output
    lint, test = result.stdout.splitlines()
    assert lint.startswith("lint=[")
    assert test.startswith("test=[")
    assert '"component": "binding/golang"' in test
