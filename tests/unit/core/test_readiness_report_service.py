from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.readiness_report_service import (
    ReadinessReportService,
)

FIXTURE = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")


def test_readiness_report_keeps_evidence_and_mapping_dimensions() -> None:
    system_map = (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )
    profiles = ProfileInferenceService().infer(
        system_map,
        build_id="build:grounded-rag",
        scan_id="scan:grounded-rag",
        environment_id="environment:default-static",
    )

    report = ReadinessReportService().build(
        system_map=system_map,
        profile_result=profiles,
    )

    assert report.schema_version == "readiness-report/v1"
    assert report.generated_from_build_id == profiles.build_id
    assert report.mapping_completeness == profiles.mapping_completeness
    assert report.grounding.status == "detected"
    assert report.capability_summaries
    assert all(
        finding.evidence_ids or finding.reason for finding in report.findings
    )
    assert not hasattr(report, "score")


def test_readiness_report_includes_source_traceability_finding() -> None:
    system_map = (
        CanonicalMapLoader()
        .load(json.loads(FIXTURE.read_text(encoding="utf-8")))
        .normalized
    )
    profiles = ProfileInferenceService().infer(
        system_map,
        build_id="build:grounded-rag",
        scan_id="scan:grounded-rag",
        environment_id="environment:default-static",
    )

    report = ReadinessReportService().build(
        system_map=system_map,
        profile_result=profiles,
    )

    assert "source_traceability" in {item.category for item in report.findings}
