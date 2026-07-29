# 2026-07-29 階段A：Plan 13.7 / 13.8 計劃查核與更新 TODO

## 目標

phase9 任務 1：在動工前，逐項確認 `13.7.md` 與 `13.8.md` 的內容與目前程式碼
（HEAD `5250953`，branch `feat/phase2-plan13.7-13.8`）一致；過時或錯誤的敘述
直接修正，不留舊錯。兩份計劃都確認更新完，才進入階段B實作。

## 實作邏輯

1. 兩份計劃是 2026-07-29 針對 HEAD `5250953` 建立的，理論上是新的；但 phase9
   要求「先根據目前專案的狀態逐個更新計畫檔案」，所以仍逐項查核每一條
   「稽核依據」引用的檔案、行號、數字、行為敘述。
2. 派兩個 Opus subagents 平行查核（一人一檔，各自只改自己負責的計劃檔），
   查核方式：讀碼比對 + 必要時 `uv run python` / `uv run pytest` 實證。
3. 主 agent（本 session）最終 review subagents 的修正 diff，確認：
   （a）修正有憑有據；（b）沒有動到裁定點的決策內容；（c）沒有改壞計劃結構。
4. 三個裁定點在此階段由主 agent 拍板並記錄理由（使用者已授權全部決策）：
   - 13.7 Task 1 `api_route` 對位 → 採 (i) 保守維持 `("api_server",)`
   - 13.7 Task 2 TOML 檔案 → 採獨立檔 `capability_type_node_map.toml`
   - 13.8 Task 1 約束強度 → 採 (a) 至少一端命中（以既有 28 個 profile 測試
     綠燈為準）

## 步驟

- [ ] 派 subagent A 查核 `13.7.md`：bridge 13 條規則/9 種 kind、表A 27 key、
  表B行號、legacy_slot 寫入點與 4 個讀者行號、catalog 52 node（含
  `tool_network`、`prompt_builder`）、測試網現況敘述。
- [ ] 派 subagent B 查核 `13.8.md`：15 張卡 required_relationship 清單、
  FlowDerivation 12 個關係名與 fallback 死碼行號、`_relationship_evidence()`
  無端點約束的事實、canonical edge 來源封閉性、附錄 15 張卡裁定表的
  required 節點欄位。
- [ ] 主 agent review 兩份修正結果（`git diff` 計劃檔）。
- [ ] 把裁定點決策寫進計劃檔（或確認計劃內文已含預設裁定）。
- [ ] 完成後寫 `2026-07-29-phase9-plan-audit-REP.md`。

## 驗收

- 兩份計劃檔內所有檔案路徑、行號、數字與 HEAD `5250953` 程式碼一致。
- 三個裁定點有明確決定與理由記錄。
