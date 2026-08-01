# Task 3: Create rag-core-v1 Reference Template

## 目標
建立 Epic 1 內建的 `rag-core-v1` reference architecture template。這份 template 要固定 RAG slots、flows、allowed statuses 與初始 requiredness hints，讓 component detection 不會自由發散。

## 為什麼要先做這個
scanner facts 必須映射到固定 slot，否則後面 `ComponentDetectionService`、flows、viewer graph 都沒有共同骨架。設計文件也明確要求 Epic 1 baseline 先固定 `rag-core-v1`，remote template import 最後才做。

## 前置需求
- Task 2 已完成 core model 與 schema。
- 已確認 Epic 1 slots 清單包含 13 個 RAG slots。
- 已確認 baseline flows 至少包含 `indexing` 與 `query_answer`。

## 與 Task 2 JSON contract 的關係
Task 2 已經固定 `ai-system-map/v1` canonical JSON schema；Task 3 不修改 `schemas/ai-system-map.v1.schema.json`，也不新增 `ai_system_map.json` top-level 欄位。

`rag-core-v1.json` 是 internal reference template，不是 scanner 最終輸出的 `ai_system_map.json`。它只提供標準 RAG slot、flow order、allowed status 與 requiredness hints；後續 scanner / detection / normalization 會依照這份 template 產生 canonical map。

可視化關係：

```text
Task 2：正式輸出 contract
┌────────────────────────────┐
│ ai-system-map/v1 schema    │
│ system_map.py              │
│ contract fixtures          │
└──────────────┬─────────────┘
               │
               │ Task 3 不改這份 contract
               ↓
Task 3：RAG 標準地圖底稿
┌────────────────────────────┐
│ rag-core-v1.json           │
│ template.py                │
│ RagTemplateService         │
└──────────────┬─────────────┘
               ↓
後續 Task：掃描、映射、產正式報告
┌────────────────────────────┐
│ ai_system_map.json         │
└────────────────────────────┘
```

Template slot id 必須完全沿用 Task 2 已固定的 13 個 snake_case slot id：

- `data_sources`
- `document_loader`
- `chunking`
- `embedding_model`
- `vector_store`
- `app_api_or_orchestrator`
- `query_processing`
- `retriever`
- `prompt_builder`
- `llm`
- `citation_or_response_composer`
- `guardrails`
- `observability`

Allowed statuses 必須沿用 Task 2 的 `SlotStatus`：

- `detected`
- `missing`
- `not_configured`
- `not_applicable`

Template `flows` 使用 bare flow ids，例如 `indexing`、`query_answer`。正式 `ai_system_map.json` 產生時，normalization 階段再轉成 canonical flow object id，例如 `flow:indexing`、`flow:query_answer`。

白話：

```text
template 裡：
indexing

正式報告裡：
flow:indexing
```

## 實作範圍
- 建立 `src/systograph/core/templates/rag-core-v1.json`。
- 建立 `src/systograph/core/models/template.py`。
- 建立 `RagTemplateService` 載入與驗證 template。
- 測試 template slots、flows、allowed statuses。

## 不包含範圍
- 不做 template 商店。
- 不做 remote repo import。
- 不讓 template 執行任何 code。
- 不實作 component detection rules。
- 不修改 `ai-system-map/v1` canonical JSON schema。

## 建議實作步驟
1. 建立 template JSON，包含 `id = rag-core-v1`、`system_type = rag`。
2. 填入 13 個 slots，slot id 必須完全使用 Task 2 contract 中的 snake_case 名稱：`data_sources`、`document_loader`、`chunking`、`embedding_model`、`vector_store`、`app_api_or_orchestrator`、`query_processing`、`retriever`、`prompt_builder`、`llm`、`citation_or_response_composer`、`guardrails`、`observability`。
3. 填入 `indexing` 與 `query_answer` flow slot order；template 內使用 bare flow id，不使用 `flow:` prefix。
4. 建立 template model 與 service。
5. 在 service 中驗證 slot 不重複、flow references 都存在。
6. 在 service 中驗證 allowed statuses 等於 `detected`、`missing`、`not_configured`、`not_applicable`。
7. 建立測試確認 template 可載入且 selected template 固定為 `rag-core-v1`。

## 預期輸出
- `src/systograph/core/templates/rag-core-v1.json`
- `src/systograph/core/models/template.py`
- `src/systograph/core/services/rag_template_service.py`
- `tests/core/test_rag_template_service.py`

## 驗收標準
- `RagTemplateService.load("rag-core-v1")` 回傳 valid template。
- 所有設計文件指定 slots 都存在。
- flow 中引用的 slot 都能在 template slots 中找到。
- template `flows` 使用 `indexing`、`query_answer` 這種 bare ids，不使用 `flow:indexing`、`flow:query_answer`。
- allowed statuses 與 Task 2 `SlotStatus` 完全一致。
- 實作過程不修改 `schemas/ai-system-map.v1.schema.json`。
- template validation 失敗時不產生 canonical map。

## 可能風險與注意事項
- 不要把 `loader`、`embedding`、`orchestrator`、`citation` 這些口語名稱寫進 template slot id；必須使用 `document_loader`、`embedding_model`、`app_api_or_orchestrator`、`citation_or_response_composer`。
- `rag-core-v1.json` 是 reference template，不是正式 `ai_system_map.json` sample。
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
