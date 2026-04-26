# 檔案上傳與分析流程 (Upload & Analysis Flow)

```mermaid
flowchart TD
    Start([使用者上傳 Excel]) --> ValidateFile{檔案驗證}
    ValidateFile -->|失敗| Error1[返回錯誤:<br/>檔案格式或大小不符]
    ValidateFile -->|通過| SaveFile[儲存原始檔案<br/>uploads/original_timestamp.xlsx]

    SaveFile --> ParseExcel[解析 Excel 內容<br/>pandas.read_excel]
    ParseExcel --> ExtractFields[抽取欄位<br/>依優先順序合併內容]

    ExtractFields --> CheckCache{檢查語意快取}
    CheckCache -->|命中| UseCache[使用快取結果]
    CheckCache -->|未命中| CallAI[呼叫 AI 分析]

    CallAI --> TryPowerAutomate{Power Automate<br/>可用?}
    TryPowerAutomate -->|是| PowerAutomate[AI Builder 分析<br/>問題摘要 + 解決方案]
    TryPowerAutomate -->|否/逾時| FallbackOllama[Ollama 本地模型<br/>多模型 fallback]

    PowerAutomate --> SaveCache[儲存到語意快取]
    FallbackOllama --> SaveCache
    UseCache --> ProcessData
    SaveCache --> ProcessData[資料處理]

    ProcessData --> RiskScoring[風險評分<br/>SmartScoring.py]
    RiskScoring --> HighRisk{高風險<br/>偵測}
    HighRisk -->|是| MarkHighRisk[標記高風險]
    HighRisk -->|否| CheckEscalation{升級處理<br/>偵測}

    MarkHighRisk --> CheckEscalation
    CheckEscalation -->|是| MarkEscalation[標記升級處理]
    CheckEscalation -->|否| CheckMultiUser{多人受影響<br/>偵測}

    MarkEscalation --> CheckMultiUser
    CheckMultiUser -->|是| MarkMultiUser[標記多人影響]
    CheckMultiUser -->|否| CalculateScore

    MarkMultiUser --> CalculateScore[計算綜合分數<br/>依權重加總]
    CalculateScore --> SaveJSON[儲存 JSON<br/>json_data/result_timestamp.json]

    SaveJSON --> ExportExcel[匯出 Excel<br/>excel_result_Unclustered/]
    ExportExcel --> AutoBuildKB[自動啟動<br/>build_kb.py]

    AutoBuildKB --> KBSync[知識庫同步<br/>Excel → SQLite → FAISS]
    KBSync --> UpdateProgress[更新進度<br/>session['progress']]

    UpdateProgress --> ReturnResult([返回分析結果<br/>含 UID])

    Error1 --> End([結束])
    ReturnResult --> End

    style Start fill:#e8f5e9
    style ReturnResult fill:#e8f5e9
    style Error1 fill:#ffebee
    style PowerAutomate fill:#e3f2fd
    style FallbackOllama fill:#fff9c4
    style SaveCache fill:#f3e5f5
    style RiskScoring fill:#fce4ec
```

## 流程說明

### 1. 檔案驗證階段
- 檢查檔案類型（僅允許 `.xlsx`）
- 檢查檔案大小（上限 10MB）
- 產生時間戳記檔名

### 2. 內容解析階段
- 使用 pandas 讀取 Excel
- 依使用者設定的欄位優先順序合併內容：
  - `resolution_priority`: 解決方案欄位順序
  - `summary_priority`: 問題摘要欄位順序

### 3. AI 分析階段
- **快取檢查**：
  - SHA-256 hash 精確匹配
  - Cosine 相似度 ≥ 0.92 模糊匹配
- **Power Automate 優先**：
  - 呼叫雲端 AI Builder
  - 最多重試 5 次
  - timeout 360 秒
- **Ollama Fallback**：
  - command-r7b (主要)
  - deepseek-coder-v2 (備援)
  - orca2, phi3 (其他備援)

### 4. 風險評分階段
- **高風險偵測**：語意相似度 > 0.7
- **升級處理偵測**：識別升級關鍵字
- **多人影響偵測**：識別受影響範圍
- **綜合分數計算**：
  ```
  總分 = keyword_weight × 關鍵字分數
       + multi_user_weight × 多人影響分數
       + escalated_weight × 升級分數
       + config_frequency_weight × 配置項頻率
       + component_frequency_weight × 元件頻率
       + cluster_size_weight × 群聚大小
  ```

### 5. 儲存與匯出階段
- **JSON 格式**：`json_data/result_YYYYMMDD_HHMMSS.json`
- **Excel 格式**：`excel_result_Unclustered/result_YYYYMMDD_HHMMSS_Unclustered.xlsx`

### 6. 自動建構知識庫
- 背景執行 `build_kb.py`
- Excel → SQLite 同步
- SQLite → FAISS 索引重建
- 不阻塞主流程
