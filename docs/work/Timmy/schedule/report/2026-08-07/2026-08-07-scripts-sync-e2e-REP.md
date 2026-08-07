# 2026-08-07 Scripts 全面同步與端到端驗證（Stage 4）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-07-web-boundary-backend-first-TODO.md`
- 分支：`refactor/web-boundary-and-legacy-retirement`；umbrella issue #277
- Commits：`5871be8`（主）＋ `b0d0632`/`493e188`（fix round 1）

## 實作邏輯

Stage 2/3 改完後端後，scripts/ 是唯一還沒被系統性驗證的表面。本階段以
「逐檔盤點 × 端到端實跑」雙軌收斂：每支腳本對照現行 route schema 與 v2 map
形狀檢查端點/payload/jq 路徑/檔頭敘述，然後以隔離環境跑 `trace_all.sh`
直到全綠。原則：**修腳本讓它誠實反映後端，絕不為了綠燈掩蓋後端問題**。

## 步驟與成果

1. **逐檔盤點 scripts/**（20 支 + lib）：8 支帶既存 v1-only jq 缺陷
   （v2 cutover 遺留，`0e48727`/`577f15b` 時代寫的）逐一修復——
   `components_by_slot | keys[0]` → v2 `components[].metadata.legacy_slot`
   （0 components 時 fallback 合法 slot）；`evidence[0].id` →
   `evidence[].evidence_id`；`unmapped_components[].id` → `.unmapped_id`。
2. **trace_all 分母 17→18**：補進漏掉的 `trace_inventory_selection_preflight.sh`
   （順帶增加 secret/路徑 leak grep 覆蓋）；檔頭誠實標註唯一無腳本覆蓋的
   route（`GET /api/projects/{project_id}`，18/19）。
3. **假 PASS 拆除**：`trace_apply_confirmations_build_lineage.sh` 的
   `source_unmapped_id` 先前恆為 null 也照樣 PASS（optional 欄位）——修 jq
   路徑後再補**非空斷言**＋摘要輸出，值回退即紅。
4. **`--start-server` port 修復（部分實作 #151）**：port 由 `API_BASE_URL`
   推導；缺 port／非 http／非數字 port 一律 0 秒 fail-fast 清楚報錯
   （原為 32 秒矛盾逾時）。#151 計畫檔已勾 Task 2/3 並註記，Task 1
   （解析回歸測試）明示留待。
5. **detail-scan 預設 target 改 `unmapped_component`**：預設 fixture
   `custom_router_rag` 偵測到 0 個 component，`component_slot` 在該 fixture
   永遠 target_not_found；`--target-type` 仍可手動指定全部 5 型別＋3 aliases。

## 遇到的問題與解法

- **發現既存後端 bug（非 #277 造成）→ 依 phase10 規則記錄並回報**：
  `POST /api/mapping-proposals/{id}/decision` 的 `skip_for_now`/`reject`
  一律 422——`ProposalManualMappingFactory.create_audit()` 產出
  `NON_BASELINE_CAPABILITY_CANDIDATE` 卻不填 candidate 欄位，被 model 層
  `validate_shape()` 擋下。`git diff main...HEAD` 相關四檔皆空、既有測試
  fixture 走 EXISTING_SLOT 分支所以 pytest 全綠抓不到。**裁定：不在本分支
  修（範圍紀律），開 issue #278 追蹤**；trace 腳本改 demo `accept` 路徑，
  檔頭與執行輸出明示 #278、`--decision skip_for_now/reject` 保留可重現，
  不掩蓋。`docs/API-GUIDE.md:884` 的 skip/reject 敘述同步加 #278 註記。
- reviewer 抓到 lineage 斷言缺口與 #151 重疊未標註——fix round 1 補齊；
  Task 1 測試未做已於計畫檔明示（含 Step 2 過時敘述更正：落地行為是
  fail-fast 而非退回 8000）。

## 測試方式與結果

- `bash scripts/trace_all.sh --start-server`（隔離 `SYSTOGRAPH_STATE_DIR`
  ＋臨時 output）：**Total: 18  Failed: 0、exit 0**；真實 `~/.systograph`
  零新增檔案（`find -newermt` 驗證）；無殘留 uvicorn。
- fail-fast 負向案例 3 個實測 0 秒清楚報錯；正向 `:9000`/`:9137` 自訂 port
  實跑 PASS（同時滿足 #151 Task 3 驗證指令）。
- 六項 gate：`uv run pytest` **1135 passed / 1 skipped**、`ruff check`、
  `ruff format --check`、`mypy`（326 files）、`pnpm test` **160**、
  `pnpm build` ✓ 全綠。
- Review：Approved with follow-ups → fix round 1 後 re-review 5/6
  ADDRESSED；殘餘兩處一行級（scratchpad 報告措辭、#151 Step 2 敘述）由
  主 agent 直接修正並記錄於 ledger。

## 已知殘留

- #278（skip/reject 422）待獨立修復；修復時 `trace_mapping_proposals_decision.sh`
  的 coverage caveat 與 API-GUIDE:884 註記一併移除。
- #151 Task 1（URL 解析回歸測試）未做，fail-fast 行為目前僅手動負向案例佐證。
- `GET /api/projects/{project_id}` 無 trace 腳本覆蓋（檔頭已標註）。
