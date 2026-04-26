# AI BDD 流程

1. **需求草案撰寫**：根據初步需求，撰寫功能需求草案，定義系統的主要功能模組。
   範例：`spec/draft/251013-invoice-detecter.md`
2. **規格化**：透過 `spec/prompts/1.formulation.md` 的提示，將上一步的需求草案轉化為詳細的規格文件，包含:

- 資料模型 `spec/erm.dbml` (格式為 DBML)。
- 功能模型 `spec/features/*.feature` (格式為 Gherkin Language)。

3. **探索**：使用 `spec/prompts/2.discovery.md` 的提示，Agent 會掃描 `spec/` 資料夾中的規格文件，識別所有未釐清或不完整的部分，並將釐清項目以結構化格式記錄於 `spec/.clarify/` 資料夾中，也會依照優先度進行排序。
4. **釐清與翻譯**：根據 `spec/prompts/3.clarify-and-translate.md` 的指引，Agent 逐一處理釐清項目，更新規格文件，並在完成後將釐清項目歸檔至 `spec/.clarify/resolved/`。Agent 在一次對話中只會處理優先度最高的釐清項目，需要多次執行此步驟以釐清所有優先度的任務。
5. **設計**：使用 `spec/prompts/4.design_prompt.md` 的指引，Agent 根據已釐清完成的規格(100%完成)，產生詳細的架構設計文件，包含：
   - 分層架構設計 (API/Services/Repositories/Agents/Utilities/Core)
   - 資料層設計 (SQLite Schema, FAISS 索引結構)
   - API 設計 (RESTful Endpoints, 統一錯誤格式)
   - 核心流程設計 (工單上傳、RAG 查詢、知識庫同步、聚類分析)
   - RAG 多代理系統設計 (Query Classifier, SQL/Semantic/Hybrid/Followup Agents)
   - 風險評分系統設計 (動態聚類 vs 固定門檻)
   - 測試策略 (單元測試/整合測試/E2E測試, 70%覆蓋率目標)
   - 實作路線圖 (Phase 1: 架構重構, Phase 2: 測試與優化, Phase 3: 增強功能)
   - 設計文件輸出至 `spec/design/architecture_design.md`

## 流程狀態

- [X] **需求草案撰寫** - 完成 (`spec/draft/demand.md`)
- [X] **規格化** - 完成 (`spec/erm.dbml`, `spec/features/*.feature`)
- [X] **探索** - 完成 (`spec/.clarify/overview.md`, 38項釐清項目已識別)
- [X] **釐清與翻譯** - 完成 (38/38項已釐清, 100%完成, 2025-10-30)
- [X] **設計** - 完成 (`spec/design/architecture_design.md`, 2025-10-30)

## 下一階段

已完成 Discovery 與 Design 階段，建議執行以下步驟：
1. **Phase 1: 架構重構** (2-3週) - 建立分層架構，抽取業務邏輯到 Services 層
2. **Phase 2: 測試與優化** (2-3週) - 達成70%測試覆蓋率，優化關鍵流程
3. **Phase 3: 增強功能** (1-2週,可選) - 實作待規格化功能(會話分頁、標題驗證、刪除確認等)