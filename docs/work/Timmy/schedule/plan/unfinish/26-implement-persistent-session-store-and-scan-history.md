# Persistent Session and Scan History Domain Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 先固定 project/session/scan history 的 domain contract、retention 與 repository ports，讓 Task 27 可以替換 storage adapter，而不改 core service 或 API 行為。

**Architecture:** Core 定義 domain models、repository protocols 與 `SessionHistoryService`；web routes 依賴 service，不依賴 `InMemorySessionStore` concrete type。第一階段仍以 bounded in-memory adapter 驗證行為，PostgreSQL concrete adapter 留給 Task 27。

**Tech Stack:** Python protocols, Pydantic v2, FastAPI dependency injection, pytest.

---

## 最新狀態（2026-06-18）

- `InMemorySessionStore` 同時承擔 project registry、latest map、build-result lookup，且無 TTL/容量上限。
- routes 直接 type-hint `InMemorySessionStore`。
- 無 history list/get routes、restart persistence、retention policy。
- GitHub issues：[#126](https://github.com/1104030360/Local-AI-Health-Doctor/issues/126)、[#150](https://github.com/1104030360/Local-AI-Health-Doctor/issues/150)、[#174](https://github.com/1104030360/Local-AI-Health-Doctor/issues/174)。
- 本計畫必須在 Task 27 前完成；Task 27 只能實作 repository adapters 與 transaction wiring，不應再重新定義 project/scan domain。

## Domain decisions

- Project record 不保存 raw source、secret 或完整 archive content。
- Scan record 保存 status、timestamps、safe error code、artifact reference/digest；不把 database 當 canonical map。
- `ai_system_map.json` 仍是正式對外 artifact。
- local-only single-user 是預設；沒有 auth/namespace 前不得宣稱 multi-user。
- Retention 先定義 policy，再實作 DB deletion。

### Task 1: Define domain models and repository ports

**Files:**
- Create: `src/kai_mind/core/models/session_history.py`
- Create: `src/kai_mind/core/repositories/session_history.py`
- Test: `tests/unit/core/test_session_history_models.py`

- [ ] **Step 1: Write failing tests for project/scan invariants and stable statuses**
- [ ] **Step 2: Define immutable domain models**
- [ ] **Step 3: Define repository protocols**

```python
class ProjectHistoryRepository(Protocol):
    def save(self, project: ProjectHistoryRecord) -> None: ...
    def get(self, project_id: str) -> ProjectHistoryRecord | None: ...
    def list(self) -> tuple[ProjectHistoryRecord, ...]: ...

class ScanHistoryRepository(Protocol):
    def save(self, scan: ScanHistoryRecord) -> None: ...
    def get(self, scan_id: str) -> ScanHistoryRecord | None: ...
    def list_for_project(self, project_id: str) -> tuple[ScanHistoryRecord, ...]: ...
```

- [ ] **Step 4: Run model tests**

### Task 2: Build bounded in-memory adapters

**Files:**
- Modify: `src/kai_mind/web/session_store.py`
- Test: `tests/unit/web/test_session_store.py`

- [ ] **Step 1: Write red tests for max projects, max scans, eviction, and concurrent access**
- [ ] **Step 2: Split latest-viewer cache from project/scan repositories**
- [ ] **Step 3: Add lock-protected atomic writes and deterministic LRU/retention behavior**
- [ ] **Step 4: Run focused tests**

### Task 3: Introduce `SessionHistoryService`

**Files:**
- Create: `src/kai_mind/core/services/session_history_service.py`
- Test: `tests/unit/core/test_session_history_service.py`

- [ ] **Step 1: Write service behavior tests**
- [ ] **Step 2: Implement import, scan-start, scan-complete, scan-fail, list/get, and cleanup use cases**
- [ ] **Step 3: Ensure error summaries pass masking/path redaction before persistence**

### Task 4: Make web routes depend on abstractions

**Files:**
- Modify: `src/kai_mind/web/dependencies.py`
- Modify: `src/kai_mind/web/routes/project_routes.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Create: `src/kai_mind/web/routes/history_routes.py`
- Modify: `src/kai_mind/web/app.py`
- Test: `tests/web/test_history_routes.py`

- [ ] **Step 1: Write route contract tests**
- [ ] **Step 2: Add `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/projects/{id}/scans`, `GET /api/scans/{id}`**
- [ ] **Step 3: Keep current import/scan responses backward-compatible**
- [ ] **Step 4: Verify routes do not import ORM or storage-specific classes**

## Acceptance Criteria

- In-memory mode remains usable and bounded.
- API/service behavior can switch to PostgreSQL without changing domain contracts.
- History responses contain no raw source, full secret, or unmanaged absolute path.
- Retention behavior is deterministic and covered by tests.
- Task 27 only needs to implement repository adapters and transaction wiring.
- Routes depend on service/repository abstractions, not `InMemorySessionStore` concrete methods.
