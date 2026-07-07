# 釐清問題

Static execution 無法把 source／target 對應到 canonical component 時，call edge 與 execution step 應如何保存？

# 定位

ERM：`StaticCallEdge.source_component_id`、`StaticCallEdge.target_component_id`、`ExecutionStep.component_id`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 不建立 edge/step，只建立 undetermined finding 與 evidence |
| B | 使用獨立 symbol/source ref 欄位保存，component id 保持空值 |
| C | 允許 component id 空值，僅以 evidence ids + undetermined reason 保存 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 static artifact schema、unknown refs validation、Profile supporting refs、Viewer drill-down 與 bounded path recovery。

# 優先級

High
- 現行欄位允許空值，但 contract 又要求所有 refs 使用 v2 ids，兩者需要一致規則。

---
# 解決記錄

- **回答**：B - 使用獨立 symbol/source ref 欄位保存，component id 保持空值
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：為 StaticCallEdge 新增必要的 source_ref／target_ref，並為 ExecutionStep 新增必要的 source_ref；無法對應 canonical component 時保留安全 reference，component id 保持空值。
