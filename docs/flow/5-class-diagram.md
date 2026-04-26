# UML 類別圖 (Class Diagram)

```mermaid
classDiagram
    class FlaskApp {
        +Flask app
        +str secret_key
        +dict config
        +upload_file()
        +cluster_excel()
        +chat_with_model()
        +build_kb()
        +get_progress()
    }

    class GPTUtils {
        -SentenceTransformer embedding_model
        -list semantic_cache_resolution
        -list semantic_cache_summary
        +find_semantic_cache(text, kind)
        +add_to_semantic_cache(text, response, kind)
        +extract_resolution_suggestion(text)
        +extract_problem_with_custom_prompt(text)
        +analyze_with_ai_builder_then_fallback(resolution, summary)
        +print_cache_report()
    }

    class SmartScoring {
        +SentenceTransformer bert_model
        +KeyBERT keybert_model
        +spacy nlp
        +is_high_risk(text, examples, embeddings)
        +is_escalated(text, examples, embeddings)
        +is_multi_user(text, examples, embeddings)
        +extract_keywords(text, top_n)
        +recommend_solution(text)
        +is_actionable_resolution(text)
        +extract_cluster_name(texts)
    }

    class GPTChat {
        +str POWERAUTOMATE_URL
        +dict metadata
        +dict faiss_id_to_text
        +SentenceTransformer kb_model
        +FaissIndex kb_index
        +list kb_texts
        +QueryClassifierAgent classifier
        +SQLAgent sql_agent
        +SemanticAgent semantic_agent
        +HybridQueryAgent hybrid_agent
        +FollowUpAgent followup_agent
        +semantic_agent_handle(message)
        +sql_agent_handle(message)
        +HybridQuery_agent_handle(message)
        +run_offline_gpt(message, model, history, chat_id)
        +rewrite_query_with_aibuilder(user_query)
        +get_tool_suggestion_with_reason_sentence(query)
        +is_rag_query_via_powerautomate(message)
        +save_query_context(chat_id, query, result_type)
    }

    class BuildKB {
        +str SQLITE_DB
        +str KB_INDEX
        +str KB_TEXTS
        +str KB_METADATA
        +str EXCEL_PATH
        +sync_excel_row_to_sqlite_custom(excel_path, sqlite_path)
        +sync_sqlite_to_excel(sqlite_path, excel_path)
        +sync_faiss_with_sqlite(sqlite_path)
        +backup_sqlite_db(db_path)
        +close_excel_if_open(filepath)
        +ensure_excel_opened(filepath)
        +id_to_int64(uid)
        +build_kb()
    }

    class QueryClassifierAgent {
        +str name
        +OllamaChatCompletionClient model_client
        +list tools
        +str system_message
        +classify(query)
    }

    class SQLAgent {
        +str model
        +str db_path
        +handle(message)
        -_split_user_question(message, mode)
        -_build_prompt(user_question, mode)
        -_generate_sql(prompt, max_retry)
        -_execute_sql(sql_code)
        -_analyze_results(df, analysis_prompt)
    }

    class SemanticAgent {
        +str model
        +SentenceTransformer kb_model
        +FaissIndex kb_index
        +list kb_texts
        +dict metadata
        +CrossEncoder cross_encoder
        +dict faiss_id_to_text
        +handle(message)
        -_determine_top_k(user_input)
        -_filter_irrelevant(group, user_query)
        -_summarize_retrieved_kb(retrieved, user_query)
        -_recursive_merge(summaries, token_limit)
        -_run_with_fallback(prompt)
    }

    class HybridQueryAgent {
        +str model
        +str db_path
        +SemanticAgent semantic_agent
        +SQLAgent sql_agent
        +handle(message)
        +plan_pipeline(user_query)
        +execute_pipeline(steps)
        +summarize_pipeline_result(result)
        +summarize_with_ai_builder(text)
    }

    class FollowUpAgent {
        +str model
        +handle(chat_id, message)
        +is_follow_up(message)
        +extract_context(chat_id)
    }

    class KBLoader {
        +ensure_metadata_table(db_path)
        +load_kb()
    }

    FlaskApp --> GPTUtils : uses
    FlaskApp --> SmartScoring : uses
    FlaskApp --> GPTChat : uses
    FlaskApp --> BuildKB : triggers

    GPTChat --> QueryClassifierAgent : orchestrates
    GPTChat --> SQLAgent : delegates
    GPTChat --> SemanticAgent : delegates
    GPTChat --> HybridQueryAgent : delegates
    GPTChat --> FollowUpAgent : delegates

    HybridQueryAgent --> SQLAgent : uses
    HybridQueryAgent --> SemanticAgent : uses

    BuildKB --> KBLoader : uses

    SemanticAgent --> GPTUtils : fallback
    SQLAgent --> GPTUtils : fallback
```

## 類別說明

### FlaskApp (Analysis.py)
**職責**：Web 應用程式主控制器
- 處理所有 HTTP 路由
- 協調各模組運作
- 管理 session 與進度追蹤

**主要方法**：
- `upload_file()`: 處理檔案上傳與分析
- `cluster_excel()`: 執行聚類分析
- `chat_with_model()`: 處理 RAG 對話
- `build_kb()`: 觸發知識庫建構
- `get_progress()`: 查詢處理進度

### GPTUtils
**職責**：AI 工具集與快取管理
- 語意快取機制 (SHA-256 + Cosine)
- LLM 呼叫與 fallback
- 摘要與解決方案抽取

**快取機制**：
- `resolution`: 解決方案快取
- `summary`: 問題摘要快取
- 閾值：0.92 (cosine 相似度)
- 上限：3000 條/檔案

### SmartScoring
**職責**：風險評估與語意分析
- 高風險偵測 (語意相似度)
- 升級處理判斷
- 多人影響偵測
- 關鍵字抽取 (KeyBERT)
- 解決方案有效性檢查

**模型**：
- BERT: `paraphrase-MiniLM-L6-v2`
- spaCy: `en_core_web_sm`
- KeyBERT: 自動關鍵字抽取

### GPTChat
**職責**：RAG 編排中樞
- AutoGen 多代理協調
- 查詢重寫與分類
- 工具選擇建議
- 對話上下文管理

**代理編排**：
- Classifier Agent: 路由決策
- SQL/Semantic/Hybrid/Followup: 專業代理

### BuildKB
**職責**：知識庫建構與同步
- Excel ↔ SQLite 雙向同步
- FAISS 索引重建
- COM 自動化 (Excel)
- 自動備份

**同步邏輯**：
1. Excel → SQLite (增量)
2. SQLite → Excel (補寫)
3. SQLite → FAISS (重建索引)

### QueryClassifierAgent
**職責**：查詢分類路由
- 接收工具建議
- 最終路由決策
- 呼叫對應代理

**工具清單**：
- SQLAgentTool
- SemanticAgentTool
- HybridQueryAgentTool

### SQLAgent
**職責**：結構化查詢處理
- 自然語言 → SQL
- 自動錯誤修復 (最多 5 次)
- Pandas 進階篩選
- 結果分析與摘要

**模型**：`deepseek-coder-v2:latest`

### SemanticAgent
**職責**：語意搜尋與摘要
- FAISS 向量檢索
- Cross-Encoder 重排序
- 動態 top-k (3-50)
- 遞迴分段摘要

**模型**：
- Encoder: `all-MiniLM-L6-v2`
- Cross-Encoder: `ms-marco-MiniLM-L-6-v2`
- LLM: `orca2:13b`

### HybridQueryAgent
**職責**：混合查詢處理
- 多步驟管線規劃
- SQL + Semantic 串接
- 結果合併與摘要

**管線類型**：
- SQL → Semantic: 先過濾後搜尋
- Semantic → SQL: 先搜尋後聚合

### FollowUpAgent
**職責**：追問查詢處理
- 上下文感知
- 對話歷史分析
- 查詢擴展

### KBLoader
**職責**：知識庫載入
- 初始化資料表
- 載入 FAISS 索引
- 載入 metadata
- 載入文字語料

## 類別關係

### 組合關係 (Composition)
- `GPTChat` 組合 `QueryClassifierAgent`, `SQLAgent`, `SemanticAgent`, `HybridQueryAgent`, `FollowUpAgent`
- `HybridQueryAgent` 組合 `SQLAgent`, `SemanticAgent`

### 依賴關係 (Dependency)
- `FlaskApp` 依賴 `GPTUtils`, `SmartScoring`, `GPTChat`, `BuildKB`
- `SemanticAgent`, `SQLAgent` 依賴 `GPTUtils` (fallback)
- `BuildKB` 依賴 `KBLoader`

### 使用關係 (Usage)
- `FlaskApp` 觸發 `BuildKB.build_kb()`
- `GPTChat` 協調所有代理
- 代理之間可互相呼叫 (Hybrid 模式)
