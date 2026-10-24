from pathlib import Path

import pytest
from conftest import Writer

from ip2region_ci.config import Phase, load_catalog, repository_root
from ip2region_ci.errors import CiError


def test_repository_components_are_valid() -> None:
    catalog = load_catalog(repository_root())

    assert "binding/golang" in catalog.components
    assert all(component.test for component in catalog.components.values())


def test_loads_components_in_path_order(repo: Path) -> None:
    catalog = load_catalog(repo)

    assert list(catalog.components) == ["binding/c", "binding/golang"]
    golang = catalog.component("binding/golang")
    assert golang.targets == (
        "linux-arm64",
        "linux-x64",
        "windows-arm64",
        "windows-x64",
    )
    assert [step.name for step in golang.steps(Phase.LINT)] == ["Vet"]


def test_reports_every_missing_config(repo: Path, write: Writer) -> None:
    write("binding/rust/src/lib.rs", "")
    write("maker/rust/Cargo.toml", "")

    with pytest.raises(CiError) as error:
        load_catalog(repo)

    assert str(error.value).splitlines() == [
        "binding/rust: missing ci.toml",
        "maker/rust: missing ci.toml",
    ]


def test_rejects_config_in_skipped_directory(repo: Path, write: Writer) -> None:
    write("maker/c/ci.toml", "")

    with pytest.raises(CiError, match=r"skipped component has a ci\.toml"):
        load_catalog(repo)


def test_rejects_unknown_keys(repo: Path, write: Writer) -> None:
    write("binding/golang/ci.toml", 'toolchain = { name = "go" }\nos = []\n')

    with pytest.raises(CiError, match=r"binding/golang/ci\.toml"):
        load_catalog(repo)


def test_rejects_step_platform_outside_component(
    repo: Path, write: Writer
) -> None:
    write(
        "binding/golang/ci.toml",
        """
        toolchain = { name = "go" }
        platforms = ["linux"]

        [[test]]
        name = "Unit tests"
        run = ["go", "test"]
        platforms = ["macos"]
        """,
    )

    with pytest.raises(CiError, match="unsupported platform"):
        load_catalog(repo)


def test_rejects_missing_dependency(repo: Path, write: Writer) -> None:
    config = repo / "binding/golang/ci.toml"
    write(
        "binding/golang/ci.toml",
        f'depends_on = ["binding/gone"]\n{config.read_text()}',
    )

    with pytest.raises(CiError, match="depends_on path does not exist"):
        load_catalog(repo)


def test_unknown_component(repo: Path) -> None:
    with pytest.raises(CiError, match="unknown component: binding/nope"):
        load_catalog(repo).component("binding/nope")
