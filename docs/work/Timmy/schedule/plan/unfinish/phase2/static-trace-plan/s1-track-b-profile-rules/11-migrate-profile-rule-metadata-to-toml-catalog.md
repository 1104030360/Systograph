# 建立 Capability Profile Registry Metadata 實作計畫

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。

**目標：** 將 generic capability profile metadata 移到 package-bundled
`profile_registry.toml`，並產生 read-only `profile_registry.json` projection 供
artifact/API consumer 使用；Python 仍負責 status、coverage 與 depth decisions。

**架構：** TOML 是唯一 hand-authored registry metadata source；JSON 是由 loader
產生的 deterministic projection，不可手動維護。Python 保留所有 executable
trigger、status、coverage/depth、cross-field semantics、related-ref selection 與
validation。Registry 不限定 12 列，frontend 不得硬編碼數量或順序。

**Current scope decision：** 2026-07-02 使用者決定本計畫不延後，納入目前 `00`～`14` path。本計畫必須在 `02-implement-stackable-profile-inference.md` 與 `10-define-profile-rule-catalog-boundary.md` 完成後執行，並在 `14-local-project-import-and-test.md` 前完成，讓 real-world validation 使用 package-bundled TOML metadata catalog。

**Tech Stack：** Python 3.11、Pydantic v2 profile signal models、`tomllib`、`src/kai_mind/core/rules/` 下 package-bundled TOML、既有 `RuleCatalogLoader`、pytest、Ruff、mypy。

---

## 2026-07-06 Confirmed Metadata-Only Contract

本節取代本文較早的三態與「status enum 不變」描述。

**Catalog split（2026-07-08 對齊 Plan 01A）：** 52 reference node metadata（10 planes /
52 nodes、legend wording、`activation_applicable`）**只**在
`capability_reference_map.toml`（Plan `01A`）。本計畫的 `profile_registry.toml` **只**含
`[[profiles]]` 列（15 MVP profile 的 label、axis、wording、recommended next checks）。
**不得**在 `profile_registry.toml` 重複定義 52 格 reference node catalog。

- **`profile_registry.toml` 可保存：** 15 MVP profile 的 id、display name、short label、
  description、axis metadata、default evidence wording、uncertainty 文案、viewer legend
  文案（profile 層級）。
- **`profile_registry.toml` 不可保存：** 52 reference node id/plane 清單、五態 threshold、
  reference node matching、profile trigger、regex、score、provider、lifecycle action。
- Python 擁有五態判斷、activation 判斷、evidence classification、field-specific conflict、
  `not_detected` coverage gate、`build_id` / `scan_id` / `environment_id` scope 驗證與
  Mapping Completeness 公式和權重。
- Mapping Completeness 固定權重為 `detected=1`、`not_detected=1`、`partial=0.5`、
  `undetermined=0`、`conflicted=0`，denominator 為全部固定 reference nodes；
  activation/not_applicable 不排除 node。TOML 不得覆寫，且此 metric 不得命名為 confidence。
- TOML 禁止 executable 欄位，包括 `status_weight`、`mapping_completeness_weight`、
  `activation_condition`、`coverage_gate`、`conflict_precedence`、regex、threshold、score、
  provider 或 lifecycle action。
- 本計畫不擁有 Step 4 component bridge，也不擁有 Step 6 executable assessment。
  `profile_registry.toml` 不能保存 `rule_id -> component`、`reference_node_id`
  matching 條件、profile trigger、accept action 或 proposal lifecycle state；這些分別
  屬於 Plan `01B`、`02`、`04` 與 `03A` 的 Python services。

## 2026-07-07 UA 整合對齊

**2026-07-08 audit 小修：** `ProfileRegistryEntry` loader 的 `allowed_fields` 須包含
`primary_axis` 與 `secondary_axes`（範例 loader 已補；實作時 fail-closed 驗證）。

本計畫仍只遷移 profile wording / metadata。若新增 UA 相關 metadata，TOML 只能保存
UA rule/source 的描述、display label、migration alias 或 generated JSON projection；
不得保存 UA `rule_id` 對 canonical component / reference node 的 executable mapping。
`AssessmentOrchestrator`（Plan 17，deferred）workflow 設定若在未來重啟時使用 TOML，
也只能作編排 metadata（agent 列表、
prompt 版本、input/output schema），不得決定五態、寫 canonical facts 或觸發
`MappingProposalService`。

## 執行摘要

### 目標

把 registry-driven capability overlay metadata 移到 TOML，提供 generated JSON
projection，同時保留 Python trigger ownership。

### 背景

02/10 先用 Python 完成正確行為；待規則穩定後再抽 metadata，可降低大量重複 wording 並讓 catalog coverage 可被完整驗證。

### 目前 code 狀態

現有 `RuleCatalogLoader` 可 fail-closed 載入多種 TOML，但沒有 profile section/dataclass；02 預計先在 Python 定義 metadata。

### 相關檔案

- `src/kai_mind/core/rules/profile_registry.toml`（新增）
- `src/kai_mind/core/services/profile_registry_projection_service.py`（新增）
- `schemas/profile-registry.v1.schema.json`（新增）
- `src/kai_mind/core/services/rule_catalog_loader.py`
- `src/kai_mind/core/services/profile_inference_service.py`
- `tests/unit/core/test_rule_catalog_loader.py`
- `tests/unit/core/test_profile_inference_boundaries.py`

### 實作步驟

先寫 loader red tests，新增 strict metadata model/catalog，再重構 service lookup，最後用 source guardrails 證明 trigger logic 仍在 Python。

### 驗收標準

Catalog 必須精確覆蓋 active generic capability ids；duplicate/missing/unknown/
trigger-like fields fail closed；generated JSON 與 TOML semantic content 相同。

### 風險與注意事項

TOML 不是 scan rule catalog、prompt config 或 scoring DSL。`not_detected` 的 empty next checks 等 cross-field invariant 仍由 Python/validation 控制。

## 為何需要本計畫

`10-define-profile-rule-catalog-boundary.md` 刻意先把 rule ownership 切清楚：trigger logic 一律在 Python，不在 TOML。2026-07-02 使用者決定在目前 00-14 path 內就執行本 metadata externalization。本計畫只把 metadata 移到 TOML，遵循成熟的 `RiskHintService` pattern：

```text
Risk hints today
  Python decides when to emit a risk
  TOML stores rule metadata, rationale, uncertainty

Profile inference after this plan
  Python decides five-state status, activation, evidence, conflicts, coverage and scope
  TOML stores profile metadata, labels, wording, default next-check text
```

這不是 scan rule catalog，也不是 LLM proposal config。不得成為編碼 executable trigger conditions 的地方。

## 實作前需重新確認的目前證據

- `src/kai_mind/core/services/rule_catalog_loader.py` 已能載入 package-bundled TOML catalogs，並 fail-closed validation。
- `src/kai_mind/core/rules/risk_hint_rules.toml` 存放 emitted risk hints 的 wording 與 metadata。
- `src/kai_mind/core/services/risk_hint_service.py` 在 Python emit risks；若 emitted `rule_id` metadata 缺失則 raise `RiskHintMetadataError`。
- `10-define-profile-rule-catalog-boundary.md` 規定 MVP 將 profile wording/metadata hard-coded 在 Python。
- 執行本計畫時 `src/kai_mind/core/services/profile_inference_service.py` 應已存在；應含來自 `02` implementation（依 `10` boundary）的 hard-coded profile metadata。

## 範圍

包含：

- 在 `src/kai_mind/core/rules/` 新增 dedicated `profile_registry.toml` catalog。
- 新增 deterministic `profile_registry.json` projection writer/schema；JSON 不成為
  第二份 authoring source。
- 擴充 `RuleCatalogLoader`：profile metadata dataclasses 與 loader methods。
- 重構 `ProfileInferenceService`，透過小型 provider/lookup path 讀取 metadata。
- Python trigger logic 維持原位。
- 新增 tests：證明 metadata 從 TOML 載入，且 missing metadata fail closed。
- 新增 guardrail tests：證明 TOML 不含 trigger expressions、regexes、thresholds、provider config、prompts 或 lifecycle state。

不包含：

- 不把五態、activation、evidence classification、conflict、coverage gate、scope validation
  或 Mapping Completeness 規則移到 TOML。
- 不新增 LLM calls、provider config、prompt templates 或 user confirmation lifecycle 到 profile inference。
- 不重用 `risk_hint_rules.toml`、`recommended_next_check_rules.toml`、`llm_proposal.toml`、`mapping_proposal.v1.yaml`。
- 不讓 risk hints 直接 trigger profile detection。
- `profile-signals` active contract 必須採五態；舊三態只允許在 migration fixture / adapter
  中存在，不得限制 active schema 演進。

## 目標 Catalog Shape

建立 `src/kai_mind/core/rules/profile_registry.toml`：

```toml
[[profiles]]
profile_id = "rag-grounding"
display_name = "RAG Grounding"
short_label = "Grounding"
description = "Core retrieval-augmented generation components were detected."
default_evidence_strength = "static_multiple_signals"
default_uncertainty = "Static evidence only; runtime retrieval and generation path not confirmed."
recommended_next_checks = []

[[profiles]]
profile_id = "reranking"
display_name = "Reranking"
short_label = "Reranking"
description = "Evidence shows a reranker participates in retrieval result ordering."
default_evidence_strength = "static_single_signal"
default_uncertainty = "Static evidence only; runtime advanced retrieval path not confirmed."
recommended_next_checks = ["review reranker code path"]

[[profiles]]
profile_id = "agentic-control"
display_name = "Agentic Control"
short_label = "Agent Control"
description = "Evidence shows a planner, router, or controller selects actions or retrieval."
default_evidence_strength = "static_single_signal"
default_uncertainty = "Agent/tool-like static signal exists; runtime tool execution is not confirmed."
recommended_next_checks = [
  "confirm tool permission boundary",
  "review human approval and tool-call logging evidence",
]
```

最終 catalog 必須包含 `MVP_CAPABILITY_PROFILE_IDS` 中每個 MVP profile id：

```python
MVP_CAPABILITY_PROFILE_IDS: tuple[str, ...] = (
    "rag-grounding",
    "agentic-control",
    "tool-calling",
    "memory",
    "workflow-orchestration",
    "hybrid-retrieval",
    "reranking",
    "corrective-retrieval",
    "self-reflection",
    "graph-retrieval",
    "hierarchical-retrieval",
    "contextual-retrieval",
    "multimodal-grounding",
    "modular-composition",
    "multi-query-retrieval",
)
```

舊 implementation examples 若仍使用 `profile_id="reranker"`，執行本計畫前應更新成 `reranking` profile metadata 搭配 reranker evidence / non-baseline capability candidate；`reranker` 不再是最新 registry-driven catalog 的 top-level profile id。

不要新增 `condition`、`regex`、`threshold`、`status_weight`、
`mapping_completeness_weight`、`activation_condition`、`coverage_gate`、
`conflict_precedence`、`requires_slot`、`requires_extension`、
`requires_capability_candidate`、`prompt`、`provider`、`accept_action`、
`mapping_type` 等欄位。

## 實作 Tasks

### Task 1：新增 Profile Metadata Catalog 的 Loader Tests

**檔案：**

- Modify: `tests/unit/core/test_rule_catalog_loader.py`
- Future source under test: `src/kai_mind/core/services/rule_catalog_loader.py`

- [ ] 新增 test：從 temp file 載入 valid profile metadata catalog。
- [ ] 新增 test：reject duplicate `profile_id`。
- [ ] 新增 test：reject missing wording fields。
- [ ] 新增 test：reject 用作 trigger logic 的 unknown fields。
- [ ] 新增 test：default package catalog 覆蓋每個 `MVP_CAPABILITY_PROFILE_IDS` 值。

Test shape：

```python
def test_load_profile_registry_from_valid_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "profile_registry.toml",
        "\n".join(
            [
                "[[profiles]]",
                'profile_id = "reranking"',
                'display_name = "Reranking"',
                'short_label = "Reranking"',
                'description = "Evidence suggests a reranker is connected to the retrieval path."',
                'default_evidence_strength = "static_single_signal"',
                (
                    'default_uncertainty = "Static evidence only; runtime '
                    'reranking path not confirmed."'
                ),
                'recommended_next_checks = ["review reranker code path"]',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_profile_registry(catalog_path)

    assert rules[0].profile_id == "reranking"
    assert rules[0].display_name == "Reranking"
    assert rules[0].short_label == "Reranking"
    assert rules[0].default_evidence_strength == "static_single_signal"
    assert rules[0].recommended_next_checks == (
        "review reranker code path",
    )


def test_profile_inference_catalog_rejects_trigger_fields(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "profile_registry.toml",
        "\n".join(
            [
                "[[profiles]]",
                'profile_id = "reranking"',
                'display_name = "Reranking"',
                'short_label = "Reranking"',
                'description = "Evidence suggests a reranker is connected to the retrieval path."',
                'default_evidence_strength = "static_single_signal"',
                'default_uncertainty = "Static evidence only."',
                'recommended_next_checks = []',
                'condition = "capability_candidate.observed_kind == reranker"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="unknown profile metadata field"):
        RuleCatalogLoader().load_profile_registry(catalog_path)
```

執行：

```bash
.venv/bin/pytest tests/unit/core/test_rule_catalog_loader.py -q
```

預期（source 變更前）：因 `load_profile_registry()` 尚不存在而失敗。

### Task 2：擴充 RuleCatalogLoader 以支援 Profile Metadata

**檔案：**

- Modify: `src/kai_mind/core/services/rule_catalog_loader.py`
- Test: `tests/unit/core/test_rule_catalog_loader.py`

- [ ] 新增 `PROFILE_REGISTRY_CATALOG = "profile_registry.toml"`。
- [ ] 新增 frozen dataclass `ProfileRegistryEntry`。
- [ ] 新增 `load_default_profile_registry()`。
- [ ] 新增 `load_profile_registry(catalog_path)`。
- [ ] Reject unknown root sections（`profiles` 以外）。
- [ ] Reject 每個 `[[profiles]]` table 內的 unknown fields。
- [ ] Require 所有 wording/metadata fields。
- [ ] 將 `recommended_next_checks` 轉為 `tuple[str, ...]`。

Implementation shape：

```python
PROFILE_REGISTRY_CATALOG = "profile_registry.toml"


@dataclass(frozen=True)
class ProfileRegistryEntry:
    """Metadata for one deterministic profile inference finding."""

    profile_id: str
    display_name: str
    short_label: str
    description: str
    default_evidence_strength: str
    default_uncertainty: str
    recommended_next_checks: tuple[str, ...]
```

```python
def load_default_profile_registry(
    self,
) -> tuple[ProfileRegistryEntry, ...]:
    return self.load_profile_registry(None)


def load_profile_registry(
    self,
    catalog_path: Path | str | None,
) -> tuple[ProfileRegistryEntry, ...]:
    loaded = self._load_toml(
        catalog_path,
        default_name=PROFILE_REGISTRY_CATALOG,
    )
    self._reject_unknown_sections(loaded, {"profiles"})
    entries = self._section_list(loaded, "profiles")
    profile_ids: set[str] = set()
    rules: list[ProfileRegistryEntry] = []
    allowed_fields = {
        "profile_id",
        "display_name",
        "short_label",
        "primary_axis",
        "secondary_axes",
        "description",
        "default_evidence_strength",
        "default_uncertainty",
        "recommended_next_checks",
    }
    for index, entry in enumerate(entries):
        section = f"profiles[{index}]"
        unknown_fields = set(entry) - allowed_fields
        if unknown_fields:
            joined = ", ".join(sorted(unknown_fields))
            raise RuleCatalogError(
                f"unknown profile metadata field: {joined}"
            )
        profile_id = self._required_string(
            entry,
            "profile_id",
            section=section,
        )
        self._reject_duplicate(
            profile_ids,
            profile_id,
            label="duplicate profile_id",
        )
        rules.append(
            ProfileRegistryEntry(
                profile_id=profile_id,
                display_name=self._required_string(
                    entry,
                    "display_name",
                    section=section,
                ),
                short_label=self._required_string(
                    entry,
                    "short_label",
                    section=section,
                ),
                description=self._required_string(
                    entry,
                    "description",
                    section=section,
                ),
                default_evidence_strength=self._required_string(
                    entry,
                    "default_evidence_strength",
                    section=section,
                ),
                default_uncertainty=self._required_string(
                    entry,
                    "default_uncertainty",
                    section=section,
                ),
                recommended_next_checks=self._required_string_tuple(
                    entry,
                    "recommended_next_checks",
                    section=section,
                    allow_empty=True,
                ),
            )
        )
    return tuple(rules)
```

若 `_required_string_tuple()` 尚不支援 empty lists，新增 `allow_empty: bool = False` 參數，並預設 `False` 以保留既有 callers。

執行：

```bash
.venv/bin/pytest tests/unit/core/test_rule_catalog_loader.py -q
```

預期：loader tests 通過，但 default-catalog coverage test 可能仍失敗，直到 package TOML 檔建立。

### Task 3：新增 Package-bundled Profile Metadata Catalog

**檔案：**

- Create: `src/kai_mind/core/rules/profile_registry.toml`
- Test: `tests/unit/core/test_rule_catalog_loader.py`

- [ ] 為 `MVP_CAPABILITY_PROFILE_IDS` 中每個 id 新增一筆 `[[profiles]]` entry。
- [ ] Entries 保持 declarative 且 wording-only。
- [ ] 無 default next checks 的 profiles 使用 `recommended_next_checks = []`。
- [ ] 不新增 trigger fields、regexes、thresholds、provider config、prompts 或 mapping lifecycle fields。
- [ ] 新增 projection service，將 validated TOML entries 轉成 stable
  `profile_registry.json`；輸出包含 schema version、profile ids、labels、axes、
  descriptions 與 ordering，不包含 executable conditions。
- [ ] 新增 schema/round-trip tests，證明 generated JSON 與 TOML registry semantic
  content 相同，且 frontend 不依賴固定 profile count。

執行：

```bash
.venv/bin/pytest tests/unit/core/test_rule_catalog_loader.py -q
```

預期：所有 rule catalog loader tests 通過，包含 default profile catalog coverage。

### Task 4：新增 Profile Metadata Lookup Tests

**檔案：**

- Modify: `tests/unit/core/test_profile_inference_service.py`
- Future source under test: `src/kai_mind/core/services/profile_inference_service.py`

- [ ] 新增 test：`ProfileInferenceService` 對 `not_detected` default findings 使用 TOML metadata。
- [ ] 新增 test：`ProfileInferenceService` 對 `undetermined` findings 使用 TOML metadata，且 Python 仍決定 evidence 何時不足。
- [ ] 新增 test：detected findings 使用 TOML default uncertainty 與 recommended next checks，除非 Python trigger logic 刻意 override。
- [ ] 新增 test：emit 的 profile 缺少 metadata 時 fail closed，raise `ProfileRuleMetadataError`。
- [ ] 新增 dependency-boundary test：profile inference 仍不 import mapping proposal、manual mapping、LLM proposal config 或 proposal routes。

Test shape：

```python
def test_profile_inference_uses_catalog_metadata_for_not_detected_profiles(
    minimal_system_map: AiSystemMapV2,
) -> None:
    service = ProfileInferenceService(
        profile_rule_catalog_path=custom_profile_catalog(
            profile_id="reranking",
            display_name="Custom Reranking",
            short_label="Custom",
            description="Custom metadata.",
            default_evidence_strength="not_detected",
            default_uncertainty="Custom uncertainty.",
            recommended_next_checks=[],
        )
    )

    result = service.infer(minimal_system_map)
    reranking = next(
        profile
        for profile in result.profiles
        if profile.profile_id == "reranking"
    )

    assert reranking.status == "not_detected"
    assert reranking.uncertainty == "Custom uncertainty."
    assert reranking.recommended_next_checks == []
```

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -q
```

預期（service 變更前）：失敗，因 service 仍使用 Python hard-coded metadata。

### Task 5：重構 ProfileInferenceService 以使用 Metadata Catalog

**檔案：**

- Modify: `src/kai_mind/core/services/profile_inference_service.py`
- Test: `tests/unit/core/test_profile_inference_service.py`

- [ ] 在 service constructor 新增 `profile_rule_catalog_path: Path | str | None = None`。
- [ ] 以 `RuleCatalogLoader().load_profile_registry(profile_rule_catalog_path)` 載入 profile metadata。
- [ ] 將 metadata 存入 `_metadata_by_profile_id`。
- [ ] 當 `MVP_CAPABILITY_PROFILE_IDS` 含 catalog 中缺失的 id 時 raise `ProfileRuleMetadataError`。
- [ ] 以 metadata lookup 取代 hard-coded default uncertainty 與 recommended next checks。
- [ ] 所有 trigger helper methods 保留在 Python。
- [ ] 當 detected profile 需要比 default 更精確的 uncertainty 或 next-check list 時，保持 Python override 明確且有 test。

Implementation shape：

```python
from pathlib import Path

from kai_mind.core.services.rule_catalog_loader import (
    ProfileRegistryEntry,
    RuleCatalogLoader,
)


class ProfileRuleMetadataError(ValueError):
    """Raised when profile inference emits a profile without metadata."""
```

```python
class ProfileInferenceService:
    def __init__(
        self,
        *,
        validation_service: ProfileSignalValidationService | None = None,
        profile_rule_catalog_path: Path | str | None = None,
    ) -> None:
        self._validation_service = (
            validation_service or ProfileSignalValidationService()
        )
        metadata = RuleCatalogLoader().load_profile_registry(
            profile_rule_catalog_path
        )
        self._metadata_by_profile_id = {
            item.profile_id: item for item in metadata
        }
        self._validate_metadata_coverage()

    def _metadata(self, profile_id: str) -> ProfileRegistryEntry:
        metadata = self._metadata_by_profile_id.get(profile_id)
        if metadata is None:
            raise ProfileRuleMetadataError(
                f"Missing profile metadata for {profile_id!r}"
            )
        return metadata

    def _validate_metadata_coverage(self) -> None:
        missing = sorted(set(MVP_CAPABILITY_PROFILE_IDS) - set(self._metadata_by_profile_id))
        if missing:
            raise ProfileRuleMetadataError(
                "Missing profile metadata for: " + ", ".join(missing)
            )
```

Replace hard-coded `not_detected` defaults. Keep `recommended_next_checks=[]`
for `not_detected` even if TOML metadata defines default next checks for
detected or `undetermined` cases:

```python
metadata = self._metadata(profile_id)
by_id.setdefault(
    profile_id,
    ProfileFinding(
        profile_id=profile_id,
        status="not_detected",
        evidence_ids=[],
        evidence_strength="not_detected",
        uncertainty=metadata.default_uncertainty,
        recommended_next_checks=[],
    ),
)
```

For detected findings, use a small helper so trigger methods stay readable:

```python
def _finding(
    self,
    *,
    profile_id: str,
    status: str,
    evidence_ids: list[str],
    evidence_strength: str | None = None,
    uncertainty: str | None = None,
    recommended_next_checks: list[str] | None = None,
    **refs: object,
) -> ProfileFinding:
    metadata = self._metadata(profile_id)
    return ProfileFinding(
        profile_id=profile_id,
        status=status,
        evidence_ids=evidence_ids,
        evidence_strength=(
            evidence_strength or metadata.default_evidence_strength
        ),
        uncertainty=uncertainty or metadata.default_uncertainty,
        recommended_next_checks=(
            recommended_next_checks
            if recommended_next_checks is not None
            else list(metadata.recommended_next_checks)
        ),
        **refs,
    )
```

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -q
```

預期：profile inference tests 通過。

### Task 6：新增 Boundary Tests，確認 TOML 不擁有 Trigger Logic

**檔案：**

- Modify: `tests/unit/core/test_profile_inference_boundaries.py`
- Modify: `tests/unit/core/test_rule_catalog_loader.py`
- Read: `src/kai_mind/core/rules/profile_registry.toml`
- Read: `src/kai_mind/core/services/profile_inference_service.py`

- [ ] 斷言 TOML 含 `[[profiles]]` 且不含 trigger field names。
- [ ] 斷言 Python service 仍含 trigger helper methods，例如 `_grounding_baseline()`、`_advanced_rag()`。
- [ ] 斷言 profile inference 仍不 import mapping proposal、manual mapping 或 LLM proposal config modules。

Test shape：

```python
def test_profile_catalog_is_metadata_only() -> None:
    catalog = Path(
        "src/kai_mind/core/rules/profile_registry.toml"
    ).read_text(encoding="utf-8")

    assert "[[profiles]]" in catalog
    forbidden = [
        "condition",
        "regex",
        "threshold",
        "requires_slot",
        "requires_extension",
        "requires_capability_candidate",
        "prompt",
        "provider",
        "mapping_type",
        "accept_action",
    ]
    assert [field for field in forbidden if field in catalog] == []


def test_profile_trigger_logic_remains_in_python() -> None:
    source = Path(
        "src/kai_mind/core/services/profile_inference_service.py"
    ).read_text(encoding="utf-8")

    assert "def _grounding_baseline" in source
    assert "def _advanced_rag" in source
    assert "load_profile_registry" in source
```

執行：

```bash
.venv/bin/pytest tests/unit/core/test_profile_inference_boundaries.py tests/unit/core/test_rule_catalog_loader.py -q
```

預期：metadata-only boundary tests 通過。

### Task 7：更新 Design Docs 與 10/11 決策記錄

**檔案：**

- Modify: `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/10-define-profile-rule-catalog-boundary.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/11-migrate-profile-rule-metadata-to-toml-catalog.md`

- [ ] 記錄：`02` + `10` 完成 deterministic profile inference boundary；`11` 是目前 00-14 path 內的 metadata externalization。
- [ ] 記錄：`11` 僅將 profile wording/metadata 移到 TOML。
- [ ] 記錄：Python 仍擁有 trigger logic 與 status decisions。
- [ ] 記錄：TOML 僅 metadata-only，不得含 executable rules。

Documentation wording：

```markdown
Profile inference follows a two-stage rule ownership model:

1. 02 + 10 MVP: Python hard-coded profile ids, metadata, wording, and trigger logic.
2. 11 refactor: TOML stores profile wording/metadata; Python still decides when a profile triggers.

`profile_registry.toml` is not a scan rule catalog and not a proposal
provider config. It must not contain conditions, thresholds, regexes, prompts,
provider settings, capability-candidate trigger logic, or user-confirmation
lifecycle state.
```

執行：

```bash
git diff --check \
  docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/10-define-profile-rule-catalog-boundary.md \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/11-migrate-profile-rule-metadata-to-toml-catalog.md
```

預期：無 whitespace errors。

## 驗收標準

- [ ] `profile_registry.toml` 存在，且 `MVP_CAPABILITY_PROFILE_IDS` 中每個 profile 都有一筆 metadata-only entry。
- [ ] `RuleCatalogLoader` 可載入 default 與 custom profile metadata catalogs。
- [ ] Loader reject duplicate profile ids、missing wording fields、malformed TOML、unknown sections 與 trigger-like fields。
- [ ] `ProfileInferenceService` 使用 TOML metadata 作為 default uncertainty、evidence strength defaults 與 recommended next checks。
- [ ] `ProfileInferenceService` 仍將五態、activation、evidence classification、conflict、
  coverage gate、assessment scope 與 Mapping Completeness 邏輯保留在 Python。
- [ ] Missing profile metadata 以 `ProfileRuleMetadataError` fail closed。
- [ ] 無 profile TOML field 控制 thresholds、conditions、regex matching、status weights、
  activation conditions、coverage gates、conflict precedence、related-ref selection、graph
  projection、LLM provider behavior 或 mapping proposal lifecycle。
- [ ] Active `profile-signals` contract 使用五態；v1 三態只由 migration adapter 讀取，
  active output 引用 `ai-system-map/v2` source schema 與相同 build scope。
- [ ] `profile_registry.json` 由 TOML deterministic 產生，通過 schema，且不可被
  loader 當作可寫回 source。

## 驗證

- [ ] `.venv/bin/pytest tests/unit/core/test_rule_catalog_loader.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_profile_inference_service.py -q`
- [ ] `.venv/bin/pytest tests/unit/core/test_profile_inference_boundaries.py -q`
- [ ] `rg -n "profile_registry|ProfileRegistryEntry|load_profile_registry|ProfileRuleMetadataError" src tests docs/work/Timmy/schedule/plan/unfinish`
- [ ] `rg -n "condition|threshold|status_weight|mapping_completeness_weight|activation_condition|coverage_gate|conflict_precedence|requires_slot|requires_extension|requires_capability_candidate|prompt|provider|mapping_type|accept_action" src/kai_mind/core/rules/profile_registry.toml` 並確認無 matches。
- [ ] `git diff --check docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/11-migrate-profile-rule-metadata-to-toml-catalog.md`

## 相依關係

- 需先完成 `10-define-profile-rule-catalog-boundary.md`。
- 需要 `02-implement-stackable-profile-inference.md` 的 `ProfileInferenceService`、`ProfileFinding`、`ProfileSignalValidationService`。
- 與 `05-add-read-only-system-map-index.md` 對齊；TOML metadata 不擁有 lookup 或 profile trigger logic。
- 鏡像 `RiskHintService` 架構：Python emit，TOML 提供 metadata。

## 不在範圍內

- 不把 profile trigger logic 移到 TOML。
- 不讓 `profile_registry.toml` 變成 scan rule catalog。
- 不新增 LLM-backed profile inference。
- 不變更 mapping proposal、manual mapping、risk hint、Plan 06 graph projection、query trace
  或 canonical map ownership；只讓既定五態 assessment contract 取得 metadata。
- 不新增 profile findings 的 user-facing accept/edit/reject actions。

## P0 Execution Mapping 補充（2026-07-03）

`profile_registry.toml` 不擁有 execution mapping logic：

- 不新增 TOML 欄位控制 `call_graph.json`、`dataflow_hints.json` 或 `execution_paths.json` 的
  extraction rule。
- 可在 profile metadata 中描述「可能參考 execution path evidence」的 wording，但 status、
  activation、evidence classification、conflict、coverage 與 score 計算仍在 Python
  deterministic logic。
- 若 profile finding related refs 指向 execution path ids，TOML 只提供 display label /
  recommended wording，不負責解析 ids。
- `profile_registry.json` projection 不包含 call graph schema。
