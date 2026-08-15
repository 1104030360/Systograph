# Phase 12 — Template Flow Retirement Gate Report

Date: 2026-08-10
Source revision: `da0d402e931a4b286022f6581f41e78342214351`
Measurement state: dirty Phase 12 worktree; deletion authorization is therefore not signed
Raw artifact: [`phase12-template-flow-retirement-measurement.json`](./phase12-template-flow-retirement-measurement.json)

## 結論

**NO-GO：不得刪除 `FlowDerivationService`、L3 `template_adjacency_only` 或
`SYSTOGRAPH_TEMPLATE_FLOW_EDGES`。**

門檻 1、2 未通過，門檻 6 因前置門檻失敗而不得簽署。依 Plan 16G Task 1 的
fail-closed 規則，本輪停在量測與缺口回報，不進入 Task 2～7 的刪除流程。

## 量測方式

```bash
.venv/bin/python scripts/measure_template_flow_retirement.py \
  --output docs/work/Timmy/schedule/report/2026-08-10/phase12-template-flow-retirement-measurement.json
```

每個 fixture 只執行一次 filesystem scan、UA sidecar 與 parity providers，接著從
同一份 immutable snapshot 分別 materialize `on` 與 `off`。12/12 fixture 的計數均為
`filesystem_scan=1`、`ua_sidecar=1`、`parity_providers=1`，因此比較沒有把重掃漂移
混進結果。

總計：

| 模式 | canonical edges | L1 observed | L2 undetermined | L3 template | graph nodes | graph edges |
|---|---:|---:|---:|---:|---:|---:|
| `on` | 4 | 2 | 0 | 2 | 685 | 4 |
| `off` | 2 | 2 | 0 | 0 | 685 | 2 |

## 門檻 1 — FAIL

分類依 fixture source 的既有角色與 call-site 意圖判定，不依本次 scanner 是否成功
產邊倒推 expected 值。`malformed_config_rag`、`missing_slots_rag`、
`secret_masking_regression_rag` 是合法零邊；其餘 fixture 至少包含一個 RAG、provider、
router、guardrail 或 extension call topology，歸為 edge-bearing。

| fixture | 分類／理由 | off L1 | off L2 | 判定 |
|---|---|---:|---:|---|
| `basic_qdrant_ollama_rag` | edge-bearing：retriever → Qdrant | 1 | 0 | PASS |
| `custom_router_rag` | edge-bearing：route → custom router | 0 | 0 | **FAIL** |
| `faiss_sentence_transformers_rag` | edge-bearing：retriever → FAISS | 0 | 0 | **FAIL** |
| `graph_rag_extension_rag` | edge-bearing：graph/vector retrieval | 0 | 0 | **FAIL** |
| `healthcare_rag_minimal` | edge-bearing：API → guardrail → citation | 0 | 0 | **FAIL** |
| `lancedb_or_chroma_local_rag` | edge-bearing：workspace search → LanceDB | 0 | 0 | **FAIL** |
| `malformed_config_rag` | malformed/config-only，expected 0 | 0 | 0 | PASS |
| `missing_slots_rag` | query route without retrieval，expected 0 | 0 | 0 | PASS |
| `openai_external_provider_rag` | edge-bearing：API → embedding provider | 0 | 0 | **FAIL** |
| `pgvector_openai_rag` | edge-bearing：retriever → pgvector | 1 | 0 | PASS |
| `reranker_extension_rag` | edge-bearing：reranker → cross encoder | 0 | 0 | **FAIL** |
| `secret_masking_regression_rag` | config-only masking fixture，expected 0 | 0 | 0 | PASS |

最小已證實缺口即包含 FAISS、GraphRAG 與 LanceDB provider variants；即使對 router、
guardrail 或 isolated extension 採更保守分類，門檻仍然失敗，不能靠重分類取得 GO。

## 門檻 2 — FAIL

off 模式的 L1 relationship 僅有：

- `queries_vector_store`

L2 relationship 為空。下列 frozen profile relationships 都沒有 L1：

- `component_selection`
- `context_enrichment`
- `context_flow`
- `fallback_route`
- `graph_retrieval`
- `hierarchical_flow`
- `multimodal_retrieval`
- `query_route`
- `rerank`
- `retrieval_fusion`
- `self_critique`
- `tool_call`
- `workflow_transition`

覆蓋率是 1/14 個量測 vocabulary（Plan 16A 的 12 張 relationship-gated 卡，加上
`rag-grounding` alias 所需的 `context_flow`，以及已實作的 vector query relationship）。
對 Plan 16G 要求的 profile relationship 集合而言是 **0/13**；
`queries_vector_store` 不能代替其中任何語意。

## 門檻 3 — PASS

12 個 fixture 的 `on`/`off` 15 張 profile 卡五態逐項相同，`profile_changes` 總數為 0。
這只證明目前 L3 沒有推進卡片，不代表 L1 relationship coverage 已足夠。

## 門檻 4 — PASS（自動化 + live Viewer）

- 12/12 `off` artifact 都保留 52 格以上的 reference catalog；總節點數與 `on` 同為 685。
- `malformed_config_rag` 在 `off` 模式為 52 nodes / 0 edges，符合合法空 topology。
- 每個 fixture 的 `graph_edge_count` 與 canonical `edge_count` 相同。

2026-08-11 以 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES=off` 啟動真實 API/Viewer，透過
Source API → import → inventory preflight → confirm → scan 操作
`malformed_config_rag`。畫面顯示 52 nodes / 0 declared edges、reference projection
active；browser console 的 warning/error 為空。該手動 QA 不改變門檻 1、2 的 NO-GO。

## 門檻 5 — PASS

`tests/integration/test_call_priority_edge_pipeline.py` 已驗證：

- basic Qdrant 與 pgvector 在 `off` 模式各產生 direct-evidence L1 edge，且
  `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 同源。
- Apply 從同一 snapshot 重用相同 edge/evidence 與 UA parity counters。
- Rescan 在 call-site 消失後移除 stale edge，並產生新的 `scan_id`。

## 門檻 6 — NOT SIGNED

- HEAD 下沒有 v1 materialization service；唯一 materialization service 是 v2。
- `FlowDerivationService.derive(...)` 的 production invocation 位於
  `SystemMapV2MaterializationService`；`MapBuildService` 只轉傳該 DI。
- 因門檻 1、2 未過，執行者不得代表 owner 簽署不可逆刪除。
- 量測綁定的 HEAD 是 `da0d402e931a4b286022f6581f41e78342214351`，且量測時
  worktree dirty；不能把尚未提交的 Phase 12 diff 假稱為 full-SHA deletion approval。

## 後續缺口

回到 Plan 16C/16D 補齊，而不是修改 16G gate：

1. 讓 FAISS、GraphRAG、LanceDB 等 edge-bearing provider variants 產出 L1/L2。
2. 逐一建立 13 個缺失 profile relationship 的 deterministic signal、endpoint
   attribution 與 direct call-site evidence；L2 不能充當 profile wiring。
3. 補齊後重跑同一 harness；六道門檻全過並綁定可審閱的 full commit SHA，才可另輪
   啟動不可逆刪除。
