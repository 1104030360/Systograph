# Audit C — web schema / helper 層現況稽核（READ-ONLY）

分區：`src/systograph/web/schemas.py`（432 行）、`inventory_error_response.py`（86 行）、
`inventory_preflight_projection.py`（116 行）、`legacy_mapping_guards.py`（39 行）。

前置：已讀完 `docs/work/Timmy/schedule/plan/unfinish/phase2.5/1.md`。Plan 1 的範圍是
`create_app()` → `AppServices` + `dependencies.py` 的 17 個 `cast()`，**與本次分區完全不重疊**
（Plan 1 不碰 `schemas.py` 與三個 helper 檔）。本報告不重複那些內容。

---

## 摘要（16 條發現）

| # | 標題 | 嚴重度 | 改 JSON？ | 破壞前端契約？ |
|---|------|--------|-----------|----------------|
| C-1 | 432 行單檔塞 8 個路由領域的 27 個 model，應按 route 拆檔 | P2 | ❌ | ❌ |
| C-2 | `__all__` 有 4 個零消費者的 core model re-export（死 code） | P3 | ❌ | ❌ |
| C-3 | Web/core 欄位重複 + 3 處型別/預設漂移（`tuple` vs `list`、`datetime` vs `str`、`can_expand` 預設相反） | P2 | ❌ | ❌ |
| C-4 | `InventoryPreflightApiRequest` 是 core model 逐欄位複製，`to_core()` 繞一圈 | P2 | ❌ | ❌ |
| C-5 | Optional 序列化四套寫法並存；`exclude_if` 需 pydantic≥2.12 但 pyproject 寫 `>=2` | P2 | 視改法 | ❌ |
| **C-6** | **`/api/scans` pending response 缺 `scan_id` → 前端 zod `.parse()` throw** | **P1** | ❌（修前端） | **已破，需修** |
| **C-7** | **SSE 送 `null`，前端 zod 只收 `undefined` → 進度事件全被當 invalid** | **P1** | ❌（修前端） | **已破，需修** |
| C-8 | `ManualMappingListResponse.available_actions` 5 個硬編字串，4 個不是合法 `decision` 值 | P2 | 視改法 | ❌（前端未消費） |
| C-9 | `/api/map/build` 與 `/api/scans` 直接回 core `MapBuildResult`，含 12 個 absolute path | P2 | ✅ | ❌（前端無實質依賴） |
| C-10 | `WebSchema` config 與 core base 不一致（無 `frozen`、`arbitrary_types_allowed` 疑似多餘） | P3 | ❌ | ❌ |
| C-11 | 20 個 `Field()` 零 `description`；全站零 `responses=` → error 形狀不在 OpenAPI | P3 | ❌ | ❌ |
| C-12 | 只有 inventory 有結構化 error envelope，其他 route 全是裸 `detail: str`；`ERROR_MESSAGES[]` 有 KeyError→500 路徑 | P2 | 視改法 | ❌ |
| C-13 | `inventory_preflight_projection.py` 在 web 層做 projection，且重建 core 剛丟掉的 index | P2 | ❌ | ❌ |
| C-14 | `legacy_mapping_guards.py` 守的是 retired mapping type，**與 v1 退場無關，不能刪** | P3 | ❌ | ❌ |
| C-15 | `target_type` 是裸 `str`；code / API-GUIDE / API_CONTRACT 三份清單互相打架 | P2 | ✅ | ❌（前端未消費） |
| C-16 | `ScanProgressEvent` 是硬編 stub，且 `slot` 是 legacy 概念 | P3 | 視改法 | 視改法 |

**最該先修的兩條是 C-6 與 C-7 —— 都是 main 上已存在的前端契約破壞，且都被測試的 mock／缺測掩蓋。**

---

## 0. `schemas.py` 全部 class 一覽表

`grep -c "^class " src/systograph/web/schemas.py` → **27**。全部繼承 `WebSchema`（除
`ApplyConfirmationsResponse` 繼承 `MapBuildScopedResponse`）。

| # | Class | 行號 | 用途 | 被誰 import（實際 grep） | 死 code？ |
|---|-------|------|------|--------------------------|-----------|
| 1 | `WebSchema` | 43-46 | base：`extra="forbid"` + `arbitrary_types_allowed` | 僅 `schemas.py` 內部（26 個子類） | 否 |
| 2 | `MapBuildApiRequest` | 49-66 | `POST /api/map/build` request | `routes/map_routes.py:16,24` | 否 |
| 3 | `ViewerLoadMapRequest` | 69-70 | `POST /api/viewer/load` request | `routes/viewer_routes.py:13,21` | 否 |
| 4 | `ProjectImportRequest` | 73-75 | `POST /api/projects/import` request | `routes/project_routes.py:12,38` | 否 |
| 5 | `ProjectImportResponse` | 78-83 | 同上 response | `routes/project_routes.py:13,36,40,47` | 否 |
| 6 | `ProjectResponse` | 86-89 | `GET /api/projects/{id}` response | `routes/project_routes.py:14,21,25,29` | 否 |
| 7 | `Phase2MapBuildResult` | 92-123 | 去路徑化的 build 摘要 | **只有 `schemas.py` 內部**（143、161、182 行當巢狀欄位/工廠） | 否（間接） |
| 8 | `ApplyConfirmationsRequest` | 126-133 | apply request | `routes/map_build_routes.py:24,44` | 否 |
| 9 | `MapBuildScopedResponse` | 136-163 | build-scoped S1 envelope | `routes/map_build_routes.py:28,81,86,91,96,101,106` | 否 |
| 10 | `ApplyConfirmationsResponse` | 166-184 | apply response（收窄 9 的 Literal） | `routes/map_build_routes.py:25,40,50,76` | 否 |
| 11 | `MapBuildHistorySummary` | 187-212 | build history 單筆 | `routes/map_build_routes.py:27,123` | 否 |
| 12 | `MapBuildHistoryResponse` | 215-217 | build history 列表 | `routes/map_build_routes.py:26,111,117,120` | 否 |
| 13 | `ScanCreateRequest` | 220-233 | `POST /api/scans` request | `routes/scan_routes.py:61,132` | 否 |
| 14 | `ScanCreateResponse` | 236-257 | `POST /api/scans` response | `routes/scan_routes.py:62,129,159,193,236,243,268,344` | 否 |
| 15 | `InventoryPreflightApiRequest` | 260-269 | preflight request | `routes/scan_routes.py:59,85` | 否 |
| 16 | `InventoryRequestedTargetView` | 272-278 | preflight 子 view | **只有 `inventory_preflight_projection.py:21,63`** | 否 |
| 17 | `InventoryReviewableExcludedPageView` | 281-284 | preflight 分頁 view | **只有 `inventory_preflight_projection.py:22,104`** | 否 |
| 18 | `InventoryBlockedSummaryView` | 287-290 | preflight blocked view | **只有 `inventory_preflight_projection.py:19,73,82`** | 否 |
| 19 | `InventoryPreflightResponse` | 294-318 | preflight response | `inventory_preflight_projection.py:20,32,91`、`routes/scan_routes.py:60,81,95` | 否 |
| 20 | `InventoryApiErrorDetail` | 321-325 | inventory 專屬 error envelope | **只有 `inventory_error_response.py:9,57,66,81`** | 否 |
| 21 | `ScanProgressEvent` | 328-345 | SSE 事件 | `routes/scan_routes.py:63,358` | 否 |
| 22 | `DetailScanCreateRequest` | 348-353 | detail scan request | `routes/detail_scan_routes.py:30,41,164` | 否 |
| 23 | `DetailScanResponse` | 356-364 | detail scan response | `routes/detail_scan_routes.py:30,39,52,115,129,134,142,171,202` | 否 |
| 24 | `TraceCreateRequest` | 367-372 | `POST /api/trace` request | `routes/trace_routes.py:21,29` | 否 |
| 25 | `ManualMappingListResponse` | 375-386 | `GET /api/mappings` response | `routes/mapping_routes.py:19,24,31,33` | 否 |
| 26 | `MappingProposalCreateRequest` | 389-392 | proposal create request | `routes/mapping_proposal_routes.py:28,60` | 否 |
| 27 | `MappingProposalListResponse` | 395-405 | proposal list response | `routes/mapping_proposal_routes.py:30,39,47,49` | 否 |

**27 個 class 沒有一個是完全沒人用的死 code。** 死 code 出現在 `__all__` 的 re-export（見 C-2）。

`__all__`（408-432 行，23 個名字）中有 **11 個不是本檔定義的 class**，而是 core model 的 re-export：
`MapBuildResult`、`ManualMapping`、`ManualMappingCreate`、`ManualMappingUpdate`、`MappingProposal`、
`MappingProposalDecisionRequest`、`MappingProposalDecisionResult`、`ScanBoundaryDecisionRequest`、
`ScanBoundaryProposal`、`ViewerPayload`（+ `ScanProgressEvent` 本檔有定義）。
反過來，本檔定義卻**不在** `__all__` 的有 12 個（`WebSchema`、`Phase2MapBuildResult`、
`MapBuildScopedResponse`、`ApplyConfirmationsRequest/Response`、`MapBuildHistorySummary/Response`、
`Inventory*View`、`InventoryPreflightApiRequest/Response`、`InventoryApiErrorDetail`、
`ProjectResponse`、`ManualMappingListResponse`、`MappingProposalListResponse`）。
`__all__` 已經與檔案內容脫節。

---

## C-1. 432 行單檔塞了 8 個路由領域的 27 個 model，應按 route 拆檔

- **位置**：`src/systograph/web/schemas.py:1-432`（全檔）
- **現況**：一個模組同時承載 8 個互不相干的 API 領域：

  | 領域 | class 行號範圍 | 消費 route |
  |------|----------------|-----------|
  | map（demo） | 49-66 | `routes/map_routes.py` |
  | viewer | 69-70 | `routes/viewer_routes.py` |
  | project | 73-89 | `routes/project_routes.py` |
  | map-build / apply / history | 92-217 | `routes/map_build_routes.py` |
  | scan + inventory preflight | 220-345 | `routes/scan_routes.py` + 2 個 helper |
  | detail-scan | 348-364 | `routes/detail_scan_routes.py` |
  | trace | 367-372 | `routes/trace_routes.py` |
  | mapping / mapping-proposal | 375-405 | `routes/mapping_routes.py`、`routes/mapping_proposal_routes.py` |

  沒有任何 route 需要跨兩個以上領域的 model：`routes/` 底下 9 個檔各自只 import 自己那一段
  （見 §0 表的「被誰 import」欄，每個 class 的消費者都收斂在單一 route 檔）。
- **為什麼是問題**：`CLAUDE.md` 的 Backend Architecture 要求 `web/` 是 adapter 層且
  `web/routes/` 已經按 route 拆成 9 個檔，schema 卻沒有跟著拆 —— 同一層裡兩種組織原則。
  實務後果：改 inventory preflight 的欄位會讓 `git blame`／PR diff 掃到 mapping、trace 的 reviewer；
  27 個 class 共用一個 `extra="forbid"` base，任何 config 調整都是全域爆炸半徑。
- **建議改法**：改成 package `src/systograph/web/schemas/`：
  - `__init__.py` — 只放 `WebSchema` base 與明確的 re-export（或乾脆不 re-export，讓 route 直接
    `from systograph.web.schemas.scan import ScanCreateRequest`）
  - `base.py` — `WebSchema`
  - `map.py` — `MapBuildApiRequest`
  - `viewer.py` — `ViewerLoadMapRequest`
  - `project.py` — `ProjectImportRequest/Response`、`ProjectResponse`
  - `map_build.py` — `Phase2MapBuildResult`、`MapBuildScopedResponse`、`ApplyConfirmations*`、
    `MapBuildHistorySummary/Response`
  - `scan.py` — `ScanCreateRequest/Response`、`ScanProgressEvent`
  - `inventory.py` — `InventoryPreflightApiRequest/Response`、三個 `Inventory*View`、
    `InventoryApiErrorDetail`
  - `detail_scan.py` — `DetailScanCreateRequest/Response`
  - `trace.py` — `TraceCreateRequest`
  - `mapping.py` — `ManualMappingListResponse`、`MappingProposalCreateRequest/ListResponse`
- **影響面**：**純 Python import 路徑搬移，JSON 輸出 0 變化**。
  `frontend/src/types.ts`、`frontend/src/services/viewerApi.ts`、`frontend/src/services/projectScanApi.ts`
  完全不受影響（前端不知道後端模組佈局）。
  唯一需要同步的是 `tests/contracts/test_v2_cutover_consumer_allowlist.py:270`
  的 `ConsumerRecord(path="src/systograph/web/schemas.py", symbol="ai-system-map/v1", ...)` ——
  `ai-system-map/v1` 這個 Literal 出現在 54-57、95-97、226-229 行，拆檔後會落到
  `schemas/map.py`、`schemas/map_build.py`、`schemas/scan.py` 三個新路徑，allowlist 必須改成 3 筆。
- **相關測試**：
  - **修改**：`tests/contracts/test_v2_cutover_consumer_allowlist.py`
    → `test_direct_legacy_consumers_match_classified_allowlist`（`CONSUMER_ALLOWLIST` 第 269-274 行那筆
      要拆成 3 筆新路徑，否則 `stale legacy consumer records` assert 會失敗）
  - **不需改**：`tests/web/` 16 個檔全部走 HTTP（`TestClient`），沒有任何一個 import
    `systograph.web.schemas`（`grep -rn "web.schemas" tests/` 只命中上面那筆字串常數）
- **嚴重度**：P2
- **風險**：低 —— 純機械式搬移，`ruff`／`mypy strict` 會抓出所有漏改的 import；行為零變動。

---

## C-2. `__all__` 有 4 個完全沒人用的 core model re-export（死 code），import 路徑雙軌

- **位置**：`src/systograph/web/schemas.py:23-31`（import）、`408-432`（`__all__`）
- **現況**：實測「這個名字在 `schemas.py` body（42-407 行）被用到幾次」：

  ```
  ManualMappingCreate              body-uses=0    ← 只為了餵 __all__ 才 import
  ManualMappingUpdate              body-uses=0    ← 同上
  MappingProposalDecisionResult    body-uses=0    ← 同上
  ViewerPayload                    body-uses=0    ← 同上
  MappingProposalDecisionRequest   body-uses=0    ← 同上，但有 1 個消費者
  ```

  再查誰真的從 `systograph.web.schemas` import 這些名字（完整清單，`grep -rn "web.schemas" src tests`
  只有 11 個 import 點）：

  | re-export 名字 | 有人從 `web.schemas` import 嗎 |
  |---|---|
  | `ManualMappingCreate` | **無** |
  | `ManualMappingUpdate` | **無** |
  | `MappingProposalDecisionResult` | **無** |
  | `ViewerPayload` | **無** |
  | `MapBuildResult` | 無（`scan_routes.py:20`、`map_routes.py:9`、`detail_scan_routes.py:10` 都是走 `core.models.map_build`） |
  | `ManualMapping` / `ManualMappingUpdate` | 無（`mapping_routes.py:9-13` 走 `core.models.mapping`） |
  | `ScanBoundaryDecisionRequest` / `ScanBoundaryProposal` | 無 |
  | `MappingProposalDecisionRequest` | **有 1 個**：`routes/mapping_proposal_routes.py:29` |

  也就是 `mapping_proposal_routes.py:29` 從 `web.schemas` 拿 `MappingProposalDecisionRequest`，
  但同一檔 `:10-13` 又從 `core.models.mapping` 拿 `MappingProposal` / `MappingProposalDecisionResult`
  —— **同一個 core module 的東西，同一個檔案用兩條 import 路徑**。
  而 `core/models/mapping.py` 本身（1-45 行）已經是一個 re-export barrel（把
  `mapping_base` / `mapping_candidates` / `mapping_proposals` 攤平），`web/schemas.py` 的 `__all__`
  是**第二層 barrel**。
- **為什麼是問題**：`CLAUDE.md` 定義的層次是「Web / CLI adapters → Core services → Providers / Models」。
  web schema 模組同時扮演「web DTO 定義處」與「core model 轉發站」兩個角色，讓
  「這個型別是 API 專屬還是 core 契約」在 import 站點看不出來 —— 而這正是
  `docs/MODEL-CONTRACT.md` §9.1「Current response boundary」表格要區分的東西。
  4 個零消費者的 re-export 是純粹的死 code。
- **建議改法**：
  1. 刪掉 `schemas.py:25-26`（`ManualMappingCreate`、`ManualMappingUpdate`）、
     `:30`（`MappingProposalDecisionResult`）、`:40` 的 `ViewerPayload` 這 4 個 import，
     以及 `__all__` 中對應的 4 筆（412、414、420、431 行）。
  2. `routes/mapping_proposal_routes.py:29` 的 `MappingProposalDecisionRequest` 改成從
     `systograph.core.models.mapping` import（跟同檔 `:10-13` 一致），
     然後把 `schemas.py:29` 與 `__all__:419` 一併刪掉。
  3. 剩下的 `MapBuildResult`、`ManualMapping`、`MappingProposal`、`ScanBoundaryDecisionRequest`、
     `ScanBoundaryProposal` 這 5 個 import 是**欄位型別**（實際被 body 用到 1-4 次），保留 import
     但從 `__all__` 移除（`__all__` 只列本檔定義的 27 個 class）。
- **影響面**：**JSON 輸出 0 變化**。前端無依賴。
- **相關測試**：**無需修改** —— 沒有任何測試 import 這些名字（`grep -rn "web.schemas" tests/`
  只有 `test_v2_cutover_consumer_allowlist.py:270` 一個字串常數，與 `__all__` 無關）。
  建議**新增** `tests/web/test_schema_module_boundary.py::test_web_schemas_all_only_exports_local_classes`
  斷言 `set(schemas.__all__) == {每個 module 內定義的 class 名}`，防止 barrel 再長回來。
- **嚴重度**：P3
- **風險**：低 —— 刪 4 個零引用符號，`ruff F401` + `mypy` 會即時驗證。

---

## C-3. Web model 與 `core/models/` 欄位重複，且有 3 處實質型別/預設值漂移

- **位置**：多處，逐條對照如下。

### 對照表 A：`MapBuildHistorySummary` vs `MapBuildLineage`

| 欄位 | web `schemas.py:187-195` | core `analysis_history.py:89-96` | 一致？ |
|------|--------------------------|----------------------------------|--------|
| `project_id` | `str` | `str` | ✅ |
| `scan_id` | `str` | `str` | ✅ |
| `build_id` | `str` | `str` | ✅ |
| `based_on_build_id` | `str \| None` | `str \| None = None` | ✅ |
| `build_reason` | inline `Literal["initial_scan","apply_confirmations","detail_scan"]` | `BuildReason`（`analysis_history.py:16-20` 的 type alias） | ⚠️ alias 被展開 |
| `applied_mapping_ids` | `list[str]` | `tuple[str, ...] = ()` | ❌ **型別不一致** |
| `generated_at` | `str` | `datetime` | ❌ **型別不一致**（web 在 `:209-211` 手工 `.isoformat().replace("+00:00","Z")`） |

`MapBuildScopedResponse:136-144` 重複同一組 7 個欄位（`applied_mapping_ids: list[str]`、
`build_reason` 又展開一次 inline Literal），`:160` 再做一次 `list(lineage.applied_mapping_ids)`。

### 對照表 B：`Phase2MapBuildResult` vs `MapBuildResult`

| 欄位 | web `schemas.py:92-104` | core `map_build.py:70-97` | 一致？ |
|------|-------------------------|---------------------------|--------|
| `status` | `Literal["ok","error"]` | `Literal["ok","error"]` | ✅ |
| `project_name` | `str` | `str` | ✅ |
| `active_schema_version` | inline `Literal["ai-system-map/v1","ai-system-map/v2"]` | `SystemMapSchemaSelection`（`map_build.py:28` alias） | ⚠️ alias 被展開 |
| `requested_schema_version` | 同上 inline | `SystemMapSchemaSelection` | ⚠️ |
| `source_schema_version` | 同上 inline | `SystemMapSchemaSelection` | ⚠️ |
| `operator_rollback_active` | `bool` | `bool = False` | ✅ |
| `migration_warnings` | `list[str]` | `list[str]` | ✅ |
| `warnings` | `list[str]` | `list[str]` | ✅ |
| `profile_inference_result` | `ProfileInferenceResult \| None` | 同 | ✅ |
| `readiness_report` | `ReadinessReport \| None` | 同 | ✅ |
| `profile_signals_available` | `bool`（web 新增，由 `:117-119` 推導） | — | web-only（**這是這個 model 存在的正當理由**） |
| `readiness_report_available` | `bool`（`:120` 推導） | — | web-only |

### 對照表 C：`InventoryBlockedSummaryView` vs `InventoryDirectorySummary`

| 欄位 | web `schemas.py:287-290` | core `inventory_selection.py:178-182` | 一致？ |
|------|--------------------------|---------------------------------------|--------|
| `path` | `str` | `str` | ✅ |
| `reason_code` | `str` | `str` | ✅ |
| `exclusion_source` | — | `InventorySelectionSource` | web 丟棄（合理，避免洩漏內部政策來源） |
| `outcome` | `Literal["hard_blocked","collapsed_directory"]` | — | web-only |
| `can_expand` | `bool = **False**` | `bool = **True**` | ❌ **預設值相反** |

`can_expand` 的預設相反目前沒有炸掉，只因為
`inventory_preflight_projection.py:72-80` 走 hard_blocked 分支時**故意不傳** `can_expand`（吃 web 的
`False`），`:81-89` 走 collapsed 分支時**明確傳** `summary.can_expand`。
這是一個沒有寫在任何地方的隱性約定 —— 任何人把 `can_expand=...` 加到 hard_blocked 分支、
或反過來忘記在 collapsed 分支傳值，語意就直接反轉。

### 對照表 D：`InventoryReviewableExcludedPageView` vs `InventoryCandidatePage`

| 欄位 | web `schemas.py:281-284` | core `inventory_selection.py:233-236` | 一致？ |
|------|--------------------------|---------------------------------------|--------|
| `items` | `list[ScanBoundaryProposal]` | `tuple[InventoryCandidate, ...]` | 型別刻意不同（web 換成 proposal） |
| `next_cursor` | `str \| None = None` | `str \| None = None` | ✅ |
| `total` | `int` | `int` | ✅ |

### 對照表 E：`InventoryRequestedTargetView` vs `InventoryRequestedTargetResult`

| 欄位 | web `schemas.py:272-278` | core `inventory_selection.py:185-192` | 一致？ |
|------|--------------------------|---------------------------------------|--------|
| `target_path` / `target_kind` / `status` | 同名同型 | 同名同型 | ✅ |
| `file_candidate` / `directory_manifest` | — | 有 | web 刻意丟棄（**這是安全邊界**，見 `frontend/API_CONTRACT.md:155-157`） |
| `proposal` | `ScanBoundaryProposal \| None` | — | web-only |
| `reason_code` | `str \| None = None` | `str \| None = None` | ✅ |
| `limit_context` | `InventoryDirectoryLimitContext \| None` | 同 | ✅ |

### 對照表 F：`MapBuildApiRequest` vs `MapBuildRequest`

| 欄位 | web `schemas.py:49-57` | core `map_build.py:49-54` | 一致？ |
|------|------------------------|---------------------------|--------|
| `project_path` | `str` | `Path` | 刻意（HTTP 邊界必須是 str） |
| `output` | `str = "outputs"` | `Path = Path("outputs")` | 刻意 |
| `redact_root_path` | `bool = True` | `bool = True` | ✅ |
| `no_snippets` | `bool = False` | `bool = False` | ✅ |
| `system_map_schema_version` | inline Literal | `SystemMapSchemaSelection` | ⚠️ alias 被展開 |

- **為什麼是問題**：`docs/MODEL-CONTRACT.md` §7.2「Current S1 Build / Viewer 模型」把
  `MapBuildScopedResponse` 的 `applied_mapping_ids` 寫成 `string[]`，core 卻是 `tuple[str, ...]`
  且帶 `MapBuildLineage.validate_lineage`（`analysis_history.py:98-112`，會檢查唯一性與
  `build_reason` 對 `based_on_build_id`／`applied_mapping_ids` 的三種組合約束）。
  Web DTO 把 tuple 換成 list 就**丟掉了 frozen 語意**（core base
  `AnalysisHistoryModel` 是 `frozen=True`，`analysis_history.py:24`），也丟掉那個
  `model_validator`。`ApplyConfirmationsResponse:166-168` 只用「收窄 Literal」重述了
  「apply build 必有 parent」，`MapBuildScopedResponse` 的 initial_scan／detail_scan 分支
  則完全沒有等價驗證 —— 契約規則在兩層各實作一半。
  對照表 C 的 `can_expand` 預設相反，是最典型的契約漂移前兆。
- **建議改法**：
  1. `MapBuildHistorySummary`、`MapBuildScopedResponse` 的 `build_reason` 改用
     `from systograph.core.models.analysis_history import BuildReason`，不要 inline Literal。
  2. `Phase2MapBuildResult` / `MapBuildApiRequest` / `ScanCreateRequest` 的三個 schema-version
     欄位改用 `from systograph.core.models.map_build import SystemMapSchemaSelection`。
  3. `InventoryBlockedSummaryView.can_expand` 的預設改成**沒有預設**（`can_expand: bool`），
     強迫 `inventory_preflight_projection.py:72-80` 明確寫 `can_expand=False`，把隱性約定變成
     顯性程式碼。
  4. `MapBuildHistorySummary` / `MapBuildScopedResponse` 抽一個共用 mixin
     `BuildLineageFields(WebSchema)`（放 `schemas/map_build.py`），7 個欄位只寫一次；
     `generated_at` 的 `.isoformat().replace("+00:00","Z")`（`:209-211`）抽成
     `schemas/base.py::to_iso_z(value: datetime) -> str`，因為
     `inventory_preflight_projection.py:94` 也複製了同一行。
- **影響面**：
  - 1、2、4：**JSON 輸出 0 變化**（alias 展開後語意完全相同）。
  - 3：**JSON 輸出 0 變化**（只是把預設改成必填參數，呼叫端補上同值）。
  - 前端依賴：`frontend/API_CONTRACT.md:145-150` 定義
    `blocked_summaries: Array<{path, reason_code, outcome, can_expand}>`；只要值不變就相容。
    `frontend/src/types.ts` **沒有**為 preflight response 定義任何 zod schema
    （`grep -n "blocked_summaries\|preflight" frontend/src/types.ts` 無命中），所以前端目前
    根本沒有驗證這塊 —— 不會破，但也代表沒有保護網。
- **相關測試**：
  - **不需改**：`tests/web/test_inventory_preflight_routes.py`
    → `test_preflight_projects_bounded_directory_summary_without_entries`（:34）、
      `test_preflight_http_supports_root_file_missing_blocked_and_pagination`（:76）
      —— 斷言 JSON 值，值不變則全綠。
  - **新增**：`tests/unit/web/test_schema_core_alignment.py`
    → `test_map_build_history_summary_matches_lineage_fields`：用
      `set(MapBuildLineage.model_fields) <= set(MapBuildHistorySummary.model_fields)` 鎖住欄位集合，
      core 新增 lineage 欄位而 web 沒跟上時直接紅燈。
- **嚴重度**：P2
- **風險**：低（1、2、4）／中（3 —— 改必填參數要確認 `inventory_preflight_projection.py` 兩個
  分支都補上，漏一個 mypy 會抓到）。

---

## C-4. `InventoryPreflightApiRequest` 是 core model 的逐欄位複製，`to_core()` 繞一圈序列化

- **位置**：`src/systograph/web/schemas.py:260-269` vs `src/systograph/core/models/inventory_selection.py:210-214`
- **現況**：兩者欄位**完全相同**，只有 `requested_paths` 的預設寫法不同：

  ```python
  # web/schemas.py:260-269
  class InventoryPreflightApiRequest(WebSchema):
      scan_depth: Literal["system"] = "system"
      requested_paths: tuple[str, ...] = ()                       # ← 裸 tuple 字面值
      reviewable_excluded_cursor: str | None = None
      reviewable_excluded_limit: int = Field(default=100, ge=1, le=200)

      def to_core(self) -> InventoryPreflightRequest:
          return InventoryPreflightRequest.model_validate(
              self.model_dump(mode="python")
          )

  # core/models/inventory_selection.py:210-214
  class InventoryPreflightRequest(InventorySelectionModel):
      scan_depth: Literal["system"] = "system"
      requested_paths: tuple[str, ...] = Field(default_factory=tuple)  # ← Field 版
      reviewable_excluded_cursor: str | None = None
      reviewable_excluded_limit: int = Field(default=100, ge=1, le=200)
  ```

  `to_core()` 的實作是 `model_dump` → `model_validate`，等於「驗證一次 → 拆成 dict → 再驗證一次」。
  `ge=1, le=200` 這條約束在兩個檔案各寫一次；
  `inventory_preflight_cursor_service.py:26` 還第三次寫了 `if not 1 <= limit <= 200`。
- **為什麼是問題**：這是純粹的重複 —— web DTO 沒有做任何 HTTP 邊界轉換（不像
  `MapBuildApiRequest` 要把 `str` 轉 `Path`）。三份同源約束意味著改 limit 上限要記得改三個地方，
  而且 `model_dump(mode="python")` → `model_validate` 這一圈在 `requested_paths` 是 tuple 時
  多做一次 list↔tuple 轉換。
- **建議改法**：直接在 route 用 core model 當 request body：
  `routes/scan_routes.py:85` 的 `payload: InventoryPreflightApiRequest` 改成
  `payload: InventoryPreflightRequest`，刪掉 `schemas.py:260-269` 與 `:14-21` 的 import，
  `:102` 的 `request = payload.to_core()` 改成 `request = payload`。
  若想保留「web 層一定用 `WebSchema` base」的規則（`extra="forbid"`），注意 core
  `InventorySelectionModel`（`inventory_selection.py:10-11`）已經是 `extra="forbid", frozen=True`，
  比 `WebSchema` **更嚴格**，不會放寬任何東西。
- **影響面**：**JSON 輸入/輸出 0 變化**（欄位、預設、驗證範圍完全相同；`extra="forbid"` 兩邊都有）。
  唯一差別是 OpenAPI 的 schema 名字從 `InventoryPreflightApiRequest` 變成
  `InventoryPreflightRequest` —— 前端沒有從 OpenAPI 產型別
  （`frontend/` 底下沒有 openapi 產碼設定），無影響。
  `frontend/API_CONTRACT.md:96-101` 的 `ScanInventoryPreflightRequest` 是手寫 TS，不受影響。
- **相關測試**：
  - **不需改**：`tests/web/test_inventory_preflight_routes.py` 全部走 HTTP JSON。
  - **不需改**：`tests/unit/core/` 底下針對 `InventoryPreflightRequest` 的既有測試。
- **嚴重度**：P2
- **風險**：低 —— 兩個 model 欄位逐字相同，且 core 的約束是超集。

---

## C-5. Optional 欄位序列化四套寫法並存，其中 `exclude_if` 還有 Pydantic 版本地雷

- **位置**：`src/systograph/web/schemas.py:236-257`（同一個 class 內就有三套）、
  以及 `:99-100, 244-252, 282, 308-318, 364, 378-386, 398-405`
- **現況**：`ScanCreateResponse` 一個 class 裡，四個 optional 欄位用了三種不同策略：

  ```python
  class ScanCreateResponse(WebSchema):                     # :236
      scan_id: str | None = Field(                         # :237  ← 策略 A：exclude_if，null 時「消失」
          default=None,
          exclude_if=lambda value: value is None,
      )
      project_id: str
      status: Literal["completed", "error", "requires_boundary_decision"]
      build_result: MapBuildResult | None = None           # :243  ← 策略 B：裸 None，序列化成 null
      boundary_proposals: list[ScanBoundaryProposal] = Field(
          default_factory=list                             # :244-246 ← 策略 C：空 list
      )
      available_boundary_actions: list[ScanBoundaryDecisionAction] = Field(
          default_factory=lambda: [...]                    # :247-252 ← 策略 D：常數 default_factory
      )
      preflight_request_id: str | None = Field(            # :253-256 ← 策略 A
          default=None,
          exclude_if=lambda value: value is None,
      )
      inventory_selection_summary: InventorySelectionSummary | None = None   # :257 ← 策略 B
  ```

  實測（`uv run python -c "..."`，READ-ONLY 只做 model_dump）：

  ```
  pending:   {"project_id":"p","status":"requires_boundary_decision","build_result":null,
              "boundary_proposals":[],"available_boundary_actions":["scan_this_run","skip_this_run"],
              "inventory_selection_summary":null}
  completed: {"scan_id":"scan:1","project_id":"p","status":"completed","build_result":null,
              "boundary_proposals":[],"available_boundary_actions":[...],
              "inventory_selection_summary":null}
  ```

  → `scan_id` / `preflight_request_id` 在 None 時**整個 key 不見**，
  `build_result` / `inventory_selection_summary` 在 None 時是 `null`。
  同一支 endpoint、同樣是「沒有值」，兩種 JSON 表示法。

  全檔沒有任何 `by_alias`、`exclude_none`、`alias`、`populate_by_name`
  （`grep -rn "by_alias\|exclude_none\|alias" src/systograph/web/` 只命中
  `inventory_error_response.py` 的三個 `.model_dump(mode="json")`）。
  所有 route 也沒有 `response_model_exclude_none` / `response_model_by_alias`
  （`grep -rn "response_model_exclude" src/systograph/web/routes/` 無命中）。
  **camelCase/snake_case**：全線 snake_case，`frontend/src/types.ts` 也全部 snake_case
  （如 `:154 project_id`、`:211 scan_id`、`:214 build_result`），這點是一致的，沒有問題。

- **Pydantic 版本地雷**：`exclude_if` 是 Pydantic **2.12.0** 才加入的
  （來源：<https://github.com/pydantic/pydantic/blob/main/HISTORY.md> —
  「Add support for `exclude_if` at the field level by @andresliszt in #12141」，列於 v2.12.0b1）。
  但 `pyproject.toml:12` 宣告的是 `"pydantic>=2,<3"` —— 允許 2.0～2.11。
  `uv.lock:652-653` 目前鎖在 `pydantic 2.13.4`，所以本機是好的；
  但在 2.11 以下，`Field(exclude_if=...)` 是「未知 kwarg」→ Pydantic 會發
  deprecation warning 並把它塞進 `json_schema_extra`，**不會報錯**，
  結果是 `scan_id` 在 pending response 從「消失」變成 `null` —— 一個靜默的 API 契約變更。
- **為什麼是問題**：`frontend/API_CONTRACT.md:186-190` 把 completed response 寫成
  `scan_id: string;`（必填）+ `build_result?: unknown;`（optional），
  `:256` 又說「When `requires_boundary_decision` is returned, `scan_id` is absent」。
  也就是**契約文件自己就靠「key 存不存在」來區分兩種 response** —— 這種設計本身脆弱，
  而且沒有被任何 pydantic config 統一保證（是靠兩個手寫 lambda）。
  正確做法是用 discriminated union，讓型別系統而不是 lambda 表達「pending 沒有 scan_id」。
- **建議改法**：
  1. **立即**：`pyproject.toml:12` 的 `"pydantic>=2,<3"` 改成 `"pydantic>=2.12,<3"`，
     讓宣告的下限對得上實際用到的 API（`uv lock --check` 會驗證）。
  2. **重構**：把 `ScanCreateResponse` 拆成 discriminated union：
     ```python
     class ScanPendingResponse(WebSchema):
         status: Literal["requires_boundary_decision"]
         project_id: str
         preflight_request_id: str | None = None
         boundary_proposals: list[ScanBoundaryProposal] = Field(default_factory=list)
         available_boundary_actions: list[ScanBoundaryDecisionAction] = Field(...)

     class ScanCompletedResponse(WebSchema):
         status: Literal["completed", "error"]
         scan_id: str                     # ← 必填，不需要 exclude_if
         project_id: str
         build_result: Phase2MapBuildResult   # ← 順帶修 C-6
         preflight_request_id: str | None = None
         inventory_selection_summary: InventorySelectionSummary | None = None

     ScanCreateResponse = Annotated[
         ScanPendingResponse | ScanCompletedResponse, Field(discriminator="status")
     ]
     ```
     並在 `schemas/base.py` 訂一條寫死的規則：**web response 一律不用 `exclude_if`，
     optional 就是 `X | None = None` 序列化成 `null`**，讓 JSON 形狀只由型別決定。
- **影響面**：**⚠️ 這會改 JSON 輸出，且是破壞性的前端契約變更。**
  - 若採用建議 2，pending response 會多出 `scan_id` 不再是「不存在」而是……（見下）。
    實際上建議 2 讓 pending response **仍然沒有 `scan_id` key**（因為 `ScanPendingResponse`
    根本沒宣告這個欄位），所以 wire format **不變**；改變的是「靠 lambda」→「靠型別」。
  - 但建議 2 順帶把 `build_result` 從 `MapBuildResult` 換成 `Phase2MapBuildResult`
    （C-6）**會**改 JSON。這兩件事應該分開做。
  - 前端實際依賴：`frontend/src/services/projectScanApi.ts:36`
    `scanCreateResponseSchema.parse(payload)`；
    `frontend/src/types.ts:210-217` 的 zod schema。
    **注意：這條路現在就是壞的，見 C-6。**
- **相關測試**：
  - **修改**：`tests/web/test_scan_boundary_routes.py`
    → `test_scan_requires_boundary_decision_before_building_map`（:76）、
      `test_scan_this_run_decision_builds_map_for_current_scan_only`（:114）、
      `test_skip_this_run_decision_builds_map_without_current_file`（:152）
      —— 若改 union，要確認 `response.json()` 斷言仍成立（預期成立）。
  - **新增**：`tests/unit/web/test_scan_response_shape.py`
    → `test_pending_response_omits_scan_id`、`test_completed_response_requires_scan_id`
      —— 把「key 存不存在」這個契約鎖進測試（目前**完全沒有測試覆蓋這件事**）。
  - **新增**：`tests/contracts/test_dependency_floor.py`
    → `test_pydantic_floor_supports_exclude_if`（或直接靠 `uv lock --check`）。
- **嚴重度**：P2（版本下限那條偏 P1，但因為 lock 已鎖住 2.13.4，實際爆炸機率低）
- **風險**：中 —— union 化會動到 `scan_routes.py` 5 個 return 點（:193, 236, 243, 268, 344），
  每個都要選對 class；mypy strict 會全部抓到。

---

## C-6. 【P1】`/api/scans` 的 `requires_boundary_decision` response 會讓前端 zod 直接 throw

- **位置**：後端 `src/systograph/web/schemas.py:237-240`；
  前端 `frontend/src/types.ts:210-217`、`frontend/src/services/projectScanApi.ts:27-37`
- **現況**：

  後端（實測 `model_dump(mode="json")`）：
  ```
  pending: {"project_id":"p","status":"requires_boundary_decision","build_result":null, ...}
           ↑ 沒有 "scan_id" —— 因為 schemas.py:237-240 的 exclude_if
  ```

  前端（`frontend/src/types.ts:210-217`）：
  ```ts
  export const scanCreateResponseSchema = z.object({
    scan_id: z.string(),                    // ← :211  必填，沒有 .optional()
    project_id: z.string(),
    status: z.enum(["completed", "error", "requires_boundary_decision"]),
    build_result: z.record(z.unknown()).nullable().optional(),
    boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
    available_boundary_actions: z.array(scanBoundaryActionSchema).default([...]),
  });
  ```

  前端呼叫端（`frontend/src/services/projectScanApi.ts:36`）：
  ```ts
  return scanCreateResponseSchema.parse(payload);   // ← 不是 safeParse，會 throw ZodError
  ```

  `status` 的 enum **明確包含** `"requires_boundary_decision"`，代表前端**設計上要處理**這條路，
  但同一個 schema 又把 `scan_id` 設成必填 —— 兩者互斥。
  只要使用者掃到一個需要 boundary 確認的專案（`tests/web/test_scan_boundary_routes.py:76`
  `test_scan_requires_boundary_decision_before_building_map` 覆蓋的正是這個情境），
  `startProjectScan()` 就會 throw 而不是回傳 pending 狀態給 UI。
- **為什麼是問題**：直接違反 `frontend/API_CONTRACT.md:256`
  「When `requires_boundary_decision` is returned, `scan_id` is absent. The frontend must not refresh the
  graph or imply the scan completed.」—— 前端連 parse 都過不了，遑論「不刷新 graph」。
  也違反 `docs/API-GUIDE.md:234-241` 記載的 pending response 形狀。
  這是 **main 上已存在的 bug**，不是重構引入的。
- **建議改法**（前端側，最小修正）：
  `frontend/src/types.ts:210-217` 改成 discriminated union，對齊 C-5 的後端形狀：
  ```ts
  const scanPendingResponseSchema = z.object({
    status: z.literal("requires_boundary_decision"),
    project_id: z.string(),
    preflight_request_id: z.string().nullish(),
    boundary_proposals: z.array(scanBoundaryProposalSchema).default([]),
    available_boundary_actions: z.array(scanBoundaryActionSchema).default(["scan_this_run", "skip_this_run"]),
  });
  const scanCompletedResponseSchema = z.object({
    status: z.enum(["completed", "error"]),
    scan_id: z.string(),
    project_id: z.string(),
    build_result: z.record(z.unknown()).nullable().optional(),
    inventory_selection_summary: z.record(z.unknown()).nullable().optional(),
  });
  export const scanCreateResponseSchema = z.discriminatedUnion("status", [
    scanPendingResponseSchema, scanCompletedResponseSchema,
  ]);
  ```
  同時 `scanBoundaryDecisionSchema`（`types.ts:194-199`）缺少後端支援的
  `selection_scope`（`core/models/scan_boundary.py:105-107`
  `selection_scope: InventorySelectionScope = EXACT_FILE`），
  `frontend/API_CONTRACT.md:176` 有記載但 zod 沒有 —— 一併補上
  `selection_scope: z.enum(["exact_file","recursive_directory"]).optional()`。
- **影響面**：**這條就是前端契約破壞本身**。修的是前端，後端 JSON 不動。
  `frontend/src/services/projectScanApi.ts:27-37` 的回傳型別 `ScanCreateResponse`
  變成 union，所有讀 `result.scan_id` 的地方需要先 narrow
  （`grep -rn "scan_id" frontend/src/` 確認消費點後再改）。
- **相關測試**：
  - **新增**：`frontend/src/services/projectScanApi.test.ts`
    → `test parses requires_boundary_decision response without scan_id`
      —— 目前 `frontend/src` 只有 3 個測試檔
      （`SampleDataIndicator.test.tsx`、`useScanProgress.test.ts`、`http.test.ts`），
      **完全沒有 projectScanApi 的測試**，所以這個 bug 一直沒被抓到。
  - **新增**：`tests/web/test_scan_boundary_routes.py::test_pending_response_omits_scan_id`
    （後端側鎖住 wire format，讓前端可以信任）。
- **嚴重度**：**P1**（前端主要掃描流程在 boundary review 情境完全走不通）
- **風險**：中 —— 改 union 會讓所有 `ScanCreateResponse` 消費點需要 narrow，
  但 TypeScript `pnpm build`（`tsc -b`）會全部抓出來。

---

## C-7. 【P1】SSE `ScanProgressEvent` 送 `null`，前端 zod 只收 `undefined` → 進度事件全部被當成 invalid

- **位置**：後端 `src/systograph/web/schemas.py:328-345`、`routes/scan_routes.py:354-359`；
  前端 `frontend/src/types.ts:116-131`、`frontend/src/services/viewerApi.ts:35-47`
- **現況**：後端實測輸出（`ScanProgressEvent().model_dump(mode="json")`）：

  ```json
  {"event":"scan_progress","status":"completed","stage":"validate","message":"Scan completed.",
   "percent":100,
   "node_id":null,"edge_id":null,"component_id":null,"source_id":null,
   "slot":null,"evidence_id":null,
   "scan_depth":"system","timestamp":"2026-07-27T15:33:48.556248Z"}
  ```

  前端 zod（`frontend/src/types.ts:123-129`）：
  ```ts
    node_id: z.string().optional(),        // ← 接受 string | undefined，**不接受 null**
    edge_id: z.string().optional(),
    component_id: z.string().optional(),
    source_id: z.string().optional(),
    slot: z.string().optional(),
    evidence_id: z.string().optional(),
  ```

  前端消費（`frontend/src/services/viewerApi.ts:35-47`）：
  ```ts
  export function parseScanProgressEvent(rawData: string): ScanProgressEvent | null {
    if (!rawData.trim()) return null;
    try {
      return scanProgressEventSchema.parse(JSON.parse(rawData));
    } catch {
      return { event: "invalid_event", status: "warning",
               message: "Received an unrecognized scan progress event." };   // ← 一定走這裡
    }
  }
  ```

  zod v3（`frontend/package.json:23` `"zod": "^3.24.1"`）的 `z.string().optional()`
  是 `ZodOptional<ZodString>`，只放行 `undefined`，`null` 一律 fail。
  後端六個欄位全部送 `null` → `parse` throw → **每一個 SSE 事件都回傳 `invalid_event` fallback**。
  `frontend/API_CONTRACT.md:301-309` 描述的「highlights the first resolvable target in this order:
  node_id → edge_id → component_id → source_id → slot」功能因此完全失效。
- **為什麼是問題**：這是 main 上的活 bug，且**測試看不到** ——
  唯一碰到它的測試 `frontend/src/hooks/useScanProgress.test.ts:8` 把
  `parseScanProgressEvent` 整個 `vi.fn()` mock 掉了：
  ```ts
  parseScanProgressEvent: vi.fn((rawData: string) => ({ event: "progress", message: rawData })),
  ```
  後端側 `tests/web/test_map_routes.py:160` `test_scan_events_returns_sse_completed_event`
  只斷言 `'"status":"completed"' in body`，沒有驗證 null 欄位。
  兩邊測試各自綠燈，中間的 wire format 沒人守。
- **建議改法**（兩條都做，各自獨立生效）：
  1. **後端**（`schemas.py:334-339`）：六個 `X: str | None = None` 都加
     `Field(default=None, exclude_if=lambda v: v is None)`，讓 null 欄位不出現在 wire 上
     —— 但這會讓 C-5 的「exclude_if 不一致」擴大，所以**建議反過來**：
     維持送 `null`，改前端。
  2. **前端**（`frontend/src/types.ts:123-129`）：六個欄位改成
     `z.string().nullish()`（= `nullable().optional()`），與同檔 `:239-242`
     `traceEventSchema` 已經在用的 `.nullable().optional()` 寫法一致
     —— 同一個檔案裡兩種寫法並存，正是這個 bug 的來源。
  另外 `scanProgressEventSchema` 缺 `type` 以外的 nullable 覆蓋，
  `percent: z.number().min(0).max(100).optional()`（:122）與後端
  `Field(default=100, ge=0, le=100)`（`schemas.py:333`）是一致的，不用動。
- **影響面**：採建議 2 → **後端 JSON 0 變化**，只改前端 zod。
  採建議 1 → 會改 SSE wire format（移除 6 個 null key），
  但因為前端目前根本 parse 不過，實務上不會弄壞任何已運作的行為。
- **相關測試**：
  - **修改**：`frontend/src/hooks/useScanProgress.test.ts`
    → 現有的 `vi.mock` 讓真實 parser 完全沒被測到；
      至少加一個不 mock 的 case，或另開檔。
  - **新增**：`frontend/src/services/viewerApi.test.ts`
    → `test parseScanProgressEvent accepts backend null fields`
      —— 直接餵上面那段實測 JSON，斷言不是 `invalid_event`。
  - **新增**：`tests/web/test_map_routes.py::test_scan_events_payload_field_nullability`
    —— 後端側鎖住 SSE 的 key 集合。
- **嚴重度**：**P1**（掃描進度 UI 整條失效，且被 mock 掩蓋）
- **風險**：低（改前端 zod）／中（改後端 wire format，需同步文件）

---

## C-8. `ManualMappingListResponse.available_actions` 硬編 5 個字串，跟 `ManualMappingDecision` enum 對不上

- **位置**：`src/systograph/web/schemas.py:375-386` vs `src/systograph/core/models/mapping_base.py:18-22`
- **現況**：

  ```python
  # web/schemas.py:375-386
  class ManualMappingListResponse(WebSchema):
      project_id: str
      mappings: list[ManualMapping]
      available_actions: list[str] = Field(          # ← 型別是裸 list[str]
          default_factory=lambda: [
              "confirm",
              "edit",
              "reject",
              "skip_for_now",
              "mark_not_applicable",
          ]
      )
  ```
  ```python
  # core/models/mapping_base.py:18-22
  class ManualMappingDecision(StrEnum):
      CONFIRMED = "confirmed"
      REJECTED = "rejected"
      SKIP_FOR_NOW = "skip_for_now"
      NOT_APPLICABLE = "not_applicable"
  ```

  `POST /api/mappings` 收的是 `ManualMappingCreate`（`routes/mapping_routes.py:44`），
  其 `decision: ManualMappingDecision`（`mapping_base.py:28`）。
  比對：

  | advertised action | 是合法 `decision` 值嗎 |
  |---|---|
  | `confirm` | ❌（enum 是 `confirmed`） |
  | `edit` | ❌（enum 裡沒有；edit 是 PATCH 動作） |
  | `reject` | ❌（enum 是 `rejected`） |
  | `skip_for_now` | ✅ |
  | `mark_not_applicable` | ❌（enum 是 `not_applicable`） |

  5 個裡只有 1 個能直接當 `decision` 送。
  對比同一檔的 `MappingProposalListResponse:395-405` **就有**用 enum：
  ```python
      available_actions: list[MappingProposalDecisionAction] = Field(
          default_factory=lambda: [
              MappingProposalDecisionAction.ACCEPT, ...
          ]
      )
  ```
  以及 `ScanCreateResponse:247-252` 也用 `ScanBoundaryDecisionAction` enum。
  **三個 `available_actions` 欄位，兩個用 enum、一個用裸字串。**
- **為什麼是問題**：`available_actions` 的存在目的就是讓 client 知道「可以送什麼」。
  現在它是一份與實際 API 對不上的清單，client 照抄會拿 422。
  `docs/API-GUIDE.md:806` 原封不動抄了同一份錯誤清單
  （`available_actions: ["confirm","edit","reject","skip_for_now","mark_not_applicable"]`），
  所以文件、程式、測試三方一起錯 —— `tests/web/test_mapping_routes.py:39-45`
  的 `test_mapping_routes_create_and_list_confirmed_mapping` 正在**鎖住這個錯誤**。
  對照 `docs/MODEL-CONTRACT.md` §10.1 Manual Mapping，這些 UI 動詞與 `decision` 值的
  對應關係從來沒有被定義在契約裡。
- **建議改法**：先決定語意，再改型別：
  - **若 `available_actions` 是 UI 動詞**（confirm/edit/…）：定義一個
    `ManualMappingUiAction(StrEnum)` 放在 `core/models/mapping_base.py`
    （與 `ManualMappingDecision` 並列，明確標註「UI 動詞，非 decision 值」），
    web 欄位改成 `list[ManualMappingUiAction]`，並在
    `docs/MODEL-CONTRACT.md` §10.1 補一張 UI 動詞 → `decision` 值的對照表。
  - **若它應該是 decision 值**：改成
    `list[ManualMappingDecision]` + `default_factory=lambda: list(ManualMappingDecision)`，
    這會把 wire 上的字串換成 `["confirmed","rejected","skip_for_now","not_applicable"]`。
  我建議第一種（因為 `edit` 明顯是 UI 動作，不是 decision）。
- **影響面**：
  - 第一種：**JSON 值不變**（字串一樣），只是型別從 `list[str]` 變 enum → OpenAPI schema 收窄。
  - 第二種：**⚠️ 改 JSON 輸出**（5 個字串換成 4 個）。
  - 前端依賴：`frontend/src/types.ts:363`
    `available_actions: z.array(z.string()).default([])` —— 用的是 `z.array(z.string())`，
    兩種改法都 parse 得過。但那一段是 `Scan Template / Mapping Profile (NEW API — not yet implemented)`
    區塊（`types.ts:261-266` 的註解），不是 `/api/mappings` 的消費者。
    `grep -rn "api/mappings" frontend/src/` **無命中** —— 前端目前根本沒有呼叫這支 endpoint，
    所以現在改的破壞面是零。
- **相關測試**：
  - **修改**：`tests/web/test_mapping_routes.py::test_mapping_routes_create_and_list_confirmed_mapping`
    （:10，斷言在 :39-45）—— 這個測試現在正在鎖住錯誤清單。
  - **新增**：`tests/unit/web/test_mapping_actions_alignment.py`
    → `test_advertised_actions_map_to_manual_mapping_decisions`
      —— 斷言每個 advertised action 都能對應到一個 `ManualMappingDecision`（或明確標記為 UI-only）。
  - **文件**：`docs/API-GUIDE.md:806` 必須同步。
- **嚴重度**：P2（前端尚未消費，但這是一份會誤導 client 的公開契約）
- **風險**：低（第一種）／中（第二種，會改 wire）

---

## C-9. `POST /api/map/build` 與 `POST /api/scans` 直接把 core `MapBuildResult` 當 response，含 absolute path

- **位置**：`src/systograph/web/routes/map_routes.py:22-34`、
  `src/systograph/web/schemas.py:243`（`build_result: MapBuildResult | None`）、
  `src/systograph/web/routes/scan_routes.py:344-351`
- **現況**：三種 build response 形狀並存：

  | endpoint | response model | 含 `*_path` / `output_run_dir`？ | 含完整 `ai_system_map`？ |
  |---|---|---|---|
  | `POST /api/map/build` | core `MapBuildResult`（`map_routes.py:22`） | ✅ 12 個路徑欄位全都在 | ✅ |
  | `POST /api/scans` | `ScanCreateResponse.build_result: MapBuildResult`（`schemas.py:243`） | ✅ 同上 | ✅ |
  | `GET /api/map-builds/{id}` 等 3 支 | `MapBuildScopedResponse.build_result: Phase2MapBuildResult`（`schemas.py:143`） | ❌ 已剝除 | ❌ 只留 profile/readiness |

  `MapBuildResult`（`core/models/map_build.py:70-97`）的 12 個 `Path | None` 欄位
  （`output_run_dir`、`map_json_path`、…、`execution_map_mermaid_path`）會被 FastAPI 直接
  序列化成字串。實際上就是 absolute path —— `tests/web/test_map_routes.py:19` 傳的是
  `"output": str(tmp_path / "outputs")`（絕對路徑），回來的 `map_json_path` 就是絕對路徑。
- **為什麼是問題**：`docs/MODEL-CONTRACT.md` §7.1 明文
  「Target API 用 safe refs（**不**暴露 absolute path）。Current v1 `*_path` 為 compatibility-only。」
  §7.2「這個 build-scoped S1 envelope 不暴露 `output_run_dir` 或 `*_path`。」
  `docs/API-GUIDE.md:376-377` 也寫「Current runtime 的 `output_run_dir` 與 `*_path` 可能是
  server-local absolute path，僅屬 compatibility contract。Phase2 target response
  不得新增或延續 absolute-path 欄位。」
  問題在於：`/api/map/build` 被 API-GUIDE:55 歸類為 **demo**（可接受），
  但 `/api/scans` 被歸類為 **project**（API-GUIDE:53），是
  `frontend/API_CONTRACT.md:159-180` 記載的**前端主要掃描入口** ——
  它卻沿用了 demo 的 path-bearing 形狀。
  API-GUIDE:410 的表格「Artifacts | build-scoped response 不回 path；demo 保留 `*_path`」
  與 `/api/scans` 的實作直接矛盾。
  另外 `/api/scans` 把整份 `ai_system_map`（`AiSystemMapV2`，`core/models/ai_system_map_v2.py`
  609 行的 model）inline 回傳，payload 很大且與 `GET /api/map` 重複
  —— `frontend/API_CONTRACT.md:264` 明說「After a completed scan, the frontend reloads
  `GET /api/map`」，也就是前端根本不用 `/api/scans` 回來的 map。
  對照 `secret_masking_service.py` / `path_safety_service.py` / `system_map_secret_boundary.py`
  的存在（整個 repo 花大力氣做 masking），這裡是 masking 走廊上的一個缺口
  —— 雖然被文件標記為 compatibility，但 CLAUDE.md 的「Local-first privacy」原則
  與這個現況是張力關係。
- **建議改法**：
  1. `schemas.py:243` 的 `build_result: MapBuildResult | None` 改成
     `Phase2MapBuildResult | None`，`scan_routes.py:348` 的
     `build_result=result` 改成 `build_result=Phase2MapBuildResult.from_core(result)`。
     這讓 `/api/scans` 與 `/api/map-builds/*` 用同一個去路徑化 envelope。
  2. `/api/map/build`（demo）維持現狀，但在 `map_routes.py:22` 加註解指向
     `MODEL-CONTRACT.md §7.1`，並在 `docs/API-GUIDE.md` 把它明確標成 deprecated-demo。
  3. 中期：依 §7.1 的 `ArtifactRef` 型別（`artifact_id` / `artifact_type` / `file_name`(basename only)
     / `media_type` / `sha256` / `size_bytes`）新增 `schemas/artifact.py::ArtifactRef`，
     取代所有 `*_path`。
- **影響面**：**⚠️ 建議 1 會破壞前端契約（wire format 變更）。**
  - `/api/scans` 的 `build_result` 從 ~25 個欄位（含 12 個路徑 + 完整 map）縮成 10 個欄位。
  - 前端依賴查證：`frontend/src/types.ts:214`
    `build_result: z.record(z.unknown()).nullable().optional()` ——
    **zod 用的是 `z.record(z.unknown())`，任何 object 都 parse 得過**，
    所以前端 parse 不會壞。
    `grep -rn "build_result" frontend/src/` 只命中 `types.ts:214` 一處，
    **沒有任何前端程式碼實際讀取 `build_result` 的內容**。
    → 實務破壞面：**零**。但 wire format 確實改了，`frontend/API_CONTRACT.md:189`
    的 `build_result?: unknown;` 與 `docs/API-GUIDE.md:253` 的
    `build_result: MapBuildResult;` 必須同步改成 `Phase2MapBuildResult`。
  - **後端測試會壞**：`tests/web/test_legacy_mapping_write_rejection.py:88-90` 讀了
    `scan_payload["build_result"]["ai_system_map"]["unmapped_components"][0]["unmapped_id"]`
    —— `Phase2MapBuildResult` 沒有 `ai_system_map`，這個測試一定紅。
- **相關測試**：
  - **修改**：`tests/web/test_legacy_mapping_write_rejection.py::test_proposal_decision_rejects_legacy_type_with_stable_code`
    （:53，讀取在 :88-90）→ 改成從 `GET /api/map` 或 `GET /api/map-builds/{id}` 取 unmapped_id。
  - **修改**：`tests/web/test_project_scan_routes.py::test_scan_create_builds_imported_project`（:63）
    —— 需確認它是否讀 `build_result` 的路徑欄位。
  - **修改**：`tests/e2e/test_inventory_selection_scan_flow.py::test_inventory_selection_scan_is_read_only_and_auditable`（:49）
  - **新增**：`tests/contracts/test_response_path_boundary.py`
    → `test_scan_response_contains_no_absolute_paths`
      —— 掃 `/api/scans` 的 JSON，斷言沒有任何值符合 absolute path pattern
      （可重用 `path_safety_service.contains_local_path`）。這條目前**不存在**。
- **嚴重度**：P2（文件已承認為 compatibility，但 `/api/scans` 屬 project workflow，
  與 §7.2 直接矛盾；且無測試守護）
- **風險**：中 —— 會動到 3-4 個既有測試；但前端零實質依賴，回滾成本低。

---

## C-10. `WebSchema` 的 `model_config` 與 core model base 不一致（`frozen` 缺席、`arbitrary_types_allowed` 疑似多餘）

- **位置**：`src/systograph/web/schemas.py:43-46` vs 四個 core base
- **現況**：

  | base class | 檔案:行號 | `extra` | `frozen` | `arbitrary_types_allowed` |
  |---|---|---|---|---|
  | `WebSchema` | `web/schemas.py:46` | `forbid` | ❌ 無 | ✅ True |
  | `MapBuildModel` | `core/models/map_build.py:38` | `forbid` | ❌ 無 | ✅ True |
  | `AnalysisHistoryModel` | `core/models/analysis_history.py:24` | `forbid` | ✅ **True** | ❌ 無 |
  | `InventorySelectionModel` | `core/models/inventory_selection.py:11` | `forbid` | ✅ **True** | ❌ 無 |
  | `ErrorModel` | `core/models/errors.py:14` | `forbid` | ❌ 無 | ❌ 無 |

  `extra="forbid"` 是全線一致的（好事）。`frozen` 與 `arbitrary_types_allowed` 是 2×2 隨機分佈。

  `arbitrary_types_allowed=True` 在 `WebSchema` 上疑似多餘：逐一檢查 27 個 class 的欄位型別
  —— `str`、`bool`、`int`、`float`、`Literal`、`list[...]`、`tuple[str, ...]`、
  `dict[str, str | int]`、StrEnum（`InventoryTargetKind` 等）、以及 pydantic BaseModel
  （`ProfileInferenceResult`、`ReadinessReport`、`ViewerLoadResult`、`MapBuildResult`、
  `AiSystemMapV2`、`DetailScanResult`、`ManualMapping`、`MappingProposal`、
  `ScanBoundaryProposal`、`InventorySelectionSummary`、`InventoryDirectoryLimitContext`、
  `MapBuildManifest`）—— **沒有一個需要 `arbitrary_types_allowed`**。
  巢狀的 `MapBuildResult` 帶 `Path`，但 `Path` 是 Pydantic 原生支援型別，
  且巢狀 model 用的是自己的 config（`MapBuildModel`），不吃 `WebSchema` 的。
- **為什麼是問題**：`arbitrary_types_allowed=True` 會讓「加了一個 Pydantic 不認識的型別」
  從 **build-time error** 降級成 **runtime isinstance check**
  —— 這正好抵銷 `extra="forbid"` 想達到的「reject silent API contract drift」
  （`schemas.py:44` 自己寫的 docstring）。
  `frozen` 缺席則代表 response model 在 route 裡是可變的
  （`map_build_routes.py:75`、`trace_routes.py:79` 都用 `model_copy(update=...)`，
  那是 core model 不是 web model，但 web model 沒有任何保護）。
- **建議改法**：
  1. 在 `schemas/base.py` 把 `WebSchema` 改成
     `model_config = ConfigDict(extra="forbid", frozen=True)`，
     移除 `arbitrary_types_allowed`。
  2. 先跑 `uv run mypy src tests` + `uv run pytest tests/web tests/e2e` 驗證：
     若某個欄位真的需要 arbitrary type，會立刻在 model 建構時報
     `PydanticSchemaGenerationError`，屆時再局部加回。
  3. `frozen=True` 若造成問題（例如某個 route 想 `model_copy`），
     先確認是否應該改成 core 的 `AnalysisHistoryModel` 那種一致做法。
- **影響面**：**JSON 輸出 0 變化**（`frozen` 與 `arbitrary_types_allowed` 都不影響序列化）。
  前端零影響。
- **相關測試**：
  - **不需改**：所有 `tests/web/` 測試走 HTTP。
  - **新增**：`tests/unit/web/test_schema_base_config.py`
    → `test_web_schema_forbids_extra_and_is_frozen`
      —— 斷言 `WebSchema.model_config["extra"] == "forbid"` 且 `frozen is True`。
- **嚴重度**：P3
- **風險**：低 —— pydantic 會在 import 時就報錯，不會有潛伏 runtime 問題。

---

## C-11. `Field()` 全檔零 `description` / `examples`，OpenAPI 沒有任何語意；沒有任何 `responses=` 宣告

- **位置**：`src/systograph/web/schemas.py` 20 個 `Field(` 呼叫（99、100、127、230、237、244、247、
  253、264、282、308、312、315、318、333、341、364、372、378、398 行）
- **現況**：20 個 `Field()` 只用了 `default` / `default_factory` / `min_length` / `ge` / `le` /
  `gt` / `exclude_if`，**沒有一個帶 `description` 或 `examples`**
  （`grep -rn "description=\|examples=\|json_schema_extra" src/systograph` 在整個
  `src/systograph/web/` 底下零命中；只有 `core/models/system_map.py:111,194` 兩處用了 `description=`）。

  所有 route 也都沒有宣告 `responses={...}`
  （`grep -rn "responses=" src/systograph/web/routes/*.py` 零命中），
  所以 `InventoryApiErrorDetail`（`schemas.py:321-325`）這個 error envelope
  **完全不在 OpenAPI schema 裡** —— client 從 `/openapi.json` 看不到 422 的形狀，
  只能讀 `frontend/API_CONTRACT.md:259` 那句手寫的
  「A stale/changed selection uses `{detail:{code,message,retryable,context}}`」。

  `Field()` 的用法也不統一：
  - `Field(default=None, exclude_if=...)`（:237, :253）明寫 `default=`
  - `Field(min_length=1)`（:127）沒有 default（欄位必填）
  - `Field(default_factory=list)`（:99, :100, :282, :308, :312, :315, :318, :364）
  - `Field(default_factory=lambda: [...])`（:247, :378, :398）—— 常數 list 卻用 lambda
  - `Field(default=100, ge=1, le=200)`（:264）／`Field(default=100, ge=0, le=100)`（:333）
    ／`Field(default=30.0, gt=0, le=120)`（:372）—— 數值約束有 3 種不同組合，沒有共用 alias
- **為什麼是問題**：`docs/API-GUIDE.md` + `frontend/API_CONTRACT.md` 是手寫維護的，
  與程式碼沒有任何機械化連結（C-8 就是手寫文件抄錯的活例）。
  Field description + `responses=` 能讓 `/openapi.json` 成為 single source of truth，
  減少手寫文件漂移。這正是 C-8 那類 bug 的結構性成因。
- **建議改法**：
  1. 在 `schemas/base.py` 定義共用 annotated alias，消掉重複的數值約束：
     ```python
     Percent = Annotated[int, Field(ge=0, le=100)]
     PageLimit = Annotated[int, Field(ge=1, le=200)]
     TimeoutSeconds = Annotated[float, Field(gt=0, le=120)]
     ```
  2. `Field(default_factory=lambda: [...])`（:247, :378, :398）改成模組層常數
     + `default_factory=lambda: list(_DEFAULT_BOUNDARY_ACTIONS)`，避免每次都重建 lambda closure。
  3. 給每個 **request** model 的欄位補 `description=`（response 可延後），
     優先補 `ScanCreateRequest`、`InventoryPreflightApiRequest`、`DetailScanCreateRequest`、
     `TraceCreateRequest` 這 4 個 client 直接填的。
  4. 在 inventory 的兩支 route（`scan_routes.py:79-82` preflight、`:127-130` scans）加
     `responses={422: {"model": InventoryApiErrorDetailEnvelope}}`，
     把 error 形狀放進 OpenAPI。
- **影響面**：**JSON 輸出 0 變化**（description 只影響 `/openapi.json`）。前端零影響。
- **相關測試**：
  - **新增**：`tests/contracts/test_openapi_documents_error_shapes.py`
    → `test_inventory_routes_declare_422_schema`
      —— 讀 `create_app().openapi()`，斷言 preflight/scan route 有 422 定義。目前不存在。
- **嚴重度**：P3
- **風險**：低。

---

## C-12. `inventory_error_response.py`：只有 inventory 有結構化 error envelope，其他 route 全是裸 `detail: str`

- **位置**：`src/systograph/web/inventory_error_response.py:1-86`；
  對照 `src/systograph/web/schemas.py:321-325`（`InventoryApiErrorDetail`）
- **現況**：整個 web 層有**兩種**錯誤形狀：

  **A. inventory 專屬結構化 envelope**（`inventory_error_response.py:54-85`，3 個工廠函式）：
  ```python
  def inventory_error_detail(error: InventorySelectionError) -> dict[str, object]:
      return InventoryApiErrorDetail(
          code=error.code.value,
          message=ERROR_MESSAGES[error.code],     # ← :11-51 的 13 條人類可讀訊息
          retryable=error.retryable,
          context=error.context,
      ).model_dump(mode="json")
  ```
  → wire 上是 `{"detail": {"code": "...", "message": "...", "retryable": bool, "context": {...}}}`

  **B. 其他所有 route 的裸字串**：
  ```python
  raise HTTPException(status_code=404, detail="project_not_found")     # project_routes.py:28
  raise HTTPException(status_code=404, detail="build_not_found")       # map_build_routes.py:90
  raise HTTPException(status_code=409, detail="base_build_not_latest") # map_build_routes.py:61
  raise HTTPException(status_code=422, detail=str(exc))                # mapping_routes.py:54,75
  raise HTTPException(status_code=422, detail="legacy_mapping_type_read_only")  # legacy_mapping_guards.py:37
  ```
  → wire 上是 `{"detail": "project_not_found"}`

  **同一支 endpoint 兩種都有**：`scan_routes.py:98-101` 用 A（`project_not_found_detail()`），
  但 `project_routes.py:28`、`detail_scan_routes.py:56`、`trace_routes.py:40`、
  `mapping_proposal_routes.py:69` 對**同一個「專案不存在」語意**用 B（`detail="project_not_found"`）。
  `inventory_error_response.py:65-70` 的 `project_not_found_detail()` 因此只在 inventory
  相關的 2 個地方被用到（`scan_routes.py:100`、`:165`）。

- **為什麼是設計還是過渡**：從證據看是**刻意設計但只做了一半**：
  - `frontend/API_CONTRACT.md:259` 明文記載
    「A stale/changed selection uses `{detail:{code,message,retryable,context}}`；
      refresh preflight rather than silently reusing decisions.」
    → 有 `retryable` 與 `context` 是為了讓前端能決定「要不要重跑 preflight」，這是真需求。
  - `docs/API-GUIDE.md:282` 也記載了 inventory 的 error code 表。
  - `InventorySelectionError`（`core/models/errors.py:79-95`）本身就帶
    `http_status` / `retryable` / `context` 三個欄位，是**core 層刻意設計的結構化錯誤**。
  結論：A 是正確方向，B 是舊寫法；不是過渡 hack，而是**新標準只鋪了 inventory 一條路**。
- **被誰用（實際 grep）**：`grep -rn "inventory_error_response" src tests` →
  只有 `src/systograph/web/routes/scan_routes.py:50-54`（import 三個函式）
  以及 6 個呼叫點（`:100, 118, 123, 165, 257, 262, 329, 334`）。**零測試直接 import**。
- **為什麼是問題**：
  1. `ERROR_MESSAGES`（:11-51）是一個 13 entry 的 dict，用 `ERROR_MESSAGES[error.code]`
     **直接索引**（:59）。`InventorySelectionErrorCode`（`core/models/errors.py:61-76`）目前正好 13 個，
     但**沒有任何測試斷言兩者同步** —— core 新增一個 error code 而忘記加訊息 → `KeyError`
     → 被 `SafeUnhandledExceptionMiddleware`（`middleware.py:105-121`）吞成 500，
     使用者拿到 `internal_server_error` 而不是 422。這是 fail-open 成 500 的路徑。
  2. 人類可讀訊息（英文 UI 文案）住在 `web/` 層，但 error code 住在 `core/models/errors.py`
     —— 加一個 code 要改兩層兩個檔。
  3. 錯誤形狀不在 OpenAPI（見 C-11）。
- **建議改法**：
  1. **立即**：`inventory_error_detail` 的 `ERROR_MESSAGES[error.code]` 改成
     `ERROR_MESSAGES.get(error.code, "Inventory selection could not be completed.")`，
     消掉 KeyError→500 的路徑。
  2. **新增測試**（見下），把「13 個 code 都有訊息」鎖住。
  3. **中期**：把 A 提升成全域標準 —— 在 `schemas/errors.py` 定義
     `ApiErrorDetail(WebSchema)`（`code` / `message` / `retryable` / `context`），
     `InventoryApiErrorDetail` 變成它的別名或子類，
     並把 `project_not_found` / `build_not_found` / `map_not_loaded` /
     `base_build_not_latest` / `scan_snapshot_stale` / `profile_sidecar_unavailable`
     這些散落的字串收攏成一個 `ApiErrorCode(StrEnum)`。
     **注意這會改所有 route 的 error wire format**（`{"detail":"x"}` → `{"detail":{"code":"x",...}}`），
     必須分階段。
  4. 檔案搬家：`inventory_error_response.py` 的 13 條訊息屬於 inventory 領域，
     建議與 C-1 一起搬到 `schemas/inventory.py` 旁邊，或保留獨立檔但改名
     `web/error_responses/inventory.py`。
- **影響面**：
  - 建議 1、2：**JSON 輸出 0 變化**。
  - 建議 3：**⚠️ 會破壞前端契約**。前端依賴查證：
    `frontend/src/types.ts:142-146`
    ```ts
    export const apiErrorSchema = z.object({
      detail: z.union([z.string(), z.record(z.unknown()), z.array(z.unknown())]).optional(),
    }).passthrough();
    ```
    → `z.union([z.string(), z.record(z.unknown()), ...])` **兩種形狀都收**，
    所以前端 parse 不會壞。但任何讀 `detail` 當字串用的地方會壞
    —— `grep -rn "apiErrorSchema\|\.detail" frontend/src/` 需要在動手前完整查一次。
- **相關測試**：
  - **新增**：`tests/unit/web/test_inventory_error_messages.py`
    → `test_every_selection_error_code_has_message`
      —— `assert set(InventorySelectionErrorCode) == set(ERROR_MESSAGES)`。
      **這條目前完全不存在**，是最高 CP 值的一條。
  - **不需改**：`tests/web/test_inventory_preflight_routes.py::test_preflight_errors_use_typed_detail_and_do_not_create_scan`（:214）、
    `::test_scan_selection_errors_are_typed_and_create_no_snapshot`（:298）
    —— 這兩條已經在守 A 形狀。
  - 若做建議 3：**修改** `tests/web/test_local_api_hardening.py::test_malformed_state_ids_return_stable_404`（:100）
    以及所有斷言 `response.json()["detail"] == "..."` 的測試（約 15 處，
    `grep -rn 'json()\["detail"\]' tests/` 可列全）。
- **嚴重度**：P2（建議 1 的 KeyError→500 路徑）／P3（整體收斂）
- **風險**：低（1、2）／高（3 —— 全站 error wire format 變更）

---

## C-13. `inventory_preflight_projection.py`：projection 邏輯放在 web 層，且重建了 core 已經丟掉的 index

- **位置**：`src/systograph/web/inventory_preflight_projection.py:26-115`
- **現況**：這是整個 `web/` 底下**唯一**的 projection 模組。core 有一整族 projection service：
  - `core/services/graph_projection_service.py:54` `GraphProjectionService.project()`
  - `core/services/profile_registry_projection_service.py:15` `ProfileRegistryProjectionService.project()`
  - `core/services/reference_map_overlay_projector.py`
  - `core/services/graph_lens_projector.py`
  - `core/services/viewer_session_service.py:180` `ViewerSessionService.project_to_graph()`

  而 `project_inventory_preflight()` 做的事遠超過「格式轉換」：

  ```python
  # inventory_preflight_projection.py:33-41 —— 建索引
  proposals = boundary_service.create_selection_proposals(state)
  by_target = {
      (proposal.target.path, proposal.selection_context.selection_scope): proposal
      for proposal in proposals
      if proposal.selection_context is not None
  }
  ```

  **這個 dict 是 core 剛剛才丟掉的東西。**
  `core/services/inventory_selection_proposal_service.py:29-70`：
  ```python
  proposals: dict[tuple[str, InventorySelectionScope], ScanBoundaryProposal] = {}   # :30-31
  ...
  return sorted(proposals.values(), key=lambda item: (...))                          # :63-70
  #      ^^^^^^^^^^^^^^^^^^^^^^^^^ key 被丟棄
  ```
  → core 建了 keyed dict → 回傳時 `.values()` 丟掉 key → web 用完全一樣的 key 規則重建。

  再看業務判斷（不是格式轉換）：
  ```python
  # :47-51 —— 決定「哪些是必須 review 的」
  required = [
      by_target[(candidate.path, InventorySelectionScope.EXACT_FILE)]
      for candidate in state.candidate_set.candidates
      if candidate.decision_required
  ]

  # :55-61 —— 決定 target 該用哪個 selection scope
  if result.status == InventoryRequestedTargetStatus.REVIEWABLE:
      scope = (
          InventorySelectionScope.RECURSIVE_DIRECTORY
          if result.directory_manifest is not None
          else InventorySelectionScope.EXACT_FILE
      )
      proposal = by_target[(result.target_path, scope)]

  # :113 —— 決定排序
  blocked_summaries=sorted(blocked, key=lambda item: item.path),
  ```

  另外 `:94` `datetime.now(UTC).isoformat().replace("+00:00","Z")` 是
  `schemas.py:209-211` 與 `:341-345` 已經出現過的同一段字串，第三次複製。

- **為什麼是問題**：
  1. 直接違反 `CLAUDE.md` 的
     「**Core engine is platform-independent** — CLI, Web API, and launchers must not duplicate
       core scanner logic.」CLI 若日後要輸出同一份 preflight view，得複製這 90 行。
  2. repo 自己有一條測試在守這條線：
     `tests/web/test_viewer_routes.py:59` `test_viewer_route_is_thin_adapter_without_project_scan_logic`
     用 `inspect.getsource(viewer_routes)` 斷言 route 不含 scan 邏輯 ——
     **這個標準只套用在 viewer_routes，沒有套用在 `inventory_preflight_projection.py`。**
  3. **隱性跨層不變量 + KeyError→500 風險**：`:48`、`:61`、`:106` 三處都是**直接索引** `by_target[...]`。
     目前之所以不炸，是因為
     `inventory_selection_proposal_service.py:32-35` 只把
     `decision_required or base_outcome == SOFT_EXCLUDED` 的 candidate 放進 dict，
     而 `:48` 查的是 `decision_required`（子集，安全）、
     `:106` 查的是 `page.items`，而
     `inventory_preflight_cursor_service.py:28-32` 只回傳 `SOFT_EXCLUDED`（也是子集，安全）。
     這條「core 的 proposal 覆蓋率 ⊇ web 的查詢集合」不變量橫跨
     **3 個 core 檔 + 1 個 web 檔**，沒有任何型別或測試保證。
     core 那邊任一個條件改動 → web 這邊 `KeyError` →
     `SafeUnhandledExceptionMiddleware`（`middleware.py:105-121`）吞成
     `500 internal_server_error`。
- **建議改法**：
  1. **搬家**：新增 `core/services/inventory_preflight_projection_service.py`
     `class InventoryPreflightProjectionService: def project(state, request, *, preflight_service, boundary_service) -> InventoryPreflightView`。
     core 回傳一個 core-owned view model（放 `core/models/inventory_selection.py`），
     web 只做 `InventoryPreflightResponse.model_validate(view)` 或直接用 core view 當 response model。
  2. **消掉重建索引**：讓 `InventorySelectionProposalService` 多開一個
     `create_indexed(state) -> dict[tuple[str, InventorySelectionScope], ScanBoundaryProposal]`，
     現有 `create()` 改成 `sorted(self.create_indexed(state).values(), key=...)`。
     projection 直接用 `create_indexed()`，web/core 不再各建一次。
  3. **消掉 KeyError**：三處 `by_target[...]` 改成 `.get(...)`，
     查不到時 raise 一個 typed `InventorySelectionError`（core 已有這個 exception 型別，
     `core/models/errors.py:79`），走既有的 422 typed detail 路徑而不是 500。
  4. `to_iso_z()` 抽成共用 helper（見 C-3 建議 4）。
- **影響面**：**JSON 輸出 0 變化**（只是把同一段計算搬到 core）。
  前端依賴：`frontend/API_CONTRACT.md:121-152` 的 `ScanInventoryPreflightResponse`
  形狀不變。`frontend/src/types.ts` 對 preflight **沒有任何 zod schema**
  （`grep -n "preflight" frontend/src/types.ts` 無命中），所以前端零影響。
- **相關測試**：
  - **不需改**：`tests/web/test_inventory_preflight_routes.py` 6 個測試全走 HTTP。
  - **新增**：`tests/unit/core/test_inventory_preflight_projection_service.py`
    → `test_projection_matches_every_required_candidate_to_a_proposal`、
      `test_projection_raises_typed_error_when_proposal_missing`
      —— 把那條跨 4 個檔的隱性不變量變成明確測試。**目前完全沒有單元測試**
      （`ls tests/unit/` 底下沒有對應檔）。
  - **可選新增**：把 `test_viewer_route_is_thin_adapter_without_project_scan_logic`
    的手法推廣成 `tests/web/test_web_layer_is_thin.py`，斷言 `src/systograph/web/`
    底下沒有模組 import 兩個以上 core service（projection 搬走後就成立）。
- **嚴重度**：P2
- **風險**：中 —— 搬 90 行跨層，但輸出可以逐欄位比對；建議先加 golden-JSON 測試再搬。

---

## C-14. `legacy_mapping_guards.py`：它守的不是 `ai-system-map/v1`，v1 退場後**不能**刪

- **位置**：`src/systograph/web/legacy_mapping_guards.py:1-39`
- **它守什麼**：一個**已退場的 manual mapping 寫入型別** `"new_extension_component"`。
  ```python
  _LEGACY_MAPPING_TYPE = LegacyManualMappingType.NEW_EXTENSION.value    # :13 → "new_extension_component"

  async def reject_legacy_mapping_type(request: Request) -> None:
      """Fail closed with a stable code before Pydantic enum validation."""   # :29
      try:
          payload = await request.json()                                       # :31 ← 第二次 parse body
      except json.JSONDecodeError:
          return
      if _payload_contains_legacy_mapping_type(payload):
          raise HTTPException(status_code=422, detail="legacy_mapping_type_read_only")   # :35-38
  ```
  對照 active enum `ManualMappingType`（`core/models/mapping_base.py:13-15`）：
  只有 `existing_slot_mapping` / `non_baseline_capability_candidate`
  —— `new_extension_component` 已經**不在** active enum 裡。
  所以沒有這個 guard，請求還是會被擋（Pydantic enum 驗證 → 422），
  只是 `detail` 會變成 FastAPI 的 `RequestValidationError` 陣列而不是穩定字串。
  **這個 guard 的唯一價值是把 422 的 `detail` 從噪音變成穩定 code。**
- **被誰用（實際 grep）**：
  - `src/systograph/web/routes/mapping_routes.py:18`（import）、`:42`
    （`POST /api/mappings` 的 `dependencies=[Depends(reject_legacy_mapping_type)]`）
  - `src/systograph/web/routes/mapping_proposal_routes.py:26`（import）、`:100`
    （`POST /api/mapping-proposals/{id}/decision`）
  - 測試：`tests/web/test_legacy_mapping_write_rejection.py`
    → `test_mapping_api_rejects_legacy_type_with_stable_code`（:28，斷言在 :49-50）
    → `test_proposal_decision_rejects_legacy_type_with_stable_code`（:53，斷言在 :118-119）
  - `PATCH /api/mappings/{id}`（`mapping_routes.py:57-58`）沒有掛這個 guard，
    但**已查證不是漏洞**：`ManualMappingUpdate`（`core/models/mapping_base.py:82-92`）
    **沒有 `mapping_type` 欄位**，且 base `MappingModel`（`:9-10`）是 `extra="forbid"`
    —— 送 `mapping_type` 會被 Pydantic 直接擋掉。**不需要補 guard。**
- **與三個 legacy service 的關係**（實際 grep 求證）：

  | service | 與這個 guard 的關係 |
  |---|---|
  | `legacy_manual_mapping_migration_service.py` | ✅ **直接依賴**：guard `:9-10` 從它 import `LegacyManualMappingType`（`:32-33` 定義）。同檔 `:170` 也用 `LegacyManualMappingType.NEW_EXTENSION.value` 做讀取端遷移。CLI `cli/migrate_legacy_mappings_command.py:8` 也用它。 |
  | `legacy_v1_rollback_service.py` | ❌ **完全無關**。它只被 `core/services/map_build_service.py:56-57,126` 用，處理的是 `ai-system-map/v1` 輸出 rollback。 |
  | `system_map_v1_to_v2_adapter.py` | ❌ **完全無關**。只被 `core/services/canonical_map_loader.py:25` 用，處理 v1 map 讀取轉 v2。 |

  → **「v1 退場後這檔能不能刪」的答案是「不能」。**
  `tests/contracts/test_v2_cutover_consumer_allowlist.py:78-85` 把
  `legacy_manual_mapping_migration_service.py` 的 `new_extension_component` 標成
  `classification="migration_only"`、`removal_plan="Plan 15 removes the legacy migration DTO and command."`
  —— 這個 guard 的生命週期綁在 **Plan 15 移除 legacy mapping migration** 上，
  跟 `ai-system-map/v1` 退場（也是 Plan 15，但不同項）是兩件事。
  另外 `legacy_mapping_guards.py` 本身**不在** allowlist 裡（allowlist 掃的 symbol 是
  `ai-system-map/v1` / `RagSystemMap` / `new_extension_component` 字面值，
  而 guard 用的是 `LegacyManualMappingType.NEW_EXTENSION.value` 而非字面字串，所以沒被掃到）
  —— 這是一個 allowlist 的盲點。
- **刪掉會影響什麼**：
  1. `POST /api/mappings` 與 `POST /api/mapping-proposals/{id}/decision` 送 legacy type 時，
     422 的 `detail` 從 `"legacy_mapping_type_read_only"` 變成 FastAPI 的
     validation error 陣列（仍然是 422，仍然被擋）。
  2. `tests/web/test_legacy_mapping_write_rejection.py` 兩個測試會紅。
  3. 沒有安全性損失（不是 fail-open）。
- **其他問題**：
  1. **雙重 JSON parse**：`await request.json()`（:31）在 route handler 之前跑，
     然後 FastAPI 又 parse 一次給 `ManualMappingCreate`。
     Starlette 會 cache `request._body`（不會重讀 socket），但 `json.loads` 跑兩次。
     這在 `DEFAULT_MAX_REQUEST_BODY_BYTES = 1_000_000`（`middleware.py:17`）的上限下
     等於最多多 parse 1MB JSON —— 兩個 route 都是低頻寫入，實務衝擊小，但是設計味道不對。
  2. **檔案沒有覆蓋 PATCH**：`mapping_routes.py:57-58` 的
     `PATCH /api/mappings/{mapping_id}` 沒掛 guard，
     若 `ManualMappingUpdate`（`core/models/mapping_base.py`）含 `mapping_type`，
     這是一個繞過口。**需驗證** `ManualMappingUpdate` 是否有 `mapping_type` 欄位。
  3. 檔名 `legacy_mapping_guards.py` 的「legacy」語意曖昧
     —— repo 裡「legacy」大多指 `ai-system-map/v1`（見 `docs/MODEL-CONTRACT.md` §11），
     這裡卻指 retired mapping type。
- **建議改法**：
  1. **改名**：`legacy_mapping_guards.py` → `retired_mapping_type_guard.py`，
     函式 `reject_legacy_mapping_type` → `reject_retired_mapping_type`，
     module docstring 明寫「這與 ai-system-map/v1 無關；生命週期綁 Plan 15 legacy mapping migration」。
  2. ~~補 PATCH~~ —— **已查證不需要**（見上，`ManualMappingUpdate` 無 `mapping_type` 且 `extra="forbid"`）。
  3. **消掉雙重 parse 的替代方案**：改用 FastAPI 的
     `RequestValidationError` exception handler，在 `web/app.py` 統一把
     「mapping_type 的 enum 驗證失敗且值是 `new_extension_component`」的 422 改寫成穩定 code。
     這樣就不需要事前讀 body。**但這會改所有 route 的 422 形狀**，風險較高，可延後。
  4. **加進 allowlist**：`tests/contracts/test_v2_cutover_consumer_allowlist.py` 補一筆
     `ConsumerRecord(path="src/systograph/web/legacy_mapping_guards.py", symbol="new_extension_component",
     classification="migration_only", removal_plan="Plan 15 removes the retired mapping type guard.")`
     —— 讓它跟 migration service 一起被追蹤移除。
- **影響面**：
  - 建議 1、4：**JSON 輸出 0 變化**。前端零影響（`grep -rn "api/mappings" frontend/src/` 無命中）。
  - 建議 2：若 legacy type 真的能從 PATCH 進來，這是**修 bug**，wire 上多一個 422 情境。
  - 建議 3：**會改所有 route 的 422 形狀**，前端 `apiErrorSchema`（`types.ts:142-146`）
    的 union 容得下，但要逐一查消費點。
- **相關測試**：
  - **修改**：`tests/web/test_legacy_mapping_write_rejection.py`
    → `test_mapping_api_rejects_legacy_type_with_stable_code`（:28）、
      `test_proposal_decision_rejects_legacy_type_with_stable_code`（:53）
      —— 改名後 import 路徑要跟著改（測試目前是走 HTTP，只有 `create_app` import，
      所以**其實不用改**，除非改了 detail 字串）。
  - **修改**：`tests/contracts/test_v2_cutover_consumer_allowlist.py::test_direct_legacy_consumers_match_classified_allowlist`
    （建議 4）。
- **嚴重度**：P3（改名／文件）
- **風險**：低（1、4）／中（3）

---

## C-15. `DetailScanCreateRequest.target_type` 是裸 `str`，而 code / API-GUIDE / API_CONTRACT **三份清單互相打架**

- **位置**：`src/systograph/web/schemas.py:348-353`
- **現況**：
  ```python
  class DetailScanCreateRequest(WebSchema):
      project_id: str
      build_id: str | None = None
      target_type: str                                            # ← :351 裸 str
      target: str
      scan_depth: Literal["component", "code_path"] = "component" # ← :353 有 Literal
  ```
  同一個 class 裡，`scan_depth` 用 Literal 收窄，`target_type` 卻是裸 `str`
  —— 而 **core 早就有現成的型別可以用**：
  ```python
  # core/services/detail_scan_service.py:29-46
  DetailScanTargetType = Literal[
      "component_slot", "component_instance", "unmapped_component", "edge", "evidence",
  ]
  TARGET_TYPE_ALIASES: dict[str, DetailScanTargetType] = {
      "slot": "component_slot",            "component_slot": "component_slot",
      "component": "component_instance",   "component_instance": "component_instance",
      "unmapped": "unmapped_component",    "unmapped_component": "unmapped_component",
      "edge": "edge",                      "evidence": "evidence",
  }
  ```
  → 程式實際接受的輸入值恰好是 `TARGET_TYPE_ALIASES` 的 **8 個 key**；
  其他值在 `detail_scan_service.py:205-209` 被
  `raise DetailScanTargetError("target_type_not_supported")` 擋掉。

  **三份清單互相打架**（逐字比對）：

  | 值 | `TARGET_TYPE_ALIASES`（實作） | `docs/API-GUIDE.md:655-658` | `frontend/API_CONTRACT.md:329` |
  |---|---|---|---|
  | `component_slot` | ✅ | ✅ | ✅ |
  | `component_instance` | ✅ | ✅ | ❌ 未列 |
  | `unmapped_component` | ✅ | ✅ | ❌ 未列 |
  | `edge` | ✅ | ✅ | ✅ |
  | `evidence` | ✅ | ✅ | ❌ 未列 |
  | `slot`（別名） | ✅ | ✅（標為別名） | ❌ 未列 |
  | `component`（別名） | ✅ | ✅（標為別名） | ✅ |
  | `unmapped`（別名） | ✅ | ✅（標為別名） | ❌ 未列 |
  | `capability_candidate` | ❌ **不支援** | ✅ **有列** | ❌ |
  | `profile` | ❌ **不支援** | ✅ **有列** | ❌ |
  | `trace_step` | ❌ **不支援** | ❌ | ✅ **有列** |

  → `docs/API-GUIDE.md` 承諾了 2 個不存在的值（`capability_candidate`、`profile`），
  `frontend/API_CONTRACT.md` 承諾了 1 個不存在的值（`trace_step`）並漏掉 4 個存在的值。
  照任一份文件寫 client，都會拿到 422 `target_type_not_supported`。
- **為什麼是問題**：
  1. request 驗證應該在邊界（Pydantic）做，而不是靠 core service 丟例外再由
     `routes/detail_scan_routes.py:98-100` 翻譯成 422。
  2. `target_type` 是裸 `str` → OpenAPI 看不出任何合法值 → 文件只能手寫 → 手寫必然漂移
     （這裡漂移出 3 個假值）。這與 C-11（Field 無 description、無 `responses=`）同源。
  3. `profile` 這個假值特別危險：`CLAUDE.md` 明訂
     「`ProfileInferenceService` is the **sole owner** of the 52-node assessment and 15 profiles」，
     文件卻暗示可以對 profile 做 detail scan —— 這會誤導 client 以為 profile 是可 drill-down 的
     掃描目標。
- **建議改法**：
  1. `schemas.py:351` 改成
     `target_type: Literal["component_slot","component_instance","unmapped_component","edge","evidence","slot","component","unmapped"]`
     —— 或更好：在 `core/services/detail_scan_service.py` 旁邊多 export 一個
     `DetailScanTargetTypeInput = Literal[...8 個 key...]`，web DTO 直接 import 它，
     讓 alias 表與 Literal 由**同一處**定義（可用 `Literal[*TARGET_TYPE_ALIASES]` 或
     `assert set(get_args(DetailScanTargetTypeInput)) == set(TARGET_TYPE_ALIASES)` 綁定）。
  2. **同步修文件**：`docs/API-GUIDE.md:655-658` 刪掉 `capability_candidate` 與 `profile`；
     `frontend/API_CONTRACT.md:327-333` 刪掉 `trace_step`、補上遺漏的 4 個。
- **影響面**：**⚠️ 會改 422 的 `detail` 形狀**：
  原本非法 `target_type` 走 `{"detail": "target_type_not_supported"}`（字串），
  改成 Pydantic 邊界驗證後變成 FastAPI 的 `RequestValidationError` 陣列。
  前端依賴：`grep -rn "api/detail-scans" frontend/src/` **無命中**
  —— 前端尚未呼叫（`frontend/API_CONTRACT.md:321-323` 明說 detail scan 目前渲染的是
  `detail_scan_result_sample`），**實務破壞面為零**。
- **相關測試**：
  - **不需改**：`tests/web/test_detail_scan_routes.py::test_detail_scan_route_rejects_invalid_target_without_writing`
    （:50）—— 已查證它送的是**合法的 `target_type: "unmapped_component"` + 不存在的 `target`**
    （:60-61），斷言 `detail == "target_not_found"`（:67），與 target_type 驗證無關，不受影響。
  - **新增**：`tests/web/test_detail_scan_routes.py::test_rejects_unknown_target_type_at_boundary`
  - **新增**：`tests/contracts/test_detail_scan_target_types_match_docs.py`
    → `test_documented_target_types_are_all_supported`
      —— 從 `TARGET_TYPE_ALIASES` 取真值，比對兩份文件裡的清單，防止再度漂移。
- **嚴重度**：P2（文件承諾了 3 個不存在的值；前端未消費所以不是 P1）
- **風險**：低（前端未消費，改動可獨立驗證）

---

## C-16. `ScanProgressEvent` 是硬編 stub，且 `slot` 欄位語意與契約不符

- **位置**：`src/systograph/web/schemas.py:328-345`、`src/systograph/web/routes/scan_routes.py:354-359`
- **現況**：
  ```python
  @router.get("/api/scan/events", response_class=EventSourceResponse)
  async def scan_events(response: Response) -> AsyncIterator[ServerSentEvent]:
      """送出目前的掃描進度 SSE 事件；現階段回傳一筆 completed 狀態。"""
      response.headers.update(SSE_HEADERS)
      event = ScanProgressEvent()          # ← 全預設值，永遠 status="completed", percent=100
      yield ServerSentEvent(event=event.event, data=event)
  ```
  所有欄位的 default 都是「已完成」：`status="completed"`（:330）、`percent=100`（:333）、
  `stage="validate"`（:331）、`message="Scan completed."`（:332）。
  也就是這支 endpoint 永遠只吐一筆假的完成事件。
- **`slot` 欄位問題**：`schemas.py:339` `slot: str | None = None`。
  `CLAUDE.md` 明文「("Slot" refers only to the 13 slots of the legacy `rag-core-v1` template.)」，
  `docs/MODEL-CONTRACT.md` §11「rag-core-v1 template … Phase2 **凍結**」。
  一個進度事件帶 `slot` 欄位，等於在 active API 表面繼續傳播 legacy 概念。
  `frontend/API_CONTRACT.md:301-309` 的 highlight 順序第 5 順位就是 `slot`。
- **為什麼是問題**：README 的「currently implemented vs roadmap」原則
  （CLAUDE.md Workflow Conventions：「don't describe roadmap items as shipped in docs or UI copy」）
  —— 這支 endpoint 對外看起來是實作好的 SSE 進度，實際是 stub。
  加上 C-7 前端根本 parse 不過，等於雙重無效。
- **建議改法**：
  1. 短期：在 `scan_routes.py:356` 的 docstring 與 `docs/API-GUIDE.md` 明確標註
     「stub / not-yet-implemented」，或直接把 endpoint 拿掉直到真的有進度串流。
  2. `slot` 欄位加註解指向 `MODEL-CONTRACT.md` §11，並列入 Plan 15 移除清單。
  3. 若保留，`ScanProgressEvent` 的 default 不應該是 `completed`
     —— 一個「事件 model」不該有一整組讓它自動變成完成態的預設值。
- **影響面**：拿掉 endpoint 會破壞
  `frontend/src/services/viewerApi.ts:31-33` `createScanEventSource()` 與
  `frontend/src/hooks/useScanProgress.ts`。但因 C-7 這條路現在就是壞的，
  影響是「從壞掉變成明確不存在」。
- **相關測試**：
  - **修改／刪除**：`tests/web/test_map_routes.py::test_scan_events_returns_sse_completed_event`（:160）
  - **修改**：`frontend/src/hooks/useScanProgress.test.ts`
- **嚴重度**：P3
- **風險**：低

---

## 我確認沒問題的部分

以下每一條都逐檔查證過，**不需要動**：

1. **Pydantic v1/v2 混用：完全沒有。**
   `grep -rn "class Config" src/ --include="*.py"` → 唯一命中是
   `core/providers/config_parse_provider.py:41`，那是一個叫 `ConfigParseProvider` 的
   普通 class，不是 Pydantic v1 的 `class Config`。
   `grep -rn "@validator\|@root_validator" src/` → **零命中**。
   `grep -rn "\.dict()\|parse_obj\|parse_raw" src/` → **零命中**
   （`.json()` 的 3 個命中是 `httpx` response 與 `starlette` Request，不是 Pydantic）。
   `schemas.py` 全部用 v2 idiom：`ConfigDict`（:46）、`model_validator(mode="after")`（:129）、
   `model_dump` / `model_validate`（:267-268）。

2. **`Optional[X]` vs `X | None` 混用：沒有。**
   `grep -rn "Optional\[" src/ --include="*.py"` → **零命中**。全 repo 統一 `X | None`（PEP 604）。

3. **camelCase vs snake_case：全線 snake_case，前後端一致。**
   後端 `schemas.py` 27 個 class 全部 snake_case 欄位；
   `grep -rn "by_alias\|alias=\|populate_by_name" src/systograph/web/` → **零命中**（沒有 alias 機制）；
   前端 `frontend/src/types.ts` 也全部 snake_case（`:154 project_id`、`:211 scan_id`、
   `:214 build_result`、`:174 evidence_ids`）。這塊沒有轉換層需求，是對的。

4. **`InventoryApiErrorDetail.context` 不會洩漏路徑。**
   逐一查了所有 `InventorySelectionError(..., context=...)` 的 raise 點：
   `inventory_preflight_limit_service.py:48`（`{"limit": int}`）、
   `:121-124`（`{"limit", "observed_at_least"}`）、
   `:135-139`（`{"limit_kind", "limit", "observed_at_least"}`）、
   `inventory_selection_decision_service.py:100`（同樣是 limit context）。
   **全部只有 bounded 整數與 enum value，沒有任何路徑或檔名。**
   型別 `dict[str, str | int] | None`（`core/models/errors.py:86`）也限制了複雜結構。

5. **`detail=str(exc)` 的 `PathSafetyError` 不會洩漏路徑。**
   `mapping_routes.py:54,75`、`detail_scan_routes.py:102`、`scan_routes.py:265,337`、
   `mapping_proposal_routes.py:94,119`、`map_build_routes.py:64` 都有 `detail=str(exc)`。
   查了 `core/services/path_safety_service.py` 的所有 `PathSafetyError` 訊息
   （:48「Path must not be empty」、:135「Windows absolute or anchored path rejected」、
   :139「POSIX absolute path rejected」、:145「Path must include at least one segment」、
   :147「Path must stay inside project root」、:149「Path segment is not cross-platform safe」）
   —— **沒有一個把違規路徑嵌進訊息**。這是刻意設計，正確。

6. **preflight response 有正確剝除敏感內容。**
   `InventoryRequestedTargetView`（`schemas.py:272-278`）刻意**不**帶 core
   `InventoryRequestedTargetResult` 的 `file_candidate` 與 `directory_manifest`
   （`core/models/inventory_selection.py:189-190`），
   後者含 `entries: tuple[InventoryCandidate, ...]`（`:97`，全部子檔案清單）。
   這正好符合 `frontend/API_CONTRACT.md:155-157`
   「internal descendant `entries[]`, file contents, snippets, absolute paths, and secret values
   must never appear in this payload」。
   `InventoryBlockedSummaryView` 也只留 `path` / `reason_code` / `outcome` / `can_expand`，
   丟掉 core 的 `exclusion_source`。**這部分的 secret/path boundary 是對的。**

7. **`WebSchema` 的 `extra="forbid"` 全線一致。**
   27 個 class 全部繼承（`ApplyConfirmationsResponse` 透過 `MapBuildScopedResponse` 間接繼承），
   core 的 4 個 base（`MapBuildModel`、`AnalysisHistoryModel`、`InventorySelectionModel`、
   `ErrorModel`）也都是 `extra="forbid"`。
   `schemas.py:44` 的 docstring「Base schema that rejects silent API contract drift」名副其實。

8. **沒有任何 model 定義了未被使用的 class**（27/27 都有消費者，見 §0 表格）。
   死 code 只出現在 `__all__` 的 re-export 層（C-2）。

9. **`schemas.py` 的兩個 `@classmethod` 工廠是正確的分層做法。**
   `Phase2MapBuildResult.from_core`（:106-123）、`MapBuildScopedResponse.from_core`（:146-163）、
   `ApplyConfirmationsResponse.from_domain`（:170-184）、
   `MapBuildHistorySummary.from_manifest`（:196-212）
   —— core → web DTO 的轉換集中在 DTO 自己身上，route 只呼叫，
   符合 CLAUDE.md「web 只做 adapter」。`MapBuildScopedResponse.from_core:150-153`
   還有 fail-closed 檢查（lineage/viewer 缺一就 raise），是好的。

10. **`inventory_error_response.py` 的三個工廠函式命名與回傳型別一致**
    （都是 `-> dict[str, object]` + `.model_dump(mode="json")`），
    內部沒有不一致；問題在於它與**其他 route** 不一致（C-12），不是它自己不一致。

11. **`legacy_mapping_guards.py` 的 fail-closed 行為正確。**
    `:30-33` 對 `json.JSONDecodeError` 直接 `return`（交給 FastAPI 正常報 422），
    `:17-18` 對非 dict payload 回 `False`，
    `:21-25` 同時檢查頂層 `mapping_type` 與巢狀 `edited_mapping.mapping_type`
    —— 兩個 route 的兩種 payload 形狀都覆蓋到了。邏輯本身沒有漏洞。
