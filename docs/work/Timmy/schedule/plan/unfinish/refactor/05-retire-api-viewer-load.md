# 退役 `POST /api/viewer/load` 實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue 待開。使用者決策：直接移除
HTTP adapter，而非執行 issue #140 的加固方案——見下方「與 issue #140 的關係」，
該決策需在 issue 上明示）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** 待開（開立後回填編號）

**Goal:** 移除 `POST /api/viewer/load` HTTP 端點。載入既有 `ai_system_map.json`
的能力保留在 CLI（`systograph validate-map`），不再經由 HTTP 暴露。

**Architecture:** 只刪 **HTTP adapter**，不動 viewer 投影能力。前端零引用，
移除對產品無影響。**核心安全動機**：現行實作把 server-local 路徑直接餵進
`Path()` 讀檔且回吐 `OSError` 細節，是未修補的 path oracle（issue #140）。

**Tech Stack:** FastAPI（route/schema 移除）、pytest web tests、bash trace
scripts、契約文件。

---

## 與 issue #140 的關係（**執行前必須確認**）

`plan/unfinish/final-phase-hardening/140-fix-viewer-map-loading-path-oracle.md`
的 Goal 是「**限制** `POST /api/viewer/load` 只能讀取受控 map」——也就是官方
方向是**加固**，不是刪除。issue **#140
`[Security][High][H-2] fix: restrict viewer map loading and remove path oracle`
仍為 OPEN**。

本計畫一旦執行，**Plan 140 整份失效**（端點不存在就沒有「限制它」可言）。
處理方式二擇一，須先決定：

- [ ] **Step 0: 決定並記錄 #140 的處置**——關閉 issue 並註明「端點已退役，
  風險以移除方式消解」，或把 #140 改寫為只涵蓋殘留範圍；同時把
  `plan/unfinish/final-phase-hardening/140-*.md` 標記為 superseded 並註明
  由本計畫取代（**不得直接刪除該 plan 檔**）

> 註：刪除確實根除了風險，成本也低於加固。但這是「捨棄一個 operator 能力」
> 而非「修好它」，屬產品決策，故列為 Step 0 而非隱含前提。

---

## Source（判準基線，2026-08-06 對程式碼查核）

- `src/systograph/web/routes/viewer_routes.py` — **全檔只有這一個 route**
  （`:21`），刪端點等於刪整檔。
- 現行實作無任何路徑驗證：`service.load_map(Path(payload.map_json_path))`
  直接讀檔；`viewer_session_service.py:93` 把 `OSError` 字串原樣回傳
  （`map_read_failed: {exc}`），含本機絕對路徑與 errno。
- 前端：`grep -rn "viewer/load" frontend/src` **零結果**；
  `frontend/API_CONTRACT.md` 亦**未提及**（無需修改）。

## 範圍

**移除：** `POST /api/viewer/load` 端點、`ViewerLoadMapRequest` schema、
`viewer_routes.py` 整檔。

**保留（不得誤刪）：**

| 東西 | 為什麼必須留 |
|---|---|
| `ViewerSessionService.load_map` | **CLI `systograph validate-map` 仍在用**（`cli/viewer_command.py:31`）；另有 `tests/unit/core/test_viewer_session_service.py` 7 處直接呼叫，以及 `tests/cli/test_viewer_command.py` 走 CLI 的覆蓋 |
| `ViewerSessionService` 本身 | 它是 build-scoped 投影的唯一擁有者——`MapBuildService`、`BuildArtifactPublisher`、`BuildManifestService`（`:76`）各自持有一份；`app.py:236-243` 另把它注入兩個 session store 當 `projection_service`（只用來產生空 payload seed，`session_store.py:85,150`）。**刪掉會讓 build → viewer 投影整條壞掉** |
| `dependencies.viewer_session_service` | 見下方 Task 3 Step 2 的判斷條件 |
| `ViewerLoadResult` / graph projection | 正式 `map-builds` 路徑以它為主體（`schemas.py:144` `MapBuildScopedResponse.viewer_load_result: ViewerLoadResult`） |
| `ViewerPayload`（**本輪留、非永久**） | 本計畫移除後 Web 層仍有 `GET /api/map`／`GET /map` 以它為 response model（`map_routes.py:37,75`，屬 Plan 02 範圍），再加 session 槽與 re-export；**正式 build-scoped 回應不使用它**（2026-08-06 更正：原記載有誤）。與 Plan 02 都完成後由 **Plan 08** 一併移除 |
| `session_store.save_viewer_payload` | 兩個 store 實作內部仍呼叫（`session_store.py:118,191`）|

---

## Task 1: 移除 route 與 schema

**Files:**
- Delete: `src/systograph/web/routes/viewer_routes.py`
- Modify: `src/systograph/web/app.py`
- Modify: `src/systograph/web/schemas.py`

- [ ] **Step 1: 刪除 `viewer_routes.py` 整檔**
- [ ] **Step 2: `app.py:76` 移除 `viewer_routes` import、`:258` 移除
  `app.include_router(viewer_routes.router)`**
- [ ] **Step 3: `app.py` 的 `ViewerSessionService` import(`:59-60`)、
  建構參數(`:134`)、`app.state.viewer_session_service`(`:236-238`)
  一律保留**——`PersistentSessionStore` 由 `:242` 注入它產生空 payload seed
  （`session_store.py:150`）
- [ ] **Step 4: `schemas.py:69` 刪除 `ViewerLoadMapRequest`、`:430` 移除
  `__all__` 條目**（已確認無其他使用者）

## Task 2: 更新結構化檔頭註解（**易漏**）

本 repo 的 service/model 檔案帶「責任 / 呼叫鏈」檔頭註解，`CLAUDE.md` 要求
改動依賴前先讀它們。端點消失而註解未改，呼叫鏈會指向不存在的東西。

**Files:**
- Modify: `src/systograph/core/models/viewer.py`
- Modify: `src/systograph/core/services/viewer_session_service.py`

- [ ] **Step 1: `models/viewer.py:10`「Web：POST /api/viewer/load →
  ViewerPayload」改寫**
- [ ] **Step 2: `models/viewer.py:276`「被誰用：viewer_routes.POST
  /api/viewer/load」改寫**
- [ ] **Step 3: `viewer_session_service.py:6`「Web POST /api/viewer/load、
  CLI viewer → load_map」改為只剩 CLI validate-map**
- [ ] **Step 4: `viewer_session_service.py:55`「被誰用：viewer_routes、
  BuildArtifactPublisher、BuildManifestService、MapBuild 相關」移除
  `viewer_routes`**（同一檔第三處殘留，最易漏）
- [ ] **Step 5: `viewer_session_service.py:80`「被誰呼叫：viewer_routes.POST
  /api/viewer/load」改為 CLI validate-map command
  （`cli/viewer_command.py`）**

## Task 3: 測試

**Files:**
- Delete: `tests/web/test_viewer_routes.py`（66 行 / 3 個測試，全數針對本端點）
- Modify: 其他 web 測試（若有殘留引用）

- [ ] **Step 1: 刪除 `tests/web/test_viewer_routes.py`**
- [ ] **Step 2: 全樹 grep `api/viewer/load` 確認無殘留測試引用**；
  若 `dependencies.viewer_session_service` 於此後無任何 route 使用者，
  一併移除該 helper 與其 import（**但不得移除 `app.state` 上的服務本身**）
- [ ] **Step 3: 新增 regression：`POST /api/viewer/load` 回 404**
- [ ] **Step 4: `tests/unit/core/test_viewer_session_service.py` 完全不動**
  ——它測的是 service，不是 HTTP adapter
- [ ] **Step 5: `uv run pytest` 全綠**

## Task 4: Trace scripts

**Files:**
- Delete: `scripts/trace_viewer_load.sh`
- Modify: `scripts/trace_all.sh`

- [ ] **Step 1: 刪除 `scripts/trace_viewer_load.sh`**
- [ ] **Step 2: `trace_all.sh:59` 移除
  `"POST /api/viewer/load|trace_viewer_load.sh"` 該列**
- [ ] **Step 3: `scripts/trace_all.sh` 端到端跑過確認全綠**

> 注意順序衝突：`trace_viewer_load.sh` 同時也是 Plan 03 Task 1 Step 2 的
> 改寫對象（它用 `POST /api/map/build` 當前置）。若 Plan 03 先執行，該檔已被
> 改寫；本計畫直接刪除即可，兩者不衝突，但**別重複工**。

## Task 5: 契約文件

**Files:**
- Modify: `docs/API-GUIDE.md`
- 不需改 `frontend/API_CONTRACT.md`（已確認未提及）

- [ ] **Step 1: `:58` Endpoint 總覽移除
  `| POST | /api/viewer/load | demo | current | 2 |` 該列**
- [ ] **Step 2: `:615-633` `### POST /api/viewer/load` 整節刪除**
- [ ] **Step 3: 全文 grep `viewer/load` 確認無殘留敘述**

---

## 驗收標準

1. `POST /api/viewer/load` 回 404，且有 regression test 鎖住。
2. CLI `systograph validate-map` 仍可載入既有 `ai_system_map.json`
   （能力未流失）。
3. 正式 viewer 路徑（`map-builds/latest`、`map-builds/{build_id}`）行為不變
   ——`MapBuildQueryService` → `BuildManifestService` 的投影仍正常。
4. `uv run pytest`、`ruff`、`mypy` 全綠；`scripts/trace_all.sh` 可完整執行。
5. `docs/API-GUIDE.md` 無殘留敘述；`models/viewer.py` 與
   `viewer_session_service.py` 的呼叫鏈註解已更新。
6. issue #140 已依 Step 0 的決定關閉或改寫，且 `140-*.md` 已標記 superseded。

## 風險

- **誤刪 `ViewerSessionService`**：最高風險。它是 build-scoped 投影的唯一
  擁有者（`MapBuildService`／`BuildArtifactPublisher`／`BuildManifestService`
  各持一份），另被兩個 session store 當 `projection_service` 注入，刪掉會讓
  build → viewer 投影整條壞掉。本計畫只刪 HTTP adapter。
- **捨棄 operator 能力**：HTTP 不再能載入任意既有 map JSON；替代方案是 CLI。
  若日後仍需 HTTP 版本，應以 build-scoped artifact API + 白名單重新設計，
  不要恢復本端點。
- **與 Plan 03 的檔案重疊**：`trace_viewer_load.sh` 兩份計畫都會碰，見
  Task 4 註記。
