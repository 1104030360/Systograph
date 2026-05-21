Feature: 建立 RAG 系統地圖
  KAI-Mind 可以 read-only 掃描既有 RAG project folder，產出 evidence-based AI System Map。

  Rule: 成功掃描 project folder

    Example: 產出 JSON 與 Markdown
      Given 使用者提供可讀取的 RAG project folder
      When 使用者執行 "kai-mind map <project_path>"
      Then 輸出 "ai_system_map.json"
      And 輸出 "ai_system_map.md"
      And JSON schema_version 為 "ai-system-map/v1"
      And system_type 為 "rag"

  Rule: detected component 必須有 evidence

    Example: Qdrant 由 Docker Compose 偵測
      Given project folder 包含 docker-compose.yml
      And docker-compose.yml 定義 qdrant service
      When scanner 建立 system map
      Then vector_store slot 狀態為 "detected"
      And vector_store component 包含 docker-compose evidence

  Rule: 缺少 evidence 時不得猜測

    Example: 找不到 retriever 訊號
      Given project folder 沒有 retriever 相關 evidence
      When scanner 建立 system map
      Then retriever slot 不得標示為 "detected"
      And output 不包含 confidence 欄位

  Rule: 解析失敗時產生 partial map

    Example: YAML config 格式錯誤
      Given project folder 包含 malformed config
      When scanner 解析 config 失敗
      Then scanner 仍輸出 partial "ai_system_map.json"
      And parse error 被記錄為 evidence
      And risk_hints 包含 parse error hint

  Rule: project folder 不存在時輸出錯誤 artifact

    Example: 路徑不存在
      Given 使用者提供不存在的 project path
      When 使用者執行 "kai-mind map <project_path>"
      Then 不輸出正常 system map
      And 輸出 "map-error.md"
      And command 以 non-zero exit code 結束

  Rule: 不輸出完整 secret

    Example: .env 包含 API key
      Given project folder 包含 ".env"
      And ".env" 裡有 secret-like value
      When scanner 建立 artifacts
      Then JSON 不包含完整 secret value
      And Markdown 不包含完整 secret value
      And evidence value 已遮罩或省略
