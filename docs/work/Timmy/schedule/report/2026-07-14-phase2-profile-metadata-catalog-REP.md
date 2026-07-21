# Phase 2 Profile Metadata Catalog 完成報告

## 階段目標

完成 Plan 11：把 15 個 active profiles 的 presentation metadata 從 Python
搬到 package-bundled `profile_registry.toml`，同時保留 Python executable
semantics，並建立只讀、deterministic 的 `profile-registry/v1` projection contract。

## 實作邏輯

```text
      executable truth                         presentation truth
┌──────────────────────────┐              ┌──────────────────────────┐
│ profile_rule_definitions │              │ profile_registry.toml    │
│ ids／nodes／wiring       │              │ labels／axes／order／text│
└────────────┬─────────────┘              └────────────┬─────────────┘
             │                                         ▼
             │                              ProfileRegistryLoader
             │                              strict + fail closed
             │                                         │
             └──────────────────┬──────────────────────┘
                                ▼
                   ProfileFindingService + assembler
                                │
             52 assessments ────┴───▶ 15 ProfileFinding

validated registry ──▶ ProjectionService ──▶ JSON model + checked-in schema
                                            （engine 不讀回、無 API、無 artifact）
```

- Python 只擁有 `profile_id`、required nodes、wiring 與所有 status/evidence
  計算規則。
- TOML 只擁有 display/presentation metadata；unknown、missing、duplicate、
  invalid version/axis 與 coverage drift 一律 fail closed。
- `ProfileFindingService` 在 inference 前驗證 exactly 15 ids；缺 metadata 不會
  產生部分結果。
- Finding 組裝抽成 pure assembler，讓 service 保持 orchestration 單一責任；
  兩個 production 模組分別為 76 與 207 行，低於 250 行限制。

## TDD + BDD 步驟

| 階段 | RED 證據 | GREEN 結果 |
|---|---|---|
| Loader boundary | 測試收集因 `profile_registry_loader` 尚不存在而失敗 | strict loader 與 15-entry TOML 建立後通過 |
| Metadata injection | 2 個測試因 `ProfileFindingService` 尚不接受 registry 而失敗 | typed injection、wording-only 與 missing coverage 行為通過 |
| Projection contract | unit/contract tests 因 projection model/service 尚不存在而失敗 | deterministic projection、schema freshness、real serialization 通過 |
| Refactor safety | 53 個 profile tests 先作為綠燈基線 | 拆分 service/test modules 後同組測試仍全綠 |

BDD 情境覆蓋：

- Given valid package TOML，When default inference runs，Then 15 筆 finding 使用
  TOML metadata 且 deterministic semantics 不變。
- Given malformed、unknown、missing、duplicate 或 invalid catalog，When loader
  parses，Then raise typed catalog error，不輸出 partial result。
- Given reversed typed registry，When projection runs，Then 依 `display_order`
  穩定排序並通過 Draft 2020-12 schema validation。
- Given custom wording，When injected into finding service，Then只改 label、
  description 與 default wording，不改 status、depth、evidence 或 coverage。

## 實作步驟與檔案

1. 建立 `profile_rule_definitions.py`，並刪除混合 ownership 的舊
   `profile_registry.py`。
2. 建立 `profile_registry.toml`、`ProfileMetadataEntry`、
   `ProfileMetadataRegistry`、loader 與 typed error taxonomy。
3. 將 runtime finding path 接上 package registry；另以
   `profile_finding_assembler.py` 隔離 deterministic aggregation。
4. 建立 projection Pydantic models/service 與
   `schemas/profile-registry.v1.schema.json`。
5. 加入 loader、runtime injection、rule detection、projection、schema、
   integration 與 direct/transitive import-boundary tests。
6. 同步 MODEL-CONTRACT、Phase 2 design、Plan 10/11 與 architecture ASCII。

## Scripts 盤點

```text
scripts/
  └── rg profile_registry／ProfileRegistry／profile-registry → 0 matches

web／cli／BuildArtifactPublisher／frontend
  └── projection symbols／profile_registry.json → 0 matches
```

結論：現有 scripts 沒有 profile registry consumer 或 duplicated rule logic，
不需要為本階段強制修改。Projection 也未被誤接成 API 或 per-build artifact。

## 遇到的問題與解法

| 問題 | 原因 | 解法 |
|---|---|---|
| `mypy .` 掃到 vendored reference code | canonical config 已限定 `src`、`tests`，但 `.` 覆蓋範圍 | 文件命令改為 `uv run mypy`，遵守 `pyproject.toml` files contract |
| Service 與單一 test module 超過 250 行 | finding aggregation 與多種測試責任混在同檔 | 拆出 pure assembler、shared test fixture helper、metadata 與 rule detection 測試模組 |
| Ruff 回報 test helper imports 排序 | `tests.helpers` 在目前 Ruff 設定被分到第三方 import group | 依 Ruff preview 的排序做機械調整後重跑 |
| Comment checker 攔截測試註解 | 新測試使用 BDD `Given/When/Then` markers | 依 checker 規則保留 BDD 註解；production code 未新增說明性註解 |

## 階段測試結果

```text
Profile-focused pytest                 59 passed
Ruff                                  All checks passed
Mypy                                  258 source files, no issues
No-excuse rules                       no violations in 19 files
Production module size               76 / 207 lines
Split test module size                116 / 213 / 161 lines
```

全量 backend/frontend、CLI manual QA、build 與 final diff audit 會記錄在本階段的
整合完成報告；在這些驗收通過前，不宣稱 Phase 5 全部完成。
