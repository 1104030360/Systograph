# Task 15: Normalize and Validate System Map

## 目標
實作 `SystemMapNormalizeService` 與完整 `SystemMapValidationService`，將 slots、instances、evidence、endpoints、flows、risk hints 組成 canonical `RagSystemMap`，並在寫出前擋下 contract violation。

## 為什麼要先做這個
Stage 7 是 canonical JSON 的最後閘門。所有後續 CLI、Markdown、viewer、trace 都應只讀 validated map，不能繞過 normalization/validation。

## 前置需求
- Task 2 已完成 schema/model。
- Task 13 已完成 component detection。
- Task 14 已完成 endpoint/risk/flow derivation。

## 實作範圍
- 組裝 top-level `RagSystemMap`。
- 產生 deterministic ids。
- 合併 duplicate evidence/component/endpoint。
- 填入 recommended next checks。
- 執行 JSON Schema validation。
- 執行 cross-reference invariants：evidence refs、edge refs、risk refs、no confidence、no absolute paths、no unmasked secrets。

## 不包含範圍
- 不寫 artifacts。
- 不產生 Markdown。
- 不做 viewer graph projection。
- 不做 AI proposal。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/system_map_normalize_service.py`。
2. 補強 `system_map_validation_service.py`。
3. 定義 deterministic id helper。
4. 組裝 classification placeholder：`user_selected_or_default`、`rag-core-v1`。
5. 組裝 project metadata 與 root path mode。
6. 加入 recommended next checks：runtime_readiness、privacy_exposure、rag_knowledge_trust。
7. 寫 contract tests：invalid references、detected without evidence、confidence、absolute evidence path。

## 預期輸出
- `src/kai_mind/core/services/system_map_normalize_service.py`
- `src/kai_mind/core/services/system_map_validation_service.py`
- `tests/contracts/test_system_map_contract.py`
- `tests/core/test_system_map_normalize_service.py`

## 驗收標準
- basic fixture 可產生 valid `RagSystemMap` object。
- invalid map 不會被 validation 放行。
- normalized map deterministic ordering 穩定。
- full secret 不出現在 serialized JSON。

## 可能風險與注意事項
- JSON Schema 無法檢查所有 dangling references，必須用 Python validator 補。
- deterministic ids 要避免使用 absolute path。
- 參考依據：JSON Schema 官方 validation 規格；GitDiagram/Understand-Anything 的 validation discipline 可作 path/graph validation 參考。

## 新手提示
Normalize 是整理資料，Validate 是守門。這一步完成後，後面的人只需要相信這份 map。

## 視覺化說明
```text
┌────────────────┐ ┌──────────┐ ┌──────────────────────┐
│ Detected        │ │ Evidence │ │ Endpoints/Risks/Flows │
│ components      │ │          │ │                      │
└───────┬────────┘ └────┬─────┘ └──────────┬───────────┘
        └───────────────┼──────────────────┘
                        ↓
┌──────────────────────────┐
│ Normalize                 │
│ ids + merge + assemble    │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ Validate                  │
│ schema + invariants       │
└──────┬────────────┬──────┘
       │ pass       │ fail
       ↓            ↓
┌──────────────┐ ┌────────────────┐
│ canonical    │ │ ValidationError │
│ system map   │ │                │
└──────────────┘ └────────────────┘
```
