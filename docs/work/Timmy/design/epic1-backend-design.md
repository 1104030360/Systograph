# Epic 1 Backend Design

> Status: Backend Design Draft  
> Owner Scope: Backend / Core Scanner / JSON Contract  
> Source Design: `docs/design/epic1.md`  
> Related Specs: `docs/spec/erm.dbml`, `docs/spec/features/*.feature`  
> Output: `docs/work/Timmy/design/epic1-backend-design.md`

## 前置導覽：後端架構圖與白話說明

> 白話：這一節先用圖把整個後端怎麼運作講清楚，再用表格快速說明每個大 section、model、provider、service 是幹嘛的。

### 一、核心概念總覽

> 白話：KAI-Mind backend 的本質是「把一個 RAG repo 轉成可信的系統地圖」，不是直接做聊天機器人，也不是把 GUI 畫圖邏輯塞進 scanner。

```text
┌────────────────────────────────────────────────────────────────────┐
│                         KAI-Mind Backend                            │
│             project_path -> evidence-based ai_system_map.json        │
└────────────────────────────────────────────────────────────────────┘

使用者輸入
  │
  ├── CLI: kai-mind map <project_path>
  │
  └── GUI: 選擇 project folder
        │
        ↓
┌──────────────────────────────┐
│ Adapter Layer                 │
│ - CLI adapter                 │
│ - Web / Local API adapter     │
└───────────────┬──────────────┘
                │ 只負責 request/response，不直接掃檔
                ↓
┌────────────────────────────────────────────────────────────────────┐
│ Core Services                                                       │
│ MapBuildService                                                     │
│   ├─ ProjectScanService                                             │
│   ├─ ComponentDetectionService                                      │
│   ├─ SystemMapNormalizeService                                      │
│   ├─ SystemMapValidationService                                     │
│   ├─ ViewerSessionService                                           │
│   └─ QueryTraceService                                              │
└───────────────┬────────────────────────────────────────────────────┘
                │ 呼叫 providers 取得 facts
                ↓
┌────────────────────────────────────────────────────────────────────┐
│ Providers                                                           │
│ Filesystem / Config / Docker / Dependencies / Code Patterns          │
│ Endpoint Call / Output Artifacts                                     │
└───────────────┬────────────────────────────────────────────────────┘
                │ 只產生 evidence，不直接決定真相
                ↓
┌────────────────────────────────────────────────────────────────────┐
│ Canonical Outputs                                                   │
│ - ai_system_map.json  ← 唯一事實來源                                 │
│ - ai_system_map.md                                                    │
│ - GraphViewModel projection                                          │
│ - QueryTraceEvent[] / DetailScanResult[]                             │
└────────────────────────────────────────────────────────────────────┘
```

### 二、資料流總覽

> 白話：這張圖說明一個 repo 進來後，backend 會怎麼一步步變成 JSON、Markdown、GUI graph、replay。

```text
┌──────────────┐
│ project_path │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ 1. Precondition       │  檢查路徑存在、可讀、輸出策略
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ 2. File Inventory     │  掃 eligible files，跳過高成本/不相關檔案
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ 3. Providers          │  config / Docker / deps / code pattern
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ 4. Evidence & Facts   │  ScanFact[] / Evidence[] / ParseIssue[]
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ 5. Slot Mapping       │  對到 rag-core-v1 slots，或留下 unmapped
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│ 6. Normalize/Validate │  組成 ai-system-map/v1 並驗證 schema
└──────┬───────────────┘
       ↓
┌────────────────────────────────────────────────────────────────┐
│ 7. Outputs                                                      │
│ ai_system_map.json / ai_system_map.md / GraphViewModel / Replay │
└────────────────────────────────────────────────────────────────┘
```

### 三、Progressive Scan 與 Replay 顆粒度

> 白話：同一份系統地圖可以先粗看，再針對可疑元件深入，最後才追到 repo 自己寫的 code path。

```text
┌──────────────────────────┐
│ L1 System Map Scan        │
│ coarse_replay             │
│ 看整個 RAG 系統有哪些元件 │
└────────────┬─────────────┘
             │ 使用者點某個 component / unknown
             ↓
┌──────────────────────────┐
│ L2 Component Detail Scan  │
│ component_replay          │
│ 看單一元件的 evidence     │
└────────────┬─────────────┘
             │ 使用者點某條 edge / evidence
             ↓
┌──────────────────────────┐
│ L3 Code Path Scan         │
│ code_path_replay          │
│ 追 project-owned path     │
└──────────────────────────┘
```

```text
L1:
  API -> Retriever -> Vector Store -> Prompt Builder -> LLM

L2:
  /chat endpoint -> Chat Approach -> Query Rewrite -> Azure AI Search -> Prompt -> LLM

L3:
  app.py:chat()
    -> ChatReadRetrieveReadApproach.run()
    -> run_search_approach()
    -> search()
    -> create_response()
```

### 四、重要邊界

> 白話：這裡列出最容易混淆的責任邊界，避免實作時把 scanner、viewer、AI proposal、runtime trace 混在一起。

| 邊界 | 可以做 | 不可以做 |
|---|---|---|
| Scanner | read-only 掃 eligible project files | 預設修改使用者 repo |
| Evidence | 記錄 masked facts / safe snippets | 輸出完整 secret values |
| Canonical JSON | 作為 CLI/GUI/CI 的 source of truth | 讓 GUI 另外維護第二份 truth |
| GraphViewModel | backend 從 JSON 轉 projection | frontend 自行判斷 component 是否存在 |
| AI proposal | 產生 pending suggestion | 未確認就寫入 canonical facts |
| L3 scan | 追 project-owned application path | 追完整 framework/runtime call graph |
| Query trace | 明確 opt-in 後呼叫 endpoint | map scan 預設偷偷呼叫服務 |

### 五、各大章節白話導覽

> 白話：如果只想快速知道每一章在講什麼，先看這張表。

| Section | 白話說明 |
|---|---|
| 1. 一句話目標 | 說明 backend 最終要產生什麼東西。 |
| 2. 後端責任邊界 | 說明 backend 做什麼、不做什麼。 |
| 3. CLI / GUI 與後端的關係 | 說明 CLI 和 GUI 都只是入口，核心邏輯在 backend。 |
| 4. 主要資料流 | 說明 repo 變成 JSON report 的完整流水線。 |
| 5. Progressive Scan | 說明 L1/L2/L3 怎麼逐步掃描。 |
| 6. 建議模組邊界 | 說明 Python package 應該怎麼切。 |
| 7. Canonical JSON Contract | 說明 `ai_system_map.json` 的穩定格式。 |
| 8. Core Models | 說明 JSON 裡每種資料物件代表什麼。 |
| 9. Provider Design | 說明低階檔案/config/Docker/parser 怎麼產生 facts。 |
| 10. Service Design | 說明高階 use case service 怎麼串 providers 和 models。 |
| 11. Manual Mapping and AI Proposal Flow | 說明不確定 mapping 時，人和 AI 怎麼協作。 |
| 12. Graph View Model Boundary | 說明 backend graph projection 和 frontend rendering 的界線。 |
| 13. Error Handling | 說明 fatal / partial error 怎麼回報。 |
| 14. Secret Safety | 說明怎麼避免 secret 外洩。 |
| 15. Observability and Logging | 說明 logs 要怎麼支援除錯但不洩密。 |
| 16. Testing Strategy | 說明要用哪些測試保護 scanner contract。 |
| 17. Delivery Order | 說明 implementation 順序。 |
| 18. 後端和前端的交付契約 | 說明前後端彼此可以假設什麼。 |
| 19. 已決策事項 | 記錄已定案的架構選擇。 |
| 20. Acceptance Checklist | 實作完成前要逐項確認的清單。 |
| 21. 實作提醒 | 收斂成最重要的三條工程原則。 |

### 六、Core Models 白話導覽

> 白話：models 是 canonical JSON 裡的名詞表，負責定義「什麼資料可以被當成事實」。

| Model | 白話說明 |
|---|---|
| `RagSystemMap` | 最終整份系統地圖。 |
| `Project` | 被掃描的專案基本資訊。 |
| `ComponentSlot` | 標準 RAG 架構中的一格，例如 retriever、llm。 |
| `ComponentInstance` | 真正在 repo 裡被偵測到的元件，例如 Qdrant。 |
| `Evidence` | scanner 為什麼這樣判斷的證據。 |
| `Endpoint` | 偵測到的 local 或 external API URL。 |
| `Flow` / `Edge` | RAG 元件之間怎麼連起來。 |
| `RiskHint` | 初步 release-readiness 風險提示。 |
| `QueryTraceEvent` | query replay 的每一步事件。 |
| `DetailScanResult` | L2/L3 深掃後的補充結果。 |
| `ExtensionComponent` | baseline RAG 之外但有意義的元件。 |
| `UnmappedComponent` | 有 evidence，但還不能安全分類的元件。 |
| `ManualMapping` | 使用者確認過、下次 scan 可重現的 mapping。 |
| `MappingProposal` | AI 或 backend 給的建議，需使用者確認。 |

### 七、Providers 白話導覽

> 白話：providers 是資料來源轉換器，只負責讀東西和產生 evidence，不負責做最後判斷。

| Provider | 白話說明 |
|---|---|
| `FilesystemProvider` | 找出哪些檔案可以掃、哪些要跳過。 |
| `ConfigParseProvider` | 讀 `.env`、YAML、JSON、TOML 類設定。 |
| `DockerComposeProvider` | 從 Docker Compose 找服務、port、env、volume。 |
| `DependencyManifestProvider` | 從 requirements/package/pyproject 找 RAG dependency。 |
| `CodePatternProvider` | 從 source code 找 RAG pattern。 |
| `EndpointCallProvider` | query trace 時呼叫 endpoint 一次並收集事件。 |
| `OutputArtifactProvider` | 寫出 JSON、Markdown、error report。 |

### 八、Services 白話導覽

> 白話：services 是 backend 的工作流程大腦，負責把 providers 的 evidence 組成可驗證的系統地圖。

| Service | 白話說明 |
|---|---|
| `MapBuildService` | 整個 map build 的總指揮。 |
| `ProjectScanService` | 跑所有 providers，收集 facts/evidence/issues。 |
| `DetailScanService` | 判斷使用者要做 L2 還是 L3 深掃。 |
| `ComponentDetailScanService` | 專門掃某個 component 的細節。 |
| `CodePathScanService` | 追 project-owned application-level code path。 |
| `RagTemplateService` | 載入 `rag-core-v1` 標準模板。 |
| `ComponentDetectionService` | 把 evidence 映射到 slots、extensions、unmapped。 |
| `EndpointDetectionService` | 從 evidence 推導 endpoints。 |
| `ManualMappingService` | 套用使用者確認過的 mapping store。 |
| `MappingProposalService` | 產生 pending AI mapping proposal。 |
| `RiskHintService` | 從 evidence 產生初步風險提示。 |
| `SystemMapNormalizeService` | 把所有中間資料整理成 canonical JSON。 |
| `SystemMapValidationService` | 驗證 JSON contract 和 invariants。 |
| `MarkdownSummaryService` | 把 canonical JSON 轉成人類可讀 Markdown。 |
| `ViewerSessionService` | 把 canonical JSON 轉成 GUI graph projection。 |
| `QueryTraceService` | 呼叫 endpoint 並產生 replay events。 |

## 0. 閱讀導覽

> 白話：這裡告訴你如果只想了解某一塊，應該先讀哪幾章，不用從頭硬讀到尾。

這份文件用「先決策、再細節」的順序寫。後端工程師可以先讀前半部掌握架構，再回到後半部查 models、services、tests。

| 你想了解 | 先讀 |
|---|---|
| 後端到底負責什麼 | 1-3 |
| 從掃 project 到 JSON 的流程 | 4 |
| 掃描要掃多細 | 5 |
| 檔案與服務怎麼切 | 6、10 |
| JSON contract 長什麼樣 | 7 |
| 不確定模組怎麼處理 | 7、11 |
| replay 會不會被影響 | 5、10、11 |
| 怎麼測 | 16 |
| 開發順序 | 17 |

### One-page summary

> 白話：這是一張超短摘要，先抓住 backend 的目標、預設掃描模式、truth rule、frontend rule。

```text
Backend goal:
  project_path -> evidence-based ai_system_map.json

Default mode:
  L1 coarse system scan first

Optional mode:
  user drills down into a component
    -> L2 component detail scan
    -> L3 code path scan

Truth rule:
  scanner evidence + user-confirmed mapping + validation
  never AI-only facts

Frontend rule:
  GUI only displays canonical JSON / graph projection
  GUI does not rescan project files
```

## 1. 一句話目標

> 白話：這一章只回答一件事：backend 最終到底要產生什麼。

後端要把一個既有 RAG project folder，轉成一份正確、穩定、可驗證、可追溯 evidence 的 `ai-system-map/v1` JSON。

```text
project_path
  -> backend scanner
  -> normalized ai_system_map.json
```

CLI 或 GUI 只是入口。後端的核心責任不是「畫圖」，而是產生 canonical `ai_system_map.json`，讓 CLI、GUI、CI/CD、後續 Epic 都讀同一份事實來源。

## 2. 後端責任邊界

> 白話：這一章把 backend 的工作範圍畫清楚，避免 scanner、GUI、security scanner、runtime health check 混在一起。

### 後端負責

> 白話：這些是 Epic 1 backend 必須交付的能力。

- 掃描 project folder，但預設 read-only。
- 定義與驗證 `ai-system-map/v1` schema。
- 載入 `rag-core-v1` reference architecture template。
- 掃描 config、Docker Compose、dependency manifests、RAG code patterns。
- 產生 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`。
- 將 facts 映射到 RAG component slots。
- 產生 component instances、endpoints、flows、risk hints、recommended next checks。
- 遮罩 secret-like values，避免完整 secret 進入 JSON、Markdown、logs、snapshots、GUI。
- 輸出 `ai_system_map.json`、`ai_system_map.md`、必要時輸出 `map-error.md`。
- 提供 viewer 可消費的 graph view model projection。
- 提供 query trace MVP 的 endpoint detection、basic call、timeout/error event、trace mapping。

### 後端不負責

> 白話：這些刻意不放在 Epic 1 backend，避免第一版範圍膨脹。

- 不實作完整 GUI layout、graph styling、drag/zoom/pan UI。
- 不讓 GUI 重新掃描 project files。
- 不做完整 runtime health check，留給 Epic 2。
- 不做完整 port security / secret scanning，留給 Epic 3。
- 不做 Agent tool policy，留給 Epic 4。
- 不做 groundedness / citation correctness，留給 Epic 5。
- 不做 final `READY` / `RISKY` / `NOT_READY` gate verdict，留給 Epic 6。
- 不讓 LLM 成為 scanner facts 或 JSON contract 的 source of truth。

## 3. CLI / GUI 與後端的關係

> 白話：CLI 和 GUI 都只是入口，真正掃描和產生 JSON 的邏輯只能在 core backend。

CLI 和 GUI 都應該呼叫同一個 core backend service。

```text
┌──────────────────────────────────────────────────────────────────┐
│ User entry                                                        │
├───────────────────────────────┬──────────────────────────────────┤
│ CLI                           │ GUI / Local Web UI               │
│ kai-mind map <project_path>   │ 使用者選 project folder          │
│ kai-mind viewer <map_json>    │ 使用者載入 ai_system_map.json    │
└───────────────┬───────────────┴──────────────────┬───────────────┘
                │                                  │
                ↓                                  ↓
┌──────────────────────────────┐   ┌────────────────────────────────┐
│ CLI adapter                  │   │ Web adapter / local API         │
│ - parse args                 │   │ - request/response              │
│ - print paths/status         │   │ - UI state only                 │
└───────────────┬──────────────┘   └────────────────┬───────────────┘
                │                                   │
                └───────────────┬───────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│ Core backend services                                             │
│ MapBuildService / ViewerSessionService / QueryTraceService        │
└──────────────────────────────────────────────────────────────────┘
```

後端設計重點：

- CLI adapter 不直接掃描檔案，只呼叫 `MapBuildService`。
- GUI adapter 不直接掃描檔案，只呼叫 `MapBuildService` 或 `ViewerSessionService`。
- canonical JSON 是正式 contract。
- graph view model 只是從 canonical JSON 轉出來的 projection，不是第二份 truth。

## 4. 主要資料流

> 白話：這一章說明一個 project folder 進來後，會經過哪些步驟變成 map、report、graph、replay。

```text
0. Input
   project_path + output option + system_type
        ↓
1. Precondition check
   檢查 project folder 是否存在、可讀，決定 output policy
        ↓
2. File inventory
   掃描候選檔案，排除 dependency/build/binary/generated files
        ↓
3. Deterministic providers
   config / Docker / dependency / code pattern parsers
        ↓
4. Raw scan facts
   ScanFact[] + Evidence[] + ParseIssue[]
        ↓
5. RAG slot mapping
   facts -> rag-core-v1 component slots
        ↓
6. Endpoint / Risk / Flow derivation
   endpoints + risk_hints + indexing/query_answer flows
        ↓
7. Normalize and validate
   assemble RagSystemMap, validate ai-system-map/v1
        ↓
8. Artifacts
   ai_system_map.json + ai_system_map.md 或 map-error.md
        ↓
9. Viewer projection
   GraphViewModel for GUI
        ↓
10. Optional drill-down scan
   user-selected component -> detail_scans[]
        ↓
11. Optional query trace MVP
   endpoint call -> QueryTraceEvent[]
```

### 後端最重要的資料轉換

> 白話：這是 backend 的資料轉換主線，所有 service 都是在幫這條線前進。

```text
FileInventory
  -> ScanFact[] + Evidence[] + ParseIssue[]
  -> ComponentSlot[] + ComponentInstance[]
  -> Endpoint[] + RiskHint[] + Flow[] + Edge[]
  -> RagSystemMap ai-system-map/v1
  -> optional DetailScanResult[]
  -> GraphViewModel
```

## 5. Progressive Scan / Drill-down Scan

> 白話：這一章定義為什麼不要一開始就深掃整個 repo，而是先粗看，再逐步深入。

Epic 1 不應該一開始就全專案深掃。比較好的策略是 progressive scan：

```text
L1 粗顆粒：System Map Scan
  先自動產生可用的 ai_system_map.json

L2 中顆粒：Component Detail Scan
  使用者針對某個 component / slot 點下去再掃更細

L3 細顆粒：Code Path Scan
  使用者針對某條 edge / trace step / evidence 再查 code path
```

這個設計的目標是：

- 使用者一開始不用等很久。
- 後端先產生穩定、可驗證的 base map。
- 使用者只對有疑問或高風險的區塊做 deeper scan。
- 深掃結果補充 detail，不破壞 L1 canonical contract。
- replay 可以隨掃描深度逐步變細，但不能因為沒深掃就失敗。

### L1: Coarse System Map Scan

> 白話：L1 是預設第一掃，目標是快速產生可用的系統地圖。

L1 是預設掃描，也是 Epic 1 的 minimum viable backend output。

掃描範圍：

- file inventory。
- config files。
- Docker Compose / Dockerfile。
- dependency manifests。
- README / project metadata。
- bounded RAG code patterns。
- app endpoint hints。

產出：

- `components_by_slot`
- `endpoints`
- `flows`
- `risk_hints`
- `extensions`
- `unmapped_components`
- `recommended_next_checks`

使用者一開始拿到的是：

```text
ai_system_map.json
ai_system_map.md
GUI graph projection
```

### L2: Component Detail Scan

> 白話：L2 是使用者點某個元件後，才針對那個元件多看一層。

L2 是使用者對某個 coarse component 按下「詳細掃描」後才觸發。

適合目標：

- `retriever`
- `vector_store`
- `prompt_builder`
- `app_api_or_orchestrator`
- `llm`
- `unmapped_component`
- `extension_component`

掃描方式：

- 只掃該 component 相關 source files。
- 讀取附近 imports / config references。
- 尋找 component input/output hints。
- 找到與其他 slots 的直接關係。
- 產生 detail scan evidence。

產出範例：

```json
{
  "id": "detail_scan_retriever_001",
  "target_type": "component_slot",
  "target": "retriever",
  "scan_depth": "component",
  "status": "completed",
  "findings": [
    {
      "kind": "retriever_call",
      "summary": "retriever invokes Qdrant similarity search",
      "evidence_ids": ["evidence_retriever_similarity_search"]
    }
  ]
}
```

### L3: Code Path Scan

> 白話：L3 是追一條具體路徑，但只追 repo 自己寫的 application code，不追框架內部。

L3 是最細的 bounded analysis，只在使用者需要確認某條 flow、edge、trace step 或高風險 unknown 時觸發。

適合問題：

- endpoint handler 實際有沒有呼叫 retriever？
- retriever 到 vector store 的 code path 是什麼？
- query router 會把問題分到哪些路徑？
- replay 某一步為什麼停在 unknown component？

產出範例：

```text
code path:
  src/api.py: query_endpoint
    -> src/rag/service.py: answer_question
    -> src/rag/retriever.py: retrieve
    -> src/rag/vectorstore.py: similarity_search
```

規則：

- L3 必須標示 `best_effort` 或 bounded analysis。
- L3 不做完整 whole-repo call graph。
- L3 不可直接推翻 L1 facts；只能補充 evidence 或產生 mapping proposal。
- L3 結果如果要更新 canonical map，仍需走 validation。

### Scan depth contract

> 白話：這裡定義 JSON 要怎麼記錄目前掃描深度，讓 GUI 和 replay 不會誤解資料精細度。

建議在 JSON 中保留 scan depth metadata：

```json
{
  "scan_depth": "system",
  "detail_scans": [
    {
      "id": "detail_scan_retriever_001",
      "target_type": "component_slot",
      "target": "retriever",
      "scan_depth": "component",
      "status": "completed"
    }
  ]
}
```

`scan_depth` 建議值：

| Value | 意義 |
|---|---|
| `system` | L1 粗顆粒，預設掃描 |
| `component` | L2 中顆粒，針對 component / slot |
| `code_path` | L3 細顆粒，針對 edge / trace / evidence |

### Replay impact

> 白話：掃得越深，replay 可以顯示越細；但只有 L1 時 replay 也應該能用。

Progressive scan 會影響 replay 的細緻程度，但不應影響 replay 能不能使用。

```text
只有 L1:
  user query -> app endpoint -> retriever -> LLM -> response

有 L2:
  user query -> app endpoint -> retriever detail -> vector store -> LLM

有 L3:
  user query -> FastAPI handler -> answer_question() -> retrieve() -> similarity_search()
```

Replay UI / API 必須標示目前 replay depth：

- `coarse_replay`
- `component_replay`
- `code_path_replay`

沒有深掃時，不代表系統沒有經過細節步驟，只代表目前沒有足夠 evidence 可以畫到那麼細。

## 6. 建議模組邊界

> 白話：這一章把未來 Python package 怎麼切先畫出來，避免 CLI、provider、models、services 互相依賴到失控。

目前 repo 尚未有 implementation scaffold。以下用 Python-like path 表示，若最後採 TypeScript，仍應保留相同邊界。

```text
src/kai_mind/
  core/
    models/
      system_map.py
      scan.py
      detail_scan.py
      template.py
      trace.py
      errors.py
    providers/
      filesystem_provider.py
      config_parse_provider.py
      docker_compose_provider.py
      dependency_manifest_provider.py
      code_pattern_provider.py
      endpoint_call_provider.py
      output_artifact_provider.py
    services/
      map_build_service.py
      project_scan_service.py
      detail_scan_service.py
      component_detail_scan_service.py
      code_path_scan_service.py
      rag_template_service.py
      component_detection_service.py
      manual_mapping_service.py
      mapping_proposal_service.py
      endpoint_detection_service.py
      risk_hint_service.py
      system_map_normalize_service.py
      system_map_validation_service.py
      markdown_summary_service.py
      viewer_session_service.py
      query_trace_service.py
      trace_mapping_service.py
      secret_masking_service.py
    templates/
      rag-core-v1.json
  cli/
    main.py
    map_command.py
    viewer_command.py
  web/
    app.py
    routes.py
  config/
    user_mapping_store.py
```

依賴方向必須固定：

```text
CLI / Web adapters
  -> Core services
      -> Provider interfaces
      -> Core models
```

禁止方向：

```text
providers -> CLI
providers -> GUI
models -> providers
report generation -> rescan files
viewer -> scan project files
```

## 7. Canonical JSON Contract

> 白話：這一章定義最重要的正式輸出格式，所有 CLI、GUI、CI、Markdown 都要以它為準。

`ai_system_map.json` 是後端最重要輸出。GUI、Markdown、CI/CD、後續 Epic 都應該讀這份 contract。

### Top-level fields

> 白話：這裡列出 `ai_system_map.json` 最外層必須有哪些欄位。

```json
{
  "schema_version": "ai-system-map/v1",
  "system_type": "rag",
  "classification": {},
  "project": {},
  "reference_architecture": {},
  "scan_depth": "system",
  "components_by_slot": {},
  "endpoints": [],
  "flows": [],
  "extensions": [],
  "unmapped_components": [],
  "detail_scans": [],
  "risk_hints": [],
  "recommended_next_checks": [],
  "query_trace_events": []
}
```

### Contract invariants

> 白話：這裡是 JSON 的硬規則，違反就代表 report 不可信或 schema contract 破壞。

- `schema_version` 必須是 `ai-system-map/v1`。
- `system_type` 在 Epic 1 必須是 `rag`。
- `classification.mode` 必須是 `user_selected_or_default`。
- `classification.selected_template` 必須是 `rag-core-v1`。
- `scan_depth` 預設是 `system`。
- `ComponentSlot.status` 只能是 `detected`、`missing`、`not_configured`、`not_applicable`。
- `detected` slot 必須至少有一個 component instance 和 evidence。
- 沒有 evidence 的 slot 不得標示為 `detected`。
- JSON 不得包含 `confidence`。
- `Evidence.file` 必須使用 project-relative POSIX path。
- 每個 `Endpoint` 必須引用 `Evidence.id`。
- `extensions` 只能包含有 evidence 或 user-confirmed mapping 的非標準元件。
- `unmapped_components` 只能表示「掃到 evidence，但尚未能安全映射」的元件，不可當成 detected standard slot。
- `detail_scans` 只能補充 detail，不可繞過 validation 改寫 canonical facts。
- 每個 `RiskHint` 必須包含 `target`、`target_type`、`evidence_id`、`rule_id`、`rationale`。
- Epic 1 無法證明完整風險嚴重度時，`RiskHint.uncertainty` 必須說明限制。
- full secret values 不得出現在 JSON、Markdown、logs、snapshots、GUI。

### Baseline template and real-world extension

> 白話：這裡說明 baseline RAG 架構只是標準框架，真實 repo 的客製元件要用 extension / unmapped 處理。

`rag-core-v1` 是 baseline template，不是硬把所有 RAG 專案塞進同一張圖的唯一真相。後端應該把實際掃到的 evidence 分成三類：

```text
1. clearly mapped
   有足夠 evidence 可以對應到 rag-core-v1 slot。

2. extension / custom
   有 evidence，也知道它是非標準但有意義的 RAG 元件，例如 reranker、query router、SQL retriever。

3. unmapped / needs_confirmation
   有 evidence，但不能安全判斷它屬於哪個 slot 或 extension。
```

設計原則：

- 不確定時不要硬塞進 `components_by_slot`。
- 不確定時也不要丟掉 evidence。
- `unmapped_components` 是使用者後續確認的入口。
- AI 可以產生 mapping proposal，但不能直接把 proposal 寫成正式 facts。
- user confirmation + evidence + validation 才能進入 canonical map。

## 8. Core Models

> 白話：這一章定義 canonical JSON 裡每個核心物件的意思。

### `RagSystemMap`

> 白話：這是最終整份 map 的根物件，其他欄位都掛在它下面。

代表最終 canonical output。

必要欄位：

- `schema_version`
- `system_type`
- `classification`
- `project`
- `reference_architecture`
- `scan_depth`
- `components_by_slot`
- `endpoints`
- `flows`
- `extensions`
- `unmapped_components`
- `detail_scans`
- `risk_hints`
- `recommended_next_checks`
- `query_trace_events`

### `Project`

> 白話：這個 model 描述被掃描的專案本身，不描述 RAG 元件。

代表被掃描專案。

欄位：

- `root_path`: input root path，可保留 absolute path。
- `name`: project name。
- `system_map_schema_version`: 對應 `ai-system-map/v1`。

注意：

- `root_path` 可以保存使用者輸入或 resolved path。
- evidence path 不可用 absolute path，必須是 project-relative POSIX path。

### `ComponentSlot`

> 白話：slot 是標準 RAG 架構裡的「位置」，例如 retriever、llm、vector_store。

代表 reference architecture 中的一個 RAG slot。

Epic 1 slots：

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

欄位：

- `slot`
- `required_for_rag`
- `status`
- `instances`

### `ComponentInstance`

> 白話：instance 是 repo 裡實際偵測到的東西，例如 Qdrant 或 OpenAI client。

代表被偵測到的具體 component。

例子：

```json
{
  "id": "qdrant_vector_db",
  "slot": "vector_store",
  "kind": "vector_db",
  "name": "Qdrant",
  "evidence_ids": ["evidence_qdrant_service", "evidence_qdrant_ports"]
}
```

### `Evidence`

> 白話：evidence 是 scanner 判斷的證據來源，沒有 evidence 就不能說 detected。

代表每個 scanner fact 的來源證據。

例子：

```json
{
  "id": "evidence_qdrant_service",
  "kind": "docker_service",
  "file": "docker-compose.yml",
  "path": "services.qdrant.image",
  "value": "qdrant/qdrant"
}
```

規則：

- `file` 必須是 project-relative POSIX path。
- `value` 必須經過 `SecretMaskingService`。
- 解析錯誤也可以成為 evidence，例如 `parse_error`。

### `Endpoint`

> 白話：endpoint 是偵測到可被呼叫或外部連線的 URL / service address。

代表偵測到的 local 或 external endpoint。

欄位：

- `id`
- `value`
- `endpoint_type`: `local` 或 `external`
- `evidence_id`
- `slot` 或 `component_instance_id`，若可判斷

例子：

- `http://localhost:8000/query`
- `http://localhost:6333`
- `https://api.openai.com/v1`

### `Flow` and `Edge`

> 白話：flow/edge 用來表達 RAG 元件之間的方向關係，例如 retriever 查 vector store。

Epic 1 至少需要：

- `indexing`
- `query_answer`

`Edge` 表示 slot 到 slot 的關係：

```json
{
  "id": "edge_retriever_vector_store",
  "flow_id": "query_answer",
  "from_slot": "retriever",
  "to_slot": "vector_store",
  "relationship": "queries_vector_store"
}
```

### `RiskHint`

> 白話：risk hint 是初步風險提示，不是最終安全 verdict。

代表 release-readiness 的初步風險提示，不是最終 security verdict。

例子：

```json
{
  "id": "risk_qdrant_published_port",
  "type": "network_exposure",
  "target": "qdrant_vector_db",
  "target_type": "component_instance",
  "evidence_id": "evidence_qdrant_ports",
  "rule_id": "docker_published_port_exposure",
  "rationale": "published port can expose Qdrant outside localhost",
  "uncertainty": "Epic 1 does not run full port security check",
  "severity_hint": "high"
}
```

### `QueryTraceEvent`

> 白話：query trace event 是 replay 裡的一步，記錄 query 執行過程中的事件。

代表 query trace MVP 的 replay step。

欄位：

- `id`
- `sequence_index`
- `timestamp`
- `slot`
- `edge_id`
- `input`
- `output`
- `latency`
- `error`
- `retrieved_chunks`

規則：

- `sequence_index` 控制 replay order。
- input/output/retrieved_chunks 必須經過 secret masking。
- timeout/error 不得丟棄已收集的 partial replay。

### `DetailScanResult`

> 白話：detail scan result 是 L2/L3 深掃補充的細節，不應繞過 validation 改寫正式 facts。

代表 L2 / L3 drill-down scan 的附加結果。

例子：

```json
{
  "id": "detail_scan_retriever_001",
  "target_type": "component_slot",
  "target": "retriever",
  "scan_depth": "component",
  "status": "completed",
  "findings": [
    {
      "kind": "retriever_call",
      "summary": "retriever invokes Qdrant similarity search",
      "evidence_ids": ["evidence_retriever_similarity_search"]
    }
  ]
}
```

規則：

- `scan_depth` 必須是 `component` 或 `code_path`。
- `target` 必須指向已存在 slot、component、extension、unmapped component、edge 或 evidence。
- detail scan 不可直接修改 canonical facts。
- detail scan 若要提升 confidence-like 判斷，不可新增 `confidence`；只能新增 evidence、mapping proposal 或 recommended next check。
- detail scan 結果必須可被重新驗證。

### `ExtensionComponent`

> 白話：extension 是標準 RAG slot 之外，但對系統架構有意義的元件。

代表不屬於 `rag-core-v1` 標準 slot，但對實際 RAG 架構有意義的元件。

例子：

```json
{
  "id": "extension_query_router",
  "name": "Query Router",
  "kind": "routing_orchestration",
  "status": "confirmed",
  "evidence_ids": ["evidence_src_router_py"],
  "confirmed_by_user": true,
  "description": "Routes user questions to vector search or SQL path."
}
```

常見 extension 類型：

- `reranker`
- `query_router`
- `sql_retriever`
- `graph_retriever`
- `hybrid_search`
- `cache`
- `memory`
- `tool_calling`
- `custom_orchestration`

### `UnmappedComponent`

> 白話：unmapped 是有 evidence 但還不能安全分類的東西，留給使用者確認。

代表 scanner 有 evidence，但目前不能安全映射到 standard slot 或 extension。

例子：

```json
{
  "id": "unmapped_src_router_py",
  "source_file": "src/router.py",
  "observed_kind": "routing_like_code",
  "status": "needs_confirmation",
  "evidence_ids": ["evidence_src_router_py"],
  "reason": "Detected routing behavior, but no safe mapping exists in rag-core-v1."
}
```

規則：

- `unmapped_components` 不等於 `detected` slot。
- `unmapped_components` 必須有 evidence。
- GUI 可以顯示為「待確認」。
- 後續可由 manual mapping 或 AI proposal 轉成 existing slot mapping 或 extension component。

### `ManualMapping`

> 白話：manual mapping 是使用者確認過的架構知識，讓下次 scan 可以重現同一個判斷。

代表使用者確認後的可重跑 mapping config。這個設定不應只存在輸出的 JSON，應保存到 KAI-Mind-managed user mapping store，讓下一次 scan 可重現。

預設儲存位置由 KAI-Mind 管理，不寫入被掃描 repo。可採 app data store 或檔案型 store：

```text
~/Library/Application Support/KAI-Mind/mappings.db
~/.kai-mind/mappings/<project_id>/kai-mind.mapping.yaml
```

`kai-mind.mapping.yaml` 可作為後續 import/export 或 `--mapping-file` 的交換格式，但不是 Epic 1 預設寫入 project root 的檔案。

例子：

```yaml
manual_mappings:
  - type: existing_slot_mapping
    source_file: src/reranker.py
    maps_to_slot: retriever
    extension_type: reranker
    evidence_ids:
      - evidence_src_reranker_py
    confirmed_by_user: true

  - type: new_extension_component
    source_file: src/router.py
    component_id: extension_query_router
    name: Query Router
    kind: routing_orchestration
    evidence_ids:
      - evidence_src_router_py
    edges:
      - flow_id: query_answer
        from: app_api_or_orchestrator
        to: extension_query_router
        relationship: routes_query_by_type
    confirmed_by_user: true
```

### `MappingProposal`

> 白話：mapping proposal 是 AI 或 backend 的建議，還不是正式事實。

代表 AI 根據使用者文字或 evidence summary 產生的建議。它不是正式 map facts。

例子：

```json
{
  "proposal_id": "proposal_query_router",
  "proposal_type": "new_extension_component",
  "source": "ai_assisted_user_description",
  "status": "pending_user_confirmation",
  "suggested_component": {
    "id": "extension_query_router",
    "name": "Query Router",
    "kind": "routing_orchestration"
  },
  "suggested_edges": [
    {
      "flow_id": "query_answer",
      "from": "app_api_or_orchestrator",
      "to": "extension_query_router",
      "relationship": "routes_query_by_type"
    }
  ],
  "evidence_ids": ["evidence_src_router_py"]
}
```

規則：

- proposal 必須顯示給使用者確認。
- proposal 不可直接寫入 canonical JSON。
- 使用者可接受、修改或拒絕。
- 接受後寫入 KAI-Mind user mapping store，再重新 normalize 成 canonical JSON。

## 9. Provider Design

> 白話：providers 是低階讀取器，只負責從檔案、config、Docker、dependency、code 裡抽出 evidence。

Provider 負責和低階來源互動。Provider 只產生 facts，不決定最終 slot status。

### `FilesystemProvider`

> 白話：它負責決定哪些檔案能掃、哪些檔案要跳過，以及 evidence path 怎麼正規化。

責任：

- 驗證 project root 是否存在、是否可讀。
- 建立 file inventory。
- 優先使用 git-tracked files；不是 git repo 時 fallback recursive listing。
- 排除 dependency/build/binary/generated files。
- 保留 config、docs、Docker、dependency manifests、source files。
- 將所有 evidence file path 正規化成 project-relative POSIX path。

輸入：

- `project_root`
- include/exclude rules
- scan limits

輸出：

- `FileInventory`
- skipped files with reason

錯誤：

- root 不存在或不可讀：fatal `PreconditionError`。
- 單一檔案不可讀：partial `ScanLimitError` 或 skipped evidence。

### `ConfigParseProvider`

> 白話：它負責讀設定檔，特別是要小心 secret-like values 只能遮罩後輸出。

責任：

- parse `.env`、`.env.example`、YAML、JSON、TOML-like config。
- 輸出 structured key/value facts。
- 對 secret-like values 只輸出 masked value。
- malformed config 產生 parse error evidence。

重要規則：

- 可以記錄「存在 `OPENAI_API_KEY` 這個 key」。
- 不可以輸出完整 key value。
- parse error 不應中止整體 scan，除非導致 output contract 無法建立。

### `DockerComposeProvider`

> 白話：它負責從 Docker Compose 找服務、image、ports、env、volume，常用來抓 vector store 或 local runtime。

責任：

- parse `docker-compose.yml` / `docker-compose.yaml`。
- 偵測 services、images、ports、environment、volumes、depends_on。
- 產生 vector store、runtime、endpoint、network exposure 相關 facts。

典型 mapping：

- image 包含 `qdrant/qdrant` -> `vector_store` candidate。
- image 包含 `ollama/ollama` -> `llm` 或 local LLM runtime candidate。
- `ports: ["6333:6333"]` -> endpoint + network exposure risk hint evidence。

### `DependencyManifestProvider`

> 白話：它負責從 dependency 檔案看出專案用了哪些 RAG framework、LLM SDK、vector store client。

責任：

- parse `requirements.txt`、`pyproject.toml`、`package.json`。
- 偵測 RAG framework 與 provider dependencies。

初始 detection examples：

- `langchain` -> orchestrator / retriever / prompt builder signals。
- `llama-index` -> orchestrator / indexing / retriever signals。
- `qdrant-client` -> vector store signal。
- `chromadb` -> vector store signal。
- `openai` -> external LLM / embedding provider signal。
- `ollama` -> local LLM runtime signal。

### `CodePatternProvider`

> 白話：它負責對 source files 做 bounded pattern scan，找出 loader、splitter、retriever、prompt、LLM call 等線索。

責任：

- 對 selected source files 做 bounded scan。
- 偵測 explicit RAG patterns。
- 不做完整 AST 理解；第一版以可解釋、可測試的 pattern rules 為主。

初始 patterns：

- data loaders / readers。
- text splitter / chunking。
- embedding model creation。
- vector store client。
- retriever construction。
- prompt template。
- LLM call。
- citation / response composer。
- FastAPI / Flask / Express route endpoint。

規則：

- 大檔案、binary、generated files 必須 skip with reason。
- pattern fact 必須帶 file/path/value/rule_id。
- 不可讓 LLM 自行創造 component。

### `EndpointCallProvider`

> 白話：它只在 query trace 時呼叫 endpoint，不是一般 map scan 的預設行為。

責任：

- Query trace MVP 呼叫 detected endpoint 一次。
- 設定 timeout。
- 收集 basic response/error event。

規則：

- 沒有 endpoint 時不得送出 query。
- timeout/error 必須回傳 trace event，不得讓 viewer 空白。
- 不記錄 raw sensitive query，除非明確設定。

### `OutputArtifactProvider`

> 白話：它負責把結果寫成檔案，並避免覆蓋舊報告。

責任：

- 建立 output directory。
- 避免覆寫舊檔。
- 寫出 JSON、Markdown、error report。

output policy：

```text
outputs/ empty
  -> outputs/ai_system_map.json
  -> outputs/ai_system_map.md

outputs/ already has artifacts
  -> outputs/<timestamp>/ai_system_map.json
  -> outputs/<timestamp>/ai_system_map.md

fatal precondition error
  -> outputs/map-error.md
```

## 10. Service Design

> 白話：services 是高階工作流程，負責把 provider 產生的 evidence 組成正式 map。

### `MapBuildService`

> 白話：它是整個 `kai-mind map` 的總指揮，從 validate path 到寫出 artifacts 都由它串起來。

最高層 use case。

輸入：

```text
MapBuildRequest {
  project_path
  output_dir
  system_type
  scan_options
}
```

輸出：

```text
MapBuildResult {
  status
  json_path
  markdown_path
  error_path
  warnings
  summary
}
```

流程：

1. validate project path。
2. prepare output run directory。
3. load `rag-core-v1` template。
4. run `ProjectScanService`。
5. run component/endpoint/risk/flow services。
6. normalize map。
7. validate schema。
8. write artifacts。
9. return result。

### `ProjectScanService`

> 白話：它負責跑 providers 收集 facts/evidence/issues，但不負責判斷最終 slot 狀態。

負責 orchestrate providers。

輸出：

- `ScanFact[]`
- `Evidence[]`
- `ParseIssue[]`
- skipped files summary

不負責：

- 不決定 slot 最終 status。
- 不寫 output artifacts。
- 不產生 Markdown。

### `DetailScanService`

> 白話：它是 L2/L3 深掃入口，根據使用者點的 target 決定要做哪種 detail scan。

負責 progressive scan 的入口。它接收使用者選定的 target，決定要執行 L2 component detail scan 或 L3 code path scan。

輸入：

```text
DetailScanRequest {
  map_json
  target_type
  target_id
  scan_depth
}
```

輸出：

```text
DetailScanResult {
  id
  target_type
  target
  scan_depth
  status
  findings
  evidence_ids
  warnings
}
```

規則：

- 只能掃 target 相關檔案，不做 whole-repo deep scan。
- 必須重用 `FilesystemProvider`、`CodePatternProvider` 與 existing evidence。
- L2/L3 結果必須附加到 `detail_scans`。
- 若 detail scan 發現新 mapping，只能產生 `MappingProposal` 或新增 evidence，不能跳過 validation。

### `ComponentDetailScanService`

> 白話：它負責針對某個元件多掃一層，例如 retriever 的 vector store、top_k、reranker 線索。

負責 L2 中顆粒掃描。

適合 target：

- component slot。
- component instance。
- extension component。
- unmapped component。

行為：

- 找出相關 source files。
- 掃描附近 imports / route / config references。
- 補充 component input/output hints。
- 補充 component-to-component relationship evidence。

### `CodePathScanService`

> 白話：它負責追一條 project-owned application code path，不追 framework 或 SDK 內部。

負責 L3 細顆粒掃描。

適合 target：

- flow edge。
- query trace event。
- evidence。
- high-impact unmapped component。

行為：

- 建立 bounded code path。
- 標示 `best_effort`。
- 不建立完整 call graph。
- 產生 code path evidence 或 mapping proposal。

### `RagTemplateService`

> 白話：它負責載入 `rag-core-v1` 標準模板，讓 detection 有固定 slot 和 flow 參考。

負責載入 `rag-core-v1`。

Template 內容至少包含：

- slots。
- allowed statuses。
- indexing flow slot order。
- query_answer flow slot order。
- slot requiredness heuristic defaults。
- rule ids metadata。

### `ComponentDetectionService`

> 白話：它負責把 evidence 映射成 detected/missing/unmapped/extension，是 scanner 判斷核心。

負責把 facts 映射成 slots 與 component instances。

核心規則：

- `detected` 必須有 evidence。
- 沒有 evidence 不得創造 instance。
- 不使用 `confidence`。
- 多個 facts 可以支撐同一 instance。
- 只能輸出 allowed status。
- 對無法安全映射的 facts，輸出 `unmapped_components`，不要硬塞進 standard slot。
- 對已確認的 manual mapping，套用到 standard slot 或 extension component。

status 判斷：

| Status | 使用時機 |
|---|---|
| `detected` | 有足夠 evidence 可指向具體 component |
| `missing` | slot 對此 RAG system 應存在，但沒有 evidence |
| `not_configured` | 有設定位置或 feature hint，但未設定具體 provider |
| `not_applicable` | 根據 project evidence 判斷此 slot 不適用 |

### `EndpointDetectionService`

> 白話：它負責從 routes、Docker ports、base URLs、provider config 推出 endpoints。

負責從 facts/evidence 推導 endpoint。

來源：

- Docker Compose published ports。
- app route pattern。
- config base URLs。
- known external provider package/config。

輸出：

- local endpoints。
- external endpoints。
- endpoint evidence link。

### `ManualMappingService`

> 白話：它負責讀 KAI-Mind user mapping store，把使用者確認過的 mapping 套回本次 scan。

負責讀取、驗證與套用使用者確認過的 mapping config。Epic 1 預設來源是 KAI-Mind-managed user mapping store；`kai-mind.mapping.yaml` 僅作為後續 import/export 或 explicit mapping file 的交換格式。

輸入：

- `ScanFact[]`
- `Evidence[]`
- effective manual mappings from KAI-Mind user mapping store

輸出：

- existing slot mapping overrides。
- extension components。
- extension edges。
- mapping validation warnings。

規則：

- mapping 必須引用仍存在的 evidence 或 source file。
- mapping 不可覆蓋 scanner 已確認的 secret masking。
- mapping 不可讓 invalid slot、invalid edge、dangling reference 進入 canonical JSON。
- mapping config 比 AI proposal 更可信，因為它已經被使用者確認。

### `MappingProposalService`

> 白話：它負責產生「待使用者確認」的 mapping 建議，不直接改 canonical facts。

負責把使用者自然語言說明與 unmapped evidence summary 轉成 mapping proposal。

輸入：

- `UnmappedComponent`
- masked evidence summary。
- user description。
- available slots and extension types。

輸出：

- `MappingProposal`

規則：

- 只產生 proposal，不直接更新 canonical map。
- proposal 必須保留 evidence ids。
- proposal 必須標示 `pending_user_confirmation`。
- 如果無法產生合理 mapping，回傳「需要使用者選擇」而不是硬猜。

### `RiskHintService`

> 白話：它負責把 evidence 轉成 release-readiness risk hints，並說明不確定性。

負責產生 Epic 1 初步 risk hints。

初始 rules：

- `docker_published_port_exposure`
- `external_provider_detected`
- `config_parse_error`
- `secret_like_config_key_detected`
- `missing_required_slot`

規則：

- 每個 risk hint 必須有 evidence。
- risk hint 是提示，不是 final verdict。
- 不確定時必須寫 `uncertainty`。

### `SystemMapNormalizeService`

> 白話：它負責把分散的 facts、components、flows、risk hints 整理成 canonical JSON 結構。

負責組裝與去重。

行為：

- merge duplicate component instances。
- merge duplicate evidence。
- 確保 ids deterministic。
- 組裝 `components_by_slot`。
- 組裝 `flows` and `edges`。
- 補上 recommended next checks。

deterministic id 建議：

```text
component:<slot>:<normalized-name>
evidence:<rule-id>:<relative-file>:<path-hash>
endpoint:<type>:<value-hash>
risk:<rule-id>:<target>
edge:<flow-id>:<from-slot>:<to-slot>
```

### `SystemMapValidationService`

> 白話：它負責守住 JSON schema 和 contract invariants，避免壞資料進入正式 report。

負責 contract validation。

必檢：

- JSON schema validation。
- no `confidence` anywhere。
- detected slot has evidence。
- endpoint references valid evidence。
- risk hint references valid evidence。
- flow edges reference valid slots。
- extension components have evidence or confirmed mapping。
- unmapped components have evidence and `needs_confirmation` status。
- extension edges do not create dangling references。
- evidence file path is relative POSIX。
- no unmasked secret values。

### `MarkdownSummaryService`

> 白話：它負責把 `ai_system_map.json` 轉成給人看的 Markdown 摘要，不重新掃描檔案。

只從 normalized map 產生 Markdown。

不可：

- 不重新掃描檔案。
- 不讀 raw project files。
- 不使用 unmasked value。

必要 sections：

- 系統總覽。
- RAG component slot coverage。
- 偵測到的元件與 missing slots。
- indexing flow。
- query / answer flow。
- 可能的外部 endpoint。
- 可能的 network exposure。
- 後續建議檢查項目。

### `ViewerSessionService`

> 白話：它負責把 canonical JSON 轉成 GUI 可以直接畫的 graph view model。

負責載入 map JSON 並輸出 graph view model。

規則：

- 載入 JSON 後必須再次 validate。
- invalid JSON 回傳 error state。
- graph hidden when map cannot load。
- 不掃描 project files。

輸出：

```text
ViewerLoadResult {
  loaded
  error_reason
  map_json
  graph_view_model
}
```

### `QueryTraceService`

> 白話：它負責在使用者明確觸發後呼叫 endpoint，並把結果轉成 replay events。

負責 query trace MVP。

流程：

1. 從 `RagSystemMap.endpoints` 找 `app_api_or_orchestrator` 或可用 local app endpoint。
2. 找不到 endpoint：回傳 `endpoint_not_found`，`query_sent=false`。
3. 找到 endpoint：呼叫一次，使用 bounded timeout。
4. 將 response/error 映射為 `QueryTraceEvent[]`。
5. 保留 partial replay。

Manual mapping 對 replay 的影響：

- confirmed existing slot mapping 可以直接參與 replay mapping。
- confirmed extension component 可以出現在 replay timeline，但要標示為 extension step。
- unmapped component 不應被當成確定 replay step；只能顯示為 `unknown_step` 或 `needs_confirmation`。
- 如果 trace 經過 unmapped component，replay 不應失敗，而是保留 partial replay 並提示「此步驟需要 mapping confirmation」。
- trace event 的 `slot` 可以為空，但應填 `component_id` 或 `unmapped_component_id`，避免資料遺失。

建議 trace mapping rule：

```text
trace event matches standard slot
  -> slot = retriever / vector_store / llm / ...

trace event matches confirmed extension
  -> component_id = extension_query_router
  -> step_type = extension

trace event only matches unmapped evidence
  -> unmapped_component_id = unmapped_src_router_py
  -> step_type = unknown
  -> error/warning = needs_mapping_confirmation
```

這樣 replay 仍可用，但不會把不確定模組偽裝成標準 RAG step。

## 11. Manual Mapping and AI Proposal Flow

> 白話：這一章說明 scanner 不確定時，怎麼讓使用者和 AI proposal 幫忙把 mapping 變成可重現的正式設定。

這個流程處理「scanner 掃得到 evidence，但 `rag-core-v1` 無法安全對位」的情況。

```text
scanner evidence
  -> auto mapping
  -> unmapped / needs_confirmation
  -> user selects existing slot OR writes explanation
  -> AI generates mapping proposal
  -> user confirms / edits / rejects
  -> backend validates proposal
  -> write KAI-Mind user mapping store
  -> regenerate ai_system_map.json
```

### Path A: 使用者手動選現有 map 區塊

> 白話：這條路徑適合使用者已經知道某個檔案或模組應該對到哪個既有 RAG slot。

適用情境：

- 使用者知道這個模組屬於哪個既有 RAG slot。
- scanner 只是沒有足夠 rule 自動判斷。

例子：

```text
scanner:
  src/reranker.py -> unmapped

user:
  this is retriever extension / reranker

backend:
  maps src/reranker.py to retriever with extension_type=reranker
```

結果：

- 寫入 KAI-Mind user mapping store。
- 下次 scan 可重現。
- `components_by_slot.retriever` 可引用這個 confirmed mapping。

### Path B: 使用者寫說明，AI 產生新的 extension proposal

> 白話：這條路徑適合標準 slot 裝不下的客製元件，由 AI 先建議，再讓使用者確認。

適用情境：

- 現有 `rag-core-v1` slot 裝不下。
- 模組是 query router、hybrid search、SQL retriever、Graph RAG、custom orchestration 等 extension。

使用者說明例子：

```text
這個 router 會根據問題類型決定走 vector search 還是 SQL query。
文件問題走 retriever，資料表問題走 SQL agent。
```

AI proposal 例子：

```json
{
  "proposal_type": "new_extension_component",
  "component": {
    "id": "extension_query_router",
    "name": "Query Router",
    "kind": "routing_orchestration"
  },
  "edges": [
    {
      "from": "app_api_or_orchestrator",
      "to": "extension_query_router",
      "relationship": "routes_query_by_type"
    },
    {
      "from": "extension_query_router",
      "to": "retriever",
      "relationship": "routes_document_query"
    }
  ]
}
```

後端規則：

- AI proposal 必須被使用者確認。
- 使用者確認後寫入 mapping config。
- 寫入 canonical JSON 前必須 schema validation。
- 若 proposal reference 不存在的 evidence、slot 或 edge target，必須拒絕。

### Why save mapping config instead of only editing JSON

> 白話：只改輸出 JSON 下次會失效，所以要把使用者確認過的 mapping 存成可重跑設定。

只改輸出 JSON 會造成不可重現：

```text
first scan + user correction -> JSON A
second scan without correction -> JSON B
```

保存 mapping config 後：

```text
scanner evidence + KAI-Mind user mapping store
  -> stable ai_system_map.json
```

這對 release-readiness、CI/CD、code review 都比較安全。

Epic 1 預設不是把 `kai-mind.mapping.yaml` 寫進被掃描 repo，而是使用 KAI-Mind-managed user mapping store。`kai-mind.mapping.yaml` 只作為後續 import/export 或 explicit `--mapping-file` 的交換格式。

### Reducing user friction

> 白話：這裡說明產品上不能要求使用者一開始就懂所有 RAG 架構，流程要允許先產生 partial map。

使用者可能懶得想，也可能不知道模組是什麼。產品體驗不能要求使用者一開始就理解所有 RAG 架構細節。

後端和 GUI 應共同支援低摩擦流程：

- 預設不要阻塞 scan。unmapped component 可先保留為 `needs_confirmation`，仍產生 partial map。
- 給 AI-assisted suggestion，但標示為 proposal。
- 優先提供 2-3 個可選 slot / extension，而不是要求使用者自由填 JSON。
- 顯示「為什麼 scanner 不確定」：列出 masked evidence、source file、detected pattern。
- 允許使用者選 `skip for now`，並把它保留在 recommended next checks。
- 允許批次確認類似模組，例如多個 `reranker_*` pattern 一次套用同一 mapping。
- 允許之後再補 mapping，不要求第一次 scan 完美。
- 對 high-impact unknowns 才強提醒，例如 endpoint path、retriever path、external provider。
- 對 low-impact unknowns 只放在「待確認」區，不打斷主流程。

建議 UI 文案概念：

```text
KAI-Mind 掃到 3 個尚未分類的模組。
你可以先略過，map 仍會產生；之後再補充會讓 replay 和風險提示更準。
```

工程取捨：

- 不要為了方便讓 AI 自動確認。
- 不要為了嚴格讓使用者每次都被迫分類。
- 最佳平衡是：auto suggestion + optional confirmation + persistent mapping config。

## 12. Graph View Model Boundary

> 白話：這一章說明 graph view model 是 backend projection，不是 frontend 重新判斷的一份新事實。

前端可以讀 canonical JSON 自己轉 graph，也可以由後端 thin adapter 提供 `GraphViewModel`。但 `GraphViewModel` 不能變成第二份 truth。

建議 view model：

```json
{
  "nodes": [
    {
      "id": "component:vector_store:qdrant",
      "type": "component",
      "slot": "vector_store",
      "status": "detected",
      "label": "Qdrant",
      "evidence_ids": ["evidence_qdrant_service"],
      "risk_hint_ids": ["risk_qdrant_published_port"]
    }
  ],
  "edges": [
    {
      "id": "edge:query_answer:retriever:vector_store",
      "flow_id": "query_answer",
      "from": "component:retriever:default",
      "to": "component:vector_store:qdrant",
      "relationship": "queries_vector_store"
    }
  ],
  "details": {
    "evidence": {},
    "risk_hints": {}
  }
}
```

規則：

- node 必須來自 `components_by_slot`。
- edge 必須來自 `flows.edges`。
- evidence detail 必須來自 canonical evidence。
- risk badges 必須來自 `risk_hints`。
- extension node 必須來自 `extensions`。
- unmapped node 必須來自 `unmapped_components`，並標示 `needs_confirmation`。
- filter 只 highlight，不移除 graph elements。

## 13. Error Handling

> 白話：這一章定義哪些錯誤會讓 scan 失敗，哪些錯誤只會變成 partial report。

### Fatal errors

> 白話：fatal error 代表連可信的 base map 都不能產生，只能輸出 error report。

這些錯誤會讓 map generation 失敗：

- project folder 不存在。
- project folder 不可讀。
- output directory 無法建立或寫入。
- normalized map 無法通過 schema validation。

Fatal precondition failure 輸出：

```text
outputs/map-error.md
```

內容至少包含：

- `project_path`
- `failure_reason`
- `scan_stage`

### Partial errors

> 白話：partial error 代表某些資料讀不到或解析失敗，但整份 map 仍可產生，只是要把問題記錄清楚。

這些錯誤不應讓整體掃描失敗：

- 單一 config parse error。
- Docker Compose parse error。
- 單一檔案太大。
- 單一檔案不可讀。
- optional local LLM unavailable。
- query trace timeout。
- mapping proposal 無法產生。
- manual mapping reference 已不存在。

Partial errors 必須轉成：

- evidence。
- parse issue。
- risk hint。
- warnings。

### Error classes

> 白話：這裡列出 backend 需要區分的錯誤類型，方便 CLI/GUI 顯示正確狀態。

```text
PreconditionError
OutputError
ParseError
ScanLimitError
ValidationError
EndpointNotFoundError
TraceTimeoutError
ProviderUnavailableError
MappingValidationError
```

## 14. Secret Safety

> 白話：這一章是安全底線：完整 secret 不可以出現在 JSON、Markdown、logs、snapshots、GUI。

Epic 1 後端必須有唯一 canonical `SecretMaskingService`。

所有輸出都必須通過同一套 masking：

- JSON evidence。
- endpoints。
- risk hint rationale 若包含 value。
- Markdown。
- logs。
- snapshots。
- GUI detail。
- query trace input/output/retrieved_chunks。
- mapping proposal evidence summary。
- user description 若可能含 sensitive content，寫入前也要 masking 或提示不要輸入 secrets。

建議策略：

```text
short value:
  mask whole value

long value:
  keep small prefix + suffix
  mask middle

known secret keys:
  API_KEY, TOKEN, SECRET, PASSWORD, BEARER, AUTH, OPENAI_API_KEY
```

禁止：

- log full `.env` value。
- snapshot full secret。
- PR comment full secret。
- GUI source preview 直接讀 `.env` raw content。

## 15. Observability and Logging

> 白話：這一章說明 logs 要能幫忙除錯，但不能把敏感資訊或完整 secret 打出來。

Log 要能 debug scanner stage，但不能洩漏敏感內容。

建議 structured events：

- `scan_started`
- `file_inventory_completed`
- `provider_completed`
- `component_detection_completed`
- `risk_hint_created`
- `artifact_written`
- `viewer_map_load_failed`
- `query_trace_started`
- `query_trace_step`
- `unmapped_component_created`
- `mapping_proposal_created`
- `manual_mapping_applied`
- `manual_mapping_rejected`
- `detail_scan_started`
- `detail_scan_completed`
- `detail_scan_failed`

禁止記錄：

- full secret values。
- raw request body containing sensitive query。
- full retrieved chunks by default。

## 16. Testing Strategy for Backend

> 白話：這一章定義要用哪些測試保護 scanner 行為、JSON contract、secret masking、cross-platform path。

### Unit tests

> 白話：unit tests 保護每個小規則，例如 parser、masking、validation、mapping service。

- POSIX relative path normalization。
- Secret masking。
- Config parse success/failure。
- Docker Compose service/port/env/volume parsing。
- Dependency manifest detection。
- Code pattern detection。
- ComponentDetectionService status rules。
- RiskHintService uncertainty rules。
- SystemMapValidationService invariants。
- ManualMappingService validates existing slot mapping。
- MappingProposalService only emits pending proposals。
- QueryTraceService maps confirmed extension and preserves unknown step for unmapped component。
- DetailScanService only scans target-related files。
- ComponentDetailScanService appends detail result without changing base map unexpectedly。
- CodePathScanService produces project-owned application-level path and does not traverse framework/runtime internals。

### Integration tests

> 白話：integration tests 用 sample projects 驗證完整 map build 流程。

- `kai-mind map ./fixtures/basic_qdrant_ollama_rag` writes JSON and Markdown。
- missing project writes `map-error.md` and no normal map。
- existing outputs create timestamped run directory。
- malformed compose produces partial map + parse_error evidence/risk hint。
- external OpenAI provider produces external endpoint/risk hint with masked key evidence。
- query trace missing endpoint returns `endpoint_not_found` and `query_sent=false`。
- query trace timeout preserves partial replay。
- unmapped component appears in JSON without becoming detected slot。
- confirmed manual mapping regenerates stable JSON。
- AI mapping proposal is not written to canonical JSON before user confirmation。
- L2 component detail scan appends `detail_scans[]`。
- L3 code path scan does not require whole-repo graph。
- replay depth changes when detail scan exists but replay still works without detail scan。

### Contract tests

> 白話：contract tests 確保 JSON schema 和既有 snapshots 不被不小心破壞。

- JSON schema validation for `ai-system-map/v1`。
- Golden snapshots for representative maps。
- Snapshot secret scanner。
- Reject `confidence` anywhere。
- Reject detected component without evidence。
- Reject invalid status enum。
- Reject absolute evidence file path。
- Reject extension without evidence or user-confirmed mapping。
- Reject dangling extension edge。
- Reject manual mapping to invalid slot。
- Reject detail scan target that does not exist in base map。
- Reject detail scan that introduces unvalidated canonical facts。

### Fixture projects

> 白話：fixtures 是用來模擬不同 RAG repo 型態的小專案，讓 scanner 測試有真實感。

```text
tests/fixtures/rag_projects/
  basic_qdrant_ollama_rag/
  openai_external_provider_rag/
  malformed_config_rag/
  missing_slots_rag/
  custom_router_rag/
  reranker_extension_rag/
  detail_scan_retriever_rag/
  code_path_query_rag/
  viewer_invalid_map/
```

## 17. Suggested Backend Delivery Order

> 白話：這一章把實作拆成里程碑，先做 schema 和 scanner 核心，再做 viewer、trace、hardening。

### M1: Schema and template

> 白話：第一步先把 JSON contract 和 baseline RAG template 固定下來。

交付：

- `rag-core-v1` template。
- `ai-system-map/v1` JSON schema。
- core model definitions。
- schema validation tests。

完成條件：

- invalid status 被拒絕。
- `confidence` 被拒絕。
- detected slot without evidence 被拒絕。

### M2: File inventory and providers

> 白話：第二步先能安全讀檔、跳過不該掃的檔案，並產生低階 evidence。

交付：

- `FilesystemProvider`
- `ConfigParseProvider`
- `DockerComposeProvider`
- `DependencyManifestProvider`
- initial `CodePatternProvider`

完成條件：

- fixtures 可以產生 raw facts。
- parse errors 不會讓整體 scan crash。
- secret values 已遮罩。

### M3: Detection and normalization

> 白話：第三步把 evidence 轉成 components、flows、risk hints，再整理成 canonical map。

交付：

- `ComponentDetectionService`
- `EndpointDetectionService`
- `RiskHintService`
- `SystemMapNormalizeService`
- `unmapped_components`

完成條件：

- JSON maps pass contract tests。
- Qdrant/Ollama/OpenAI fixtures 被正確映射。
- custom router fixture 被保留為 unmapped 或 extension，不硬塞 standard slot。

### M4: CLI artifacts

> 白話：第四步讓 CLI 可以產生 JSON、Markdown、error report。

交付：

- `kai-mind map`
- output directory policy。
- `ai_system_map.md`
- `map-error.md`

完成條件：

- feature `建立RAG系統地圖.feature` 的 backend scenarios 可測。

### M5: Viewer backend boundary

> 白話：第五步提供 GUI 載入 map 和 graph projection 的 backend 邊界。

交付：

- `ViewerSessionService`
- graph view model projection。
- invalid map error state result。

完成條件：

- viewer scenarios 可用 static JSON 測試。
- viewer 不掃描 project files。

### M6: Progressive detail scan

> 白話：第六步加入 L2/L3 深掃，讓使用者能對特定 component 或 path 深入。

交付：

- `DetailScanService`
- `ComponentDetailScanService`
- `CodePathScanService`
- `detail_scans[]` contract。

完成條件：

- L1 scan 先產生 base map。
- 使用者可針對 component / unmapped component 觸發 L2。
- 使用者可針對 edge / trace event 觸發 L3。
- L2/L3 結果只補 detail，不破壞 base map contract。

### M7: Query trace backend MVP

> 白話：第七步做 opt-in query trace，讓 replay 能呈現 endpoint 呼叫結果。

交付：

- endpoint selection。
- endpoint call with timeout。
- `QueryTraceEvent[]` mapping。
- `endpoint_not_found` behavior。
- confirmed extension / unmapped trace mapping rules。

完成條件：

- missing endpoint 不送出 query。
- timeout/error 保留 partial replay。
- trace 進入 unmapped component 時保留 unknown step，不讓 replay 失敗。
- detail scan 存在時，replay 可以顯示更細 steps；detail scan 不存在時仍顯示 coarse replay。

### M8: Hardening

> 白話：最後一步補強跨平台、secret safety、logging、mapping validation、target validation。

交付：

- cross-platform path tests。
- snapshot secret scanner。
- structured logging。
- docs update。
- manual mapping config validation。
- progressive scan target validation。

完成條件：

- release-readiness review 沒有 P1 scanner test gaps。

## 18. 後端和前端的交付契約

> 白話：這一章說明前端可以期待 backend 給什麼，也明確禁止前端自己掃 project 或判斷 facts。

前端可以假設後端會提供：

- valid `ai_system_map.json`。
- graph view model 或足夠欄位讓前端自行轉 graph。
- invalid map 的 error state。
- query trace request result。
- unmapped components and mapping proposal result。
- detail scan request/result。

前端不可以假設：

- 可以直接讀 project folder。
- 可以自行判斷 component 是否存在。
- 可以顯示 unmasked secrets。
- 可以把 hidden graph nodes 當成 filter 行為；Epic 1 filter 是 highlight。
- 可以把 AI proposal 當成已確認 facts。

後端可以假設前端會：

- 依照 JSON contract 顯示 nodes/edges/details。
- 對 invalid map 顯示 error state。
- 對 query trace events 做 replay controls。
- 讓使用者確認、修改或拒絕 mapping proposal。
- 讓使用者從 graph node / edge / trace step 觸發 detail scan。

## 19. 已決策事項與深入討論記錄

> 白話：這一章是決策紀錄，列出 implementation 前已經定案的架構選擇和原因。

以下決策已在 implementation 前定案。這一節是 Epic 1 backend 的決策記錄，後續實作若要偏離，必須更新本節並說明 migration / compatibility impact。

### 19.1 決策總表

> 白話：這張表把 13 個已定案的選擇放在一起，方便 implementation 時快速查。

| # | 決策題目 | 決策 |
|---|---|---|
| 1 | 實作語言 | Python |
| 2 | JSON schema 檔案位置 | `schemas/ai-system-map.v1.schema.json` |
| 3 | `GraphViewModel` 轉換責任 | backend `ViewerSessionService` 轉，frontend 只渲染 |
| 4 | Query trace 入口 | CLI + GUI 都支援，但預設關閉，必須明確 opt-in |
| 5 | 預設 scan scope | 掃完整 eligible project files，排除明顯不相關或高成本檔案 |
| 6 | Evidence snippets | 支援 safe short snippets，必須 masking、限長、標行號，且可關閉 |
| 7 | `Project.root_path` | CI / report artifact 支援 redacted mode；local interactive 可保留 absolute path |
| 8 | `extensions` / `unmapped_components` | 正式納入 `ai-system-map/v1` top-level fields |
| 9 | Manual mapping store | 預設存於 KAI-Mind-managed user mapping store，不寫入被掃描 repo |
| 10 | AI mapping proposal | Epic 1 中後半段實作；必須 user confirmation 後才生效 |
| 11 | replay extension / unknown step | manual selection 前顯示 `Unknown / Needs confirmation`；確認後顯示正式 extension |
| 12 | L2 / L3 結果保存 | Epic 1 先寫回同一份 `ai_system_map.json`，之後再評估拆 artifact |
| 13 | Progressive scan / replay 顆粒度 | 明確定義 L1 / L2 / L3 的輸入、範圍、輸出、停止邊界與 uncertainty |

### 19.2 實作語言：Python

> 白話：這裡記錄為什麼 core scanner 選 Python，而不是 TypeScript。

Epic 1 backend 採 Python。

理由：

- Epic 1 核心是 local scanner、RAG project pattern detection、schema validation、CLI、parser rules。
- Python 與 RAG / AI backend 生態較貼近，較容易偵測 LangChain、LlamaIndex、OpenAI SDK、vector store client 等常見 patterns。
- Python standard library 的 `ast` 可支援 bounded source analysis。
- FastAPI / Pydantic 可支援 typed models、validation、OpenAPI / JSON Schema 相關工作。

TypeScript 可以留給 frontend / viewer 實作，但 core scanner 不應依賴 frontend runtime。

### 19.3 JSON schema 位置

> 白話：這裡記錄 schema 要放在 repo root 的 `schemas/`，因為它是跨系統 contract。

`ai-system-map/v1` schema 放在：

```text
schemas/ai-system-map.v1.schema.json
```

理由：

- `ai_system_map.json` 是跨 CLI、GUI、CI/CD、Markdown report、後續 Epic 的正式 contract。
- schema 不應只藏在 Python package 內部。
- frontend、tests、docs、external validators 都應可直接引用同一份 schema。

schema 應包含穩定 dialect / id：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://kai-mind.local/schemas/ai-system-map.v1.schema.json"
}
```

### 19.4 `GraphViewModel` 由 backend 轉

> 白話：這裡記錄 graph projection 的語意規則由 backend 管，frontend 只管畫。

`GraphViewModel` 由 backend `ViewerSessionService` 從 canonical `ai_system_map.json` 轉出。

理由：

- graph projection 含有 backend domain semantics，不只是視覺 layout。
- 哪些 node 是 standard slot、extension、unmapped、risk hint badge、replay depth，應由 backend contract 決定。
- frontend 不應自行判斷 component 是否存在，也不應重新掃描 project files。
- snapshot tests 可以直接驗證 graph projection，避免 CLI / Markdown / GUI 顯示不同一套 facts。

frontend 負責：

- layout
- styling
- interaction
- expand / collapse
- highlight / filter display state

frontend 不負責：

- 判斷 slot 是否 detected
- 把 unmapped component 自行升級成 extension
- 重新解析 project files

### 19.5 Query trace：CLI + GUI 支援，但 opt-in

> 白話：這裡記錄 trace 可以用 CLI/GUI 觸發，但預設不會呼叫任何 endpoint。

Epic 1 支援 CLI 與 GUI query trace，但預設關閉，必須明確 opt-in。

理由：

- query trace 會呼叫 endpoint，可能觸發 local service side effect、timeout、敏感 query / response 記錄風險。
- release-readiness 工具仍需要 headless / CI 可重現能力，因此不能只做 GUI。

建議介面：

```text
kai-mind map <project_path> --trace-endpoint http://localhost:8000/query
```

或拆成更清楚的命令：

```text
kai-mind trace <map_json> --endpoint-id query_api --query "..."
```

規則：

- trace 預設關閉。
- 使用者必須明確指定 endpoint / endpoint id。
- trace input / output / retrieved chunks 必須經過 secret masking。
- timeout / error 必須回傳 partial replay event，不得讓 viewer 空白。
- query / model runtime timeout 與 static scan limits 分開設定。

### 19.6 預設 scan scope：掃 eligible project files

> 白話：這裡記錄預設掃整個可掃範圍，但跳過 dependency、build、binary、large output 這類高成本檔案。

預設策略不是盲目掃整個 repo，也不是只掃高相關檔案。Epic 1 採：

```text
scan all eligible project files
skip clearly irrelevant or high-cost files by default
```

Eligible files 包含：

- git-tracked files，若是 git repo。
- 若不是 git repo，fallback recursive listing。
- config files。
- Docker / Compose / infra entry files。
- dependency manifests。
- README / docs。
- source files。
- notebooks 的 bounded metadata / source cells。
- tests / fixtures 中可提供 scanner evidence 的小型檔案。

預設排除：

- `.git`
- `node_modules`
- `.venv` / `venv`
- `__pycache__`
- `dist` / `build` / `target` / `.next`
- `coverage`
- binary files
- large logs
- model weights
- minified / generated files
- obviously generated snapshots or large test outputs

Git repo 建議用：

```text
git ls-files --cached --others --exclude-standard
```

非 Git repo 建議：

```text
Python pathlib/os.walk + .gitignore matcher + hard exclusions
```

重要規則：

- skipped files 必須記錄 reason。
- 使用者可透過 include / exclude 設定覆蓋預設。
- L2 / L3 仍需 target-scoped，不因 L1 掃 eligible files 而變成 whole-repo call graph。

### 19.7 Evidence snippets

> 白話：這裡記錄 evidence 可以附短片段，但必須遮罩、限長、可關閉。

`Evidence` 可包含 safe short snippet，但必須嚴格限制。

建議欄位：

```json
{
  "file": "src/api.py",
  "line_start": 42,
  "line_end": 44,
  "snippet": "@app.post(\"/query\")\ndef query(...):\n    ..."
}
```

規則：

- snippet 必須先經過 `SecretMaskingService`。
- default mode 只允許 safe snippets。
- 建議上限：3-5 lines 或 300 chars。
- `.env` actual values 不輸出 snippet。
- private key、token-like strings、raw retrieved documents、large prompt / sample data 不輸出 snippet。
- CLI 必須支援 `--no-snippets` 或等價設定。
- JSON、Markdown、GUI 都讀同一份 masked snippet，不各自重新讀原始檔。

理由：

- release-readiness report 必須 evidence-based。
- 使用者拿到陌生 repo 時，只有 file / line / rule_id 不足以快速 review scanner 判斷。
- safe snippet 能提升可審查性，但不能犧牲 secret safety。

### 19.8 `Project.root_path` redacted mode

> 白話：這裡記錄 CI/report 不能暴露使用者本機或 runner 的完整路徑。

`Project.root_path` 在 local interactive mode 可保留 absolute path，但 CI / report artifact 必須支援 redacted mode。

理由：

- absolute path 可能暴露 username、客戶名稱、內部目錄結構、CI runner path。
- evidence path 仍必須永遠是 project-relative POSIX path。

建議：

```json
{
  "project": {
    "root_path": "<redacted>",
    "root_path_redacted": "<project_root>",
    "path_mode": "redacted"
  }
}
```

local interactive 可使用：

```json
{
  "project": {
    "root_path": "/Users/alice/projects/customer-rag",
    "root_path_redacted": "<project_root>",
    "path_mode": "local_absolute"
  }
}
```

### 19.9 `extensions` / `unmapped_components` 正式納入 v1

> 白話：這裡記錄 extension 和 unmapped 是正式 contract，不是實驗欄位。

`extensions` / `unmapped_components` 是 `ai-system-map/v1` 的正式 top-level fields，不放 experimental namespace。

理由：

- 真實 RAG 系統常有 reranker、query router、hybrid search、SQL retriever、graph retriever、cache、memory、tool calling 等非 baseline 元件。
- 如果沒有 `extensions`，scanner 容易把非標準元件硬塞進 standard slot。
- 如果沒有 `unmapped_components`，scanner 遇到 ambiguous evidence 時只能誤判或丟 evidence。

規則：

- `extensions` 必須有 evidence 或 user-confirmed mapping。
- `unmapped_components` 必須有 evidence。
- `unmapped_components` 不可計入 detected standard slot。
- AI proposal 未經使用者確認不可進入 canonical facts。

### 19.10 Manual mapping：KAI-Mind-managed user mapping store

> 白話：這裡記錄 manual mapping 預設存在 KAI-Mind 自己的 store，不污染被掃描 repo。

Manual mapping 預設存於 KAI-Mind-managed user mapping store，不寫入被掃描 repo。

決策理由：

- scanner / readiness gate 預設應 read-only。
- 不應污染客戶 repo、第三方 repo、demo repo。
- output directory 是 report artifact，不應成為下一次 scan 的設定來源。
- project root mapping 容易產生「是否要 commit」和權限問題。
- 使用者在 GUI 確認 mapping 後，應由 KAI-Mind 自己管理這份使用者設定。

建議儲存位置可以是 app data store，例如：

```text
~/Library/Application Support/KAI-Mind/mappings.db
```

或檔案型 store：

```text
~/.kai-mind/mappings/<project_id>/kai-mind.mapping.yaml
```

`project_id` 應避免只用 project name，建議由以下資訊組合產生 hash：

```text
resolved_root_path + git_remote_url + optional git_root
```

規則：

- default scan read-only，不寫被掃描 repo。
- GUI manual selection 後寫入 KAI-Mind user mapping store。
- report 只記錄 mapping source / digest，不把 output artifact 當 source of truth。
- CI / team sharing 的 import/export 或 `--mapping-file` 留到後續功能。

建議 report metadata：

```json
{
  "mapping_config": {
    "source": "kai_mind_user_store",
    "digest": "sha256:..."
  }
}
```

### 19.11 AI mapping proposal 分期

> 白話：這裡記錄 AI proposal 會做，但先做 manual selection，AI 建議必須等使用者確認。

Epic 1 會實作 AI mapping proposal，但排在中後半段。

分期：

```text
Epic 1 baseline:
  manual selection first

Epic 1 later milestone:
  AI mapping proposal suggests mappings
  proposal status = pending_user_confirmation
  user must accept / edit / reject
  accepted mapping enters KAI-Mind user mapping store
```

硬性規則：

- AI proposal 不可直接寫入 canonical JSON。
- AI proposal 不可直接把 `unmapped_component` 升級成 detected slot / extension。
- user confirmation + evidence + validation 後，才可重新 normalize 成 canonical map。

### 19.12 Replay 對 unknown / extension step 的呈現

> 白話：這裡記錄未確認前顯示 Unknown，確認後才顯示正式 extension。

Replay 必須同時處理 manual selection 前與後。

manual selection 前：

```text
User query
  -> API
  -> Retriever
  -> Unknown / Needs confirmation
  -> LLM
  -> Response
```

manual selection 後：

```text
User query
  -> API
  -> Retriever
  -> Reranker
  -> LLM
  -> Response
```

規則：

- manual selection 前，不可把 ambiguous evidence 顯示成 confirmed extension。
- manual selection 前，也不可把 unknown step 藏起來，否則使用者會誤以為 flow 已完整確認。
- manual selection 後，KAI-Mind 重新 normalize / regenerate `ai_system_map.json`。
- 新版 map 才顯示正式 extension step。

### 19.13 L2 / L3 結果保存

> 白話：這裡記錄初版把深掃結果先放回同一份 JSON，未來再拆附件檔。

Epic 1 先採簡單策略：L2 / L3 progressive scan results 寫回同一份 `ai_system_map.json` 的 `detail_scans[]`。

理由：

- 初版實作簡單。
- viewer 不需要合併多份 artifact。
- canonical JSON 仍是 GUI / CLI / Markdown 的單一讀取入口。

Guardrails：

- `detail_scans[]` 只能放 bounded summary + masked evidence。
- 不放大量原始碼。
- 不放長 trace。
- 不放 unmasked data。
- 不允許 detail scan 繞過 schema validation 改寫 canonical facts。

後續若 detail data 變大，可 migration 到：

```text
ai_system_map.json:
  detail_scans[] summary + artifact_path

detail_scan_results/*.json:
  full detail artifacts
```

### 19.14 Progressive scan / replay 顆粒度

> 白話：這裡記錄 L1/L2/L3 的邊界，避免 L3 被誤做成完整 call graph。

Epic 1 明確定義 L1 / L2 / L3 的輸入、分析範圍、輸出、停止邊界與 uncertainty。

這個分層不是任意命名，而是根據真實 RAG repo 常見結構整理而來：

- production-style RAG app 常同時有 backend routes、approach/service classes、prompt templates、infra、frontend、tests、sample data。
- tutorial-style RAG app 常把 indexing flow 和 query flow 分成不同 scripts。
- notebook-heavy RAG app 可能主要 evidence 都在 `.ipynb` cells。
- LangChain / LlamaIndex / Haystack 等生態通常以 ingestion / indexing / retrieval / generation / component pipeline 描述 RAG。

#### L1: System Map Scan / `coarse_replay`

> 白話：L1 是系統地圖層，只看 RAG 元件和 slot 關係，不追 function path。

Input：

```text
project_path
```

Scope：

```text
eligible project files
config / env example
Docker / Compose / infra entry files
dependency manifests
README / docs
bounded source patterns
bounded notebook source cells
```

Output：

```text
components_by_slot
endpoints
flows
extensions
unmapped_components
risk_hints
recommended_next_checks
coarse_replay events
```

Boundary：

```text
不追完整 function call path
不深入 framework internals
不深入 third-party library internals
不呼叫 runtime endpoint
```

Uncertainty：

```text
missing evidence
skipped files
ambiguous mapping
unmapped components
network exposure uncertainty
```

Replay 顆粒度：

```text
User query
  -> API / Orchestrator
  -> Retriever
  -> Vector Store
  -> Prompt Builder
  -> LLM
  -> Response
```

#### L2: Component Detail Scan / `component_replay`

> 白話：L2 是元件細節層，只針對使用者選到的 component 補 evidence 和關係。

Input：

```text
selected component slot
selected extension
selected unmapped component
```

Scope：

```text
target evidence files
nearby imports
nearby config references
direct input/output hints
component-specific patterns
```

Examples：

```text
retriever:
  vector store client
  top_k
  score threshold
  reranker signal
  query rewrite signal

llm:
  provider
  model/deployment config
  streaming flag
  response token limit

prompt_builder:
  prompt templates
  context injection
  citation instructions
```

Output：

```text
detail_scans[] findings
additional evidence
mapping proposal candidates
component-level replay events
```

Boundary：

```text
只分析 target 相關檔案
不做 whole-repo call graph
不深入 third-party internals
```

Uncertainty：

```text
ambiguous mapping
unsupported framework pattern
dynamic config
manual confirmation needed
```

Replay 顆粒度：

```text
User query
  -> /chat endpoint
  -> Chat Approach
  -> Query Rewrite
  -> Azure AI Search Retriever / Vector Store
  -> Prompt Template
  -> LLM Provider
  -> Response Composer
```

#### L3: Code Path Scan / `code_path_replay`

> 白話：L3 是 application code path 層，只追 project-owned 主要 hop，不追 framework/runtime internals。

Input：

```text
selected edge
selected endpoint
selected trace step
selected evidence
```

Scope：

```text
project-owned application-level code path
main RAG hops
endpoint / edge / evidence related files
```

Output：

```text
file:function path
edge validation evidence
partial path if incomplete
code_path_replay events
```

Boundary：

```text
不追 FastAPI / Quart / Express internal dispatch
不追 LangChain / LlamaIndex / Haystack internals
不追 Azure / OpenAI / Qdrant / Chroma client internals
不追 HTTP client internals
max application hops / max project files 只作為保險
```

Uncertainty：

```text
dynamic dispatch
dependency injection
framework magic
third-party boundary
limit hit
partial path
```

Replay 顆粒度：

```text
app.py:chat()
  -> ChatReadRetrieveReadApproach.run()
  -> run_search_approach()
  -> search()
  -> build_conversation()
  -> create_response()
```

L3 的核心定義：

```text
L3 = project-owned application-level code path
L3 != full framework/runtime call graph
```

### 19.15 參考依據

> 白話：這裡列出本節決策參考過的官方文件和真實 RAG repo。

本節決策參考了以下公開資料與實際 repo 結構：

- JSON Schema structuring / `$id` / `$schema`: https://json-schema.org/understanding-json-schema/structuring.html
- FastAPI Python types / validation: https://fastapi.tiangolo.com/python-types/
- Python `ast`: https://docs.python.org/3/library/ast.html
- Git `ls-files --exclude-standard`: https://git-scm.com/docs/git-ls-files.html
- Git ignore rules: https://git-scm.com/docs/gitignore.html
- ripgrep ignore / hidden / binary behavior: https://ripgrep.dev/docs/getting-started/
- Semgrep ignore and scan performance references: https://semgrep.dev/docs/ignoring-files-folders-code
- Azure Search OpenAI Demo repo: https://github.com/Azure-Samples/azure-search-openai-demo
- LangChain RAG tutorial repo: https://github.com/pixegami/langchain-rag-tutorial
- LangChain rag-from-scratch repo: https://github.com/langchain-ai/rag-from-scratch
- LlamaIndex RAG overview: https://docs.llamaindex.ai/en/stable/understanding/rag/
- Haystack components overview: https://docs.haystack.deepset.ai/v2.0/docs/components_overview

## 20. Backend Acceptance Checklist

> 白話：這是完成 Epic 1 backend 前的驗收清單，每一項都應能被測試或人工驗證。

- [ ] `kai-mind map <project_path>` 可以產生 `ai_system_map.json`。
- [ ] `ai_system_map.json` 通過 `ai-system-map/v1` schema validation。
- [ ] `ai_system_map.json` 不包含 `confidence`。
- [ ] 每個 `detected` component 都有 evidence。
- [ ] 沒有 evidence 的 slot 不會被標示為 `detected`。
- [ ] evidence file path 是 project-relative POSIX path。
- [ ] secret-like values 已遮罩。
- [ ] config/Docker parse failure 會產生 partial map、evidence、risk hint。
- [ ] outputs 已存在時不覆寫，改用 timestamped directory。
- [ ] missing project 只輸出 `map-error.md`，不輸出正常 map。
- [ ] viewer load invalid JSON 時回傳 error state。
- [ ] viewer graph projection 不重新掃描 project files。
- [ ] query trace 找不到 endpoint 時回傳 `endpoint_not_found` 且不送出 query。
- [ ] query trace timeout/error 保留 partial replay。
- [ ] unmapped component 不會被硬塞成 detected standard slot。
- [ ] AI mapping proposal 未經使用者確認不會進入 canonical JSON。
- [ ] confirmed manual mapping 可寫入 KAI-Mind user mapping store 並在下次 scan 重現。
- [ ] replay 遇到 extension component 可顯示 extension step。
- [ ] replay 遇到 unmapped component 可顯示 unknown/needs_confirmation step，不會失敗。
- [ ] L1 coarse scan 可以先產生 base `ai_system_map.json`。
- [ ] L2 component detail scan 只掃 target 相關檔案。
- [ ] L3 code path scan 是 project-owned application-level path，不做 whole-repo / framework runtime call graph。
- [ ] `detail_scans[]` 不會繞過 schema validation 改寫 canonical facts。
- [ ] backend tests 使用 sample projects / fixtures。

## 21. 對後端工程師的實作提醒

> 白話：最後收斂成最重要的工程提醒：facts 要有 evidence，JSON 是唯一事實來源，GUI 只是 projection。

Epic 1 後端最容易出錯的地方不是 parser 寫不出來，而是 contract 邊界被模糊化。

需要守住三條線：

```text
1. Scanner facts must be evidence-based.
2. ai_system_map.json is the source of truth.
3. GUI graph is only a projection of JSON.
```

只要這三條線穩定，後續 Runtime Readiness、Privacy & Exposure、RAG Knowledge Trust、Release Gate 才能建立在同一份可信事實層上。
