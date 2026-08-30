"""Typer command-line interface for the CI control plane."""

from pathlib import Path
from typing import Annotated

import typer

from ip2region_ci.cangjie import CangjieInstallError, install_cangjie
from ip2region_ci.manifest import (
    ManifestError,
    component_by_id,
    default_manifest_path,
    load_manifest,
    repository_root,
    validate_repository_coverage,
)
from ip2region_ci.runner import ComponentRunError, current_architecture, run_component

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)

ManifestOption = Annotated[
    Path | None,
    typer.Option("--manifest", exists=True, dir_okay=False, readable=True),
]
RootOption = Annotated[
    Path | None,
    typer.Option("--repository", exists=True, file_okay=False, readable=True),
]


def fail(message: str) -> None:
    """Print one contextual error and terminate the CLI command."""
    typer.secho(f"error: {message}", fg=typer.colors.RED, err=True)
    raise typer.Exit(code=1)


@app.command("validate")
def validate_command(manifest: ManifestOption = None, repository: RootOption = None) -> None:
    """Validate schema, aliases, paths, and exhaustive component coverage."""
    try:
        loaded = load_manifest(manifest)
        errors = validate_repository_coverage(loaded, repository or repository_root())
    except ManifestError as error:
        fail(str(error))
    if errors:
        fail("\n".join(errors))
    manifest_source = manifest or default_manifest_path()
    typer.echo(f"validated {len(loaded.components)} components from {manifest_source}")


@app.command("list")
def list_command(manifest: ManifestOption = None) -> None:
    """List every registered binding, maker, alias, and unsupported placeholder."""
    try:
        loaded = load_manifest(manifest)
    except ManifestError as error:
        fail(str(error))
    for component in loaded.components:
        platforms = ",".join(sorted(component.platforms)) if component.platforms else "-"
        typer.echo(f"{component.id}\t{component.kind}\t{platforms}\t{component.path}")


@app.command("architecture")
def architecture_command(
    expected: Annotated[str, typer.Argument(help="Expected x64 or arm64 architecture")],
) -> None:
    """Verify the runner uses the requested native processor architecture."""
    try:
        actual = current_architecture()
    except ComponentRunError as error:
        fail(str(error))
    if expected not in {"x64", "arm64"}:
        fail(f"unsupported expected architecture: {expected}")
    if actual != expected:
        fail(f"runner architecture mismatch: expected {expected}, got {actual}")
    typer.echo(f"verified native {actual} runner")


@app.command("install-cangjie")
def install_cangjie_command(
    destination: Annotated[Path, typer.Argument(file_okay=False, resolve_path=True)],
) -> None:
    """Install the pinned Linux x64 Cangjie SDK and print its envsetup path."""
    try:
        envsetup = install_cangjie(destination)
    except CangjieInstallError as error:
        fail(str(error))
    typer.echo(envsetup)


@app.command("run")
def run_command(
    component_id: Annotated[str, typer.Argument(help="Stable component ID")],
    manifest: ManifestOption = None,
    repository: RootOption = None,
) -> None:
    """Run one component's canonical build and test sequence."""
    try:
        loaded = load_manifest(manifest)
        component = component_by_id(loaded, component_id)
        run_component(component, repository or repository_root())
    except (ManifestError, ComponentRunError) as error:
        fail(str(error))
