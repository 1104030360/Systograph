# Project Upload Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 安全接受 `.zip` / `.tar` 專案上傳，解壓到 KAI-Mind 管理的暫存 workspace，再沿用既有 project/scan pipeline。

**Architecture:** Upload ingestion 只負責接收、驗證、解壓與生命週期管理；不得直接呼叫 scanner provider。合法 archive 轉成受控 project record 後，仍經 `POST /api/scans`、scan boundary review 與 `MapBuildService`。

**Tech Stack:** FastAPI multipart upload, Python `zipfile` / `tarfile`, Pydantic v2, pytest.

---

## 最新狀態（2026-06-18）

- `ProjectImportRequest.source_type` 仍固定為 `local_path`。
- 尚無 upload route、archive extractor、temporary workspace manager 或 cleanup。
- 本計畫不是 Epic 1 blocker；GitHub issue：[#125](https://github.com/1104030360/Local-AI-Health-Doctor/issues/125)。
- 啟動前必須完成 #140、#142、#146、#147、#152 與 Task 26，否則 upload 會放大既有 path、decode、output、resource 與 retention 風險。
- 官方文件查證（2026-06-18）：Python 3.14 的 `tarfile` 預設 extraction filter 已改為 `data`，但文件仍提醒 extraction 發生 exception 後可能已部分寫入，需自行 cleanup；本 repo 支援 Python 3.11，因此此計畫不可依賴 3.14 預設防線，必須逐 entry 驗證並手動寫入。

## Scope

- 支援 `.zip` 與一般 `.tar`；不支援 remote URL、Git clone、encrypted archive。
- 逐 entry 驗證後手動寫入，不直接呼叫 `extractall()`。
- 拒絕 absolute path、`..`、drive/UNC path、symlink、hardlink、device file。
- 限制 upload bytes、展開後總 bytes、檔案數、單檔 bytes、目錄深度。
- workspace 由 service 管理，project record 只保存 safe metadata 與 workspace id。
- cleanup 不得刪除非 KAI-Mind 管理的目錄。

### Task 1: Define upload models and limits

**Files:**
- Create: `src/kai_mind/core/models/project_upload.py`
- Test: `tests/unit/core/test_project_upload_models.py`

- [ ] **Step 1: Write failing model tests**

```python
def test_upload_limits_reject_non_positive_values() -> None:
    with pytest.raises(ValidationError):
        ProjectUploadLimits(max_files=0)
```

- [ ] **Step 2: Add `ProjectUploadLimits`, `ProjectUploadResult`, and stable error codes**

Error codes:

```text
unsupported_archive
archive_path_unsafe
archive_entry_type_unsafe
upload_too_large
archive_expanded_too_large
archive_file_count_exceeded
archive_depth_exceeded
archive_cleanup_failed
```

- [ ] **Step 3: Run model tests**

```bash
.venv/bin/pytest tests/unit/core/test_project_upload_models.py -v
```

### Task 2: Implement safe archive extraction

**Files:**
- Create: `src/kai_mind/core/services/project_upload_ingestion_service.py`
- Modify: `src/kai_mind/core/services/path_safety_service.py`
- Test: `tests/unit/core/test_project_upload_ingestion_service.py`

- [ ] **Step 1: Write red tests for traversal, links, device entries, zip bomb limits, and cleanup**
- [ ] **Step 2: Normalize every entry to project-relative POSIX form before creating directories**
- [ ] **Step 3: Stream entry data while counting actual extracted bytes**
- [ ] **Step 4: Return a managed workspace handle; do not expose arbitrary local paths**
- [ ] **Step 5: Run focused tests**

```bash
.venv/bin/pytest tests/unit/core/test_project_upload_ingestion_service.py -v
```

### Task 3: Add upload route without creating a second scan pipeline

**Files:**
- Create: `src/kai_mind/web/routes/upload_routes.py`
- Modify: `src/kai_mind/web/app.py`
- Modify: `src/kai_mind/web/schemas.py`
- Modify: `src/kai_mind/web/session_store.py`
- Test: `tests/web/test_project_upload_routes.py`

- [ ] **Step 1: Write route tests for valid upload and every stable error code**
- [ ] **Step 2: Implement `POST /api/projects/upload`**
- [ ] **Step 3: Save `source_type="uploaded_archive"` through the same project repository port introduced by Task 26**
- [ ] **Step 4: Assert route source does not instantiate scanner providers**
- [ ] **Step 5: Run route tests**

```bash
.venv/bin/pytest tests/web/test_project_upload_routes.py -v
```

### Task 4: Add retention and documentation

**Files:**
- Modify: `src/kai_mind/core/services/session_history_service.py`
- Modify: `docs/API-GUIDE.md`
- Test: `tests/unit/core/test_session_history_service.py`

- [ ] **Step 1: Define cleanup on failed upload, explicit delete, and retention expiry**
- [ ] **Step 2: Document accepted formats, limits, local-only policy, and scan handoff**
- [ ] **Step 3: Verify no response/log contains archive content, secret, or unmanaged absolute path**

## Acceptance Criteria

- Unsafe archive entry is rejected before any write outside the managed workspace.
- Resource limits are enforced from streamed bytes, not archive header trust alone.
- Uploaded projects still pass boundary review and `MapBuildService`.
- Cleanup is idempotent and cannot delete user-owned directories.
- Full backend gates pass.

## Sources

- Python archive handling must follow the current standard-library security notes for `zipfile` and `tarfile`: https://docs.python.org/3/library/tarfile.html
- `docs/work/Timmy/schedule/fable-5/find-error/report/2026-06-12-backend-security-ai-findings.md`
