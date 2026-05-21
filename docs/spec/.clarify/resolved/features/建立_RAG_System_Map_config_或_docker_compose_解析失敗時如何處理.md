# 釐清問題

掃描期間遇到 config、JSON、YAML 或 docker-compose 解析失敗時，System Map 應如何處理？

# 定位

Feature：建立 RAG System Map。規則：Scanner 必須根據明確檔案與設定訊號掃描 project folder。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗，不產生 System Map |
| B | 產生 partial System Map，並把 parse error 記錄為 evidence 或 risk hint |
| C | 跳過解析失敗檔案，只在 Markdown summary 顯示 warning |
| D | 將解析失敗檔案視為沒有 evidence |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 scanner robustness、read-only 掃描行為、error evidence schema、Markdown report、CLI 測試與 sample project fixtures。

# 優先級

High
- High：常見輸入錯誤會影響核心 scanner 是否可用與可測試。

---
# 解決記錄

- **回答**：B - 產生 partial System Map，並把 parse error 記錄為 evidence 或 risk hint
- **更新的規格檔**：spec/features/建立RAG系統地圖.feature
- **變更內容**：在 scanner 檔案掃描規則新增 parse error Example，要求仍輸出 `ai_system_map.json` 與 `ai_system_map.md`，並把 parse error 記錄為 evidence 與 risk hint。
