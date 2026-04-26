# 系統架構圖 (System Architecture)

```mermaid
graph TB
    subgraph "使用者介面層"
        UI[Web Browser]
        UI --> |HTTP/WebSocket| Flask
    end

    subgraph "Flask 應用層"
        Flask[Flask App<br/>Analysis.py]
        Flask --> Upload[檔案上傳模組]
        Flask --> Cluster[聚類分析模組]
        Flask --> Chat[RAG 對話模組]
        Flask --> History[歷史記錄模組]
        Flask --> Prompt[提示詞管理模組]
    end

    subgraph "AI/ML 處理層"
        Upload --> GPTUtils[gpt_utils.py]
        Upload --> SmartScore[SmartScoring.py]
        Chat --> GPTChat[gptChat.py]

        GPTUtils --> |語意快取| Cache[(cache/)]
        GPTChat --> |AutoGen 編排| Agents

        subgraph "多代理系統"
            Agents[Agent 協調器]
            Agents --> QueryClassifier[Query Classifier]
            QueryClassifier --> SQLAgent[SQL Agent]
            QueryClassifier --> SemanticAgent[Semantic Agent]
            QueryClassifier --> HybridAgent[Hybrid Agent]
            QueryClassifier --> FollowupAgent[Followup Agent]
        end
    end

    subgraph "知識庫層"
        BuildKB[build_kb.py<br/>知識庫建構器]

        SQLAgent --> SQLiteDB[(SQLite<br/>resultDB.db)]
        SemanticAgent --> FAISS[(FAISS<br/>kb_index.faiss)]
        SemanticAgent --> Metadata[(Metadata<br/>kb_metadata.json)]

        BuildKB --> |同步| Excel[(Excel<br/>SharePoint/OneDrive)]
        BuildKB --> |雙向同步| SQLiteDB
        BuildKB --> |重建索引| FAISS
        BuildKB --> |更新| Metadata
    end

    subgraph "外部服務層"
        GPTUtils --> |API 呼叫| PowerAutomate[Power Automate<br/>AI Builder]
        GPTUtils --> |Fallback| Ollama[Ollama<br/>本地 LLM]
        SQLAgent --> |Fallback| Ollama
        SemanticAgent --> |Fallback| Ollama
    end

    subgraph "資料儲存層"
        Upload --> |儲存| UploadFolder[(uploads/)]
        Upload --> |輸出| JSONData[(json_data/)]
        Upload --> |未聚類| Unclustered[(excel_result_Unclustered/)]
        Cluster --> |已聚類| Clustered[(excel_result_Clustered/)]
        Chat --> |對話記錄| ChatHistory[(chat_history/)]
    end

    style Flask fill:#e1f5ff
    style Agents fill:#fff3e0
    style BuildKB fill:#f3e5f5
    style PowerAutomate fill:#e8f5e9
    style Ollama fill:#fff9c4
```

## 圖表說明

### 使用者介面層
- **Web Browser**: 使用者透過瀏覽器訪問系統
- 支援 HTTP 請求和 WebSocket 即時通訊

### Flask 應用層 (Analysis.py)
- **檔案上傳模組**: 處理 Excel 上傳與分析
- **聚類分析模組**: 執行 KMeans/HDBSCAN 聚類
- **RAG 對話模組**: 處理智能問答
- **歷史記錄模組**: 管理分析歷史
- **提示詞管理模組**: 自訂 GPT 提示詞

### AI/ML 處理層
- **gpt_utils.py**: AI 工具集，包含語意快取
- **SmartScoring.py**: 風險評分與關鍵字抽取
- **gptChat.py**: RAG 編排中樞，協調多代理系統

### 多代理系統 (AutoGen)
- **Query Classifier**: 分類查詢意圖
- **SQL Agent**: 處理結構化查詢
- **Semantic Agent**: 處理語意搜尋
- **Hybrid Agent**: 處理混合查詢
- **Followup Agent**: 處理追問查詢

### 知識庫層
- **build_kb.py**: Excel ↔ SQLite ↔ FAISS 三向同步
- **SQLite**: 結構化資料儲存
- **FAISS**: 向量索引檢索
- **Metadata**: 結構化 metadata

### 外部服務層
- **Power Automate AI Builder**: 雲端 LLM (優先)
- **Ollama**: 本地 LLM (fallback)

### 資料儲存層
- **uploads/**: 原始上傳檔案
- **json_data/**: JSON 格式分析結果
- **excel_result_Unclustered/**: 未聚類 Excel
- **excel_result_Clustered/**: 已聚類 Excel
- **chat_history/**: 對話記錄
