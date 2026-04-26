# Backend Code Review

審查依據：

- `.cursor/rules/linux_torvalds_code_review.mdc`
- `.cursor/rules/linus_torvalds.mdc`
- 通用後端工程最佳實踐

## 核心判斷

目前後端已從巨石 `Analysis.py` 拆出 API / service / repository / core / utils，方向是對的；但真正的風險集中在「安全邊界缺失」、「LLM 產出被當程式碼執行」、「檔案型資料存取未全面正規化」、「全域狀態與背景 subprocess」這四類。

以指定規則來看，這些不是理論問題，而是會直接造成資料刪除、任意程式碼執行、跨使用者狀態污染或 KB rebuild 競態的真問題。短期應先修安全與資料邊界，再談更漂亮的抽象。

## 評分表

| 面向 | 分數 | 優先級 | 現況與證據 | 問題 | 建議 |
|---|---:|---|---|---|---|
| 架構清晰度 | 3 | Medium | `Analysis.py:138-143` 註冊 Blueprint；`core/dependencies.py` 提供手動 DI | 分層已成形，但 `gptChat.py`、`ClusterService`、`TicketService` 仍是大型 orchestration | 把 AI provider、agent state、file persistence 拆成明確介面 |
| 模組邊界 | 3 | High | API 呼叫 service；service 又直接操作檔案、subprocess、AI | service 邊界太寬，repository 沒完整承接資料存取 | 建立 ResultRepository、FileStorage、JobQueue 介面 |
| 關注點分離 | 2 | High | `TicketService.save_analysis_files()` 同時寫 JSON、Excel、sync；`ClusterService.cluster_excel()` 同時分類、寫檔、搬檔 | 單一函式做太多事，特殊情況與副作用混在一起 | 拆成 analyze、persist、export、sync、schedule KB rebuild |
| 命名與可讀性 | 3 | Medium | 多數類別命名清楚；但 `HybridQuery_agent_handle`、中英文混雜、`pass` placeholder 多 | 可讀性不穩，部分註解描述已過期 | 移除空 `pass`、統一 function 命名、保留必要註解 |
| 錯誤處理 | 2 | High | `core/error_handler.py` 有統一格式；route 又各自 catch；`ClusterService` 多處 `except Exception: pass` | 會吞掉真錯誤，造成假成功 | 禁止裸 `pass`，將 recoverable / fatal error 分級 |
| 日誌與可觀測性 | 3 | Medium | `core/logger.py` 有 rotating logs；多數 service 用 logger | agents / gpt_utils 仍大量 `print()`，缺 request id / job id | 增加 request_id、job_id、provider latency、structured logs |
| 安全性 | 1 | Critical | 無 auth；`/clear-folder` 可清任意路徑；SQLAgent 執行 LLM 產出的 pandas code | 有實際任意刪除與任意程式碼執行風險 | 先加 auth/admin guard、路徑白名單、移除 eval/exec |
| 測試性 | 3 | Medium | `tests/unit`、`tests/integration` 完整；`conftest.py` stub heavy deps | 最高風險流程標示 `pragma: no cover`，AI/檔案錯誤路徑覆蓋不足 | 對安全 guard、job lock、path traversal、LLM code 禁止加測試 |
| 可維護性 | 2 | High | service 層已有，但大型流程仍很長 | 改一個流程容易影響檔案、AI、sync、KB | 先切資料存取與 provider adapter，降低 blast radius |
| 可擴充性 | 3 | Medium | 手動 DI 簡單；AI fallback 已集中部分邏輯 | 背景任務用 `subprocess.Popen`，無佇列與狀態 | 導入最小 job table / worker，不急著上大型 queue |
| 資料庫設計 | 2 | Medium | SQLite schema 簡單；`metadata` 可供 RAG | 無 migration、索引、資料版本；JSON / SQLite / FAISS 同步關係鬆散 | 增加 schema version、必要索引、KB build manifest |
| API 設計 | 2 | High | `/api/v2` prefix 已有；保留 legacy paths | GET 開本機檔案、POST 清資料夾、設定 API 無 auth；錯誤格式不完全一致 | 區分 public/user/admin API；破壞性 API 加確認與權限 |
| 程式碼重複與複雜度 | 2 | Medium | 多處 AI fallback、sync handling、Excel formatting 重複 | 重複邏輯讓 bug 修一次不會全修 | 建立 provider chain、excel export helper、sync result helper |
| 過度設計或不必要抽象 | 3 | Low | 手動 DI、repository 抽象簡單 | `ConfigRepository` 與 `ConfigLoader` 重疊；某些 repository 名不符實際用途 | 刪除或合併未使用抽象，不新增框架式複雜度 |
| 高風險技術債 | 1 | Critical | LLM code execution、無 auth、全域 callback、任意 path 操作 | 這些會造成事故，不是風格問題 | 排入 Critical / High roadmap |

## Critical Issues

### 1. LLM 產出的 pandas code 會被 `eval()` / `exec()` 執行

- 影響範圍：RAG hybrid / SQL agent pandas filter。
- 證據：`agents/sql_agent.py:544-566`。
- 問題：模型輸出是不可信輸入。即使 global 只傳 `pd`，Python 仍不應執行任意字串。這違反「實用、安全、簡單」原則，因為它把查詢問題變成任意程式碼執行問題。
- 建議：

```python
import ast

ALLOWED_NODES = (
    ast.Expression,
    ast.Subscript,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Compare,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
)

def reject_unsafe_expression(code: str) -> None:
    tree = ast.parse(code, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"Unsupported pandas filter syntax: {type(node).__name__}")
```

更務實的第一步：停用 pandas code execution，只允許 SQL SELECT 或預先定義 filter DSL。

### 2. `/api/v2/clear-folder` 可刪除任意資料夾

- 影響範圍：後端主機檔案系統。
- 證據：`api/config_routes.py:569-580` 將使用者輸入交給 service；`services/config_service.py:580-597` 對輸入路徑執行 `shutil.rmtree()`。
- 問題：沒有 auth、沒有白名單、沒有 path canonicalization。這是實際資料毀損風險。
- 建議：

```python
from pathlib import Path

ALLOWED_CLEAR_DIRS = {
    Path("uploads").resolve(),
    Path("json_data").resolve(),
    Path("excel_result_Unclustered").resolve(),
    Path("excel_result_Clustered").resolve(),
    Path("cache").resolve(),
}

def resolve_allowed_clear_dir(folder_name: str) -> Path:
    target = Path(folder_name).resolve()
    if target not in ALLOWED_CLEAR_DIRS:
        raise ValidationError("INVALID_PATH", "Folder is not allowed to be cleared")
    return target
```

### 3. 沒有認證與授權

- 影響範圍：全部 API，尤其設定、刪除、檔案開啟、清空歷史。
- 證據：route 中找不到 login/auth/token decorator；`CLAUDE.md` 也註明 internal tool no user auth。
- 問題：只要能連到 Flask，就能刪檔、改設定、讀歷史、開本機檔案。
- 建議：先做最小化 API key / admin token middleware，再評估 Flask-Login。內網單機也應保護破壞性 API。

### 4. History / Chat 檔案 ID 未正規化，存在 path traversal 風險

- 影響範圍：chat session、history result、download/delete。
- 證據：`repositories/chat_repository.py:174-175` 直接 `history_dir / f"{chat_id}.json"`；`services/history_service.py:133`、`167`、`298` 直接 join `uid`。
- 問題：`chat_id` / `uid` 是 URL 或 request 參數，不能直接組檔案路徑。
- 建議：只允許 `^[A-Za-z0-9_-]+$`，且用 `Path.resolve().relative_to(base)` 驗證。

## High Issues

### 5. RAG 狀態用 module-level global，與多使用者併發不相容

- 影響範圍：SSE streaming、AutoGen tool callback、步驟進度。
- 證據：`gptChat.py:60-64` 說明假設 Flask sequential single thread；`gptChat.py:144-164` 使用全域 step tracker。
- 問題：Flask debug reloader 或 production WSGI 不保證單 request，同時查詢會互相覆蓋 callback。
- 建議：用 request-scoped context 物件傳入 agents，或以 `chat_id/job_id` 綁定 status event sink。

### 6. 背景 KB rebuild 用裸 subprocess，沒有工作佇列與狀態管理

- 影響範圍：上傳完成後的 KB freshness、CPU/IO、lock file。
- 證據：`services/ticket_service.py:864-873` 每次上傳都 `subprocess.Popen([sys.executable, build_kb.py])`。
- 問題：多次上傳會產生多個 rebuild；錯誤只寫 log，不回到 UI；與 `KBService` lock 機制沒有統一。
- 建議：用 SQLite job table 或單 worker thread，合併短時間內 rebuild request。

### 7. 分群流程吞掉 Excel/AI 寫入錯誤

- 影響範圍：cluster output correctness。
- 證據：`services/cluster_service.py:245-265`、其他寫檔區塊多處 `except Exception as e: pass`。
- 問題：失敗被隱藏，使用者收到完成訊息但檔案可能不完整。
- 建議：能跳過單檔就記錄 per-file failure；不能繼續就丟 `ValidationError`。

### 8. 檔案下載 path guard 使用 `startswith()` 不嚴謹

- 影響範圍：clustered / summary download / open file。
- 證據：`services/cluster_service.py:971-975`、`1006-1010`、`1056-1060`。
- 問題：`/base_dir_evil` 會通過字串 `startswith('/base_dir')` 這種判斷。
- 建議：

```python
def ensure_inside(base: Path, target: Path) -> Path:
    base = base.resolve()
    target = target.resolve()
    target.relative_to(base)
    return target
```

## Medium Issues

### 9. SQLite schema 沒有 migration 與索引

- 證據：`core/database.py:27-50` 直接字串建表。
- 影響：欄位演進、查詢效能與部署相容性難追蹤。
- 建議：增加 `schema_version` 表與最小 migration runner，為 `opened`、`configurationItem`、`roleComponent` 建索引。

### 10. ConfigLoader 與 ConfigRepository 重疊

- 證據：`core/config_loader.py` 管理 `weight_config.json`；`repositories/config_repository.py` 管理 `weights.json` / `prompts.json`。
- 影響：設定來源混亂，未來會出現改 A 不改 B 的 bug。
- 建議：保留 `ConfigLoader` 或建立單一 `ConfigRepository`，另一個 deprecated 後移除。

### 11. `Analysis.py` 仍保留大量 legacy import / 註解

- 證據：`Analysis.py:146-185` 是已遷移函式的長註解清單。
- 影響：閱讀入口時噪音偏高。
- 建議：移到 migration notes，入口檔只保留 app setup。

### 12. 測試覆蓋避開最高風險路徑

- 證據：多個重 IO / AI workflow 標示 `pragma: no cover`，例如 `TicketService.save_analysis_files()`、`ClusterService.cluster_excel()`。
- 影響：安全 guard、錯誤處理、資料一致性沒有足夠測試保護。
- 建議：以 fake provider、tmp_path、fake excel client 補上行為測試。

## Low Issues

### 13. 部分註解與輸出不符合規則語系

- 證據：程式註解、debug print 有中文、emoji；規則要求程式註解、回傳內容、除錯訊息使用英文。
- 影響：團隊規範一致性不足。
- 建議：新改動先遵守；舊程式碼分批整理，不要做一次性大改。

### 14. `requirements.txt` 為 UTF-16 LE 且相依過大

- 證據：讀取時可見 null bytes；依賴包含 FastAPI、OpenTelemetry、ChromaDB、Docker、pywin32 等大量非核心套件。
- 影響：安裝慢、供應鏈風險大、跨平台更難。
- 建議：拆 `requirements-backend.txt`、`requirements-dev.txt`、`requirements-ai.txt`。

## 綜合評語

目前架構不是無法維護，而是「已拆層但安全與資料邊界還沒拆乾淨」。最符合指定規則的修法不是一次導入大型框架，而是先砍掉危險特殊情況：禁止 LLM code execution、限制破壞性檔案 API、補認證、移除全域 request state。這些做完，後面的 service 拆分才有穩固基礎。

