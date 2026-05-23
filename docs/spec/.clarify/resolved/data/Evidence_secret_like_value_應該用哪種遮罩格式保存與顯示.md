# 釐清問題

Secret-like value 應該用哪種遮罩格式保存與顯示？

# 定位

ERM：`Evidence.value`、`QueryTraceEvent.input`、`QueryTraceEvent.output`。Feature：建立與檢視 RAG System Map 的 secret 顯示規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 一律顯示固定字串 `[REDACTED]` |
| B | 顯示 provider / key name，不顯示 value |
| C | 顯示前後少量字元，其餘遮罩 |
| D | 顯示不可逆 hash，不顯示原值 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 evidence serialization、Markdown report、GUI detail panel、test snapshots，以及 secret exposure regression 測試。

# 優先級

High
- High：專案規範明確禁止輸出完整 secret values。

---
# 解決記錄

- **回答**：C - 顯示前後少量字元，其餘遮罩
- **更新的規格檔**：spec/erm.dbml, spec/features/建立RAG系統地圖.feature, spec/features/檢視RAG系統地圖.feature
- **變更內容**：更新 secret-like value 的顯示規則：允許前後少量字元可見，中間必須遮罩，完整 secret value 不得出現在 scanner output 或 GUI。
