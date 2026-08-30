"""Manifest loading and repository coverage validation."""

import tomllib
from pathlib import Path

from pydantic import ValidationError

from ip2region_ci.models import Component, Manifest


class ManifestError(RuntimeError):
    """Raised when the CI manifest cannot be loaded or validated."""


def package_directory() -> Path:
    """Return the ci-workflow package directory."""
    return Path(__file__).resolve().parents[2]


def repository_root() -> Path:
    """Return the repository root derived from this installed source tree."""
    return package_directory().parents[1]


def default_manifest_path() -> Path:
    """Return the canonical component manifest path."""
    return package_directory() / "components.toml"


def load_manifest(path: Path | None = None) -> Manifest:
    """Load and strictly validate a TOML component manifest."""
    manifest_path = path or default_manifest_path()
    try:
        with manifest_path.open("rb") as file:
            payload = tomllib.load(file)
        return Manifest.model_validate(payload)
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as error:
        msg = f"failed to load CI manifest {manifest_path}: {error}"
        raise ManifestError(msg) from error


def component_by_id(manifest: Manifest, component_id: str) -> Component:
    """Resolve one component by its stable manifest identifier."""
    for component in manifest.components:
        if component.id == component_id:
            return component
    msg = f"unknown component: {component_id}"
    raise ManifestError(msg)


def validate_repository_coverage(manifest: Manifest, root: Path) -> tuple[str, ...]:
    """Return all manifest-to-repository contract violations."""
    errors: list[str] = []
    registered_paths = {component.path for component in manifest.components}
    component_ids = {component.id for component in manifest.components}
    discovered_paths: set[str] = set()

    for component_root in manifest.component_roots:
        root_path = root / component_root
        if not root_path.is_dir():
            errors.append(f"component root does not exist: {component_root}")
            continue
        discovered_paths.update(
            child.relative_to(root).as_posix() for child in root_path.iterdir() if child.is_dir()
        )

    for missing in sorted(discovered_paths - registered_paths):
        errors.append(f"unregistered component directory: {missing}")
    for extra in sorted(registered_paths - discovered_paths):
        errors.append(f"manifest path does not exist: {extra}")

    for component in manifest.components:
        if component.alias_of is not None and component.alias_of not in component_ids:
            errors.append(f"{component.id} aliases unknown component {component.alias_of}")

    return tuple(errors)
