# 釐清問題

Phase2 的 `environment_id` 應採用哪一種完整生命週期策略？

# 定位

ERM：`Build.environment_id`、所有 assessment／sidecar scope；Feature：掃描、Apply、Viewer。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 固定使用 `environment:default-static`，Phase2 不提供建立或變更操作 |
| B | 由 assessment config 推導；config 改變時沿用 snapshot 建立新 child build 與 environment id |
| C | 由 build request 明確指定；environment 改變時沿用 snapshot 建立新 child build |
| D | Environment 是 snapshot identity 的一部分；任何變更都必須建立新 scan、snapshot 與 initial build |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 build identity、Apply、cache/idempotency、Viewer scope 顯示、readiness 比較與 API request contract。

# 優先級

High
- 目前只定義 environment 是 assessment scope，尚未定義建立與變更流程。

---
# 解決記錄

- **回答**：A - 固定使用 `environment:default-static`，Phase2 不提供建立或變更操作
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：將 Phase2 的 Build、Artifact、CanonicalMap、ReferenceAssessment、ProfileSignalSet 與 ReadinessReport 環境範圍固定為 `environment:default-static`，不提供建立、選擇或切換 Environment 的操作。
