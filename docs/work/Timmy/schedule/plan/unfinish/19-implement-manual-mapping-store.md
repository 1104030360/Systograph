# Task 19: Implement Manual Mapping Store

## 目標
實作 KAI-Mind-managed manual mapping store，讓使用者確認過的 mapping 可以在下次 scan 重現。此任務處理 manual selection，不處理 AI proposal。

## 為什麼要先做這個
unmapped components 不能永遠停在 needs_confirmation。設計文件要求 user-confirmed mapping 寫入 KAI-Mind-managed store，而不是修改被掃描 repo 或只改 output JSON。

## 前置需求
- Task 13 已產生 unmapped components。
- Task 15 已有 validation。
- Task 18 已能讓 GUI/CLI 看到 unmapped。

## 實作範圍
- 建立 `ManualMapping` model。
- 建立 file-based KAI-Mind-managed mapping store，採已決策選項 A：使用 OS app data directory，不固定寫死 `~/.kai-mind`。
- 以 project_id 分區儲存，project_id 由 resolved root path + git remote/git root hash 產生。
- 支援 existing slot mapping 與 new extension mapping。
- 驗證 mapping references source file/evidence/slot。
- 將 confirmed mapping 套回 `ComponentDetectionService` 或 normalize flow。

## 不包含範圍
- 不寫入被掃描 repo。
- 不做 team sharing/import/export。
- 不做 AI proposal。
- 不做 GUI form。

## 建議實作步驟
1. 建立 `src/kai_mind/config/user_mapping_store.py`。
2. 建立 `src/kai_mind/core/models/mapping.py`。
3. 建立 `src/kai_mind/core/services/manual_mapping_service.py`。
4. 使用 `platformdirs.user_data_dir("KAI-Mind")` 或等價 wrapper 決定預設 store root；測試中必須可注入 temp path。
5. 實作 mapping load/save/list，底層用 YAML/JSON file-based store。
6. 實作 mapping validation：slot exists、evidence exists、edge no dangling refs。
7. 將 valid manual mapping 套用到 component detection。
8. 寫測試：confirmed reranker mapping 下次 scan 穩定重現；invalid slot 被拒絕。

## 預期輸出
- `src/kai_mind/config/user_mapping_store.py`
- `src/kai_mind/core/models/mapping.py`
- `src/kai_mind/core/services/manual_mapping_service.py`
- `tests/unit/core/test_manual_mapping_service.py`

## 驗收標準
- confirmed mapping 不寫入 project root。
- 預設 store root 來自 OS app data directory，且可在測試中覆寫。
- mapping digest 可記錄到 report metadata。
- invalid mapping 不進 canonical JSON。
- rerun scan 可重現 confirmed mapping。

## 可能風險與注意事項
- mapping store path 在測試中要可注入，不能寫真實 user home。
- 不要直接 hard-code `~/.kai-mind` 作為唯一預設；可保留為 future explicit override。
- mapping 不可覆蓋 secret masking。
- 手動 mapping 比 AI proposal 可信，但仍需 validation。

## 新手提示
Manual mapping 是使用者說「這個檔案其實是 reranker」後，系統記住這個決定。下次掃描才能穩定重現。

## 視覺化說明
```text
┌──────────────────────┐
│ unmapped component    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ user confirms mapping │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ KAI-Mind mapping      │
│ store                 │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ next scan             │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ confirmed slot or     │
│ extension             │
└──────────────────────┘
```
