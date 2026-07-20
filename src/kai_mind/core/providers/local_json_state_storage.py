from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from filelock import FileLock, Timeout
from pydantic import BaseModel, ValidationError

from kai_mind.core.providers.local_json_state_errors import (
    InvalidStateIdError,
    ProjectStateBusyError,
    StateCorruptionError,
)

StateModel = TypeVar("StateModel", bound=BaseModel)
_SAFE_ID = re.compile(r"^[a-z][a-z0-9-]*:[A-Za-z0-9._-]+$")


class LocalJsonStateStorage:
    def __init__(self, state_root: Path, *, lock_timeout: float) -> None:
        self.root = state_root.resolve()
        self.projects_root = self.root / "projects"
        self._lock_timeout = lock_timeout

    @contextmanager
    def project_lock(self, project_id: str) -> Iterator[None]:
        directory = self.project_dir(project_id)
        directory.mkdir(parents=True, exist_ok=True)
        lock = FileLock(
            str(directory / ".project.lock"),
            timeout=self._lock_timeout,
        )
        try:
            with lock:
                yield
        except Timeout as exc:
            raise ProjectStateBusyError("project_state_busy") from exc

    def write_model(self, path: Path, model: BaseModel) -> None:
        self.write_json(path, model.model_dump(mode="json"))

    def write_json(
        self,
        path: Path,
        payload: object,
        *,
        mode: int | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(self.serialize(payload))
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)

    @staticmethod
    def serialize(payload: object) -> str:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def read_model(
        self,
        path: Path,
        model_type: type[StateModel],
    ) -> StateModel | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return model_type.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise StateCorruptionError(
                f"invalid local state: {path.name}"
            ) from exc

    def find_model(
        self,
        directory_name: str,
        segment: str,
        model_type: type[StateModel],
        *,
        nested_name: str | None = None,
    ) -> StateModel | None:
        if not self.projects_root.exists():
            return None
        for project_dir in sorted(self.projects_root.iterdir()):
            path = project_dir / directory_name / segment
            if nested_name is not None:
                path /= nested_name
            item = self.read_model(path, model_type)
            if item is not None:
                return item
        return None

    def project_file(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    def mapping_file(self, project_id: str, mapping_id: str) -> Path:
        return (
            self.project_dir(project_id)
            / "mappings"
            / f"{self.segment(mapping_id)}.json"
        )

    def snapshot_file(self, project_id: str, scan_id: str) -> Path:
        return (
            self.project_dir(project_id)
            / "scans"
            / self.segment(scan_id)
            / "snapshot.json"
        )

    def build_file(self, project_id: str, build_id: str) -> Path:
        return (
            self.project_dir(project_id)
            / "builds"
            / self.segment(build_id)
            / "manifest.json"
        )

    def project_dir(self, project_id: str) -> Path:
        self.validate_id(project_id, "project")
        return self.projects_root / self.segment(project_id)

    @staticmethod
    def segment(identity: str) -> str:
        return identity.replace(":", "_")

    @staticmethod
    def validate_id(identity: str, prefix: str) -> None:
        if (
            ".." in identity
            or not _SAFE_ID.fullmatch(identity)
            or not identity.startswith(prefix + ":")
        ):
            raise InvalidStateIdError(f"invalid {prefix} id")
