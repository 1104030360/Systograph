from __future__ import annotations

import json
import shutil
import subprocess
from errno import EACCES, EPERM
from pathlib import Path

import pytest

from kai_mind.core.models.errors import InventoryEnumerationError
from kai_mind.core.models.filesystem import (
    FileInventorySource,
    SkippedFile,
    SkipReason,
)
from kai_mind.core.models.inventory_policy import ScanInventoryPolicyCatalog
from kai_mind.core.providers.filesystem_provider import FilesystemProvider
from kai_mind.core.services.inventory_policy_matcher import (
    InventoryPolicyMatcher,
)
from kai_mind.core.services.scan_inventory_rule_loader import (
    ScanInventoryRuleLoader,
    ScanInventoryRulesError,
    ScanInventoryRulesErrorCode,
)


class StaticInventoryRuleLoader(ScanInventoryRuleLoader):
    def __init__(self, catalog: ScanInventoryPolicyCatalog) -> None:
        self._catalog = catalog

    def load_default(self) -> ScanInventoryPolicyCatalog:
        return self._catalog


class MissingInventoryRuleLoader(ScanInventoryRuleLoader):
    def load_default(self) -> ScanInventoryPolicyCatalog:
        raise ScanInventoryRulesError(ScanInventoryRulesErrorCode.UNAVAILABLE)


class FailingGitListProvider(FilesystemProvider):
    def _run_git(
        self,
        root: Path,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if args[:1] == ("rev-parse",):
            return subprocess.CompletedProcess(
                args=["git", *args],
                returncode=0,
                stdout="true\n",
                stderr="",
            )
        if args[:1] == ("ls-files",):
            raise subprocess.CalledProcessError(
                returncode=128,
                cmd=["git", *args],
                stderr="fatal: simulated git failure",
            )
        return super()._run_git(
            root,
            *args,
            input_text=input_text,
            check=check,
        )


class RecursiveOnlyProvider(FilesystemProvider):
    def _is_git_work_tree(self, root: Path) -> bool:
        del root
        return False


class FailingRecursiveFallbackProvider(FailingGitListProvider):
    def _recursive_candidates(
        self,
        root: Path,
        *,
        matcher: InventoryPolicyMatcher,
    ) -> tuple[list[str], list[SkippedFile]]:
        del root, matcher
        raise InventoryEnumerationError()


class UnreadableSizeProvider(FilesystemProvider):
    def _safe_size(self, path: Path) -> int | None:
        if path.name == "unreadable.txt":
            return None
        return super()._safe_size(path)


def run_git(
    project_root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=True,
        text=True,
        capture_output=True,
    )


def symlink_or_skip(link_path: Path, target_path: Path) -> None:
    try:
        link_path.symlink_to(target_path)
    except OSError as exc:
        if (
            exc.errno in {EACCES, EPERM}
            or getattr(exc, "winerror", None) == 1314
        ):
            pytest.skip("symlink privilege is unavailable on this platform")
        raise


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_inventory_includes_tracked_and_untracked_unignored_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    (project_root / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (project_root / "tracked.py").write_text(
        "tracked = True\n",
        encoding="utf-8",
    )
    run_git(project_root, "add", ".gitignore", "tracked.py")
    (project_root / "untracked.py").write_text(
        "untracked = True\n",
        encoding="utf-8",
    )
    (project_root / "ignored.py").write_text(
        "ignored = True\n",
        encoding="utf-8",
    )

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped_paths = {
        record.path: record.reason for record in inventory.skipped
    }
    assert inventory.source == FileInventorySource.GIT
    assert file_paths == {".gitignore", "tracked.py", "untracked.py"}
    assert skipped_paths["ignored.py"] == SkipReason.GITIGNORED
    assert all(not Path(path).is_absolute() for path in file_paths)


def test_recursive_inventory_for_non_git_zip_project_skips_noisy_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "node_modules" / "pkg").mkdir(parents=True)
    (project_root / ".venv").mkdir()
    (project_root / "dist").mkdir()
    (project_root / "models").mkdir()
    (project_root / "logs").mkdir()
    (project_root / "src" / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    (project_root / "node_modules" / "pkg" / "index.js").write_text(
        "module.exports = {};\n",
        encoding="utf-8",
    )
    (project_root / ".venv" / "pyvenv.cfg").write_text("", encoding="utf-8")
    (project_root / "dist" / "bundle.js").write_text(
        "x = 1;\n",
        encoding="utf-8",
    )
    (project_root / "models" / "llm.gguf").write_bytes(b"model")
    (project_root / "logs" / "scan.log").write_text(
        "x" * 40,
        encoding="utf-8",
    )
    (project_root / "binary.bin").write_bytes(b"abc\x00def")

    inventory = FilesystemProvider(max_file_size_bytes=16).build_inventory(
        project_root
    )

    assert inventory.source == FileInventorySource.RECURSIVE
    assert [record.path for record in inventory.files] == ["src/app.py"]
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert skipped["node_modules/"] == SkipReason.DEPENDENCY_DIRECTORY
    assert skipped[".venv/"] == SkipReason.VIRTUAL_ENV
    assert skipped["dist/"] == SkipReason.BUILD_OUTPUT
    assert skipped["models/llm.gguf"] == SkipReason.MODEL_WEIGHT
    assert skipped["logs/scan.log"] == SkipReason.LARGE_LOG
    assert skipped["binary.bin"] == SkipReason.BINARY


def test_recursive_inventory_honors_gitignore_double_star_rules(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    (project_root / "docs" / "deep").mkdir(parents=True)
    (project_root / "nested").mkdir()
    (project_root / ".gitignore").write_text(
        "**/secret.env\ndocs/**/*.log\n",
        encoding="utf-8",
    )
    (project_root / "secret.env").write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    (project_root / "nested" / "secret.env").write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    (project_root / "docs" / "scan.log").write_text(
        "scan log\n",
        encoding="utf-8",
    )
    (project_root / "docs" / "deep" / "scan.log").write_text(
        "scan log\n",
        encoding="utf-8",
    )
    (project_root / "src.py").write_text("print('ok')\n", encoding="utf-8")

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert file_paths == {".gitignore", "src.py"}
    assert skipped["secret.env"] == SkipReason.GITIGNORED
    assert skipped["nested/secret.env"] == SkipReason.GITIGNORED
    assert skipped["docs/scan.log"] == SkipReason.GITIGNORED
    assert skipped["docs/deep/scan.log"] == SkipReason.GITIGNORED


def test_recursive_inventory_honors_nested_gitignore_files(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "zip-project"
    service_root = project_root / "service"
    (service_root / "sub").mkdir(parents=True)
    (service_root / ".gitignore").write_text(
        ".env\n*.local\n!keep.local\nsub/*.log\n",
        encoding="utf-8",
    )
    (service_root / ".env").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "settings.local").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "keep.local").write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    (service_root / "sub" / "debug.log").write_text(
        "debug log\n",
        encoding="utf-8",
    )
    (service_root / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert file_paths == {
        "service/.gitignore",
        "service/app.py",
        "service/keep.local",
    }
    assert skipped["service/.env"] == SkipReason.GITIGNORED
    assert skipped["service/settings.local"] == SkipReason.GITIGNORED
    assert skipped["service/sub/debug.log"] == SkipReason.GITIGNORED


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_inventory_skips_tracked_symlink_to_file_outside_project(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside.env"
    outside_file.write_text(
        "placeholder=redacted\n",
        encoding="utf-8",
    )
    symlink_or_skip(project_root / "outside.env", outside_file)
    run_git(project_root, "init")
    run_git(project_root, "add", "outside.env")

    inventory = FilesystemProvider().build_inventory(project_root)

    file_paths = {record.path for record in inventory.files}
    skipped = {record.path: record.reason for record in inventory.skipped}
    assert inventory.source == FileInventorySource.GIT
    assert "outside.env" not in file_paths
    assert skipped["outside.env"] == SkipReason.SYMLINK_OUTSIDE_ROOT


def test_path_normalization_outputs_project_relative_posix_paths(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    source_file = project_root / "src" / "api.py"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("from fastapi import FastAPI\n", encoding="utf-8")

    provider = FilesystemProvider()

    assert (
        provider.normalize_project_relative_path(
            source_file,
            project_root=project_root,
        )
        == "src/api.py"
    )
    assert (
        provider.normalize_project_relative_path(
            Path("src\\api.py"),
            project_root=project_root,
        )
        == "src/api.py"
    )


def test_git_listing_failure_falls_back_to_recursive_inventory(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "src" / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )

    inventory = FailingGitListProvider().build_inventory(project_root)

    assert inventory.source == FileInventorySource.FALLBACK_AFTER_GIT_ERROR
    assert [record.path for record in inventory.files] == ["src/app.py"]
    assert inventory.warnings == ["git_enumeration_failed_fallback_used"]
    assert inventory.inventory_run_digest is not None
    recursive = RecursiveOnlyProvider().build_inventory(project_root)
    assert inventory.files == recursive.files
    assert inventory.inventory_run_digest != recursive.inventory_run_digest


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_tracked_ignored_file_is_git_mode_specific(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    (project_root / ".gitignore").write_text(
        "tracked.py\n",
        encoding="utf-8",
    )
    (project_root / "tracked.py").write_text(
        "tracked = True\n",
        encoding="utf-8",
    )
    run_git(project_root, "add", ".gitignore")
    run_git(project_root, "add", "-f", "tracked.py")

    git_inventory = FilesystemProvider().build_inventory(project_root)
    recursive_inventory = RecursiveOnlyProvider().build_inventory(project_root)

    assert "tracked.py" in {item.path for item in git_inventory.files}
    assert {item.path: item.reason for item in recursive_inventory.skipped}[
        "tracked.py"
    ] == SkipReason.GITIGNORED


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_private_exclude_is_not_recursive_project_source(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    run_git(project_root, "init")
    (project_root / ".git" / "info" / "exclude").write_text(
        "private.py\n",
        encoding="utf-8",
    )
    (project_root / "private.py").write_text(
        "private = True\n",
        encoding="utf-8",
    )

    git_inventory = FilesystemProvider().build_inventory(project_root)
    recursive_inventory = RecursiveOnlyProvider().build_inventory(project_root)

    assert "private.py" not in {item.path for item in git_inventory.files}
    assert "private.py" in {item.path for item in recursive_inventory.files}


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_configured_global_exclude_is_git_mode_specific(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    global_excludes = tmp_path / "global-excludes"
    global_excludes.write_text("global.py\n", encoding="utf-8")
    run_git(project_root, "init")
    run_git(
        project_root,
        "config",
        "core.excludesFile",
        str(global_excludes),
    )
    (project_root / "global.py").write_text(
        "global_value = True\n",
        encoding="utf-8",
    )

    git_inventory = FilesystemProvider().build_inventory(project_root)
    recursive_inventory = RecursiveOnlyProvider().build_inventory(project_root)

    assert "global.py" not in {item.path for item in git_inventory.files}
    assert "global.py" in {item.path for item in recursive_inventory.files}


def test_symlink_to_file_outside_project_is_skipped(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_file = tmp_path / "outside-secret.env"
    outside_file.write_text(
        "OPENAI_API_KEY=sk-test-example\n",
        encoding="utf-8",
    )
    symlink_or_skip(project_root / "outside.env", outside_file)

    inventory = FilesystemProvider().build_inventory(project_root)

    assert inventory.files == []
    assert inventory.skipped[0].path == "outside.env"
    assert inventory.skipped[0].reason == SkipReason.SYMLINK_OUTSIDE_ROOT


def test_provider_does_not_write_artifacts_to_project_root(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    before = sorted(path.name for path in project_root.iterdir())

    FilesystemProvider().build_inventory(project_root)

    after = sorted(path.name for path in project_root.iterdir())
    assert after == before


@pytest.mark.skipif(shutil.which("git") is None, reason="git is unavailable")
def test_git_and_recursive_apply_same_catalog_directory_policy(
    tmp_path: Path,
) -> None:
    git_root = tmp_path / "git-project"
    recursive_root = tmp_path / "recursive-project"
    for project_root in (git_root, recursive_root):
        (project_root / "src").mkdir(parents=True)
        (project_root / "node_modules" / "pkg").mkdir(parents=True)
        (project_root / "src" / "app.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (project_root / "node_modules" / "pkg" / "index.js").write_text(
            "module.exports = {};\n",
            encoding="utf-8",
        )
    run_git(git_root, "init")
    run_git(git_root, "add", "src/app.py", "node_modules/pkg/index.js")

    git_inventory = FilesystemProvider().build_inventory(git_root)
    recursive_inventory = FilesystemProvider().build_inventory(recursive_root)

    assert [item.path for item in git_inventory.files] == ["src/app.py"]
    assert [item.path for item in recursive_inventory.files] == ["src/app.py"]
    assert {item.path: item.reason for item in git_inventory.skipped}[
        "node_modules/pkg/index.js"
    ] == SkipReason.DEPENDENCY_DIRECTORY
    assert {item.path: item.reason for item in recursive_inventory.skipped}[
        "node_modules/"
    ] == SkipReason.DEPENDENCY_DIRECTORY


def test_recursive_policy_include_can_reverse_earlier_directory_exclude(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "node_modules" / "local").mkdir(parents=True)
    (project_root / "node_modules" / "other").mkdir(parents=True)
    (project_root / "node_modules" / "local" / "index.js").write_text(
        "export const local = true;\n",
        encoding="utf-8",
    )
    (project_root / "node_modules" / "other" / "index.js").write_text(
        "export const other = true;\n",
        encoding="utf-8",
    )
    catalog = _load_inventory_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.exclude.node_modules"
action = "exclude"
pattern = "node_modules/"
reason = "dependency_directory"
category = "dependency"
message = "Dependency directories are excluded by default."

[[path_rules]]
inventory_policy_id = "inventory.include.local_dependency"
action = "include"
pattern = "node_modules/local/**"
reason = "explicit_include"
category = "source"
message = "The local dependency is included."
""",
    )

    inventory = FilesystemProvider(
        inventory_rule_loader=StaticInventoryRuleLoader(catalog)
    ).build_inventory(project_root)

    assert [item.path for item in inventory.files] == [
        "node_modules/local/index.js"
    ]
    assert {item.path: item.reason for item in inventory.skipped}[
        "node_modules/other/index.js"
    ] == SkipReason.DEPENDENCY_DIRECTORY


def test_catalog_include_cannot_override_binary_safety(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "payload.bin").write_bytes(b"text\x00binary")
    catalog = _load_inventory_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.include.binary"
action = "include"
pattern = "*.bin"
reason = "explicit_include"
category = "source"
message = "Binary-looking files enter safety checks."
""",
    )

    inventory = FilesystemProvider(
        inventory_rule_loader=StaticInventoryRuleLoader(catalog)
    ).build_inventory(project_root)

    assert inventory.files == []
    assert inventory.skipped[0].reason == SkipReason.BINARY


def test_catalog_include_cannot_override_other_safety_boundaries(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    symlink_or_skip(project_root / "outside.txt", outside)
    (project_root / "large.txt").write_text("x" * 32, encoding="utf-8")
    (project_root / "unreadable.txt").write_text(
        "unreadable\n",
        encoding="utf-8",
    )
    catalog = _load_inventory_catalog(
        tmp_path,
        """
[[path_rules]]
inventory_policy_id = "inventory.include.all"
action = "include"
pattern = "*"
reason = "explicit_include"
category = "source"
message = "All candidates enter safety checks."
""",
    )

    inventory = UnreadableSizeProvider(
        max_file_size_bytes=16,
        inventory_rule_loader=StaticInventoryRuleLoader(catalog),
    ).build_inventory(project_root)

    assert inventory.files == []
    assert {item.path: item.reason for item in inventory.skipped} == {
        "large.txt": SkipReason.LARGE_FILE,
        "outside.txt": SkipReason.SYMLINK_OUTSIDE_ROOT,
        "unreadable.txt": SkipReason.UNREADABLE,
    }


def test_inventory_provenance_is_deterministic_and_auditable(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "dist").mkdir()
    (project_root / "src" / "app.py").write_text(
        "print('ok')\n",
        encoding="utf-8",
    )
    (project_root / "dist" / "bundle.js").write_text(
        "bundle\n",
        encoding="utf-8",
    )
    provider = FilesystemProvider()

    first = provider.build_inventory(project_root)
    second = provider.build_inventory(project_root)

    assert first.inventory_policy_schema_version == (
        "scan-inventory-policy/v1"
    )
    assert first.inventory_policy_digest is not None
    assert first.inventory_run_digest is not None
    assert first.inventory_run_digest == second.inventory_run_digest
    assert first.inventory_policy_audit == second.inventory_policy_audit
    assert [entry.path for entry in first.inventory_policy_audit] == [
        "dist/",
        "src/app.py",
    ]
    dist_entry, source_entry = first.inventory_policy_audit
    assert dist_entry.effective_inventory_policy_id == (
        "inventory.exclude.dist"
    )
    assert source_entry.reason == "included_by_default"
    audit_payload = json.dumps(
        [
            entry.model_dump(mode="json")
            for entry in first.inventory_policy_audit
        ]
    )
    assert str(project_root) not in audit_payload
    assert "print('ok')" not in audit_payload


def test_inventory_run_digest_changes_with_catalog_bytes(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")
    first_catalog = _load_inventory_catalog(
        tmp_path,
        _single_rule("dist/"),
        name="first.toml",
    )
    second_catalog = _load_inventory_catalog(
        tmp_path,
        _single_rule("dist/") + "\n",
        name="second.toml",
    )

    first = FilesystemProvider(
        inventory_rule_loader=StaticInventoryRuleLoader(first_catalog)
    ).build_inventory(project_root)
    second = FilesystemProvider(
        inventory_rule_loader=StaticInventoryRuleLoader(second_catalog)
    ).build_inventory(project_root)

    assert first.inventory_policy_digest != second.inventory_policy_digest
    assert first.inventory_run_digest != second.inventory_run_digest


def test_missing_inventory_catalog_fails_closed_before_inventory(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")

    with pytest.raises(
        ScanInventoryRulesError,
        match="inventory_rules_unavailable",
    ):
        FilesystemProvider(
            inventory_rule_loader=MissingInventoryRuleLoader()
        ).build_inventory(project_root)


def test_git_fallback_propagates_recursive_enumeration_failure(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(
        InventoryEnumerationError,
        match="inventory_enumeration_failed",
    ):
        FailingRecursiveFallbackProvider().build_inventory(project_root)


def _load_inventory_catalog(
    tmp_path: Path,
    rules: str,
    *,
    name: str = "inventory-rules.toml",
) -> ScanInventoryPolicyCatalog:
    path = tmp_path / name
    path.write_text(
        "schema_version = 'scan-inventory-policy/v1'\n" + rules,
        encoding="utf-8",
    )
    return ScanInventoryRuleLoader().load(path)


def _single_rule(pattern: str) -> str:
    return f"""
[[path_rules]]
inventory_policy_id = "inventory.exclude.test"
action = "exclude"
pattern = "{pattern}"
reason = "build_output"
category = "build"
message = "Build output is excluded by default."
"""
