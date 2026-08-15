from __future__ import annotations

from systograph.core.models.scan import ProviderScanResult, ScanFact
from systograph.core.models.structural_fact import (
    FactoryInferenceStructuralFact,
    SourceSpan,
)
from systograph.core.services.ast_construction_factory import (
    FactoryCandidate,
    FactoryResolver,
)
from systograph.core.services.ast_construction_factory_index import (
    FactoryCallSite,
    FactoryIndex,
)
from systograph.core.services.ast_construction_output import (
    AstConstructionOutput,
)

FACTORY_IDENTITY_NAMESPACE = "ast_factory_inference"


def emit_factory_inferences(
    result: ProviderScanResult,
    *,
    index: FactoryIndex,
    output: AstConstructionOutput,
) -> None:
    resolver = FactoryResolver(index, output.known_symbols)
    for call_site in index.call_sites:
        resolution = resolver.resolve(call_site.factory)
        for warning in sorted(resolution.warnings):
            output.append_issue(
                result,
                call_site.parsed.relative_path,
                warning,
                _warning_message(warning),
                line=call_site.runtime_call.node.lineno,
            )
        for candidate in resolution.candidates:
            _emit_candidate(result, call_site, candidate, output)


def _emit_candidate(
    result: ProviderScanResult,
    call_site: FactoryCallSite,
    candidate: FactoryCandidate,
    output: AstConstructionOutput,
) -> None:
    rule = output.rules_by_symbol[candidate.symbol]
    node = call_site.runtime_call.node
    line_start = node.lineno
    line_end = node.end_lineno or line_start
    result.facts.append(
        ScanFact(
            kind=rule.fact_kind,
            file=call_site.parsed.relative_path,
            path=f"line[{line_start}]",
            value=candidate.symbol,
            rule_id=rule.rule_id,
        )
    )
    result.structural_facts.append(
        FactoryInferenceStructuralFact(
            identity_namespace=FACTORY_IDENTITY_NAMESPACE,
            caller=call_site.runtime_call.caller,
            factory=call_site.factory,
            constructed_symbol=candidate.symbol,
            call_span=SourceSpan(
                file=call_site.parsed.relative_path,
                line_start=line_start,
                line_end=line_end,
            ),
            provenance=candidate.provenance,
        )
    )
    result.evidence.append(
        output.evidence(
            call_site.parsed,
            kind=rule.fact_kind,
            rule_id=rule.rule_id,
            value=candidate.symbol,
            line_start=line_start,
            line_end=line_end,
            hint="indirect",
            identity_context=(
                f"factory:{node.col_offset}:"
                + "|".join(
                    f"{step.factory}:{step.span.line_start}:{step.resolution}"
                    for step in candidate.provenance
                )
            ),
        )
    )


def _warning_message(rule_id: str) -> str:
    if rule_id == "ast_construction_factory_cycle":
        return "Factory inference stopped at a cycle"
    return "Factory inference stopped at the hop limit"
