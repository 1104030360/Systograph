# KAI-Mind (Phase 2) 完整架構與資料流圖 (Architecture & Data Flow)

基於 `epic1-phase2.md` 與 2026-07-07/08 contract 修訂，這份圖只作
Understand-Anything 整合邊界的 reference diagram。權威契約仍以
`docs/design/epic1-phase2.md`、`docs/MODEL-CONTRACT.md` 與 `docs/API-GUIDE.md` 為準。

Phase2 active path 是 deterministic / Python 主導：Step 3 只產 facts/evidence，Step 4
做 canonical component bridge，Step 6 由 `ProfileInferenceService` 定案五態與
Mapping Completeness。AI semantic / `AssessmentOrchestrator` / LLM candidate flow 屬
Plan 17 deferred，不是 Plan 14 / 15 / 18 前置條件。

```mermaid
flowchart TD
    %% 角色與層級定義
    subgraph Adapters ["Interface Adapters (CLI / Web)"]
        CLI["Typer CLI<br>(Local Execution)"]
        WebAPI["FastAPI Web API<br>(Viewer Backend)"]
    end

    subgraph Core_Engine ["Core Engine Layer (Python Orchestration)"]
        Scanner["Scanner Service<br>(Two-Phase Analysis Controller)"]
        Validator["SystemMapValidationService<br>(Enforces Evidence Rules)"]
        Publisher["Atomic Publisher<br>(JSON Writer)"]
    end

    subgraph Providers ["Deterministic Extraction Layer (Evidence Gatherers)"]
        P_Code["CodePatternProvider<br>(AST / Regex)"]
        P_Config["ConfigParseProvider<br>(.env, TOML, YAML)"]
        P_Docker["DockerComposeProvider<br>(Container Topology)"]
    end

    subgraph Deferred_AI ["Deferred AI Candidate Flow (Plan 17 · Not Phase2 Gate)"]
        AI_Candidate["AI Semantic Candidate<br>(No Phase2 consumer)"]
        AI_Review["Human-reviewed future input<br>(Never canonical directly)"]
    end

    subgraph Data_Artifacts ["Immutable Data Artifacts (Canonical Truth)"]
        Facts["Raw Scan Facts & Evidence<br>(Masked / Secret-Safe)"]
        DraftMap["Draft System Map<br>(Nodes + Evidence)"]
        CanonicalJSON["ai_system_map.json<br>(Final Build Artifact)"]
    end

    subgraph Frontend ["Local Viewer UI (Dumb Renderer)"]
        VM["GraphViewModel<br>(Projection Adapter)"]
        UI["React Viewer<br>(RAG/Agent Topology)"]
        Sidebar["Evidence / Trace Panel<br>(Read-Only)"]
    end

    %% 控制流與執行順序
    CLI --> Scanner
    WebAPI --> Scanner

    %% Phase 1: Deterministic Scan
    Scanner -- "Phase 1: Dispatch Providers" --> Providers
    P_Code --> Facts
    P_Config --> Facts
    P_Docker --> Facts

    %% Mapping & Draft
    Facts -- "Step 4: Python component bridge" --> DraftMap
    Facts -- "Step 6: ProfileInferenceService" --> DraftMap
    AI_Candidate -. "Deferred only; no Phase2 write path" .-> AI_Review

    %% Validation & Publish
    Scanner -- "Trigger Validation" --> Validator
    Validator -- "Strict Rules Check" --> DraftMap
    DraftMap -- "If Valid" --> Publisher
    Publisher -- "Atomic Save" --> CanonicalJSON

    %% 前端存取
    CanonicalJSON -. "Load (Read-Only)" .-> VM
    VM --> UI
    UI -- "Select Node" --> Sidebar
    CanonicalJSON -. "Fetch Evidence Details" .-> Sidebar

    %% 樣式設定（高亮區塊使用深色文字）
    classDef core fill:#fcf3cf,stroke:#f1c40f,stroke-width:2px,color:#1f2937;
    classDef provider fill:#d4e6f1,stroke:#2980b9,stroke-width:2px,color:#1f2937;
    classDef ai fill:#fdedec,stroke:#e74c3c,stroke-width:2px,stroke-dasharray: 5 5,color:#1f2937;
    classDef json fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#1f2937;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#1f2937;

    class CLI,WebAPI,Scanner,Validator,Publisher core;
    class P_Code,P_Config,P_Docker provider;
    class AI_Candidate,AI_Review ai;
    class Facts,DraftMap,CanonicalJSON json;
    class VM,UI,Sidebar ui;

    style Adapters fill:#fefce8,stroke:#f1c40f,color:#1f2937,stroke-width:2px;
    style Core_Engine fill:#fefce8,stroke:#f1c40f,color:#1f2937,stroke-width:2px;
    style Providers fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    style Deferred_AI fill:#fef2f2,stroke:#e74c3c,color:#1f2937,stroke-width:2px;
    style Data_Artifacts fill:#fef6ef,stroke:#e67e22,color:#1f2937,stroke-width:2px;
    style Frontend fill:#eefaf7,stroke:#1abc9c,color:#1f2937,stroke-width:2px;
```

### 架構圖亮點解說

1. **黃色區域 (Core Engine)**：KAI-Mind 的大腦。這是一個嚴格的軟體工程 Pipeline，由 Python 程式碼負責編排所有流程，沒有任何 Autonomous Agent 參與流程控制。
2. **藍色區域 (Deterministic Providers)**：這才是系統獲取事實的**唯一來源**。所有的 Component 都必須基於此層抓取到的 `evidence` 才能被建立。
3. **紅色虛線區域 (Deferred AI Candidate Flow)**：不是 Phase2 active path。Plan 17 若日後重啟，也只能產生候選輸入；五態、Mapping Completeness、readiness 與 canonical truth 仍由 Python/service contract 定案。
4. **橘色區域 (Immutable Artifacts)**：資料流絕對單向。任何人工或 AI 的修改建議都必須產生一個全新的 Build ID 重新跑完 Pipeline，確保 `ai_system_map.json` 是不可回寫 (Immutable) 的最終真理。
5. **綠色區域 (Frontend Viewer)**：作為單純的投影展示。不同於 UA 的彈性語意圖，這裡的前端會強制將 JSON 轉換為 `GraphViewModel`，專注呈現 Release Readiness 相關的五態評估與網路拓樸。
