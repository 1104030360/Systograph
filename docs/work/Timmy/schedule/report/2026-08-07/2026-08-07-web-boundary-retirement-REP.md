# 2026-08-07 Web 邊界退役（Stage 2：Plans 01B/05/03/02B/08）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-07-web-boundary-backend-first-TODO.md`
- 分支：`refactor/web-boundary-and-legacy-retirement`；umbrella issue #277
- 起點基線 1136 passed / 1 skipped → 收尾 **1138 passed / 1 skipped**；
  ruff / ruff format / mypy / pnpm test（160）全綠

## 實作邏輯

Stage 2 的本質是「把正式路徑之外的第二條路全部拆掉」，順序即依賴：

1. **01B 最先**：`POST /api/scans` 必帶 `preflight_request_id` 之後，
   「造一個 build」只剩一種寫法。先把 tests 端共用 helper
   （`tests/helpers/web_flows.py`）與 scripts 端 `systograph_run_scan`
   升級成 explicit preflight 流程，17 個裸呼叫點一次遷移到位——
   後續每個計畫的測試/腳本遷移全部收斂到同一個資料結構。
2. **05 → 03 → 02B**：刪 `POST /api/viewer/load`（順帶建立
   `tests/web/test_retired_endpoints.py` 共用退役 regression 檔）→
   刪 `POST /api/map/build` → 刪 `GET /api/map`/`GET /map`。
   05 先於 03 是為了讓 `trace_viewer_load.sh` 直接刪除、不做將被丟棄的改寫。
3. **08 收尾**：02+05 之後 `ViewerPayload` 只剩自我指涉，整型別、session
   旁路槽、以及唯一用途隨之消失的 `projection_service` 注入線一併清除。

每個 plan 一輪 TDD（退役端點先寫 404 紅測試、breaking change 先寫穩定
錯誤碼紅測試）＋一個實作 commit ＋獨立 task review ＋（如有 findings）
fix round 與 scoped re-review。

## 步驟與成果（依執行順序）

| Plan | Commits | 核心變更 | Review 結果 |
|---|---|---|---|
| 01B | `4d8f5c6`/`9ecfd0d`/`6572817` | implicit preflight 分支＋fallback 刪除；422 `preflight_request_id_required`；17 呼叫點/9 檔遷移＋2 檔刪除；`web_flows.py` helper；scripts preflight 化；API-GUIDE/API_CONTRACT 同步 | 需修 5 項 → fix round 1 全 ADDRESSED |
| 05 | `b31cf4e`/`4b9333e` | `viewer_routes.py` 整檔刪；`ViewerLoadMapRequest` 刪；#140 以移除消解（140-*.md 標 superseded）；`trace_viewer_load.sh` 刪；檔頭呼叫鏈 5 處 | Approved（0 Critical/Important） |
| 03 | `f15d4ea`/`b6e3c69`/`9e04802` | `build_map` handler＋`MapBuildApiRequest` 刪；`trace_map_build.sh` 刪、`trace_map_report.sh` 改 import→scans；API-GUIDE 整節刪＋10 處、API_CONTRACT 3 處；`GET /api/map` 唯一正向覆蓋保留 | Approved → fix round 1（4 項文字級）全 ADDRESSED |
| 02B | `f0b9ef5`/`3a819d4`/`eaef26b` | `get_api_map`/`get_map_fallback` 刪（`get_map_report` 保留）；wait_for_api 探針換 `/openapi.json`；`trace_map_get/fallback.sh` 刪；兩支 boundary/QA script 改 build-scoped 並實跑 PASS；API-GUIDE「兩種流程」收斂單一流程；mapping 測試補 baseline 正向投影斷言 | Approved with fixes → fix round 1 八項全 ADDRESSED |
| 08 | `a1ce0c6`/`be80c0d` | `ViewerPayload` 型別＋re-export＋session 旁路槽＋`save_build_result` re-wrap 行刪除；追加：`projection_service` 死接線（兩 store 建構參數、import、app.py 注入）清除 | Approved（免 fix round） |

（另有 `b56b260` Stage 1 計畫查核、`d949b9f` ledger 中繼 commit。）

## 測試方式

- 每個退役端點：紅 404 regression（先看它紅）→ 刪端點 → 綠；集中在共用檔
  `tests/web/test_retired_endpoints.py`（404＋路由表雙斷言＋`/api/scans`
  positive control 防 vacuous pass）。
- Breaking change：`test_create_scan_without_preflight_request_id_returns_422_stable_code`
  等行為敘述式命名；含「不建 state/output」「sensitive 專案不退回 pending」
  等邊界斷言。
- 遷移類：既有 1136 個測試當回歸網；reviewer 逐案對照 git show BASE 確認
  斷言語意未弱化（多處實際變強：mapping 測試補了 `loaded is True`＋
  `nodes` 非空 baseline，封掉 latest 404 時 before==after 的 vacuity）。
- 每輪 review/re-review 由獨立 subagent 執行，並含破壞性驗證
  （例：暫時停用 SecretMaskingService 證明新遮罩斷言抓得到外洩，驗後還原）。
- scripts：改動過的每支實跑（`--start-server`）：
  `trace_inventory_selection_preflight.sh`、`trace_map_report.sh`、
  `trace_graph_projection_qa.sh`、`trace_scan_boundary_multi_decision_gate.sh`、
  `trace_scan_boundary_policy_overlay.sh`、`trace_scans_create.sh` 全 PASS。

## 遇到的問題與解法

1. **刪測試檔導致獨有覆蓋流失（最重要的一課）**：01B 刪
   `test_scan_boundary_routes.py` 時，「掃到真 secret 的 completed 回應不
   外洩原值」的 HTTP 層斷言一度歸零（repo 明列的 secret 紅線）。task review
   抓到後 fix round 補回（fixture 換真 secret＋skip/scan_this_run 兩情境
   斷言），並以「暫時拿掉遮罩」驗證斷言有牙齒。
2. **`scan_summary` 既壞斷言**：兩支 boundary trace script 自 v2 cutover 起
   斷言就對不上（v2 無該 key）。reviewer 以 schema grep＋git log 確認為
   「修復既壞」而非行為變更，改指 `inventory_selection_summary`。
3. **wait_for_api 探針地雷**：所有 trace script 的 bootstrap 都探測
   `GET /api/map`，端點刪除會全體卡死 60 次重試——02B 換成 `/openapi.json`
   （框架自帶、無副作用、不會再被退役）。
4. **CLAUDE.md 過時敘述**：`web/app_services.py`／`AppServices` 不存在，
   實況是 `create_app()` 逐個掛 `app.state.*`——已在後續每個 dispatch 註明
   防誤導，校正排入 Stage 5。
5. **跨計畫檔案重疊**：`trace_viewer_load.sh`（03 改寫 vs 05 刪除）與
   `test_viewer_routes.py`/`test_scan_boundary_routes.py`（02 的表格 vs
   01/05 已刪）以執行順序裁定，兩側計畫檔互相標作廢註記，零重工。

## 測試結果（收尾實測）

- `uv run pytest`：**1138 passed, 1 skipped**（1136 → −5 刪整檔 −1 legacy
  pending −1 v1 拒絕案 −3 viewer routes −2 map demo 案；＋新增 404
  regression×4、路由表×4、preflight 422×2、守門順序×1、secret 遮罩×2、
  explicit pending×1、session projection×1 等，帳目經 reviewer 逐項核對）
- `ruff check` / `ruff format --check` / `mypy src tests`：全綠
- `pnpm test`：160 passed（前端零改動，同名 TS 型別未受影響）
- 驗收 grep：`ViewerPayload` 於 `src/systograph` **零命中**；
  `api/viewer/load`、`map/build`、`GET /api/map` 殘留僅剩退役 regression
  常數與 dated 歷史文件

## 已知殘留（交 Stage 4/5 與最終 review）

- trace_all.sh 現 9 PASS / 8 FAIL：全為既存 mapping/detail-scan 類
  v1-only jq 缺陷（`components_by_slot` 等），Stage 4 處理。
- `app.state.viewer_session_service` 成零讀取死槽（保留 DI 槽的裁定下）
  → Stage 5 sweep 裁量。
- `POST /api/scans` 回應面的正向投影斷言 HTTP 層無承接（service 層有）。
- plan/unfinish/README.md 索引落後、#140 待關、CLAUDE.md 校正 → Stage 5。
