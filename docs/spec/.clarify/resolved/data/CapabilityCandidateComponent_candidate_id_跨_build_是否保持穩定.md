# 釐清問題

同一筆 confirmed mapping 重新 materialize 到 B2、B3 或 rescan build 時，`capability_candidate_id` 是否保持穩定？

# 定位

ERM：`CapabilityCandidateComponent.capability_candidate_id`、`ManualMapping.capability_candidate_id`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | Candidate id 由 mapping decision 決定，跨 build 保持穩定 |
| B | 每個 build 建立新的 candidate id，使用 mapping id 追溯 lineage |
| C | Candidate 是 project-global registry identity，獨立於 mapping 與 build |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 ProfileSignal related refs、Graph overlay identity、Apply/rescan、history diff、foreign keys 與 UI selection state。

# 優先級

Medium
- 不影響首次 build，但會影響跨版本追蹤與未來資料庫主鍵。

---
# 解決記錄

- **回答**：A - Candidate id 由 mapping decision 決定，跨 build 保持穩定
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：明定 `capability_candidate_id` 由 durable `ManualMapping` decision 決定，materialize 到 apply child build、detail child build 或 rescan build 時保持相同 id；移除以 `source_build_id + capability_candidate_id` 直接 FK 到單一 build candidate 的錯誤關係。
