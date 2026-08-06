# 投影平面改由 canonical type 推導（退役 slot→layer 查表）實作計畫

Status: **done**（2026-08-07 完成，commit `PLACEHOLDER_COMMIT`；2026-08-06 起草；
GitHub issue #277。**與 UA 零相依，可在 s2-ua-integration 之前執行**——這是
「slot 殘餘職責」中目前唯一能先做的一項；有計畫承接的另一項（模板假邊）屬
16C→16D→16G 鏈，留在 s2-ua-integration，見下方「與 16G 的邊界」）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** #277（umbrella：Web 邊界收斂後端先行，2026-08-07 回填）

**Goal:** 讓 repo component 的 `layer`（投影時的 `plane_id`）由
`canonical_type → capability node → node 所屬 plane` 推導，取代現行的
`slot → SLOT_LAYER_BY_ID` 查表。完成後，slot 誤填不再造成「畫錯帶」，
投影與評估共用同一條 type-driven 語意鏈。

**Architecture:** 純 backend 語意變更 + 前端視覺驗證。輸出契約不變
（`components[].layer` 與 `GraphViewModel.plane_id` 欄位與值域照舊——值域
本來就是 canonical plane id），變的只有**每個元件落在哪個值**。不新增
mapping 表：推導鏈全部用既有資料（`capability_type_node_map.toml` +
52-node catalog 的 per-node plane）。

**Tech Stack:** Python 3.11、pytest、既有 TOML loaders、Playwright MCP
（前端 before/after 視覺驗證）。

---

## 與 16G 的邊界（為什麼 16G 不搬進 refactor）

「slot 殘餘職責」目前只有兩項有實作計畫承接（其餘見文末索引）：

| 殘餘 | 歸屬 | 為什麼 |
|---|---|---|
| **投影平面**（slot→layer→plane） | **本計畫**，UA 零相依 | 推導鏈只需要 13.7 已交付的 type→node 表 + catalog 的 per-node plane |
| **模板假邊**（flows 相鄰） | **16G**，留在 s2-ua-integration | 16G 硬前置 16C（L1/L2 真邊）與 16D（呼叫優先 cutover）；沒有真邊之前刪假邊，圖上一條邊都不剩（16G 自述）。整條鏈本質是 UA 工作，不可先於 Plan 16 |

依使用者工作順序（refactor 全部完成 → 才開始 s2-ua-integration），把 16G
搬進 refactor 會使它先於自己的硬前置執行，屬依賴倒置——**不搬**。

## Source（判準基線，2026-08-06 對程式碼查核，均有行號證據）

- 現行寫入：`system_map_v2_normalize_service.py:121`
  `layer=SLOT_LAYER_BY_ID.get(slot.slot, "undetermined")`；`:120`
  `canonical_type=instance.kind`。
- 現行投影：`graph_projection_service.py:186` `plane_id=component.layer`
  （`:193` subtitle 同源）。
- 評估已是 type-driven：`reference_capability_assessment_service.py:107`
  `self._type_to_nodes.get(component.canonical_type, ())`——投影平面是最後
  一個還掛在 slot 上的主開關。
- catalog 具備 per-node plane：`reference_capability_assessment_service.py`
  `_assessment(node_id, plane_id, ...)` 簽名即證明（plane 由 catalog 提供）。
- `SLOT_LAYER_BY_ID`（`legacy_slot_layer_map.py:19-33`）有兩個消費者：
  active v2 normalize（本計畫切走）與 v1→v2 adapter（migration-only，留）。
- 多對一收斂實例：`vector_db` / `vector_store` / `http_vector_store` /
  `local_persistent_vector_store` / `vector_db_config` 五個 type 全部 →
  `index_builder` 節點——type 詞彙比 52 格細，映射是收斂式的。

## 範圍外

- **模板邊退役**（16G）與任何 UA 相關工作。
- **`metadata.legacy_slot` 的移除**——它另有消費者（graph projection 的
  node id slug 與 node／endpoint `slot` 標籤、detail scan 的
  `component_slot` target、query trace），退場受 16 系列（13-slot
  keyspace）與 public 契約（detail-scan `component_slot`）阻擋，目前
  無人認領。本計畫**不動**這個欄位。
- **Mapping UI 從選 slot 改選 capability**（產品層決策，另案）。

---

## Task 0: 裁定兩條推導規則（**先拍板再動工**）

**(a) 多 node 型別的主平面**：type 可對到多個 node（如
`api_input = ["user_input", "api_server"]`），節點可能跨 plane。

- [x] **Step 1: 採「陣列第一個 node = primary」的確定性慣例**，並把慣例
  寫進 `capability_type_node_map.toml` 檔頭註解（維護者排序時即決定主平面）；
  或改折衷方案（TOML 加 primary 欄）——擇一並記錄理由

  **裁定：採「陣列第一個 node = primary」，不加 TOML 欄位、不改 schema。**
  理由：(1) 這是最簡方案——推導鏈不新增任何資料欄位，維護者排序即決策；
  (2) 加 `primary` 欄會讓同一件事有兩個真相源（陣列順序 vs. 欄位），
  兩者不一致時沒有裁決規則；(3) loader 的 fail-closed 驗證已保證陣列
  非空且每個 node id ∈ 52-node catalog，`[0]` 恆存在。慣例已寫進
  `capability_type_node_map.toml` 檔頭（英文，明示 `ARRAY ORDER IS
  SEMANTIC: the first node decides the projection plane`），並在
  `MODEL-CONTRACT.md` §5.1.1 與 `canonical_type_plane_map.py` 檔頭複述。
  代價（已在「風險」節記錄）：重排陣列＝改畫面，review 時視為 P2 檢查點。

**(b) 對不到表的 type 的 fallback**：`canonical_type` 不在表裡時
（manual mapping 的 `component_kind` 是自由文字，可能產生任意 kind）。

- [x] **Step 2: fallback = `"undetermined"`**（與現行 slot 查表的 fallback
  同語意），**不得**退回 slot 查表——那會把 slot 依賴從後門帶回來

  **裁定：fallback = `"undetermined"`，零 slot 後路。** 實作上
  `CanonicalTypePlaneResolver` 只認得 `canonical_type`，連 slot 參數都
  不接收，結構上不可能退回 slot 查表。`system_map_v2_normalize_service.py`
  對 `SLOT_LAYER_BY_ID` 的 import 已移除，並由
  `test_legacy_slot_layer_map.py::test_active_v2_path_no_longer_imports_the_slot_layer_map`
  鎖住。

- [x] **Step 3: 覆蓋審計**——枚舉 bridge 全部 kind 值與既有 mappings 的
  `component_kind`，比對 TOML key 空間；缺列的補進 TOML（純詞彙擴充，
  不改程式），避免切換當下一批元件掉進 undetermined

  **審計結果：TOML 零缺列，未新增任何一列。**

  | 來源 | 枚舉出的 `component_kind` | 在 TOML？ |
  |---|---|---|
  | `COMPONENT_BRIDGE_RULES` 全部 `candidates[].kind` | `vector_db`, `http_vector_store`, `local_persistent_vector_store`, `local_llm_runtime`, `external_llm_provider`, `embedding_provider`, `api_route`, `retriever`, `prompt_template` | 9/9 ✅ |
  | bridge config 路徑（`_config_candidates` → `_vector_store_candidates` / `_llm_candidates` / `_openai_config_candidates`） | `vector_db_config`（另 3 個與 rules 重複） | 1/1 ✅ |
  | 既有測試／fixtures 出現的 `canonical_type` / `component_kind` | `api_input`, `llm`, `retriever`, `workflow_node`, `tool`, `agent_loop`, `vector_store`, `vector_retriever`, `vector_db`, `reranker` | 10/10 ✅ |
  | v1 adapter 專屬 | `slot_placeholder`, `legacy_extension` | 不適用（migration-only 路徑不走本 helper） |

  唯一**刻意不列**的值：`manual_mapping_materializer.py` 在 manual mapping
  既沒有 `component_kind` 也沒有 `observed_kind` 時填的字面值
  `"manual_mapping"`。它不對應任何 capability，硬塞一個 node 才是錯的；
  讓它落 `undetermined` 帶正是「顯性化而非錯置」的預期行為，已由
  `test_component_layer_is_undetermined_for_an_unlisted_type` 鎖住。

  審計本身也寫成常駐測試：`test_canonical_type_plane_map.py::
  test_every_bridge_component_kind_resolves_to_a_real_plane` 掃
  `COMPONENT_BRIDGE_RULES` ＋ config 路徑 kind 清單，任何一個掉進
  `undetermined` 就紅燈，之後新增 bridge rule 也擋得住。

  端到端驗證：12 個 fixture 專案全跑 build，15 個元件**沒有任何一個**
  落在 `undetermined`（見 Task 3 對照表）。

## Task 1: 實作 type→plane 推導

**Files:**
- Modify: `src/systograph/core/services/system_map_v2_normalize_service.py`
- Create or extend: type→plane helper（建議放在
  `capability_type_node_map_loader.py` 旁，複用同一份載入與驗證）

- [x] **Step 1: helper：`canonical_type → primary node → node.plane_id`**，
  查無 type 回 `"undetermined"`

  **落點：新檔 `src/systograph/core/services/canonical_type_plane_map.py`
  （`CanonicalTypePlaneResolver`），與 `capability_type_node_map_loader.py`
  同層。** 選「新檔組合兩個 loader」而不是「擴充 loader 加
  `plane_for_type()`」的理由：loader 的既有責任是「讀 TOML ＋ fail-closed
  驗證 node id ∈ catalog」，塞進 plane 推導會讓它同時扛「載入」與「投影
  語意」兩件事，而且 plane 資料其實來自另一個 loader
  （`capability_reference_map_loader`）——擴充等於讓 A loader 內含 B
  loader 的知識。新檔只做 join，零自有對照表，組合方式與
  `ReferenceCapabilityAssessmentService`（同樣同時持有 catalog 與
  type→node map）一致。額外加一道 fail-closed：catalog 的 `plane_id`
  必須 ∈ `CanonicalLayer` literal，否則建構時就炸，不會流出不合約的
  `layer` 值。

- [x] **Step 2: `system_map_v2_normalize_service.py:121` 改用 helper**，
  輸入從 `slot.slot` 換成 `instance.kind`（即 canonical_type）
  → `layer=self._plane_resolver.plane_for(instance.kind)`；
  `_components` 由 `@staticmethod` 改為 instance method，resolver 走
  constructor 注入（`plane_resolver: CanonicalTypePlaneResolver | None`），
  維持可測試性與既有 `SystemMapV2NormalizeService()` 零參數呼叫點不變。
- [x] **Step 3: 移除該檔對 `SLOT_LAYER_BY_ID` 的 import**
- [x] **Step 4: `legacy_slot_layer_map.py` 檔頭更新**——它從「雙消費者」
  降為 migration-only（v1 adapter 專用）；順手修正檔頭第 6 行「新的 v2
  元件不應該擴充這張表」的過時語境（現在是真的不會再被 v2 讀到）
  → 改寫為「這張表已凍結在 13 個 legacy slot，不再擴充；新的 canonical
  type 要落哪一帶，改 `capability_type_node_map.toml`」，呼叫鏈段落也
  縮成唯一消費者 `system_map_v1_to_v2_adapter._layer_for_slot()`。

## Task 2: 測試

- [x] **Step 1: helper 單元測試**——單 node、多 node（取 primary）、
  查無 type（undetermined）、TOML 缺列審計案例

  新檔 `tests/unit/core/test_canonical_type_plane_map.py`（5 個 BDD 測試）：
  單 node（`retriever`/`vector_db`/`prompt_template`）、多 node 取 primary
  （`api_input`→`input_intent` 而非 `deployment_topology`、`agent_loop`、
  `tool`）、查無 type（`manual_mapping` / `totally_unknown_kind`）、
  bridge kind 覆蓋審計、catalog plane 越界 fail-closed。

- [x] **Step 2: 關鍵 regression：「slot 誤填不再影響平面」**——構造
  slot 錯、`canonical_type` 對的元件，斷言 plane 正確（這是本計畫的
  行為承諾，也是與現況的可觀察差異）

  `test_system_map_v2_normalize_service.py` 加 3 個測試，**切換前全紅**：

  | 測試 | slot | canonical_type | BASE（紅） | HEAD（綠） |
  |---|---|---|---|---|
  | `test_component_layer_follows_canonical_type_not_a_wrong_slot` | `llm` | `vector_db` | `generation` | `ingestion_indexing` |
  | `test_component_layer_ignores_a_wrong_slot_in_both_directions` | `vector_store` | `prompt_template` | `retrieval` | `generation` |
  | `test_component_layer_is_undetermined_for_an_unlisted_type` | `llm` | `manual_mapping` | `generation` | `undetermined` |

- [x] **Step 3: 更新受影響的 normalize / projection 既有測試與 fixtures**；
  其中 `tests/unit/core/test_legacy_slot_layer_map.py:7-10` 的
  `CONSUMER_MODULES` 斷言「v1 adapter 與 v2 normalize 綁同一份 dict」，
  Task 1 Step 3 移除 import 後必然失敗，需縮成只剩 v1 adapter

  `CONSUMER_MODULES` 已縮成只剩 v1 adapter，並**加一條反向斷言**
  `test_active_v2_path_no_longer_imports_the_slot_layer_map`——把「v2
  normalize 不得再綁這份 dict」變成常駐 guard，而不是靜靜地少一個
  module name。**其餘既有 normalize / projection 測試與 fixtures 零改動**：
  查核後沒有任何既有測試在 pin「由真實掃描產生的 `layer` 值」
  （`tests/fixtures/ai_system_map/**` 是靜態輸入 fixture，不由 normalize
  重新產生；`test_graph_projection_service.py` / `test_detail_scan_service.py`
  的 `layer=` 是手寫 CanonicalComponent 輸入，不經 helper）。

- [x] **Step 4: v1 adapter 的 layer 輸出不動**——`SLOT_LAYER_BY_ID` 在
  migration 路徑產出的 layer 值由既有測試鎖住，不得跟著改
  → `system_map_v1_to_v2_adapter.py` 一行未改，
  `test_system_map_v1_to_v2_adapter.py` 全綠且未修改。

## Task 3: 前端視覺驗證（不改前端程式碼）

plane 值域不變，前端 zod 與元件無需修改；但**元件實際落帶會移動**，
需人眼確認新佈局合理。

- [x] **Step 1: 以 fixture 專案（如 `basic_qdrant_ollama_rag`）跑
  before/after，用 Playwright MCP 截圖比對**

  **(i) 決定性紀錄**：在 BASE(`829fd75`) 與 HEAD 各跑一次
  `MapBuildService.build`，涵蓋 **12 個 fixture 專案全部**（不只計畫
  點名的兩個），diff `components[].layer` 與 `GraphViewModel.plane_id`。
  結果：**15 個元件，7 個移帶，0 個掉進 `undetermined`**。

  **(ii) Playwright MCP 視覺比對**：backend uvicorn ＋
  `frontend pnpm dev` 起服務，viewer 以 API 模式跑同一個
  `basic_qdrant_ollama_rag`，BASE / HEAD 各截圖一輪，實際看到帶位移動
  （見下表「畫面驗證」欄）。前端 `POST /api/scans` 不帶
  `preflight_request_id` 會 422（既有前端缺口，不屬本計畫範圍），
  截圖時在瀏覽器端裝了一個只補 preflight 的 `window.fetch` shim 當
  測試治具；**產品程式碼與前端零改動**。

- [x] **Step 2: 逐一確認移動的元件「新帶位」與其 capability 歸屬一致**

  **元件 × before帶 × after帶 × 對應 capability node 對照表**

  | fixture | 元件 | `canonical_type` | legacy slot | before 帶 | after 帶 | primary node | 一致？ |
  |---|---|---|---|---|---|---|---|
  | basic_qdrant_ollama_rag | `component:app_api_or_orchestrator:application_api` | `api_route` | `app_api_or_orchestrator` | `control` | **`deployment_topology`** | `api_server` | ✅ |
  | healthcare_rag_minimal | 同上 | `api_route` | 同上 | `control` | **`deployment_topology`** | `api_server` | ✅ |
  | missing_slots_rag | 同上 | `api_route` | 同上 | `control` | **`deployment_topology`** | `api_server` | ✅ |
  | openai_external_provider_rag | 同上 | `api_route` | 同上 | `control` | **`deployment_topology`** | `api_server` | ✅ |
  | basic_qdrant_ollama_rag | `component:vector_store:qdrant` | `vector_db` | `vector_store` | `retrieval` | **`ingestion_indexing`** | `index_builder` | ✅ |
  | pgvector_openai_rag | `component:vector_store:pgvector` | `vector_db` | `vector_store` | `retrieval` | **`ingestion_indexing`** | `index_builder` | ✅ |
  | graph_rag_extension_rag | `component:vector_store:qdrant` | `vector_db_config` | `vector_store` | `retrieval` | **`ingestion_indexing`** | `index_builder` | ✅ |
  | （其餘 8 個元件） | `local_llm_runtime` / `external_llm_provider` / `retriever` / `embedding_provider` | — | — | 不變 | 不變 | `llm_answerer` / `dense_retriever` / `embedder` | ✅ |

  **逐列判讀（為什麼新帶位是對的）：**

  - **`vector_db` / `vector_db_config`：retrieval → ingestion_indexing。**
    這三個 type 全部指向 `index_builder` 節點，而 `index_builder` 在
    catalog 屬 ingestion/indexing plane。舊行為是「slot 叫 `vector_store`
    ⇒ 畫在 retrieval」，但 Qdrant/pgvector 這類元件在 52 格語意裡是
    **索引建置**（`index_builder`），檢索能力另有 `dense_retriever`
    等節點承接。畫面驗證：Qdrant 卡片現在直接落在 `Index Builder`
    reference node 旁邊（同一帶），retrieval 帶留下的是
    `Retriever`（`retriever` → `dense_retriever`），語意更乾淨。
  - **`api_route`：control → deployment_topology。** `api_route` 指向
    `api_server`，catalog 把 `api_server` 放在 deployment/topology plane
    （control plane 是 planner / router / agent_loop / orchestrator /
    stop_policy / human_approval_gate 這類**推理與控制**能力）。
    舊 slot 名 `app_api_or_orchestrator` 把「API 服務面」與「編排器」
    混成一格，這正是本計畫要退役的 slot 詞彙不精確；FastAPI/Flask
    route 是 API 服務邊界，不是 orchestrator。畫面驗證：Application API
    卡片現在落在 `API Server` reference node 正下方（該節點本身也是
    detected/enabled），對位關係一眼可見。
  - **未移動的 8 個元件**：`local_llm_runtime` / `external_llm_provider`
    → `llm_answerer` → generation（與舊 slot `llm` 同帶）；`retriever`
    → `dense_retriever` → retrieval；`embedding_provider` → `embedder`
    → ingestion_indexing。舊 slot 查表本來就與 capability 歸屬吻合，
    所以無變化——這也是「只有錯的會動」的佐證。

  **畫面驗證（Playwright，`basic_qdrant_ollama_rag`）：**

  | 帶 | BASE 節點數 | BASE 內容 | HEAD 節點數 | HEAD 內容 |
  |---|--:|---|--:|---|
  | 02 Control | 7 | 6 reference ＋ **Application API** | 6 | 只剩 6 reference |
  | 03 Ingestion & Indexing | 6 | 6 reference | 7 | 6 reference ＋ **Qdrant** |
  | 04 Retrieval | 8 | 6 reference ＋ Retriever ＋ **Qdrant** | 7 | 6 reference ＋ Retriever |
  | 10 Deployment Topology | 6 | 6 reference | 7 | 6 reference ＋ **Application API** |

  側欄 lens 計數同步變動：Agent Control 10→9、Ingestion & Indexing 6→7、
  Topology 6→7；`Normalized nodes` 恆為 61、`Mapping completeness` 恆為
  6.7%（只是換帶，不是增刪元件，也不影響 Step 6 評估）。

- [x] **Step 3: 差異記錄進 PR 描述**（哪些元件從哪帶移到哪帶、為什麼）
  → 上兩張表即 PR 描述素材。

## Task 4: 順手清理（小而獨立，可拆單獨 commit）

- [x] **Step 1: `risk_hint_rules.toml:61` 使用者可見文案去除 "rag-core-v1"
  字樣**（「Required rag-core-v1 slot was not detected...」→ 中性措辭）；
  對應測試同步

  → `"Required core slot was not detected in the available evidence."`
  （保留 "slot" 一字，因為 `RiskHintService` 會接上
  `Missing slot: '<slot>'` 後綴，兩段措辭需一致）。
  對應測試無需同步：`test_risk_hint_service.py` 用自帶的 minimal catalog
  文字，沒有 pin 生產 TOML 的 rationale 字串。
  `tests/fixtures/ai_system_map/*.v1.json` 裡的舊字串**刻意不動**——那是
  legacy v1 map 的歷史內容（migration 輸入 fixture），改掉等於竄改歷史
  證據，且不是使用者可見的新產出。

## Task 5: 契約文件

- [x] **Step 1: `docs/MODEL-CONTRACT.md` 中若有描述 layer/plane 來源為
  slot 查表的敘述，更新為 type→node→plane 推導**（執行時 grep `layer` /
  `SLOT_LAYER_BY_ID` / `plane` 相關段落確認）

  grep 結果：MODEL-CONTRACT 原本**完全沒有**描述 `layer` 的來源，只在
  §5.1 欄位表列過欄位名（`SLOT_LAYER_BY_ID` 全文零出現）——也就是說
  舊敘述不是「錯的」而是「缺的」。新增 **§5.1.1「`components[].layer`
  的來源（type-driven，非 slot）」**：推導鏈圖、值域、primary node 慣例、
  fallback 規則、slot 的殘餘角色、`SLOT_LAYER_BY_ID` 降為 migration-only，
  並在 §5.1 欄位表的 `components[]` 那列加指向 §5.1.1 的連結。

- [x] **Step 2: 檔頭呼叫鏈註解**——`legacy_slot_layer_map.py`（Task 1
  Step 4 已含）；`system_map_v2_normalize_service.py` 目前**沒有**檔頭註解
  （第 1 行即 import），依 CLAUDE.md 慣例補上責任／呼叫鏈並寫明 layer 來源
  → 已補（「這個檔案負責 / layer 來源 / 呼叫鏈」三段，中文欄位名格式比照
  `map_build_service.py` 等既有 service 檔）。新檔
  `canonical_type_plane_map.py` 亦帶完整 docstring（責任／組合理由／
  primary-node 慣例／呼叫鏈）。

---

## 驗收標準（2026-08-07 全數達成）

1. ✅ `components[].layer` / `GraphViewModel.plane_id` 值域不變（仍為
   canonical plane id），前端無需改動即可渲染
   → 前端零改動，`pnpm test` 160 passed 不變；Playwright 實測渲染正常。
2. ✅ slot 誤填不再影響平面（Task 2 Step 2 的 regression 鎖住）
   → 3 條 regression 切換前紅、切換後綠。
3. ✅ `SLOT_LAYER_BY_ID` 在 active v2 路徑零 import；v1 adapter
   （migration）行為不變 → 反向 guard 測試鎖住；v1 adapter 一行未改。
4. ✅ Task 0 Step 3 的覆蓋審計完成：切換後 fixture 專案無元件因「type
   缺列」掉進 undetermined → 12 fixture / 15 元件，undetermined = 0。
5. ✅ 視覺 before/after 已比對並記錄（Task 3 兩張表）；使用者可見文案無
   "rag-core-v1" 字樣。
6. ✅ `uv run pytest`（**1133 passed, 1 skipped**；BASE 1124 ＋ 9 新測試，
   coverage 90.78% ≥ 85% gate）、`ruff check` / `ruff format --check`
   （340 files clean）、`mypy src tests`（326 files, no issues）、
   `pnpm test`（35 files / 160 tests passed）全綠。

## 風險

- **畫面佈局移動**：這是預期行為不是 bug，但對熟悉舊佈局的使用者是視覺
  變化；以 Task 3 的記錄與 PR 說明對沖。
- **多 node 主平面慣例**：一旦採「第一個 node = primary」，TOML 陣列順序
  就變成語意（重排即改畫面）；檔頭必須寫明，review 時視為 P2 檢查點。
- **自由文字 kind 掉 undetermined**：manual mapping 可寫任意
  `component_kind`；Task 0 Step 3 的審計 + fallback 讓它可見（undetermined
  帶）而非錯置，屬可接受的顯性化。

## 完成後 slot 還剩什麼（供後續追蹤）

本計畫完成後，slot 的殘餘職責只剩：`metadata.legacy_slot` 標籤、模板假邊
（16G）、manual mapping 的 `target_slot` 白名單與 `available_slots`、
`recommended_next_check_service` 的硬編碼 slot 名單，以及 13-slot 偵測
keyspace 本身。**slot 對投影平面已無任何影響**（graph node id 的 slug
與 `GraphNodeModel.slot` 仍取自 `metadata.legacy_slot`）——已於 2026-08-07
達成。

**留給後續的觀察點（本計畫刻意不處理）：**

- `ComponentInstance.id` 仍是 `component:<slot>:<slug(name)>`，所以
  slot 誤填**還是會**污染 component id 與 graph node id 的 slug——只是
  不再污染帶位。id 詞彙退場屬 16 系列（13-slot keyspace）。
- `RiskHintService` 的 `missing_required_slot` 仍以 13 slot 為 keyspace，
  文案已中性化但語意仍是 slot 覆蓋率，非 52 格 capability 覆蓋率。

完整歸屬與各項可否動工，見
[`RAG-CORE-V1-RETIREMENT-INDEX.md`](./RAG-CORE-V1-RETIREMENT-INDEX.md)
——注意其中 **C1 / C3b / C4 / C5 / C7 目前無人認領**（本計畫涵蓋 C3a 與 C6）。
