# Task 23: Hardening Cross-platform Paths, Logging, and Snapshot Safety

## 目標
補強 Epic 1 backend 的 cross-platform path、structured logging、snapshot secret safety、target validation 與 release-readiness review gaps。這是 baseline 功能完成後的品質收斂任務。

## 為什麼要先做這個
設計文件與 AGENTS.md 都要求 Windows/macOS path、secret-safe snapshots、scanner tests、evidence-based findings。功能完成後若不做 hardening，很容易在 review 時出現 P1。

## 前置需求
- Task 16 已完成 end-to-end map build。
- Task 21/22 已完成 progressive scan/query trace。
- Task 5 secret masking 已全域接入。

## 實作範圍
- Cross-platform path tests。
- Snapshot secret scanner。
- Structured logging events。
- Provider failure structured warnings。
- Validation hardening：dangling references、invalid target、unmasked secret pattern。
- Docs update：開發命令與 known limitations。

## 不包含範圍
- 不新增大型 feature。
- 不改 JSON schema breaking fields，除非另有 migration note。
- 不做 full security scanner。
- 不做 packaging/launcher。

## 建議實作步驟
1. 建立 cross-platform path fixtures。
2. 補測 Windows-style input -> POSIX evidence path。
3. 建立 snapshot scanner helper，掃描 JSON/Markdown snapshot 是否含 fake full secret。
4. 加入 structured logging wrapper 或 helper。
5. 確認 logs 不輸出 full secret。
6. 補 target validation tests。
7. 更新 docs 或 README 的 backend test commands。

## 預期輸出
- `tests/contracts/test_secret_snapshot_safety.py`
- `tests/core/test_cross_platform_paths.py`
- `src/kai_mind/core/services/logging_service.py` 或等價 helper
- 更新相關 tests/docs

## 驗收標準
- Windows/macOS path tests 通過。
- snapshot scanner 可抓到故意放入的 fake full secret。
- logs 只記錄 stage/count/id，不記錄 raw values。
- release-readiness review 沒有 scanner test gap。

## 可能風險與注意事項
- 不要在 hardening task 順手重構所有 services。
- 若發現 schema 需要 breaking change，必須記錄 migration。
- 這一步主要是補防線，不是加產品功能。

## 新手提示
Hardening 是把已經能跑的功能變成比較不容易壞、比較不容易洩密、比較能跨平台工作的版本。

## 視覺化說明
```text
┌──────────────────────┐
│ Working baseline      │
└──────┬──────┬────────┘
       │      │
       ↓      ↓
┌──────────────┐ ┌──────────────────────┐
│ Path tests   │ │ Secret snapshot scan  │
└──────┬───────┘ └──────────┬───────────┘
       │                    │
       ↓                    ↓
┌──────────────┐ ┌──────────────────────┐
│ Structured   │ │ Validation hardening  │
│ logs         │ │                      │
└──────┬───────┘ └──────────┬───────────┘
       └──────────┬─────────┘
                  ↓
┌──────────────────────┐
│ Release-ready         │
│ Epic 1 backend        │
└──────────────────────┘
```
