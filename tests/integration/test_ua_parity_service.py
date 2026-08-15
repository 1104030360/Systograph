from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError
from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.filesystem import FileInventory
from systograph.core.models.ua_analysis import (
    UaAnalysisResult,
    UaAnalysisStats,
    UaCallRow,
    UaStructuralResult,
)
from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.ua_parity_service import UaParityService
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter


class FixedUaAnalysisService:
    def __init__(self, result: UaAnalysisResult) -> None:
        self._result = result
        self.calls: list[tuple[Path, FileInventory]] = []

    def analyze(
        self,
        project_root: Path,
        inventory: FileInventory,
    ) -> UaAnalysisResult:
        self.calls.append((project_root, inventory))
        return self._result


def _analysis(*calls: UaCallRow) -> UaAnalysisResult:
    return UaAnalysisResult(
        schema_version="systograph-ua-result/v1",
        status="completed",
        structural=UaStructuralResult(
            imports=(),
            symbols=(),
            calls=calls,
            resources=(),
            endpoints=(),
        ),
        semantic=None,
        warnings=(),
        stats=UaAnalysisStats(
            filesScanned=7,
            filesWithImports=0,
            totalEdges=0,
            totalBatches=1,
            algorithm="count-fallback",
            filesAnalyzed=7,
            batchCompletion=(),
        ),
        extra={},
    )


def _fixture_root() -> Path:
    return rag_project_fixture_path("basic_qdrant_ollama_rag")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        kind = "file" if path.is_file() else "directory"
        digest.update(f"{kind}:{relative}\0".encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def test_catalog_mirrors_classify_equivalent_facts_with_both_provenances() -> (
    None
):
    # Given: Plan 31's first parity fixture and catalog-resolved UA calls.
    analyzer = FixedUaAnalysisService(
        _analysis(
            UaCallRow(
                file="src/ingest.py",
                caller="ingest_documents",
                callee="qdrant_client.QdrantClient",
                line_number=7,
            ),
            UaCallRow(
                file="src/retriever.py",
                caller="retrieve_context",
                callee="qdrant_client.QdrantClient",
                line_number=13,
            ),
            UaCallRow(
                file="src/retriever.py",
                caller="retrieve_context",
                callee="client.search",
                line_number=15,
            ),
            UaCallRow(
                file="src/retriever.py",
                caller="retrieve_context",
                callee="ollama.embeddings",
                line_number=8,
            ),
        )
    )
    service = UaParityService(ua_analysis_service=analyzer)

    # When: the end-to-end parity harness runs all deterministic providers.
    report = service.run(_fixture_root())

    # Then: mirror pairs match by catalog identity and file/line provenance.
    equivalents = [
        item
        for item in report.comparisons
        if item.classification == "equivalent"
    ]
    assert report.schema_version == "systograph-ua-parity/v1"
    assert report.llm_mode == "disabled"
    assert report.summary.equivalent == 3
    assert report.summary.missing == 0
    assert len(analyzer.calls) == 1
    assert len(equivalents) == 3
    mirror_pairs = {
        "code_pattern_vector_store_qdrant": (
            "ua_call_hint_vector_store_qdrant"
        ),
        "code_pattern_embedding_ollama": "ua_call_hint_embedding_ollama",
    }
    for item in equivalents:
        assert item.legacy is not None
        assert item.ua is not None
        assert item.legacy.source == "legacy"
        assert item.legacy.provider == "code_pattern"
        assert item.ua.source == "ua"
        assert item.ua.provider == "understand_anything"
        assert item.legacy.rule_id is not None
        assert item.ua.rule_id == mirror_pairs[item.legacy.rule_id]
        assert item.legacy.file == item.ua.file
        assert item.legacy.line_start == item.ua.line_start
        assert item.legacy.evidence_ids
        assert item.ua.evidence_ids
    assert {
        item.legacy.rule_id for item in equivalents if item.legacy is not None
    } == set(mirror_pairs)

    degraded_dependencies = [
        item
        for item in report.comparisons
        if item.legacy is not None
        and item.legacy.provider == "dependency_manifest"
    ]
    assert degraded_dependencies
    assert all(
        item.classification == "intentionally_degraded"
        for item in degraded_dependencies
    )
    assert any(
        item.classification == "extra"
        and item.ua is not None
        and item.ua.rule_id == "ua_call_hint_static"
        for item in report.comparisons
    )


def test_mapped_fact_at_a_different_line_is_missing_and_extra() -> None:
    # Given: one mapped UA fact that does not share a legacy evidence line.
    analyzer = FixedUaAnalysisService(
        _analysis(
            UaCallRow(
                file="src/retriever.py",
                caller="retrieve_context",
                callee="qdrant_client.QdrantClient",
                line_number=14,
            )
        )
    )

    # When: parity compares mapped facts without fuzzy source matching.
    report = UaParityService(ua_analysis_service=analyzer).run(_fixture_root())

    # Then: both unmatched sides remain visible instead of false
    # equivalence. The two qdrant facts miss on line provenance and the
    # fixture's ollama.embeddings mirror has no UA row at all.
    assert report.summary.equivalent == 0
    assert report.summary.missing == 3
    assert report.summary.extra == 1
    assert {
        item.legacy.rule_id
        for item in report.comparisons
        if item.classification == "missing" and item.legacy is not None
    } == {
        "code_pattern_vector_store_qdrant",
        "code_pattern_embedding_ollama",
    }
    assert any(
        item.classification == "extra"
        and item.ua is not None
        and item.ua.rule_id == "ua_call_hint_vector_store_qdrant"
        for item in report.comparisons
    )


def test_real_harness_is_stable_read_only_with_frozen_counters() -> None:
    # Given: the real pinned Node sidecar and the Plan 31 parity corpus entry.
    project_root = _fixture_root()
    digest_before = _tree_digest(project_root)
    service = UaParityService()

    # When: the complete deterministic harness is rerun on the same target.
    first = service.run(project_root)
    second = service.run(project_root)

    # Then: reports are stable, target is read-only, and each run is counted.
    assert first.model_dump_json() == second.model_dump_json()
    assert _tree_digest(project_root) == digest_before
    assert first.invocations.filesystem_scan == 1
    assert first.invocations.ua_sidecar == 1
    assert first.invocations.parity_providers == 1
    assert str(project_root.resolve()) not in first.model_dump_json()
    with pytest.raises(ValidationError, match="frozen"):
        first.invocations.filesystem_scan = 2


def test_compare_consumes_approved_results_without_rerunning_scanners() -> (
    None
):
    # Given: B1 already produced one approved inventory and both scan results.
    project_root = _fixture_root()
    inventory = FilesystemProvider().build_inventory(project_root)
    legacy_result = ProjectScanService().scan_inventory(
        project_root,
        inventory=inventory,
    )
    ua_result = UaStructuralAdapter().adapt(_analysis())
    analyzer = FixedUaAnalysisService(_analysis())
    service = UaParityService(ua_analysis_service=analyzer)

    # When: the integration path builds parity from those existing objects.
    first = service.compare_existing(
        inventory=inventory,
        legacy_scan=legacy_result,
        ua_scan=ua_result,
    )
    second = service.compare_existing(
        inventory=inventory,
        legacy_scan=legacy_result,
        ua_scan=ua_result,
    )

    # Then: comparison is pure, stable, and records the one-shot B1 contract.
    assert analyzer.calls == []
    assert first.model_dump_json() == second.model_dump_json()
    assert first.invocations.filesystem_scan == 1
    assert first.invocations.ua_sidecar == 1
    assert first.invocations.parity_providers == 1


def test_compare_includes_ast_g1_facts_from_the_legacy_project_result(
    tmp_path: Path,
) -> None:
    # Given: regex and AST both observe a constructor UA cannot see at G1.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text(
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n",
        encoding="utf-8",
    )
    inventory = FilesystemProvider().build_inventory(project_root)
    legacy_result = ProjectScanService().scan_inventory(
        project_root,
        inventory=inventory,
    )

    # When: parity consumes the pre-UA project result and an empty UA result.
    report = UaParityService().compare_existing(
        inventory=inventory,
        legacy_scan=legacy_result,
        ua_scan=UaStructuralAdapter().adapt(_analysis()),
    )

    # Then: AST/G1 remains a distinct, provenance-backed missing row.
    ast_missing = [
        item
        for item in report.comparisons
        if item.classification == "missing"
        and item.legacy is not None
        and item.legacy.provider == "ast_construction"
    ]
    assert len(ast_missing) == 1
    assert ast_missing[0].legacy is not None
    assert ast_missing[0].legacy.rule_id == (
        "code_pattern_vector_store_qdrant"
    )
    assert ast_missing[0].legacy.file == "app.py"
    assert ast_missing[0].legacy.line_start == 2
    assert all(
        evidence_id.startswith("evidence:ast-construction:")
        for evidence_id in ast_missing[0].legacy.evidence_ids
    )


def test_endpoint_identity_facts_stay_out_of_parity(tmp_path: Path) -> None:
    # Given: a project whose only signal is a raw vendor URL, which the
    # endpoint identity layer picks up.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "client.py").write_text(
        "URL = 'https://api.anthropic.com/v1/messages'\n",
        encoding="utf-8",
    )
    inventory = FilesystemProvider().build_inventory(project_root)
    legacy_result = ProjectScanService().scan_inventory(
        project_root,
        inventory=inventory,
    )
    assert any(
        fact.rule_id == "endpoint_vendor_anthropic_llm"
        for fact in legacy_result.facts
    )

    # When: parity compares that result against an empty UA result.
    report = UaParityService().compare_existing(
        inventory=inventory,
        legacy_scan=legacy_result,
        ua_scan=UaStructuralAdapter().adapt(_analysis()),
    )

    # Then: endpoint identity has no legacy<->UA rule mapping at all, so
    # it is measured by neither side rather than failing the run closed.
    assert all(
        item.legacy is None
        or not (item.legacy.rule_id or "").startswith("endpoint_vendor_")
        for item in report.comparisons
    )
