# 2026-05-27 Phase 1 Python Backend Foundation TODO

## 目標

依照 `docs/work/Timmy/schedule/plan/finish/01-setup-python-backend-foundation.md` 建立 Epic 1 Python backend foundation。

## 實作邏輯

- 採 `src/` layout，讓 package import 不依賴目前工作目錄。
- 保持 adapter 邊界：`web/` 與 `cli/` 是入口層，`core/` 不依賴 FastAPI request object。
- 只建立 foundation，不加入 scanner provider、JSON schema、queue、worker、database 或真實 scan logic。
- 使用 direct dependency range pin，並以 UV 建立 dev/CI lock file。
- 用 TDD/BDD：先寫描述行為的 smoke tests，再補最小可通過的 package skeleton。

## 步驟

1. 閱讀 `AGENTS.md`、`.cursor/rules/linus_torvalds.mdc`、phase1 dev prompt、Task 1 plan。
2. 閱讀 `epic1-backend-design.md` Sections 6、17、19.2、19.17，確認模組邊界與 FastAPI 決策。
3. 建立最小測試，涵蓋 package import、CLI help、core 不載入 FastAPI。
4. 執行測試，確認因尚未建立 package 而失敗。
5. 建立 `pyproject.toml`、`src/systograph/`、`core/`、`web/`、`cli/`。
6. 把 runtime dependencies 放在 `[project].dependencies`，把 pytest/ruff 放在 `[dependency-groups].dev`。
7. 執行 `uv lock` 建立 `uv.lock`。
8. 執行 `uv sync` 驗證 UV 環境同步。
9. 執行 `uv run pytest`、`uv run ruff check .`、`uv run python -m systograph.cli.main --help`。
10. 撰寫 report 並逐項核對驗收標準。

## 驗收

- `uv sync` 通過。
- `uv run pytest` 通過。
- `uv run python -m systograph.cli.main --help` 可以顯示 help。
- `pyproject.toml` 含 direct dependency range pin。
- repo 中存在 `uv.lock`。
- `core` package 不 import FastAPI。
