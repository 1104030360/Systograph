# Test Infrastructure Cleanup Report

## 結論

測試目錄保持原樣，改用 pytest collection hook 將既有目錄變成正式 markers。現在可以用
`-m` 穩定選取各層測試，marker 拼錯與無效 pytest config 會直接失敗；coverage 也已成為
可重現的 dev gate。

## 實作邏輯

- 100 個測試檔已按目錄分類，逐檔加 `pytestmark` 只會製造重複；集中式 collection hook
  才是最小且不漏標的做法。
- `contracts` 目錄對外 marker 使用單數 `contract`，讓語意與 marker 名稱一致。
- coverage 門檻採 85%，低於本次 89% baseline，能擋明顯 regression，又不逼團隊測試
  re-export、Protocol 或不可能 branch。

## 變更內容

- `pyproject.toml`
  - 增加 `pytest-cov>=6,<8` dev dependency。
  - 啟用 `--strict-config --strict-markers`。
  - 註冊 `unit`、`integration`、`contract`、`e2e`、`web`、`cli`、`smoke`。
  - 設定 branch coverage、source package 與 `fail_under = 85`。
- `tests/conftest.py`
  - 依測試檔第一層目錄自動套用 marker。
  - root `test_smoke.py` 明確套用 `smoke`。
- `uv.lock`
  - 鎖定 coverage 7.15.1、pytest-cov 7.1.0 與相依套件。

## Red / Green 證據

### Red

- 修改前 `.venv/bin/python -m pytest --collect-only -q -m unit`
  - `no tests collected (819 deselected)`。
- 修改前 `.venv/bin/python -m pytest --collect-only -q -m integration`
  - `no tests collected (819 deselected)`。
- 修改 dependency 後 `uv lock --check`
  - 明確失敗並回報 lockfile 需要更新。

### Green

- `-m unit`：649 tests collected。
- `-m integration`：56 tests collected。
- `-m contract`：35 tests collected。
- `-m 'e2e or web or cli or smoke'`：79 tests collected。
- marker 總數：649 + 56 + 35 + 79 = 819，沒有漏收或重複。
- `uv lock --check`：exit 0。
- `.venv/bin/ruff check tests/conftest.py pyproject.toml`：通過。
- `.venv/bin/mypy tests/conftest.py`：通過。

## 分層實際測試結果

- unit：`649 passed, 170 deselected in 5.64s`
- integration：`56 passed, 763 deselected in 2.76s`
- contract/e2e/web/cli/smoke：`114 passed, 705 deselected in 8.38s`
- 全量：`819 passed in 13.96s`

## 遇到的問題與解法

### comment checker 擋下不必要 docstring

- 現象：新增 collection hook 時，comment checker 指出 docstring 只是重述函式行為。
- 解法：移除 docstring，以短函式與清楚常數名稱表達行為；沒有繞過檢查。

### fixture 是否需要重新分層

- 盤點結果只有 `tests/conftest.py` 提供跨 suite 的 state isolation fixture，其他測試資料多為
  單檔 helper 或 `tests/helpers` 的 path helper。
- 因此沒有搬動 fixture；製造 nested conftest 反而會增加 lookup 隱性與維護成本。

## 使用方式

```bash
.venv/bin/python -m pytest -m unit
.venv/bin/python -m pytest -m integration
.venv/bin/python -m pytest -m contract
.venv/bin/python -m pytest -m "e2e or web or cli or smoke"
.venv/bin/python -m pytest --cov --cov-report=term-missing:skip-covered
```

## 剩餘風險

- marker 代表 test level，不代表所有 integration tests 都會連外；scanner fixtures 依設計維持
  read-only、deterministic、無外部服務。
- coverage 85% 是 regression floor，不是「所有行為都完成」的替代品；下一階段仍依高風險
  未覆蓋 branch 補測試。
