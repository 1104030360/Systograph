# Test Baseline and Taxonomy Report

## 結論

現有 suite 並沒有壞掉，也不需要大搬家。真正缺口是 pytest 沒有 executable taxonomy、
strict marker/config gate 與可重現的 coverage gate。現有目錄責任大致合理，應在原結構上
補齊執行契約。

## 實作邏輯

- 先執行完整 baseline，再決定是否搬檔，避免把「檔案很多」誤判為架構錯誤。
- 以 scanner 的 read-only、安全、artifact lifecycle、CLI/API contract 風險解讀 coverage，
  不為提高百分比去測 re-export 或 Protocol 宣告。
- 比對 R2R 後只採用清楚的 unit/integration 分層；它的大型 mock fixture 與吞錯 cleanup
  不適合直接複製到本專案。

## 步驟

1. 確認 `.venv/bin/python`、pytest、uv 與 Git 工作樹。
2. 執行全量 pytest 與 collection，記錄數量、時間與最慢測試。
3. 逐層統計 `contracts`、`unit`、`integration`、`e2e`、`web`、`cli` 與 smoke。
4. 以臨時 `pytest-cov` 執行 branch coverage，不先修改 dependency contract。
5. 讀取 integration tests 的 action boundary，確認多數測試會執行真實 provider/service、
   temporary filesystem 或 FastAPI route，而不是只驗 mock 呼叫。

## 測試方式與結果

- `.venv/bin/python -m pytest -q --durations=20`
  - 結果：`819 passed in 13.27s`
  - 最慢單一測試：0.31 秒，沒有明顯 slow-test blocker。
- `.venv/bin/python -m pytest --collect-only -q`
  - 結果：`819 tests collected in 0.90s`
- 分層 collection：
  - contracts：35
  - unit：649
  - integration：56
  - e2e：1
  - web：66
  - cli：11
  - smoke：1
- `uv run --frozen --with pytest-cov python -m pytest -q --cov=src/kai_mind
  --cov-branch --cov-report=term-missing:skip-covered --cov-report=json:coverage.json`
  - 結果：`819 passed in 25.44s`
  - production coverage：`89%`（9,420 statements、2,410 branches）。

## 遇到的問題與解法

### `-m unit`／`-m integration` 選不到任何測試

- 現象：兩個命令都回報 `819 deselected`。
- 根因：目錄有分類，但沒有註冊或套用 pytest markers。
- 解法：下一階段以單一 collection hook 依既有目錄套用 markers，並啟用 strict markers；
  不在 100 個測試檔重複增加 decorator。

### coverage 工具沒有納入專案 dependency

- 現象：`.venv` 只有 pytest，沒有 pytest-cov/coverage。
- 解法：baseline 先使用 `uv run --with pytest-cov` 的隔離環境；下一階段再把 coverage gate
  明確寫入 dev dependency 與 `pyproject.toml`。

## Coverage 風險判讀

- 不追求沒有意義的 100%；0% 檔案多是相容 re-export 或 Protocol-only module。
- 優先補齊的真實邊界：CLI failure output、query trace config validation、manifest/detail-scan
  lifecycle，以及 mapping proposal decision branches。
- suite 已具良好 unit 基線，但 E2E 目錄只有一個完整 lineage scenario；CLI/API 的真實表面
  目前分散在 `cli` 與 `web`，後續以 marker 統一選取，不強行改名。

## 剩餘風險

- 尚未建立 coverage fail-under，因此新增未測 production code 不會被 CI/本機 gate 擋下。
- 尚未驗證 marker 分層執行與 strict config。
- 89% 是 line/branch 綜合基線，不代表每個 release-readiness failure mode 都已受保護。
