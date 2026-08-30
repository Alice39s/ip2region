import os
import sys
from pathlib import Path

import pytest

from ip2region_ci.models import Component, Step
from ip2region_ci.runner import ComponentRunError, current_architecture, run_component


@pytest.mark.parametrize(
    ("machine", "expected"),
    [("AMD64", "x64"), ("x86_64", "x64"), ("aarch64", "arm64"), ("ARM64", "arm64")],
)
def test_current_architecture(machine: str, expected: str) -> None:
    assert current_architecture(machine) == expected


def test_runner_executes_structured_command(tmp_path: Path) -> None:
    component_directory = tmp_path / "binding" / "example"
    component_directory.mkdir(parents=True)
    output = component_directory / "result.txt"
    component = Component(
        id="binding-example",
        kind="binding",
        path="binding/example",
        platforms=frozenset({"linux"}),
        steps=(
            Step(
                name="write marker",
                command=(
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('result.txt').write_text('ok')",
                ),
            ),
        ),
    )

    run_component(component, tmp_path, platform="linux", environment=os.environ)

    assert output.read_text() == "ok"


def test_runner_rejects_platform_mismatch(tmp_path: Path) -> None:
    component = Component(
        id="binding-example",
        kind="binding",
        path="binding/example",
        platforms=frozenset({"windows"}),
        steps=(Step(name="noop", command=(sys.executable, "-c", "pass")),),
    )

    with pytest.raises(ComponentRunError, match="does not support linux"):
        run_component(component, tmp_path, platform="linux")
