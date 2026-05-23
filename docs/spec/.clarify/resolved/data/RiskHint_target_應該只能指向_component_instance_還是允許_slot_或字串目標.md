# 釐清問題

`RiskHint.target` 應該只能指向 detected component instance，還是允許指向 slot 或其他字串目標？

# 定位

ERM：`RiskHint.target`。目前 note 寫成 `Target ComponentInstance.id or component target named by the risk hint`，關聯型別不夠明確。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | `target` 必須是 `ComponentInstance.id`，沒有 detected instance 時不得建立 RiskHint |
| B | `target` 可以是 `ComponentInstance.id` 或 `ComponentSlot.slot`，並新增 target_type 欄位 |
| C | `target` 保持字串，不建立外鍵，由 `evidence_ref` 作為可追溯依據 |
| D | `RiskHint` 必須同時包含 `target` 與 `evidence_id`，以 evidence 為主要關聯 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 `RiskHint` DBML 關係、JSON schema、risk hint 測試、GUI 點選 risk hint 的跳轉行為。

# 優先級

High
- High：不釐清會導致 schema 關聯與實作方式不一致。

---
# 解決記錄

- **回答**：Short - target+evidence+rationale
- **更新的規格檔**：spec/erm.dbml, spec/features/建立RAG系統地圖.feature
- **變更內容**：更新 `RiskHint`，新增 `target_type`、`evidence_id`、`rule_id`、`rationale`、`uncertainty`，並將 network exposure feature example 改為包含 rule、rationale 與 uncertainty 的 evidence-based risk hint。
