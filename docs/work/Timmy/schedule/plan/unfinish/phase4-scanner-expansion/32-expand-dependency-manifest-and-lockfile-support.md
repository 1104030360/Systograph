# Dependency Manifest and Lockfile Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 擴充 `DependencyManifestProvider`，讓 lockfile 與進階 manifest 語法成為 deterministic evidence。

**Architecture:** Provider 仍只做 static parse，不執行 package manager、不下載 dependency、不做完整 SBOM。Vulnerability awareness 必須獨立 opt-in，且不得成為預設 network access。

**Tech Stack:** Python stdlib parsers where possible, PyYAML, TOML parsing, pytest, existing rule catalog loader.

---

## 最新狀態（2026-06-18）

- Task 10 已完成基礎 dependency manifest provider。
- Task 12a 已完成 rule catalog externalization。
- `pyproject.toml` 目前沒有 Syft、pip-audit、OSV client 或 SBOM dependency。
- `uv.lock` 存在於本 repo，但 provider 尚未將 lockfile 作為 first-class deterministic evidence。

## Scope

- Parse `uv.lock`、`poetry.lock`、`package-lock.json`、`pnpm-lock.yaml`、`yarn.lock` 的 declared/resolved dependencies。
- Support `requirements.txt` `-r` include、`-c` constraints、`-e` editable、VCS URL name extraction within `FileInventory` boundary.
- Add `go.mod` / `go.sum` and `Cargo.toml` / `Cargo.lock` static parse if fixture coverage exists.
- Optional lightweight SBOM-like summary is local-only and declared-dependency-only.

## Out of scope

- 不執行 package manager。
- 不下載 dependency。
- 不掃 installed packages。
- 不做 license compliance。
- 不預設呼叫 OSV/pip-audit；network vulnerability awareness 需另設 opt-in plan。

### Task 1: Add lockfile parser tests

**Files:**
- Modify: `src/systograph/core/providers/dependency_manifest_provider.py`
- Test: `tests/unit/core/test_dependency_manifest_provider.py`
- Fixture: `tests/fixtures/rag_projects/dependency_lockfiles_rag/`

- [ ] **Step 1: Create minimal lockfile fixture**

Required files:

```text
uv.lock
poetry.lock
package-lock.json
pnpm-lock.yaml
requirements.txt
```

- [ ] **Step 2: Write failing tests for resolved dependency facts**

Expected fact shape:

```text
kind = dependency
provider = package manager ecosystem if known
name = package name
version = exact lockfile version when available
source_file = lockfile path
rule_id = dependency_lockfile_detected
```

- [ ] **Step 3: Implement parsers incrementally**

Parse only fields needed for scanner evidence. On malformed lockfile, emit parse issue and continue.

### Task 2: Support requirements include and VCS syntax safely

**Files:**
- Modify: `src/systograph/core/providers/dependency_manifest_provider.py`
- Test: `tests/unit/core/test_dependency_manifest_provider.py`

- [ ] **Step 1: Add failing tests for `-r`, `-c`, `-e`, and VCS URL**
- [ ] **Step 2: Resolve include targets only through `FileInventory` records**
- [ ] **Step 3: Reject include paths with absolute path, `..`, backslash, or outside-root symlink**
- [ ] **Step 4: Record unsupported/unsafe include as parse issue, not exception**

### Task 3: Add ecosystem manifests behind fixtures

**Files:**
- Modify: `src/systograph/core/rules/dependency_manifest_rules.toml`
- Modify: `src/systograph/core/providers/dependency_manifest_provider.py`
- Test: `tests/integration/test_phase10_dependency_manifest_provider_behaviors.py`

- [ ] **Step 1: Add `go.mod` and `Cargo.toml` synthetic fixture files**
- [ ] **Step 2: Add parser support for package/module names and version constraints**
- [ ] **Step 3: Ensure unsupported syntax becomes uncertainty evidence**

### Task 4: Add optional declared-dependency summary

**Files:**
- Modify: `src/systograph/core/models/scan.py`
- Modify: `src/systograph/core/services/project_scan_service.py`
- Test: `tests/unit/core/test_project_scan_service.py`

- [ ] **Step 1: Define a lightweight summary built from existing facts**
- [ ] **Step 2: Do not introduce CycloneDX/SPDX full schema in this task**
- [ ] **Step 3: Ensure summary excludes raw source, secrets, and local absolute paths**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Lockfile versions become deterministic evidence.
- Requirements includes are confined to `FileInventory` and cannot expand scan boundary.
- Malformed/unsupported dependency files do not fail the entire scan.
- No package manager or network call is executed.

