# Retire Systograph Scan TOML Providers After Parity 實作計畫

Status: planned（Plan 14 UA parity gate 通過後執行）

> **2026-08-05 修訂：** 退役範圍由「三項全退」收斂為「一項全退、一項半退、一項不退」，
> 並釐清「Python provider（掃描機制）」與「TOML（語彙目錄）」是兩件事。
> Status 語意不變，仍是 planned、仍等 Plan 14 gate。

> **2026-08-10 注記：** 本檔已依
> [`CLARIFICATIONS-2026-08-10.md`](../s2-ua-integration/CLARIFICATIONS-2026-08-10.md)
> 的 **Q17** 裁定修訂——`ua_*` ↔ legacy 對照表產出者更正為 **Plan 16 Task 3**、
> 「Tier A」改用 Plan 14 的唯一定義（＝外部真實 repo，不再用來稱呼 fixtures）、
> 退役報告格式與 Plan 14 對齊（分類由 14 產出、18 消費）；並依 16E 移交（經 Q17 裁定）
> 補上「函式外建構（G1）parity」退役準則。Task 3／Task 5 Files 的三處舊套件死路徑
> 與 Task 6 的舊 env 名一併更正為 `src/systograph/` 與 `SYSTOGRAPH_*`（#277 後的唯一命名）。
> 裁定軌跡以該檔為準。

> **執行者注意：** 本計畫只能在 Plan 14 留下通過的 UA parity / fail-closed /
> Apply no-UA-rerun validation report 後執行。逐 task、逐 provider 退役，不得一次刪光。

## 目標

在 UA sidecar 已成為 Step 3 primary 掃描來源且 parity gate 通過後，退役**有 UA 等價替代**的
Systograph scan providers 主掃描路徑，避免同一掃描事實長期由兩套機制維護；**沒有等價替代的機制續留**。

## 名詞澄清（2026-08-05 修訂）

> **2026-08-05 修訂：原文標題與內文把「退役 TOML providers」當成一件事，
> 因查核發現原文據此推出「刪 TOML 檔」的錯誤結論，改為明確區分兩層。**

本計畫的退役對象是**下層（機制）**，不是上層（語彙）：

| 層 | 內容 | 本計畫處置 |
|---|---|---|
| **機制**：Python provider | `CodePatternProvider` 的 regex 引擎、`DockerComposeProvider` 的 compose 解析、`DependencyManifestProvider` 的 manifest 解析 | **逐項裁定**（見下節三分法） |
| **語彙**：`core/rules/*.toml` | `rule_id` / `kind` / 對照表 —— 「什麼字串代表 Qdrant client」這類領域知識 | **全部續留**，部分升格 |

兩個佐證這個方向正確：

- `core/rules/` 現有 10 份 TOML（`capability_reference_map` 491 行、`profile_registry` 166、
  `scan_inventory_rules` 137、`code_pattern_rules` 103、`risk_hint_rules` 83、
  `dependency_manifest_rules` 49、`capability_type_node_map` 47、
  `recommended_next_check_rules` 23、`profile_relationship_alias` 21、`docker_image_rules` 15），
  其中多數本來就只是語彙/座標，與掃描機制無關。
- [16C](../s2-ua-integration/16C-component-attribution-and-edge-derivation.md) Task 2 還要**新增**
  `core/rules/edge_relationship_rules.toml`。UA 落地後 TOML 總數是**上升**的。

所以「退役」的正確語意是：**移除 TOML 內的可執行機制（`regex` 欄位）**，語彙目錄反而升格。
這與 CLAUDE.md「TOML 放文案/座標、Python 放邏輯」的邊界方向一致。

## 架構

```text
Before Plan 18
  UA sidecar primary
  Systograph scan providers parity-only

After Plan 18
  UA sidecar primary
  UaStructuralAdapter owns symbol / endpoint / docker-image scan facts
  code_pattern provider retired      -> code_pattern_rules.toml lives on as symbol catalog
  docker_image provider slimmed      -> env / env_file / volumes / depends_on per consumer audit
  dependency_manifest provider stays -> no UA equivalent, complementary evidence class
  retained TOML: symbol vocabulary + metadata + boundary + provider config
```

> **2026-08-05 修訂：原 After 圖寫 `retired providers unavailable in main scan path` 與
> `retained TOML catalogs only for metadata or inventory policy`，因查核發現語彙目錄續存、
> 且 `dependency_manifest` provider 不退，改為上圖。**

## 退役範圍（2026-08-05 修訂）

> **2026-08-05 修訂：原文將 `code_pattern` / `dependency_manifest` / `docker_image` 三項並列全退，
> 因逐項查核發現三者的 UA 替代度完全不同，改為「全退 / 半退 / 不退」三分法。**

| 項目 | 裁定 | Python provider（機制） | TOML（語彙目錄） |
|---|---|---|---|
| `code_pattern` | **全退** | regex 掃描引擎退役 | 只退 `regex` 欄位；其餘升格為符號語彙目錄 |
| `docker_image` | **半退** | image 偵測退役；其餘 fact 類別待 consumer audit | `docker_image_rules.toml` 續留為查表 |
| `dependency_manifest` | **不退（續留 primary）** | 無替代機制，續留 | `dependency_manifest_rules.toml` 續留 |
| config patterns | **全退**（主掃描路徑） | 由 UA 結構事實取代 | — |

### `code_pattern` —— 全退機制，TOML 升格

`code_pattern_rules.toml` 現有 13 條 `[[patterns]]`，欄位為
`rule_id` / `kind` / `languages` / `extensions` / `regex` / `snippet_group`。
退役的只有 `regex` 欄位所代表的**掃描機制**；`rule_id` / `kind` 是 Step 4 bridge 的匹配鍵，必須續留。

[16E §2.7](../s2-ua-integration/16E-ua-coverage-gaps-and-llm-boundary.md) 進一步規劃在每列加上
optional `symbol` 欄位（如 `symbol = "qdrant_client.QdrantClient"`），
供 [`16H`](../s2-ua-integration/16H-ast-construction-provider.md) 的
`ast_construction_provider`（G1/G2/G3 的 Python 補充 provider，**不在本計畫退役範圍**）
與 regex 目錄共用同一 source of truth。**這是加性擴充，方向與退役相反。**

**退役準則：函式外建構（G1）parity（16E §2 移交，2026-08-10 經 Q17 裁定）**

`def` 之外的建構——模組頂層與 class body 頂層——**今天正是靠 `code_pattern` 的 regex 掃到的**
（regex 無作用域概念，照樣命中並產出帶 file+line 的 `direct` evidence）；UA extractor 受
`functionStack.length > 0` 守衛，這一類建構全部看不到。RAG 專案的設定類別寫法極常見，
所以這不是邊角案例。

因此：**16H `ast_construction_provider` 的 G1 產出必須先納入 parity 對比，才可退役
`code_pattern` provider**（已列入「Parity Gate 標準」）。未納入即退役＝靜默丟失一整類
今天就拿得到的 direct evidence，違反 accepted degradation 必須書面化的原則。

### `docker_image` —— 半退，且退役前必須先做 consumer audit

`DockerComposeProvider` 實際抽出**六類** fact，不是只有 image：

| fact kind | rule_id | UA 等價物 | 2026-08-05 預查 consumer |
|---|---|---|---|
| `docker_service` | 查 `docker_image_rules.toml`，查無則 fallback `docker_service_image_detected`（`:30`,`:410-413`） | ✅ UA `services[].image` | `component_bridge_rules.py` |
| `published_port` | `docker_published_port_detected` | ✅ UA `services[].ports` | `endpoint_detection_service.py:22,58,111`、`risk_hint_service.py:26,78,149` |
| `docker_environment` | `docker_environment_detected` | ❌ **無** | `endpoint_detection_service.py:153`、`risk_hint_service.py:292` |
| `docker_env_file` | `docker_env_file_detected` | ❌ **無** | **查無 consumer**（僅 provider 內定義與 emit） |
| `docker_volume` | `docker_volume_detected` | ❌ **無** | **查無 consumer** |
| `docker_depends_on` | `docker_depends_on_detected` | ❌ **無** | **查無 consumer** |

UA `extract-structure` 的 `services[]` 只輸出 `name` / `image` / `ports` / `startLine` / `endLine`
（見 [16B §3.3](../s2-ua-integration/16B-ua-sidecar-io-adapter-reference.md)），
所以 `environment` / `env_file` / `volumes` / `depends_on` **四類 fact 沒有 UA 等價物**。

裁定：

- image 偵測機制可由 UA `services[]` + `docker_image_rules.toml` 查表取代；
  UA 帶 `startLine` / `endLine`，**可升級為帶行號的 direct evidence**。
- 其餘四類**不得順手刪掉**。Task 2 consumer audit 完成前不動 provider。
- 上表「預查 consumer」欄是 2026-08-05 的 `rg` 結果，**只是 Task 2 的起點不是結論**；
  Task 2 需正式確認後，依結果二選一：
  **(a) provider 瘦身續命**（`docker_environment` 有兩個真實 consumer，傾向此案）；
  **(b) accepted degradation**（`env_file` / `volumes` / `depends_on` 目前查無 consumer，
  但要刪必須寫下書面理由並記入 retirement report）。

### `dependency_manifest` —— 移出退役範圍

> **2026-08-05 修訂：原文將本項列為退役範圍，因查核發現 UA 無任何 manifest 解析機制、
> 且其證據類別是契約明文的互補證據（不是重複來源），改列為續留 primary。**

兩個獨立理由：

1. **機制無替代。** UA core 沒有 dependency manifest parser。
   `plugins/parsers/` 全是格式性 parser（`json` / `yaml` / `toml` / `dockerfile` / `env` / `sql` …），
   不產出依賴事實。唯一沾邊的是 `languages/framework-registry.ts:45 detectFrameworks()`，
   但它 (i) 只做整檔 `contentLower.includes(keyword)` 子字串比對，**無行號、無版本、無套件解析**；
   (ii) 只覆蓋 django / flask / fastapi / react / vue / nextjs / express 等 web 框架，
   **完全不含 RAG 語彙**（langchain / llama-index / qdrant-client / chromadb / ollama）；
   (iii) 在整個 plugin 內**查無任何 caller**，三支已採用的 sidecar script
   （`extract-import-map` / `compute-batches` / `extract-structure`）都不呼叫它——
   **它根本不在 sidecar 契約的採用面上**。
2. **證據類別互補，不是重複。**
   [16E §4.2](../s2-ua-integration/16E-ua-coverage-gaps-and-llm-boundary.md) 明文定義：
   `dependency_manifest_rules.toml` 回答「**宣告了**什麼依賴」（indirect）、
   G3 外部 import 邊回答「**哪一行實際用了**」（direct，帶行號）。
   兩者是互補的兩類證據。退役前者不是換來源，**是刪掉一整類證據**。

補充：`dependency_candidate` fact 有真實 consumer——
`component_bridge_registry.py:67` 將其路由為 `UNMAPPED_REVIEW_ITEM`。退役會靜默少掉 review items。

## 保留項（2026-08-05 修訂）

> **2026-08-05 修訂：原保留清單未含三份 scan TOML，因原文誤把它們當退役對象，補入並標注新定位。**

| TOML | 定位 |
|---|---|
| `code_pattern_rules.toml` | **語彙目錄（升格）**——符號 → `rule_id` / `kind`；16E §2.7 還要加 `symbol` 欄位 |
| `docker_image_rules.toml` | **語彙目錄**——image repository → `rule_id` 查表，UA 路徑仍需要 |
| `dependency_manifest_rules.toml` | **語彙目錄 + 機制續留**——套件名 → `rule_id`，provider 不退 |
| `risk_hint_rules.toml` | metadata |
| `recommended_next_check_rules.toml` | metadata |
| `scan_inventory_rules.toml` | boundary / include-ignore policy |
| profile / reference metadata TOML | metadata（`profile_registry`、`capability_reference_map`、`capability_type_node_map`、`profile_relationship_alias`） |
| `core/configs/llm_proposal.toml` | Step 9 optional provider config |

> 三份 scan TOML 若要改名以反映新定位（例如 `code_pattern_rules.toml` →
> `component_symbol_catalog.toml`），列為 **open option，本計畫不決定**。
> 改名會牽動 `rule_catalog_loader` 與既有測試，應獨立成案。

## 依賴

- 依賴 Plan 14 通過並保存 parity report。
- 依賴 Plan 16 UA structural path 已覆蓋主掃描 facts。
- 依賴 Plan 01B bridge registry 已支援 UA `rule_id`。
- **依賴 `ua_*` ↔ legacy `rule_id` 對照表已產出**（2026-08-05 新增，見下節 provenance 兩難）。
  產出者為 **[Plan 16 Task 3](../s2-ua-integration/16-implement-understand-anything-sidecar-service.md)
  （語彙目錄＋bridge 鏡射）**——對照表併入 `code_pattern_rules.toml` 演進版，每列同載
  legacy id / kind / symbol / ua id，bridge 的 `ua_*` 鏡射項隨同一 task 落地。
  （2026-08-10 更正 Q17③：原標「Task 7 / Plan 01B」有誤，與下節 2026-08-05 裁定敘述不一致。）
  [Plan 16 Task 7](../s2-ua-integration/16-implement-understand-anything-sidecar-service.md)
  parity harness **只消費**該對照欄做 equivalence 判定與 provenance 標示；
  [Plan 01B](../../../../finish/s1-pipeline-core/01B-extract-step4-component-bridge-registry.md)
  是「bridge registry 支援 UA `rule_id`」這條依賴的來源，不是對照表產出者。
  本計畫只消費不產出。

### rule_id provenance 兩難（2026-08-05 新增）

parity diff 要有意義，前提是能分辨「這筆 fact 是誰掃出來的」。但兩條路都有代價：

| 選項 | 代價 |
|---|---|
| UA adapter 沿用 legacy `rule_id` | bridge 零改動（[16E §2.7](../s2-ua-integration/16E-ua-coverage-gaps-and-llm-boundary.md) 正是此案），但 **parity diff 無法區分 fact 來源**——兩套機制輸出同一組 id |
| UA adapter 改用新 `ua_*` id | 來源可辨，但 bridge 13 條規則需逐條加鏡射項（[13.7](../../../../finish/s1-v2-cutover/13.7.md) 射程） |

無論選哪邊，都必須有**一張 `ua_*` ↔ legacy `rule_id` 對照表**，
且 parity report 必須能標示每筆 fact 的 provenance。
**這兩者是 parity gate 的必要輸入，不是 Plan 18 的產出物**——缺任一項，本計畫維持 pending。

> **2026-08-05 裁定（機制已定，兩難已解）：採第二案——UA adapter 用新 `ua_*` id**，
> provenance 靠前綴天然可分（零 model 變更）；對照表不另建檔，**併入語彙目錄**
> （每列同載 legacy id / kind / symbol / ua id）；bridge 鏡射項為 Plan 01B
> 「支援 UA rule_id」依賴的具體化，於 Plan 16 Task 3 落地。
> 本節的 gate 輸入需求（對照表 + provenance 可標示）**維持不變**。

## Parity Gate 標準

Plan 14 report 必須至少包含：

> **語料用語（2026-08-10 裁定 Q17①）：** 本檔「Tier A」一律採
> [Plan 14「語料唯一定義」](../s3-validation/14-local-project-import-and-test.md) 的定義＝
> **外部真實 repo（釘 SHA）**，**不含任何內部 fixture**。內部語料請直呼其名
> （Phase4 Plan 31 parity corpus／`tests/fixtures/rag_projects/`），不得寫成「Tier A fixtures」。

| 指標 | Gate |
|---|---|
| 覆蓋率 | **Tier A**（外部真實 repo、釘 SHA）代表性 facts 必須有 UA 等價輸出；缺口需有 accepted degradation 理由 |
| Evidence 等價性 | UA facts 必須能對回 project-relative path + line/config/json pointer evidence |
| 安全性 | UA output 不含 unmasked secrets、raw source、absolute local paths |
| Fail-closed | invalid schema / Node missing / required batch failed 不進 Step 4 |
| Apply regression | B1→B2 不重跑 UA 或 parity providers，只使用 `ScanSnapshot.scan_result` 重跑 Step 4～7；semantic sidecar 不消費 |
| Rule id migration | Step 4 bridge registry 可處理代表性 UA `rule_id` |
| **Rule id 對照 + provenance** | **`ua_*` ↔ legacy `rule_id` 對照表存在；parity report 每筆 fact 可標示來源（UA / legacy provider）。缺此項無法判讀 diff，gate 不通過**（2026-08-05 新增） |
| **per-provider 分類表** | **Plan 14 報告含固定第二張表「per-provider parity 分類表」，每個 Systograph provider rule 都有五分類之一（`covered_by_ua`／`accepted_gap`／`needs_ua_adapter_fix`／`retain_as_vocabulary`／`retain_as_mechanism`）與 provenance 欄。未分類或存在 `needs_ua_adapter_fix` 時 gate 不通過**（2026-08-10 裁定 Q17③） |
| **函式外建構（G1）parity** | **[16H](../s2-ua-integration/16H-ast-construction-provider.md) `ast_construction_provider` 的產出須納入 parity 對比，作為 `code_pattern` provider 退役的前提之一**（16E §2 移交，2026-08-10 經 Q17 裁定）。理由見上方「`code_pattern` —— 全退機制，TOML 升格」節 |

> **Machine diff 與退役裁定是兩層 contract：** Plan 16 Task 7 的
> `systograph-ua-parity/v1` 先逐 fact 輸出 `equivalent`／`missing`／`extra`／
> `intentionally_degraded` 與雙邊 provenance；Plan 14 再把這些 raw rows 聚合為本表的五種
> provider-rule 治理分類。raw `intentionally_degraded` 只代表「catalog 無 UA mirror」，不能
> 直接當作本計畫已接受的 `accepted_gap`。Plan 18 必須同時保存 machine report 的
> `inventory_digest`、byte-stable artifact digest，以及 Plan 14 凍結的五分類表。

任何 blocker 未解時，本計畫維持 pending。

## Task 1：凍結 parity report 與退役清單

**Files**

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s3-validation/14-local-project-import-and-test.md`
- Create: `docs/work/Timmy/schedule/report/ua-parity-retirement-YYYY-MM-DD.md`
- Test: documentation review

> **報告格式分工（2026-08-10 裁定 Q17③）：** per-provider 五分類表**由 Plan 14 產出、本計畫消費**。
> Plan 14 的本地 parity report 固定含第二張表「per-provider parity 分類表」（欄位：
> provider rule / provider / provenance / UA 等價 `rule_id` / 分類 / 依據，格式見
> [Plan 14 Task 7](../s3-validation/14-local-project-import-and-test.md)）。
> 本計畫的 `ua-parity-retirement-YYYY-MM-DD.md` **不重新分類**，只原樣凍結該表，
> 並引用原始 `systograph-ua-parity/v1` artifact path／digest 與 immutable invocation counters
> （`filesystem_scan=1`、`ua_sidecar=1`、`parity_providers=1`），再加上本計畫自有的決策紀錄
> （docker fact 四類裁定、回退方案、owner、fallback status）。

**Steps**

- [ ] 收集 Plan 14 parity report 路徑、執行日期、target / fixture 清單。
- [ ] 確認 `ua_*` ↔ legacy `rule_id` 對照表已存在，且 parity report 可標示 fact provenance；
  缺任一項則本 task 停止（gate 必要輸入，見「rule_id provenance 兩難」）。
- [ ] **確認 Plan 14 報告的「per-provider parity 分類表」覆蓋全部 Systograph provider rule**，
  分類值唯五：`covered_by_ua`、`accepted_gap`、`needs_ua_adapter_fix`、
  `retain_as_vocabulary`（語彙目錄續留）、`retain_as_mechanism`（機制續留，如
  `dependency_manifest`）；覆蓋不全或出現自創分類值，本 task 停止。
- [ ] 將該表**原樣凍結**進 `ua-parity-retirement-YYYY-MM-DD.md`；
  **本計畫不重新分類**（分類的 source of truth 是 Plan 14 報告）。
- [ ] 未分類或 `needs_ua_adapter_fix` 不得退役。
- [ ] 記錄回退方案與 owner。

## Task 2：建立 provider usage inventory

**Files**

- Test: `tests/unit/core/test_scan_provider_retirement_boundaries.py`
- Tooling: `rg` inventory（實作時執行）

**Steps**

- [ ] 搜尋 `CodePatternProvider`、`DockerComposeProvider`、config provider 直接被
  `ProjectScanService` / `MapBuildService` 使用的位置。
  （`DependencyManifestProvider` 不在退役範圍，只需確認其呼叫點不受影響。）
- [ ] **docker fact consumer audit（本 task 的核心產出）**：逐一確認
  `docker_environment` / `docker_env_file` / `docker_volume` / `docker_depends_on`
  四類 fact 的真實 consumer。2026-08-05 預查結果見「退役範圍」表，
  **須以實作當下的 `rg` 結果為準**，不得直接沿用。
- [ ] 依 audit 結果對四類 fact 各自裁定「provider 瘦身續命」或「accepted degradation」；
  選後者必須寫下書面理由並記入 retirement report。
- [ ] 搜尋 tests / fixtures 依賴舊 `rule_id` 的位置。
- [ ] 將 usage 分類為 main scan path、parity harness、legacy fixture、metadata-only、
  migration test。
- [ ] 新增 source guardrail：main scan path 不得 import retired providers
  （guardrail 允許清單需含 `DependencyManifestProvider`，它是續留的 primary provider）。

## Task 3：切換 main scan path

**Files**

- Modify: `src/systograph/core/services/project_scan_service.py`
- Modify: `src/systograph/core/services/ua_structural_adapter.py`
- Test: `tests/unit/core/test_project_scan_service.py`
- Test: `tests/integration/test_map_build_service.py`

**Steps**

- [ ] `ProjectScanService` main path 以 `UnderstandAnythingAnalysisService` +
  `UaStructuralAdapter` 為 primary，**並保留 `DependencyManifestProvider`**
  （無 UA 等價物，見「退役範圍」）。
- [ ] 移除或 feature-flag 退役 providers 的 default registration
  （`code_pattern`、config patterns；`docker_image` 依 Task 2 audit 結果決定瘦身或退役）。
- [ ] Parity harness 可保留顯式 dry-run 入口，但不在 production/default scan path 執行。
- [ ] `ProjectScanResult` ordering、dedup、masking 與 warnings 保持 deterministic。

## Task 4：遷移 fixture 與 rule_id expectations

**Files**

- Modify: `tests/fixtures/rag_projects/`
- Modify: `tests/unit/core/test_component_bridge_registry.py`
- Modify: `tests/integration/test_phase4_rag_fixture_behaviors.py`
- Test: focused fixture regressions

**Steps**

- [ ] Phase4 Plan 31（`31-expand-advanced-rag-fixtures.md`）的 fixtures 轉成 UA parity corpus；保留 old/new expected facts 對照。
- [ ] 將 tests 中直接 assert 舊 TOML `rule_id` 的地方改為 UA `rule_id` 或 migration alias。
- [ ] `component_bridge_registry.py` 支援必要 UA `rule_id`。
- [ ] **同步更新 `component_bridge_rules.py` 寫死的 legacy `rule_id` 字串**（見 R2）——
  改 `rule_id` 只改 TOML 會漏；13 條規則的 `rule_ids=frozenset({...})` 必須一起改。
- [ ] `dependency_*` rule id 與 `dependency_candidate` fact kind 的既有 assertions **維持不變**
  （provider 不退役）。
- [ ] 舊 rule id 只在 parity report、migration fixtures 或 accepted compatibility tests 中出現。

## Task 5：保留語彙 / metadata TOML，只移除可執行掃描機制

**Files**

- Modify: `src/systograph/core/services/rule_catalog_loader.py`（只有必要時）
- Test: `tests/unit/core/test_rule_catalog_loader.py`
- Test: `tests/unit/core/test_scan_provider_retirement_boundaries.py`

**Steps**

- [ ] 保留 `risk_hint` / `recommended_next_check` metadata loaders。
- [ ] 保留 `scan_inventory_rules.toml` 作 boundary / include-ignore metadata。
- [ ] 不移除 `llm_proposal.toml`；它屬 Step 9 optional provider config。
- [ ] **保留 `code_pattern_rules.toml` 的 `rule_id` / `kind`（Step 4 bridge 匹配鍵），
  只移除 `regex` 欄位所代表的掃描機制**；預留 16E §2.7 的 optional `symbol` 欄位空間。
- [ ] **保留 `docker_image_rules.toml`**——UA 路徑仍需 image repository → `rule_id` 查表，
  以及查無時的 `docker_service_image_detected` fallback。
- [ ] **保留 `dependency_manifest_rules.toml` 與其 provider**（機制與語彙都不退）。
- [ ] Loader / docs 明確標示：這三份 TOML 的定位由「掃描規則」改為
  **語彙目錄（symbol / image / package → `rule_id`）**，不再承載 regex 掃描機制。

## Task 6：回退方案

**Files**

- Modify: `docs/MODEL-CONTRACT.md` 或 implementation issue checklist（視實作安排）
- Test: `tests/unit/core/test_project_scan_service.py`

**Steps**

- [ ] 定義暫時恢復 providers 的 feature flag / config，例如
  `SYSTOGRAPH_ENABLE_LEGACY_SCAN_PROVIDERS`（沿用 `canonical_output_configuration.py` 的
  `SYSTOGRAPH_*` env 慣例；2026-08-10 由舊命名更正）。
- [ ] 回退預設為 off；啟用時必須在 logs / build warnings 明確標示 legacy scan fallback。
- [ ] 回退不得繞過 UA fail-closed；只有 UA 重大缺陷且經明確風險決策時可使用。
- [ ] 回退路徑有測試，並不更新 Plan 18 retirement report 為完成。

## Task 7：最終退役驗證

**Files**

- Test: `tests/unit/core/test_project_scan_service.py`
- Test: `tests/unit/core/test_component_bridge_registry.py`
- Test: `tests/integration/test_map_build_service.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`

**Steps**

- [ ] 跑 focused backend tests，確認 UA-primary main scan path 通過
  （UA + 續留的 `DependencyManifestProvider`；不是 UA-only）。
- [ ] 跑 source guardrail，確認 retired providers 不在 default scan path，
  且**續留 provider 未被誤擋**。
- [ ] 跑 secret/path safety tests，確認退役後沒有 masking regression。
- [ ] 跑 **Plan 14 的內部 fixture 子集**（`tests/fixtures/rag_projects/` 邊推導基線 +
  Phase4 Plan 31 parity corpus 的代表列），確認 results deterministic。
  （2026-08-10 更正 Q17①：原寫「Tier A fixture subset」；Tier A 依 Plan 14 唯一定義＝
  外部真實 repo，不得用來稱呼 fixtures。Tier A 本身的覆蓋率判定在「Parity Gate 標準」。）
- [ ] 確認 `dependency_candidate` → `UNMAPPED_REVIEW_ITEM` 路徑仍有 review items 產出，
  沒有因退役而靜默歸零。
- [ ] 更新 retirement report，記錄 retained 語彙 / metadata catalogs、
  docker fact 四類的裁定結果與 fallback status。

## Acceptance Criteria

- [ ] Plan 14 parity report 通過且被本計畫引用。
- [ ] `ua_*` ↔ legacy `rule_id` 對照表存在（產出者＝Plan 16 Task 3），
  且 parity report 每筆 fact 可標示 provenance。
- [ ] Plan 14 的 **per-provider parity 分類表**已原樣凍結進 retirement report，
  且無未分類、無自創分類值、無 `needs_ua_adapter_fix` 殘留（Q17③）。
- [ ] **`code_pattern` 退役前，16H `ast_construction_provider` 的 G1（函式外建構）產出
  已納入 parity 對比**（16E 移交，2026-08-10 經 Q17 裁定）。
- [ ] Default Step 3 main scan path 不再執行 `code_pattern`、config patterns providers。
- [ ] `docker_image` provider 已依 Task 2 consumer audit 結果處置：
  image 偵測改由 UA 提供；`environment` / `env_file` / `volumes` / `depends_on`
  四類 fact 各有明確裁定（瘦身續命或書面 accepted degradation）。
- [ ] **`DependencyManifestProvider` 仍在 default scan path 正常運作**（不在退役範圍）。
- [ ] UA structural facts 覆蓋代表性 config / docker image / symbol / endpoint facts。
- [ ] Step 4 bridge registry 可處理 UA `rule_id`。
- [ ] Retained TOML catalogs 為**語彙目錄 / metadata / boundary / provider config**，
  其中語彙目錄（`code_pattern_rules`、`docker_image_rules`、`dependency_manifest_rules`）
  不再承載 regex 掃描機制，但仍是 `rule_id` / `kind` 的 source of truth。
- [ ] Legacy provider fallback 預設關閉，且有明確風險標示與測試。
- [ ] Fixture / rule_id migration 不破壞五態、52 列完整 emit、禁止 numeric confidence 等凍結契約。

## 風險 / 已知缺口（2026-08-05 新增）

### R1：語言缺口——「12 語言」效益會被語彙目錄卡住（不在本計畫 scope）

UA 提供 12 語言的**結構事實**，但 Systograph 的**符號語彙**幾乎只有 Python：
`code_pattern_rules.toml` 13 條中 11 條是 python-only，
1 條 `["python","javascript","typescript"]`（`embedding_openai_sdk_create`），
1 條 `["javascript","typescript"]`（`route_express`）。

後果：UA 掃到 TypeScript 專案的 `new QdrantClient()` **有結構事實、無語彙對應**，
在 Step 4 變不成元件。擴大語言覆蓋的效益會卡在語彙目錄這一關，而不是掃描機制。

**處置：記為風險，不擴 Plan 18 scope。** 本計畫只負責退役機制，
補語彙是後續計畫的事（與 16E §2.7 的 `symbol` 欄位擴充同一戰場）。

### R2：bridge 寫死 legacy `rule_id`——刪 TOML 不會讓它消失

`component_bridge_rules.py` 的 13 條規則**把 legacy `rule_id` 字串寫死在 Python 裡**
（`code_pattern_vector_store_qdrant`、`docker_qdrant_image_detected`、
`code_pattern_route_fastapi` …，見 `:14-15,29,41,53,67-68,82,94,106,120-121,137-139,153,165,178`）。

即使把 TOML 檔整個刪掉，這些 id 仍活在 Python 常數裡——
**刪檔不等於退役，只會讓 source of truth 從「一份 TOML」變成「散在 Python 的字串」。**
這反向佐證了本計畫的核心裁定：語彙應該集中在 TOML 目錄裡管理，而不是刪掉。

同時這也是 Task 4 的實作前提：改 `rule_id` 必須同步改 `component_bridge_rules.py`，
不能只改 TOML。

## 邊界 / 不做事項

- 不退役 UA sidecar。
- **不退役 `DependencyManifestProvider`**（2026-08-05 修訂：原列為退役對象）。
- **不刪除任何 `core/rules/*.toml`**——包含三份 scan TOML；本計畫只移除其中的掃描機制。
- 不刪除 `risk_hint` / `recommended_next_check` / `scan_inventory_rules` / profile metadata TOML。
- 不決定語彙目錄改名（如 `component_symbol_catalog.toml`）；列為 open option。
- 不擴充符號語彙的語言覆蓋（見 R1），也不實作 16E §2.7 的 `symbol` 欄位。
- 不更動 `ProfileInferenceService` 五態語意。
- 不新增 public artifact 或 frontend 欄位。
- 不產出 `ua_*` ↔ legacy `rule_id` 對照表；本計畫只消費它（產出者＝Plan 16 Task 3，見「依賴」）。
- 不產出 per-provider parity 分類表，也不重新分類；本計畫只凍結 Plan 14 的表（Q17③）。
- 不實作 16H `ast_construction_provider`；只把它的 G1 產出列為 `code_pattern` 退役前提。
- 不把 Plan 18 當成 Plan 14 的替代；沒有 Plan 14 parity report 不得執行。
