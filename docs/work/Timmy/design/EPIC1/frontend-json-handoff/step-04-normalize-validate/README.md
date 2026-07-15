# Step 4 — Normalize / Validate

Last updated: 2026-07-15（current normalized model + Plan 13 cutover boundary）

## 目前是哪一種 contract？

[`frontend-ai-system-map-sample.json`](frontend-ai-system-map-sample.json) 通過 current
`AiSystemMapV2` Pydantic model，代表 backend normalized contract；它**不是**在宣稱 normal
build 已把 public `ai_system_map.json` 切成 v2。

2026-07-15 live runtime 仍是：

```text
public ai_system_map.json / active_schema_version = ai-system-map/v1
  -> CanonicalMapLoader / adapter
  -> normalized AiSystemMapV2
  -> SystemMapIndex / Step 6 / Step 7 consumers
```

Plan 13 仍 blocked，必須等 00A normalized-consumer 與 readiness semantic-equivalence gates
完成後，normal public output 才能切到 v2。Frontend 不得先移除 v1 rollback／migration 邊界，
也不得把 v2 sample 當成目前 `/api/map` 的 raw map shape。

## 頂層

| 欄位 | 白話 |
| --- | --- |
| `schema_version` | 固定 `ai-system-map/v2` |
| `system_type` | 固定 `ai_system`；不把產品預設成 RAG-only |
| `scan_id` / `build_id` / `environment_id` | Assessment scope |
| `generated_from_build_id` | 必須等於目前 `build_id`；parent lineage 不放這裡 |
| `source_schema_version` | normalized input 來源；sample 是 current adapter 的 v1 |
| `migration_warnings` | v1→v2 migration 的 bounded warnings |
| `project` | Project identity；local root 可 redact |
| `components` / `edges` / `evidence` | Canonical structural facts |
| `endpoints` / `risk_hints` | 對外入口與 evidence-backed risk hints |
| `unmapped_components` | 尚未完成 taxonomy 對位的觀察 |
| `candidate_facts` | Legacy migration fact；不是允許 normal extension write |

## `components[]`

| 欄位 | 白話 |
| --- | --- |
| `component_id` | 穩定 canonical id |
| `display_name` / `canonical_type` | UI 名稱與 canonical type |
| `layer` | 10-plane layer，例如 `input_intent`、`retrieval`、`generation` |
| `status` | Detection status：`detected` / `missing` / `not_configured` / `not_applicable` / `confirmed` / `partial` / `undetermined` |
| `activation` | `enabled` / `disabled` / `conditional` / `unknown` / `conflicted` / `not_applicable` |
| `evidence_ids` | 對回 `evidence[]` |
| `framework` / `metadata` | Optional framework 與 bounded structured metadata |

Component detection status 不是 Step 6 的 assessment 五態；尤其 canonical component 沒有
`not_detected`，Step 6 profile 才使用完整五態。

## `edges[]`

| 欄位 | 白話 |
| --- | --- |
| `source` / `target` | `component_id`，不是 viewer node id |
| `relationship` | Static relationship |
| `status` | `observed` / `detected` / `undetermined` |
| `undetermined_reason` | 無法確定時的 bounded reason |
| `evidence_ids` | 支撐此 relationship 的 evidence |

## `evidence[]`

| 欄位 | 白話 |
| --- | --- |
| `evidence_id` / `artifact_type` | Stable id 與來源類型 |
| `evidence_kind` | `direct` / `indirect` / `explicit_negative` |
| `location` | `path`、line、JSON pointer、config key；使用 project-relative path |
| `extract_summary` / `rule_id` | Safe summary 與 deterministic rule |

Frontend 不顯示 absolute path、raw secret 或未遮罩 snippet。`location` 是巢狀物件，不是
舊 sample 的 flat `path`／`start_line` 欄位。

## `endpoints[]` 與 review inputs

- Endpoint 使用 `value`、`endpoint_type`、optional `method`／`component_id` 與
  `evidence_ids`；沒有 `handler` 欄位。
- `unmapped_components[]` 可進 Step 9 proposal，但 proposal 不直接修改本 map。
- `candidate_facts[]` 只保存 migration provenance。Plan 13 target 會停止 normal
  `new_extension_component` write，legacy records 由 migration／quarantine 流程處理。

## 驗證

```bash
.venv/bin/python -m pytest \
  tests/contracts/test_ai_system_map_v2_schema.py -q
```
