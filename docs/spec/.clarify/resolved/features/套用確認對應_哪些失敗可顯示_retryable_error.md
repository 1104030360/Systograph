# 釐清問題

Apply 的哪些失敗可以顯示為 retryable error，哪些失敗必須要求使用者修正 request 或重新載入 latest build？

# 定位

Feature：`套用確認對應` 的「其他 Apply 失敗不得清除目前 graph 或 pending confirmations」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 只有 transient network／500 類錯誤可 retry；4xx 不可直接 retry |
| B | 除 validation 4xx 外全部可 retry |
| C | 只依 server 回傳的 explicit `retryable` 欄位判定 |
| D | Phase2 不提供自動 retry，全部由使用者重新操作 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 error schema、Apply UI、retry button、idempotency、pending confirmations 與 telemetry。

# 優先級

Medium
- 現行規格要求 retryable error，但沒有分類規則。

---
# 解決記錄

- **回答**：C - 只依 server 回傳的 explicit `retryable` 欄位判定
- **更新的規格檔**：`docs/spec/features/套用確認對應.feature`
- **變更內容**：明定 Apply retry UI 不依 HTTP status 或前端推測分類，而是依 server response 的 `retryable` 欄位決定是否顯示 retry action；無論是否可重試都不得清除目前 graph 或 pending confirmations。
