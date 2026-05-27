# Task 3: Create rag-core-v1 Reference Template

## 目標
建立 Epic 1 內建的 `rag-core-v1` reference architecture template。這份 template 要固定 RAG slots、flows、allowed statuses 與初始 requiredness hints，讓 component detection 不會自由發散。

## 為什麼要先做這個
scanner facts 必須映射到固定 slot，否則後面 `ComponentDetectionService`、flows、viewer graph 都沒有共同骨架。設計文件也明確要求 Epic 1 baseline 先固定 `rag-core-v1`，remote template import 最後才做。

## 前置需求
- Task 2 已完成 core model 與 schema。
- 已確認 Epic 1 slots 清單包含 13 個 RAG slots。
- 已確認 baseline flows 至少包含 `indexing` 與 `query_answer`。

## 實作範圍
- 建立 `src/kai_mind/core/templates/rag-core-v1.json`。
- 建立 `src/kai_mind/core/models/template.py`。
- 建立 `RagTemplateService` 載入與驗證 template。
- 測試 template slots、flows、allowed statuses。

## 不包含範圍
- 不做 template 商店。
- 不做 remote repo import。
- 不讓 template 執行任何 code。
- 不實作 component detection rules。

## 建議實作步驟
1. 建立 template JSON，包含 `id = rag-core-v1`、`system_type = rag`。
2. 填入 13 個 slots：data sources、loader、chunking、embedding、vector store、orchestrator、query processing、retriever、prompt builder、LLM、citation、guardrails、observability。
3. 填入 `indexing` 與 `query_answer` flow slot order。
4. 建立 template model 與 service。
5. 在 service 中驗證 slot 不重複、flow references 都存在。
6. 建立測試確認 template 可載入且 selected template 固定為 `rag-core-v1`。

## 預期輸出
- `src/kai_mind/core/templates/rag-core-v1.json`
- `src/kai_mind/core/models/template.py`
- `src/kai_mind/core/services/rag_template_service.py`
- `tests/core/test_rag_template_service.py`

## 驗收標準
- `RagTemplateService.load("rag-core-v1")` 回傳 valid template。
- 所有設計文件指定 slots 都存在。
- flow 中引用的 slot 都能在 template slots 中找到。
- template validation 失敗時不產生 canonical map。

## 可能風險與注意事項
- `required_for_rag` 不應在 template 中寫死成所有 slot 都 required；設計文件說它要由 scanner evidence 判定。
- 不要為 remote template 預留會執行 code 的 hook。

## 新手提示
Template 是 scanner 的地圖底稿，不是掃描結果。它說「RAG 通常有哪些位置」，真正 detect 與 missing 要由 evidence 決定。

## 視覺化說明
```text
┌──────────────────────┐
│ rag-core-v1 template  │
└───────┬─────────┬────┘
        │         │
        ↓         ↓
┌──────────────┐  ┌──────────────────────┐
│ Component    │  │ indexing /            │
│ slots        │  │ query_answer flows    │
└──────┬───────┘  └──────────┬───────────┘
       ↓                     ↓
┌──────────────────────┐  ┌──────────────────────┐
│ ComponentDetection   │  │ Viewer graph          │
│ Service              │  │ projection            │
└──────────────────────┘  └──────────────────────┘
```
