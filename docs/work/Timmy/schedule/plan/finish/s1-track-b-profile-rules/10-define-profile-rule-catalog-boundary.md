# Profile Rule / Catalog Boundary Hardening 實作計畫

Status: completed（2026-07-14；ownership、guardrails、semantic regressions 與文件已驗收）

> **執行者注意：** 使用 TDD，逐 task 執行並保留 checkbox。若使用 Superpowers，請用
> `superpowers:executing-plans` 在同一工作階段逐項完成；本計畫不要求 subagent。

**目標：** 鎖定 Profile Engine、metadata catalog、generated projection、LLM proposal 與
UA scanner 的責任邊界，避免 `profile_registry.toml` 演變成第二套 rule engine，也避免 Plan 18
退役 matching catalogs 時誤刪仍需保留的 metadata catalogs。

**架構：** Python 是 profile/capability 判定的唯一 executable source of truth；Plan 11
只把 presentation metadata 搬到 package-bundled TOML。LLM、proposal、risk wording 與 scan
matching catalogs 都不能改寫 canonical facts、五態或 Mapping Completeness。

**Tech Stack：** Python 3.11、Pydantic v2、pytest、AST import graph、TOML metadata。

## Global Constraints

- Scanner 對 target repo 維持 read-only；catalog 只能從 Systograph package 載入。
- Two-Phase Analysis：先由 deterministic parser/adapter 產出 facts，再做 deterministic profile inference。
- `detected` 必須有 direct evidence；absence 不等於 explicit-negative。
- `not_detected` 必須通過 profile-specific coverage gate。
- 不新增 numeric confidence，也不讓 TOML 覆寫 Mapping Completeness 權重。
- 不新增 repo-local `.codex/` 設定。

---

## 1. 文件用途與 source of truth

| 項目 | 內容 |
|---|---|
| Audience | Phase 2 backend implementer、reviewer、後續 Plan 11 執行者 |
| 本計畫 owner | Profile rule/catalog ownership、dependency guard、handoff boundary |
| 前置條件 | Plan 02 Profile Engine 已存在；Plan 01A reference catalog 已存在 |
| 後續計畫 | Plan 11 metadata migration；Plan 14 validation；Plan 18 provider retirement |
| Last verified | 2026-07-14，依目前 code、tests、Plan 14/16/18/19 與 static-trace README |

判斷衝突時依下列順序：

1. executable code、schemas、tests。
2. `docs/MODEL-CONTRACT.md`、`docs/API-GUIDE.md`。
3. `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`。
4. Plan 02、10、11、14、16、18、19。
5. 其他歷史設計或研究文件。

## 2. 目前真實狀態

舊版計畫曾寫「Profile service 尚不存在」，目前已不正確。執行本計畫時不得重做 Plan 02。

| 能力 | 目前狀態 | 證據 |
|---|---|---|
| 15 個 profile ids 與 executable rule definitions | 已完成 | `src/systograph/core/services/profile_registry.py` |
| Profile inference orchestration | 已完成 | `src/systograph/core/services/profile_inference_service.py` |
| 五態、六種 activation、evidence kinds、scope、Mapping Completeness | 已完成 backend contract | `src/systograph/core/models/profile_signal.py` |
| Profile aggregation 與 evidence strength | 已完成 | `profile_finding_service.py`、`profile_finding_rules.py` |
| 52-node reference metadata catalog | 已完成 | `capability_reference_map.toml`、Plan 01A |
| Profile dependency guard | 部分完成 | 現有 AST test 只檢查手列 modules 與 direct imports |
| Profile presentation metadata TOML | 尚未完成 | 由 Plan 11 建立 |
| `profile_registry.json` read-only projection | 尚未完成 | 由 Plan 11 建立 projection contract |

目前 `profile_registry.py` 同時放 `label`、`primary_axis` 與
`required_node_ids`、`required_relationship`。Plan 11 必須把 presentation metadata 與
executable definitions 分檔，不能只把相同資料複製一份到 TOML。

## 3. 完整時序：UA 接手與 catalog 退場

使用者提供的退場資訊經 Plan 14、16、18、19 與 README 交叉確認後成立。更精確的 gate
時序如下：

```text
Phase A / S1          Gate-1          Plan 16 / Gate-2        Plan 14 / Gate-3       Plan 18
------------------    ---------       -------------------     ------------------     ------------------
Systograph TOML providers -> 解鎖 UA 整合 -> UA = Step 3 primary  -> parity 驗證通過   -> default Step 3
= Step 3 primary                       Systograph = parity-only                              不再跑舊 providers

Profile Engine        一直由 Python deterministic semantics 擁有，不隨 scanner owner 切換
Metadata catalogs     risk / next-check / reference / profile / inventory / llm config 保留
```

### 3.1 Plan 18 退役的是什麼

| 退役的主掃描項目 | 現有 catalog / path | 現有 provider |
|---|---|---|
| `code_pattern` | `code_pattern_rules.toml` | `CodePatternProvider` |
| `dependency_manifest` | `dependency_manifest_rules.toml` | `DependencyManifestProvider` |
| `docker_image` | `docker_image_rules.toml` | `DockerComposeProvider` |
| config patterns | config parsing path，非獨立 catalog | `ConfigParseProvider` |

「退役」的必要條件與結果：

- 必須先有 Plan 14 保存的 parity、fail-closed、Apply no-UA-rerun 報告。
- default Step 3 不再註冊或執行上述 providers。
- UA sidecar + `UaStructuralAdapter` 成為 scan fact/evidence 的 primary source。
- parity dry-run 或明確 feature-flag fallback 可以暫留，但預設必須關閉，且不得被描述成 primary truth。
- matching TOML 檔案是否立即刪除由 Plan 18 的逐 provider usage inventory 決定；Plan 10/11 不刪。

### 3.2 Plan 18 明確保留什麼

| 保留 catalog | Owner / 用途 | 為何不退役 |
|---|---|---|
| `risk_hint_rules.toml` | risk 文案 metadata | 不負責 repo matching |
| `recommended_next_check_rules.toml` | next-check 文案 metadata | 不負責 repo matching |
| `capability_reference_map.toml` | 10 planes / 52 nodes reference metadata | 是 Step 6/7 共同閱讀座標 |
| `profile_registry.toml` | Plan 11 profile presentation metadata | Profile Engine 顯示資料，不是 scanner |
| `scan_inventory_rules.toml` | Plan 19 Step 2 include/ignore boundary metadata | 發生在 Step 3 之前 |
| `llm_proposal.toml` | Step 9 optional provider config | 不參與 deterministic profile truth |

一句話：**退役的是「怎麼掃出 ScanFact」，不是「怎麼解釋、呈現或評估 profile」。**

## 4. Profile ownership

```text
Target repo
   |
   v
Step 3 deterministic scanner owner
   Phase A: Systograph TOML providers
   Phase B/C: UA sidecar + UaStructuralAdapter
   |
   v
ScanFact / Evidence
   |
   v
Step 4 Python component bridge
   rule_id + evidence -> component / unmapped / candidate input
   |
   v
Step 6 Python Profile Engine
   reference assessment + executable profile rules
   |
   +-----------------------------+
   |                             |
   v                             v
profile_signals.json       profile_registry.toml
canonical assessment      labels / axes / wording only
```

### 4.1 Python 必須擁有

- `required_node_ids`、`required_relationship` 與 high-specificity wiring gates。
- 五態：`detected`、`partial`、`undetermined`、`not_detected`、`conflicted`。
- 六種 activation 與 `not_applicable` 的 applicability 使用方式。
- direct / indirect / explicit-negative evidence classification。
- field-specific conflicts、coverage gates、assessment scope。
- `implementation_depth_level`、evidence strength、related-ref selection。
- Mapping Completeness 公式與固定權重。
- missing/unknown refs 的 validation 與 error outcome。

### 4.2 Plan 11 TOML 可以擁有

- stable `profile_id`。
- `display_name`、`short_label`、`description`。
- `primary_axis`、`secondary_axes`、`display_order`。
- generic `default_uncertainty` 顯示文案。
- generic `recommended_next_checks` 顯示文案。

### 4.3 TOML 與 generated JSON 不得擁有

- `condition`、regex、threshold、score、status weight。
- `allowed_evidence_kinds`、`related_rule_ids`。
- `required_node_ids`、`required_relationship`、coverage gate。
- provider、prompt、model、API endpoint 或 lifecycle action。
- `rule_id -> component/reference node` executable mapping。
- related refs、graph projection、accept/edit/reject 行為。

`allowed_evidence_kinds` 與 `related_rule_ids` 看似 metadata，實際會改變哪些 evidence 能觸發
profile，因此明確留在 Python，不出現在 Plan 11 catalog shape。

## 5. 狀態與錯誤語意

| 已驗證輸入 | 必要結果 |
|---|---|
| direct evidence + profile wiring gate 通過 | `detected` |
| indirect-only 或部分 wiring | `partial` |
| known profile 只有相關 risk/unmapped/candidate refs | `undetermined` |
| explicit-negative 且 profile coverage gate 完成 | `not_detected` |
| 同 scope/field 有無法消解的正反 evidence | `conflicted` |
| node 本質沒有 activation 語意 | `activation="not_applicable"` |
| unknown related id 或 mixed scope | validation error |

`not_applicable` 是 activation 值，不是 profile status。沒有證據且 coverage 未完成時必須是
`undetermined`，不能因「沒有找到」直接寫 `not_detected`。

Plan 11 error contract：

| Error | 用途 |
|---|---|
| `ProfileRegistryError` | TOML parse、schema、unknown/missing field、duplicate id/order |
| `ProfileMetadataCoverageError` | catalog ids 與 active Python profile ids 不相等 |

不要再增加語意重疊的 `ProfileRuleCatalogError`。

## 6. Stable ID 與版本規則

- 現有 15 個 `profile_id` 是 active contract；Plan 10/11 不 rename。
- label、description 可以修文案，但 `profile_id` 必須穩定。
- 未來真的需要 rename 時，先增加 migration alias/deprecated id，再升 catalog/schema version。
- 增刪 profile、改變 executable rule semantics 或 active id set，不能當一般文案修改。
- `profile_registry.json` 若產生，只能是 TOML 的 deterministic read-only projection，不能被 engine 讀回作第二份 truth。

## 7. 範圍

### 包含

- 同步目前已完成與仍待做的狀態。
- 鎖定 Python/TOML/LLM/UA ownership。
- 補強 direct + indirect dependency guard。
- 補足 risk-only、unknown refs、coverage、activation 與 immutable weights 邊界測試。
- 建立 Plan 11 可直接執行的 metadata-only handoff。

### 不包含

- 不重做 Plan 02 Profile Engine。
- 不建立 `profile_registry.toml`；由 Plan 11 建立。
- 不改 ProfileInference 的既有五態行為，除非 focused regression test 證明目前違反本契約。
- 不實作 Plan 16 UA sidecar 或 Plan 18 provider retirement。
- 不新增 LLM-backed profile inference、frontend contract 或 mutation route。

## 8. 實作 Tasks

### Task 1：同步 canonical boundary 文件

**Files**

- Modify: `docs/design/epic1-phase2.md`
- Modify: `docs/work/Timmy/design/EPIC1/Phase2/epic1-phase2/epic1-phase2-design.md`
- Modify: `docs/MODEL-CONTRACT.md`
- Review: 本計畫與 Plan 11

- [x] 將「Profile service 尚不存在」改成目前 backend 已完成狀態。
- [x] 寫入第 3～6 節的 owner、retirement、state 與 version 規則。
- [x] 明確記錄 Plan 10 不建立 TOML，Plan 11 才遷移 presentation metadata。
- [x] 確認文件沒有把 Plan 18 說成刪除所有 TOML，也沒有把 Plan 10/11 說成 retirement owner。

### Task 2：補強 direct + transitive dependency guard

**Files**

- Modify: `tests/unit/core/test_profile_inference_boundaries.py`

- [x] 自動探索 `src/systograph/core/services/profile*.py`，並納入
  `reference_capability_assessment_service.py`；不要再只維護四個手列檔案。
- [x] 建立 repo-local import graph，檢查 direct 與 transitive imports。
- [x] 禁止 profile path 依賴 manual mapping、mapping proposal、LLM proposal config/provider、web routes。
- [x] Plan 10 不新增 Import Linter dependency；若未來出現三條以上 architecture contracts，再另案評估。
- [x] Guard test 的 failure message 列出完整 import chain，讓 reviewer 能定位越界來源。

### Task 3：補齊 profile semantic boundary regressions

**Files**

- Modify: `tests/unit/core/test_profile_inference_boundaries.py`
- Modify: `tests/unit/core/test_profile_inference_service.py`
- Modify: `tests/unit/core/test_profile_signal_validation_service.py`
- Modify: `tests/unit/core/test_profile_signal_models.py`

- [x] known risk/unmapped/candidate refs 不足時保持 `undetermined`，不得升級 `detected`。
- [x] unknown related id 必須 validation error；不使用「reject 或 undetermined」模糊措辭。
- [x] explicit-negative + coverage complete 才可 `not_detected`。
- [x] 覆蓋六種 activation，並證明 `not_applicable` 不會被當成 status。
- [x] 鎖定 Mapping Completeness 權重，證明外部 mapping/TOML 無法覆寫。

### Task 4：完成 Plan 11 handoff 與 UA lifecycle 對照

**Files**

- Modify: 本計畫
- Modify: `11-migrate-profile-rule-metadata-to-toml-catalog.md`
- Review: Plan 14、16、18、19、static-trace README

- [x] Plan 11 的 allowed fields 與本計畫完全一致。
- [x] 移除舊範例中的 `allowed_evidence_kinds`、`related_rule_ids`、`default_evidence_strength`。
- [x] Plan 11 使用一致的 error taxonomy、stable id 與 projection 規則。
- [x] 記錄 `profile_registry.toml` 是 Plan 18 明確保留項。

## 9. 驗收標準

- [x] 文件正確反映 Profile Engine 已存在，且 Plan 10 不重做 Plan 02。
- [x] Python/TOML/LLM/UA ownership 沒有重疊或第二份 truth。
- [x] Profile dependency guard 可抓 direct 與 transitive forbidden imports。
- [x] risk-only、coverage、unknown refs、activation、weights 邊界都有 focused tests。
- [x] Plan 10 結束時尚未建立 `profile_registry.toml`；Plan 11 才建立。
- [x] Plan 18 retirement table 與 Plan 14/16/18/19、README gates 一致。
- [x] 所有路徑與驗證命令可在 repo root 執行。

## 10. 驗證

```bash
uv run pytest tests/unit/core/test_profile_inference_boundaries.py -q
uv run pytest \
  tests/unit/core/test_profile_inference_service.py \
  tests/unit/core/test_profile_signal_validation_service.py \
  tests/unit/core/test_profile_signal_models.py -q
uv run ruff check src tests
uv run mypy
test ! -e src/systograph/core/rules/profile_registry.toml
git diff --check \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-b-profile-rules/10-define-profile-rule-catalog-boundary.md \
  docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s1-track-b-profile-rules/11-migrate-profile-rule-metadata-to-toml-catalog.md
```

`test ! -e .../profile_registry.toml` 只適用 Plan 10 完成點；Plan 11 完成後由「catalog 必須存在」取代。

## 11. 開源實作對照與採用範圍

| 來源 | 查到的做法 | 本計畫採用 | 不照搬 |
|---|---|---|---|
| OpenSSF Scorecard probes（Apache-2.0） | 每個 probe 分成 definition、implementation、test，且有 unavailable/lifecycle 語意 | metadata、Python logic、tests 分離；保留 `undetermined` | 不採用不透明 aggregate score |
| OpenTelemetry Semantic Conventions（Apache-2.0） | YAML 是 authoring source，產生 Markdown，並做 naming/backward-compat policy checks | TOML 單一 authoring source + deterministic projection + freshness test | 不導入其完整 generator toolchain |
| Import Linter（BSD-2-Clause） | forbidden contracts 預設涵蓋 descendants 與 indirect imports | architecture guard 檢查 transitive path | 現階段不新增 dependency |
| SARIF 2.1.0（OASIS） | 區分 insufficient information 與 not-applicable；rule id 應穩定 | 對齊 `undetermined` / activation `not_applicable` 與 stable profile ids | 不改用完整 SARIF artifact |

Sources：

- [OpenSSF Scorecard probes](https://github.com/ossf/scorecard/blob/main/probes/README.md)
- [OpenTelemetry Semantic Conventions YAML model](https://github.com/open-telemetry/semantic-conventions/blob/main/model/README.md)
- [Import Linter forbidden contracts](https://import-linter.readthedocs.io/en/stable/contract_types/forbidden/)
- [OASIS SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html)
