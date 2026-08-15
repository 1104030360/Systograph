# 偵測層擴充與掃描邊界收斂

- 日期：2026-08-15
- 範圍：使用者指定的五項（安全規則放寬、tests 硬排除、endpoint 身分層、reranker 收斂、規則廣度）
- 驗收：全套件 1510 passed / 1 skipped、ruff check＋format、mypy strict 全過；三個真實 repo 重掃

## 1. 安全規則放寬（可正確跑出來為主）

| 項目 | 改動 | 理由 |
|---|---|---|
| `token` 檔名誤判 | `InventoryRiskService` 對**程式原始碼**（含 `.ipynb`）不再套用 secret 檔名 marker | `TokenChunker.py` / `tokenizers/` / `tokenizer_config.py` 三個 repo 全中；檔名不是機密證據，內容仍由 SecretMaskingService 遮罩。shell script 保留檢查（常內嵌 `export API_KEY=`） |
| CLI 被審查閘門擋死 | 新增 `systograph map --approve-boundary-review` | 個人專案不必為了一個 `.env` 開 Web review；每筆仍以 `scan_this_run` 記進 provenance（runtime_user_decision），硬封鎖路徑不受影響 |

先前 5 個 bug（risk-hint 缺目、snapshot 誤殺、4 處 O(N²)）已於 2026-08-14 修畢，本次不重複。

## 2. tests/ 硬排除（測試假資料汙染）

`scan_inventory_rules.toml` 新增第三種 action：**`block`**。

```
 include  ──► 進 inventory
 exclude  ──► 軟排除，scan_this_run 可撈回來
 block    ──► HARD_BLOCKED，在 precedence 解析「決策」之前就定案 → 撈不回來
```

- 只封鎖目錄慣例：`tests/`、`test/`、`__tests__/`。**不做檔名 `*test*` 比對**（`TokenChunker.py`、`testimonials.py`、`protest/` 都有測試釘住不得誤傷）。
- 效果實測：graphrag 原本兩個 detected 元件的證據來自 `tests/unit/config/fixtures/**/settings.yaml`，**重掃後 tests/ 路徑證據 = 0 筆**，假的 `embedding_model:openai` 消失。
- Systograph 自己的 fixture 專案不受影響（掃描根就是 scenario 目錄，相對路徑不含 `tests/`）。

## 3. Endpoint 身分層（裸 HTTP 廠商偵測）

新開一層，**不動任何舊規則**：新目錄 + 新 rule_id 前綴 + 新 fact kind + 獨立 bridge 分支。

| 元件 | 內容 |
|---|---|
| `core/rules/endpoint_capability_rules.toml` | 20 條，host 白名單（查證官方文件） |
| `core/providers/endpoint_capability_provider.py` | 掃 source/config 的 URL 字面量 |
| fact kind | `endpoint_vendor`（全新，碰不到舊 bridge） |
| rule_id | 一律 `endpoint_vendor_*` 前綴（有測試釘住與舊 rule_id／package module 零交集） |

比對契約：
- `host` 精確比對（不做子字串），`port` 用於本地 runtime（Ollama 11434 在 localhost / 127.0.0.1 / host.docker.internal / compose service name 後面都成立）。
- `path_prefix` 最長者勝：`api.openai.com/v1/embeddings` → embedder，同 host 其餘 → llm_answerer；`api.cohere.com/v2/rerank` → reranker。
- **明確不收**：8080 / 8000 / 1234 這類泛用本地埠（vLLM、llama.cpp、LM Studio、LocalAI）——那更可能是專案自己的服務；自架 OpenAI-compatible base_url 絕不歸給 OpenAI；註解與 `.md` 文件裡的 URL 不算整合。
- URL 內嵌帳密會被遮罩，evidence 只留 host。

## 4. Reranker 過度宣告收斂

移除 `llama_index.core.postprocessor` → `reranker_candidate` 這條泛用對應（該 namespace 16 個匯出只有 3 個是 reranker，其餘是相似度過濾、時序排序、PII 清洗、文字壓縮）。改為 12 條**具體符號／定義子模組**：

- core：`SentenceTransformerRerank`、`sbert_rerank`、`LLMRerank`、`llm_rerank`、`StructuredLLMRerank`、`structured_llm_rerank`、`rankGPT_rerank`（注意大小寫，官方就是這樣命名）
- integrations：`llama_index.postprocessor.{sbert_rerank, flag_embedding_reranker, cohere_rerank, rankgpt_rerank, colbert_rerank}`
- 另加 `sentence_transformers.CrossEncoder`

結果：private-gpt 不再被誤判有 reranker（ground truth 確認它只有 tree-expansion postprocessor）。

## 5. 規則廣度（查證官方接口後補上）

package identity 新增：

| 類別 | 模組 | kind |
|---|---|---|
| 向量庫 | `weaviate`、`lancedb`、`pymilvus`、`pinecone` | vector_db |
| LLM 閘道 | `litellm` | `llm`（有 answerer，但**不宣稱**是哪家；litellm 可路由本地或雲端） |
| chunking | `langchain_text_splitters`、`nltk.tokenize` | chunker |
| loader | `markitdown`、`assemblyai` | document_loader |
| embedding | `sentence_transformers` | embedding_provider |
| graph | `graspologic.partition`、`graspologic_native` | `graph_rag_system`（新 canonical type → 既有 52 節點的 graph_rag_system） |

**刻意不收**（寫進目錄的 EXCLUSIONS，附理由）：
- `tiktoken`：token 計數同時服務 chunk 切分與 context 預算（private-gpt 是後者、graphrag 是前者），一個 import 分不出來。
- `spacy`：同一 import 服務句子切分與 NER。
- `networkx`：泛用圖論，無 AI 語意；GraphRAG 證據改由 graspologic 承擔（hierarchical_leiden 沒有非圖用途）。
- `httpx` / `aiohttp` / `requests`：傳輸層套件，廠商歸屬歸 endpoint 層。

dependency manifest 另補 10 個 Python + 4 個 node 套件（宣告即候選，不等於元件）。

## 6. 實測結果

### graphrag

| | 改動前 | 改動後 |
|---|---|---|
| components | 2 | **5** |
| 52 節點 | 1 detected＋1 partial | **4 detected** |
| 證據來自 tests/ | 是（兩個元件全靠它） | **0 筆** |
| 掃描時間 | 160s | **65s** |
| CLI 可直接跑 | 否（要 driver script） | **是** |

新測到：`markitdown`（loader）、`graspologic`（graph_rag_system）、`litellm`（llm）、`lancedb`（vector_db）；`openai` 改由產品碼 `drift_search/primer.py` 的 code_pattern 證據支撐，不再是測試 fixture。

### private-gpt

| | 改動前 | 改動後 |
|---|---|---|
| components | 14 | **15** |
| 52 節點 | 15 detected | 13 detected＋1 partial |
| edges | 5 | **6** |
| evidence | 45,472 | 29,985（tests 排除） |
| 證據來自 tests/ | 有 | **0 筆** |

三個變化都是**變誠實**，不是退步：

1. **新增** `markitdown`（document_loader）、`nltk`（chunker）——規則廣度補上的真元件。
2. **`reranker` 從 detected → undetermined（0 筆證據）**：ground truth 早已確認 private-gpt 沒有 reranker，只有 tree-expansion postprocessor。過度宣告修掉了。
3. **`orchestrator` 從 detected → partial**：產品碼只有 `llama_index.core.workflow` 的 import（33 筆 indirect），先前把它推到 detected 的直接呼叫證據來自測試檔。tests 排除後回到「import 證明存在、不證明使用」的五態契約——這正是預期行為。

### Verba（改動幅度最大）

| | 改動前 | 改動後 |
|---|---|---|
| components | 3 | **15** |
| 52 節點 detected | 3 | **7** |
| edges | 0 | 3 |

Verba 原本幾乎全隱形（只有 pypdf／bs4／api_route），因為它不裝任何廠商 SDK、全部用 aiohttp/httpx 直接打 URL。endpoint 身分層一上線：

- **LLM 供應商 7 家全中**：anthropic、cohere、groq、novita、openai、upstage（雲端 host）＋ ollama（11434 埠）。對照 ground truth 的 8 家註冊供應商，只差 Atlas Cloud（`api.atlascloud.ai` 不在白名單，見下方未決事項）——未知 host 不產生元件，這是設計行為。
- **Weaviate 向量庫**：靠新加的 package identity 規則（`import weaviate`）。
- **其他新測到**：`voyageai`（embedding）、`sentence_transformers`（embedding）、`langchain`（chunker，來自 langchain_text_splitters）、`assemblyai`（document_loader）。

## 7. 三專案彙總

| | Verba | private-gpt | graphrag |
|---|---|---|---|
| components | 3 → **15** | 14 → **15** | 2 → **5** |
| 52 節點 detected | 3 → **7** | 15 → 13（＋1 partial） | 1 → **4** |
| tests/ 證據 | 0 | 0 | 0（原本是兩個元件的唯一來源） |

private-gpt 的節點數下降是修正而非退步：假 reranker 消失、orchestrator 因為直接呼叫證據原在測試檔而誠實降為 partial。

## 8. 未決事項

- **Atlas Cloud（`api.atlascloud.ai`）未收**：Verba 確實在用，但目錄政策要求 host 出自官方文件查證，單一 repo 的用法證據較弱。要補的話請查證後加一列即可，不影響其他層。
- **`tiktoken` 未收**：使用者原列在建議清單，本次判定 ambiguous（chunk 切分 vs context 預算）。若要收，正確位置是 code_pattern 層的消歧義規則（例如同檔是否有 splitter 呼叫），不是 package identity。
- **邊（edges）產出仍偏少**（3 / 6 / 0）：根因是元件的檔案歸屬（residence）覆蓋率，不是解析保守度。
- 新檔案皆為 untracked，commit 時需手動 `git add`：`core/providers/endpoint_capability_provider.py`、`core/rules/endpoint_capability_rules.toml`、`core/rules/package_capability_rules.toml`、`tests/unit/core/test_{endpoint_capability_provider,inventory_risk_service,inventory_test_suite_block,package_capability_breadth}.py`、`tests/integration/test_endpoint_identity_layer.py`。
