# 2026-07-28 — scripts/ 與 architecture.md 同步 TODO

對應 phase8 任務 3、4（`docs/work/Timmy/schedule/dev-prompt/phase2/phase8.md`）。

## 實作邏輯

1. **scripts/ 逐檔盤點**：13.5（C1 刪 legacy detail scan fallback、C7 scan 提前
   拒絕 v1）與 13.6（T11 router prefix 統一但 URL 不變、Plan 1 組裝重構但
   create_app 簽名不變）對 scripts 的實際影響預期很小 — URL 契約一字不變是
   Plan 2 T11 的硬驗收。仍逐檔檢查 trace_*.sh / dev.py / lib/ 是否引用被刪的
   行為（如 `legacy_latest_build_fallback` warning、v1 schema version 參數），
   需要就更新，全部更新完才進下一步。
2. **實測驗證**：起 dev server 跑 `scripts/trace_all.sh` 全數通過
   （Plan 2 T11 Step 6 已含，此處做最終複驗）。
3. **architecture.md**：更新 `docs/work/Timmy/learn/architecture.md` 的 ASCII
   全景圖，重點反映：recommended_next_checks 回到 active v2 pipeline、
   RecommendedNextCheckService 新位置、v1 rollback 改 lazy、web 層新結構
   （AppServices 容器、middleware 順序、router prefix）、刪除的死碼。
   敘述精簡、全景圖必須完整無缺漏。
4. **過渡期做法清點**：確認已隨 13.5/13.6 移除的過渡期 code 與測試
   （legacy_source viewer 特例、_legacy_detail_scan、v1-typed viewer 入口、
   module-level app、18 行 app.state 相容賦值）不再殘留於圖或文件敘述。

## 步驟

- [x] `ls scripts/` 逐檔 grep 受影響字串（legacy_latest_build_fallback、
      system_map_schema_version、/api URL、app.state）
- [x] 需要修改的 scripts 逐檔更新（全部更新完才進下一步）
- [x] dev server + `bash scripts/trace_all.sh` 全數通過
- [x] 讀現行 architecture.md，對照最新程式碼結構重畫 ASCII 全景圖
- [x] 確認全景圖無缺失（10-plane viewer、pipeline 步驟、web 層、CLI、storage）
- [x] 過渡期做法殘留清點（grep 驗證）

## 完成註記（2026-07-29）

- trace_all.sh：10 PASS / 11 FAIL → **22 PASS / 0 FAIL**（10 個 script 修復 +
  孤兒 `trace_inventory_selection_preflight.sh` 接回 runner；commit `4865a79`）。
- 發現 1 個 pre-existing product bug（2026-07-11 起）：proposal decision
  `reject`/`skip_for_now` 在無 existing_slot 候選時 422 — 已記錄於
  scripts-repair-report.md，未修（非本次改動範圍），script 印 KNOWN PRODUCT BUG banner。
- architecture.md 全景圖重繪完成（983 行；該目錄 gitignored，磁碟更新）。
- CLAUDE.md State persistence／web 層敘述已同步（gitignored，磁碟更新）。
