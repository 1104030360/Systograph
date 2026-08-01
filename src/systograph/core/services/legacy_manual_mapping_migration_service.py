from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
)
from systograph.core.providers.local_json_state_errors import (
    ProjectStateBusyError,
)
from systograph.core.providers.local_json_state_storage import (
    LocalJsonStateStorage,
)
from systograph.core.services.manual_mapping_support import digest
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

LEGACY_MAPPING_MIGRATION_VERSION = (
    "legacy-extension-to-capability-candidate/v1"
)


class LegacyManualMappingType(StrEnum):
    NEW_EXTENSION = "new_extension_component"


class LegacyManualMappingDTO(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_id: str
    mapping_id: str
    mapping_digest: str
    mapping_type: LegacyManualMappingType
    decision: ManualMappingDecision
    source_unmapped_id: str | None = None
    source_file: str | None = None
    observed_kind: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reason: str | None = None
    extension_id: str | None = None
    extension_name: str | None = None
    extension_kind: str | None = None
    extension_edges: list[dict[str, str]] = Field(default_factory=list)
    proposal_id: str | None = None
    decision_source: str = "manual"
    audit_metadata: dict[str, str] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class LegacyMappingMigrationItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mapping_id: str
    status: Literal[
        "converted",
        "already_migrated",
        "requires_manual_review",
        "failed",
    ]
    input_digest: str
    output_digest: str | None = None
    quarantine_ref: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None


class LegacyMappingMigrationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["legacy-mapping-migration-report/v1"] = (
        "legacy-mapping-migration-report/v1"
    )
    migration_version: str = LEGACY_MAPPING_MIGRATION_VERSION
    status: Literal[
        "dry_run",
        "complete",
        "requires_manual_review",
        "partial_requires_retry",
    ]
    scanned: int
    converted: int
    already_migrated: int
    requires_manual_review: int
    failed: int
    # Rows retired to the quarantine bag by an earlier run and still
    # awaiting a human decision. Defaulted rather than required so that
    # reading back a report emitted before this field existed still
    # parses; `_report` always supplies it.
    unresolved_quarantined: int = 0
    cutover_blocked: bool
    items: list[LegacyMappingMigrationItem] = Field(default_factory=list)


class LegacyManualMappingMigrationService:
    def __init__(
        self,
        state_root: Path,
        *,
        clock: Callable[[], datetime] | None = None,
        lock_timeout: float = 5.0,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._storage = LocalJsonStateStorage(
            state_root,
            lock_timeout=lock_timeout,
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._masking = masking_service or SecretMaskingService()

    def migrate(self, *, apply: bool) -> LegacyMappingMigrationReport:
        candidates = self._candidates()
        items: list[LegacyMappingMigrationItem] = []
        by_project: dict[str, list[tuple[Path, dict[str, object]]]] = {}
        for path, payload in candidates:
            project_id = payload.get("project_id")
            if not isinstance(project_id, str):
                items.append(self._failed_item(payload, path))
                continue
            by_project.setdefault(project_id, []).append((path, payload))

        for project_id in sorted(by_project):
            project_candidates = by_project[project_id]
            if apply:
                try:
                    with self._storage.project_lock(project_id):
                        items.extend(
                            self._migrate_project(
                                project_candidates,
                                apply=True,
                            )
                        )
                except (ProjectStateBusyError, ValueError):
                    items.extend(
                        self._project_failure_items(project_candidates)
                    )
            else:
                items.extend(
                    self._migrate_project(project_candidates, apply=False)
                )
        return self._report(
            items,
            apply=apply,
            unresolved_quarantined=self._unresolved_quarantined(),
        )

    def _unresolved_quarantined(self) -> int:
        """Count rows retired to the bag that still owe a human decision.

        The quarantine bag IS the durable requires-manual-review record.
        Once `_retire_original` moves a row out of `mappings/`, no later
        run can rediscover it as a candidate, so gating on this run's item
        counts alone would let `cutover_blocked` fall back to False while
        a human still owes that row a decision — and the CLI exit code is
        machine-consumed. Operators clear the gate by resolving and
        removing the quarantined files (retention policy documented in
        MODEL-CONTRACT, Stage E).

        Only `*.original.json` counts. The sibling `*.legacy.json` payload
        copy is also written for rows that converted *cleanly* but had
        their `extension_edges` dropped
        (`legacy_extension_edges_quarantined`), so counting that suffix
        would hold the gate shut on a fully successful migration.

        The whole bag is scanned, not just the projects scanned this run:
        after a retire there are no candidates left to scope by, which is
        exactly the case this gate exists to cover. Rows quarantined
        before retiring existed still have their original in `mappings/`,
        so the per-run arm catches them on the next run regardless.
        """
        bag = self._storage.root / "migration-quarantine"
        if not bag.exists():
            return 0
        return len(list(bag.glob("*/*.original.json")))

    def _candidates(self) -> list[tuple[Path, dict[str, object]]]:
        if not self._storage.projects_root.exists():
            return []
        result: list[tuple[Path, dict[str, object]]] = []
        for path in sorted(
            self._storage.projects_root.glob("*/mappings/*.json")
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                result.append((path, {}))
                continue
            if not isinstance(payload, dict):
                result.append((path, {}))
                continue
            audit = payload.get("audit_metadata")
            migrated = (
                isinstance(audit, dict)
                and audit.get("legacy_mapping_migration_version")
                == LEGACY_MAPPING_MIGRATION_VERSION
            )
            if (
                payload.get("mapping_type")
                == LegacyManualMappingType.NEW_EXTENSION.value
                or migrated
            ):
                result.append((path, payload))
        return result

    def _migrate_project(
        self,
        candidates: list[tuple[Path, dict[str, object]]],
        *,
        apply: bool,
    ) -> list[LegacyMappingMigrationItem]:
        return [
            self._migrate_one(path, payload, apply=apply)
            for path, payload in candidates
        ]

    def _migrate_one(
        self,
        path: Path,
        payload: dict[str, object],
        *,
        apply: bool,
    ) -> LegacyMappingMigrationItem:
        input_digest = digest(payload)
        audit = payload.get("audit_metadata")
        if (
            isinstance(audit, dict)
            and audit.get("legacy_mapping_migration_version")
            == LEGACY_MAPPING_MIGRATION_VERSION
        ):
            return LegacyMappingMigrationItem(
                mapping_id=str(payload.get("mapping_id", "mapping:unknown")),
                status="already_migrated",
                input_digest=str(
                    audit.get("legacy_payload_digest", input_digest)
                ),
                output_digest=digest(payload),
            )
        try:
            legacy = LegacyManualMappingDTO.model_validate(payload)
        except ValidationError:
            return self._failed_item(payload, path)

        complete = all(
            value is not None and value.strip()
            for value in (
                legacy.extension_id,
                legacy.extension_name,
                legacy.extension_kind,
            )
        )
        quarantine_ref = (
            self._quarantine_ref(input_digest)
            if legacy.extension_edges or not complete
            else None
        )
        if not complete:
            if apply:
                ref = quarantine_ref or self._quarantine_ref(input_digest)
                try:
                    self._backup(legacy, payload, input_digest)
                    self._quarantine(legacy, payload, input_digest, ref)
                    self._retire_original(legacy, path, ref)
                except OSError:
                    return LegacyMappingMigrationItem(
                        mapping_id=legacy.mapping_id,
                        status="failed",
                        input_digest=input_digest,
                        quarantine_ref=quarantine_ref,
                        error_code="legacy_mapping_migration_failed",
                    )
            return LegacyMappingMigrationItem(
                mapping_id=legacy.mapping_id,
                status="requires_manual_review",
                input_digest=input_digest,
                quarantine_ref=quarantine_ref,
            )

        converted = self._convert(
            legacy,
            input_digest=input_digest,
            quarantine_ref=quarantine_ref,
        )
        output_digest = digest(converted.model_dump(mode="json"))
        warnings = (
            ["legacy_extension_edges_quarantined"]
            if legacy.extension_edges
            else []
        )
        if apply:
            try:
                self._backup(legacy, payload, input_digest)
                if quarantine_ref is not None:
                    self._quarantine(
                        legacy,
                        payload,
                        input_digest,
                        quarantine_ref,
                    )
                self._storage.write_model(path, converted)
            except OSError:
                return LegacyMappingMigrationItem(
                    mapping_id=legacy.mapping_id,
                    status="failed",
                    input_digest=input_digest,
                    quarantine_ref=quarantine_ref,
                    warnings=warnings,
                    error_code="legacy_mapping_migration_failed",
                )
        return LegacyMappingMigrationItem(
            mapping_id=legacy.mapping_id,
            status="converted",
            input_digest=input_digest,
            output_digest=output_digest,
            quarantine_ref=quarantine_ref,
            warnings=warnings,
        )

    def _convert(
        self,
        legacy: LegacyManualMappingDTO,
        *,
        input_digest: str,
        quarantine_ref: str | None,
    ) -> ManualMapping:
        audit = dict(legacy.audit_metadata)
        audit.update(
            {
                "legacy_mapping_migration_version": (
                    LEGACY_MAPPING_MIGRATION_VERSION
                ),
                "legacy_payload_digest": input_digest,
            }
        )
        if quarantine_ref is not None:
            audit["quarantine_ref"] = quarantine_ref
        draft = ManualMappingCreate(
            project_id=legacy.project_id,
            mapping_type=(ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE),
            decision=legacy.decision,
            source_unmapped_id=legacy.source_unmapped_id,
            source_file=legacy.source_file,
            observed_kind=legacy.observed_kind,
            evidence_ids=list(legacy.evidence_ids),
            reason=(
                self._masking.mask_text(legacy.reason)
                if legacy.reason is not None
                else None
            ),
            capability_candidate_id=legacy.extension_id,
            capability_candidate_name=legacy.extension_name,
            capability_candidate_kind=legacy.extension_kind,
            proposal_id=legacy.proposal_id,
            decision_source=legacy.decision_source,
            audit_metadata=audit,
        )
        return ManualMapping(
            **draft.model_dump(mode="python"),
            mapping_id=legacy.mapping_id,
            mapping_digest=digest(draft.model_dump(mode="json")),
            created_at=legacy.created_at,
            updated_at=self._clock().isoformat().replace("+00:00", "Z"),
        )

    def _backup(
        self,
        legacy: LegacyManualMappingDTO,
        payload: dict[str, object],
        input_digest: str,
    ) -> None:
        token = input_digest.removeprefix("sha256:")[:16]
        directory = (
            self._storage.root
            / "migration-backups"
            / self._storage.segment(legacy.project_id)
        )
        path = directory / (
            f"{self._storage.segment(legacy.mapping_id)}.{token}.legacy.json"
        )
        if not path.exists():
            self._storage.write_json(path, payload, mode=0o600)
        index_path = directory / "index.json"
        entries: list[dict[str, str]] = []
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if isinstance(index, dict) and isinstance(
                index.get("entries"), list
            ):
                entries = [
                    entry
                    for entry in index["entries"]
                    if isinstance(entry, dict)
                    and all(
                        isinstance(entry.get(key), str)
                        for key in (
                            "mapping_id",
                            "input_digest",
                            "backup_ref",
                        )
                    )
                ]
        entry = {
            "mapping_id": legacy.mapping_id,
            "input_digest": input_digest,
            "backup_ref": f"backup:{token}",
        }
        if entry not in entries:
            entries.append(entry)
        index_payload = {
            "migration_version": LEGACY_MAPPING_MIGRATION_VERSION,
            "entries": sorted(
                entries,
                key=lambda item: (item["mapping_id"], item["input_digest"]),
            ),
        }
        self._storage.write_json(index_path, index_payload, mode=0o600)

    def _quarantine(
        self,
        legacy: LegacyManualMappingDTO,
        payload: dict[str, object],
        input_digest: str,
        quarantine_ref: str,
    ) -> None:
        path = self._quarantine_file(legacy, quarantine_ref, "legacy")
        if not path.exists():
            self._storage.write_json(
                path,
                {
                    "migration_version": LEGACY_MAPPING_MIGRATION_VERSION,
                    "input_digest": input_digest,
                    "payload": payload,
                },
                mode=0o600,
            )

    def _retire_original(
        self,
        legacy: LegacyManualMappingDTO,
        path: Path,
        quarantine_ref: str,
    ) -> None:
        """Move an unconverted legacy row out of the active mappings glob.

        A row that cannot be converted keeps its legacy shape, and
        `projects/<p>/mappings/*.json` is the glob that
        `LocalJsonProjectRepository.list_for_project` reads as
        `ManualMapping`. Leaving the original in place therefore fails the
        whole project's mapping listing closed with `StateCorruptionError`
        — one unconverted row takes down every flow that lists mappings.

        Provenance chain after this move (files owner-only `0600`; the
        directories stay `0755`, as `_backup` / `_quarantine` already
        leave them):
        - `migration-backups/<project>/<mapping>.<token>.legacy.json`
          plus an `index.json` entry — re-serialized payload (`_backup`)
        - `migration-quarantine/<project>/<mapping>.<token>.legacy.json`
          — re-serialized payload wrapped with migration version and
          input digest (`_quarantine`)
        - `migration-quarantine/<project>/<mapping>.<token>.original.json`
          — the file moved here, byte-for-byte as the operator held it.

        Both copies above are re-serializations (sorted keys, normalized
        indent), so the moved file is the only byte-exact evidence of the
        pre-migration state; that is why this retires the original by
        moving it rather than unlinking it. The row is quarantined, never
        skipped in place: a per-file skip would be the silent dual-read
        this cutover exists to remove.

        `os.chmod` only moves the read-only bit on Windows, matching the
        pre-existing `_backup` / `_quarantine` behaviour.
        """
        target = self._quarantine_file(legacy, quarantine_ref, "original")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            # Same token means the same input digest, so the evidence
            # already banked here IS this row — and it is byte-exact,
            # while whatever is back in `mappings/` can only be a
            # normalized restore of it. Never clobber the stronger copy;
            # drop the source instead. (`_backup` / `_quarantine` guard
            # their writes the same way.)
            path.unlink()
            return
        os.chmod(path, 0o600)
        os.replace(path, target)

    def _quarantine_file(
        self,
        legacy: LegacyManualMappingDTO,
        quarantine_ref: str,
        suffix: str,
    ) -> Path:
        token = quarantine_ref.removeprefix("quarantine:")
        return (
            self._storage.root
            / "migration-quarantine"
            / self._storage.segment(legacy.project_id)
            / (
                f"{self._storage.segment(legacy.mapping_id)}."
                f"{token}.{suffix}.json"
            )
        )

    @staticmethod
    def _quarantine_ref(input_digest: str) -> str:
        return "quarantine:" + input_digest.removeprefix("sha256:")[:16]

    @staticmethod
    def _failed_item(
        payload: dict[str, object],
        path: Path,
    ) -> LegacyMappingMigrationItem:
        """Report a row that could not be read as a legacy mapping.

        Unlike `requires_manual_review` rows these are deliberately NOT
        retired out of `mappings/`: without a validated DTO there is no
        trustworthy project/mapping id to build a provenance-bearing
        quarantine path from, and no backup has been written, so moving
        the file would put state where nothing can trace it back. They
        therefore keep failing `list_for_project` closed until resolved —
        `partial_requires_retry` means exactly "retry". Deciding custody
        for unparseable rows is a Plan 15 hand-off, not this migration's
        call.
        """
        del path
        return LegacyMappingMigrationItem(
            mapping_id=str(payload.get("mapping_id", "mapping:unknown")),
            status="failed",
            input_digest=digest(payload),
            error_code="legacy_mapping_migration_failed",
        )

    @classmethod
    def _project_failure_items(
        cls,
        candidates: list[tuple[Path, dict[str, object]]],
    ) -> list[LegacyMappingMigrationItem]:
        return [
            cls._failed_item(payload, path) for path, payload in candidates
        ]

    @staticmethod
    def _report(
        items: list[LegacyMappingMigrationItem],
        *,
        apply: bool,
        unresolved_quarantined: int,
    ) -> LegacyMappingMigrationReport:
        counts = {
            status: sum(item.status == status for item in items)
            for status in (
                "converted",
                "already_migrated",
                "requires_manual_review",
                "failed",
            )
        }
        status: Literal[
            "dry_run",
            "complete",
            "requires_manual_review",
            "partial_requires_retry",
        ]
        if not apply:
            status = "dry_run"
        elif counts["failed"]:
            status = "partial_requires_retry"
        elif counts["requires_manual_review"]:
            status = "requires_manual_review"
        else:
            status = "complete"
        return LegacyMappingMigrationReport(
            status=status,
            scanned=len(items),
            converted=counts["converted"],
            already_migrated=counts["already_migrated"],
            requires_manual_review=counts["requires_manual_review"],
            failed=counts["failed"],
            unresolved_quarantined=unresolved_quarantined,
            # Strict per-run rule (any requires_manual_review or failed row
            # blocks) OR'd with the durable bag, so the gate cannot reopen
            # on a later run while retired rows remain unresolved.
            cutover_blocked=bool(
                counts["requires_manual_review"]
                or counts["failed"]
                or unresolved_quarantined
            ),
            items=items,
        )
