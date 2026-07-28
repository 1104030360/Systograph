from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

from systograph.core.models.inventory_selection import InventoryCandidate
from systograph.core.services.inventory_metadata_service import (
    InventoryMetadataService,
)

BINARY_PROBE_BYTES: Final = 4_096
HASH_READ_BYTES: Final = 65_536


@dataclass(frozen=True, slots=True)
class InventoryPostDecisionSafetyResult:
    allowed: bool
    reason_code: str | None = None
    changed: bool = False
    content_fingerprint: str | None = None


class InventoryPostDecisionSafetyService:
    def __init__(
        self,
        *,
        metadata_service: InventoryMetadataService | None = None,
    ) -> None:
        self._metadata = metadata_service or InventoryMetadataService()

    def check(
        self,
        project_root: Path,
        candidate: InventoryCandidate,
    ) -> InventoryPostDecisionSafetyResult:
        return self.fingerprint_record(
            project_root,
            path=candidate.path,
            expected_size_bytes=candidate.size_bytes,
            expected_metadata_fingerprint=candidate.metadata_fingerprint,
        )

    def fingerprint_record(
        self,
        project_root: Path,
        *,
        path: str,
        expected_size_bytes: int | None,
        expected_metadata_fingerprint: str | None,
    ) -> InventoryPostDecisionSafetyResult:
        root = project_root.resolve()
        local_path = root / path
        try:
            resolved = local_path.resolve(strict=True)
            resolved.relative_to(root)
            metadata = local_path.lstat()
        except (OSError, ValueError):
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="target_changed",
                changed=True,
            )
        current_fingerprint = self._metadata.file_fingerprint(
            path=path,
            target_type=self._target_type(metadata.st_mode),
            size_bytes=metadata.st_size,
            mtime_ns=metadata.st_mtime_ns,
        )
        if (
            expected_metadata_fingerprint is not None
            and current_fingerprint != expected_metadata_fingerprint
        ) or (
            expected_size_bytes is not None
            and metadata.st_size != expected_size_bytes
        ):
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="target_changed",
                changed=True,
            )
        if not stat.S_ISREG(metadata.st_mode):
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="unsupported_file_type",
            )
        open_flags = self._open_flags()
        if open_flags is None:
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="safe_open_unavailable",
            )
        try:
            handle = self._open_relative(root, path, open_flags)
        except OSError:
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="unreadable",
            )
        try:
            opened = os.fstat(handle)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_size != metadata.st_size
                or opened.st_mtime_ns != metadata.st_mtime_ns
                or opened.st_dev != metadata.st_dev
                or opened.st_ino != metadata.st_ino
            ):
                return InventoryPostDecisionSafetyResult(
                    allowed=False,
                    reason_code="target_changed",
                    changed=True,
                )
            probe = os.read(handle, BINARY_PROBE_BYTES)
            if b"\x00" in probe:
                return InventoryPostDecisionSafetyResult(
                    allowed=False,
                    reason_code="binary",
                )
            digest = hashlib.sha256()
            digest.update(probe)
            while chunk := os.read(handle, HASH_READ_BYTES):
                digest.update(chunk)
        except OSError:
            return InventoryPostDecisionSafetyResult(
                allowed=False,
                reason_code="unreadable",
            )
        finally:
            os.close(handle)
        return InventoryPostDecisionSafetyResult(
            allowed=True,
            content_fingerprint="sha256:" + digest.hexdigest(),
        )

    def _open_flags(self) -> int | None:
        nofollow = getattr(os, "O_NOFOLLOW", None)
        directory = getattr(os, "O_DIRECTORY", None)
        if (
            not isinstance(nofollow, int)
            or nofollow == 0
            or not isinstance(directory, int)
            or os.open not in os.supports_dir_fd
        ):
            return None
        flags = os.O_RDONLY
        flags |= nofollow
        flags |= getattr(os, "O_BINARY", 0)
        return flags

    def _open_relative(self, root: Path, path: str, flags: int) -> int:
        parts = PurePosixPath(path).parts
        if not parts or PurePosixPath(path).is_absolute() or ".." in parts:
            raise OSError("invalid project-relative path")
        directory_flags = (
            os.O_RDONLY
            | os.O_NOFOLLOW
            | os.O_DIRECTORY
            | getattr(os, "O_CLOEXEC", 0)
        )
        directory_handle = os.open(root, directory_flags)
        try:
            for part in parts[:-1]:
                next_handle = os.open(
                    part,
                    directory_flags,
                    dir_fd=directory_handle,
                )
                os.close(directory_handle)
                directory_handle = next_handle
            return os.open(parts[-1], flags, dir_fd=directory_handle)
        finally:
            os.close(directory_handle)

    def _target_type(self, mode: int) -> str:
        if stat.S_ISREG(mode):
            return "regular_file"
        if stat.S_ISDIR(mode):
            return "directory"
        if stat.S_ISLNK(mode):
            return "symlink"
        return "special"
