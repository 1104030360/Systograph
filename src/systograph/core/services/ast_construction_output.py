from __future__ import annotations

import hashlib
from typing import Literal

from systograph.core.models.evidence_kind import AssessmentEvidenceKind
from systograph.core.models.scan import (
    ParseIssue,
    ProviderScanResult,
    ScanFact,
)
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
    SourceSpan,
    StructuralFact,
    SymbolStructuralFact,
)
from systograph.core.models.system_map import Evidence
from systograph.core.services.ast_construction_types import (
    ImportBinding,
    ParsedPythonFile,
    RuntimeCall,
)
from systograph.core.services.path_safety_service import redact_local_paths
from systograph.core.services.rule_catalog_loader import CodePatternRule
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

PROVIDER_NAME = "ast_construction"
SCAN_STAGE: Literal["code_pattern_scan"] = "code_pattern_scan"
EXTERNAL_IMPORT_RULE_ID = "ast_external_import"
EXTERNAL_IMPORT_FACT_KIND = "external_import_declaration"
CALL_IDENTITY_NAMESPACE = "ast_construction_call"
IMPORT_IDENTITY_NAMESPACE = "ua_external_import"


class AstConstructionOutput:
    def __init__(
        self,
        *,
        rules_by_symbol: dict[str, CodePatternRule],
        masking_service: SecretMaskingService,
        max_snippet_chars: int,
    ) -> None:
        self.rules_by_symbol = rules_by_symbol
        self.known_symbols = frozenset(rules_by_symbol)
        self.masking_service = masking_service
        self.max_snippet_chars = max_snippet_chars

    def emit_imports(
        self,
        result: ProviderScanResult,
        parsed: ParsedPythonFile,
        bindings: list[ImportBinding],
    ) -> None:
        for binding_index, binding in enumerate(bindings):
            if binding.is_star:
                self.append_issue(
                    result,
                    parsed.relative_path,
                    "ast_construction_unresolved_star_import",
                    "Wildcard import cannot be resolved deterministically",
                    line=binding.line_start,
                )
            if not binding.external:
                continue
            span = SourceSpan(
                file=parsed.relative_path,
                line_start=binding.line_start,
                line_end=binding.line_end,
            )
            result.structural_facts.append(
                ImportStructuralFact(
                    identity_namespace=IMPORT_IDENTITY_NAMESPACE,
                    import_scope="external",
                    module=binding.module,
                    symbol=binding.symbol,
                    alias=binding.alias,
                    span=span,
                )
            )
            value = binding.module
            if binding.symbol is not None:
                value = f"{value}.{binding.symbol}"
            # The fact mirrors the evidence tuple exactly so
            # EvidenceLookup joins them for the package identity layer
            # in ComponentBridgeRegistry.
            result.facts.append(
                ScanFact(
                    kind=EXTERNAL_IMPORT_FACT_KIND,
                    file=parsed.relative_path,
                    path=f"line[{binding.line_start}]",
                    value=value,
                    rule_id=EXTERNAL_IMPORT_RULE_ID,
                )
            )
            result.evidence.append(
                self.evidence(
                    parsed,
                    kind=EXTERNAL_IMPORT_FACT_KIND,
                    rule_id=EXTERNAL_IMPORT_RULE_ID,
                    value=value,
                    line_start=binding.line_start,
                    line_end=binding.line_end,
                    hint="indirect",
                    identity_context=f"import:{binding_index}",
                )
            )

    def emit_direct_call(
        self,
        result: ProviderScanResult,
        parsed: ParsedPythonFile,
        runtime_call: RuntimeCall,
        symbol: str,
    ) -> None:
        rule = self.rules_by_symbol[symbol]
        line_start = runtime_call.node.lineno
        line_end = runtime_call.node.end_lineno or line_start
        result.facts.append(
            ScanFact(
                kind=rule.fact_kind,
                file=parsed.relative_path,
                path=f"line[{line_start}]",
                value=symbol,
                rule_id=rule.rule_id,
            )
        )
        result.structural_facts.append(
            CallStructuralFact(
                identity_namespace=CALL_IDENTITY_NAMESPACE,
                caller=runtime_call.caller,
                callee=symbol,
                span=SourceSpan(
                    file=parsed.relative_path,
                    line_start=line_start,
                    line_end=line_end,
                ),
            )
        )
        result.evidence.append(
            self.evidence(
                parsed,
                kind=rule.fact_kind,
                rule_id=rule.rule_id,
                value=symbol,
                line_start=line_start,
                line_end=line_end,
                hint="direct",
                identity_context=f"call:{runtime_call.node.col_offset}",
            )
        )

    def evidence(
        self,
        parsed: ParsedPythonFile,
        *,
        kind: str,
        rule_id: str,
        value: str,
        line_start: int,
        line_end: int,
        hint: AssessmentEvidenceKind,
        identity_context: str = "",
    ) -> Evidence:
        raw_snippet = "\n".join(
            parsed.source.splitlines()[line_start - 1 : line_end]
        )
        snippet = self.masking_service.mask_text(raw_snippet)
        if len(snippet) > self.max_snippet_chars:
            end = max(0, self.max_snippet_chars - len("...[truncated]"))
            snippet = f"{snippet[:end]}...[truncated]"
        digest = hashlib.sha256(
            (
                f"{parsed.relative_path}|{line_start}|{rule_id}|{value}|"
                f"{identity_context}"
            ).encode()
        ).hexdigest()[:20]
        return Evidence(
            id=f"evidence:ast-construction:{digest}",
            kind=kind,
            file=parsed.relative_path,
            path=f"line[{line_start}]",
            value=value,
            rule_id=rule_id,
            line_start=line_start,
            line_end=line_end,
            snippet=snippet,
            evidence_kind_hint=hint,
        )

    def append_issue(
        self,
        result: ProviderScanResult,
        file: str,
        rule_id: str,
        message: str,
        *,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        safe_message = redact_local_paths(
            self.masking_service.mask_text(message)
        )
        result.issues.append(
            ParseIssue(
                provider=PROVIDER_NAME,
                scan_stage=SCAN_STAGE,
                file=file,
                message=safe_message,
                rule_id=rule_id,
                line=line,
                column=column,
            )
        )

    @staticmethod
    def sort_result(result: ProviderScanResult) -> None:
        result.facts.sort(
            key=lambda item: (
                item.file,
                item.path,
                item.rule_id or "",
                item.value or "",
            )
        )
        result.structural_facts.sort(key=_structural_fact_key)
        result.evidence.sort(
            key=lambda item: (
                item.file or "",
                item.line_start or 0,
                item.rule_id or "",
                item.id,
            )
        )
        result.issues.sort(
            key=lambda item: (item.file, item.line or 0, item.rule_id)
        )


def _structural_fact_key(fact: StructuralFact) -> tuple[str, int, str, str]:
    if isinstance(fact, FactoryInferenceStructuralFact):
        span = fact.call_span
    elif isinstance(
        fact,
        (CallStructuralFact, ImportStructuralFact, SymbolStructuralFact),
    ):
        span = fact.span
    return (
        span.file,
        span.line_start or 0,
        fact.fact_type,
        fact.stable_id,
    )
