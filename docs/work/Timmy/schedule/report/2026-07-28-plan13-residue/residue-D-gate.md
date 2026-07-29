# Residue D — Plan 13 v2 cutover 守門機制完整性稽核

READ-ONLY 稽核，未修改任何檔案。所有結論皆附 live 指令輸出。

- Repo: `/Users/linjunting/Local_AI_Health_Doctor`（branch `main`，HEAD `0a68ccd`）
- 稽核日期：2026-07-28
- 受稽核 gate：`tests/contracts/test_v2_cutover_consumer_allowlist.py`

---

### RD-1. Allowlist gate live 驗證通過，census 數字與 digest 完全可重現【C類 正常】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/tests/contracts/test_v2_cutover_consumer_allowlist.py:278`
- **現況**

```
$ uv run pytest tests/contracts/test_v2_cutover_consumer_allowlist.py -v -p no:randomly
tests/contracts/test_v2_cutover_consumer_allowlist.py::test_direct_legacy_consumers_match_classified_allowlist PASSED [100%]
============================== 1 passed in 0.45s ===============================
```

以測試自身的 `_direct_legacy_hits()` 實作跑 census（read-only probe，未寫檔）：

```
ALLOWLIST records : 35
ACTUAL scanned hits: 35
unknown: []
stale  : []
classification counts: Counter({'migration_only': 22, 'operator_rollback': 8, 'migrate': 5})

--- scanned python hits by root ---
python(src/kai_mind): 30  frontend/src: 5  scripts/*.sh: 0
scripts hits: []
```

REP 宣稱的 census SHA-256 也能精確重現（payload = allowlist tuple 順序 + sorted-key compact JSON）：

```
as-ordered  : 59fa4f066a0e37c9f73ce488e64da96cccab7c8a9e6a429b0c073a738544714b
REP claim   : 59fa4f066a0e37c9f73ce488e64da96cccab7c8a9e6a429b0c073a738544714b   ← 相符
```

5 筆 `migrate` 全部仍在 frontend，與 REP 一致：

```
frontend/src/types.ts:334,371                     new_extension_component
frontend/src/data/scanTemplate.mock.ts:201        new_extension_component
frontend/src/components/proposal/EditForm.tsx:38  new_extension_component
frontend/src/data/frontend-json-sample.json:21,32,842,1634  ai-system-map/v1
frontend/src/data/frontend-json-sample.json:1595  new_extension_component
```

- **判定理由**：`35 records / 35 hits`、`migrate=5 / migration_only=22 / operator_rollback=8`、SHA-256 三項與 REP `docs/work/Timmy/schedule/report/2026-07-17-phase2-plan13-v2-cutover-REP.md:33-35,143` 完全一致。這份 census 不是編造的。
- **建議處置**：無。
- **風險**：低

---

### RD-2. Stale 偵測是雙向的，新增 hit 也確實 fail closed【C類 正常】

- **位置**：`tests/contracts/test_v2_cutover_consumer_allowlist.py:285-292`
- **現況**：實作是純集合雙向差集，因此刪檔與加 hit 都會失敗。

```python
actual = _direct_legacy_hits()
unknown = sorted(actual - allowed.keys())     # 新增 → fail
stale   = sorted(allowed.keys() - actual)     # 刪除/改名 → fail
assert not unknown, f"unclassified direct legacy consumers: {unknown}"
assert not stale, f"stale legacy consumer records: {stale}"
```

in-memory 模擬（未動任何檔案）：

```
--- STALE SIMULATION: pretend one allowlisted path disappears ---
stale detected: [('src/kai_mind/core/services/legacy_v1_rollback_service.py', 'RagSystemMap')]

--- NEW-HIT SIMULATION: pretend a new file gains RagSystemMap ---
unknown detected: [('src/kai_mind/web/routes/scan_routes.py', 'RagSystemMap')]
```

- **判定理由**：兩個方向都會觸發 assertion。另外 `_python_legacy_hits()` 對 syntax error 會 raise、`read_text(encoding="utf-8")` 對非 UTF-8 會 raise，也都是 fail closed；若 CWD 不是 repo root，`rglob` 回空集合會讓全部 35 筆變 stale 而失敗，同樣不會靜默通過。
- **建議處置**：無。
- **風險**：低

---

### RD-3. `web/legacy_mapping_guards.py` 用 enum 間接引用，整檔逃過掃描【B類 盲點·無人追蹤】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/web/legacy_mapping_guards.py:13`
- **現況**

```python
from kai_mind.core.services.legacy_manual_mapping_migration_service import (
    LegacyManualMappingType,
)

_LEGACY_MAPPING_TYPE = LegacyManualMappingType.NEW_EXTENSION.value
```

```
$ grep -n "legacy_mapping_guards" tests/contracts/test_v2_cutover_consumer_allowlist.py
NOT PRESENT
```

`grep -rn "LegacyManualMappingType\|NEW_EXTENSION" src --include="*.py"` 的全部 hit 與 allowlist 對照：

| src hit | allowlist 有此 path？ |
| --- | --- |
| `core/services/legacy_manual_mapping_migration_service.py:32,33,42,170` | 有（`new_extension_component`，`migration_only`） |
| `web/legacy_mapping_guards.py:10` (`LegacyManualMappingType` import) | **無** |
| `web/legacy_mapping_guards.py:13` (`NEW_EXTENSION.value`) | **無** |

- **判定理由**：`_legacy_symbol()` 只比對 `ast.Name.id` / `ast.Attribute.attr` / class·function 名 / `ast.alias` 是否落在 `LEGACY_NAMES = {RagSystemMap, ExtensionComponent, SystemMapValidationService, new_extension_component}`。這裡的 attribute 是 `NEW_EXTENSION` 與 `value`、alias 是 `LegacyManualMappingType`，全都不在集合中；而檔內沒有任何 `"new_extension_component"` 字面值。**這是 legacy write surface 的唯一 runtime 實作點**（`mapping_routes.py:42` 與 `mapping_proposal_routes.py:100` 都 `Depends(reject_legacy_mapping_type)`），卻完全不在 census 內，Plan 15 做 removal sweep 時查不到它。
- **建議處置**：把 `LegacyManualMappingType`、`NEW_EXTENSION` 加入 `LEGACY_NAMES`，並為 `src/kai_mind/web/legacy_mapping_guards.py` 補一筆 `migration_only` record（removal_plan：Plan 15 隨 Legacy DTO 一起移除 guard）。
- **風險**：中

---

### RD-4. 裸字串常數只比對兩個字面值，`"ExtensionComponent"` 這類寫法逃逸【B類 盲點·無人追蹤】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/system_map_validation_service.py:109`（另見 `:309`、`:315`）
- **現況**

```python
self._reject_duplicate_ids(
    [extension.id for extension in system_map.extensions],
    "ExtensionComponent",          # ← 純字串，不是 Name
)
...
f"ExtensionComponent '{extension.id}' must include "   # :309
f"ExtensionComponent '{extension.id}'",                # :315
```

allowlist 對此檔只有 `RagSystemMap` 與 `SystemMapValidationService` 兩筆（test line 236-248），**沒有 `ExtensionComponent`**。

- **判定理由**：`ast.Constant` 分支比對的是 `LEGACY_LITERALS = {"ai-system-map/v1", "new_extension_component"}`，不是 `LEGACY_NAMES`。因此 `"ExtensionComponent"`、`"RagSystemMap"`、`"SystemMapValidationService"` 三個名字只要寫成字串就完全不算 hit。這證明「即使是已被列管的檔案，也可能藏有未列管的 legacy symbol」。
- **建議處置**：把 `ast.Constant` 分支的比對集合改成 `LEGACY_NAMES | LEGACY_LITERALS`，並回補此檔的 `ExtensionComponent` record。
- **風險**：低（目前這幾處只是 error message），但機制缺口是中等。

---

### RD-5. Substring / f-string / comment / docstring / getattr / quoted annotation 全部逃逸【B類 盲點·無人追蹤】

- **位置**：`tests/contracts/test_v2_cutover_consumer_allowlist.py:334-350`（`_legacy_symbol`）
- **現況**：對 `_legacy_symbol()` 逐一餵入 12 個 snippet（純 in-memory，未寫檔）：

```
  enum_indirection     -> ESCAPES    x = LegacyManualMappingType.NEW_EXTENSION.value
  getattr_string       -> ESCAPES    cls = getattr(system_map, "RagSystemMap")
  quoted_annotation    -> ESCAPES    def f(x: "RagSystemMap") -> None: ...
  fstring_partial      -> ESCAPES    v = f"ai-system-map/v{major}"
  concat_literal       -> ESCAPES    v = "ai-system-map/" + "v1"
  substring_msg        -> ESCAPES    msg = "schema must be ai-system-map/v1 legacy"
  comment_only         -> ESCAPES    # RagSystemMap is legacy
  docstring            -> ESCAPES    """Uses ai-system-map/v1 shape."""
  str_extcomp          -> ESCAPES    name = "ExtensionComponent"
  exact_literal        -> CAUGHT ['ai-system-map/v1']
  attr_access          -> CAUGHT ['RagSystemMap']       # system_map.RagSystemMap
  import_alias         -> CAUGHT ['RagSystemMap']       # import ... as Legacy
```

Repo 裡已有 4 個檔案是「rg 有 hit、AST 掃不到、也不在 allowlist」的實例：

```
src/kai_mind/cli/viewer_command.py:17        "Validate and project one ai-system-map/v1 or "
src/kai_mind/core/models/scan.py:1           """Scanner workflow models that are not part of ai-system-map/v1."""
src/kai_mind/core/models/viewer.py:4         # RagSystemMap。
src/kai_mind/core/models/viewer.py:14        """Viewer projection models derived from ai-system-map/v1."""
src/kai_mind/core/services/rag_template_service.py:117  "Allowed statuses must match ai-system-map/v1 SlotStatus"
```

- **判定理由**：正面消息是 `system_map.RagSystemMap`（module attribute 間接引用）與 `import ... as Legacy`（re-export/alias）**都會被抓到**，因為 `ast.Attribute.attr` 與 `ast.alias` 都有比對。但字串層一律是「整串完全相等」比對，所以任何把 legacy 值放進更長字串、f-string、拼接或動態 `getattr` 的寫法都能無聲通過 CI。上述 5 處目前只是註解／help text，屬低風險殘留；但同樣的機制無法阻擋一個真的用 `f"ai-system-map/v{n}"` 或 `getattr()` 拿到 v1 型別的新 consumer。
- **建議處置**：
  1. `ast.Constant` 改成 substring 比對（`any(lit in node.value for lit in LEGACY_LITERALS)`）並把 `LEGACY_NAMES` 併入比對集合；
  2. 追加一層純文字掃描（含 comment/docstring）當作 advisory-fail，或至少把上述 5 處納入 allowlist 成為可追蹤殘留。
- **風險**：中

---

### RD-6. Executable scope 小於 Plan Task 5 宣告的 census 指令 scope【A類 cut 不乾淨】

- **位置**：`tests/contracts/test_v2_cutover_consumer_allowlist.py:15-18` vs
  `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-v2-cutover/13-retire-legacy-extension-contract.md:448-451`
- **現況**

| | Plan Task 5 census 指令 | 測試實際掃描 |
| --- | --- | --- |
| 範圍 | `rg ... src tests frontend docs` | `src/kai_mind/**/*.py`(AST) + `frontend/src/**/*.{json,ts,tsx}` + `scripts/**/*.sh` |
| `schemas/` | 未列（但 Plan line 278 明列 v1 schema 為 migration-only allowlist 成員） | **未掃** |
| `tests/` | 有 | **未掃** |
| `docs/` | 有 | **未掃** |
| `scripts/*.py` | 有（`src` 不含，但 `scripts/dev.py` 是 Python） | **未掃**（只掃 `.sh`） |
| `frontend/` root 以外 | 有 | **未掃**（只掃 `frontend/src`） |

實測缺口證據：

```
$ rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1" schemas/
schemas/ai-system-map.v2.schema.json:664:            "ai-system-map/v1",
schemas/ai-system-map.v1.schema.json:573:    "ExtensionComponent": {
schemas/ai-system-map.v1.schema.json:630:      "title": "ExtensionComponent",
schemas/ai-system-map.v1.schema.json:724:              "const": "ai-system-map/v1",
schemas/ai-system-map.v1.schema.json:1236:      "const": "ai-system-map/v1",
schemas/ai-system-map.v1.schema.json:1304:        "$ref": "#/$defs/ExtensionComponent"
schemas/ai-system-map.v1.schema.json:1363:  "title": "RagSystemMap",
```

- **判定理由**：Plan line 278 的 census baseline 把 `schemas/ai-system-map.v1.schema.json` 明白列為 migration-only allowlist 成員，但 executable gate 既沒有這筆 record、也不掃 `schemas/`。也就是說 Plan 15 若想靠這支測試證明 v1 schema 是否還被引用，會得到假陰性。`scripts/*.py` 與 `frontend/` root 同理。（`tests/` 與 `docs/` 排除是合理設計，因為 test fixtures 本來就是 legacy evidence，但 Plan 文字並未說明這個縮限。）
- **建議處置**：把 `schemas/*.json` 加入 text scan roots，並在 Plan Task 5 明確寫下 executable scope 與 census 指令的差異（何者被刻意排除、為什麼）。
- **風險**：中

---

### RD-7. `scripts/*.sh` scope 目前是空轉【C類 正常，但宣稱要收斂】

- **位置**：`tests/contracts/test_v2_cutover_consumer_allowlist.py:17,303`
- **現況**

```
$ rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1|SystemMapValidationService" scripts/
NONE
scripts hits: 0
```

- **判定理由**：REP line 79-82（Stage A）宣稱「operational `scripts/*.sh` 都在 executable scope」。這句話為真但零覆蓋——目前沒有任何 shell script 命中，所以這條 scope 對現況沒有防護貢獻，只是為未來保留。不是錯誤，但不該被當成 gate 強度的證據。
- **建議處置**：報告措辭改為「scripts scope 已接上，current hits = 0」。
- **風險**：低

---

### RD-8. 三個 stable error code 完全沒有進入任何 contract 文件【D類 文件不一致】

- **位置**：`docs/API-GUIDE.md`、`docs/MODEL-CONTRACT.md`、`frontend/API_CONTRACT.md`
- **現況**：見下方對照表。
- **判定理由**：Plan Global Constraints line 35-36 要求「所有 migration、rollback、publish failure 都要有 stable error code、可回讀報告」。`invalid_canonical_output_version`、`legacy_rollback_not_representable`、`unsupported_system_map_schema_version` 三個碼只出現在 Plan 檔與 REP，沒有進入任何 authoritative contract doc。`legacy_mapping_type_read_only` 雖在 API-GUIDE 全域 422 表（line 988），但 `POST /api/mappings` 端點自己的錯誤表（line 843-845）只寫「驗證失敗 | 422 | 缺 evidence、未知 slot、含未遮蔽 secret 等」，沒有這個碼——而前端負責人正是照端點段落實作的。
- **建議處置**：把三個缺席碼補進 `docs/API-GUIDE.md`（rollback/loader 章節）與 `docs/MODEL-CONTRACT.md`；`legacy_mapping_type_read_only` 補進 `POST /api/mappings` 與 `POST /api/mapping-proposals/*/decision` 的錯誤表。
- **風險**：中

#### 錯誤碼文件化對照表

| 錯誤碼 | src 實作位置 | 測試位置 | `docs/API-GUIDE.md` | `frontend/API_CONTRACT.md` | `docs/MODEL-CONTRACT.md` |
| --- | --- | --- | --- | --- | --- |
| `legacy_output_not_selectable` | `core/services/canonical_output_configuration.py:33`（呼叫點 `core/services/map_build_service.py:187,252,292`） | `tests/cli/test_map_command.py`、`tests/integration/test_v2_active_cutover.py`、`tests/unit/core/test_canonical_output_configuration.py`、`tests/web/test_map_routes.py` | ✅ line 341 + 988 | ❌ | ✅ line 502 |
| `invalid_canonical_output_version` | `core/services/canonical_output_configuration.py:24`（呼叫點 `web/app.py:138`、`core/services/map_build_service.py:149`） | `tests/integration/test_v2_active_cutover.py`、`tests/unit/core/test_canonical_output_configuration.py` | ❌ | ❌ | ❌ |
| `legacy_rollback_not_representable` | `core/services/legacy_v1_rollback_service.py:85,91`、`core/services/map_build_pipeline.py:180` | `tests/integration/test_v2_active_cutover.py` | ❌ | ❌ | ❌ |
| `legacy_mapping_type_read_only` | `web/legacy_mapping_guards.py:37`（wiring `web/routes/mapping_routes.py:42`、`web/routes/mapping_proposal_routes.py:100`） | `tests/web/test_legacy_mapping_write_rejection.py` | ⚠️ 只在全域 422 表 line 988；端點錯誤表未列 | ❌ | ❌ |
| `unsupported_system_map_schema_version` | `core/services/canonical_map_loader.py:124` | `tests/integration/test_v2_active_cutover.py`、`tests/unit/core/test_canonical_map_loader.py` | ❌ | ❌ | ❌ |

（`frontend/API_CONTRACT.md` 只涵蓋 map loading / inventory / detail scan，完全未涵蓋 `/api/mappings` 與 build 錯誤碼——這本身就是 frontend handoff 缺口的一部分。）

---

### RD-9. `unsupported_system_map_schema_version` 不是結構化 stable code，只是 message prefix【D類 文件不一致 / 契約弱化】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/services/canonical_map_loader.py:124`
- **現況**

```python
raise CanonicalMapLoadError(
    f"unsupported_system_map_schema_version: {schema_version!r}"
)
```

對照同 plan 的另一個碼有專屬欄位：

```python
# core/services/canonical_output_configuration.py:11-17
class CanonicalOutputConfigurationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
```

- **判定理由**：Plan Task 1B line 336-337 要求「未知 schema version fail closed 並回傳 stable `unsupported_system_map_schema_version`」。目前它被嵌在自由文字訊息裡，consumer 只能用 `startswith` 比對；`CanonicalMapLoadError` 沒有 `.code`。同一 plan 內兩個碼的 stability 保證不一致。
- **建議處置**：給 `CanonicalMapLoadError` 加 `code` 欄位（或新增子類），讓所有 Plan 13 stable code 有一致的取用方式。
- **風險**：低～中

---

### RD-10. `docs/API-GUIDE.md` 仍把 `new_extension_component` 列成可送出的 `mapping_type`【D類 文件不一致】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/docs/API-GUIDE.md:812` 與 `:838`
- **現況**

```
# line 812（POST /api/mappings 的 mapping_type 表）
| `new_extension_component` | legacy compatibility only；active v2 UI 不應建立新的 extension |

# line 838
- `mapping_type`：`existing_slot_mapping` | `non_baseline_capability_candidate` |
  `new_extension_component`（legacy compatibility）
```

但 backend 現況：

```python
# src/kai_mind/core/models/mapping_base.py:13-15
class ManualMappingType(StrEnum):
    EXISTING_SLOT = "existing_slot_mapping"
    NON_BASELINE_CAPABILITY_CANDIDATE = "non_baseline_capability_candidate"
```
且 `Depends(reject_legacy_mapping_type)` 會在 Pydantic 驗證前直接回 422 `legacy_mapping_type_read_only`。

- **判定理由**：文件把一個「送出必定 422」的值描述成「legacy compatibility，只是不建議用」。Plan Task 4 line 425-427 要求 backend 立即拒絕，`[x]` 已打，但 API 文件沒同步。這正是還沒遷移的前端負責人會讀的段落，會直接造成錯誤實作。
- **建議處置**：把該列改成「已停用；送出回 `422 legacy_mapping_type_read_only`」，並從 line 838 的可用值清單移除（或標成 rejected）。`docs/MODEL-CONTRACT.md:602` 的「**legacy only**；v2 happy path 禁用」措辭較接近正確，但也建議補上錯誤碼。
- **風險**：中

#### `docs/MODEL-CONTRACT.md` / `docs/API-GUIDE.md` v1 敘述逐處判定

| 檔案:行 | 敘述 | 判定 |
| --- | --- | --- |
| `MODEL-CONTRACT.md:301` | `schema_version` = `"ai-system-map/v2"` | ✅ 正確（active output） |
| `MODEL-CONTRACT.md:483-485` | manifest 三個欄位為 `v1｜v2` union | ✅ migration note（provenance 需保留 v1） |
| `MODEL-CONTRACT.md:501-503` | 「public build requested_schema_version 固定 v2；要求 v1 回 `legacy_output_not_selectable`」 | ✅ 正確 |
| `MODEL-CONTRACT.md:602` | `new_extension_component` = 「legacy only；v2 happy path 禁用」 | ⚠️ 大致正確，但未說明會回 422 stable code |
| `MODEL-CONTRACT.md:629-631` | 「### ai-system-map/v1 — Legacy-readable via 00A。Plan 13 後非 active output。」 | ✅ 標準 migration note |
| `MODEL-CONTRACT.md:640` | 「新 Phase2 UI：不要求使用者建 `extensions`」 | ✅ 正確 |
| `API-GUIDE.md:339-342` | 「`system_map_schema_version` 是 Plan 15 前 deprecated input…指定 v1 回 422 + `legacy_output_not_selectable`」 | ✅ 正確且完整 |
| `API-GUIDE.md:366-368`、`469-471`、`487-488` | response/manifest 的 `v1｜v2` union 欄位 | ✅ migration note |
| `API-GUIDE.md:812` | `new_extension_component` 列在可用 mapping_type 表 | ❌ **過時**（見 RD-10） |
| `API-GUIDE.md:838` | 可用值清單含 `new_extension_component`（legacy compatibility） | ❌ **過時**（見 RD-10） |
| `API-GUIDE.md:843-845` | `POST /api/mappings` 錯誤表未列 `legacy_mapping_type_read_only` | ❌ **缺文件** |

---

### RD-11. `schemas/ai-system-map.v1.schema.json` 沒有任何 legacy/read-only 標示，但 Task 5 checkbox 已打 `[x]`【D類 文件不一致】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/schemas/ai-system-map.v1.schema.json`（全檔）
- **現況**

```
$ rg -n -i "legacy|read-only|deprecat|migration" schemas/ai-system-map.v1.schema.json
（無輸出）
```

Plan line 443-444（`[x]`）：「v1 schema/fixture、Legacy DTO、adapter 與 operator rollback serializer 明確標示 legacy/read-only；normal build path 不得 import。」

Python 端實測：

| 檔案 | legacy 標示 |
| --- | --- |
| `core/models/system_map.py` | ✅ 檔頭註解「定義 ai-system-map/v1 的 Pydantic 資料契約（舊版 / v1 map）」 |
| `core/services/system_map_validation_service.py` | ✅ docstring「00A keeps this service as the v1 validator…」 |
| `core/services/system_map_v1_to_v2_adapter.py` | ❌ 無 module docstring / 檔頭註解，第 1 行即 `from __future__` |
| `core/services/legacy_v1_rollback_service.py` | ❌ 同上 |
| `core/services/legacy_manual_mapping_migration_service.py` | ❌ 同上 |
| `schemas/ai-system-map.v1.schema.json` | ❌ 無任何 marker |

- **判定理由**：4 個被 checkbox 點名的 surface（adapter、rollback serializer、Legacy DTO、v1 schema）中有 4 個沒有顯式 legacy/read-only 標示，只靠檔名暗示。這同時違反 `CLAUDE.md` 的「Service files carry structured header comments（責任 / 呼叫鏈）」慣例。`schemas/` 目錄本身乾淨（只有 v1/v2/profile-registry 三檔，全部 git-tracked，無未追蹤 legacy schema）。
- **建議處置**：v1 schema 加 top-level `"description": "LEGACY read-only …retired in Plan 15"`（注意此檔由 `core/models/system_map.py:334` 產生，需改 model docstring / `json_schema_extra`）；三個 service 補檔頭 legacy 標示。
- **風險**：低

---

### RD-12. `static-trace-plan/README.md` 對 Plan 13 沒有任何狀態標註【D類 文件不一致】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md:320`
- **現況**

```
| 13 | [13-retire-legacy-extension-contract.md](./s1-v2-cutover/13-retire-legacy-extension-contract.md) | 00A gate 後 active v2 cutover + extension 退役 | 需 Gate-0；納入 Gate-1 E2E |
```

對照 README 對其他 plan 的做法（line 308）：

```
| 19 | [19-add-scan-inventory-rules-toml.md](...) | Step 2 executable ...（已實作） | 無 hard gate |
```

- **判定理由**：README 表格沒有 Status 欄，但確實會用「（已實作）」標註完成度（Plan 19）。Plan 13 檔頭是 `Status: backend-complete / frontend-handoff-required`、REP 是 `Status: backend complete / frontend handoff required`，README 對此完全沉默。三方一致性上不算矛盾，但讀 README 的人無法得知 backend 已切換完成、只剩 5 筆 frontend hits。
- **建議處置**：README line 320 補「（backend 已完成；frontend handoff 未完成）」，與 Plan 19 的標註慣例一致。
- **風險**：低

---

### RD-13. `MapBuildManifest` 的 `active_schema_version` / `requested_schema_version` 預設值仍是 v1【C類 正常，經查為刻意設計】

- **位置**：`/Users/linjunting/Local_AI_Health_Doctor/src/kai_mind/core/models/analysis_history.py:148-153`
- **現況**

```python
active_schema_version: Literal["ai-system-map/v1", "ai-system-map/v2"] = (
    "ai-system-map/v1"
)
requested_schema_version: Literal[
    "ai-system-map/v1", "ai-system-map/v2"
] = "ai-system-map/v1"
```

唯一 production 建構點永遠顯式傳值：

```
src/kai_mind/core/services/build_manifest_service.py:98  MapBuildManifest(
src/kai_mind/core/services/build_manifest_service.py:107      active_schema_version=result.active_schema_version,
```
（對比 `core/models/map_build.py:91-93`，`MapBuildResult` 三個欄位預設已是 v2。）

- **判定理由**：初看像「cut 不乾淨」，但反序列化舊 manifest JSON 時該欄位本來就缺，預設成 v1 才是正確的歷史 provenance。production 路徑不依賴預設值，且 `build_manifest_service.py:134` 與 `build_manifest_artifacts.py:180` 都會做雙向 badge mismatch 檢查。判定為可接受。
- **建議處置**：可選——加註解說明「此預設專供 pre-cutover manifest 反序列化」，避免未來誤讀。
- **風險**：低

---

## Plan 13 checkbox 抽查結果表

抽 5 個關鍵 `[x]` 驗收，逐一用 code + live pytest 驗證：

| # | Plan checkbox | 位置 | 驗證方式與證據 | 結果 |
| --- | --- | --- | --- | --- |
| 1 | 「`MapBuildResult` 只有一個 normalized v2 canonical field」 | plan line 556、line 331-333 | `core/models/map_build.py:86` 只有 `ai_system_map: AiSystemMapV2 \| None`；`rg normalized_ai_system_map src tests frontend` 僅命中 `tests/integration/test_v2_active_cutover.py:59` 的反向斷言 `assert "normalized_ai_system_map" not in MapBuildResult.model_fields`。`test_normal_build_defaults_to_one_native_v2_canonical_map` PASSED | ✅ 成立 |
| 2 | 「active `ManualMappingType` 已不含 `NEW_EXTENSION`」 | plan line 430-432、line 562-563 | `core/models/mapping_base.py:13-15` 僅 `EXISTING_SLOT`、`NON_BASELINE_CAPABILITY_CANDIDATE`。`test_active_mapping_enums_do_not_contain_legacy_extension` PASSED；`test_mapping_api_rejects_legacy_type_with_stable_code`、`test_proposal_decision_rejects_legacy_type_with_stable_code` PASSED | ✅ 成立 |
| 3 | 「新 build 預設輸出 `ai-system-map/v2`」 | plan line 552 | `core/services/canonical_output_configuration.py:21` `os.environ.get(ENV, "ai-system-map/v2")`；`core/models/map_build.py:91-93` 三欄預設 v2。`test_operator_output_defaults_to_v2`、`test_normal_build_defaults_to_one_native_v2_canonical_map`、`test_normal_v2_artifact_has_no_legacy_or_rag_only_shape` PASSED | ✅ 成立 |
| 4 | 「public v1 selection 回 `legacy_output_not_selectable`」 | plan line 349-351、line 533 | `canonical_output_configuration.py:29-33`；呼叫點 `map_build_service.py:187,252,292`（三條 build 入口都有）。`test_public_v1_selection_fails_before_writing_artifacts`、`test_public_v1_output_selection_is_rejected` PASSED | ✅ 成立 |
| 5 | 「invalid env fail startup（`invalid_canonical_output_version`）」 | plan line 352-354、line 533 | `canonical_output_configuration.py:20-26`；composition root `web/app.py:138` 在 create_app 時呼叫。`test_invalid_operator_output_version_fails_startup`、`test_invalid_operator_version_prevents_app_startup` PASSED | ✅ 成立 |

Live gate 輸出：

```
$ uv run pytest tests/integration/test_v2_active_cutover.py \
    tests/unit/core/test_canonical_output_configuration.py \
    tests/web/test_legacy_mapping_write_rejection.py -v -p no:randomly
...
============================== 15 passed in 2.82s ==============================
```

補充：checkbox #2 的 runtime 實作點 `web/legacy_mapping_guards.py` 雖然行為正確、有測試覆蓋，但正是 RD-3 指出的 census 盲點——**驗收成立，但這個檔案不在 gate 的守備範圍內**。

---

## 守門結論

**allowlist gate 現在有 4 個已證實的盲點**（RD-3 enum 間接引用整檔逃逸、RD-4 裸字串名稱不比對、RD-5 substring/f-string/註解/docstring/getattr/quoted-annotation 逃逸、RD-6 `schemas/` 等目錄不在掃描範圍），其中 RD-3 的 `src/kai_mind/web/legacy_mapping_guards.py` 是唯一持有 legacy `new_extension_component` 值的 active web 檔案卻完全不在 census，屬實質漏網；

**新增 legacy 引用今天「大部分會、但不保證」被 CI 擋下**——只要新 consumer 是用直接 import、`Name`、module attribute（`system_map.RagSystemMap`）或完整字面值 `"ai-system-map/v1"`，就會立刻 fail closed（已用模擬驗證）；但若透過 enum 屬性、`getattr` 字串、f-string 拼接、substring 訊息、quoted annotation，或把檔案放在 `schemas/`、`scripts/*.py`、`frontend/` root，就會靜默通過。核心 stale/unknown 雙向 fail-closed 機制與 census 數字（35/35）、SHA-256 digest 皆真實可重現，gate 本身沒有造假，只是掃描面不足以宣稱「所有 legacy 引用都被守住」。
