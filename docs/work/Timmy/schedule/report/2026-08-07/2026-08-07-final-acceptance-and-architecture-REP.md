# 2026-08-07 架構圖更新與最終驗收（Stage 5）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-07-web-boundary-backend-first-TODO.md`
- 分支：`refactor/web-boundary-and-legacy-retirement`；umbrella issue #277
- Stage 5 commits：`7052d1a`（收尾五項）、`d40efcc`（殘餘批次 11 項）、
  `dfd8b40`（arch-graph v1 敘述）、`1d8f2d9`（最終 review fix wave 5 項）
  ＋本 REP／ledger／API_CONTRACT:7 收尾 commit

## 實作邏輯

Stage 5 是「查漏 → 收斂 → 最終防線」三段式：先做收尾雜項與 gitignored
架構圖，再跑唯讀全面驗收掃描產出殘餘清單，一次批次修完，最後由獨立的
whole-branch reviewer 以橫向視角（跨 commit 一致性、累積效應）做 merge 前
最後一道品管，其 5 項 findings 以單一 fix wave 收斂。

## 步驟與成果

1. **收尾五項**（`7052d1a`）：plan/unfinish README 索引同步（140 superseded、
   151 部分完成、refactor 七項完成）；CLAUDE.md web-layer 假敘述就地修正
   （該檔 gitignored，修正僅本機）；arch-graph `/api/scans` 入口描述拆正；
   `app.state.viewer_session_service` 零讀取死槽移除（推翻 Plan 08 當時的
   保留裁定，三條件 grep 佐證）；spec feature 檔空轉斷言改為端點無關的
   等價敘述。
2. **architecture.md ASCII 全景圖**（gitignored，不入 commit）：38 hunks、
   1035→1087 行——Route 表重寫為 19 支實際端點＋退役區塊、preflight 必帶、
   SessionStore 旁路槽移除、v1 寫入三服務刪除＋`V2_SCHEMA_VERSION` 單一
   真相源、type→plane resolver 子樹、trace scripts 現況；全景圖鏈路
   CLI/Web 入口→preflight→pipeline→publisher→viewer 投影→route 表→frontend
   連續無斷點，框線以 python east-asian-width 驗證零錯位。
3. **最終驗收掃描**（唯讀）：七計畫驗收逐條複驗（後端範圍全數成立）、
   13.7/13.8 護欄 47 個測試實跑零失敗、殘餘 grep（9 個已刪符號 scope 內
   零非法命中）、31 commits 健康檢查、trace_all 實跑 18/18。
4. **殘餘批次**（`d40efcc`，11 項）＋ **最終 fix wave**（`1d8f2d9`，5 項）：
   契約過渡態敘述、arch-graph v1 框/分支移除、map_build_service 檔頭
   caller 註解對、feature 檔欄位名、退役告示補第四端點（viewer/load＋
   #140 安全動機）、API_CONTRACT build-scoped 完整回應形狀、
   `preflight_request_id` 的 OpenAPI Field 註解（防未來誤改成
   pydantic-required 而破壞穩定錯誤碼）、Endpoint 總覽補 scan-preflights、
   錯誤體兩形狀並存準確化。

## 重大事故與復原（必讀）

**`docs/work/Timmy/learn/` 整個目錄在本階段開工前已從磁碟消失**（約
2026-08-06 19:10；gitignored → git 無法救援，Trash 備份亦無）。已由
subagent 從 Claude Code transcript **重播還原** `architecture.md`：以
2026-07-29 的一次完整 Read（984 行）為 base、重播其後 9 個 Edit（每個
old_string 唯一命中，重播可證等價），三重交叉驗證（21 個 code fence 與
記憶記載一致；`_LEGACY_SLOT_TO_NODES` 正落第 815 行與 08-05 引用一致；
base Read 無截斷）後才套用 #277 更新。**建議：請目視複核該檔，並考慮
取消 learn/ 的 gitignore 或建立備份機制——這次能救回是運氣。**

## 測試方式與結果

- 全套 gate（最終 review 獨立重跑）：pytest **1135 passed / 1 skipped**、
  ruff check / format --check、mypy 326 files、pnpm test 160、pnpm build ✓、
  trace_all **18/18 exit 0**。
- 最終 whole-branch review 判定 **READY-with-notes**：三個自選高風險區塊
  抽查（pipeline v1 切除＝invariant 淨增益；wiring guard 三層防護強於被刪
  的 239 個 rollback 測試；web_flows helper 薄且 fresh-preflight by
  construction）全過；安全紅線（secret／絕對路徑／read-only）零違反；
  5 項文件級 findings 已以 `1d8f2d9` 收斂，錯誤體三測試逐欄不變。
- Deferred triage 兩項結案：422/守門測試重複 detail dict 字面＝**設計行為**
  （抽共用常數反而弱化守門順序測試）；v1 fixture 凍結＝**正確設計**
  （無 writer 後凍結 artifact 即歷史 artifact 的正確表徵，v2 路徑另有
  live 覆蓋）。

## 收尾決策記錄

- PR 使用 **Refs #277**（Phase A／FE-1／FE-2 未完成，不得 Closes）＋
  issue 留 FE checklist；**Closes #140**（path oracle 以移除消解）。
- 8 筆 subagent commits 缺 trailer：不 rebase（改寫會使文件中數十處
  hash 引用失真），PR body 註記。
- 計畫檔不搬 finish/（美觀性搬移不進功能 PR），merge 後由使用者執行。
- 前端 F1-F4（StateOverlay 文案、viewerApi fallback 等）維持 FE-2 工作包
  範圍，不入本 PR。
