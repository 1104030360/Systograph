# 真實專案能力實測報告（Verba / private-gpt / graphrag）

- 日期：2026-08-14
- 目的：從 `test-input/rag_github_repo_research.md` 挑三個真實 RAG 專案實際匯入掃描，驗證 Systograph 能力並找出改進點。
- 測試專案（clone 於 `test-input/test-repo/`，已加入 `.gitignore`，皆 `--depth 1`）：
  - **weaviate/Verba**（中小型 Python；Weaviate＋8 家 LLM/8 家 embedding 供應商，測廠商廣度）
  - **zylon-ai/private-gpt**（中型 Python；llama_index＋Qdrant＋OpenAI-compatible，正中規則甜蜜點）
  - **microsoft/graphrag**（大型 Python monorepo；litellm＋lancedb＋graph pipeline，測目錄外類別）
- 執行方式：CLI 同款 `CliMapWorkflow`，邊界審查以程式化核可（等同 Web review 全選 `scan_this_run`）。
- 對照組：每個 repo 由獨立 agent 建立逐檔驗證的 ground-truth 元件清單。

## 一、掃描結果總覽

| 指標 | Verba | private-gpt | graphrag |
|---|---|---|---|
| 核可掃描檔數 | 292 | ~1,000 | ~900 |
| evidence 筆數 | 49,073 | 45,472 | 19,885 |
| **components** | **3** | **14** | **2** |
| **edges** | **0** | **5** | **0** |
| 52 節點 detected | 3 | 15 | 1（+1 partial） |
| profiles 有判定 | 0/15 | 6/15 | 0/15 |
| 掃描耗時（修復後） | ~5 分 | ~18 分* | 2.7 分 |

\* private-gpt 該輪跑在部分效能修復前，實際會更快。

**結論一句話：pipeline 在規則涵蓋範圍內表現良好（private-gpt 14 元件/15 節點），但規則廣度不足讓另外兩個真實專案幾乎隱形（3 與 2 個元件、合計 0 條邊）。**

### private-gpt（甜蜜點驗證 ✅）
agent_loop / orchestrator / chunker / document_loader×2 / embedding / llm / prompt_builder / tool / vector_store(qdrant) / working_memory / api_route / parser 全亮；agentic-control profile `detected 2/2`。llama_index 規則層（2026-08-13/14 的 registry v2）實測有效。

### Verba（廠商廣度失敗 ❌）
只測到 pypdf / bs4 / api_route。**Weaviate（唯一向量庫）全滅**——`weaviate-client` 不在任何規則目錄；8 家 LLM（OpenAI/Anthropic/Cohere/Groq/Ollama/Novita/Upstage/AtlasCloud）與 8 家 embedding 供應商全走 aiohttp/httpx 裸 HTTP 呼叫，無 SDK import 可比對 → 全部隱形。

### graphrag（類別空白 ❌）
只測到 OpenAI llm＋embedding——而且證據來自 **tests/unit 的 fixture settings.yaml**，不是產品程式碼。litellm（唯一 LLM 層）、lancedb（預設向量庫）、graspologic（Leiden 社群偵測）、markitdown（loader）、4 個 query engine 全部無規則可落地；**graph-retrieval profile 在旗艦 GraphRAG 專案上 undetermined 0/1**。

## 二、實測揪出並已修復的產品 bug（5 項，全部 TDD＋全套件 1433 綠）

| # | Bug | 影響 | 修復 |
|---|---|---|---|
| 1 | `code_pattern_file_skipped` / `code_pattern_invalid_inventory_path` 無 risk-hint metadata | 任何含 >250KB 原始檔的專案整掃 crash（Verba 首掃即中） | `risk_hint_rules.toml` 補兩條目＋參數化測試 |
| 2 | Snapshot 安全檢查對「JSON 序列化後」文字掃描：`as f:` ＋換行變成字面 `f:\n` 被 WINDOWS_LOCAL_PATH_RE 誤判 | private-gpt、graphrag 掃描全死於 `SnapshotSafetyError`（fail closed 誤殺） | `scan_json_like` 改走訪原始字串（含 dict key，防護不降級）＋契約測試 |
| 3 | `UaParityService` 每 fact 線性掃全部 evidence＋每 legacy 線性掃全部 ua facts（O(N²)） | Verba 80k facts → 352 秒 | 五欄位鍵索引＋首見位置索引 → **1.3 秒**，行為不變 |
| 4 | `ComponentDetectionService.EvidenceLookup`、`RiskHintService.EvidenceLookup` 同款 O(N²) | build 階段 120s＋176s 起跳 | 預建索引 → 秒級 |
| 5 | `ua_edge_resolution._evidence_at` / `import_evidence` 同款 O(N²)（6.1M 次比對） | edge derivation 228 秒起跳；Verba build 跑不完 | (file,line)/(file,path) 索引 → **Verba build 112 秒完成** |

修復前 Verba 全掃 45+ 分鐘（首輪 10 分鐘 timeout、次輪 30 分鐘才到 build 又卡死）；修復後全流程 ~5 分鐘。

## 三、待改進清單（按優先序）

### P1 — 規則廣度（最大缺口）
現況：dependency 規則 6 個套件、package_capability 19 個 module、code_pattern 25 條。建議補：
- **向量庫**：`weaviate`/`weaviate-client`、`lancedb`、`pymilvus`、`pinecone`
- **LLM 抽象層**：`litellm`（graphrag 唯一 LLM 通道）、`langchain_text_splitters`（Verba 用）
- **embedding/工具**：`sentence_transformers`、`tiktoken`、`assemblyai`
- **loader/graph**：`markitdown`、`graspologic`、`networkx`（graph 語境）、`nltk`/`spacy`（chunking 語境）

### P1 — 裸 HTTP 供應商偵測
Verba 型專案（不裝 SDK、直接打 API URL）目前完全隱形。需要「endpoint URL → 廠商能力」規則類：`api.openai.com`、`api.anthropic.com`、`api.cohere.com`、`api.groq.com`、`api.voyageai.com`、`localhost:11434`（Ollama）等。此規則類也能讓 docker-compose env（`OLLAMA_URL=...`）變成 direct evidence。

### P1 — 檔名 `token*` 邊界審查誤判
`secret_like_config` 檔名啟發式把 `TokenChunker.py`、`tokenizers/`、`tokenizer_config.py` 全標成需人工審查——**三個專案 3/3 全中**（合計 38 檔），CLI 非互動模式直接被擋。tokenizer/token_count/token_chunk 是 AI 專案常態命名，應加排除模式或提供 CLI 核可參數。

### P2 — 測試 fixture 證據汙染
graphrag 的兩個 detected 元件證據來自 `tests/unit/config/fixtures/**/settings.yaml`。test/fixture 路徑的證據應降權或標記 provenance，避免「測試假資料撐起 detected」。

### P2 — reranker 過度宣告
private-gpt 因 `llama_index.core.postprocessor` import 被判 `reranker detected`，但 ground truth 確認該專案**沒有** reranker（只有 tree-expansion postprocessor）。`postprocessor ≠ reranker`；規則應收斂到 `SentenceTransformerRerank`/`FlagEmbeddingReranker` 等具體符號，泛用 import 最多 partial。

### P2 — build 產物拖垮 pipeline
Verba 的 Next.js build output（147 個 minified JS）產出 79,886 條 call 事實、近 5 萬 evidence——全是雜訊又是效能負載主因。建議 inventory policy 把 `**/_next/static/**`、`*.min.js`、單行超長檔分類為 build artifact 軟排除（可審查覆寫，不是硬擋）。

### P3 — 邊推導產出率
三專案合計 5 條邊（皆 private-gpt）。撞名 v2 的保守解析正確地不畫假邊，但 Verba/graphrag 0 邊代表 fixture 之外的真實佈局（registry/factory 動態分派、跨包 monorepo import）幾乎推不出 wiring，可視化價值受限。方向：擴 residence 涵蓋（元件檔案歸屬多半失敗才是 0 邊主因）而非放鬆解析。

### P3 — Graph RAG 類別
52 節點目錄對 graph pipeline 只有零星節點；entity extraction、community detection、graph index、community report 無 canonical type 可歸。若 GraphRAG 是目標市場，需要目錄擴充提案（走正式 reference map 變更流程）。

### 觀察（不急）
- 秒級剩餘熱點：secret boundary 遞迴驗證 ~52s、publisher ~41s（Verba 85k facts 規模）；線性但常數大，必要時再優化。
- private-gpt 掃描 18 分中 UA node 子程序占大宗；批次並行化可再壓。

## 四、產出物

- 掃描輸出（map/readiness/profile_signals 全套）：session scratchpad `runs/out-{verba,pgpt,graphrag}`
- Ground-truth 報告：三份 agent 產出（Verba 56 檔全清點、private-gpt v1.0.1 重寫版勘誤、graphrag v3.1.1 monorepo 全目錄）
- 程式修復：`risk_hint_rules.toml`、`snapshot_safety_service.py`、`local_json_snapshot_safety.py`、`ua_parity_service.py`、`component_detection_service.py`、`risk_hint_service.py`、`ua_edge_resolution.py`＋對應測試（工作區未 commit）
