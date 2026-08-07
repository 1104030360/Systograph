# 2026-05-27 Phase 1 Python Backend Foundation Report

## 實作邏輯

- 建立 Epic 1 Python backend foundation，採 `src/` layout。
- 保留清楚邊界：`cli/` 與 `web/` 是 adapter layer，`core/` 是後續 services/models/providers 放置邊界。
- 此階段不實作 scanner、provider、JSON schema、queue、worker、database 或真實 Web API route。
- `pyproject.toml` 使用 direct dependency range pin。
- 使用 UV 專案模式建立 `uv.lock`，固定 dev/CI 解析結果。
- 用 TDD/BDD 的順序執行：先寫 smoke tests，確認失敗，再補最小 package skeleton，最後確認測試通過。

## 步驟

1. 讀取 `AGENTS.md`，確認 scanner 預設 read-only、不能暴露 secret、CLI/JSON contract 要穩定。
2. 讀取 `.cursor/rules/linus_torvalds.mdc`，以簡單資料結構、零破壞、避免過度設計為實作準則。
3. 讀取 Task 1 plan 與 `epic1-backend-design.md` Sections 6、17、19.2、19.17。
4. 建立 TODO：`docs/work/Timmy/schedule/todo/2026-05-27-phase1-python-backend-foundation-TODO.md`。
5. 先建立 `tests/test_smoke.py`：
   - package 可 import。
   - CLI help 可用。
   - import `systograph.core` 不會載入 `fastapi`。
6. 建立 `pyproject.toml`，設定 build backend、dependencies、dev dependencies、pytest、ruff、CLI entry point。
7. 執行 RED 測試，確認 3 個測試因 `systograph` package 不存在而失敗。
8. 建立最小 package skeleton：
   - `src/systograph/__init__.py`
   - `src/systograph/cli/__init__.py`
   - `src/systograph/cli/main.py`
   - `src/systograph/core/__init__.py`
   - `src/systograph/web/__init__.py`
9. 修正 Typer 空 app 無法產生 help command 的問題。
10. 依 UV 專案模式把 dev dependencies 放到 `[dependency-groups].dev`。
11. 執行 `uv lock` 建立 `uv.lock`。
12. 執行 `uv sync` 驗證 UV 可以同步專案環境。
13. 更新 `README.md` 的 backend 開發命令。

## 測試方式

```bash
uv run pytest
uv run ruff check .
uv run python -m systograph.cli.main --help
uv lock --check
uv run --project /Users/linjunting/Systograph python -c 'import systograph; print(systograph.__version__)'
uv run --project /Users/linjunting/Systograph python -m systograph.cli.main --help
```

最後兩個命令從 `/private/tmp` 執行，用來確認 package import 與 CLI help 不依賴 repo cwd。

## 遇到的問題與解法

- 問題：系統 Python 沒有 `pytest`，本機也沒有 `uv` 或 `ruff`。
  - 解法：先安裝 UV CLI，再以 UV 建立與同步專案環境。
- 問題：RED 階段尚未建立 `src/systograph`，package install/import 會失敗。
  - 解法：先確認 smoke tests 因缺少 package 失敗，再建立最小 package skeleton。
- 問題：Typer 空 app 無法被 `CliRunner` 轉成 command。
  - 解法：增加 no-op callback，讓 CLI help 成為穩定的最小行為。
- 問題：沙盒不允許 UV 寫入 `/Users/linjunting/.cache/uv`。
  - 解法：本次驗證把 `UV_CACHE_DIR` 指到 `/private/tmp/uv-cache`；這是執行環境限制，不影響 repo 設定。

## 測試結果

- `pytest`: 3 passed。
- `ruff`: All checks passed。
- `uv sync`: 通過。
- `uv lock --check`: Resolved 40 packages。
- CLI help: exit code 0。
- 從 `/private/tmp` import package: 成功，輸出 `0.1.0`。
- 從 `/private/tmp` 執行 CLI help: exit code 0。

## 驗收核對

- `pyproject.toml`: 已建立。
- `src/systograph/` package skeleton: 已建立。
- `src/systograph/web/`、`src/systograph/cli/`、`src/systograph/core/`: 已建立。
- `tests/` 與 smoke test: 已建立。
- pytest 設定: 已建立。
- ruff 設定: 已建立。
- FastAPI / Uvicorn dependency: 已列入 `pyproject.toml`。
- 無真實 scanner logic: 符合。
- 無真實 Web API route: 符合。
- `core` 不 import FastAPI: 已由測試覆蓋。
- dev/CI lock file: `uv.lock` 已建立。
