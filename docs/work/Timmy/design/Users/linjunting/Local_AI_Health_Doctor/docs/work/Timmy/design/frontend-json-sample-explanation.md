# Epic 1 Frontend JSON Handoff

## 目的

這份文件提供 Epic 1 前端開發用的 JSON sample 與資料使用說明。前端可以先用這份資料完成 RAG System Map Viewer 的 UX mock、graph rendering、detail panel、filter highlight、query replay、detail scan 與 unmapped component confirmation 畫面。

前端第一版的主要資料入口是：

```text
viewer_load_result.graph_view_model
```

`graph_view_model` 已經是後端整理好的畫圖資料，前端不需要自行從完整 `ai_system_map` 推導 graph。

## Epic 1 前端使用者體驗

使用者載入 map 後，Viewer 需要讓使用者快速理解一個 RAG 系統的組成、資料流、風險提示與待確認元件。

核心體驗：

- 使用者可以看到完整 RAG 系統圖。
- 使用者可以點擊 node / edge 查看 evidence、risk hint 與 relationship。
- 使用者可以用 filter 高亮特定流程、風險或待確認元件。
- 使用者可以執行 query replay，查看查詢依序經過哪些 component。
- 使用者可以對特定 node / edge 觸發 detail scan，從粗顆粒逐步看到中顆粒與細顆粒分析。
- 使用者可以看到 `Needs confirmation` 的 unknown / unmapped component，並進入確認流程。

Progressive scan 的 UX 層級：

- 第一層是粗顆粒：先看整個 RAG 系統地圖，例如 API、Retriever、Vector Store、Prompt、LLM。
- 第二層是中顆粒：使用者點某個 node / edge 後，可以要求 backend 針對這個元件做 detail scan，例如 retriever 到底查哪個 vector store、top_k 是多少、有沒有 reranker 線索。
- 第三層是細顆粒：使用者再點更細的 edge / trace step / evidence，可以要求 backend 追 project-owned code path，例如從 `api.py:query()` 追到 `service.py:answer_question()` 再到 `generator.py:generate_answer()`。

```text
使用者載入 map
  ↓
看到 RAG 系統圖
  ↓
點 node / edge 看 evidence 與 risk
  ↓
需要更清楚時，點「詳細分析」
  ↓
看到中顆粒 component detail
  ↓
再點 edge / trace step / evidence
  ↓
看到細顆粒 code path
  ↓
用 filter 高亮流程或風險
  ↓
執行 query replay 檢查實際查詢路徑
  ↓
確認 unknown / unmapped 元件
```

```text
粗顆粒 L1：System Map
API → Retriever → Vector Store → Prompt Builder → LLM

中顆粒 L2：Component Detail
/query endpoint → Query Rewrite → Qdrant Retriever → top_k=5 → Prompt Template

細顆粒 L3：Code Path
src/api.py:query()
  → src/rag/service.py:answer_question()
  → src/rag/retriever.py:retrieve()
  → src/rag/generator.py:generate_answer()
```

## 一、核心概念總覽

Epic 1 的正式資料來源是 `ai_system_map.json`。前端畫圖時主要使用後端投影出的 `graph_view_model`。

```text
┌────────────────────────────┐
│ ai_system_map              │
│ canonical source of truth  │
└──────────────┬─────────────┘
               ↓ backend projection
┌────────────────────────────┐
│ graph_view_model           │
│ frontend directly renders  │
└──────────────┬─────────────┘
               ↓ user actions
┌────────────────────────────┐
│ trace / detail / mapping   │
│ replay, drill-down, confirm│
└────────────────────────────┘
```

前端畫面與 JSON 欄位對應：

| 前端畫面 | sample 對應欄位 |
|---|---|
| Graph nodes / edges | `viewer_load_result.graph_view_model.nodes`, `edges` |
| Node / edge detail panel | `graph_view_model.details`, `ai_system_map.evidence`, `risk_hints` |
| Filter highlight | `graph_view_model.filters` |
| Risk badges | `nodes[].risk_hint_ids`, `risk_hints_by_id` |
| Missing / not configured 狀態 | `components_by_slot.*.status`, slot nodes |
| Query trace replay | `ai_system_map.query_trace_events`, `trace_result_samples` |
| Timeout / partial replay | `trace_result_samples.timeout_partial_replay` |
| Endpoint not found | `trace_result_samples.endpoint_not_found` |
| Unmapped confirmation | `unmapped_components`, `mapping_proposal_result_sample` |
| Invalid JSON error state | `invalid_map_error_sample` |

## 二、前端要用到的 JSON 架構

前端第一版目前先以 `viewer_load_result.graph_view_model` 作為主要 rendering input。

### Response 結構

後端回傳給 Viewer 的主要 response 是 `viewer_load_result`：

```text
viewer_load_result
  ├─ ai_system_map       正式資料，完整事實
  └─ graph_view_model    前端畫圖用 projection
```

`viewer_load_result` 不是兩份 source of truth，而是一個 response 同時提供正式資料與畫圖資料。

| 區塊 | 用途 | 前端第一版怎麼用 |
|---|---|---|
| `ai_system_map` | 後端正式 map，保存完整 scanner facts、evidence、flows、risk、trace | 保留為原始資料；第一版不需要用它自行組 graph |
| `graph_view_model` | 後端從 `ai_system_map` 投影出的畫圖資料 | 直接用 `nodes` / `edges` / `details` render Viewer |

前端第一版 rendering input：

```text
viewer_load_result.graph_view_model.nodes
viewer_load_result.graph_view_model.edges
viewer_load_result.graph_view_model.details
```

`ai_system_map` 的用途是保留完整事實，讓 detail、replay、report、CI 或後續 Epic 可以回到同一份資料來源。

```text
Source of truth:
  1. ai_system_map.json

Primary viewer response:
  1. viewer_load_result
     ├─ ai_system_map       原始 canonical map
     └─ graph_view_model    graph rendering payload

Additional sample payloads in this file:
  2. trace_result_samples             query replay 狀態範例
  3. detail_scan_result_sample        L2 / L3 詳細分析結果範例
  4. mapping_proposal_result_sample   unknown 元件的 mapping 建議範例
  5. invalid_map_error_sample         map 載入失敗狀態範例
```

資料責任：

```text
ai_system_map.json 是真相
graph_view_model 是畫圖用投影
trace / detail / mapping / error 是互動結果
```

### 最小 JSON 骨架

```json
{
  "viewer_load_result": {
    "loaded": true,
    "error_reason": null,
    "map_json": "outputs/ai_system_map.json",
    "ai_system_map": {
      "schema_version": "ai-system-map/v1",
      "project": {
        "name": "sample-health-rag"
      },
      "components_by_slot": {},
      "evidence": [],
      "endpoints": [],
      "flows": [],
      "extensions": [],
      "unmapped_components": [],
      "detail_scans": [],
      "risk_hints": [],
      "recommended_next_checks": [],
      "query_trace_events": []
    },
    "graph_view_model": {
      "nodes": [],
      "edges": [],
      "details": {
        "evidence_by_id": {},
        "risk_hints_by_id": {}
      },
      "filters": {
        "available": [],
        "behavior": "highlight_only_do_not_hide_unmatched_elements"
      }
    }
  },
  "trace_result_samples": {},
  "detail_scan_result_sample": {},
  "mapping_proposal_result_sample": {},
  "invalid_map_error_sample": {}
}
```

### 塞完假資料後會長這樣

這是一份縮小版 sample，保留前端最重要的欄位。完整版本請看 `frontend-json-sample.json`。

```json
{
  "viewer_load_result": {
    "loaded": true,
    "error_reason": null,
    "map_json": "outputs/ai_system_map.json",
    "ai_system_map": {
      "schema_version": "ai-system-map/v1",
      "system_type": "rag",
      "project": {
        "name": "sample-health-rag"
      },
      "scan_depth": "system",
      "components_by_slot": {
        "retriever": {
          "slot": "retriever",
          "status": "detected",
          "instances": [
            {
              "id": "component:retriever:qdrant-retriever",
              "name": "Qdrant Retriever",
              "evidence_ids": ["evidence:retriever-code"]
            }
          ]
        },
        "vector_store": {
          "slot": "vector_store",
          "status": "detected",
          "instances": [
            {
              "id": "component:vector_store:qdrant",
              "name": "Qdrant",
              "evidence_ids": ["evidence:qdrant-docker"]
            }
          ]
        },
        "guardrails": {
          "slot": "guardrails",
          "status": "missing",
          "instances": []
        }
      },
      "evidence": [
        {
          "id": "evidence:retriever-code",
          "kind": "code_pattern",
          "file": "src/rag/retriever.py",
          "path": "as_retriever",
          "value": "top_k=5"
        },
        {
          "id": "evidence:qdrant-docker",
          "kind": "docker_service",
          "file": "docker-compose.yml",
          "path": "services.qdrant.image",
          "value": "qdrant/qdrant:v1.11.0"
        },
        {
          "id": "evidence:openai-key",
          "kind": "config_key",
          "file": ".env.example",
          "path": "OPENAI_API_KEY",
          "value": "sk-****ample"
        }
      ],
      "flows": [
        {
          "id": "flow:query_answer",
          "name": "Query Answer Flow",
          "edges": [
            {
              "id": "edge:retriever:vector_store",
              "from_component_id": "component:retriever:qdrant-retriever",
              "to_component_id": "component:vector_store:qdrant",
              "relationship": "queries_vector_store",
              "evidence_ids": ["evidence:retriever-code", "evidence:qdrant-docker"]
            }
          ]
        }
      ],
      "risk_hints": [
        {
          "id": "risk:qdrant-port",
          "type": "network_exposure",
          "target": "component:vector_store:qdrant",
          "target_type": "component_instance",
          "evidence_id": "evidence:qdrant-docker",
          "rationale": "Qdrant may be exposed by Docker Compose.",
          "uncertainty": "Epic 1 does not run full port security checks.",
          "severity_hint": "high"
        }
      ],
      "unmapped_components": [
        {
          "id": "unmapped:rerank",
          "source_file": "src/rag/rerank.py",
          "status": "needs_confirmation",
          "reason": "Looks like reranker, but scanner needs user confirmation.",
          "evidence_ids": ["evidence:rerank-code"]
        }
      ],
      "detail_scans": [],
      "query_trace_events": [
        {
          "id": "trace:001",
          "sequence_index": 0,
          "slot": "retriever",
          "component_id": "component:retriever:qdrant-retriever",
          "edge_id": "edge:retriever:vector_store",
          "latency_ms": 82,
          "error": null
        }
      ]
    },
    "graph_view_model": {
      "nodes": [
        {
          "id": "node:retriever",
          "source_id": "component:retriever:qdrant-retriever",
          "type": "component",
          "slot": "retriever",
          "status": "detected",
          "label": "Qdrant Retriever",
          "subtitle": "Retriever",
          "badges": ["detected"],
          "evidence_ids": ["evidence:retriever-code"],
          "risk_hint_ids": []
        },
        {
          "id": "node:qdrant",
          "source_id": "component:vector_store:qdrant",
          "type": "component",
          "slot": "vector_store",
          "status": "detected",
          "label": "Qdrant",
          "subtitle": "Vector Store",
          "badges": ["detected", "risk:high"],
          "evidence_ids": ["evidence:qdrant-docker"],
          "risk_hint_ids": ["risk:qdrant-port"]
        },
        {
          "id": "node:rerank-unknown",
          "source_id": "unmapped:rerank",
          "type": "unmapped",
          "slot": null,
          "status": "needs_confirmation",
          "label": "rerank.py",
          "subtitle": "Needs confirmation",
          "badges": ["unknown"],
          "evidence_ids": ["evidence:rerank-code"],
          "risk_hint_ids": []
        }
      ],
      "edges": [
        {
          "id": "graph_edge:retriever:qdrant",
          "source_id": "edge:retriever:vector_store",
          "from": "node:retriever",
          "to": "node:qdrant",
          "label": "queries",
          "relationship": "queries_vector_store",
          "evidence_ids": ["evidence:retriever-code", "evidence:qdrant-docker"],
          "risk_hint_ids": ["risk:qdrant-port"]
        }
      ],
      "details": {
        "evidence_by_id": {
          "evidence:qdrant-docker": {
            "title": "Qdrant Docker service",
            "file": "docker-compose.yml",
            "value": "qdrant/qdrant:v1.11.0"
          },
          "evidence:openai-key": {
            "title": "OpenAI API key exists",
            "file": ".env.example",
            "value": "sk-****ample"
          }
        },
        "risk_hints_by_id": {
          "risk:qdrant-port": {
            "title": "Possible vector store network exposure",
            "severity_hint": "high",
            "rationale": "Qdrant may be exposed by Docker Compose."
          }
        }
      },
      "filters": {
        "available": [
          {
            "id": "filter:risk",
            "label": "Risk hints",
            "matches_node_ids": ["node:qdrant"],
            "matches_edge_ids": ["graph_edge:retriever:qdrant"]
          }
        ],
        "behavior": "highlight_only_do_not_hide_unmatched_elements"
      }
    }
  },
  "trace_result_samples": {
    "endpoint_not_found": {
      "status": "endpoint_not_found",
      "query_sent": false,
      "events": []
    }
  },
  "detail_scan_result_sample": {
    "target_type": "component_slot",
    "target": "retriever",
    "scan_depth": "component",
    "status": "completed"
  },
  "mapping_proposal_result_sample": {
    "proposal_id": "proposal:reranker",
    "status": "pending_user_confirmation",
    "user_actions": ["accept", "edit", "reject", "skip_for_now"]
  },
  "invalid_map_error_sample": {
    "loaded": false,
    "error_reason": "schema_validation_failed",
    "graph_view_model": null
  }
}
```

### Graph node contract

每一筆 `graph_view_model.nodes[]` 對應 Viewer 上一個可點擊的 node。

```json
{
  "id": "node:component:retriever:qdrant-retriever",
  "source_id": "component:retriever:qdrant-retriever",
  "type": "component",
  "slot": "retriever",
  "status": "detected",
  "label": "Qdrant Retriever",
  "subtitle": "Retriever",
  "badges": ["detected", "detail_available"],
  "evidence_ids": ["evidence:code_pattern:retriever"],
  "risk_hint_ids": []
}
```

欄位說明：

| 欄位 | 畫面用途 |
|---|---|
| `id` | 前端畫圖用的唯一 ID |
| `label` | 方塊主標題 |
| `subtitle` | 方塊副標題 |
| `type` | 決定樣式：component / slot / extension / unmapped |
| `status` | 決定狀態：detected / missing / not_configured / needs_confirmation |
| `badges` | 方塊上的小標籤，例如 risk、external、unknown |
| `evidence_ids` | 點擊後去 details 找 evidence |
| `risk_hint_ids` | 點擊後去 details 找 risk |

### Graph edge contract

每一筆 `graph_view_model.edges[]` 對應 Viewer 上兩個 node 之間的一條連線。

```json
{
  "id": "graph_edge:query_answer:retriever:vector_store",
  "source_id": "edge:query_answer:retriever:vector_store",
  "flow_id": "flow:query_answer",
  "from": "node:component:retriever:qdrant-retriever",
  "to": "node:component:vector_store:qdrant",
  "relationship": "queries_vector_store",
  "label": "queries",
  "evidence_ids": [
    "evidence:code_pattern:retriever",
    "evidence:docker:qdrant-service"
  ],
  "risk_hint_ids": [
    "risk:docker_published_port_exposure:component-vector-store-qdrant"
  ]
}
```

欄位說明：

| 欄位 | 畫面用途 |
|---|---|
| `from` | 箭頭起點 node id |
| `to` | 箭頭終點 node id |
| `label` | 線上的短文字 |
| `flow_id` | 屬於 indexing 還是 query_answer |
| `relationship` | 後端語意，detail panel 可顯示 |
| `evidence_ids` | 這條線為什麼存在 |
| `risk_hint_ids` | 這條線是否有風險提示 |

### Detail lookup

使用者點擊 node / edge 後，前端使用該物件上的 `evidence_ids` 與 `risk_hint_ids` 查詢 `graph_view_model.details`，並將結果顯示在 detail panel。

```json
{
  "details": {
    "evidence_by_id": {
      "evidence:docker:qdrant-port": {
        "title": "Qdrant published port",
        "kind": "docker_port",
        "file": "docker-compose.yml",
        "path": "services.qdrant.ports[0]",
        "value": "6333:6333",
        "rule_id": "docker_published_port_detected"
      }
    },
    "risk_hints_by_id": {
      "risk:docker_published_port_exposure:component-vector-store-qdrant": {
        "title": "Possible vector store network exposure",
        "severity_hint": "high",
        "rationale": "Qdrant has a published Docker port and may be reachable outside the app container boundary.",
        "uncertainty": "Epic 1 does not run full port security or firewall checks."
      }
    }
  }
}
```

## 三、怎麼利用 JSON 畫出圖

Rendering 對應關係：

```text
nodes = 要畫出來的方塊
edges = 方塊之間的箭頭
details = 點方塊或箭頭後要顯示的說明
filters = 高亮哪些方塊和箭頭
query_trace_events = replay 時每一步走到哪裡
```

### Render 流程

```text
1. 讀 graph_view_model.nodes
   ↓
   每一筆 node 畫成一個方塊

2. 讀 graph_view_model.edges
   ↓
   用 edge.from 找起點 node
   用 edge.to 找終點 node
   畫一條箭頭

3. 使用者點方塊或箭頭
   ↓
   讀它的 evidence_ids / risk_hint_ids
   去 details.evidence_by_id / risk_hints_by_id 找內容
   顯示在右側 detail panel

4. 使用者點 filter
   ↓
   讀 filter.matches_node_ids / matches_edge_ids
   只高亮符合的方塊和箭頭
   保留完整 graph，不移除未命中的方塊

5. 使用者跑 query replay
   ↓
   依 query_trace_events.sequence_index 排序
   一步一步高亮 component_id 或 edge_id 對應的 node / edge
```

### Rendering example

以下 edge payload：

```json
{
  "from": "node:component:retriever:qdrant-retriever",
  "to": "node:component:vector_store:qdrant",
  "label": "queries"
}
```

對應的畫面：

```text
┌──────────────────┐       queries       ┌──────────────┐
│ Qdrant Retriever │ ─────────────────→ │ Qdrant       │
│ Retriever        │                    │ Vector Store │
└──────────────────┘                    └──────────────┘
```

點擊 `Qdrant` node 後的 detail lookup：

```text
node.risk_hint_ids
  ↓
details.risk_hints_by_id
  ↓
detail panel 顯示：
  - Possible vector store network exposure
  - severity_hint: high
  - uncertainty: Epic 1 does not run full port security checks
```

點擊 `queries` edge 後的 detail lookup：

```text
edge.evidence_ids
  ↓
details.evidence_by_id
  ↓
detail panel 顯示：
  - src/rag/retriever.py 有 retriever pattern
  - docker-compose.yml 有 qdrant service
```

### L1 / L2 / L3 drill-down 呈現方式

```text
L1 粗顆粒：畫主架構
API → Retriever → Vector Store → Prompt → LLM

使用者點 Retriever，按「詳細分析」
  ↓
L2 中顆粒：顯示 retriever 細節
Retriever → Qdrant
top_k = 5
possible reranker = needs confirmation

使用者再點某條 edge 或 trace step
  ↓
L3 細顆粒：顯示 code path
src/api.py:query()
  → src/rag/service.py:answer_question()
  → src/rag/retriever.py:retrieve()
```

前端不需要自行分析 L2 / L3。前端只需要將使用者選取的 `target_type`、`target` 與 `scan_depth` 送給後端；後端回傳 detail scan result 後，前端負責呈現結果。

### Interaction request payloads

L2 component detail scan request：

```json
{
  "target_type": "component_slot",
  "target": "retriever",
  "scan_depth": "component"
}
```

L3 code path scan request：

```json
{
  "target_type": "edge",
  "target": "edge:query_answer:prompt_builder:llm",
  "scan_depth": "code_path"
}
```

Query replay request：

```json
{
  "endpoint_id": "endpoint:local:chat-query",
  "query": "What documents mention discharge instructions?",
  "timeout_ms": 10000
}
```

Mapping confirmation request：

```json
{
  "proposal_id": "proposal:reranker-extension",
  "action": "accept",
  "confirmed_component_id": "extension:reranker:health-reranker"
}
```

Interaction summary：

```text
點 node / edge
  → 送 target_type + target + scan_depth

跑 replay
  → 送 endpoint_id + query

確認 unknown
  → 送 proposal_id + action
```

## 四、資料邊界

前端負責 Viewer UX 呈現與互動。scanner 判斷、component detection、graph projection 由後端提供。

| 前端範圍 | 說明 |
|---|---|
| Render graph | 使用 `graph_view_model.nodes` / `edges` |
| Detail panel | 使用 `graph_view_model.details` |
| Filter highlight | 使用 `graph_view_model.filters.available` |
| Replay timeline | 使用 `query_trace_events` 或 trace result |
| Confirmation UI | 使用 `mapping_proposal_result_sample` / `unmapped_components` 做 UX |

| 非前端範圍 | 說明 |
|---|---|
| Project scan | 前端不直接掃描 project folder |
| Component detection | 前端不自行判斷 component 是否存在 |
| Graph projection | 前端不自行從 `ai_system_map` 重建 domain graph |
| Filter semantics | Filter 是 highlight，不是刪除 graph elements |

## 五、主要 payload 說明

### 1. `viewer_load_result.ai_system_map`

這是 `ai_system_map.json` contract 的 sample。它保留後端 scanner 產生的完整 map 資料。

主要欄位：

| 欄位 | 用途 |
|---|---|
| `schema_version` | 確認是 `ai-system-map/v1` |
| `components_by_slot` | 每個 RAG slot 的 detected / missing / not_configured 狀態 |
| `evidence` | detail panel 顯示 scanner 為什麼這樣判斷 |
| `endpoints` | query trace 可以選的 endpoint |
| `flows[].edges` | RAG 資料流，後端會投影成 graph edge |
| `extensions` | baseline RAG 之外但已確認的元件 |
| `unmapped_components` | 有 evidence，但需要使用者確認的元件 |
| `risk_hints` | release-readiness 初步風險提示 |
| `detail_scans` | L2 / L3 drill-down 結果 |
| `query_trace_events` | replay timeline |

### 2. `viewer_load_result.graph_view_model`

這是 Viewer 的主要 rendering payload。它由後端從 `ai_system_map` 投影產生，提供前端畫 graph 所需的 nodes、edges、details 與 filters。

```text
components_by_slot / extensions / unmapped_components
          ↓
        nodes

flows[].edges
          ↓
        edges

evidence / risk_hints
          ↓
        details / badges
```

### 3. `trace_result_samples`

Replay UI 需要支援以下狀態：

| 狀態 | 前端應顯示 |
|---|---|
| `success` | 正常 replay timeline |
| `timeout_partial_replay` | 已完成步驟保留，timeout step 高亮 |
| `endpoint_not_found` | 不送 query，顯示 endpoint 缺失 |
| `unknown_step_needs_confirmation` | 顯示 Unknown / Needs confirmation 狀態 |

### 4. `mapping_proposal_result_sample`

這是 unknown / unmapped component 的 mapping suggestion sample。前端可用它設計 confirmation UI，例如 accept、edit、reject、skip。

## 六、Sample coverage

| 覆蓋項目 | 前端可驗證的 UX |
|---|---|
| detected + missing + not_configured | 前端要測不同 node 狀態和空 slot 呈現 |
| evidence lookup | 使用者點 node / edge 時要看可追溯證據 |
| risk hints | Epic 1 是 release-readiness map，不只是架構圖 |
| unmapped component | 支援手動 mapping 與 AI proposal flow |
| trace success / timeout / endpoint_not_found | replay UI 不能只測 happy path |
| invalid map error | viewer 載入壞 JSON 時不能顯示空白 graph |
| filter matches | Epic 1 filter 是 highlight，不是刪除 graph elements |

## 七、前端實作建議

建議前端先依這個順序開發：

```text
1. load viewer_load_result
   ↓
2. render graph_view_model.nodes / edges
   ↓
3. click node / edge → show evidence + risk detail
   ↓
4. filter → highlight matched nodes / edges only
   ↓
5. replay query_trace_events timeline
   ↓
6. handle timeout / endpoint_not_found / invalid_map
   ↓
7. mapping proposal confirm/edit/reject UI
```

Rendering rules：

- Graph node / edge 以 `graph_view_model` 為準。
- `unmapped_components` 在 UX 上呈現為 `Needs confirmation`。
- Filter 行為是 highlight matched nodes / edges，完整 graph 仍保留在畫面上。

## 八、檔案

- JSON sample: `frontend-json-sample.json`
- 本說明: `frontend-json-sample-explanation.md`
