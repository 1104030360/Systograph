# 2026-08-10 scripts 清點、架構圖更新與總驗證（Stage 4）REP

- 對應 TODO：`docs/work/Timmy/schedule/todo/2026-08-10-build-scoped-report-download-TODO.md`
- 分支：`main`（本輪依指示**不 commit、不 push**，全部改動留在 working tree 由使用者驗收）

## 實作邏輯

程式碼與契約文件都換到新世界之後，剩下兩件事：(1) 確認 scripts/ 與其他
文件沒有殘留舊端點引用；(2) `learn/architecture.md` 的 ASCII 全景圖必須
如實反映現況——不只換掉舊端點那幾行，凡是「數 router、列 route 模組」的
地方都要跟 `src/systograph/web/` 的實況對齊。最後跑全套驗證收尾。

## 步驟與產出

### scripts/ 清點

- `rg "map/report|trace_map_report|latest_build_result"` 掃 `scripts/`、
  `README.md`、`docs/API-GUIDE.md`：僅剩 API-GUIDE 退役清單那 1 筆刻意
  保留的字面（退役佐證），其餘 0 筆。
- `scripts/dev.py`、`scripts/lib/api_trace_common.sh` 確認無需修改；
  全部 22 個 shell scripts `bash -n` 通過。

### architecture.md（gitignored 學習文件）

- 更新 18 處：兩張全景圖的端點清單、Web route 對照表（新增 artifact
  端點列）、退役框（補第 5 筆 `GET /api/map/report（2026-08-10 退役）`）、
  SessionStore 職責區（5 個方法、persistent save 為 no-op、
  `build_result` 不攔例外的實況描述）、router 數量 8→7（兩處）、
  已刪 router 清單（三支具名）、`routes/` 模組清單、關鍵檔對照、3 列 FAQ。
- **對齊驗證**：寫了 `check_box_alignment.py`（display width：全形=2、
  半形=1）驗證每個框的邊緣對齊，對全檔跑 exit 0；並用 4 種人為破壞
  （少一格、牆錯位、刪導引線、半形換全形）確認 checker 真的會抓錯——
  4/4 都抓到。

### 全量驗證（Stage 4b）

| Gate | 結果 |
|---|---|
| `uv run pytest` | **1146 passed, 1 skipped** |
| `uv run ruff check src tests` | 通過 |
| `uv run ruff format --check src tests` | 339 檔全部已格式化 |
| `uv run mypy src tests`（strict） | 325 檔 0 issue |
| `uv lock --check` | lock 與 pyproject 一致 |
| `pnpm lint` | 0 errors（1 個既有 warning 在未觸碰檔案） |
| `pnpm test` | **182 passed**（36 檔） |
| `pnpm build` | 通過 |
| `scripts/trace_all.sh --start-server`（隔離 state dir） | **18/18 PASS**（含更名後的 artifact 端點腳本） |

trace_all 以 `SYSTOGRAPH_STATE_DIR` 指到隔離目錄執行，真實
`~/.systograph` 未被觸碰。

## 遇到的問題與解法

1. **brief 給的 display-width 規則是錯的**：East Asian Width 的
   box-drawing 字元（U+2500–257F）屬 class `A`，照「W/F/A=2」算會全部
   爆炸。實測後改用「W/F=2」，每個框恰好收斂到單一寬度——用量測推翻
   指令，證據留在報告。
2. **對齊 gate 抓到兩次真錯**：手數全形寬度兩次都少 1 格，checker 都
   攔下——結論是這個檔案以後改動應該用腳本補寬，不要手數。
3. **token grep 掃不到語意殘留**：`include_router × 8`、模組清單裡的
   `map` 這種「數量與列表」殘留沒有關鍵字可 grep，第一輪漏掉、review
   抓回——補了一輪「凡數 router / 列模組的行都對照實況」的語意掃描。

## 收尾與遺留事項

- download.md checkbox 19 項全數勾選、Status **done**——每一項都由主
  agent 對照實作證據逐項確認後才勾。
- **2026-08-10 追記：** 前端改動因分工調整同日退回（本 repo 這輪由
  後端 owner 負責）。frontend 計畫改寫為**交接版**（Status 回
  planned、checkbox 未勾），含已驗證設計決策、陷阱、與通過全部 gate
  的 reference patch；退回後前端回到基線 `pnpm test` 160/160 全綠，
  `API_CONTRACT.md` 僅保留後端 Task 4 所寫的契約章節。上表 `pnpm`
  三列與 182/182 是**退回前**參考實作的量測值。
- 刻意保留的既有現象（都已記錄、不屬本次缺陷）：
  - `save_committed_build_projection` 的 except 分支在本次改動**之前**
    就已無法在 production 觸發（僅測試 monkeypatch 可達）——是否收斂
    屬後續 Protocol 瘦身決策。
  - `SessionStore.save_build_result` 的 `project_id` 參數現在唯一
    caller 都會帶，Optional 形同虛設——同上，屬後續決策。
  - `trace_map_build_artifact.sh` 在 curl 本身失敗時會留下 TMP_DIR
    （舊腳本同樣行為；共用 EXIT trap 屬 `--start-server`，不宜自設）。
  - 前端三個 UI 打磨項（disabled 按鈕的鍵盤焦點、`unknown` 文案、
    「Saved」措辭）——不影響正確性，見 Stage 3 REP。
- 後續可接的工作：#219 其餘範圍（`.mmd` 下載只需在白名單加兩列、
  `artifact_refs[]` 平台屬 Plan 06）、FE-2（`mapEndpoints` 死碼清理）。
