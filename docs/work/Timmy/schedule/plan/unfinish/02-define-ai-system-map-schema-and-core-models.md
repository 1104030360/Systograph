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
- 產生或維護 `schemas/ai-system-map.v1.schema.json`。
- 實作基本 schema validation helper。
- 實作 contract invariants 的測試起點。

## 不包含範圍
- 不實作 provider 掃描。
- 不產生真實 map。
- 不實作 Markdown、viewer、query trace。
- 不處理 remote template schema。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/system_map.py`。
2. 用 Pydantic v2 model 定義 top-level 與 nested types。
3. 將 status、endpoint type、scan depth 等欄位改成 enum 或 Literal。
4. 設定 models 禁止未知欄位，避免 contract 偷偷擴張。
5. 建立 `src/kai_mind/core/services/system_map_validation_service.py` 的最小 validator。
6. 建立 `schemas/ai-system-map.v1.schema.json`。
7. 加上測試：拒絕 `confidence`、拒絕 invalid status、拒絕 absolute evidence path。

## 預期輸出
- `schemas/ai-system-map.v1.schema.json`
- `src/kai_mind/core/models/system_map.py`
- `src/kai_mind/core/services/system_map_validation_service.py`
- `tests/contracts/test_ai_system_map_schema.py`
- `tests/core/test_system_map_validation.py`

## 驗收標準
- schema 含 `$schema`、`$id`、required top-level fields。
- valid minimal map 可通過 Pydantic 與 JSON Schema validation。
- 出現 `confidence` 時 validation 失敗。
- `detected` slot 沒有 evidence 時 validation 失敗。
- evidence file 是 absolute path 時 validation 失敗。

## 可能風險與注意事項
- Pydantic 產出的 JSON Schema 無法涵蓋所有 cross-reference invariant，所以必須有額外 validator。
- 不要只靠 Type hints，以免 dangling evidence、dangling edge 沒被擋住。
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
