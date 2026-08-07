# 2026-06-04 Phase 15 Normalize and Validate System Map REP

## 實作邏輯

本階段新增 canonical map assembly layer：

```text
Task 12 ProjectScanResult
Task 13 ComponentDetectionResult
Task 14 endpoints / flows / risk_hints
        ↓
SystemMapNormalizeService
        ↓
RecommendedNextCheckService
  Python deterministic triggers
  + recommended_next_check_rules.toml metadata
  + thin target resolver
        ↓
SystemMapValidationService
        ↓
validated RagSystemMap
```

分工原則：

- Normalizer 只組裝 upstream outputs，不重新掃描、不重新偵測、不重新推導 endpoint / risk / flow。
- `recommended_next_checks` 的 trigger 留在 Python，metadata 放 package-bundled TOML。
- `recommended_next_checks` 使用混合 target 策略：能 evidence-based 指到 component / endpoint / slot 時就指到具體 target，不能精準對應時才 fallback 到 system。
- 不做 `condition = "..."` TOML DSL。
- 不用 LLM 動態產生 canonical checks。
- Evidence path 錯誤不自動修正；交給 validator fail fast。

## 實作步驟

1. 建立 `docs/work/Timmy/schedule/todo/2026-06-04-phase15-normalize-validate-system-map-TODO.md`。
2. 先補 RED tests：
   - `tests/unit/core/test_rule_catalog_loader.py`
   - `tests/unit/core/test_system_map_validation.py`
   - `tests/unit/core/test_system_map_normalize_service.py`
3. RED 確認：
   - `SystemMapNormalizeService` 尚不存在，測試收集失敗。
4. 擴充 `RuleCatalogLoader`：
   - `RecommendedNextCheckRuleMetadata`
   - `load_recommended_next_check_rules()`
   - `load_default_recommended_next_check_rules()`
5. 新增 `src/systograph/core/rules/recommended_next_check_rules.toml`。
6. 新增 `src/systograph/core/services/system_map_normalize_service.py`：
   - `RecommendedNextCheckService`
   - `SystemMapNormalizeService`
   - `RecommendedCheckTarget`
   - deterministic sorting
   - scan summary assembly
   - project root redaction
   - explicit empty arrays
   - thin target resolver for component / endpoint / slot / system fallback
7. 補強 `SystemMapValidationService`：
   - duplicate ids fail fast
   - `recommended_next_checks.target` cross-reference validation
   - `target_type = "system"` fallback 支援2. validator 需要知道 target_type = "system"
   - 問題：recommended check metadata 預設 target 是整體系統，不是 component / endpoint / evidence。
8. 解法：在 SystemMapValidationService._validate_recommended_next_checks() 中明確允許 target_type="system" 且 target="system"。
   - fixture raw secret guard
9. 更新 phase14 integration test，改用 normalizer 建立 canonical map。
10. 將 plan 移到 `docs/work/Timmy/schedule/plan/finish/15-normalize-and-validate-system-map.md`。
11. `RecommendedNextCheckService` final target strategy：
    - `privacy_exposure` 能從 endpoint risk 透過 `endpoint.component_instance_id` 對應到 component；若 endpoint 沒有 component，fallback 到 endpoint。
    - `runtime_readiness` 對 endpoint 優先指向 component，missing runtime-critical slot 指向 `component_slot`。
    - `rag_knowledge_trust` 對 missing trust-critical slot 指向 `component_slot`。
    - file / evidence only privacy risk fallback 到 `system`，避免 heuristic 猜 component。
12. 用 `(check_id, target_type, target)` dedup，並讓 check id 包含 slugged target，避免 duplicate id。
13. 在 `recommended_next_check_rules.toml` 補註解，說明 `default_target_type` 只作為 Python target resolution 無法取得精準 target 時的 fallback。

## 測試方式

RED / targeted：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_rule_catalog_loader.py tests/unit/core/test_system_map_validation.py tests/unit/core/test_system_map_normalize_service.py
```

Phase 14 integration + contract：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/contracts/test_ai_system_map_schema.py
```

Full verification：

```bash
.venv/bin/ruff check src tests
.venv/bin/mypy src tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
```

Component-targeted next checks targeted：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_system_map_normalize_service.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/core/test_rule_catalog_loader.py tests/unit/core/test_system_map_validation.py tests/unit/core/test_system_map_normalize_service.py tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py tests/contracts/test_ai_system_map_schema.py
```

## 遇到的問題與解法

### 1. recommended next check 要不要 TOML condition DSL

問題：若把 trigger 寫成 TOML `condition = "..."`，會變成自製 DSL。

解法：只把 `id`、`default_target_type`、`reason`、`action` 放 TOML；trigger 留在 Python，和前一階段 risk hint metadata 外部化一致。

### 2. validator 需要支援 fallback `target_type = "system"`

問題：有些 recommended next checks 無法 evidence-based 對應到 component、endpoint、slot、risk、evidence、file、unmapped component 或 extension，需要合法的 system-level fallback target。

解法：在 `SystemMapValidationService._validate_recommended_next_checks()` 中明確允許 `target_type="system"` 且 `target="system"`，並同時保留 component / endpoint / slot 等具體 target 的 cross-reference validation。

### 3. phase14 integration 手刻 canonical map

問題：phase14 integration test 直接組 dict，會繞過 Task 15 normalizer，後續容易 contract drift。

解法：保留 phase14 endpoint/risk/flow assertions，但 map 建立改用 `SystemMapNormalizeService.normalize()`。

### 4. duplicate id 以前沒有 fail fast

問題：schema 無法保證 canonical collections 的 ids 唯一。

解法：validator 新增 duplicate id 檢查，覆蓋 evidence、component instances、endpoints、flows、edges、extensions、unmapped、detail scans、risk hints、recommended checks、query trace events。

### 5. recommended next checks 必須能貼到具體 target

問題：UI detail panel 需要知道某個 component / endpoint / slot 對應哪些下一步確認；若所有 recommended checks 都只指向 `system`，使用者無法從 component detail 直接看到相關建議。

解法：保留 service 只吃 typed data，不呼叫 detection service；在 `RecommendedNextCheckService` 內使用薄 target resolver：

```text
privacy endpoint risk
  -> endpoint.component_instance_id exists
  -> component_instance target

privacy endpoint risk
  -> endpoint.component_instance_id missing
  -> endpoint target

missing runtime / RAG trust slot
  -> component_slot target

file / evidence only risk
  -> system fallback
```

這樣避免把 endpoint detection、component detection、TOML metadata、UI 呈現揉在同一層，也避免沒有 evidence 的 component 猜測。

### 6. 同一 target 多個 privacy risk 會重複產生 check

問題：例如同一個 Chroma component 同時有 HTTP endpoint 與 local persistence 風險時，如果每個 risk 都產一個 `privacy_exposure` check，會造成重複建議或 duplicate id。

解法：用 `(check_id, target_type, target)` 當 aggregation key。多個 risk 指到同一 target 時，只產生一個 generic `privacy_exposure` check；TOML 的 `reason/action` 保持泛用文字，能涵蓋 data egress、published port、secret-like config、local persistence。

### 7. `default_target_type` 是 fallback metadata

問題：TOML metadata 只應提供文案與 fallback，不應決定所有 runtime target。實際 target type 由 Python resolver 根據 evidence-backed entities 動態決定。

解法：保留 `default_target_type` 欄位名稱，並在 TOML 補註解說明它只在 Python target resolver 無法找到更精準 target 時使用。這避免 schema / loader churn，也保留 TOML metadata 的簡單性。

## 測試結果

```text
.venv/bin/ruff check src tests
All checks passed!

.venv/bin/mypy src tests
Success: no issues found in 64 source files

PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
239 passed in 1.49s
```

## 驗收對照

- `SystemMapNormalizeService`：已完成。
- 補強既有 `SystemMapValidationService`：已完成。
- `recommended_next_check_rules.toml`：已完成。
- normalizer input 使用 typed upstream results：已完成。
- explicit top-level arrays：已完成。
- classification / project metadata / reference architecture：已完成。
- `project.root_path` redacted：已完成。
- `scan_summary`：已完成。
- deterministic ordering：已完成。
- duplicate id fail fast：已完成。
- recommended next checks 條件式產生：已完成。
- recommended next checks target-specific 產生：已完成，支援 component_instance / endpoint / component_slot / system fallback。
- endpoint risk 透過 `endpoint.component_instance_id` 對應 component：已完成。
- endpoint 無 component 時 fallback endpoint：已完成。
- missing slot 指向 `component_slot`：已完成。
- file / evidence only risk fallback system：已完成。
- `(check_id, target_type, target)` dedup：已完成。
- recommended check metadata TOML，不做 condition DSL：已完成。
- `default_target_type` 作為 fallback，而非唯一 target type：已完成。
- phase14 integration 不再手刻 canonical map dict：已完成。
- contract / unit / integration / full verification 通過：已完成。
