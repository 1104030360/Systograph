from __future__ import annotations

import ast
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from systograph.core.models.filesystem import FileInventory, FileRecord
from systograph.core.models.scan import ProviderScanResult
from systograph.core.services.ast_construction_analysis import (
    collect_imports,
    collect_runtime_calls,
)
from systograph.core.services.ast_construction_factory_index import (
    build_factory_index,
)
from systograph.core.services.ast_construction_factory_output import (
    emit_factory_inferences,
)
from systograph.core.services.ast_construction_output import (
    AstConstructionOutput,
)
from systograph.core.services.ast_construction_types import (
    ImportBinding,
    ParsedPythonFile,
    internal_module_names,
    module_level_bindings,
    module_name_for_path,
    resolve_call_symbol,
)
from systograph.core.services.path_safety_service import (
    is_project_relative_posix_path,
)
from systograph.core.services.rule_catalog_loader import RuleCatalogLoader
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

DEFAULT_MAX_FILE_SIZE_BYTES = 250_000
DEFAULT_MAX_SNIPPET_CHARS = 800


@dataclass(frozen=True, slots=True)
class _PinnedProjectRoot:
    path: Path
    descriptor: int
    device: int
    inode: int


class AstConstructionProvider:
    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_snippet_chars: int = DEFAULT_MAX_SNIPPET_CHARS,
        rule_catalog_path: Path | str | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._max_file_size_bytes = max_file_size_bytes
        rules = RuleCatalogLoader().load_code_pattern_rules(rule_catalog_path)
        rules_by_symbol = {
            rule.symbol: rule for rule in rules if rule.symbol is not None
        }
        self._output = AstConstructionOutput(
            rules_by_symbol=rules_by_symbol,
            masking_service=self._masking_service,
            max_snippet_chars=max(1, max_snippet_chars),
        )

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root).resolve()
        records = sorted(inventory.files, key=lambda item: item.path)
        try:
            pinned_root = self._pin_project_root(project_root)
        except OSError:
            for record in records:
                if PurePosixPath(record.path).suffix == ".py":
                    self._output.append_issue(
                        result,
                        record.path,
                        "ast_construction_read_error",
                        "Failed to read Python source safely",
                    )
            self._output.sort_result(result)
            return result
        try:
            internal_modules = internal_module_names(
                [
                    record.path
                    for record in records
                    if PurePosixPath(record.path).suffix == ".py"
                    and is_project_relative_posix_path(record.path)
                ]
            )
            parsed_files: list[ParsedPythonFile] = []
            for record in records:
                parsed = self._parse_record(pinned_root, record, result)
                if parsed is not None:
                    parsed_files.append(parsed)

            # Re-export resolution needs every file's bindings, so the
            # binding pass must finish before any call is resolved.
            bindings_by_file: dict[str, list[ImportBinding]] = {}
            for parsed in parsed_files:
                bindings = collect_imports(
                    parsed.tree,
                    module_name=parsed.module_name,
                    is_package=parsed.is_package,
                    internal_modules=internal_modules,
                )
                bindings_by_file[parsed.relative_path] = bindings
                self._output.emit_imports(result, parsed, bindings)

            module_bindings = module_level_bindings(
                parsed_files,
                bindings_by_file,
            )
            for parsed in parsed_files:
                runtime_calls = collect_runtime_calls(
                    parsed.tree,
                    module_name=parsed.module_name,
                )
                for runtime_call in runtime_calls:
                    symbol = resolve_call_symbol(
                        runtime_call.node.func,
                        scope=runtime_call.scope,
                        bindings=bindings_by_file[parsed.relative_path],
                        known_symbols=self._output.known_symbols,
                        module_bindings=module_bindings,
                    )
                    if symbol is not None:
                        self._output.emit_direct_call(
                            result,
                            parsed,
                            runtime_call,
                            symbol,
                        )

            factory_index = build_factory_index(
                parsed_files,
                bindings_by_file,
                self._output.known_symbols,
                module_bindings=module_bindings,
            )
            emit_factory_inferences(
                result,
                index=factory_index,
                output=self._output,
            )
        finally:
            os.close(pinned_root.descriptor)

        self._output.sort_result(result)
        return result

    def _parse_record(
        self,
        pinned_root: _PinnedProjectRoot,
        record: FileRecord,
        result: ProviderScanResult,
    ) -> ParsedPythonFile | None:
        if PurePosixPath(record.path).suffix != ".py":
            return None
        if record.size_bytes > self._max_file_size_bytes:
            self._output.append_issue(
                result,
                record.path,
                "ast_construction_file_skipped",
                "Skipped Python source: large_file",
            )
            return None
        file_path = self._resolve_inventory_path(
            pinned_root.path,
            record.path,
        )
        if file_path is None:
            self._output.append_issue(
                result,
                record.path,
                "ast_construction_invalid_inventory_path",
                "Skipped Python source: invalid inventory path",
            )
            return None
        try:
            source = self._read_verified_source(pinned_root, record)
            tree = ast.parse(source, filename=record.path)
        except (OSError, UnicodeDecodeError):
            self._output.append_issue(
                result,
                record.path,
                "ast_construction_read_error",
                "Failed to read Python source safely",
            )
            return None
        except SyntaxError as exc:
            self._output.append_issue(
                result,
                record.path,
                "ast_construction_parse_error",
                f"Failed to parse Python source: {exc.msg}",
                line=exc.lineno,
                column=exc.offset,
            )
            return None
        return ParsedPythonFile(
            relative_path=record.path,
            source=source,
            tree=tree,
            module_name=module_name_for_path(record.path),
            is_package=PurePosixPath(record.path).name == "__init__.py",
        )

    @staticmethod
    def _resolve_inventory_path(
        project_root: Path,
        relative_path: str,
    ) -> Path | None:
        if not is_project_relative_posix_path(relative_path):
            return None
        posix_path = PurePosixPath(relative_path)
        candidate = (project_root / Path(*posix_path.parts)).resolve()
        if not candidate.is_file() or not candidate.is_relative_to(
            project_root
        ):
            return None
        return candidate

    @classmethod
    def _read_verified_source(
        cls,
        pinned_root: _PinnedProjectRoot,
        record: FileRecord,
    ) -> str:
        expected_fingerprint = record.content_fingerprint
        if expected_fingerprint is None:
            raise OSError("inventory content fingerprint is unavailable")
        cls._assert_root_identity(pinned_root)
        descriptor = cls._open_relative(
            pinned_root.descriptor,
            record.path,
        )
        try:
            opened = os.fstat(descriptor)
            cls._assert_root_identity(pinned_root)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_size != record.size_bytes
            ):
                raise OSError("inventory path changed before safe read")
            with os.fdopen(descriptor, "rb") as handle:
                descriptor = -1
                payload = handle.read()
            cls._assert_root_identity(pinned_root)
            actual_fingerprint = (
                "sha256:" + hashlib.sha256(payload).hexdigest()
            )
            if (
                len(payload) != record.size_bytes
                or actual_fingerprint != expected_fingerprint
            ):
                raise OSError("inventory content changed before safe read")
            return payload.decode("utf-8")
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    @staticmethod
    def _safe_open_flags(
        platform_name: str | None = None,
    ) -> tuple[int, int] | None:
        if (platform_name or os.name) != "posix":
            return None
        nofollow = getattr(os, "O_NOFOLLOW", None)
        directory = getattr(os, "O_DIRECTORY", None)
        if (
            not isinstance(nofollow, int)
            or nofollow == 0
            or not isinstance(directory, int)
            or directory == 0
            or os.open not in getattr(os, "supports_dir_fd", ())
        ):
            return None
        directory_flags = (
            os.O_RDONLY | nofollow | directory | getattr(os, "O_CLOEXEC", 0)
        )
        file_flags = (
            os.O_RDONLY
            | nofollow
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        return directory_flags, file_flags

    @classmethod
    def _pin_project_root(
        cls,
        project_root: Path,
    ) -> _PinnedProjectRoot:
        before = os.stat(project_root, follow_symlinks=False)
        if not stat.S_ISDIR(before.st_mode):
            raise OSError("project root is not a directory")
        flags = cls._safe_open_flags()
        if flags is None:
            raise OSError("safe project root open is unavailable")
        directory_flags, _ = flags
        descriptor = os.open(
            project_root,
            directory_flags,
        )
        try:
            opened = os.fstat(descriptor)
            current = os.stat(project_root, follow_symlinks=False)
            identities = {
                (before.st_dev, before.st_ino),
                (opened.st_dev, opened.st_ino),
                (current.st_dev, current.st_ino),
            }
            if not stat.S_ISDIR(opened.st_mode) or len(identities) != 1:
                raise OSError("project root changed before safe read")
            return _PinnedProjectRoot(
                path=project_root,
                descriptor=descriptor,
                device=opened.st_dev,
                inode=opened.st_ino,
            )
        except BaseException:
            os.close(descriptor)
            raise

    @staticmethod
    def _assert_root_identity(pinned_root: _PinnedProjectRoot) -> None:
        current = os.stat(pinned_root.path, follow_symlinks=False)
        if not stat.S_ISDIR(current.st_mode) or (
            current.st_dev,
            current.st_ino,
        ) != (pinned_root.device, pinned_root.inode):
            raise OSError("project root changed before safe read")

    @classmethod
    def _open_relative(
        cls,
        root_descriptor: int,
        relative_path: str,
    ) -> int:
        posix_path = PurePosixPath(relative_path)
        parts = posix_path.parts
        if (
            not parts
            or not is_project_relative_posix_path(relative_path)
            or posix_path.is_absolute()
            or ".." in parts
        ):
            raise OSError("invalid project-relative path")
        flags = cls._safe_open_flags()
        if flags is None:
            raise OSError("safe project-relative open is unavailable")
        directory_flags, file_flags = flags
        directory_descriptor = os.dup(root_descriptor)
        try:
            for part in parts[:-1]:
                next_descriptor = os.open(
                    part,
                    directory_flags,
                    dir_fd=directory_descriptor,
                )
                os.close(directory_descriptor)
                directory_descriptor = next_descriptor
            return os.open(
                parts[-1],
                file_flags,
                dir_fd=directory_descriptor,
            )
        finally:
            os.close(directory_descriptor)
