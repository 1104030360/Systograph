# 2026-07-29 — scripts/ 與 architecture.md 同步 完成報告

對應 phase8 任務 3、4；TODO：`2026-07-28-scripts-architecture-sync-TODO.md`（全數勾選）。

## 實作邏輯

1. **scripts 修復以「腳本過時 vs 產品 bug」二分**：13.5/13.6 落地後
   `trace_all.sh` 有 11 個失敗，但 T11 已證明失敗與 routing 無關（變更前後
   worktree 對照完全一致）。逐 script 診斷根因：過時期望（v2 cutover 前寫的
   斷言）、fixture 選錯（掃不出被斷言的條件）、讀錯 artifact 路徑等——只修腳本；
   確認為產品 bug 的**不修**，記錄並在腳本印 KNOWN PRODUCT BUG banner。
2. **architecture.md 只重繪不擴寫**：全景圖對照 HEAD 逐框逐箭驗證（讀實際程式碼，
   不憑清單），過渡期做法只允許出現在「已刪」對照表。

## 步驟與結果

### 任務 3 — scripts/（commit `4865a79`，10 檔）

- `bash scripts/trace_all.sh --start-server`：**10 PASS / 11 FAIL → 22 PASS / 0 FAIL**
  （21→22 是把孤兒腳本 `trace_inventory_selection_preflight.sh` 接回 runner）。
  連跑兩次同 state dir 驗證冪等；每次跑完 port 8000 乾淨。
- 修復根因分類（逐 script 診斷表見
  `.superpowers/sdd/2/scripts-repair-report.md`）：v2 cutover 前的過時斷言、
  fixture 專案選擇不會觸發被斷言的行為、artifact 路徑/欄位過時等。
- 一般盤查：`dev.py`、`lib/api_trace_common.sh`、`test_*.sh` 逐檔檢查
  （module-level `app`、舊 error code、legacy fallback、`app.state.*`）——
  未過時者記錄「checked, current」。
- `uv run pytest -q` 維持 1143 passed；ruff 全綠。

### 任務 4 — architecture.md（gitignored 目錄，磁碟更新，842→983 行）

- WEB ADAPTER 區重畫：`create_app` → `build_app_services` → `AppServices`
  （18 typed 欄位）、`app.state.services` 唯一屬性、startup `hydrate_from_latest`、
  無 module-level `app`、middleware 五層外→內順序、22 條 endpoint 逐列。
- CORE 區補：`RecommendedNextCheckService`（版本中立、active v2）、
  `build_canonical`、v1 rollback lazy 化；新增「v1 退場閘門」區塊
  （census 37/37、三入口 import 純度、quarantine `cutover_blocked` durable gate、
  web legacy guard、`legacy_slot_layer_map`）。
- 新增 Step 1–9 對照圖；Plane 1 補 `migration-quarantine/` + `migration-backups/`
  （三種 artifact）。
- 修掉三處 FALSE 敘述（`ViewerSessionService` 入口清單、`app.state.*` 平鋪、
  v2 路徑誤植）；被刪除的過渡期做法只出現在「已刪」對照表。
- 主 agent 抽查：removed-item grep 僅命中「已刪」表；新內容
  （app_services×12、recommended_next_check×9、hydrate×4、census 圖）全部在位。
- 同場修正 CLAUDE.md（亦 gitignored）web 層與 State persistence 敘述。

## 遇到的問題與解決

1. **發現真 product bug（記錄不修）**：`POST /api/mapping-proposals/{id}/decision`
   在 proposal 無 `existing_slot_mapping` 候選時，`reject`/`skip_for_now` 回 422
   （`ProposalManualMappingFactory.create_audit` 抄了候選的 `mapping_type` 但沒帶
   `capability_candidate_*` 欄位，`ManualMappingCreate.validate_shape` 無視 decision
   一律要求）。`accept` 正常。**自 `577f15b`（2026-07-11）就存在**，與本次改動無關
   （唯一 unit test 的封包恰好以 existing_slot 開頭所以沒抓到）。腳本現只容忍
   該特定 422 substring（限非 accept）並印 banner；其他任何失敗照樣紅。
2. architecture.md／CLAUDE.md／`docs/work/Timmy/learn/` 皆被 gitignore——
   更新以磁碟檔案存在，不隨分支移動（與該目錄既有管理方式一致）。

## 測試結果

- `scripts/trace_all.sh --start-server`：22 PASS / 0 FAIL（連跑兩次）
- `uv run pytest -q`：1143 passed；`ruff check` 全綠
- 全景圖完整性 checklist（per-subsystem y/n）見
  `.superpowers/sdd/2/architecture-update-report.md`
