# Persistent Session and Scan History Domain Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Phase2 Plan 03A 已凍結的 project/scan/build identity、repository ports與
atomic local JSON persistence之上，補齊可查詢的 session/history domain、retention與 bounded
cache行為，讓 Task 27只替換 storage adapter，不改 core service或 API語意。

**Architecture:** Phase2 Plan 03A擁有 stable `project_id`、immutable `scan_id` snapshot、
versioned `build_id` lineage、Apply command與 atomic local JSON repositories。Task 26延伸這些
ports建立 `SessionHistoryService`、history queries、retention與 bounded cache；web routes依賴
service，不依賴 `InMemorySessionStore` concrete type。PostgreSQL concrete adapter留給 Task 27。

**Tech Stack:** Python protocols, Pydantic v2, FastAPI dependency injection, pytest.

---

## 最新狀態（2026-07-05）

- `InMemorySessionStore` 同時承擔 project registry、latest map、build-result lookup，且無 TTL/容量上限。
- routes 直接 type-hint `InMemorySessionStore`。
- 無 history list/get routes、restart persistence、retention policy。
- GitHub issues：[#126](https://github.com/1104030360/Systograph/issues/126)、[#150](https://github.com/1104030360/Systograph/issues/150)、[#174](https://github.com/1104030360/Systograph/issues/174)。
- 本計畫必須在 Task 27 前完成；Task 27 只能實作 repository adapters 與 transaction wiring，不應再重新定義 project/scan domain。
- Phase2 Plan `03A-implement-apply-build-lineage-and-local-json-persistence.md` 已先定義
  `project_id`、`scan_id`、`build_id`、Apply/B1→B2 lineage、immutable artifacts與 atomic
  local JSON adapter。本計畫不得另建第二套 project registry、build identity或 local JSON
  persistence。

## Domain decisions

- Project record 不保存 raw source、secret 或完整 archive content。
- Scan record代表一次 read-only repo snapshot；build record代表從 snapshot產生的一組 artifacts。
- History保存 status、timestamps、safe error code、artifact reference/digest與
  `based_on_build_id`；不把 database當 canonical map。
- `ai_system_map.json` 仍是正式對外 artifact。
- local-only single-user 是預設；沒有 auth/namespace 前不得宣稱 multi-user。
- Retention 先定義 policy，再實作 DB deletion。
- Apply重用同一 `scan_id` snapshot並建立新 `build_id`；只有 explicit rescan才建立新
  `scan_id`。

### Phase2 03A ownership boundary

```text
Plan 03A owns
  project / scan snapshot / build lineage identities
  repository protocols required by Apply
  atomic local JSON persistence
  immutable build artifacts and latest-build switch

Task 26 owns
  list/get history use cases
  retention and bounded cache policy
  history API and session orchestration
  compatibility tests over the 03A repositories
```

### Task 1: Define domain models and repository ports

**Files:**
- Create: `src/systograph/core/models/session_history.py`
- Create: `src/systograph/core/repositories/session_history.py`
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

class BuildHistoryRepository(Protocol):
    def get(self, build_id: str) -> BuildHistoryRecord | None: ...
    def list_for_project(self, project_id: str) -> tuple[BuildHistoryRecord, ...]: ...
```

這些 history-facing protocols必須 adapter/extend Plan 03A repositories；不得使用不同
`run_id` 或另建不相容的 project/scan models。

- [ ] **Step 4: Run model tests**

### Task 2: Characterize Phase2 persistence and build bounded caches

**Files:**
- Modify: `src/systograph/web/session_store.py`
- Test: `tests/unit/web/test_session_store.py`

- [ ] **Step 1: Write compatibility tests against Plan 03A local JSON repositories and build lineage**
- [ ] **Step 2: Write red tests for max projects, scans/builds, eviction, and concurrent access**
- [ ] **Step 3: Split latest-viewer cache from durable project/scan/build repositories**
- [ ] **Step 4: Add lock-protected cache writes and deterministic LRU/retention behavior；不得重寫 03A atomic JSON commit**
- [ ] **Step 5: Run focused tests**

### Task 3: Introduce `SessionHistoryService`

**Files:**
- Create: `src/systograph/core/services/session_history_service.py`
- Test: `tests/unit/core/test_session_history_service.py`

- [ ] **Step 1: Write service behavior tests**
- [ ] **Step 2: Implement import, scan-start, scan-complete, scan-fail, list/get, and cleanup use cases**
- [ ] **Step 3: Ensure error summaries pass masking/path redaction before persistence**

### Task 4: Make web routes depend on abstractions

**Files:**
- Modify: `src/systograph/web/dependencies.py`
- Modify: `src/systograph/web/routes/project_routes.py`
- Modify: `src/systograph/web/routes/scan_routes.py`
- Create: `src/systograph/web/routes/history_routes.py`
- Modify: `src/systograph/web/app.py`
- Test: `tests/web/test_history_routes.py`

- [ ] **Step 1: Write route contract tests**
- [ ] **Step 2: Add `GET /api/projects`, `GET /api/projects/{id}`, `GET /api/projects/{id}/scans`, `GET /api/scans/{id}`, and project/build history reads**
- [ ] **Step 3: Keep current import/scan responses backward-compatible**
- [ ] **Step 4: Verify routes do not import ORM or storage-specific classes**

## Acceptance Criteria

- In-memory mode remains usable and bounded.
- API/service behavior can switch to PostgreSQL without changing domain contracts.
- History responses contain no raw source, full secret, or unmanaged absolute path.
- Retention behavior is deterministic and covered by tests.
- Task 27 only needs to implement repository adapters and transaction wiring.
- Routes depend on service/repository abstractions, not `InMemorySessionStore` concrete methods.
- Task 26 reuses Plan 03A `project_id`/`scan_id`/`build_id` and local JSON persistence；沒有第二套 `run_id` 或 Apply implementation。
