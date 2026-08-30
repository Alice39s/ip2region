from pathlib import Path

from ip2region_ci.manifest import (
    component_by_id,
    load_manifest,
    repository_root,
    validate_repository_coverage,
)


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


def test_script_style_bindings_invoke_real_test_functions() -> None:
    manifest = load_manifest()

    for component_id in ("binding-lua", "binding-lua-c", "binding-php", "binding-python"):
        component = component_by_id(manifest, component_id)
        test_steps = tuple(step for step in component.steps if step.name.startswith("Test"))
        assert test_steps
        assert all(len(step.command) >= 3 for step in test_steps)
