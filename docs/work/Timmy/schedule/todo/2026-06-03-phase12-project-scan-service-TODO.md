# 2026-06-03 Phase 12 Project Scan Service TODO

## 目標

實作 `ProjectScanService`，統一呼叫 filesystem、config、Docker Compose、dependency manifest、code pattern providers，將 provider-local `ProviderScanResult` 聚合成穩定、可追溯、可部分失敗的 raw scan result。

## 實作邏輯

1. 先用 TDD/BDD 補測試，鎖住 `ProjectScanService` 的對外行為。
2. 保留 provider 邊界：provider 只回傳 `ProviderScanResult`，service 只做 orchestration、merge、dedupe、排序、stage warnings。
3. Task 12 只輸出 raw facts/evidence/issues/skipped summary，不做 component detection、endpoint/risk/flow derivation，也不寫 artifacts。
4. 避免新增複雜 framework；用現有 Pydantic models、provider classes、fixtures 和測試風格完成最小可用聚合層。
5. 延續 Task 5 secret masking：aggregation 不重新暴露 full raw config value。

## 步驟

1. 補 `tests/unit/core/test_project_scan_service.py`：
   - service 會呼叫 filesystem provider 建立 inventory。
   - service 會整合 config / Docker / dependency / code pattern provider outputs。
   - 單一 provider 丟 exception 時，不讓整體 scan crash，保留其他 provider facts 並記錄 issue / warning。
   - 重複 facts 會合併 evidence，不覆蓋 evidence。
   - facts / evidence / issues / skipped files ordering deterministic。
   - service 不產生 component slot、endpoint、risk、flow final judgment。
2. 補 `tests/integration/test_phase12_project_scan_service_behaviors.py`：
   - 使用 fixture project 驗證 basic RAG 專案可產生 config / Docker / dependency / code pattern facts。
   - malformed compose/config 情境保留 partial output。
3. 實作或擴充 scanner models：
   - `ProjectScanResult`
   - provider stage warning / skipped summary 欄位。
4. 建立 `src/kai_mind/core/services/project_scan_service.py`：
   - default providers wiring。
   - provider dependency injection，方便測試。
   - provider exception isolation。
   - dedupe + evidence merge。
   - deterministic ordering。
5. 確認 Task 12a rule catalog failure 不被 service 靜默吞掉：
   - provider construction/catalog loading 失敗應明確報錯。
   - provider runtime parse failure 才轉成 partial issue。
6. 跑 RED 測試確認先失敗，再實作 GREEN。
7. 跑 full verification。
8. 建立 Phase 12 Report，記錄實作邏輯、步驟、測試方式、問題與解法、測試結果。
9. 逐一對照 `12-aggregate-raw-scan-facts.md` 驗收標準，確認全部落地。

## 驗證命令

```bash
.venv/bin/python -m pytest tests/unit/core/test_project_scan_service.py
.venv/bin/python -m pytest tests/integration/test_phase12_project_scan_service_behaviors.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 完成狀態

- [x] 建立 TODO 文件。
- [x] 先寫 Phase 12 unit tests 並確認 RED。
- [x] 先寫 Phase 12 integration tests 並確認 RED。
- [x] 實作 `ProjectScanResult` 與 `ProjectScanService`。
- [x] 實作 provider exception isolation。
- [x] 實作 dedupe + evidence merge。
- [x] 實作 deterministic ordering。
- [x] 保留 skipped files summary 與 inventory warnings。
- [x] 確認 Task 12 不做 component / endpoint / risk / flow final judgment。
- [x] 跑 full pytest、ruff、mypy。
- [x] 建立 Phase 12 Report。
- [x] 將完成的 plan 移到 `plan/finish`。
