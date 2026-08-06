# 16A — Q3 決策：選 Lv2（UA call graph → flow 可視化）

> 📖 **第一次看？** 先讀 [`README.md`](./README.md)（閱讀順序 + 名詞對照表）。
> **白話一句話：** 為什麼「誰呼叫誰」這份資料值得花力氣拿——因為它一份餵飽五個下游。
> **想搞懂整件事為什麼要做，從這份開始讀。**

Status: **decision recorded**（2026-07-29）— 產品／架構洞察，非正式實作 plan。
實作仍以 [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) 為主；本檔說明 **為什麼 call-graph 深度（Lv2）值得做，以及一份 UA 資料會餵飽哪些下游。**

> **對象：** Plan 16 執行者、討論「接 UA 之後能畫什麼 flow」的人
> **性質：** 決策紀錄 + 現況對照；**不**改產品碼
> **來源：** 2026-07-29 UA 整合對話 Q3（選 Lv2）
> **證據交叉驗證（寫入當日）：** `FlowDerivationService`、`rag-core-v1.json` flows、`profile_rule_definitions.py`（`rag-grounding` → `context_flow`）、static-trace README P0 artifacts

---

## 1. 決策一句話

**選 Lv2：讓 UA / Tree-sitter 的「誰呼叫誰」（帶檔案＋行號）經 Adapter 變成 `ScanFact` / `Evidence(direct)`，用同一份 call 資料同時升級 flow 邊、FlowDerivation、靜態執行產物與前端圖。**

關鍵洞察（使用者原問）：

> 「UA 知道誰呼叫誰 → 那不就可以做 flow 可視化？」→ **對，這正是關鍵洞察。**

---

## 2. 今天的資料流程圖（flow）畫到什麼程度（現況，非目標）

今日圖上的「flow（資料流程線）」，主要來自**舊模板裡寫死的假想線**——
不是從程式碼真的看到「A 呼叫了 B」而畫的。
（legacy template = 舊的參考模板 `rag-core-v1`；call edge = 有真實呼叫證據的線。）

### 2.1 模板寫死兩條線

來源：`src/systograph/core/templates/rag-core-v1.json` → `flows[]`

```text
indexing:
  data_sources → document_loader → chunking → embedding_model → vector_store

query_answer:
  app_api_or_orchestrator → query_processing → retriever → vector_store
  → prompt_builder → llm → citation_or_response_composer
  → guardrails → observability
```

（對話裡的簡稱 `loader / embedding / api / query / prompt` 對應上表正式 slot id。）

### 2.2 畫線條件與證據品質

來源：`FlowDerivationService`（docstring：**Build flow edges only when both endpoint slots are detected.**）

| 項目 | 現況行為 | 證據語意 |
|------|----------|----------|
| 畫線條件 | 模板 `slot_order` 相鄰兩格**都 detected** 才連邊 | 假設「模板順序 = 真實接線」 |
| 邊的 `evidence_ids` | 兩端 component 證據的 **聯集**（`set(from) \| set(to)`） | **猜的接線**，不是「看到 A 呼叫 B」 |
| relationship | 查硬編碼 `RELATIONSHIPS` 表；沒有則 `"connects_to"` | 模板語意，非 call-site |

```text
今天（假想線）

  template.slot_order 相鄰對
           │
           ▼
  兩端 slot 都 detected？
      │ yes
      ▼
  畫一條 Edge
  evidence = 兩端證據聯集   ← 不是 call-site evidence
```

**限制（必須寫進後續實作）：** 這仍是 static inferred / release-readiness 視角；接上 UA 後也 **不得** 宣稱 runtime proof（見 static-trace README：`runtime_verified=false`）。

### 2.3 實證數據（2026-07-29 兩輪查核，`uv run python` 全管線）

以下數字取代本檔早期版本的定性描述（「常只是成對的點」），實作時以此為準：

| 量測 | 結果 |
|------|------|
| `FlowDerivationService` 關係名總數 | **12**（`connects_to` fallback 因模板相鄰 pair 全有明確 key 而**永不可達**，是死碼） |
| 13 張卡要求的關係名 ∩ 上述 12 個 | **空集合** |
| 12 個真實 fixture 端到端的關係名聯集 | **只有 2 種**：`queries_vector_store`、`stores_vectors` |
| 15 張卡達到 `detected` 的數量 | **0**（`basic_qdrant_ollama_rag` 僅 `rag-grounding` / `hierarchical-retrieval` 為 partial） |
| canonical edge 的產生來源 | **只有 `FlowDerivationService` 一處**（proposal `suggested_edges` 驗完即丟、detail scan 只 merge evidence、`workflow_edge` ScanFact 無消費者） |

**對 Plan 16 的意涵**：UA 之前，關係邊的字彙是一個**封閉且與 profile 契約
不相交**的 12 元集合。因此「讓卡片變綠」不可能靠現有管線調參達成——UA 的
call hints 是唯一能同時提供**新語意**與**真實 call-site 證據**的來源。

### 2.4 ⚠️ 前置條件：端點約束（Plan 13.8 Task 1）

查核發現 `_relationship_evidence()`（`profile_finding_assembler.py:196-205`）
**只用關係名查邊，完全不驗邊的 source/target 是否落在該卡的
`required_node_ids` 上**。實證：把 `rerank` 別名到 `queries_vector_store`
（一條語意無關的 `retriever → vector_store` 邊）即可讓 reranking 卡翻成
`detected`。

**這對 UA 是硬前置**：UA 開始產生新關係名的邊之後，若端點約束仍缺席，
任何一條同名邊（不論接在哪兩個元件之間）都會點亮卡片——假陽性風險比今天
更高，因為 UA 產出的邊數量級遠大於現在的 12 條。Plan 13.8 Task 1 必須先落地。

---

## 3. 接上 UA 呼叫關係圖（call graph）之後：一份資料餵飽五張嘴

```text
        UA / Tree-sitter：誰呼叫誰（帶檔案＋行號）
                        │
            Adapter → ScanFact / Evidence（direct！）
                        │
     ┌──────────────────┼──────────────────┐
     ▼                  ▼                  ▼
① context_flow 邊     ② FlowDerivation 升級   ③ 靜態執行產物變真
   （G5c 的解）          假想線 → 真實接線        call_graph.json
   rag-grounding                                  execution_paths.json
   終於可達 🟢                                    （現在常只是成對的點）
                                                  execution_map.mmd 變真圖
     ▼
④ 前端直接受益：SystemGraph 的邊、Flow filter、
   execution 圖——契約都在了，不用改前端
     ▼
⑤ 「flow 可視化」= ② + ③ + ④ 的自然結果
```

### 3.1 五個消費者（對照表）

| # | 消費者 | 今天痛點 | UA call graph 帶來什麼 | 相關錨點 |
|---|--------|----------|------------------------|----------|
| ① | `context_flow` 等 relationship 邊 | `rag-grounding` 要求 `dense_retriever` + `llm_answerer` **且** `required_relationship = "context_flow"`；沒有真 wiring 時 profile 難到 `detected` | call-site → **direct** evidence 的 `context_flow` 邊 → G5c／rag-grounding 路徑可達 | `profile_rule_definitions.py` |
| ② | `FlowDerivationService` | 模板相鄰 + 兩端 detected → 假想線 | 有 call 證據才連／優先連；假想線降級或標 `static_inferred` 來源 | Plan 16 adapter 之後的 Step 4 consumer 升級（後續 task，非 16 本體必做完） |
| ③ | Static execution siblings | `call_graph.json` / `execution_paths.json` / `execution_map.mmd` 在缺 call 事實時偏「成對的點」 | 真 call edge → 路徑與 Mermaid 變「真圖」（仍標 static-only） | Track-C `dynamic/00`、`StaticExecutionArtifactService` |
| ④ | Frontend Viewer | 契約已有邊 / Flow filter / execution 圖 | **資料變真，契約不必改** | `GraphViewModel` / SystemGraph |
| ⑤ | 「flow 可視化」產品敘事 | 看起來像 flow，其實是模板假設 | ②+③+④ 自然結果；不必另開前端專案 | 本決策的 why |

### 3.2 與 Plan 16 的邊界

| 在 Plan 16 內 | 不在 Plan 16 一次做完（後續） |
|---------------|-------------------------------|
| Sidecar structural path（import / structure / **call hints**） | FlowDerivation 從「模板假想」改「call 優先」的完整行為切換 → **[`16C`](./16C-component-attribution-and-edge-derivation.md) + [`16D`](./16D-call-priority-consumer-cutover.md)** |
| `UaStructuralAdapter` → `ScanFact` / `Evidence(direct)`，含穩定 `rule_id`（如 `ua_call_hint_*`） | Profile / readiness 文案與 G5c 專案收斂 → **[`16D`](./16D-call-priority-consumer-cutover.md) Task 5** |
| Parity、fail-closed、不寫 target repo | Frontend 視覺 polish（契約不變則可不改） → **[`16D`](./16D-call-priority-consumer-cutover.md) Task 6** |

分工速記：

- **16C** = 怎麼把 call/import 編成元件層邊（L1/L2），並把模板邊降成 L3 `undetermined`
- **16D** = materialization／static execution／profile **正式以 call 邊為主**（完整消費者切換）

**Lv2 的意思（本決策語境）：** 不只用 UA 補強「有哪些元件」，而是把 **call graph 當一等公民**，讓 flow／execution／relationship 共用同一批 direct evidence。

---

## 4. 為什麼這比「只接 structure 做 component detection」賺更多

```text
Lv（對話語境，非正式版本號）

  若只停在「多抓一點 symbols / imports」
       → 元件格子更滿
       → flow 仍可能是模板假想線（②③幾乎不升級）

  選 Lv2（本決策）
       → 同一 Adapter 輸出 call 事實
       → ①②③④⑤ 一起變好
       → 前端契約已就緒 → ROI 集中在 backend adapter + derivation
```

一句話：**call graph 是槓桿點；flow 可視化是槓桿結果，不是另起一個前端功能。**

---

## 5. 必須守住的契約／安全邊界

與 Plan 16、`ref-opensource/systograph-understand-anything-integration-boundary.md`、static-trace README 一致：

1. **Adapter 必經之路**：UA 輸出不得直接當 `ai_system_map.json`；必須變成 Systograph `ScanFact` / `Evidence`。
2. **direct evidence 語意**：只有「真的看到 call／wiring」才能標 `evidence_kind=direct`；不得把兩端證據聯集假裝成 call-site。
3. **仍是 static inferred**：`runtime_verified=false`；不得在 UI／報告宣稱 runtime proof。
4. **不跑 UA semantic / knowledge-graph.json canonical**：Phase2 structural only。
5. **不改 frontend contract 欄位**：④ 的前提是既有 Graph／Flow／execution 契約已足夠。
6. **Apply 不重跑 UA**：重放同一 `scan_id` 的 `scan_result`。

---

## 6. 建議的後續落地順序（給執行者；落地 = 實際做出來）

1. **Plan 16**：sidecar + adapter 先把 `ua_call_hint_*`（或等價 call facts）穩定進 `scan_result`。
2. **[`16C`](./16C-component-attribution-and-edge-derivation.md)**：residence + L1/L2/L3 邊推導；模板邊標 `undetermined`。
3. **[`16D`](./16D-call-priority-consumer-cutover.md)**：materialization call 優先、static execution 同源、profile/G5c、可選關 L3、viewer 煙測。
4. （可選）Frontend 虛線 polish — 見 16D Task 6。

Gate 仍以 static-trace README 為準：Gate-1 後才開 Plan 16；Gate-2 要 structural + fail-closed + parity；16C/16D 在 Gate-2 之後。

---

## 7. 已知缺口／勿過度解讀

| 項目 | 狀態 |
|------|------|
| 對話中的「G5c」完整 finding 編號 | 本檔當 **rag-grounding / `context_flow` 缺口** 的別名使用；已正式化為 [`../../../../finish/s1-v2-cutover/13.8.md`](../../../../finish/s1-v2-cutover/13.8.md) |
| Lv1 / Lv3 完整定義 | 未完整寫入本檔；**已拍板的是選 Lv2（call graph 槓桿）** |
| 今日 `execution_paths`「只有成對的點」 | **已量化**，見 §2.3；實作時仍以具體 artifact 對照為準 |
| FlowDerivation 是否在 v2 materialization 路徑仍為 primary | **已確認為 primary 且是唯一 canonical edge 來源**（`system_map_v2_materialization_service.py:124` → `system_map_v2_normalize_service.py:136-158`），見 §2.3 |

## 7.1 相依計畫（2026-07-29 新增）

UA 落地前必須完成的兩份前置計畫，否則 UA 的成果無法在 52 格／15 張卡上顯現：

| 計畫 | 為什麼是 UA 的前置 |
|------|--------------------|
| [`../../../../finish/s1-v2-cutover/13.7.md`](../../../../finish/s1-v2-cutover/13.7.md) | UA 只替換 fact 來源；元件仍以 bridge kind 字彙表示，若 `_TYPE_TO_NODES` 未補齊，UA 掃得再準 52 格照樣點不亮（實測今天 4/52，拆 legacy 表後 1/52） |
| [`../../../../finish/s1-v2-cutover/13.8.md`](../../../../finish/s1-v2-cutover/13.8.md) | 端點約束缺口；UA 產出的邊數量級遠大於現有 12 條，無約束時假陽性風險放大（見 §2.4） |

## 7.2 給 Plan 16 的驗收輸入：12 張卡的關係語意需求

13.8 附錄裁定表列出，除 `rag-grounding`（純命名不一致，13.8 以 alias 過渡
處理）與 `agentic-control` / `memory`（無 relationship gate）之外，其餘 12 張
卡都需要 **UA call hints 才能提供語意相符的邊**。UA adapter 設計時應確認
call hints 能表達下列語意（不必一次全做，但要能逐步覆蓋）：

| profile_id | 需要的關係語意 | UA call hint 應能證明什麼 |
|---|---|---|
| tool-calling | `tool_call` | agent loop 呼叫了工具函式／工具註冊表 |
| workflow-orchestration | `workflow_transition` | orchestrator 節點之間的狀態轉移呼叫 |
| hybrid-retrieval | `retrieval_fusion` | 兩種以上 retriever 的結果被合併／加權 |
| reranking | `rerank` | retriever 結果流入 rerank 函式後才進下游 |
| corrective-retrieval | `fallback_route` | 檢查失敗後走另一條檢索分支 |
| self-reflection | `self_critique` | 生成結果回饋進同一 agent loop 再評估 |
| graph-retrieval | `graph_retrieval` | 圖查詢 API 的呼叫進入檢索路徑 |
| hierarchical-retrieval | `hierarchical_flow` | 索引層級之間的父子檢索呼叫 |
| contextual-retrieval | `context_enrichment` | metadata 抽取結果併入 context 組裝 |
| multimodal-grounding | `multimodal_retrieval` | 非文字模態的檢索呼叫 |
| modular-composition | `component_selection` | orchestrator 依條件選擇不同元件 |
| multi-query-retrieval | `query_route` | query 分類結果決定走哪條檢索路徑 |

**注意**：這些關係名是 profile 契約既有的字串（`profile_rule_definitions.py`），
UA 端不得自創同義新名——否則又製造一次字彙漂移（同 G5 的病因）。新增關係名
必須同時更新 profile 規則或 13.8 的 alias 表。

---

## 8. 相關檔案

| 檔案 | 角色 |
|------|------|
| [`16-implement-understand-anything-sidecar-service.md`](./16-implement-understand-anything-sidecar-service.md) | S2 實作主 plan |
| `ref-opensource/systograph-understand-anything-integration-boundary.md` | UA 整合邊界（Accepted） |
| `../README.md` | Stage / Gate / artifact 對照 |
| `src/systograph/core/services/flow_derivation_service.py` | 今日假想線實作 |
| `src/systograph/core/templates/rag-core-v1.json` | indexing / query_answer 模板 |
| `src/systograph/core/services/profile_rule_definitions.py` | `rag-grounding` ↔ `context_flow` |
| `src/systograph/core/services/static_execution_artifact_service.py` | call_graph / execution_paths / mermaid |
