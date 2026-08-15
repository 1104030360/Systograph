# 邊推導：residence 擴充與掉邊歸因

- 日期：2026-08-15
- 範圍：改動 A（file-level 唯一元件 fallback）＋改動 B（觀測欄位）；改動 C 依指示不做
- 不動：撞名 v2、`import as` / `__init__` re-export fail closed、動態分派升級、self-loop 與 cap
- 驗收：全套件 **1516 passed / 1 skipped**、ruff、format、mypy 全過；三專案地圖 bit-identical

## 步驟 0：先量再改（證實 residence 是最大桶）

| counter | graphrag | private-gpt |
|---|---:|---:|
| `calls_seen` | 5,464 | 16,497 |
| **`dropped_unresolved_source`** | **6,101** | **16,091**（calls 的 97.5%） |
| `dropped_unresolved_target` | 284 | 2,145 |
| `ambiguous_*` 合計 | 0 | 28 |

`ambiguous_callee_names` 為 **0**——名字解析根本沒在掉東西，撞名規則確實不該動。

## 改動 A：file-level 唯一元件 fallback

`ComponentResidenceIndex.component_ids_at()`：某行沒有任何「帶元件的 span」涵蓋時，改看該檔案的元件集合。

```
 line 沒被任何 component-bearing span 涵蓋
      │
      ├─ 檔內恰好 1 個元件 → 歸屬給它（檔內無歧義可言）
      └─ 檔內 ≥2 個元件   → 回空集合，不猜
                            deriver 透過 file_level_ambiguous()
                            記為 ambiguous_* 而非 unresolved_source
```

**嚴格不猜**：fallback 永遠不回多元素集合，所以多元件檔案不會有半個元件洩漏進 pair 計算（避免「self-loop 消掉一個候選後剩一組」而畫出猜測邊）。

契約變更：既有的 `test_file_level_residence_never_resolves_as_a_call_site` 正是這條的反面，已改寫為新契約，並補上「span 優先於 fallback」「兩元件不猜」兩個測試；deriver 層另加兩個行為測試。

### 效果

| | 改動前 | 改動後 |
|---|---:|---:|
| private-gpt `dropped_unresolved_source` | 16,091 | **14,482**（−1,609） |
| graphrag `dropped_unresolved_source` | 6,101 | 6,046（−55） |

## 邊數為何沒有增加（把殘留量化）

那 1,609 個通過 source 關卡的呼叫往下游走，我把「source 已解析」的 3,542 個呼叫分類：

| 數量 | 類別 | 範例 | 判定 |
|---:|---|---|---|
| 1,864 | 屬性呼叫，無 import 對應 | `ctx.store.set`、`runner.submit`、`super().model_post_init` | 需型別推論＝明列不動的動態分派 |
| 1,316 | 裸名，不在任何 import 檔定義 | `TextNode`、`ValueError`、`isinstance`、`dict` | builtins／外部符號，本來就不是元件 |
| 328 | **target 解析成功** | — | 其中 **319 是同元件內 self-loop** |
| 34 | 名字在本檔找到，但該檔無元件 | `service.list_files` | 元件覆蓋缺口（P1 規則） |

結論：這些 repo 裡「可解析、且跨元件」的呼叫點本來就極少。改動 A 把瓶頸從「歸屬」推到「呼叫本質」，而後者的分佈證明剩下的殘留是 out-of-scope，不是未知。

## 改動 B：把 0 邊變成可歸因

- `UaEdgeDerivationStats` 新增 `components_without_code_residence`。
- warning 列出**具體元件 id**（上限 20 個，超出附 `+N more`）：
  `UA edge derivation components with no code residence=1: component:vector_store:qdrant`
- **CLI 補印 `warning=`**：先前 `map` 只印 `migration_warning=`，derivation warning 從未露出，改動 B 的清單等於看不到。現在實跑 graphrag 會印：
  ```
  warning=UA edge derivation unresolved source=6046
  warning=UA edge derivation unresolved target=337
  warning=UA edge derivation self loops=20
  ```

private-gpt 實測 3 個無程式住址的元件：`app_api_or_orchestrator:application_api`、`document_loader:llama_index`、`orchestrator:llama_index`。

## 回歸驗收

| | components | edges | 是否 bit-identical |
|---|---|---|---|
| Verba | 15 → 15 | 3 → 3 | ✅ |
| private-gpt | 15 → 15 | 6 → 6 | ✅ |
| graphrag | 5 → 5 | 0 → 0 | ✅ |

「可多不可變」成立（實際是完全未變）；fixture 元件集合由全套件覆蓋，1516 全綠。

## 後續（roadmap，本次不做）

- **改動 C：config → reader 連結**——evidence 在 yaml/compose 的元件，找唯一 reader 檔延伸 residence。private-gpt 的 3 個無住址元件是候選樣本。
- **屬性呼叫型別推論**（1,864 筆最大殘留）：需要 local variable 型別追蹤，屬 L2/undetermined 範疇。
- **元件覆蓋缺口**（34 筆 `name_found_locally_but_file_has_no_component`）：走 P1 規則廣度，不是歸屬層問題。
