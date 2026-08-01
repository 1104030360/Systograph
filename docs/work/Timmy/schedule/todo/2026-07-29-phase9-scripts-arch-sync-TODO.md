# 2026-07-29 階段D：scripts/ 稽核更新 + architecture.md ASCII 全景圖更新 TODO

## 目標

phase9 任務 3、4：
1. 逐檔稽核 `scripts/`（`dev.py`、`lib/`、26 支 trace/test script）是否需要
   因 13.7/13.8 的變更而更新；需要就改，每個檔案確認完才進下一步。
2. 更新 `docs/work/Timmy/learn/architecture.md` 的 ASCII 全景圖，反映
   13.7/13.8 後的最新架構（表A TOML 化、表B移除、relationship alias +
   端點約束），全景圖必須完整無缺失。

## 實作邏輯

- 13.7/13.8 都不動 HTTP API contract（endpoint、request/response schema 不變），
  所以 trace script 預期大多不需改；但仍逐檔核對其斷言的欄位與流程是否
  受 assessment/profile 變更影響（例如 readiness/profile 輸出欄位）。
- 新增的 `core/rules/*.toml`（capability_type_node_map、
  profile_relationship_alias）屬 pipeline 內部規則檔，架構圖的 rules 區塊
  需要反映。
- ASCII 圖遵守既有慣例（與 ref-opensource/arch-graph 同規則）：框內
  English-only、行寬 ≤100、用 python 驗證寬度與框線對齊，勿用 awk。
- 過渡期做法檢查：13.7 已拆表B（過渡字典）；13.8 的 alias TOML 是「明文
  標註的過渡機制」，計劃明確要求保留到 UA 落地，不得在本階段刪除。

## 步驟

- [ ] 稽核 `scripts/dev.py` 與 `scripts/lib/`。
- [ ] 逐檔稽核 26 支 `trace_*.sh` / `test_*.sh`（重點：map build、viewer_load、
  graph_projection_qa、query_trace 等與 assessment/profile 輸出相關者）。
- [ ] 需要修改的 script 逐檔改完並驗證語法（bash -n）。
- [ ] 讀 `docs/work/Timmy/learn/architecture.md` 現況，比對 13.7/13.8 後的
  管線（MapBuildService → ... → ProfileInferenceService → ...）與 rules 目錄。
- [ ] 更新 ASCII 全景圖；用 python 腳本驗證行寬與框線完整性。
- [ ] 完成後寫 `2026-07-29-phase9-scripts-arch-sync-REP.md`。

## 驗收

- scripts/ 每檔都有「已檢查（改/不改＋理由）」記錄。
- architecture.md 全景圖完整、行寬 ≤100、框線對齊、內容反映最新管線。
