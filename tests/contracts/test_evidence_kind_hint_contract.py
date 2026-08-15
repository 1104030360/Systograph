from __future__ import annotations

import ast
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import AssessmentEvidenceKind
from systograph.core.models.system_map import Evidence
from systograph.core.services.canonical_evidence_service import (
    canonical_evidence_from_scan,
)

EVIDENCE_KIND_MODULE = (
    Path(__file__).parents[2]
    / "src"
    / "systograph"
    / "core"
    / "models"
    / "evidence_kind.py"
)


@pytest.mark.parametrize(
    ("hint", "file", "line_start"),
    [
        ("indirect", "src/factory.py", 12),
        ("explicit_negative", "src/factory.py", 12),
        ("direct", None, None),
    ],
)
def test_explicit_hint_overrides_location_shape(
    hint: AssessmentEvidenceKind,
    file: str | None,
    line_start: int | None,
) -> None:
    given_evidence = Evidence(
        id=f"evidence:hint:{hint}",
        kind="factory_inference",
        file=file,
        path="line[12]",
        line_start=line_start,
        evidence_kind_hint=hint,
    )

    when_canonical = canonical_evidence_from_scan(
        given_evidence,
        no_snippets=False,
    )

    then_evidence_kind = when_canonical.evidence_kind
    assert then_evidence_kind == hint


@pytest.mark.parametrize(
    ("file", "path", "line_start", "expected"),
    [
        ("src/direct.py", "line[4]", 4, "direct"),
        ("config/settings.json", "/provider", None, "direct"),
        ("requirements.txt", "dependency[0]", None, "indirect"),
    ],
)
def test_missing_hint_keeps_legacy_location_heuristic(
    file: str,
    path: str,
    line_start: int | None,
    expected: AssessmentEvidenceKind,
) -> None:
    given_evidence = Evidence(
        id=f"evidence:legacy:{expected}:{line_start}",
        kind="legacy_signal",
        file=file,
        path=path,
        line_start=line_start,
    )

    when_canonical = canonical_evidence_from_scan(
        given_evidence,
        no_snippets=False,
    )

    then_evidence_kind = when_canonical.evidence_kind
    assert then_evidence_kind == expected


def test_explicit_hint_survives_evidence_round_trip() -> None:
    given_evidence = Evidence(
        id="evidence:factory:round-trip",
        kind="factory_inference",
        file="src/factory.py",
        path="line[12]",
        line_start=12,
        evidence_kind_hint="indirect",
    )

    when_reloaded = Evidence.model_validate(
        given_evidence.model_dump(mode="json")
    )

    then_hint = when_reloaded.evidence_kind_hint
    assert then_hint == "indirect"


def test_neutral_evidence_kind_module_has_no_model_dependency() -> None:
    given_module_path = EVIDENCE_KIND_MODULE
    missing_module_message = "neutral evidence-kind module is missing"
    assert given_module_path.exists(), missing_module_message

    when_syntax_tree = ast.parse(given_module_path.read_text(encoding="utf-8"))
    when_model_imports = {
        node.module
        for node in ast.walk(when_syntax_tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("systograph.core.models")
    }

    then_model_imports = when_model_imports
    assert then_model_imports == set()
