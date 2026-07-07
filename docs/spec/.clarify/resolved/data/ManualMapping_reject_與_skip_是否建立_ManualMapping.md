# 釐清問題

使用者對 MappingProposal 選擇 reject 或 skip 時，是否要建立 `ManualMapping`，還是只更新 Proposal 狀態？

# 定位

ERM：`MappingProposal`、`ManualMapping`；Feature：`檢查掃描器建議` 的 reject／skip 規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | Reject／skip 只更新 Proposal；只有 accept／edit 建立 ManualMapping |
| B | 所有 decision 都建立 ManualMapping，只有 confirmed 可被 Apply |
| C | Reject／skip 建立獨立 MappingDecisionAudit，不建立 ManualMapping |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 proposal lifecycle、local JSON layout、Apply selection、audit history、restart recovery 與 DB relationships。

# 優先級

High
- ERM note 與現行 decision result model 的語意不完全一致，會造成持久化分歧。

---
# 解決記錄

- **回答**：B - 所有 decision 都建立 ManualMapping，只有 confirmed 可被 Apply
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/檢查掃描器建議.feature`
- **變更內容**：明定 accept／edit／reject／skip 都建立 durable ManualMapping；accept／edit 寫入 confirmed，reject／skip 保存對應 audit decision，Apply 只接受 confirmed。
