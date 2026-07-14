# KAI-Mind

> **命名狀態：** Repository 與部分既有文件目前仍使用
> `Local_AI_Health_Doctor` / `Local AI Health Doctor`。這是暫時名稱，後續會統一更名；
> 現階段產品與程式碼名稱以 **KAI-Mind** 為主。

KAI-Mind 是一個 AI Agent / RAG 系統的 **Release Readiness Gate**。它協助團隊在
demo、交付、部署或進入 CI/CD 前，掃描既有 local AI 系統、建立 AI System Map，並產出
可追蹤的 evidence-backed 檢查結果。

KAI-Mind 是開發者工具，不是醫療診斷、治療、臨床決策或醫療器材認證工具；
`Health Doctor` 暫名不代表產品提供醫療建議或醫療級保證。

## 目前能力與目標能力

README 必須區分「目前程式碼已能執行」與「roadmap / 尚未交付」，避免把設計文件寫成
已完成產品功能。

### 目前已實作（含 Phase2 S1 pipeline-core 後端）

- deterministic-first scanner：先以 filesystem、config、dependency、Docker 與 code pattern
  providers 擷取結構化 facts / evidence（Understand-Anything 結構主掃仍為後續 Phase）。
- `ai-system-map/v1` 仍為 **active canonical** artifact；另有 v2 compatibility migration／
  internal normalized v2（`active` 尚未切到 v2）。
- 每次成功 build 可 atomic publish **10 public siblings**（map／Markdown／Mermaid、
  `profile_signals.json`、`readiness_report.json`、static execution JSON 等）。
- package-bundled **10-plane / 52-node** capability reference catalog 與 **15 MVP profiles**；
  `ProfileInferenceService` 為確定性 Python 評估（與 mapping proposal 運行時分離）。
- durable local JSON state：`${KAI_MIND_STATE_DIR:-~/.kai-mind}`，含 project／scan／build
  lineage、manual mappings、latest pointer；支援 restart recovery。
- Apply confirmations、map-builds query／history、Detail Scan child build、Trace build binding。
- CLI（`kai-mind`）、FastAPI local web API 與 frontend Viewer 共用同一套 core services。
- scan boundary review、path redaction、secret masking 與 snapshot safety checks。
- sample projects、contract／unit／integration／web／e2e tests 與 frontend 基礎串接
  （import → scans → map／SSE）。

### 尚未全部實作／仍屬後續目標

- 將 `ai-system-map/v2` 切成 **active** canonical（Plan 13／cutover）。
- Understand-Anything 結構掃描升為主掃（Phase B／C）與舊 TOML 主掃退役。
- frontend v2 cutover、Graph Studio、profile／readiness 完整 UI、Apply button 產品流。
- CI／產品級 release gate，以及對外宣稱穩定的單一 `READY`／`RISKY`／`NOT READY` runtime
  verdict UX（後端已有 `readiness_report.json` 與 evidence-backed findings；正式產品
  verdict／CI gate 仍以後續 Epic／contract 為準）。
- runtime component trace（deferred）與 AssessmentOrchestrator（不做／deferred）。

因此，demo 或 UI 不應把「正式 release gate 已上線」寫成現況；請以
[`docs/MODEL-CONTRACT.md`](docs/MODEL-CONTRACT.md) 與
[`docs/API-GUIDE.md`](docs/API-GUIDE.md) 的 current 標記為準。

這個專案不是 AI chatbot、RAG builder，也不是完整 observability 平台。它的核心邊界是：
掃描一套已存在的 AI 系統，建立 canonical AI System Map，並用 evidence 支援後續 readiness
判斷，而不是代替團隊建立或執行 AI 應用。

## 產品方向

KAI-Mind 應該先以跨平台核心為主。Epic 1 目前優先支援 GUI / local web UI，但 scanner core
必須獨立，CLI、Web API、launcher 與 CI 都不可重複實作 core scanner logic。

```text
Core Engine
    |
    +-- Local Web API / GUI
    +-- CLI
    +-- Windows launcher
    +-- macOS launcher
    +-- CI / GitHub Actions
```

這樣可以避免做成只能在 Windows 開啟的 `.exe`，並讓核心 scanner 可以同時支援 Windows、
macOS、Linux、本機開發與 CI。

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

Epic 1 已能產出可用的 `ai_system_map.json` 與 Phase2 S1 後端契約；後續依 Phase2 static
pipeline／各 Epic 子任務推進，不要把未合併的 design-only 文件當成已交付。

## 重要文件

| 用途 | 文件 |
|------|------|
| HTTP 契約 | [`docs/API-GUIDE.md`](docs/API-GUIDE.md) |
| Artifact／欄位語意 | [`docs/MODEL-CONTRACT.md`](docs/MODEL-CONTRACT.md) |
| Phase2 設計基線 | [`docs/design/epic1-phase2.md`](docs/design/epic1-phase2.md) |
| Epic 1 設計 | [`docs/design/epic1.md`](docs/design/epic1.md) |
| Frontend JSON handoff | [`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`](docs/work/Timmy/design/EPIC1/frontend-json-handoff/) |
| Phase2 執行計畫 | [`docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/`](docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/) |
| API trace scripts | [`scripts/trace_*.sh`](scripts/) |

## 建議的開發流程

1. 從對應 Epic／Phase2 task issue 開 branch（一例：`feat/phase2/s1-pipeline-core`）。
2. 每個 task issue 一條 branch；PR body 使用 `Closes #<issue-number>`（或 `Ref`）。
3. 合併前需要 human review 加上 Codex review。
4. 契約變更時同步 `docs/API-GUIDE.md` 與 `docs/MODEL-CONTRACT.md`。
5. 本機 API 驗收可用 `scripts/trace_*.sh`；前後端一起跑用 `uv run python scripts/dev.py`。

## 工作原則

- Scanner 預設必須是 read-only（對**被掃專案**）；寫入僅限明確的 state／output 目錄。
- 產品預設採 local-first privacy。
- 不顯示完整 secret value。
- 報告要提供 evidence，不只給不透明總分。
- Packaging 要和 core scanner 分離。
- **Two-Phase Analysis**：先確定性結構 facts，再視需要做語意分析；禁止把原始碼整包丟給 LLM
  做黑箱架構發現。
- Core engine 行為獨立於 platform launchers。

## Backend 結構

目前 Python backend 採 `src/` layout：

```text
src/kai_mind/
  core/       # services、models、providers、rules（不可依賴 web／cli）
  web/        # FastAPI adapter（routes／schemas／Depends／session）
  cli/        # Typer adapter（kai-mind）
  storage/    # 薄 re-export；durable JSON 在 core/providers
tests/        # unit／integration／contracts／web／cli／e2e／fixtures
```

依賴方向固定：

```text
Web / CLI adapters -> Core services -> Providers / Models
```

兩種持久化平面：

```text
~/.kai-mind（或 KAI_MIND_STATE_DIR）  → project／scan／build／mapping／latest
專案 output_dir                       → 10 sibling artifacts（map／profile／…）
```

## Backend 開發命令（UV）

本專案的 Python backend 使用 UV 管理 dependency、lock file 和執行環境：

- `pyproject.toml`：宣告專案 metadata、runtime dependencies、dev dependencies。
- `uv.lock`：固定 dev/CI 實際安裝版本。
- `.venv/`：UV 依照 `uv.lock` 建立的本機虛擬環境，不需要 commit。

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
uv run ruff check src tests
uv run mypy
uv run kai-mind --help
# 或
uv run python -m kai_mind.cli.main --help
```

`uv run` 會在專案環境裡執行命令，不需要先手動啟用 `.venv`。正式 lint gate 以
`ruff check src tests` 為準（全 repo 裸 `ruff check .` 可能掃到參考樹）。

### 一鍵啟動前後端

開發 Viewer / Mapping UI 時，可以在專案根目錄同時啟動後端 API 與前端 Vite
dev server：

```bash
uv run python scripts/dev.py
```

預設啟動：

- 後端 API：`http://127.0.0.1:8000`（OpenAPI：`/docs`）
- 前端：`http://127.0.0.1:5173`

如果前端依賴還沒安裝，先執行：

```bash
corepack pnpm --dir frontend install
```

`scripts/dev.py` 只負責啟動本機 dev server，不會自動安裝套件；按 `Ctrl+C` 會一起停止
前後端。前端 API base 預設 `http://127.0.0.1:8000`，可用 `VITE_API_BASE_URL` 覆寫。

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

原則：不要手動編輯 `uv.lock`；要改依賴就改 `pyproject.toml` 或使用 `uv add`，再讓 UV
重新產生 lock。
