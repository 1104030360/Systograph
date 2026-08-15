from __future__ import annotations

import hashlib
import json
from typing import Final

from systograph.core.models.evidence_kind import AssessmentEvidenceKind
from systograph.core.models.scan import (
    ParseIssue,
    ProviderScanResult,
    ScanFact,
)
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    ImportStructuralFact,
    SourceSpan,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import Evidence
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaCallRow,
    UaEndpointRow,
    UaImportRow,
    UaResourceRow,
    UaSymbolRow,
)
from systograph.core.services.rule_catalog_loader import RuleCatalogLoader

PROVIDER_NAME: Final = "understand_anything"
IMPORT_RULE_ID: Final = "ua_import_internal"
SYMBOL_RULE_PREFIX: Final = "ua_symbol_"
GENERIC_CALL_RULE_ID: Final = "ua_call_hint_static"
RESOURCE_RULE_ID: Final = "ua_endpoint_resource"
ENDPOINT_RULE_ID: Final = "ua_endpoint_route"
WARNING_RULE_ID: Final = "ua_structural_warning"


class UaStructuralAdapter:
    def __init__(self) -> None:
        rules = RuleCatalogLoader().load_default_code_pattern_rules()
        self._call_rule_by_symbol = {
            rule.symbol: (rule.fact_kind, rule.ua_rule_id)
            for rule in rules
            if rule.symbol is not None and rule.ua_rule_id is not None
        }

    def adapt(self, analysis: UaAnalysisResult) -> ProviderScanResult:
        result = ProviderScanResult()
        for import_row in analysis.structural.imports:
            self._append_import(result, import_row)
        for symbol_row in analysis.structural.symbols:
            self._append_symbol(result, symbol_row)
        for call_row in analysis.structural.calls:
            self._append_call(result, call_row)
        for resource_row in analysis.structural.resources:
            self._append_resource(result, resource_row)
        for endpoint_row in analysis.structural.endpoints:
            self._append_endpoint(result, endpoint_row)
        result.issues.extend(
            ParseIssue(
                provider=PROVIDER_NAME,
                scan_stage="ua_structural_scan",
                file="ua-analysis-result.json",
                message=f"{warning.stage}: {warning.message}",
                rule_id=WARNING_RULE_ID,
            )
            for warning in analysis.warnings
        )
        return result

    @staticmethod
    def _append_import(
        result: ProviderScanResult,
        row: UaImportRow,
    ) -> None:
        span = SourceSpan(file=row.source_file)
        fact = ScanFact(
            kind="import",
            file=row.source_file,
            path=f"imports[{row.target_file}]",
            value=row.target_file,
            rule_id=IMPORT_RULE_ID,
            provider=PROVIDER_NAME,
        )
        result.facts.append(fact)
        result.evidence.append(_evidence(fact, span, "indirect"))
        result.structural_facts.append(
            ImportStructuralFact(
                identity_namespace="ua_import",
                import_scope="internal",
                module=row.target_file,
                span=span,
            )
        )

    @staticmethod
    def _append_symbol(
        result: ProviderScanResult,
        row: UaSymbolRow,
    ) -> None:
        span = SourceSpan(
            file=row.file,
            line_start=row.line_start,
            line_end=row.line_end,
        )
        fact = ScanFact(
            kind="symbol",
            file=row.file,
            path=f"symbols[{row.kind}:{row.name}]",
            value=row.name,
            rule_id=f"{SYMBOL_RULE_PREFIX}{row.kind}",
            provider=PROVIDER_NAME,
        )
        result.facts.append(fact)
        result.evidence.append(_evidence(fact, span, "direct"))
        result.structural_facts.append(
            SymbolStructuralFact(
                identity_namespace="ua_symbol",
                symbol=row.name,
                symbol_kind=row.kind,
                span=span,
            )
        )

    def _append_call(
        self,
        result: ProviderScanResult,
        row: UaCallRow,
    ) -> None:
        matched = self._call_rule_by_symbol.get(row.callee)
        if matched is None:
            kind = "call_hint"
            rule_id = GENERIC_CALL_RULE_ID
        else:
            kind, rule_id = matched
        span = SourceSpan(
            file=row.file,
            line_start=row.line_number,
            line_end=row.line_number,
        )
        fact = ScanFact(
            kind=kind,
            file=row.file,
            path=f"calls[{row.caller}->{row.callee}]",
            value=row.callee,
            rule_id=rule_id,
            provider=PROVIDER_NAME,
        )
        result.facts.append(fact)
        result.evidence.append(_evidence(fact, span, "direct"))
        result.structural_facts.append(
            CallStructuralFact(
                identity_namespace="ua_call_hint",
                caller=row.caller,
                callee=row.callee,
                span=span,
            )
        )

    @staticmethod
    def _append_resource(
        result: ProviderScanResult,
        row: UaResourceRow,
    ) -> None:
        span = SourceSpan(
            file=row.file,
            line_start=row.line_start,
            line_end=row.line_end,
        )
        fact = ScanFact(
            kind="resource",
            file=row.file,
            path=f"resources[{row.kind}:{row.name}]",
            value=row.name,
            rule_id=RESOURCE_RULE_ID,
            provider=PROVIDER_NAME,
        )
        hint: AssessmentEvidenceKind = (
            "direct" if span.line_start is not None else "indirect"
        )
        result.facts.append(fact)
        result.evidence.append(_evidence(fact, span, hint))

    @staticmethod
    def _append_endpoint(
        result: ProviderScanResult,
        row: UaEndpointRow,
    ) -> None:
        span = SourceSpan(
            file=row.file,
            line_start=row.line_start,
            line_end=row.line_end,
        )
        method = row.method or "*"
        fact = ScanFact(
            kind="endpoint",
            file=row.file,
            path=f"endpoints[{method}:{row.path}]",
            value=row.path,
            rule_id=ENDPOINT_RULE_ID,
            provider=PROVIDER_NAME,
        )
        hint: AssessmentEvidenceKind = (
            "direct" if span.line_start is not None else "indirect"
        )
        result.facts.append(fact)
        result.evidence.append(_evidence(fact, span, hint))


def _evidence(
    fact: ScanFact,
    span: SourceSpan,
    hint: AssessmentEvidenceKind,
) -> Evidence:
    identity = json.dumps(
        (
            fact.kind,
            fact.file,
            fact.path,
            fact.value,
            fact.rule_id,
            span.line_start,
            span.line_end,
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()
    return Evidence(
        id=f"evidence:ua:sha256:{digest}",
        kind=fact.kind,
        file=fact.file,
        path=fact.path,
        value=fact.value,
        rule_id=fact.rule_id,
        line_start=span.line_start,
        line_end=span.line_end,
        evidence_kind_hint=hint,
    )
