# Task 2: Define AI System Map Schema and Core Models

## 目標
建立 `ai-system-map/v1` 的 JSON Schema 與 Python core models。這個任務要先把 canonical contract 固定，讓所有 scanner output、Markdown、GUI projection、CI contract tests 都有同一份事實標準。

## 為什麼要先做這個
設計文件反覆強調 `ai_system_map.json` 是 CLI、GUI、CI/CD、後續 Epic 的 source of truth。若先寫 scanner 再補 schema，後面會很容易破壞欄位相容性或產生沒有 evidence 的 detected component。

## 前置需求
- Task 1 已完成。
- 已確認 schema 位置為 `schemas/ai-system-map.v1.schema.json`。
- 已確認 Epic 1 固定 `system_type = rag` 與 `schema_version = ai-system-map/v1`。

## 實作範圍
- 建立 Pydantic models：`RagSystemMap`、`Project`、`Classification`、`ReferenceArchitecture`、`ComponentSlot`、`ComponentInstance`、`Evidence`、`Endpoint`、`Flow`、`Edge`、`RiskHint`、`DetailScanResult`、`QueryTraceEvent`、`ExtensionComponent`、`UnmappedComponent`。
- 以 Pydantic models 作為唯一 schema 定義來源，產生 `schemas/ai-system-map.v1.schema.json`。
- 實作基本 schema validation helper。
- 實作 contract invariants 的測試起點。
- 建立 `tests/fixtures/ai_system_map/` contract fixtures，包含手寫的 minimal valid fixture、由前端 sample 抽出的 rich valid fixture，以及 minimal invalid fixtures。

## 不包含範圍
- 不實作 provider 掃描。
- 不產生真實 map。
- 不實作 Markdown、viewer、query trace。
- 不處理 remote template schema。

## 建議實作步驟
1. 建立 `src/systograph/core/models/system_map.py`。
2. 用 Pydantic v2 model 定義 top-level 與 nested types。
3. 將 status、endpoint type、scan depth 等欄位改成 enum 或 Literal。
4. 設定 models 禁止未知欄位，避免 contract 偷偷擴張。
5. 建立 `src/systograph/core/services/system_map_validation_service.py` 的最小 validator。
6. 建立 `schemas/ai-system-map.v1.schema.json`。
7. 建立 `tests/fixtures/ai_system_map/valid_minimal.v1.json`，必須手寫，不可從 rich sample 自動裁切；內容只放剛好能通過 schema 與 runtime invariant 的最小 `ai_system_map.json`。
8. 從 `docs/work/Timmy/design/Users/linjunting/Systograph/docs/work/Timmy/design/frontend-json-sample.json` 抽出 `viewer_load_result.ai_system_map`，建立 `tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json`。
9. 建立 minimal invalid fixtures：`invalid_confidence.v1.json`、`invalid_detected_without_evidence.v1.json`、`invalid_invalid_status.v1.json`、`invalid_absolute_evidence_path.v1.json`。每份 invalid fixture 必須從 `valid_minimal.v1.json` 複製後只改一個錯誤點。
10. 加上 contract tests：直接讀取 fixtures，驗證 valid fixtures 通過 Pydantic、JSON Schema、runtime invariant validation，並驗證 invalid fixtures 以預期原因失敗。

## Contract Fixtures
- `tests/fixtures/ai_system_map/valid_minimal.v1.json`
  - 手寫 canonical minimal map。
  - 只包含 `ai-system-map/v1` required top-level fields 與通過 invariant 所需的最少資料。
  - 必須包含 `schema_version = ai-system-map/v1`、`system_type = rag`、`classification.mode = user_selected_or_default`、`classification.selected_template = rag-core-v1`、`scan_depth = system`。
  - 若包含 `detected` slot，該 slot 必須至少有一個 instance，且 instance 的 `evidence_ids` 必須指向存在的 evidence。
  - Evidence `file` 必須是 project-relative POSIX path，不可使用 absolute path。
- `tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json`
  - 從前端 handoff sample 的 `viewer_load_result.ai_system_map` 抽出。
  - 用於保護 backend canonical map 與 frontend graph projection handoff 的 rich contract baseline。
  - 不可包含 `sample_meta`、`viewer_load_result`、`graph_view_model`、`trace_result_samples`、`detail_scan_result_sample`、`mapping_proposal_result_sample`、`invalid_map_error_sample`。
- `tests/fixtures/ai_system_map/invalid_confidence.v1.json`
  - 從 `valid_minimal.v1.json` 複製，只新增一個 `confidence` 欄位。
  - 預期 validation 失敗原因：JSON contract 不允許任何 `confidence`。
- `tests/fixtures/ai_system_map/invalid_detected_without_evidence.v1.json`
  - 從 `valid_minimal.v1.json` 複製，只讓一個 `detected` slot 缺少有效 evidence。
  - 預期 validation 失敗原因：detected component 必須有 evidence。
- `tests/fixtures/ai_system_map/invalid_invalid_status.v1.json`
  - 從 `valid_minimal.v1.json` 複製，只把一個 slot status 改成非法 enum。
  - 預期 validation 失敗原因：status 不在允許集合內。
- `tests/fixtures/ai_system_map/invalid_absolute_evidence_path.v1.json`
  - 從 `valid_minimal.v1.json` 複製，只把一個 evidence `file` 改成 absolute path。
  - 預期 validation 失敗原因：evidence file 必須是 project-relative POSIX path。

## 預期輸出
- `schemas/ai-system-map.v1.schema.json`
- `src/systograph/core/models/system_map.py`
- `src/systograph/core/services/system_map_validation_service.py`
- `tests/fixtures/ai_system_map/valid_minimal.v1.json`
- `tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json`
- `tests/fixtures/ai_system_map/invalid_confidence.v1.json`
- `tests/fixtures/ai_system_map/invalid_detected_without_evidence.v1.json`
- `tests/fixtures/ai_system_map/invalid_invalid_status.v1.json`
- `tests/fixtures/ai_system_map/invalid_absolute_evidence_path.v1.json`
- `tests/contracts/test_ai_system_map_schema.py`
- `tests/core/test_system_map_validation.py`

## 驗收標準
- schema 含 `$schema`、`$id`、required top-level fields。
- `tests/fixtures/ai_system_map/valid_minimal.v1.json` 可通過 Pydantic、JSON Schema、runtime invariant validation。
- `tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json` 可通過 Pydantic、JSON Schema、runtime invariant validation。
- contract tests 必須直接讀取 `tests/fixtures/ai_system_map/*.json`，不可在 test 中動態組裝 minimal map。
- checked-in `schemas/ai-system-map.v1.schema.json` 必須與 Pydantic 產生的 schema 一致，避免 schema drift。
- 出現 `confidence` 時 validation 失敗。
- `detected` slot 沒有 evidence 時 validation 失敗。
- evidence file 是 absolute path 時 validation 失敗。
- invalid fixtures 必須各自只測一個錯誤點，避免測試失敗原因不明確。

## 可能風險與注意事項
- Pydantic 產出的 JSON Schema 無法涵蓋所有 cross-reference invariant，所以必須有額外 validator。
- 不要只靠 Type hints，以免 dangling evidence、dangling edge 沒被擋住。
- Pydantic models 與 JSON Schema 不可雙邊手動維護；Pydantic models 是 schema source of truth，checked-in schema 是 deterministic generated artifact。
- rich frontend sample 只能抽出 `viewer_load_result.ai_system_map` 當 canonical fixture；整包 viewer response 不是 `ai_system_map.json` contract。
- `invalid_map_error_sample` 是 GUI 載入失敗 response sample，不是 invalid `ai_system_map.json` fixture。
- `schema_version = ai-system-map/v1` 不可破壞既有欄位語意；新增欄位預設必須 optional 或有 backward-compatible default，破壞性變更需新增 v2 並記錄 migration。
- 參考依據：JSON Schema Draft 2020-12 官方規格；Pydantic v2 官方文件使用 `model_json_schema()` 產生 schema，並可用 `extra='forbid'` 禁止額外欄位。

## 新手提示
Schema 是後端對外的合約。就像 API 規格一樣，scanner 可以改進，但輸出的 JSON 形狀不能隨便漂移。

## 視覺化說明
```text
┌──────────────────────┐
│ Pydantic Models       │
│ Python runtime types  │
└───────┬─────────┬────┘
        │         │
        ↓         ↓
┌──────────────┐  ┌──────────────────────┐
│ JSON Schema  │  │ Runtime Validation   │
│ v1 contract  │  │ invariants + refs    │
└──────┬───────┘  └──────────┬───────────┘
       ↓                     ↓
┌──────────────┐  ┌──────────────────────┐
│ Contract     │  │ ai_system_map.json   │
│ Tests        │  │ accepted / rejected  │
└──────────────┘  └──────────────────────┘
```
