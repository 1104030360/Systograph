# Task 12: Aggregate Raw Scan Facts

## 目標
建立 `ProjectScanService`，統一 orchestration providers，將各 provider 結果整理成 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`、skipped files summary。這一層只收集 facts，不做 slot final judgment。

## 為什麼要先做這個
設計文件將 Stage 4 Raw Scan Facts 定義為 canonical truth 的最低層。若 providers 各自輸出不同形狀，後續 mapping、risk、validation 會難以穩定。

## 前置需求
- Task 7-11 providers 已有初始實作。
- Task 5 secret masking 已可共用。
- Task 2 已有 models/schema 基礎。

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
1. 補齊 `src/kai_mind/core/models/scan.py`。
2. 建立 provider result interface。
3. 建立 `src/kai_mind/core/services/project_scan_service.py`。
4. 將 provider outputs normalize 成統一 facts/evidence/issues。
5. 加入 deterministic ordering，讓 snapshot 穩定。
6. 寫 integration test：basic fixture 產生 Docker/config/dependency/code facts。
7. 寫 partial failure test：malformed compose 仍有 facts output。

## 預期輸出
- `src/kai_mind/core/models/scan.py`
- `src/kai_mind/core/services/project_scan_service.py`
- `tests/unit/core/test_project_scan_service.py`

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
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ScanFact / Evidence       │
│ ParseIssue                │
└──────────────────────────┘
```
