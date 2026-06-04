# 2026-06-04 Phase 14a Risk Hint Rule Metadata TOML TODO

## 目標

把 Task 14 中可安全外部化的 risk hint metadata 抽到 `risk_hint_rules.toml`，讓 `RiskHintService` 保留 trigger / target / evidence 選擇邏輯，但不再散落 rule type、default severity、rationale、uncertainty 文案。

## 實作邏輯

1. 使用 TDD + BDD：先寫 catalog loader 與 service 行為測試，確認 RED 後才改 production code。
2. 不建立 condition DSL：TOML 只放 metadata，不放 trigger condition / expression parser。
3. 保留 typed Python trigger：`RiskHintService` 仍負責判斷何時 emit hint、target 指向哪裡、evidence_id 是否 valid。
4. Fail fast：catalog duplicate rule id、missing required metadata、unknown emitted rule id 都要直接失敗。
5. Secret safety：catalog 只放固定 wording，不包含 runtime value 或 raw secret。

## 步驟

1. 補 `tests/unit/core/test_rule_catalog_loader.py`：
   - valid risk hint catalog loads metadata。
   - duplicate `rule_id` raises `RuleCatalogError`。
   - missing `rationale` / `uncertainty` raises `RuleCatalogError`。
   - bundled `risk_hint_rules.toml` 覆蓋 Task 14 emitted rule ids。
2. 補 `tests/unit/core/test_risk_hint_service.py`：
   - emitted hints 使用 catalog metadata。
   - unknown emitted `rule_id` fail loudly。
   - loopback published port 仍可由 Python trigger override severity/rationale。
   - target / evidence 行為維持 Task 14 不變。
3. 新增 `src/kai_mind/core/rules/risk_hint_rules.toml`。
4. 擴充 `RuleCatalogLoader`：
   - `RiskHintRuleMetadata` dataclass。
   - `load_default_risk_hint_rules()`。
   - `load_risk_hint_rules(path)`。
5. 重構 `RiskHintService`：
   - 初始化時載入 risk metadata catalog。
   - 使用 `rule_id` 取 metadata 建立 `RiskHint`。
   - 保留特殊情境的 Python override，例如 loopback published port severity / wording。
6. 跑 targeted tests。
7. 跑 full verification。
8. 建立 Phase 14a Report。
9. 逐一對照 Task 14a plan，確認完成後將 plan 移到 `plan/finish`。

## 驗證命令

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py
.venv/bin/python -m pytest tests/unit/core/test_risk_hint_service.py
.venv/bin/python -m pytest tests/unit/core/test_endpoint_detection_service.py tests/unit/core/test_flow_derivation_service.py tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 完成狀態

- [x] 建立 TODO 文件。
- [x] 先寫 risk hint catalog loader tests 並確認 RED。
- [x] 實作 `RiskHintRuleMetadata` 與 `load_risk_hint_rules()`。
- [x] 新增 `risk_hint_rules.toml` 並覆蓋 Task 14 rule ids。
- [x] 先寫 RiskHintService catalog usage tests 並確認 RED。
- [x] 重構 `RiskHintService` 使用 catalog metadata。
- [x] 確認 target / evidence behavior 不變。
- [x] 跑 full pytest、ruff、mypy。
- [x] 建立 Phase 14a Report。
- [x] 將完成的 plan 移到 `plan/finish`。
