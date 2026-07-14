# Profile Presentation Metadata 遷移至 TOML Catalog 實作計畫

Status: completed（2026-07-14；TDD/BDD、runtime QA、full regression 與文件已驗收）

> **執行者注意：** 使用 TDD，逐 task 執行並保留 checkbox。若使用 Superpowers，請用
> `superpowers:executing-plans` 在同一工作階段逐項完成；本計畫不要求 subagent。

**目標：** 將目前混在 Python `profile_registry.py` 的 presentation metadata 搬到
package-bundled `profile_registry.toml`，同時把 executable profile definitions 留在 Python；
建立 deterministic、read-only `profile_registry.json` projection contract，但不增加新的
public API 或 per-build artifact。

**架構：** TOML 是唯一 hand-authored profile presentation metadata source。Python 是
profile ids、required nodes、wiring gates、status、activation、evidence strength、coverage、
depth、scope 與 related refs 的唯一 executable source。JSON 只能由 validated TOML
deterministically 產生，Profile Engine 不得讀回 JSON。

**Tech Stack：** Python 3.11、Pydantic v2、`tomllib`、package resources、pytest、
JSON Schema Draft 2020-12、Ruff、mypy。

## Global Constraints

- Scanner 對 target repo read-only；不得從 target repo、remote URL 或 environment override 載入 catalog。
- Active contract 仍是 exactly 15 profiles；本計畫不增刪或 rename profile ids。
- TOML unknown/missing/duplicate fields fail closed，不使用隱藏 fallback metadata。
- `default_evidence_strength` 不進 TOML；evidence strength 必須由實際 status/evidence 計算。
- JSON projection 不成為 authoring source、runtime rule input 或新的 build sibling artifact。
- 所有行為改動先寫 failing test，再做最小實作。

---

## 1. 文件用途與執行 gate

| 項目 | 內容 |
|---|---|
| Audience | Backend implementer、catalog editor、schema/API reviewer |
| 前置條件 | Plan 02 Profile Engine 已完成；Plan 10 boundary/guardrails 已完成 |
| 完成期限 | Plan 14 real-world validation 前 |
| 後續生命週期 | Plan 18 保留 `profile_registry.toml`；不因 UA-primary 切換而退役 |
| Last verified | 2026-07-14，依目前 code、tests、Plan 10/14/16/18 與 MODEL-CONTRACT |

```text
Plan 02                 Plan 10                    Plan 11                    Plan 14
------------------      ----------------------     -----------------------    ------------------
Profile behavior     -> 鎖定 ownership/guards  -> 搬 presentation metadata -> real-world validate
已在 Python             不建立 profile TOML       Python rules 不變

Plan 16 / UA-primary --------------------------------------------------------------+
                                                                                   |
Plan 18 retirement：只退 Step 3 matching providers；profile_registry.toml 保留 <---+
```

## 2. 目前真實狀態與本計畫要修正的問題

| 觀察 | 影響 | 本計畫做法 |
|---|---|---|
| `profile_registry.py` 混合 label/axis 與 required nodes/relationship | metadata 與 executable rule 同名且難以審查 | 分成 `profile_rule_definitions.py` 與 TOML loader |
| `ProfileInferenceService`、52 assessments、15 profiles 已完成 | 舊版「02 預計建立」敘述過時 | 先寫 characterization tests，不重做 service |
| `ProfileFindingService` 在 Python 組 label、uncertainty、next checks | presentation wording 無單一 catalog owner | 由 metadata registry 注入 finding service |
| `profile_finding_rules.evidence_strength()` 依 status/direct evidence 計算 | evidence strength 是 executable output semantics | 永遠留在 Python，不設 TOML default |
| 舊版 loader 範例允許 axis fields，卻未把它們放入 dataclass/constructor | 範例本身無法正確實作 | dedicated typed loader，一次定義完整 allowlist |
| 舊版用 raw substring 搜尋 forbidden fields/method names | 文案可能誤命中，method rename 會脆弱 | parse TOML keys、測試行為與 dependency graph |
| 舊版宣稱 frontend 不依賴固定 profile count | 與 active model exactly 15 profiles 不完整對齊 | backend contract 維持 15；frontend 不複製 ids/order |

## 3. Target architecture

```text
                         HAND-AUTHORED                         EXECUTABLE
                    +----------------------+          +--------------------------+
                    | profile_registry.toml|          | profile_rule_definitions |
                    | labels / axes / text |          | ids / nodes / wiring     |
                    +----------+-----------+          +------------+-------------+
                               |                                   |
                               v                                   v
                    +----------------------+          +--------------------------+
                    | ProfileRegistryLoader|          | profile_finding_rules    |
                    | strict + fail closed |          | status/depth/evidence    |
                    +----------+-----------+          +------------+-------------+
                               |                                   |
                               +---------------+-------------------+
                                               v
                                  +---------------------------+
                                  | ProfileFindingService     |
                                  | deterministic aggregation |
                                  +-------------+-------------+
                                                |
                         +----------------------+----------------------+
                         |                                             |
                         v                                             v
              profile_signals.json                           profile_registry.json
              assessment truth                              read-only projection
              engine output                                 engine never reads it
```

### 3.1 File responsibility map

| File | 單一責任 |
|---|---|
| `profile_rule_definitions.py` | active profile ids、required node ids、required relationship |
| `profile_registry.toml` | labels、description、axes、display order、default wording |
| `profile_registry_loader.py` | strict TOML parsing、typed metadata、coverage validation |
| `profile_finding_rules.py` | status、depth、activation、evidence strength |
| `profile_finding_service.py` | 合併 rule definitions、metadata 與 assessments |
| `profile_registry.py` | 遷移完成後刪除；不得留 compatibility shim 或第二份 metadata |
| `profile_registry_projection.py` | read-only projection models 與 schema builder |
| `profile_registry_projection_service.py` | validated registry → deterministic projection |

## 4. Catalog contract

### 4.1 唯一允許的 fields

```toml
schema_version = "profile-registry/v1"

[[profiles]]
profile_id = "reranking"
display_name = "Reranking"
short_label = "Reranking"
description = "Evidence shows a reranker participates in retrieval ordering."
primary_axis = "retrieval_strategy"
secondary_axes = []
display_order = 60
default_uncertainty = "Static evidence only; runtime ordering is not confirmed."
recommended_next_checks = [
  "Review the runtime path that invokes the reranker.",
]
```

Allowed root key：

- `schema_version`，固定為 `profile-registry/v1`。
- `profiles` array of tables。

Allowed `[[profiles]]` keys：

- `profile_id`
- `display_name`
- `short_label`
- `description`
- `primary_axis`
- `secondary_axes`
- `display_order`
- `default_uncertainty`
- `recommended_next_checks`

`display_order` 必須為 unique non-negative integer。`primary_axis` / `secondary_axes` 必須是
`ProfileAxis` 合法值；secondary 不得重複或再包含 primary。

### 4.2 明確禁止的 fields

- `default_evidence_strength`
- `condition`、regex、threshold、score、weight
- `status_weight`、`mapping_completeness_weight`
- `activation_condition`、`coverage_gate`、`conflict_precedence`
- `allowed_evidence_kinds`、`related_rule_ids`
- `required_node_ids`、`required_relationship`
- `requires_slot`、`requires_extension`、`requires_capability_candidate`
- `prompt`、`provider`、model、endpoint
- `mapping_type`、`accept_action`、edit/reject lifecycle
- graph/call graph/dataflow/execution mapping fields

Unknown fields 一律由 parsed-key allowlist 拒絕；不要用 raw text substring 搜尋代替 schema validation。

### 4.3 Active profile ids

Catalog 必須精確覆蓋下列 15 個 ids，不能缺少或多出：

```text
rag-grounding             agentic-control           tool-calling
memory                    workflow-orchestration    hybrid-retrieval
reranking                 corrective-retrieval      self-reflection
graph-retrieval           hierarchical-retrieval    contextual-retrieval
multimodal-grounding      modular-composition       multi-query-retrieval
```

目前仍使用 `reranker` 的舊 fixture/example 必須改成 profile id `reranking`；`reranker` 只可作
reference node / observed kind，不是 top-level profile id。

## 5. Runtime semantic boundary

### 5.1 Python rule definition

```python
@dataclass(frozen=True, slots=True)
class ProfileRuleDefinition:
    profile_id: str
    required_node_ids: tuple[str, ...]
    required_relationship: str | None = None
```

這個型別不能包含 label、description、display order 或文案。

### 5.2 Metadata loader interface

```python
class ProfileRegistryLoader:
    def load_default(self) -> ProfileMetadataRegistry: ...
    def load(self, catalog_path: Path) -> ProfileMetadataRegistry: ...
```

- `load_default()` 只用 `importlib.resources` 讀 package-bundled TOML。
- `load(path)` 只供 tests 或明確的 KAI-Mind-owned admin tooling；不得接 target repo path、API body 或 scan config。
- Loader 完成後立刻驗證 catalog id set 等於 `MVP_CAPABILITY_PROFILE_IDS`。

### 5.3 Error taxonomy

```python
class ProfileRegistryError(ValueError): ...

class ProfileMetadataCoverageError(ProfileRegistryError): ...
```

| Error | 觸發情境 |
|---|---|
| `ProfileRegistryError` | malformed TOML、unknown/missing field、invalid type/axis/version、duplicate id/order |
| `ProfileMetadataCoverageError` | catalog ids 與 active Python profile ids 不相等 |

不要重用描述 scan provider catalogs 的 `RuleCatalogError`，也不要再增加
`ProfileRuleCatalogError` / `ProfileRuleMetadataError` 等重疊名稱。

### 5.4 Finding 組裝規則

- `profile_id`、required nodes、wiring：來自 Python `ProfileRuleDefinition`。
- label、primary axis：來自 validated metadata。
- status、depth、activation、coverage、evidence strength：全部由 Python 計算。
- Python status rule 已產生具體 uncertainty reason 時保留；回傳 `None` 時，才使用 catalog
  `default_uncertainty`，例如 detected 但 runtime path 未驗證的限制文案。
- `detected` / `not_detected` 的 `recommended_next_checks` 維持空集合；
  `partial` / `undetermined` / `conflicted` 才可使用 catalog default，Python 可用更具體內容覆寫。
- 缺 metadata fail closed，不產生部分 profile list。

## 6. Read-only JSON projection contract

`profile_registry.json` 是 consumer projection，不是 build assessment truth：

```json
{
  "schema_version": "profile-registry/v1",
  "profiles": [
    {
      "profile_id": "reranking",
      "display_name": "Reranking",
      "short_label": "Reranking",
      "description": "...",
      "primary_axis": "retrieval_strategy",
      "secondary_axes": [],
      "display_order": 60,
      "default_uncertainty": "...",
      "recommended_next_checks": []
    }
  ]
}
```

規則：

- 由 `ProfileRegistryProjectionService.project()` 從 validated registry 產生。
- 依 `display_order` deterministic 排序，JSON serialization 使用 stable key ordering。
- 通過 `schemas/profile-registry.v1.schema.json`。
- Checked-in schema 必須等於 Pydantic `build_profile_registry_schema()` 的輸出。
- Projection 不包含 status、evidence、threshold、required nodes、wiring、rule ids 或 provider config。
- Plan 11 只建立 projection model/service/schema；不新增 API route，不把 JSON 寫進 target repo，
  也不重複寫入每個 build。未來 consumer owner 要發布時，必須另行更新 MODEL-CONTRACT/API。

## 7. UA 與 Plan 18 對照

```text
UA 接手前：KAI matching providers -> ScanFact -> Profile Engine -> profile metadata
UA 接手後：UA + adapter           -> ScanFact -> Profile Engine -> profile metadata
                                               ^                 ^
                                               |                 |
                                         Python semantics   TOML presentation
```

- Plan 18 退役 `code_pattern`、`dependency_manifest`、`docker_image` 與 config patterns 的
  default Step 3 ownership。
- `profile_registry.toml` 不掃 repo、不 emit `ScanFact`，因此是 Plan 18 明確保留項。
- Plan 11 不修改 Plan 16、Plan 18、`ProjectScanService` 或 UA adapter。

## 8. 範圍

### 包含

- 嚴格 metadata TOML 與 dedicated loader。
- Python executable definitions / presentation metadata 分檔。
- `ProfileFindingService` metadata injection。
- deterministic JSON projection model/service/schema。
- fail-closed、coverage、round-trip、freshness 與 architecture boundary tests。
- canonical docs 同步。

### 不包含

- 不改五態、activation、coverage、depth、evidence strength 或 Mapping Completeness。
- 不新增/刪除/rename active profile ids。
- 不新增 LLM、provider、prompt 或 mapping lifecycle。
- 不新增 public API、frontend 欄位或 per-build `profile_registry.json` artifact。
- 不退役 scan providers；那是 Plan 18。
- 不把 `capability_reference_map.toml` 的 52 nodes 複製進 profile catalog。

## 9. 實作 Tasks

### Task 1：先建立 characterization 與 failing loader tests

**Files**

- Create: `tests/unit/core/test_profile_registry_loader.py`
- Create: `tests/unit/core/test_profile_metadata_runtime.py`
- Modify: `tests/unit/core/test_profile_inference_service.py`
- Modify: `tests/unit/core/test_profile_inference_boundaries.py`

**Produces**

- 固定目前 15 ids、ProfileFinding order、status/depth/evidence strength 行為。
- Loader 在 source 尚未建立時先紅燈。

- [x] Characterize 15 profile ids 與 existing fixtures 的 profile status，不把 metadata migration 寫成行為變更。
- [x] 新增 valid catalog、malformed TOML、unknown field、missing field、duplicate id/order、invalid axis/version tests。
- [x] 新增 exact coverage test：catalog id set 必須等於 Python active id set。
- [x] 先執行 focused tests，確認 loader tests 因 module/API 尚不存在而失敗；記錄預期 failure。

```bash
uv run pytest tests/unit/core/test_profile_registry_loader.py -q
uv run pytest tests/unit/core/test_profile_inference_service.py -q
```

### Task 2：分離 executable profile definitions

**Files**

- Create: `src/kai_mind/core/services/profile_rule_definitions.py`
- Modify: `src/kai_mind/core/services/profile_finding_service.py`
- Modify: `src/kai_mind/core/services/profile_inference_service.py`
- Modify: `src/kai_mind/core/services/profile_signal_validation_service.py`
- Delete after callers migrate: `src/kai_mind/core/services/profile_registry.py`
- Test: existing profile tests

**Produces**

- `ProfileRuleDefinition`
- `PROFILE_RULE_DEFINITIONS`
- `MVP_CAPABILITY_PROFILE_IDS`

- [x] 只搬 `profile_id`、`required_node_ids`、`required_relationship` 到新檔案。
- [x] label、axis 不留在 rule definition。
- [x] 更新所有 imports；`rg` 確認沒有 runtime caller 使用舊 module 後才刪除。
- [x] 跑既有 profile tests，結果必須與 characterization 完全一致。

```bash
uv run pytest \
  tests/unit/core/test_profile_inference_service.py \
  tests/unit/core/test_profile_signal_validation_service.py \
  tests/unit/core/test_profile_inference_boundaries.py -q
```

### Task 3：實作 strict TOML loader 與 package catalog

**Files**

- Create: `src/kai_mind/core/rules/profile_registry.toml`
- Create: `src/kai_mind/core/services/profile_registry_loader.py`
- Modify: `tests/unit/core/test_profile_registry_loader.py`

**Produces**

- `ProfileMetadataEntry`
- `ProfileMetadataRegistry`
- `ProfileRegistryLoader`
- `ProfileRegistryError`
- `ProfileMetadataCoverageError`

- [x] 依第 4 節建立 15 筆 metadata；不加入第 4.2 節禁止欄位。
- [x] Loader reject unknown root/table fields、invalid types、empty required strings、duplicate ids/order。
- [x] 驗證 axes、display order、schema version 與 exact active-id coverage。
- [x] `load_default()` 只讀 package resource；invalid/missing catalog fail closed。
- [x] 不修改 `RuleCatalogLoader`；profile metadata 不是 scan provider rule catalog。

```bash
uv run pytest tests/unit/core/test_profile_registry_loader.py -q
```

### Task 4：將 metadata 注入 ProfileFindingService

**Files**

- Modify: `src/kai_mind/core/services/profile_finding_service.py`
- Create: `src/kai_mind/core/services/profile_finding_assembler.py`
- Modify: `src/kai_mind/core/services/profile_inference_service.py`（只有 default wiring 必要時）
- Create: `tests/unit/core/test_profile_metadata_runtime.py`
- Modify: `tests/unit/core/test_profile_inference_boundaries.py`

**Consumes**

- `PROFILE_RULE_DEFINITIONS`
- `ProfileMetadataRegistry`

**Produces**

- 相同的 15 筆 deterministic `ProfileFinding`，但 presentation metadata 來自 TOML。

- [x] `ProfileFindingService` constructor 接受 typed metadata registry；default 使用 package registry。
- [x] Service 以 instance registry 協調；finding aggregation 抽成 pure assembler，分別接收 rule definition 與 metadata。
- [x] label/axis/default wording 從 metadata 取得。
- [x] status/depth/activation/evidence strength/coverage/related refs 仍走既有 Python functions。
- [x] 新增 custom metadata injection test，證明只改文案不改 status、evidence、depth。
- [x] Missing metadata 在 inference 前 raise `ProfileMetadataCoverageError`，不輸出 partial result。

```bash
uv run pytest tests/unit/core/test_profile_inference_service.py -q
uv run pytest tests/unit/core/test_profile_inference_boundaries.py -q
```

### Task 5：建立 deterministic JSON projection 與 schema

**Files**

- Create: `src/kai_mind/core/models/profile_registry_projection.py`
- Create: `src/kai_mind/core/services/profile_registry_projection_service.py`
- Create: `schemas/profile-registry.v1.schema.json`
- Create: `tests/contracts/test_profile_registry_schema.py`
- Create: `tests/unit/core/test_profile_registry_projection_service.py`

**Produces**

- `ProfileRegistryProjection`
- `build_profile_registry_schema()`
- `ProfileRegistryProjectionService.project()`

- [x] Projection 只含第 6 節 fields，依 `display_order` deterministic 排序。
- [x] Contract test 驗證 checked-in schema 等於 Pydantic generated schema。
- [x] Round-trip semantic test 比較 TOML typed registry 與 JSON projection，不做 JSON → runtime registry loader。
- [x] 寫入 temp path 做 real serialization/schema validation；不新增 public route 或 build artifact。
- [x] Source guard 確認 projection model/service 不 import scanner、mapping、LLM 或 web modules。

```bash
uv run pytest tests/contracts/test_profile_registry_schema.py -q
uv run pytest tests/unit/core/test_profile_registry_projection_service.py -q
```

### Task 6：補齊 boundary、docs 與 migration checks

**Files**

- Modify: `tests/unit/core/test_profile_inference_boundaries.py`
- Modify: `docs/MODEL-CONTRACT.md`
- Modify: `docs/design/epic1-phase2.md`
- Modify: `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md`
- Modify: Plan 10 與本計畫

- [x] Parse TOML 並 assert exact allowed key set；不要掃 raw substrings。
- [x] Re-run Plan 10 direct/transitive forbidden dependency guard。
- [x] Docs 寫明 `profile_registry.py` 已拆成 Python rules + TOML metadata。
- [x] Docs 寫明 active contract 仍為 15 profiles，frontend 不得複製 ids/order。
- [x] Docs 寫明 JSON 是 read-only projection，沒有新 public artifact/API。
- [x] Docs 保留 Plan 18 lifecycle 對照與 source links。

### 實作備註（2026-07-14）

- RED 已觀察：loader module 缺失、constructor injection 缺失、projection module 缺失。
- GREEN 已觀察：59 個 profile-focused tests、Ruff、Mypy 與 no-excuse rules 全數通過。
- 為符合 250 行限制，`ProfileFindingService` 保留 orchestration，deterministic aggregation
  移到 pure `profile_finding_assembler.py`；這不改 public constructor 或 finding contract。
- `scripts/`、web、CLI、frontend 與 `BuildArtifactPublisher` usage inventory 均無 projection
  consumer，因此沒有加入不必要的 script、route 或 artifact wiring。

## 10. 驗收標準

- [x] `profile_registry.toml` 存在且精確覆蓋 15 active profile ids。
- [x] Python executable definitions 不含 presentation metadata；TOML 不含 executable fields。
- [x] `default_evidence_strength` 不在 TOML，evidence strength 仍由 Python evidence 計算。
- [x] Loader 對 malformed/unknown/missing/duplicate/version/axis/coverage 錯誤 fail closed。
- [x] Metadata migration 不改任何 existing fixture 的 status、depth、evidence ids/strength、coverage 或 Mapping Completeness。
- [x] Missing metadata 不產生 partial profile results。
- [x] JSON projection deterministic、schema-valid，且 semantic content 等於 typed TOML registry。
- [x] Engine 不讀 JSON；Plan 11 不增加 API、frontend 欄位或 per-build artifact。
- [x] Profile path 仍不依賴 mapping/manual/LLM/web，包含 indirect imports。
- [x] `profile_registry.toml` 明確列為 Plan 18 retained metadata catalog。

## 11. 完整驗證

```bash
uv run pytest \
  tests/unit/core/test_profile_registry_loader.py \
  tests/unit/core/test_profile_registry_projection_service.py \
  tests/unit/core/test_profile_inference_service.py \
  tests/unit/core/test_profile_inference_boundaries.py \
  tests/unit/core/test_profile_signal_validation_service.py \
  tests/unit/core/test_profile_signal_models.py \
  tests/contracts/test_profile_registry_schema.py -q
uv run pytest
uv run ruff check src tests
uv run mypy
uv run kai-mind --help
git diff --check \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-b-profile-rules/10-define-profile-rule-catalog-boundary.md \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-b-profile-rules/11-migrate-profile-rule-metadata-to-toml-catalog.md
```

額外 mechanical checks：

```bash
test -e src/kai_mind/core/rules/profile_registry.toml
test ! -e src/kai_mind/core/services/profile_registry.py
rg -n "profile_registry|profile_rule_definitions|ProfileRegistryLoader" src tests docs/MODEL-CONTRACT.md
```

最後一個 `rg` 是 usage inventory，不是「零 matches」驗收；每個 match 必須分類成 active loader、
Python rule definitions、test、projection 或更新後文件。

### 2026-07-14 final verification evidence

```text
Focused profile suite                  77 passed
Full backend suite                     819 passed in 17.31s
Ruff format/check                      272 files formatted / all checks passed
Mypy                                   258 source files, no issues
Frontend tests                         3 files / 7 tests passed
Frontend lint / build                  0 errors / build succeeded
CLI help / happy / bad input           exit 0 / exit 0 / exit 1
Baseline semantic diff                 4 fixtures × 15 profiles identical
Wheel package resource                 profile_registry.toml present
git diff --check                       passed
```

## 12. Stop conditions

遇到下列任一情況停止本計畫，不得以 metadata migration 名義繼續擴張：

- 必須改五態、activation、coverage、depth 或 Mapping Completeness 才能完成。
- 必須新增 public API/frontend field/build artifact 才能使用 projection。
- Catalog 需要 `required_node_ids`、conditions、thresholds 或 rule ids 才能運作。
- Plan 02 characterization tests 出現 status/evidence regression。
- Loader 需要讀 target repo 或 remote catalog。

這些情況代表 scope 已跨到 Plan 02、06、API contract 或新 migration plan。

## 13. 開源實作對照與研究結論

| 來源 | 可借鏡做法 | 套用到本計畫 | Trade-off |
|---|---|---|---|
| OpenSSF Scorecard probes（Apache-2.0） | definition、implementation、test 分離；資料不足有明確 outcome；有 lifecycle | TOML / Python rules / tests 三者可追溯；不把 absence 當 negative | 不採用 aggregate score |
| OpenTelemetry Semantic Conventions（Apache-2.0） | YAML authoring source 產生文件；policy checks 驗 naming/backward compatibility | TOML 單一 source、JSON projection、schema freshness test | 不引入 Weaver 等完整工具鏈 |
| Import Linter v2.13（BSD-2-Clause） | forbidden contract 預設檢查 descendants 與 indirect imports | Plan 10/11 architecture guard 檢查 transitive path | 目前只有一條 contract，先不加 dependency |
| SARIF 2.1.0（OASIS） | stable rule ids；`open` 與 `notApplicable` 分開 | profile ids 穩定；`undetermined` 與 activation `not_applicable` 分開 | 不改 artifact format |

本計畫只借鏡架構模式與驗證方式，沒有複製外部專案程式碼。

Sources：

- [OpenSSF Scorecard probes](https://github.com/ossf/scorecard/blob/main/probes/README.md)
- [OpenTelemetry Semantic Conventions YAML model](https://github.com/open-telemetry/semantic-conventions/blob/main/model/README.md)
- [Import Linter forbidden contracts](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/)
- [Import Linter v2.13 release commit](https://github.com/seddonym/import-linter/commit/f544debbb0efe10092cd387032ea76b94a0acee0)
- [OASIS SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)
