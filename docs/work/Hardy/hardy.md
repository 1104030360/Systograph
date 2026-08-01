# Hardy 工作事項 - Epic 1 Viewer / Graph UX / Query Trace

> 對應角色：工程師 B  
> 主要範圍：Viewer、graph UX、detail panel、filters、query trace replay  
> 參考設計：`docs/design/epic1.md`

## 1. 工作目標

Hardy 負責建立 Epic 1 的「呈現與互動層」。也就是讓使用者可以透過 `systograph viewer <map_json>` 載入 Timmy 產出的 `ai_system_map.json`，用互動式 graph 看懂 RAG System Map，並能查看 node / edge evidence、risk hints、filter highlight 與 query trace replay。

這一側的重點不是重新掃描 repo，而是把 Timmy 產出的事實層清楚呈現出來。

Hardy 的核心原則：

- viewer 只讀 `ai_system_map.json`。
- viewer 不得自行推論新 component。
- viewer 不得重新掃描 project folder。
- viewer 必須完整呈現 evidence 與 slot status。
- viewer 必須正確處理 invalid map、missing endpoint、trace timeout 等錯誤狀態。

## 2. 責任邊界

### Hardy 負責

- `systograph viewer <map_json>`。
- Local RAG System Map Viewer。
- graph view model。
- node / edge rendering。
- indexing flow 與 query_answer flow 顯示。
- detail panel。
- filter controls。
- zoom / pan / drag。
- viewer error state。
- query trace request UI。
- query trace replay controls。
- trace step highlight。
- UI / view-model / trace replay tests。

### Hardy 不負責

- 不負責 filesystem scanner。
- 不負責 config / Docker compose / dependency parser。
- 不負責判斷 component 是否 detected。
- 不負責建立 scanner evidence。
- 不負責產生 `ai_system_map.json` 的 source facts。
- 不在 UI 裡顯示完整 secret。

## 3. 必須交付的檔案或模組

實際路徑可依最終 UI 技術棧調整，但責任邊界應維持一致。

| 類別 | 建議路徑 | 說明 |
|---|---|---|
| Viewer adapter | `src/systograph/web/` | Local Web UI / in-process viewer adapter |
| CLI viewer command | `src/systograph/cli/` | `systograph viewer <map_json>` command wiring |
| Graph view model | `src/systograph/core/services/` 或 `src/systograph/web/` | 將 `ai_system_map.json` 轉成 UI 可用 nodes / edges |
| UI components | `src/systograph/web/components/` | graph、detail panel、filters、trace replay controls |
| Trace UI | `src/systograph/web/trace/` | query form、trace event list、replay state |
| Tests | `tests/web/`, `tests/contracts/` | viewer load、invalid map、filters、trace replay |

## 4. 主要工作項目

### B1. 建立 viewer load flow

- [ ] 實作 `systograph viewer <map_json>` 的入口。
- [ ] 載入 `ai_system_map.json`。
- [ ] 驗證 map JSON 基本格式。
- [ ] valid map 時建立 graph view model。
- [ ] map 不存在或格式無效時，GUI 顯示 error state。
- [ ] invalid map 時不顯示 graph。

驗收條件：

- `systograph viewer outputs/ai_system_map.json` 能載入正常 map。
- `systograph viewer outputs/broken-map.json` 顯示 `map_json` 與 `error_reason`。
- invalid map 不會出現空白畫面或半殘 graph。

### B2. 建立 graph view model

- [ ] 從 `components_by_slot` 建立 nodes。
- [ ] 從 `flows.edges` 建立 edges。
- [ ] 將 endpoint 與 risk hints 映射到可視覺化元素。
- [ ] 每個 node 至少保留：
  - component id
  - slot
  - status
  - name
  - evidence refs
  - risk hint refs
- [ ] 每個 edge 至少保留：
  - from slot
  - to slot
  - relationship
  - flow id
- [ ] missing / not_configured / not_applicable slots 也要能被呈現，不得只顯示 detected nodes。

驗收條件：

- indexing flow 與 query_answer flow 都能顯示。
- Qdrant node 可以從 sample map 顯示為 vector store。
- retriever -> vector_store edge 可以顯示 `queries_vector_store` relationship。

### B3. 實作 node / edge graph UI

- [ ] 顯示 RAG component node / edge graph。
- [ ] 用不同視覺樣式區分：
  - data source
  - parser
  - chunking
  - embedding
  - vector store
  - retriever
  - LLM
  - citation
  - external endpoint
  - network exposure
- [ ] 支援基本 zoom。
- [ ] 支援基本 pan。
- [ ] 支援 node drag。
- [ ] graph layout 不應讓文字重疊到無法閱讀。

驗收條件：

- 使用者能看出 indexing flow 與 query_answer flow。
- missing slots 與 detected components 有明顯差異。
- risk hint / network exposure 有高亮或標記。

### B4. 實作 detail panel

- [ ] 點選 node 時顯示：
  - slot
  - status
  - name
  - component kind
  - evidence
  - related risk hints
  - recommended next checks
- [ ] 點選 edge 時顯示：
  - from slot
  - to slot
  - relationship
  - flow id
- [ ] evidence 顯示：
  - kind
  - file
  - path
  - masked value
- [ ] secret-like value 不得完整顯示。

驗收條件：

- 點選 `qdrant_vector_db` 能看到 `docker-compose.yml` evidence。
- 點選 retriever 到 vector store 的 edge 能看到 relationship。
- detail panel 不會顯示 full secret。

### B5. 實作 filter controls

- [ ] 支援 filter 類型：
  - RAG slot
  - detected
  - missing
  - external endpoint
  - network exposure
  - risk hint
- [ ] 套用 filter 時保留完整 graph。
- [ ] 符合 filter 的 items 高亮。
- [ ] 不符合 filter 的 items 不隱藏。
- [ ] filter 狀態可清除。

驗收條件：

- 套用 risk hint filter 時，完整 graph 仍可見。
- matched items 高亮。
- unmatched items 不被移除。

### B6. 實作 query trace request flow

- [ ] 在 viewer 中提供測試問題輸入。
- [ ] 使用 map 中的 `app_api_or_orchestrator` endpoint。
- [ ] 找不到 endpoint 時顯示 `endpoint_not_found`。
- [ ] 找不到 endpoint 時不得送出 query。
- [ ] 成功送出 query 後，接收 basic trace events。
- [ ] timeout / error 時保留 partial trace event。

驗收條件：

- map 有 app endpoint 時，query trace 狀態會變成 requested / running。
- map 沒有 app endpoint 時，顯示 `endpoint_not_found` 且 `query_sent = false`。
- timeout 時不丟棄 replay。

### B7. 實作 query trace replay UI

- [ ] 將 `QueryTraceEvent.sequence_index` 作為 replay order。
- [ ] 顯示 trace steps：
  - user query
  - query processing
  - retriever
  - vector store
  - retrieved chunks
  - prompt builder
  - LLM
  - citation / response composer
  - final response
- [ ] 支援 controls：
  - pause
  - step forward
  - step backward
  - replay
- [ ] 目前 trace step 對應的 node / edge 高亮。
- [ ] error step 高亮並在 detail panel 顯示 error。
- [ ] detail panel 顯示：
  - sequence_index
  - timestamp
  - input
  - output
  - latency
  - error
  - retrieved chunks

驗收條件：

- replay 可以逐步前進與後退。
- retriever step 時 retriever component 高亮。
- error step 不會讓整次 replay 消失。

### B8. 與 Timmy 對齊 viewer contract

- [ ] 跟 Timmy 確認 graph node 必要欄位。
- [ ] 跟 Timmy 確認 edge relationship 欄位。
- [ ] 跟 Timmy 確認 risk hint 如何連到 node / endpoint / slot。
- [ ] 跟 Timmy 確認 `QueryTraceEvent` 欄位與 replay mapping。
- [ ] 把 viewer 需要但 JSON 缺少的欄位回報給 Timmy，不要在 UI 自行補假資料。

驗收條件：

- viewer 不需要讀 project folder。
- viewer 不需要呼叫 scanner provider。
- viewer 使用 sample map 即可完成大部分 UI 測試。

## 5. 測試責任

Hardy 主要負責：

- viewer load tests。
- invalid map error state tests。
- graph view model tests。
- node / edge detail panel tests。
- filter highlight tests。
- query trace replay tests。
- endpoint missing / timeout UI tests。

最低測試清單：

- [ ] valid map 可載入 graph。
- [ ] invalid map 顯示 error state，不顯示 graph。
- [ ] 點選 node 顯示 evidence。
- [ ] 點選 edge 顯示 relationship。
- [ ] filter 只高亮，不隱藏 graph。
- [ ] missing endpoint 不送出 query。
- [ ] trace error 保留 partial replay。
- [ ] UI 不顯示完整 secret。

## 6. 與 Timmy 的協作節點

| 時點 | Hardy 需要 | Timmy 交付 |
|---|---|---|
| 第 1 次同步 | slot / flow 清單 | `rag-core-v1` slots / flows |
| 第 2 次同步 | view model 欄位 | `ai-system-map/v1` schema 草案 |
| 第 3 次同步 | UI fixture data | 3 份 sample `ai_system_map.json` |
| 第 4 次同步 | trace endpoint / event contract | endpoint detection 與 `QueryTraceEvent` |
| 第 5 次同步 | final validation rules | schema validation 與 no-secret policy |

## 7. Code Review 重點

Hardy 需要特別檢查 Timmy 的 PR：

- JSON 是否有足夠 human-readable label。
- evidence 是否能支援 detail panel。
- missing / not_configured / not_applicable 是否能清楚呈現。
- risk hint 是否包含足夠的 `rationale` 與 `uncertainty`。
- `QueryTraceEvent` 是否足夠支援 replay controls。

Timmy 需要特別檢查 Hardy 的 PR：

- viewer 是否有重新掃描檔案。
- viewer 是否自行推論 JSON 中不存在的 component。
- viewer 是否可能顯示 full secret。
- query trace endpoint missing 時是否仍送出 query。
- trace replay 是否依 `sequence_index` 排序。

## 8. 完成定義

Hardy 的 Epic 1 工作完成標準：

- [ ] `systograph viewer <map_json>` 可載入 valid `ai_system_map.json`。
- [ ] invalid map JSON 顯示 error state，不顯示 graph。
- [ ] graph 顯示 indexing flow 與 query_answer flow。
- [ ] node / edge 可點選並顯示 detail panel。
- [ ] filters 符合規格：保留完整 graph，只高亮 matched items。
- [ ] query trace missing endpoint 顯示 `endpoint_not_found` 且不送出 query。
- [ ] query trace replay 支援 pause、step forward、step backward、replay。
- [ ] trace error / timeout 保留 partial replay。
- [ ] UI 不顯示完整 secret。
- [ ] viewer 不重新掃描 repo，也不創造 JSON 中不存在的 component。
