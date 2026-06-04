# Task 14a: Extract Risk Hint Rule Metadata to TOML

## 目標
在 Task 14 的 `EndpointDetectionService` / `RiskHintService` 穩定後，把可安全外部化的 risk rule metadata 抽到 `risk_hint_rules.toml`，降低 Python service 內的重複文字與 metadata hard code。

此任務不是重寫 Task 14，也不是建立完整 rule engine。它只把 rule metadata 外部化，觸發條件仍保留在 typed Python code。

## 為什麼要做這個
Task 14 的 MVP 應先用 deterministic Python rules 打通 endpoint / risk / flow derivation。等規則穩定後，`rule_id`、`type`、`severity_hint`、`rationale`、`uncertainty` 這些文字型 metadata 會開始重複，適合抽成 catalog。

這樣可以：
- 讓 rule wording 更集中。
- 讓測試可以驗證所有 rule metadata 都存在且完整。
- 避免 `RiskHintService` 同時承擔 rule trigger logic 與大量文案管理。
- 保留未來 rule registry / policy set 演進空間。

## 前置需求
- Task 14 已完成並通過測試。
- `RiskHintService` 已有穩定的 deterministic rule functions。
- 初始 generic rules 與 Chroma-specific rules 的 `rule_id` 已固定。
- `RiskHint` canonical contract 已由 `SystemMapValidationService` 驗證。

## 實作範圍
- 新增 `src/kai_mind/core/rules/risk_hint_rules.toml`。
- 擴充 `RuleCatalogLoader`，新增 `load_risk_hint_rules()`。
- 定義 `RiskHintRuleMetadata` model / dataclass。
- 讓 `RiskHintService` 透過 `rule_id` 讀取 metadata。
- 驗證每條 rule metadata 必須包含：
  - `rule_id`
  - `type`
  - `default_severity_hint`
  - `rationale`
  - `uncertainty`
- 補 unit tests，確認 metadata catalog malformed / missing field / duplicate rule id 會被拒絕。

## 不包含範圍
- 不把 trigger condition 寫成 TOML DSL。
- 不支援 `condition = "A AND B"` 這類 expression parser。
- 不引入 OPA/Rego、Semgrep engine、Checkov engine、Bandit engine。
- 不允許外部 rule catalog 直接繞過 `RiskHint.target` / `evidence_id` validation。
- 不讓非 deterministic AI 生成 risk hint。

## 建議 TOML 形狀
```toml
[[risk_hints]]
rule_id = "docker_published_port_exposure"
type = "network_exposure"
default_severity_hint = "high"
rationale = "A Docker service publishes a port on the host and may be reachable outside the container boundary."
uncertainty = "Static scan does not verify runtime reachability, firewall rules, or host network exposure."

[[risk_hints]]
rule_id = "external_provider_detected"
type = "external_provider"
default_severity_hint = "medium"
rationale = "An external provider component was detected and may receive prompts, embeddings, retrieved context, or outputs."
uncertainty = "Static scan does not verify runtime egress policy, provider settings, or data handling controls."
```

## Python 分工
```text
RiskHintService
  owns:
    - trigger condition
    - target selection
    - evidence_id selection
    - component / endpoint / slot cross-reference safety

risk_hint_rules.toml
  owns:
    - rule_id metadata
    - type
    - default severity
    - rationale template
    - uncertainty template
```

## 驗收標準
- `RiskHintService` 不再散落重複 rationale / uncertainty 字串。
- 每個 emitted `RiskHint.rule_id` 都能在 `risk_hint_rules.toml` 找到 metadata。
- metadata catalog duplicate `rule_id` 會 fail fast。
- metadata catalog missing required fields 會 fail fast。
- existing Task 14 behavior 不變。
- `SystemMapValidationService` 仍能拒絕 missing evidence refs、dangling targets、invalid risk targets。

## 測試建議
- `tests/unit/core/test_rule_catalog_loader.py`
  - valid `risk_hint_rules.toml` loads metadata。
  - duplicate `rule_id` raises error。
  - missing `rationale` / `uncertainty` raises error。
- `tests/unit/core/test_risk_hint_service.py`
  - emitted hints use catalog metadata。
  - unknown emitted `rule_id` fails loudly。
  - target / evidence behavior unchanged from Task 14。

## 可能風險與注意事項
- 不要把 TOML metadata 抽離誤解成「所有邏輯都外部化」。
- 不要為了抽 TOML 發明 expression language；那會變成另一個 rule engine task。
- 不要讓 catalog wording 包含 raw secret values。
- `rationale` / `uncertainty` 若需要 provider-specific wording，優先用不同 `rule_id` 或 small Python template variables，不要在 TOML 內放複雜條件。

## 外部參考
- Semgrep rules 可用 YAML 描述 pattern / message / severity，但它有完整 engine 支援 rule syntax：https://semgrep.dev/docs/writing-rules/overview
- Checkov custom policies 可用 Python 或 YAML，複雜邏輯不一定只靠 YAML：https://www.checkov.io/3.Custom%20Policies/Custom%20Policies%20Overview.html
- Bandit detection logic 以 Python AST plugins 為主，config 可放在 `pyproject.toml`：https://bandit.readthedocs.io/en/latest/

## 視覺化說明
```text
Task 14 stable Python rules
        │
        ↓
find repeated metadata
        │
        ↓
┌─────────────────────┐       ┌────────────────────────┐
│ RiskHintService      │       │ risk_hint_rules.toml    │
│ trigger / target /   │──────▶│ type / severity /       │
│ evidence selection   │       │ rationale / uncertainty │
└──────────┬──────────┘       └────────────────────────┘
           │
           ↓
     emitted RiskHint
           │
           ↓
SystemMapValidationService
```
