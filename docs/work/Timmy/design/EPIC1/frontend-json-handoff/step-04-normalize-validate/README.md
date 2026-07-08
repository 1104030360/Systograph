# frontend-ai-system-map-sample.json 欄位說明

Step 4 產出的 **canonical map**（磁碟檔名 `ai_system_map.json`）。
這是唯一「真相來源」；profile / readiness / graph 都從這裡讀，**不要 write back**。

## 頂層

| 欄位 | 白話 |
|------|------|
| `schema_version` | 固定 `ai-system-map/v2` |
| `system_type` | 被掃的系統類型，sample 為 `ai_system`（不預設一定是 RAG） |
| `scan_id` / `build_id` / `environment_id` | 這份 canonical map 的 assessment scope |
| `generated_from_build_id` | 必須等於目前 `build_id`；parent lineage 另用 `based_on_build_id` |
| `project` | 這次掃描綁定的專案 identity |
| `components` | 掃到的元件（API、retriever、LLM…） |
| `edges` | 元件之間的關係（資料流、context 流…） |
| `evidence` | 每筆 finding 對應的檔案/行號/rule |
| `endpoints` | HTTP 等對外入口 |
| `risk_hints` | 風險提示（sample 為空陣列） |
| `unmapped_components` | 掃到了但還對不上標準 taxonomy 的東西，可進 review |

## `project`

| 欄位 | 白話 |
|------|------|
| `project_id` | 專案 ID，後續 scan / build 都綁它 |
| `name` | 顯示用專案名 |
| `root_path` | 實際路徑；對外常 redact 成 `null` |
| `root_path_redacted` / `path_mode` | 隱藏本機絕對路徑 |

## `components[]` 每一筆

| 欄位 | 白話 |
|------|------|
| `component_id` | 穩定 ID，edges / evidence 都引用它 |
| `display_name` | UI 顯示名稱 |
| `canonical_type` | 標準類型（如 `retriever`、`llm`） |
| `layer` | 落在哪一層（input / retrieval / generation…） |
| `status` | 五態之一：`detected` / `partial` / `undetermined` / `not_detected` / `conflicted` |
| `activation` | 獨立啟用狀態；正式欄位名稱不是 `activation_state` |
| `framework` | 推斷用的框架（fastapi、langchain…） |
| `evidence_ids` | 支撐這個元件的 evidence 列表 |
| `metadata` | 額外結構化資訊（route、provider 等） |

## `edges[]` 每一筆

| 欄位 | 白話 |
|------|------|
| `edge_id` | 邊的 ID |
| `source` / `target` | 起點、終點 `component_id` |
| `relationship` | 關係類型，如 `data_flow`、`context_flow` |
| `status` | 這條邊證據是否足夠（sample 裡 retriever→LLM 是 `undetermined`） |
| `evidence_ids` | 支撐這條邊的 evidence |

## `evidence[]` 每一筆

| 欄位 | 白話 |
|------|------|
| `evidence_id` | 穩定 ID，被 component / edge / finding 引用 |
| `artifact_type` | 來源種類，如 `source_code` |
| `path` / `start_line` / `end_line` | 專案內相對路徑與行號 |
| `extract_summary` | scanner 用一句話描述看到了什麼 |
| `rule_id` | 哪條規則命中的 |

## `endpoints[]` 每一筆

| 欄位 | 白話 |
|------|------|
| `endpoint_id` | 入口 ID |
| `method` / `path` | HTTP method 與 path |
| `handler` | 對應程式符號 |
| `component_id` | 綁到哪個 component |
| `evidence_ids` | 支撐 evidence |

## `unmapped_components[]` 每一筆

| 欄位 | 白話 |
|------|------|
| `unmapped_id` | 未對位元件 ID |
| `source_file` / `observed_kind` | 在哪個檔、像什麼（如 reranker） |
| `status` | 如 `needs_review` → 可走 Step 9 review |
| `reason` | 為何還不能自動對位 |
| `suggested_actions` | 使用者可選的下一步 |
