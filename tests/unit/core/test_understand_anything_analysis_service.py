from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.filesystem import (
    FileCategory,
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from systograph.core.services.understand_anything_analysis_service import (
    UaAnalysisError,
    UaProcessOutput,
    UaRuntimePaths,
    UnderstandAnythingAnalysisService,
)

SHA256_A = "sha256:" + "a" * 64
SHA256_B = "sha256:" + "b" * 64


class ReadyPreflight:
    def __init__(self, paths: UaRuntimePaths) -> None:
        self.paths = paths
        self.calls = 0

    def validate(self) -> UaRuntimePaths:
        self.calls += 1
        return self.paths


class ScriptFixtureRunner:
    def __init__(
        self,
        *,
        dangling_import: bool = False,
        zero_edges: bool = False,
        tree_sitter_failure: bool = False,
        omit_structure_output: bool = False,
        garbage_call_graph_entry: bool = False,
        stderr_lines: int = 0,
    ) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.dangling_import = dangling_import
        self.zero_edges = zero_edges
        self.tree_sitter_failure = tree_sitter_failure
        self.omit_structure_output = omit_structure_output
        self.garbage_call_graph_entry = garbage_call_graph_entry
        self.stderr_lines = stderr_lines

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
    ) -> UaProcessOutput:
        self.calls.append(command)
        script_name = Path(command[1]).name
        if script_name == "extract-import-map.mjs":
            target = (
                "../escape.py" if self.dangling_import else "src/helper.py"
            )
            app_imports = [] if self.zero_edges else [target]
            self._write(
                Path(command[3]),
                {
                    "scriptCompleted": True,
                    "stats": {
                        "filesScanned": 2,
                        "filesWithImports": 0 if self.zero_edges else 1,
                        "totalEdges": 0 if self.zero_edges else 1,
                    },
                    "importMap": {
                        "src/app.py": app_imports,
                        "src/helper.py": [],
                    },
                },
            )
            return UaProcessOutput(stdout="", stderr=self._chatter())
        if script_name == "compute-batches.mjs":
            output_path = self._option_path(command, "--output=")
            self._write(
                output_path,
                {
                    "schemaVersion": 1,
                    "algorithm": "louvain",
                    "totalFiles": 2,
                    "totalBatches": 1,
                    "exportsByPath": {},
                    "batches": [
                        {
                            "batchIndex": 1,
                            "files": [
                                {
                                    "path": "src/app.py",
                                    "language": "python",
                                    "fileCategory": "code",
                                    "sizeLines": 4,
                                },
                                {
                                    "path": "src/helper.py",
                                    "language": "python",
                                    "fileCategory": "code",
                                    "sizeLines": 2,
                                },
                            ],
                            "batchImportData": {
                                "src/app.py": ["src/helper.py"],
                                "src/helper.py": [],
                            },
                            "neighborMap": {},
                        }
                    ],
                },
            )
            return UaProcessOutput(stdout="", stderr=self._chatter())
        if script_name == "extract-structure.mjs":
            if not self.omit_structure_output:
                self._write(
                    Path(command[3]),
                    {
                        "scriptCompleted": True,
                        "filesAnalyzed": 2,
                        "filesSkipped": [],
                        "results": [
                            {
                                "path": "src/app.py",
                                "language": "python",
                                "fileCategory": "code",
                                "totalLines": 4,
                                "nonEmptyLines": 3,
                                "functions": [
                                    {
                                        "name": "main",
                                        "startLine": 1,
                                        "endLine": 4,
                                        "params": [],
                                    }
                                ],
                                "exports": [
                                    {
                                        "name": "main",
                                        "line": 1,
                                        "isDefault": False,
                                    }
                                ],
                                "callGraph": [
                                    {
                                        "caller": "main",
                                        "callee": "helper",
                                        "lineNumber": 3,
                                    },
                                    *(
                                        [
                                            {
                                                "caller": "main",
                                                "callee": "x" * 600,
                                                "lineNumber": 4,
                                            }
                                        ]
                                        if self.garbage_call_graph_entry
                                        else []
                                    ),
                                ],
                            },
                            {
                                "path": "src/helper.py",
                                "language": "python",
                                "fileCategory": "code",
                                "totalLines": 2,
                                "nonEmptyLines": 2,
                                "functions": [
                                    {
                                        "name": "helper",
                                        "startLine": 1,
                                        "endLine": 2,
                                        "params": [],
                                    }
                                ],
                            },
                        ],
                    },
                )
            marker = (
                "Warning: compute-batches: tree-sitter init failed"
                if self.tree_sitter_failure
                else self._chatter()
            )
            return UaProcessOutput(stdout="", stderr=marker)
        raise AssertionError(f"Unexpected script: {script_name}")

    def _chatter(self) -> str:
        return "\n".join(
            f"stage warning {index}" for index in range(self.stderr_lines)
        )

    def _option_path(
        self,
        command: tuple[str, ...],
        prefix: str,
    ) -> Path:
        return Path(
            next(
                item.removeprefix(prefix)
                for item in command
                if item.startswith(prefix)
            )
        )

    def _write(self, path: Path, payload: object) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )


def inventory(project_root: Path) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path="src/app.py",
                size_bytes=32,
                language="python",
                file_category=FileCategory.CODE,
                size_lines=4,
                content_fingerprint=SHA256_A,
            ),
            FileRecord(
                path="src/helper.py",
                size_bytes=16,
                language="python",
                file_category=FileCategory.CODE,
                size_lines=2,
                content_fingerprint=SHA256_B,
            ),
        ],
        final_inventory_digest=SHA256_A,
    )


def runtime_paths(tmp_path: Path) -> UaRuntimePaths:
    script_root = tmp_path / "ua"
    script_root.mkdir()
    paths = {
        name: script_root / name
        for name in (
            "extract-import-map.mjs",
            "compute-batches.mjs",
            "extract-structure.mjs",
        )
    }
    for path in paths.values():
        path.write_text("", encoding="utf-8")
    return UaRuntimePaths(
        node_executable=Path("/usr/bin/node"),
        script_root=script_root,
        extract_import_map=paths["extract-import-map.mjs"],
        compute_batches=paths["compute-batches.mjs"],
        extract_structure=paths["extract-structure.mjs"],
        core_dist=script_root / "dist" / "index.js",
    )


def test_analysis_uses_only_approved_inventory_and_cleans_work_dir(
    tmp_path: Path,
) -> None:
    # Given: an approved two-file inventory and deterministic script outputs.
    project_root = tmp_path / "project"
    project_root.mkdir()
    work_parent = tmp_path / "work"
    work_parent.mkdir()
    preflight = ReadyPreflight(runtime_paths(tmp_path))
    runner = ScriptFixtureRunner()
    service = UnderstandAnythingAnalysisService(
        preflight=preflight,
        runner=runner,
        work_dir_parent=work_parent,
    )

    # When: the sidecar analysis completes.
    result = service.analyze(project_root, inventory(project_root))

    # Then: no autonomous scanner or durable target write participates.
    assert result.status == "completed"
    assert result.semantic is None
    assert result.stats.files_scanned == 2
    assert result.stats.total_edges == 1
    assert result.stats.files_analyzed == 2
    assert result.structural.imports[0].source_file == "src/app.py"
    assert result.structural.calls[0].line_number == 3
    assert preflight.calls == 1
    assert len(runner.calls) == 3
    assert all("scan-project.mjs" not in call for call in runner.calls)
    assert list(work_parent.iterdir()) == []


def test_zero_import_edges_are_a_valid_completed_result(
    tmp_path: Path,
) -> None:
    # Given: a runner whose import phase reports a legal empty graph.
    runner = ScriptFixtureRunner(zero_edges=True)
    project_root = tmp_path / "project"
    project_root.mkdir()
    service = UnderstandAnythingAnalysisService(
        preflight=ReadyPreflight(runtime_paths(tmp_path)),
        runner=runner,
        work_dir_parent=tmp_path,
    )

    # When: the result has no repository topology edge.
    result = service.analyze(project_root, inventory(project_root))

    # Then: completion depends on typed stage integrity, not edge count.
    assert result.stats.total_edges == 0
    assert result.status == "completed"


def test_garbage_structure_entry_is_quarantined_not_fatal(
    tmp_path: Path,
) -> None:
    # Given: the structure stage emits one garbage callGraph entry next
    # to otherwise valid output.
    runner = ScriptFixtureRunner(garbage_call_graph_entry=True)
    project_root = tmp_path / "project"
    project_root.mkdir()
    service = UnderstandAnythingAnalysisService(
        preflight=ReadyPreflight(runtime_paths(tmp_path)),
        runner=runner,
        work_dir_parent=tmp_path,
    )

    # When: the sidecar analysis completes.
    result = service.analyze(project_root, inventory(project_root))

    # Then: the scan still completes on the valid entries and the drop
    # surfaces as a warning on the final result.
    assert result.status == "completed"
    assert [item.callee for item in result.structural.calls] == ["helper"]
    quarantine = [
        item for item in result.warnings if item.stage == "validate-structure"
    ]
    assert len(quarantine) == 1
    assert "callGraph" in quarantine[0].message
    assert "src/app.py" in quarantine[0].message


def test_quarantine_warning_survives_stderr_noise_at_the_cap(
    tmp_path: Path,
) -> None:
    # Given: stages spam enough stderr chatter to overflow the 100-warning
    # cap on their own, and one garbage entry is quarantined.
    runner = ScriptFixtureRunner(
        garbage_call_graph_entry=True,
        stderr_lines=60,
    )
    project_root = tmp_path / "project"
    project_root.mkdir()
    service = UnderstandAnythingAnalysisService(
        preflight=ReadyPreflight(runtime_paths(tmp_path)),
        runner=runner,
        work_dir_parent=tmp_path,
    )

    # When
    result = service.analyze(project_root, inventory(project_root))

    # Then: truncation drops chatter, never the evidence-loss record.
    assert len(result.warnings) <= 100
    assert any(item.stage == "validate-structure" for item in result.warnings)


@pytest.mark.parametrize(
    ("runner", "expected_code"),
    [
        (ScriptFixtureRunner(dangling_import=True), "ua_path_not_approved"),
        (ScriptFixtureRunner(omit_structure_output=True), "ua_output_missing"),
        (
            ScriptFixtureRunner(tree_sitter_failure=True),
            "ua_tree_sitter_unavailable",
        ),
    ],
)
def test_analysis_fails_closed_before_returning_partial_result(
    tmp_path: Path,
    runner: ScriptFixtureRunner,
    expected_code: str,
) -> None:
    # Given: one required sidecar invariant is broken.
    project_root = tmp_path / "project"
    project_root.mkdir()
    service = UnderstandAnythingAnalysisService(
        preflight=ReadyPreflight(runtime_paths(tmp_path)),
        runner=runner,
        work_dir_parent=tmp_path,
    )

    # When/Then: no partial result crosses the service boundary.
    with pytest.raises(UaAnalysisError) as exc_info:
        service.analyze(project_root, inventory(project_root))

    assert exc_info.value.code == expected_code
