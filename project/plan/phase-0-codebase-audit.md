# Phase 0：從零建構專案基礎（Project Bootstrap & Core Infrastructure）

**預估時間：** 2.5–3 週  
**前置條件：** 無（這是第一步）  
**開發模式：** 兩人合作

**目的：** 從零開始建立 KAI-Mind 的完整專案骨架，包含後端 service layer、前端 skeleton、開發環境、CI/CD、協作流程。完成後，每個後續 Phase 都能在這個穩固的基礎上快速開發。

**核心原則：**

> **先 service layer，後 LangGraph。**  
> 不要一開始就把邏輯塞進 LangGraph。先寫乾淨、可測的 service function，後續再用 workflow 串起來。

---

## 🎯 Phase 0 的判斷標準

每個決定都問這四個問題：

1. 它有沒有服務 8 月前 demo？
2. 它有沒有讓產品更像 Local AI Health Doctor？
3. 它有沒有幫使用者判斷 fast / safe / compatible / trustworthy？
4. 它有沒有幫履歷展示 SWE / Backend / Applied AI 能力？

**如果答案不是，先不做。**

---

## Phase 0a：第一週 — 專案骨架 + 協作基礎

> 第一週不要急著做完整功能。先做 skeleton。

### 0a.1 GitHub Repo + 協作流程

- [ ] 建立 GitHub repo
- [ ] 設定 `main` branch protection（require PR review）
- [ ] 建立 `dev` branch 作為開發主幹
- [ ] 設定 commit message 慣例（Conventional Commits）
- [ ] 建立 issue template（feature / bug）
- [ ] 建立 GitHub Project board（Kanban）
- [ ] 建立 labels：

```text
type:feature
type:bug
type:docs
type:test
area:backend
area:frontend
area:diagnostics
area:rag
area:infra
priority:p0
priority:p1
status:blocked
```

- [ ] 建立第一批 issues（Phase 0 的每個 checklist 項目）
- [ ] 確認兩人都能 clone、push、建 PR

### 0a.2 專案結構初始化

- [ ] 建立以下目錄結構：

```text
kai-mind/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # pydantic-settings
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── router.py
│   │   ├── diagnostics/         # 診斷 service layer（核心）
│   │   │   ├── __init__.py
│   │   │   ├── environment_scanner.py
│   │   │   ├── model_fit_advisor.py
│   │   │   ├── performance_benchmark.py
│   │   │   ├── privacy_guard.py
│   │   │   └── rag_quality_inspector.py
│   │   ├── services/            # 外部服務整合
│   │   │   ├── __init__.py
│   │   │   ├── ollama.py
│   │   │   └── qdrant.py
│   │   └── models/              # Pydantic schemas
│   │       └── __init__.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   └── test_health.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── .env.example
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── docs/
```

- [ ] 建立完整的 `.gitignore`（Python + Node.js + Docker + IDE + `.env`）

### 0a.3 後端 Skeleton（FastAPI）

- [ ] 初始化 Python 專案（`pyproject.toml`）
- [ ] 安裝核心依賴：

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "httpx>=0.27.0",
    "psutil>=6.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "black>=24.0",
    "ruff>=0.5.0",
]
```

- [ ] 建立 `main.py`：
  - `GET /healthz` → `{"status": "ok", "version": "0.1.0"}`
  - CORS middleware（允許 `localhost:3000`）
  - API versioning prefix：`/api/v1`
- [ ] 建立 `config.py`（pydantic-settings）：

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "KAI-Mind"
    debug: bool = False
    ollama_base_url: str = "http://localhost:11434"
    qdrant_url: str = "http://localhost:6333"
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] 建立 `.env.example`
- [ ] 確認 `uvicorn` 啟動後 `/healthz` 回應 200
- [ ] 確認 `/docs` 能看到 FastAPI 自動生成的 API 文件

### 0a.4 前端 Skeleton（React）

- [ ] 初始化前端專案（Vite + React + TypeScript）
- [ ] 安裝 Tailwind CSS
- [ ] 建立最基本的 dashboard layout：
  - Sidebar（5 個模組的 nav links，先用 placeholder）
  - Main content area
  - Top bar（KAI-Mind logo + status indicator）
- [ ] 確認 dev server 可以啟動
- [ ] 確認前端可以呼叫後端 `/healthz`（CORS 正常）

### 0a.5 Docker Compose

- [ ] 撰寫後端 `Dockerfile`
- [ ] 撰寫前端 `Dockerfile`
- [ ] 撰寫 `docker-compose.yml`：

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./backend:/app
    depends_on:
      - qdrant

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    depends_on:
      - backend

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

- [ ] 確認 `docker compose up` 能啟動所有服務
- [ ] 確認三個服務互相可以連線

### 0a.6 Environment Scanner 最小版

> 第一週就要有一個能 demo 的最小功能，證明系統是活的。

- [ ] 在 `diagnostics/environment_scanner.py` 實作：
  - `get_os_info()` → OS 類型、版本
  - `get_cpu_info()` → CPU 型號、核心數
  - `get_ram_info()` → 總量、已使用、可用
  - `check_ollama()` → 呼叫 `http://localhost:11434/api/version`，回傳 running / not running
  - `check_qdrant()` → 呼叫 `http://localhost:6333/healthz`，回傳 running / not running
- [ ] 建立 API endpoint：`GET /api/v1/diagnostics/environment`
- [ ] 回傳 JSON 結構：

```json
{
  "os": {"type": "macOS", "version": "15.0"},
  "cpu": {"model": "Apple M1", "cores": 8},
  "ram": {"total_gb": 16, "used_gb": 10, "available_gb": 6},
  "services": {
    "ollama": {"status": "running", "version": "0.5.0"},
    "qdrant": {"status": "running"},
    "docker": {"status": "running"}
  }
}
```

- [ ] 前端顯示 Environment Scanner 結果（簡單 card，不用漂亮）

---

### 📌 第一週完成標準

- [ ] GitHub repo 建好，兩人都能建 PR
- [ ] `docker compose up` 能啟動 backend + frontend + Qdrant
- [ ] `/healthz` 回應正常
- [ ] `/api/v1/diagnostics/environment` 回傳系統資訊
- [ ] 前端能顯示 Environment Scanner 的結果
- [ ] GitHub Project board 有第一批 issues
- [ ] README 有基本啟動步驟

### ❌ 第一週不要做

- ❌ LangGraph workflow
- ❌ RAG Quality Inspector
- ❌ Cloud deploy
- ❌ PostgreSQL / pgvector
- ❌ 漂亮 UI / 動畫
- ❌ Observability / Tracing
- ❌ RAG 評估

---

## Phase 0b：第二~三週 — Service Layer + CI + 文件

### 0b.1 Ollama Service

- [ ] 建立 `services/ollama.py`：
  - `async get_version() -> dict | None` — Ollama 是否運行
  - `async list_models() -> list[dict]` — 本機模型列表
  - `async get_running_models() -> list[dict]` — 目前載入的模型
  - `async generate(prompt: str, model: str) -> dict` — 基本推論
- [ ] 所有 API 呼叫使用 `httpx.AsyncClient`
- [ ] Ollama 不可用時回傳 `None`（不 crash）
- [ ] 撰寫單元測試（mock HTTP response）

### 0b.2 Qdrant Service

- [ ] 建立 `services/qdrant.py`：
  - `async health_check() -> bool`
  - `async list_collections() -> list[str]`
  - `async get_collection_info(name: str) -> dict | None`
- [ ] Qdrant 不可用時回傳 `None`
- [ ] 撰寫單元測試

### 0b.3 系統偵測 Service

- [ ] 擴展 `diagnostics/environment_scanner.py`：
  - `get_gpu_info()` — GPU 偵測
    - macOS Apple Silicon：`sysctl` / `system_profiler`
    - Linux NVIDIA：`nvidia-smi`
    - 其他平台：回傳 `null`
  - `check_docker()` — `docker info` 是否可用
  - `get_ollama_models()` — 使用 Ollama service 取得模型列表
  - `get_loaded_model()` — 使用 Ollama service 取得目前載入模型
- [ ] 判斷模型目前是 CPU / GPU / hybrid 執行
- [ ] 撰寫單元測試

### 0b.4 Health Score 計算

- [ ] 定義 Environment Health Score 計算規則（0–100 分）：

```text
OS 偵測成功      +5
RAM ≥ 16GB       +15
RAM ≥ 32GB       +5 (bonus)
GPU 可用         +20
Docker 可用      +10
Ollama 運行中    +20
Qdrant 運行中    +10
有模型已載入     +15
```

- [ ] 分級：Healthy（≥ 80）、Warning（50–79）、Critical（< 50）
- [ ] 根據結果產生 recommendations 列表
- [ ] 更新 API endpoint 回傳 health score

### 0b.5 程式碼品質 + Linter

- [ ] 設定 Python：`black` + `ruff`
- [ ] 設定前端：`eslint` + `prettier`
- [ ] 在 `pyproject.toml` 加入工具設定
- [ ] 跑一次全專案 format
- [ ] 確認 `ruff check` 無錯誤

### 0b.6 CI — GitHub Actions

- [ ] 建立 `.github/workflows/ci.yml`：

```yaml
name: CI

on:
  push:
    branches: [main, dev]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install black ruff
      - run: black --check backend/
      - run: ruff check backend/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e "backend/[dev]"
      - run: pytest backend/tests/ -v --tb=short

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] 確認 CI push 後自動跑
- [ ] 在 README 加入 CI status badge

### 0b.7 測試

- [ ] `tests/conftest.py` — FastAPI test client fixture
- [ ] `tests/test_health.py` — `/healthz` 回應 200
- [ ] `tests/test_environment.py` — Environment Scanner API 回傳正確結構
- [ ] `tests/unit/test_ollama_service.py` — mock test
- [ ] `tests/unit/test_qdrant_service.py` — mock test
- [ ] 確認 `pytest` 全部通過
- [ ] 加入 `pytest-cov` 看 coverage

### 0b.8 文件

- [ ] 撰寫 `README.md`：
  - 專案一句話描述（中英文）
  - 技術棧列表
  - 快速啟動（Docker Compose）
  - 本機開發啟動（不用 Docker）
  - API 文件（指向 `/docs`）
  - CI badge
  - 專案結構說明
- [ ] 建立 `CONTRIBUTING.md`（開發規範、branch 流程、PR 流程、commit 慣例）
- [ ] 加入 `LICENSE`（MIT）
- [ ] 建立 `CHANGELOG.md`
- [ ] 更新 GitHub Project board：Phase 0 完成的 issues 移到 Done

---

## 🔀 分工建議

| 項目 | Timmy | 隊友 |
| --- | :---: | :---: |
| GitHub repo + 協作流程設定 | ✅ | — |
| 後端 skeleton + config | ✅ | — |
| 前端 skeleton + layout | — | ✅ |
| Docker Compose | ✅ | review |
| Environment Scanner service | ✅ | — |
| Environment Scanner 前端顯示 | — | ✅ |
| Ollama service | ✅ | — |
| Qdrant service | ✅ | — |
| CI / GitHub Actions | ✅ | — |
| 測試 | 各自負責各自的模組 | 各自負責 |
| README + CONTRIBUTING | ✅ | review |
| Health Score 計算 | ✅ | — |
| 前端整合 API 顯示 | — | ✅ |

> ⚠️ **但每個人都要會跑全系統。** 不能變成隊友不懂 backend、你不懂 frontend，最後 demo 斷掉。

---

## ❌ Phase 0 不做的事（推遲到後續 Phase）

| 項目 | 推遲到 | 原因 |
| --- | --- | --- |
| LangGraph workflow | Phase 2–3 | 先寫乾淨 service，有東西可串了再導入 |
| RAG Quality Inspector | Phase 5 | 最複雜的模組，不是第一步 |
| RAG 評估（RAGAS） | Phase 5 | 等 RAG 功能做好再評估 |
| Observability / Tracing | Phase 3+ | 等有實際 workflow 再加 |
| 雲端部署 | Phase 6 | 先專注本機開發 |
| PostgreSQL + pgvector | Phase 6+ | MVP 用 Qdrant 夠了 |
| 背景任務 Queue | Phase 3 | 等 benchmark 需要長時間才加 |
| 漂亮 UI / 動畫 | Phase 1 | 第一週先求能用，不求好看 |

---

## 📌 Phase 0 完成標準

完成 Phase 0 之後，你們應該能自信地說：

> ✅ GitHub repo 有完整的協作流程（branch protection、PR review、Project board）  
> ✅ `docker compose up` 能啟動 backend + frontend + Qdrant  
> ✅ 後端 `/healthz` 和 `/api/v1/diagnostics/environment` 回應正常  
> ✅ 前端能顯示 Environment Scanner 的基本結果  
> ✅ Ollama / Qdrant service 有 graceful fallback  
> ✅ Environment Health Score 能計算出分數  
> ✅ CI pipeline 在 GitHub 自動跑 lint + test  
> ✅ `pytest` 全部通過  
> ✅ README 有清楚的啟動步驟和專案說明  
> ✅ 每個 service function 都是獨立、可測試的（不依賴 LangGraph）  
> ✅ 兩個人都能跑全系統，不會整合失敗

### Environment Scanner Done 驗收

- [ ] 能偵測 OS / CPU / RAM / GPU
- [ ] 能偵測 Docker / Ollama / Qdrant 狀態
- [ ] 能列出 Ollama models
- [ ] API 有測試
- [ ] UI 能顯示 health status + health score
- [ ] README 有使用說明

---

## ➡️ 下一步

完成後前往 → [Phase 1：重新定位與 UI 骨架](./phase-1-rebranding-ui.md)
