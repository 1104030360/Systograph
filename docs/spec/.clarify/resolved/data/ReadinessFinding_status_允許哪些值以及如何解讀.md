# 釐清問題

`ReadinessFinding.status` 允許哪些值，以及每個值在 release-readiness 中如何解讀？

# 定位

ERM：`ReadinessFinding.status`；Feature：`檢視 Readiness 報告`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 沿用五態：`detected / partial / undetermined / not_detected / conflicted` |
| B | 使用交付狀態：`ready / needs_review / blocked` |
| C | 使用檢查結果：`pass / warning / fail` |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 readiness schema、finding renderer、排序／篩選、release gate 邏輯、CLI/API 與驗收測試。

# 優先級

High
- 規格只說 finding status 不等於 activation，尚未定義合法值域。

---
# 解決記錄

- **回答**：A - 沿用五態：`detected / partial / undetermined / not_detected / conflicted`
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：將 `ReadinessFinding.status` 固定為五態並補上 evidence-backed 語意，且明定不得與 activation 或 top-level release verdict 混用。
