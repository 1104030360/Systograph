# 2026-06-04 Phase 14a Risk Hint Rule Metadata TOML REP

## 實作邏輯

本階段把 Task 14 的 risk hint metadata 抽到 bundled TOML catalog：

```text
RiskHintService
  -> trigger condition / target / evidence_id
  -> rule_id
  -> risk_hint_rules.toml metadata
  -> RiskHint
```

分工原則：

- Python service 保留 trigger logic、target selection、evidence selection。
- `risk_hint_rules.toml` 只保存 `rule_id`、`type`、`default_severity_hint`、`rationale`、`uncertainty`。
- 不實作 condition DSL。
- 不引入 external scanner engine。
- emitted `rule_id` 若找不到 metadata，直接 fail loudly。

## 實作步驟

1. 建立 `docs/work/Timmy/schedule/todo/2026-06-04-phase14a-risk-hint-rule-metadata-toml-TODO.md`。
2. 先補 `tests/unit/core/test_rule_catalog_loader.py`：
   - valid risk hint catalog loads metadata。
   - duplicate `rule_id` raises `RuleCatalogError`。
   - missing `rationale` / `uncertainty` raises `RuleCatalogError`。
   - bundled catalog covers Task 14 rule ids。
3. RED 確認：`RuleCatalogLoader` 尚無 `load_risk_hint_rules()` / `load_default_risk_hint_rules()`。
4. 擴充 `src/kai_mind/core/services/rule_catalog_loader.py`：
   - `RISK_HINT_RULE_CATALOG`
   - `RiskHintRuleMetadata`
   - `load_default_risk_hint_rules()`
   - `load_risk_hint_rules(path)`
5. 新增 `src/kai_mind/core/rules/risk_hint_rules.toml`，覆蓋：
   - `docker_published_port_exposure`
   - `external_provider_detected`
   - `config_parse_error`
   - `secret_like_config_key_detected`
   - `missing_required_slot`
   - `chroma_http_endpoint_detected`
   - `chroma_local_persistence_detected`
   - `chroma_server_published_port`
6. 先補 `tests/unit/core/test_risk_hint_service.py`：
   - emitted hints use catalog metadata。
   - unknown emitted `rule_id` fails loudly。
   - existing target / evidence behavior remains unchanged。
7. RED 確認：`RiskHintService` 尚無 `RiskHintMetadataError` 與 `rule_catalog_path` injection。
8. 重構 `src/kai_mind/core/services/risk_hint_service.py`：
   - 初始化時載入 risk metadata catalog。
   - 用 `rule_id` 取得 metadata 建立 `RiskHint`。
   - loopback published port 保留 Python override，維持 lower-risk wording。
   - missing required slot 保留 slot-specific rationale suffix。
9. 修正 mypy 指出的 `RiskHint.target_type` literal 型別，改用 `RiskTargetType`。

## 測試方式

RED / targeted：

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py -q
.venv/bin/python -m pytest tests/unit/core/test_risk_hint_service.py -q
```

Phase 14a + Task 14 regression：

```bash
.venv/bin/python -m pytest tests/unit/core/test_rule_catalog_loader.py tests/unit/core/test_risk_hint_service.py tests/unit/core/test_endpoint_detection_service.py tests/unit/core/test_flow_derivation_service.py tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 1. unknown emitted rule id 必須在 emit 時 fail

如果 custom catalog 缺少 `missing_required_slot`，service 初始化仍可成功，因為 catalog 不知道本次 scan 會 emit 哪些 hints。

解法：`RiskHintService._metadata(rule_id)` 在實際建立 hint 時檢查 metadata 是否存在；缺少就 raise `RiskHintMetadataError`。

### 2. loopback published port 需要保留 Python override

`docker_published_port_exposure` 的一般 metadata 來自 TOML，但 loopback binding 需要 lower-risk wording 和 severity。

解法：trigger 判斷仍留在 Python；只有 metadata default 放 TOML。loopback 時覆寫 `rationale` / `severity_hint`，`uncertainty` 仍可沿用 catalog。

### 3. mypy target_type literal

重構 `_risk_hint()` helper 時，`target_type` 初版使用 `str`，mypy 無法保證符合 `RiskHint` contract。

解法：改成 `RiskTargetType` literal。

## 測試結果

```text
.venv/bin/python -m pytest
222 passed in 1.77s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy
Success: no issues found in 62 source files
```

## 驗收對照

- 新增 `risk_hint_rules.toml`：已完成。
- 擴充 `RuleCatalogLoader.load_risk_hint_rules()`：已完成。
- 定義 `RiskHintRuleMetadata`：已完成。
- `RiskHintService` 透過 `rule_id` 讀取 metadata：已完成。
- metadata 必含 `rule_id` / `type` / `default_severity_hint` / `rationale` / `uncertainty`：已完成，unit tests 覆蓋。
- duplicate `rule_id` fail fast：已完成。
- missing required fields fail fast：已完成。
- unknown emitted `rule_id` fails loudly：已完成。
- trigger condition 不進 TOML：已遵守。
- existing Task 14 behavior 不變：已用 targeted tests 與 integration validation 確認。
- Full verification 通過：已完成。
