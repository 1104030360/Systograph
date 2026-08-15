from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from systograph.core.services.understand_anything_analysis_service import (
    KEEP_WORK_DIR_ENV,
    UnderstandAnythingAnalysisService,
)


class LifecycleProbeError(RuntimeError):
    pass


def _service(work_dir_parent: Path) -> UnderstandAnythingAnalysisService:
    return UnderstandAnythingAnalysisService(
        work_dir_parent=work_dir_parent,
    )


def test_work_directory_is_removed_after_normal_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: retention is disabled for a system-temporary UA work directory.
    monkeypatch.delenv(KEEP_WORK_DIR_ENV, raising=False)
    service = _service(tmp_path)

    # When: the work-directory context exits normally.
    with service._work_directory() as work_dir:
        captured_path = work_dir
        (work_dir / "stage-output.json").write_text("{}", encoding="utf-8")

    # Then: the directory and its transient output are removed.
    assert not captured_path.exists()


def test_work_directory_is_removed_after_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: retention is disabled and a stage will fail inside the context.
    monkeypatch.delenv(KEEP_WORK_DIR_ENV, raising=False)
    service = _service(tmp_path)
    captured_path: Path | None = None

    # When: execution leaves the context through an exception.
    with pytest.raises(LifecycleProbeError):
        with service._work_directory() as work_dir:
            captured_path = work_dir
            (work_dir / "partial-output.json").write_text(
                "{}",
                encoding="utf-8",
            )
            raise LifecycleProbeError

    # Then: failure does not leak the transient directory.
    assert captured_path is not None
    assert not captured_path.exists()


def test_keep_work_directory_environment_retains_stage_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: explicit diagnostic retention is enabled for this process.
    monkeypatch.setenv(KEEP_WORK_DIR_ENV, "1")
    service = _service(tmp_path)

    # When: the work-directory context exits normally.
    with service._work_directory() as work_dir:
        retained_path = work_dir
        marker = work_dir / "stage-output.json"
        marker.write_text("{}", encoding="utf-8")

    # Then: the directory and stage output remain available for diagnosis.
    try:
        assert retained_path.is_dir()
        assert marker.read_text(encoding="utf-8") == "{}"
    finally:
        shutil.rmtree(retained_path, ignore_errors=True)
