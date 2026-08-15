from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.map_build import MapBuildRequest, MapBuildResult
from systograph.core.models.scan import OutputRun
from systograph.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from systograph.core.services.map_build_service import MapBuildService
from systograph.core.services.profile_rule_definitions import (
    PROFILE_RULE_DEFINITIONS,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.scan_snapshot_service import ScanSnapshotService
from systograph.core.services.system_map_v2_materialization_service import (
    TEMPLATE_FLOW_EDGES_ENV,
)
from systograph.core.services.ua_parity_service import UaParityService
from systograph.core.services.ua_structural_adapter import UaStructuralAdapter
from systograph.core.services.understand_anything_analysis_service import (
    UnderstandAnythingAnalysisService,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "rag_projects"
ALL_FIXTURES = tuple(
    sorted(path.name for path in FIXTURES_ROOT.iterdir() if path.is_dir())
)


@contextmanager
def template_edges(value: str) -> Iterator[None]:
    previous = os.environ.get(TEMPLATE_FLOW_EDGES_ENV)
    os.environ[TEMPLATE_FLOW_EDGES_ENV] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(TEMPLATE_FLOW_EDGES_ENV, None)
        else:
            os.environ[TEMPLATE_FLOW_EDGES_ENV] = previous


def build_snapshot(fixture: str, work_root: Path) -> tuple[ScanSnapshot, Path]:
    project_root = FIXTURES_ROOT / fixture
    repository = LocalJsonStateProvider(work_root / fixture / "state")
    scanner = ProjectScanService()
    service = ScanSnapshotService(
        project_scan_service=scanner,
        repository=repository,
        ua_analysis_service=UnderstandAnythingAnalysisService(),
        ua_adapter=UaStructuralAdapter(),
        ua_parity_service=UaParityService(),
        scan_id_factory=lambda: f"scan:{fixture}",
    )
    inventory = service.build_inventory(project_root)
    snapshot = service.scan_and_save(
        project_id=f"project:{fixture}",
        project_root=project_root,
        inventory=inventory,
    )
    return snapshot, project_root


def build_mode(
    *,
    fixture: str,
    mode: str,
    snapshot: ScanSnapshot,
    project_root: Path,
    work_root: Path,
    service: MapBuildService,
) -> MapBuildResult:
    with template_edges(mode):
        return service.build_from_snapshot(
            snapshot,
            request=MapBuildRequest(project_path=project_root),
            output_run=OutputRun(
                root_dir=work_root / fixture / f"build-{mode}"
            ),
            build_reason="initial_scan",
            build_id=f"build:{fixture}:{mode}",
        )


def summarize(result: MapBuildResult) -> dict[str, Any]:
    if (
        result.ai_system_map is None
        or result.profile_inference_result is None
        or result.viewer_load_result is None
    ):
        raise RuntimeError("measurement build returned incomplete artifacts")
    edges = result.ai_system_map.edges
    return {
        "edge_count": len(edges),
        "l1_observed": sum(edge.status == "observed" for edge in edges),
        "l2_undetermined": sum(
            edge.status == "undetermined"
            and edge.undetermined_reason != "template_adjacency_only"
            for edge in edges
        ),
        "l3_template": sum(
            edge.undetermined_reason == "template_adjacency_only"
            for edge in edges
        ),
        "l1_relationships": sorted(
            {edge.relationship for edge in edges if edge.status == "observed"}
        ),
        "l2_relationships": sorted(
            {
                edge.relationship
                for edge in edges
                if edge.status == "undetermined"
                and edge.undetermined_reason != "template_adjacency_only"
            }
        ),
        "l3_relationships": sorted(
            {
                edge.relationship
                for edge in edges
                if edge.undetermined_reason == "template_adjacency_only"
            }
        ),
        "profile_statuses": {
            item.profile_id: item.status
            for item in result.profile_inference_result.profiles
        },
        "graph_node_count": len(
            result.viewer_load_result.graph_view_model.nodes
        ),
        "graph_edge_count": len(
            result.viewer_load_result.graph_view_model.edges
        ),
    }


def measure_fixture(fixture: str, work_root: Path) -> dict[str, Any]:
    snapshot, project_root = build_snapshot(fixture, work_root)
    service = MapBuildService()
    on = summarize(
        build_mode(
            fixture=fixture,
            mode="on",
            snapshot=snapshot,
            project_root=project_root,
            work_root=work_root,
            service=service,
        )
    )
    off = summarize(
        build_mode(
            fixture=fixture,
            mode="off",
            snapshot=snapshot,
            project_root=project_root,
            work_root=work_root,
            service=service,
        )
    )
    parity = snapshot.ua_parity_report
    if parity is None:
        raise RuntimeError("measurement snapshot is missing parity evidence")
    profile_changes = {
        profile_id: {"on": status, "off": off["profile_statuses"][profile_id]}
        for profile_id, status in on["profile_statuses"].items()
        if status != off["profile_statuses"][profile_id]
    }
    return {
        "fixture": fixture,
        "ua_invocations": parity.invocations.model_dump(mode="json"),
        "on": on,
        "off": off,
        "profile_changes": profile_changes,
    }


def repository_state() -> tuple[str, bool]:
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return sha, dirty


def build_report(fixtures: Sequence[str]) -> dict[str, Any]:
    unknown = sorted(set(fixtures) - set(ALL_FIXTURES))
    if unknown:
        raise ValueError(f"unknown fixtures: {', '.join(unknown)}")
    with tempfile.TemporaryDirectory(prefix="systograph-phase12-") as temp:
        work_root = Path(temp)
        measurements = [
            measure_fixture(fixture, work_root) for fixture in fixtures
        ]
    required_relationships = sorted(
        {
            item.required_relationship
            for item in PROFILE_RULE_DEFINITIONS
            if item.required_relationship is not None
        }
    )
    l1_coverage = sorted(
        {
            relationship
            for item in measurements
            for relationship in item["off"]["l1_relationships"]
        }
    )
    l2_coverage = sorted(
        {
            relationship
            for item in measurements
            for relationship in item["off"]["l2_relationships"]
        }
    )
    sha, dirty = repository_state()
    return {
        "schema_version": "template-flow-retirement/v1",
        "head_sha": sha,
        "worktree_dirty": dirty,
        "fixtures": measurements,
        "relationship_coverage": {
            "required": required_relationships,
            "l1": l1_coverage,
            "l2": l2_coverage,
            "missing_l1": sorted(
                set(required_relationships) - set(l1_coverage)
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", nargs="+", default=list(ALL_FIXTURES))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args.fixtures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    args.output.write_text(payload + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
