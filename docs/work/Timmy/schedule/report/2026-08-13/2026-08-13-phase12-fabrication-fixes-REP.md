# 2026-08-13 — Phase12 Critical 修復（16H terminal-name / 16C 規則表消歧 / Dockerfile 503）REP

> **範圍：** phase12 review（2026-08-11 NO-GO）11 個 Critical 中「捏造類」的前兩項。
> **性質：** 修復報告 + 明文基線調整記錄。變更以 unstaged 編輯疊在 staged 的
> phase12 142 檔之上，尚未 commit。

## 1. 修復一：16H terminal-name fallback 捏造 direct fact

**問題**：`resolve_call_symbol` 解析失敗時，拿名字最後一段跟 code pattern
規則表比對，唯一命中就回傳外部套件符號並標 `direct` 證據——專案自定義的
`class QdrantClient` 會被捏造成 `qdrant_client.QdrantClient` 的
vector_store_client 事實。

**修法**（提升真實掃描能力，非基線調整）：

- `ast_construction_types.py` — fallback 整段改為 **re-export 鏈追蹤**：
  沿目標模組的 module-level import bindings 逐跳驗證（`MAX_REEXPORT_HOPS=3`、
  防循環；星號 import／TYPE_CHECKING／未解析模組／模組名撞名一律拒絕）。
  只有鏈上證明名字真的源自規則表符號才回傳。新增 `module_level_bindings()`
  （模組名撞名（`src/` 折疊）者整名剔除）。
- `ast_construction_provider.py` — `collect()` 拆成兩段：先收齊全部檔案
  bindings，再解析呼叫（否則按路徑排序時 `app.py` 先於 `clients.py`
  解析，合法 re-export 也會失敗）。
- `ast_construction_factory_index.py` / `ast_construction_factory.py` —
  `module_bindings` 掛上 `FactoryIndex`，三個 `resolve_call_symbol`
  呼叫點（return construction / annotation / dict registry）補線。

**測試**：新增重現測試 `test_internal_class_sharing_catalog_name_is_not_external`
（紅→綠）＋ 4 個新分支測試（兩跳鏈、跳數上限、目標模組缺席、模組名撞名）；
`test_internal_reexport_uses_terminal_symbol_fallback` 更名為
`..._resolves_through_import_chain`（行為不變，機制名撤下）。

## 2. 修復二：16C ambiguous 歸屬被規則表消歧＋`resolve_by_span` 死碼

**問題**：`_derive_semantic_signal` 把多候選 (source, target) 的全笛卡兒積
丟給 `edge_relationship_rules.toml`，表剛好只認得一組就畫邊（call 邊一律
`observed`）——端點與方向由表的涵蓋範圍決定，violates 16C §3.2/§4
（丟棄＋計數、表只准命名關係）。計畫指定的 `resolve_by_span` 寫了、測了、
production 零呼叫。

**修法**：

- `ua_edge_signal_deriver.py` — 「**非 self 配對必須恰好一組**」檢查移到
  查表之前；多於一組 → `ambiguous_calls/ambiguous_factories` +1、不畫邊。
  `_relationship_matches` 收斂為單配對查詢（表後守衛保留：同配對映出
  多個關係名仍計 ambiguous）。消歧不再有任何路徑經過規則表。
  - 採「非 self 配對唯一」而非字面的 `len(source_ids)>1` 是刻意的：
    候選 {A,B}×{B} 排除 self-loop 後只剩 A→B 一個可表達宣稱，丟棄它
    沒有誠實依據；反方驗證確認字面版會誤殺 4 個合法單元測試。
- `component_residence_index.py` — 刪除 `resolve_by_span`（死碼；其
  單一回傳值無法區分「無歸屬」與「多歸屬」兩種計數，顯式分支較忠於
  16C §4 的分類計數要求）。**計畫字面點名此函式，此為小幅計畫偏離，
  語意（單一解析、歧義丟棄）完整實現。**
- 測試：新增 `test_ambiguous_source_is_discarded_before_catalog_lookup`
  （紅→綠）；residence index 測試改寫至 production 實際使用的
  `component_ids_at`。

## 3. 明文基線調整（honest-scan 模式）

修復二移除表消歧後暴露：**兩個旗艦 fixture 的唯一 L1 observed 邊都是
鏡像對**——bridge 把 retriever 與 vector_store 錨在同一筆證據
（`code_pattern_vector_store_qdrant @ src/retriever.py:13`），source 與
target 候選集相同，方向本來是表挑的。誠實結果：`SYSTOGRAPH_TEMPLATE_FLOW_EDGES=off`
下 fixture 邊數 1 → 0。依 CLAUDE.md honest-scan 紅線走「明文基線調整」：

| 測試 | 調整 |
|------|------|
| `test_real_fixture_edges_drive_all_static_siblings`（兩參數） | `assert edges == []`；姊妹 artifact 一致性與 parity 斷言保留（空圖不得被任何 artifact 憑空補邊） |
| `test_rescan_replaces_stale_call_edges` | 目的改由「證據被替換」承載（b1 有 qdrant 證據、b2 無）；邊兩端皆空 |
| `test_measurement_cli_compares_on_and_off_from_one_snapshot` | 16G 量測 `off.l1_observed` 誠實改斷言 0；`l1_relationships == []` |
| `test_pgvector_mirror_pair_is_ambiguous_not_catalog_directed`（單元，原 `test_pgvector_execute_call_emits_observed_query_edge`） | 原測試釘住表挑方向行為，改斷言丟棄＋計數 |
| `test_profile_card_status_baseline` 註解 | 「fixture 有一條 queries_vector_store 邊」已不成立，就地更正 |

**邊要誠實地回來，需要 owner 決策**：bridge 證據角色分離（residence vs
manifestation）／「pgvector Retriever 合成」裁定——與 review 既列的 5 個
owner 決策同源。16G 退役門檻量測數字變差是誠實方向（16G NO-GO 本就判定
門檻真 FAIL）。

## 4. 驗證

- 全量 pytest：1342 passed / 1 skipped（修復前基線 1340；UA patch 已套用
  狀態）。觸及檔案 ruff / mypy strict 全綠。
- ua_parity 不消費邊，parity 數字不受影響（已由調查驗證）。

## 4.5 修復三：Dockerfile 整條 503（`UaResource.kind` 缺欄 + endLine 差一）

**問題（三路驗證＋活體重現確認）**：任何含 Dockerfile 的專案掃描全滅
（web 503 / CLI exit 1、零 artifact）。兩個獨立致命因：(a) 上游 UA 的
Dockerfile service 本來就不帶 `kind`，而 inbound 讓 services 與 resources
共用 `kind` 必填的 `UaResource` → 整份結構輸出 `ua_result_invalid`；
(b) 上游 `split("\n")` 幽靈行使結尾換行檔的**最後一個 stage** endLine
永遠比檔案多 1，`_validate_span` 無夾回直接 `ua_line_invalid`。
fixture 零 Dockerfile，故測試一直全綠。

**修法 A（kind）**：`ua_sidecar_script_models.py` 新增 `UaService`
（name + start/end，無 kind，照上游真實 wire 形狀），
`UaStructureFile.services` 改用之；`UaResource`（kind 必填）留給
Terraform resources（該處嚴格是對的）。投影層（`_resources`）對 service
注入 Systograph 自己的 `kind="service"`。公開 schema `UaResourceRow.kind`
維持必填不動。

**修法 B（endLine）**：`ua_sidecar_projection.py` 新增
`_clamped_service_end`——**只對 services、只在 `end == size_lines + 1`
這一個已證實簽名**夾回檔尾，並記 `UaWarning(stage="structure_projection")`
（經 `UaAnalysisResult.warnings` → adapter ParseIssue 浮出，不靜默）。
`end == size+2`、Terraform resources 越界、start 越界維持 fail-closed。
選投影層夾回而非擴 sidecar patch：patch 面維持最小，上游修好後夾回
條件自然不再觸發。`project_structure_rows` 回傳值增加 warnings
（result builder 併入，cap 100 截斷防自傷）。

**覆蓋補洞**：新增 `tests/integration/test_dockerfile_project_scan.py`——
temp 專案含結尾換行 Dockerfile（同時踩兩個缺陷）端到端掃描成功、
artifact 齊全、地圖含 Dockerfile 證據。單元新增 5 測試
（`test_ua_sidecar_projection.py`）：service 無 kind 通過並投影
`kind="service"`、resource 無 kind 仍拒收、+1 夾回＋warning、
+2 仍 fail、resource +1 不夾。

**未做（待 owner）**：修法 C（fail-closed funnel 拆兩級嚴謹度＋
`ua_script_timeout` 改 retryable）需分類表拍板後另開一波。
16B（ua-sidecar-io-adapter-reference）若明文記載 services 模型形狀，
需同步一行（文件由 owner 管理，未代改）。

## 5. 已確認但不在本次範圍的既有缺口

1. **Ambiguity 警告只達 web API**：`UaEdgeDerivationResult.warnings` →
   `MapBuildResult.warnings` → `Phase2MapBuildResult`；CLI stdout 與發佈
   artifact 均看不到，ambiguity 也不產 `recommended_next_check`——16C §4
   要求的兩個通道字面上皆未滿足（先於本修復存在）。
2. `docs/.../step-08-viewer/frontend-json-sample.json`（staged doc 樣本）
   仍含 `queries_vector_store` 邊，需隨基線重新擷取。
3. MODEL-CONTRACT / API-GUIDE「UA 可缺席」矛盾等其餘 9 個 Critical 未動。
