# 聚類分析流程 (Clustering Flow)

```mermaid
flowchart TD
    Start([使用者觸發聚類]) --> ScanFiles[掃描未聚類檔案<br/>excel_result_Unclustered/]
    ScanFiles --> CheckFiles{有檔案?}
    CheckFiles -->|否| NoFiles([返回: 無檔案需處理])
    CheckFiles -->|是| InitProgress[初始化進度<br/>cluster_progress_log]

    InitProgress --> LoopStart{遍歷每個檔案}
    LoopStart --> LoadExcel[讀取 Excel<br/>pandas.read_excel]

    LoadExcel --> LoopRows{遍歷每筆資料}
    LoopRows --> GetConfigItem[取得 configurationItem]
    GetConfigItem --> LoadCategories[載入分類記憶<br/>data/sentences/{config}_categories.json]

    LoadCategories --> CheckMemory{記憶檔案<br/>存在?}
    CheckMemory -->|否| CreateMemory[建立新記憶檔案<br/>空陣列]
    CheckMemory -->|是| UseMemory[使用現有分類]

    CreateMemory --> CallAI
    UseMemory --> CallAI[呼叫 AI 分類<br/>classify_summary_with_ai]

    CallAI --> AIClassify{AI 分類<br/>成功?}
    AIClassify -->|是| GetCategory[取得 category]
    AIClassify -->|否| DefaultCategory[使用預設分類]

    GetCategory --> CheckNewCategory{新分類?}
    DefaultCategory --> UpdateRow
    CheckNewCategory -->|是| AddToMemory[加入記憶檔案]
    CheckNewCategory -->|否| UpdateRow

    AddToMemory --> UpdateRow[更新 aiCategory 欄位]
    UpdateRow --> NextRow{還有下一筆?}
    NextRow -->|是| LoopRows
    NextRow -->|否| Dedup[去重處理<br/>deduplicate_by_id_and_time]

    Dedup --> SaveBack[覆蓋原 Excel<br/>更新 aiCategory]
    SaveBack --> FormatExcel[Excel 格式化<br/>表格樣式 + 批次上色]

    FormatExcel --> ExportClustered[匯出聚類結果<br/>cluster_excel_export]
    ExportClustered --> MoveFile[移動檔案<br/>→ excel_result_Clustered/]

    MoveFile --> UpdateFileProgress[更新檔案進度]
    UpdateFileProgress --> NextFile{還有下一個<br/>檔案?}
    NextFile -->|是| LoopStart
    NextFile -->|否| Complete([完成所有聚類])

    NoFiles --> End([結束])
    Complete --> End

    style Start fill:#e8f5e9
    style Complete fill:#e8f5e9
    style NoFiles fill:#fff9c4
    style CallAI fill:#e3f2fd
    style AddToMemory fill:#f3e5f5
```

## 流程說明

### 1. 檔案掃描階段
- 掃描 `excel_result_Unclustered/` 資料夾
- 篩選 `*_Unclustered.xlsx` 檔案
- 初始化進度追蹤

### 2. AI 分類階段
- **分類記憶機制**：
  - 每個 `configurationItem` 有獨立的分類記憶檔案
  - 路徑：`data/sentences/{configurationItem}_categories.json`
  - 格式：
    ```json
    [
      {"category": "網路連線問題"},
      {"category": "登入失敗"}
    ]
    ```

- **AI 分類流程**：
  ```python
  # 呼叫 AI，傳入歷史分類供參考
  category = classify_summary_with_ai(
      summary=問題摘要,
      categories=歷史分類列表,
      config_item=配置項
  )
  ```

- **新分類處理**：
  - 檢查是否為新分類（不區分大小寫）
  - 新分類自動加入記憶檔案
  - 下次遇到相同 configurationItem 時可參考

### 3. 去重處理
- 依 `id` 與 `analysisTime` 去重
- 保留 `analysisTime` 最新的記錄
- 確保資料唯一性

### 4. Excel 格式化
- **表格樣式**：TableStyleMedium9
- **批次上色**：
  - 依 `analysisTime` 分批
  - 交替使用淺綠色 (#d9ffd9) 和淺藍色 (#DAEBFF)
- **欄寬調整**：依內容自動調整

### 5. 聚類匯出
- 依 `aiCategory` 分組
- 每個類別獨立工作表
- 匯出到 `excel_result_Clustered/`

### 6. 進度追蹤
- 全域變數：`cluster_progress_log`
- 即時更新處理狀態
- 前端可透過 `/cluster-progress` 查詢
