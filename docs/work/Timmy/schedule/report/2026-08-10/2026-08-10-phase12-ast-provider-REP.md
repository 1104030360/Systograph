# Phase 12 — AST Construction Provider REP

Date: 2026-08-10
Plan: `16H-ast-construction-provider.md`

## 結果

Plan 16H Task 1～5 已落地並接入 deterministic `ProjectScanService`：

- `AssessmentEvidenceKind` 移到無反向依賴的中立 model，v1 `Evidence` 增加 optional
  `evidence_kind_hint`；canonicalization 固定 hint 優先，未設 hint 維持舊推導。
- 定義 call/import/symbol/factory typed structural facts，不再把結構資料塞進
  `extra: dict`。
- `code_pattern_rules.toml` 增加受驗證、可選且唯一的 dotted `symbol`；regex 與 AST
  catalog 同源，未填 symbol 的規則不被強迫改寫。
- `AstConstructionProvider` 覆蓋 import-time constructor（G1）、external import
  declaration（G3）與 factory inference（G2）。
- source read 在 collect 起點釘住 project root directory fd 與 device/inode；POSIX
  後續由該 dirfd 逐層 `openat` + `O_NOFOLLOW`，leaf 與整棵 root replacement race
  都 fail closed。descriptor 實際讀到的 bytes 還必須同時符合 inventory 的
  `size_bytes` 與 `content_fingerprint`，才允許 decode／parse。
- 非 POSIX 或缺少上述安全 primitive 時，provider 對每個 Python 檔產生 structured
  read issue、零 AST fact；目前沒有 pathname fallback。原生 Windows safe-handle
  讀取是明載 capability gap，不以 pathname check 冒充等價安全性。
- internal-module 名單只由 approved inventory 中語法合法的 Python 相對路徑推導，
  不查詢 live pathname 是否暫時存在；leaf absence/restore 不會把 internal import
  誤發成 external evidence。
- 工廠固定最多 3 hops、cycle guard、branch/dict-registry provenance；任何推論一律
  `evidence_kind_hint=indirect`，不會因有行號升成 direct。
- `TYPE_CHECKING`、star import、dynamic import、re-export ambiguity、try/except import、
  metaclass 等邊界維持 fail-closed／不產 fact。

## TDD / 驗證

- `tests/contracts/test_evidence_kind_hint_contract.py`
- `tests/contracts/test_structural_fact_contract.py`
- `tests/unit/core/test_ast_construction_provider.py`
- `tests/unit/core/test_code_pattern_provider.py`
- `tests/unit/core/test_rule_catalog_loader.py`
- `tests/integration/test_phase12_project_scan_service_behaviors.py`

安全 RED/GREEN 另涵蓋 approved leaf 換成 outside symlink、approved project root
整棵 rename／replacement，以及同 inode／同長度的暫時內容置換；最後都只產
structured read issue，不產替代內容 fact。非 POSIX contract 也斷言不存在 pathname
safe-open fallback，且 `collect()` 對每個 Python 檔都產 read issue、零 facts/evidence。
另有 transient internal-module absence/restore regression，防止 module classification
繞過 approved inventory truth。

全套 Python suite 已涵蓋上述測試；最終總數與 browser QA 另記於 Phase 12 final
acceptance report。

## 邊界

本 provider 只做 deterministic Python AST 分析。UA `file-analyzer`、semantic graph、
LLM assessment 仍未進入 Step 3，也沒有 public artifact 欄位。Native POSIX safe-open
是目前 AST source read 的必要能力；其他平台會保留 UA 與其他 provider 結果，但不產
AST facts。
