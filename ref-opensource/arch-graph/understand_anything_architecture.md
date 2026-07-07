# Understand-Anything 完整架構與資料流圖 (Architecture & Data Flow)

基於您所釐清的 `Understand-Anything` 專案底層流程，我為您繪製了這份完整的系統架構圖。本圖明確劃分了 **「AI 編排層」**、**「確定性腳本層」**、**「JSON 資料流管線」** 與 **「唯讀前端渲染層」** 的職責邊界與互動關係。

```mermaid
flowchart TD
    %% 角色與層級定義
    subgraph AI_Layer ["AI Agent Layer (Orchestration & Semantics)"]
        L0["L0: Host Orchestrator Agent<br>(Reads SKILL.md)"]
        L1_File["L1: Subagents (e.g., file-analyzer)<br>(Semantic Inferencing)"]
        L1_Arch["L1: Architecture Analyzer / Tour Builder<br>(Layering & Post-processing)"]
    end

    subgraph Script_Layer ["Deterministic Script Layer (Node / Python)"]
        L2_Scan["scan-project.mjs<br>extract-import-map.mjs"]
        L2_Extract["extract-structure.mjs<br>(AST / Fact Extraction)"]
        L2_Batch["compute-batches.mjs"]
        L2_Merge["merge-batch-graphs.py"]

        L3_Core["L3: @understand-anything/core<br>(Tree-sitter, Parsers)"]
    end

    subgraph Data_Artifacts ["JSON Artifacts Pipeline (Data Flow)"]
        JSON_Scan["scan-result.json<br>(File List & importMap)"]
        JSON_Struct["ua-file-extract-results-*.json<br>(Pure Structure Facts)"]
        JSON_Batch["batch-*.json<br>(Semantic Graph Fragments)"]
        JSON_Assembled["assembled-graph.json<br>(Merged Graph)"]
        JSON_Final["knowledge-graph.json<br>(Final Knowledge Graph)"]
    end

    subgraph Frontend ["Frontend Dashboard (Read-Only)"]
        Vite["Vite Dev Server<br>(HTTP Middleware)"]
        ReactFlow["Zustand + ReactFlow<br>(Visualizer)"]
        FileViewer["File Content Viewer<br>(Bounded Bounded Access)"]
    end

    %% 控制流與執行順序 (Phase 0 - Phase 7)
    L0 -- "1. Dispatch Phase 0-1 (掃描)" --> L2_Scan
    L2_Scan -- "Uses AST" --> L3_Core
    L2_Scan -- "Writes" --> JSON_Scan

    L0 -- "2. Trigger Phase 1.5 (分批)" --> L2_Batch
    JSON_Scan --> L2_Batch

    L0 -- "3. Trigger Phase 2 Script (擷取結構)" --> L2_Extract
    L2_Extract -- "Uses AST" --> L3_Core
    L2_Extract -- "Writes" --> JSON_Struct

    L0 -- "4. Dispatch Parallel Subagents (語意分析)" --> L1_File
    JSON_Struct --> L1_File
    L1_File -- "Writes Summary/Tags/Edges" --> JSON_Batch

    L0 -- "5. Trigger Merge Script (圖譜合併)" --> L2_Merge
    JSON_Batch --> L2_Merge
    L2_Merge -- "Outputs" --> JSON_Assembled

    L0 -- "6. Dispatch Phase 3-5 (架構分層/導覽)" --> L1_Arch
    JSON_Assembled --> L1_Arch
    L1_Arch -- "Refines & Outputs" --> JSON_Final

    %% 前端存取
    JSON_Final -. "GET /knowledge-graph.json" .-> Vite
    Vite --> ReactFlow
    ReactFlow -- "GET /file-content.json (Check Allowlist)" --> FileViewer

    %% 樣式設定（高亮區塊使用深色文字）
    classDef ai fill:#f9e0fb,stroke:#c442c4,stroke-width:2px,color:#1f2937;
    classDef script fill:#d4e6f1,stroke:#2980b9,stroke-width:2px,color:#1f2937;
    classDef json fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#1f2937;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#1f2937;

    class L0,L1_File,L1_Arch ai;
    class L2_Scan,L2_Extract,L2_Batch,L2_Merge,L3_Core script;
    class JSON_Scan,JSON_Struct,JSON_Batch,JSON_Assembled,JSON_Final json;
    class Vite,ReactFlow,FileViewer ui;

    style AI_Layer fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:2px;
    style Script_Layer fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    style Data_Artifacts fill:#fef6ef,stroke:#e67e22,color:#1f2937,stroke-width:2px;
    style Frontend fill:#eefaf7,stroke:#1abc9c,color:#1f2937,stroke-width:2px;
```

### 架構圖亮點解說

1. **粉色區域 (AI Layer)**：代表擁有語意推論與流程控制權的 Agent。最上層的 `L0: Host Orchestrator` 是整個系統的大腦，負責讀取劇本並依序調度腳本或子 Agent。
2. **藍色區域 (Script Layer)**：這是純粹 Deterministic（確定性）的苦力層。它們完全沒有 AI，只負責讀檔、切分 AST、建立 Import Map 與圖譜合併。
3. **橘色區域 (JSON Pipeline)**：完美展示了您提到的產物演進過程：從純結構 (`ua-file-extract-results-*.json`) ➡️ 透過 LLM 加上語意的圖譜碎片 (`batch-*.json`) ➡️ 最終整合成完整的 Knowledge Graph。
4. **綠色區域 (Frontend)**：明確標示了 Dashboard 只是透過 Vite 讀取 JSON 並畫圖的 UI，證明了**前端絕對不會觸發或重跑 Agent**。
