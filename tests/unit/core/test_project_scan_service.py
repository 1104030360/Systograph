from __future__ import annotations

import logging
from pathlib import Path

import pytest

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
    SkippedFile,
    SkipReason,
)
from kai_mind.core.models.scan import ProviderScanResult, ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services import project_scan_service
from kai_mind.core.services.project_scan_service import ProjectScanService


class FakeFilesystemProvider:
    def __init__(self, inventory: FileInventory) -> None:
        self.inventory = inventory
        self.seen_root: Path | None = None

    def build_inventory(self, project_root: Path) -> FileInventory:
        self.seen_root = project_root
        return self.inventory


class FakeProvider:
    def __init__(
        self,
        result: ProviderScanResult,
        *,
        name: str = "fake",
    ) -> None:
        self.result = result
        self.name = name
        self.seen_inventory: FileInventory | None = None

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        self.seen_inventory = inventory
        return self.result


class FailingProvider:
    name = "failing_provider"

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        raise RuntimeError("provider exploded with sk-live-secret-value")


def build_inventory(project_root: Path) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[FileRecord(path="config.yaml", size_bytes=10)],
        skipped=[
            SkippedFile(
                path="node_modules/",
                reason=SkipReason.DEPENDENCY_DIRECTORY,
            )
        ],
        warnings=["inventory fallback used"],
    )


def fact(
    kind: str,
    file: str,
    path: str,
    value: str,
    rule_id: str,
) -> ScanFact:
    return ScanFact(
        kind=kind,
        file=file,
        path=path,
        value=value,
        rule_id=rule_id,
    )


def evidence(
    evidence_id: str,
    kind: str,
    file: str,
    path: str,
    value: str,
    rule_id: str,
) -> Evidence:
    return Evidence(
        id=evidence_id,
        kind=kind,
        file=file,
        path=path,
        value=value,
        rule_id=rule_id,
    )


def provider_result(
    facts: list[ScanFact],
    evidence_items: list[Evidence],
) -> ProviderScanResult:
    return ProviderScanResult(facts=facts, evidence=evidence_items)


def test_scan_builds_inventory_and_aggregates_provider_results(
    tmp_path: Path,
) -> None:
    inventory = build_inventory(tmp_path)
    filesystem_provider = FakeFilesystemProvider(inventory)
    config_provider = FakeProvider(
        provider_result(
            [
                fact(
                    "config_value",
                    "config.yaml",
                    "llm.provider",
                    "ollama",
                    "config_yaml_value_detected",
                )
            ],
            [
                evidence(
                    "evidence:config",
                    "config_value",
                    "config.yaml",
                    "llm.provider",
                    "ollama",
                    "config_yaml_value_detected",
                )
            ],
        ),
        name="config",
    )

    result = ProjectScanService(
        filesystem_provider=filesystem_provider,
        providers=[config_provider],
    ).scan(tmp_path)

    assert filesystem_provider.seen_root == tmp_path
    assert config_provider.seen_inventory == inventory
    assert [item.rule_id for item in result.facts] == [
        "config_yaml_value_detected"
    ]
    assert [item.id for item in result.evidence] == ["evidence:config"]
    assert [
        (item.path, item.reason, item.size_bytes)
        for item in result.skipped_files
    ] == [("node_modules/", "dependency_directory", None)]
    assert result.warnings == ["inventory fallback used"]


def test_scan_preserves_partial_output_when_one_provider_fails(
    tmp_path: Path,
) -> None:
    inventory = build_inventory(tmp_path)
    good_provider = FakeProvider(
        provider_result(
            [
                fact(
                    "dependency_candidate",
                    "requirements.txt",
                    "line[1]",
                    "langchain",
                    "dependency_rag_framework_langchain",
                )
            ],
            [
                evidence(
                    "evidence:dependency",
                    "dependency_candidate",
                    "requirements.txt",
                    "line[1]",
                    "langchain",
                    "dependency_rag_framework_langchain",
                )
            ],
        ),
        name="dependency_manifest",
    )

    result = ProjectScanService(
        filesystem_provider=FakeFilesystemProvider(inventory),
        providers=[FailingProvider(), good_provider],
    ).scan(tmp_path)

    assert [item.value for item in result.facts] == ["langchain"]
    assert [item.id for item in result.evidence] == ["evidence:dependency"]
    assert len(result.issues) == 1
    assert result.issues[0].provider == "failing_provider"
    assert result.issues[0].scan_stage == "project_scan"
    assert "sk-live-secret-value" not in result.issues[0].message
    assert result.warnings == [
        "inventory fallback used",
        "failing_provider failed",
    ]


def test_scan_logs_provider_crash_traceback_for_developers(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    inventory = build_inventory(tmp_path)
    caplog.set_level(logging.ERROR, logger=project_scan_service.__name__)

    result = ProjectScanService(
        filesystem_provider=FakeFilesystemProvider(inventory),
        providers=[FailingProvider()],
    ).scan(tmp_path)

    assert len(result.issues) == 1
    assert "sk-live-secret-value" not in result.issues[0].message
    matching_records = [
        record
        for record in caplog.records
        if (
            record.name == project_scan_service.__name__
            and record.levelno == logging.ERROR
            and "failing_provider" in record.getMessage()
        )
    ]
    assert len(matching_records) == 1
    assert matching_records[0].exc_info is None
    assert "Traceback frames:" in caplog.text
    assert "project_scan_service.py" in caplog.text
    assert "test_project_scan_service.py" in caplog.text
    assert "sk-live-secret-value" not in caplog.text


def test_scan_merges_duplicate_facts_and_keeps_all_evidence(
    tmp_path: Path,
) -> None:
    inventory = build_inventory(tmp_path)
    duplicate_fact = fact(
        "dependency_candidate",
        "requirements.txt",
        "line[1]",
        "langchain",
        "dependency_rag_framework_langchain",
    )
    first_provider = FakeProvider(
        provider_result(
            [duplicate_fact],
            [
                evidence(
                    "evidence:first",
                    "dependency_candidate",
                    "requirements.txt",
                    "line[1]",
                    "langchain",
                    "dependency_rag_framework_langchain",
                )
            ],
        ),
        name="first",
    )
    second_provider = FakeProvider(
        provider_result(
            [duplicate_fact],
            [
                evidence(
                    "evidence:second",
                    "dependency_candidate",
                    "pyproject.toml",
                    "project.dependencies[0]",
                    "langchain",
                    "dependency_rag_framework_langchain",
                )
            ],
        ),
        name="second",
    )

    result = ProjectScanService(
        filesystem_provider=FakeFilesystemProvider(inventory),
        providers=[second_provider, first_provider],
    ).scan(tmp_path)

    assert result.facts == [duplicate_fact]
    assert {item.id for item in result.evidence} == {
        "evidence:first",
        "evidence:second",
    }


def test_scan_orders_facts_evidence_issues_and_skipped_files_deterministically(
    tmp_path: Path,
) -> None:
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(tmp_path),
        files=[],
        skipped=[
            SkippedFile(path="z.log", reason=SkipReason.LARGE_LOG),
            SkippedFile(path="a.bin", reason=SkipReason.BINARY),
        ],
    )
    unordered_provider = FakeProvider(
        provider_result(
            [
                fact("b", "z.py", "line[2]", "z", "rule_b"),
                fact("a", "a.py", "line[1]", "a", "rule_a"),
            ],
            [
                evidence("evidence:z", "b", "z.py", "line[2]", "z", "rule_b"),
                evidence("evidence:a", "a", "a.py", "line[1]", "a", "rule_a"),
            ],
        )
    )

    result = ProjectScanService(
        filesystem_provider=FakeFilesystemProvider(inventory),
        providers=[FailingProvider(), unordered_provider],
    ).scan(tmp_path)

    assert [(item.kind, item.file, item.path) for item in result.facts] == [
        ("a", "a.py", "line[1]"),
        ("b", "z.py", "line[2]"),
    ]
    assert [item.id for item in result.evidence] == [
        "evidence:a",
        "evidence:z",
    ]
    assert [(item.provider, item.file) for item in result.issues] == [
        ("failing_provider", "$provider")
    ]
    assert [item.path for item in result.skipped_files] == ["a.bin", "z.log"]


def test_scan_result_stays_at_raw_fact_boundary(tmp_path: Path) -> None:
    result = ProjectScanService(
        filesystem_provider=FakeFilesystemProvider(build_inventory(tmp_path)),
        providers=[],
    ).scan(tmp_path)

    assert not hasattr(result, "components_by_slot")
    assert not hasattr(result, "endpoints")
    assert not hasattr(result, "risk_hints")
    assert not hasattr(result, "flows")
