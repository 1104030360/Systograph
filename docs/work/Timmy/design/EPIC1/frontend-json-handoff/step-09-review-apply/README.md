# Step 9 — Review / Apply（可選）

Last updated: 2026-07-15（current backend + Plan 13 legacy boundary）

Ambiguous evidence 的 review 不阻塞第一次 build／Viewer。Scanner 先建立 proposal，使用者決策
寫成 durable manual mapping；Apply 才重播同一 snapshot、建立新的 child build。

```text
MappingProposal
  -> user decision
  -> ManualMapping audit record
  -> Apply confirmed mappings
  -> same scan_id / snapshot, new build_id
```

Rescan 與 Apply 不同：Rescan 重新讀 repo 並建立新 `scan_id`；Apply 不重掃 repo，也不重跑
Step 2 inventory review。

## 2026-07-15 contract 狀態

Backend current proposal candidates 同時接受：

- `existing_slot_mapping`
- legacy `new_extension_component`
- `non_baseline_capability_candidate`
- `needs_more_information`
- `skip_for_now`

Durable `ManualMapping` 的 `mapping_type` 只有前三種可 materialize 的 mapping 類型；
`decision` 使用 `confirmed` / `rejected` / `skip_for_now` / `not_applicable`。

本資料夾兩份 sample 已通過 current backend Pydantic，示範 non-baseline candidate 流程；不使用
numeric confidence。

Frontend 尚未對齊：`types.ts`、mock 與 `EditForm` 仍只有 existing-slot／legacy-extension
選項，無法完整 parse／建立 non-baseline candidate。這是 current integration gap。

Plan 13 的 target 是 normal API／UI 停止接受 `new_extension_component`，先 migration／quarantine
既有 records，再把 v2 設為 normal active output。Plan 13 目前仍 blocked，因此文件不能宣稱
legacy write surface 已退役；也不能再把 legacy extension 當推薦的新資料模型。

## Proposal 與 Manual mapping

| | Proposal | Manual mapping |
| --- | --- | --- |
| 是什麼 | Scanner 的 evidence packet + candidates | 使用者決策的 durable audit record |
| API | `POST /api/mapping-proposals` | `POST /api/mapping-proposals/{id}/decision` |
| 是否直接改 map | 否 | 否；Apply 才 materialize |
| 是否阻塞初次 Viewer | 否 | 否 |

## frontend-mapping-proposal-sample.json

Current `MappingProposal` response：

| 欄位 | 白話 |
| --- | --- |
| `proposal_id` / `source_unmapped_id` | Proposal identity 與來源 unmapped item |
| `status` | `pending_user_confirmation` |
| `evidence_packet` | Safe evidence summary，不含 secret／absolute path |
| `candidates[]` | Backend 提供的可選方案 |
| `candidate_type` | Sample 使用 `non_baseline_capability_candidate`、`skip_for_now` |
| `available_actions` | `accept` / `edit` / `reject` / `skip_for_now` |

Proposal 只能建議，不得直接改 profile status 或 canonical map。

## frontend-manual-mapping-create-capability-candidate-sample.json

Current `ManualMappingCreate` request body：

| 欄位 | 白話 |
| --- | --- |
| `mapping_type` | Sample 是 `non_baseline_capability_candidate` |
| `decision` | `confirmed` / `rejected` / `skip_for_now` / `not_applicable` |
| `source_unmapped_id` / `proposal_id` | Audit lineage |
| `capability_candidate_*` | Confirmed candidate 的 stable id／name／kind |
| `decision_source` | 例如 `proposal_accept` |

Reject／skip 也建立 audit record，但不 materialize，不能進 `applied_mapping_ids`。Apply 只接受
non-empty、unique、同 project、confirmed 且可 materialize 的 mappings，base build 也必須仍是
latest。

## Frontend invariants

- 不從 proposal wording 或 topology 推導 candidate type。
- 不把 `pending_user_confirmation` 混成 assessment 五態。
- 不在 frontend 建立 legacy extension fallback；Plan 13 migration 由 backend 擁有。
- Apply 成功後依 response 的 child `build_id` 重新載入 project-scoped Viewer。
