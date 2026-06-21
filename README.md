# KAI-Mind / Local AI Health Doctor

KAI-Mind 是一個 AI Agent / RAG 系統的 Release Readiness Gate。它協助團隊在 demo、交付、部署或進入 CI/CD 前，檢查一套 local AI 系統是否安全、可用、可信，並產出可追蹤的檢查報告。

這個專案不是 AI chatbot、RAG builder，也不是完整 observability 平台。它的定位是掃描一套已存在的 AI Agent / RAG 系統，建立 AI System Map，執行 readiness checks，最後輸出清楚的判斷：

- `READY`
- `RISKY`
- `NOT READY`

## 產品方向

KAI-Mind 應該先以跨平台核心為主。Epic 1 目前優先支援 GUI / local web UI，但 scanner core 必須獨立，CLI、Web API、launcher 與 CI 都不可重複實作 core scanner logic。

```text
Core Engine
    |
    +-- Local Web API / GUI
    +-- CLI
    +-- Windows launcher
    +-- macOS launcher
    +-- CI / GitHub Actions
```

這樣可以避免做成只能在 Windows 開啟的 `.exe`，並讓核心 scanner 可以同時支援 Windows、macOS、Linux、本機開發與 CI。

## MVP 模組

目前 roadmap 以 Parent / Epic issues 管理：

- [Epic 0：專案基礎](https://github.com/1104030360/Local-AI-Health-Doctor/issues/1)
- [Epic 1：System Map Builder](https://github.com/1104030360/Local-AI-Health-Doctor/issues/2)
- [Epic 2：Runtime Readiness](https://github.com/1104030360/Local-AI-Health-Doctor/issues/3)
- [Epic 3：Privacy & Exposure Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/4)
- [Epic 4：Agent Tool Risk Guard](https://github.com/1104030360/Local-AI-Health-Doctor/issues/5)
- [Epic 5：RAG Knowledge Trust](https://github.com/1104030360/Local-AI-Health-Doctor/issues/6)
- [Epic 6：Release Report & CI Gate](https://github.com/1104030360/Local-AI-Health-Doctor/issues/7)
- [Epic 7：Distribution & Integrations](https://github.com/1104030360/Local-AI-Health-Doctor/issues/8)

建議從 Epic 1 開始開發。其他 Epic 先保留為 roadmap 層級的 Parent Issue，等 System Map Builder 能產出第一版可用的 `ai_system_map.json` 後，再往下一個模組推進。

## 重要文件

- [Epic 1 設計文件](docs/design/epic1.md)
- [Epic 1 backend design](docs/work/Timmy/design/epic1-backend-design.md)
- [Epic 1 scan pipeline research](docs/work/Timmy/design/epic1-scan-pipeline-research.md)
- [Task 1：Python backend foundation](docs/work/Timmy/schedule/plan/finish/01-setup-python-backend-foundation.md)

## 建議的第一階段開發流程

1. 選定 Epic 1：System Map Builder。
2. 依照 Epic 1 sub-issues `#23` 到 `#46` 逐步開發。
3. 每個 task issue 開一條 branch，例如 `chore/setup-uv-python-backend-foundation`。
4. 開 PR 合併回 `main`。
5. PR body 使用 `Closes #<issue-number>` 關聯對應 task issue。
6. 合併前需要 human review 加上 Codex review。
7. Epic 1 可用後，再開始拆 Epic 2。

## 工作原則

- Scanner 預設必須是 read-only。
- 產品預設採 local-first privacy。
- 不顯示完整 secret value。
- 報告要提供 evidence，不只給分數。
- Packaging 要和 core scanner 分離。
- 先穩定 CLI 與 JSON report，再打磨 launcher。

## Backend 結構

目前 Python backend 採 `src/` layout：

```text
src/kai_mind/
  core/   # 核心 scanner、services、models，不能依賴 CLI 或 Web adapter
  web/    # local web API / FastAPI adapter
  cli/    # command-line adapter
tests/    # smoke tests 與後續 scanner fixtures / contract tests
```

依賴方向固定：

```text
Web / CLI adapters -> Core services -> Providers / Models
```

## Backend 開發命令（UV）

本專案的 Python backend 使用 UV 管理 dependency、lock file 和執行環境：

- `pyproject.toml`：宣告專案 metadata、runtime dependencies、dev dependencies。
- `uv.lock`：固定 dev/CI 實際安裝版本。
- `.venv/`：UV 依照 `uv.lock` 建立的本機虛擬環境，不需要 commit。

VS Code interpreter 請選：

```text
/Users/linjunting/Local_AI_Health_Doctor/.venv/bin/python
```

### 第一次設定

如果電腦還沒有 UV，先安裝 UV。

Windows PowerShell 可使用：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS / Linux 可使用：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

安裝後重新開啟 terminal，確認 `uv --version` 可以執行。

進入專案根目錄後，同步環境：

```bash
uv sync
```

`uv sync` 會讀取 `pyproject.toml` 與 `uv.lock`，建立或更新 `.venv/`。

### 日常開發

```bash
uv run pytest
uv run ruff check .
uv run python -m kai_mind.cli.main --help
```

`uv run` 會在專案環境裡執行命令，不需要先手動啟用 `.venv`。

### 一鍵啟動前後端

開發 Viewer / Mapping UI 時，可以在專案根目錄同時啟動後端 API 與前端 Vite dev server：

```bash
uv run python scripts/dev.py
```

預設啟動：

- 後端 API：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

如果前端依賴還沒安裝，先執行：

```bash
corepack pnpm --dir frontend install
```

`scripts/dev.py` 只負責啟動本機 dev server，不會自動安裝套件；按 `Ctrl+C` 會一起停止前後端。

### 修改依賴

新增 runtime dependency：

```bash
uv add package-name
```

新增開發工具，例如測試或 lint 套件：

```bash
uv add --dev package-name
```

手動更新 lock file：

```bash
uv lock
```

檢查 `uv.lock` 是否跟 `pyproject.toml` 一致：

```bash
uv lock --check
```

原則：不要手動編輯 `uv.lock`；要改依賴就改 `pyproject.toml` 或使用 `uv add`，再讓 UV 重新產生 lock。
