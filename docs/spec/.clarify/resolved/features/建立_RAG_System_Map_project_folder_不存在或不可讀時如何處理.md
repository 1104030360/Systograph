# 釐清問題

執行 `kai-mind map <project_path>` 時，如果 project folder 不存在或不可讀，系統應如何處理？

# 定位

Feature：建立 RAG System Map。規則：使用者可以用 map command 輸入 project folder。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗，不產生 `ai_system_map.json` 或 `ai_system_map.md` |
| B | 操作失敗，但產生錯誤報告檔 |
| C | 產生空的 RAG System Map，所有 slots 標示 missing |
| D | 互動式要求使用者重新輸入 project folder |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 CLI error behavior、exit behavior、output file contract、跨平台 path 驗證與錯誤案例測試。

# 優先級

High
- High：核心 CLI 前置條件失敗行為尚未定義。

---
# 解決記錄

- **回答**：B - 操作失敗，但產生錯誤報告檔；錯誤報告要提及為何掃不到或掃描過程遇到什麼問題
- **更新的規格檔**：spec/features/建立RAG系統地圖.feature
- **變更內容**：在 map command 規則新增 project folder 不存在或不可讀的 Example，要求操作失敗、輸出 `outputs/map-error.md`、不輸出正常 map/summary，且錯誤報告包含 project_path、failure_reason、scan_stage。
