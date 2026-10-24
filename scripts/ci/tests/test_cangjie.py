import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from ip2region_ci import cangjie
from ip2region_ci.errors import CiError


def sdk_archive(path: Path) -> cangjie.Sdk:
    payload = b'export PATH="$PWD/bin:$PATH"\n'
    with tarfile.open(path, "w:gz") as archive:
        envsetup = tarfile.TarInfo("cangjie/envsetup.sh")
        envsetup.size = len(payload)
        archive.addfile(envsetup, io.BytesIO(payload))
    content = path.read_bytes()
    return cangjie.Sdk(
        version="test",
        url=path.as_uri(),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def test_installs_and_reuses_sdk(tmp_path: Path) -> None:
    sdk = sdk_archive(tmp_path / "sdk.tar.gz")
    destination = tmp_path / "installed"

    envsetup = cangjie.install(destination, sdk)

    assert envsetup == destination / "cangjie" / "envsetup.sh"
    assert cangjie.install(destination, sdk) == envsetup


def test_rejects_digest_mismatch(tmp_path: Path) -> None:
    sdk = sdk_archive(tmp_path / "sdk.tar.gz")
    tampered = cangjie.Sdk(sdk.version, sdk.url, "0" * 64, sdk.size)

    with pytest.raises(CiError, match="SHA-256 mismatch"):
        cangjie.install(tmp_path / "installed", tampered)
    assert not (tmp_path / "installed").exists()
