from pathlib import Path

import pytest
from ruamel.yaml import YAML

from ip2region_ci.manifest import load_manifest, repository_root

WORKFLOW_DIRECTORY = repository_root() / ".github" / "workflows"


def load_workflow(name: str) -> dict[str, object]:
    yaml = YAML(typ="safe")
    workflow = yaml.load(WORKFLOW_DIRECTORY / name)
    assert isinstance(workflow, dict)
    return workflow


@pytest.mark.parametrize("workflow_path", sorted(WORKFLOW_DIRECTORY.glob("*.yml")))
def test_workflow_has_security_and_manual_dispatch(workflow_path: Path) -> None:
    yaml = YAML(typ="safe")
    workflow = yaml.load(workflow_path)

    assert workflow["permissions"] == {"contents": "read"}
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["concurrency"]["cancel-in-progress"] is True
    assert all("timeout-minutes" in job for job in workflow["jobs"].values())


def test_cpp_workflow_covers_every_native_platform_pair() -> None:
    workflow = load_workflow("cpp.yml")
    matrix = workflow["jobs"]["build-and-test"]["strategy"]["matrix"]["include"]
    actual = {(item["system"], item["architecture"]) for item in matrix}

    assert actual == {
        ("Linux", "x64"),
        ("Linux", "arm64"),
        ("macOS", "x64"),
        ("macOS", "arm64"),
        ("Windows", "x64"),
        ("Windows", "arm64"),
    }


def test_cpp_workflow_uses_manifest_adapter() -> None:
    workflow_text = (WORKFLOW_DIRECTORY / "cpp.yml").read_text()

    assert "ip2region-ci architecture" in workflow_text
    assert "ip2region-ci run binding-cpp" in workflow_text


def test_bindings_workflow_covers_every_non_cpp_binding() -> None:
    workflow = load_workflow("bindings.yml")
    matrix = workflow["jobs"]["build-and-test"]["strategy"]["matrix"]["include"]
    actual = {item["component"] for item in matrix}
    expected = {
        component.id
        for component in load_manifest().components
        if component.kind == "binding" and component.id != "binding-cpp"
    }

    assert actual == expected


def test_makers_workflow_covers_every_runnable_maker() -> None:
    workflow = load_workflow("makers.yml")
    matrix = workflow["jobs"]["build-and-test"]["strategy"]["matrix"]["include"]
    actual = {item["component"] for item in matrix}
    expected = {
        component.id for component in load_manifest().components if component.kind == "maker"
    }

    assert actual == expected


@pytest.mark.parametrize("workflow_name", ["bindings.yml", "makers.yml"])
def test_language_workflows_use_manifest_adapters(workflow_name: str) -> None:
    workflow_text = (WORKFLOW_DIRECTORY / workflow_name).read_text()

    assert "ip2region-ci run" in workflow_text


@pytest.mark.parametrize("workflow_path", sorted(WORKFLOW_DIRECTORY.glob("*.yml")))
def test_setup_uv_uses_resolvable_release_tag(workflow_path: Path) -> None:
    workflow_text = workflow_path.read_text()

    assert "astral-sh/setup-uv@v10.0.1" in workflow_text
