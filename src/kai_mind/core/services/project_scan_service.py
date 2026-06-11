"""Aggregate provider-local scanner facts into one raw scan result."""

from __future__ import annotations

import logging
import re
import traceback
from collections.abc import Iterable
from pathlib import Path
from typing import Literal, Protocol

from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.models.scan import (
    ParseIssue,
    ProjectScanResult,
    ProviderScanResult,
    ScanFact,
    SkippedFileSummary,
)
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.providers.code_pattern_provider import CodePatternProvider
from kai_mind.core.providers.config_parse_provider import ConfigParseProvider
from kai_mind.core.providers.dependency_manifest_provider import (
    DependencyManifestProvider,
)
from kai_mind.core.providers.docker_compose_provider import (
    DockerComposeProvider,
)
from kai_mind.core.providers.filesystem_provider import FilesystemProvider
from kai_mind.core.services.logging_service import safe_log_event
from kai_mind.core.services.path_safety_service import redact_local_paths
from kai_mind.core.services.secret_masking_service import SecretMaskingService

PROJECT_SCAN_STAGE: Literal["project_scan"] = "project_scan"
PROVIDER_FAILURE_RULE_ID = "project_scan_provider_failed"
PROVIDER_FAILURE_FILE = "$provider"
logger = logging.getLogger(__name__)


class FilesystemInventoryProvider(Protocol):
    """Builds the shared inventory consumed by scanner providers."""

    def build_inventory(self, project_root: Path) -> FileInventory:
        """Return deterministic project inventory."""
        ...


class ScanResultProvider(Protocol):
    """Collects provider-local raw scan results from a shared inventory."""

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        """Return provider-local facts, evidence and issues."""
        ...


class InventoryPolicyOverlay(Protocol):
    """Transforms inventory before provider collection for one scan run."""

    def apply(
        self,
        *,
        project_root: Path,
        inventory: FileInventory,
    ) -> FileInventory:
        """Return inventory after applying controlled policy decisions."""
        ...


class ProjectScanService:
    """Coordinate deterministic scanner providers and aggregate raw facts."""

    def __init__(
        self,
        *,
        filesystem_provider: FilesystemInventoryProvider | None = None,
        providers: Iterable[ScanResultProvider] | None = None,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._filesystem_provider = filesystem_provider or FilesystemProvider()
        self._providers = (
            tuple(providers)
            if providers is not None
            else (
                ConfigParseProvider(),
                DockerComposeProvider(),
                DependencyManifestProvider(),
                CodePatternProvider(),
            )
        )
        self._masking_service = masking_service or SecretMaskingService()

    def scan(
        self,
        project_root: Path,
        *,
        inventory_policy: InventoryPolicyOverlay | None = None,
    ) -> ProjectScanResult:
        """Run providers and return raw facts without final mapping."""

        inventory = self._filesystem_provider.build_inventory(project_root)
        if inventory_policy is not None:
            inventory = inventory_policy.apply(
                project_root=project_root,
                inventory=inventory,
            )
        result = ProjectScanResult(
            skipped_files=self._skipped_file_summaries(inventory.skipped),
            warnings=list(inventory.warnings),
            files_scanned=inventory.files_scanned,
            files_skipped=inventory.files_skipped,
        )

        for provider in self._providers:
            provider_name = self._provider_name(provider)
            try:
                provider_result = provider.collect(inventory)
            except Exception as exc:  # noqa: BLE001
                self._log_provider_failure(provider_name, exc)
                result.issues.append(
                    self._provider_failure_issue(provider_name, exc)
                )
                result.warnings.append(f"{provider_name} failed")
                continue

            result.facts.extend(
                self._fact_with_provider(fact, provider_name)
                for fact in provider_result.facts
            )
            result.evidence.extend(provider_result.evidence)
            result.issues.extend(provider_result.issues)

        result.facts = self._dedupe_facts(result.facts)
        result.evidence = self._dedupe_evidence(result.evidence)
        result.issues = sorted(result.issues, key=self._issue_sort_key)
        return result

    def _provider_failure_issue(
        self,
        provider_name: str,
        exc: Exception,
    ) -> ParseIssue:
        message = redact_local_paths(
            self._masking_service.mask_text(
                f"Provider failed during project scan: {exc}"
            )
        )
        return ParseIssue(
            provider=provider_name,
            scan_stage=PROJECT_SCAN_STAGE,
            file=PROVIDER_FAILURE_FILE,
            message=message,
            rule_id=PROVIDER_FAILURE_RULE_ID,
        )

    def _log_provider_failure(
        self,
        provider_name: str,
        exc: Exception,
    ) -> None:
        traceback_frames = self._format_traceback_frames(exc)
        safe_log_event(
            logger,
            logging.ERROR,
            "provider_scan_failed",
            stage=PROJECT_SCAN_STAGE,
            provider=provider_name,
            exception_type=exc.__class__.__name__,
            frame_count=len(traceback_frames),
            masking_service=self._masking_service,
        )

    def _format_traceback_frames(
        self,
        exc: Exception,
    ) -> list[traceback.FrameSummary]:
        frames = traceback.extract_tb(exc.__traceback__)
        return list(frames)

    def _fact_with_provider(
        self,
        fact: ScanFact,
        provider_name: str,
    ) -> ScanFact:
        if fact.rule_id is not None or fact.provider is not None:
            return fact
        return fact.model_copy(update={"provider": provider_name})

    def _dedupe_facts(self, facts: Iterable[ScanFact]) -> list[ScanFact]:
        by_key: dict[
            tuple[str, str, str, str | None, str | None],
            ScanFact,
        ] = {}
        for fact in facts:
            key = (fact.kind, fact.file, fact.path, fact.value, fact.rule_id)
            by_key.setdefault(key, fact)
        return sorted(by_key.values(), key=self._fact_sort_key)

    def _dedupe_evidence(
        self,
        evidence_items: Iterable[Evidence],
    ) -> list[Evidence]:
        by_id: dict[str, Evidence] = {}
        for item in evidence_items:
            by_id.setdefault(item.id, item)
        return sorted(by_id.values(), key=self._evidence_sort_key)

    def _provider_name(self, provider: ScanResultProvider) -> str:
        explicit_name = getattr(provider, "name", None)
        if isinstance(explicit_name, str) and explicit_name:
            return explicit_name
        return self._to_snake_case(provider.__class__.__name__)

    def _to_snake_case(self, name: str) -> str:
        stem = name.removesuffix("Provider")
        with_underscores = re.sub(r"(?<!^)(?=[A-Z])", "_", stem)
        return with_underscores.lower()

    def _skipped_file_summaries(
        self,
        skipped_files: Iterable[object],
    ) -> list[SkippedFileSummary]:
        summaries = [
            SkippedFileSummary(
                path=str(getattr(item, "path", "")),
                reason=str(getattr(getattr(item, "reason", ""), "value", "")),
                size_bytes=getattr(item, "size_bytes", None),
            )
            for item in skipped_files
        ]
        return sorted(
            summaries,
            key=lambda item: (
                item.path,
                item.reason,
            ),
        )

    def _fact_sort_key(
        self,
        fact: ScanFact,
    ) -> tuple[str, str, str, str, str]:
        return (
            fact.kind,
            fact.file,
            fact.path,
            fact.rule_id or "",
            fact.value or "",
        )

    def _evidence_sort_key(
        self,
        evidence: Evidence,
    ) -> tuple[str, str, str, str, str]:
        return (
            evidence.file or "",
            evidence.path or "",
            evidence.rule_id or "",
            evidence.id,
            evidence.value or "",
        )

    def _issue_sort_key(
        self,
        issue: ParseIssue,
    ) -> tuple[str, str, str, str]:
        return (
            issue.provider,
            issue.scan_stage,
            issue.file,
            issue.message,
        )
