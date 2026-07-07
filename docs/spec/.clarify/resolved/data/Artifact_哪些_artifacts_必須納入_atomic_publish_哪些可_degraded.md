# 釐清問題

哪些 Phase2 artifacts 必須全部驗證成功後才能 atomic publish，哪些 artifacts 失敗時可以 degraded publish？

# 定位

ERM：`Artifact`、`CanonicalMap`、`ProfileSignalSet`、`ReadinessReport`、static execution tables。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 所有 JSON artifacts 都是 atomic core set；Markdown／Mermaid 可 degraded 並附 warning |
| B | Map、profile、readiness、evidence table 是 atomic core set；static execution 與 renderers 可 degraded |
| C | 只有 `ai_system_map.json` 阻塞 publish；其他 sidecars 全部可 degraded |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 build 成功條件、latest pointer、Viewer degraded behavior、Apply rollback、artifact manifest 與 failure tests。

# 優先級

High
- 現行規格同時要求 JSON 失敗不 publish，並允許部分顯示 degraded，必須先界定 core set。

---
# 解決記錄

- **回答**：A - 所有 JSON artifacts 都是 atomic core set；Markdown／Mermaid 可 degraded 並附 warning
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：明定七個 Phase2 JSON artifacts 全部屬於 atomic core set，任一缺失或驗證失敗時不發布 Build；Markdown／Mermaid renderer 失敗時可附 warning 降級發布。
