# GitDiagram 後端分析報告

參考專案：<https://github.com/ahmedkhaleel2004/gitdiagram>

注意：這份文件改用 ASCII 視覺化圖表，不依賴 Mermaid renderer，避免出現 `No diagram type detected`。

本地 clone 位置：

```text
/private/tmp/gitdiagram-review/GitDiagram
```

## 一句話結論

GitDiagram 的後端不是直接叫 LLM 畫 Mermaid。

它的流程是：

```text
┌─────────────┐
│ GitHub repo │
└─────────────┘
  └─→ 抓 file tree 和 README

┌──────────────────────┐
│ 抓 file tree 和 README │
└──────────────────────┘
  └─→ 估算 token 和 quota

┌──────────────────┐
│ 估算 token 和 quota │
└──────────────────┘
  └─→ LLM 先寫架構解釋

┌────────────┐
│ LLM 先寫架構解釋 │
└────────────┘
  └─→ LLM 產生 structured graph JSON

┌──────────────────────────────┐
│ LLM 產生 structured graph JSON │
└──────────────────────────────┘
  └─→ 驗證 graph 是否合理

┌───────────────┐
│ 驗證 graph 是否合理 │
└───────────────┘
  ├─【失敗】→ LLM 產生 structured graph JSON
  └─【成功】→ 程式編譯成 Mermaid

┌───────────────┐
│ 程式編譯成 Mermaid │
└───────────────┘
  └─→ 驗證 Mermaid 語法

┌───────────────┐
│ 驗證 Mermaid 語法 │
└───────────────┘
  └─→ 存到 R2 / Redis

┌───────────────┐
│ 存到 R2 / Redis │
└───────────────┘
  └─→ 前端顯示互動圖
```

重點是：

| 階段 | 誰負責 | 目的 |
|---|---|---|
| 抓 repo 資料 | 後端程式 | 取得 file tree、README、default branch |
| 理解 repo | LLM | 先產生文字版架構理解 |
| 產生圖資料 | LLM + schema | 產出 `groups / nodes / edges` |
| 驗證圖資料 | 後端程式 | 檢查 path、node id、edge endpoint |
| 產生 Mermaid | 後端程式 | deterministic compile，不讓 LLM 直接寫 Mermaid |
| 顯示結果 | 前端 | 用 Mermaid / viewer 呈現 |

## 從 input repo 到產生 JSON 的完整流程

這一段只看後端，從使用者輸入 repo 到後端產生 graph JSON，中間做了哪些事。

```text
┌──────────────────┐
│ 使用者輸入 owner/repo │
└──────────────────┘
  └─→ POST /generate/stream

┌───────────────────────┐
│ POST /generate/stream │
└───────────────────────┘
  └─→ 驗證 request schema

┌───────────────────┐
│ 驗證 request schema │
└───────────────────┘
  └─→ 建立 session audit

┌──────────────────┐
│ 建立 session audit │
└──────────────────┘
  └─→ 讀 AI_PROVIDER / model

┌───────────────────────┐
│ 讀 AI_PROVIDER / model │
└───────────────────────┘
  └─→ 檢查免費 quota gate

┌─────────────────┐
│ 檢查免費 quota gate │
└─────────────────┘
  └─→ GitHubService 初始化

┌───────────────────┐
│ GitHubService 初始化 │
└───────────────────┘
  └─→ 選擇 GitHub auth

┌────────────────┐
│ 選擇 GitHub auth │
└────────────────┘
  └─→ 抓 repo metadata

┌─────────────────┐
│ 抓 repo metadata │
└─────────────────┘
  └─→ 抓 recursive file tree

┌───────────────────────┐
│ 抓 recursive file tree │
└───────────────────────┘
  └─→ 過濾不需要的檔案

┌──────────┐
│ 過濾不需要的檔案 │
└──────────┘
  └─→ 抓 README

┌──────────┐
│ 抓 README │
└──────────┘
  └─→ 組成 GithubData

┌───────────────┐
│ 組成 GithubData │
└───────────────┘
  └─→ 估算 input/output tokens 和 cost

┌───────────────────────────────┐
│ 估算 input/output tokens 和 cost │
└───────────────────────────────┘
  └─→ 檢查 token limit

┌────────────────┐
│ 檢查 token limit │
└────────────────┘
  └─→ LLM Pass 1: architecture explanation

┌──────────────────────────────────────┐
│ LLM Pass 1: architecture explanation │
└──────────────────────────────────────┘
  └─→ 抽出 explanation 文字

┌───────────────────┐
│ 抽出 explanation 文字 │
└───────────────────┘
  └─→ 建立 file_tree lookup

┌─────────────────────┐
│ 建立 file_tree lookup │
└─────────────────────┘
  └─→ LLM Pass 2: structured graph JSON

┌───────────────────────────────────┐
│ LLM Pass 2: structured graph JSON │
└───────────────────────────────────┘
  └─→ 用 schema parse graph

┌──────────────────────┐
│ 用 schema parse graph │
└──────────────────────┘
  └─→ validate graph correctness

┌────────────────────────────┐
│ validate graph correctness │
└────────────────────────────┘
  ├─【不通過】→ 把 validation feedback 丟回 LLM
  └─【通過】→ 得到 valid graph JSON

┌──────────────────────────────┐
│ 把 validation feedback 丟回 LLM │
└──────────────────────────────┘
  └─→ LLM Pass 2: structured graph JSON

┌─────────────────────┐
│ 得到 valid graph JSON │
└─────────────────────┘
  └─→ compile Mermaid

┌─────────────────┐
│ compile Mermaid │
└─────────────────┘
  └─→ validate Mermaid syntax

┌─────────────────────────┐
│ validate Mermaid syntax │
└─────────────────────────┘
  └─→ 存 artifact: graph JSON + diagram + explanation + audit
```

### Step 1：接收 input repo

使用者送進來的 request 大概長這樣：

```json
{
  "username": "owner",
  "repo": "repo-name",
  "api_key": "optional-user-ai-key",
  "github_pat": "optional-private-repo-token"
}
```

後端用 Pydantic `GenerateRequest` 驗證：

| 欄位 | 用途 | 驗證 |
|---|---|---|
| `username` | GitHub owner | 至少 1 字 |
| `repo` | GitHub repo name | 至少 1 字 |
| `api_key` | 使用者自己的 OpenAI/OpenRouter key | optional，但如果有值至少 1 字 |
| `github_pat` | private repo 或 higher rate limit 用 | optional，但如果有值至少 1 字 |

如果 JSON 格式壞掉，或 schema 不通過，直接回：

```json
{
  "ok": false,
  "error": "Invalid request payload.",
  "error_code": "VALIDATION_ERROR"
}
```

### Step 2：建立 generation session audit

進入 `/generate/stream` 後，後端會先建立一份 audit。

```text
┌──────────────────┐
│ request accepted │
└──────────────────┘
        ↓
┌────────────────┐
│ uuid sessionId │
└────────────────┘
        ↓
┌────────────────┐
│ status running │
└────────────────┘
        ↓
┌───────────────┐
│ stage started │
└───────────────┘
        ↓
┌──────────────────┐
│ timeline started │
└──────────────────┘
```

audit 初始內容大概是：

```json
{
  "sessionId": "...",
  "status": "running",
  "stage": "started",
  "provider": "openai",
  "model": "gpt-5.4-mini",
  "stageUsages": [],
  "graph": null,
  "graphAttempts": [],
  "timeline": [
    {
      "stage": "started",
      "createdAt": "..."
    }
  ],
  "createdAt": "...",
  "updatedAt": "..."
}
```

這份 audit 後面會記錄：

| 欄位 | 記錄什麼 |
|---|---|
| `stage` | 現在跑到哪一步 |
| `timeline` | 每一步的時間點 |
| `estimatedCost` | 預估成本 |
| `finalCost` | 實際成本 |
| `graphAttempts` | 每一次 graph JSON 嘗試 |
| `validationError` | graph 或流程錯誤 |
| `compilerError` | Mermaid compile/validate 錯誤 |

### Step 3：決定 AI provider 和 model

後端從環境變數決定要用哪個 AI provider。

```text
┌───────────────┐
│ 讀 AI_PROVIDER │
└───────────────┘
  └─→ 是不是 openrouter

┌────────────────┐
│ 是不是 openrouter │
└────────────────┘
  ├─【是】→ provider=openrouter
  └─【否】→ provider=openai

┌─────────────────────┐
│ provider=openrouter │
└─────────────────────┘
  └─→ 讀 OPENROUTER_MODEL

┌─────────────────┐
│ provider=openai │
└─────────────────┘
  └─→ 讀 OPENAI_MODEL

┌────────────────────┐
│ 讀 OPENROUTER_MODEL │
└────────────────────┘
  └─→ 得到 model

┌────────────────┐
│ 讀 OPENAI_MODEL │
└────────────────┘
  └─→ 得到 model
```

預設值：

| 設定 | 預設 |
|---|---|
| `AI_PROVIDER` | `openai` |
| `OPENAI_MODEL` | `gpt-5.4-mini` |
| `OPENROUTER_MODEL` | `openai/gpt-5.4` |

### Step 4：免費 quota gate

如果啟用 `OPENAI_COMPLIMENTARY_GATE_ENABLED`，而且使用者沒有提供自己的 `api_key`，後端會檢查免費額度。

```text
┌─────────────────┐
│ 免費 gate enabled │
└─────────────────┘
  └─→ provider 是 openai?

┌────────────────────┐
│ provider 是 openai? │
└────────────────────┘
  ├─【否】→ 拒絕: provider mismatch
  └─【是】→ model family 符合?

┌──────────────────┐
│ model family 符合? │
└──────────────────┘
  ├─【否】→ 拒絕: model mismatch
  └─【是】→ 預估本次最多可能消耗 tokens

┌───────────────────┐
│ 預估本次最多可能消耗 tokens │
└───────────────────┘
  └─→ Upstash Redis 檢查今日 quota

┌──────────────────────────┐
│ Upstash Redis 檢查今日 quota │
└──────────────────────────┘
  ├─【超過】→ 拒絕: daily free token limit
  └─【通過】→ 進入生成流程
```

它估算 quota 時不是只算一次 graph，而是把 retry 也算進去：

| Token 類型 | 用途 |
|---|---|
| explanation input | file tree + README |
| explanation output cap | 第一階段架構解釋最大輸出 |
| graph static input | explanation + file tree + repo metadata |
| graph output cap | graph JSON 最大輸出 |
| retry input buffer | graph retry 時會多帶 previous graph / validation feedback |
| retry 次數 | 最多 3 次 graph attempts |

這不是為了 graph 正確性，而是為了避免免費 server key 被一次 request 用爆。

### Step 5：GitHub auth 決策

GitHubService 會依照優先順序選 token。

```text
┌───────────────┐
│ GitHubService │
└───────────────┘
  └─→ request 有 github_pat?

┌───────────────────────┐
│ request 有 github_pat? │
└───────────────────────┘
  ├─【有】→ 使用 request PAT
  └─【沒有】→ 環境變數 GITHUB_PAT?

┌──────────────────┐
│ 環境變數 GITHUB_PAT? │
└──────────────────┘
  ├─【有】→ 使用 env PAT
  └─【沒有】→ GitHub App credentials 完整?

┌────────────────────────────┐
│ GitHub App credentials 完整? │
└────────────────────────────┘
  ├─【有】→ 產生 GitHub App installation token
  └─【沒有】→ 匿名 GitHub API
```

優先順序：

| 順序 | Auth 來源 |
|---|---|
| 1 | request 傳入的 `github_pat` |
| 2 | server env `GITHUB_PAT` |
| 3 | GitHub App installation token |
| 4 | 無 token，匿名 GitHub API |

GitHub App token 會 cache 到 class-level shared token，接近過期前才重新產生。

### Step 6：抓 repo metadata

呼叫：

```text
GET https://api.github.com/repos/{username}/{repo}
```

取得：

| 欄位 | 後面用途 |
|---|---|
| `default_branch` | 產生 GitHub click link 時要用 |
| `private` | 決定 artifact visibility |
| `stargazers_count` | public browse index 顯示用 |

如果 GitHub 回 404，後端丟：

```text
Repository not found.
```

如果其他 HTTP error，會保留 status code 與 GitHub response text。

### Step 7：抓 recursive file tree

呼叫：

```text
GET https://api.github.com/repos/{username}/{repo}/git/trees/{branch}?recursive=1
```

GitHub 回來的是整個 repo 的 tree。後端只取 `path`，再串成一個文字版 `file_tree`：

```text
README.md
package.json
src/app/page.tsx
src/server/generate/graph.ts
...
```

視覺化：

```text
┌──────────────────────┐
│ GitHub tree API JSON │
└──────────────────────┘
        ↓
┌────────────────┐
│ 取出每個 item.path │
└────────────────┘
        ↓
┌──────────────────────┐
│ 過濾 excluded patterns │
└──────────────────────┘
        ↓
┌──────────┐
│ 用換行 join │
└──────────┘
        ↓
┌────────────────┐
│ file_tree text │
└────────────────┘
```

### Step 8：過濾不適合分析的檔案

它不會把所有 path 都丟給 LLM，會排除雜訊。

| 類型 | 例子 |
|---|---|
| dependencies | `node_modules/`, `vendor/`, `venv/` |
| compiled artifacts | `.pyc`, `.pyo`, `.pyd`, `.so`, `.dll`, `.class` |
| images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.ico`, `.svg`, `.webp` |
| fonts | `.ttf`, `.woff` |
| cache/temp | `__pycache__/`, `.cache/`, `.tmp/` |
| lock files | `yarn.lock`, `poetry.lock` |
| IDE folders | `.vscode/`, `.idea/` |
| logs/minified | `*.log`, `.min.` |

注意一個細節：它的 `_should_include_file` 是用 `pattern in lower_path` 做 substring check，不是完整 glob parser。

所以：

| Pattern | 實際效果 |
|---|---|
| `.min.` | 只要 path 裡有 `.min.` 就排除 |
| `*.log` | 因為不是 glob match，只有 path 裡真的包含 `*.log` 才會命中 |

### Step 9：file tree 大小限制

後端有兩層 repo 過大保護。

```text
┌──────────────────────────┐
│ GitHub tree API response │
└──────────────────────────┘
  └─→ data.truncated == true?

┌─────────────────────────┐
│ data.truncated == true? │
└─────────────────────────┘
  ├─【是】→ Repository too large
  └─【否】→ 組成 file_tree

┌──────────────┐
│ 組成 file_tree │
└──────────────┘
  └─→ file_tree 長度 > 780000 chars?

┌──────────────────────────────┐
│ file_tree 長度 > 780000 chars? │
└──────────────────────────────┘
  ├─【是】→ Repository too large
  └─【否】→ 繼續
```

這是為了避免超大 repo 造成 token 爆炸。

### Step 10：抓 README

呼叫：

```text
GET https://api.github.com/repos/{username}/{repo}/readme
```

處理流程：

```text
┌───────────────────┐
│ GitHub README API │
└───────────────────┘
  └─→ size > 750000 bytes?

┌──────────────────────┐
│ size > 750000 bytes? │
└──────────────────────┘
  ├─【是】→ Repository too large
  └─【否】→ content 存在?

┌─────────────┐
│ content 存在? │
└─────────────┘
  ├─【否】→ No README found
  └─【是】→ encoding == base64?

┌─────────────────────┐
│ encoding == base64? │
└─────────────────────┘
  ├─【是】→ base64 decode
  └─【否】→ 直接使用 content

┌───────────────┐
│ base64 decode │
└───────────────┘
  └─→ decoded README > 750000 bytes?

┌──────────────┐
│ 直接使用 content │
└──────────────┘
  └─→ decoded README > 750000 bytes?

┌────────────────────────────────┐
│ decoded README > 750000 bytes? │
└────────────────────────────────┘
  ├─【是】→ Repository too large
  └─【否】→ readme text
```

如果沒有 README，後端會報錯。GitDiagram 把 README 視為必要輸入。

### Step 11：組成 GithubData

後端最後會得到：

```json
{
  "default_branch": "main",
  "file_tree": "README.md\nsrc/...\n",
  "readme": "# Project ...",
  "is_private": false,
  "stargazer_count": 123
}
```

這份 `GithubData` 是後續 LLM 理解 repo 的唯一主要輸入。

也就是說，它沒有讀每個 source file 的內容。

```text
┌──────────┐
│ metadata │
└──────────┘
  └─→ GithubData

┌───────────┐
│ file_tree │
└───────────┘
  └─→ GithubData

┌────────┐
│ README │
└────────┘
  └─→ GithubData
```

### Step 12：估算 token 與成本

在真正 call LLM 前，後端會估算成本。

```text
┌────────────────────┐
│ file_tree + README │
└────────────────────┘
  └─→ 算 explanation prompt tokens

┌────────────────────────────────────────────┐
│ file_tree + empty explanation placeholders │
└────────────────────────────────────────────┘
  └─→ 算 graph prompt tokens

┌─────────────────────────────┐
│ 算 explanation prompt tokens │
└─────────────────────────────┘
  └─→ 估算 input tokens

┌───────────────────────┐
│ 算 graph prompt tokens │
└───────────────────────┘
  └─→ 估算 input tokens

┌─────────────────┐
│ 估算 input tokens │
└─────────────────┘
  └─→ 加上 output caps

┌────────────────┐
│ 加上 output caps │
└────────────────┘
  └─→ 依 model pricing 算 cost
```

它會估兩段 prompt：

| Prompt | 用途 |
|---|---|
| `SYSTEM_FIRST_PROMPT` + `file_tree/readme` | 第一段架構解釋 |
| `SYSTEM_GRAPH_PROMPT` + `file_tree/repo metadata/empty explanation` | 第二段 graph JSON |

如果 provider 是 OpenAI 且使用者有自己的 api key，會嘗試用 `responses.input_tokens.count` 精準計算。

如果不能精準計算，就 fallback：

```text
ceil(len(text) / 3) + 32
```

output cap：

| 階段 | max output tokens |
|---|---|
| explanation | 12000 |
| graph JSON | 6000 |

### Step 13：token limit gate

成本估算後，還會檢查 input tokens。

```text
┌────────────────────────────────────┐
│ estimated explanation input tokens │
└────────────────────────────────────┘
  └─→ > 195000?

┌───────────┐
│ > 195000? │
└───────────┘
  ├─【是】→ 拒絕: TOKEN_LIMIT_EXCEEDED
  └─【否】→ > 100000 且沒有 api_key?

┌───────────────────────┐
│ > 100000 且沒有 api_key? │
└───────────────────────┘
  ├─【是】→ 拒絕: API_KEY_REQUIRED
  └─【否】→ 可以生成
```

| Limit | 條件 | 結果 |
|---|---|---|
| `100_000` | free generation 超過這個，但還沒到 hard limit | 要使用者提供自己的 API key |
| `195_000` | hard limit | 直接拒絕 |

### Step 14：把資料包成 tagged message

傳給 LLM 的 user message 不是隨便串字串，而是用 XML-like tag。

第一段：

```xml
<file_tree>
README.md
src/app/page.tsx
...
</file_tree>
<readme>
# Project README
...
</readme>
```

第二段：

```xml
<explanation>
...
</explanation>
<file_tree>
...
</file_tree>
<repo_owner>
owner
</repo_owner>
<repo_name>
repo
</repo_name>
<previous_graph>
...
</previous_graph>
<validation_feedback>
...
</validation_feedback>
```

這樣做的好處是每個輸入區塊很清楚，模型比較不容易混淆 README、file tree、feedback。

### Step 15：LLM Pass 1 產生架構解釋

第一段 LLM 使用：

| 設定 | 值 |
|---|---|
| system prompt | `SYSTEM_FIRST_PROMPT` |
| reasoning effort | `medium` |
| max output tokens | `12000` |
| output mode | streaming text |

Prompt 目標：

| 要求 | 目的 |
|---|---|
| repo-specific | 不要產生通用架構描述 |
| 找 main subsystems | 後面 graph nodes 需要 |
| 找 data flows | 後面 graph edges 需要 |
| 找 boundaries | 後面 groups / subsystems 需要 |
| 不要 Mermaid / JSON | 避免第一階段格式污染 |

輸出格式要求：

```xml
<explanation>
...
</explanation>
```

後端會 stream 每個 chunk 給前端，同時累積成 `explanation_response`。

### Step 16：抽出 explanation

後端用 `_extract_tagged_section(text, "explanation")` 抽出 `<explanation>` 中間內容。

```text
┌──────────────┐
│ LLM raw text │
└──────────────┘
  └─→ 有 opening tag 和 closing tag?

┌──────────────────────────────┐
│ 有 opening tag 和 closing tag? │
└──────────────────────────────┘
  ├─【有】→ 取中間內容
  └─【沒有】→ 使用整段 text.strip

┌────────┐
│ 取中間內容  │
└────────┘
  └─→ 內容是否空白?

┌─────────────────┐
│ 使用整段 text.strip │
└─────────────────┘
  └─→ 內容是否空白?

┌─────────┐
│ 內容是否空白? │
└─────────┘
  ├─【空白】→ error: no usable output
  └─【非空】→ explanation
```

這裡有一個重要限制：

| 行為 | 意義 |
|---|---|
| 如果 tag 不存在，會 fallback 成整段文字 | 容錯性高 |
| 但不會強制模型一定有 tag | 格式正確性較弱 |
| 空白才會失敗 | 只保證有內容，不保證內容一定好 |

### Step 17：建立 file tree lookup

在產生 graph 前，後端把 file tree 轉成 set：

```text
README.md
src/app/page.tsx
src/server/generate/graph.ts
```

變成：

```json
[
  "README.md",
  "src/app/page.tsx",
  "src/server/generate/graph.ts"
]
```

用途是後面驗證：

```text
node.path 必須真的存在於 file_tree_lookup
```

### Step 18：LLM Pass 2 產生 structured graph JSON

第二段 LLM 使用：

| 設定 | 值 |
|---|---|
| system prompt | `SYSTEM_GRAPH_PROMPT` |
| reasoning effort | `low` |
| max output tokens | `6000` |
| output mode | structured output |
| schema | `DiagramGraph` |

這一步很關鍵：後端不是叫 LLM 回傳普通文字，而是要求模型照 Pydantic/Zod schema 回傳 structured output。

輸出的目標 JSON：

```json
{
  "groups": [
    {
      "id": "backend",
      "label": "Backend",
      "description": "API and generation workflow"
    }
  ],
  "nodes": [
    {
      "id": "github_service",
      "label": "GitHub Service",
      "type": "Repository Fetcher",
      "description": "Fetches metadata, README, and file tree",
      "groupId": "backend",
      "path": "backend/app/services/github_service.py",
      "shape": "box"
    }
  ],
  "edges": [
    {
      "from": "github_service",
      "to": "graph_planner",
      "label": "provides file tree",
      "description": "The graph planner receives repo structure as input",
      "style": "solid"
    }
  ]
}
```

### Step 19：Graph JSON schema 限制

```text
┌──────────────┐
│ DiagramGraph │
└──────────────┘
  ├─→ groups
  ├─→ nodes
  └─→ edges

┌────────┐
│ groups │
└────────┘
  ├─→ id
  ├─→ label
  └─→ description

┌────────┐
│ nodes  │
└────────┘
  ├─→ id
  ├─→ label
  ├─→ type
  ├─→ description
  ├─→ groupId
  ├─→ path
  └─→ shape

┌────────┐
│ edges  │
└────────┘
  ├─→ from
  ├─→ to
  ├─→ label
  ├─→ description
  └─→ style
```

欄位限制：

| 欄位 | 限制 |
|---|---|
| `groups` | 最多 10 |
| `nodes` | 最少 1，最多 34 |
| `edges` | 最多 48 |
| `group.id` | regex `^[a-z][a-z0-9_]*$` |
| `node.id` | regex `^[a-z][a-z0-9_]*$` |
| `edge.from` / `edge.to` | regex `^[a-z][a-z0-9_]*$` |
| `label` | 1 到 72 字 |
| `type` | 1 到 72 字 |
| `description` | 最多 240 字，可為 null |
| `path` | 1 到 512 字，可為 null |
| `shape` | `box/database/queue/document/circle/hexagon/null` |
| `style` | `solid/dashed/null` |

這一層確保 JSON 形狀正確，但還不等於語意正確。

### Step 20：Graph JSON validation

Schema parse 通過後，後端再做 graph-level validation。

```text
┌────────────┐
│ Graph JSON │
└────────────┘
  └─→ 檢查 group id 是否重複

┌──────────────────┐
│ 檢查 group id 是否重複 │
└──────────────────┘
  └─→ 檢查 node id 是否重複

┌─────────────────┐
│ 檢查 node id 是否重複 │
└─────────────────┘
  └─→ 檢查 node.groupId 是否存在

┌──────────────────────┐
│ 檢查 node.groupId 是否存在 │
└──────────────────────┘
  └─→ 檢查 node.path 是否真的在 file_tree

┌──────────────────────────────┐
│ 檢查 node.path 是否真的在 file_tree │
└──────────────────────────────┘
  └─→ 檢查 edge.from 是否存在

┌───────────────────┐
│ 檢查 edge.from 是否存在 │
└───────────────────┘
  └─→ 檢查 edge.to 是否存在

┌─────────────────┐
│ 檢查 edge.to 是否存在 │
└─────────────────┘
  └─→ issues.length == 0?

┌─────────────────────┐
│ issues.length == 0? │
└─────────────────────┘
  ├─【是】→ valid graph JSON
  └─【否】→ format validation feedback
```

validation feedback 長這樣：

```text
nodes.3.path: Path "src/fake.ts" does not exist in the repository file tree.
edges.2.to: Unknown target node id "missing_node".
```

### Step 21：失敗就 retry graph planning

最多嘗試 3 次。

```text
┌───────────────────────────────────────┐
│ Backend sends explanation + file_tree │
└───────────────────────────────────────┘
  └─→ LLM returns graph attempt 1

┌─────────────────────────────┐
│ LLM returns graph attempt 1 │
└─────────────────────────────┘
  └─→ Backend validates graph

┌─────────────────────────┐
│ Backend validates graph │
└─────────────────────────┘
  └─→ valid?

┌────────┐
│ valid? │
└────────┘
  ├─【No】→ Backend formats validation feedback
  └─【Yes】→ Backend accepts valid graph JSON

┌─────────────────────────────────────┐
│ Backend formats validation feedback │
└─────────────────────────────────────┘
  └─→ Backend sends previous_graph + feedback

┌─────────────────────────────────────────┐
│ Backend sends previous_graph + feedback │
└─────────────────────────────────────────┘
  └─→ LLM returns graph attempt 2

┌─────────────────────────────┐
│ LLM returns graph attempt 2 │
└─────────────────────────────┘
  └─→ Backend validates graph
```

每次 attempt 都會記錄到 audit：

| 欄位 | 記錄 |
|---|---|
| `attempt` | 第幾次 |
| `rawOutput` | LLM 原始 structured output text |
| `graph` | parse 後 graph |
| `validationFeedback` | 如果失敗，記錄失敗原因 |
| `status` | `succeeded` 或 `failed` |
| `createdAt` | 產生時間 |

如果 3 次都失敗，流程停止，回：

```json
{
  "status": "error",
  "error_code": "GRAPH_VALIDATION_FAILED",
  "failure_stage": "graph_validating",
  "validation_error": "..."
}
```

### Step 22：成功得到的 graph JSON 是什麼

成功後，後端會把 valid graph 寫入 audit：

```json
{
  "graph": {
    "groups": [],
    "nodes": [],
    "edges": []
  }
}
```

這就是 GitDiagram 後端真正的「圖資料模型」。

Mermaid 不是主資料模型，Mermaid 是後面由這份 graph JSON 編譯出來的 render format。

```text
┌──────────────────┐
│ valid graph JSON │
└──────────────────┘
  ├─→ compile Mermaid
  └─→ persist artifact.graph

┌─────────────────┐
│ compile Mermaid │
└─────────────────┘
  └─→ persist artifact.diagram
```

### Step 23：Graph JSON 到 Mermaid

雖然使用者問的是到 JSON，但 GitDiagram 會繼續把 JSON 編譯成 Mermaid。

```text
┌─────────────┐
│ groups data │
└─────────────┘
  └─→ subgraph

┌────────────┐
│ nodes data │
└────────────┘
  └─→ Mermaid nodes

┌────────────┐
│ edges data │
└────────────┘
  └─→ Mermaid arrows

┌───────────┐
│ node.path │
└───────────┘
  └─→ click GitHub URL

┌─────────────┐
│ group order │
└─────────────┘
  └─→ color class

┌──────────┐
│ subgraph │
└──────────┘
  └─→ flowchart TD

┌───────────────┐
│ Mermaid nodes │
└───────────────┘
  └─→ flowchart TD

┌────────────────┐
│ Mermaid arrows │
└────────────────┘
  └─→ flowchart TD

┌──────────────────┐
│ click GitHub URL │
└──────────────────┘
  └─→ flowchart TD

┌─────────────┐
│ color class │
└─────────────┘
  └─→ flowchart TD
```

轉換規則：

| Graph 欄位 | Mermaid 結果 |
|---|---|
| `groups[].label` | `subgraph group_x["Label"]` |
| `nodes[].id` | 加上 `node_` prefix |
| `nodes[].label` | node 主文字 |
| `nodes[].type` | 如果不是太 generic，顯示成第二行 |
| `nodes[].path` | 如果是檔案，顯示 `[filename]` hint |
| `nodes[].shape` | 控制 box/database/circle/hexagon |
| `edges[].style` | `solid` 變 `-->`，`dashed` 變 `-.->` |
| `edges[].label` | arrow label |
| `nodes[].path` | 產生 `click node_x "https://github.com/..."` |

文字會做 escaping：

| 字元 | 處理 |
|---|---|
| `\` | 轉成 `\\` |
| `"` | 轉成 `\"` |
| 前後空白 | trim |

### Step 24：Mermaid 語法驗證

Mermaid 產生後，後端還會用 Mermaid parser 驗證。

```text
┌──────────────────┐
│ compiled Mermaid │
└──────────────────┘
  └─→ validate_mermaid_syntax

┌─────────────────────────┐
│ validate_mermaid_syntax │
└─────────────────────────┘
  └─→ 呼叫 bun scripts/validate_mermaid.mjs

┌─────────────────────────────────────┐
│ 呼叫 bun scripts/validate_mermaid.mjs │
└─────────────────────────────────────┘
  └─→ backend/lib/mermaid-validator.ts

┌──────────────────────────────────┐
│ backend/lib/mermaid-validator.ts │
└──────────────────────────────────┘
  └─→ 建立 server-side DOM

┌────────────────────┐
│ 建立 server-side DOM │
└────────────────────┘
  └─→ patch DOMPurify

┌─────────────────┐
│ patch DOMPurify │
└─────────────────┘
  └─→ mermaid.initialize

┌────────────────────┐
│ mermaid.initialize │
└────────────────────┘
  └─→ mermaid.parse diagram

┌───────────────────────┐
│ mermaid.parse diagram │
└───────────────────────┘
  ├─【成功】→ valid true
  └─【失敗】→ 回傳 message/line/token/expected
```

FastAPI 版有：

| 保護 | 說明 |
|---|---|
| subprocess | 用 `bun scripts/validate_mermaid.mjs` 跑 JS validator |
| timeout | 15 秒超時 |
| semaphore | 一次只跑一個 Mermaid validation |
| JSON parse result | validator 必須回 valid JSON |
| normalized error | 把 Mermaid server runtime 常見錯誤轉成可讀訊息 |

如果 Mermaid validation 失敗：

```json
{
  "status": "error",
  "error_code": "COMPILER_VALIDATION_FAILED",
  "failure_stage": "diagram_compiling",
  "validation_error": "..."
}
```

### Step 25：存成功 artifact

如果 graph JSON 有效、Mermaid 也有效，後端會存 artifact。

```text
┌──────────────────┐
│ valid graph JSON │
└──────────────────┘
  └─→ artifact

┌──────────────────┐
│ compiled Mermaid │
└──────────────────┘
  └─→ artifact

┌─────────────┐
│ explanation │
└─────────────┘
  └─→ artifact

┌───────────────┐
│ audit summary │
└───────────────┘
  └─→ artifact

┌──────────┐
│ artifact │
└──────────┘
  ├─→ Cloudflare R2
  └─→ public browse index
```

artifact 內容：

```json
{
  "version": 1,
  "visibility": "public",
  "username": "owner",
  "repo": "repo",
  "stargazerCount": 123,
  "diagram": "flowchart TD ...",
  "explanation": "...",
  "graph": {
    "groups": [],
    "nodes": [],
    "edges": []
  },
  "generatedAt": "...",
  "usedOwnKey": false,
  "latestSessionSummary": {},
  "lastSuccessfulAt": "..."
}
```

Public repo artifact key：

```text
public/v1/{username}/{repo}.json
```

Private repo artifact key：

```text
private/v1/{hmac_pat_namespace}/{username}/{repo}.json
```

Private repo 不直接把 PAT 放進 key，而是用 `CACHE_KEY_SECRET` 對 PAT 做 HMAC。

### Step 26：SSE 回傳前端

整個流程會一路 stream 狀態給前端。

```text
┌────────────────────────────────┐
│ Frontend POST /generate/stream │
└────────────────────────────────┘
        ↓
┌───────────────────────┐
│ Backend sends started │
└───────────────────────┘
        ↓
┌───────────────────────────────────────────┐
│ Backend calls GitHub metadata/tree/readme │
└───────────────────────────────────────────┘
        ↓
┌────────────────────────────────┐
│ Backend sends explanation_sent │
└────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ Backend sends explanation prompt to LLM │
└─────────────────────────────────────────┘
        ↓
┌────────────────────────────────┐
│ LLM streams explanation chunks │
└────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────┐
│ Backend sends explanation_chunk to frontend │
└─────────────────────────────────────────────┘
        ↓
┌──────────────────────────┐
│ Backend sends graph_sent │
└──────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│ Backend sends structured graph prompt to LLM │
└──────────────────────────────────────────────┘
        ↓
┌────────────────────────┐
│ LLM returns graph JSON │
└────────────────────────┘
        ↓
┌─────────────────────────────────┐
│ Backend sends graph to frontend │
└─────────────────────────────────┘
        ↓
┌──────────────────────────┐
│ Backend compiles diagram │
└──────────────────────────┘
        ↓
┌─────────────────────────────────┐
│ Backend sends diagram_compiling │
└─────────────────────────────────┘
        ↓
┌───────────────────────────────────┐
│ Backend saves artifact to storage │
└───────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────────┐
│ Backend sends complete + graph + diagram + audit │
└──────────────────────────────────────────────────┘
```

最後 `complete` event 會包含：

| 欄位 | 說明 |
|---|---|
| `diagram` | Mermaid diagram |
| `explanation` | 第一階段架構解釋 |
| `graph` | valid graph JSON |
| `graph_attempts` | graph retry 紀錄 |
| `latest_session_audit` | 這次生成的完整 audit |
| `cost_summary` | 預估或實際成本 |
| `generated_at` | 產生時間 |

## 它如何確保結果正確

GitDiagram 的「正確」不是指 100% 理解 codebase 語意，而是它做了多層保護，確保輸出至少是可 parse、可連線、可點擊、不引用不存在路徑、可被 Mermaid render。

```text
┌───────────────────┐
│ Input correctness │
└───────────────────┘
  └─→ Request schema

┌───────────────────────┐
│ Repo data correctness │
└───────────────────────┘
  └─→ GitHub API status / size limits / filters

┌─────────────┐
│ Cost safety │
└─────────────┘
  └─→ token estimate / quota / hard limit

┌──────────────────┐
│ LLM output shape │
└──────────────────┘
  └─→ Structured output schema

┌─────────────────┐
│ Graph integrity │
└─────────────────┘
  └─→ Graph validator

┌──────────────────┐
│ Retry correction │
└──────────────────┘
  └─→ validation feedback loop

┌────────────────────┐
│ Render correctness │
└────────────────────┘
  └─→ Deterministic compiler

┌─────────────────────┐
│ Mermaid correctness │
└─────────────────────┘
  └─→ Mermaid parser validation

┌──────────────┐
│ Traceability │
└──────────────┘
  └─→ audit / graphAttempts / evidence paths
```

### 正確性保護 1：Request schema

| 保護 | 能確保什麼 | 不能確保什麼 |
|---|---|---|
| Pydantic request validation | request 至少有 owner/repo，optional key 不會是空字串 | owner/repo 是否真的存在 |

### 正確性保護 2：GitHub API error handling

| 保護 | 能確保什麼 | 不能確保什麼 |
|---|---|---|
| 404 轉成 repo not found | repo 不存在時不會繼續生成 |
| 非 2xx 轉成錯誤 | API fail 不會被當成正常資料 |
| `data.truncated` 檢查 | GitHub tree 被截斷時不會用不完整 tree |
| empty path 檢查 | 空 repo 或不可讀時會失敗 |

### 正確性保護 3：大小限制

| 保護 | 能確保什麼 | 不能確保什麼 |
|---|---|---|
| file tree 780k chars limit | 不會把過大的 tree 丟給 LLM |
| README 750k bytes limit | 不會把過大的 README 丟給 LLM |
| 195k token hard limit | 超出模型/系統承受範圍就拒絕 |
| 100k free limit | 免費模式下避免成本失控 |

### 正確性保護 4：Prompt 分階段

| 保護 | 能確保什麼 | 不能確保什麼 |
|---|---|---|
| 第一階段只產 explanation | 降低直接產圖的混亂 |
| 第二階段只產 structured graph | 圖資料格式更可控 |
| XML-like tagged input | 模型比較容易分辨 file tree、README、feedback |
| Prompt 要求 path 必須存在 | 降低假路徑機率 |

### 正確性保護 5：Structured output schema

| 保護 | 能確保什麼 | 不能確保什麼 |
|---|---|---|
| Pydantic/Zod schema | graph 一定有 `groups/nodes/edges` |
| id regex | Mermaid id 比較穩定 |
| enum shape/style | renderer 不會收到未知 shape/style |
| max lengths | 避免 label/description 過長 |
| min/max node count | 避免空圖或過大圖 |

### 正確性保護 6：Graph integrity validation

| 檢查 | 防止的問題 |
|---|---|
| duplicate group id | subgraph id 撞名 |
| duplicate node id | edge 指向不確定 |
| unknown groupId | node 掛到不存在 group |
| path not in file tree | LLM 編不存在的檔案 |
| edge source missing | 斷掉的 edge |
| edge target missing | 斷掉的 edge |

這是它最核心的 correctness gate。

### 正確性保護 7：Validation feedback retry

如果 graph validation 失敗，後端不會直接接受，也不會自己猜著修。

它會把：

| 回饋 | 給誰 |
|---|---|
| `previous_graph` | LLM |
| `validation_feedback` | LLM |

再要求 LLM 重新輸出完整 graph。

這個設計讓模型可以修正：

| 常見錯誤 | 修正方式 |
|---|---|
| path 不存在 | 換成 file tree 中真的存在的 path，或設成 null |
| edge 指到不存在 node | 改 edge endpoint，或補 node |
| groupId 不存在 | 改成正確 groupId，或設成 null |
| id 重複 | 改成唯一 id |

### 正確性保護 8：Deterministic compiler

通過 validation 後，Mermaid 不是 LLM 寫的，而是程式固定規則產生。

| 保護 | 作用 |
|---|---|
| node id 加 `node_` prefix | 避免和 Mermaid keyword / group id 撞名 |
| group id 加 `group_` prefix | 避免和 node id 撞名 |
| label escaping | 避免 quote/backslash 破壞 Mermaid |
| path 轉 GitHub URL | clickable link 規則固定 |
| classDef 固定 | 視覺樣式穩定 |

### 正確性保護 9：Mermaid parser validation

compile 完後還要 parse。

| 保護 | 作用 |
|---|---|
| `mermaid.parse` | 確認 Mermaid 語法真的可被 Mermaid 接受 |
| timeout 15 秒 | validator 不會無限卡住 |
| subprocess | Python/FastAPI 後端可以呼叫 JS Mermaid runtime |
| normalized error | 方便回傳 failure reason |

### 正確性保護 10：Persistence/audit

每次結果都會帶 audit。

| audit 欄位 | 用途 |
|---|---|
| `graphAttempts` | 看每次 graph JSON 是怎麼失敗或成功 |
| `validationFeedback` | 看 validator 抓到什麼問題 |
| `stageUsages` | 看每階段 token usage |
| `timeline` | 看流程跑到哪一步 |
| `failureStage` | 失敗定位 |
| `compilerError` | Mermaid compile/parse 問題 |

這讓錯誤可以被追蹤，不是只丟一個黑箱分數。

## 它沒有保證的事情

這點對 KAI-Mind 很重要。

GitDiagram 做了很多格式與結構正確性保護，但它沒有完全保證「架構理解一定正確」。

| 沒有完全保證 | 原因 |
|---|---|
| node 的語意一定正確 | LLM 主要看 file tree + README，不讀全部 source code |
| edge 的資料流一定真實 | validator 只檢查 edge endpoint 存在，不檢查 code call graph |
| null path 的 node 一定真實 | node.path 可以是 null，這種 node 無法被 file tree 驗證 |
| README 描述一定準確 | README 可能過期 |
| file filter 一定正確 | filter 是 substring check，不是完整語言級 parser |
| explanation 一定有正確 XML tag | tag missing 時會 fallback 成整段文字 |

所以它的 correctness 更準確地說是：

```text
它確保輸出格式正確、路徑可追溯、圖可 render。
它不能完全確保 LLM 對 codebase 的語意理解一定正確。
```

## 對 KAI-Mind 的直接啟發

GitDiagram 的做法如果搬到 KAI-Mind，應該改成：

```text
┌────────────┐
│ input repo │
└────────────┘
  └─→ read-only scanner

┌───────────────────┐
│ read-only scanner │
└───────────────────┘
  └─→ deterministic facts

┌─────────────────────┐
│ deterministic facts │
└─────────────────────┘
  └─→ ai_system_map.json

┌────────────────────┐
│ ai_system_map.json │
└────────────────────┘
  ├─→ schema validation
  └─→ optional LLM explanation

┌───────────────────┐
│ schema validation │
└───────────────────┘
  └─→ path/evidence validation

┌──────────────────────────┐
│ path/evidence validation │
└──────────────────────────┘
  └─→ viewer graph model

┌────────────────────┐
│ viewer graph model │
└────────────────────┘
  ├─→ interactive map
  └─→ replay timeline

┌──────────────────────────┐
│ optional LLM explanation │
└──────────────────────────┘
  └─→ 只產生白話，不改 facts
```

對 Local AI Health Doctor 來說，最重要的原則是：

| GitDiagram | KAI-Mind 應該怎麼改 |
|---|---|
| LLM 從 file tree + README 推 graph | scanner 從實際檔案/config/log/evidence 產 facts |
| graph JSON 是主要圖模型 | `ai_system_map.json` 是主要 contract |
| Mermaid 是 render output | viewer 是 render output |
| validator 檢查 graph path/edge | validator 檢查 RAG node、retriever、vector store、config、evidence |
| LLM 可 retry 修 graph | LLM 最多修 explanation，不應修改 readiness facts |
| click GitHub path | click local evidence / file path |
| graphAttempts audit | scan/replay audit |

最適合照抄的是這條 pipeline：

```text
┌────────────┐
│ facts JSON │
└────────────┘
        ↓
┌─────────────────┐
│ schema validate │
└─────────────────┘
        ↓
┌────────────────────┐
│ integrity validate │
└────────────────────┘
        ↓
┌──────────────────────────┐
│ deterministic view model │
└──────────────────────────┘
        ↓
┌─────────────────┐
│ render validate │
└─────────────────┘
        ↓
┌────────┐
│ audit  │
└────────┘
```

## 後端有兩套入口

GitDiagram 同時保留兩種 backend implementation：

| 後端 | 位置 | 用途 |
|---|---|---|
| FastAPI backend | `backend/app/routers/generate.py` | README 說 production 可部署在 Railway |
| Next.js route handler | `src/app/api/generate/stream/route.ts` | Next app 內建 API route |

兩套邏輯很像，核心流程都是：

```text
┌─────────┐
│ request │
└────┬────┘
     ↓
┌─────────────────┐
│ get GitHub data │
└────┬────────────┘
     ↓
┌─────────────────────┐
│ estimate cost/quota │
└────┬────────────────┘
     ↓
┌────────────────────┐
│ stream explanation │
└────┬───────────────┘
     ↓
┌─────────────────────┐
│ generate graph JSON │
└────┬────────────────┘
     ↓
┌────────────────┐
│ validate graph │
└────┬───────────┘
     ↓
┌─────────────────┐
│ compile Mermaid │
└────┬────────────┘
     ↓
┌──────────────────┐
│ validate Mermaid │
└────┬─────────────┘
     ↓
┌────────────────┐
│ persist result │
└────┬───────────┘
     ↓
┌────────────────┐
│ SSE 回傳給前端 │
└────────────────┘
```

FastAPI 主流程在 `backend/app/routers/generate.py`：

| 功能 | 程式位置 |
|---|---|
| request schema | `GenerateRequest`, lines 61-65 |
| 抓 GitHub data | `_get_github_data`, lines 161-170 |
| 估算成本與 token | lines 526-548 |
| 第一段 LLM explanation | lines 691-747 |
| 第二段 LLM graph planning | lines 750-858 |
| graph validation retry | lines 764-858 |
| compile Mermaid | lines 878-896 |
| validate Mermaid | lines 899-921 |
| persist success | lines 937-964 |

Next.js route 的相同流程在 `src/app/api/generate/stream/route.ts`，尤其是 graph retry、compile、persist 這段，集中在 lines 549-780。

## GitHub repo 是怎麼被讀進來的

後端只抓三種主要資料：

```text
┌────────────┐
│ GitHub API │
└────────────┘
  ├─→ repo metadata
  ├─→ recursive file tree
  └─→ README

┌───────────────┐
│ repo metadata │
└───────────────┘
  └─→ default branch / private / stars

┌─────────────────────┐
│ recursive file tree │
└─────────────────────┘
  └─→ file_tree text

┌────────┐
│ README │
└────────┘
  └─→ readme text
```

來源：`backend/app/services/github_service.py`

| 功能 | 說明 |
|---|---|
| `get_repo_metadata` | 取得 default branch、是否 private、star count，lines 167-176 |
| `get_github_file_paths_as_list` | 用 GitHub tree API 抓 recursive file tree，lines 178-200 |
| `get_github_readme` | 抓 README 並解 base64，lines 202-227 |
| `get_github_data` | 組合成 `GithubData`，lines 229-239 |

它會過濾掉一些不適合丟給 LLM 的內容：

```text
node_modules/
vendor/
venv/
圖片
字型
lock files
IDE folder
cache/temp folder
```

限制也很明確：

| 限制 | 值 |
|---|---|
| file tree 最大字元數 | `780_000` |
| README 最大 bytes | `750_000` |
| 後面生成流程 hard token limit | `195_000` |

這代表 GitDiagram 主要看的是「repo 結構 + README」，不是深入讀每個 source file 的內容。

## LLM 分兩階段使用

GitDiagram 不是一次叫模型直接輸出圖，而是分兩次。

### 第一階段：產生架構解釋

Prompt 在 `backend/app/prompts.py` 的 `SYSTEM_FIRST_PROMPT`。

輸入：

```text
<file_tree>...</file_tree>
<readme>...</readme>
```

輸出：

```xml
<explanation>
...
</explanation>
```

它要求模型像 principal software engineer 一樣解釋 repo 架構，重點是：

| 要求 | 用途 |
|---|---|
| repo-specific | 避免講空話 |
| 找 main subsystems | 幫下一步抽 node |
| 找 data flows / boundaries | 幫下一步抽 edge |
| 不輸出 Mermaid / JSON | 避免第一步就混格式 |

FastAPI 對應邏輯在 `backend/app/routers/generate.py` lines 706-747。

### 第二階段：產生 graph JSON

Prompt 在 `backend/app/prompts.py` 的 `SYSTEM_GRAPH_PROMPT`。

輸入：

```text
<explanation>...</explanation>
<file_tree>...</file_tree>
<repo_owner>...</repo_owner>
<repo_name>...</repo_name>
<previous_graph>...</previous_graph>
<validation_feedback>...</validation_feedback>
```

輸出不是 Mermaid，而是受 schema 控制的 graph：

```json
{
  "groups": [],
  "nodes": [],
  "edges": []
}
```

Prompt 特別要求：

| 規則 | 意義 |
|---|---|
| 不要輸出 Mermaid | Mermaid 由程式產生 |
| path 只能用真的存在於 file tree 的 repo-relative path | 避免假路徑 |
| graph 不是完整 inventory | 只要高訊號架構圖 |
| nodes 建議 14-24 個 | 避免圖太滿 |
| failed validation 時修正 previous graph | 支援 retry |

## Graph schema 長什麼樣

FastAPI 版 schema 在 `backend/app/services/graph_service.py` lines 38-67。

TypeScript 版 schema 在 `src/features/diagram/graph.ts` lines 7-67。

核心結構：

```json
{
  "groups": [
    {
      "id": "frontend",
      "label": "Frontend",
      "description": "..."
    }
  ],
  "nodes": [
    {
      "id": "api_route",
      "label": "API Route",
      "type": "Next.js Route",
      "description": "...",
      "groupId": "frontend",
      "path": "src/app/api/generate/stream/route.ts",
      "shape": "box"
    }
  ],
  "edges": [
    {
      "from": "api_route",
      "to": "openai_service",
      "label": "calls",
      "description": "...",
      "style": "solid"
    }
  ]
}
```

限制：

| 欄位 | 限制 |
|---|---|
| groups | 最多 10 |
| nodes | 1 到 34 |
| edges | 最多 48 |
| label/type | 最多 72 字 |
| description | 最多 240 字 |
| path | 最多 512 字 |

## Graph 怎麼驗證

驗證在 `backend/app/services/graph_service.py` lines 75-140。

它會檢查：

| 檢查 | 為什麼重要 |
|---|---|
| group id 不可重複 | Mermaid subgraph 不會撞名 |
| node id 不可重複 | edge 才能正確連線 |
| node.groupId 必須存在 | 避免掛到不存在的 group |
| node.path 必須存在於 file tree | 避免 LLM 編假檔案 |
| edge.from / edge.to 必須存在 | 避免斷掉的連線 |

如果驗證失敗，後端會把錯誤回饋給 LLM，再試一次。

最大 retry 次數：

```text
MAX_GRAPH_ATTEMPTS = 3
```

這點很值得 KAI-Mind 參考：

```text
┌──────────────────┐
│ LLM output graph │
└──────────────────┘
  └─→ 後端驗證

┌────────┐
│ 後端驗證   │
└────────┘
  ├─【通過】→ compile Mermaid
  └─【失敗】→ 產生 validation feedback

┌────────────────────────┐
│ 產生 validation feedback │
└────────────────────────┘
  └─→ 把 feedback + previous graph 丟回 LLM

┌────────────────────────────────────┐
│ 把 feedback + previous graph 丟回 LLM │
└────────────────────────────────────┘
  └─→ LLM output graph
```

## Mermaid 不是 LLM 寫的，是後端編譯的

Mermaid compile 在 `backend/app/services/graph_service.py` lines 234-287。

後端會：

| 動作 | 說明 |
|---|---|
| 固定產生 `flowchart TD` | 圖方向固定 |
| groups 轉成 `subgraph` | 分區顯示 |
| nodes 依 shape 轉成 Mermaid node | box / database / circle / hexagon |
| edges 轉成 Mermaid arrow | solid 或 dashed |
| node.path 轉成 GitHub click link | 點節點可開 GitHub 檔案 |
| classDef 加顏色 | 讓不同 group 有視覺區隔 |

所以 GitDiagram 的可視化核心是：

```text
Graph JSON 是主資料
Mermaid 只是 render output
```

這和 KAI-Mind 的 `ai_system_map.json` 很像：JSON 應該是主資料，viewer 或 Mermaid 是投影結果。

## Mermaid 語法也會被驗證

Mermaid validator 在 `backend/app/services/mermaid_service.py` lines 31-81。

FastAPI 版會呼叫：

```text
bun scripts/validate_mermaid.mjs
```

然後用 Mermaid parser 檢查圖能不能被 parse。

TypeScript 版 validator 在 `src/server/generate/mermaid-validator.ts`，它多做了幾件事：

| 機制 | 用途 |
|---|---|
| server-side DOM patch | 讓 Mermaid 可以在 server parse |
| click directive 檢查 | 避免 click 語法壞掉 |
| subprocess fallback | Mermaid runtime 在 server 壞掉時還能驗證 |
| timeout | 避免 validator 卡住 |

這代表它不相信 compiler 永遠正確，compile 後還會再驗一次。

## 成功或失敗狀態怎麼存

儲存層在 `backend/app/services/diagram_state_repository.py`。

它用兩種外部服務：

| 服務 | 用途 |
|---|---|
| Cloudflare R2 | 存成功產出的 diagram artifact |
| Upstash Redis | 存 failure summary、quota usage |

成功 artifact 內容在 lines 316-353：

```json
{
  "version": 1,
  "visibility": "public",
  "username": "...",
  "repo": "...",
  "stargazerCount": 123,
  "diagram": "flowchart TD ...",
  "explanation": "...",
  "graph": {},
  "generatedAt": "...",
  "usedOwnKey": false,
  "latestSessionSummary": {},
  "lastSuccessfulAt": "..."
}
```

Private repo 的 key 不會直接用 PAT，而是用 HMAC namespace：

```text
private/v1/{hmac_pat_namespace}/{username}/{repo}.json
```

相關位置在 `diagram_state_repository.py` lines 79-127。

失敗狀態存在 Redis，TTL 是 3 天，相關位置在 lines 403-455。

Quota 也是 Redis，相關位置在 lines 21-48 和 lines 458-497。

## SSE 回傳給前端的狀態

生成流程是 streaming 的，不是等全部完成才回傳。

大致會送出這些狀態：

```text
┌─────────┐
│ started │
└─────────┘
  └─→ explanation_sent

┌──────────────────┐
│ explanation_sent │
└──────────────────┘
  └─→ explanation_chunk

┌───────────────────┐
│ explanation_chunk │
└───────────────────┘
  └─→ graph_sent

┌────────────┐
│ graph_sent │
└────────────┘
  └─→ graph

┌─────────────────┐
│ 收到 graph result │
└─────────────────┘
  ├─→ graph_validating
  └─→ diagram_compiling

┌──────────────────┐
│ graph_validating │
└──────────────────┘
  └─→ graph

┌───────────────────┐
│ diagram_compiling │
└───────────────────┘
  └─→ complete
```

如果錯誤：

```text
status: error
error_code: ...
failure_stage: ...
validation_error: ...
latest_session_audit: ...
```

這對 KAI-Mind 的 replay / viewer 很有參考價值，因為使用者不熟 AI 時，看到「現在做到哪一步」會比只看到最後結果更容易理解。

## 和 Understand-Anything 的差別

| 項目 | GitDiagram | Understand-Anything |
|---|---|---|
| 主要輸入 | GitHub file tree + README | 本地 codebase 掃描 + 多階段分析 |
| 是否深入 parse source | 比較少 | 比較多 |
| 主要產物 | 架構 diagram | knowledge graph / dashboard |
| LLM 角色 | 從 repo snapshot 推論架構 | 輔助建立 codebase knowledge graph |
| 圖資料 | `groups / nodes / edges` | `nodes / edges / layers / tour` |
| 強項 | 簡潔、漂亮、可點 GitHub path | 深入理解 codebase、可做 tour |

簡單說：

```text
GitDiagram 比較像「快速產生架構圖」
Understand-Anything 比較像「建立可探索的 codebase knowledge graph」
```

## 對 KAI-Mind Epic 1 的參考價值

KAI-Mind 可以參考 GitDiagram 的「流程設計」，但不建議直接照抄它的資料來源。

### 可以抄的部分

| 可參考設計 | 為什麼適合 KAI-Mind |
|---|---|
| JSON graph 作為主資料 | `ai_system_map.json` 本來就應該是 viewer 的 contract |
| deterministic renderer | 不要讓 LLM 直接決定最後畫面 |
| schema validation | 避免 viewer 吃到壞資料 |
| validation feedback retry | 若有 LLM enrichment，可以讓它修正 |
| clickable path | 使用者可以從圖回到 evidence file |
| generation audit / timeline | 幫不熟 AI 的使用者理解每一步 |
| compile 後再 validate | 避免畫面壞掉才被前端發現 |

### 不建議照抄的部分

| 不建議 | 原因 |
|---|---|
| 只靠 file tree + README 理解系統 | KAI-Mind 要做 release readiness，必須靠 scanner evidence |
| 讓 LLM 決定 readiness facts | 會有 hallucination 風險 |
| Mermaid 當唯一資料模型 | KAI-Mind 需要 query trace、retriever、index、config、risk evidence |
| 只做高階架構圖 | KAI-Mind 需要能看 RAG pipeline 和 readiness gap |

## 建議 KAI-Mind 採用的版本

對 Epic 1，可以設計成這樣：

```text
┌───────────────────┐
│ Read-only scanner │
└───────────────────┘
  └─→ ai_system_map.json

┌────────────────────┐
│ ai_system_map.json │
└────────────────────┘
  ├─→ Schema validation
  └─→ Evidence links

┌───────────────────┐
│ Schema validation │
└───────────────────┘
  └─→ Viewer view model

┌───────────────────┐
│ Viewer view model │
└───────────────────┘
  ├─→ Interactive AI Map
  └─→ Replay timeline

┌────────────────┐
│ Evidence links │
└────────────────┘
  ├─→ Interactive AI Map
  └─→ Replay timeline
```

如果要加入 LLM，建議放在 facts 之後：

```text
┌───────────────┐
│ scanner facts │
└───────────────┘
        ↓
┌──────────────────────────────┐
│ validated ai_system_map.json │
└──────────────────────────────┘
        ↓
┌────────────┐
│ LLM 產生白話說明 │
└────────────┘
        ↓
┌───────────────┐
│ 後端驗證不要改 facts │
└───────────────┘
        ↓
┌───────────────────────────────────────┐
│ viewer 顯示 explanation / labels / tour │
└───────────────────────────────────────┘
```

也就是：

```text
scanner 負責真相
LLM 負責白話解釋
viewer 負責互動理解
```

## 給 Timmy 的實作建議

`ai_system_map.json` 可以學 GitDiagram，分成三層：

```json
{
  "nodes": [],
  "edges": [],
  "evidence": [],
  "replay": [],
  "readiness": {}
}
```

Viewer 不要直接吃 scanner raw output，而是先轉成 view model：

```text
┌────────────────────┐
│ ai_system_map.json │
└────────────────────┘
  └─→ validate schema

┌─────────────────┐
│ validate schema │
└─────────────────┘
  └─→ normalize ids

┌───────────────┐
│ normalize ids │
└───────────────┘
  └─→ group nodes

┌─────────────┐
│ group nodes │
└─────────────┘
  └─→ attach evidence

┌─────────────────┐
│ attach evidence │
└─────────────────┘
  ├─→ render graph
  └─→ render replay
```

建議保留這些欄位：

| 欄位 | 用途 |
|---|---|
| `node.id` | 穩定連線用 |
| `node.label` | viewer 顯示名稱 |
| `node.kind` | retriever / llm / vector_store / api / config |
| `node.summary` | 白話說明 |
| `node.evidence_refs` | 點回 evidence |
| `edge.from / edge.to` | pipeline 流向 |
| `edge.reason` | 為什麼這兩個元件有關 |
| `replay.steps` | query replay 的每一步 |
| `readiness.findings` | readiness gap |

## 最重要的取捨

GitDiagram 可以當作「互動架構圖 pipeline」參考，不應該當作「RAG readiness scanner」參考。

對 KAI-Mind 來說，正確方向是：

```text
┌─────────┐
│ 不要：repo │
└─────────┘
  └─【LLM】→ 圖

┌────────────────┐
│ 要：repo scanner │
└────────────────┘
  └─【verified JSON / viewer】→ 白話互動解釋
```

這樣才符合 Local AI Health Doctor 的定位：release readiness gate，而不是單純的 codebase diagram generator。
