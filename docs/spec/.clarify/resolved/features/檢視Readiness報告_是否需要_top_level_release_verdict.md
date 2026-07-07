# 釐清問題

Readiness report 是否需要一個可測試的 top-level release verdict？

# 定位

Feature：`檢視 Readiness 報告`；ERM：`ReadinessReport`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 不提供 top-level verdict，只顯示 evidence-backed summary 與 findings |
| B | 提供 `ready / needs_review / blocked`，由固定 policy 從 findings 推導 |
| C | 提供 `pass / warning / fail`，由固定 policy 從 findings 推導 |
| D | Verdict 由可選、版本化 readiness policy 設定 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響產品是否能作 release gate、CLI exit code、CI/CD、report schema、finding severity 與 frontend summary。

# 優先級

High
- 產品定位是 release-readiness gate，但目前只明確禁止不透明分數，尚未決定是否輸出總體判定。

---
# 解決記錄

- **回答**：B - 提供 `ready / needs_review / blocked`，由固定 policy 從 findings 推導
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/檢視Readiness報告.feature`
- **變更內容**：在 `ReadinessReport` 增加必要 `release_verdict`，固定值域為 `ready / needs_review / blocked`；明定 verdict 由 backend 固定 readiness policy 從同 build findings 推導，frontend 只呈現不得重算或覆寫。
