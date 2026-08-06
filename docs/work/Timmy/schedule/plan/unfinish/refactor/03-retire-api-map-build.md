# 退役 `POST /api/map/build` 實作計畫

Status: **done**（2026-08-06 起草；GitHub issue #277。從
`02-retire-process-wide-api-map.md` 拆出獨立執行——本端點**沒有任何前端依賴**，
不需要等前端工作，可立即動工；2026-08-07 實作完成 @ commit `f15d4ea`）

> **2026-08-07 完成紀錄**：Task 1–4 全數執行。`POST /api/map/build` handler、
> `MapBuildApiRequest`、`scripts/trace_map_build.sh` 與 `trace_all.sh` 該列皆已移除；
> `tests/web/test_retired_endpoints.py` 以 404 +「路由表無此 path」雙重 regression
> 鎖住（並補上 `/api/scans` positive control，避免路由表為空時 vacuously pass）。
> `GET /api/map`、`GET /map`、`GET /api/map/report` 全數保留（Plan 02 範圍）。
> 契約文件掃乾淨的範圍**超出原列表兩檔**：`docs/design/epic1-phase2.md`（3 處）
> 與 `ref-opensource/arch-graph/`（3 處）原本把本端點寫成 current entry point，
> 已一併改為 `POST /api/scans`；`docs/work/` 下的計畫歷史文件依約定不清。
> API-GUIDE 整節刪除時，`ArtifactRef` 型別定義（§2 的 `artifact_refs` 仍引用它）
> 改置入 §2，避免隨 demo 節一起消失。

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填）

**Goal:** 移除 all-in-one demo 建圖端點 `POST /api/map/build`，把 HTTP 建圖入口
收斂為正式 project session 流程（`import` → `scans`）。

**Architecture:** 這是 breaking API change，但 blast radius 遠小於 `GET /api/map`：
前端零引用，且能力不會消失——CLI `systograph map`（`cli/map_command.py:63`
同樣呼叫 `MapBuildService().build()`）提供完全等價的「一次掃一個路徑就出圖」。
本計畫只砍寫入端點，**不動** `GET /api/map` / `GET /map`（那兩支仍有前端
fallback 依賴，屬 Plan 02 範圍）。

**Tech Stack:** FastAPI（handler 移除）、pytest web tests、bash trace scripts、
契約文件。

---

## Source（判準基線，2026-08-07 對程式碼查核）

- `src/systograph/web/routes/map_routes.py:22-34` — `build_map` handler。
- `src/systograph/web/schemas.py:49`（`MapBuildApiRequest`）與 `:411` 的
  `__all__` 條目——**唯一使用者就是這個 handler**，可一併退役。
- 前端：`grep -rn "map/build" frontend/src` **零結果**；
  `frontend/API_CONTRACT.md:75` 明載「It does not call `/api/map/build`
  for this interactive flow」。
- 等價能力：`src/systograph/cli/map_command.py:63`。
- 既有 helper：`scripts/lib/api_trace_common.sh:187`
  `systograph_import_project`、`:202` `systograph_run_scan`——script 遷移
  直接改用它們，不需自行拼 curl。

## 範圍

**移除：** `POST /api/map/build`、`MapBuildApiRequest`。

**不動：** `GET /api/map`、`GET /map`（Plan 02 範圍；前端 fallback 仍在，
但該計畫的前端先行 gate 已於 2026-08-07 解除）、`GET /api/map/report`
（issue #219，待接線非待退役）。

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
| ~~`trace_viewer_load.sh:55-65`~~ | ~~先建圖取得 `map_json_path`~~ | **已由 Plan 05 刪除，本列作廢（2026-08-07）** |
| `trace_all.sh:55` | 清單引用 | 移除該列 |

- [x] **Step 1: `trace_map_report.sh` 的 setup 改寫**——把
  `setup_post "/api/map/build" ...` 換成
  `systograph_import_project` + `systograph_run_scan`
- [x] ~~**Step 2: `trace_viewer_load.sh` 的 setup 改寫**~~——
  **已由 Plan 05 刪除該檔，本步作廢（2026-08-07）**；原註記如下：同上；
  `map_json_path` 改從 scan 回應取
  （`echo "$scan" | jq -r '.build_result.map_json_path'`），
  保留原有的 null 檢查與 `systograph_die`。
  **2026-08-07 順序註記：** 本輪執行順序為 Plan 05 先於本計畫；Plan 05
  Task 4 會把該檔整檔刪除，屆時本步與上表第 3 列直接跳過（Plan 05
  L140-142 有對應註記，勿重工）
- [x] **Step 3: 刪除 `scripts/trace_map_build.sh`**
- [x] **Step 4: 從 `trace_all.sh:55` 移除
  `"POST /api/map/build|trace_map_build.sh"` 該列**
- [x] **Step 5: `scripts/trace_all.sh` 端到端跑過一次確認全綠**——
  19 支跑完 11 PASS / 8 FAIL。改動過的 `trace_map_report.sh` 單跑 PASS
  （HTTP 200 + `text/markdown`）。8 支 FAIL 全在 mapping／detail-scan 群，
  失敗點是 helper 的 `components_by_slot | keys[0]` 打到 null
  （`jq: error ... null (null) has no keys`），**既有缺陷、與本計畫無關**：
  這 8 支本來就走 import → scans，從未引用 `POST /api/map/build`

## Task 2: 遷移測試

2 檔 6 處引用：

| 檔案 | 處數 | 用途 |
|---|---:|---|
| `tests/web/test_map_routes.py` | 5 | 2 處測端點本身（其一兼驗 `/api/map`）；3 處為 `/api/map/report` 前置 build |
| `tests/web/test_local_api_hardening.py` | 1 | 拿它當 CORS／hardening 的 request 素材 |

- [x] **Step 1: `test_map_routes.py` 中純粹測 `POST /api/map/build`
  行為的案例刪除**。**注意（2026-08-07 查核）：** `:11-33` 的第一個測試
  兼驗 `GET /api/map` / `GET /map` 讀取——它是這兩個端點**全樹唯一**的
  正向覆蓋，不得當「純測 map/build」整案刪除；歸 Step 2 改前置、保留
  讀取斷言（其退役歸 Plan 02）。
  **執行結果：** 只刪 `test_map_build_route_rejects_public_v1_selection`
  一案（v1 拒絕已由 `test_project_scan_routes.py::
  test_scan_create_rejects_public_v1_selection_before_scanning` 完整覆蓋，
  含「不建 output dir」斷言，零覆蓋損失）；`:11-33` 改名為
  `test_committed_scan_is_readable_from_process_wide_map_routes`，
  `/api/map` + `/map` 讀取斷言原樣保留
- [x] **Step 2: 其餘把它當前置 build 的案例改走 `import` → `scans`**；
  若重複出現，抽 helper 放 `tests/helpers/`。
  **執行結果：** scan 兩步流程用既有共用 helper
  `tests/helpers/web_flows.py::scan_project`；`import` + `scan` 的組合
  只在本檔重複 4 次，故以 module-level `scan_fixture_project()` 收斂，
  未再新增跨檔 helper
- [x] **Step 3: `test_local_api_hardening.py` 改用其他仍存在的寫入端點
  （如 `POST /api/scans`）當素材，維持原本的 hardening 斷言不變**
  （body 的 key 一併改為 `project_id`；該測試靠 middleware 在 routing 前
  攔截，不依賴端點存在，三條斷言原樣不動）
- [x] **Step 4: 新增 regression：`POST /api/map/build` 回 404**——
  加在共用檔 `tests/web/test_retired_endpoints.py`，比照 viewer/load
  的「404 + 路由表無此 path」雙重寫法；順帶把路由表斷言抽成
  `assert_path_is_unregistered()` 並補 `/api/scans` positive control
  （review M5：避免 `app.routes` 為空時 vacuously pass）

## Task 3: 移除 handler 與 schema

- [x] **Step 1: 刪除 `map_routes.py:22-34` 的 `build_map`**（檔頭 docstring
  「Map build and viewer payload routes」一併改寫為讀取用途，並指向
  `import` → `scans` 與 CLI `systograph map`）
- [x] **Step 2: 刪除 `schemas.py:49` 的 `MapBuildApiRequest` 與 `:411`
  的 `__all__` 條目**（已確認無其他使用者）
- [x] **Step 3: 清理 `map_routes.py` 隨之無用的 import**——`MapBuildResult`、
  `CanonicalOutputConfigurationError`、`MapBuildService`、
  `dependencies.map_build_service`、`MapBuildApiRequest`；`schemas.py`
  另清掉隨之無用的 `pathlib.Path` 與 `MapBuildRequest`。
  `dependencies.map_build_service` helper **保留**（`scan_routes.py:136`
  仍是消費者，與 Plan 05 的 `viewer_session_service` 情況不同）
- [x] **Step 4: `uv run ruff check src tests`、
  `uv run ruff format --check src tests`、`uv run mypy src tests` 全綠**

## Task 4: 契約文件

`docs/API-GUIDE.md` 需處理 10 處（**執行時實際行號比計畫所列大 4～6 行**，
Plan 01 的快速開始 preflight 段落插在前面；以內容為準）：

- [x] **Step 1: `:55` Endpoint 總覽移除該列**
- [x] **Step 2: `:325-414` `### POST /api/map/build` 整節刪除**
  （該節從 `### POST /api/map/build` 一路延伸到 `## 2. 地圖讀取（Viewer）`
  之前的 `---`，不只到 request 範例為止）——實際刪除 89 行。
  **例外：** 該節末尾的 `ArtifactRef` 型別定義被 §2 的
  `artifact_refs` 敘述引用（三處），若隨節消失會留下無定義的型別名，
  故改置入 §2「Current build-scoped response…尚未包含 `artifact_refs`」段落之後
- [x] **Step 3: `:93` 快速開始的 deprecated 提示改寫**
  （只剩 `GET /api/map` 尚未退役）；同時修 `:96` 的範例腳本清單——
  它點名 `scripts/trace_map_build.sh`，Task 1 Step 3 已把該檔刪除
  （改指 `scripts/trace_scans_create.sh`）
- [x] **Step 4: `:613` `GET /map` 節、`:661` detail scan 前置敘述
  （「只用 `map/build` 不足以滿足 `map_not_loaded` 檢查」）、`:734` query
  trace 節、`:1067`／`:1070` 錯誤說明中提及本端點的敘述逐一改寫**
  （`:1070` 原本描述本端點「只攔 `CanonicalOutputConfigurationError`
  故落到 500」的差異行為，端點消失後整句移除）
- [x] **Step 5: `:30-35`「兩種流程」表的 Viewer demo 列改寫**——
  `map/build` 已不存在，demo 流程僅剩 `GET /api/map` 讀取；該列在
  Plan 02 完成時整列移除。`:104` §1 開頭同義的「Viewer demo 捷徑」
  敘述一併處理
- [x] **Step 6: `frontend/API_CONTRACT.md` 三處**——`:37`（與 `/api/map`
  一同退役的敘述）、`:75`（「does not call」敘述已無意義）、`:290`
  （`legacy_output_not_selectable` 錯誤表移除該端點）
- [x] **Step 7（計畫外，全文 grep 補掃）：** `docs/design/epic1-phase2.md`
  `:981`／`:998`／`:1201` 與 `ref-opensource/arch-graph/`
  （`systograph_architecture.md:162`、`systograph_flow.md:25`／`:147`）
  原本把本端點列為 current entry point／viewer demo flow，逐處改為
  `POST /api/scans`。`docs/work/` 下的計畫歷史文件依約定不清

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
