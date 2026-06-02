# Task 12: Aggregate Raw Scan Facts

## 目標
建立 `ProjectScanService`，統一 orchestration providers，將各 provider 結果整理成 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`、skipped files summary。這一層只收集 facts，不做 slot final judgment。

## 為什麼要先做這個
設計文件將 Stage 4 Raw Scan Facts 定義為 canonical truth 的最低層。若 providers 各自輸出不同形狀，後續 mapping、risk、validation 會難以穩定。

## 前置需求
- Task 7-11 providers 已有初始實作。
- Task 5 secret masking 已可共用。
- Task 2 已有 models/schema 基礎。
- **Task 12a (Extract Provider Rule Catalogs) 應在 Task 12 之前完成。**

## 與 Task 12a 的關係

Task 12a 將 Task 9 / 10 / 11 provider 中硬編碼的 detection rules 搬到 package-bundled TOML rule catalogs（詳見 [12a-extract-provider-rule-catalogs.md](./12a-extract-provider-rule-catalogs.md)）。

執行順序：

```text
Task 9  DockerComposeProvider（硬編碼 image rules）
Task 10 DependencyManifestProvider（硬編碼 package rules）
Task 11 CodePatternProvider（硬編碼 regex rules）
        ↓
Task 12a Extract Provider Rule Catalogs
  ├── dependency_manifest_rules.toml
  ├── docker_image_rules.toml
  ├── code_pattern_rules.toml
  └── RuleCatalogLoader
        ↓
Task 12 Aggregate Raw Scan Facts（本任務）
  └── ProjectScanService 收集所有 provider 結果
```

### 為什麼 12a 要在 12 之前

- Task 12 的 `ProjectScanService` 會統一呼叫所有 providers。如果 providers 的 rule 來源還在重構中（從 Python 搬到 TOML），同時做 aggregation 會增加 regression 風險。
- 先讓 12a 把規則來源穩定下來，12 只需要收集穩定的 `ProviderScanResult`，不用擔心 rule loading 方式的變化。

### Task 12a 對 Task 12 的影響

| 影響面 | 說明 |
|---|---|
| Provider API | 不變。每個 provider 仍回傳 `ProviderScanResult` |
| Facts / Evidence | 不變。rule_id、fact_kind、evidence 格式都不改 |
| Provider 建構方式 | 可能改變。Provider `__init__` 可能需要接收 rule catalog path 或 loader |
| 測試 | 12a 完成後，原有 provider tests 應全部通過，12 可放心整合 |

## 實作範圍
- 建立 `ScanFact`、`Evidence`、`ParseIssue` 統一 models。
- 建立 `ProjectScanService`。
- 串接 Filesystem、Config、Docker、Dependency、CodePattern providers。
- 產生 provider stage warnings。
- 保留 partial failures，不讓單一 provider 失敗中止整體 scan。

## 不包含範圍
- 不做 component detection。
- 不做 endpoint/risk/flow derivation。
- 不寫 artifacts。
- 不產生 Markdown。

## 建議實作步驟
1. **確認 Task 12a 已完成**：providers 已從 TOML rule catalogs 載入 rules，原有 provider tests 全部通過。
2. 補齊 `src/kai_mind/core/models/scan.py`。
3. 建立 provider result interface。
4. 建立 `src/kai_mind/core/services/project_scan_service.py`。
5. 將 provider outputs normalize 成統一 facts/evidence/issues。
6. 加入 deterministic ordering，讓 snapshot 穩定。
7. 寫 integration test：basic fixture 產生 Docker/config/dependency/code facts。
8. 寫 partial failure test：malformed compose 仍有 facts output。
9. 寫 rule catalog 載入失敗 test：TOML catalog 損壞時 `ProjectScanService` 應明確報錯，不靜默跳過。

## 預期輸出
- `src/kai_mind/core/models/scan.py`
- `src/kai_mind/core/services/project_scan_service.py`
- `tests/unit/core/test_project_scan_service.py`

### 前置產出（由 Task 12a 提供）
- `src/kai_mind/core/rules/dependency_manifest_rules.toml`
- `src/kai_mind/core/rules/docker_image_rules.toml`
- `src/kai_mind/core/rules/code_pattern_rules.toml`
- `src/kai_mind/core/services/rule_catalog_loader.py`
- `tests/unit/core/test_rule_catalog_loader.py`

## 驗收標準
- 所有 facts 都有 rule_id 或 provider source。
- 所有 evidence 都有 project-relative file path 或合理 non-file source。
- parse issues 帶 scan_stage、file、reason。
- provider partial failure 不讓 ProjectScanService crash。

## 可能風險與注意事項
- 這層不可偷偷決定 slot detected。
- evidence id 先可用穩定 hash input，但最終 deterministic id 在 normalize task 收斂。
- 不要保存 full raw config value。

## 新手提示
ProjectScanService 像資料收件中心：把每個 provider 的結果收齊、排好，但還不判斷誰代表什麼 RAG 元件。

## 視覺化說明
```text
┌──────────────────────────────────────────────────────────┐
│ Task 12a: TOML Rule Catalogs                             │
│ ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│ │ dependency_    │ │ docker_image │ │ code_pattern_    │ │
│ │ manifest_rules │ │ _rules.toml  │ │ rules.toml       │ │
│ │ .toml          │ │              │ │                  │ │
│ └───────┬────────┘ └──────┬───────┘ └────────┬─────────┘ │
│         └─────────────────┼──────────────────┘           │
│                           ↓                              │
│              RuleCatalogLoader                           │
└──────────────────────────┬───────────────────────────────┘
                           ↓
┌────────────┐ ┌──────────┐ ┌──────────┐
│ Filesystem │ │ Config   │ │ Docker   │
└─────┬──────┘ └────┬─────┘ └────┬─────┘
      │             │            │
      └─────────────┼────────────┘
                    ↓
┌──────────────┐ ┌────────────────┐
│ Dependencies │ │ Code Patterns  │
└──────┬───────┘ └───────┬────────┘
       └─────────┬───────┘
                 ↓
┌──────────────────────────┐
│ ProjectScanService        │
│ (Task 12)                 │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ScanFact / Evidence       │
│ ParseIssue                │
└──────────────────────────┘
```
