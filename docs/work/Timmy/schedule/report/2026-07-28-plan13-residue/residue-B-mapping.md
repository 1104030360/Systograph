# 殘留稽核 B：mapping-type migration surface + CLI/web adapter

- Repo：`/Users/linjunting/Systograph` @ `0a68ccd`（Plan 13 cutover merge commit）
- 範圍：Plan 13 Task 4/5 的 persisted mapping migration surface、active mapping 家族、
  persisted storage、web/CLI adapter 的 legacy 分支
- 模式：READ-ONLY，未修改任何檔案

---

## 必做實證結果（先貼證據，後面 finding 引用）

### 實證 1：active 寫入路徑封閉性 — PASS

```
$ uv run python -c "from systograph.core.models.mapping_base import ManualMappingCreate; \
    ManualMappingCreate(project_id='p', mapping_type='new_extension_component', decision='confirmed')"

ValidationError
1 validation error for ManualMappingCreate
mapping_type
  Input should be 'existing_slot_mapping' or 'non_baseline_capability_candidate'
  [type=enum, input_value='new_extension_component', input_type=str]
```

`ManualMappingType`（`mapping_base.py:13-15`）只剩 2 個成員，`MappingCandidateType`
（`mapping_candidates.py:27-31`）只剩 4 個。整條 active 家族
（`manual_mapping_service.py:133/156/169`、`manual_mapping_materializer.py:37`、
`manual_mapping_support.py:67`、`mapping_proposal_mapping_factory.py:90/110`）全部用
`match` + `assert_never(unreachable)` 做窮舉，加回 `NEW_EXTENSION` 會 mypy 直接紅。
Plan 13 Task 5「不再建立/接受」在 **backend model 層是徹底的**。

### 實證 2：storage 讀取封閉性 — PASS（fail-closed，無 dict passthrough、無吞 ValidationError）

唯一入口是 `LocalJsonProjectRepository.get / list_for_project`
（`local_json_project_repository.py:76-96`），都委派
`LocalJsonStateStorage.read_model(path, ManualMapping)`。

```python
# src/systograph/core/providers/local_json_state_storage.py:77-90
def read_model(self, path, model_type):
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return model_type.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise StateCorruptionError(f"invalid local state: {path.name}") from exc
```

**沒有** try/except 吞掉 `ValidationError` 後回 `None`／回 dict 的分支——反而是 re-raise。
`LocalJsonStateProvider`（`local_json_state_provider.py:77-84`）只是薄轉發，不做第二套 parse。

migration 之外讀 raw mapping JSON 的只有
`LegacyManualMappingMigrationService._candidates`
（`legacy_manual_mapping_migration_service.py:147-174`，`json.loads` + `glob("*/mappings/*.json")`）。
active 側沒有第二個 raw reader。

但這個 fail-closed 的**失敗形態**有問題，見 RB-4。

### 實證 3：quarantine / backup 產物完整盤點

`rg -n "quarantine|backup" src`（排除 `__pycache__`）的 hit **全部**落在
`legacy_manual_mapping_migration_service.py`，無第二個檔案。實際產物：

| 產物 | 路徑 | 權限 | 產生者 |
| --- | --- | --- | --- |
| backup payload | `<state_root>/migration-backups/<project_seg>/<mapping_seg>.<token>.legacy.json` | `0600` | `_backup` `:338-389` |
| backup index | `<state_root>/migration-backups/<project_seg>/index.json` | `0600` | `_backup` `:355-389` |
| quarantine payload | `<state_root>/migration-quarantine/<project_seg>/<mapping_seg>.<token>.legacy.json` | `0600` | `_quarantine` `:391-417` |
| audit key（寫進 active row，**永久**） | `ManualMapping.audit_metadata.{legacy_mapping_migration_version, legacy_payload_digest, quarantine_ref}` | n/a | `_convert` `:299-309` |

實測（scratchpad probe）：

```
migration status: requires_manual_review | cutover_blocked: True
backup dir exists: True
quarantine dir exists: True
--- perms ---
0o755 migration-backups/project_demo
0o600 migration-backups/project_demo/index.json
0o600 migration-backups/project_demo/mapping_incomplete.c5ffe97df4b971f0.legacy.json
0o755 migration-quarantine/project_demo
0o600 migration-quarantine/project_demo/mapping_incomplete.c5ffe97df4b971f0.legacy.json
```

`0600` owner-only 符合 Plan 13 Task 4 條款。目錄名 `migration-backups` /
`migration-quarantine` **沒有出現在 Plan 13、Plan 15 或任何 `docs/` 檔案**（見 RB-5）。

### 實證 4：`legacy_mapping_type_read_only` 消費端

```
src/systograph/web/legacy_mapping_guards.py:37          （唯一 producer）
tests/web/test_legacy_mapping_write_rejection.py:50,119（POST /api/mappings、POST proposal decision）
docs/API-GUIDE.md:988                                 （422 錯誤碼表）
docs/work/Meeting-Sync/.../frontend-*.md              （前端 handoff 說明 ×2）
docs/work/Timmy/schedule/plan/.../13-*.md:426、15-*.md:215
frontend/API_CONTRACT.md                              ← 0 hit
frontend/src/**                                       ← 0 hit
```

覆蓋 2 個 POST endpoint；`PATCH /api/mappings/{mapping_id}` 無 guard（見 RB-8）。

---

## Findings

### RB-1. `web/legacy_mapping_guards.py` 對 Plan 13 executable allowlist 是完全隱形的（AST census 與 rg 雙盲）【B類】

- **位置**：`src/systograph/web/legacy_mapping_guards.py:9-13`；census 在
  `tests/contracts/test_v2_cutover_consumer_allowlist.py:20-28, 334-350`

- **現況**

```python
# src/systograph/web/legacy_mapping_guards.py:9-13
from systograph.core.services.legacy_manual_mapping_migration_service import (
    LegacyManualMappingType,
)

_LEGACY_MAPPING_TYPE = LegacyManualMappingType.NEW_EXTENSION.value
```

  census 只認 4 個名字 + 2 個字面值：

```python
# tests/contracts/test_v2_cutover_consumer_allowlist.py:20-28
LEGACY_NAMES = frozenset({
    "RagSystemMap", "ExtensionComponent",
    "SystemMapValidationService", "new_extension_component",
})
LEGACY_LITERALS = frozenset({"ai-system-map/v1", "new_extension_component"})
```

  `LegacyManualMappingType.NEW_EXTENSION.value` 的 AST 是
  `Attribute(attr='value', value=Attribute(attr='NEW_EXTENSION', value=Name(id='LegacyManualMappingType')))`
  ——`value` / `NEW_EXTENSION` / `LegacyManualMappingType` 三個名字**都不在** `LEGACY_NAMES`，
  檔案裡也沒有 `"new_extension_component"` 字面值。

- **證據**（直接跑 census 的 `_legacy_symbol` 邏輯）

```
census AST hits for legacy_mapping_guards.py: NONE (blind spot confirmed)

plain-text rg of Plan13 Task5 command would match?
  ExtensionComponent -> False
  RagSystemMap -> False
  SystemMapValidationService -> False
  ai-system-map/v1 -> False
  new_extension_component -> False
```

  也就是說 Plan 13 Task 5 明列的 gate 指令
  `rg -n "RagSystemMap|ExtensionComponent|new_extension_component|ai-system-map/v1" src tests frontend docs`
  **同樣掃不到這個檔案**。allowlist 現有 35 筆記錄裡沒有任何一筆 path 是
  `src/systograph/web/legacy_mapping_guards.py`。

- **判定理由**：Plan 13 Task 5 最後一條「Task 1 allowlist 是 **executable gate**；backend hit
  只能命中 `operator_rollback`、`migration_only` 或測試明列的 legacy evidence」。這個檔案是
  Plan 13 自己在 `0a68ccd` 新建、專門處理 legacy mapping type 的 backend surface，卻既不在
  allowlist、也不被 gate 指令看見。census 用「`.value` 間接引用」規避了自己的 gate，屬於
  **無人追蹤的過渡寫法**。（Plan 15 Task 3b 的 rg 因為包含 `LegacyManualMapping` 關鍵字才會撈到，
  但那是 Plan 15 的 gate，Plan 13 的 gate 在此是失效的。）

- **建議處置**：補進 Plan 15 清單 + 修 census。兩個修法擇一：
  (a) `LEGACY_NAMES` 加入 `LegacyManualMappingType` / `NEW_EXTENSION`；
  (b) 在 allowlist 加一筆 `src/systograph/web/legacy_mapping_guards.py` 記錄，
  classification=`migration_only`，removal_plan 指向 Plan 15 Task 3b bullet 5。
  兩者都做最好——單純加 allowlist 記錄會因為 census 掃不到而變成 `stale` 而 fail。

- **風險**：中。目前檔案行為正確，但 gate 已被證明無法阻擋「用 `.value` 間接引用 legacy 常數」
  的新增 hit——同一招可以再被用一次而不觸發任何測試。

---

### RB-2. Plan 15 Task 3b 要刪的 module 裡有 active（非 migration）消費者：`LegacyManualMappingType`【B類】

- **位置**：`src/systograph/core/services/legacy_manual_mapping_migration_service.py:32-33`
  ← 被 `src/systograph/web/legacy_mapping_guards.py:9-13` import

- **現況**

```python
# legacy_manual_mapping_migration_service.py:32-33
class LegacyManualMappingType(StrEnum):
    NEW_EXTENSION = "new_extension_component"
```

  這個 enum 有兩個消費端，用途完全相反：
  1. `LegacyManualMappingDTO.mapping_type`（`:42`）與 `_candidates`（`:170`）—— migration-only，Task 3b 要刪
  2. `legacy_mapping_guards._LEGACY_MAPPING_TYPE`（`:13`）—— **active fail-closed 防線，Task 3b 要留**

- **證據**（Plan 15 Task 3b 自己的 rg gate 輸出）

```
$ rg -n "LegacyManualMapping|migrate-legacy-mappings|legacy_manual_mapping_migration|new_extension_component" src
src/systograph/cli/migrate_legacy_mappings_command.py:8,9,14,33
src/systograph/web/legacy_mapping_guards.py:9,10,13          ← 這三行必須「不是 remove」
src/systograph/core/services/legacy_manual_mapping_migration_service.py:32,33,36,42,99,170,210,294,340,393
```

- **判定理由**：Plan 15 Task 3b 第 1 條要求「刪除 `LegacyManualMappingDTO` 與**任何仍能 parse
  `new_extension_component` 的 migration-only model**」，第 2 條要求「刪除
  `LegacyManualMappingMigrationService`」——照字面做會整個模組消失，`LegacyManualMappingType`
  一併消失。但同一 Task 3b 第 5 條又要求「normal mapping repository／API／UI：**拒絕** legacy
  mapping shape，回傳穩定 error（沿用或收斂 Plan 13 的 `legacy_mapping_type_read_only`）」——
  guard 必須活下來。兩條互相矛盾，且 Task 3b 從頭到尾**沒有提到 `LegacyManualMappingType` 這個名字**，
  也沒說它該搬去哪。這是 census 盲點（RB-1）造成的直接後果：guard 對 Plan 13 隱形，所以 Plan 15
  的 handoff 表也漏了它。

- **建議處置**：補進 Plan 15 清單。明確寫成「執行 Task 3b 時先把
  `_LEGACY_MAPPING_TYPE = "new_extension_component"` 內聯進 `web/legacy_mapping_guards.py`
  （或搬到 `web/` 自有常數），切斷對 migration module 的 import，再刪 module」。

- **風險**：高。照現行 Task 3b 字面執行會 `ImportError` 打爛整個 FastAPI app 啟動
  （`mapping_routes.py:18`、`mapping_proposal_routes.py:26` 都 import 它）；就算修掉 import，
  隨手刪 guard 就等於重新打開 legacy write surface，把 Plan 13 Task 5 的成果整個回退。

---

### RB-3. `_legacy_detail_scan` / `legacy_latest_build_fallback` 是 Plan 13 之前的過渡寫法，production 不可達，且 13/15 都沒追蹤【B類】

- **位置**：`src/systograph/web/routes/detail_scan_routes.py:59-71`（分歧點）、`:163-208`（實作）

- **現況**

```python
# detail_scan_routes.py:58-71
build_result = store.build_result(payload.project_id)
if (
    payload.build_id is None
    and build_result is not None
    and build_result.lineage is None      # ← 觸發條件
):
    return _legacy_detail_scan(...)
...
# detail_scan_routes.py:202-208
return DetailScanResponse(
    ...
    warnings=["legacy_latest_build_fallback"],
)
```

- **證據**

  1. production 不可達，證據鏈完整：

```
$ rg -n "InMemorySessionStore|PersistentSessionStore" src
src/systograph/web/app.py:233:    app.state.session_store = session_store or PersistentSessionStore(
src/systograph/web/session_store.py:70:class InMemorySessionStore:      ← src/ 內無任何使用者
src/systograph/web/session_store.py:134:class PersistentSessionStore:
```

  `PersistentSessionStore.build_result`（`session_store.py:216-228`）唯一產出路徑是
  `self._manifest_service.load(manifest)`，而

```
src/systograph/core/models/analysis_history.py:142:    lineage: MapBuildLineage   ← 非 Optional，required
src/systograph/core/services/build_manifest_service.py:179:            lineage=manifest.lineage,   ← 無條件賦值
```

  → `build_result.lineage is None` 在 production 恆為 False。

  2. **它不是 Plan 13 的產物**：

```
$ git log --oneline -S "_legacy_detail_scan" -- src/systograph/web/routes/detail_scan_routes.py
577f15b feat(core): #202 完成 Phase2 S1 pipeline-core 後端 (#248)

$ git log --oneline -S "legacy_latest_build_fallback"
577f15b feat(core): #202 完成 Phase2 S1 pipeline-core 後端 (#248)
```

  Plan 13 的 merge 是 `0a68ccd`（#240 / PR #257），比 `577f15b` 晚。

  3. 無任何計畫追蹤：`legacy_latest_build_fallback` 這個字串在 `src/`、`tests/`、
     `frontend/`、`docs/API-GUIDE.md` 都只出現一次（就是 `:207` 本身），
     只有 phase2.5 的 `audit-B-routes.md` 提過。Plan 13 的「相關檔案」列了
     `detail_scan_routes.py` 但只講 v2 input/output，Plan 15 Task 3b 完全沒提。

- **判定理由**：符合 B類定義——「過渡 scaffolding 不在 allowlist 也不在 Plan 15 Task 3b 清單」。
  它是 #202 引入的「舊 session build 沒有 lineage 時退回 in-place detail scan」相容路徑，
  在 Plan 13 Task 6 把 `BuildCommitService` 變成唯一 commit state machine、
  `MapBuildManifest.lineage` 變成 required 之後，前提條件已永久消失。
  **它不是 Plan 13 建的，所以 Plan 15 的「Plan 13 Task 4 handoff」表結構性地不會涵蓋它。**

- **建議處置**：立刻可刪（46 行 dead code：`:59-71` 分歧 + `:163-208` 函式，連帶可移除
  `DetailScanService` / `ViewerSessionService` / `Path` / `viewer_session_service` 這幾個
  只為它存在的 route 依賴）。若不想在 Plan 13 範圍外動 route，最低限度要**補進 Plan 15 清單**，
  並同時修 `docs/API-GUIDE.md`（見 RB-8 註記：文件記的是 `latest_build_fallback`，
  少了 `legacy_` 前綴，是另一個字串）。

- **風險**：低（刪除本身）／中（放著不管）。放著的成本是：它是 route 層唯一還會呼叫
  `viewer_service.build_canonical(...)` 並繞過 `BuildCommitService` 直接
  `store.save_build_result(updated, ...)` 的路徑（`:187-201`），等於在 Plan 13 Task 6 的
  atomic visibility contract 上留了一個沒有 manifest、沒有 CAS promotion 的側門。

---

### RB-4. quarantined 未完成 row 留在原地會讓 active repository 整個 project 讀取炸掉——與 Plan 13 「可以留作 migration evidence」的敘述不符【B類】

- **位置**：`legacy_manual_mapping_migration_service.py:227-250`（不完整 row 不改寫原檔）
  ↔ `local_json_project_repository.py:84-96` + `local_json_state_storage.py:87-90`

- **現況**

```python
# legacy_manual_mapping_migration_service.py:227-250
if not complete:
    if apply:
        try:
            self._backup(legacy, payload, input_digest)
            self._quarantine(legacy, payload, input_digest, quarantine_ref or ...)
        except OSError:
            return ...  # failed
    return LegacyMappingMigrationItem(
        mapping_id=legacy.mapping_id,
        status="requires_manual_review",
        input_digest=input_digest,
        quarantine_ref=quarantine_ref,
    )
    # ← 注意：原本的 projects/<p>/mappings/<m>.json 完全沒被動過，
    #        仍然是 mapping_type="new_extension_component"
```

- **證據**（scratchpad probe，真實跑 apply 後再用 active repository 讀同一個 state dir）

```
migration status: requires_manual_review | cutover_blocked: True
items: [('mapping:incomplete', 'requires_manual_review', 'quarantine:c5ffe97df4b971f0')]
on-disk mapping_type after apply: new_extension_component
backup dir exists: True
quarantine dir exists: True

--- active repository read of the same state dir ---
RAISED: StateCorruptionError | invalid local state: mapping_incomplete.json
```

  `list_for_project` 是 list comprehension，沒有 per-file try/except
  （`local_json_project_repository.py:87-92`），所以**一個 quarantined row 會讓整個 project
  的 mapping 列表無法讀取**——`GET /api/mappings?project_id=...` 與所有走
  `ManualMappingService.list_for_project` 的流程（含
  `ProposalManualMappingFactory._reject_duplicate_confirmed_mapping`
  `mapping_proposal_mapping_factory.py:182`，即整條 proposal decision 路徑）一起 500。

- **判定理由**：這**不是** A類——沒有任何 active path 能寫出或讀出 legacy shape，
  `StateCorruptionError` 是正確的 fail-closed。但 Plan 13 Task 4 最後一條寫的是
  「其他 unresolved quarantined rows **可以留作 migration evidence**，但會繼續阻擋 Plan 15 cleanup」，
  這句話描述的是一個「可以共存」的狀態，實際上不能共存：留著就等於該 project 的 mapping
  子系統整個不可用。Plan 13/15 都沒有規定 quarantine 後原檔該不該搬走／改名／加 `.quarantined`
  副檔名，也沒有任何 code 負責把它移出 `projects/*/mappings/` glob 範圍。
  這是**無人追蹤的過渡狀態語意缺口**。

- **建議處置**：補進 Plan 15 清單（也建議回頭修 Plan 13 Task 4 敘述）。技術上二選一：
  (a) `_quarantine` 成功後把原檔 move 出 `mappings/`（quarantine 已有完整 payload 副本，不會丟資料）；
  (b) `list_for_project` 對單檔 `StateCorruptionError` 降級成 warning + skip。
  (a) 較符合 Plan 13「先搬家，再拆舊門」的原則；(b) 會引入 Plan 15 明令禁止的 silent dual-read 風味，不建議。

- **風險**：中。只在真的有「CONFIRMED/缺欄位」legacy row 的既有安裝才會踩到，
  但踩到就是整個 project 的 mapping API 500，而且 migration report 顯示的是
  `requires_manual_review`（聽起來像「稍後處理即可」），誤導性強。

---

### RB-5. Plan 15 Task 3b 描述的「state-side migration report writers」不存在；真正的 state 產物目錄名反而沒被任何文件記載【D類】

- **位置**：Plan 15 `15-*.md:212-213` ↔ `legacy_manual_mapping_migration_service.py:338-421`、
  `migrate_legacy_mappings_command.py:33-38`

- **現況**

  Plan 15 Task 3b 第 4 條寫：

  > 清除 quarantine／backup index helpers 與不再需要的 **state-side migration report writers**；
  > 文件記載既有 backup 目錄是否人工保留、何時可刪（不得靜默留 code path）。

  但 code 裡 report **從來不寫進 state**：

```python
# cli/migrate_legacy_mappings_command.py:33-38
report = LegacyManualMappingMigrationService(state_dir).migrate(apply=apply)
typer.echo(report.model_dump_json(indent=2))   # ← 只印到 stdout
if apply and report.cutover_blocked:
    raise typer.Exit(code=1)
```

  `LegacyMappingMigrationReport`（`:77-96`）是純回傳值，`_report`（`:445-485`）是 `@staticmethod`
  純計算。`self._storage.write_json` 只在 `_backup` / `_quarantine` 出現。

- **證據**

```
$ rg -n "migration-backups|migration-quarantine" src tests docs scripts frontend
src/systograph/core/services/legacy_manual_mapping_migration_service.py:347   / "migration-backups"
src/systograph/core/services/legacy_manual_mapping_migration_service.py:401   / "migration-quarantine"
tests/unit/core/test_legacy_manual_mapping_migration_service.py:49,210
                                                    ← docs/ 0 hit，plan 0 hit
```

- **判定理由**：D類（文件與 code 不一致）。Task 3b 要刪一個不存在的東西（state-side report writer），
  同時要求「文件記載既有 backup 目錄是否人工保留、何時可刪」——但**該目錄叫什麼名字從未被寫下來**。
  執行 Plan 15 的人只能靠讀 code 才知道要跟使用者說「請自行處理 `~/.systograph/migration-backups/`
  與 `~/.systograph/migration-quarantine/`」。這是可預期會漏掉的 retention 條款。

- **建議處置**：修文件。把 Task 3b 第 4 條改寫為：
  (a) 刪掉「state-side migration report writers」（不存在）；
  (b) 明確寫出兩個目錄的絕對相對路徑 `<SYSTOGRAPH_STATE_DIR>/migration-backups/`、
      `<SYSTOGRAPH_STATE_DIR>/migration-quarantine/`，以及保留/刪除決策與時點。
  同時建議把這兩個路徑補進 `docs/MODEL-CONTRACT.md` 或 CLAUDE.md 的 State persistence 段落
  （目前那段只提「project/scan/build lineage, manual mappings, latest pointer」）。

- **風險**：低（安全性）／中（隱私）。backup 目錄依 Plan 13 定義**含 legacy free-text**，
  沒有文件化的保留策略等於 local-first privacy 條款缺一角。

  附帶低風險觀察（同一區塊，不另立條目）：`LocalJsonStateStorage.write_json`
  （`local_json_state_storage.py:55-63`）是 `open temp → write → fsync → chmod(0600) → replace`。
  在 `open` 到 `chmod` 之間，含 legacy free-text 的暫存檔是預設 umask 權限（實測目錄為 `0755`）。
  最終檔案 `0600` 正確，但寫入窗口內短暫可讀。若要嚴格符合「必須使用平台可提供的 owner-only access」，
  應改用 `os.open(..., 0o600)` 或先 `os.umask`。

---

### RB-6. 遷移後永久留在 active `ManualMapping.audit_metadata` 的 legacy key 無人追蹤【B類】

- **位置**：`legacy_manual_mapping_migration_service.py:299-309`（寫入）、
  `:162-172` 與 `:196-208`（讀回做 idempotence 判斷）

- **現況**

```python
# legacy_manual_mapping_migration_service.py:299-309
audit = dict(legacy.audit_metadata)
audit.update({
    "legacy_mapping_migration_version": LEGACY_MAPPING_MIGRATION_VERSION,
    "legacy_payload_digest": input_digest,
})
if quarantine_ref is not None:
    audit["quarantine_ref"] = quarantine_ref
```

  這三個 key 被寫進**active `ManualMapping`** 的 `audit_metadata: dict[str, str]`
  （`mapping_base.py:43`，型別是自由 dict，不受 enum 收斂保護），並且會被
  `local_json_project_repository.save/get` 原封不動 round-trip，永久留在 state。

- **證據**

```
$ rg -n "legacy_mapping_migration_version|legacy_payload_digest" src tests docs
src/systograph/core/services/legacy_manual_mapping_migration_service.py:165,198,205,302,305
tests/unit/core/test_legacy_manual_mapping_migration_service.py:80,83
                                                    ← plan 13 / plan 15 皆 0 hit
```

  Plan 13 Task 4 轉換矩陣只規定了 `quarantine_ref`（第四列：「將原 payload digest、opaque
  `quarantine_ref` 與 warning 寫入 audit metadata」）；`legacy_mapping_migration_version`
  與 `legacy_payload_digest` 兩個 key 是實作自行新增的，兩份計畫都沒有提到名字。

- **判定理由**：B類。這是 migration 的持久化副作用，Plan 15 Task 3b 的 rg gate
  （`LegacyManualMapping|migrate-legacy-mappings|legacy_manual_mapping_migration|new_extension_component`）
  **掃不到** `legacy_mapping_migration_version`（底線分隔、非 camelCase，
  `legacy_manual_mapping_migration` 這個 pattern 不匹配 `legacy_mapping_migration_version`）。
  Task 3b 刪掉 module 後 `LEGACY_MAPPING_MIGRATION_VERSION` 常數消失，但**字串仍活在使用者的
  state JSON 裡**，且再也沒有任何 code 能解釋它的意義。

- **建議處置**：補進 Plan 15 清單。決策二選一並寫進文件：
  (a) 明示保留為 audit provenance（則需在 `docs/MODEL-CONTRACT.md` 記錄這三個 key 的語意，
      因為 Plan 15 後將不再有任何 code 定義它們）；
  (b) Task 3b 順手加一段 state sweep 清掉。
  建議 (a)——這是 evidence-based 稽核痕跡，刪掉反而違反可追溯原則；但**必須文件化**。

- **風險**：低。不影響 runtime，但會製造「state 裡有沒人認得的欄位」的長期認知債。

---

### RB-7. `cutover_blocked` 比 Plan 13 轉換矩陣第三列嚴格（任何 `requires_manual_review` 都擋，不只 `CONFIRMED`）【D類】

- **位置**：`legacy_manual_mapping_migration_service.py:481-483`

- **現況**

```python
# legacy_manual_mapping_migration_service.py:481-483
cutover_blocked=bool(
    counts["requires_manual_review"] or counts["failed"]
),
```

  `_migrate_one`（`:227-250`）判斷 `requires_manual_review` 的條件只看
  `extension_id/name/kind` 是否齊全（`complete`，`:214-221`），**完全不看 `decision`**。

- **證據**：Plan 13 Task 4 轉換矩陣第三列原文：

  > | 任一 legacy row 缺少必要 extension 欄位 | `requires_manual_review`，不建立猜測值 |
  > 原 row 只留 migration quarantine；**若 decision 是 `CONFIRMED`，阻擋 v2 cutover** |

  以及 Task 4 倒數第三條：「所有 `CONFIRMED` legacy rows 都完成轉換後才可 flip backend v2；
  其他 unresolved quarantined rows 可以留作 migration evidence」。

  實測（probe 用的是 `decision="confirmed"` 的 row，符合規格；但一個
  `decision="rejected"` 且缺欄位的 row 依現行 code 同樣會 `cutover_blocked=True`）。

- **判定理由**：D類。方向是**更保守**（fail-safe），不是漏洞，但 code 與計畫敘述不一致：
  計畫明說非 `CONFIRMED` 的 quarantined row「可以留作 migration evidence」不擋 cutover，
  code 一律擋。這會讓依 report 判斷「能不能 flip」的人得到與計畫不同的答案。
  搭配 RB-4，實際上 code 的嚴格版本更正確（因為任何留在 `mappings/` 的 legacy row 都會炸
  `list_for_project`），但計畫沒有記錄這個推理。

- **建議處置**：修文件。把 Plan 13 Task 4 矩陣第三列與 Task 4 倒數第三條，
  改成「**任何** unresolved `requires_manual_review` row 都阻擋 cutover」，
  並註明理由是 active repository 對 legacy shape fail-closed（引 RB-4）。

- **風險**：低。

---

### RB-8. `PATCH /api/mappings/{id}` 沒有掛 guard，legacy payload 回的是 pydantic 泛用錯誤而非穩定錯誤碼；`legacy_mapping_type_read_only` 也沒進 `frontend/API_CONTRACT.md`【D類】

- **位置**：`src/systograph/web/routes/mapping_routes.py:58-61`（無 `dependencies=`）；
  對照 `:39-43`（POST 有掛）與 `mapping_proposal_routes.py:97-101`（有掛）

- **現況**

```python
# mapping_routes.py:39-43  — 有 guard
@router.post(
    "/api/mappings",
    response_model=ManualMapping,
    dependencies=[Depends(reject_legacy_mapping_type)],
)

# mapping_routes.py:58-61  — 無 guard
@router.patch("/api/mappings/{mapping_id}", response_model=ManualMapping)
def update_mapping(
    mapping_id: str,
    payload: ManualMappingUpdate,
```

- **證據**

```
$ uv run python -c "from systograph.core.models.mapping_base import ManualMappingUpdate; \
    ManualMappingUpdate(mapping_type='new_extension_component', decision='confirmed')"
1 validation error for ManualMappingUpdate
mapping_type
  Extra inputs are not permitted [type=extra_forbidden, input_value='new_extension_component', ...]
```

  `legacy_mapping_type_read_only` 的文件/測試覆蓋：

```
tests/web/test_legacy_mapping_write_rejection.py:50   POST /api/mappings
tests/web/test_legacy_mapping_write_rejection.py:119  POST /api/mapping-proposals/{id}/decision
docs/API-GUIDE.md:988                                 有列
frontend/API_CONTRACT.md                              0 hit  ← 前端契約文件沒有這個錯誤碼
```

- **判定理由**：D類。**安全性上沒破口**——`ManualMappingUpdate` 根本沒有 `mapping_type` 欄位、
  `MappingModel` 是 `extra="forbid"`，所以 PATCH 永遠改不了 mapping type。但 Plan 15 Task 3b
  第 5 條要求的是「normal mapping repository／**API**／UI：拒絕 legacy mapping shape，
  回傳**穩定 error**」，PATCH 回的是 pydantic 陣列格式的 `extra_forbidden`，前端無法用同一個
  `detail === "legacy_mapping_type_read_only"` 分支處理。且 `frontend/API_CONTRACT.md`
  （CLAUDE.md 列為 HTTP contract 的權威文件之一）完全沒收錄這個錯誤碼，
  而前端 handoff 文件（`meeting_sync_2026_07_28/frontend-v2-cutover-handoff.md`；原子集檔已併入）
  卻要求前端針對它做 UX 處理。

  順帶（同屬 D類，併此條）：`detail_scan_routes.py:207` 的 `legacy_latest_build_fallback`
  在 `docs/API-GUIDE.md:638` 被寫成 `latest_build_fallback`（少 `legacy_` 前綴），
  而那個無前綴版本其實是 `trace_routes.py:78` 的另一個 warning。兩個相近字串只有一個進了文件。

- **建議處置**：修文件為主。
  (1) 把 `legacy_mapping_type_read_only`（與 `legacy_output_not_selectable`）補進
      `frontend/API_CONTRACT.md`；
  (2) 若要 PATCH 也回穩定碼，把 `dependencies=[Depends(reject_legacy_mapping_type)]`
      加到 `mapping_routes.py:58` 的 decorator（guard 本身已支援 top-level `mapping_type`，
      `legacy_mapping_guards.py:19`，零改動）；
  (3) `docs/API-GUIDE.md:638` 補上 `legacy_latest_build_fallback`（或依 RB-3 直接刪 code）。

- **風險**：低。

---

### RB-9. Plan 13 「相關檔案」清單漏列自己新建/修改的三個 legacy 停寫檔案【D類】

- **位置**：Plan 13 `13-*.md:124-193` 的 Reuse/Modify/Create/Test 清單

- **現況**：Plan 13 在 `0a68ccd` 實際新建/修改但**沒有列進計畫**的檔案：

| 檔案 | 角色 | 在 Plan 13 清單？ |
| --- | --- | --- |
| `src/systograph/web/legacy_mapping_guards.py` | Create（Task 4/5 的 API fail-closed 核心） | ✗ |
| `src/systograph/web/routes/mapping_routes.py` | Modify（掛 guard） | ✗（只列了 `mapping_proposal_routes.py`） |
| `tests/web/test_legacy_mapping_write_rejection.py` | Create（Task 4「Normal API 立即拒絕」的唯一測試） | ✗ |

- **證據**

```
$ git log --oneline -- src/systograph/web/legacy_mapping_guards.py
0a68ccd feat(core): #240 Phase2 Plan 13 ai-system-map/v2 active cutover (#257)
```

  Plan 13 `:170-175` 的 Modify 清單有 `web/schemas.py`、`web/routes/scan_routes.py`、
  `web/routes/detail_scan_routes.py`、`web/routes/trace_routes.py`、
  `web/routes/mapping_proposal_routes.py`、`web/session_store.py`——就是沒有
  `web/legacy_mapping_guards.py` 與 `web/routes/mapping_routes.py`。

- **判定理由**：D類。這是 RB-1（census 盲點）與 RB-2（Plan 15 handoff 漏項）的共同上游成因：
  guard 從一開始就沒被登記在 Plan 13 的 file inventory，所以既沒進 allowlist、
  也沒被 Plan 15 的 Task 4 handoff 表繼承。

  另外查了 `web/session_store.py`（Plan 13 Modify 清單內）：現況**沒有任何 legacy 殘留**——
  全檔無 `legacy` / `RagSystemMap` / `new_extension_component` 字樣，
  `PersistentSessionStore.build_result` 只走 `manifest_service.load`（唯一 loader），
  `save_committed_build_projection`（`:53-67`）的 fallback 只加
  `session_projection_save_failed` warning，不觸碰 schema。**判定乾淨**。

- **建議處置**：修文件。把三個檔案補進 Plan 13 「相關檔案」清單（標註為 backend-complete 已完成），
  並在 Plan 15 Task 3b 的 handoff 表加一列（見 RB-2）。

- **風險**：低（單看）／中（作為 RB-1/RB-2 的根因）。

---

### RB-10. active normal path 仍直接 import v1 model module `core/models/system_map.py`，與 Plan 13 Task 5「normal build path 不得 import」矛盾；census 因只掃 4 個符號而看不到【B類】

- **位置**：`src/systograph/core/services/manual_mapping_materializer.py:10-13`、
  `manual_mapping_support.py:11`、`detail_scan_service.py:10`、
  `web/routes/detail_scan_routes.py:11`、`web/schemas.py:39`、
  `component_detection_service.py`、`endpoint_detection_service.py`、
  `flow_derivation_service.py`、`risk_hint_service.py`、`project_scan_service.py`、
  `canonical_evidence_service.py`、`scan_boundary_review_service.py`、
  `component_bridge_registry.py`、`code_path_scan_service.py`、
  `detail_scan_build_service.py`、`query_trace_service.py` 等（共 37 個檔案）

- **現況**

```python
# src/systograph/core/services/manual_mapping_materializer.py:10-13
from systograph.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
)

# src/systograph/web/schemas.py:39
from systograph.core.models.system_map import DetailScanResult
```

  而 `core/models/system_map.py` 自己的檔頭寫得很清楚：

```python
# src/systograph/core/models/system_map.py:1,16,24
# 這個檔案負責：定義 ai-system-map/v1 的 Pydantic 資料契約（舊版 / v1 map）。
"""Pydantic models for the ai-system-map/v1 contract."""
SCHEMA_VERSION = "ai-system-map/v1"
```

- **證據**

```
$ rg -ln "from systograph.core.models.system_map import" src | wc -l
      37
```

  其中屬於 normal active path 的至少有：`component_detection_service.py`、
  `endpoint_detection_service.py`、`flow_derivation_service.py`、`risk_hint_service.py`、
  `project_scan_service.py`、`manual_mapping_materializer.py`、`manual_mapping_support.py`、
  `detail_scan_service.py`、`detail_scan_build_service.py`、`query_trace_service.py`、
  `system_map_v2_normalize_service.py`、`web/schemas.py`、`web/routes/detail_scan_routes.py`。

  census 掃不到，因為它只認 `RagSystemMap` / `ExtensionComponent` /
  `SystemMapValidationService` / `new_extension_component` 四個名字
  （`test_v2_cutover_consumer_allowlist.py:20-27`）——
  `ComponentInstance`、`ComponentSlot`、`UnmappedComponent`、`Evidence`、
  `DetailScanResult`、`ScanDepth`、`CodePathStep`、`DetailScanFinding`、`Edge`、`Flow`、
  `RiskHint` 這些**同一個 v1 module 內的其他 DTO**全部不在名單上。

- **判定理由**：B類。Plan 13 Task 5 第 4 條白紙黑字：
  「v1 schema/fixture、Legacy DTO、adapter 與 operator rollback serializer 明確標示
  legacy/read-only；**normal build path 不得 import**」，且該 checkbox 已被標成 `[x]`。
  實際上 scan phase（Step 1-5）的整套 intermediate fact DTO 仍住在 v1 module 裡並被 active path
  直接 import。allowlist 只把 `core/models/system_map.py` 的三個符號分類為 `migration_only`
  （`:137-148`），沒有處理「同一 module 的其他 DTO 是 active 共用」這個事實。

  這**不是 A類**——這些 DTO 是 scan-phase 中介事實，不是 canonical output 形狀；
  active canonical output 確定是 `AiSystemMapV2`（實證 1/2 已證 mapping 側封閉、
  `map_build_pipeline.py` 只在 `_canonical_output_version == "ai-system-map/v1"` 時走 rollback）。
  但它讓 Task 5 那個 `[x]` checkbox 在字面上是假的，且 Plan 15 Task 2/3
  （「移除 v1 write path」「退役 Extension product surface」）執行時會撞上
  「刪不掉 `system_map.py`，因為 37 個檔案在用」的意外阻礙。

- **建議處置**：補進 Plan 15 清單 + 改名／拆檔。建議把 scan-phase 共用 DTO
  （`Evidence`、`ComponentInstance`、`ComponentSlot`、`UnmappedComponent`、`Edge`、`Flow`、
  `RiskHint`、`DetailScanResult`、`ScanDepth`、`CodePathStep`、`DetailScanFinding`）
  從 `core/models/system_map.py` 拆到 `core/models/scan_facts.py`（或既有的 `models/scan.py`），
  讓 `system_map.py` 只剩真正的 v1 map contract（`RagSystemMap`、`ExtensionComponent`、
  `SCHEMA_VERSION`），Plan 15 才能整檔刪除。同時修 Plan 13 Task 5 該條 checkbox 的敘述
  （或降級為「不得 import v1 **map contract**」）。

- **風險**：中。純機械式拆檔，但涉及 37 個 import；不做的話 Plan 15 Task 2/3 會卡住或被迫
  留下一個「名字叫 v1、內容一半是 active」的模組。

---

## C類：合法保留（Plan 15 Task 3b 已追蹤），一句帶過

以下全部已被 Plan 15 Task 3b handoff 表明確涵蓋，**現況正確、不需動作**：

- `LegacyManualMappingDTO`（`:36-57`）— Task 3b bullet 1；`extra="allow"` 是刻意的
  （讓未知 legacy 欄位不炸 migration），只在 migration module 內使用。
- `LegacyManualMappingMigrationService`（`:99-485`）與其全部 private helper
  （`_candidates` `:147`、`_migrate_project` `:176`、`_migrate_one` `:187`、`_convert` `:292`、
  `_backup` `:338`、`_quarantine` `:391`、`_quarantine_ref` `:419`、`_failed_item` `:423`、
  `_project_failure_items` `:436`、`_report` `:445`）— Task 3b bullet 2/4；
  逐一比對後，**除了 `LegacyManualMappingType`（RB-2）之外全部被涵蓋**，沒有漏網 helper。
- `LegacyMappingMigrationItem` / `LegacyMappingMigrationReport`
  （`:60-96`，`legacy-mapping-migration-report/v1`）與 `LEGACY_MAPPING_MIGRATION_VERSION`
  （`:27-29`）— 隨 module 一併刪除，Task 3b bullet 2 涵蓋。
- `migrate-legacy-mappings` CLI（`cli/migrate_legacy_mappings_command.py` 全檔 +
  `cli/main.py:6-8,17` 註冊）— Task 3b bullet 3。預設 `--dry-run`、`--apply` 才寫入、
  `cutover_blocked` 時 exit 1，符合 Plan 13 Task 4 規格。
- `migration-backups` / `migration-quarantine` 目錄產物 — Task 3b bullet 4 概念上涵蓋
  （但目錄名未文件化，見 RB-5）。
- operator rollback 家族（`legacy_v1_rollback_service.py`、
  `system_map_materialization_service.py`、`system_map_normalize_service.py`、
  `canonical_output_configuration.py`、`map_build_pipeline.py` 的 v1 分支）—
  allowlist 分類 `operator_rollback`，Plan 15 Task 2 涵蓋。非本次分區。
- v1 read/migration 家族（`canonical_map_loader.py` v1 分支、
  `system_map_v1_to_v2_adapter.py`、`system_map_validation_service.py`、
  `viewer_legacy_compatibility.py`）— allowlist 分類 `migration_only`，Plan 15 Task 4 涵蓋。
- **僅為識別符/註解、非 active legacy 分支**（逐一看過，判定乾淨）：
  `graph_projection_service.py:178,324` / `reference_capability_assessment_service.py:137` /
  `detail_scan_service.py:227,263` / `query_trace_service.py:328` 讀的
  `component.metadata["legacy_slot"]` 是 **v2 canonical component 的 metadata key**，
  由 active 的 `system_map_v2_normalize_service.py:128` 寫入，用來保留 `rag-core-v1` 13 slot
  的可讀前綴，符合 CLAUDE.md「Slot 只指 legacy `rag-core-v1` 的 13 slots」；
  `scan_snapshot_service.py:97` 的 `legacy_inventory_policy_unknown` 是 inventory 子系統
  的 warning 字串，與 mapping/v1 無關；
  `mapping_proposal_deterministic.py:77` 的 "legacy slot" 只是 rationale 文案。
- `web/session_store.py` — Plan 13 Modify 清單內，逐行看過**無任何 legacy 殘留**（見 RB-9 附註）。
- Frontend 5 筆 `migrate` hit（`types.ts:334,371`、`EditForm.tsx:38`、
  `scanTemplate.mock.ts:201`、`frontend-json-sample.json:1595`）—
  allowlist 已分類、Plan 13 已明列為 frontend handoff。
  惟需提醒：`types.ts:334` 的 zod enum 是
  `z.enum(["existing_slot_mapping", "new_extension_component"])`，
  **無法解析 backend 現在會回的 `non_baseline_capability_candidate` /
  `needs_more_information` / `skip_for_now`**——所以現況不只是「前端還送得出 legacy request」
  （Plan 13 `:428` 與 cutover report `:54` 的措辭），而是「前端連 active response 都 parse 不了」。
  這條屬於前端 owner，僅記錄措辭落差，不列為本區 finding。

---

## 封閉性結論

**問題：今天 active path 還有任何地方能寫入或讀出 legacy mapping shape 嗎？**

**答：沒有。backend active path 對 legacy mapping shape 是完全封閉的（write 與 read 皆然）。**

三道獨立防線，逐一實證：

1. **Model 層（最硬）** — `ManualMappingType` 只剩 2 個成員，`MappingCandidateType` 只剩 4 個；
   `ManualMappingCreate(mapping_type='new_extension_component')` 直接 `ValidationError`（實證 1）。
   `ManualMappingUpdate` 連 `mapping_type` 欄位都沒有且 `extra="forbid"`。
   全部消費點用 `match` + `assert_never` 窮舉，回加 enum 會 mypy 紅。
   `ManualMappingCreate` 也沒有 `extension_id/name/kind/edges` 這些欄位（`extra="forbid"`），
   即使 mapping_type 對了也組不出 legacy payload。

2. **API 層** — `POST /api/mappings` 與 `POST /api/mapping-proposals/{id}/decision`
   在 pydantic 之前就以 `reject_legacy_mapping_type` 回 422 `legacy_mapping_type_read_only`；
   `PATCH` 雖無 guard 但 model 層封死（RB-8，僅錯誤碼不一致）。

3. **Storage 層** — `LocalJsonStateStorage.read_model` 對 `ValidationError`
   **re-raise 成 `StateCorruptionError`**，沒有任何 fallback 到 dict / 回 `None` / 吞例外的分支
   （實證 2）。migration service 之外沒有第二個 raw mapping JSON reader（實證 3）。
   實測：磁碟上留一筆 `new_extension_component`，`list_for_project` 直接
   `StateCorruptionError`，不會被讀出來（實證 4 / RB-4）。

**但這個「封閉」有兩個必須立刻登記的邊界條件：**

- **封閉性的守門員本身無人守門。** 唯一的 API 停寫防線 `web/legacy_mapping_guards.py`
  同時逃出 Plan 13 的 AST census 與 rg gate（RB-1），且它依賴的
  `LegacyManualMappingType` 位於 Plan 15 Task 3b 要整個刪除的 module 裡（RB-2）。
  照 Task 3b 現行字面執行 → 先 `ImportError` 打爛 app 啟動，修掉 import 後若順手刪 guard →
  Plan 13 Task 5 的成果被靜默回退。**這是本次稽核最高風險項。**

- **封閉的代價沒被記錄。** Storage 是「fail-closed 到整個 project 讀不了」而非「跳過該筆」，
  所以 Plan 13 Task 4 那句「其他 unresolved quarantined rows 可以留作 migration evidence」
  在實務上不成立（RB-4）；且 migration 不會把 quarantined 原檔搬離 `mappings/` glob，
  沒有任何 code 或計畫負責這件事。

另有一項**不影響 mapping 封閉性、但會擋住 Plan 15**：active scan path 仍直接 import
v1 model module `core/models/system_map.py` 的 11 個非 map DTO（RB-10），
與 Plan 13 Task 5 已打勾的「normal build path 不得 import」矛盾；
census 因只掃 4 個符號而看不見。

**建議 Plan 15 執行前必做（依序）：**
1. RB-2 — 先切斷 `legacy_mapping_guards.py` → migration module 的 import。
2. RB-1 — 修 census（加 `LegacyManualMappingType` / `NEW_EXTENSION` 進 `LEGACY_NAMES`）並補 allowlist 記錄。
3. RB-4 — 決定 quarantined 原檔的去向，並回頭修 Plan 13 Task 4 敘述。
4. RB-10 — 拆 `core/models/system_map.py`，否則 Plan 15 Task 2/3 刪不動。
5. RB-3 — 刪 `_legacy_detail_scan`（46 行 dead code，順帶關掉繞過 `BuildCommitService` 的側門）。
6. RB-5 / RB-6 / RB-7 / RB-8 / RB-9 — 文件同步。
