from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeVar

from pydantic import ValidationError

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaAnalysisStats,
    UaBatchCompletion,
    UaImportRow,
    UaStructuralResult,
    UaWarning,
)
from systograph.core.services.ua_sidecar_projection import (
    project_structure_rows,
)
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError
from systograph.core.services.ua_sidecar_script_models import (
    UaBatchScriptOutput,
    UaCall,
    UaEndpoint,
    UaExport,
    UaImportScriptOutput,
    UaNamedSpan,
    UaResource,
    UaScriptModel,
    UaService,
    UaStructureFile,
    UaStructureScriptOutput,
)

UaScriptModelT = TypeVar("UaScriptModelT", bound=UaScriptModel)

# Upstream extractors occasionally emit garbage entries (e.g. a whole
# multi-line source expression captured as a callee). One bad entry must
# not fail the whole scan closed: entries are validated one by one and
# invalid ones are quarantined with a loud warning, while envelope-level
# corruption and path-boundary violations stay fatal.
_STRUCTURE_ENTRY_MODELS: Final[dict[str, type[UaScriptModel]]] = {
    "functions": UaNamedSpan,
    "classes": UaNamedSpan,
    "exports": UaExport,
    # The models accept the alias and the field-name spelling alike
    # (validate_by_name), so quarantine must clean both keys.
    "callGraph": UaCall,
    "call_graph": UaCall,
    "resources": UaResource,
    "services": UaService,
    "endpoints": UaEndpoint,
}

_PATH_VIOLATION_MARKER: Final = "project-relative POSIX path"
_VALIDATE_STRUCTURE_STAGE: Final = "validate-structure"


@dataclass(frozen=True)
class UaStructureLoadResult:
    output: UaStructureScriptOutput
    warnings: tuple[UaWarning, ...]


class UnderstandAnythingResultValidator:
    def load_import(self, path: Path) -> UaImportScriptOutput:
        return self._load(path, UaImportScriptOutput)

    def load_batches(self, path: Path) -> UaBatchScriptOutput:
        return self._load(path, UaBatchScriptOutput)

    def load_structure(self, path: Path) -> UaStructureLoadResult:
        raw = self._read_json_object(path)
        try:
            return UaStructureLoadResult(
                output=UaStructureScriptOutput.model_validate(raw),
                warnings=(),
            )
        except ValidationError as exc:
            self._raise_on_path_violation(exc, path)
        return self._quarantine_structure(raw, path)

    def build(
        self,
        *,
        inventory: FileInventory,
        import_output: UaImportScriptOutput,
        batch_output: UaBatchScriptOutput,
        structure_outputs: tuple[
            tuple[int, UaStructureScriptOutput],
            ...,
        ],
        warnings: tuple[UaWarning, ...],
    ) -> UaAnalysisResult:
        approved = {item.path: item.size_lines for item in inventory.files}
        approved_paths = set(approved)
        self._validate_imports(import_output, approved_paths)
        self._validate_batches(batch_output, approved_paths)
        structure_rows = self._validate_structures(
            structure_outputs,
            approved,
        )

        imports = tuple(
            sorted(
                (
                    UaImportRow(source_file=source, target_file=target)
                    for source, targets in import_output.import_map.items()
                    for target in targets
                ),
                key=lambda item: (item.source_file, item.target_file),
            )
        )
        try:
            symbols, calls, resources, endpoints, projection_warnings = (
                project_structure_rows(
                    structure_rows,
                    approved,
                )
            )
        except ValidationError as exc:
            # Backstop for any inbound/contract-model parity gap: an
            # entry the gate accepted but the rows reject must fail
            # typed, never leak a raw pydantic error to the adapters.
            raise UaAnalysisError(
                "ua_result_invalid",
                "UA structural rows failed contract validation",
            ) from exc

        analyzed = sum(item.files_analyzed for _, item in structure_outputs)
        completions = tuple(
            UaBatchCompletion(
                batchIndex=batch_index,
                scriptCompleted=output.script_completed,
                outputPresent=True,
                filesAnalyzed=output.files_analyzed,
            )
            for batch_index, output in structure_outputs
        )
        return UaAnalysisResult(
            schema_version="systograph-ua-result/v1",
            status="completed",
            structural=UaStructuralResult(
                imports=imports,
                symbols=symbols,
                calls=calls,
                resources=resources,
                endpoints=endpoints,
            ),
            semantic=None,
            # The contract caps warnings at 100; overflow is truncated
            # rather than failing the result it is warning about.
            # Evidence-loss records (projection corrections, quarantine
            # drops) lead so stage chatter is what truncation discards.
            warnings=(*projection_warnings, *warnings)[:100],
            stats=UaAnalysisStats(
                filesScanned=import_output.stats.files_scanned,
                filesWithImports=import_output.stats.files_with_imports,
                totalEdges=import_output.stats.total_edges,
                totalBatches=batch_output.total_batches,
                algorithm=batch_output.algorithm,
                filesAnalyzed=analyzed,
                batchCompletion=completions,
            ),
            extra={},
        )

    def _load(
        self,
        path: Path,
        model: type[UaScriptModelT],
    ) -> UaScriptModelT:
        if not path.is_file():
            raise UaAnalysisError(
                "ua_output_missing",
                f"Required UA output is missing: {path.name}",
            )
        try:
            return model.model_validate_json(path.read_text(encoding="utf-8"))
        except ValidationError as exc:
            code = (
                "ua_path_not_approved"
                if any(
                    _PATH_VIOLATION_MARKER in error["msg"]
                    for error in exc.errors()
                )
                else "ua_result_invalid"
            )
            raise UaAnalysisError(
                code,
                f"UA output failed validation: {path.name}",
            ) from exc
        except (OSError, UnicodeError) as exc:
            raise UaAnalysisError(
                "ua_result_invalid",
                f"UA output failed validation: {path.name}",
            ) from exc

    def _read_json_object(self, path: Path) -> dict[str, object]:
        if not path.is_file():
            raise UaAnalysisError(
                "ua_output_missing",
                f"Required UA output is missing: {path.name}",
            )
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise UaAnalysisError(
                "ua_result_invalid",
                f"UA output failed validation: {path.name}",
            ) from exc
        if not isinstance(raw, dict):
            raise UaAnalysisError(
                "ua_result_invalid",
                f"UA output failed validation: {path.name}",
            )
        return raw

    def _raise_on_path_violation(
        self,
        exc: ValidationError,
        path: Path,
    ) -> None:
        if any(
            _PATH_VIOLATION_MARKER in error["msg"] for error in exc.errors()
        ):
            raise UaAnalysisError(
                "ua_path_not_approved",
                f"UA output failed validation: {path.name}",
            ) from exc

    def _quarantine_structure(
        self,
        raw: dict[str, object],
        path: Path,
    ) -> UaStructureLoadResult:
        warnings: list[UaWarning] = []
        cleaned = dict(raw)
        results = raw.get("results")
        if isinstance(results, list):
            cleaned["results"] = [
                self._quarantine_entries(row, warnings) for row in results
            ]
        try:
            output = UaStructureScriptOutput.model_validate(cleaned)
        except ValidationError as exc:
            raise UaAnalysisError(
                "ua_result_invalid",
                f"UA output failed validation: {path.name}",
            ) from exc
        return UaStructureLoadResult(output=output, warnings=tuple(warnings))

    def _quarantine_entries(
        self,
        row: object,
        warnings: list[UaWarning],
    ) -> object:
        # Only entries inside a structurally sound file row are eligible
        # for quarantine; anything else falls through to the strict
        # revalidation above and stays fatal.
        if not isinstance(row, dict):
            return row
        cleaned = dict(row)
        for key, model in _STRUCTURE_ENTRY_MODELS.items():
            entries = row.get(key)
            if not isinstance(entries, list):
                continue
            kept: list[object] = []
            for index, entry in enumerate(entries):
                try:
                    model.model_validate(entry)
                except ValidationError:
                    warnings.append(
                        UaWarning(
                            stage=_VALIDATE_STRUCTURE_STAGE,
                            message=(
                                f"quarantined invalid {key} entry "
                                f"#{index + 1} in {row.get('path')}"
                            )[:2048],
                        )
                    )
                    continue
                kept.append(entry)
            cleaned[key] = kept
        return cleaned

    def _validate_imports(
        self,
        output: UaImportScriptOutput,
        approved: set[str],
    ) -> None:
        if not output.script_completed:
            raise UaAnalysisError("ua_stage_incomplete", "Import stage failed")
        if set(output.import_map) != approved:
            raise UaAnalysisError(
                "ua_path_not_approved",
                "Import map does not match approved inventory",
            )
        targets = {
            target
            for values in output.import_map.values()
            for target in values
        }
        if not targets.issubset(approved):
            raise UaAnalysisError(
                "ua_path_not_approved",
                "Import map contains an unapproved path",
            )
        edge_count = sum(len(values) for values in output.import_map.values())
        with_imports = sum(
            bool(values) for values in output.import_map.values()
        )
        if (
            output.stats.files_scanned != len(approved)
            or output.stats.total_edges != edge_count
            or output.stats.files_with_imports != with_imports
        ):
            raise UaAnalysisError(
                "ua_stats_mismatch",
                "Import statistics do not match typed output",
            )

    def _validate_batches(
        self,
        output: UaBatchScriptOutput,
        approved: set[str],
    ) -> None:
        paths = [item.path for batch in output.batches for item in batch.files]
        if (
            output.total_files != len(approved)
            or output.total_batches != len(output.batches)
            or len(paths) != len(set(paths))
            or set(paths) != approved
        ):
            raise UaAnalysisError(
                "ua_batch_mismatch",
                "Batch output does not cover approved inventory exactly once",
            )

    def _validate_structures(
        self,
        outputs: tuple[tuple[int, UaStructureScriptOutput], ...],
        approved: dict[str, int],
    ) -> tuple[UaStructureFile, ...]:
        rows: list[UaStructureFile] = []
        for _, output in outputs:
            if (
                not output.script_completed
                or output.files_skipped
                or output.files_analyzed != len(output.results)
            ):
                raise UaAnalysisError(
                    "ua_stage_incomplete",
                    "Structure stage did not complete every file",
                )
            rows.extend(output.results)
        paths = [row.path for row in rows]
        if len(paths) != len(set(paths)) or set(paths) != set(approved):
            raise UaAnalysisError(
                "ua_path_not_approved",
                "Structure output does not match approved inventory",
            )
        return tuple(rows)
