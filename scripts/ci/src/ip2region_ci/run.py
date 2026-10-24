import os
import platform as host
import shlex
import shutil
import subprocess
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from ip2region_ci.config import Architecture, Component, Phase, Platform, Step
from ip2region_ci.errors import CiError


def current_platform() -> Platform:
    match sys.platform:
        case "darwin":
            return "macos"
        case "win32":
            return "windows"
        case name if name.startswith("linux"):
            return "linux"
        case name:
            raise CiError(f"unsupported platform: {name}")


def current_architecture() -> Architecture:
    match host.machine().lower():
        case "amd64" | "x86_64":
            return "x64"
        case "arm64" | "aarch64":
            return "arm64"
        case name:
            raise CiError(f"unsupported architecture: {name}")


def current_target() -> str:
    return f"{current_platform()}-{current_architecture()}"


def run_component(
    component: Component,
    directory: Path,
    phases: Iterable[Phase],
    target: str | None = None,
) -> None:
    """Runs the steps of `phases` that apply to the target, in order."""
    target = target or current_target()
    if target not in component.targets:
        raise CiError(f"{directory}: not supported on {target}")
    platform = cast(Platform, target.partition("-")[0])
    for phase in phases:
        for step in component.steps(phase):
            if step.applies_to(platform):
                run_step(step, directory)


def run_step(step: Step, directory: Path) -> None:
    """Runs one step; `fail_on_output` steps also fail on any stdout."""
    directory /= step.working_directory or ""
    command = (_executable(step.run[0], directory), *step.run[1:])
    shown = shlex.join(step.run)
    with _group(step.name):
        print(f"$ {shown}", flush=True)
        try:
            result = subprocess.run(
                command,
                cwd=directory,
                env=os.environ | step.env,
                check=True,
                timeout=step.timeout,
                stdout=subprocess.PIPE if step.fail_on_output else None,
                text=True,
            )
        except subprocess.TimeoutExpired as error:
            message = f"{step.name}: timed out after {step.timeout}s"
            raise CiError(message) from error
        except subprocess.CalledProcessError as error:
            print(error.stdout or "", end="")
            message = f"{step.name}: {shown} exited with {error.returncode}"
            raise CiError(message) from error
        if result.stdout:
            print(result.stdout, end="")
            raise CiError(f"{step.name}: {shown} reported findings")


def _executable(program: str, directory: Path) -> str:
    # which() applies PATHEXT on Windows, so "npm" resolves to npm.cmd.
    relative = "/" in program or os.sep in program
    found = shutil.which(str(directory / program) if relative else program)
    if found is None:
        raise CiError(f"executable not found: {program}")
    return found


@contextmanager
def _group(title: str) -> Iterator[None]:
    on_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    print(f"::group::{title}" if on_actions else f"==> {title}", flush=True)
    try:
        yield
    finally:
        if on_actions:
            print("::endgroup::", flush=True)
