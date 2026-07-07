# 釐清問題

Strict mode 載入無效 `profile_signals.json` 時，應使用哪一種錯誤回應契約？

# 定位

Feature：`檢視建置報告` 的「Profile sidecar 損壞時 strict validation 必須 fail closed」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | HTTP 422，表示 persisted sidecar 不符合 contract |
| B | HTTP 409，表示 build state 與 strict request 衝突 |
| C | HTTP 500，但只回傳安全、穩定 error code |
| D | HTTP 200，回傳 strict validation result object 且不載入 Viewer |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 Viewer load API、strict CI validation、error codes、frontend handling、logs 與 regression tests。

# 優先級

Medium
- Fail-closed 行為已確認，但外部可觀察的 error contract 尚未定義。

---
# 解決記錄

- **回答**：A - HTTP 422，表示 persisted sidecar 不符合 contract
- **更新的規格檔**：`docs/spec/features/檢視建置報告.feature`
- **變更內容**：明定 strict mode 載入無效 `profile_signals.json` 時回傳 HTTP 422 與穩定錯誤碼 `profile_sidecar_contract_invalid`，且不得載入 viewer payload。
