from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from systograph.core.models.ua_analysis import UaAnalysisResult
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.ua_sidecar_runtime import (
    UaProcessOutput,
    UnderstandAnythingSubprocessRunner,
)
from systograph.core.services.understand_anything_analysis_service import (
    KEEP_WORK_DIR_ENV,
    UnderstandAnythingAnalysisService,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
UA_SCRIPT_ROOT = (
    REPO_ROOT
    / "ref-opensource"
    / "Understand-Anything"
    / "understand-anything-plugin"
    / "skills"
    / "understand"
)


class RecordingRealRunner:
    def __init__(self) -> None:
        self._delegate = UnderstandAnythingSubprocessRunner()
        self.script_paths: list[Path] = []

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
    ) -> UaProcessOutput:
        self.script_paths.append(Path(command[1]).resolve())
        return self._delegate.run(command, cwd=cwd)


@dataclass(frozen=True, slots=True)
class SidecarExecutionEvidence:
    project_root: Path
    first: UaAnalysisResult
    second: UaAnalysisResult
    script_paths: tuple[Path, ...]
    digest_before: str
    digest_after: str


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        kind = "file" if path.is_file() else "directory"
        digest.update(f"{kind}:{relative}\0".encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


@pytest.fixture(scope="module")
def real_sidecar_execution(
    tmp_path_factory: pytest.TempPathFactory,
) -> SidecarExecutionEvidence:
    project_root = tmp_path_factory.mktemp("ua-target")
    (project_root / "app.py").write_text(
        "def answer():\n    return 42\n",
        encoding="utf-8",
    )
    work_dir_parent = tmp_path_factory.mktemp("ua-work")
    inventory = FilesystemProvider().build_inventory(project_root)
    runner = RecordingRealRunner()
    service = UnderstandAnythingAnalysisService(
        runner=runner,
        work_dir_parent=work_dir_parent,
    )
    digest_before = _tree_digest(project_root)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.delenv(KEEP_WORK_DIR_ENV, raising=False)
        first = service.analyze(project_root, inventory)
        second = service.analyze(project_root, inventory)

    return SidecarExecutionEvidence(
        project_root=project_root,
        first=first,
        second=second,
        script_paths=tuple(runner.script_paths),
        digest_before=digest_before,
        digest_after=_tree_digest(project_root),
    )


def test_real_pinned_node_executes_only_the_three_approved_stages(
    real_sidecar_execution: SidecarExecutionEvidence,
) -> None:
    # Given: the default preflight accepted the pinned UA checkout and Node.
    expected_once = (
        UA_SCRIPT_ROOT / "extract-import-map.mjs",
        UA_SCRIPT_ROOT / "compute-batches.mjs",
        UA_SCRIPT_ROOT / "extract-structure.mjs",
    )

    # When: the real sidecar executes the fixture twice.
    executed = real_sidecar_execution.script_paths

    # Then: each run uses only the approved three-stage sequence.
    assert executed == (*expected_once, *expected_once)
    assert all(path.name != "scan-project.mjs" for path in executed)


def test_real_sidecar_keeps_the_target_tree_read_only(
    real_sidecar_execution: SidecarExecutionEvidence,
) -> None:
    # Given / When: two real sidecar runs analyze the same target tree.
    evidence = real_sidecar_execution

    # Then: path/content digest is unchanged and no UA work tree appears there.
    assert evidence.digest_after == evidence.digest_before
    assert not (evidence.project_root / ".understand-anything").exists()


def test_real_zero_edge_result_is_deterministic_across_reruns(
    real_sidecar_execution: SidecarExecutionEvidence,
) -> None:
    # Given / When: a single-file fixture has no internal dependency edge.
    first = real_sidecar_execution.first
    second = real_sidecar_execution.second

    # Then: zero edges complete successfully and typed output is byte-stable.
    assert first.status == "completed"
    assert first.stats.total_edges == 0
    assert first.structural.imports == ()
    assert first.model_dump_json() == second.model_dump_json()
