# Phase 2 Profile Catalog 整合驗收報告

## 結論

Plan 10 與 Plan 11 已實作完成。Profile Engine 的 executable semantics 與
presentation metadata 已分開；TOML loader、runtime injection、read-only projection、
schema、boundary guards、canonical docs 與 architecture ASCII 均已驗收。

```text
Python rules + 52 assessments          package TOML metadata
             │                                  │
             └───────────┬──────────────────────┘
                         ▼
            deterministic Profile Engine
                         │
                         ├──▶ 15 ProfileFinding → readiness
                         └──▶ profile_signals.json

validated TOML ──▶ read-only projection + schema
                   （engine 不讀回、無 API、無 build artifact）
```

## Manual QA

### Library happy path、bad catalog 與 projection

```text
H1_DEFAULT_OK ids=15 schema=profile-registry/v1
H1_BAD_INPUT_OK error=ProfileRegistryError
H2_PROJECTION_OK count=15 orders=10..150
H3_SEMANTICS_OK assessments=52 profiles=15 denominator=52
                rag=detected/static_multiple_signals
```

### 真實 CLI surface

```text
uv run systograph --help                  exit 0
uv run systograph map --help              exit 0
CLI map fixture                         exit 0
profile_signals.json                    52 assessments / 15 profiles
CLI map missing project                 exit 1
failure reason                          project_path_not_found
error report stage                      precondition
```

所有 CLI output 都寫入 `TemporaryDirectory` 並於 read-back 後清除；一次 diagnostic
誤用 default output 產生的 `map-error.md` 也已刪除，沒有留下 debug artifact。

## 三個 runtime 假說與證據

| 假說 | 實際證據 | 結果 |
|---|---|---|
| wheel/package path 找不到 TOML，或 invalid TOML 被接受 | default loader 讀到 15 ids；invalid catalog raise `ProfileRegistryError` | 推翻 |
| projection order/schema drift | real JSON serialization 為 10..150，Draft 2020-12 validation 通過 | 推翻 |
| Metadata 遷移改變 executable semantics | 從 Git `HEAD` 解出舊 code，在隔離 `PYTHONPATH` 比對 4 個 v2 fixtures | 推翻 |

Baseline semantic diff 比較欄位：status、activation、depth/reason、所有 evidence ids、
conflicts、coverage、related refs 與 Mapping Completeness；4 個 fixtures × 15 profiles
完全相同。

## 完整驗證結果

```text
uv lock --check                         resolved 55 packages
backend full pytest                     819 passed in 17.31s
focused profile pytest                  77 passed
Ruff format / check                     272 files formatted / all checks passed
Mypy                                    258 source files, no issues
frontend Vitest                         3 files / 7 tests passed
frontend ESLint                         0 errors / 1 existing warning
frontend TypeScript + Vite build        success, 1844 modules transformed
wheel build                             exit 0
wheel package resource                  systograph/core/rules/profile_registry.toml
no-excuse checker                       no violations in 19 changed Python files
git diff --check                        passed
```

Frontend 沒有本階段 diff；lint/build 顯示的 Fast Refresh、`web-worker` external 與
large chunk warnings是既有前端警告，沒有因本次 backend/catalog 改動新增 error。

## 人工 Review

- Ownership：Python definitions 沒有 label/axis/wording；TOML 沒有 executable keys。
- Fail closed：malformed、unknown、missing、duplicate、invalid type/version/axis 與 id
  coverage 都有 boundary tests。
- Dependency：profile-prefixed models/services 與 reference assessment 會自動進入
  repo-local import graph，direct/transitive mapping、manual、LLM、web chain 都會失敗。
- Lifecycle：matching catalogs 仍留給 Plan 16 parity / Plan 18 retirement；profile、risk、
  next-check、reference、inventory 與 LLM config metadata 保留。
- Surface：web、CLI、frontend、scripts、`BuildArtifactPublisher` 沒有 projection consumer；
  因此沒有偷偷增加 API 或 per-build `profile_registry.json`。
- Scope：沒有變更五態、activation、depth、evidence strength、coverage 或 Mapping
  Completeness，且與 `HEAD` 舊實作做過 runtime semantic diff。

依 no-subagent 邊界，本輪使用主 agent 自行執行完整 diff review、runtime hypotheses 與
全量驗收，沒有啟動 review subagent。

## Scripts 與 Architecture

- `scripts/` usage inventory 為 0 個 profile registry consumers，不需要修改。
- `docs/work/Timmy/learn/architecture.md` 已更新完整 ASCII 全景與 focused catalog flow。
- 該 `learn/` 目錄目前由 repo `.gitignore` 忽略；檔案已在本機更新，但不在一般 Git diff
  中。未修改 `.gitignore`，避免擴張版本控制政策。

## 最終風險

本階段沒有未解 blocker。僅保留既有 frontend build warnings；它們不屬於 Plan 10/11，
也沒有 frontend change 可歸因到本次實作。
