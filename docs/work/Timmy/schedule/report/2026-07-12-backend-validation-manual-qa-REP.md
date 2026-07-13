# Backend Validation / Manual QA Report

## 範圍與結果

Plan 05–09 backend implementation已通過實際 CLI/API surface；automated gates
（pytest / Ruff / Mypy / diff check）以 **2026-07-13 重驗** 為準（見下方 correction）。
Frontend 不在本次交付；本輪 frontend changes已全部恢復。

## 實作邏輯

- Focused tests用來快速定位 Plan 05–09 contract regression；full suite才是最終 gate。
- CLI以 help、valid map與invalid path三條使用者路徑驗證。
- Live API使用 fresh state建立真實 build，再依序驗證 valid、missing、invalid
  `profile_signals.json`；每次 sidecar狀態改變後重啟 server，避免 memory cache造成假綠燈。
- Review-work依使用者「不要 subagent」要求改為單代理執行五個 lane：goal/constraint、
  hands-on QA、code quality、security、context/history。

## 步驟

1. 執行 Plan 05–09 focused backend matrix。
2. 執行 full pytest、Ruff、Mypy與 diff check。
3. 執行 `kai-mind --help`、`validate-map --help`、`map --help`。
4. 驗證 valid v1 map與 absolute evidence path invalid map exit behavior。
5. 掃描真實 sample project並檢查十個 sibling artifacts。
6. 啟動 local API、import project、建立 build並查詢 build-scoped response。
7. 分別移除、破壞 profile sidecar，restart後回讀 degraded response。
8. 停止 server並清理 fresh state、output與 temp payloads。

## 測試方式與結果

| Gate | 結果 |
|---|---|
| Focused backend matrix | `118 passed`（2026-07-12） |
| Full backend suite | `768 passed in 17.43s`（2026-07-12） |
| Ruff | **2026-07-13 重驗通過**：`uv run ruff check src tests` + `uv run ruff format --check src tests`（見 correction；原 2026-07-12 宣稱已失效） |
| Mypy | `247 source files`, 0 issues（2026-07-12；與 2026-07-13 重驗一致） |
| Git diff check | pass |
| `uv lock --check` | **2026-07-13 重驗通過**（原報告未重驗） |
| CLI valid map | exit 0，`loaded=true nodes=67 edges=9` |
| CLI invalid map | exit 1，回傳 project-relative POSIX path error |
| Real map build | 10 sibling artifacts完整產生 |
| Artifact safety scan | 無 `/Users/`、AWS key prefix或 OpenAI-style key pattern |

## Live API 結果

### Valid profile sidecar

- `loaded=true`
- warnings：空
- profile/readiness available：true/true
- graph：70 nodes、1 canonical edge
- semantic kinds：reference、repo、unmapped、profile attachment
- details：52 reference assessments、15 profile findings
- Mapping Completeness：`3.5 / 52`

### Missing profile sidecar

- `loaded=true`
- warning：`profile_signals_missing_or_invalid`
- profile available：false；readiness available：true
- base graph：67 nodes；profile nodes：0
- Mapping Completeness：null

### Invalid profile sidecar

- 與 missing相同 fail-soft contract：loaded base graph、bounded warning、67 nodes、
  profile nodes 0、Mapping Completeness null。

## 遇到的問題與解法

- 問題：full suite先前有 stale `highlight` assertion與 Markdown compatibility gap。
- 解法：保留 target `highlight_and_dim` contract；為缺少的 Markdown sections新增
  regression test後恢復輸出。
- 問題：最終 review發現 v1 compatibility details會清空 profile/reference details。
- 解法：先讓 regression test紅燈，再改為局部更新 evidence/risk dictionaries；live API
  最終確認 52/15 detail dictionaries存在。
- 問題：使用 production preview做 frontend QA會受既有 CORS allowlist與 Vite
  `web-worker` baseline影響。
- 解法：依最新 backend-only分工撤回全部 frontend changes，不放寬 CORS，也不把
  frontend baseline問題混入後端交付。

## Review / Debugging 三假設

1. Confirmed/fixed：v1 detail enrichment整體覆寫 semantic details。
2. Refuted：`SystemMapIndex`回傳物件可反向 mutation source map；direct driver證明 source
   map不變。
3. Refuted：semantic mappings被加入 runtime topology；direct driver得到2 canonical
   edges與7 separate semantic relationships，ids無重疊。

## Correction（2026-07-13）— Ruff gate 假綠燈

驗收時發現本報告與 Plan 06 原先宣稱「Ruff 通過」不成立：

- 當時實際：`ruff check src tests` 大量 E501（中文註解依 East Asian 顯示寬度超長）；
  `ruff format --check src tests` 多檔需重排。
- 根因：後續加入的中文檔頭／函式註解未依 `line-length = 79`（CJK 雙寬）折行；
  另有少數過長測試函式名與 format 衝突。
- 修正：折行註解、`ruff format`、縮短兩個測試函式名；並重跑
  `uv run ruff check src tests`、`uv run ruff format --check src tests`、
  `uv lock --check` 皆通過。
- 因此「automated gates 全通過」以本 correction 後的重驗為準，不以 2026-07-12
  原文 Ruff 列為證據。

## 最終判定

Backend review lanes均通過，沒有 blocking issue。Fresh API server、state、build output與
temp payload已清理，沒有 background process留在 QA port。

**Automated lint gate（2026-07-13）**：Ruff check + format check + `uv lock --check` 已重驗通過。
