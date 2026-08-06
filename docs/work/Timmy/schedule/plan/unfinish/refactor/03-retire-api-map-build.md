# 退役 `POST /api/map/build` 實作計畫

Status: **planned**（2026-08-06 起草；GitHub issue 待開。從
`02-retire-process-wide-api-map.md` 拆出獨立執行——本端點**沒有任何前端依賴**，
不需要等前端工作，可立即動工）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** 待開（開立後回填編號）

**Goal:** 移除 all-in-one demo 建圖端點 `POST /api/map/build`，把 HTTP 建圖入口
收斂為正式 project session 流程（`import` → `scans`）。

**Architecture:** 這是 breaking API change，但 blast radius 遠小於 `GET /api/map`：
前端零引用，且能力不會消失——CLI `systograph map`（`cli/map_command.py:63`
同樣呼叫 `MapBuildService().build()`）提供完全等價的「一次掃一個路徑就出圖」。
本計畫只砍寫入端點，**不動** `GET /api/map` / `GET /map`（那兩支卡在前端
fallback，見 Plan 02）。

**Tech Stack:** FastAPI（handler 移除）、pytest web tests、bash trace scripts、
契約文件。

---

## Source（判準基線，2026-08-06 對程式碼查核）

- `src/systograph/web/routes/map_routes.py:22-35` — `build_map` handler。
- `src/systograph/web/schemas.py:49`（`MapBuildApiRequest`）與 `:411` 的
  `__all__` 條目——**唯一使用者就是這個 handler**，可一併退役。
- 前端：`grep -rn "map/build" frontend/src` **零結果**；
  `frontend/API_CONTRACT.md:75` 明載「It does not call `/api/map/build`
  for this interactive flow」。
- 等價能力：`src/systograph/cli/map_command.py:63`。
- 既有 helper：`scripts/lib/api_trace_common.sh:186`
  `systograph_import_project`、`:201` `systograph_run_scan`——script 遷移
  直接改用它們，不需自行拼 curl。

## 範圍

**移除：** `POST /api/map/build`、`MapBuildApiRequest`。

**不動：** `GET /api/map`、`GET /map`（Plan 02 範圍，需等前端拔 fallback）、
`GET /api/map/report`（issue #219，待接線非待退役）。

**注意副作用：** 本端點是餵養 process-wide latest 的來源之一。移除後
`GET /api/map` 仍可運作，寫入者剩下走 `save_committed_build_projection` 的
三支 project session 端點（`POST /api/scans`、`POST /api/detail-scans`、
`POST /api/map-builds/{id}/apply`）與 `POST /api/viewer/load`
（`viewer_routes.py:35` 的 `save_viewer_payload`）——即必須先跑過一次
`import` → `scans`，或從磁碟 load 既有地圖，才有內容。對前端無影響
（它本來就是掃完才 fallback）。

---

## Task 1: 遷移 trace scripts（**先做**，確保退役後仍可驗證）

4 支引用，只有 1 支該刪，另外 2 支是把它當**前置佈置**而非受測對象：

| script | 用途 | 處理 |
|---|---|---|
| `trace_map_build.sh` | 專測本端點 | **刪除** |
| `trace_map_report.sh:48-55` | 先建圖讓 markdown report 存在 | 改用 import → scans |
| `trace_viewer_load.sh:55-64` | 先建圖取得 `map_json_path` | 改用 import → scans |
| `trace_all.sh:55` | 清單引用 | 移除該列 |

- [ ] **Step 1: `trace_map_report.sh` 的 setup 改寫**——把
  `setup_post "/api/map/build" ...` 換成
  `systograph_import_project` + `systograph_run_scan`
- [ ] **Step 2: `trace_viewer_load.sh` 的 setup 改寫**——同上；
  `map_json_path` 改從 scan 回應取
  （`echo "$scan" | jq -r '.build_result.map_json_path'`），
  保留原有的 null 檢查與 `systograph_die`
- [ ] **Step 3: 刪除 `scripts/trace_map_build.sh`**
- [ ] **Step 4: 從 `trace_all.sh:55` 移除
  `"POST /api/map/build|trace_map_build.sh"` 該列**
- [ ] **Step 5: `scripts/trace_all.sh` 端到端跑過一次確認全綠**

## Task 2: 遷移測試

2 檔 6 處引用：

| 檔案 | 處數 | 用途 |
|---|---:|---|
| `tests/web/test_map_routes.py` | 5 | 測端點本身 ＋ 當作 `GET /api/map` 等測試的前置 build |
| `tests/web/test_local_api_hardening.py` | 1 | 拿它當 CORS／hardening 的 request 素材 |

- [ ] **Step 1: `test_map_routes.py` 中純粹測 `POST /api/map/build`
  行為的案例刪除**
- [ ] **Step 2: 其餘把它當前置 build 的案例改走 `import` → `scans`**；
  若重複出現，抽 helper 放 `tests/helpers/`
- [ ] **Step 3: `test_local_api_hardening.py` 改用其他仍存在的寫入端點
  （如 `POST /api/scans`）當素材，維持原本的 hardening 斷言不變**
- [ ] **Step 4: 新增 regression：`POST /api/map/build` 回 404**

## Task 3: 移除 handler 與 schema

- [ ] **Step 1: 刪除 `map_routes.py:22-35` 的 `build_map`**
- [ ] **Step 2: 刪除 `schemas.py:49` 的 `MapBuildApiRequest` 與 `:411`
  的 `__all__` 條目**（已確認無其他使用者）
- [ ] **Step 3: 清理 `map_routes.py` 隨之無用的 import**
- [ ] **Step 4: `uv run ruff check src tests`、
  `uv run ruff format --check src tests`、`uv run mypy src tests` 全綠**

## Task 4: 契約文件

`docs/API-GUIDE.md` 需處理 10 處：

- [ ] **Step 1: `:55` Endpoint 總覽移除該列**
- [ ] **Step 2: `:325-414` `### POST /api/map/build` 整節刪除**
  （該節從 `### POST /api/map/build` 一路延伸到 `## 2. 地圖讀取（Viewer）`
  之前的 `---`，不只到 request 範例為止）
- [ ] **Step 3: `:93` 快速開始的 deprecated 提示改寫**
  （只剩 `GET /api/map` 尚未退役）；同時修 `:96` 的範例腳本清單——
  它點名 `scripts/trace_map_build.sh`，Task 1 Step 3 已把該檔刪除
- [ ] **Step 4: `:613` `GET /map` 節、`:661` detail scan 前置敘述
  （「只用 `map/build` 不足以滿足 `map_not_loaded` 檢查」）、`:734` query
  trace 節、`:1067`／`:1070` 錯誤說明中提及本端點的敘述逐一改寫**
- [ ] **Step 5: `:30-35`「兩種流程」表的 Viewer demo 列改寫**——
  `map/build` 已不存在，demo 流程僅剩 `GET /api/map` 讀取；該列在
  Plan 02 完成時整列移除。`:104` §1 開頭同義的「Viewer demo 捷徑」
  敘述一併處理
- [ ] **Step 6: `frontend/API_CONTRACT.md` 三處**——`:37`（與 `/api/map`
  一同退役的敘述）、`:75`（「does not call」敘述已無意義）、`:290`
  （`legacy_output_not_selectable` 錯誤表移除該端點）

---

## 驗收標準

1. `POST /api/map/build` 回 404，且有 regression test 鎖住。
2. `GET /api/map` / `GET /map` 行為不變（跑過一次正式 scan 後仍可讀取）。
3. `uv run pytest`、`ruff`、`mypy` 全綠；`scripts/trace_all.sh` 可完整執行。
4. `docs/API-GUIDE.md`、`frontend/API_CONTRACT.md` 無指向已刪端點的殘留敘述。
5. CLI `systograph map` 仍可完成等價的一次性建圖（能力未流失）。

## 風險

- **Breaking change**：任何以此端點當快速入口的本機腳本或外部整合會失效；
  退役需在 issue 與 API-GUIDE 明示，並指向 CLI `systograph map` 作為替代。
- **測試遷移成本**：改走 `import` → `scans` 會拉長 web 測試時間；建議抽共用
  helper 而非逐案複製。
- **順序**：Task 1 先於 Task 3，確保 trace scripts 在端點消失前就已可用
  新流程驗證。
