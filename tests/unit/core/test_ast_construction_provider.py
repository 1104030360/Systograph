from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from systograph.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from systograph.core.models.scan import ProviderScanResult
from systograph.core.models.structural_fact import (
    CallStructuralFact,
    FactoryInferenceStructuralFact,
    ImportStructuralFact,
)
from systograph.core.providers.ast_construction_provider import (
    AstConstructionProvider,
    _PinnedProjectRoot,
)


def build_inventory(project_root: Path, *paths: str) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path=path,
                size_bytes=(project_root / path).stat().st_size,
                content_fingerprint=(
                    "sha256:"
                    + hashlib.sha256(
                        (project_root / path).read_bytes()
                    ).hexdigest()
                ),
            )
            for path in paths
        ],
    )


def scan_project(
    tmp_path: Path,
    files: dict[str, str],
) -> tuple[Path, ProviderScanResult]:
    project_root = tmp_path / "project"
    for relative_path, content in files.items():
        path = project_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    inventory = build_inventory(project_root, *files)
    return project_root, AstConstructionProvider().collect(inventory)


def calls(result: ProviderScanResult) -> list[CallStructuralFact]:
    return [
        fact
        for fact in result.structural_facts
        if isinstance(fact, CallStructuralFact)
    ]


def imports(result: ProviderScanResult) -> list[ImportStructuralFact]:
    return [
        fact
        for fact in result.structural_facts
        if isinstance(fact, ImportStructuralFact)
    ]


def factories(
    result: ProviderScanResult,
) -> list[FactoryInferenceStructuralFact]:
    return [
        fact
        for fact in result.structural_facts
        if isinstance(fact, FactoryInferenceStructuralFact)
    ]


def test_g1_emits_direct_facts_for_module_and_class_calls_only(
    tmp_path: Path,
) -> None:
    # Given: the same aliased constructor at module, class, and function scope.
    _, result = scan_project(
        tmp_path,
        {
            "src/app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient as Client",
                    "module_client = Client()",
                    "class Settings:",
                    "    class_client = Client()",
                    "def build():",
                    "    return Client()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: import-time calls are direct; a function-body call is absent.
    assert [(fact.file, fact.path, fact.rule_id) for fact in result.facts] == [
        ("src/app.py", "line[1]", "ast_external_import"),
        ("src/app.py", "line[2]", "code_pattern_vector_store_qdrant"),
        ("src/app.py", "line[4]", "code_pattern_vector_store_qdrant"),
    ]
    assert [item.evidence_kind_hint for item in result.evidence] == [
        "indirect",
        "direct",
        "direct",
    ]
    assert [(item.callee, item.span.line_start) for item in calls(result)] == [
        ("qdrant_client.QdrantClient", 2),
        ("qdrant_client.QdrantClient", 4),
    ]


def test_g1_resolves_module_and_symbol_aliases(tmp_path: Path) -> None:
    # Given: module aliases, from-import aliases, and a plain module import.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "import qdrant_client as qc",
                    "from qdrant_client import QdrantClient as Client",
                    "import qdrant_client",
                    "first = qc.QdrantClient()",
                    "second = Client()",
                    "third = qdrant_client.QdrantClient()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: every spelling resolves to one canonical catalog symbol.
    assert [item.callee for item in calls(result)] == [
        "qdrant_client.QdrantClient",
        "qdrant_client.QdrantClient",
        "qdrant_client.QdrantClient",
    ]
    # Three import declaration facts plus three direct call facts.
    assert len(result.facts) == 6
    assert (
        sum(fact.rule_id == "ast_external_import" for fact in result.facts)
        == 3
    )


def test_g1_visits_decorators_bases_and_defaults_before_function_scope(
    tmp_path: Path,
) -> None:
    # Given: constructor calls evaluated while definitions are created.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def decorate(value):",
                    "    return lambda target: target",
                    "@decorate(QdrantClient())",
                    "class Store(QdrantClient()):",
                    "    pass",
                    "def build(client=QdrantClient()):",
                    "    return QdrantClient()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: three outer evaluations are direct, not the function body.
    assert [item.span.line_start for item in calls(result)] == [4, 5, 7]


def test_type_checking_import_is_indirect_but_never_direct_construction(
    tmp_path: Path,
) -> None:
    # Given: a type-only external import and call plus a runtime else branch.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from typing import TYPE_CHECKING",
                    "if TYPE_CHECKING:",
                    "    from qdrant_client import QdrantClient as TypeClient",
                    "    hidden = TypeClient()",
                    "else:",
                    "    from qdrant_client import "
                    "QdrantClient as RuntimeClient",
                    "    visible = RuntimeClient()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: both declarations remain traceable,
    # while only runtime use is direct.
    qdrant_imports = [
        item for item in imports(result) if item.module == "qdrant_client"
    ]
    assert [(item.alias, item.span.line_start) for item in qdrant_imports] == [
        ("TypeClient", 3),
        ("RuntimeClient", 6),
    ]
    assert [item.span.line_start for item in calls(result)] == [7]
    # Two external import declarations plus one direct call fact
    # (typing is stdlib, so it never becomes an external import).
    assert [fact.rule_id for fact in result.facts] == [
        "ast_external_import",
        "ast_external_import",
        "code_pattern_vector_store_qdrant",
    ]
    assert result.evidence[0].evidence_kind_hint == "indirect"


def test_star_import_is_counted_without_guessing_a_constructor(
    tmp_path: Path,
) -> None:
    # Given: a wildcard import followed by an otherwise recognizable name.
    _, result = scan_project(
        tmp_path,
        {"app.py": ("from qdrant_client import *\nclient = QdrantClient()\n")},
    )

    # When/Then: import evidence survives,
    # while no resolved component is invented.
    assert [(fact.rule_id, fact.value) for fact in result.facts] == [
        ("ast_external_import", "qdrant_client.*")
    ]
    assert calls(result) == []
    assert [(item.module, item.symbol) for item in imports(result)] == [
        ("qdrant_client", "*")
    ]
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_unresolved_star_import"
    ]


def test_internal_reexport_resolves_through_import_chain(
    tmp_path: Path,
) -> None:
    # Given: a package re-exports a known constructor into another module.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/clients.py": (
                "from qdrant_client import QdrantClient\n"
            ),
            "src/app_pkg/app.py": (
                "from .clients import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: the internal import is not G3, while the call is direct.
    assert [(item.module, item.symbol) for item in imports(result)] == [
        ("qdrant_client", "QdrantClient")
    ]
    assert [(item.callee, item.span.file) for item in calls(result)] == [
        ("qdrant_client.QdrantClient", "src/app_pkg/app.py")
    ]


def test_two_hop_reexport_chain_resolves_to_external_symbol(
    tmp_path: Path,
) -> None:
    # Given: the external constructor is re-exported through two modules.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/backends.py": (
                "from qdrant_client import QdrantClient\n"
            ),
            "src/app_pkg/clients.py": ("from .backends import QdrantClient\n"),
            "src/app_pkg/app.py": (
                "from .clients import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: the chain proves the origin, so the call stays direct.
    assert [(item.callee, item.span.file) for item in calls(result)] == [
        ("qdrant_client.QdrantClient", "src/app_pkg/app.py")
    ]


def test_reexport_chain_beyond_hop_limit_is_not_followed(
    tmp_path: Path,
) -> None:
    # Given: a re-export chain one module deeper than MAX_REEXPORT_HOPS.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/level3.py": (
                "from qdrant_client import QdrantClient\n"
            ),
            "src/app_pkg/level2.py": "from .level3 import QdrantClient\n",
            "src/app_pkg/level1.py": "from .level2 import QdrantClient\n",
            "src/app_pkg/level0.py": "from .level1 import QdrantClient\n",
            "src/app_pkg/app.py": (
                "from .level0 import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: resolution stops at the bound instead of guessing.
    assert [fact.rule_id for fact in result.facts] == ["ast_external_import"]
    assert calls(result) == []


def test_reexport_from_unparsed_module_is_not_guessed(
    tmp_path: Path,
) -> None:
    # Given: the imported module is absent from the scan inventory.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/app.py": (
                "from .missing import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: an unverifiable chain yields no fact.
    assert result.facts == []
    assert calls(result) == []


def test_colliding_module_names_cannot_anchor_a_reexport(
    tmp_path: Path,
) -> None:
    # Given: "src/dup.py" and "dup.py" collapse to the same module name.
    _, result = scan_project(
        tmp_path,
        {
            "src/dup.py": "from qdrant_client import QdrantClient\n",
            "dup.py": "class QdrantClient:\n    pass\n",
            "app.py": (
                "from dup import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: the ambiguous module name is refused, not guessed.
    assert [fact.rule_id for fact in result.facts] == ["ast_external_import"]
    assert calls(result) == []


def test_internal_class_sharing_catalog_name_is_not_external(
    tmp_path: Path,
) -> None:
    # Given: the project defines its own class named like a catalog symbol.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/clients.py": "class QdrantClient:\n    pass\n",
            "src/app_pkg/app.py": (
                "from .clients import QdrantClient\nclient = QdrantClient()\n"
            ),
        },
    )

    # When/Then: no external construction fact or direct evidence is invented.
    assert result.facts == []
    assert calls(result) == []
    assert [
        item for item in result.evidence if item.evidence_kind_hint == "direct"
    ] == []


def test_try_import_binding_remains_available(tmp_path: Path) -> None:
    # Given: an optional dependency import guarded by ImportError handling.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "try:",
                    "    from qdrant_client import QdrantClient",
                    "except ImportError:",
                    "    QdrantClient = None",
                    "client = QdrantClient()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: the guarded import still resolves the import-time call.
    assert [item.span.line_start for item in calls(result)] == [5]


def test_implicit_metaclass_and_init_subclass_emit_no_component(
    tmp_path: Path,
) -> None:
    # Given: class creation can execute imported hooks
    # without an explicit call.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from provider_hooks import ProviderMeta, ProviderBase",
                    "class Store(ProviderBase, metaclass=ProviderMeta):",
                    "    pass",
                ]
            )
            + "\n"
        },
    )

    # When/Then: implicit runtime behavior never becomes a guessed component.
    assert [fact.rule_id for fact in result.facts] == [
        "ast_external_import",
        "ast_external_import",
    ]
    assert calls(result) == []
    assert factories(result) == []
    assert all("not_detected" not in issue.rule_id for issue in result.issues)


def test_g3_unused_external_import_never_emits_component_fact(
    tmp_path: Path,
) -> None:
    # Given: one external dependency import
    # and one flat-layout internal import.
    _, result = scan_project(
        tmp_path,
        {
            "clients.py": "def helper():\n    return None\n",
            "app.py": "\n".join(
                [
                    "from clients import helper",
                    "from qdrant_client import QdrantClient",
                ]
            )
            + "\n",
        },
    )

    # When/Then: only the external declaration and indirect evidence are added.
    assert [(fact.kind, fact.value) for fact in result.facts] == [
        ("external_import_declaration", "qdrant_client.QdrantClient")
    ]
    assert calls(result) == []
    assert [
        (item.module, item.symbol, item.span.line_start)
        for item in imports(result)
    ] == [("qdrant_client", "QdrantClient", 2)]
    assert len(result.evidence) == 1
    assert result.evidence[0].evidence_kind_hint == "indirect"


def test_src_layout_absolute_internal_import_is_not_external(
    tmp_path: Path,
) -> None:
    # Given: an absolute package import under a src layout.
    _, result = scan_project(
        tmp_path,
        {
            "src/app_pkg/clients.py": "class LocalClient:\n    pass\n",
            "src/app_pkg/app.py": (
                "from app_pkg.clients import LocalClient\n"
            ),
        },
    )

    # When/Then: the inventory-derived package root classifies it as internal.
    assert imports(result) == []
    assert result.evidence == []


def test_parse_failure_is_file_local_and_fail_closed(tmp_path: Path) -> None:
    # Given: one malformed file and one valid import-time constructor.
    _, result = scan_project(
        tmp_path,
        {
            "broken.py": "def broken(:\n",
            "valid.py": (
                "from qdrant_client import QdrantClient\n"
                "client = QdrantClient()\n"
            ),
        },
    )

    # When/Then: valid evidence survives and syntax failure is structured.
    assert [fact.rule_id for fact in result.facts] == [
        "ast_external_import",
        "code_pattern_vector_store_qdrant",
    ]
    assert [(issue.file, issue.rule_id) for issue in result.issues] == [
        ("broken.py", "ast_construction_parse_error")
    ]
    assert result.issues[0].scan_stage == "code_pattern_scan"
    assert result.issues[0].provider == "ast_construction"


def test_inventory_parent_traversal_is_rejected_without_reading_outside(
    tmp_path: Path,
) -> None:
    # Given: inventory metadata points at a Python file outside project root.
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside.py"
    outside.write_text(
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n",
        encoding="utf-8",
    )
    inventory = FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(path="../outside.py", size_bytes=outside.stat().st_size)
        ],
    )

    # When: the provider receives the untrusted inventory path.
    result = AstConstructionProvider().collect(inventory)

    # Then: no outside fact leaks and the boundary failure is explicit.
    assert result.facts == []
    assert result.structural_facts == []
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_invalid_inventory_path"
    ]


def test_inventory_path_swap_cannot_read_symlink_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an approved file is swapped to an outside symlink after resolve.
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = project_root / "app.py"
    source.write_text("value = 1\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text(
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py")
    original_resolve = AstConstructionProvider._resolve_inventory_path
    resolve_calls = 0

    def swap_after_resolve(
        root: Path,
        relative_path: str,
    ) -> Path | None:
        nonlocal resolve_calls
        resolved = original_resolve(root, relative_path)
        resolve_calls += 1
        if resolve_calls == 1:
            source.unlink()
            try:
                source.symlink_to(outside)
            except OSError:
                pytest.skip("symlink creation is unavailable")
        return resolved

    monkeypatch.setattr(
        AstConstructionProvider,
        "_resolve_inventory_path",
        staticmethod(swap_after_resolve),
    )

    # When: the AST provider reaches its read boundary.
    result = AstConstructionProvider().collect(inventory)

    # Then: outside constructor facts are never read or published.
    assert result.facts == []
    assert result.structural_facts == []
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_read_error"
    ]


def test_project_root_swap_cannot_read_replacement_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the approved project root is replaced after inventory resolution.
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = project_root / "app.py"
    source.write_text("value = 1\n", encoding="utf-8")
    inventory = build_inventory(project_root, "app.py")
    original_resolve = AstConstructionProvider._resolve_inventory_path
    resolve_calls = 0

    def replace_root_after_resolve(
        root: Path,
        relative_path: str,
    ) -> Path | None:
        nonlocal resolve_calls
        resolved = original_resolve(root, relative_path)
        resolve_calls += 1
        if resolve_calls == 1:
            project_root.rename(tmp_path / "approved-root-moved")
            project_root.mkdir()
            (project_root / "app.py").write_text(
                "from qdrant_client import QdrantClient\n"
                "client = QdrantClient()\n",
                encoding="utf-8",
            )
        return resolved

    monkeypatch.setattr(
        AstConstructionProvider,
        "_resolve_inventory_path",
        staticmethod(replace_root_after_resolve),
    )

    # When: the provider reaches its source-open boundary.
    result = AstConstructionProvider().collect(inventory)

    # Then: replacement-root bytes are never parsed into facts.
    assert result.facts == []
    assert result.structural_facts == []
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_read_error"
    ]


def test_transient_same_inode_content_swap_cannot_publish_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: approved bytes are replaced only while the descriptor is read.
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = project_root / "app.py"
    replacement = (
        b"from qdrant_client import QdrantClient\nclient = QdrantClient()\n"
    )
    approved = b"value = 1\n#".ljust(len(replacement), b"x")
    assert len(approved) == len(replacement)
    source.write_bytes(approved)
    approved_stat = source.stat()
    approved_inode = approved_stat.st_ino
    inventory = build_inventory(project_root, "app.py")
    original_read = AstConstructionProvider._read_verified_source

    def swap_during_read(
        cls: type[AstConstructionProvider],
        pinned_root: _PinnedProjectRoot,
        record: FileRecord,
    ) -> str:
        source.write_bytes(replacement)
        assert source.stat().st_ino == approved_inode
        try:
            return original_read(pinned_root, record)
        finally:
            source.write_bytes(approved)
            os.utime(
                source,
                ns=(approved_stat.st_atime_ns, approved_stat.st_mtime_ns),
            )

    monkeypatch.setattr(
        AstConstructionProvider,
        "_read_verified_source",
        classmethod(swap_during_read),
    )

    # When: the transient replacement is invisible to the final path hash.
    result = AstConstructionProvider().collect(inventory)

    # Then: descriptor bytes still must match the approved content digest.
    assert result.facts == []
    assert result.structural_facts == []
    assert source.read_bytes() == approved
    assert source.stat().st_mtime_ns == approved_stat.st_mtime_ns
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_read_error"
    ]


def test_non_posix_platform_has_no_pathname_safe_open_fallback() -> None:
    assert AstConstructionProvider._safe_open_flags("nt") is None


def test_missing_safe_open_primitives_fail_closed_for_every_python_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("value = 1\n", encoding="utf-8")
    (project_root / "worker.py").write_text("value = 2\n", encoding="utf-8")
    (project_root / "README.md").write_text("fixture\n", encoding="utf-8")
    inventory = build_inventory(
        project_root,
        "app.py",
        "worker.py",
        "README.md",
    )
    open_calls = 0

    def reject_pathname_open(*args: object, **kwargs: object) -> int:
        nonlocal open_calls
        del args, kwargs
        open_calls += 1
        raise AssertionError("safe-open failure must not fall back to os.open")

    monkeypatch.setattr(
        AstConstructionProvider,
        "_safe_open_flags",
        staticmethod(lambda platform_name=None: None),
    )
    monkeypatch.setattr(os, "open", reject_pathname_open)

    result = AstConstructionProvider().collect(inventory)

    assert result.facts == []
    assert result.structural_facts == []
    assert result.evidence == []
    assert open_calls == 0
    assert [(issue.file, issue.rule_id) for issue in result.issues] == [
        ("app.py", "ast_construction_read_error"),
        ("worker.py", "ast_construction_read_error"),
    ]


def test_scan_is_read_only_and_deterministic(tmp_path: Path) -> None:
    # Given: a project with stable source bytes and directory contents.
    project_root = tmp_path / "project"
    project_root.mkdir()
    source = project_root / "app.py"
    source.write_text(
        "from qdrant_client import QdrantClient\nclient = QdrantClient()\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "app.py")
    before_bytes = source.read_bytes()
    before_paths = sorted(
        path.relative_to(project_root) for path in project_root.rglob("*")
    )

    # When: the same provider scan is repeated twenty times.
    payloads = [
        AstConstructionProvider().collect(inventory).model_dump_json()
        for _ in range(20)
    ]

    # Then: output is byte-stable and the scanned project is untouched.
    assert len(set(payloads)) == 1
    assert source.read_bytes() == before_bytes
    assert (
        sorted(
            path.relative_to(project_root) for path in project_root.rglob("*")
        )
        == before_paths
    )


def test_g2_resolves_return_annotation_as_indirect(tmp_path: Path) -> None:
    # Given: an invoked factory declares a known constructor return type.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def get_store() -> QdrantClient:",
                    "    raise RuntimeError",
                    "store = get_store()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: the call yields one indirect component
    # with annotation provenance.
    assert [fact.rule_id for fact in result.facts] == [
        "ast_external_import",
        "code_pattern_vector_store_qdrant",
    ]
    inferred = factories(result)
    assert len(inferred) == 1
    assert inferred[0].constructed_symbol == "qdrant_client.QdrantClient"
    assert [step.resolution for step in inferred[0].provenance] == [
        "return_annotation"
    ]
    factory_evidence = [
        item
        for item in result.evidence
        if item.rule_id == "code_pattern_vector_store_qdrant"
    ]
    assert [item.evidence_kind_hint for item in factory_evidence] == [
        "indirect"
    ]


def test_g2_resolves_direct_return_and_delegate_chain(tmp_path: Path) -> None:
    # Given: a called factory delegates twice
    # before constructing a known client.
    _, result = scan_project(
        tmp_path,
        {
            "factories.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def leaf():",
                    "    return QdrantClient()",
                    "def middle():",
                    "    return leaf()",
                    "def outer():",
                    "    return middle()",
                ]
            )
            + "\n",
            "app.py": "from factories import outer\nstore = outer()\n",
        },
    )

    # When/Then: one inference preserves both delegates and the construction.
    inferred = factories(result)
    assert len(inferred) == 1
    assert [step.resolution for step in inferred[0].provenance] == [
        "delegate_call",
        "delegate_call",
        "return_construction",
    ]
    assert [step.hop for step in inferred[0].provenance] == [0, 1, 2]
    assert inferred[0].call_span.file == "app.py"
    assert inferred[0].call_span.line_start == 2


def test_g2_preserves_branch_disjunction(tmp_path: Path) -> None:
    # Given: one invoked factory can construct two catalog-backed clients.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "import chromadb",
                    "from qdrant_client import QdrantClient",
                    "def get_store(use_qdrant):",
                    "    if use_qdrant:",
                    "        return QdrantClient()",
                    "    return chromadb.HttpClient()",
                    "store = get_store(True)",
                ]
            )
            + "\n"
        },
    )

    # When/Then: both possible constructions survive as indirect facts.
    assert {item.constructed_symbol for item in factories(result)} == {
        "qdrant_client.QdrantClient",
        "chromadb.HttpClient",
    }
    # Two import declaration facts plus two factory inference facts.
    assert len(result.facts) == 4
    component_evidence = [
        item
        for item in result.evidence
        if item.rule_id != "ast_external_import"
    ]
    assert {item.evidence_kind_hint for item in component_evidence} == {
        "indirect"
    }


def test_g2_expands_literal_registry_entries(tmp_path: Path) -> None:
    # Given: a factory dispatches through a literal module-level registry.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "import chromadb",
                    "from qdrant_client import QdrantClient",
                    "PROVIDERS = {",
                    "    'qdrant': QdrantClient,",
                    "    'chroma': chromadb.HttpClient,",
                    "}",
                    "def get_store(name):",
                    "    return PROVIDERS[name]()",
                    "store = get_store('qdrant')",
                ]
            )
            + "\n"
        },
    )

    # When/Then: each literal value becomes a separate indirect possibility.
    inferred = factories(result)
    assert {item.constructed_symbol for item in inferred} == {
        "qdrant_client.QdrantClient",
        "chromadb.HttpClient",
    }
    assert {
        step.resolution for item in inferred for step in item.provenance
    } == {"registry_entry"}


def test_g2_parameter_passthrough_emits_no_component(tmp_path: Path) -> None:
    # Given: a called function returns an unconstrained parameter.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": (
                "def get_store(client):\n"
                "    return client\n"
                "store = get_store(existing_client)\n"
            )
        },
    )

    # When/Then: no constant propagation or negative fact is invented.
    assert result.facts == []
    assert factories(result) == []
    assert all("not_detected" not in issue.rule_id for issue in result.issues)


def test_g2_reflection_emits_no_component(tmp_path: Path) -> None:
    # Given: a called factory uses dynamic reflection and module loading.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "import importlib",
                    "def get_store(module, name):",
                    "    loaded = importlib.import_module(module)",
                    "    return getattr(loaded, name)()",
                    "store = get_store('providers', 'Client')",
                ]
            )
            + "\n"
        },
    )

    # When/Then: reflection remains undetermined without component output.
    assert result.facts == []
    assert factories(result) == []


def test_g2_opaque_attribute_chain_emits_no_component(tmp_path: Path) -> None:
    # Given: a called function returns state hidden behind an attribute chain.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": (
                "def get_store(holder):\n"
                "    return holder.config.client\n"
                "store = get_store(settings)\n"
            )
        },
    )

    # When/Then: opaque state is not treated as a constructor.
    assert result.facts == []
    assert factories(result) == []


def test_g2_decorated_factory_emits_no_component(tmp_path: Path) -> None:
    # Given: a custom decorator may replace an annotated factory return value.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def registered_provider(fn):",
                    "    return fn",
                    "@registered_provider",
                    "def get_store() -> QdrantClient:",
                    "    return QdrantClient()",
                    "store = get_store()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: the provider stops before annotation or return inference.
    assert [fact.rule_id for fact in result.facts] == ["ast_external_import"]
    assert factories(result) == []


def test_g2_hop_cap_emits_warning_without_partial_guess(
    tmp_path: Path,
) -> None:
    # Given: a factory requires four delegate edges before construction.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def f4(): return QdrantClient()",
                    "def f3(): return f4()",
                    "def f2(): return f3()",
                    "def f1(): return f2()",
                    "def f0(): return f1()",
                    "store = f0()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: the fourth edge is fail-closed and explicitly counted.
    assert [fact.rule_id for fact in result.facts] == ["ast_external_import"]
    assert factories(result) == []
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_factory_hop_limit"
    ]


def test_g2_cycle_emits_warning_without_hanging(tmp_path: Path) -> None:
    # Given: two invoked factories delegate to each other forever at runtime.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "def first(): return second()",
                    "def second(): return first()",
                    "store = first()",
                ]
            )
            + "\n"
        },
    )

    # When/Then: cycle guard returns deterministically with no component fact.
    assert result.facts == []
    assert factories(result) == []
    assert [issue.rule_id for issue in result.issues] == [
        "ast_construction_factory_cycle"
    ]


def test_internal_root_comes_from_inventory_when_module_parse_fails(
    tmp_path: Path,
) -> None:
    # Given: an internal module exists in inventory but has invalid syntax.
    _, result = scan_project(
        tmp_path,
        {
            "clients.py": "def broken(:\n",
            "app.py": "from clients import LocalClient\n",
        },
    )

    # When/Then: parse failure does not reclassify an internal import as G3.
    assert imports(result) == []
    assert result.evidence == []
    assert [(item.file, item.rule_id) for item in result.issues] == [
        ("clients.py", "ast_construction_parse_error")
    ]


def test_transient_internal_module_absence_cannot_reclassify_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: both modules are approved, but one path is absent only during
    # pathname-based internal-module classification.
    project_root = tmp_path / "project"
    project_root.mkdir()
    app_path = project_root / "app.py"
    internal_path = project_root / "internal.py"
    moved_path = project_root / "internal-approved-moved.py"
    app_path.write_text("from internal import LocalClient\n", encoding="utf-8")
    internal_path.write_text(
        "class LocalClient:\n    pass\n", encoding="utf-8"
    )
    inventory = build_inventory(project_root, "app.py", "internal.py")
    original_resolve = AstConstructionProvider._resolve_inventory_path
    original_read = AstConstructionProvider._read_verified_source
    read_started = False

    def mark_read_started(
        cls: type[AstConstructionProvider],
        pinned_root: _PinnedProjectRoot,
        record: FileRecord,
    ) -> str:
        nonlocal read_started
        read_started = True
        return original_read(pinned_root, record)

    def hide_internal_before_reads(
        root: Path,
        relative_path: str,
    ) -> Path | None:
        if relative_path != "internal.py" or read_started:
            return original_resolve(root, relative_path)
        internal_path.rename(moved_path)
        try:
            return original_resolve(root, relative_path)
        finally:
            moved_path.rename(internal_path)

    monkeypatch.setattr(
        AstConstructionProvider,
        "_read_verified_source",
        classmethod(mark_read_started),
    )
    monkeypatch.setattr(
        AstConstructionProvider,
        "_resolve_inventory_path",
        staticmethod(hide_internal_before_reads),
    )

    # When: the scan completes after the approved path has been restored.
    result = AstConstructionProvider().collect(inventory)

    # Then: approved inventory membership remains the classification truth.
    assert imports(result) == []
    assert result.evidence == []
    assert result.issues == []
    assert internal_path.is_file()


def test_multiple_import_aliases_have_unique_evidence_ids(
    tmp_path: Path,
) -> None:
    # Given: two aliases for the same external symbol share one source line.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": (
                "from qdrant_client import "
                "QdrantClient as First, QdrantClient as Second\n"
                "first = First()\n"
                "second = Second()\n"
            )
        },
    )

    # When/Then: structural and evidence identities remain collision-free.
    assert len(imports(result)) == 2
    evidence_ids = [item.id for item in result.evidence]
    assert len(evidence_ids) == len(set(evidence_ids))


def test_g2_resolves_factory_call_nested_in_function_return(
    tmp_path: Path,
) -> None:
    # Given: a function passes a factory result into another return-time call.
    _, result = scan_project(
        tmp_path,
        {
            "app.py": "\n".join(
                [
                    "from qdrant_client import QdrantClient",
                    "def get_store():",
                    "    return QdrantClient()",
                    "def endpoint():",
                    "    return consume(get_store())",
                ]
            )
            + "\n"
        },
    )

    # When/Then: the nested factory call is inferred from function scope.
    inferred = factories(result)
    assert len(inferred) == 1
    assert inferred[0].caller == "app.endpoint"
    assert inferred[0].factory == "app.get_store"
    assert inferred[0].call_span.line_start == 5
