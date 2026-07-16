from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pathspec import GitIgnoreSpec

from kai_mind.core.models.errors import InventoryEnumerationError
from kai_mind.core.services.path_safety_service import (
    normalize_project_relative_path,
)


@dataclass(frozen=True, slots=True)
class InventoryIgnoreRules:
    base_path: str
    spec: GitIgnoreSpec


class InventoryIgnoreService:
    def load_for_directory(
        self,
        directory: Path,
        *,
        project_root: Path,
    ) -> InventoryIgnoreRules | None:
        path = directory / ".gitignore"
        if not path.is_file():
            return None
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise InventoryEnumerationError() from exc
        base_path = (
            ""
            if directory == project_root
            else normalize_project_relative_path(
                directory,
                project_root=project_root,
            )
        )
        return InventoryIgnoreRules(
            base_path=base_path,
            spec=GitIgnoreSpec.from_lines(lines),
        )

    def rules_to_directory(
        self,
        project_root: Path,
        directory: Path,
    ) -> tuple[InventoryIgnoreRules, ...]:
        relative = directory.relative_to(project_root)
        current = project_root
        rules: list[InventoryIgnoreRules] = []
        loaded = self.load_for_directory(current, project_root=project_root)
        if loaded is not None:
            rules.append(loaded)
        for part in relative.parts:
            current /= part
            loaded = self.load_for_directory(
                current,
                project_root=project_root,
            )
            if loaded is not None:
                rules.append(loaded)
        return tuple(rules)

    def is_ignored(
        self,
        path: str,
        rules: tuple[InventoryIgnoreRules, ...],
    ) -> bool:
        ignored = False
        for rule_set in rules:
            scoped = self._relative_to_base(path, rule_set.base_path)
            if scoped is None:
                continue
            result = rule_set.spec.check_file(scoped)
            if result.include is not None:
                ignored = result.include
        return ignored

    def _relative_to_base(self, path: str, base_path: str) -> str | None:
        if not base_path:
            return path
        prefix = f"{base_path}/"
        if not path.startswith(prefix):
            return None
        return path.removeprefix(prefix)
