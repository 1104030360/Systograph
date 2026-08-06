# 移除 `_latest_viewer_payload` 旁路槽與 `ViewerPayload` 型別實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue 待開。**Gate：Plan 02 與
Plan 05 都完成後才可執行**——在那之前 `ViewerPayload` 仍有活的消費者）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** 待開（開立後回填編號）

**Goal:** 移除 demo 讀圖端點退役後成為死碼的 session 旁路槽
（`_latest_viewer_payload`、`save_viewer_payload`、`latest_viewer_payload`、
`save_build_result` 內的 re-wrap 行）與 `ViewerPayload` pydantic model。

**Architecture:** 純死碼清除，無行為變更、無契約變更。`ViewerPayload` 是
demo 端點的 response 包裝層；Plan 02（`GET /api/map`、`GET /map`）與 Plan 05
（`POST /api/viewer/load`）移除後，它只剩 session 槽與 re-export 兩種「自我
指涉」的使用者。**正式 build-scoped 回應不經過它**——
`schemas.py:144` `MapBuildScopedResponse.viewer_load_result: ViewerLoadResult`。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、Ruff、mypy。

---

## 為什麼需要獨立計畫（而不是塞進 02 或 05）

本工作**同時 gate 在兩份計畫上**，塞進任一份都會產生「另一份還沒做完就不能
執行這個 Task」的跨計畫相依。原本僅以散文註記記在 Plan 02 的「不動」段落，
但散文註記沒有 checkbox、不進執行佇列，容易在兩份計畫都完成後被遺忘——
故獨立成可勾選的計畫。

## Source（判準基線，2026-08-06 對程式碼查核）

`ViewerPayload` 在 `src/systograph/` 的**全部**使用處，逐一分類：

| 位置 | 性質 | Plan 02/05 後 |
|---|---|---|
| `core/models/viewer.py:280` | 型別定義 | 本計畫移除 |
| `core/models/viewer.py:9,10,261` | 檔頭呼叫鏈註解 | 本計畫更新 |
| `core/models/graph_view.py:13,24` | re-export | 本計畫移除 |
| `web/schemas.py:40,431` | import + `__all__` re-export | 本計畫移除 |
| `web/routes/map_routes.py:10,37,40,75,78` | import + `GET /api/map`、`GET /map` 的 response_model 與回傳型別 | **Plan 02 已移除** |
| `web/routes/viewer_routes.py:10,21,29,32` | `POST /api/viewer/load` | **Plan 05 已移除**（整檔刪） |
| `web/session_store.py`（12 處） | 旁路槽本體 | **本計畫移除** |

對照組：`ViewerLoadResult` 分佈於 8 個檔案，含
`build_artifact_publisher.py`、`graph_projection_service.py`、`map_build.py`、
`apply_confirmations.py`——它是正式產出主體，**必留**。

## 範圍

**移除：** `ViewerPayload` 型別與其 re-export；`SessionStore` Protocol 與兩個
實作的 `save_viewer_payload` / `latest_viewer_payload`；
`_latest_viewer_payload` 欄位；`save_build_result` 內的 re-wrap 行。

**不得更動：**

| 東西 | 為什麼 |
|---|---|
| `ViewerLoadResult` / `graph_view_model` | 正式 build-scoped 回應主體 |
| `MapBuildResult` / `save_build_result` 本身 | 只刪其中的 re-wrap 行，方法本體是正式路徑 |
| `save_committed_build_projection` | 正式 scan / apply / detail scan 都在用 |
| `ViewerSessionService` | `PersistentSessionStore` 的 `projection_service` |
| 前端 `frontend/src/types.ts` 的 `ViewerPayload` TS 型別 | **同名不同物**——前端內部正規化型別，與 backend 無關，零改動 |

---

## Task 0: 前置確認

- [ ] **Step 1: 確認 Plan 02 已完成**（`GET /api/map`、`GET /map` 回 404）
- [ ] **Step 2: 確認 Plan 05 已完成**（`POST /api/viewer/load` 回 404，
  `viewer_routes.py` 已刪）
- [ ] **Step 3: `grep -rn "ViewerPayload" src/systograph --include="*.py"`
  確認殘餘只剩本計畫列出的位置**（定義、re-export、session 槽、註解）；
  若出現新的活消費者，**停止並重新評估**

## Task 1: 移除 session 旁路槽

**Files:**
- Modify: `src/systograph/web/session_store.py`

- [ ] **Step 1: `SessionStore` Protocol 移除 `save_viewer_payload`(`:46`)
  與 `latest_viewer_payload`(`:48`)**
- [ ] **Step 2: `InMemorySessionStore` 移除 `_latest_viewer_payload`
  欄位(`:84`)、兩個方法(`:122,125`)，以及 `save_build_result` 內的 re-wrap
  行(`:117-120`)**
- [ ] **Step 3: `PersistentSessionStore` 同上**——欄位(`:149`)、
  兩個方法(`:195,198`)、re-wrap 行(`:190-193`)
- [ ] **Step 4: 移除該檔對 `ViewerPayload` 的 import(`:14`)**

> 注意 `PersistentSessionStore.latest_viewer_payload`(`:198-202`)有一段
> 「先從 `latest_build_result` 導出、拿不到才用記憶體槽」的 fallback 邏輯，
> 整個方法一起移除即可，不需要保留該 fallback。

## Task 2: 移除 `ViewerPayload` 型別與 re-export

**Files:**
- Modify: `src/systograph/core/models/viewer.py`
- Modify: `src/systograph/core/models/graph_view.py`
- Modify: `src/systograph/web/schemas.py`

- [ ] **Step 1: 刪除 `core/models/viewer.py:274-281` 的 `ViewerPayload`
  class 與其上方註解區塊**（註解區塊無 `ViewerPayload` 字面，驗收的 grep
  抓不到，留著會變孤兒）
- [ ] **Step 2: 刪除 `core/models/graph_view.py:13` import 與 `:24` `__all__`
  條目**
- [ ] **Step 3: `web/schemas.py:40` import 改為只留 `ViewerLoadResult`；
  刪除 `:431` `__all__` 條目**
- [ ] **Step 4: `uv run mypy src tests` 確認無殘留參照**

## Task 3: 更新檔頭呼叫鏈註解

`core/models/viewer.py` 檔頭記載的鏈路在本計畫後不再成立。

- [ ] **Step 1: `:9`「→ 包成 ViewerLoadResult → ViewerPayload」改為止於
  `ViewerLoadResult`**
- [ ] **Step 2: `:10`「Web：POST /api/viewer/load → ViewerPayload」移除**
  （Plan 05 Task 2 可能已處理，確認後補齊）
- [ ] **Step 3: `:261`「再包進 ViewerPayload 給 API」改寫為 build-scoped
  回應路徑**

## Task 4: 測試

- [ ] **Step 1: 移除或改寫引用 `save_viewer_payload` /
  `latest_viewer_payload` / `ViewerPayload` 的測試**
  （執行時 `grep -rn` 取得清單；Plan 02/05 完成後殘餘應該很少）
- [ ] **Step 2: `tests/web/test_trace_routes.py` 使用 `InMemorySessionStore`，
  確認移除方法後仍可建構**
- [ ] **Step 3: `uv run pytest`、`ruff check`、`ruff format --check`、
  `mypy src tests` 全綠**
- [ ] **Step 4: `pnpm test`**——前端不應受影響（同名 TS 型別無關），
  跑一次確認

## Task 5: 契約與 census

- [ ] **Step 1: 全文 grep `ViewerPayload` 於 `docs/`——
  若 `docs/MODEL-CONTRACT.md` 或 `docs/API-GUIDE.md` 有描述該包裝層，更新之**
  （現行敘述多以 `viewer_load_result` 為主，預期改動很少）
- [ ] **Step 2: 確認 `tests/contracts/` 無因型別消失而需同步的記錄**

---

## 驗收標準

1. `grep -rn "ViewerPayload" src/systograph --include="*.py"` 零命中。
2. `SessionStore` Protocol 只剩 project 與 build 相關方法；兩個實作無旁路槽。
3. 正式讀圖路徑行為不變：`map-builds/latest`、`map-builds/{build_id}`、
   `GET /api/map/report` 全部正常。
4. `uv run pytest`、`ruff`、`mypy`、`pnpm test` 全綠。
5. `core/models/viewer.py` 檔頭呼叫鏈與現況一致。

## 風險

- **提前執行**：Plan 02 或 05 未完成就動工，會刪掉仍有端點在用的型別，
  直接讓 app 起不來。Task 0 的三個前置確認是硬性的。
- **同名混淆**：前端 `types.ts` 也有 `ViewerPayload`，**不要跟著刪**——
  它是前端內部正規化型別，Sample 模式與 API 模式都依賴。
- **`save_build_result` 誤刪**：只刪其中的 re-wrap 行，方法本體是正式
  scan / apply / detail scan 的投影發佈路徑。
