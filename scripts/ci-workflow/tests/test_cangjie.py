import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from ip2region_ci.cangjie import (
    LINUX_X64_ARTIFACT,
    CangjieArtifact,
    CangjieInstallError,
    install_cangjie,
)


def create_sdk_archive(path: Path) -> CangjieArtifact:
    payload = b'export PATH="$PWD/bin:$PATH"\n'
    with tarfile.open(path, "w:gz") as archive:
        envsetup = tarfile.TarInfo("cangjie/envsetup.sh")
        envsetup.size = len(payload)
        archive.addfile(envsetup, io.BytesIO(payload))

    content = path.read_bytes()
    return CangjieArtifact(
        version="test",
        url=path.as_uri(),
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
    )


def test_install_cangjie_verifies_and_reuses_sdk(tmp_path: Path) -> None:
    artifact = create_sdk_archive(tmp_path / "sdk.tar.gz")
    destination = tmp_path / "installed"

    envsetup = install_cangjie(destination, artifact)

    assert envsetup == destination / "cangjie" / "envsetup.sh"
    assert install_cangjie(destination, artifact) == envsetup


def test_install_cangjie_rejects_digest_mismatch(tmp_path: Path) -> None:
    artifact = create_sdk_archive(tmp_path / "sdk.tar.gz")
    invalid = CangjieArtifact(
        version=artifact.version,
        url=artifact.url,
        sha256="0" * 64,
        size=artifact.size,
    )

    with pytest.raises(CangjieInstallError, match="SHA-256 mismatch"):
        install_cangjie(tmp_path / "installed", invalid)


def test_cangjie_release_is_pinned() -> None:
    assert LINUX_X64_ARTIFACT.version == "1.1.3"
    assert len(LINUX_X64_ARTIFACT.sha256) == 64
    assert LINUX_X64_ARTIFACT.url.startswith("https://cangjie-lang.cn/")
