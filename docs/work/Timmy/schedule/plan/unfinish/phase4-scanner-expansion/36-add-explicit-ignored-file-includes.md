# Explicit Ignored File Includes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可明確指定少數被 `.gitignore` 排除的檔案進入 scan inventory，同時保留 binary、size、symlink、secret、boundary gate 防線。

**Architecture:** Default 行為仍尊重 `.gitignore`；include ignored files 是高風險 opt-in。Override 只作用於明確 project-relative path，不可成為「掃整個 ignored tree」的旁路。

**Tech Stack:** Existing `FilesystemProvider`, pathspec, Pydantic config models, pytest.

---

## 最新狀態（2026-06-18）

- Task 7 已完成 `.gitignore` / dependency / build / binary / symlink 等 hard skip。
- Task 24 已完成 same-run boundary review gate。
- GitHub #138、#146、#152 必須先完成；否則 include ignored files 會放大 secret、scan root 與 resource 風險。

## Scope

- 新增 explicit include config model，例如 `ScanInventoryPolicy(include_ignored_paths=[...])`。
- 只允許 project-relative POSIX path。
- Include 後仍套用 binary、size、symlink-outside-root、model-weight、large-log、secret-like boundary review。
- API/CLI 必須清楚顯示這是 opt-in。

## Out of scope

- 不預設掃描 gitignored files。
- 不支援 glob 掃整個 ignored tree 第一版。
- 不掃 `.git/`。
- 不繞過 hard skip。

### Task 1: Define include policy model

**Files:**
- Create: `src/kai_mind/core/models/scan_policy.py`
- Test: `tests/unit/core/test_scan_policy_model.py`

- [ ] **Step 1: Write tests for allowed and rejected paths**

Rejected:

```text
/absolute.env
../secret.env
foo\bar.env
.git/config
node_modules/package/.env
```

- [ ] **Step 2: Define immutable policy model**
- [ ] **Step 3: Normalize to project-relative POSIX paths**

### Task 2: Extend filesystem inventory behavior

**Files:**
- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Test: `tests/unit/core/test_filesystem_provider.py`

- [ ] **Step 1: Add fixture where `.gitignore` excludes `.env.example`**
- [ ] **Step 2: Assert default scan skips it**
- [ ] **Step 3: Assert explicit include adds it**
- [ ] **Step 4: Assert binary/large/symlink-outside-root remain skipped even when included**

### Task 3: Wire through scan route and map build service

**Files:**
- Modify: `src/kai_mind/core/models/map_build.py`
- Modify: `src/kai_mind/core/services/map_build_service.py`
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Test: `tests/web/test_project_scan_routes.py`
- Test: `tests/unit/core/test_project_scan_service.py`

- [ ] **Step 1: Add request schema for include paths**
- [ ] **Step 2: Pass policy to `FilesystemProvider` through core service boundary**
- [ ] **Step 3: Ensure scan boundary review still gates secret-like include targets**
- [ ] **Step 4: Keep `/api/map/build` behavior conservative or explicitly document if unsupported**

### Task 4: Add docs and warnings

**Files:**
- Modify: `docs/API-GUIDE.md`
- Modify: `frontend/API_CONTRACT.md`

- [ ] **Step 1: Document include behavior as opt-in**
- [ ] **Step 2: Document hard-skip precedence**
- [ ] **Step 3: Provide safe example using `.env.example`, not real `.env`**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_scan_policy_model.py tests/unit/core/test_filesystem_provider.py tests/web/test_project_scan_routes.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Default scanner still respects `.gitignore`.
- Explicit include can include only exact safe project-relative paths.
- Hard skips and boundary review still apply after include.
- No included file can leak raw secret or unmanaged absolute path.

