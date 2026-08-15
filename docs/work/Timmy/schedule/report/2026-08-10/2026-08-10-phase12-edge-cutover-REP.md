# Phase 12 — Call-priority Edge Cutover REP

Date: 2026-08-10
Plans: `16C-component-attribution-and-edge-derivation.md`,
`16D-call-priority-consumer-cutover.md`

## 結果

- `ComponentResidenceIndex` 以 component evidence、file 與最小 enclosing symbol span
  建元件居所索引；ambiguous／missing residence 不猜。
- `edge_relationship_rules.toml` 以完整 semantic discriminant、endpoint kinds 與 symbol
  查 relationship；查無規則產生 counters / `recommended_next_check`，不 fallback。
- `UaEdgeDerivationService` 產 L1 direct-call `observed` 與 L2 import/factory
  `undetermined`；self-loop、歧義與上限丟棄全部可見。
- `CallPriorityEdgeMergeService` 固定 `(source,target,relationship)` 與 L1 > L2 > L3；
  同級才合 evidence，低級敗者 evidence 不污染勝者。
- `FlowDerivationService` 目前只供 L3 `template_adjacency_only`；
  `SYSTOGRAPH_TEMPLATE_FLOW_EDGES` 預設 on、可設 off，非法值 fail closed。
- materialization、call graph、dataflow hints、`execution-paths/v2`、GraphViewModel 與
  profile 消費同一批 canonical edges；v2 paths 是完整 edge records，status/reason/
  evidence 不在 projection 遺失。
- `observed` validation 要求全部 evidence direct；current v2 producer 不產 `detected`。
  v1 read adapter 只把全-direct legacy edge 保留 observed，含 indirect 的歷史 edge 降成
  reserved legacy `detected`，因此舊 artifact 可讀且不冒充 call-site proof。
- Qdrant 與 pgvector real fixtures 在 L3 off 模式各得到 1 條
  `queries_vector_store` L1 edge；pgvector 使用 bounded SQL distance operator signal，
  沒有 fixture-path 特判。

## Regression 修復

AST evidence 增加後曾使 `RiskHintService` 取到非 component-owned evidence，造成 API
published-port risk context 漂移。修正為 component-owned evidence 優先，並以 focused
regression 鎖住；risk 與 profile 不再受額外 AST evidence 排序影響。

## Apply / Rescan

- Apply：同 snapshot 的 edge/evidence 與 UA invocation counters 位元級穩定。
- Rescan：call-site 移除後 stale edge 消失，使用新 `scan_id`。
- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json` 對 basic/pgvector 都與
  canonical edges 完全一致，`runtime_verified=false`。

## 獨立複核修正

- 初次複核發現 `execution_paths.json` 的 v1 node-pair projection 會遺失 edge
  status/reason/evidence；已升為 `execution-paths/v2` 並以完整 canonical edge records
  產出。
- build manifest reference validator 同步改驗 v2 edge endpoint 與 evidence IDs；先出現
  13 個 route RED，再修到全量 GREEN。
- `undetermined` edge 現在無論是否已有 evidence 都必須帶 reason，避免半可解釋狀態。
- 第二輪複核證明 references 合法時仍可篡改 sibling semantics；目前 ArtifactEdge model
  自身要求 undetermined reason，publish boundary 再把三份 typed sibling edge records
  與磁碟 canonical map 做完整有序比對，任一欄位差異都 fail closed。

## Retirement 判定

16G 的 12-fixture on/off harness 已執行，結論 **NO-GO**：門檻 1、2 未過、門檻 6
不得簽署。詳見
[`2026-08-10-phase12-template-flow-retirement-gates-REP.md`](./2026-08-10-phase12-template-flow-retirement-gates-REP.md)。
因此本輪正確結果是保留 L3 service/reason/flag，而不是為完成 checkbox 強行刪除。
