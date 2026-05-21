# 釐清問題

`ai_system_map.json` 中的 endpoints 是否需要獨立建模為資料實體？

# 定位

ERM：目前 `epic1.md` 明確要求 JSON output 包含 `endpoints`，但 `erm.dbml` 尚未定義 Endpoint 實體或 endpoint 欄位。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 不新增 Endpoint 實體，endpoint 只透過 `ComponentInstance` 與 `Evidence` 表示 |
| B | 新增 `Endpoint` 實體，記錄 endpoint value、來源 evidence、local/external 類型 |
| C | 將 endpoint 欄位直接加到 `ComponentInstance` |
| D | 將 endpoint 只作為 `RiskHint` 的一種，不進入核心 map schema |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 `erm.dbml`、JSON schema、external endpoint detection、network exposure hints、viewer detail panel 與後續 Privacy & Exposure Check。

# 優先級

High
- High：JSON contract 已要求 endpoints，但資料模型尚未覆蓋。

---
# 解決記錄

- **回答**：B - 新增 `Endpoint` 實體，記錄 endpoint value、來源 evidence、local/external 類型
- **更新的規格檔**：spec/erm.dbml
- **變更內容**：新增 `Endpoint` Table，包含 `value`、`evidence_id` 與 `endpoint_type`，並建立 `Endpoint` 到 `RagSystemMap` 與 `Evidence` 的關聯。
