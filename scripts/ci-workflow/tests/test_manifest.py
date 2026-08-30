from pathlib import Path

from ip2region_ci.manifest import load_manifest, repository_root, validate_repository_coverage


def test_manifest_covers_every_component_directory() -> None:
    manifest = load_manifest()

    assert validate_repository_coverage(manifest, repository_root()) == ()


def test_manifest_has_runnable_bindings_and_makers() -> None:
    manifest = load_manifest()
    runnable_kinds = {component.kind for component in manifest.components if component.runnable}

    assert runnable_kinds == {"binding", "maker"}
    assert all(
        Path(component.path).parts[0] in {"binding", "maker"} for component in manifest.components
    )
