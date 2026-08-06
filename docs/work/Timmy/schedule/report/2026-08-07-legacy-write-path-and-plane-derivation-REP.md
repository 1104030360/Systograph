# 2026-08-07 Legacy 清理與語意收斂（Stage 3：Plans 06/07）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-07-web-boundary-backend-first-TODO.md`
- 分支：`refactor/web-boundary-and-legacy-retirement`；umbrella issue #277
- 起點 1138 passed / 1 skipped → 收尾 **1135 passed / 1 skipped**
  （06：−27 rollback 測試 +13 新測試；07：+9 +3 −1；帳目經 reviewer 獨立複算）

## 實作邏輯

Stage 2 收斂了 Web 邊界，Stage 3 收斂**產出語意**：

- **Plan 06**：v1 rollback writer 是「v2 之外的第二條產出路徑」。它的三個服務、
  兩個 pipeline 分支、env 觸發全部移除後，`MapBuildService`/`MapBuildPipeline`
  的 materialize 沒有 if/else——一條路。v1 的**讀取**能力（歷史 artifact 載入、
  v1→v2 adapter、validate-map）一行未動，`legacy_output_not_selectable` 422
  錯誤碼契約不退化。
- **Plan 07**：投影平面是 slot 的最後一個主開關。改為
  `canonical_type → capability node（陣列第一個 = primary）→ node.plane_id`
  之後，投影與評估（13.7 交付的 type 對位）共用同一條 type-driven 語意鏈，
  slot 誤填只污染 id/slug、不再畫錯帶。

## 步驟與成果

| Plan | Commits | 核心變更 | Review |
|---|---|---|---|
| 06 | `7b091ac`/`963b284`/`829fd75` | 三服務檔刪除；pipeline 單一 v2 路徑；env 收斂（`invalid_canonical_output_version`）；census 8→1 筆同 commit 同步；兩處 fixture 測試改吃靜態 v1 fixture（v1 讀取覆蓋保留）；(A) `operator_rollback_active` 恆 false；fix round 收斂 `canonical_output_version` 建構參數為單一真相源 `V2_SCHEMA_VERSION` | Approved → fix 3 項全 ADDRESSED |
| 07 | `fb65e27`/`e927ca2`/`e6a378e` | `CanonicalTypePlaneResolver`（fail-closed 沿用 loader 驗證）；normalize service 切換；`SLOT_LAYER_BY_ID` 降為 v1 adapter migration-only；risk hint 文案去 rag-core-v1；lens 成員資格契約化＋regression；MODEL-CONTRACT §5.1.1 | Approved with follow-ups → fix 7 項全 ADDRESSED |

## 測試方式

- **06 紅測試**：env 設 `ai-system-map/v1` → `MapBuildService()` 建構即失敗、
  `assert not (tmp_path / "build").exists()`（零 artifact）——切換前紅
  （舊行為會成功建出 v1）。
- **07 紅測試**：slot 誤填但 canonical_type 正確 → plane 斷言（切換前紅：
  `assert 'generation' == 'ingestion_indexing'`；以 git worktree 檢出 BASE
  複驗紅證據）。
- **行為對照**：12 個 fixture 全跑 BASE/HEAD build，15 個元件 7 個移帶、
  0 個掉 undetermined；只有 `vector_db`/`vector_db_config`
  （retrieval→ingestion_indexing，primary=index_builder）與 `api_route`
  （control→deployment_topology，primary=api_server）兩類移動，reviewer
  逐節點對 catalog 原始資料核對確認為忠實投影。Playwright 前後截圖 5 張。
- **護欄複驗**：13.7 Test A/Test B、type-node map loader fail-closed、
  13.8 profile 基線快照、census contract（46 passed）全綠未回退。
- **v1 讀取不回歸**：`systograph validate-map` 對 v1 fixture 實跑
  `loaded=true`。

## 遇到的問題與解法

1. **移除建構參數差點打掉 CLI 的 env fail-fast**（review 與計畫都未預見）：
   `cli/map_command.py` 直接 `MapBuildService()`，先前全靠 `__init__` 讀 env
   擋 v1。全套測試當場抓到；處置為保留 env 驗證**作為 guard**（丟棄回傳值＋
   註解明示），並補上先前根本不存在的 CLI env regression。
2. **census 雙向 fail-closed**：allowlist 同步必須與模組刪除同一 commit，
   否則 pre-commit 的 pytest 直接擋下——依計畫預告執行，無意外。
3. **`BuildArtifactPublisher.artifact_map` 計畫外刪除**：rollback 消失後
   恆為 None，留著等於保留任意 caller 可觸發的 v1 寫入能力——reviewer 逐
   caller 追溯（唯一 non-None 生產者就是被刪的 rollback service）判定為
   計畫目標的必然結果。
4. **`layer` 的第二個消費者**：review 發現 lens 成員資格也吃 `plane_id`
   （`lens:control` 10→9）——已契約化並加 regression，防止未來改 TOML
   primary node 時 lens 靜默漂移。
5. **stash 誤彈事故**：fix round 取 BASE 數據時 `git stash pop` 誤彈 main
   的既存舊 stash，4 檔暫時 conflict——完整復原（舊 stash 未 drop）、
   re-review 確認 fix diff 無汙染；後續改用 git worktree、禁用 stash pop。

## 測試結果（收尾實測）

- `uv run pytest`：**1135 passed, 1 skipped**；coverage 90.78%（gate 85%）
- `tests/contracts/`：46 passed（census 無 stale record、fail-closed 雙向）
- ruff check / ruff format --check / mypy：全綠
- `pnpm test`：160 passed（前端零改動）
- 驗收 grep：五個 rollback 類名全樹零命中；`SLOT_LAYER_BY_ID` active v2
  路徑零 import；risk hint 文案無 rag-core-v1

## 已知殘留（交 Stage 4/5 與最終 review）

- env guard 在 core 建構子屬層次混用（pre-existing 模式；正解 CLI startup
  hook，另案）
- `api_route → deployment_topology` 帶位若產品端不接受，修 catalog／映射
  而非回退查表
- v1/v2 對同類元件可能給不同 plane（migration 呈現 vs active 推導，
  已於 MODEL-CONTRACT 明示不回溯對齊）
- fixture 級 layer golden 斷言未加（unit 層 regression 已有）
