# 開源專案匯入與掃描測試計畫

> **執行者注意：** 本計畫是 Gate-2 通過，且 `00`～`13` active static readiness path
> 完成後的 validation / regression plan。逐 task 實作，不要與 profile inference / sidecar
> contract migration 混在同一支 PR。`12-add-runtime-component-trace-contract.md` 與 Plan 17
> 都是 deferred boundary，不是本計畫前置條件。

**來源：** 使用者需求、`epic1-phase2-design.md` 的 target repository boundary、`MODEL-CONTRACT.md` 的 registry-driven capability overlay catalog，以及 2026-07-03 對公開 GitHub repo / 官方 README 的外部查詢。

**目標：** 在 00A compatibility gate 與 Plan 13 active v2 cutover 完成後，以固定
SHA 的真實 AI application repos、四象限 fixtures 與 workflow artifacts 驗證 generic
AI system static readiness path：

- local project import 能處理 non-grounded LLM app、tool agent、RAG、grounded
  agent 與 workflow-orchestrated AI system；
- scanner 不執行 target app、不安裝依賴、不修改 target repo；
- `ai_system_map.json`、`profile_signals.json`、`readiness_report.json`、
  `ai_system_map.md`、`system_map.mmd` 與 viewer payload 符合最新 contract；
- registry-driven capability overlay matrix 至少都有 direct app 或 fixture / snippet 來源可驗證；
- 測試結果能用簡潔表格記錄，並可貼到對應 GitHub issue comment 當 durable record。

**關鍵修正：** 本計畫原本把 framework / research / cookbook repo 混入「直接 import 掃描」清單。這不符合 Phase 2 design 的 target boundary。本版改成兩層：

```text
Direct import targets
  = 真正 AI application repo
  = 可 clone 後以 repo 或明確 app/backend subdir 做 read-only scan

Fixture / reference-only sources
  = framework、research implementation、notebook cookbook、PoC
  = 只抽最小 fixture/snippet 或用來校準 expected profile signals
  = 不作為「直接 import 成功率」驗收基準
```

**2026-07-03 sequencing note：** runtime/query trace 仍不阻擋本計畫。00A 先完成
v1/v2 compatibility；Plan 13 再切換 active v2 output；本計畫最後驗證 active v2
與 legacy v1 import。若 00A 或 Plan 13 未通過，不得把 Plan 14 標成成功。

**2026-07-02 coverage decision：** 使用者確認 `14` 的 registry-driven capability overlay coverage
不要求每個 profile 都一定有 direct app target。沒有可靠 direct app 的 profile
可以用 fixture / reference-only source 驗證 rule coverage，但結果表必須標記
coverage gap，且 fixture 不計入 direct import success rate。

**2026-07-06 assessment validation decision：** Plan 14 必須驗證固定 10-plane / 52-node reference
map + repo overlay、五態、activation、direct / indirect / explicit-negative evidence、
field-specific conflicts、assessment scope 與 Mapping Completeness。DeepResearch 網頁中的
Validation Simulator 僅是需求研究參考，不是 KAI-Mind 產品功能，本計畫不實作 simulator。

## 2026-07-07 UA 整合對齊

**Do not start until Gate-2 passes：** Plan 16 UA structural path、`ScanSnapshot` internal
sidecar、fail-closed behavior 與 parity harness 必須全部通過並留下可回溯結果。Gate-2 未通過
時，本計畫維持 blocked。Plan 17 `AssessmentOrchestrator` 維持 deferred，明確不是 Gate-2 或
本計畫的依賴；`validated_candidates` 使用空集合。

Plan 14 新增 UA parity gate，作為 Plan 18 退役 KAI scan TOML providers 的前置驗證：

- UA structural facts / evidence 必須與過渡期 KAI TOML providers 的代表性輸出做 parity
  diff，涵蓋 dependency、docker/config、code pattern 與 endpoint/symbol 類 facts。
- UA fail-closed 必須被驗證：schema 不合法、Node runtime 缺失、必要 batch 失敗時不得進入
  Step 4，也不得產出可被當作成功的 partial artifacts。
- Apply regression 必須證明 B1→B2 不重跑 UA，只使用 `ScanSnapshot.scan_result` 的
  deterministic structural facts / evidence 重跑 Step 4～7；`ua-analysis-result` semantic
  internal sidecar 僅保存、不消費。
- Plan 18 只能在本計畫 parity / fail-closed / no-UA-rerun regression 都通過後執行。

**外部 clone 目錄決策：** direct targets 固定 clone 到 repo-relative
`/tests/fixtures/external_projects/`。實作 Plan 14 前必須先把此目錄加入 `.gitignore` 並以
測試確認不會被追蹤；本次只更新 plan 文件，不修改 `.gitignore`。

---

## 執行摘要

### 目標

以固定 SHA 的真實 AI application repos、四象限 fixtures、workflow JSON 與最小
research fixtures，驗證 00–11、13 的 static readiness path 保持 read-only、
evidence-backed、schema-valid。

### 背景

單元 fixture 無法覆蓋 monorepo、混合語言、複雜 config、超大目錄與 application/framework 邊界；但直接把外部 repo 當硬性單一 gate 也會造成不可控 flakiness。

### 目前 code 狀態

Import/scan API 已存在，profile sidecar/overlay 與 frontend integration 尚待 00–11 實作；repo 內也尚無固定 SHA manifest、外部 clone harness 或結果報告格式的自動化。

### 相關檔案

- `scripts/test_opensource_projects.sh` 或等效 Python harness（新增）
- `/tests/fixtures/external_projects/`（implementation 前必須加入 `.gitignore`）
- `tests/fixtures/rag_projects/`
- `tests/fixtures/ai_systems/`（新增四象限與 workflow fixtures）
- `docs/work/Timmy/schedule/report/local-project-import-results-YYYY-MM-DD.md`
- `src/kai_mind/cli/map_command.py`
- `frontend/src/` API mode viewer flow

### 實作步驟

先建立 manifest/clone/read-only harness，再跑 small direct gate、bounded large-repo calibration 與 fixture coverage，最後驗證 artifacts/frontend 並產生可回溯報告。

### 驗收標準

Tier A deterministic fixtures 與小型 targets 全部通過；Tier B 至少兩個大型 app
bounded scan 通過；每個 active registry profile 有 direct 或 fixture evidence；v1
migration 與 active v2 outputs 全部通過。

### 風險與注意事項

外部 repo、license、default branch 與目錄會變。不得用 floating branch 當 regression baseline，也不得把 framework/research repo 成功掃描算入 application success rate。

## Target Boundary

根據 `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md` Section 5：

適合作為 Phase 2 target：

```text
FastAPI + LangChain/LlamaIndex + Qdrant/FAISS/Chroma + Ollama/OpenAI
LangGraph app repo with retrieval tools
CrewAI app repo with agents/tasks/tools
custom RAG service with reranker or hybrid retriever
non-grounded LLM application
tool-using agent without retrieval
workflow JSON artifact with explicit nodes and edges
```

不適合作為 direct import primary target：

```text
framework source code
foundation model repo
model weight repo
full platform repo
notebook-only tutorial repo
research-only implementation repo
```

注意：大型 product repo 可以作為 bounded direct scan target，但若它更像 full platform，結果只用於 calibration，不作為本 plan 的唯一 acceptance gate。

### Required Deterministic AI-system Fixtures

| Fixture | Grounding | Agent control | 預期 |
|---|---:|---:|---|
| `non_grounded_llm_app` | no | no | generic LLM app；Capability Map 不產生 compatibility-derived product verdict |
| `tool_using_agent` | no | yes | tool/agent components detected；不可只因 agent/tool 宣告 RAG |
| `grounded_rag_service` | yes | no | retrieval / grounding components detected；agentic-control not detected |
| `grounded_agent_system` | yes | yes | grounding + agentic-control，各自有 evidence |
| `workflow_orchestrated_ai_system` | optional | optional | workflow nodes/edges 來自 JSON pointers |

Workflow fixture 可使用最小 Langflow/Dify/Flowise-like exported JSON，但只驗證 generic
nodes/edges/config facts；不承諾平台專用 importer、runtime execution 或 round-trip。

---

## Research Snapshot

外部查詢日期：2026-07-03。

| Repo | 外部訊號 | 判定 | 用途 |
|---|---|---|---|
| `QuivrHQ/quivr` | 約 39k stars；未封存；default `main`；最後 push 2025-07-09；GitHub API 未回傳 SPDX license。 | 可用但偏 full-stack RAG platform，且活躍度較低 | Tier B bounded scan；執行時先 review license file |
| `zylon-ai/private-gpt` | 約 57k stars；Apache-2.0；未封存；最後 push 2026-06-29。 | 適合 | Tier B bounded direct import |
| `chatchat-space/Langchain-Chatchat` | 約 38k stars；Apache-2.0；未封存；default `master`；最後 push 2025-11-10。 | 適合但需注意 repo drift | Tier B bounded backend scan |
| `khoj-ai/khoj` | 約 35k stars；AGPL-3.0；未封存；最後 push 2026-06-24。 | 適合，license 需記錄但 read-only clone/scan 不修改上游 | Tier B bounded direct import |
| `Cinnamon/kotaemon` | 約 25k stars；Apache-2.0；未封存；最後 push 2026-06-09。 | 適合 | Tier B direct/bounded import |
| `neo4j-labs/llm-graph-builder` | 約 4.9k stars；Apache-2.0；未封存；最後 push 2026-07-02。 | 適合 GraphRAG app target | Tier B direct/bounded import |
| `onyx-dot-app/onyx` | 約 30k stars；未封存；最後 push 2026-07-02；repo 約 1.77 GB GitHub size units。 | 大型 platform-like app | Calibration only；不得作為 blocking gate |
| `backblaze-b2-samples/agentic-rag-vector-starter-kit` | MIT；未封存；最後 push 2026-06-25；repo 小。 | 小型 sample app | Tier A direct gate，補 agentic-control |
| `HKUDS/LightRAG` | README：lightweight knowledge-graph RAG framework。 | 不符合 direct app boundary | Fixture / reference only |
| `microsoft/graphrag` | 官方 docs：data pipeline and transformation suite / structured hierarchical RAG。 | 不符合 direct app boundary | Fixture / reference only |
| `HKUDS/RAG-Anything` | README / paper：All-in-One multimodal RAG framework。 | 不符合 direct app boundary | Fixture / reference only |
| `AkariAsai/self-rag` | README：Self-RAG original research implementation。 | research-only | Fixture / reference only |
| `NirDiamant/RAG_Techniques` | README：advanced RAG technique notebook tutorials。 | notebook cookbook | Fixture / snippet only |
| `Raudaschl/rag-fusion` | README：RAG-Fusion PoC / evaluation harness。 | small PoC, not app | Fixture / snippet only |
| `ara-5/Enterprise-Agentic-RAG-Platform` | 名稱與描述相關，但 GitHub API 顯示 stars 極低、license unknown。 | 成熟度不足 | 暫不納入 |
| `Abiorh001/Contextual_rag` | 描述相關，但 stars 極低、license unknown。 | 成熟度不足 | 暫不納入 |
| `garvitsingh006/PrecisionRAG` | 描述與 metadata 不足、stars 極低、license unknown。 | 成熟度不足 | 暫不納入 |

---

## Direct Import Targets

這些專案會被 clone 到本機外部測試目錄，直接以 read-only scanner 跑 import / scan。大型 repo 可限制掃描目錄，但限制必須記錄在結果表。

| # | Repo | 主要驗證 profile | Import mode | 驗證重點 |
|---|---|---|---|---|
| 1 | `zylon-ai/private-gpt` | `rag-grounding`, `modular-composition` | full repo 或 backend package | LlamaIndex / local document QA / API layer；驗證 grounding dimensions 與 private/local patterns |
| 2 | `QuivrHQ/quivr` | `rag-grounding`, `reranking`, `modular-composition` | bounded app/backend scan | opinionated RAG、file ingestion、custom parser / vectorstore；驗證 app repo 中的 baseline + modular evidence |
| 3 | `chatchat-space/Langchain-Chatchat` | `reranking`, `hybrid-retrieval`, `agentic-control`, `multimodal-grounding` | bounded backend scan | File RAG、BM25+KNN、Agent、多模態 image chat；驗證多 profile stack |
| 4 | `khoj-ai/khoj` | `hybrid-retrieval`, `agentic-control`, `modular-composition` | full repo 或 backend package | personal AI app、custom agents、docs/web answers；驗證 agentic + hybrid search signals |
| 5 | `Cinnamon/kotaemon` | `rag-grounding`, `reranking`, `modular-composition`, `multimodal-grounding` | full repo 或 app package | document chat RAG UI、customizable pipeline；驗證 UI-backed RAG app 的 profile projection |
| 6 | `neo4j-labs/llm-graph-builder` | `graph-retrieval` | full repo / backend subdir | unstructured data -> knowledge graph app；驗證 graph extraction / Neo4j graph store signals |
| 7 | `onyx-dot-app/onyx` | `hybrid-retrieval`, `agentic-control` | bounded scan only | enterprise-scale app / platform-like repo；只作 calibration，不作唯一 acceptance gate |
| 8 | `backblaze-b2-samples/agentic-rag-vector-starter-kit` | `agentic-control`, `rag-grounding` | full repo | 小型 grounded agent sample；補足大型 app 外的可讀性 regression case |

### Validation Tiers

| Tier | Targets | Gate |
|---|---|---|
| A: deterministic direct gate | Backblaze starter kit + 至少兩個固定 SHA 的小型 app/curated app subdir | 必須全部通過；適合放 CI 或 release checklist |
| B: real-world bounded app gate | PrivateGPT、Kotaemon、Neo4j Graph Builder、Khoj、Langchain-Chatchat、Quivr | 至少兩個通過；其餘可為 documented gap，不得 silent pass |
| C: scale calibration | Onyx 或其他超大型 platform-like repo | 非 blocking；只量測 scan boundary、耗時、記憶體與 false positives |

---

## Fixture / Reference-Only Sources

這些不算 direct import 成功率。只能用最小可審查 fixture / snippet 來測 rule coverage，或用來校準 profile signal wording。

| Source | 覆蓋 profile | 使用方式 | 不作 direct import 的原因 |
|---|---|---|---|
| `HKUDS/LightRAG` | `graph-retrieval`, `hierarchical-retrieval` | 抽取 minimal server / graph retrieval sample 或作 expected-signal reference | framework / library，不是 application repo |
| `microsoft/graphrag` | `graph-retrieval`, `hierarchical-retrieval` | 作 hierarchical graph RAG reference；必要時抽 fixture | data pipeline / transformation suite，不是 application repo |
| `HKUDS/RAG-Anything` | `multimodal-grounding` | 抽 multimodal parsing / dual-graph fixture | framework，不是 application repo |
| `AkariAsai/self-rag` | `self-reflection` | 抽 reflection-token / adaptive retrieval fixture | original research implementation，不是 app |
| `NirDiamant/RAG_Techniques` | `corrective-retrieval`, `contextual-retrieval`, `multi-query-retrieval` | notebook cells 轉成最小 `.py` fixture | notebook cookbook，不適合 full repo scan |
| `Raudaschl/rag-fusion` | `multi-query-retrieval` | 抽 multi-query + RRF fixture | PoC / evaluation harness，不是 app |

---

## Profile Coverage Matrix

| Profile ID | Direct app target | Fixture / reference fallback | 驗收說明 |
|---|---|---|---|
| `rag-grounding` | PrivateGPT, Quivr, Kotaemon | N/A | 至少一個 direct app 必須 `detected` 或有明確 slot evidence |
| `agentic-control` | Khoj, Langchain-Chatchat, Onyx, Backblaze starter kit | grounded/tool-agent fixtures | 需要 planner/router/controller 與 action/retrieval decision evidence |
| `tool-calling` | Khoj, Backblaze starter kit | tool-agent fixture | tool definition 與 actual binding/dispatch evidence 必須分開記錄 |
| `memory` | Khoj 或其他 app target | memory fixture | dependency/name-only 不得 detected；需 state persistence/use evidence |
| `workflow-orchestration` | app target 若適用 | workflow JSON fixture | nodes/edges 必須有 JSON pointer evidence；不推測 runtime path |
| `reranking` | Langchain-Chatchat, Kotaemon, Quivr | RAG_Techniques | 只驗證明確 retrieval enhancement，且不可吃掉更精準 profile；不可只憑 dependency / naming 猜測 |
| `hybrid-retrieval` | Khoj, Langchain-Chatchat, Onyx | RAG_Techniques | BM25 / sparse + dense retrieval evidence 必須可追到 code/config |
| `corrective-retrieval` | 暫無可靠 direct app | RAG_Techniques fixture | 允許只用 fixture 驗證 rule，結果須標記 coverage gap |
| `self-reflection` | 暫無可靠 direct app | Self-RAG fixture | 研究 repo 不作 direct import acceptance gate |
| `graph-retrieval` | Neo4j LLM Graph Builder | LightRAG, GraphRAG | direct app + framework reference 交叉驗證 |
| `hierarchical-retrieval` | 暫無可靠 direct app | GraphRAG, LightRAG fixture | 允許只用 fixture 驗證；需記錄 gap |
| `contextual-retrieval` | 暫無可靠 direct app | RAG_Techniques fixture | 允許只用 fixture 驗證；需記錄 gap |
| `multimodal-grounding` | Langchain-Chatchat, Kotaemon | RAG-Anything fixture | direct app 若只支援 image chat，需明確標記 evidence 邊界 |
| `modular-composition` | PrivateGPT, Quivr, Khoj, Kotaemon | N/A | 必須有 provider registry、plugin catalog、config-driven component selection 或可替換 pipeline evidence；一般 framework usage 不足 |
| `multi-query-retrieval` | 暫無可靠 direct app | RAG-Fusion / RAG_Techniques fixture | 允許只用 fixture 驗證；需記錄 gap |

---

## Scope

包含：

- Clone direct import targets 到固定的 repo-relative
  `/tests/fixtures/external_projects/`；不得改用其他未記錄位置。
- 對 direct targets 執行 `Local AI Health Doctor` CLI scan，不安裝 target repo dependencies，不啟動 target app。
- 對 fixture / reference-only sources 抽取最小 `.py` fixture / snippet，並標明來源 commit SHA。
- 驗證 scanner read-only：掃描前後 target repo `git status --short` 不應變化。
- 驗證 `ai_system_map.json`、`profile_signals.json`、CLI stdout / stderr 不暴露 secret values。
- 驗證固定 reference map + repo overlay 的五態都有 evidence-based 理由，並驗證
  activation、evidence kind、field-specific conflicts、coverage gate 與 scope。
- 驗證 Mapping Completeness 可由 `detected=1`、`not_detected=1`、`partial=0.5`、
  `undetermined/conflicted=0` 重算，且不被呈現成 confidence。
- 將每次 import / scan 的實際結果整理成簡潔表格，貼到對應 GitHub issue comment。

不包含：

- 修改外部開源專案本身。
- 對外部專案開 PR 或 issue。
- 安裝或執行外部專案依賴。
- 把 framework / cookbook repo 當成 application direct scan 的成功率基準。
- 做完整 runtime topology reconstruction。
- 實作或驗收 Validation Simulator。

---

## Implementation Tasks

### Task 1: 建立外部專案測試目錄與 clone manifest

- [ ] 在任何 clone 前，確認 `/tests/fixtures/external_projects/` 已加入 `.gitignore`；
  若尚未加入，先在 Plan 14 implementation PR 補上並新增 ignore guard test。
- [ ] 建立固定外部專案目錄 `/tests/fixtures/external_projects/`；不得使用
  `var/external-test-projects/` 或其他未列入 contract 的替代目錄。
- [ ] 撰寫 `scripts/test_opensource_projects.sh` 或 Python orchestration script，從 manifest clone direct import targets。
- [ ] Manifest 必須記錄 repo URL、expected commit SHA、import mode、scan subdir、target profiles、是否 direct import。
- [ ] Clone 後固定 commit SHA，不用 floating branch 當 regression baseline。
- [ ] 對大型 repo 設定 bounded scan path，並在結果表記錄實際 scan root。

### Task 2: 建立 fixture / reference-only 流程

- [ ] 建立五個 deterministic `tests/fixtures/ai_systems/` fixtures：non-grounded
  LLM app、tool agent、grounded RAG、grounded agent、workflow JSON。
- [ ] Workflow JSON evidence 必須保留 project-relative path 與 JSON pointer；只用
  `nodes`/`edges` 字串出現不得直接判斷支援某平台。
- [ ] 將 LightRAG、GraphRAG、RAG-Anything、Self-RAG、RAG_Techniques、RAG-Fusion 放入 fixture/reference manifest，不納入 direct import success rate。
- [ ] 對 notebook cookbook 只抽最小 code cell 轉 `.py` fixture，並保留來源 URL / commit SHA / notebook path。
- [ ] Fixture 必須足以驗證 profile rule，不可引入整個外部專案或大檔案。
- [ ] 每個 fixture 都要有 expected profile rows 與 expected evidence rule IDs。

### Task 3: 驗證 Two-Phase Analysis

- [ ] 執行 scan 並確認 core engine 先用 UA structural path（import map、structure、
  symbol/endpoint/call hints）產生 deterministic facts；過渡期 KAI TOML providers 僅做
  parity diff。
- [ ] 檢查 log / test hooks，確認未將 raw source tree 整包丟給 LLM。
- [ ] 驗證 PrivateGPT / Quivr / Kotaemon 的 baseline slot evidence 來自 deterministic facts。
- [ ] 驗證 Neo4j LLM Graph Builder 與 graph fixtures 的 entity / relationship / graph-store signals 可追到 code/config evidence。
- [ ] Phase2 active path 不執行 UA file-analyzer；KAI-Mind Step 6 以外不新增 AI
  orchestration。若未來 Plan 17 重啟 semantic output，也不能新增 component/edge/evidence
  或單獨提升 profile status。
- [ ] 驗證 `scan-project.mjs` 不執行；其語言 / fileCategory / 行數 enrichment 已在 Step 2
  inventory 中出現。

### Task 4: 驗證安全與隱私

- [ ] 掃描前後對每個 direct target 執行 `git status --short`，確認 scanner read-only。
- [ ] 驗證 CLI output、logs、`ai_system_map.json`、`ai_system_map.md`、`profile_signals.json` 不包含 unmasked secrets。
- [ ] 若掃描發現 secret-like values，只記錄 masked evidence 與 rule IDs，不記錄完整值。
- [ ] Network exposure findings 必須保留 uncertainty，不可宣稱 runtime reachability。

### Task 5: 驗證 Profile Inference 與 SystemMap 結構

- [ ] 驗證所有 direct targets 可產生 schema-valid active
  `ai-system-map/v2` `ai_system_map.json`。
- [ ] 驗證 Step 3 scan TOML / providers 只產 raw facts 與 evidence；掃描規則中不得含
  `plane_id`、`reference_node_id`、profile trigger 或 canonical output 欄位；且這些 providers
  在 UA-primary 過渡期只作 parity-only。
- [ ] 驗證 UA parity gate：UA facts / evidence 對照 KAI TOML providers 的代表性輸出，
  記錄 missing / extra / equivalent / intentionally-degraded 差異，並保存可追溯報告。
- [ ] 驗證 UA fail-closed：invalid result schema、Node runtime 缺失、必要 batch 失敗時，
  build 停在 Step 3，不進 Step 4，不更新 latest viewer payload。
- [ ] 驗證 Step 4 `component_bridge_registry.py` 可把代表性 `rule_id` 分流為
  component / unmapped / candidate input，且不輸出 10 planes / 52 nodes 對位。
- [ ] 驗證 Step 6 `ProfileInferenceService` 才把 validated repo facts 對到 fixed
  reference nodes；Step 7 GraphProjection 只消費此結果來畫 reference map + repo overlay。
- [ ] 以 v1 legacy fixtures 驗證 00A adapter 可讀且 semantic evidence 不遺失；
  新 build 不再輸出 v1。
- [ ] 驗證所有成功 scan 的 direct targets 都產生 `profile_signals.json`，且包含完整 registry-driven capability overlay matrix。
- [ ] 對每個 reference row 檢查五態與 evidence：`detected` 必須有高特異性
  direct evidence；只有 indirect evidence 時一律為 `partial`（多個 convergent indirect
  signals 也不得升級）；
  `not_detected` 必須完成相關 coverage gate；完成 coverage 後沒有 positive evidence即可
  判定未偵測到，不要求捏造 explicit-negative evidence。
- [ ] 驗證 explicit-negative 只接受明確 disabled / bypassed / forbidden 等否定證據；
  absence 或未命中不得標成 explicit-negative。
- [ ] 驗證 `conflicted` 只標記發生矛盾的欄位並保存雙方 evidence ids，不把整個
  component 無差別降級。
- [ ] 驗證每列 `activation` 為 enabled / disabled / conditional / unknown /
  conflicted / not_applicable 之一，且與 status 分開判斷。`not_applicable` 只適用於
  catalog 宣告本質上沒有 activation 語意的 node，不是 system/scope applicability 判斷。
- [ ] 驗證 `build_id`、`scan_id`、`environment_id` 一致，repo overlay component
  不可混入其他 build / snapshot / environment。
- [ ] 驗證 Mapping Completeness 可從固定權重與全部固定 reference rows 重算；
  activation/not_applicable 不得縮小 denominator。
- [ ] 驗證 `SystemMapIndex` 可處理大型 repo 的 slot / evidence / unmapped / profile lookup，結果 deterministic。
- [ ] 驗證全新 scan 不再建立 active `extensions` product concept；若 legacy field 仍因 v1 compatibility 出現，必須是空或 clearly legacy-only。
- [ ] 驗證四象限 fixtures 的 grounding applicable 與 agent-control 結論符合 matrix。

### Task 6: JSON report schema 與跨平台行為

- [ ] 驗證 JSON reports 通過最新 schema / contract tests。
- [ ] 驗證 macOS 與 Windows 路徑處理、encoding、project-relative path redaction。
- [ ] 驗證 readiness report 是 evidence-based findings，不是單一分數。
- [ ] 驗證 JSON reports 不輸出 compatibility-derived product verdict。
- [ ] 驗證 retrieval / grounding / generation / control / evidence 等能力由 Capability Map
  plane/component assessment 表達。
- [ ] 驗證沒有 citation / source mapping 只會產生 `source_traceability` readiness finding。
- [ ] 驗證 `ai_system_map.json`、`profile_signals.json`、
  `readiness_report.json`、`ai_system_map.md`、`system_map.mmd` 成對出現在同一
  output 目錄，且 schema/source versions 一致。
- [ ] 驗證 `system_map.mmd` 對五種 fixtures 非空、node/edge ids 可回查 evidence，
  且不把 static edge 描述成 runtime traversal。
- [ ] `primary_map_type` 僅在 readiness summary/report，且由 canonical facts 可重算。
- [ ] 刻意移除 `profile_signals.json` 時，viewer load 應維持 `ai_system_map.json` base graph 可載入，並回傳穩定 warning / degraded state，例如 `profile_signals_missing`；不得在 load-time transient inference。

### Task 7: 記錄實際 import / scan 結果並貼到 GitHub issue

- [ ] 每次執行 direct import 或 fixture validation 後，產生一張簡潔結果表。
- [ ] 結果表可先存在本地 Markdown，例如
  `docs/work/Timmy/schedule/report/local-project-import-results-YYYY-MM-DD.md`。
- [ ] 將最新摘要用 comment 貼到本 plan 對應的 GitHub sub-issue，讓測試結果可追蹤。
- [ ] comment 不貼完整 logs，不貼 secrets，不貼過長 JSON，只貼 pass/fail/gap 與 artifact path。

建議 issue comment 格式：

```markdown
## Local Project Import Test Result

Date: YYYY-MM-DD
Plan: `14-local-project-import-and-test.md`

| Target | Mode | Commit | Scan root | Result | Profiles observed | Artifact | Notes |
|---|---|---|---|---|---|---|---|
| `zylon-ai/private-gpt` | direct | `<sha>` | `<path>` | pass/fail | `rag-grounding=detected`, `modular-composition=undetermined` | `outputs/...` | short note |
| `NirDiamant/RAG_Techniques` | fixture | `<sha>` | `<fixture>` | pass/fail | `corrective-retrieval=detected` | `outputs/...` | fixture-only |

Summary:
- Direct targets passed: X/Y
- Fixture validations passed: X/Y
- Schema validation: pass/fail
- Secret masking: pass/fail
- Read-only check: pass/fail
- Follow-up issues: #...
```

### Task 8: 驗證 Apply、Build Lineage 與 Restart Recovery

- [ ] 依 Plan `03A-implement-apply-build-lineage-and-local-json-persistence.md` 建立
  B1→Apply→B2 測試；Apply 不得再次執行 filesystem scan、UA sidecar 或 parity providers。
- [ ] 同一測試必須證明 Apply 不重跑 UA sidecar，也不重跑 parity providers；B2 只讀
  B1 `ScanSnapshot.scan_result`，不消費 `ua-analysis-result` semantic internal sidecar。
- [ ] 驗證 B1 與 B2 artifacts 都保留，B2 的 `scan_id` 與 B1 相同、`build_id` 不同，
  且 `based_on_build_id`、`applied_mapping_ids` 完整可追溯。
- [ ] 驗證 B2 的 map、profile、readiness、GraphViewModel、Markdown、Mermaid 與 static
  execution artifacts 皆使用同一 `generated_from_build_id`，沒有 B1 stale state。
- [ ] 重啟 backend 後，從 local JSON adapter 恢復 project、confirmed mappings、scan
  snapshot、B1/B2 history 與 latest=B2。
- [ ] 對同一路徑重新 import 時驗證 `project_id` reuse；不得產生讀不到舊 mappings 的
  orphan project identity。
- [ ] 另執行一次明確 `POST /api/scans`，驗證它建立新 `scan_id`；不得把 Apply 誤記成
  rescan。

---

## Acceptance Criteria

- [ ] Tier A deterministic direct targets 全部成功完成 read-only scan，且不修改外部 repo。
- [ ] Tier B 至少 2 個固定 SHA 的 bounded app targets 成功；失敗 target 必須有可重現分類與 follow-up，不得 silent pass。
- [ ] Tier C 只作 calibration，不計入 blocking success rate。
- [ ] Fixture / reference-only sources 不被計入 direct import success rate。
- [ ] registry-driven capability overlay matrix 的每個 profile 都至少有 direct app evidence 或 fixture coverage；沒有 direct app 的 profile 必須在結果表標記 coverage gap。
- [ ] 五種 AI-system fixtures 全部通過，且 workflow JSON 只作 generic fact input。
- [ ] Assessment fixtures 覆蓋五態：`detected`、`partial`、`undetermined`、
  `not_detected`、`conflicted`，並確認 `source_traceability` 是獨立 readiness finding。
- [ ] `not_detected` fixture 只有在 coverage gate 通過後才成立；未通過時必須是
  `undetermined`。
- [ ] Frontend legend 能區分五態、六種 activation state、direct / indirect /
  explicit-negative evidence，並顯示 Mapping Completeness 的公式語意。
- [ ] KAI-Mind product / viewer 不包含 Validation Simulator；DeepResearch simulator
  僅作 reference，不列入產品 acceptance。
- [ ] `ai_system_map.json`、`profile_signals.json`、`readiness_report.json`、
  `ai_system_map.md`、`system_map.mmd`、viewer payload 均符合最新 contract。
- [ ] Active output 是 v2；legacy v1 只能透過 00A adapter read-only 載入。
- [ ] 所有 outputs 與 issue comment 不揭露 unmasked secrets、absolute local paths 或過長 raw snippets。
- [ ] 產生一份簡潔測試結果表，並以 GitHub issue comment 形式貼到對應 sub-issue。
- [ ] 如果某個 repo 因 license、結構、規模或 dependency policy 不適合繼續使用，需在結果表標記 `removed` 或 `fixture-only`，不可 silently pass。
- [ ] Apply 建立 B2 時不重新掃描 repo；B1/B2 lineage、applied mappings、restart recovery
  與 explicit rescan S2 均通過 Plan 03A 的端到端驗收。
- [ ] Scan Boundary 無 proposals 時可自動進入正式 scan；有 proposals 時，在所有
  `target_path + fingerprint` decisions 完整且有效前，不得呼叫 provider scan、建立
  `ScanSnapshot`／Build、寫 artifacts 或更新 latest viewer payload。Missing/stale decision
  必須再次回 `requires_boundary_decision`。
- [ ] B1→B2 Apply 的量測證明 filesystem scan、UA sidecar 與 parity providers 總呼叫次數
  維持一次，但 component detection 會從同一 `ScanSnapshot` replay，並重新計算 normalization、assessment、static
  execution、GraphViewModel、Mapping Completeness 與 sibling artifacts；explicit rescan 則
  必須重新通過 boundary gate，建立新 `scan_id` 與新 snapshot。
- [ ] UA parity gate、UA fail-closed 行為、Apply 不重跑 UA regression 全部通過，且結果
  報告明確列為 Plan 18 的退役前置條件。

---

## Dependencies

- **Hard gate：Gate-2 必須先通過。** Plan 16 structural path、snapshot internal sidecar、
  fail-closed 與 parity harness 任一未完成時，不得開始本計畫。
- 依賴 00A compatibility gate 與 Plan 13 active v2 cutover。`12` 是 deferred
  boundary，不作為前置條件。
- 依賴 Plan 16 UA sidecar structural path；本計畫的 parity report 是 Plan 18 的 gate。
  **不依賴 Plan 17**（AssessmentOrchestrator deferred）；validation 使用 deterministic
  `ProfileInferenceService`，AI semantic candidates 維持空集合。
- 依賴穩定的 `SystemMapIndex`、`ProfileInferenceService`、`profile-signals/v1`
  sidecar lifecycle、viewer load degraded behavior、`11` 的
  `profile_registry.toml` metadata catalog，以及明確的 legacy extension
  狀態：v1 只能作 legacy read-only input，不可參與新的 profile capability flow。
- 依賴 Plan `03A-implement-apply-build-lineage-and-local-json-persistence.md` 的
  Scan/Build identity、Apply command 與 local JSON repository contract。

## Sources

- Quivr README: <https://github.com/QuivrHQ/quivr>
- PrivateGPT README: <https://github.com/zylon-ai/private-gpt>
- Langchain-Chatchat README: <https://github.com/chatchat-space/Langchain-Chatchat>
- Khoj README: <https://github.com/khoj-ai/khoj>
- Kotaemon README: <https://github.com/Cinnamon/kotaemon>
- Neo4j LLM Graph Builder README / docs: <https://github.com/neo4j-labs/llm-graph-builder>
- Onyx README: <https://github.com/onyx-dot-app/onyx>
- LightRAG README: <https://github.com/HKUDS/LightRAG>
- Microsoft GraphRAG docs: <https://microsoft.github.io/graphrag/>
- RAG-Anything README / paper: <https://github.com/HKUDS/RAG-Anything>
- Self-RAG README / paper: <https://github.com/AkariAsai/self-rag>
- RAG_Techniques README: <https://github.com/NirDiamant/RAG_Techniques>
- RAG-Fusion README: <https://github.com/Raudaschl/rag-fusion>

## P0 Execution Mapping 補充（2026-07-03）

Final validation 需要把 P0 execution map 納入驗收：

- 每個 deterministic fixture 至少驗證 `ai_system_map.json`、`call_graph.json`、
  `dataflow_hints.json`、`execution_paths.json`、`profile_signals.json`、
  `readiness_report.json` 與 Mermaid outputs 的 schema / evidence refs。
- Direct import target 至少兩個要產生非空 execution path；若 repo 架構太動態，結果可為
  `undetermined`，但必須有 limitations 與 recommended next checks。
- Workflow JSON fixture 只驗證 nodes/edges/config facts 與 JSON pointer evidence；不宣稱
  Langflow/Dify/Flowise runtime semantics。
- Scan report 必須區分 static inferred execution path 與 dynamic runtime trace；Plan 14 不把
  dynamic `01` 作為前置條件。
