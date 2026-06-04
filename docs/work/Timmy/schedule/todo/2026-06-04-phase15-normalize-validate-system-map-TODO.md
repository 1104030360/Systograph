# 2026-06-04 Phase 15 Normalize and Validate System Map TODO

## 目標

依照 `plan/unfinish/15-normalize-and-validate-system-map.md` 實作 canonical system map 組裝層，讓 Task 12 scan、Task 13 components、Task 14 endpoints / flows / risk hints 能被整理成 validated `RagSystemMap`。

## 實作邏輯

1. 先補測試，再補功能程式碼。
2. `SystemMapNormalizeService` 只組裝既有 upstream outputs，不重新掃描、不重新偵測、不重新推導 endpoint / risk / flow。
3. `recommended_next_checks` 使用 Python deterministic triggers 產生，穩定文案從 package-bundled TOML metadata catalog 讀取。
4. `SystemMapValidationService` 作最後守門，擋掉 dangling references、壞路徑、raw secret 與 contract drift。

## 步驟

1. 盤點既有 `RagSystemMap`、`ProjectScanResult`、`ComponentDetectionResult`、template、endpoint/risk/flow models。
2. 新增或擴充 catalog loader 測試，覆蓋 recommended next check TOML metadata。
3. 新增 normalizer unit tests，覆蓋空陣列、deterministic ordering、redacted project path、scan summary、recommended checks 條件式產生。
4. 擴充 validator tests，覆蓋 duplicate ids 與 `recommended_next_checks.target` cross-reference。
5. 實作 `recommended_next_check_rules.toml`、loader metadata model、`RecommendedNextCheckService`、`SystemMapNormalizeService`。
6. 更新 phase14 integration test，避免手刻 canonical map dict。
7. 執行相關測試與全量驗證，修正回歸。
8. 完成 report，確認 plan checklist 後移動 plan 到 `finish`。

## 驗證

- `.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py`
- `.venv/bin/python -m pytest tests/unit/core/test_system_map_validation.py`
- `.venv/bin/python -m pytest tests/unit/core/test_system_map_normalize_service.py`
- `.venv/bin/python -m pytest tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`
- `.venv/bin/python -m pytest`
