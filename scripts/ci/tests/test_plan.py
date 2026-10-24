import subprocess
from pathlib import Path

import pytest

from ip2region_ci import plan
from ip2region_ci.config import load_catalog


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        (None, ["binding/c", "binding/golang"]),
        ([], []),
        (["README.md"], []),
        (["binding/golang/main.go"], ["binding/golang"]),
        (["binding/golangx/main.go"], []),
        (["data/ipv4_source.txt"], ["binding/c", "binding/golang"]),
    ],
)
def test_affected(
    repo: Path, changed: list[str] | None, expected: list[str]
) -> None:
    assert plan.affected(load_catalog(repo), changed) == expected


def test_depends_on_triggers_component(repo: Path) -> None:
    config = repo / "binding/golang/ci.toml"
    config.write_text(f'depends_on = ["binding/c"]\n{config.read_text()}')

    affected = plan.affected(load_catalog(repo), ["binding/c/xdb.c"])

    assert affected == ["binding/c", "binding/golang"]


def test_jobs(repo: Path) -> None:
    catalog = load_catalog(repo)

    lint = plan.lint_jobs(catalog, ["binding/golang"])
    test = plan.test_jobs(catalog, ["binding/golang"])

    assert lint == [
        {
            "component": "binding/golang",
            "target": "linux-x64",
            "runner": "ubuntu-x64",
            "toolchain": "go",
            "toolchain-version": "",
        }
    ]
    assert [job["runner"] for job in test] == [
        "ubuntu-arm64",
        "ubuntu-x64",
        "windows-arm64",
        "windows-x64",
    ]


@pytest.mark.parametrize("since", ["", "0" * 40])
def test_no_base_commit_selects_everything(repo: Path, since: str) -> None:
    assert plan.changed_files(load_catalog(repo), since) is None


def test_changed_files_since_commit(repo: Path) -> None:
    def git(*args: str) -> str:
        return subprocess.run(
            ("git", *args), cwd=repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "--quiet")
    git("add", ".")
    git(
        "-c",
        "user.name=ci",
        "-c",
        "user.email=ci@example.com",
        "commit",
        "--quiet",
        "-m",
        "base",
    )
    base = git("rev-parse", "HEAD")
    (repo / "binding/c/xdb.c").write_text("")
    git("add", ".")
    git(
        "-c",
        "user.name=ci",
        "-c",
        "user.email=ci@example.com",
        "commit",
        "--quiet",
        "-m",
        "change",
    )

    assert plan.changed_files(load_catalog(repo), base) == ("binding/c/xdb.c",)
