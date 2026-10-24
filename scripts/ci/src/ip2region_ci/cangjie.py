import hashlib
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from ip2region_ci.errors import CiError


@dataclass(frozen=True)
class Sdk:
    version: str
    url: str
    sha256: str
    size: int


LINUX_X64 = Sdk(
    version="1.1.3",
    url=(
        "https://cangjie-lang.cn/v1/files/auth/downLoad?nsId=142267"
        "&fileName=cangjie-sdk-linux-x64-1.1.3.tar.gz"
        "&objectKey=6a19349d21f5a8178d6fd22b"
    ),
    sha256="2b68905afc466e665ae181595c63f96c18d75fd2c1fb6c6f0cb64e179c28d61a",
    size=403_288_797,
)


def install(destination: Path, sdk: Sdk = LINUX_X64) -> Path:
    """Installs a verified SDK, or reuses a complete one, and returns the
    path of its envsetup.sh."""
    if destination.is_dir():
        return _envsetup(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as scratch:
        archive_path = Path(scratch) / "sdk.tar.gz"
        extracted = Path(scratch) / "sdk"
        _download(sdk, archive_path)
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(extracted, filter="data")
        except tarfile.TarError as error:
            raise CiError(f"Cangjie SDK {sdk.version}: {error}") from error
        envsetup = _envsetup(extracted).relative_to(extracted)
        shutil.move(extracted, destination)
    return destination / envsetup


def _download(sdk: Sdk, destination: Path) -> None:
    request = Request(sdk.url, headers={"User-Agent": "ip2region-ci"})
    digest = hashlib.sha256()
    size = 0
    try:
        with (
            urlopen(request, timeout=60) as response,
            destination.open("wb") as out,
        ):
            while chunk := response.read(1 << 20):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise CiError(f"Cangjie SDK {sdk.version}: {error}") from error
    if (size, digest.hexdigest()) != (sdk.size, sdk.sha256):
        raise CiError(f"Cangjie SDK {sdk.version}: size or SHA-256 mismatch")


def _envsetup(directory: Path) -> Path:
    matches = list(directory.rglob("envsetup.sh"))
    if len(matches) != 1:
        message = f"{directory}: expected one envsetup.sh, found {len(matches)}"
        raise CiError(message)
    return matches[0]
