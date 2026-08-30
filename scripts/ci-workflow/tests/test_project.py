import tomllib

from ip2region_ci.manifest import package_directory


def test_lock_file_uses_only_pypi_registry() -> None:
    with (package_directory() / "uv.lock").open("rb") as lock_file:
        lock = tomllib.load(lock_file)

    registries = {
        package["source"]["registry"]
        for package in lock["package"]
        if "registry" in package["source"]
    }
    assert registries == {"https://pypi.org/simple"}
