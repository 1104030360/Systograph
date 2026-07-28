# Understand-Anything 完整運作流程圖 (Operational Flow)

> Source: `ref-opensource/Understand-Anything/understand-anything-plugin/`
> 詳細架構圖見：`understand_anything_architecture_detailed.md`
> **Canonical 可視化總圖見：`understand_anything_pipeline_visual.md`**

---

## 一、使用者視角（最簡流程）

```mermaid
flowchart LR
    A["安裝 Plugin<br>/plugin install"] --> B["/understand"]
    B --> C["掃描 repo<br>產 knowledge-graph.json"]
    C --> D["/understand-dashboard<br>啟動 Vite"]
    D --> E["瀏覽器開啟<br>127.0.0.1:5173/?token=…"]
    E --> F["互動式知識圖譜<br>點節點看 code"]
```

| 步驟 | 誰做 | 產物 |
|------|------|------|
| 安裝 | 使用者 | Claude Code 索引 `skills/` + `agents/` |
| `/understand` | Claude agent 編排 | `.understand-anything/knowledge-graph.json` |
| `/understand-dashboard` | Claude 啟動 Vite | 本機 URL（非 Claude 內嵌） |
| 瀏覽 | 使用者瀏覽器 | 讀 JSON 渲染圖（不重跑 AI） |

---

## 二、技術流程（Phase 0–7 + Dashboard）

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'noteTextColor': '#1f2937', 'actorTextColor': '#1f2937', 'signalTextColor': '#1f2937', 'labelTextColor': '#1f2937', 'loopTextColor': '#1f2937', 'altTextColor': '#1f2937'}}}%%
sequenceDiagram
    autonumber
    actor User as 使用者
    participant CC as Claude Code 主 Session
    participant Skill as SKILL.md 劇本
    participant Sub as LLM Subagent
    participant Script as .mjs / .py 腳本
    participant Core as @understand-anything/core
    participant Disk as .understand-anything/
    participant Dash as Vite Dashboard

    User->>CC: /understand [path]
    CC->>Skill: 載入 understand skill
    Note over CC,Skill: PROJECT_ROOT = CWD 或指定路徑

    rect rgb(234, 242, 248)
        Note over CC: Phase 0–0.5 Pre-flight + ignore
        CC->>Script: generate-ignore.mjs
        Script->>Disk: .understandignore
    end

    rect rgb(234, 242, 248)
        Note over CC: Phase 1 Scan
        CC->>Sub: dispatch project-scanner
        Sub->>Script: scan-project.mjs
        Script->>Core: Tree-sitter / inventory
        Script->>Disk: scan-result.json (files, importMap)
        Sub->>Sub: LLM 讀 README/manifest → 敘述欄位
    end

    rect rgb(250, 229, 211)
        Note over CC: Phase 1.5 Batch
        CC->>Script: compute-batches.mjs
        Script->>Disk: batches.json
    end

    rect rgb(232, 248, 245)
        Note over CC: Phase 2 Analyze (≤5 並行)
        loop 每個 batch
            CC->>Sub: dispatch file-analyzer
            Sub->>Script: extract-structure.mjs
            Script->>Core: AST / parsers
            Script->>Disk: ua-file-extract-results-*.json
            Sub->>Sub: LLM 讀結構 JSON → 語意 nodes/edges
            Sub->>Disk: batch-*.json
        end
        CC->>Script: merge-batch-graphs.py
        Script->>Disk: assembled-graph.json
    end

    rect rgb(253, 235, 208)
        Note over CC: Phase 3–5 語意補強
        CC->>Sub: assemble-reviewer / architecture-analyzer / tour-builder
        Sub->>Disk: layers.json, tour.json
    end

    rect rgb(245, 238, 248)
        Note over CC: Phase 6–7 Validate + Save
        CC->>Script: inline validate (+ 可選 graph-reviewer)
        CC->>Disk: knowledge-graph.json + meta.json
    end

    alt 驗證通過
        CC->>CC: invoke /understand-dashboard
        CC->>Dash: 背景 npx vite --host 127.0.0.1
        Dash-->>User: http://127.0.0.1:5173/?token=…
    else 驗證失敗
        CC-->>User: 警告，不啟動 dashboard
    end

    User->>Dash: 瀏覽器開啟 URL
    Dash->>Disk: GET /knowledge-graph.json?token=
    Dash-->>User: ReactFlow 互動圖
    User->>Dash: 點節點看原始碼
    Dash->>Disk: GET /file-content.json?token=&path=
```

---

## 三、資料演進（JSON 管線）

```mermaid
flowchart TD
    A["scan-result.json<br>inventory + importMap"] --> B["batches.json"]
    B --> C["ua-file-extract-results-*.json<br>structure facts"]
    C --> D["batch-*.json<br>semantic graph fragments"]
    D --> E["assembled-graph.json<br>merged graph"]
    E --> F["layers.json + tour.json"]
    F --> G["knowledge-graph.json<br>final product"]
    G --> H["Dashboard 讀取渲染"]
```

---

## 四、角色分工（一圖看懂）

```mermaid
flowchart TB
    subgraph AI["🟣 AI 層（Claude Code）"]
        L0["Host Orchestrator<br>讀 SKILL.md 編排"]
        L1["Subagents<br>file-analyzer 等"]
    end

    subgraph Script["🔵 腳本層（無 AI）"]
        MJS[".mjs 讀檔 + 解析"]
        PY[".py merge"]
        CORE["core: Tree-sitter"]
    end

    subgraph Data["🟠 資料層"]
        JSON["knowledge-graph.json"]
    end

    subgraph UI["🟢 視覺化層（無 AI）"]
        VITE["Vite + React Dashboard"]
    end

    L0 --> L1
    L0 --> MJS
    L1 --> MJS
    MJS --> CORE
    MJS --> PY
    L1 --> JSON
    PY --> JSON
    L0 --> JSON
    JSON --> VITE

    classDef ai fill:#f9e0fb,stroke:#c442c4,stroke-width:2px,color:#1f2937;
    classDef script fill:#d4e6f1,stroke:#2980b9,stroke-width:2px,color:#1f2937;
    classDef data fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#1f2937;
    classDef ui fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#1f2937;
    class L0,L1 ai;
    class MJS,PY,CORE script;
    class JSON data;
    class VITE ui;

    style AI fill:#fdf5ff,stroke:#c442c4,color:#1f2937,stroke-width:2px;
    style Script fill:#eef6fb,stroke:#2980b9,color:#1f2937,stroke-width:2px;
    style Data fill:#fef6ef,stroke:#e67e22,color:#1f2937,stroke-width:2px;
    style UI fill:#eefaf7,stroke:#1abc9c,color:#1f2937,stroke-width:2px;
```

---

## 五、重點釐清

| 常見誤解 | 實際 |
|----------|------|
| mjs 建立可視化 HTML | ❌ mjs 只產 JSON；UI 是預建 React app |
| 圖嵌入 Claude 介面 | ❌ 獨立 Vite dev server + 系統瀏覽器 |
| 只掃當前 repo | ⚠️ 預設 CWD，可傳 `/understand /path` |
| 腳本在底層叫 AI | ❌ **上層 AI 叫腳本** |
| Dashboard 重跑 scan | ❌ 只讀已存的 JSON |

---

## 六、與 Systograph 對照

見 `systograph_flow.md`：Systograph 由 **Python Core** 線性編排；UA 由 **IDE 內 AI agent** 依 Markdown 劇本編排。
