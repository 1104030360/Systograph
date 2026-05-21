# language: zh-TW
功能: 建立 RAG 系統地圖
  KAI-Mind 可以 read-only 掃描既有 RAG project folder，產出 evidence-based AI System Map。

  規則: 成功掃描 project folder

    場景: 產出 JSON 與 Markdown
      假設 使用者提供可讀取的 RAG project folder
      當 使用者執行 "kai-mind map <project_path>"
      那麼 輸出 "ai_system_map.json"
      而且 輸出 "ai_system_map.md"
      而且 JSON schema_version 為 "ai-system-map/v1"
      而且 system_type 為 "rag"

  規則: detected component 必須有 evidence

    場景: Qdrant 由 Docker Compose 偵測
      假設 project folder 包含 docker-compose.yml
      而且 docker-compose.yml 定義 qdrant service
      當 scanner 建立 system map
      那麼 vector_store slot 狀態為 "detected"
      而且 vector_store component 包含 docker-compose evidence

  規則: 缺少 evidence 時不得猜測

    場景: 找不到 retriever 訊號
      假設 project folder 沒有 retriever 相關 evidence
      當 scanner 建立 system map
      那麼 retriever slot 不得標示為 "detected"
      而且 output 不包含 confidence 欄位

  規則: 解析失敗時產生 partial map

    場景: YAML config 格式錯誤
      假設 project folder 包含 malformed config
      當 scanner 解析 config 失敗
      那麼 scanner 仍輸出 partial "ai_system_map.json"
      而且 parse error 被記錄為 evidence
      而且 risk_hints 包含 parse error hint

  規則: project folder 不存在時輸出錯誤 artifact

    場景: 路徑不存在
      假設 使用者提供不存在的 project path
      當 使用者執行 "kai-mind map <project_path>"
      那麼 不輸出正常 system map
      而且 輸出 "map-error.md"
      而且 command 以 non-zero exit code 結束

  規則: 不輸出完整 secret

    場景: .env 包含 API key
      假設 project folder 包含 ".env"
      而且 ".env" 裡有 secret-like value
      當 scanner 建立 artifacts
      那麼 JSON 不包含完整 secret value
      而且 Markdown 不包含完整 secret value
      而且 evidence value 已遮罩或省略
