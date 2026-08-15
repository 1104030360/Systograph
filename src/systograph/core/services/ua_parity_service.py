from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.scan import (
    ProjectScanResult,
    ProviderScanResult,
    ScanFact,
)
from systograph.core.models.system_map import Evidence
from systograph.core.models.ua_analysis import UaAnalysisResult
from systograph.core.models.ua_parity import (
    ParityFactComparison,
    ParityFactProjection,
    ParityFactProvenance,
    ParityRuleMapping,
    UaParityContractError,
    UaParityReport,
)
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.ast_construction_output import (
    EXTERNAL_IMPORT_RULE_ID,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.rule_catalog_loader import (
    ENDPOINT_VENDOR_FACT_KIND,
    RuleCatalogLoader,
)
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter
from systograph.core.services.understand_anything_analysis_service import (
    UnderstandAnythingAnalysisService,
)

_EvidenceKey = tuple[
    str | None,
    str | None,
    str,
    str | None,
    str | None,
]

LegacyProviderName = Literal[
    "config_parse",
    "docker_compose",
    "dependency_manifest",
    "code_pattern",
    "ast_construction",
]
LEGACY_PROVIDER_ALIASES: dict[str, LegacyProviderName] = {
    "config": "config_parse",
    "config_parse": "config_parse",
    "docker_compose": "docker_compose",
    "dependency_manifest": "dependency_manifest",
    "code_pattern": "code_pattern",
    "ast_construction": "ast_construction",
}


class UaAnalysisService(Protocol):
    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult: ...


class UaParityService:
    def __init__(
        self,
        *,
        ua_analysis_service: UaAnalysisService | None = None,
    ) -> None:
        self._filesystem = FilesystemProvider()
        self._legacy_scan = ProjectScanService()
        self._ua_analysis = (
            ua_analysis_service or UnderstandAnythingAnalysisService()
        )
        self._ua_adapter = UaStructuralAdapter()
        code_rules = RuleCatalogLoader().load_default_code_pattern_rules()
        mappings = tuple(
            ParityRuleMapping(
                legacy_rule_id=rule.rule_id,
                ua_rule_id=rule.ua_rule_id,
            )
            for rule in code_rules
            if rule.ua_rule_id is not None
        )
        self._code_pattern_rule_ids = frozenset(
            rule.rule_id for rule in code_rules
        )
        self._mapping_by_legacy = {
            item.legacy_rule_id: item for item in mappings
        }
        self._mapping_by_ua = {item.ua_rule_id: item for item in mappings}

    def run(self, project_root: Path) -> UaParityReport:
        inventory = self._filesystem.build_inventory(project_root)
        legacy_result = self._legacy_scan.scan_inventory(
            project_root,
            inventory=inventory,
        )
        analysis = self._ua_analysis.analyze(project_root, inventory)
        return self.compare_existing(
            inventory=inventory,
            legacy_scan=legacy_result,
            ua_scan=self._ua_adapter.adapt(analysis),
        )

    def compare_existing(
        self,
        *,
        inventory: FileInventory,
        legacy_scan: ProjectScanResult,
        ua_scan: ProviderScanResult,
    ) -> UaParityReport:
        legacy_facts = self._legacy_provenances(legacy_scan)
        ua_facts = self._ua_provenances(ua_scan)
        comparisons = self._compare_facts(legacy_facts, ua_facts)
        return UaParityReport.from_one_shot(
            inventory,
            comparisons,
        )

    def _legacy_provenances(
        self,
        result: ProjectScanResult,
    ) -> tuple[ParityFactProvenance, ...]:
        provenances: list[ParityFactProvenance] = []
        evidence_index = self._evidence_index(result.evidence)
        for fact in result.facts:
            if (
                fact.rule_id == EXTERNAL_IMPORT_RULE_ID
                or fact.kind == ENDPOINT_VENDOR_FACT_KIND
            ):
                # Package identity import facts and endpoint identity
                # URL facts have no legacy<->UA rule mapping: parity
                # measures the code-pattern rule families only.
                continue
            default_provider = self._legacy_provider(fact)
            matches = self._matching_evidence(fact, evidence_index)
            if not matches:
                raise UaParityContractError(
                    f"{default_provider} fact has no evidence: {fact.file}"
                )
            by_provider: dict[LegacyProviderName, list[Evidence]] = {}
            for evidence in matches:
                provider: LegacyProviderName = (
                    "ast_construction"
                    if evidence.id.startswith("evidence:ast-construction:")
                    else default_provider
                )
                by_provider.setdefault(provider, []).append(evidence)
            for provider, provider_evidence in sorted(by_provider.items()):
                provenances.append(
                    ParityFactProvenance.from_projection(
                        ParityFactProjection(
                            source="legacy",
                            provider=provider,
                            fact=fact,
                            evidence=tuple(provider_evidence),
                        )
                    )
                )
        return tuple(sorted(provenances, key=lambda fact: fact.sort_key))

    def _ua_provenances(
        self,
        result: ProviderScanResult,
    ) -> tuple[ParityFactProvenance, ...]:
        provenances: list[ParityFactProvenance] = []
        evidence_index = self._evidence_index(result.evidence)
        for fact in result.facts:
            matches = self._matching_evidence(fact, evidence_index)
            provenances.append(
                ParityFactProvenance.from_projection(
                    ParityFactProjection(
                        source="ua",
                        provider="understand_anything",
                        fact=fact,
                        evidence=matches,
                    )
                )
            )
        return tuple(sorted(provenances, key=lambda fact: fact.sort_key))

    def _legacy_provider(self, fact: ScanFact) -> LegacyProviderName:
        if fact.provider is not None:
            provider = LEGACY_PROVIDER_ALIASES.get(fact.provider)
            if provider is None:
                raise UaParityContractError(
                    f"unexpected legacy provider: {fact.provider}"
                )
            return provider
        rule_id = fact.rule_id
        if rule_id in self._code_pattern_rule_ids:
            return "code_pattern"
        if rule_id is not None and rule_id.startswith("dependency_"):
            return "dependency_manifest"
        if rule_id is not None and rule_id.startswith("docker_"):
            return "docker_compose"
        if rule_id is not None and rule_id.startswith("config_"):
            return "config_parse"
        raise UaParityContractError(
            f"cannot resolve legacy provider for rule_id: {rule_id}"
        )

    def _evidence_index(
        self,
        evidence_items: list[Evidence],
    ) -> dict[_EvidenceKey, list[Evidence]]:
        # Facts and evidence both number in the tens of thousands on
        # real repositories; a per-fact linear scan is quadratic.
        index: dict[_EvidenceKey, list[Evidence]] = {}
        for evidence in evidence_items:
            key = (
                evidence.file,
                evidence.path,
                evidence.kind,
                evidence.rule_id,
                evidence.value,
            )
            index.setdefault(key, []).append(evidence)
        return index

    def _matching_evidence(
        self,
        fact: ScanFact,
        evidence_index: dict[_EvidenceKey, list[Evidence]],
    ) -> tuple[Evidence, ...]:
        matches = evidence_index.get(
            (fact.file, fact.path, fact.kind, fact.rule_id, fact.value),
            [],
        )
        return tuple(sorted(matches, key=lambda evidence: evidence.id))

    def _compare_facts(
        self,
        legacy_facts: tuple[ParityFactProvenance, ...],
        ua_facts: tuple[ParityFactProvenance, ...],
    ) -> tuple[ParityFactComparison, ...]:
        comparisons: list[ParityFactComparison] = []
        matched_ua: set[int] = set()
        # First-in-order lookup tables reproducing has_same_location():
        # a legacy fact with line numbers matches on exact line spans; a
        # legacy fact without them matches line-less UA facts by path.
        by_lines: dict[tuple[object, ...], int] = {}
        by_path: dict[tuple[object, ...], int] = {}
        for index, ua in enumerate(ua_facts):
            lines_key = (
                ua.rule_id,
                ua.kind,
                ua.file,
                ua.line_start,
                ua.line_end,
            )
            by_lines.setdefault(lines_key, index)
            if ua.line_start is None:
                path_key = (ua.rule_id, ua.kind, ua.file, ua.path)
                by_path.setdefault(path_key, index)
        for legacy in legacy_facts:
            mapping = self._mapping_by_legacy.get(legacy.rule_id)
            if mapping is None:
                comparisons.append(
                    ParityFactComparison(
                        classification="intentionally_degraded",
                        legacy=legacy,
                    )
                )
                continue
            if legacy.line_start is not None:
                ua_index = by_lines.get(
                    (
                        mapping.ua_rule_id,
                        legacy.kind,
                        legacy.file,
                        legacy.line_start,
                        legacy.line_end,
                    )
                )
            else:
                ua_index = by_path.get(
                    (
                        mapping.ua_rule_id,
                        legacy.kind,
                        legacy.file,
                        legacy.path,
                    )
                )
            if ua_index is None:
                comparisons.append(
                    ParityFactComparison(
                        classification="missing",
                        mapping=mapping,
                        legacy=legacy,
                    )
                )
                continue
            matched_ua.add(ua_index)
            comparisons.append(
                ParityFactComparison(
                    classification="equivalent",
                    mapping=mapping,
                    legacy=legacy,
                    ua=ua_facts[ua_index],
                )
            )
        comparisons.extend(
            ParityFactComparison(
                classification="extra",
                mapping=self._mapping_by_ua.get(ua.rule_id),
                ua=ua,
            )
            for index, ua in enumerate(ua_facts)
            if index not in matched_ua
        )
        return tuple(sorted(comparisons, key=lambda item: item.sort_key))
