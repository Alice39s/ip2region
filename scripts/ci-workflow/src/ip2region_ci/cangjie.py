"""Verified installation of the Cangjie SDK used by CI."""

import hashlib
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


class CangjieInstallError(RuntimeError):
    """Raised when the pinned Cangjie SDK cannot be installed safely."""


@dataclass(frozen=True)
class CangjieArtifact:
    """One immutable SDK download published by the Cangjie project."""

    version: str
    url: str
    sha256: str
    size: int


LINUX_X64_ARTIFACT = CangjieArtifact(
    version="1.1.3",
    url=(
        "https://cangjie-lang.cn/v1/files/auth/downLoad?nsId=142267"
        "&fileName=cangjie-sdk-linux-x64-1.1.3.tar.gz"
        "&objectKey=6a19349d21f5a8178d6fd22b"
    ),
    sha256="2b68905afc466e665ae181595c63f96c18d75fd2c1fb6c6f0cb64e179c28d61a",
    size=403_288_797,
)


def find_envsetup(directory: Path) -> Path:
    """Locate the SDK environment script while rejecting ambiguous archives."""
    matches = tuple(directory.rglob("envsetup.sh"))
    if len(matches) != 1:
        msg = f"expected one envsetup.sh under {directory}, found {len(matches)}"
        raise CangjieInstallError(msg)
    return matches[0]


def download_artifact(artifact: CangjieArtifact, destination: Path) -> None:
    """Stream one SDK archive to disk and verify its length and digest."""
    request = Request(artifact.url, headers={"User-Agent": "ip2region-ci"})
    digest = hashlib.sha256()
    downloaded = 0

    try:
        with urlopen(request, timeout=60) as response, destination.open("wb") as output:
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                output.write(chunk)
                digest.update(chunk)
                downloaded += len(chunk)
    except OSError as error:
        msg = f"failed to download Cangjie SDK {artifact.version}: {error}"
        raise CangjieInstallError(msg) from error

    if downloaded != artifact.size:
        msg = f"Cangjie SDK length mismatch: expected {artifact.size}, got {downloaded}"
        raise CangjieInstallError(msg)
    if digest.hexdigest() != artifact.sha256:
        msg = "Cangjie SDK SHA-256 mismatch"
        raise CangjieInstallError(msg)


def install_cangjie(destination: Path, artifact: CangjieArtifact = LINUX_X64_ARTIFACT) -> Path:
    """Install a verified SDK atomically, or reuse a complete cached installation."""
    if destination.is_dir():
        return find_envsetup(destination)
    if destination.exists():
        msg = f"Cangjie SDK destination is not a directory: {destination}"
        raise CangjieInstallError(msg)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="cangjie-sdk-", suffix=".tar.gz", dir=destination.parent, delete=False
    ) as archive_handle:
        archive_path = Path(archive_handle.name)
    extraction_path = Path(tempfile.mkdtemp(prefix="cangjie-extract-", dir=destination.parent))

    try:
        download_artifact(artifact, archive_path)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extraction_path, filter="data")
        relative_envsetup = find_envsetup(extraction_path).relative_to(extraction_path)
        extraction_path.rename(destination)
        return destination / relative_envsetup
    except (OSError, tarfile.TarError) as error:
        msg = f"failed to extract Cangjie SDK {artifact.version}: {error}"
        raise CangjieInstallError(msg) from error
    finally:
        archive_path.unlink(missing_ok=True)
        if extraction_path.exists():
            shutil.rmtree(extraction_path)
