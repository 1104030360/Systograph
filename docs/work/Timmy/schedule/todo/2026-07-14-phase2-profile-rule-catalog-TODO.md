# Phase 2 Profile Rule / Catalog TODO

## 目標

依 `phase5.md` 完成 Plan 10 與 Plan 11：鎖定 Profile Engine 的 executable
ownership，以 TDD + BDD 補齊 direct／transitive dependency guard，並將 15 個
profile 的 presentation metadata 從 Python 遷移至 package-bundled TOML，且不改變
既有 status、evidence、depth、coverage 或 Mapping Completeness。

## 已確認基線

- [x] 閱讀 `AGENTS.md`、Linus rule、Phase 5、Plan 10 與 Plan 11。
- [x] 建立 `codex/phase2-profile-catalog` 分支，保留既有 Plan 10/11 文件更新。
- [x] 後端 baseline：`.venv/bin/pytest -q`，`776 passed`。
- [x] 前端 baseline：`pnpm test`，`7 passed`。
- [x] 確認目前 active contract 為 52 reference assessments、15 profiles 與五態。
- [x] 確認本階段不新增 API、frontend 欄位或 per-build `profile_registry.json` artifact。

## 實作邏輯

1. Python rule definitions 只保存 `profile_id`、required nodes 與 wiring；所有會改變
   status、depth、activation、evidence strength 或 coverage 的邏輯都留在 Python。
2. `profile_registry.toml` 只保存 label、description、axes、display order 與預設文案，
   並由 dedicated loader 在 package boundary 一次 parse 成 frozen typed registry。
3. `ProfileFindingService` 同時讀 executable definition 與 validated metadata；缺少任何
   active profile metadata 時 fail closed，不輸出部分結果。
4. JSON registry 是 deterministic read-only projection，只用於 contract/schema 驗證；
   engine 不讀回 JSON，也不把它發布成 API 或 build artifact。
5. 每個 production behavior 都先寫 Given／When／Then 測試並觀察正確 RED，再以最小
   實作轉 GREEN；每個階段完成後執行 focused regression 並寫 Report。

## 執行階段與步驟

### 階段 A：計畫與基線

- [x] 逐條對照 Plan 10/11 與目前 profile codepath、tests、contracts。
- [x] 確認 UA／Plan 18 只改 Step 3 scan ownership，不退役 profile metadata。
- [x] 執行 backend/frontend baseline。
- [x] 建立本 TODO 與 live-state Report。

### 階段 B：Plan 10 boundary hardening

- [x] RED：讓 dependency guard 自動探索 profile modules，並驗證 indirect import chain。
- [x] GREEN：建立最小 repo-local import graph guard 與可定位的 failure message。
- [x] RED/GREEN：補齊 risk-only、unknown refs、coverage、六種 activation 與 immutable
  Mapping Completeness weights regressions。
- [x] 同步 canonical ownership 文件並完成 Plan 10 focused verification。
- [x] 建立 Plan 10 完成 Report。

### 階段 C：Plan 11 metadata migration

- [x] RED：先建立 loader characterization、strict validation 與 exact coverage tests。
- [x] GREEN：拆出 `profile_rule_definitions.py`，移除舊 `profile_registry.py`。
- [x] GREEN：建立 `profile_registry.toml`、typed registry 與 dedicated loader。
- [x] RED/GREEN：將 Metadata 注入 `ProfileFindingService`，證明只改文案、不改語意。
- [x] RED/GREEN：建立 deterministic JSON projection、schema 與 freshness contract tests。
- [x] 建立 Plan 11 完成 Report。

### 階段 D：整合、文件與架構圖

- [x] 盤點並更新受影響 scripts；沒有必要變更時以實際 usage 驗證留下證據。
- [x] 同步 `MODEL-CONTRACT.md` 與 Phase 2 design 文件。
- [x] 更新 `docs/work/Timmy/learn/architecture.md` ASCII 全景圖。
- [x] 執行 CLI happy path、bad input 與 `--help` Manual QA。
- [x] 建立整合完成 Report。

### 階段 E：完整驗收

- [x] 執行 focused、full backend/frontend tests、Ruff、Mypy 與 schema checks。
- [x] 執行 changed-file diagnostics、diff review、secret/path safety 與 plan compliance audit。
- [x] 逐條確認 Plan 10/11 checkbox 與 stop conditions，更新完成狀態。
- [x] 完成最終 Report 與本 TODO 的測試摘要。

## 驗收重點

- Scanner 與 catalog loader 都不讀 target repo metadata catalog，也不寫 target repo。
- TOML 沒有 executable fields；Python definitions 沒有 presentation metadata。
- 15 profile ids、排序與既有 fixture 行為保持相容。
- Missing、malformed、unknown、duplicate、invalid version／axis 都 fail closed。
- Profile path 不直接或間接依賴 mapping、manual、LLM 或 web modules。
- `profile_registry.json` projection schema-valid，但不是 runtime truth 或 public artifact。

## 測試結果

- 開發前 backend baseline：`776 passed in 18.66s`。
- 開發前 frontend baseline：`3 files / 7 tests passed`。
- Plan 11 focused：`59 passed`。
- Final extended focused：`77 passed`；完整 backend：`819 passed in 17.31s`。
- 完整 frontend：`3 files / 7 tests passed`；ESLint `0 errors / 1 existing warning`；
  TypeScript + Vite build 成功。
- Ruff format：`272 files already formatted`；Ruff check：all checks passed；
  Mypy：`258 source files` 無問題。
- Wheel build 成功，且包含 package resource `kai_mind/core/rules/profile_registry.toml`。
- Manual QA：CLI help exit 0、fixture map exit 0 並產 52/15、missing project exit 1
  且回報 `project_path_not_found`。
- 舊 `HEAD` 與新實作的 4 個 v2 fixtures semantic diff 完全相同。
