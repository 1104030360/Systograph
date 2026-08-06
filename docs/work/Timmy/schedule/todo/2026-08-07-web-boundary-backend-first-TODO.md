# 2026-08-07 Web 邊界收斂後端先行（Refactor Plans 01B/02B/03/05/06/07/08）TODO

- 分支：`refactor/web-boundary-and-legacy-retirement`
- 執行者：Claude（自主執行 phase10 dev-prompt）
- 方法：TDD（紅→綠→重構）＋ BDD（測試以行為命名、Given/When/Then 描述）＋
  subagent-driven development（每階段獨立 implementer + reviewer）
- 基線（動工前實測）：`uv run pytest` **1136 passed, 1 skipped**；
  `pnpm test` **160 passed (35 files)**——起點全綠。

## 目標

依 `docs/work/Timmy/schedule/plan/unfinish/refactor/` 的 8 份計畫，把 Web 層
demo/相容路徑全部退役、v1 rollback 寫入路徑移除、投影平面改為 type-driven，
使正式路徑成為唯一路徑。13.7/13.8（已完成）交付的 52 格 type 對位是本次
Plan 07 的前置基礎，收尾時逐項複驗不得回退。

## 範圍界定（誰做什麼）

- **本次執行（後端 + scripts + 契約文件）**：
  - Plan 01 **Phase B**（explicit preflight cutover；breaking：未帶單號回 422）
  - Plan 02 **Phase B**（退役 `GET /api/map`、`GET /map`）
  - Plan 03 全份（退役 `POST /api/map/build`）
  - Plan 05 全份（退役 `POST /api/viewer/load`；#140 以移除方式消解）
  - Plan 06 全份（移除 v1 rollback 寫入路徑；讀取路徑完整保留）
  - Plan 07 全份（plane 由 canonical_type → node → plane 推導）
  - Plan 08 全份（gate＝02+05 完成；移除 `ViewerPayload` 與 session 旁路槽）
- **不在本次範圍（前端 handoff，見
  `docs/work/Meeting-Sync/meeting_sync_2026_08_06/frontend-web-boundary-refactor-handoff.md`）**：
  FE-1（前端兩段式掃描）、FE-2（API mode 空狀態 + fallback 移除）、
  FE-3（Plan 04 Markdown report 下載，全份前端）。
- **已知並接受的代價**（2026-08-07 使用者決策，記載於 Plan 01/02 檔頭）：
  後端 Phase B 合併後到 FE-1/FE-2 上線前，正式前端掃描回 422、
  API mode 未選專案讀圖報錯——`main` 對前端暫時是壞的。

## 實作邏輯（Linus 式判斷）

1. **資料結構優先**：所有測試與 trace scripts 的「造一個 build」動作必須收斂到
   同一個 helper（scripts 端 `systograph_run_scan` 升級為 preflight 先行；
   tests 端新增共用 helper）。先把 helper 修好，再讓 17 個裸呼叫點與各 demo
   端點的 fixture 全部改用它——一個資料結構，消滅所有特殊情況。
2. **消除特殊情況**：implicit preflight 分支、demo 讀寫端點、v1 rollback
   分支、slot→layer 查表，全是「正式路徑之外的第二條路」。退役它們之後，
   每個行為只剩一條路，if/else 消失。
3. **Never break userspace 的邊界**：這裡的 userspace 是「正式契約使用者」
   （build-scoped 端點、CLI、v1 artifact 讀取能力、`legacy_output_not_selectable`
   錯誤碼契約）——這些一項都不能壞。demo 端點不是契約使用者，是計畫明載
   要退役的 deprecated surface（文件已於 2026-08-06 標記 deprecation）。
4. **順序即依賴**：01B 最先（定義最終 scan 流程，後續遷移一次到位）→
   05（刪 viewer/load，順便讓 02/03 的測試表縮短）→ 03 → 02 →
   08（gate 滿足）→ 06 → 07（互相獨立，排最後因為有視覺驗證）。

## 階段規劃與步驟

### Stage 1：計畫檔查核更新（8 份逐檔）✅ 2026-08-07 完成
- [x] Fan out 8 個 Opus subagents 逐檔比對計畫敘述 vs 現行程式碼（行號、
  引用數、issue 狀態、gate 敘述），過時處直接修正、不留舊錯
- [x] 開 umbrella GitHub issue **#277** 並回填各計畫檔的「GitHub Issue」欄
  （Plan 04 除外——它歸前端，保持待開）
- [x] 主 agent 最終 review 全部 diff ＋ 補 Plan 03 兩處執行順序註記
- 驗收：8 份計畫檔內容與 2026-08-07 程式碼現況一致 ✅
- 查核結論：所有行號/計數層級的事實 95% 準確；實質修正集中在
  Plan 02（API_CONTRACT `:75` 歸屬改 Plan 03）、Plan 03（handler 行號、
  helper 行號、測試表用途、gate 敘述）、Plan 05（ViewerSessionService
  持有關係）、Plan 06（後兩檔測試無 rollback 分支斷言）、Plan 07
  （legacy_slot 消費者清單、C3b 阻擋原因）。無阻斷級發現。
- 執行期裁定（記錄於各計畫檔）：(1) Plan 05 先於 Plan 03 →
  `trace_viewer_load.sh` 直接刪除不改寫；(2) `test_map_routes.py:11-33`
  是 `GET /api/map` 唯一正向覆蓋，Plan 03 階段保留讀取斷言；
  (3) Plan 08 追加清除 `projection_service` 死接線；(4) Plan 06 追加清理
  `map_build_pipeline.py:115-119` census 孤兒註解。

### Stage 2：Web 邊界退役（每個 plan 一個 commit，TDD）
- [x] **2a Plan 01 Phase B**：✅ 完成（commits `4d8f5c6`/`9ecfd0d`/`6572817`）。
  紅測試（422 `preflight_request_id_required`）→ 刪 implicit 分支與
  fallback → 17 呼叫點遷移（`tests/helpers/web_flows.py` 新共用 helper、
  `systograph_run_scan` preflight 先行、2 支 boundary trace script 既壞
  `scan_summary` 斷言修復）→ API-GUIDE / API_CONTRACT 同步。
  Review fix round 1（secret 遮罩 HTTP 覆蓋補回＋4 項）後 re-review 全數
  ADDRESSED。測試 1136 passed / 1 skipped。
  - deferred minor：pending 回應的 `str(tmp_path) not in str(pending)`
    絕對路徑斷言未還原（unit 層 `test_scan_boundary_review_service.py:94`
    有等價覆蓋）；守門順序測試與 422 regression 重複整份 detail dict 字面
    （文案改動會紅兩支）——留給最終 review 裁量
  - 既存缺陷（非本次引入，另開 issue 候選）：`api_trace_common.sh` 的
    `systograph_create_demo_mapping`/`systograph_first_unmapped_id` 讀
    v1-only 欄位，mapping 類 trace scripts 在 v2 下會死在 jq
- [x] **2b Plan 05**：✅ 完成（commits `b31cf4e`/`4b9333e`，review Approved
  無 Critical/Important）。140-*.md 已標 superseded；`tests/web/
  test_retired_endpoints.py` 設立為退役 regression 共用檔；CLI validate-map
  實跑確認能力未流失。測試 1135 passed / 1 skipped。
  - 待辦路由：M1+M7（session store 註解與 protocol 收斂）→ Stage 2e；
    M2（Plan 03 的 trace_viewer_load 步驟作廢標記）→ Stage 2c；
    M3（Plan 02 失效清單列）→ Stage 2d；M5（retired_endpoints 加 positive
    control）→ Stage 2c；M4（plan/unfinish/README.md 索引同步）+
    **關閉 issue #140** + CLAUDE.md `app_services.py` 過時敘述校正 →
    Stage 5；M6（標點混用）不處理
  - trace_all.sh 現況 12 PASS / 8 FAIL（全為既知 mapping 類 v1-only jq
    缺陷）→ Stage 4 處理
- [x] **2c Plan 03**：✅ 完成（commits `f15d4ea`/`b6e3c69`/`9e04802`，
  review Approved + fix round 1 全數 ADDRESSED）。404+路由表雙 regression
  進共用檔（含 `/api/scans` positive control，M5 落地）；`GET /api/map`
  唯一正向覆蓋保留並改名；越界文件掃除（epic1-phase2、arch-graph 3 處，
  reviewer 驗證 house 規則全過）。測試 1136 passed / 1 skipped。
  - 路由給 2d：N1（API-GUIDE:347 `*_path` 敘述過寬——欄位仍在
    `POST /api/scans` build_result）＋ `trace_map_get.sh` 檔頭措辭
    （整檔將刪、自然解消）＋ wait_for_api 探針必換（否則全 trace 卡死）
  - 既存（記錄）：arch-graph `systograph_architecture.md:162` 把
    `/api/scans` 寫成 `MapBuildService.build` 入口（實際 build_from_snapshot）
    → Stage 5 架構圖同步時修
- [x] **2d Plan 02 Phase B**：✅ 完成（commits `f0b9ef5`/`3a819d4`/`eaef26b`，
  review Approved with fixes → fix round 1 八項全 ADDRESSED、無新破壞）。
  探針換 `/openapi.json`；mapping 測試補 baseline 正向投影斷言（HTTP 讀取面
  覆蓋從 0 補回）；trace_graph_projection_qa 與 boundary gate 兩支實跑 PASS。
  測試 1138 passed / 1 skipped。
  - 主 agent 直接修（例外，記錄供最終 review 覆核）：Plan 02 執行註記中
    「scans-response 投影面」承接措辭一行收窄（HTTP 層無承接者，僅剩
    service 層 `test_map_build_service.py:172-175`）——re-review 指出、
    一行文字級、不再燒 fix round
  - 已知殘留（記錄）：`POST /api/scans` 回應面的正向投影斷言在 HTTP 層
    無covering test（service 層有）；`docs/spec/features/套用確認對應
    .feature:142` 的「GET /api/map 呼叫次數為 0」成為空轉斷言（repo 無
    BDD runner，不紅不錯，Stage 5 sweep 裁量）
- [ ] **2e Plan 08**：Task 0 gate 確認 → 刪 session 旁路槽（Protocol + 兩個
  實作）→ 刪 `ViewerPayload` 型別與 re-export → 檔頭註解 → grep 零命中
- 驗收：四個端點回 404 有 regression 鎖住；正式路徑行為不變；全套測試綠

### Stage 3：Legacy 清理與語意收斂
- [ ] **3a Plan 06**：紅測試（env 設 v1 → 穩定錯誤碼且零 artifact）→ 刪三個
  rollback 服務檔 → pipeline/service 接線移除 → census allowlist 同步（同一
  commit）→ 六檔測試改寫 + 兩處 fixture 測試改吃靜態 v1 fixture → 檔頭註解
  4 處 → API-GUIDE / MODEL-CONTRACT → 採 **(A)**：`operator_rollback_active`
  欄位保留、永遠 false
- [ ] **3b Plan 07**：Task 0 裁定（primary node 慣例 + undetermined fallback +
  覆蓋審計）→ helper TDD（單 node / 多 node / 查無 type）→ normalize service
  切換 + 移除 `SLOT_LAYER_BY_ID` import → slot 誤填 regression → v1 adapter
  不動 → `risk_hint_rules.toml` 文案清理 → MODEL-CONTRACT → 前端視覺
  before/after（Playwright）記錄
- 驗收：v2 只剩一條產出路徑；plane 與 slot 脫鉤有 regression 鎖住；
  v1 讀取能力不變

### Stage 4：scripts 全面同步 + 端到端驗證
- [ ] scripts/ 逐檔檢查與新後端一致（trace_all.sh 清單、lib helper、
  其餘 trace script 的前置流程）
- [ ] 起本機後端跑 `scripts/trace_all.sh` 全綠
- [ ] `uv run pytest` / `ruff check` / `ruff format --check` / `mypy` /
  `pnpm test` / `pnpm build` 全綠
- 驗收：trace_all 端到端完整執行；六項 gate 全綠

### Stage 5：架構圖 + 最終驗收 + 收尾
- [ ] 更新 `docs/work/Timmy/learn/architecture.md` ASCII 全景圖
  （完整、無缺漏；反映端點退役、v1 寫入路徑移除、type→plane 推導）
- [ ] 逐項複驗 13.7 / 13.8 驗收條件未回退（護欄測試仍在、grep 零命中）
- [ ] 逐項複驗 Plans 01B/02B/03/05/06/07/08 驗收標準，計畫檔 checkbox 勾選
  + status 更新 + 移至 finish/（含 04 除外的歸檔判斷）
- [ ] 過渡期程式碼殘留 grep 掃描（deprecated 標記、compatibility 敘述）
- [ ] 寫最終 REP、push、開 PR（Closes umbrella issue）
- 驗收：13.7/13.8 + 7 份執行計畫全部想法實現；文件與程式碼一致

## 測試方式（TDD+BDD 落實）

- 每個退役端點先寫「回 404」的紅測試、每個 breaking change 先寫「穩定錯誤碼」
  的紅測試，看它紅、再動刀、看它綠。
- 行為敘述式命名（`test_scan_without_preflight_request_id_returns_422_stable_code`
  這類 Given/When/Then 可讀句），不寫 `test1`。
- 遷移類改動靠既有測試網（1136 個）當回歸保護；改 fixture 不改斷言語意。

## 紀錄

- 每階段完成 → `docs/work/Timmy/schedule/report/2026-08-07-<階段名>-REP.md`
- 本檔為 ledger：階段完成即回填 checkbox 與 commit hash。

## 階段完成紀錄（ledger）

- Stage 1：（待記）
- Stage 2：（待記）
- Stage 3：（待記）
- Stage 4：（待記）
- Stage 5：（待記）
