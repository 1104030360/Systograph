# RAG 對話流程 (RAG Chat Flow)

```mermaid
flowchart TD
    Start([使用者發送訊息]) --> CheckRAG{是 RAG 問題?<br/>is_rag_query}
    CheckRAG -->|否| GeneralChat[一般對話處理]
    CheckRAG -->|是| AddDate[加入今日日期<br/>Today is YYYY-MM-DD]

    GeneralChat --> CallGeneral{Power Automate<br/>可用?}
    CallGeneral -->|是| PAGeneral[AI Builder 回答]
    CallGeneral -->|否| OllamaGeneral[Ollama 回答]
    PAGeneral --> SaveContext1[儲存對話上下文]
    OllamaGeneral --> SaveContext1
    SaveContext1 --> ReturnGeneral([返回一般回答])

    AddDate --> RewriteQuery[改寫問題<br/>rewrite_query_with_aibuilder]
    RewriteQuery --> GetToolSuggestion[取得工具建議<br/>get_tool_suggestion]

    GetToolSuggestion --> ToolSuggest{建議的工具}
    ToolSuggest -->|SQLAgentTool| PrepareSQLMsg[準備 SQL 訊息]
    ToolSuggest -->|SemanticAgentTool| PrepareSemanticMsg[準備 Semantic 訊息]
    ToolSuggest -->|HybridQueryAgentTool| PrepareHybridMsg[準備 Hybrid 訊息]

    PrepareSQLMsg --> DispatchAutoGen
    PrepareSemanticMsg --> DispatchAutoGen
    PrepareHybridMsg --> DispatchAutoGen[AutoGen 分派<br/>autogen_dispatch]

    DispatchAutoGen --> ClassifierAgent[Classifier Agent<br/>路由決策]
    ClassifierAgent --> RouteDecision{路由決策}

    RouteDecision -->|SQL| SQLAgentHandle[sql_agent_handle]
    RouteDecision -->|Semantic| SemanticAgentHandle[semantic_agent_handle]
    RouteDecision -->|Hybrid| HybridAgentHandle[hybrid_agent_handle]

    SQLAgentHandle --> SQLProcess[SQL 處理流程]
    SemanticAgentHandle --> SemanticProcess[語意搜尋流程]
    HybridAgentHandle --> HybridProcess[混合查詢流程]

    subgraph "SQL Agent 流程"
        SQLProcess --> SplitSQL[拆解問題<br/>SQL + Analysis Prompt]
        SplitSQL --> GenerateSQL[生成 SQL<br/>自然語言 → SQL]
        GenerateSQL --> ExecuteSQL{執行 SQL}
        ExecuteSQL -->|錯誤| RetrySQL{重試次數 < 5?}
        RetrySQL -->|是| FixSQL[LLM 修復 SQL]
        FixSQL --> GenerateSQL
        RetrySQL -->|否| SQLError[返回錯誤]
        ExecuteSQL -->|成功| AnalyzeResult[LLM 分析結果]
        AnalyzeResult --> SQLReturn[返回 SQL 結果]
    end

    subgraph "Semantic Agent 流程"
        SemanticProcess --> DetermineTopK[動態決定 top-k<br/>3-50 筆]
        DetermineTopK --> FAISSSearch[FAISS 向量搜尋]
        FAISSSearch --> CrossEncoder[Cross-Encoder<br/>重排序]
        CrossEncoder --> FilterIrrelevant[過濾不相關<br/>LLM 判斷]
        FilterIrrelevant --> CheckSize{結果集大小}
        CheckSize -->|小| DirectSummary[直接摘要]
        CheckSize -->|大| ChunkSummary[分段摘要]
        ChunkSummary --> RecursiveMerge[遞迴合併]
        RecursiveMerge --> SemanticReturn[返回語意結果]
        DirectSummary --> SemanticReturn
    end

    subgraph "Hybrid Agent 流程"
        HybridProcess --> PlanPipeline[規劃管線<br/>LLM 拆解步驟]
        PlanPipeline --> ParseSteps[解析 JSON 步驟]
        ParseSteps --> ExecuteStep1{執行第 1 步}
        ExecuteStep1 -->|SQL| CallSQL[呼叫 SQL Agent]
        ExecuteStep1 -->|Semantic| CallSemantic[呼叫 Semantic Agent]
        CallSQL --> CheckStep2{有第 2 步?}
        CallSemantic --> CheckStep2
        CheckStep2 -->|是| ExecuteStep2[執行第 2 步]
        CheckStep2 -->|否| MergeResults
        ExecuteStep2 --> MergeResults[合併結果]
        MergeResults --> HybridReturn[返回混合結果]
    end

    SQLReturn --> KBContext
    SemanticReturn --> KBContext
    HybridReturn --> KBContext[組合 KB 上下文]

    KBContext --> CheckResult{AI Builder 檢查<br/>有結果?}
    CheckResult -->|否| FallbackAgent{Fallback}
    CheckResult -->|是| SynthesizeAnswer

    FallbackAgent -->|SQL→Hybrid| CallHybridFB[呼叫 Hybrid Agent]
    FallbackAgent -->|Semantic→Hybrid| CallHybridFB
    CallHybridFB --> SynthesizeAnswer

    SynthesizeAnswer[LLM 合成最終答案<br/>Power Automate/Ollama]
    SynthesizeAnswer --> SaveContext2[儲存對話上下文<br/>chat_history/]

    SaveContext2 --> ReturnRAG([返回 RAG 答案])
    SQLError --> ReturnRAG
    ReturnGeneral --> End([結束])
    ReturnRAG --> End

    style Start fill:#e8f5e9
    style ReturnRAG fill:#e8f5e9
    style ReturnGeneral fill:#e8f5e9
    style ClassifierAgent fill:#fff3e0
    style FAISSSearch fill:#e3f2fd
    style GenerateSQL fill:#f3e5f5
```

## 流程說明

### 1. RAG 問題判斷
- **判斷邏輯**：
  ```python
  if is_rag_query_via_powerautomate(message):
      # 進入 RAG 流程
  else:
      # 一般對話處理
  ```
- **判斷標準**：
  - 需要查詢知識庫？→ RAG
  - 一般閒聊、問候？→ 一般對話

### 2. 問題改寫
- **目的**：
  - 標準化問題格式
  - 補充時間資訊
  - 結構化查詢條件
- **範例**：
  ```
  原始: 最近一個月 Teams 問題
  改寫: Please list the Teams-related incidents in the past month.
  ```

### 3. 工具選擇
- **AI Builder 預先建議**：
  - 分析問題類型
  - 建議最適合的代理
- **選擇邏輯**：
  - 統計查詢 → SQL Agent
  - 語意搜尋 → Semantic Agent
  - 複雜多步驟 → Hybrid Agent

### 4. AutoGen 多代理協作
- **Classifier Agent**：
  - 接收工具建議
  - 最終路由決策
  - 呼叫對應代理

### 5. SQL Agent 處理
- **自動錯誤修復**：
  - 捕獲 SQL 執行錯誤
  - LLM 分析錯誤原因
  - 重新生成正確 SQL
  - 最多重試 5 次

### 6. Semantic Agent 處理
- **動態 top-k**：
  - LLM 預測需要檢索的文件數
  - 範圍：3-50 筆
  - 依查詢具體程度調整
- **重排序機制**：
  - FAISS 初步檢索
  - Cross-Encoder 精確重排
  - LLM 過濾不相關內容
- **遞迴摘要**：
  - 結果集過大時分段處理
  - 每段獨立摘要
  - 遞迴合併成最終摘要

### 7. Hybrid Agent 處理
- **管線規劃**：
  ```json
  [
    {"tool": 1, "prompt": "Filter incidents by location..."},
    {"tool": 2, "prompt": "Find similar cases in filtered set..."}
  ]
  ```
- **步驟執行**：
  - 依序執行每個步驟
  - 前一步結果傳遞給下一步
  - 最後合併所有結果

### 8. Fallback 機制
- **觸發條件**：
  - AI Builder 判斷無有效結果
  - 查詢失敗
- **Fallback 策略**：
  - SQL Agent 無結果 → 切換 Hybrid Agent
  - Semantic Agent 無結果 → 切換 Hybrid Agent
  - 確保使用者得到最佳答案

### 9. 答案合成
- **Context 組合**：
  ```
  Knowledge Base Entries:
  [檢索到的知識庫內容]

  User Question:
  [使用者問題]
  ```
- **LLM 合成**：
  - Power Automate (優先)
  - Ollama (fallback)
  - 生成人類可讀的答案

### 10. 對話記錄
- **儲存位置**：`chat_history/{chatId}.json`
- **記錄內容**：
  - 使用者問題
  - 系統回答
  - 查詢類型
  - 過濾條件
  - 結果摘要
