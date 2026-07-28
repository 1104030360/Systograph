# Understand-Anything 後端分析報告

> 參考專案：https://github.com/Lum1104/Understand-Anything  
> 本地檢視位置：`/private/tmp/understand-anything-review/Understand-Anything`  
> 主要分析範圍：`understand-anything-plugin/skills/understand/SKILL.md`、`agents/*.md`、`skills/understand/*.mjs|*.py`、`packages/core/src/*.ts`、`packages/dashboard/*`  
> 本文件用途：用可視化方式解釋 Understand-Anything 從 input repo 掃檔案到最後產生 JSON，實際做了哪些後端事情，以及它用哪些機制確保結果盡量正確。
> 視覺化格式：依 `.cursor/rules/explain_visualize.mdc`，使用 ASCII 方框、箭頭與表格呈現，避免 Markdown renderer 對 Mermaid 區塊報 `No diagram type detected`。

## 一句話結論

Understand-Anything 的「後端」不是傳統 API server。

它是：

```text
AI coding plugin workflow
  + deterministic scanner scripts
  + LLM subagents
  + schema / merge / validation scripts
  + local Vite middleware dashboard
```

核心資料流是：

```text
input repo
  -> .understandignore filter
  -> project scan inventory
  -> per-batch structural extraction
  -> per-batch semantic graph
  -> merge / normalize / recover
  -> architecture layers
  -> guided tour
  -> review / validation
  -> .understand-anything/knowledge-graph.json
  -> local dashboard fetch + validate + render
```

對 Systograph 的最大啟發是：

```text
release-readiness scanner 不應該直接讓 LLM 產生最終 report。

比較安全的形狀應該是：

deterministic evidence scanner
  -> normalized evidence graph / map
  -> strict schema validation
  -> report JSON
  -> viewer 只讀 JSON，不重新推論事實
```

## 全域可視化總覽

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ /understand <repo>                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────┐
│ Phase 0 Pre-flight   │  resolve root / worktree redirect / build core
└──────────────────────┘
        ↓
┌──────────────────────┐
│ .understandignore    │  user-controlled scan boundary
└──────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 1 project-scanner                                                     │
│ git ls-files → filter → language/category → framework → importMap           │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ intermediate/scan-result.json                                                │
│ files[] + fileCategory + languages + frameworks + importMap                 │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 2 file-analyzer batches                                                │
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                  │
│   │ batch-0     │     │ batch-1     │ ... │ batch-N     │                  │
│   │ analyzer    │     │ analyzer    │     │ analyzer    │                  │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                  │
│          ↓                   ↓                   ↓                         │
│   batch-0.json        batch-1.json        batch-N.json                     │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ merge-batch-graphs.py                                                       │
│ normalize IDs / dedupe / drop dangling / recover imports from importMap     │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ assembled-graph.json         │
└──────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 3-6 review + layers + tour + validation                               │
│ assemble-reviewer → architecture-analyzer → tour-builder → validator        │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Phase 7 save                                                                │
│ knowledge-graph.json + fingerprints.json + meta.json                        │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ /understand-dashboard                                                       │
│ local Vite middleware → token check → frontend validateGraph → render        │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 產物與中繼檔地圖

```text
<input repo>/
  .understand-anything/
    .understandignore                 # 使用者可調整的掃描排除規則
    config.json                       # autoUpdate / outputLanguage 設定
    knowledge-graph.json              # 最終主輸出，dashboard 主要讀這個
    fingerprints.json                 # full rebuild 後產生，供 incremental update 比對
    meta.json                         # lastAnalyzedAt / gitCommitHash / version / analyzedFiles
    intermediate/                     # 分析期間使用，Phase 7 會清掉
      scan-result.json                # repo inventory + language/framework/importMap
      batch-0.json                    # 某批檔案的 nodes / edges
      batch-1.json
      batch-existing.json             # incremental update 時保留的舊 graph fragment
      assembled-graph.json            # 合併 batch 後，還沒包 project/layers/tour 前後都會被覆寫
      assemble-review.json            # assemble reviewer 的修正摘要
      layers.json                     # architecture analyzer 輸出
      tour.json                       # tour builder 輸出
      review.json                     # inline validator 或 graph-reviewer 輸出
      fingerprint-input.json          # build-fingerprints.mjs input
    tmp/                              # 臨時 scripts / script results，Phase 7 會清掉
      ua-project-scan.js
      ua-scan-results.json
      ua-file-analyzer-input-<batch>.json
      ua-file-extract-results-<batch>.json
      ua-inline-validate.cjs
      ua-arch-input.json
      ua-arch-results.json
      ua-tour-input.json
      ua-tour-results.json
```

重點：

```text
scan-result.json 是「掃描到哪些檔案」與「哪些 import 是 project-internal」的 deterministic source of truth。
batch-*.json 是 LLM + deterministic extraction 混合產出的 graph fragment。
assembled-graph.json 是 merge script 合併與修正後的 graph。
knowledge-graph.json 是最終 dashboard contract。
```

## Phase 0：Pre-flight 做了什麼

入口是：

```text
understand-anything-plugin/skills/understand/SKILL.md
```

`/understand` 先處理執行環境與決策，不立刻掃檔案。

### 0.1 解析 input repo

它從 `$ARGUMENTS` 找第一個不是 flag 的 token。

```text
/understand /path/to/repo --full --language zh-TW
            ^^^^^^^^^^^^^
            input repo path
```

處理規則：

| 情況 | 行為 |
|---|---|
| 有 path argument | relative path 會用 current working directory resolve 成 absolute path |
| path 不存在 | 報錯並停止 |
| path 不是 directory | 報錯並停止 |
| 沒有 path argument | 使用當前 working directory |

### 0.2 Git worktree redirect

它會檢查 target repo 是否在 git worktree 裡：

```text
git rev-parse --git-dir
git rev-parse --git-common-dir
```

如果 `--git-dir` 和 `--git-common-dir` 指向不同位置，代表可能是 worktree。

此時它預設把輸出 redirect 到 main repo root，原因是 Claude Code 這類工具的 worktree 可能是暫時的，`.understand-anything/` 寫在 worktree 裡可能會消失。

可用：

```text
UNDERSTAND_NO_WORKTREE_REDIRECT=1
```

關閉 redirect。

### 0.3 確認 plugin/core build 可用

後面會執行 Node scripts，且 scripts 會 import：

```text
@understand-anything/core
```

所以它會尋找 plugin root，候選包含：

```text
CLAUDE_PLUGIN_ROOT
~/.understand-anything-plugin
~/.agents/skills/understand 的 symlink 真實位置
~/.copilot/skills/understand 的 symlink 真實位置
~/.codex/understand-anything/understand-anything-plugin
~/.opencode/understand-anything/understand-anything-plugin
~/understand-anything/understand-anything-plugin
```

如果 `packages/core/dist/index.js` 不存在，它會：

```text
pnpm install
pnpm --filter @understand-anything/core build
```

如果 `pnpm` 不存在，會要求安裝 Node.js >= 22 和 pnpm >= 10。

### 0.4 建立工作資料夾與設定

它建立：

```text
.understand-anything/intermediate
.understand-anything/tmp
```

也會讀取/寫入：

```text
.understand-anything/config.json
```

支援：

| flag | 寫入設定 |
|---|---|
| `--auto-update` | `{"autoUpdate": true}` |
| `--no-auto-update` | `{"autoUpdate": false}` |
| `--language <lang>` | `{"outputLanguage": "<normalized lang>"}` |

語言設定會影響後續 LLM 生成的文字欄位，例如 summary、tags、layer description、tour description。

### 0.5 判斷 full / incremental / review-only

它會看：

```text
.understand-anything/knowledge-graph.json
.understand-anything/meta.json
git rev-parse HEAD
```

決策表：

| 條件 | 行為 |
|---|---|
| 有 `--full` | full analysis |
| 沒有 existing graph 或 meta | full analysis |
| 有 `--review` 且 commit 未變 | review-only，跳到 Phase 6 review |
| graph 存在且 commit 未變 | 詢問使用者是否 rebuild / review / do nothing |
| graph 存在且 commit 已變 | incremental update |

Incremental update 會用：

```text
git diff <lastCommitHash>..HEAD --name-only
```

取得 changed files，只重跑部分分析。

### 0.6 蒐集 subagent context

為了讓 project-scanner、file-analyzer、architecture-analyzer、tour-builder 更準，主流程會先讀：

```text
README.md / README.rst / readme.md 的前 3000 chars
package.json / pyproject.toml / Cargo.toml / go.mod / pom.xml
top-level dir tree, maxdepth 2, 最多 100 files
常見 entry point
```

entry point 偵測包含：

```text
src/index.ts
src/main.ts
src/App.tsx
index.js
main.py
manage.py
app.py
wsgi.py
asgi.py
run.py
__main__.py
main.go
cmd/*/main.go
src/main.rs
src/lib.rs
src/main/java/**/Application.java
Program.cs
config.ru
index.php
```

## Phase 0.5：`.understandignore` 做了什麼

掃描前它要求使用者檢查 `.understandignore`。

它優先使用：

```text
<repo>/.understand-anything/.understandignore
```

也支援：

```text
<repo>/.understandignore
```

如果不存在，它會產生 starter file，內容包含：

```text
內建排除建議
.gitignore 中額外 pattern 的註解版
偵測到的 tests/docs/examples/scripts/migrations 等 directory 建議
test file pattern 建議
```

重要點：

```text
它會等待使用者確認後才繼續掃描。
```

這是因為 scanner 可能讀很多 repo 檔案。對 release-readiness 工具來說，這個 checkpoint 很值得參考：掃描範圍應該清楚、可控、可重現。

## Phase 1：Project Scanner 如何從 input repo 掃檔案

Phase 1 dispatch：

```text
agents/project-scanner.md
```

它不是叫 LLM 直接猜檔案，而是要求 subagent 寫並執行 deterministic discovery script。

```text
┌────────────────┐
│ PROJECT_ROOT   │
└───────┬────────┘
        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Discovery Script                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. git ls-files preferred                                                    │
│    └─ fallback: recursive listing                                            │
│                                                                             │
│ 2. exclusion filter                                                          │
│    ├─ dependency dirs / build output / binary assets                         │
│    └─ optional .understandignore unified filter                              │
│                                                                             │
│ 3. deterministic metadata                                                    │
│    ├─ language detection                                                     │
│    ├─ fileCategory detection                                                 │
│    ├─ line counting                                                          │
│    ├─ framework detection                                                    │
│    └─ internal import resolution                                             │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ tmp/ua-scan-results.json     │  raw script result
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ LLM adds description only    │  no file path guessing
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────────────────┐
│ intermediate/scan-result.json             │
│ source of truth for files + importMap      │
└──────────────────────────────────────────┘
```

### 1.1 File discovery

優先：

```text
git ls-files
```

原因：git tracked files 比自行 recursive listing 更穩定，也比較不會掃到 build output 或 local garbage。

如果不是 git repo，才 fallback recursive listing。

### 1.2 預設排除規則

預設排除：

| 類別 | examples |
|---|---|
| dependency dirs | `node_modules/`、`.git/`、`vendor/`、`venv/`、`.venv/`、`__pycache__/` |
| build output | `dist/`、`build/`、`out/`、`coverage/`、`.next/`、`.cache/`、`.turbo/`、`target/`、`obj/` |
| lock files | `*.lock`、`package-lock.json`、`yarn.lock`、`pnpm-lock.yaml` |
| binary/assets | png/jpg/gif/svg/ico/font/mp3/mp4/pdf/zip/tar/gz |
| generated/minified | `*.min.js`、`*.min.css`、`*.map`、`*.generated.*` |
| IDE/editor config | `.idea/`、`.vscode/` |
| misc non-source | `LICENSE`、`.gitignore`、`.editorconfig`、`.prettierrc`、`.eslintrc*`、`*.log` |

特別注意：

```text
bin/ 沒有預設排除，因為 Node.js / Ruby 專案可能把 CLI launcher 放在 bin/。
```

### 1.3 明確保留 non-code files

它刻意保留很多非程式碼檔，因為理解系統架構不能只看 `.ts` / `.py`：

| 保留類型 | examples |
|---|---|
| docs | `*.md`、`*.rst`、`*.txt` |
| config | `*.yaml`、`*.yml`、`*.json`、`*.toml`、`*.xml`、`*.cfg`、`*.ini`、`.env`、`.env.example` |
| infra | `Dockerfile`、`docker-compose.*`、`*.tf`、`Makefile`、`Jenkinsfile`、`Procfile`、`Vagrantfile` |
| CI/CD | `.github/workflows/*`、`.gitlab-ci.yml`、`.circleci/*` |
| data/schema | `*.sql`、`*.graphql`、`*.gql`、`*.proto`、`*.prisma`、`*.schema.json` |
| markup | `*.html`、`*.css`、`*.scss`、`*.sass`、`*.less` |
| scripts | `*.sh`、`*.bash`、`*.ps1`、`*.bat` |
| Kubernetes | `*.k8s.yaml`、`k8s/`、`kubernetes/` |

`.env` 會出現在 file list 裡，但 prompt 明確要求 downstream agent 不得把 `.env` variable values 寫進 summary 或 output。這對 Systograph 很重要：可以知道「有 env config」，但不應暴露 secret value。

### 1.4 `.understandignore` unified filter

如果 `.understandignore` 存在，scanner 不只是把使用者 pattern 疊在預設排除後面。

它會用 `@understand-anything/core` 的 `createIgnoreFilter` 把：

```text
hardcoded defaults + user patterns
```

合在同一個 gitignore-compatible matcher 裡。

這樣使用者可以用 `!` negation override 預設排除，例如強制 include `dist/` 裡某些檔。

### 1.5 Language detection

scanner 把副檔名映射成 language id：

```text
.ts/.tsx     -> typescript
.js/.jsx     -> javascript
.py          -> python
.go          -> go
.rs          -> rust
.java        -> java
.rb          -> ruby
.cpp/.h      -> cpp
.c           -> c
.cs          -> csharp
.swift       -> swift
.kt          -> kotlin
.php         -> php
.vue         -> vue
.svelte      -> svelte
.sh/.bash    -> shell
.ps1         -> powershell
.bat/.cmd    -> batch
.md/.rst     -> markdown
.yaml/.yml   -> yaml
.json        -> json
.jsonc       -> jsonc
.toml        -> toml
.sql         -> sql
.graphql     -> graphql
.proto       -> protobuf
.tf/.tfvars  -> terraform
.html        -> html
.css/.scss   -> css
.xml         -> xml
.cfg/.ini/.env -> config
Dockerfile   -> dockerfile
Makefile     -> makefile
Jenkinsfile  -> jenkinsfile
```

未知副檔名會用 lowercased extension；完全沒有副檔名則是 `unknown`。它不輸出 `null`，因為 downstream 依賴 language 是 string。

### 1.6 File category detection

每個檔案會有：

```json
{"path": "src/index.ts", "language": "typescript", "sizeLines": 150, "fileCategory": "code"}
```

`fileCategory` 有：

```text
code
config
docs
infra
data
script
markup
```

這個欄位會影響 file-analyzer 如何建立 node type。

### 1.7 Line counting

它會計算每個檔案 line count：

```text
< 500 files：全部 count
>= 500 files：仍全部 count，但 batch wc -l，避免 spawn 太多 process
```

### 1.8 Framework detection

scanner 會讀 manifest/config 來確認 framework，不只靠檔名猜。

| 檔案 | 會讀什麼 |
|---|---|
| `package.json` | name、description、dependencies、devDependencies |
| `tsconfig.json` | confirms TypeScript |
| `Cargo.toml` | Rust project / package name / dependencies |
| `go.mod` | Go module / dependencies |
| `requirements.txt` | Python packages |
| `pyproject.toml` | project deps / Poetry deps / pytest / Django hints |
| `setup.py` / `setup.cfg` / `Pipfile` | Python package hints |
| `Gemfile` | Ruby frameworks |
| `pom.xml` / `build.gradle` | JVM frameworks |

它會辨識：

```text
React, Vue, Svelte, Angular, Express, Fastify, Koa, Next, Nuxt, Vite,
Vitest, Jest, Mocha, Tailwind, Prisma, TypeORM, Sequelize, Mongoose,
Redux, Zustand, MobX, Django, DRF, FastAPI, Flask, SQLAlchemy, Alembic,
Celery, Pydantic, Uvicorn, Gunicorn, AIOHTTP, Tornado, Starlette,
pytest, Rails, Sinatra, Grape, RSpec, Sidekiq, Gin, Echo, Fiber, Chi,
Gorm, Actix, Axum, Rocket, Diesel, Tokio, Serde, Spring, Quarkus,
Micronaut, Hibernate, Ktor
```

也會從 infra files 偵測：

```text
Docker
Docker Compose
Terraform
GitHub Actions
GitLab CI
Jenkins
```

### 1.9 Complexity estimation

以 total file count 粗略分：

| total files | estimatedComplexity |
|---|---|
| 1-30 | `small` |
| 31-150 | `moderate` |
| 151-500 | `large` |
| >500 | `very-large` |

這是 project-level complexity，不是 GraphNode 的 `simple/moderate/complex`。

### 1.10 Project name

優先順序：

```text
package.json name
Cargo.toml [package].name
go.mod module path 最後一段
pyproject.toml [project].name 或 [tool.poetry].name
directory name
```

### 1.11 Import resolution

這是 Phase 1 對正確性最重要的部分。

scanner 會對每個 `fileCategory === "code"` 的檔案解析 project-internal imports。非 code files 在 `importMap` 裡仍有 key，但 value 是 `[]`。

ImportMap 形狀：

```json
{
  "src/index.ts": ["src/utils.ts", "src/config.ts"],
  "src/utils.ts": [],
  "README.md": [],
  "Dockerfile": []
}
```

支援語言：

| 語言 | import resolution |
|---|---|
| TS/JS | relative import / require，外加 tsconfig `paths` / `baseUrl` alias |
| Python | relative import 與 absolute dotted import；會探測 `.py` 與 `__init__.py` |
| Go | `go.mod` module path 內部 import |
| Rust | `use crate::`、`use super::`、`mod x` |
| Java | `import com.example.Foo` 對應 `**/com/example/Foo.java` |
| Kotlin | 同 Java，對應 `.kt` |
| Ruby | `require_relative`，也會探測 `lib/`、`app/`、bare path |
| PHP | 讀 `composer.json` PSR-4 autoload map |
| C/C++ | `#include "foo.h"` 與 `<foo.h>`，探測 relative、include/、src/ |

Import resolution 的原則：

```text
只保留 project-internal、能對上 discovered file list 的路徑。
external package imports 直接丟掉。
dynamic / unresolved imports 也丟掉。
```

這代表後面 graph 的 `imports` edge 有 deterministic evidence，而不是 LLM 猜的。

### 1.12 scan-result.json 最終 schema

Project scanner 最終寫：

```text
.understand-anything/intermediate/scan-result.json
```

形狀：

```json
{
  "name": "project-name",
  "description": "Brief description from README or package.json",
  "languages": ["markdown", "typescript", "yaml"],
  "frameworks": ["React", "Vite", "Docker"],
  "files": [
    {"path": "src/index.ts", "language": "typescript", "sizeLines": 150, "fileCategory": "code"},
    {"path": "README.md", "language": "markdown", "sizeLines": 45, "fileCategory": "docs"}
  ],
  "totalFiles": 42,
  "filteredByIgnore": 0,
  "estimatedComplexity": "moderate",
  "importMap": {
    "src/index.ts": ["src/utils.ts"]
  }
}
```

LLM 在這個 phase 只負責 `description`。其他 structural data 來自 script。

Project-scanner 的 critical constraints：

```text
不得 invent file paths。
每個 files[].path 必須真的來自 script discovery。
totalFiles 必須等於 files.length。
files 必須按 path deterministic sort。
每個 file 必須有 fileCategory。
structural data 要信任 script，不要重跑或重數。
```

## Phase 2：File Analyzer 如何把檔案變成 nodes / edges

Phase 2 會把 Phase 1 的 `files` 切 batch：

```text
每批 20-30 files
目標約 25 files / batch
最多 5 個 file-analyzer subagents 並行
```

對 non-code files 它會盡量 group related files：

```text
Dockerfile + docker-compose.yml + .dockerignore
SQL migrations 按檔名排序
CI/CD config files
docs/*.md
```

目的：讓 analyzer 看得到跨檔關係，例如 docker-compose depends_on Dockerfile。

```text
┌──────────────────────────────┐
│ scan-result.json             │
├──────────────────────────────┤
│ files[] + fileCategory       │
│ importMap                    │
└───────────────┬──────────────┘
                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ Batch Builder                                                               │
│ 20-30 files per batch, related non-code files grouped together              │
└───────────────┬─────────────────────────────────────────────────────────────┘
                ↓
┌──────────────────────────────┐
│ ua-file-analyzer-input-0     │
├──────────────────────────────┤
│ batchFiles                   │
│ batchImportData              │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ extract-structure.mjs        │  deterministic tree-sitter + parser pass
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ ua-file-extract-results-0    │  functions / classes / services / endpoints
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ file-analyzer semantic pass  │  summaries / tags / semantic edges
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ intermediate/batch-0.json    │
└──────────────────────────────┘
```

### 2.1 batchImportData

主流程會從 `$IMPORT_MAP` 建：

```json
{
  "src/index.ts": ["src/utils.ts", "src/config.ts"],
  "src/utils.ts": []
}
```

file-analyzer 被明確要求：

```text
不要自己重新 resolve imports。
對每個 batchImportData[filePath] entry 1:1 emit imports edge。
即使 target 在其他 batch，也要 emit，因為 scanner 已經驗證 target exists。
```

這是避免 LLM 在 import edge 上漏掉或亂猜的重要設計。

### 2.2 Structural Extraction：extract-structure.mjs

file-analyzer 不是先讀 source 然後自由發揮。

它必須先執行：

```text
skills/understand/extract-structure.mjs
```

input：

```json
{
  "projectRoot": "<repo>",
  "batchFiles": [
    {"path": "src/index.ts", "language": "typescript", "sizeLines": 100, "fileCategory": "code"}
  ],
  "batchImportData": {
    "src/index.ts": ["src/utils.ts"]
  }
}
```

output：

```json
{
  "scriptCompleted": true,
  "filesAnalyzed": 5,
  "filesSkipped": [],
  "results": [
    {
      "path": "src/index.ts",
      "language": "typescript",
      "fileCategory": "code",
      "totalLines": 150,
      "nonEmptyLines": 120,
      "functions": [],
      "classes": [],
      "exports": [],
      "callGraph": [],
      "metrics": {}
    }
  ]
}
```

這支 script 使用：

```text
TreeSitterPlugin
PluginRegistry
builtinLanguageConfigs
registerAllParsers
```

支援：

```text
code files：TypeScript, JavaScript, Python, Go, Rust, Java, Ruby, PHP, C/C++, C#
non-code parsers：Dockerfile, env, GraphQL, JSON, Makefile, Markdown, Protobuf, shell, SQL, Terraform, TOML, YAML
```

如果某個檔案讀取失敗，會放進 `filesSkipped`，不會讓整批直接崩潰。

如果 script exit 0 但 output file 不存在或空檔，file-analyzer 必須視為 hard failure，不能繼續靠 LLM 自己補。

### 2.3 extract-structure.mjs 抽出的 deterministic structure

對 code files：

| 欄位 | 來源 |
|---|---|
| `functions` | tree-sitter / extractor |
| `classes` | tree-sitter / extractor |
| `exports` | tree-sitter / extractor |
| `callGraph` | registry.extractCallGraph |
| `metrics.importCount` | 優先 batchImportData count；fallback parser internal relative imports |
| `metrics.exportCount` | exports length |
| `metrics.functionCount` | functions length |
| `metrics.classCount` | classes length |

對 non-code files：

| 欄位 | 常見來源 | 後續用途 |
|---|---|---|
| `sections` | Markdown/YAML/JSON/TOML | context，通常不建 node |
| `definitions` | `.env` / GraphQL / Protobuf | schema definitions；env definitions 不輸出值 |
| `services` | Dockerfile / docker-compose | service nodes |
| `endpoints` | OpenAPI / Swagger / route files | endpoint nodes |
| `steps` | GitHub Actions / GitLab CI | step / pipeline context |
| `resources` | Terraform / CloudFormation / K8s | resource nodes |

### 2.4 LLM semantic pass 做什麼

file-analyzer 讀 extraction results 後，才生成：

```text
GraphNode[]
GraphEdge[]
```

LLM 主要負責：

```text
summary
tags
complexity
languageNotes
semantic/non-code edges
function/class significance decision
```

但它的行動被很多約束限制。

### 2.5 每個檔案都要有 file-level node

每個 batch 裡的 file 都必須產生一個 node。

`fileCategory` 到 default node type：

| fileCategory | default node type | override |
|---|---|---|
| `code` | `file` | 一般 source file |
| `config` | `config` | config file |
| `docs` | `document` | docs file |
| `infra` | `service` | Dockerfile / docker-compose / K8s |
| `infra` | `pipeline` | GitHub Actions / GitLab CI / Jenkins / CircleCI |
| `infra` | `resource` | Terraform / CloudFormation / Vagrant |
| `data` | `table` | SQL table / migration |
| `data` | `schema` | GraphQL / Protobuf / Prisma |
| `data` | `endpoint` | OpenAPI / Swagger |
| `script` | `file` | shell scripts as code-like files |
| `markup` | `file` | HTML/CSS as code-like files |

### 2.6 Function / class node significance filter

不是每個 function 都變成 node，避免 graph 爆炸。

只產生：

```text
function/method >= 10 lines
class >= 2 methods
class >= 20 lines
exported function/class
```

跳過：

```text
trivial one-liners
type aliases
simple re-exports
auto-generated boilerplate
```

### 2.7 Node ID conventions

file-analyzer 必須用固定 prefix：

| Node type | ID |
|---|---|
| file | `file:<relative-path>` |
| function | `function:<relative-path>:<function-name>` |
| class | `class:<relative-path>:<class-name>` |
| config | `config:<relative-path>` |
| document | `document:<relative-path>` |
| service | `service:<relative-path>` |
| table | `table:<relative-path>:<table-name>` |
| endpoint | `endpoint:<relative-path>:<endpoint-name>` |
| pipeline | `pipeline:<relative-path>` |
| schema | `schema:<relative-path>` |
| resource | `resource:<relative-path>` |

file-analyzer 不得產生 `module:` / `concept:`。這些是高階分析保留類型。

### 2.8 Edge creation

Code edge types：

| Edge | 何時建立 | weight |
|---|---|---|
| `contains` | file contains emitted function/class | 1.0 |
| `imports` | batchImportData 的每個 internal import，1:1 | 0.7 |
| `calls` | confidence 足夠的跨檔 function call | 0.8 |
| `inherits` | class extends project class | 0.9 |
| `implements` | class implements project interface | 0.9 |
| `exports` | file exports emitted function/class | 0.8 |
| `depends_on` | runtime dependency broader than imports | 0.6 |
| `tested_by` | production file 被 test file exercise | 0.5 |

Non-code edge types：

| Edge | 何時建立 | weight |
|---|---|---|
| `configures` | config affects code/module | 0.6 |
| `documents` | doc describes code/component | 0.5 |
| `deploys` | infra builds/deploys code | 0.7 |
| `migrates` | SQL migration changes table/schema | 0.7 |
| `triggers` | CI/CD triggers pipeline/deployment/tests | 0.6 |
| `defines_schema` | GraphQL/Proto/OpenAPI schema used by code | 0.8 |
| `serves` | service/deployment exposes endpoint | 0.7 |
| `provisions` | Terraform creates infra | 0.7 |
| `routes` | routing config routes to service | 0.6 |
| `related` | topical relation without stronger structural type | 0.5 |
| `depends_on` | non-code file depends on another file | 0.6 |

禁止：

```text
edge source == target
edge to non-existing node
invented filePath
edge type outside allowed table
```

### 2.9 batch JSON

每個 file-analyzer 寫：

```text
.understand-anything/intermediate/batch-<batchIndex>.json
```

形狀：

```json
{
  "nodes": [
    {
      "id": "file:src/index.ts",
      "type": "file",
      "name": "index.ts",
      "filePath": "src/index.ts",
      "summary": "Main entry point...",
      "tags": ["entry-point", "barrel", "exports"],
      "complexity": "simple"
    }
  ],
  "edges": [
    {
      "source": "file:src/index.ts",
      "target": "file:src/utils.ts",
      "type": "imports",
      "direction": "forward",
      "weight": 0.7
    }
  ]
}
```

## Phase 2 merge：merge-batch-graphs.py 如何合併與修正

所有 batch 完成後執行：

```text
skills/understand/merge-batch-graphs.py <PROJECT_ROOT>
```

輸入：

```text
.understand-anything/intermediate/batch-*.json
.understand-anything/intermediate/scan-result.json
```

輸出：

```text
.understand-anything/intermediate/assembled-graph.json
stderr report
```

```text
┌──────────────────────────────┐
│ batch-*.json                 │
└───────────────┬──────────────┘
                ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ merge-batch-graphs.py                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. load valid batches only                                                   │
│ 2. normalize node IDs                                                        │
│ 3. normalize complexity                                                      │
│ 4. rewrite edge refs after ID mapping                                        │
│ 5. deduplicate nodes by ID, keep last                                        │
│ 6. canonicalize tested_by                                                    │
│ 7. deduplicate edges, keep higher weight                                     │
│ 8. drop dangling edges                                                       │
│ 9. recover missing imports from scan-result#importMap                        │
└───────────────┬─────────────────────────────────────────────────────────────┘
                ↓
┌──────────────────────────────┐        ┌─────────────────────────────────────┐
│ assembled-graph.json         │        │ stderr report                        │
│ nodes + edges                │        │ fixed / could not fix / recovered    │
└──────────────────────────────┘        └─────────────────────────────────────┘
```

### Merge Step 1：load batch files

它只接受有：

```text
nodes: array
edges: array
```

的 batch。

JSON parse error 或 missing arrays 會 warning 並 skip。

如果沒有任何有效 batch，merge script 失敗。

### Merge Step 2：normalize node IDs

它修正常見 LLM output 問題：

| 問題 | 修正 |
|---|---|
| `file:file:src/foo.ts` | `file:src/foo.ts` |
| `my-project:file:src/foo.ts` | `file:src/foo.ts` |
| `func:src/foo.ts:bar` | `function:src/foo.ts:bar` |
| bare path `src/foo.ts` | 依 node.type 補成 `file:src/foo.ts` |
| function/class bare id | 用 `filePath` + `name` 補成 `function:<filePath>:<name>` |

如果 function/class 缺 `filePath`，它會用：

```text
function:__nofilepath__:<name>
```

讓 collision 可以被後面 review 看見，而不是靜默合併錯誤 node。

### Merge Step 3：normalize complexity

合法值：

```text
simple
moderate
complex
```

aliases：

| input | output |
|---|---|
| `low`, `easy` | `simple` |
| `medium`, `intermediate` | `moderate` |
| `high`, `hard`, `difficult` | `complex` |
| number <= 3 | `simple` |
| number <= 6 | `moderate` |
| number > 6 | `complex` |
| unknown / null | `moderate`，但列入 Could not fix |

### Merge Step 4：rewrite edge references

如果 node ID 被修正，edge 的 `source` / `target` 也會套用同一份 id mapping。

例如：

```text
node id: func:src/a.ts:run -> function:src/a.ts:run
edge source: func:src/a.ts:run -> function:src/a.ts:run
```

### Merge Step 5：dedupe nodes

以 node `id` 去重：

```text
keep last occurrence
```

這代表後面的 batch 或 existing fragment 可能覆蓋前面的同 ID node。

### Merge Step 5b：tested_by linker

這是專門處理 test coverage edge 的 deterministic 修正器。

問題背景：

```text
LLM 常在分析 test file 時看到 test imports production，
因此會 emit test -> production 的 tested_by。
但 schema 語意想要 production -> test。
```

它做兩 pass：

#### Pass 1：修正 LLM 已經 emit 的 tested_by

| source/target 類型 | 行為 |
|---|---|
| production -> test | 保留 |
| test -> production | flip 成 production -> test，description 加 direction corrected |
| test -> test | drop |
| production -> production | drop |
| endpoint missing / non-file endpoint | drop |

Test file 判斷支援：

```text
JS/TS: *.test.ts, *.spec.ts, *.test.tsx, ...
Go: *_test.go
Python: test_*.py, *_test.py
Java/Kotlin/C#/C/C++ 常見 Test / Tests / IT / test_ pattern
```

#### Pass 2：用 path convention 補 missing tested_by

如果某個 test file 沒有 paired edge，它會用路徑規則找 production candidate。

Examples：

```text
src/foo.test.ts        -> src/foo.ts / src/foo.tsx / src/foo.js ...
src/__tests__/foo.ts   -> src/foo.ts ...
tests/foo/test_bar.py  -> src/foo/bar.py / foo/bar.py
pkg/foo_test.go        -> pkg/foo.go
src/test/java/FooTest.java -> src/main/java/Foo.java
My.App.Tests/BarTests.cs   -> My.App/Bar.cs
```

最後：

```text
所有 tested_by edge 都是 production -> test。
production node 會被加上 "tested" tag。
```

### Merge Step 6：dedupe edges and drop dangling

edge 去重 key：

```text
(source, target, type, direction)
```

如果重複，保留 `weight` 較高的。

它也 normalize direction：

```text
both / mutual -> bidirectional
invalid -> forward
```

如果 edge source 或 target 不存在於 merged node set：

```text
drop edge
記錄到 Could not fix
```

### Merge Step 7：recover imports from importMap

這是 Understand-Anything 很關鍵的 correctness 補強。

merge script 會讀：

```text
intermediate/scan-result.json#importMap
```

然後檢查每個 deterministic import 是否已存在 graph 裡。

如果 batch analyzer 漏掉 import edge，就補上：

```json
{
  "source": "file:src/a.py",
  "target": "file:src/b.py",
  "type": "imports",
  "direction": "forward",
  "weight": 0.7,
  "recoveredFromImportMap": true
}
```

它會避免：

```text
self-import
source file node 不存在
target file node 不存在
重複 edge
```

這代表 `imports` edge 的最終 completeness 不完全依賴 LLM。

### Merge report

merge script 在 stderr 產生 report：

```text
Input: X nodes, Y edges

Fixed:
  N × id pattern corrections
  N × complexity alias mappings
  N × edge references rewritten
  N × duplicate node IDs removed
  N × tested_by edges flipped/dropped

Tested-by linker:
  N × tested_by edges produced
  N × production nodes tagged "tested"

Could not fix:
  unknown node types
  unknown complexity values
  dangling edges dropped

Imports edge recovery:
  Recovered N imports edges from importMap
  Skipped N source/target without file node

Output: X nodes, Y edges
```

Phase 3 會把這份 report 傳給 assemble-reviewer。

## Phase 3：Assemble Reviewer 做什麼

Phase 3 dispatch：

```text
agents/assemble-reviewer.md
```

它的定位不是重新分析 source code，而是 review `merge-batch-graphs.py` 的結果。

輸入：

```text
assembled-graph.json
batch-*.json
merge script stderr report
IMPORT_MAP
```

它做：

| Step | 目的 |
|---|---|
| sanity-check Fixed section | 看修正量是否合理，例如 >30% node ID 被修可能代表 upstream system pattern |
| investigate Could not fix | 缺 id、unknown node type、unknown complexity、dropped dangling edge |
| recover nodes/edges where justified | 只有能從 batch / scan result 判斷時才補 |
| cross-batch imports gap check | 用 IMPORT_MAP 確認 imports edge 是否存在，缺就補 |
| write assemble-review.json | 記錄 nodesRecovered、edgesRestored、crossBatchEdgesAdded 等 |

注意：

```text
這是 LLM reviewer，但它被要求只基於 assembled graph、batch files、IMPORT_MAP。
不得 speculative add edges。
```

## Phase 4：Architecture Analyzer 如何產生 layers

Phase 4 dispatch：

```text
agents/architecture-analyzer.md
```

輸入：

```text
all file-level nodes
imports edges
all file-level edges, including configures/documents/deploys/triggers...
detected frameworks
top-level dir tree
language-specific guidance files
framework-specific guidance files
optional locale guidance
```

```text
┌──────────────────────────────┐
│ assembled graph              │
│ nodes + edges                │
└───────┬───────────┬──────────┘
        │           │
        ↓           ↓
┌──────────────┐  ┌──────────────────┐
│ file-level   │  │ imports + all     │
│ nodes        │  │ file-level edges  │
└──────┬───────┘  └────────┬─────────┘
       └──────────┬────────┘
                  ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ architecture structural script                                               │
│ directory groups / node type groups / fan-in-out / dependency matrices       │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────┐
│ LLM architecture semantic assignment │
└──────────────────┬──────────────────┘
                   ↓
┌──────────────────────────────┐
│ layers.json                  │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ main workflow normalizes     │
│ layer ids + nodeIds          │
└──────────────────────────────┘
```

### 4.1 deterministic script computes architecture signals

architecture-analyzer 先寫/執行 script，計算：

| Signal | 說明 |
|---|---|
| directory grouping | 以 common prefix 後的 top-level directory grouping |
| node type grouping | file/config/document/service/pipeline/table/schema/resource/endpoint 分布 |
| import adjacency | 每個 file fan-in / fan-out |
| cross-category dependency | config -> file、service -> file、schema -> file 等 |
| inter-group import frequency | routes -> services: 12 |
| intra-group density | 群組內聚程度 |
| directory pattern matching | routes/api/controllers -> api；services/core -> service；models/db -> data |
| deployment topology | Dockerfile / Compose / K8s / Terraform / CI |
| data pipeline | schema / migration / data model / API handler |
| doc coverage | 哪些 groups 有 docs |
| dependency direction | 哪個 group depends on 哪個 group |

### 4.2 LLM produces 3-10 layers

LLM 根據 script output 與 prompt guidance，輸出 logical architecture layers。

目標：

```text
3-10 layers
每個 file-level node exactly one layer
包含 non-code files
layer name / description 可依 language directive localize
```

### 4.3 layers normalization

主流程讀 `layers.json` 後會 normalize：

| 問題 | 修正 |
|---|---|
| `{ "layers": [...] }` envelope | unwrap |
| legacy `nodes` field | rename to `nodeIds` |
| `nodes` 是 object array | extract `id` |
| missing `id` | synthesize `layer:<kebab-case-name>` |
| raw file path in `nodeIds` | convert to `file:<relative-path>` |
| dangling node id | drop |

最終每個 layer：

```json
{
  "id": "layer:core",
  "name": "Core",
  "description": "Core application logic",
  "nodeIds": ["file:src/index.ts", "config:tsconfig.json"]
}
```

## Phase 5：Tour Builder 如何產生 guided tour

Phase 5 dispatch：

```text
agents/tour-builder.md
```

輸入：

```text
README first 3000 chars
detected entry point
nodes, file-level only
layers without nodeIds
all edges
language directive
```

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ file-level   │   │ all edges    │   │ layers       │
│ nodes        │   │              │   │              │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       └──────────────────┼──────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ tour topology script                                                        │
│ entry candidates / fan-in-out / BFS / clusters / non-code inventory          │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────┐
│ LLM pedagogical tour design          │
└──────────────────┬──────────────────┘
                   ↓
┌──────────────────────────────┐
│ tour.json                    │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ normalize order + nodeIds    │
└──────────────────────────────┘
```

### 5.1 deterministic topology script computes tour signals

它計算：

| Signal | 說明 |
|---|---|
| fan-in ranking | 被很多 node 指向，代表重要 dependency |
| fan-out ranking | 指向很多 node，代表 broad scope / overview |
| entry point candidates | README、main/index/app/server/manage 等 |
| BFS traversal | 從 top code entry point 追 imports/calls |
| non-code inventory | docs / infra / data / config |
| tightly coupled clusters | 互相連很多 edge 的 2-5 nodes |
| layer list | layer count / names / descriptions |
| nodeSummaryIndex | node id -> name/type/summary |

### 5.2 LLM produces 5-15 tour steps

tour-builder 被要求：

```text
README 通常 Step 1
code entry point Step 2
BFS depth 1/2/3 對應後續 steps
non-code stops 插入適當位置
clusters 可合成一個 step
描述 WHAT / WHY / 與前一步關係
```

### 5.3 tour normalization

主流程 normalize：

| 問題 | 修正 |
|---|---|
| `{ "steps": [...] }` envelope | unwrap |
| `nodesToInspect` | rename to `nodeIds` |
| `whyItMatters` | rename to `description` |
| raw file path in nodeIds | convert to `file:<relative-path>` |
| dangling node id | drop |
| order out of order | sort by `order` |

最終 step：

```json
{
  "order": 1,
  "title": "Project Overview",
  "description": "Start with the README...",
  "nodeIds": ["document:README.md"]
}
```

`languageLesson` 是 optional。

## Phase 6：組成最終 KnowledgeGraph 並 review / validate

Phase 6 把前面結果組成 root object：

```json
{
  "version": "1.0.0",
  "project": {
    "name": "<projectName>",
    "languages": ["typescript"],
    "frameworks": ["React"],
    "description": "<projectDescription>",
    "analyzedAt": "<ISO timestamp>",
    "gitCommitHash": "<commit hash>"
  },
  "nodes": [],
  "edges": [],
  "layers": [],
  "tour": []
}
```

### 6.1 pre-review checks

寫 final assembled graph 前，它先檢查：

```text
layers 是 array
layers 每個元素有 id/name/description/nodeIds
tour 是 array
tour 每個元素有 order/title/description/nodeIds
tour[*].languageLesson 可選
每個 layers[*].nodeIds 存在於 node set
每個 tour[*].nodeIds 存在於 node set
```

如果失敗，會自動 normalize / rewrite。若最後仍失敗：

```text
graph 可存，但 dashboard auto-launch skipped。
```

### 6.2 default path：inline deterministic validation

沒有 `--review` 時，會寫並執行：

```text
.understand-anything/tmp/ua-inline-validate.cjs
```

檢查：

| 檢查 | 類型 |
|---|---|
| `nodes` / `edges` 是否 array | issue |
| node 必須有 id/type/name/summary/tags | issue |
| duplicate node id | issue |
| edge source/target 必須存在 | issue |
| layers/tour array shape | issue/warning |
| layer nodeIds 必須存在 | issue |
| file-level nodes 必須出現在 layer | issue |
| tour nodeIds 必須存在 | issue |
| orphan nodes | warning |
| stats | totalNodes/totalEdges/totalLayers/tourSteps/nodeTypes/edgeTypes |

輸出：

```text
.understand-anything/intermediate/review.json
```

形狀：

```json
{
  "issues": [],
  "warnings": [],
  "stats": {
    "totalNodes": 42,
    "totalEdges": 87,
    "totalLayers": 5,
    "tourSteps": 8,
    "nodeTypes": {},
    "edgeTypes": {}
  }
}
```

### 6.3 `--review` path：graph-reviewer

如果有 `--review`，Phase 6 dispatch：

```text
agents/graph-reviewer.md
```

graph-reviewer 也不是純手看 JSON，而是必須先寫/執行 validation script。

檢查包含：

| Check | Severity |
|---|---|
| node required fields / types / id prefix | critical |
| edge required fields / types / weight range | critical |
| edge/layer/tour referential integrity | critical |
| at least one node/edge/layer/tour | critical；domain graph 對 layer/tour 放寬 |
| every file-level node exactly one layer | critical |
| duplicate node IDs | critical |
| tour order sequential / count 5-15 | warning |
| generic summaries | warning |
| self-referencing edges | warning |
| orphan nodes | warning |
| non-code nodes missing expected relation | warning |
| node type / ID prefix mismatch | warning |

輸出：

```json
{
  "approved": true,
  "issues": [],
  "warnings": [],
  "stats": {
    "totalNodes": 42,
    "totalEdges": 87,
    "totalLayers": 5,
    "tourSteps": 8,
    "nodeTypes": {},
    "edgeTypes": {}
  }
}
```

規則：

```text
issues 非空 => rejected。
warnings 不阻止 approved。
```

### 6.4 issues 後自動修正

Phase 6 讀 `review.json` 後，如果 `issues` 非空：

```text
drop dangling edges
fill missing required fields with sensible defaults
remove invalid node types
re-run validation once
```

如果 critical issues 仍存在：

```text
save graph with warnings
skip dashboard auto-launch
```

## Phase 7：Save 做了什麼

Phase 7 寫最終檔案。

```text
┌──────────────────────────────────┐
│ validated / normalized graph     │
└───────────────┬──────────────────┘
                ↓
┌──────────────────────────────────┐
│ write knowledge-graph.json       │
└───────────────┬──────────────────┘
                ↓
┌──────────────────────────────────┐
│ build-fingerprints.mjs           │
│ input: fingerprint-input.json     │
└───────────────┬──────────────────┘
                ↓
┌──────────────────────────────────┐
│ write fingerprints.json           │
└───────────────┬──────────────────┘
                ↓
┌──────────────────────────────────┐
│ write meta.json                   │
└───────────────┬──────────────────┘
                ↓
┌──────────────────────────────────┐
│ clean intermediate + tmp          │
└───────────────┬──────────────────┘
                ↓
        ┌───────────────────┐
        │ validation passed?│
        └───────┬───────────┘
                │
        ┌───────┴────────┐
        ↓                ↓
┌──────────────┐  ┌──────────────────────────┐
│ launch       │  │ skip dashboard auto-launch│
│ dashboard    │  │ but report warnings       │
└──────────────┘  └──────────────────────────┘
```

### 7.1 Write final graph

輸出：

```text
.understand-anything/knowledge-graph.json
```

這是 dashboard 的主 contract。

### 7.2 Build fingerprints baseline

接著它寫：

```text
.understand-anything/intermediate/fingerprint-input.json
```

包含：

```json
{
  "projectRoot": "<repo>",
  "sourceFilePaths": ["src/index.ts", "README.md"],
  "gitCommitHash": "<current commit>"
}
```

然後執行：

```text
skills/understand/build-fingerprints.mjs
```

它用和 `extract-structure.mjs` 一樣的：

```text
TreeSitterPlugin
PluginRegistry
registerAllParsers
```

產生：

```text
.understand-anything/fingerprints.json
```

如果 fingerprint script 失敗，或 stdout 沒有包含：

```text
Fingerprints baseline:
```

Phase 7 會 abort，不寫 `meta.json`。

原因：如果 meta 寫了新 commit hash 但 fingerprints 沒有 baseline，後續 auto-update 會以為所有檔案都是 structural change，導致每次都 full update。

### 7.3 Write meta

只有 fingerprint 成功後才寫：

```text
.understand-anything/meta.json
```

形狀：

```json
{
  "lastAnalyzedAt": "<ISO timestamp>",
  "gitCommitHash": "<commit hash>",
  "version": "1.0.0",
  "analyzedFiles": 42
}
```

### 7.4 Clean up

最後清掉：

```text
.understand-anything/intermediate
.understand-anything/tmp
```

### 7.5 Final summary

回報：

```text
project name / description
files analyzed / total files by fileCategory
nodes by type
edges by type
layers names
tour steps count
warnings
output file path
```

如果 validation 通過，才自動啟動 dashboard。

## 最終 KnowledgeGraph schema

核心定義在：

```text
packages/core/src/types.ts
packages/core/src/schema.ts
```

Root：

```ts
interface KnowledgeGraph {
  version: string;
  kind?: "codebase" | "knowledge";
  project: ProjectMeta;
  nodes: GraphNode[];
  edges: GraphEdge[];
  layers: Layer[];
  tour: TourStep[];
}
```

### ProjectMeta

```ts
interface ProjectMeta {
  name: string;
  languages: string[];
  frameworks: string[];
  description: string;
  analyzedAt: string;
  gitCommitHash: string;
}
```

### GraphNode

```ts
interface GraphNode {
  id: string;
  type: NodeType;
  name: string;
  filePath?: string;
  lineRange?: [number, number];
  summary: string;
  tags: string[];
  complexity: "simple" | "moderate" | "complex";
  languageNotes?: string;
  domainMeta?: DomainMeta;
  knowledgeMeta?: KnowledgeMeta;
}
```

Node types 共 21 類：

| 類別 | types |
|---|---|
| code | `file`, `function`, `class`, `module`, `concept` |
| non-code | `config`, `document`, `service`, `table`, `endpoint`, `pipeline`, `schema`, `resource` |
| domain | `domain`, `flow`, `step` |
| knowledge | `article`, `entity`, `topic`, `claim`, `source` |

### GraphEdge

```ts
interface GraphEdge {
  source: string;
  target: string;
  type: EdgeType;
  direction: "forward" | "backward" | "bidirectional";
  description?: string;
  weight: number;
}
```

Edge types 共 35 類：

| 類別 | types |
|---|---|
| structural | `imports`, `exports`, `contains`, `inherits`, `implements` |
| behavioral | `calls`, `subscribes`, `publishes`, `middleware` |
| data flow | `reads_from`, `writes_to`, `transforms`, `validates` |
| dependencies | `depends_on`, `tested_by`, `configures` |
| semantic | `related`, `similar_to` |
| infrastructure/schema | `deploys`, `serves`, `provisions`, `triggers`, `migrates`, `documents`, `routes`, `defines_schema` |
| domain | `contains_flow`, `flow_step`, `cross_domain` |
| knowledge | `cites`, `contradicts`, `builds_on`, `exemplifies`, `categorized_under`, `authored_by` |

### Layer

```ts
interface Layer {
  id: string;
  name: string;
  description: string;
  nodeIds: string[];
}
```

### TourStep

```ts
interface TourStep {
  order: number;
  title: string;
  description: string;
  nodeIds: string[];
  languageLesson?: string;
}
```

## Schema validation 與 auto-fix

核心函式：

```text
packages/core/src/schema.ts
validateGraph()
sanitizeGraph()
normalizeGraph()
autoFixGraph()
```

```text
┌──────────────┐
│ raw JSON     │
└──────┬───────┘
       ↓
┌─────────────────────┐
│ is object?          │
└──────┬──────────────┘
       ├─ no  → 【fatal】invalid input
       ↓ yes
┌─────────────────────┐
│ sanitizeGraph       │  null cleanup + lowercase enum-like fields
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ normalizeGraph      │  aliases: func→function, import→imports...
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ autoFixGraph        │  defaults + weight coercion + clamps
└──────┬──────────────┘
       ↓
┌─────────────────────┐
│ schema validation   │
├─────────────────────┤
│ project metadata    │
│ nodes               │
│ edges + references  │
│ layers              │
│ tour                │
└──────┬──────────────┘
       ↓
┌────────────────────────────────────┐
│ success: normalized graph + issues │
│ fatal: no project or no valid nodes│
└────────────────────────────────────┘
```

### sanitizeGraph

做：

```text
top-level null tour/layers -> []
optional node fields null -> delete
node.type / node.complexity lowercase
edge.type / edge.direction lowercase
edge.description null -> delete
tour.languageLesson null -> delete
```

### normalizeGraph aliases

Node aliases：

```text
func/fn/method -> function
interface/struct -> class
mod/pkg/package -> module
container/deployment/pod -> service
doc/readme/docs -> document
job/ci -> pipeline
route/api/query/mutation -> endpoint
setting/env/configuration -> config
infra/infrastructure/terraform -> resource
migration/database/db/view -> table
proto/protobuf/definition/typedef -> schema
business_domain -> domain
business_flow/business_process -> flow
task/business_step -> step
note/page/wiki_page -> article
person/actor/organization -> entity
tag/category/theme -> topic
assertion/decision/thesis -> claim
reference/raw/paper -> source
```

Edge aliases：

```text
extends -> inherits
invokes/invoke -> calls
uses/requires -> depends_on
relates_to/related_to -> related
similar -> similar_to
import -> imports
export -> exports
contain -> contains
publish -> publishes
subscribe -> subscribes
describes/documented_by -> documents
creates -> provisions
exposes/listens -> serves
deploys_to -> deploys
migrates_to -> migrates
routes_to -> routes
triggers_on/fires -> triggers
defines -> defines_schema
has_flow -> contains_flow
next_step -> flow_step
interacts_with -> cross_domain
references/cites_source -> cites
conflicts_with/disagrees_with -> contradicts
refines/elaborates -> builds_on
illustrates/instance_of/example_of -> exemplifies
belongs_to/tagged_with -> categorized_under
written_by/created_by -> authored_by
```

明確不做：

```text
implemented_by 不 alias 成 implements
```

原因是方向相反，不能偷修。

### autoFixGraph

Node auto-fix：

| 問題 | 修正 |
|---|---|
| missing type | default `file` |
| missing complexity | default `moderate` |
| complexity alias | map to simple/moderate/complex |
| missing tags | default `[]` |
| missing summary | default to name |

Edge auto-fix：

| 問題 | 修正 |
|---|---|
| missing type | default `depends_on` |
| missing direction | default `forward` |
| direction alias | map |
| missing weight | default `0.5` |
| string weight | parse float if possible |
| invalid numeric weight | default/clamp |
| weight <0 or >1 | clamp to 0..1 |

Validation 後：

```text
invalid nodes are dropped。
invalid edges are dropped。
dangling source/target edges are dropped。
invalid layers/tour steps are dropped。
layer/tour dangling nodeIds are filtered。
```

這表示 dashboard 可以載入「被修到可顯示」的 graph，同時保留 `issues` 讓 UI 顯示 warning banner。

## Dashboard 後端：Vite middleware 如何讀 JSON

Dashboard 不是獨立 Express/FastAPI server。

它是 Vite dev server 加 middleware：

```text
packages/dashboard/vite.config.ts
```

### 只綁 localhost

```text
server.host = "127.0.0.1"
server.port = 5173
```

不綁 `0.0.0.0`，避免同 Wi-Fi / LAN 其他裝置讀到 local graph 或 source preview。

### 一次性 token

server 啟動時產生：

```text
UNDERSTAND_ACCESS_TOKEN or random 16-byte hex
```

Dashboard open URL：

```text
http://127.0.0.1:5173/?token=<ACCESS_TOKEN>
```

受保護 endpoints：

```text
/knowledge-graph.json
/domain-graph.json
/diff-overlay.json
/meta.json
/config.json
/file-content.json
```

這些 endpoint 都要求：

```text
?token=<ACCESS_TOKEN>
```

否則 403。

### graph file lookup

會找：

```text
GRAPH_DIR/.understand-anything/<fileName>
process.cwd()/.understand-anything/<fileName>
process.cwd()/../../../.understand-anything/<fileName>
```

支援 dashboard 在 plugin package 內跑，也能找到 target repo 的 `.understand-anything`。

### graph JSON path sanitization

送 graph JSON 給 browser 前，它會 sanitize node.filePath：

| node.filePath 情況 | 行為 |
|---|---|
| absolute 且在 projectRoot 內 | 改成 relative path |
| absolute 但不在 projectRoot | 只保留 basename |
| already relative | 原樣保留 |

目的：

```text
避免把 /Users/alice/company-secret-project/... 這種完整 local path 暴露到 browser payload。
```

### `/file-content.json` source preview 安全限制

`/file-content.json?path=<path>&token=<token>` 會讀 source file 給 CodeViewer，但限制很多：

| 檢查 | 行為 |
|---|---|
| missing path | 400 |
| path 包 NUL | 400 |
| absolute path | reject |
| `..` path traversal | reject |
| graph 不存在 | 404 |
| resolved path 不在 projectRoot | reject |
| path 不在 knowledge graph 的 node.filePath set | 404 |
| file 不存在 | 404 |
| 不是 file | reject |
| > 1MB | 413 |
| buffer 含 NUL，疑似 binary | 415 |

這個設計非常適合 Systograph viewer 參考：

```text
viewer 可以 preview evidence source，
但只能 preview report graph 中已列為 evidence 的 file，
不能任意讀 filesystem。
```

## Dashboard frontend 如何載入與再驗證

入口：

```text
packages/dashboard/src/App.tsx
```

載入流程：

```text
┌──────────────────────────────┐
│ /?token=...                  │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ resolveInitialToken          │
│ store token in sessionStorage│
│ remove token from URL        │
└───────────────┬──────────────┘
                ↓
        ┌───────┼───────────────┬────────────────┬─────────────────┐
        ↓       ↓               ↓                ↓                 ↓
┌───────────┐ ┌───────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│ meta.json │ │ config    │ │ knowledge     │ │ diff overlay │ │ domain graph │
│           │ │ .json     │ │ graph.json    │ │ optional     │ │ optional     │
└───────────┘ └───────────┘ └───────┬───────┘ └──────────────┘ └──────┬───────┘
                                    ↓                                  ↓
                            ┌───────────────┐                  ┌──────────────┐
                            │ validateGraph │                  │ validateGraph│
                            │ in browser    │                  │ if present   │
                            └───────┬───────┘                  └──────────────┘
                                    ↓
                    ┌───────────────┼────────────────┐
                    ↓               ↓                ↓
              ┌──────────┐   ┌──────────────┐  ┌──────────────┐
              │ setGraph │   │ WarningBanner│  │ loadError    │
              │ success  │   │ issues       │  │ fatal        │
              └──────────┘   └──────────────┘  └──────────────┘
```

重點：

```text
Dashboard 不直接信任 knowledge-graph.json。
它還會在 frontend 再跑 core validateGraph()。
```

`validateGraph()` 成功時才：

```text
setGraph(result.data)
```

如果 fatal：

```text
顯示 loadError，不渲染壞 graph。
```

如果只有 auto-corrected / dropped issues：

```text
graph 仍可顯示，但 WarningBanner 會提示可請 agent 修 knowledge-graph.json。
```

## Incremental update 與 fingerprints

除了 full analysis，Understand-Anything 還有 auto-update flow：

```text
hooks/auto-update-prompt.md
```

這不是一般使用者主流程，但和「結果正確」很相關。

### Fingerprint store

Core 定義在：

```text
packages/core/src/fingerprint.ts
```

每個 file fingerprint 包含：

```text
contentHash SHA-256
functions: name, params, returnType, exported, lineCount
classes: name, methods, properties, exported, lineCount
imports: source, specifiers
exports
totalLines
hasStructuralAnalysis
```

### Change classification

比較 old/new fingerprint：

| 結果 | 條件 |
|---|---|
| `NONE` | contentHash identical |
| `COSMETIC` | content changed but function/class/import/export structural signatures same |
| `STRUCTURAL` | new/removed functions/classes、signature changed、imports changed、exports changed、large line count change |

如果沒有 structural analysis：

```text
conservative: STRUCTURAL
```

也就是不能證明安全時就重分析。

### Auto-update 行為

Auto-update 會：

```text
只對 structural changed files re-run file-analyzer。
cosmetic-only changes 不花 LLM tokens。
new/deleted files 視為 structural。
fingerprint script fail 時 conservative fallback。
```

它也要求 fingerprints 更新時：

```text
LOAD existing fingerprints
PATCH changed entries only
SAVE full dict
```

避免只寫新 batch 導致其他檔 fingerprint 消失。

## 它如何確保結果是正確的

Understand-Anything 不能「保證所有 semantic summary 都 100% 正確」，但它用了多層機制把最關鍵的結構事實交給 deterministic code，並讓 LLM output 被 schema / merge / reviewer 約束。

### 正確性防線總覽

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 正確性防線                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ 1. User chooses repo          │  scan boundary is explicit
│    + .understandignore        │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 2. git ls-files discovery     │  deterministic file inventory
│    + file exists checks       │
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 3. language/category/framework│  deterministic metadata
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 4. importMap resolution       │  internal imports evidence
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 5. extract-structure.mjs      │  tree-sitter + non-code parsers
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 6. constrained LLM generation │  semantic text, bounded by evidence
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 7. merge + normalize          │  IDs, complexity, edges, tested_by
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 8. importMap recovery         │ 補漏 imports edge
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 9. reviewer + validators      │  dangling refs, schema, completeness
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 10. dashboard validateGraph   │  render only valid graph
└───────────────┬──────────────┘
                ↓
┌──────────────────────────────┐
│ 11. regression tests          │  schema / extractor / merge / fingerprint
└──────────────────────────────┘
```

### 1. 掃描檔案不是 LLM 猜的

`project-scanner` 被要求先寫 script，使用：

```text
git ls-files
fallback recursive listing
deterministic exclusions
.understandignore filter
```

並且：

```text
每個 path 必須實際存在。
不得 invent path。
totalFiles 必須等於 files.length。
files sorted by path。
```

這確保「掃到哪些檔案」是可重現的。

### 2. importMap 是 deterministic source of truth

Import resolution 在 Phase 1 完成，且 external/unresolved imports 被丟掉。

後面 file-analyzer 被要求：

```text
imports edge count == sum(batchImportData[file].length)
```

即使 LLM 漏掉，merge script 還會從 `scan-result.json#importMap` 補。

這是最強的 correctness design 之一。

### 3. structural extraction 先於 LLM semantic analysis

`extract-structure.mjs` 用 Tree-sitter / parser registry 抽：

```text
functions
classes
exports
callGraph
sections
definitions
services
endpoints
steps
resources
metrics
```

LLM 不需要從 raw source 重新猜這些結構。

### 4. LLM 的輸出有強約束

file-analyzer prompt 有明確規則：

```text
每個 batch file 必須產生 node。
node id prefix 固定。
edge type 固定。
imports edge 必須依 batchImportData 1:1。
不要創造不存在的 filePath。
不要產生 edge to nonexistent node。
function/class node 受 significance filter 限制。
summary/tags/complexity 必填。
```

這降低 LLM 自由發揮空間。

### 5. merge script 修常見 LLM 格式錯誤

`merge-batch-graphs.py` 可修：

```text
double prefix
project-name prefix
func -> function
bare path missing prefix
complexity aliases
direction aliases
edge refs after ID rewrite
duplicate nodes
duplicate edges
tested_by direction
missing imports edges
```

無法修的會出現在 report，交給 reviewer。

### 6. dangling edges 被 drop

merge script 和 schema validator 都會檢查：

```text
edge.source exists
edge.target exists
```

不存在就 drop。這避免 dashboard render 時引用不存在 node。

### 7. layer / tour 也檢查 dangling references

Phase 4 / Phase 5 normalization 會把：

```text
raw file path -> file:<path>
dangling nodeIds -> drop
```

Phase 6 再檢查：

```text
layers[*].nodeIds exists
tour[*].nodeIds exists
```

### 8. schema.ts 有 runtime validator

`validateGraph()` 不是 TypeScript compile-time type 而已，它會 runtime parse JSON：

```text
Zod schemas
auto-fix defaults
drop invalid nodes/edges/layers/tour steps
fatal if project invalid or no valid nodes
```

Dashboard 也用同一個 validator。

### 9. graph-reviewer 可做更嚴格 QA

`--review` 時 graph-reviewer 會跑更完整檢查：

```text
required fields
valid node/edge types
id prefix
referential integrity
layer coverage
duplicate IDs
tour order
orphan nodes
non-code expected edges
summary quality
```

它以 `issues` 決定 approved/rejected。

### 10. fingerprints 確保 incremental update 不亂省略

`fingerprints.json` 讓 auto-update 可以判斷：

```text
NONE
COSMETIC
STRUCTURAL
```

不能做 structural analysis 時採保守策略：

```text
STRUCTURAL
```

這降低 incremental mode 因為省 token 而漏掉 graph 更新的風險。

### 11. tests 覆蓋關鍵正確性邏輯

repo 裡有測試覆蓋：

```text
packages/core/src/__tests__/schema.test.ts
packages/core/src/__tests__/fingerprint.test.ts
packages/core/src/__tests__/ignore-filter.test.ts
packages/core/src/__tests__/parsers.test.ts
packages/core/src/__tests__/plugin-registry.test.ts
packages/core/src/__tests__/search.test.ts
src/__tests__/extract-structure.test.mjs
src/__tests__/merge-recover-imports.test.mjs
src/__tests__/worktree-redirect.test.mjs
skills/understand/test_merge_batch_graphs.py
packages/core/src/plugins/extractors/__tests__/*.test.ts
```

具體 regression examples：

| 測試 | 保護什麼 |
|---|---|
| `merge-recover-imports.test.mjs` | batch 漏 imports edge 時，merge 從 importMap 補；不重複；不產生 dangling/self import |
| `extract-structure.test.mjs` | language pass-through、importCount fallback、line count 與 `wc -l` semantics |
| `schema.test.ts` | invalid graph reject/drop/autofix、aliases、weight clamp、dangling references、null handling |
| `fingerprint.test.ts` | function/class/import/export fingerprint 與 change classification |
| extractor tests | Python/Rust/Go/Java/Ruby/PHP/C++/C# 等 structural extraction |

## 它不能完全確保的地方

這些是重要限制，Systograph 若借鏡必須補強。

### 1. Summary / tags 仍是 LLM judgment

`summary`、`tags`、`languageNotes`、部分 semantic edges 仍由 LLM 產生。

它能確保：

```text
格式合法
引用 node 存在
某些 edge 有 deterministic evidence
```

但不能完全保證：

```text
summary 沒有誤解
tags 一定最準
related / configures / documents / deploys edge 一定完整
```

### 2. Non-code semantic edges 可能不完整

例如：

```text
README documents which modules
Dockerfile deploys which entry point
CI workflow triggers which test files
Terraform provisions what service
```

這些有些靠 LLM 判斷。graph-reviewer 會 warning，但不一定能補齊。

### 3. Layer / tour 是導覽品質，不是 hard evidence

layers 和 tour 有 normalization / validation，但它們本質上是 interpretation。

它確保：

```text
nodeIds 存在
shape 合法
file-level nodes 有 layer coverage（review path 更嚴）
```

但不保證：

```text
layer naming 一定最佳
tour 教學順序一定最佳
```

### 4. Partial result 策略會保存不完整 graph

Error handling 明確說：

```text
partial graph is better than no graph
ALWAYS save partial results
```

這對 UX 好，但對 release-readiness gate 可能危險。

Systograph 如果用在 CI/CD gate，應該把 partial result 區分成：

```text
scan_status: complete | partial | failed
blocking_errors[]
warnings[]
```

不能只輸出漂亮 JSON。

### 5. Scanner 會列出 `.env`

prompt 要求不得輸出 `.env` values，但如果 source preview 允許 `.env` node path，dashboard 的 `/file-content.json` 可能讀出 `.env` 內容。

Understand-Anything 的 file-content endpoint 只限制「必須是 graph 裡的 filePath」，但沒有針對 `.env` 做 redaction。

對 Systograph 來說，這是需要補強的點：

```text
secret-like files 可以列為 evidence path，
但 preview/report/log/snapshot 不應顯示 raw values。
```

## 對 Systograph 的設計建議

Systograph 是 AI Agent / RAG Release Readiness Gate，不是一般 codebase graph viewer。

所以可以借鏡流程，但不要照搬 schema。

### 建議保留的設計

```text
1. JSON-first contract
   scanner 產生 ai_system_map.json，viewer 只讀 JSON。

2. deterministic-first extraction
   RAG components / endpoints / env / network exposure / vector store hints
   先由 rule-based scanner 產生 evidence。

3. import/evidence source of truth
   重要 facts 必須有 evidence file path / line / detector id。

4. strict schema validation
   report 給 viewer 前先 normalize + validate。

5. local dashboard hardening
   127.0.0.1、one-time token、path traversal guard、file size limit。

6. partial result explicitness
   可以輸出 partial report，但要明確標記 partial 與 blocking reasons。

7. guided tour
   對 RAG 系統 map，可帶使用者從 query entry -> retriever -> vector store -> prompt -> LLM -> response/citation。
```

### Systograph 不應照搬的地方

```text
1. 不要用 file/function/class 作為主 domain model。
   Systograph 主體應是 RAG slots/components/endpoints/evidence/risk_hints。

2. 不要讓 LLM 創造 readiness facts。
   release readiness 結論必須能追 evidence。

3. 不要把 viewer 當 scanner。
   viewer 不應重新掃 filesystem 或自行推論 missing components。

4. 不要把 secret-like file raw content 送到 UI。
   evidence 可以存在，但 values 要 redact。

5. 不要把 partial graph 當 pass。
   CI/CD gate 應把 scanner failures 當 P1/P0 depending scope。
```

## Systograph 可參考的 ai_system_map.json 形狀

不是 Understand-Anything 的原 schema，而是借它的 pipeline pattern：

```json
{
  "schema_version": "ai-system-map/v1",
  "project": {
    "root_name": "example-rag-app",
    "analyzed_at": "2026-05-23T00:00:00.000Z",
    "git_commit": "abc123",
    "scan_status": "complete"
  },
  "scanner": {
    "version": "0.1.0",
    "mode": "read-only",
    "files_scanned": 42,
    "files_skipped": [],
    "warnings": []
  },
  "components_by_slot": {
    "query_entry": [],
    "retriever": [],
    "vector_store": [],
    "embedding_model": [],
    "prompt_builder": [],
    "llm_client": [],
    "response_composer": [],
    "citation": [],
    "eval_or_tests": [],
    "deployment": []
  },
  "endpoints": [],
  "flows": [],
  "evidence": [
    {
      "id": "evidence:requirements:langchain",
      "file_path": "requirements.txt",
      "line_range": [3, 3],
      "detector": "python_requirements_package",
      "snippet_redacted": "langchain==..."
    }
  ],
  "risk_hints": [
    {
      "id": "risk:network:bind-all",
      "severity": "warning",
      "title": "Potential 0.0.0.0 binding",
      "evidence_ids": ["evidence:server:host"],
      "confidence": "medium",
      "uncertainty": "Config may be overridden by environment variables."
    }
  ],
  "recommended_next_checks": [],
  "guided_tour": []
}
```

Systograph 的 correctness rule 應更嚴：

```text
任何 component / endpoint / risk_hint 都必須連到 evidence_ids。
任何 secret-like snippet 都必須 redacted。
任何 network exposure finding 都要說明 uncertainty。
JSON schema 破壞相容性要 migration note。
```

## 最終判斷

Understand-Anything 從 input repo 到 JSON 的後端流程可以濃縮成：

```text
repo path
  -> deterministic inventory + importMap
  -> deterministic structural extraction
  -> constrained LLM graph fragment generation
  -> deterministic merge / normalization / recovery
  -> LLM-assisted architecture/tour
  -> deterministic validation / optional LLM review
  -> fingerprints + metadata
  -> protected local dashboard fetch
  -> frontend validation before render
```

它用多層方式確保結果盡量正確：

```text
file discovery 可重現
importMap 有 deterministic evidence
tree-sitter/parsers 先抽 structure
LLM 只在受限範圍補 semantic meaning
merge script 修常見錯誤並補 imports
schema validator auto-fix/drop/fatal
reviewer 做 completeness / referential integrity / quality checks
dashboard 再 validateGraph
tests 覆蓋 schema、merge recovery、extractor、fingerprint 等核心路徑
```

但它不是 release gate 等級的完整 correctness guarantee。

對 Systograph 來說，最重要的採用原則是：

```text
JSON report 裡的每個 readiness conclusion 都必須 evidence-based。
LLM 可以幫忙摘要與導覽，但不能成為唯一事實來源。
viewer 只能呈現與 drill-down，不應重新掃描或創造 facts。
secret / filesystem / network exposure 要比 Understand-Anything 更嚴格處理。
```
