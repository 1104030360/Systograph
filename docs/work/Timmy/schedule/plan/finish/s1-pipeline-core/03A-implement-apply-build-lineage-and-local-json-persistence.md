# Apply Confirmations、Build Lineage 與 Local JSON Persistence Implementation Plan

> **2026-07-11 backend execution status：** project/scan/build identity、immutable
> snapshot、atomic local JSON、project locks、CAS latest、Apply replay、restart/history、Detail
> child 與 Trace binding 已完成並測試。Task 6 frontend Apply/version UI 已依使用者要求還原，
> frontend-only checkboxes 保持未完成；後端證據見
> `docs/work/Timmy/schedule/report/2026-07-11/2026-07-11-phase2-s1-pipeline-core-REP.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將一次 repo scan 與其後多次 map build 分開，讓使用者可在不重新掃描 repo 的情況下套用 confirmed mappings、建立可追溯的新分析版本，並以 Phase2 local JSON persistence 保存 project、scan snapshot、build lineage 與 manual mappings。

**Architecture:** `project_id` 識別本機專案，`scan_id` 識別一次 read-only repo 掃描與 immutable scan snapshot，`build_id` 識別從該 snapshot materialize 出來的一組完整 artifacts。對外採容易理解的 `POST /api/map-builds/{base_build_id}/apply` command；內部不得另寫 apply-specific graph/profile/readiness 邏輯，而必須呼叫共用 Map Build pipeline。Phase2 使用 repository protocols + atomic local JSON adapter，正式 database adapter 留在 Phase2 完成後。每個 project 使用獨立 cross-process file lock 保護 state mutation，`latest.json` 另帶單調遞增 revision 做 compare-and-swap；不可只靠單檔 `os.replace()` 推論多檔交易安全。

**Tech Stack:** Python 3.11、Pydantic v2、FastAPI、standard-library JSON/filesystem APIs、`filelock`（cross-platform project lock）、React、TypeScript、Zod、pytest。

## Contract source of truth

| 主題 | Source |
|---|---|
| Phase2 primary endpoints | `docs/API-GUIDE.md` §2 |
| `scan_id` / `build_id` / `based_on_build_id` / `build_reason` | `docs/MODEL-CONTRACT.md` Assessment scope & build lineage |
| `POST /api/map-builds/{base_build_id}/apply` | `docs/API-GUIDE.md` §2 Apply；response 欄位為 `viewer_load_result`（非 `viewer_payload`） |
| `ViewerLoadResult`（含巢狀 `graph_view_model`） | `docs/MODEL-CONTRACT.md` |
| Manual mapping HTTP contract | `docs/API-GUIDE.md` §5–6 |

Phase2 固定 `environment_id: "environment:default-static"`；所有 sibling artifacts 共用同一
scope triple。

---

## Confirmed Decisions（through 2026-07-05）

1. 正式拆分 `scan_id` 與 `build_id`，不再用語意模糊的單一 `run_id` 同時代表掃描與建構。
   `scan_id` 即一次 immutable `ScanSnapshot` 的 identity；Phase2 不新增 `snapshot_id`。
2. 同一個 `scan_id` 可產生多個 immutable builds：初次自動結果、套用確認後結果、Detail Scan enrichment 結果。
3. 使用者按鈕名稱使用 **「套用 N 項確認並建立新版本」**；輔助文案明確說明不會重新掃描專案。
4. 對外 API 名稱保留容易理解的 `apply`：`POST /api/map-builds/{base_build_id}/apply`。
5. Apply API 內部只是一個 Map Build use case；不得複製、直接 patch 或就地覆寫舊 `ai_system_map.json`。
6. Apply 使用既有 `ScanSnapshot`，不讀取 repo filesystem；真正重掃仍只由 `POST /api/scans` 執行。
7. Phase2 先用 local JSON persistence，不導入 database；後續 database 只能替換 repository adapter，不得重定義 domain/API contract。
8. Run A / Build B1 必須保留；Apply 建立 Build B2，並記錄 `based_on_build_id` 與 `applied_mapping_ids`。
9. 每個 build 的 capability assessment 必須綁定同一 `build_id` 與 environment/profile
   scope；Apply 後不得沿用 B1 的 stale status、activation 或 Mapping Completeness。
10. Project-scoped `POST /api/scans` 的 Scan Boundary 是正式 provider scan 前的 hard gate；
    boundary 未完成時不得建立 `ScanSnapshot`、Build 或 artifacts，也不得更新 latest viewer
    payload。
11. Boundary completion 不代表每次都要人工確認：沒有 proposals 時自動通過；有 proposals
    時必須收到每個 `target_path + fingerprint` 的完整 same-run decision 才能繼續。
12. Rebuild／Apply 從既有 `ScanSnapshot` 的 raw `ProjectScanResult` 開始，先 **Step 4-1
    bridge replay**，再 **Step 4-2 overlay confirmed mappings**，然後重算 normalization 與全部
    downstream artifacts；不得從舊 B1 的 normalized map 直接 patch，也不得重新執行
    filesystem/provider scan。
13. 依 Phase2 pipeline terminology，Apply **跳過 Step 3**，但仍重跑 Step 4～7：
    Step 4 使用 `component_bridge_registry.py` 重新 materialize repo component /
    unmapped / candidate input，並在 4-2 套用 confirmed manual mappings；Step 6 再重算
    10 planes / 52 reference node assessment。
14. 依 2026-07-07 UA 整合決策，Apply **不重跑 UA**：它只使用
    `ScanSnapshot.scan_result` 內已驗證的 deterministic structural facts / evidence 重跑
    Step 4～7。`ua-analysis-result` semantic internal sidecar 在 Phase2 僅隨 snapshot 保存，
    不重新 validate、不作 Step 6 assessment input。只有 explicit rescan 會建立新
    `scan_id` / snapshot 並重跑 UA。
15. 每個 project state directory 使用自己的 `.project.lock`；不同 project 不共用全域鎖。
    Lock 只涵蓋 latest/base re-check、repository mutation 與 pointer promotion，不得包住
    filesystem scan、UA、LLM、Step 4～7 materialization 或 render。
16. `latest.json` 必須帶 `revision`。任何 Apply／Detail Scan promotion 都要提交
    `expected_latest_build_id + expected_revision`；取得 lock 後重新讀取並 compare-and-swap，
    stale writer 回 `409 base_build_not_latest`，不得覆蓋較新的 latest。
17. 每個 build 先寫入獨一無二的 `output/{build_id}/` staging/publish 路徑並完成驗證；
    **不得對目錄執行 `os.replace()`**。`os.replace()` 只用於同目錄的單一 JSON temp file，
    最後在 project lock 內原子替換 `latest.json`。
18. 同 base build、相同 sorted mapping ids 與相同 mapping digests 的並發重試維持
    idempotent：最多一個 child build 成為 latest；另一個 request 回同一結果或明確 stale conflict，
    不得形成 lineage fork 或 lost update。

## 2026-07-07 UA 整合對齊

`ScanSnapshot` 的持久化內容必須包含 UA deterministic structural facts /
evidence；`ua-analysis-result` 是同 snapshot 的 reserved nullable internal sidecar slot。Apply 的重新 materialize 不讀 target
repo filesystem、不呼叫 UA subprocess、不重新執行 Systograph parity providers；它只使用
`ScanSnapshot.scan_result` 的 deterministic structural facts / evidence 重新 materialize 與
assessment。Semantic sidecar 在 Phase2 active path 不產生、不消費。Explicit rescan 才會走
Step 2 inventory enrichment、重跑 UA structural extraction 並產生新的 `scan_id`；該 `scan_id` 即識別新的
immutable `ScanSnapshot`，不另設 `snapshot_id`。

## Domain Model

```text
Project project:123
└── Scan scan:S1                         # 一次 filesystem/provider scan
    ├── Build build:B1                   # initial_scan
    ├── Build build:B2                   # apply_confirmations，based on B1
    └── Build build:B3                   # detail_scan，based on B2
```

### Identity boundary

| ID | 代表什麼 | 何時改變 |
|---|---|---|
| `project_id` | 本機專案 registry identity | 新專案或明確要求建立新 identity |
| `scan_id` | 一次 repo inventory + provider collection + immutable snapshot | 只有重新掃描 repo 才改變 |
| `build_id` | 從 snapshot 產生的一組完整、同版本 artifacts | initial build、apply、detail enrichment 都建立新 ID |
| `mapping_id` | 一筆 durable review decision | 建立 decision 時產生；更新維持同 ID |

不得同時增加 `run_id`、`previous_run_id` 與 `based_on_run_id`。Active contract 統一使用：

```text
scan_id
build_id
based_on_build_id
```

### Required build lineage

```json
{
  "project_id": "project:123",
  "scan_id": "scan:S1",
  "build_id": "build:B2",
  "based_on_build_id": "build:B1",
  "build_reason": "apply_confirmations",
  "applied_mapping_ids": ["mapping:abc", "mapping:def"],
  "generated_at": "2026-07-04T10:30:00Z"
}
```

`build_reason` Phase2 enum：

```text
initial_scan
apply_confirmations
detail_scan
```

## Scan Boundary Completion Gate

本節適用於正式 project-session flow：`POST /api/scans`。Scan Boundary preflight 可以建立
inventory 並辨識敏感／不確定 targets，但在 boundary completion 之前不得進入正式 provider
collection。

```text
POST /api/scans
  -> scan boundary preflight
       |-- no decision proposals
       |     -> boundary complete automatically
       |     -> provider scan -> persist ScanSnapshot S1 -> initial Build B1
       |
       `-- one or more decision proposals
             -> return requires_boundary_decision
             -> no provider scan
             -> no persisted ScanSnapshot / Build / artifacts / latest update
             -> client submits all same-run boundary_decisions
                  |-- complete and fingerprint-matched
                  |     -> provider scan -> persist ScanSnapshot S1 -> initial Build B1
                  `-- missing, invalid, or stale
                        -> return requires_boundary_decision again
                        -> remain blocked before provider scan
```

Boundary completion rules：

- 沒有 proposal 時視為已完成，不顯示多餘的人工確認步驟。
- deterministic hard-skip 的 large、binary、generated、cache、model-weight 等 targets 不產生
  proposal；它們保留在 skipped audit trail。
- 有 proposal 時，request 必須涵蓋每一個 proposal，且 `target_path + fingerprint` 必須相符；
  每項 action 只能是 `scan_this_run` 或 `skip_this_run`。
- Decisions 只套用於本次 scan，不保存成下次 scan 的長期偏好。Explicit rescan 必須重新跑
  boundary preflight；內容或 metadata 改變造成 fingerprint stale 時也必須重新確認。
- `requires_boundary_decision` 是等待使用者完成 scope decision，不是 scan error；此狀態下
  `build_result` 必須為空，且不得留下看似成功或可載入的半成品。
- Legacy viewer demo `POST /api/map/build` 目前是 compatibility path，不得被文件或前端描述成
  已套用上述 project-scoped boundary gate。

## Apply Semantics

Apply 必須從 `ScanSnapshot` 重跑 materialization，不得重跑 filesystem/provider scan、UA sidecar 或 parity providers，也不得直接修改 B1 JSON：

```text
ScanSnapshot S1
  + scan_result deterministic structural facts / evidence
  + ua-analysis-result internal sidecar（保存但 Phase2 不消費）
  + confirmed mappings selected by mapping_id
  -> Step 4-1 component bridge replay           # raw facts -> component / unmapped / candidate input
  -> Step 4-2 apply confirmed mappings          # overlay durable decisions; same snapshot
  -> canonical normalization / validate
  -> edge/flow derivation
  -> profile inference（Step 6-1；含 Mapping Completeness 重算）
  -> readiness + static execution artifacts
  -> GraphViewModel projection
  -> Markdown / Mermaid / sibling JSON artifacts
  -> cross-reference validation
  -> immutable Build B2
```

### Pipeline restart boundary

`ScanSnapshot.scan_result` 保存正式 scan 產生的 raw `ProjectScanResult`，並以 internal
sidecar 保存同次 UA `ua-analysis-result`。它不是已完成 mapping 的 canonical map，因此
Rebuild／Apply 必須從 **Step 4-1 bridge replay** 開始，再 **Step 4-2 overlay confirmed
mappings**；不能跳到 normalization-only，也不能沿用 B1 的 component、edge、assessment
或 projection 結果。

| Operation | 起點 | Filesystem/provider scan | Component detection | Identity result |
|---|---|---:|---:|---|
| Initial scan | boundary-complete scan request | 執行一次 | 執行 | 新 `scan_id` + 新 `build_id` |
| Rebuild / Apply | 既有 `ScanSnapshot` + confirmed mappings | 不執行 | **4-1 replay → 4-2 overlay** | 相同 `scan_id` + 新 `build_id` |
| Explicit rescan | 新的 boundary preflight | 重新執行 | 執行 | 新 `scan_id` + 新 `build_id` |

```text
Initial scan / explicit rescan
  boundary complete
    -> filesystem inventory + provider collection
    -> persist raw ScanSnapshot
    -> Step 4-1 component bridge（initial scan 亦走 bridge registry）
    -> endpoint / risk / edge / flow derivation
    -> normalize + validate
    -> downstream assessment / projection / artifacts

Rebuild / Apply
  load existing ScanSnapshot
    + resolve validated confirmed mappings
    -> Step 4-1 component bridge replay           # raw facts -> component / unmapped / candidate input
    -> Step 4-2 apply confirmed mappings          # same snapshot, new decisions
    -> endpoint / risk / edge / flow derivation
    -> normalize + validate
    -> Step 6 recompute capability assessment
    -> Step 7 recompute projection / artifacts
    -> atomically publish immutable Build B2
```

Rebuild 必須重新計算 profile/capability assessment、activation、Mapping Completeness、
static execution、readiness、GraphViewModel 與所有輸出 artifacts。不得只更新被 mapping
直接影響的 JSON 欄位，否則會留下跨 build 的 stale
derived state。

Decision type effects：

- `existing_slot_mapping`：從 matching `unmapped_components` 移除，materialize 到 applicable canonical component/grounding target，重新計算 downstream artifacts。
- `non_baseline_capability_candidate`：從 review queue 移除，materialize 到 `profile_signals.json.capability_candidate_components`；不得直接加入 canonical topology，也不得單靠 confirmed candidate 將 profile 升為 `detected`。
- `rejected` / `not_applicable` / `skip_for_now`：不得成為 `applied_mapping_ids`；review queue/readiness warning 如何保留依 Plan 01 contract 處理。

## Local JSON Layout

Default state root：

```text
${SYSTOGRAPH_STATE_DIR:-~/.systograph}/projects/{project_id}/
├── project.json
├── mappings/
│   └── {mapping_id}.json
├── scans/
│   └── {scan_id}/
│       ├── manifest.json
│       └── snapshot.json
├── builds/
│   └── {build_id}/
│       └── manifest.json
└── latest.json
```

`latest.json` 最少包含：

```json
{
  "project_id": "project:123",
  "latest_build_id": "build:B2",
  "revision": 2,
  "updated_at": "2026-07-08T10:30:00Z"
}
```

Lock path 固定為同 project 目錄下的 `.project.lock`。Lock file 只做協調，不得寫入 secret、
project path、mapping 內容或 artifact payload。

Product artifacts 仍寫入 build output directory；state store 只保存 safe metadata、snapshot、artifact references/digests 與 decisions，不建立第二份 canonical map truth。

```text
output/{build_id}/
├── ai_system_map.json
├── evidence_table.json
├── profile_signals.json
├── readiness_report.json
├── call_graph.json
├── dataflow_hints.json
├── execution_paths.json
├── ai_system_map.md
├── system_map.mmd
└── execution_map.mmd
```

## API Contract

### Apply confirmed mappings

```http
POST /api/map-builds/{base_build_id}/apply
```

Request：

```json
{
  "mapping_ids": ["mapping:abc", "mapping:def"]
}
```

Response：

```json
{
  "project_id": "project:123",
  "scan_id": "scan:S1",
  "build_id": "build:B2",
  "based_on_build_id": "build:B1",
  "build_reason": "apply_confirmations",
  "applied_mapping_ids": ["mapping:abc", "mapping:def"],
  "build_result": {},
  "viewer_load_result": {}
}
```

Validation rules：

- `base_build_id` 必須存在且屬於同一 project。
- Phase2 採 linear history；base build 不是 project latest build 時回 `409 base_build_not_latest`，不建立 branch。
- 每個 `mapping_id` 必須存在、屬於同一 project、`decision="confirmed"`，且 evidence ids 必須存在於 source snapshot。
- 空陣列、重複 mapping ids、跨 project ids 回 `422`。
- 相同 base build + 相同 sorted mapping ids + 相同 mapping digests 的重試必須 idempotent，回傳既有 build，不重複建立 B2。
- 只有全部 artifacts validate 且 atomic publish 成功後，才更新 project `latest_build_id` 與 latest `viewer_load_result`（legacy `GET /api/map` 的 `ViewerPayload` 僅 compatibility）。
- 任一階段失敗時保留 B1 為 latest，不留下可被載入的 partial B2。

### Read builds

```http
GET /api/map-builds/{build_id}
GET /api/projects/{project_id}/map-builds
GET /api/projects/{project_id}/map-builds/latest
```

`GET /api/map-builds/{build_id}` 與 project latest route 必須回同一個 build-scoped typed
response：包含 request 所指定或解析出的 `project_id`、`scan_id`、`build_id`、lineage、
`ViewerLoadResult` 與 backend 產生的 `GraphViewModel`。不得在查不到 requested build 時 fallback
到 process-wide latest。`GET /api/projects/{project_id}/map-builds` 只回 immutable build
summaries，不混入其他 project，也不回傳 filesystem path。

Profile sidecar missing / invalid 時，read route 仍回可載入的 base graph 與穩定 warning /
degraded state；只有 canonical map missing / invalid 或 project-build identity mismatch 才 fail
closed。Route tests 必須覆蓋 project latest、指定歷史 build、unknown build、cross-project build、
sidecar degraded load 與 deterministic history ordering。

`GET /api/map` 暫時保留 compatibility，回傳 process-wide latest `ViewerPayload`（內層
`viewer_load_result`）；Phase2 正式 workflow 應優先使用 Apply response 的
`viewer_load_result` 或 project-scoped latest route，避免 process-wide latest 混用。

## Implementation Tasks

### Task 1: Define Scan and Build Identity Models

**Files:**
- Create: `src/systograph/core/models/analysis_history.py`
- Modify: `src/systograph/core/models/map_build.py`
- Modify: `src/systograph/core/models/scan.py`
- Test: `tests/unit/core/test_analysis_history_models.py`

- [ ] **Step 1: Write failing model tests**

```python
def test_apply_build_requires_parent_and_mapping_ids() -> None:
    build = MapBuildLineage(
        project_id="project:demo",
        scan_id="scan:s1",
        build_id="build:b2",
        based_on_build_id="build:b1",
        build_reason="apply_confirmations",
        applied_mapping_ids=["mapping:m1"],
        generated_at="2026-07-04T10:30:00Z",
    )
    assert build.scan_id == "scan:s1"


def test_initial_build_rejects_parent_build() -> None:
    with pytest.raises(ValidationError):
        MapBuildLineage(
            project_id="project:demo",
            scan_id="scan:s1",
            build_id="build:b1",
            based_on_build_id="build:older",
            build_reason="initial_scan",
            applied_mapping_ids=[],
            generated_at="2026-07-04T10:30:00Z",
        )
```

- [ ] **Step 2: Run tests and verify RED**

```bash
.venv/bin/pytest tests/unit/core/test_analysis_history_models.py -q
```

Expected: collection fails because `analysis_history.py` does not exist.

- [ ] **Step 3: Implement strict Pydantic models**

Define:

```python
BuildReason = Literal["initial_scan", "apply_confirmations", "detail_scan"]

class ScanSnapshot(AnalysisHistoryModel):
    schema_version: Literal["scan-snapshot/v1"] = "scan-snapshot/v1"
    project_id: str
    scan_id: str
    generated_at: str
    inventory_digest: str
    scan_result: ProjectScanResult
    ua_analysis_result: UaAnalysisResult | None = None  # internal sidecar, not public artifact

class MapBuildLineage(AnalysisHistoryModel):
    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str | None = None
    build_reason: BuildReason
    applied_mapping_ids: list[str] = Field(default_factory=list)
    generated_at: str
```

Add model validation so `initial_scan` requires no parent/no mappings and `apply_confirmations` requires parent/non-empty unique mappings.

- [ ] **Step 4: Extend `MapBuildResult` with one required lineage object for successful project-scoped builds**

Use a nested `lineage: MapBuildLineage | None` during compatibility migration rather than duplicating every field across response models. Strict project-scoped scan/apply paths require it; legacy `/api/map/build` may return `lineage=None` until its wrapper migration is complete.

- [ ] **Step 5: Run model tests and type checks**

```bash
.venv/bin/pytest tests/unit/core/test_analysis_history_models.py -q
.venv/bin/mypy src/systograph/core/models
```

Expected: PASS.

### Task 2: Introduce Repository Ports and Atomic Local JSON Adapter

**Files:**
- Create: `src/systograph/core/repositories/__init__.py`
- Create: `src/systograph/core/repositories/analysis_history.py`
- Create: `src/systograph/core/providers/local_json_state_provider.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Test: `tests/unit/core/test_local_json_state_provider.py`
- Test: `tests/integration/test_local_json_concurrency.py`

- [ ] **Step 1: Write failing repository behavior tests**

Cover:

```python
def test_state_survives_provider_recreation(tmp_path: Path) -> None:
    first = LocalJsonStateProvider(tmp_path)
    first.save_mapping(confirmed_mapping())

    second = LocalJsonStateProvider(tmp_path)
    assert second.get_mapping("mapping:m1") == confirmed_mapping()


def test_latest_build_update_is_atomic(tmp_path: Path) -> None:
    provider = LocalJsonStateProvider(tmp_path)
    provider.save_build_manifest(build_manifest("build:b1"))
    provider.set_latest_build("project:demo", "build:b1")
    assert provider.get_latest_build_id("project:demo") == "build:b1"
```

Also test corrupted JSON, duplicate IDs, cross-project lookup, path traversal IDs, interrupted temp file, deterministic sorted serialization, stale revision, lock timeout, two concurrent Apply promotions, and concurrent writes to two different projects.

- [ ] **Step 2: Define storage-neutral repository protocols**

```python
class ProjectRepository(Protocol): ...
class ScanSnapshotRepository(Protocol): ...
class MapBuildRepository(Protocol): ...
class ManualMappingRepository(Protocol): ...
```

Do not expose filesystem `Path` operations through service interfaces. Database adapters added later must implement the same protocols.

`MapBuildRepository` 的 latest promotion 必須表達 CAS，而不是拆成可競爭的 `get()` + `set()`：

```python
def promote_latest_build(
    self,
    *,
    project_id: str,
    build_id: str,
    expected_latest_build_id: str | None,
    expected_revision: int,
) -> LatestBuildPointer: ...
```

- [ ] **Step 3: Implement atomic JSON writes**

Write to a temporary file in the same directory, flush/fsync, then `os.replace()`. Reject IDs containing `/`, `\\`, `..`, NUL, or values outside the typed ID prefixes. `os.replace()` 的 source 與 destination 都必須是 regular file；禁止把 build/staging directory 當 replacement target。

- [ ] **Step 4: Add project-scoped cross-process locking and CAS**

Use `filelock.FileLock` at `{project_dir}/.project.lock`. Acquire only around project-state
read-modify-write sections；取得後重新讀 `latest.json`，驗證 expected base/revision，再 promotion。
Lock timeout 回 stable `project_state_busy` domain error；不得退化成無鎖寫入。不同 project 的 lock
必須可並行。

- [ ] **Step 5: Apply snapshot safety before persistence**

Before writing `snapshot.json`, use `SecretMaskingService`, relative-path normalization, and `SnapshotSafetyService`. The persisted snapshot must not contain full secrets or unmanaged absolute paths. `project.json` may retain the local project path only inside the local state adapter; API serializers must not expose it by default.

- [ ] **Step 6: Run tests**

```bash
.venv/bin/pytest tests/unit/core/test_local_json_state_provider.py tests/integration/test_local_json_concurrency.py tests/contracts/test_secret_snapshot_safety.py -q
```

Expected: PASS.

### Task 3: Separate Filesystem Scan from Snapshot Materialization

**Files:**
- Create: `src/systograph/core/services/scan_snapshot_service.py`
- Modify: `src/systograph/core/services/map_build_service.py`
- Modify: `src/systograph/web/routes/scan_routes.py`
- Test: `tests/integration/test_scan_snapshot_materialization.py`

- [ ] **Step 1: Write a characterization test proving current `POST /api/scans` performs provider collection once**

Use injected counting inventory/provider doubles. The target architecture must not preserve the current duplicate inventory construction between the route preflight and `ProjectScanService.scan()`.

Add a boundary state matrix：

| Case | Expected provider calls | Expected persisted result |
|---|---:|---|
| no proposals | 1 | one `ScanSnapshot` and initial B1 |
| unresolved proposals | 0 | no snapshot, build, artifacts, or latest update |
| complete matching decisions | 1 | one `ScanSnapshot` and initial B1 |
| missing decision or stale fingerprint | 0 | `requires_boundary_decision` again; no partial result |

Tests must verify all proposals are returned together and the formal scan cannot start after only a
subset has been decided.

- [ ] **Step 2: Write failing snapshot reuse test**

```python
def test_second_build_reuses_snapshot_without_scanning_filesystem() -> None:
    snapshot = snapshot_service.scan_and_save(...)
    first = map_build_service.build_from_snapshot(snapshot, ...)
    second = map_build_service.build_from_snapshot(
        snapshot,
        based_on_build_id=first.lineage.build_id,
        mapping_ids=["mapping:m1"],
    )
    assert counting_scan_provider.calls == 1
    assert second.lineage.scan_id == first.lineage.scan_id
    assert second.lineage.build_id != first.lineage.build_id
```

The same test must use a counting component bridge replay hook and assert Step 4-1 runs once for B1
and replays once for B2 (with 4-2 overlay), while the filesystem/provider scan count remains one. It must also assert that
B2 recomputes downstream assessment, projection, completeness, and artifact refs instead of reusing B1
derived objects.

Gate-1 另外必須新增兩個明確使用 `ua_analysis_result=None` 的 regression tests：

```python
def test_initial_build_succeeds_without_ua_sidecar() -> None: ...

def test_apply_replays_toml_snapshot_without_ua_sidecar() -> None: ...
```

兩者都必須證明 Phase A TOML-primary snapshot 可完成 Step 4～7、產生一致 lineage 與原子
artifacts；Apply 維持相同 `scan_id`、建立新 `build_id`，且不呼叫 UA、filesystem scan 或
parity providers。

- [ ] **Step 3: Extract `MapBuildService.build_from_snapshot(...)`**

The method consumes `ScanSnapshot`, validated confirmed mappings, output run, build reason, and parent build. It owns all downstream component/edge/readiness/profile/static-execution/projection/report materialization. It must not call `ProjectScanService.scan()`.

- [ ] **Step 4: Keep current `build(...)` as compatibility orchestration**

Current CLI and `/api/map/build` may continue calling `build(...)`; internally it performs `scan_and_save()` followed by `build_from_snapshot()`. Do not duplicate normalization or writers.

- [ ] **Step 5: Update project-scoped `/api/scans`**

After boundary decisions are complete, create one persisted `ScanSnapshot`, then create initial Build B1 with `build_reason="initial_scan"`. If the gate returns `requires_boundary_decision`, return before `scan_and_save()` and prove that snapshot/build repositories, artifact writers, and latest pointers were not mutated.

- [ ] **Step 6: Run integration tests**

```bash
.venv/bin/pytest tests/integration/test_scan_snapshot_materialization.py tests/web/test_project_scan_routes.py tests/web/test_scan_boundary_routes.py -q
```

Expected: PASS and provider collection count remains one per completed scan.

### Task 4: Implement Apply Command over the Shared Build Pipeline

**Files:**
- Create: `src/systograph/core/services/apply_confirmations_service.py`
- Create: `src/systograph/web/routes/map_build_routes.py`
- Modify: `src/systograph/web/schemas.py`
- Modify: `src/systograph/web/app.py`
- Test: `tests/unit/core/test_apply_confirmations_service.py`
- Test: `tests/web/test_map_build_apply_routes.py`

- [ ] **Step 1: Write failing service tests**

Cover successful B1→B2, unconfirmed mapping, cross-project mapping, unknown/stale base, evidence not present in snapshot, repeated request idempotency, concurrent same-base Apply, and build failure preserving B1 as latest. The successful path must prove that Apply resolves the original snapshot, replays **4-1 bridge → 4-2 overlay** with the selected mappings, recomputes every downstream artifact, keeps the same `scan_id`, creates a new `build_id`, and never calls filesystem/provider scan。並發測試必須證明 lock 內會重新讀 base/revision，最多一個 child promotion 成功，另一個 request 不會覆蓋 latest 或建立 lineage fork。

- [ ] **Step 2: Implement `ApplyConfirmationsService.apply(...)`**

```python
def apply(
    self,
    *,
    base_build_id: str,
    mapping_ids: tuple[str, ...],
) -> ApplyConfirmationsResult:
    ...
```

The service validates command inputs, resolves source snapshot, and calls `MapBuildService.build_from_snapshot(...)`. It must not know component, profile, readiness, graph, Markdown, Mermaid, or artifact writer details.

- [ ] **Step 3: Add API models**

```python
class ApplyConfirmationsRequest(WebSchema):
    mapping_ids: list[str] = Field(min_length=1)

class ApplyConfirmationsResponse(WebSchema):
    project_id: str
    scan_id: str
    build_id: str
    based_on_build_id: str
    build_reason: Literal["apply_confirmations"]
    applied_mapping_ids: list[str]
    build_result: Phase2MapBuildResult  # 見 docs/API-GUIDE.md
    viewer_load_result: ViewerLoadResult  # 見 docs/MODEL-CONTRACT.md；內含 graph_view_model
```

- [ ] **Step 4: Add `POST /api/map-builds/{base_build_id}/apply`**

Map domain errors to explicit statuses: 404 unknown build/mapping, 409 stale base/revision, 422 invalid decision/evidence, 503 `project_state_busy`, 500 safe build failure. Do not update latest pointers before successful atomic publish/CAS promotion.

- [ ] **Step 5: Add read routes**

Implement build-by-id, project build list, and project latest routes using repository interfaces.
Build-by-id 與 project latest 使用同一個 typed build-scoped response，明確帶
`project_id` / `scan_id` / `build_id` / lineage / `ViewerLoadResult` / `GraphViewModel`；history
list 只回 immutable summaries。Sort history by `generated_at`, then `build_id` as deterministic
tie-breaker，並拒絕 cross-project lookup 或 process-wide latest fallback。

- [ ] **Step 6: Run service and route tests**

```bash
.venv/bin/pytest tests/unit/core/test_apply_confirmations_service.py tests/web/test_map_build_apply_routes.py -q
```

Expected: PASS.

### Task 5: Persist Stable Project Identity and Manual Mappings

**Files:**
- Modify: `src/systograph/web/session_store.py`
- Modify: `src/systograph/core/services/manual_mapping_service.py`
- Modify: `src/systograph/web/routes/project_routes.py`
- Modify: `src/systograph/web/dependencies.py`
- Modify: `src/systograph/web/app.py`
- Test: `tests/web/test_local_json_restart_recovery.py`

- [ ] **Step 1: Write failing restart recovery tests**

```python
def test_project_mapping_and_latest_build_survive_app_restart(tmp_path: Path) -> None:
    first = create_app(state_dir=tmp_path)
    project_id = import_project(first)
    mapping_id = save_confirmed_mapping(first, project_id)
    build_id = apply_mapping(first, project_id, mapping_id)

    second = create_app(state_dir=tmp_path)
    assert get_project(second, project_id).status_code == 200
    assert list_mappings(second, project_id)[0]["mapping_id"] == mapping_id
    assert latest_build(second, project_id)["build_id"] == build_id
```

- [ ] **Step 2: Move app wiring to repository protocols**

`ManualMappingService` must receive the shared local JSON repository instance. Routes must stop type-hinting `InMemorySessionStore` where durable project/build lookup is required.

- [ ] **Step 3: Implement re-import reuse**

Compute a local-only canonical path digest. Importing the same resolved path returns the existing active `project_id` with `reused=true`; it must not silently merge two different paths with the same project name. Keep an explicit future escape hatch for creating a new identity, but do not implement branching UX in this plan.

- [ ] **Step 4: Preserve compatibility**

Existing import response fields remain; add `reused: bool = false` as backward-compatible output. Existing in-memory adapter remains available for isolated unit tests.

- [ ] **Step 5: Run restart/re-import tests**

```bash
.venv/bin/pytest tests/web/test_local_json_restart_recovery.py tests/web/test_mapping_routes.py tests/web/test_project_scan_routes.py -q
```

Expected: PASS.

### Task 6: Implement Frontend Apply and Version State

**Files:**
- Modify: `frontend/src/types.ts`
- Create: `frontend/src/services/mapBuildApi.ts`
- Modify: `frontend/src/components/proposal/ProposalModal.tsx`
- Modify: `frontend/src/store/viewerStore.ts`
- Modify: `frontend/src/hooks/useViewerPayload.ts`
- Modify: `frontend/src/wording.ts`
- Test: `frontend/src/services/mapBuildApi.test.ts`
- Test: `frontend/src/components/proposal/ProposalModal.test.tsx`

- [ ] **Step 1: Add Zod contracts for build lineage and apply response**

Reject missing/mismatched `scan_id`, `build_id`, parent build, or applied mapping ids. Keep legacy ViewerPayload parsing backward compatible while the backend cutover is in progress.

- [ ] **Step 2: Add pending-apply UI state**

Do not overload proposal status. Track selected confirmed mapping ids separately and render:

```text
3 項確認尚未套用
```

- [ ] **Step 3: Add primary action**

Button label：

```text
套用 3 項確認並建立新版本
```

Supporting copy：

```text
將沿用目前的掃描資料更新分析結果，不會重新掃描專案。
```

- [ ] **Step 4: Update viewer atomically from Apply response**

On success, replace the current viewer state with response `viewer_load_result`（含
`graph_view_model`），clear only mapping ids listed in `applied_mapping_ids`, and display B2
lineage. Do not issue a mandatory extra `GET /api/map`.

- [ ] **Step 5: Handle failure without losing B1**

On 409 stale base, reload project latest build and preserve pending confirmations for user review. On other failures, keep current graph visible and show a retryable error.

- [ ] **Step 6: Run frontend tests**

```bash
cd frontend && npm test -- --run mapBuildApi ProposalModal
```

Expected: PASS.

### Task 7: Bind Detail Scan and Query Trace to Build Identity

**Files:**
- Modify: `src/systograph/web/schemas.py`
- Modify: `src/systograph/web/routes/detail_scan_routes.py`
- Modify: `src/systograph/web/routes/trace_routes.py`
- Modify: `src/systograph/core/models/trace.py`
- Test: `tests/web/test_detail_scan_build_binding.py`
- Test: `tests/web/test_trace_build_binding.py`

- [ ] **Step 1: Add `build_id` to Detail Scan and Query Trace requests**

During compatibility migration it may be optional with latest-build fallback plus warning; active Phase2 web flow must always send it.

- [ ] **Step 2: Make Detail Scan create a child build**

Detail Scan against B2 creates B3 with `based_on_build_id=B2` and `build_reason="detail_scan"`. It must not mutate B2 in memory while keeping B2 artifact paths unchanged, which is the current route behavior.

- [ ] **Step 3: Detect stale target files**

Compare target file fingerprints with the source snapshot. If changed, return `409 scan_snapshot_stale` and require explicit repo rescan; never combine S1 map facts with changed source files silently.

- [ ] **Step 4: Bind Query Trace without creating a build**

Trace remains transient and records `source_scan_id` + `source_build_id`. It must not write runtime evidence into map/profile artifacts.

- [ ] **Step 5: Run focused tests**

```bash
.venv/bin/pytest tests/web/test_detail_scan_build_binding.py tests/web/test_trace_build_binding.py -q
```

Expected: PASS.

### Task 8: Align Artifact Headers, Contracts, and Handoff Docs

**Files:**
- Modify: `docs/MODEL-CONTRACT.md`
- Modify: `docs/API-GUIDE.md`
- Modify: `docs/work/Timmy/design/EPIC1/frontend-json-handoff/README.md`
- Modify: `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-07-projection-publication/frontend-map-build-result-sample.json`
- Modify: all sibling artifact samples currently using `generated_from_run_id`
- Test: JSON parsing and documentation grep checks

- [ ] **Step 1: Replace ambiguous active output field**

New Phase2 outputs use `generated_from_build_id`. Readers may accept legacy `generated_from_run_id` during compatibility migration, but writers must not emit both.

- [ ] **Step 2: Document Scan vs Build vs Apply**

Document that `POST /api/scans` reads repo and creates S1+B1, while `POST /api/map-builds/{base_build_id}/apply` reuses S1 and creates B2.

- [ ] **Step 3: Update frontend samples**

Every sibling artifact in one build must carry the same `generated_from_build_id`. Samples must demonstrate B1/B2 lineage and applied mapping ids without embedding raw source or absolute paths.

- [ ] **Step 4: Validate JSON and stale terminology**

```bash
find docs/work/Timmy/design/EPIC1/frontend-json-handoff -name '*.json' -print0 \
  | xargs -0 -n1 jq empty
rg -n 'generated_from_run_id|previous_run_id|based_on_run_id' \
  docs/MODEL-CONTRACT.md docs/API-GUIDE.md \
  docs/work/Timmy/design/EPIC1/frontend-json-handoff
```

Expected: all JSON parses; remaining legacy names appear only in explicit compatibility notes.

### Task 9: Add Plan 14 End-to-End Validation

**Files:**
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/14-local-project-import-and-test.md`
- Create: `scripts/trace_apply_confirmations_build_lineage.sh`
- Test: `tests/e2e/test_apply_confirmations_build_lineage.py`

- [ ] **Step 1: Build one deterministic fixture scenario**

Flow:

```text
import project
→ scan S1 / build B1
→ confirm two mappings
→ apply B1 / build B2
→ verify scanner provider was not invoked again
→ restart app
→ recover project, mappings, S1, B1, B2
→ verify latest=B2 and B1 remains readable
```

- [ ] **Step 2: Assert artifact consistency**

All B2 sibling artifacts must reference B2, contain no B1-only stale readiness/profile state, and pass evidence cross-reference validation.

- [ ] **Step 3: Assert explicit rescan remains separate**

A later `POST /api/scans` creates S2+B3, with a new `scan_id`; Apply B1→B2 must retain S1.

- [ ] **Step 4: Run regression suite**

```bash
.venv/bin/pytest tests/e2e/test_apply_confirmations_build_lineage.py -q
.venv/bin/pytest tests/unit/core tests/integration tests/web -q
cd frontend && npm test -- --run
git diff --check
```

Expected: PASS.

## Acceptance Criteria

- [ ] Project-scoped scan 在 boundary 無 proposals 時自動繼續；有 proposals 時，只有全部
  same-run decisions 完整且 fingerprint-matched 才能進入 provider scan。
- [ ] `requires_boundary_decision` 不呼叫正式 provider scan、不建立 persisted
  `ScanSnapshot`／Build、不寫 artifacts，也不更新 latest `viewer_load_result`；missing/stale decision
  仍停在 boundary gate。
- [ ] `scan_id` 與 `build_id` 是不同 domain identities；Apply 不建立新 `scan_id`。
- [ ] `scan_id` 同時識別 immutable `ScanSnapshot`；Phase2 domain/API/artifacts 不新增或要求
  `snapshot_id`。
- [ ] Gate-1 的 `ua_analysis_result=None` initial build 與 Apply regression 都通過；兩者皆可
  完成 Step 4～7 與 atomic publish，且 Apply 不呼叫 UA/filesystem/parity providers。
- [ ] Apply API 對外名稱為 `/apply`，內部只呼叫共用 Map Build pipeline。
- [ ] 使用者按「套用 N 項確認並建立新版本」不觸發 filesystem/provider scan。
- [ ] Rebuild／Apply 從原 `ScanSnapshot.scan_result` **4-1 bridge replay → 4-2 overlay**，再重算
  normalization 與所有 downstream artifacts；不得從舊 normalized map 或 B1 derived results
  開始 patch。
- [ ] Explicit rescan 重新跑 boundary preflight 與 filesystem/provider scan，並建立新的
  `scan_id`、`ScanSnapshot` 與 initial build。
- [ ] B1 保持 immutable；B2 有 `based_on_build_id=B1`、`build_reason=apply_confirmations` 與 exact `applied_mapping_ids`。
- [ ] Existing-slot、non-baseline、rejected/skipped decisions 依各自 contract materialize，不把 capability candidate 錯寫入 canonical topology。
- [ ] B2 的 map、profile、readiness、GraphViewModel、reports、Mermaid 與 static execution artifacts 來自同一次 validated materialization。
- [ ] Apply 失敗不更新 latest Viewer，也不留下可載入的 partial build。
- [ ] Project、scan snapshot、build lineage 與 confirmed mappings 在 backend restart 後可由 local JSON store 恢復。
- [ ] 每個 project 有獨立 cross-process file lock；不同 project 不互相阻塞，lock 不包住 scan、UA、LLM 或 Step 4～7 計算。
- [ ] `latest.json` 帶單調遞增 `revision`；所有 promotion 使用 expected base + revision CAS，stale writer 無法覆蓋新 latest。
- [ ] 同 base／mapping digest 的並發 Apply 最多 publish 一個 latest child；不得 Lost Update、lineage fork 或重複有效 build。
- [ ] Build 使用獨一無二的 `output/{build_id}/`；`os.replace()` 僅替換 regular JSON file，Windows/macOS/Linux 都不做 directory replacement。
- [ ] Lock timeout fail-closed 為 `project_state_busy`，不留下 partial pointer、半套 artifacts 或未受保護寫入。
- [ ] 相同 canonical project path re-import 預設重用 project identity，不產生孤立 mappings。
- [ ] Local JSON adapter 可由未來 database adapter 替換，不改 service/API domain contract。
- [ ] Detail Scan 綁定 base build 並建立 child build；stale files 要求 rescan。
- [ ] Query Trace 綁定 source build，但不建立或 mutate build artifacts。
- [ ] Plan 14 覆蓋 B1→Apply→B2→restart recovery→explicit S2 rescan。

## Non-Goals

- 不在 Phase2 導入 PostgreSQL、SQLite、ORM 或 migration framework。
- 不建立多使用者、authentication、tenant namespace 或 remote sync。
- 不允許 arbitrary build branching；Phase2 history 維持 linear latest-base apply。
- 不把 manual mapping decisions 寫入 `ai_system_map.json` 當 durable source of truth。
- 不把 Apply 實作成直接 patch JSON 或 frontend 自行 merge artifacts。
- 不在 Apply 時重新讀取 repo；repo 變更只能由明確 `POST /api/scans` 納入。
- 不把 Query Trace 結果持久化為 canonical/profile evidence。

## Dependency and Execution Order

完整 stage、track 與 Gate-0～Gate-4 順序只由本資料夾 `README.md` 維護；本計畫不複製第二份
完整排序。執行 03A 時，直接依 README 的 S1 位置與 Gate-1 `sidecar=null` 條件判斷。

- Plan 01 提供 confirmed mapping lifecycle。
- Plan 02/03 提供 profile/readiness/artifact same-build lifecycle。
- 本 Plan 03A 提供 snapshot/build identity、Apply orchestration 與 local JSON persistence。
- Plan 04 之後的 profile/mapping boundary 必須消費 03A contract，不得另建 apply path。
- Plan 14 將 03A 的 restart/history/no-rescan 行為納入 blocking validation。
- Phase3 Task 26/27 必須改成承接既有 repository/domain contract與 database adapter，不得重新發明 scan/build identity。
