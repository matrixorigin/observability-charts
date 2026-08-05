#!/usr/bin/env python3
"""Compare two Helm Chart archives without extracting either archive."""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import tarfile
import tempfile
from dataclasses import dataclass


MAX_MEMBERS = 16_384
MAX_MEMBER_SIZE = 512 * 1024 * 1024
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024
MAX_NESTING_DEPTH = 8
READ_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ArchiveMember:
    kind: str
    mode: int
    size: int
    sha256: str | None


@dataclass
class ArchiveBudget:
    members: int = 0
    total_size: int = 0


def fail(message: str) -> None:
    raise ValueError(message)


def canonical_member_name(archive_path: str, raw_name: str) -> str:
    member_path = pathlib.PurePosixPath(raw_name)
    canonical_name = str(member_path)

    if (
        not raw_name
        or "\\" in raw_name
        or member_path.is_absolute()
        or ".." in member_path.parts
        or canonical_name in {"", "."}
        or canonical_name != raw_name.rstrip("/")
    ):
        fail(f"unsafe or non-canonical member in {archive_path}: {raw_name!r}")

    return canonical_name


def copy_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    destination=None,
) -> str:
    extracted = archive.extractfile(member)

    if extracted is None:
        fail(f"cannot read archive member: {member.name}")

    digest = hashlib.sha256()
    bytes_read = 0

    while True:
        chunk = extracted.read(READ_SIZE)

        if not chunk:
            break

        bytes_read += len(chunk)
        digest.update(chunk)

        if destination is not None:
            destination.write(chunk)

    if bytes_read != member.size:
        fail(
            f"archive member size mismatch for {member.name}: "
            f"declared={member.size}, read={bytes_read}"
        )

    return digest.hexdigest()


def manifest_digest(manifest: dict[str, ArchiveMember]) -> str:
    serializable = [
        [name, member.kind, member.mode, member.size, member.sha256]
        for name, member in sorted(manifest.items())
    ]
    encoded = json.dumps(
        serializable,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_archive_manifest(
    archive: tarfile.TarFile,
    archive_path: str,
    depth: int,
    budget: ArchiveBudget,
) -> dict[str, ArchiveMember]:
    result: dict[str, ArchiveMember] = {}

    if depth > MAX_NESTING_DEPTH:
        fail(f"Chart archive nesting is too deep: {archive_path}")

    for member in archive:
        budget.members += 1

        if budget.members > MAX_MEMBERS:
            fail(f"too many members in Chart archive {archive_path}")

        member_name = canonical_member_name(archive_path, member.name)

        if member_name in result:
            fail(f"duplicate member in {archive_path}: {member_name}")

        if member.isdir():
            result[member_name] = ArchiveMember(
                kind="directory",
                mode=member.mode,
                size=0,
                sha256=None,
            )
            continue

        if not member.isfile():
            fail(
                f"unsupported member type in {archive_path}: "
                f"{member_name}"
            )

        if member.size < 0 or member.size > MAX_MEMBER_SIZE:
            fail(
                f"invalid or oversized member in {archive_path}: "
                f"{member_name} ({member.size} bytes)"
            )

        budget.total_size += member.size

        if budget.total_size > MAX_TOTAL_SIZE:
            fail(f"uncompressed Chart archives are too large: {archive_path}")

        if member_name.endswith(".tgz"):
            with tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024) as nested_file:
                copy_member(archive, member, nested_file)
                nested_file.seek(0)

                try:
                    with tarfile.open(fileobj=nested_file, mode="r:gz") as nested_archive:
                        nested_manifest = read_archive_manifest(
                            nested_archive,
                            f"{archive_path}!/{member_name}",
                            depth + 1,
                            budget,
                        )
                except (OSError, tarfile.TarError) as error:
                    fail(
                        f"cannot open nested Chart archive "
                        f"{archive_path}!/{member_name}: {error}"
                    )

            result[member_name] = ArchiveMember(
                kind="chart-archive",
                mode=member.mode,
                size=0,
                sha256=manifest_digest(nested_manifest),
            )
        else:
            result[member_name] = ArchiveMember(
                kind="file",
                mode=member.mode,
                size=member.size,
                sha256=copy_member(archive, member),
            )

    if not result:
        fail(f"empty Chart archive: {archive_path}")

    return result


def archive_manifest(archive_path: str) -> dict[str, ArchiveMember]:
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            return read_archive_manifest(
                archive,
                archive_path,
                depth=0,
                budget=ArchiveBudget(),
            )
    except (OSError, tarfile.TarError) as error:
        fail(f"cannot open Chart archive {archive_path}: {error}")


def main() -> int:
    if len(sys.argv) != 3:
        print(
            f"usage: {pathlib.Path(sys.argv[0]).name} LOCAL.tgz PUBLISHED.tgz",
            file=sys.stderr,
        )
        return 2

    try:
        local_manifest = archive_manifest(sys.argv[1])
        published_manifest = archive_manifest(sys.argv[2])
    except (ValueError, OSError, tarfile.TarError) as error:
        print(error, file=sys.stderr)
        return 1

    if local_manifest == published_manifest:
        return 0

    local_names = set(local_manifest)
    published_names = set(published_manifest)
    added = sorted(published_names - local_names)
    removed = sorted(local_names - published_names)
    changed = sorted(
        name
        for name in local_names & published_names
        if local_manifest[name] != published_manifest[name]
    )
    print("published Chart content differs from the local package", file=sys.stderr)
    print(f"added={added}", file=sys.stderr)
    print(f"removed={removed}", file=sys.stderr)
    print(f"changed={changed}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
