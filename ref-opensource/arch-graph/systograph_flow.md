# Systograph (Phase 2) 完整運作流程圖 (Operational Flow)

這張 **循序圖 (Sequence Diagram)** 展示 Systograph Phase2 active path 的標準執行生命週期。與 Understand-Anything 由 AI 主導控制流不同，Systograph 的流程是 **由 Python 核心主導的嚴格線性管線 (Linear Pipeline)**。

此圖特別強調 **Two-Phase Analysis**：先用 deterministic scripts / AST / config parser
產生結構性 facts，再由 Python service 做語意對位與五態判定。Phase2 不建立
`AssessmentOrchestrator`，也不讓 LLM 直接裁決 profile / readiness；AI semantic candidate
flow 屬 Plan 17 deferred。

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'noteTextColor': '#1f2937', 'actorTextColor': '#1f2937', 'signalTextColor': '#1f2937', 'labelTextColor': '#1f2937', 'loopTextColor': '#1f2937', 'altTextColor': '#1f2937'}}}%%
sequenceDiagram
    autonumber
    actor User as 使用者
    participant Core as Core Engine (Scanner Service)
    participant Provider as Deterministic Providers (提取層)
    participant Profile as ProfileInferenceService (Step 6)
    participant Validator as SystemMapValidationService (驗證閘口)
    participant Disk as Storage (本地磁碟)
    participant Viewer as Local Viewer (GUI)

    User->>Core: 觸發掃描指令 `systograph scan [target_repo]`
    Note over Core: 啟動不可逆的線性掃描管線

    rect rgb(234, 242, 248)
        Note right of Core: Step 1-4: 確定性掃描、橋接與證據收集 (No AI)
        Core->>Core: Precondition Check (過濾忽略名單、建立掃描邊界)
        Core->>Provider: 派發分析任務 (Config, Docker, CodePattern)
        Note over Provider: 使用 AST、正則表示式與組態檔 Parser
        Provider-->>Core: 回傳 Raw Facts & Evidence 陣列
        Core->>Core: Step 4 component bridge 產生 validated ai_system_map
    end

    rect rgb(253, 235, 208)
        Note right of Core: Step 6: Python deterministic assessment
        Core->>Profile: 傳送 validated map、evidence、catalog、confirmed mappings
        Note over Profile: 52 格五態、15 profiles、Mapping Completeness 的唯一定案 owner
        Profile-->>Core: 回傳 profile_signals.json / readiness inputs
    end

    rect rgb(245, 238, 248)
        Note right of Core: Phase 3: 嚴格驗證與原子化發布
        Core->>Validator: 傳遞豐富化後的 Draft Map
        Note over Validator: 執行鐵律：若節點狀態為 active 但無 evidence_id，立即拋出異常
        Validator-->>Core: 驗證通過
        Core->>Disk: 賦予全新 Build ID，Atomic Save 至 `ai_system_map.json`
        Core-->>User: 掃描完成，回報總結
    end

    User->>Viewer: 開啟 Local Viewer (GUI 介面)
    Viewer->>Disk: 載入 `ai_system_map.json` (Canonical Truth)
    Note over Viewer: 轉換為 GraphViewModel 投影 (剔除無效狀態)
    Viewer-->>User: 渲染五態與六啟動拓樸圖

    User->>Viewer: 在 UI 點擊特定 Agent 或 RAG 元件
    Viewer->>Disk: 根據 JSON 內的 `evidence_id` 拉取具體程式碼片段
    Viewer-->>User: 在側邊欄展示不可竄改的程式碼證據 (Read-only)
```

### 流程圖亮點解說

1. **Python 核心主導 (Core Engine)**：所有流程發起者都是 `Core Engine`。它將任務交給 deterministic Provider、ProfileInferenceService 與 Validator，徹底貫徹「LLM 不具備 Orchestration 權限」的設計。
2. **Facts 先於 Assessment**：流程強迫系統必須先取得 evidence-backed facts，才進入 Step 6 的 Python profile/reference assessment。這避免模型或前端憑空捏造不存在的架構節點。
3. **把關者 (Validator)**：在寫入硬碟前（步驟 10），Validator 扮演最後的防線，這對應了作為 Release Readiness Gate 所必需的安全與相容性檢查。
4. **前端直接讀取真理 (Viewer)**：前端不僅不跑 AI，連狀態都不必推算，完全只依賴 `ai_system_map.json` 中的 `evidence_id` 去展示證據。
