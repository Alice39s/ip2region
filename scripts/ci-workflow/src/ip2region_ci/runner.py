"""Portable, shell-free component command execution."""

import os
import platform as platform_module
import shlex
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from ip2region_ci.models import Component, Platform, Step


class ComponentRunError(RuntimeError):
    """Raised when a component cannot run or one of its steps fails."""


def current_architecture(machine: str | None = None) -> str:
    """Normalize common operating-system architecture names."""
    architecture = (machine or platform_module.machine()).lower()
    if architecture in {"amd64", "x86_64"}:
        return "x64"
    if architecture in {"aarch64", "arm64"}:
        return "arm64"
    msg = f"unsupported host architecture: {architecture}"
    raise ComponentRunError(msg)


def current_platform() -> Platform:
    """Normalize Python's platform name to the manifest vocabulary."""
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    msg = f"unsupported host platform: {sys.platform}"
    raise ComponentRunError(msg)


def run_step(step: Step, working_directory: Path, base_environment: Mapping[str, str]) -> None:
    """Execute one structured command with timeout and contextual errors."""
    environment = dict(base_environment)
    environment.update(step.environment)
    command_display = shlex.join(step.command)
    print(f"::group::{step.name}")
    print(f"$ {command_display}")
    try:
        subprocess.run(
            step.command,
            check=True,
            cwd=working_directory,
            env=environment,
            timeout=step.timeout_seconds,
        )
    except FileNotFoundError as error:
        msg = f"{step.name} requires missing executable {step.command[0]}"
        raise ComponentRunError(msg) from error
    except subprocess.TimeoutExpired as error:
        msg = f"{step.name} timed out after {step.timeout_seconds}s: {command_display}"
        raise ComponentRunError(msg) from error
    except subprocess.CalledProcessError as error:
        msg = f"{step.name} exited with status {error.returncode}: {command_display}"
        raise ComponentRunError(msg) from error
    finally:
        print("::endgroup::")


def run_component(
    component: Component,
    root: Path,
    platform: Platform | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Run every build/test step owned by a component on the current platform."""
    host_platform = platform or current_platform()
    if not component.runnable:
        msg = f"component {component.id} is {component.kind}, not runnable"
        raise ComponentRunError(msg)
    if host_platform not in component.platforms:
        msg = f"component {component.id} does not support {host_platform}"
        raise ComponentRunError(msg)

    working_directory = root / component.path
    if not working_directory.is_dir():
        msg = f"component directory does not exist: {working_directory}"
        raise ComponentRunError(msg)

    base_environment = environment if environment is not None else os.environ
    for step in component.steps:
        run_step(step, working_directory, base_environment)
