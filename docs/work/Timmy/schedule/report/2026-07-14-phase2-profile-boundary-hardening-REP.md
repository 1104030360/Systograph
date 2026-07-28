# Phase 2 Profile Boundary Hardening Report

## 完成範圍

完成 Plan 10：profile dependency guard 已從四個手列檔案的 direct-import scan，提升為
自動探索所有 `profile*.py` 與 reference assessment service 的 repo-local transitive import
graph；同時補齊 profile semantics characterization 並同步 canonical ownership 文件。

## 實作邏輯

- 使用 Python AST 解析 project-owned imports，不增加 Import Linter dependency。
- 從每個 profile root 以 BFS 尋找最短 forbidden import chain，讓失敗訊息可直接定位
  direct 或 indirect boundary violation。
- Semantic regressions 鎖定既有五態、六種 activation、unknown navigation refs、coverage
  與固定 Mapping Completeness weights；沒有改寫 production inference semantics。
- 文件明確區分 Plan 18 matching-provider retirement 與持續保留的 Metadata／設定 catalogs。

## 執行步驟

1. 新增 auto-discovery 與 transitive-chain tests。
2. 觀察 RED：兩個 tests 因 helper 尚不存在而以 `NameError` 失敗。
3. 實作最小 AST import graph、BFS chain finder 與 deterministic failure output。
4. 補齊六種 activation、unknown refs 與 fixed weights characterization tests。
5. 同步 `MODEL-CONTRACT.md` 與兩份 Phase 2 design 文件。
6. 修正 README／Plan 10／Plan 11 的 Mypy 指令，使其遵守 `pyproject.toml` 的
   `files = ["src", "tests"]` canonical scope。

## 測試方式

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_boundaries.py -q
.venv/bin/pytest \
  tests/unit/core/test_profile_inference_service.py \
  tests/unit/core/test_profile_signal_validation_service.py \
  tests/unit/core/test_profile_signal_models.py -q
.venv/bin/ruff check src tests
.venv/bin/mypy
test ! -e src/systograph/core/rules/profile_registry.toml
git diff --check
```

## 遇到的問題與解法

- 問題：新 BFS queue 的 tuple 型別被 Mypy 推斷得過窄。
- 解法：明確標示 `deque[tuple[str, tuple[str, ...]]]`，不使用 `Any` 或 ignore。
- 問題：文件原本使用 `mypy .`，導致 CLI argument 覆蓋 pyproject scope，誤掃 vendored
  `ref-opensource/` 與不在正式 Mypy gate 的 scripts。
- 解法：改為無位置參數的 `mypy`，讓工具依 canonical `files` 設定檢查 project-owned
  `src` 與 `tests`；沒有修改第三方參考碼。

## 測試結果

- RED：`2 failed`，原因為 auto-discovery／chain helpers 尚未存在。
- GREEN：boundary file `5 passed`。
- Plan 10 focused suite：`46 passed`。
- Ruff：`All checks passed`。
- Mypy：`Success: no issues found in 247 source files`。
- Plan 10 checkpoint：`profile_registry.toml` 尚未存在，符合 Plan 11 handoff。
