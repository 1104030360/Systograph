from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from systograph.core.services.path_safety_service import redact_local_paths
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

EXPECTED_UA_PIN: Final = "73559a160645359c57be44c174935899dec9f9f2"
MINIMUM_NODE_MAJOR: Final = 20
DEFAULT_TIMEOUT_SECONDS: Final = 120.0
DEFAULT_OUTPUT_LIMIT: Final = 16_384


class UaAnalysisError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class UaRuntimePaths:
    node_executable: Path
    script_root: Path
    extract_import_map: Path
    compute_batches: Path
    extract_structure: Path
    core_dist: Path


@dataclass(frozen=True)
class UaProcessOutput:
    stdout: str
    stderr: str


class NodeRuntimePreflight:
    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        node_executable: Path | None = None,
        git_executable: str = "git",
    ) -> None:
        self._repo_root = (
            repo_root
            if repo_root is not None
            else Path(__file__).resolve().parents[4]
        )
        self._node_executable = node_executable
        self._git_executable = git_executable

    def validate(self) -> UaRuntimePaths:
        node = self._resolve_node()
        ua_root = self._repo_root / "ref-opensource" / "Understand-Anything"
        script_root = (
            ua_root / "understand-anything-plugin" / "skills" / "understand"
        )
        paths = UaRuntimePaths(
            node_executable=node,
            script_root=script_root,
            extract_import_map=script_root / "extract-import-map.mjs",
            compute_batches=script_root / "compute-batches.mjs",
            extract_structure=script_root / "extract-structure.mjs",
            core_dist=(
                ua_root
                / "understand-anything-plugin"
                / "packages"
                / "core"
                / "dist"
                / "index.js"
            ),
        )
        self._require_pin(ua_root)
        self._require_node_version(node)
        for path in (
            paths.extract_import_map,
            paths.compute_batches,
            paths.extract_structure,
            paths.core_dist,
        ):
            if not path.is_file() or not os.access(path, os.R_OK):
                raise UaAnalysisError(
                    "ua_runtime_not_ready",
                    f"Required UA runtime file is unavailable: {path.name}",
                )
        compute_source = paths.compute_batches.read_text(encoding="utf-8")
        if "--work-dir" not in compute_source:
            raise UaAnalysisError(
                "ua_patch_not_applied",
                "UA compute-batches work-dir patch is not applied",
            )
        return paths

    def _resolve_node(self) -> Path:
        candidate = self._node_executable
        if candidate is None:
            located = shutil.which("node")
            candidate = Path(located) if located is not None else None
        if (
            candidate is None
            or not candidate.is_file()
            or not os.access(candidate, os.X_OK)
        ):
            raise UaAnalysisError(
                "ua_node_missing",
                "Node runtime is unavailable",
            )
        return candidate

    def _require_pin(self, ua_root: Path) -> None:
        completed = self._run_preflight_command(
            (
                self._git_executable,
                "-C",
                str(ua_root),
                "rev-parse",
                "HEAD",
            ),
            code="ua_pin_unavailable",
        )
        if completed.stdout.strip() != EXPECTED_UA_PIN:
            raise UaAnalysisError(
                "ua_pin_mismatch",
                "UA submodule pin does not match the supported revision",
            )

    def _require_node_version(self, node: Path) -> None:
        completed = self._run_preflight_command(
            (str(node), "--version"),
            code="ua_node_version_unavailable",
        )
        raw = completed.stdout.strip().removeprefix("v")
        major_text = raw.partition(".")[0]
        if not major_text.isdigit() or int(major_text) < MINIMUM_NODE_MAJOR:
            raise UaAnalysisError(
                "ua_node_version_unsupported",
                f"Node {MINIMUM_NODE_MAJOR}+ is required",
            )

    def _run_preflight_command(
        self,
        command: tuple[str, ...],
        *,
        code: str,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise UaAnalysisError(code, "UA runtime preflight failed") from exc
        if completed.returncode != 0:
            raise UaAnalysisError(code, "UA runtime preflight failed")
        return completed


class UnderstandAnythingSubprocessRunner:
    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        output_limit: int = DEFAULT_OUTPUT_LIMIT,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._output_limit = output_limit
        self._masking_service = masking_service or SecretMaskingService()

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
    ) -> UaProcessOutput:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise UaAnalysisError(
                "ua_script_timeout",
                "UA script exceeded its execution deadline",
            ) from exc
        except OSError as exc:
            raise UaAnalysisError(
                "ua_script_unavailable",
                "UA script could not be started",
            ) from exc

        stdout = self._safe_output(completed.stdout)
        stderr = self._safe_output(completed.stderr)
        if completed.returncode != 0:
            detail = stderr or "no diagnostic output"
            raise UaAnalysisError(
                "ua_script_failed",
                f"UA script failed: {detail}",
            )
        return UaProcessOutput(stdout=stdout, stderr=stderr)

    def _safe_output(self, value: str) -> str:
        bounded = value[: self._output_limit]
        masked = self._masking_service.mask_text(bounded)
        return redact_local_paths(masked)
