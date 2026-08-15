from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaWarning,
)
from systograph.core.services.ua_sidecar_request_builder import (
    UaRequestBuilder,
    write_json,
)
from systograph.core.services.ua_sidecar_result_builder import (
    UnderstandAnythingResultValidator,
)
from systograph.core.services.ua_sidecar_runtime import (
    NodeRuntimePreflight,
    UaAnalysisError,
    UaProcessOutput,
    UaRuntimePaths,
    UnderstandAnythingSubprocessRunner,
)
from systograph.core.services.ua_sidecar_script_models import (
    UaStructureScriptOutput,
)

KEEP_WORK_DIR_ENV = "SYSTOGRAPH_KEEP_UA_WORK_DIR"
TREE_SITTER_FAILURE_MARKER = "tree-sitter init failed"


class UaRuntimePreflight(Protocol):
    def validate(self) -> UaRuntimePaths: ...


class UaProcessRunner(Protocol):
    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
    ) -> UaProcessOutput: ...


class UnderstandAnythingAnalysisService:
    def __init__(
        self,
        *,
        preflight: UaRuntimePreflight | None = None,
        runner: UaProcessRunner | None = None,
        validator: UnderstandAnythingResultValidator | None = None,
        request_builder: UaRequestBuilder | None = None,
        work_dir_parent: Path | None = None,
    ) -> None:
        self._preflight = preflight or NodeRuntimePreflight()
        self._runner = runner or UnderstandAnythingSubprocessRunner()
        self._validator = validator or UnderstandAnythingResultValidator()
        self._request_builder = request_builder or UaRequestBuilder()
        self._work_dir_parent = work_dir_parent

    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult:
        root = project_root.resolve(strict=True)
        request = self._request_builder.build(root, inventory)
        paths = self._preflight.validate()
        warnings: list[UaWarning] = []
        quarantine_warnings: list[UaWarning] = []

        with self._work_directory() as work_dir:
            request_path = work_dir / "ua-request.json"
            import_input = work_dir / "import-input.json"
            import_output = work_dir / "import-output.json"
            scan_result = work_dir / "scan-result.json"
            batches_output = work_dir / "batches.json"
            request_path.write_text(request.model_dump_json(indent=2))
            write_json(
                import_input, self._request_builder.import_input(request)
            )

            output = self._run(
                "extract-import-map",
                (
                    str(paths.node_executable),
                    str(paths.extract_import_map),
                    str(import_input),
                    str(import_output),
                ),
                paths.script_root,
            )
            warnings.extend(self._warnings("extract-import-map", output))
            typed_imports = self._validator.load_import(import_output)
            write_json(
                scan_result,
                {
                    "files": self._request_builder.script_files(request),
                    "importMap": typed_imports.import_map,
                },
            )

            output = self._run(
                "compute-batches",
                (
                    str(paths.node_executable),
                    str(paths.compute_batches),
                    str(root),
                    f"--input={scan_result}",
                    f"--output={batches_output}",
                    f"--work-dir={work_dir}",
                ),
                paths.script_root,
            )
            warnings.extend(self._warnings("compute-batches", output))
            batches = self._validator.load_batches(batches_output)

            structures: list[tuple[int, UaStructureScriptOutput]] = []
            for batch in batches.batches:
                input_path = (
                    work_dir / f"structure-{batch.batch_index}.input.json"
                )
                output_path = work_dir / f"structure-{batch.batch_index}.json"
                write_json(
                    input_path,
                    {
                        "projectRoot": str(root),
                        "batchFiles": [
                            item.model_dump(by_alias=True)
                            for item in batch.files
                        ],
                        "batchImportData": batch.batch_import_data,
                    },
                )
                output = self._run(
                    "extract-structure",
                    (
                        str(paths.node_executable),
                        str(paths.extract_structure),
                        str(input_path),
                        str(output_path),
                    ),
                    paths.script_root,
                )
                warnings.extend(self._warnings("extract-structure", output))
                loaded = self._validator.load_structure(output_path)
                quarantine_warnings.extend(loaded.warnings)
                structures.append((batch.batch_index, loaded.output))

            return self._validator.build(
                inventory=inventory,
                import_output=typed_imports,
                batch_output=batches,
                structure_outputs=tuple(structures),
                # Quarantine records evidence loss; they outrank stage
                # stderr chatter when the 100-warning cap truncates.
                warnings=tuple((*quarantine_warnings, *warnings)[:100]),
            )

    def _run(
        self,
        stage: str,
        command: tuple[str, ...],
        cwd: Path,
    ) -> UaProcessOutput:
        output = self._runner.run(command, cwd=cwd)
        if TREE_SITTER_FAILURE_MARKER in output.stderr.lower():
            raise UaAnalysisError(
                "ua_tree_sitter_unavailable",
                f"UA {stage} could not initialize tree-sitter",
            )
        return output

    def _warnings(
        self,
        stage: str,
        output: UaProcessOutput,
    ) -> list[UaWarning]:
        lines = [
            line.strip() for line in output.stderr.splitlines() if line.strip()
        ]
        return [UaWarning(stage=stage, message=line[:2048]) for line in lines]

    @contextmanager
    def _work_directory(self) -> Iterator[Path]:
        parent = str(self._work_dir_parent) if self._work_dir_parent else None
        if os.getenv(KEEP_WORK_DIR_ENV) == "1":
            yield Path(tempfile.mkdtemp(prefix="systograph-ua-", dir=parent))
            return
        with tempfile.TemporaryDirectory(
            prefix="systograph-ua-",
            dir=parent,
        ) as directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            try:
                yield path
            finally:
                if path.exists():
                    shutil.rmtree(path, ignore_errors=True)


__all__ = [
    "NodeRuntimePreflight",
    "UaAnalysisError",
    "UaProcessOutput",
    "UaRuntimePaths",
    "UnderstandAnythingAnalysisService",
    "UnderstandAnythingSubprocessRunner",
]
