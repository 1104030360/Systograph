# Understand-Anything `/understand` 可視化流程圖

> Canonical pipeline（已驗證版）
> 來源：`skills/understand/SKILL.md`、`agents/*.md`、`packages/dashboard/`

在 IDE 開啟本檔 Markdown Preview 即可渲染 Mermaid 圖。

---

## 圖 1：主管線總覽（Phase 0 → Dashboard）

```mermaid
flowchart TD
    START(["/understand [path]"])
    ORCH["主 Session / Orchestrator<br>讀取 skills/understand/SKILL.md"]

    P0["Phase 0 Pre-flight<br>full / incremental / review<br>目錄 · 語言 · config"]
    P05["Phase 0.5 Ignore<br>generate-ignore.mjs"]
    P1["Phase 1 Project Scan<br>project-scanner"]
    P15["Phase 1.5 Batch<br>compute-batches.mjs"]
    P2["Phase 2 File Analysis<br>file-analyzer × ≤5 並行"]
    MERGE["merge-batch-graphs.py"]
    P3["Phase 3 Assemble Review<br>assemble-reviewer"]
    P4["Phase 4 Architecture<br>architecture-analyzer"]
    P5["Phase 5 Tour<br>tour-builder"]
    P6["Phase 6 組裝與驗證<br>inline validate 或 graph-reviewer"]
    P7["Phase 7 儲存<br>knowledge-graph.json · meta · fingerprints"]
    DASH["Dashboard<br>Vite 127.0.0.1:5173/?token=…<br>ReactFlow 渲染"]

    A0[".understandignore"]
    A1["scan-result.json"]
    A15["batches.json"]
    A2B["batch-N.json"]
    A2M["assembled-graph.json"]
    A3["assemble-review.json"]
    A4["layers.json"]
    A5["tour.json"]
    A6["review.json"]
    A7["knowledge-graph.json"]

    START --> ORCH --> P0 --> P05 --> P1 --> P15 --> P2 --> MERGE --> P3 --> P4 --> P5 --> P6 --> P7 --> DASH

    P05 --> A0
    P1 --> A1
    P15 --> A15
    P2 --> A2B
    MERGE --> A2M
    P3 --> A3
    P4 --> A4
    P5 --> A5
    P6 --> A6
    P7 --> A7
    A7 --> DASH

    classDef orch fill:#f9e0fb,stroke:#c442c4,stroke-width:2px,color:#1f2937;
    classDef phase fill:#eef6fb,stroke:#2980b9,stroke-width:2px,color:#1f2937;
    classDef agent fill:#fdebd0,stroke:#d68910,stroke-width:2px,color:#1f2937;
    classDef script fill:#d4e6f1,stroke:#1e6fa8,stroke-width:2px,color:#1f2937;
    classDef artifact fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#1f2937;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#1f2937;

    class ORCH orch;
    class P0,P05,P15,P6,P7 phase;
    class P1,P2,P3,P4,P5 agent;
    class MERGE script;
    class A0,A1,A15,A2B,A2M,A3,A4,A5,A6,A7 artifact;
    class DASH ui;
```

---

## 圖 2：Phase 展開（Agent · Script · 產物）

```mermaid
flowchart TB
    subgraph P0["Phase 0 — Pre-flight"]
        direction TB
        O0["Orchestrator 直接執行"]
        O0 --> D0{"full / incremental / review-only"}
    end

    subgraph P05["Phase 0.5 — Ignore"]
        S05["generate-ignore.mjs"]
        S05 --> F05[".understandignore"]
    end

    subgraph P1["Phase 1 — Project Scan"]
        AG1["project-scanner agent"]
        S11["scan-project.mjs<br>列檔 · 語言 · 分類 · 行數"]
        S12["extract-import-map.mjs<br>內部 imports"]
        L11["LLM 讀 README / manifest<br>專案描述"]
        AG1 --> S11 --> S12 --> L11
        L11 --> F1["scan-result.json"]
    end

    subgraph P15["Phase 1.5 — Batch"]
        S15["compute-batches.mjs<br>依 import graph 分批"]
        S15 --> F15["batches.json"]
    end

    subgraph P2["Phase 2 — File Analysis（≤5 並行）"]
        direction TB
        AG2["file-analyzer agent<br>（每 batch 一個）"]
        S21["extract-structure.mjs"]
        L21["LLM 補 summary · tags · semantic edges"]
        AG2 --> S21 --> L21
        L21 --> F2N["batch-N.json"]
        F2N --> S22["merge-batch-graphs.py<br>合併 · 修正 ID · 去重<br>移除 dangling · importMap 補邊"]
        S22 --> F2M["assembled-graph.json"]
    end

    subgraph P3["Phase 3 — Assemble Review"]
        AG3["assemble-reviewer agent"]
        AG3 --> F3R["assemble-review.json"]
        AG3 --> F2M
    end

    subgraph P4["Phase 4 — Architecture"]
        AG4["architecture-analyzer agent"]
        S41["script：路徑 · import graph · fan-in/out"]
        L41["LLM：邏輯架構分層"]
        AG4 --> S41 --> L41 --> F4["layers.json"]
    end

    subgraph P5["Phase 5 — Tour"]
        AG5["tour-builder agent"]
        S51["script：graph topology"]
        L51["LLM：導覽順序"]
        AG5 --> S51 --> L51 --> F5["tour.json"]
    end

    subgraph P6["Phase 6 — 組裝與驗證"]
        O6["Orchestrator inline 合併<br>nodes + edges + layers + tour"]
        V6{"驗證方式"}
        V6D["ua-inline-validate.cjs<br>（預設）"]
        V6R["graph-reviewer agent<br>（--review）"]
        O6 --> V6
        V6 --> V6D
        V6 --> V6R
        V6D --> F6["review.json"]
        V6R --> F6
    end

    subgraph P7["Phase 7 — 儲存"]
        O7["build-fingerprints.mjs<br>寫 knowledge-graph.json · meta.json<br>cleanup intermediate/tmp"]
        O7 --> F7["knowledge-graph.json"]
    end

    subgraph UI["Dashboard（無 AI）"]
        VITE["Vite middleware<br>平行 fetch 多 JSON"]
        RF["ReactFlow layout<br>瀏覽器端畫圖"]
        FC["/file-content.json<br>點節點才 lazy fetch"]
        VITE --> RF --> FC
    end

    P0 --> P05 --> P1 --> P15 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> UI

    classDef orch fill:#f9e0fb,stroke:#c442c4,stroke-width:2px,color:#1f2937;
    classDef agent fill:#fdebd0,stroke:#d68910,stroke-width:2px,color:#1f2937;
    classDef script fill:#d4e6f1,stroke:#2980b9,stroke-width:2px,color:#1f2937;
    classDef llm fill:#fce4ec,stroke:#e91e63,stroke-width:2px,color:#1f2937;
    classDef artifact fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#1f2937;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#1f2937;

    class O0,O6,O7 orch;
    class AG1,AG2,AG3,AG4,AG5,V6R agent;
    class S05,S11,S12,S15,S21,S22,S41,S51,V6D script;
    class L11,L21,L41,L51 llm;
    class F05,F1,F15,F2N,F2M,F3R,F4,F5,F6,F7 artifact;
    class VITE,RF,FC ui;

    style P0 fill:#f4f4f5,stroke:#71717a,color:#1f2937,stroke-width:2px;
    style P05 fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    style P1 fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style P15 fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    style P2 fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style P3 fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style P4 fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style P5 fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style P6 fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:2px;
    style P7 fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:2px;
    style UI fill:#eefaf7,stroke:#1abc9c,color:#1f2937,stroke-width:2px;
```

---

## 圖 3：資料流（JSON 演進）

```mermaid
flowchart LR
    subgraph Scan["掃描"]
        SR["scan-result.json<br>files · importMap"]
    end

    subgraph Batch["分批"]
        BT["batches.json"]
    end

    subgraph Analyze["分析"]
        EX["ua-file-extract-*.json<br>structure facts"]
        BN["batch-*.json<br>semantic fragments"]
    end

    subgraph Merge["合併"]
        AG["assembled-graph.json"]
    end

    subgraph Enrich["補強"]
        AR["assemble-review.json"]
        LY["layers.json"]
        TR["tour.json"]
    end

    subgraph Final["最終"]
        RV["review.json"]
        KG["knowledge-graph.json<br>nodes · edges · layers · tour"]
    end

    subgraph View["呈現"]
        DB["Dashboard ReactFlow"]
    end

    SR --> BT --> EX --> BN --> AG
    AG --> AR
    AG --> LY
    AG --> TR
    LY --> KG
    TR --> KG
    AG --> RV
    RV --> KG
    KG --> DB

    classDef scan fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    classDef data fill:#fdf2e9,stroke:#e67e22,color:#1f2937,stroke-width:2px;
    classDef final fill:#fdebd0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,color:#1f2937,stroke-width:2px;

    class SR,BT scan;
    class EX,BN,AG,AR,LY,TR,RV data;
    class KG final;
    class DB ui;

    style Scan fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:1px;
    style Batch fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:1px;
    style Analyze fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:1px;
    style Merge fill:#fef6ef,stroke:#e67e22,color:#1f2937,stroke-width:1px;
    style Enrich fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:1px;
    style Final fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:1px;
    style View fill:#eefaf7,stroke:#1abc9c,color:#1f2937,stroke-width:1px;
```

---

## 圖 4：Subagent 與執行者對照

```mermaid
flowchart LR
    subgraph Orchestrator["Orchestrator（主 session）"]
        O["SKILL.md 編排"]
    end

    subgraph Agents["Subagents（LLM worker）"]
        A1["project-scanner"]
        A2["file-analyzer"]
        A3["assemble-reviewer"]
        A4["architecture-analyzer"]
        A5["tour-builder"]
        A6["graph-reviewer<br>（可選）"]
    end

    subgraph Direct["Orchestrator 直接跑腳本"]
        D1["generate-ignore.mjs"]
        D2["compute-batches.mjs"]
        D3["merge-batch-graphs.py"]
        D4["inline validate / fingerprints"]
    end

    O --> A1
    O --> A2
    O --> A3
    O --> A4
    O --> A5
    O --> A6
    O --> D1
    O --> D2
    O --> D3
    O --> D4

    classDef orch fill:#f9e0fb,stroke:#c442c4,stroke-width:2px,color:#1f2937;
    classDef agent fill:#fdebd0,stroke:#d68910,stroke-width:2px,color:#1f2937;
    classDef script fill:#d4e6f1,stroke:#2980b9,stroke-width:2px,color:#1f2937;

    class O orch;
    class A1,A2,A3,A4,A5,A6 agent;
    class D1,D2,D3,D4 script;

    style Orchestrator fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:2px;
    style Agents fill:#fef8f0,stroke:#d68910,color:#1f2937,stroke-width:2px;
    style Direct fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
```

---

## 圖例

| 顏色 | 意義 |
|------|------|
| 粉紫 | Orchestrator / 主 session 編排 |
| 橘黃 | LLM Subagent |
| 藍色 | 確定性腳本（.mjs / .py / .cjs） |
| 橘色 | JSON artifact |
| 綠色 | Dashboard / ReactFlow（無 AI） |

## 關鍵邊界

- **沒有 agent 產視覺圖**；`layers.json` 是邏輯分層 metadata，ReactFlow 在瀏覽器 layout。
- **Python 只在 Phase 2** merge batch；layers/tour 由 Orchestrator Phase 6 inline 組裝。
- **file-analyzer 內部**先 `extract-structure.mjs` 再 LLM；Orchestrator 不跨管線餵結構 JSON。
- **Dashboard** 啟動時平行 fetch 多 JSON；原始碼 `/file-content.json` 才按需拉取。

## 相關檔案

- `understand_anything_flow.md` — 循序圖版
- `understand_anything_architecture_detailed.md` — 元件級架構圖
- `kai_mind_flow.md` — KAI-Mind 對照
