# Task 1: Setup Python Backend Foundation

## 目標
建立 Epic 1 後端的 Python 專案骨架，讓後續 scanner、service、local web API、CLI、tests 都有穩定放置位置。這個任務只建立基礎結構與最小可執行測試，不實作實際掃描邏輯。

## 為什麼要先做這個
兩份設計文件已決定 Epic 1 backend 使用 Python，且目前 repo 尚未有 `src/`、`tests/`、`pyproject.toml`。現在產品入口優先順序改為 GUI/local web UI，因此 foundation 必須先預留 `web/` adapter 邊界，避免後續 frontend 對接時再重切架構。

## 前置需求
- 已閱讀 `epic1-backend-design.md` 的 Sections 6、17、19.2。
- 已確認目前 repo 沒有既有 Python backend scaffold。
- 已確認 task plan 檔案只規劃 Epic 1 backend，不實作 frontend 畫面。
- 已確認 local web backend framework 採 FastAPI。
- 已確認 Python dependency / lock / run workflow 採 UV。

## 實作範圍
- 建立 `pyproject.toml`。
- Dependency 策略採已決策選項 A：`pyproject.toml` 放 direct dependency 版本範圍，並用 `uv.lock` 固定 dev/CI 完整環境。
- 開發依賴放在 `[dependency-groups].dev`，由 `uv sync` 預設同步。
- 建立 `src/kai_mind/` package skeleton。
- 建立 `src/kai_mind/web/`、`src/kai_mind/cli/` 與 `src/kai_mind/core/` 基本目錄。
- 建立 `tests/` 與最小 smoke test。
- 設定 pytest、ruff 或等價 lint/test 指令。
- 加入 FastAPI local web API 所需 dependency，但不實作真實 route。

## 不包含範圍
- 不建立 scanner provider。
- 不建立 JSON schema。
- 不實作 CLI command 的真實掃描。
- 不實作真實 Web API route、queue、worker、database。
- 不實作 frontend GUI 畫面。

## 建議實作步驟
1. 建立 `pyproject.toml`，採用 Python `src/` layout。
2. 加入最小 runtime direct dependencies，使用範圍 pin：`pydantic>=2,<3`、`fastapi>=0.115,<1`、`uvicorn[standard]>=0.30,<1`、`typer>=0.12,<1`、`jsonschema>=4,<5`、`httpx>=0.27,<1`。
3. 在 `[dependency-groups].dev` 加入開發依賴：`pytest>=8,<9`、`ruff>=0.6,<1`。
4. 建立 `src/kai_mind/__init__.py` 與 `src/kai_mind/cli/main.py`。
5. 建立 `src/kai_mind/core/__init__.py` 與 `src/kai_mind/web/__init__.py`。
6. 執行 `uv lock` 建立 `uv.lock`。
7. 執行 `uv sync` 確認環境可同步。
8. 建立 `tests/test_smoke.py`，確認 package 可 import。
9. 執行 `uv run pytest`，確認測試通過。
10. 記錄常用 UV 開發命令到 README 或後續 dev note。

## 預期輸出
- `pyproject.toml`
- `src/kai_mind/__init__.py`
- `src/kai_mind/cli/main.py`
- `src/kai_mind/core/__init__.py`
- `src/kai_mind/web/__init__.py`
- `tests/test_smoke.py`
- `uv.lock`

## 驗收標準
- `uv sync` 可以同步開發環境。
- `uv run pytest` 可以執行並通過 smoke test。
- `uv run python -m kai_mind.cli.main --help` 或等價 CLI entry 可以顯示 help。
- package import 不依賴 cwd hack。
- `pyproject.toml` 使用 direct dependency range pin，repo 中存在 `uv.lock`。
- 新增目錄符合設計文件的 dependency direction：Web/CLI adapters -> core services -> providers/models。
- FastAPI / Uvicorn dependency 已列入 `pyproject.toml`，但 core package 不 import FastAPI request object。

## 可能風險與注意事項
- 不要在這一步加入 business logic，避免 foundation task 膨脹。
- `src/` layout 要確認 pytest 能找到 package。
- UV cache 是執行環境細節，不應寫入 repo；repo 只保存 `uv.lock`。
- 參考依據：PyPA 官方 packaging docs 建議以 `pyproject.toml` 宣告專案 metadata；Typer 官方文件支援 type-hint based CLI 與 `CliRunner` 測試；FastAPI 官方文件提供 OpenAPI、Pydantic model、automatic docs，適合作為 GUI/local web UI 的 local API layer。

## 新手提示
這一步像是先蓋工地的地基和路標。後面每個功能都會放進固定資料夾，才不會把 scanner、local web API、CLI、model 混在一起。

## 視覺化說明
```text
┌──────────────────────┐
│ pyproject.toml        │
│ dependencies + tools  │
└───────────┬──────────┘
            ↓
┌──────────────────────┐
│ src/kai_mind package  │
│ backend source root   │
└───────┬─────────┬────┘
        │         │
        ↓         ↓
┌──────────────┐  ┌──────────────┐
│ core/        │  │ web/ + cli/  │
│ models       │  │ commands     │
│ services     │  │ API/entrypts │
│ providers    │  │              │
└──────┬───────┘  └──────┬───────┘
       │                 │
       └────────┬────────┘
                ↓
┌──────────────────────┐
│ tests/                │
│ smoke + future tests  │
└──────────────────────┘
```
